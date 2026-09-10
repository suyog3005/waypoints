"""SQLAlchemy engine and session management."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
# expire_on_commit=False: persistence.py functions open and close a session
# within a single call, then return the ORM object -- callers shouldn't hit
# DetachedInstanceError reading its columns just because the session closed.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    """Commits on success, rolls back and re-raises on error, always closes."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
