"""GET /trains — list trains (Read Store, Redis cache-aside)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import Cache, cache_get_or_load, cache_key
from app.db import get_read_store
from app.schemas import TrainOut
from app.serialize import row_to_dict
from db.readstore.models import TrainView

router = APIRouter(tags=["trains"])


@router.get("/trains", response_model=list[TrainOut])
def list_trains(
    request: Request,
    db: Session = Depends(get_read_store),
    active_only: bool = Query(default=False, description="Only active trains."),
) -> list[dict]:
    cache: Cache = request.app.state.cache
    key = cache_key("trains", active_only=active_only or None)

    def loader() -> list[dict]:
        stmt = select(TrainView)
        if active_only:
            stmt = stmt.where(TrainView.is_active.is_(True))
        rows = db.scalars(stmt.order_by(TrainView.train_number)).all()
        return [row_to_dict(r) for r in rows]

    return cache_get_or_load(cache, key, loader)
