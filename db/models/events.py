"""Events consumed from Kafka or generated internally.

Mirrors docs/database_schema.md Section 11. Notifications/weather/audit
(Sections 12-14) are omitted from the MVP — see docs/plan.md backlog.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as PgEnum, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base
from db.models.enums import EventSource, pg_enum_values


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_type_time", "event_type", "occurred_at"),
        Index("idx_events_entity", "entity_type", "entity_id"),
        Index("idx_events_correlation", "correlation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[EventSource] = mapped_column(
        PgEnum(EventSource, name="event_source", values_callable=pg_enum_values),
        nullable=False,
        default=EventSource.INTERNAL,
    )
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
