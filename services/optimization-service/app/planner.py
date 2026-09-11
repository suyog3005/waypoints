"""Planner: orchestrates the CP-SAT pipeline and persists the result.

Loads eligible block requests for a section, runs the vendored pipeline
(services/optimization-service/pipeline/) end to end -- LightGBM priority
classifier -> CP-SAT solver -> independent feasibility validator -- and
writes a Plan/Blocks/PlanItems/OptimizationResult via app/adapter.py. A
schedule that fails validation is never persisted; the run is marked FAILED
with the violations recorded instead.

The old placeholder (app/optimizer.py's merge_windows, app/shadow_finder.py)
is no longer wired in here but stays in the tree unused.
"""

from __future__ import annotations

import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app import adapter
from app.config import settings
from app.db import SessionLocal
from db.models import OptimizationRun, Track
from db.models.enums import OptimizationRunStatus

# Same vendored-pipeline bootstrapping as app/adapter.py: pipeline/src is a
# symlink to pipeline/ itself, so `from src.config import ...` (the vendored
# files' own internal imports) resolves once pipeline/ is on sys.path.
_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

import check as pipeline_check  # noqa: E402
import model as pipeline_model  # noqa: E402
from solver import schedule_solver  # noqa: E402

# model.py's MODEL_PATH ("models/priority_classifier.joblib") is relative to
# block-planner's own repo root, not this service's cwd. Patch the module
# attribute at runtime rather than editing the vendored file.
pipeline_model.MODEL_PATH = str(_PIPELINE_DIR / "models" / "priority_classifier.joblib")

logger = logging.getLogger(__name__)


@dataclass
class PlanMetrics:
    total_block_duration_minutes: int
    affected_tracks_count: int
    merged_requests_count: int
    block_count: int
    request_count: int


@dataclass
class OptimizationOutcome:
    """Result of one optimization cycle."""

    plan_id: uuid.UUID | None
    metrics: PlanMetrics | None


def _section_for_track(db: Session, track: Track) -> uuid.UUID:
    return track.section_id


def _compute_metrics(possessions_df, schedule_df, merged_requests_count: int) -> PlanMetrics:
    total_block_duration_minutes = int((possessions_df["end_min"] - possessions_df["start_min"]).sum())
    affected_tracks = {
        (segment, poss.line)
        for poss in possessions_df.itertuples()
        for segment in range(poss.segment_start, poss.segment_end + 1)
    }
    return PlanMetrics(
        total_block_duration_minutes=total_block_duration_minutes,
        affected_tracks_count=len(affected_tracks),
        merged_requests_count=merged_requests_count,
        block_count=len(possessions_df),
        request_count=len(schedule_df),
    )


def _summarize_violations(violations: list) -> str:
    by_rule: dict[str, int] = {}
    for v in violations:
        by_rule[v.rule] = by_rule.get(v.rule, 0) + 1
    counts = ", ".join(f"{rule}={count}" for rule, count in sorted(by_rule.items()))
    examples = "; ".join(f"[{v.rule}] {v.job_id or v.possession_id}: {v.detail}" for v in violations[:5])
    return f"check.validate found {len(violations)} violation(s) ({counts}). Examples: {examples}"


def run_optimization(
    *,
    track_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    triggered_by_event_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
) -> OptimizationOutcome:
    """Run one optimization cycle for a section. Returns an
    OptimizationOutcome; plan_id is None when there were no eligible
    requests, or when the solved schedule failed validation.
    """
    with SessionLocal() as db:
        run = OptimizationRun(
            triggered_by_event_id=triggered_by_event_id,
            status=OptimizationRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()

        try:
            resolved_section_id = section_id
            if resolved_section_id is None:
                if track_id is None:
                    raise ValueError("run_optimization requires track_id or section_id")
                track = db.get(Track, track_id)
                if track is None:
                    raise ValueError(f"track {track_id} not found")
                resolved_section_id = _section_for_track(db, track)

            jobs_df, trains_df, windows_df, segments_df = adapter.build_pipeline_inputs(db, resolved_section_id)
            if jobs_df.empty:
                run.status = OptimizationRunStatus.SUCCEEDED
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                return OptimizationOutcome(plan_id=None, metrics=None)

            weights = pipeline_model.predicted_weights(jobs_df)
            schedule_df, possessions_df, metrics, solve_info = schedule_solver(
                jobs_df, trains_df, windows_df, weights, time_limit=settings.solve_time_limit
            )
            logger.info(
                "run %s: solver status=%s wall_clock=%ss objective=%s bound=%s",
                run.id,
                solve_info["status"],
                solve_info["wall_clock_seconds"],
                solve_info["objective_value"],
                solve_info["best_objective_bound"],
            )

            violations = pipeline_check.validate(
                schedule_df, possessions_df, segments_df, trains_df, windows_df, jobs_df
            )
            if violations:
                run.status = OptimizationRunStatus.FAILED
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = _summarize_violations(violations)
                db.commit()
                return OptimizationOutcome(plan_id=None, metrics=None)

            plan, merged_requests_count = adapter.persist_solver_output(db, run, schedule_df, possessions_df, metrics)

            run.status = OptimizationRunStatus.SUCCEEDED
            run.completed_at = datetime.now(timezone.utc)
            db.commit()

            plan_metrics = _compute_metrics(possessions_df, schedule_df, merged_requests_count)
            return OptimizationOutcome(plan_id=plan.id, metrics=plan_metrics)

        except Exception:
            db.rollback()
            run.status = OptimizationRunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            db.add(run)
            db.commit()
            raise
