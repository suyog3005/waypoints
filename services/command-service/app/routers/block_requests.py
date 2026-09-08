"""Block request write endpoints (architecture Section 13).

Flow: validate -> persist (request + type extension + affected tracks + event
row) -> commit -> publish event to Kafka (best-effort).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import BlockRequestCreate, BlockRequestResponse, BlockRequestUpdate
from app.validation import validate_create
from contracts.events import BlockRequestSubmitted, BlockRequestUpdated, make_event
from contracts.events.topics import EVENT_TOPIC_MAP
from db.models import (
    BlockRequest,
    BlockRequestAffectedTrack,
    Event,
    OperationalRequest,
    TechnicalRequest,
)
from db.models.enums import RequestStatus

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
    )
    db.add(block_request)
    db.flush()  # populate block_request.id

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
