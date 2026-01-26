"""Add records cursor index for keyset pagination

Revision ID: 001_add_records_cursor_index
Revises: 2a3b4c5d6e7f
Create Date: 2026-01-25 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = '001_add_records_cursor_index'
down_revision: Union[str, None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create composite index on (table_id, created_at) for cursor-based pagination
    # This index optimizes queries that filter by table_id and order by created_at
    # which is essential for efficient keyset pagination on large datasets
    op.create_index(
        'table_id_created_at',
        'records',
        ['table_id', 'created_at'],
        unique=False,
        schema='pybase',
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop the cursor pagination index
    op.drop_index('table_id_created_at', table_name='records', schema='pybase')
