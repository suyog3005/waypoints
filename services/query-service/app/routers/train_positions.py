"""POST /trainpositions — tile-based train position fetch (Phase 10a.8).

Implements *delta transfer*: the client sends the tiles it is viewing (with the
versions it already has); the server returns positions only for tiles whose
version has changed, plus the latest version of every requested tile so the
client can update its cache.

Reads the Read Store projections ``train_position`` and ``data_tile``
(populated by ``db.readstore.etl``). Responses are cached in Redis for a short
TTL (10 s) to absorb the 2 s polling burst.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import Cache, cache_get_or_load, cache_key
from app.db import get_read_store
from app.schemas import TrainPositionsRequest, TrainPositionsResponse
from db.readstore.models import DataTile, TrainPosition
from db.readstore.tiling import position_tiles

router = APIRouter(tags=["trainpositions"])

# Short TTL: the frontend polls every 2 s, so a 10 s cache absorbs bursts while
# still keeping positions fresh.
_POSITIONS_TTL = 10


@router.post("/trainpositions", response_model=TrainPositionsResponse)
def get_train_positions(
    request: Request,
    payload: TrainPositionsRequest,
    db: Session = Depends(get_read_store),
) -> dict:
    cache: Cache = request.app.state.cache

    # Map of tile_id -> client's known version (None if the client has it not).
    client_versions: dict[str, uuid.UUID | None] = {t.id: t.version for t in payload.tiles}
    tile_ids = list(client_versions)

    # Deterministic cache key from the requested tile IDs (sorted).
    key = cache_key("trainpositions", tiles=",".join(sorted(tile_ids)))

    def loader() -> dict:
        # Latest version of every requested tile (so the client can refresh its
        # cache even for tiles it does not need to refetch).
        latest_versions: dict[str, uuid.UUID] = {}
        if tile_ids:
            rows = db.scalars(select(DataTile).where(DataTile.tile_id.in_(tile_ids))).all()
            latest_versions = {t.tile_id: t.version for t in rows}

        # A tile needs refetching if the client has no version, or its version
        # differs from the latest.
        changed = {
            tid
            for tid in tile_ids
            if tid in latest_versions and client_versions.get(tid) != latest_versions[tid]
        }

        # Group positions by tile (delta transfer unit). For each CHANGED tile,
        # include every position that spans it (from_time..to_time). Unchanged
        # tiles are omitted entirely — the frontend keeps its cached positions
        # for them. The frontend filters by display time afterwards.
        tiles_payload: dict[str, list[dict]] = {}
        if changed:
            pos_rows = db.scalars(select(TrainPosition)).all()
            for p in pos_rows:
                pos = {
                    "train_id": p.train_id,
                    "x": p.x,
                    "y": p.y,
                    "track_id": p.track_id,
                    "track_code": p.track_code,
                    "speed_kmph": p.speed_kmph,
                    "from_time": p.from_time,
                    "to_time": p.to_time,
                }
                for tid in position_tiles(p.x, p.y, p.from_time, p.to_time):
                    if tid in changed:
                        tiles_payload.setdefault(tid, []).append(pos)

        return {
            "tiles": tiles_payload,
            "meta": {
                "data_tile_versions": latest_versions,
                "business_clock": datetime.now(timezone.utc),
            },
        }

    return cache_get_or_load(cache, key, loader, ttl=_POSITIONS_TTL)
