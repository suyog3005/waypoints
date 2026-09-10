"""Enum types mirroring the Postgres ENUM types in docs/database_schema.md
(Section 2). Only the enums used by core-MVP tables are defined here; enums
used exclusively by backlog/extended-feature tables (approval_decision,
notification_channel, notification_status, simulation_status,
weather_risk_level) are intentionally omitted until those features are built.
"""

import enum


class RequestStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABORTED = "aborted"
    CANCELLED = "cancelled"


class RequestPriority(str, enum.Enum):
    NORMAL = "normal"
    HIGH = "high"
    EMERGENCY = "emergency"


class RequestType(str, enum.Enum):
    TECHNICAL = "technical"
    OPERATIONAL = "operational"


class BlockClass(str, enum.Enum):
    """OPUS-5 Part F5 block classes. Drives notice period, approval chain and
    mandatory fields (SR-002, SR-009)."""

    ROUTINE = "routine"
    CORRIDOR = "corridor"
    MEGA = "mega"
    MAJOR_WORKS = "major_works"
    PROJECT = "project"
    THIRD_PARTY = "third_party"
    SHORT_MICRO = "short_micro"
    EMERGENCY = "emergency"
    RESTORATION = "restoration"
    SECURITY = "security"


class OriginType(str, enum.Enum):
    """How the demand originated (OPUS-5 G2 field 1.8). Determines criticality
    defaults and whether a due date is legally binding."""

    DEFECT = "defect"
    STATUTORY = "statutory"
    CONDITION_BASED = "condition_based"
    PROJECT = "project"
    FAILURE = "failure"
    DIRECTIVE = "directive"
    AUDIT = "audit"
    AD_HOC = "ad_hoc"


class Criticality(str, enum.Enum):
    """Mandatory criticality classification (SR-009). Feeds the optimiser
    objective as a weight, not a free choice."""

    SAFETY_CRITICAL = "safety_critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AdjacentLineStatus(str, enum.Enum):
    """Adjacent-line protection state (SR-039). A first-class safety fact,
    separate from the traffic block itself."""

    OPEN = "open"
    CAUTIONED = "cautioned"
    BLOCKED = "blocked"
    PHYSICAL_BARRIER = "physical_barrier"
    LOOKOUT_POSTED = "lookout_posted"


class ExecutionState(str, enum.Enum):
    """OPUS-5 Part H execution state machine (SR-026..SR-036). Each transition
    is a timestamped, immutable event; the block cannot advance past a safety
    gate until the gate is confirmed (SR-038, SR-040)."""

    REQUESTED = "requested"
    APPROVED = "approved"
    GRANTED = "granted"
    PROTECTED = "protected"
    ISOLATED = "isolated"
    WORKING = "working"
    HANDED_BACK = "handed_back"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PowerBlockState(str, enum.Enum):
    """Power (OHE) isolation state (SR-038). Modelled as a *distinct, separately
    confirmed* state from the traffic block. Work near live OHE cannot start
    until ``EARTHED`` is recorded by the TPC."""

    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    GRANTED = "granted"
    EARTHED = "earthed"
    EARTH_REMOVED = "earth_removed"


class PlanStatus(str, enum.Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class OptimizationRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ConstraintSeverity(str, enum.Enum):
    HARD = "hard"
    SOFT = "soft"


class EventSource(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


def pg_enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Helper for SQLAlchemy's `Enum(..., values_callable=pg_enum_values)`."""
    return [member.value for member in enum_cls]
