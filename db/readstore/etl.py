"""Polling ETL: sync the Operational DB into the Read Store projections.

MVP strategy (architecture Section 8, plan.md Phase 6): a simple *full-refresh*
poll. Each run reads the authoritative Operational DB, recomputes every
projection in memory, and atomically replaces the corresponding Read Store
table (delete-all + insert within one transaction). True CDC (Debezium) is
backlog; polling is sufficient for the MVP's freshness requirements.

Run once:
    python -m db.readstore.etl
Run continuously (poll every N seconds):
    python -m db.readstore.etl --loop --interval 30

The Operational DB is read via ``db.session.SessionLocal`` (``DATABASE_URL``);
the Read Store is written via ``db.readstore.session.ReadStoreSession``
(``READ_STORE_URL``). Both must be reachable.
"""

from __future__ import annotations

import argparse
import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db.models import (
    Block,
    Division,
    Plan,
    PlanItem,
    Section,
    Train,
    TrainSchedule,
    Track,
    Zone,
)
from db.readstore.models import BlockView, PlanSummary, TrackView, TrainView
from db.readstore.session import ReadStoreSession
from db.session import SessionLocal

logger = logging.getLogger(__name__)


def _duration_minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def _org_names(db: Session) -> dict[uuid.UUID, tuple[str | None, str | None]]:
    """Map section_id -> (division_name, zone_name)."""
    divisions = {d.id: (d.name, d.zone_id) for d in db.scalars(select(Division)).all()}
    zones = {z.id: z.name for z in db.scalars(select(Zone)).all()}
    section_div = {s.id: s.division_id for s in db.scalars(select(Section)).all()}
    result: dict[uuid.UUID, tuple[str | None, str | None]] = {}
    for section_id, division_id in section_div.items():
        division = divisions.get(division_id)
        if division is None:
            result[section_id] = (None, None)
        else:
            division_name, zone_id = division
            result[section_id] = (division_name, zones.get(zone_id))
    return result


def _build_plan_summary(db: Session) -> list[dict]:
    plans = db.scalars(select(Plan)).all()
    sections = {s.id: s.name for s in db.scalars(select(Section)).all()}
    org = _org_names(db)

    blocks = db.scalars(select(Block)).all()
    blocks_by_plan: dict[uuid.UUID, list[Block]] = {}
    for b in blocks:
        blocks_by_plan.setdefault(b.plan_id, []).append(b)

    # request_count per plan = distinct block_request_id across its plan_items.
    items = db.scalars(select(PlanItem)).all()
    requests_by_plan: dict[uuid.UUID, set[uuid.UUID]] = {}
    for it in items:
        requests_by_plan.setdefault(it.plan_id, set()).add(it.block_request_id)

    rows: list[dict] = []
    for p in plans:
        plan_blocks = blocks_by_plan.get(p.id, [])
        total_minutes = sum(_duration_minutes(b.start_time, b.end_time) for b in plan_blocks)
        division_name, zone_name = org.get(p.section_id, (None, None))
        rows.append(
            {
                "plan_id": p.id,
                "status": p.status.value,
                "section_id": p.section_id,
                "section_name": sections.get(p.section_id, ""),
                "division_name": division_name,
                "zone_name": zone_name,
                "block_count": len(plan_blocks),
                "request_count": len(requests_by_plan.get(p.id, set())),
                "total_block_duration_minutes": total_minutes,
                "created_at": p.created_at,
            }
        )
    return rows


def _build_block_view(db: Session) -> list[dict]:
    blocks = db.scalars(select(Block)).all()
    plans = {p.id: p.status.value for p in db.scalars(select(Plan)).all()}
    tracks = {t.id: t for t in db.scalars(select(Track)).all()}
    sections = {s.id: s.name for s in db.scalars(select(Section)).all()}

    items = db.scalars(select(PlanItem)).all()
    requests_by_block: dict[uuid.UUID, int] = {}
    for it in items:
        requests_by_block[it.block_id] = requests_by_block.get(it.block_id, 0) + 1

    rows: list[dict] = []
    for b in blocks:
        track = tracks.get(b.track_id)
        section_name = sections.get(track.section_id) if track else None
        rows.append(
            {
                "block_id": b.id,
                "plan_id": b.plan_id,
                "plan_status": plans.get(b.plan_id, ""),
                "track_id": b.track_id,
                "track_code": track.code if track else "",
                "track_name": track.name if track else "",
                "section_name": section_name,
                "start_time": b.start_time,
                "end_time": b.end_time,
                "is_merged": b.is_merged,
                "request_count": requests_by_block.get(b.id, 0),
            }
        )
    return rows


def _build_track_view(db: Session) -> list[dict]:
    tracks = db.scalars(select(Track)).all()
    sections = {s.id: s.name for s in db.scalars(select(Section)).all()}
    org = _org_names(db)
    rows: list[dict] = []
    for t in tracks:
        division_name, zone_name = org.get(t.section_id, (None, None))
        rows.append(
            {
                "track_id": t.id,
                "code": t.code,
                "name": t.name,
                "line": t.line,
                "direction": t.direction,
                "is_active": t.is_active,
                "section_id": t.section_id,
                "section_name": sections.get(t.section_id, ""),
                "division_name": division_name,
                "zone_name": zone_name,
            }
        )
    return rows


def _build_train_view(db: Session) -> list[dict]:
    trains = db.scalars(select(Train)).all()
    schedules = db.scalars(select(TrainSchedule)).all()
    schedules_by_train: dict[uuid.UUID, int] = {}
    for s in schedules:
        schedules_by_train[s.train_id] = schedules_by_train.get(s.train_id, 0) + 1
    rows: list[dict] = []
    for t in trains:
        rows.append(
            {
                "train_id": t.id,
                "train_number": t.train_number,
                "train_type": t.train_type,
                "is_active": t.is_active,
                "schedule_count": schedules_by_train.get(t.id, 0),
            }
        )
    return rows


def _replace(session: Session, model, rows: list[dict]) -> int:
    """Atomically replace all rows of a projection table with ``rows``."""
    session.execute(delete(model))
    if rows:
        session.execute(model.__table__.insert(), rows)
    return len(rows)


def sync_read_store() -> dict[str, int]:
    """Run one full-refresh sync. Returns per-projection row counts."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as op_db:
        plan_rows = _build_plan_summary(op_db)
        block_rows = _build_block_view(op_db)
        track_rows = _build_track_view(op_db)
        train_rows = _build_train_view(op_db)

    # Stamp every row with the sync time, then write to the Read Store.
    for rows in (plan_rows, block_rows, track_rows, train_rows):
        for r in rows:
            r["synced_at"] = now

    with ReadStoreSession() as rs:
        counts = {
            "plan_summary": _replace(rs, PlanSummary, plan_rows),
            "block_view": _replace(rs, BlockView, block_rows),
            "track_view": _replace(rs, TrackView, track_rows),
            "train_view": _replace(rs, TrainView, train_rows),
        }
        rs.commit()
    logger.info("Read Store synced: %s", counts)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Sync the Operational DB into the Read Store.")
    parser.add_argument("--loop", action="store_true", help="Run continuously.")
    parser.add_argument(
        "--interval", type=int, default=30, help="Seconds between polls when --loop is set."
    )
    args = parser.parse_args()

    if not args.loop:
        sync_read_store()
        return

    logger.info("Starting polling ETL (interval=%ss). Ctrl-C to stop.", args.interval)
    while True:
        try:
            sync_read_store()
        except Exception:  # noqa: BLE001 - keep the poller alive on transient errors
            logger.exception("Sync failed; will retry next interval")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
