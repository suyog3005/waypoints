"""Concrete event classes, one per event type.

Each class fixes `event_type` and types `payload` with the matching model from
`contracts.events.schemas`. `EVENT_REGISTRY` maps event_type -> class so
consumers can dispatch on the type string.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from contracts.events.base import BaseEvent
from contracts.events.schemas import (
    BlockRequestPayload,
    OptimizationRequestPayload,
    OptimizationResultPayload,
    TrackStatusPayload,
    TrainDelayPayload,
)


class BlockRequestSubmitted(BaseEvent):
    event_type: str = Field(default="block_request.submitted")
    entity_type: str = Field(default="BLOCK_REQUEST")
    payload: BlockRequestPayload


class BlockRequestUpdated(BaseEvent):
    event_type: str = Field(default="block_request.updated")
    entity_type: str = Field(default="BLOCK_REQUEST")
    payload: BlockRequestPayload


class OptimizationRequested(BaseEvent):
    event_type: str = Field(default="optimization.requested")
    payload: OptimizationRequestPayload


class OptimizationResult(BaseEvent):
    event_type: str = Field(default="optimization.result")
    entity_type: str = Field(default="PLAN")
    payload: OptimizationResultPayload


class TrackStatusChanged(BaseEvent):
    event_type: str = Field(default="track.status_changed")
    entity_type: str = Field(default="TRACK")
    payload: TrackStatusPayload


class TrainDelay(BaseEvent):
    event_type: str = Field(default="train.delay")
    entity_type: str = Field(default="TRAIN")
    payload: TrainDelayPayload


EVENT_REGISTRY: dict[str, type[BaseEvent]] = {
    cls.event_type: cls  # type: ignore[misc]
    for cls in (
        BlockRequestSubmitted,
        BlockRequestUpdated,
        OptimizationRequested,
        OptimizationResult,
        TrackStatusChanged,
        TrainDelay,
    )
}


def make_event(
    event_cls: type[BaseEvent],
    payload: dict,
    *,
    occurred_at: datetime,
    correlation_id: uuid.UUID | None = None,
    **overrides,
) -> BaseEvent:
    """Convenience constructor: builds an event from a raw payload dict."""
    return event_cls(
        occurred_at=occurred_at,
        correlation_id=correlation_id,
        payload=payload,
        **overrides,
    )
