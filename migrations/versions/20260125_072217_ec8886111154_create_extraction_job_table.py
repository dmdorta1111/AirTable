"""Create extraction_jobs table for database-backed job queue

Revision ID: ec8886111154
Revises: 2a3b4c5d6e7f
Create Date: 2026-01-25 07:22:17.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "ec8886111154"
down_revision: Union[str, None] = "2a3b4c5d6e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Extraction jobs table
    op.create_table(
        "extraction_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("pybase.users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, default="pending", index=True),
        sa.Column("extraction_format", sa.String(20), nullable=False),
        sa.Column("file_path", sa.String(2048), nullable=True),
        sa.Column("result_path", sa.String(2048), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, default=0),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("processed_items", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_items", sa.Integer(), nullable=False, default=0),
        sa.Column("retry_count", sa.Integer(), nullable=False, default=0),
        sa.Column("max_retries", sa.Integer(), nullable=False, default=3),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "celery_task_id",
            sa.String(255),
            nullable=True,
            unique=True,
            index=True,
        ),
        sa.Column("options", sa.Text(), nullable=True, default="{}"),
        sa.Column("results", sa.Text(), nullable=True, default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_stack_trace", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="pybase",
    )

    # Create composite indexes for common query patterns
    op.create_index(
        "ix_extraction_jobs_status_created",
        "extraction_jobs",
        ["status", "created_at"],
        schema="pybase",
    )
    op.create_index(
        "ix_extraction_jobs_user_created",
        "extraction_jobs",
        ["user_id", "created_at"],
        schema="pybase",
    )
    op.create_index(
        "ix_extraction_jobs_format_status",
        "extraction_jobs",
        ["extraction_format", "status"],
        schema="pybase",
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table("extraction_jobs", schema="pybase")
