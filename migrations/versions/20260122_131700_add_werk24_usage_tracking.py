"""Add Werk24 usage tracking

Revision ID: 2a3b4c5d6e7f
Revises: 8481bfd7da02
Create Date: 2026-01-22 13:17:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = '8481bfd7da02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create werk24_usages table in pybase schema
    op.create_table(
        'werk24_usages',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('request_type', sa.String(length=100), nullable=False),
        sa.Column('ask_types', sa.Text(), nullable=False),
        sa.Column('source_file', sa.String(length=500), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('api_calls_count', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('dimensions_extracted', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('gdts_extracted', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('materials_extracted', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('threads_extracted', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('api_key_used', sa.String(length=50), nullable=True),
        sa.Column('request_ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('cost_units', sa.Float(), nullable=True),
        sa.Column('quota_remaining', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
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
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['pybase.users.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'],
            ['pybase.workspaces.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # Create indexes
    op.create_index(
        'ix_werk24_usages_user_id',
        'werk24_usages',
        ['user_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_werk24_usages_workspace_id',
        'werk24_usages',
        ['workspace_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_werk24_usage_user_created',
        'werk24_usages',
        ['user_id', 'created_at'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_werk24_usage_workspace_created',
        'werk24_usages',
        ['workspace_id', 'created_at'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_werk24_usage_success',
        'werk24_usages',
        ['success'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_werk24_usage_request_type',
        'werk24_usages',
        ['request_type'],
        unique=False,
        schema='pybase',
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes first
    op.drop_index('ix_werk24_usage_request_type', table_name='werk24_usages', schema='pybase')
    op.drop_index('ix_werk24_usage_success', table_name='werk24_usages', schema='pybase')
    op.drop_index('ix_werk24_usage_workspace_created', table_name='werk24_usages', schema='pybase')
    op.drop_index('ix_werk24_usage_user_created', table_name='werk24_usages', schema='pybase')
    op.drop_index('ix_werk24_usages_workspace_id', table_name='werk24_usages', schema='pybase')
    op.drop_index('ix_werk24_usages_user_id', table_name='werk24_usages', schema='pybase')

    # Drop table
    op.drop_table('werk24_usages', schema='pybase')
