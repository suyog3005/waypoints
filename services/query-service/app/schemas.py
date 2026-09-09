"""Query Service response models.

These mirror the Read Store projections (db/readstore/models.py) and are what
the API Gateway / frontend consume. They are intentionally flat (denormalized)
so the read path needs no further joins (architecture Section 8).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class PlanSummaryOut(BaseModel):
    plan_id: uuid.UUID
    status: str
    section_id: uuid.UUID
    section_name: str
    division_name: str | None = None
    zone_name: str | None = None
    block_count: int
    request_count: int
    total_block_duration_minutes: int
    created_at: datetime
    synced_at: datetime


class BlockOut(BaseModel):
    block_id: uuid.UUID
    plan_id: uuid.UUID
    plan_status: str
    track_id: uuid.UUID
    track_code: str
    track_name: str
    section_name: str | None = None
    start_time: datetime
    end_time: datetime
    is_merged: bool
    request_count: int
    synced_at: datetime


class TrackOut(BaseModel):
    track_id: uuid.UUID
    code: str
    name: str
    line: str | None = None
    direction: str | None = None
    is_active: bool
    section_id: uuid.UUID
    section_name: str
    division_name: str | None = None
    zone_name: str | None = None
    synced_at: datetime


class TrainOut(BaseModel):
    train_id: uuid.UUID
    train_number: str
    train_type: str | None = None
    is_active: bool
    schedule_count: int
    synced_at: datetime


# ── Map / train-position schemas (Phase 10a) ──────────────────────────
#
# These serialize to camelCase (matching the frontend's TypeScript types in
# components/map/TrainLayer.ts and MapContainer.ts) while being populated from
# snake_case Read Store rows.


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class TrainPositionOut(_CamelModel):
    train_id: uuid.UUID
    x: float
    y: float
    track_id: uuid.UUID | None = None
    track_code: str | None = None
    # Frontend TrainPosition interface uses `speed` (not `speedKmph`).
    speed: int | None = Field(default=None, validation_alias="speed_kmph")
    from_time: datetime
    to_time: datetime


class DataTileIn(_CamelModel):
    """A tile the client is requesting, with the version it already has."""

    id: str
    version: uuid.UUID | None = None


class TrainPositionsRequest(BaseModel):
    tiles: list[DataTileIn] = Field(default_factory=list)


class TrainPositionsMeta(_CamelModel):
    data_tile_versions: dict[str, uuid.UUID]
    business_clock: datetime


class TrainPositionsResponse(_CamelModel):
    positions: list[TrainPositionOut]
    meta: TrainPositionsMeta


class BaseGraphNodeOut(_CamelModel):
    id: str
    x: float
    y: float
    type: str
    name: str | None = None


class BaseGraphEdgeOut(_CamelModel):
    id: str
    # `from` is a Python keyword; the wire name is `from` (frontend BaseGraphEdge).
    from_: str = Field(serialization_alias="from", validation_alias="from")
    to: str
    track_id: uuid.UUID | None = None


class BaseGraphOut(_CamelModel):
    nodes: list[BaseGraphNodeOut]
    edges: list[BaseGraphEdgeOut]
