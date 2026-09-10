"""Event injection endpoints for testing the real-time loop (Phase 11).

Simulates operational events (train delays, track status changes) to verify
that events flow through the optimizer and update the frontend in real-time.
Architecture Sections 15 (events), 23 (real-time loop).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.kafka import get_publisher
from contracts.events import (
    OptimizationRequested,
    TrainDelay,
    make_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inject", tags=["event-injection"])


@router.post("/train-delay")
async def inject_train_delay(
    train_id: str | None = None,
    delay_minutes: int = 15,
    reason: str = "Phase 11 event injection test",
    session: Session = Depends(get_session),
    publisher = Depends(get_publisher),
) -> dict:
    """Inject a train delay event to test the real-time loop.

    Publishes a TrainDelay event to TRAIN_EVENTS topic, which may trigger
    re-optimization (full wiring deferred; for now, manually trigger
    /trigger-optimization).

    Args:
        train_id: UUID of train to delay (optional; random if omitted)
        delay_minutes: How many minutes late (default 15)
        reason: Human-readable reason

    Returns:
        Event details (event_id, train_id, delay_minutes, timestamp)
    """
    if not publisher:
        raise HTTPException(status_code=503, detail="Kafka publisher not available")

    # If no train_id, pick a random train from the DB
    if not train_id:
        from db.models import Train
        trains = session.query(Train).limit(50).all()
        if not trains:
            raise HTTPException(status_code=400, detail="No trains in database")
        train = trains[0]  # In a real system, pick randomly
        train_id_uuid = train.id
    else:
        try:
            train_id_uuid = uuid.UUID(train_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid train_id UUID")

    # Create and publish the event
    event = make_event(
        TrainDelay,
        payload={
            "train_id": str(train_id_uuid),
            "track_id": None,
            "delay_minutes": delay_minutes,
            "reason": reason,
        },
        occurred_at=datetime.now(timezone.utc),
    )

    try:
        from contracts.events.topics import Topics
        await publisher.send_and_wait(
            Topics.TRAIN_EVENTS,
            event.model_dump_json().encode(),
        )
        logger.info(
            "Injected train delay: train=%s delay=%d min reason=%s event_id=%s",
            train_id_uuid,
            delay_minutes,
            reason,
            event.event_id,
        )
    except Exception as exc:
        logger.error("Failed to publish train delay event: %s", exc)
        raise HTTPException(status_code=500, detail=f"Kafka publish failed: {exc}")

    return {
        "event_id": str(event.event_id),
        "event_type": event.event_type,
        "train_id": str(train_id_uuid),
        "delay_minutes": delay_minutes,
        "reason": reason,
        "occurred_at": event.occurred_at.isoformat(),
        "message": "Train delay event published to TRAIN_EVENTS topic",
    }


@router.post("/trigger-optimization")
async def trigger_optimization(
    track_id: str | None = None,
    section_id: str | None = None,
    reason: str = "Phase 11 manual re-optimization trigger",
    publisher = Depends(get_publisher),
) -> dict:
    """Manually trigger the optimizer to re-plan a track or section.

    Publishes an OptimizationRequested event to OPTIMIZATION_REQUESTS topic,
    which will cause the optimization service to re-run and produce a new Plan.

    Args:
        track_id: UUID of track to re-optimize (optional)
        section_id: UUID of section to re-optimize (optional)
        reason: Human-readable reason for re-optimization

    Returns:
        Event details (event_id, track_id, section_id, timestamp)
    """
    if not publisher:
        raise HTTPException(status_code=503, detail="Kafka publisher not available")

    track_uuid = None
    section_uuid = None

    if track_id:
        try:
            track_uuid = uuid.UUID(track_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid track_id UUID")

    if section_id:
        try:
            section_uuid = uuid.UUID(section_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid section_id UUID")

    # Create and publish the event
    event = make_event(
        OptimizationRequested,
        payload={
            "track_id": str(track_uuid) if track_uuid else None,
            "section_id": str(section_uuid) if section_uuid else None,
            "reason": reason,
            "include_request_ids": [],
        },
        occurred_at=datetime.now(timezone.utc),
    )

    try:
        from contracts.events.topics import Topics
        await publisher.send_and_wait(
            Topics.OPTIMIZATION_REQUESTS,
            event.model_dump_json().encode(),
        )
        logger.info(
            "Triggered optimization: track=%s section=%s reason=%s event_id=%s",
            track_uuid,
            section_uuid,
            reason,
            event.event_id,
        )
    except Exception as exc:
        logger.error("Failed to publish optimization request: %s", exc)
        raise HTTPException(status_code=500, detail=f"Kafka publish failed: {exc}")

    return {
        "event_id": str(event.event_id),
        "event_type": event.event_type,
        "track_id": str(track_uuid) if track_uuid else None,
        "section_id": str(section_uuid) if section_uuid else None,
        "reason": reason,
        "occurred_at": event.occurred_at.isoformat(),
        "message": "Optimization request published to OPTIMIZATION_REQUESTS topic",
    }
