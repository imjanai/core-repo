"""Initiële tabellen: projects en corrections.

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("file_type", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("original_filename", sa.String(512), nullable=False, server_default=""),
        sa.Column("s3_key", sa.String(1024), nullable=False, server_default=""),
        sa.Column("scale", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("rooms", JSONB, nullable=False, server_default="[]"),
        sa.Column("symbols", JSONB, nullable=False, server_default="[]"),
        sa.Column("materials", JSONB, nullable=False, server_default="[]"),
        sa.Column("warnings", JSONB, nullable=False, server_default="[]"),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("task_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "corrections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False, index=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("symbol_id", sa.String(36), nullable=True),
        sa.Column("new_type", sa.String(64), nullable=True),
        sa.Column("new_x", sa.Float, nullable=True),
        sa.Column("new_y", sa.Float, nullable=True),
        sa.Column("comment", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_corrections_project_id", "corrections", ["project_id"]
    )


def downgrade():
    op.drop_index("ix_corrections_project_id", table_name="corrections")
    op.drop_table("corrections")
    op.drop_table("projects")
