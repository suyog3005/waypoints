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
    # Origins allowed to call the gateway cross-origin (the frontend dev server).
    # The browser blocks the response without CORS headers, so the map page
    # (localhost:3000-3005) cannot read /basegraph or /trainpositions otherwise.
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
        "http://127.0.0.1:3005",
    ]


settings = Settings()
