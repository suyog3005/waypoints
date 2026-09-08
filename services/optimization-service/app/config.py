"""Optimization Service configuration.

Mirrors DATABASE_URL into os.environ so the shared `db.session` module (which
reads it at import time) uses the same value.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/block_planning"
    kafka_brokers: str = "localhost:9092"
    kafka_consumer_group: str = "optimization-service"


settings = Settings()

os.environ.setdefault("DATABASE_URL", settings.database_url)
