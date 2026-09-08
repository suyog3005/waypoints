"""Organizational hierarchy: Zone -> Division -> Section.

`stations` (database_schema.md Section 3.4) is omitted from the MVP — it is
only used for GIS/map visualization, which is a backlog feature (architecture
Section 29.6).
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin


class Zone(Base, TimestampMixin):
    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)


class Division(Base, TimestampMixin):
    __tablename__ = "divisions"
    __table_args__ = (UniqueConstraint("zone_id", "code", name="division_code_unique"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)


class Section(Base, TimestampMixin):
    """A railway operating section (a stretch of line between two control
    points) — not a SQL schema section.
    """

    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("division_id", "code", name="section_code_unique"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    division_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("divisions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
