"""Add database indexes for bulk job query patterns

Revision ID: c1d2e3f4g5h6
Revises: b2c3d4e5f6g7
Create Date: 2026-01-27 06:03:55.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add composite index on status and next_retry_at for retry queue queries
    # This supports queries for stuck job recovery and retry scheduling
    op.create_index(
        "ix_extraction_jobs_status_retry",
        "extraction_jobs",
        ["status", "next_retry_at"],
        schema="pybase",
    )

    # Add index on file_url for bulk job file lookups
    # This supports queries like get_job_by_file_url used in bulk job status checks
    op.create_index(
        "ix_extraction_jobs_file_url",
        "extraction_jobs",
        ["file_url"],
        schema="pybase",
    )

    # Add index on cloud_file_id for record/attachment-based job queries
    # This supports queries filtering jobs by associated cloud files
    op.create_index(
        "ix_extraction_jobs_cloud_file",
        "extraction_jobs",
        ["cloud_file_id"],
        schema="pybase",
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(
        "ix_extraction_jobs_cloud_file",
        table_name="extraction_jobs",
        schema="pybase",
    )
    op.drop_index(
        "ix_extraction_jobs_file_url",
        table_name="extraction_jobs",
        schema="pybase",
    )
    op.drop_index(
        "ix_extraction_jobs_status_retry",
        table_name="extraction_jobs",
        schema="pybase",
    )
