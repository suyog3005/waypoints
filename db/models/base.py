"""Shared SQLAlchemy declarative base + common mixins.

All models in this package share one `Base` so Alembic's `target_metadata`
(see db/migrations/env.py) can discover every table in one place.
"""

from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Adds `created_at` / `updated_at` columns, matching every table in
    docs/database_schema.md.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
    )
