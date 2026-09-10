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
    Restriction,
    Section,
    Train,
    TrainSchedule,
    Track,
    Zone,
)
from db.readstore.models import (
    BaseGraphEdge,
    BaseGraphNode,
    BlockView,
    DataTile,
    PlanSummary,
    TrackView,
    TrainPosition,
    TrainView,
)
from db.readstore.session import ReadStoreSession
from db.readstore.tiling import position_tiles
from db.session import SessionLocal

logger = logging.getLogger(__name__)


def _duration_minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


# ── Schematic geometry & tiling helpers ────────────────────────────────


def _track_geometry(tracks: list[Track]) -> dict[uuid.UUID, tuple[float, float, float, float]]:
    """Assign each track a schematic (x1, y1, x2, y2) segment on a large grid.

    The Operational DB stores tracks as abstract segments. For the MVP map we lay
    the network out on a grid where:
    - Rows (Y-axis) represent parallel lines (UP Main, DOWN Main, Goods, Sidings).
    - Columns (X-axis) represent sections (North, Central, South, Express).

    Each grid cell is 40 km × 20 km, creating a large, complex network. Tracks are
    drawn as lines connecting two grid cells. This is a *schematic* layout suitable
    for rendering a busy, realistic rail network. A real deployment would read
    geographic coordinates from GIS.
    """
    geometry: dict[uuid.UUID, tuple[float, float, float, float]] = {}

    # Parse track codes like "TRK-A1", "TRK-B2" -> (row_letter, col_num)
    # Then map to grid coordinates
    for t in tracks:
        code = t.code
        # Extract row (A-Z) and column (1-9)
        try:
            parts = code.split("-")
            if len(parts) >= 2:
                row_col = parts[1]  # e.g., "A1", "B2"
                row_letter = row_col[0]  # "A", "B", etc.
                col_num = int(row_col[1:])  # 1, 2, 3, etc.

                row = ord(row_letter) - ord("A")  # 0, 1, 2, 3, 4
                col = col_num - 1  # 0, 1, 2, 3
            else:
                # Fallback: simple linear assignment
                row, col = 0, 0
        except (ValueError, IndexError):
            row, col = 0, 0

        # Grid spacing: 40 km × 20 km per cell
        cell_width = 40_000.0
        cell_height = 20_000.0

        # Each track spans multiple columns within its row (40 km)
        x1 = col * cell_width
        x2 = (col + 1) * cell_width
        y = row * cell_height + 10_000.0  # Center of the row

        geometry[t.id] = (x1, y, x2, y)

    return geometry



# Tile-ID / time-bucket helpers live in ``db.readstore.tiling`` (shared with the
# Query Service) and are imported at the top of this module.


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


def _build_train_positions(db: Session) -> list[dict]:
    """Derive a schematic position for each train schedule.

    A train is "on" its track between ``scheduled_start`` and ``scheduled_end``.
    For the MVP we place the train at the track's midpoint (a static position
    per schedule window). A real system would interpolate along the segment
    using the schedule timing.
    """
    trains = {t.id: t for t in db.scalars(select(Train)).all()}
    tracks = {t.id: t for t in db.scalars(select(Track)).all()}
    geometry = _track_geometry(list(tracks.values()))
    schedules = db.scalars(select(TrainSchedule)).all()

    rows: list[dict] = []
    for s in schedules:
        train = trains.get(s.train_id)
        track = tracks.get(s.track_id)
        if train is None or track is None:
            continue
        x1, y1, x2, y2 = geometry[s.track_id]
        rows.append(
            {
                "train_id": s.train_id,
                "train_number": train.train_number,
                "track_id": s.track_id,
                "track_code": track.code,
                "x": (x1 + x2) / 2,
                "y": (y1 + y2) / 2,
                "speed_kmph": None,
                "from_time": s.scheduled_start,
                "to_time": s.scheduled_end,
            }
        )
    return rows


def _build_base_graph(db: Session) -> tuple[list[dict], list[dict]]:
    """Build the schematic node + edge lists from the track network.

    Each track becomes an edge between two synthetic nodes (``{code}-A`` and
    ``{code}-B``) at the track's segment endpoints. Tracks that share an
    endpoint coordinate are visually connected (the frontend renders edges
    independently, so shared coordinates produce a connected-looking network).
    """
    tracks = list(db.scalars(select(Track)).all())
    geometry = _track_geometry(tracks)

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[tuple[str, float, float]] = set()

    for t in tracks:
        x1, y1, x2, y2 = geometry[t.id]
        a_key, b_key = f"{t.code}-A", f"{t.code}-B"
        for key, x, y in ((a_key, x1, y1), (b_key, x2, y2)):
            if (key, x, y) not in seen_nodes:
                seen_nodes.add((key, x, y))
                nodes.append(
                    {
                        "node_key": key,
                        "node_type": "junction",
                        "name": None,
                        "x": x,
                        "y": y,
                    }
                )
        edges.append(
            {
                "edge_key": t.code,
                "from_node": a_key,
                "to_node": b_key,
                "track_id": t.id,
                "track_code": t.code,
            }
        )
    return nodes, edges


def _build_data_tiles(position_rows: list[dict]) -> dict[str, dict]:
    """Group positions by tile and return ``{tile_id: {train_count}}``.

    A position is counted in **every** 15-minute tile it spans (from
    ``from_time`` to ``to_time``), because the frontend requests the tile for
    the current display-time bucket and filters by ``fromTime <= t <= toTime``.
    A tile's version is bumped (in ``sync_read_store``) only when its
    ``train_count`` or position signature changes — see the upsert logic there.
    """
    tiles: dict[str, dict] = {}
    for r in position_rows:
        sig_entry = f"{r['train_id']}:{r['x']}:{r['y']}"
        for tid in position_tiles(r["x"], r["y"], r["from_time"], r["to_time"]):
            entry = tiles.setdefault(tid, {"train_count": 0, "_sig": []})
            entry["train_count"] += 1
            entry["_sig"].append(sig_entry)
    return tiles


def _replace(session: Session, model, rows: list[dict]) -> int:
    """Atomically replace all rows of a projection table with ``rows``."""
    session.execute(delete(model))
    if rows:
        session.execute(model.__table__.insert(), rows)
    return len(rows)


def _sync_data_tiles(rs: Session, tiles: dict[str, dict]) -> int:
    """Upsert data tiles, bumping ``version`` only when a tile's content changed.

    The version bump is what drives the frontend's delta transfer: an unchanged
    tile keeps its version, so the Query Service can skip it in the response.
    Returns the number of tiles whose version was bumped.
    """
    bumped = 0
    for tile_id, entry in tiles.items():
        sig = ",".join(sorted(entry["_sig"]))
        existing = rs.get(DataTile, tile_id)
        if existing is None:
            rs.add(
                DataTile(
                    tile_id=tile_id,
                    train_count=entry["train_count"],
                    signature=sig,
                    last_updated=datetime.now(timezone.utc),
                )
            )
            bumped += 1
        elif existing.train_count != entry["train_count"] or existing.signature != sig:
            # Content changed -> bump version (fresh UUID) so clients refetch.
            existing.version = uuid.uuid4()
            existing.train_count = entry["train_count"]
            existing.signature = sig
            existing.last_updated = datetime.now(timezone.utc)
            bumped += 1
    # Drop tiles that no longer have any positions.
    current_ids = set(tiles)
    stale = rs.scalars(select(DataTile)).all()
    for t in stale:
        if t.tile_id not in current_ids:
            rs.delete(t)
    return bumped


def sync_read_store() -> dict[str, int]:
    """Run one full-refresh sync. Returns per-projection row counts."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as op_db:
        plan_rows = _build_plan_summary(op_db)
        block_rows = _build_block_view(op_db)
        track_rows = _build_track_view(op_db)
        train_rows = _build_train_view(op_db)
        position_rows = _build_train_positions(op_db)
        node_rows, edge_rows = _build_base_graph(op_db)

    # Stamp every row with the sync time, then write to the Read Store.
    for rows in (plan_rows, block_rows, track_rows, train_rows, position_rows, node_rows, edge_rows):
        for r in rows:
            r["synced_at"] = now

    tiles = _build_data_tiles(position_rows)

    with ReadStoreSession() as rs:
        counts = {
            "plan_summary": _replace(rs, PlanSummary, plan_rows),
            "block_view": _replace(rs, BlockView, block_rows),
            "track_view": _replace(rs, TrackView, track_rows),
            "train_view": _replace(rs, TrainView, train_rows),
            "train_position": _replace(rs, TrainPosition, position_rows),
            "base_graph_node": _replace(rs, BaseGraphNode, node_rows),
            "base_graph_edge": _replace(rs, BaseGraphEdge, edge_rows),
        }
        counts["data_tile_bumped"] = _sync_data_tiles(rs, tiles)
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
