"""GET /tracks — list tracks (Read Store, Redis cache-aside)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import Cache, cache_get_or_load, cache_key
from app.db import get_read_store
from app.schemas import TrackOut
from app.serialize import row_to_dict
from db.readstore.models import TrackView

router = APIRouter(tags=["tracks"])


@router.get("/tracks", response_model=list[TrackOut])
def list_tracks(
    request: Request,
    db: Session = Depends(get_read_store),
    section_id: uuid.UUID | None = Query(default=None, description="Filter by section."),
    active_only: bool = Query(default=False, description="Only active tracks."),
) -> list[dict]:
    cache: Cache = request.app.state.cache
    key = cache_key("tracks", section_id=section_id, active_only=active_only or None)

    def loader() -> list[dict]:
        stmt = select(TrackView)
        if section_id is not None:
            stmt = stmt.where(TrackView.section_id == section_id)
        if active_only:
            stmt = stmt.where(TrackView.is_active.is_(True))
        rows = db.scalars(stmt.order_by(TrackView.code)).all()
        return [row_to_dict(r) for r in rows]

    return cache_get_or_load(cache, key, loader)
