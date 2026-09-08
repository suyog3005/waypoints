"""FastAPI database session dependency.

Imports `app.config` first so DATABASE_URL is set before `db.session` is
imported (the shared session factory reads it at import time).
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app import config  # noqa: F401  (ensures DATABASE_URL is set before db.session import)
from db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
