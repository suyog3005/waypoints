"""Database session access for the optimization service.

Imports `app.config` first so DATABASE_URL is set before `db.session` is
imported (the shared session factory reads it at import time).
"""

from app import config  # noqa: F401  (ensures DATABASE_URL is set before db.session import)
from db.session import SessionLocal

__all__ = ["SessionLocal"]
