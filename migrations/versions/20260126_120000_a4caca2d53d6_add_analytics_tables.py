"""Add analytics tables

Revision ID: a4caca2d53d6
Revises: 2a3b4c5d6e7f
Create Date: 2026-01-26 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = 'a4caca2d53d6'
down_revision: Union[str, None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create dashboards table
    op.create_table(
        'dashboards',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('base_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_personal', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('layout_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('settings', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('global_filters', sa.Text(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('icon', sa.String(length=100), nullable=True),
        sa.Column('template_id', sa.String(length=100), nullable=True),
        sa.Column('share_token', sa.String(length=255), nullable=True),
        sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('share_token'),
        schema='pybase',
    )

    # Create indexes for dashboards table
    op.create_index(
        'ix_dashboards_base_id',
        'dashboards',
        ['base_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_dashboards_base_name',
        'dashboards',
        ['base_id', 'name'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_dashboards_base_default',
        'dashboards',
        ['base_id', 'is_default'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_dashboards_share_token',
        'dashboards',
        ['share_token'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_dashboards_template',
        'dashboards',
        ['template_id'],
        unique=False,
        schema='pybase',
    )

    # Create dashboard_members table
    op.create_table(
        'dashboard_members',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('permission', sa.String(length=50), nullable=False, server_default=sa.text("'view'")),
        sa.Column('shared_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('shared_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
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
            ['dashboard_id'],
            ['pybase.dashboards.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['pybase.users.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['shared_by_id'],
            ['pybase.users.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dashboard_id', 'user_id', name='uq_dashboard_member'),
        schema='pybase',
    )

    # Create indexes for dashboard_members table
    op.create_index(
        'ix_dashboard_members_dashboard',
        'dashboard_members',
        ['dashboard_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_dashboard_members_user',
        'dashboard_members',
        ['user_id'],
        unique=False,
        schema='pybase',
    )

    # Create charts table
    op.create_table(
        'charts',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('table_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('chart_type', sa.String(length=50), nullable=False, server_default=sa.text("'bar'")),
        sa.Column('position', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('width', sa.Integer(), nullable=False, server_default=sa.text('6')),
        sa.Column('height', sa.Integer(), nullable=False, server_default=sa.text('4')),
        sa.Column('data_config', sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('filters', sa.Text(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column('sorts', sa.Text(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column('visual_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('axis_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('color_scheme', sa.String(length=50), nullable=True),
        sa.Column('drilldown_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('auto_refresh', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('refresh_interval', sa.Integer(), nullable=True),
        sa.Column('cache_duration', sa.Integer(), nullable=True),
        sa.Column('last_refreshed_at', sa.DateTime(timezone=True), nullable=True),
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
            ['dashboard_id'],
            ['pybase.dashboards.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['table_id'],
            ['pybase.tables.id'],
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

    # Create indexes for charts table
    op.create_index(
        'ix_charts_dashboard_id',
        'charts',
        ['dashboard_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_charts_table_id',
        'charts',
        ['table_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_charts_dashboard_position',
        'charts',
        ['dashboard_id', 'position'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_charts_table',
        'charts',
        ['table_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_charts_type',
        'charts',
        ['chart_type'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_charts_dashboard_type',
        'charts',
        ['dashboard_id', 'chart_type'],
        unique=False,
        schema='pybase',
    )

    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('base_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('format', sa.String(length=50), nullable=False, server_default=sa.text("'pdf'")),
        sa.Column('frequency', sa.String(length=50), nullable=False, server_default=sa.text("'manual'")),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('schedule_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('delivery_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('export_config', sa.Text(), nullable=True, server_default=sa.text("'{}'")),
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
            ['dashboard_id'],
            ['pybase.dashboards.id'],
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

    # Create indexes for reports table
    op.create_index(
        'ix_reports_base_id',
        'reports',
        ['base_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_reports_dashboard_id',
        'reports',
        ['dashboard_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_reports_base_dashboard',
        'reports',
        ['base_id', 'dashboard_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_reports_frequency',
        'reports',
        ['frequency'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_reports_active',
        'reports',
        ['is_active', 'is_paused'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_reports_next_run',
        'reports',
        ['next_run_at'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_reports_last_run',
        'reports',
        ['last_run_at'],
        unique=False,
        schema='pybase',
    )

    # Create report_schedules table
    op.create_table(
        'report_schedules',
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
            ['pybase.reports.id'],
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

    # Create indexes for report_schedules table
    op.create_index(
        'ix_report_schedules_report_id',
        'report_schedules',
        ['report_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_schedules_report',
        'report_schedules',
        ['report_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_schedules_status',
        'report_schedules',
        ['status'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_schedules_scheduled_at',
        'report_schedules',
        ['scheduled_at'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_schedules_report_status',
        'report_schedules',
        ['report_id', 'status'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_report_schedules_report_scheduled',
        'report_schedules',
        ['report_id', 'scheduled_at'],
        unique=False,
        schema='pybase',
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop report_schedules table and indexes
    op.drop_index('ix_report_schedules_report_scheduled', table_name='report_schedules', schema='pybase')
    op.drop_index('ix_report_schedules_report_status', table_name='report_schedules', schema='pybase')
    op.drop_index('ix_report_schedules_scheduled_at', table_name='report_schedules', schema='pybase')
    op.drop_index('ix_report_schedules_status', table_name='report_schedules', schema='pybase')
    op.drop_index('ix_report_schedules_report', table_name='report_schedules', schema='pybase')
    op.drop_index('ix_report_schedules_report_id', table_name='report_schedules', schema='pybase')
    op.drop_table('report_schedules', schema='pybase')

    # Drop reports table and indexes
    op.drop_index('ix_reports_last_run', table_name='reports', schema='pybase')
    op.drop_index('ix_reports_next_run', table_name='reports', schema='pybase')
    op.drop_index('ix_reports_active', table_name='reports', schema='pybase')
    op.drop_index('ix_reports_frequency', table_name='reports', schema='pybase')
    op.drop_index('ix_reports_base_dashboard', table_name='reports', schema='pybase')
    op.drop_index('ix_reports_dashboard_id', table_name='reports', schema='pybase')
    op.drop_index('ix_reports_base_id', table_name='reports', schema='pybase')
    op.drop_table('reports', schema='pybase')

    # Drop charts table and indexes
    op.drop_index('ix_charts_dashboard_type', table_name='charts', schema='pybase')
    op.drop_index('ix_charts_type', table_name='charts', schema='pybase')
    op.drop_index('ix_charts_table', table_name='charts', schema='pybase')
    op.drop_index('ix_charts_dashboard_position', table_name='charts', schema='pybase')
    op.drop_index('ix_charts_table_id', table_name='charts', schema='pybase')
    op.drop_index('ix_charts_dashboard_id', table_name='charts', schema='pybase')
    op.drop_table('charts', schema='pybase')

    # Drop dashboard_members table and indexes
    op.drop_index('ix_dashboard_members_user', table_name='dashboard_members', schema='pybase')
    op.drop_index('ix_dashboard_members_dashboard', table_name='dashboard_members', schema='pybase')
    op.drop_table('dashboard_members', schema='pybase')

    # Drop dashboards table and indexes
    op.drop_index('ix_dashboards_template', table_name='dashboards', schema='pybase')
    op.drop_index('ix_dashboards_share_token', table_name='dashboards', schema='pybase')
    op.drop_index('ix_dashboards_base_default', table_name='dashboards', schema='pybase')
    op.drop_index('ix_dashboards_base_name', table_name='dashboards', schema='pybase')
    op.drop_index('ix_dashboards_base_id', table_name='dashboards', schema='pybase')
    op.drop_table('dashboards', schema='pybase')
