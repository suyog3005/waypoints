"""Query Service response models.

These mirror the Read Store projections (db/readstore/models.py) and are what
the API Gateway / frontend consume. They are intentionally flat (denormalized)
so the read path needs no further joins (architecture Section 8).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


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
