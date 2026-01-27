"""Add custom reports tables

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-27 14:00:00.000000+00:00
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

    # Create report_templates table first (no foreign keys to other report tables)
    op.create_table(
        'report_templates',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('base_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column('template_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
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
            ['base_id'],
            ['pybase.bases.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['created_by_id'],
            ['pybase.users.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # Create indexes for report_templates table
    op.create_index(
        'ix_report_templates_base',
        'report_templates',
        ['base_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_templates_category',
        'report_templates',
        ['category'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_templates_active',
        'report_templates',
        ['is_active', 'is_system'],
        unique=False,
        schema='pybase',
    )

    # Create custom_reports table
    op.create_table(
        'custom_reports',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('base_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('format', sa.String(length=50), nullable=False, server_default=sa.text("'pdf'")),
        sa.Column('layout_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('style_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('frequency', sa.String(length=50), nullable=False, server_default=sa.text("'manual'")),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('schedule_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('delivery_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('export_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('max_runs_per_day', sa.Integer(), nullable=False, server_default=sa.text('10')),
        sa.Column('notify_on_success', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('notify_on_failure', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('notification_email', sa.String(length=255), nullable=True),
        sa.Column('total_runs', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('successful_runs', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('failed_runs', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('average_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('last_output_path', sa.String(length=500), nullable=True),
        sa.Column('last_output_size_bytes', sa.Integer(), nullable=True),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('parameters_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
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
            ['base_id'],
            ['pybase.bases.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['created_by_id'],
            ['pybase.users.id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['template_id'],
            ['pybase.report_templates.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # Create indexes for custom_reports table
    op.create_index(
        'ix_custom_reports_base',
        'custom_reports',
        ['base_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_reports_created_by',
        'custom_reports',
        ['created_by_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_reports_template',
        'custom_reports',
        ['template_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_reports_frequency',
        'custom_reports',
        ['frequency'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_reports_active',
        'custom_reports',
        ['is_active', 'is_paused', 'is_published'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_reports_next_run',
        'custom_reports',
        ['next_run_at'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_reports_last_run',
        'custom_reports',
        ['last_run_at'],
        unique=False,
        schema='pybase',
    )

    # Create report_sections table
    op.create_table(
        'report_sections',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('section_type', sa.String(length=50), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('section_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('style_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
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
            ['report_id'],
            ['pybase.custom_reports.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # Create indexes for report_sections table
    op.create_index(
        'ix_report_sections_report',
        'report_sections',
        ['report_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_sections_order',
        'report_sections',
        ['report_id', 'order'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_sections_type',
        'report_sections',
        ['report_id', 'section_type'],
        unique=False,
        schema='pybase',
    )

    # Create report_data_sources table
    op.create_table(
        'report_data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tables_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('fields_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('filters_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('sort_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('parameters_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
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
            ['report_id'],
            ['pybase.custom_reports.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # Create indexes for report_data_sources table
    op.create_index(
        'ix_report_data_sources_report',
        'report_data_sources',
        ['report_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_data_sources_name',
        'report_data_sources',
        ['report_id', 'name'],
        unique=False,
        schema='pybase',
    )

    # Create custom_report_schedules table
    op.create_table(
        'custom_report_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('triggered_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('output_path', sa.String(length=500), nullable=True),
        sa.Column('output_size_bytes', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_status', sa.String(length=100), nullable=True),
        sa.Column('recipients_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('parameters_used', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
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
            ['report_id'],
            ['pybase.custom_reports.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['triggered_by_id'],
            ['pybase.users.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # Create indexes for custom_report_schedules table
    op.create_index(
        'ix_custom_report_schedules_report',
        'custom_report_schedules',
        ['report_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_report_schedules_status',
        'custom_report_schedules',
        ['status'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_report_schedules_scheduled_at',
        'custom_report_schedules',
        ['scheduled_at'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_report_schedules_report_status',
        'custom_report_schedules',
        ['report_id', 'status'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_custom_report_schedules_report_scheduled',
        'custom_report_schedules',
        ['report_id', 'scheduled_at'],
        unique=False,
        schema='pybase',
    )


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop custom_report_schedules table and indexes
    op.drop_index(
        'ix_custom_report_schedules_report_scheduled',
        table_name='custom_report_schedules',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_report_schedules_report_status',
        table_name='custom_report_schedules',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_report_schedules_scheduled_at',
        table_name='custom_report_schedules',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_report_schedules_status',
        table_name='custom_report_schedules',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_report_schedules_report',
        table_name='custom_report_schedules',
        schema='pybase'
    )
    op.drop_table('custom_report_schedules', schema='pybase')

    # Drop report_data_sources table and indexes
    op.drop_index(
        'ix_report_data_sources_name',
        table_name='report_data_sources',
        schema='pybase'
    )
    op.drop_index(
        'ix_report_data_sources_report',
        table_name='report_data_sources',
        schema='pybase'
    )
    op.drop_table('report_data_sources', schema='pybase')

    # Drop report_sections table and indexes
    op.drop_index(
        'ix_report_sections_type',
        table_name='report_sections',
        schema='pybase'
    )
    op.drop_index(
        'ix_report_sections_order',
        table_name='report_sections',
        schema='pybase'
    )
    op.drop_index(
        'ix_report_sections_report',
        table_name='report_sections',
        schema='pybase'
    )
    op.drop_table('report_sections', schema='pybase')

    # Drop custom_reports table and indexes
    op.drop_index(
        'ix_custom_reports_last_run',
        table_name='custom_reports',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_reports_next_run',
        table_name='custom_reports',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_reports_active',
        table_name='custom_reports',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_reports_frequency',
        table_name='custom_reports',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_reports_template',
        table_name='custom_reports',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_reports_created_by',
        table_name='custom_reports',
        schema='pybase'
    )
    op.drop_index(
        'ix_custom_reports_base',
        table_name='custom_reports',
        schema='pybase'
    )
    op.drop_table('custom_reports', schema='pybase')

    # Drop report_templates table and indexes
    op.drop_index(
        'ix_report_templates_active',
        table_name='report_templates',
        schema='pybase'
    )
    op.drop_index(
        'ix_report_templates_category',
        table_name='report_templates',
        schema='pybase'
    )
    op.drop_index(
        'ix_report_templates_base',
        table_name='report_templates',
        schema='pybase'
    )
    op.drop_table('report_templates', schema='pybase')
