"""Read routes — proxied to the Query Service (architecture Section 4, item 79).

The gateway exposes a stable external read API; the frontend never learns the
Query Service's address. Query strings are forwarded so filters work.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import Response

from app.config import settings
from app.proxy import forward

router = APIRouter(tags=["reads"])


@router.get("/plans")
async def get_plans(request: Request) -> Response:
    return await forward(request, "GET", "/plans", base_url=settings.query_service_url)


@router.get("/blocks")
async def get_blocks(request: Request) -> Response:
    return await forward(request, "GET", "/blocks", base_url=settings.query_service_url)


@router.get("/tracks")
async def get_tracks(request: Request) -> Response:
    return await forward(request, "GET", "/tracks", base_url=settings.query_service_url)


@router.get("/trains")
async def get_trains(request: Request) -> Response:
    return await forward(request, "GET", "/trains", base_url=settings.query_service_url)


@router.get("/basegraph")
async def get_basegraph(request: Request) -> Response:
    return await forward(request, "GET", "/basegraph", base_url=settings.query_service_url)


@router.post("/trainpositions")
async def get_train_positions(request: Request) -> Response:
    return await forward(request, "POST", "/trainpositions", base_url=settings.query_service_url)
