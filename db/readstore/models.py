"""Read Store projection models (denormalized, dashboard-oriented).

These are the read model the Query Service (Phase 7) serves. Each table is a
flat, join-free view of the Operational DB so dashboard queries avoid expensive
joins (architecture Section 8). They are populated exclusively by the ETL
(``db.readstore.etl``) and carry a ``synced_at`` freshness stamp.

Projections (aligned with Phase 7's GET endpoints):
- ``plan_summary``  -> GET /plans
- ``block_view``    -> GET /blocks
- ``track_view``    -> GET /tracks
- ``train_view``    -> GET /trains
"""

import uuid

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.readstore.base import ReadStoreBase, SyncedMixin

# NOTE: The Read Store is a *separate* Postgres database, so it cannot declare
# foreign keys to the Operational DB's tables (Postgres does not support
# cross-database FKs). The ``*_id`` columns below are plain indexed columns that
# reference Operational DB rows by value; referential integrity is maintained by
# the ETL (which recomputes the whole projection each run).


class PlanSummary(ReadStoreBase, SyncedMixin):
    """One row per plan, with org hierarchy + aggregate counts denormalized."""

    __tablename__ = "plan_summary"
    __table_args__ = (
        Index("idx_plan_summary_status", "status"),
        Index("idx_plan_summary_section", "section_id"),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    # Org hierarchy (denormalized names so the dashboard need not join).
    section_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    section_name: Mapped[str] = mapped_column(String(150), nullable=False)
    division_name: Mapped[str | None] = mapped_column(String(150))
    zone_name: Mapped[str | None] = mapped_column(String(150))
    # Aggregates precomputed by the ETL.
    block_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_block_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


class BlockView(ReadStoreBase, SyncedMixin):
    """One row per block, with track + plan context denormalized."""

    __tablename__ = "block_view"
    __table_args__ = (
        Index("idx_block_view_track_time", "track_id", "start_time", "end_time"),
        Index("idx_block_view_plan", "plan_id"),
    )

    block_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_status: Mapped[str] = mapped_column(String(30), nullable=False)
    track_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    track_code: Mapped[str] = mapped_column(String(50), nullable=False)
    track_name: Mapped[str] = mapped_column(String(150), nullable=False)
    section_name: Mapped[str | None] = mapped_column(String(150))
    start_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_merged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TrackView(ReadStoreBase, SyncedMixin):
    """One row per track, with org hierarchy denormalized."""

    __tablename__ = "track_view"
    __table_args__ = (Index("idx_track_view_section", "section_id"),)

    track_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    line: Mapped[str | None] = mapped_column(String(100))
    direction: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    section_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    section_name: Mapped[str] = mapped_column(String(150), nullable=False)
    division_name: Mapped[str | None] = mapped_column(String(150))
    zone_name: Mapped[str | None] = mapped_column(String(150))


class TrainView(ReadStoreBase, SyncedMixin):
    """One row per train, with schedule count denormalized."""

    __tablename__ = "train_view"

    train_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    train_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    train_type: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schedule_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
