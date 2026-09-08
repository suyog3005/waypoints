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
