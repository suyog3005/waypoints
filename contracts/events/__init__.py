"""Kafka event contracts.

Import the concrete event classes from `contracts.events.events` and the
payload models from `contracts.events.schemas`. JSON Schema files for each
event type live in `contracts/events/json_schemas/` and are the wire contract
consumed by non-Python services and by schema-validation tooling.
"""

from contracts.events.base import BaseEvent, EventSource
from contracts.events.events import (
    BlockRequestSubmitted,
    BlockRequestUpdated,
    OptimizationRequested,
    OptimizationResult,
    TrackStatusChanged,
    TrainDelay,
    EVENT_REGISTRY,
    make_event,
)

__all__ = [
    "BaseEvent",
    "EventSource",
    "BlockRequestSubmitted",
    "BlockRequestUpdated",
    "OptimizationRequested",
    "OptimizationResult",
    "TrackStatusChanged",
    "TrainDelay",
    "EVENT_REGISTRY",
    "make_event",
]
