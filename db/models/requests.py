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
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin
from db.models.enums import (
    AdjacentLineStatus,
    BlockClass,
    Criticality,
    ExecutionState,
    OriginType,
    PowerBlockState,
    RequestPriority,
    RequestStatus,
    RequestType,
    pg_enum_values,
)


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

    # ── Structured demand fields (OPUS-5 Part G, SR-002/004/006/007/009) ──
    # These turn the free-text form into a machine-plannable request.
    block_class: Mapped[BlockClass] = mapped_column(
        PgEnum(BlockClass, name="block_class", values_callable=pg_enum_values),
        nullable=False,
        default=BlockClass.ROUTINE,
    )
    origin_type: Mapped[OriginType] = mapped_column(
        PgEnum(OriginType, name="origin_type", values_callable=pg_enum_values),
        nullable=False,
        default=OriginType.AD_HOC,
    )
    criticality: Mapped[Criticality] = mapped_column(
        PgEnum(Criticality, name="criticality", values_callable=pg_enum_values),
        nullable=False,
        default=Criticality.MEDIUM,
    )
    consequence_of_deferral: Mapped[str | None] = mapped_column(Text)
    work_type: Mapped[str | None] = mapped_column(String(150))
    quantum: Mapped[int | None] = mapped_column()
    quantum_unit: Mapped[str | None] = mapped_column(String(50))
    estimated_duration_minutes: Mapped[int | None] = mapped_column()
    # Data-derived duration suggestion shown at request time (SR-006).
    suggested_duration_minutes: Mapped[int | None] = mapped_column()
    duration_confidence: Mapped[str | None] = mapped_column(String(20))
    # Adjacent-line protection (SR-039) — a first-class safety fact.
    adjacent_line_status: Mapped[AdjacentLineStatus | None] = mapped_column(
        PgEnum(AdjacentLineStatus, name="adjacent_line_status", values_callable=pg_enum_values)
    )
    # Lead-time / late-request classification (SR-002).
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lead_time_days: Mapped[int | None] = mapped_column()

    # One-to-one execution + safety state (OPUS-5 Part H).
    execution: Mapped["BlockExecutionState | None"] = relationship(
        "BlockExecutionState",
        back_populates="block_request",
        uselist=False,
        cascade="all, delete-orphan",
    )


class BlockExecutionState(Base, TimestampMixin):
    """Execution + safety state machine for a block request (OPUS-5 Part H,
    SR-026..SR-044). One row per request, updated as the block progresses.

    Safety states are *explicit, separate and fail-safe* (F1 principle 4):
    the traffic ``execution_state`` and the ``power_block_state`` are distinct
    facts, individually confirmed. A block cannot reach ``WORKING`` until the
    power block is ``EARTHED`` (SR-038), and cannot reach ``HANDED_BACK`` with
    an open disconnection (SR-040).
    """

    __tablename__ = "block_execution_states"

    block_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("block_requests.id", ondelete="CASCADE"), primary_key=True
    )
    block_request: Mapped["BlockRequest"] = relationship(
        "BlockRequest", back_populates="execution"
    )
    execution_state: Mapped[ExecutionState] = mapped_column(
        PgEnum(ExecutionState, name="execution_state", values_callable=pg_enum_values),
        nullable=False,
        default=ExecutionState.REQUESTED,
    )
    power_block_state: Mapped[PowerBlockState] = mapped_column(
        PgEnum(PowerBlockState, name="power_block_state", values_callable=pg_enum_values),
        nullable=False,
        default=PowerBlockState.NOT_REQUESTED,
    )
    # Actual grant time vs sanctioned time (SR-026) + reason code.
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    grant_reason_code: Mapped[str | None] = mapped_column(String(50))
    # Protection / isolation timestamps (SR-028, SR-038).
    protected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    earthed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    earthed_by: Mapped[str | None] = mapped_column(String(150))
    # Work window (SR-028 decomposition).
    work_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    work_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Hand-back certificate (SR-033): named certifier + fitness + restriction.
    handed_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    handed_back_by: Mapped[str | None] = mapped_column(String(150))
    fitness_declaration: Mapped[str | None] = mapped_column(Text)
    imposed_speed_kmph: Mapped[int | None] = mapped_column()
    # Output / quantum reporting (SR-032).
    quantum_completed: Mapped[int | None] = mapped_column()
    output_notes: Mapped[str | None] = mapped_column(Text)
    # Open disconnection flag (SR-040). Blocks hand-back while True.
    has_open_disconnection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


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
