"""Translation layer between this codebase's domain model and the vendored
CP-SAT pipeline (services/optimization-service/pipeline/).

Translation only: no Kafka, no event publishing. `build_pipeline_inputs`
reads Tracks/TrainSchedules/BlockRequests; `persist_solver_output` writes
exactly a Plan, its Blocks, BlockAffectedTracks, PlanItems and one
OptimizationResult -- nothing else.

Time representations differ: the pipeline works in integer minutes from a
fixed horizon start (day * 1440 + minute-of-day); this codebase stores
absolute, timezone-aware datetimes. `settings.horizon_start` (app/config.py)
is the anchor both directions of the conversion use -- it must match
whatever anchor a section's rows were seeded against.
"""

from __future__ import annotations

import math
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from db.models import (
    Block,
    BlockAffectedTrack,
    BlockRequest,
    Department,
    OperationalRequest,
    OptimizationResult,
    OptimizationRun,
    Plan,
    PlanItem,
    Track,
    Train,
    TrainSchedule,
)
from db.models.enums import RequestStatus

# The vendored files import each other as `from src.config import ...`
# (their original package layout in block-planner); pipeline/src is a
# symlink to pipeline/ itself so that resolves once pipeline/ is on
# sys.path. See pipeline/README.md.
_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from data_gen import MINUTES_PER_DAY, generate_windows  # noqa: E402

# Track.direction ("UP"/"DOWN", this codebase's convention) <-> the
# pipeline's own line labels ("Up"/"Down", from data_gen.LINES). The pipeline
# indexes internal dicts by these exact strings, so this must round-trip
# precisely -- do not normalize case on either side.
_DIRECTION_TO_LINE = {"UP": "Up", "DOWN": "Down"}
_LINE_TO_DIRECTION = {"Up": "UP", "Down": "DOWN"}


def _day_and_start_min(dt: datetime) -> tuple[int, float]:
    """Decompose an absolute datetime into (day, minute-of-day) relative to
    settings.horizon_start, matching data_gen's (day, start_min) scheme."""
    total_minutes = (dt - settings.horizon_start).total_seconds() / 60.0
    day = math.floor(total_minutes / MINUTES_PER_DAY)
    return day, total_minutes - day * MINUTES_PER_DAY


def _abs_minutes_to_datetime(abs_minutes: float) -> datetime:
    """Inverse of the day*MINUTES_PER_DAY + minute-of-day scheme the solver
    outputs (schedule_df/possessions_df start_min/end_min are already
    absolute minutes from horizon start, not within-day clock minutes)."""
    return settings.horizon_start + timedelta(minutes=float(abs_minutes))


def build_pipeline_inputs(
    db: Session, section_id: uuid.UUID
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load one section's Tracks/TrainSchedules/SUBMITTED BlockRequests and
    translate them into the (jobs_df, trains_df, windows_df, segments_df)
    DataFrames the pipeline needs -- solver.py/baseline.py for the first
    three, model.py's classifier and check.py's validator for the rest of
    jobs_df's columns and for segments_df. Columns and dtypes matched to
    src/data_gen.py, not the other way around.
    """
    tracks = db.scalars(select(Track).where(Track.section_id == section_id)).all()
    segment_of = {t.id: (int(t.metadata_["sequence"]), _DIRECTION_TO_LINE[t.direction]) for t in tracks}
    track_ids = list(segment_of)
    segments_df = pd.DataFrame({"segment_id": sorted({seg for seg, _ in segment_of.values()})})

    train_rows = []
    schedule_rows = db.execute(
        select(TrainSchedule, Train)
        .join(Train, TrainSchedule.train_id == Train.id)
        .where(TrainSchedule.track_id.in_(track_ids))
    ).all()
    for ts, train in schedule_rows:
        segment, line = segment_of[ts.track_id]
        day, start_min = _day_and_start_min(ts.scheduled_start)
        end_total_min = (ts.scheduled_end - settings.horizon_start).total_seconds() / 60.0
        end_min = end_total_min - day * MINUTES_PER_DAY
        train_rows.append(
            {
                "train_id": train.train_number,
                "train_type": train.train_type,
                "day": int(day),
                "line": line,
                "segment": segment,
                "start_min": start_min,
                "end_min": end_min,
            }
        )
    trains_df = pd.DataFrame(
        train_rows, columns=["train_id", "train_type", "day", "line", "segment", "start_min", "end_min"]
    )

    job_rows = []
    request_rows = db.execute(
        select(BlockRequest, OperationalRequest, Department)
        .join(OperationalRequest, OperationalRequest.block_request_id == BlockRequest.id)
        .join(Department, BlockRequest.department_id == Department.id)
        .where(BlockRequest.track_id.in_(track_ids), BlockRequest.status == RequestStatus.SUBMITTED)
    ).all()
    for request, op_request, department in request_rows:
        segment, line = segment_of[request.track_id]
        params = op_request.additional_parameters
        day, _ = _day_and_start_min(request.submitted_at)
        job_rows.append(
            {
                "id": str(request.id),
                "department": department.name,
                "segment": segment,
                "line": line,
                "estimated_duration_min": int(params["estimated_duration_min"]),
                "days_overdue": int(params["days_overdue"]),
                "defect_severity": int(params["defect_severity"]),
                "asset_age_years": float(params["asset_age_years"]),
                "traffic_density": float(params["traffic_density"]),
                "days_since_last_maintenance": int(params["days_since_last_maintenance"]),
                "defect_type": str(params["defect_type"]),
                "recurrence_count": int(params["recurrence_count"]),
                "section_speed_limit": int(params["section_speed_limit"]),
                "passenger_train_count": int(params["passenger_train_count"]),
                "speed_restriction_active": bool(params["speed_restriction_active"]),
                "day": int(day),
                "priority_class": str(params["priority_class"]),
            }
        )
    jobs_df = pd.DataFrame(
        job_rows,
        columns=[
            "id",
            "department",
            "segment",
            "line",
            "estimated_duration_min",
            "days_overdue",
            "defect_severity",
            "asset_age_years",
            "traffic_density",
            "days_since_last_maintenance",
            "defect_type",
            "recurrence_count",
            "section_speed_limit",
            "passenger_train_count",
            "speed_restriction_active",
            "day",
            "priority_class",
        ],
    )

    windows_df = generate_windows()

    return jobs_df, trains_df, windows_df, segments_df


def _sanitize(value):
    """JSONB-safe conversion: numpy scalars -> native Python, NaN -> None
    (schedule_solver's per-priority-class metrics contain NaN when a class
    has no scheduled jobs; bare NaN is not valid JSON)."""
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return None if math.isnan(value) else value
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def persist_solver_output(
    db: Session,
    run: OptimizationRun,
    schedule_df: pd.DataFrame,
    possessions_df: pd.DataFrame,
    metrics: dict,
) -> tuple[Plan, int]:
    """Persist one solver run: a Plan, one Block per possession,
    BlockAffectedTrack rows for every track in each possession's segment
    range, one PlanItem per scheduled job, and an OptimizationResult.
    Returns (plan, merged_requests_count) -- the caller needs the latter to
    report/publish metrics without re-deriving it from the raw DataFrames."""
    if schedule_df.empty:
        raise ValueError("cannot persist an empty schedule -- no track to infer the plan's section from")

    request_ids = [uuid.UUID(job_id) for job_id in schedule_df["job_id"]]
    requests_by_id = {
        r.id: r for r in db.scalars(select(BlockRequest).where(BlockRequest.id.in_(request_ids))).all()
    }

    section_id = db.get(Track, next(iter(requests_by_id.values())).track_id).section_id
    tracks = db.scalars(select(Track).where(Track.section_id == section_id)).all()
    track_by_seq_dir = {(int(t.metadata_["sequence"]), t.direction): t for t in tracks}

    plan = Plan(section_id=section_id, optimization_run_id=run.id)
    db.add(plan)
    db.flush()

    blocks_by_possession: dict[str, tuple[Block, tuple]] = {}
    for poss in possessions_df.itertuples():
        direction = _LINE_TO_DIRECTION[poss.line]
        anchor = track_by_seq_dir[(poss.segment_start, direction)]
        block = Block(
            plan_id=plan.id,
            track_id=anchor.id,
            start_time=_abs_minutes_to_datetime(poss.start_min),
            end_time=_abs_minutes_to_datetime(poss.end_min),
            is_merged=False,
        )
        db.add(block)
        blocks_by_possession[poss.possession_id] = (block, poss)
    db.flush()

    for possession_id, (block, poss) in blocks_by_possession.items():
        direction = _LINE_TO_DIRECTION[poss.line]
        for segment in range(poss.segment_start, poss.segment_end + 1):
            track = track_by_seq_dir[(segment, direction)]
            db.add(BlockAffectedTrack(block_id=block.id, track_id=track.id))

    jobs_by_possession: dict[str, int] = {}
    plan_items = []
    for job in schedule_df.itertuples():
        matched = None
        for possession_id, (block, poss) in blocks_by_possession.items():
            if (
                poss.line == job.line
                and poss.segment_start <= job.segment <= poss.segment_end
                and poss.start_min <= job.start_min
                and job.end_min <= poss.end_min
            ):
                matched = (possession_id, block)
                break
        if matched is None:
            raise AssertionError(f"scheduled job {job.job_id} matches no possession")
        possession_id, block = matched
        jobs_by_possession[possession_id] = jobs_by_possession.get(possession_id, 0) + 1
        plan_items.append(
            PlanItem(plan_id=plan.id, block_id=block.id, block_request_id=requests_by_id[uuid.UUID(job.job_id)].id)
        )
    db.add_all(plan_items)

    merged_requests_count = 0
    for possession_id, count in jobs_by_possession.items():
        if count > 1:
            blocks_by_possession[possession_id][0].is_merged = True
            merged_requests_count += count

    result_metrics = _sanitize(dict(metrics))
    result_metrics["block_count"] = len(possessions_df)
    result_metrics["request_count"] = len(schedule_df)
    result_metrics["merged_requests_count"] = merged_requests_count

    db.add(
        OptimizationResult(
            optimization_run_id=run.id,
            plan_id=plan.id,
            merged_requests_count=merged_requests_count,
            metrics=result_metrics,
        )
    )
    db.flush()

    return plan, merged_requests_count
