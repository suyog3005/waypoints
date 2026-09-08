"""Query Service configuration.

Loads settings from the environment / `.env` (see .env.example). Mirrors
READ_STORE_URL into os.environ so the shared `db.readstore.session` module
(which reads it at import time) uses the same value — without overriding a
value already set in the real environment (e.g. by Docker).
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8002
    read_store_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/block_planning_read"
    )
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 60


settings = Settings()

os.environ.setdefault("READ_STORE_URL", settings.read_store_url)
