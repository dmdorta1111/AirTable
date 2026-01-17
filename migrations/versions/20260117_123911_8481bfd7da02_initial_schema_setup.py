"""Initial schema setup

Revision ID: 8481bfd7da02
Revises:
Create Date: 2026-01-17 12:39:11.733986+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "8481bfd7da02"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create dedicated schema for PyBase
    op.execute("CREATE SCHEMA IF NOT EXISTS pybase")

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("verification_token", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_reset_token", sa.String(255), nullable=True),
        sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferences", sa.Text(), nullable=True, default="{}"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="pybase",
    )
    op.create_index("ix_users_email_active", "users", ["email", "is_active"], schema="pybase")

    # API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("pybase.users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("hashed_key", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("scopes", sa.Text(), nullable=True, default="[]"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(45), nullable=True),
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
    op.create_index("ix_api_keys_prefix", "api_keys", ["key_prefix"], schema="pybase")
    op.create_index(
        "ix_api_keys_user_active", "api_keys", ["user_id", "is_active"], schema="pybase"
    )

    # Workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(),
            sa.ForeignKey("pybase.users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("settings", sa.Text(), nullable=True, default="{}"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="pybase",
    )

    # Workspace members table
    op.create_table(
        "workspace_members",
        sa.Column(
            "workspace_id",
            sa.String(),
            sa.ForeignKey("pybase.workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("pybase.users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(50), nullable=False, default="viewer"),
        sa.Column(
            "invited_by_id",
            sa.String(),
            sa.ForeignKey("pybase.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "invited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_workspace_members_workspace", "workspace_members", ["workspace_id"], schema="pybase"
    )
    op.create_index("ix_workspace_members_user", "workspace_members", ["user_id"], schema="pybase")
    op.execute(
        "ALTER TABLE pybase.workspace_members ADD CONSTRAINT uq_workspace_member UNIQUE (workspace_id, user_id)"
    )

    # Bases table
    op.create_table(
        "bases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(),
            sa.ForeignKey("pybase.workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, default=0),
        sa.Column("settings", sa.Text(), nullable=True, default="{}"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="pybase",
    )
    op.create_index("ix_bases_workspace_name", "bases", ["workspace_id", "name"], schema="pybase")
    op.create_index(
        "ix_bases_workspace_position", "bases", ["workspace_id", "position"], schema="pybase"
    )

    # Tables table
    op.create_table(
        "tables",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "base_id",
            sa.String(),
            sa.ForeignKey("pybase.bases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, default=0),
        sa.Column("settings", sa.Text(), nullable=True, default="{}"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="pybase",
    )
    op.create_index("ix_tables_base_name", "tables", ["base_id", "name"], schema="pybase")
    op.create_index("ix_tables_base_position", "tables", ["base_id", "position"], schema="pybase")

    # Fields table
    op.create_table(
        "fields",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "table_id",
            sa.String(),
            sa.ForeignKey("pybase.tables.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, default=0),
        sa.Column("options", sa.Text(), nullable=True, default="{}"),
        sa.Column("settings", sa.Text(), nullable=True, default="{}"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="pybase",
    )
    op.create_index("ix_fields_table", "fields", ["table_id"], schema="pybase")
    op.create_index("ix_fields_table_position", "fields", ["table_id", "position"], schema="pybase")

    # Records table
    op.create_table(
        "records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "table_id",
            sa.String(),
            sa.ForeignKey("pybase.tables.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("data", sa.JSON(), nullable=False, default="{}"),
        sa.Column(
            "created_by_id",
            sa.String(),
            sa.ForeignKey("pybase.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "last_modified_by_id",
            sa.String(),
            sa.ForeignKey("pybase.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="pybase",
    )
    op.create_index("ix_records_table", "records", ["table_id"], schema="pybase")
    op.create_index(
        "ix_records_table_created", "records", ["table_id", "created_at"], schema="pybase"
    )
    op.create_index("ix_records_created_by", "records", ["created_by_id"], schema="pybase")

    # Migration tables created successfully


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop tables in reverse order
    op.drop_table("api_keys", schema="pybase")
    op.drop_table("users", schema="pybase")
    op.execute("DROP SCHEMA IF EXISTS pybase")
