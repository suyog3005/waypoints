"""API Gateway entrypoint.

The controlled entry point for the frontend (architecture Section 4). It routes
reads to the Query Service and writes to the Command Service, and handles common
HTTP concerns: correlation-ID injection, a stub auth check, and request logging.
It holds no railway business logic — that lives in the backend services.
"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import settings
from app.middleware import CorrelationIdMiddleware, StubAuthMiddleware
from app.routers import reads, writes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=settings.upstream_timeout_seconds)
    logger.info(
        "API Gateway started (command=%s, query=%s, auth=%s).",
        settings.command_service_url,
        settings.query_service_url,
        "on" if settings.auth_enabled else "off",
    )
    yield
    await app.state.http.aclose()
    logger.info("API Gateway stopped.")


app = FastAPI(title="API Gateway", lifespan=lifespan)

# Middleware order: add_middleware inserts at the front, so the LAST one added is
# outermost (runs first). We want correlation-ID outermost so even auth 401
# responses carry the header.
app.add_middleware(StubAuthMiddleware, enabled=settings.auth_enabled)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(reads.router)
app.include_router(writes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
