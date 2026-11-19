"""Pipeline-run-tabellen: checkpoints en stage-voortgang.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pipeline_runs",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("pipeline", sa.String(64), nullable=False, server_default="analyse"),
        sa.Column("state", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("current_stage", sa.String(64), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("stages", JSONB, nullable=False, server_default="[]"),
        sa.Column("project_snapshot", JSONB, nullable=False, server_default="{}"),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_pipeline_runs_project_id", "pipeline_runs", ["project_id"])
    op.create_index(
        "ix_pipeline_runs_idempotency_key", "pipeline_runs", ["idempotency_key"]
    )
    # De sweeper zoekt hiermee gestrande runs op.
    op.create_index("ix_pipeline_runs_state", "pipeline_runs", ["state"])


def downgrade():
    op.drop_index("ix_pipeline_runs_state", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_idempotency_key", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_project_id", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
