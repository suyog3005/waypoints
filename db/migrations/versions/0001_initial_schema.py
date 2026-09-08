"""Initial core-MVP schema

Hand-authored from docs/database_schema.md (core-MVP subset per docs/plan.md
Phase 1) — no live Postgres instance was available in this environment to run
`alembic revision --autogenerate`. Once Postgres is reachable (Phase 4/11
Docker Compose), verify this migration matches db/models via:
    alembic upgrade head && alembic check

Revision ID: 0001
Revises:
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')

    request_status = postgresql.ENUM(
        "draft", "submitted", "under_review", "approved", "rejected",
        "merged", "scheduled", "in_progress", "completed", "aborted", "cancelled",
        name="request_status",
    )
    request_priority = postgresql.ENUM("normal", "high", "emergency", name="request_priority")
    plan_status = postgresql.ENUM(
        "proposed", "approved", "active", "completed", "superseded", "cancelled",
        name="plan_status",
    )
    request_type = postgresql.ENUM("technical", "operational", name="request_type")
    optimization_run_status = postgresql.ENUM(
        "pending", "running", "succeeded", "failed", name="optimization_run_status"
    )
    constraint_severity = postgresql.ENUM("hard", "soft", name="constraint_severity")
    event_source = postgresql.ENUM("internal", "external", name="event_source")

    bind = op.get_bind()
    for enum_type in (
        request_status,
        request_priority,
        plan_status,
        request_type,
        optimization_run_status,
        constraint_severity,
        event_source,
    ):
        enum_type.create(bind, checkfirst=True)

    # --- Organizational hierarchy ---------------------------------------
    op.create_table(
        "zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "divisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("zones.id"),
                  nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("zone_id", "code", name="division_code_unique"),
    )

    op.create_table(
        "sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("division_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("divisions.id"),
                  nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("division_id", "code", name="section_code_unique"),
    )

    # --- Identity (minimal: no roles/user_roles/RBAC in MVP) ------------
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("employee_code", sa.String(50), unique=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(20)),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("division_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("divisions.id")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # --- Track network & assets -----------------------------------------
    op.create_table(
        "tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id"),
                  nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("line", sa.String(100)),
        sa.Column("direction", sa.String(20)),
        sa.Column("segment_start", sa.String(100)),
        sa.Column("segment_end", sa.String(100)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_tracks_section", "tracks", ["section_id"])

    op.create_table(
        "track_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"),
                  nullable=False),
        sa.Column("affected_track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"),
                  nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("track_id <> affected_track_id", name="track_dependency_not_self"),
        sa.UniqueConstraint("track_id", "affected_track_id", "relationship_type",
                             name="track_dependency_unique"),
    )

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id")),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="operational"),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "trains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("train_number", sa.String(20), nullable=False, unique=True),
        sa.Column("train_type", sa.String(50)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "train_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("train_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trains.id"),
                  nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"),
                  nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("scheduled_end > scheduled_start", name="train_schedule_time_check"),
    )
    op.create_index(
        "idx_train_schedules_track_time", "train_schedules",
        ["track_id", "scheduled_start", "scheduled_end"],
    )

    op.create_table(
        "restrictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id")),
        sa.Column("restriction_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("max_speed_kmph", sa.Integer),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name="restriction_validity_check"
        ),
    )
    op.create_index(
        "idx_restrictions_track_validity", "restrictions", ["track_id", "valid_from", "valid_to"]
    )

    op.create_table(
        "maintenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id")),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id")),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("required_duration_minutes", sa.Integer),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # --- Block requests ---------------------------------------------------
    op.create_table(
        "block_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id"),
                  nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"),
                  nullable=False),
        sa.Column("request_type", request_type, nullable=False),
        sa.Column("priority", request_priority, nullable=False, server_default="normal"),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"),
                  nullable=False),
        sa.Column("requested_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", request_status, nullable=False, server_default="draft"),
        sa.Column("is_emergency", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("requested_end > requested_start", name="block_request_time_check"),
    )
    op.create_index(
        "idx_block_requests_track_time", "block_requests",
        ["track_id", "requested_start", "requested_end"],
    )
    op.create_index("idx_block_requests_status", "block_requests", ["status"])

    op.create_table(
        "block_request_affected_tracks",
        sa.Column("block_request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("block_requests.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"),
                  primary_key=True),
        sa.Column("reason", sa.String(255)),
    )

    op.create_table(
        "technical_requests",
        sa.Column("block_request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("block_requests.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("train_stops", sa.Text),
        sa.Column("railway_line", sa.String(100)),
        sa.Column("direction", sa.String(20)),
        sa.Column("restriction_type", sa.String(50)),
        sa.Column("train_type", sa.String(50)),
        sa.Column("finance_reference", sa.String(100)),
        sa.Column("responsible_department_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("departments.id")),
        sa.Column("additional_parameters", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "operational_requests",
        sa.Column("block_request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("block_requests.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("reason_details", sa.Text),
        sa.Column("expected_duration_minutes", sa.Integer),
        sa.Column("safety_notes", sa.Text),
        sa.Column("additional_parameters", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # --- Constraints & optimization ---------------------------------------
    op.create_table(
        "constraints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("severity", constraint_severity, nullable=False, server_default="soft"),
        sa.Column("penalty_weight", sa.Numeric(10, 4)),
        sa.Column("applies_to", sa.String(50)),
        sa.Column("definition", postgresql.JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "(severity = 'hard' AND penalty_weight IS NULL) OR (severity = 'soft')",
            name="constraint_penalty_check",
        ),
    )

    op.create_table(
        "optimization_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # FK to events.id added below via ALTER TABLE, since `events` is created after this table.
        sa.Column("triggered_by_event_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", optimization_run_status, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("input_summary", postgresql.JSONB),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # --- Plans & blocks -----------------------------------------------------
    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id"),
                  nullable=False),
        sa.Column("status", plan_status, nullable=False, server_default="proposed"),
        sa.Column("optimization_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("optimization_runs.id")),
        sa.Column("superseded_by_plan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("plans.id")),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"),
                  nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_merged", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("end_time > start_time", name="block_time_check"),
    )
    op.create_index("idx_blocks_track_time", "blocks", ["track_id", "start_time", "end_time"])

    op.create_table(
        "plan_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block_request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("block_requests.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("block_id", "block_request_id", name="plan_item_unique"),
    )
    op.create_index("idx_plan_items_plan", "plan_items", ["plan_id"])
    op.create_index("idx_plan_items_request", "plan_items", ["block_request_id"])

    op.create_table(
        "block_affected_tracks",
        sa.Column("block_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("blocks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"),
                  primary_key=True),
        sa.Column("impact_reason", sa.String(255)),
    )

    op.create_table(
        "optimization_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("optimization_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id")),
        sa.Column("total_block_duration_minutes", sa.Integer),
        sa.Column("affected_trains_count", sa.Integer),
        sa.Column("expected_delay_minutes", sa.Integer),
        sa.Column("utilization_percent", sa.Numeric(5, 2)),
        sa.Column("merged_requests_count", sa.Integer),
        sa.Column("affected_tracks_count", sa.Integer),
        sa.Column("objective_score", sa.Numeric(12, 4)),
        sa.Column("metrics", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # --- Events -------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("source", event_source, nullable=False, server_default="internal"),
        sa.Column("entity_type", sa.String(50)),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True)),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_events_type_time", "events", ["event_type", "occurred_at"])
    op.create_index("idx_events_entity", "events", ["entity_type", "entity_id"])
    op.create_index("idx_events_correlation", "events", ["correlation_id"])

    # --- Deferred FK now that `events` exists --------------------------------
    op.create_foreign_key(
        "fk_optimization_runs_event", "optimization_runs", "events",
        ["triggered_by_event_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_optimization_runs_event", "optimization_runs", type_="foreignkey")
    op.drop_table("events")
    op.drop_table("optimization_results")
    op.drop_table("block_affected_tracks")
    op.drop_table("plan_items")
    op.drop_table("blocks")
    op.drop_table("plans")
    op.drop_table("optimization_runs")
    op.drop_table("constraints")
    op.drop_table("operational_requests")
    op.drop_table("technical_requests")
    op.drop_table("block_request_affected_tracks")
    op.drop_table("block_requests")
    op.drop_table("maintenance")
    op.drop_table("restrictions")
    op.drop_table("train_schedules")
    op.drop_table("trains")
    op.drop_table("assets")
    op.drop_table("track_dependencies")
    op.drop_table("tracks")
    op.drop_table("users")
    op.drop_table("departments")
    op.drop_table("sections")
    op.drop_table("divisions")
    op.drop_table("zones")

    for enum_name in (
        "event_source",
        "constraint_severity",
        "optimization_run_status",
        "request_type",
        "plan_status",
        "request_priority",
        "request_status",
    ):
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
