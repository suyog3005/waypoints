"""Map projections: train_position, base_graph_node, base_graph_edge, data_tile

Hand-authored from db/readstore/models.py (Phase 10a) — no live Postgres
instance was available in this environment to run `alembic revision
--autogenerate`. Verify against the models once the read database is reachable:
    alembic -c db/readstore/alembic.ini upgrade head && alembic -c db/readstore/alembic.ini check

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-09
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
    # ── train_position ────────────────────────────────────────────────
    op.create_table(
        "train_position",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("train_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("train_number", sa.String(20), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_code", sa.String(50), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("speed_kmph", sa.Integer()),
        sa.Column("from_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("to_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_train_position_time", "train_position", ["from_time", "to_time"])
    op.create_index("idx_train_position_track", "train_position", ["track_id"])

    # ── base_graph_node ───────────────────────────────────────────────
    op.create_table(
        "base_graph_node",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("node_key", sa.String(50), nullable=False),
        sa.Column("node_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(150)),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_base_graph_node_key", "base_graph_node", ["node_key"])

    # ── base_graph_edge ───────────────────────────────────────────────
    op.create_table(
        "base_graph_edge",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("edge_key", sa.String(50), nullable=False),
        sa.Column("from_node", sa.String(50), nullable=False),
        sa.Column("to_node", sa.String(50), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True)),
        sa.Column("track_code", sa.String(50)),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_base_graph_edge_key", "base_graph_edge", ["edge_key"])

    # ── data_tile ─────────────────────────────────────────────────────
    op.create_table(
        "data_tile",
        sa.Column("tile_id", sa.String(120), primary_key=True),
        sa.Column(
            "version",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("train_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("signature", sa.String(2000), nullable=False, server_default=sa.text("''")),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("data_tile")
    op.drop_table("base_graph_edge")
    op.drop_table("base_graph_node")
    op.drop_table("train_position")
