"""Constraints, optimization runs/results, plans, and blocks.

Mirrors docs/database_schema.md Sections 8-10 (core-MVP subset only).
Omitted (backlog): `corridor_groups`/`corridor_group_requests` (6.5),
`approval_steps`/`escalations` (7), `simulation_runs`/`simulation_results`
(10.3), `block_execution_reports` (8.5).
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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin
from db.models.enums import (
    ConstraintSeverity,
    OptimizationRunStatus,
    PlanStatus,
    pg_enum_values,
)


class Constraint(Base, TimestampMixin):
    __tablename__ = "constraints"
    __table_args__ = (
        CheckConstraint(
            "(severity = 'hard' AND penalty_weight IS NULL) OR (severity = 'soft')",
            name="constraint_penalty_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[ConstraintSeverity] = mapped_column(
        PgEnum(ConstraintSeverity, name="constraint_severity", values_callable=pg_enum_values),
        nullable=False,
        default=ConstraintSeverity.SOFT,
    )
    penalty_weight: Mapped[float | None] = mapped_column(Numeric(10, 4))
    applies_to: Mapped[str | None] = mapped_column(String(50))
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    # FK to events.id added via a deferred ALTER TABLE in the migration, since
    # `events` is created after `optimization_runs` (see database_schema.md Section 10.1).
    triggered_by_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[OptimizationRunStatus] = mapped_column(
        PgEnum(
            OptimizationRunStatus, name="optimization_run_status", values_callable=pg_enum_values
        ),
        nullable=False,
        default=OptimizationRunStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_summary: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class OptimizationResult(Base):
    __tablename__ = "optimization_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"))
    total_block_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    affected_trains_count: Mapped[int | None] = mapped_column(Integer)
    expected_delay_minutes: Mapped[int | None] = mapped_column(Integer)
    utilization_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    merged_requests_count: Mapped[int | None] = mapped_column(Integer)
    affected_tracks_count: Mapped[int | None] = mapped_column(Integer)
    objective_score: Mapped[float | None] = mapped_column(Numeric(12, 4))
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False
    )
    status: Mapped[PlanStatus] = mapped_column(
        PgEnum(PlanStatus, name="plan_status", values_callable=pg_enum_values),
        nullable=False,
        default=PlanStatus.PROPOSED,
    )
    optimization_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("optimization_runs.id")
    )
    superseded_by_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id")
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Block(Base, TimestampMixin):
    """Note: `corridor_group_id` (database_schema.md Section 8.2) is omitted —
    corridor bundling is a backlog feature (architecture Section 29.1).
    """

    __tablename__ = "blocks"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="block_time_check"),
        Index("idx_blocks_track_time", "track_id", "start_time", "end_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_merged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PlanItem(Base):
    __tablename__ = "plan_items"
    __table_args__ = (
        UniqueConstraint("block_id", "block_request_id", name="plan_item_unique"),
        Index("idx_plan_items_plan", "plan_id"),
        Index("idx_plan_items_request", "block_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    block_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False
    )
    block_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("block_requests.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class BlockAffectedTrack(Base):
    __tablename__ = "block_affected_tracks"

    block_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blocks.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), primary_key=True
    )
    impact_reason: Mapped[str | None] = mapped_column(String(255))
