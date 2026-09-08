"""Initial Read Store projections

Hand-authored from db/readstore/models.py (Phase 6) — no live Postgres instance
was available in this environment to run `alembic revision --autogenerate`.
Once the read database is reachable (Phase 11 Docker Compose), verify this
migration matches the models via:
    alembic -c db/readstore/alembic.ini upgrade head && alembic -c db/readstore/alembic.ini check

The Read Store is a separate database, so these tables declare no foreign keys
to the Operational DB (Postgres does not support cross-database FKs).

Revision ID: 0001
Revises:
Create Date: 2026-09-09
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
    op.create_table(
        "plan_summary",
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_name", sa.String(150), nullable=False),
        sa.Column("division_name", sa.String(150)),
        sa.Column("zone_name", sa.String(150)),
        sa.Column("block_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "total_block_duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_plan_summary_status", "plan_summary", ["status"])
    op.create_index("idx_plan_summary_section", "plan_summary", ["section_id"])

    op.create_table(
        "block_view",
        sa.Column("block_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_status", sa.String(30), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_code", sa.String(50), nullable=False),
        sa.Column("track_name", sa.String(150), nullable=False),
        sa.Column("section_name", sa.String(150)),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_merged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_block_view_track_time", "block_view", ["track_id", "start_time", "end_time"])
    op.create_index("idx_block_view_plan", "block_view", ["plan_id"])

    op.create_table(
        "track_view",
        sa.Column("track_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("line", sa.String(100)),
        sa.Column("direction", sa.String(20)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_name", sa.String(150), nullable=False),
        sa.Column("division_name", sa.String(150)),
        sa.Column("zone_name", sa.String(150)),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_track_view_section", "track_view", ["section_id"])
    op.create_unique_constraint("uq_track_view_code", "track_view", ["code"])

    op.create_table(
        "train_view",
        sa.Column("train_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("train_number", sa.String(20), nullable=False),
        sa.Column("train_type", sa.String(50)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_train_view_number", "train_view", ["train_number"])


def downgrade() -> None:
    op.drop_table("train_view")
    op.drop_table("track_view")
    op.drop_table("block_view")
    op.drop_table("plan_summary")
