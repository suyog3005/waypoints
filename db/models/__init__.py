"""Shared SQLAlchemy models package.

Tables are translated from docs/database_schema.md (core-MVP subset only, per
docs/plan.md Phase 1). Import every model module here so `Base.metadata`
(used by Alembic's `target_metadata` in db/migrations/env.py) is complete.

Omitted from the MVP (backlog — see docs/plan.md Section 3 and
docs/application_architecture_flow.md Sections 27-32):
`stations`, `roles`, `user_roles`, `corridor_groups`, `corridor_group_requests`,
`approval_steps`, `escalations`, `simulation_runs`, `simulation_results`,
`block_execution_reports`, `notifications`, `notification_recipients`,
`weather_observations`, `weather_risk_assessments`, `audit_logs`.
"""

from db.models.base import Base
from db.models.enums import (
    AdjacentLineStatus,
    BlockClass,
    ConstraintSeverity,
    Criticality,
    EventSource,
    ExecutionState,
    OptimizationRunStatus,
    OriginType,
    PlanStatus,
    PowerBlockState,
    RequestPriority,
    RequestStatus,
    RequestType,
)
from db.models.events import Event
from db.models.identity import Department, User
from db.models.network import (
    Asset,
    Maintenance,
    Restriction,
    Track,
    TrackDependency,
    Train,
    TrainSchedule,
)
from db.models.org import Division, Section, Zone
from db.models.planning import (
    Block,
    BlockAffectedTrack,
    Constraint,
    OptimizationResult,
    OptimizationRun,
    Plan,
    PlanItem,
)
from db.models.requests import (
    BlockExecutionState,
    BlockRequest,
    BlockRequestAffectedTrack,
    OperationalRequest,
    TechnicalRequest,
)

__all__ = [
    "Base",
    "AdjacentLineStatus",
    "BlockClass",
    "ConstraintSeverity",
    "Criticality",
    "EventSource",
    "ExecutionState",
    "OptimizationRunStatus",
    "OriginType",
    "PlanStatus",
    "PowerBlockState",
    "RequestPriority",
    "RequestStatus",
    "RequestType",
    "Event",
    "Department",
    "User",
    "Asset",
    "Maintenance",
    "Restriction",
    "Track",
    "TrackDependency",
    "Train",
    "TrainSchedule",
    "Zone",
    "Division",
    "Section",
    "Block",
    "BlockAffectedTrack",
    "Constraint",
    "OptimizationResult",
    "OptimizationRun",
    "Plan",
    "PlanItem",
    "BlockRequest",
    "BlockRequestAffectedTrack",
    "BlockExecutionState",
    "OperationalRequest",
    "TechnicalRequest",
]
