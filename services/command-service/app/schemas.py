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
    # ── Structured demand fields (OPUS-5 Part G) ──
    block_class: str = Field(default="routine")
    origin_type: str = Field(default="ad_hoc")
    criticality: str = Field(default="medium")
    consequence_of_deferral: str | None = None
    work_type: str | None = None
    quantum: int | None = None
    quantum_unit: str | None = None
    estimated_duration_minutes: int | None = None
    suggested_duration_minutes: int | None = None
    duration_confidence: str | None = None
    adjacent_line_status: str | None = None
    is_late: bool = False
    lead_time_days: int | None = None


class BlockRequestUpdate(BaseModel):
    requested_start: datetime | None = None
    requested_end: datetime | None = None
    priority: str | None = None
    is_emergency: bool | None = None
    affected_track_ids: list[uuid.UUID] | None = None
    technical: TechnicalRequestPayload | None = None
    operational: OperationalRequestPayload | None = None
    block_class: str | None = None
    origin_type: str | None = None
    criticality: str | None = None
    consequence_of_deferral: str | None = None
    work_type: str | None = None
    quantum: int | None = None
    quantum_unit: str | None = None
    estimated_duration_minutes: int | None = None
    adjacent_line_status: str | None = None


class ExecutionStateOut(BaseModel):
    """Execution + safety state for a block request (OPUS-5 Part H)."""

    model_config = ConfigDict(from_attributes=True)

    execution_state: str
    power_block_state: str
    granted_at: datetime | None = None
    grant_reason_code: str | None = None
    protected_at: datetime | None = None
    earthed_at: datetime | None = None
    earthed_by: str | None = None
    work_started_at: datetime | None = None
    work_ended_at: datetime | None = None
    handed_back_at: datetime | None = None
    handed_back_by: str | None = None
    fitness_declaration: str | None = None
    imposed_speed_kmph: int | None = None
    quantum_completed: int | None = None
    output_notes: str | None = None
    has_open_disconnection: bool = False


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
    # Structured demand fields.
    block_class: str
    origin_type: str
    criticality: str
    consequence_of_deferral: str | None = None
    work_type: str | None = None
    quantum: int | None = None
    quantum_unit: str | None = None
    estimated_duration_minutes: int | None = None
    suggested_duration_minutes: int | None = None
    duration_confidence: str | None = None
    adjacent_line_status: str | None = None
    is_late: bool = False
    lead_time_days: int | None = None
    # Execution + safety state (nested; None if not yet created).
    execution: ExecutionStateOut | None = None


class ExecutionStateUpdate(BaseModel):
    """Advance the execution/safety state machine (OPUS-5 Part H, SR-026..044).

    Only the fields relevant to the requested transition need be supplied.
    Safety gates are enforced in the router (e.g. cannot reach ``working``
    until the power block is ``earthed``; cannot hand back with an open
    disconnection).
    """

    execution_state: str | None = None
    power_block_state: str | None = None
    grant_reason_code: str | None = None
    earthed_by: str | None = None
    handed_back_by: str | None = None
    fitness_declaration: str | None = None
    imposed_speed_kmph: int | None = None
    quantum_completed: int | None = None
    output_notes: str | None = None
    has_open_disconnection: bool | None = None
