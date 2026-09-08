"""Declarative base for Read Store projection models.

A separate ``Base`` from ``db.models.Base`` so the Read Store tables are not
discovered by the Operational DB's Alembic ``target_metadata`` (and vice
versa). The Read Store has its own Alembic env (``db/readstore/alembic.ini`` +
``db/readstore/migrations/env.py``) that uses ``ReadStoreBase.metadata``.
"""

from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ReadStoreBase(DeclarativeBase):
    pass


class SyncedMixin:
    """Adds a ``synced_at`` freshness stamp to every projection row.

    The ETL sets this to the time the row was last (re)computed, so the Query
    Service / frontend can surface how fresh a read is (architecture Section 8:
    the Read Store holds precomputed, dashboard-oriented data).
    """

    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
