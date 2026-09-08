"""API request/response schemas for the Command Service.

Reuses the shared event payload models from `contracts` for the type-specific
extensions so the API and the event bus never drift apart.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from contracts.events.schemas import OperationalRequestPayload, TechnicalRequestPayload


class BlockRequestCreate(BaseModel):
    department_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    request_type: str = Field(description="'technical' or 'operational'")
    priority: str = Field(default="normal", description="'normal', 'high', or 'emergency'")
    track_id: uuid.UUID
    requested_start: datetime
    requested_end: datetime
    is_emergency: bool = False
    affected_track_ids: list[uuid.UUID] = Field(default_factory=list)
    technical: TechnicalRequestPayload | None = None
    operational: OperationalRequestPayload | None = None


class BlockRequestUpdate(BaseModel):
    requested_start: datetime | None = None
    requested_end: datetime | None = None
    priority: str | None = None
    is_emergency: bool | None = None
    affected_track_ids: list[uuid.UUID] | None = None
    technical: TechnicalRequestPayload | None = None
    operational: OperationalRequestPayload | None = None


class BlockRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    request_type: str
    priority: str
    track_id: uuid.UUID
    requested_start: datetime
    requested_end: datetime
    status: str
    is_emergency: bool
    submitted_at: datetime | None
    created_at: datetime
