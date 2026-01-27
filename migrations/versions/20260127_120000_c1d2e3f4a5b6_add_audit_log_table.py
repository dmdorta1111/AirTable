"""Add audit_log table for comprehensive audit logging

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6g7
Create Date: 2026-01-27 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Audit logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        # Actor information
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("pybase.users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("user_email", sa.String(255), nullable=True, index=True),
        # Action details
        sa.Column("action", sa.String(50), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=False, index=True),
        sa.Column("resource_id", sa.String(), nullable=True, index=True),
        # Table context
        sa.Column("table_id", sa.String(), nullable=True, index=True),
        # Data changes
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        # Request context
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True, index=True),
        # Tamper-evident storage
        sa.Column("integrity_hash", sa.String(64), nullable=False, index=True),
        sa.Column("previous_log_hash", sa.String(64), nullable=True),
        # Additional context
        sa.Column("meta", sa.Text(), nullable=True, default="{}"),
        # Timestamps
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
        schema="pybase",
    )

    # Create composite indexes for common query patterns
    op.create_index(
        "ix_audit_logs_user_action", "audit_logs", ["user_id", "action"], schema="pybase"
    )
    op.create_index(
        "ix_audit_logs_table_action", "audit_logs", ["table_id", "action"], schema="pybase"
    )
    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id"],
        schema="pybase",
    )
    op.create_index(
        "ix_audit_logs_created_at", "audit_logs", ["created_at"], schema="pybase"
    )
    op.create_index(
        "ix_audit_logs_integrity", "audit_logs", ["integrity_hash"], schema="pybase"
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table("audit_logs", schema="pybase")
