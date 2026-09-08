"""GET /blocks — list blocks (Read Store, Redis cache-aside)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import Cache, cache_get_or_load, cache_key
from app.db import get_read_store
from app.schemas import BlockOut
from app.serialize import row_to_dict
from db.readstore.models import BlockView

router = APIRouter(tags=["blocks"])


@router.get("/blocks", response_model=list[BlockOut])
def list_blocks(
    request: Request,
    db: Session = Depends(get_read_store),
    plan_id: uuid.UUID | None = Query(default=None, description="Filter by plan."),
    track_id: uuid.UUID | None = Query(default=None, description="Filter by track."),
) -> list[dict]:
    cache: Cache = request.app.state.cache
    key = cache_key("blocks", plan_id=plan_id, track_id=track_id)

    def loader() -> list[dict]:
        stmt = select(BlockView)
        if plan_id is not None:
            stmt = stmt.where(BlockView.plan_id == plan_id)
        if track_id is not None:
            stmt = stmt.where(BlockView.track_id == track_id)
        rows = db.scalars(stmt.order_by(BlockView.start_time)).all()
        return [row_to_dict(r) for r in rows]

    return cache_get_or_load(cache, key, loader)
