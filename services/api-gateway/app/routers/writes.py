"""Write routes — proxied to the Command Service (architecture Section 4, item 80).

The gateway forwards block-request create/update commands to the Command
Service, which owns validation, persistence, and event publishing. The gateway
adds no business logic here.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import Response

from app.config import settings
from app.proxy import forward

router = APIRouter(prefix="/block-requests", tags=["writes"])


@router.post("")
async def create_block_request(request: Request) -> Response:
    return await forward(
        request, "POST", "/block-requests", base_url=settings.command_service_url
    )


@router.patch("/{request_id}")
async def update_block_request(request: Request, request_id: str) -> Response:
    return await forward(
        request,
        "PATCH",
        f"/block-requests/{request_id}",
        base_url=settings.command_service_url,
    )
