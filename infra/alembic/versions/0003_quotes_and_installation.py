"""Saved quote versions and installation checklist.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_quotes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_quotes_project_id", "project_quotes", ["project_id"])
    op.create_table(
        "installation_checks",
        sa.Column("project_id", sa.String(36), primary_key=True),
        sa.Column("symbol_id", sa.String(36), primary_key=True),
    )


def downgrade():
    op.drop_table("installation_checks")
    op.drop_table("project_quotes")
