"""Planner: orchestrates Shadow Finder + optimizer and persists the result.

Loads eligible block requests, runs the pure merge logic, and writes a Plan,
its Blocks, and PlanItems (traceability back to source requests) to the
Operational DB. Also computes the metrics exposed on the optimization result
(architecture Section 20).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.optimizer import MergedBlock, merge_windows
from app.shadow_finder import RequestWindow
from db.models import (
    Block,
    BlockAffectedTrack,
    BlockRequest,
    BlockRequestAffectedTrack,
    OptimizationResult,
    OptimizationRun,
    Plan,
    PlanItem,
    Track,
)
from db.models.enums import OptimizationRunStatus, PlanStatus, RequestStatus


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


def _load_eligible_requests(db: Session, track_id: uuid.UUID | None) -> list[BlockRequest]:
    """Requests that need planning: submitted (not yet scheduled/merged)."""
    stmt = select(BlockRequest).where(BlockRequest.status == RequestStatus.SUBMITTED)
    if track_id is not None:
        stmt = stmt.where(BlockRequest.track_id == track_id)
    return list(db.scalars(stmt).all())


def _section_for_track(db: Session, track: Track) -> uuid.UUID:
    return track.section_id


def _compute_metrics(blocks: list[MergedBlock], request_count: int) -> PlanMetrics:
    total_minutes = sum(b.duration_minutes for b in blocks)
    affected_tracks = {b.track_id for b in blocks}
    merged_requests = sum(len(b.request_ids) for b in blocks if b.is_merged)
    return PlanMetrics(
        total_block_duration_minutes=total_minutes,
        affected_tracks_count=len(affected_tracks),
        merged_requests_count=merged_requests,
        block_count=len(blocks),
        request_count=request_count,
    )


def run_optimization(
    *,
    track_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    triggered_by_event_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
) -> OptimizationOutcome:
    """Run one optimization cycle. Returns an OptimizationOutcome; plan_id is
    None when there were no eligible requests (nothing to plan).
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
            requests = _load_eligible_requests(db, track_id)
            if not requests:
                run.status = OptimizationRunStatus.SUCCEEDED
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                return OptimizationOutcome(plan_id=None, metrics=None)

            # Build windows (primary track only for the MVP merge; affected
            # tracks are recorded on the block for dependency visibility).
            windows = [
                RequestWindow(
                    request_id=r.id,
                    track_id=r.track_id,
                    start=r.requested_start,
                    end=r.requested_end,
                )
                for r in requests
            ]

            # Group by track and merge each track's windows independently.
            by_track: dict[uuid.UUID, list[RequestWindow]] = {}
            for w in windows:
                by_track.setdefault(w.track_id, []).append(w)
            merged_blocks: list[MergedBlock] = []
            for tw in by_track.values():
                merged_blocks.extend(merge_windows(tw))

            # Determine the plan's section (from the first block's track).
            first_track = db.get(Track, merged_blocks[0].track_id)
            if first_track is None:
                raise ValueError(f"track {merged_blocks[0].track_id} not found")
            plan_section = section_id or _section_for_track(db, first_track)

            plan = Plan(
                section_id=plan_section,
                status=PlanStatus.PROPOSED,
                optimization_run_id=run.id,
            )
            db.add(plan)
            db.flush()

            for mb in merged_blocks:
                block = Block(
                    plan_id=plan.id,
                    track_id=mb.track_id,
                    start_time=mb.start,
                    end_time=mb.end,
                    is_merged=mb.is_merged,
                )
                db.add(block)
                db.flush()
                for req_id in mb.request_ids:
                    db.add(PlanItem(plan_id=plan.id, block_id=block.id, block_request_id=req_id))
                # Record affected tracks declared by the contributing requests.
                for req_id in mb.request_ids:
                    affected = db.scalars(
                        select(BlockRequestAffectedTrack.track_id).where(
                            BlockRequestAffectedTrack.block_request_id == req_id
                        )
                    ).all()
                    for at in affected:
                        if at != mb.track_id:
                            db.add(BlockAffectedTrack(block_id=block.id, track_id=at))

            # Mark the source requests as scheduled (they are now in a plan).
            for r in requests:
                r.status = RequestStatus.SCHEDULED

            metrics = _compute_metrics(merged_blocks, len(requests))
            result = OptimizationResult(
                optimization_run_id=run.id,
                plan_id=plan.id,
                total_block_duration_minutes=metrics.total_block_duration_minutes,
                affected_tracks_count=metrics.affected_tracks_count,
                merged_requests_count=metrics.merged_requests_count,
                metrics={
                    "block_count": metrics.block_count,
                    "request_count": metrics.request_count,
                },
            )
            db.add(result)

            run.status = OptimizationRunStatus.SUCCEEDED
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return OptimizationOutcome(plan_id=plan.id, metrics=metrics)

        except Exception:
            db.rollback()
            run.status = OptimizationRunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            db.add(run)
            db.commit()
            raise
