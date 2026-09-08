"""Track network, assets, trains, restrictions, and maintenance.

Mirrors docs/database_schema.md Section 5 in full (all core-MVP tables).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin


class Track(Base, TimestampMixin):
    __tablename__ = "tracks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    line: Mapped[str | None] = mapped_column(String(100))
    direction: Mapped[str | None] = mapped_column(String(20))  # UP / DOWN / BIDIRECTIONAL
    segment_start: Mapped[str | None] = mapped_column(String(100))
    segment_end: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)


class TrackDependency(Base):
    __tablename__ = "track_dependencies"
    __table_args__ = (
        CheckConstraint("track_id <> affected_track_id", name="track_dependency_not_self"),
        UniqueConstraint(
            "track_id",
            "affected_track_id",
            "relationship_type",
            name="track_dependency_unique",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False
    )
    affected_track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    track_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tracks.id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="operational")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)


class Train(Base, TimestampMixin):
    __tablename__ = "trains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    train_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    train_type: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)


class TrainSchedule(Base):
    __tablename__ = "train_schedules"
    __table_args__ = (
        CheckConstraint("scheduled_end > scheduled_start", name="train_schedule_time_check"),
        Index("idx_train_schedules_track_time", "track_id", "scheduled_start", "scheduled_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    train_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trains.id"), nullable=False
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False
    )
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Restriction(Base, TimestampMixin):
    __tablename__ = "restrictions"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name="restriction_validity_check"
        ),
        Index("idx_restrictions_track_validity", "track_id", "valid_from", "valid_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    track_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tracks.id"))
    restriction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    max_speed_kmph: Mapped[int | None] = mapped_column(Integer)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Maintenance(Base, TimestampMixin):
    __tablename__ = "maintenance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    track_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tracks.id"))
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id")
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
