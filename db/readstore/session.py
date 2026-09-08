"""Engine/session factory for the Read Store.

Reads ``READ_STORE_URL`` from the environment (see ``db/.env.example``). This
points at the *separate* read database (``block_planning_read``), distinct from
the Operational DB's ``DATABASE_URL``. Nothing connects at import time.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

READ_STORE_URL = os.environ.get(
    "READ_STORE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/block_planning_read",
)

read_engine = create_engine(READ_STORE_URL, pool_pre_ping=True, future=True)
ReadStoreSession = sessionmaker(bind=read_engine, autoflush=False, autocommit=False, future=True)
