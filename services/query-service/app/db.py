"""FastAPI Read Store session dependency.

Imports `app.config` first so READ_STORE_URL is set before `db.readstore.session`
is imported (the shared session factory reads it at import time).
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app import config  # noqa: F401  (ensures READ_STORE_URL is set before import)
from db.readstore.session import ReadStoreSession


def get_read_store() -> Generator[Session, None, None]:
    db = ReadStoreSession()
    try:
        yield db
    finally:
        db.close()
