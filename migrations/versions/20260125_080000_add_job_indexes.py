"""Add database indexes for common job queries

Revision ID: 3d4e5f6a7b8c
Revises: ec8886111154
Create Date: 2026-01-25 08:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "3d4e5f6a7b8c"
down_revision: Union[str, None] = "ec8886111154"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add single-column index on created_at for time-based queries
    op.create_index(
        "ix_extraction_jobs_created_at",
        "extraction_jobs",
        ["created_at"],
        schema="pybase",
    )

    # Add composite index for user status queries
    op.create_index(
        "ix_extraction_jobs_user_status",
        "extraction_jobs",
        ["user_id", "status"],
        schema="pybase",
    )

    # Add composite index for status and user queries
    op.create_index(
        "ix_extraction_jobs_status_user",
        "extraction_jobs",
        ["status", "user_id"],
        schema="pybase",
    )

    # Add composite index for user, status, and created_at
    op.create_index(
        "ix_extraction_jobs_user_status_created",
        "extraction_jobs",
        ["user_id", "status", "created_at"],
        schema="pybase",
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(
        "ix_extraction_jobs_user_status_created",
        table_name="extraction_jobs",
        schema="pybase",
    )
    op.drop_index(
        "ix_extraction_jobs_status_user",
        table_name="extraction_jobs",
        schema="pybase",
    )
    op.drop_index(
        "ix_extraction_jobs_user_status",
        table_name="extraction_jobs",
        schema="pybase",
    )
    op.drop_index(
        "ix_extraction_jobs_created_at",
        table_name="extraction_jobs",
        schema="pybase",
    )
