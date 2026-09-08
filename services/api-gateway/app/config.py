"""API Gateway configuration.

The gateway is a lightweight reverse proxy (architecture Section 4): it routes
reads to the Query Service and writes to the Command Service, and handles
common HTTP concerns (auth stub, correlation-ID injection, logging). It holds
no railway business logic.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8000
    command_service_url: str = "http://localhost:8001"
    query_service_url: str = "http://localhost:8002"
    # Stub auth: when enabled, requests must carry a (non-empty) bearer token.
    # Real authentication is a backlog feature (architecture Section 27).
    auth_enabled: bool = False
    # Outbound request timeout to backend services (seconds).
    upstream_timeout_seconds: float = 10.0


settings = Settings()
