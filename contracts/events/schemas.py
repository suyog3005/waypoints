"""Typed payload models for each event type.

These are the domain-specific bodies carried inside `BaseEvent.payload`.
Field choices follow docs/application_architecture_flow.md Sections 11-12
(block request fields) and 16-20 (optimization inputs/outputs).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TechnicalRequestPayload(BaseModel):
    train_stops: str | None = None
    railway_line: str | None = None
    direction: str | None = None
    restriction_type: str | None = None
    train_type: str | None = None
    finance_reference: str | None = None
    responsible_department_id: uuid.UUID | None = None
    additional_parameters: dict | None = None


class OperationalRequestPayload(BaseModel):
    reason: str = Field(description="BRIDGE, UNDERPASS, ROAD_CROSSING, TREE_WORK, ...")
    reason_details: str | None = None
    expected_duration_minutes: int | None = None
    safety_notes: str | None = None
    additional_parameters: dict | None = None


class BlockRequestPayload(BaseModel):
    """Common fields for a block request, plus the type-specific extension.

    The structured demand fields (block_class, origin_type, criticality,
    work_type, quantum, ...) implement OPUS-5 Part G — they turn a free-text
    request into a machine-plannable object (SR-002/004/006/007/009).
    """

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


class OptimizationRequestPayload(BaseModel):
    """Trigger for the optimizer. `scope` limits the re-plan to a section/track."""

    section_id: uuid.UUID | None = None
    track_id: uuid.UUID | None = None
    reason: str = Field(default="new_request", description="Why optimization was triggered.")
    include_request_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Optional explicit set of requests to consider."
    )


class OptimizationResultPayload(BaseModel):
    plan_id: uuid.UUID
    total_block_duration_minutes: int | None = None
    affected_trains_count: int | None = None
    expected_delay_minutes: int | None = None
    utilization_percent: float | None = None
    merged_requests_count: int | None = None
    affected_tracks_count: int | None = None
    objective_score: float | None = None
    metrics: dict | None = None


class TrackStatusPayload(BaseModel):
    track_id: uuid.UUID
    status: str = Field(description="e.g. AVAILABLE, UNAVAILABLE, DEGRADED")
    reason: str | None = None


class TrainDelayPayload(BaseModel):
    train_id: uuid.UUID
    track_id: uuid.UUID | None = None
    delay_minutes: int = Field(ge=0)
    reason: str | None = None
