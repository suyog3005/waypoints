"""Base event envelope shared by every Kafka event.

Field set mirrors the `events` table in docs/database_schema.md (Section 11)
so an event can be persisted verbatim: event_type, event_version, source,
entity_type, entity_id, correlation_id, payload, occurred_at.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventSource(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class BaseEvent(BaseModel):
    """Envelope for all events. Concrete events subclass this and override
    `payload` with a typed model (see contracts.events.schemas).
    """

    model_config = ConfigDict(frozen=True)

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    event_version: int = Field(default=1, ge=1)
    occurred_at: datetime
    source: EventSource = EventSource.INTERNAL
    producer: str | None = Field(
        default=None, description="Name of the service/system that produced the event."
    )
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    correlation_id: uuid.UUID | None = Field(
        default=None, description="Links related operations across services."
    )
    payload: dict = Field(default_factory=dict)
