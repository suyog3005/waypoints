"""Block request write endpoints (architecture Section 13).

Flow: validate -> persist (request + type extension + affected tracks + event
row) -> commit -> publish event to Kafka (best-effort).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    BlockRequestCreate,
    BlockRequestResponse,
    BlockRequestUpdate,
    ExecutionStateOut,
    ExecutionStateUpdate,
)
from app.validation import validate_create
from contracts.events import BlockRequestSubmitted, BlockRequestUpdated, make_event
from contracts.events.topics import EVENT_TOPIC_MAP
from db.models import (
    BlockExecutionState,
    BlockRequest,
    BlockRequestAffectedTrack,
    Event,
    OperationalRequest,
    TechnicalRequest,
)
from db.models.enums import ExecutionState, PowerBlockState, RequestStatus

router = APIRouter(prefix="/block-requests", tags=["block-requests"])

UPDATABLE_STATUSES = (RequestStatus.DRAFT, RequestStatus.SUBMITTED)


def _correlation_id(request: Request) -> uuid.UUID:
    """Use the gateway-provided correlation ID if present, else generate one
    (architecture Section 4, items 85-86)."""
    header = request.headers.get("X-Correlation-Id")
    if header:
        try:
            return uuid.UUID(header)
        except ValueError:
            pass
    return uuid.uuid4()


def _persist_event(db: Session, event) -> None:
    """Store the event in the `events` table (durable record + traceability)."""
    serialized = event.model_dump(mode="json")
    db.add(
        Event(
            event_type=event.event_type,
            event_version=event.event_version,
            source=event.source,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            correlation_id=event.correlation_id,
            payload=serialized["payload"],
            occurred_at=event.occurred_at,
        )
    )


def _core_payload(block_request: BlockRequest) -> dict:
    """Minimal valid BlockRequestPayload for update events. The optimizer reloads
    full detail from the DB via entity_id (architecture Section 16, item 350)."""
    return {
        "department_id": str(block_request.department_id),
        "requested_by_user_id": str(block_request.requested_by_user_id),
        "request_type": block_request.request_type.value,
        "priority": block_request.priority.value,
        "track_id": str(block_request.track_id),
        "requested_start": block_request.requested_start.isoformat(),
        "requested_end": block_request.requested_end.isoformat(),
        "is_emergency": block_request.is_emergency,
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BlockRequestResponse)
async def create_block_request(
    payload: BlockRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> BlockRequest:
    errors = validate_create(payload, db)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errors": errors}
        )

    now = datetime.now(timezone.utc)
    correlation_id = _correlation_id(request)

    block_request = BlockRequest(
        department_id=payload.department_id,
        requested_by_user_id=payload.requested_by_user_id,
        request_type=payload.request_type,
        priority=payload.priority,
        track_id=payload.track_id,
        requested_start=payload.requested_start,
        requested_end=payload.requested_end,
        status=RequestStatus.SUBMITTED,
        is_emergency=payload.is_emergency,
        submitted_at=now,
        # Structured demand fields (OPUS-5 Part G).
        block_class=payload.block_class,
        origin_type=payload.origin_type,
        criticality=payload.criticality,
        consequence_of_deferral=payload.consequence_of_deferral,
        work_type=payload.work_type,
        quantum=payload.quantum,
        quantum_unit=payload.quantum_unit,
        estimated_duration_minutes=payload.estimated_duration_minutes,
        suggested_duration_minutes=payload.suggested_duration_minutes,
        duration_confidence=payload.duration_confidence,
        adjacent_line_status=payload.adjacent_line_status,
        is_late=payload.is_late,
        lead_time_days=payload.lead_time_days,
    )
    db.add(block_request)
    db.flush()  # populate block_request.id

    # Every request starts in the REQUESTED execution state (OPUS-5 Part H).
    db.add(BlockExecutionState(block_request_id=block_request.id))

    if payload.technical is not None:
        db.add(TechnicalRequest(block_request_id=block_request.id, **payload.technical.model_dump()))
    if payload.operational is not None:
        db.add(
            OperationalRequest(
                block_request_id=block_request.id, **payload.operational.model_dump()
            )
        )
    for track_id in payload.affected_track_ids:
        db.add(BlockRequestAffectedTrack(block_request_id=block_request.id, track_id=track_id))

    event = make_event(
        BlockRequestSubmitted,
        payload=payload.model_dump(mode="json"),
        occurred_at=now,
        entity_id=block_request.id,
        correlation_id=correlation_id,
        producer="command-service",
    )
    _persist_event(db, event)
    db.commit()
    db.refresh(block_request)

    await request.app.state.kafka.publish(
        EVENT_TOPIC_MAP[event.event_type], str(event.event_id), event.model_dump(mode="json")
    )
    return block_request


@router.patch("/{request_id}", response_model=BlockRequestResponse)
async def update_block_request(
    request_id: uuid.UUID,
    payload: BlockRequestUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> BlockRequest:
    block_request = db.get(BlockRequest, request_id)
    if block_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="block request not found")

    if block_request.status not in UPDATABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"cannot update a request in status '{block_request.status.value}'",
        )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no fields to update")

    new_start = data.get("requested_start", block_request.requested_start)
    new_end = data.get("requested_end", block_request.requested_end)
    if new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="requested_end must be after requested_start",
        )

    for field, value in data.items():
        if field == "affected_track_ids":
            continue
        setattr(block_request, field, value)

    if "affected_track_ids" in data:
        db.execute(
            delete(BlockRequestAffectedTrack).where(
                BlockRequestAffectedTrack.block_request_id == block_request.id
            )
        )
        for track_id in data["affected_track_ids"]:
            db.add(BlockRequestAffectedTrack(block_request_id=block_request.id, track_id=track_id))

    now = datetime.now(timezone.utc)
    correlation_id = _correlation_id(request)
    event = make_event(
        BlockRequestUpdated,
        payload=_core_payload(block_request),
        occurred_at=now,
        entity_id=block_request.id,
        correlation_id=correlation_id,
        producer="command-service",
    )
    _persist_event(db, event)
    db.commit()
    db.refresh(block_request)

    await request.app.state.kafka.publish(
        EVENT_TOPIC_MAP[event.event_type], str(event.event_id), event.model_dump(mode="json")
    )
    return block_request


@router.get("", response_model=list[BlockRequestResponse])
async def list_block_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[BlockRequest]:
    """List block requests (authoritative write path).

    Served from the Command Service rather than the Read Store so the list is
    always fresh and each row carries its live execution/safety state (OPUS-5
    Part H). The Read Store projection is for the dashboard; this is the
    operational list.
    """
    stmt = select(BlockRequest).order_by(BlockRequest.created_at.desc())
    if status_filter:
        try:
            stmt = stmt.where(BlockRequest.status == RequestStatus(status_filter.lower()))
        except ValueError:
            pass
    rows = db.scalars(stmt).all()
    # Force-load each execution state so serialization never lazy-loads.
    for row in rows:
        _ = row.execution
    return list(rows)


@router.get("/{request_id}", response_model=BlockRequestResponse)
async def get_block_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BlockRequest:
    """Fetch a single block request with its execution/safety state.

    Served from the Command Service (authoritative write path) so the frontend
    detail page can show the live execution state machine (OPUS-5 Part H).
    """
    block_request = db.get(BlockRequest, request_id)
    if block_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="block request not found")
    # Force-load the one-to-one execution state so serialization never relies
    # on a lazy load after the session is torn down.
    _ = block_request.execution
    return block_request


# Legal execution-state transitions (OPUS-5 Part H). A block may only move
# forward along this chain; safety gates are enforced below.
_EXECUTION_ORDER = [
    ExecutionState.REQUESTED,
    ExecutionState.APPROVED,
    ExecutionState.GRANTED,
    ExecutionState.PROTECTED,
    ExecutionState.ISOLATED,
    ExecutionState.WORKING,
    ExecutionState.HANDED_BACK,
    ExecutionState.CLOSED,
]


def _enforce_safety_gates(
    current: BlockExecutionState,
    new_execution: ExecutionState | None,
    new_power: PowerBlockState | None,
) -> list[str]:
    """Return errors if the requested transition violates a safety gate.

    - SR-038: cannot reach WORKING until the power block is EARTHED.
    - SR-040: cannot reach HANDED_BACK with an open disconnection.
    - No backward transitions (states are fail-safe and monotonic).
    """
    errors: list[str] = []
    if new_execution is None:
        return errors

    cur_idx = _EXECUTION_ORDER.index(current.execution_state)
    new_idx = _EXECUTION_ORDER.index(new_execution)
    if new_idx < cur_idx:
        errors.append(
            f"cannot move execution state backwards from "
            f"'{current.execution_state.value}' to '{new_execution.value}'"
        )
        return errors

    effective_power = new_power or current.power_block_state
    if new_execution == ExecutionState.WORKING and effective_power != PowerBlockState.EARTHED:
        errors.append(
            "cannot start work (WORKING) until the power block is EARTHED (SR-038)"
        )
    if new_execution == ExecutionState.HANDED_BACK and current.has_open_disconnection:
        errors.append(
            "cannot hand back while a disconnection is open (SR-040)"
        )
    return errors


@router.patch("/{request_id}/execution", response_model=BlockRequestResponse)
async def update_execution_state(
    request_id: uuid.UUID,
    payload: ExecutionStateUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> BlockRequest:
    """Advance the execution/safety state machine (OPUS-5 Part H).

    Timestamps are set automatically based on the target state so the actuals
    (grant, protection, earthing, work, hand-back) are captured for the
    learning loop (F1 principle 5).
    """
    block_request = db.get(BlockRequest, request_id)
    if block_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="block request not found")

    exec_state = block_request.execution
    if exec_state is None:
        exec_state = BlockExecutionState(block_request_id=block_request.id)
        db.add(exec_state)
        db.flush()

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no fields to update")

    new_execution = (
        ExecutionState(data["execution_state"]) if data.get("execution_state") else None
    )
    new_power = PowerBlockState(data["power_block_state"]) if data.get("power_block_state") else None

    errors = _enforce_safety_gates(exec_state, new_execution, new_power)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errors": errors})

    now = datetime.now(timezone.utc)

    # Apply explicit field updates.
    if new_execution is not None:
        exec_state.execution_state = new_execution
    if new_power is not None:
        exec_state.power_block_state = new_power
    for field in (
        "grant_reason_code",
        "earthed_by",
        "handed_back_by",
        "fitness_declaration",
        "imposed_speed_kmph",
        "quantum_completed",
        "output_notes",
        "has_open_disconnection",
    ):
        if field in data:
            setattr(exec_state, field, data[field])

    # Auto-stamp timestamps based on the (new) state so actuals are captured.
    if exec_state.execution_state == ExecutionState.GRANTED and exec_state.granted_at is None:
        exec_state.granted_at = now
    if exec_state.execution_state == ExecutionState.PROTECTED and exec_state.protected_at is None:
        exec_state.protected_at = now
    if exec_state.power_block_state == PowerBlockState.EARTHED and exec_state.earthed_at is None:
        exec_state.earthed_at = now
    if exec_state.execution_state == ExecutionState.WORKING and exec_state.work_started_at is None:
        exec_state.work_started_at = now
    if exec_state.execution_state == ExecutionState.HANDED_BACK and exec_state.handed_back_at is None:
        exec_state.handed_back_at = now

    # Keep the request status in sync with the execution state.
    if new_execution is not None:
        status_map = {
            ExecutionState.APPROVED: RequestStatus.APPROVED,
            ExecutionState.GRANTED: RequestStatus.IN_PROGRESS,
            ExecutionState.WORKING: RequestStatus.IN_PROGRESS,
            ExecutionState.HANDED_BACK: RequestStatus.COMPLETED,
            ExecutionState.CLOSED: RequestStatus.COMPLETED,
            ExecutionState.CANCELLED: RequestStatus.CANCELLED,
        }
        if new_execution in status_map:
            block_request.status = status_map[new_execution]

    correlation_id = _correlation_id(request)
    event = make_event(
        BlockRequestUpdated,
        payload=_core_payload(block_request),
        occurred_at=now,
        entity_id=block_request.id,
        correlation_id=correlation_id,
        producer="command-service",
    )
    _persist_event(db, event)
    db.commit()
    db.refresh(block_request)

    await request.app.state.kafka.publish(
        EVENT_TOPIC_MAP[event.event_type], str(event.event_id), event.model_dump(mode="json")
    )
    return block_request
