"""Gateway middleware: correlation-ID injection + stub authentication.

Correlation IDs (architecture Section 4, items 85-86) let a request be traced
across the gateway -> service -> Kafka event chain. The gateway generates one
if the client didn't supply it, forwards it to the upstream service, and echoes
it back in the response.

Authentication is a *stub* (Section 4 item 81; real RBAC is backlog, Section
27): when enabled, it only checks that a non-empty bearer token is present.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

CORRELATION_HEADER = "X-Correlation-Id"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Ensure every request/response carries an X-Correlation-Id header."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(CORRELATION_HEADER)
        correlation_id = incoming if _is_valid_uuid(incoming) else str(uuid.uuid4())
        # Attach for downstream handlers (and the proxy) to forward upstream.
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response


class StubAuthMiddleware(BaseHTTPMiddleware):
    """Minimal bearer-token presence check. No real validation (backlog)."""

    def __init__(self, app, enabled: bool = False) -> None:
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled:
            return await call_next(request)
        # /health is always open so load balancers / compose healthchecks work.
        if request.url.path == "/health":
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer ") or not auth.split(" ", 1)[1].strip():
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or malformed Authorization bearer token."},
            )
        return await call_next(request)


def _is_valid_uuid(value: str | None) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
