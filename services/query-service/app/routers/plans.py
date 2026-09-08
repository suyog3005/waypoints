"""GET /plans — list plan summaries (Read Store, Redis cache-aside)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import Cache, cache_get_or_load, cache_key
from app.db import get_read_store
from app.schemas import PlanSummaryOut
from app.serialize import row_to_dict
from db.readstore.models import PlanSummary

router = APIRouter(tags=["plans"])


@router.get("/plans", response_model=list[PlanSummaryOut])
def list_plans(
    request: Request,
    db: Session = Depends(get_read_store),
    status: str | None = Query(default=None, description="Filter by plan status."),
    section_id: uuid.UUID | None = Query(default=None, description="Filter by section."),
) -> list[dict]:
    cache: Cache = request.app.state.cache
    key = cache_key("plans", status=status, section_id=section_id)

    def loader() -> list[dict]:
        stmt = select(PlanSummary)
        if status is not None:
            stmt = stmt.where(PlanSummary.status == status)
        if section_id is not None:
            stmt = stmt.where(PlanSummary.section_id == section_id)
        rows = db.scalars(stmt.order_by(PlanSummary.created_at.desc())).all()
        return [row_to_dict(r) for r in rows]

    return cache_get_or_load(cache, key, loader)
