"""Business validation for block requests (architecture Sections 11-12).

These fields are planning inputs, not just display fields — validation happens
here, in the Command Service, before an event is published (Section 11, item 260).
"""

from sqlalchemy.orm import Session

from app.schemas import BlockRequestCreate
from db.models import Department, Track, User

VALID_OPERATIONAL_REASONS = {
    "BRIDGE",
    "UNDERPASS",
    "ROAD_CROSSING",
    "TREE_WORK",
    "CABLE_MAINTENANCE",
    "TRACK_MAINTENANCE",
    "OTHER",
}


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

    return errors
