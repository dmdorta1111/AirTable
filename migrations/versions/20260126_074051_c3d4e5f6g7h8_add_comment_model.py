"""Add comment model

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-26 07:40:51.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create comments table in pybase schema
    op.create_table(
        'comments',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('record_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_edited', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
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
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['record_id'],
            ['pybase.records.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['pybase.users.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # Create indexes
    op.create_index(
        'ix_comments_record',
        'comments',
        ['record_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_comments_user',
        'comments',
        ['user_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_comments_record_created',
        'comments',
        ['record_id', 'created_at'],
        unique=False,
        schema='pybase',
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes first
    op.drop_index('ix_comments_record_created', table_name='comments', schema='pybase')
    op.drop_index('ix_comments_user', table_name='comments', schema='pybase')
    op.drop_index('ix_comments_record', table_name='comments', schema='pybase')

    # Drop table
    op.drop_table('comments', schema='pybase')
