"""Lightweight HTTP proxying helpers (architecture Section 4).

The gateway forwards requests to the correct backend service and streams the
response back. It adds the correlation-ID header (set by the middleware on
``request.state``) so the trace continues into the upstream service. It does
no business logic — validation and persistence live in the backend services.
"""

from __future__ import annotations

from fastapi import HTTPException, Request
from starlette.responses import Response

from app.middleware import CORRELATION_HEADER

# Headers that must not be forwarded verbatim to the upstream (hop-by-hop /
# host-specific). Everything else (including X-Correlation-Id) is passed through.
_HOP_BY_HOP = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


async def forward(request: Request, method: str, path: str, *, base_url: str) -> Response:
    """Forward ``method path`` to ``base_url`` and return the upstream response.

    The request body and (filtered) headers are passed through. The correlation
    ID from ``request.state`` is injected so the upstream can continue the trace.
    """
    client = request.app.state.http
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP
    }
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id

    body = await request.body()

    try:
        upstream = await client.request(
            method,
            f"{base_url}{path}",
            headers=headers,
            content=body,
            params=request.query_params,
        )
    except Exception as exc:  # noqa: BLE001 - upstream unreachable / timeout
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc

    # Stream the upstream response back, dropping hop-by-hop response headers.
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers={
            k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP
        },
    )
