"""Block requests and their technical/operational extensions.

Mirrors docs/database_schema.md Section 6.1-6.4. `corridor_groups` /
`corridor_group_requests` (Section 6.5) are omitted — corridor bundling is a
backlog feature (architecture Section 29.1).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as PgEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin
from db.models.enums import RequestPriority, RequestStatus, RequestType, pg_enum_values


class BlockRequest(Base, TimestampMixin):
    __tablename__ = "block_requests"
    __table_args__ = (
        CheckConstraint("requested_end > requested_start", name="block_request_time_check"),
        Index("idx_block_requests_track_time", "track_id", "requested_start", "requested_end"),
        Index("idx_block_requests_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    request_type: Mapped[RequestType] = mapped_column(
        PgEnum(RequestType, name="request_type", values_callable=pg_enum_values), nullable=False
    )
    priority: Mapped[RequestPriority] = mapped_column(
        PgEnum(RequestPriority, name="request_priority", values_callable=pg_enum_values),
        nullable=False,
        default=RequestPriority.NORMAL,
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False
    )
    requested_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        PgEnum(RequestStatus, name="request_status", values_callable=pg_enum_values),
        nullable=False,
        default=RequestStatus.DRAFT,
    )
    is_emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BlockRequestAffectedTrack(Base):
    __tablename__ = "block_request_affected_tracks"

    block_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("block_requests.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), primary_key=True
    )
    reason: Mapped[str | None] = mapped_column(String(255))


class TechnicalRequest(Base, TimestampMixin):
    __tablename__ = "technical_requests"

    block_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("block_requests.id", ondelete="CASCADE"), primary_key=True
    )
    train_stops: Mapped[str | None] = mapped_column(Text)
    railway_line: Mapped[str | None] = mapped_column(String(100))
    direction: Mapped[str | None] = mapped_column(String(20))
    restriction_type: Mapped[str | None] = mapped_column(String(50))
    train_type: Mapped[str | None] = mapped_column(String(50))
    finance_reference: Mapped[str | None] = mapped_column(String(100))
    responsible_department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id")
    )
    additional_parameters: Mapped[dict | None] = mapped_column(JSONB)


class OperationalRequest(Base, TimestampMixin):
    __tablename__ = "operational_requests"

    block_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("block_requests.id", ondelete="CASCADE"), primary_key=True
    )
    # BRIDGE, UNDERPASS, ROAD_CROSSING, TREE_WORK, CABLE_MAINTENANCE, TRACK_MAINTENANCE, OTHER
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_details: Mapped[str | None] = mapped_column(Text)
    expected_duration_minutes: Mapped[int | None] = mapped_column()
    safety_notes: Mapped[str | None] = mapped_column(Text)
    additional_parameters: Mapped[dict | None] = mapped_column(JSONB)
