"""SQLAlchemy engine/session factory, shared by all services.

Reads DATABASE_URL from the environment (see db/.env.example). Services import
`SessionLocal` to open a session; nothing here starts a connection at import
time.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/block_planning",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
