"""Add unique constraints table

Revision ID: 3efa5ff2e3cf
Revises: 001_add_records_cursor_index
Create Date: 2026-01-25 12:21:10.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '3efa5ff2e3cf'
down_revision: Union[str, None] = '001_add_records_cursor_index'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create unique_constraints table in pybase schema
    op.create_table(
        'unique_constraints',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            'field_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('pybase.fields.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'active'")),
        sa.Column('case_sensitive', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            onupdate=sa.text('NOW()'),
            nullable=False,
        ),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # Create indexes
    op.create_index(
        'ix_unique_constraints_field_id',
        'unique_constraints',
        ['field_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_unique_constraints_status',
        'unique_constraints',
        ['status'],
        unique=False,
        schema='pybase',
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes first
    op.drop_index('ix_unique_constraints_status', table_name='unique_constraints', schema='pybase')
    op.drop_index('ix_unique_constraints_field_id', table_name='unique_constraints', schema='pybase')

    # Drop table
    op.drop_table('unique_constraints', schema='pybase')
