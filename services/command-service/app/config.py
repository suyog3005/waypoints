"""Command Service configuration.

Loads settings from the environment / `.env` (see .env.example). Also mirrors
DATABASE_URL into os.environ so the shared `db.session` module (which reads it
at import time) uses the same value — without overriding a value already set
in the real environment (e.g. by Docker).
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8001
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/block_planning"
    kafka_brokers: str = "localhost:9092"
    kafka_enabled: bool = True


settings = Settings()

os.environ.setdefault("DATABASE_URL", settings.database_url)
