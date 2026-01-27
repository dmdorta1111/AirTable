"""Add deleted_by_id field to records table

This migration adds the deleted_by_id field to track which user deleted a record.
This is part of the soft delete and trash bin feature implementation.

Revision ID: c4d5e6f7g8h9
Revises: b2c3d4e5f6g7
Create Date: 2026-01-27 05:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = 'c4d5e6f7g8h9'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add deleted_by_id column to records table
    op.add_column(
        'records',
        sa.Column(
            'deleted_by_id',
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
        schema='pybase',
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_records_deleted_by_id',
        'records',
        'users',
        ['deleted_by_id'],
        ['id'],
        ondelete='SET NULL',
        schema='pybase',
        source_schema='pybase',
        referent_schema='pybase',
    )

    # Create index for deleted_by_id
    op.create_index(
        'ix_records_deleted_by',
        'records',
        ['deleted_by_id'],
        unique=False,
        schema='pybase',
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop index first
    op.drop_index('ix_records_deleted_by', table_name='records', schema='pybase')

    # Drop foreign key constraint
    op.drop_constraint(
        'fk_records_deleted_by_id',
        'records',
        schema='pybase',
        type_='foreignkey',
    )

    # Drop column
    op.drop_column('records', 'deleted_by_id', schema='pybase')
