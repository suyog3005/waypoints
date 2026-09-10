"""Business validation for block requests (architecture Sections 11-12).

These fields are planning inputs, not just display fields — validation happens
here, in the Command Service, before an event is published (Section 11, item 260).

The structured demand fields (OPUS-5 Part G) are validated here too:
- SR-002: lead-time / late-request classification per block class.
- SR-004: mandatory structured fields (work_type + quantum for non-emergency).
- SR-009: criticality must be a known value.
- SR-039: adjacent-line status must be a known value.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schemas import BlockRequestCreate
from db.models import Department, Track, User
from db.models.enums import (
    AdjacentLineStatus,
    BlockClass,
    Criticality,
    OriginType,
)

VALID_OPERATIONAL_REASONS = {
    "BRIDGE",
    "UNDERPASS",
    "ROAD_CROSSING",
    "TREE_WORK",
    "CABLE_MAINTENANCE",
    "TRACK_MAINTENANCE",
    "OTHER",
}

# Minimum notice period (days) per block class (OPUS-5 Part F5). Used to
# classify a request as "late" (SR-002) rather than silently accepting it.
NOTICE_PERIOD_DAYS: dict[str, int] = {
    BlockClass.ROUTINE.value: 14,
    BlockClass.CORRIDOR.value: 365,
    BlockClass.MEGA.value: 30,
    BlockClass.MAJOR_WORKS.value: 60,
    BlockClass.PROJECT.value: 90,
    BlockClass.THIRD_PARTY.value: 45,
    BlockClass.SHORT_MICRO.value: 1,
    BlockClass.EMERGENCY.value: 0,
    BlockClass.RESTORATION.value: 0,
    BlockClass.SECURITY.value: 0,
}


def compute_lead_time(requested_start: datetime, now: datetime | None = None) -> int:
    """Whole days from now until the requested start (negative if in the past)."""
    now = now or datetime.now(timezone.utc)
    if requested_start.tzinfo is None:
        requested_start = requested_start.replace(tzinfo=timezone.utc)
    return (requested_start - now).days


def validate_create(payload: BlockRequestCreate, db: Session) -> list[str]:
    """Return a list of human-readable errors (empty list == valid)."""
    errors: list[str] = []

    if payload.requested_end <= payload.requested_start:
        errors.append("requested_end must be after requested_start")
    if db.get(Department, payload.department_id) is None:
        errors.append("department_id does not reference an existing department")
    if db.get(User, payload.requested_by_user_id) is None:
        errors.append("requested_by_user_id does not reference an existing user")
    if db.get(Track, payload.track_id) is None:
        errors.append("track_id does not reference an existing track")

    if payload.request_type == "technical" and payload.technical is None:
        errors.append("a technical payload is required for technical requests")
    if payload.request_type == "operational" and payload.operational is None:
        errors.append("an operational payload is required for operational requests")
    if payload.operational is not None and payload.operational.reason not in VALID_OPERATIONAL_REASONS:
        errors.append(
            "operational.reason must be one of: " + ", ".join(sorted(VALID_OPERATIONAL_REASONS))
        )

    for track_id in payload.affected_track_ids:
        if db.get(Track, track_id) is None:
            errors.append(f"affected track {track_id} does not exist")

    # ── Structured demand validation (OPUS-5 Part G) ──
    if payload.block_class not in {c.value for c in BlockClass}:
        errors.append(
            "block_class must be one of: " + ", ".join(c.value for c in BlockClass)
        )
    if payload.origin_type not in {o.value for o in OriginType}:
        errors.append(
            "origin_type must be one of: " + ", ".join(o.value for o in OriginType)
        )
    if payload.criticality not in {c.value for c in Criticality}:
        errors.append(
            "criticality must be one of: " + ", ".join(c.value for c in Criticality)
        )
    if payload.adjacent_line_status is not None and payload.adjacent_line_status not in {
        a.value for a in AdjacentLineStatus
    }:
        errors.append(
            "adjacent_line_status must be one of: "
            + ", ".join(a.value for a in AdjacentLineStatus)
        )

    # SR-004: a non-emergency request must be plannable — it needs a work type
    # and a quantum. Emergency blocks use the minimum-field fast path.
    if not payload.is_emergency and payload.block_class != BlockClass.EMERGENCY.value:
        if not payload.work_type:
            errors.append("work_type is required for non-emergency requests (SR-004)")
        if payload.quantum is None:
            errors.append("quantum is required for non-emergency requests (SR-007)")

    # SR-002: classify late requests distinctly. We do not reject them, but we
    # flag them so the planner and approver see the reduced lead time.
    lead = compute_lead_time(payload.requested_start)
    notice = NOTICE_PERIOD_DAYS.get(payload.block_class, 14)
    payload.lead_time_days = lead
    payload.is_late = lead < notice

    return errors
