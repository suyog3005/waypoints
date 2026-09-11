"""Structured block requests + execution/safety state machine.

Adds the OPUS-5 Part G structured demand fields to ``block_requests`` and a
new ``block_execution_states`` table carrying the execution + safety state
machine (OPUS-5 Part H, SR-026..SR-044).

Hand-authored to match db/models/requests.py and db/models/enums.py. Verify
against the models once Postgres is reachable:
    alembic upgrade head && alembic check

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New ENUM types ---------------------------------------------------
    # Named ENUMs are auto-created by SQLAlchemy only when a column carrying
    # them is part of a CREATE TABLE (see block_execution_states below,
    # which auto-creates execution_state/power_block_state). The four types
    # below are only ever used via ADD COLUMN on the existing block_requests
    # table, which does NOT auto-create the type, so those four must be
    # created explicitly first (checkfirst=True keeps this idempotent).
    bind = op.get_bind()

    block_class = postgresql.ENUM(
        "routine", "corridor", "mega", "major_works", "project",
        "third_party", "short_micro", "emergency", "restoration", "security",
        name="block_class",
    )
    origin_type = postgresql.ENUM(
        "defect", "statutory", "condition_based", "project", "failure",
        "directive", "audit", "ad_hoc",
        name="origin_type",
    )
    criticality = postgresql.ENUM(
        "safety_critical", "high", "medium", "low", name="criticality"
    )
    adjacent_line_status = postgresql.ENUM(
        "open", "cautioned", "blocked", "physical_barrier", "lookout_posted",
        name="adjacent_line_status",
    )
    execution_state = postgresql.ENUM(
        "requested", "approved", "granted", "protected", "isolated", "working",
        "handed_back", "closed", "cancelled",
        name="execution_state",
    )
    power_block_state = postgresql.ENUM(
        "not_requested", "requested", "granted", "earthed", "earth_removed",
        name="power_block_state",
    )

    for enum_type in (block_class, origin_type, criticality, adjacent_line_status):
        enum_type.create(bind, checkfirst=True)

    # --- Structured demand fields on block_requests (OPUS-5 Part G) -------
    op.add_column(
        "block_requests",
        sa.Column("block_class", block_class, nullable=False, server_default="routine"),
    )
    op.add_column(
        "block_requests",
        sa.Column("origin_type", origin_type, nullable=False, server_default="ad_hoc"),
    )
    op.add_column(
        "block_requests",
        sa.Column("criticality", criticality, nullable=False, server_default="medium"),
    )
    op.add_column("block_requests", sa.Column("consequence_of_deferral", sa.Text))
    op.add_column("block_requests", sa.Column("work_type", sa.String(150)))
    op.add_column("block_requests", sa.Column("quantum", sa.Integer()))
    op.add_column("block_requests", sa.Column("quantum_unit", sa.String(50)))
    op.add_column("block_requests", sa.Column("estimated_duration_minutes", sa.Integer()))
    op.add_column("block_requests", sa.Column("suggested_duration_minutes", sa.Integer()))
    op.add_column("block_requests", sa.Column("duration_confidence", sa.String(20)))
    op.add_column(
        "block_requests",
        sa.Column("adjacent_line_status", adjacent_line_status),
    )
    op.add_column(
        "block_requests",
        sa.Column("is_late", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column("block_requests", sa.Column("lead_time_days", sa.Integer()))

    # --- Execution + safety state machine (OPUS-5 Part H) -----------------
    op.create_table(
        "block_execution_states",
        sa.Column("block_request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("block_requests.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("execution_state", execution_state, nullable=False,
                  server_default="requested"),
        sa.Column("power_block_state", power_block_state, nullable=False,
                  server_default="not_requested"),
        sa.Column("granted_at", sa.DateTime(timezone=True)),
        sa.Column("grant_reason_code", sa.String(50)),
        sa.Column("protected_at", sa.DateTime(timezone=True)),
        sa.Column("earthed_at", sa.DateTime(timezone=True)),
        sa.Column("earthed_by", sa.String(150)),
        sa.Column("work_started_at", sa.DateTime(timezone=True)),
        sa.Column("work_ended_at", sa.DateTime(timezone=True)),
        sa.Column("handed_back_at", sa.DateTime(timezone=True)),
        sa.Column("handed_back_by", sa.String(150)),
        sa.Column("fitness_declaration", sa.Text),
        sa.Column("imposed_speed_kmph", sa.Integer()),
        sa.Column("quantum_completed", sa.Integer()),
        sa.Column("output_notes", sa.Text),
        sa.Column("has_open_disconnection", sa.Boolean, nullable=False,
                  server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("block_execution_states")

    for col in (
        "lead_time_days",
        "is_late",
        "adjacent_line_status",
        "duration_confidence",
        "suggested_duration_minutes",
        "estimated_duration_minutes",
        "quantum_unit",
        "quantum",
        "work_type",
        "consequence_of_deferral",
        "criticality",
        "origin_type",
        "block_class",
    ):
        op.drop_column("block_requests", col)

    # Drop the ENUM types (safe to drop after the columns that use them).
    for enum_name in (
        "power_block_state",
        "execution_state",
        "adjacent_line_status",
        "criticality",
        "origin_type",
        "block_class",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
