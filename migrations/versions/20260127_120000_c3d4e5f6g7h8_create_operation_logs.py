"""Create operation_logs table for undo/redo functionality

This migration adds the OperationLog model which tracks all operations
for 24 hours to enable users to undo/redo changes. Operations are limited
to 100 per user with automatic cleanup of old entries.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-27 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create operation_logs table."""
    op.create_table(
        "operation_logs",
        # Primary key (inherited from BaseModel)
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # Foreign key to user who performed the operation
        # Note: FK constraint not added here as users table may not exist yet in all environments
        # The FK will be enforced at application level and can be added via separate migration if needed
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        # Operation metadata
        sa.Column("operation_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        # Operation data (JSON stored as text)
        sa.Column("before_data", sa.Text(), nullable=True),
        sa.Column("after_data", sa.Text(), nullable=True),
        # Timestamps (inherited from BaseModel)
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
        schema="pybase",
    )

    # Add comment for documentation
    op.execute(
        "COMMENT ON TABLE pybase.operation_logs IS "
        "'Stores operation history for undo/redo functionality. Tracks operations for 24 hours.'"
    )

    # Create indexes for common query patterns
    op.create_index(
        "ix_operation_logs_user",
        "operation_logs",
        ["user_id"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_operation_logs_user_created",
        "operation_logs",
        ["user_id", "created_at"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_operation_logs_operation",
        "operation_logs",
        ["operation_type"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_operation_logs_entity",
        "operation_logs",
        ["entity_type", "entity_id"],
        unique=False,
        schema="pybase",
    )


def downgrade() -> None:
    """Drop operation_logs table."""
    # Drop indexes first
    op.drop_index("ix_operation_logs_entity", table_name="operation_logs", schema="pybase")
    op.drop_index("ix_operation_logs_operation", table_name="operation_logs", schema="pybase")
    op.drop_index("ix_operation_logs_user_created", table_name="operation_logs", schema="pybase")
    op.drop_index("ix_operation_logs_user", table_name="operation_logs", schema="pybase")

    # Drop table
    op.drop_table("operation_logs", schema="pybase")
