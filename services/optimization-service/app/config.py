"""Optimization Service configuration.

Mirrors DATABASE_URL into os.environ so the shared `db.session` module (which
reads it at import time) uses the same value.
"""

import os
from datetime import datetime, timezone

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5433/block_planning"
    kafka_brokers: str = "localhost:9092"
    kafka_consumer_group: str = "optimization-service"

    # Reference point ("day 0") the vendored pipeline's integer-minute
    # timestamps are relative to -- see app/adapter.py, which converts
    # between this codebase's absolute datetimes and the pipeline's
    # (day, minute-of-day) / absolute-minute scheme using this anchor. Must
    # match whatever anchor a section's BlockRequest/TrainSchedule rows were
    # seeded against (scripts/seed_from_pipeline.py uses the seed run's own
    # UTC midnight).
    horizon_start: datetime = datetime(2026, 9, 11, tzinfo=timezone.utc)

    # Wall-clock budget (seconds) for the CP-SAT solve in app/planner.py.
    # Matches src/config.py's own SOLVE_TIME_LIMIT default.
    solve_time_limit: int = 60


settings = Settings()

os.environ.setdefault("DATABASE_URL", settings.database_url)
