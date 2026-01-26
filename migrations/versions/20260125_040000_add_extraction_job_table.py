"""Add extraction_job table for CAD/PDF extraction job tracking

This migration adds the ExtractionJob model which replaces the in-memory
job storage in extraction.py with persistent database tracking.

Revision ID: 5e6f7g8h9i0j
Revises: 4d5e6f7g8h9i
Create Date: 2026-01-25 04:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "5e6f7g8h9i0j"
down_revision: Union[str, None] = "4d5e6f7g8h9i"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create extraction_jobs table."""
    op.create_table(
        "extraction_jobs",
        # Primary key
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # File identification
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_url", sa.String(2048), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        # Optional linking to Record.data attachment (records table not in current schema)
        # sa.Column("record_id", sa.UUID(as_uuid=False), nullable=True),
        # sa.Column("field_id", sa.String(255), nullable=True),
        # sa.Column("attachment_id", sa.String(255), nullable=True),
        # Linking to CloudFiles table instead
        sa.Column("cloud_file_id", sa.Integer(), nullable=True),
        # Job tracking
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("options", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Retry logic
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        # Timing
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # User tracking
        sa.Column("created_by_id", sa.UUID(as_uuid=False), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Foreign keys
        # Note: users table not in pybase schema, omitting FK for created_by_id
        # sa.ForeignKeyConstraint(
        #     ["created_by_id"],
        #     ["pybase.users.id"],
        #     name="fk_extraction_jobs_created_by_id",
        #     ondelete="SET NULL",
        # ),
        schema="pybase",
    )

    # Create indexes for common query patterns
    op.create_index(
        "ix_extraction_jobs_status",
        "extraction_jobs",
        ["status"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_extraction_jobs_status_retry",
        "extraction_jobs",
        ["status", "next_retry_at"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_extraction_jobs_file_url",
        "extraction_jobs",
        ["file_url"],
        unique=False,
        schema="pybase",
    )
    # Index for CloudFiles linking (replaces record_id index)
    op.create_index(
        "ix_extraction_jobs_cloud_file",
        "extraction_jobs",
        ["cloud_file_id"],
        unique=False,
        schema="pybase",
    )


def downgrade() -> None:
    """Drop extraction_jobs table."""
    op.drop_index("ix_extraction_jobs_cloud_file", table_name="extraction_jobs", schema="pybase")
    op.drop_index("ix_extraction_jobs_file_url", table_name="extraction_jobs", schema="pybase")
    op.drop_index("ix_extraction_jobs_status_retry", table_name="extraction_jobs", schema="pybase")
    op.drop_index("ix_extraction_jobs_status", table_name="extraction_jobs", schema="pybase")
    op.drop_table("extraction_jobs", schema="pybase")
