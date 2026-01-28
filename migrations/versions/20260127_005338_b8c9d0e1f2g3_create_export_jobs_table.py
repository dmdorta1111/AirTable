"""Create export_jobs table for bulk data export tracking

Revision ID: b8c9d0e1f2g3
Revises: a4caca2d53d6
Create Date: 2026-01-27 00:53:38.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = 'b8c9d0e1f2g3'
down_revision: Union[str, None] = 'a4caca2d53d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Export jobs table
    op.create_table(
        'export_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('pybase.users.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', index=True),
        sa.Column('export_format', sa.String(20), nullable=False, comment='Format: csv, xlsx, json, xml'),
        sa.Column(
            'table_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('pybase.tables.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'view_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('pybase.views.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column('file_path', sa.String(2048), nullable=True, comment='Path to exported file or S3 location'),
        sa.Column('download_url', sa.String(2048), nullable=True, comment='Temporary download URL for exported file'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0', comment='Progress percentage (0-100)'),
        sa.Column('total_records', sa.Integer(), nullable=True, comment='Total records to export'),
        sa.Column('processed_records', sa.Integer(), nullable=False, server_default='0', comment='Number of records successfully exported'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0', comment='Number of retry attempts'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3', comment='Maximum number of retry attempts'),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp of last retry attempt'),
        sa.Column(
            'celery_task_id',
            sa.String(255),
            nullable=True,
            unique=True,
            index=True,
            comment='Celery task ID for worker coordination',
        ),
        sa.Column('options', sa.Text(), nullable=True, server_default='{}', comment='Export options (field_ids, flatten_linked_records, include_attachments, etc.)'),
        sa.Column('results', sa.Text(), nullable=True, server_default='{}', comment='Export results (record_count, file_size, attachment_count, etc.)'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Human-readable error message'),
        sa.Column('error_stack_trace', sa.Text(), nullable=True, comment='Full error stack trace for debugging'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True, comment='Total execution duration in milliseconds'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Download link expiration time'),
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
        schema='pybase',
    )

    # Create composite indexes for common query patterns
    op.create_index(
        'ix_export_jobs_status_created',
        'export_jobs',
        ['status', 'created_at'],
        schema='pybase',
    )
    op.create_index(
        'ix_export_jobs_user_created',
        'export_jobs',
        ['user_id', 'created_at'],
        schema='pybase',
    )
    op.create_index(
        'ix_export_jobs_table_status',
        'export_jobs',
        ['table_id', 'status'],
        schema='pybase',
    )
    op.create_index(
        'ix_export_jobs_format_status',
        'export_jobs',
        ['export_format', 'status'],
        schema='pybase',
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index('ix_export_jobs_format_status', table_name='export_jobs', schema='pybase')
    op.drop_index('ix_export_jobs_table_status', table_name='export_jobs', schema='pybase')
    op.drop_index('ix_export_jobs_user_created', table_name='export_jobs', schema='pybase')
    op.drop_index('ix_export_jobs_status_created', table_name='export_jobs', schema='pybase')
    op.drop_table('export_jobs', schema='pybase')
