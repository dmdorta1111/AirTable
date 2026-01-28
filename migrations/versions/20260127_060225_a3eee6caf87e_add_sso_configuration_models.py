"""Add SSO configuration models

Revision ID: a3eee6caf87e
Revises: a4caca2d53d6
Create Date: 2026-01-27 06:02:25.837225+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = "a3eee6caf87e"
down_revision: Union[str, None] = "a4caca2d53d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create SAML configs table
    op.create_table(
        "saml_configs",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("idp_entity_id", sa.String(length=500), nullable=False),
        sa.Column("idp_sso_url", sa.String(length=500), nullable=False),
        sa.Column("idp_slo_url", sa.String(length=500), nullable=True),
        sa.Column("idp_x509_cert", sa.Text(), nullable=False),
        sa.Column("sp_entity_id", sa.String(length=500), nullable=False),
        sa.Column("sp_acs_url", sa.String(length=500), nullable=False),
        sa.Column("sp_slo_url", sa.String(length=500), nullable=True),
        sa.Column("name_id_format", sa.String(length=255), nullable=False),
        sa.Column("attribute_mapping", sa.Text(), nullable=True),
        sa.Column("jit_provisioning_enabled", sa.Boolean(), nullable=False),
        sa.Column("role_mapping", sa.Text(), nullable=True),
        sa.Column("group_attribute", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="pybase",
    )
    op.create_index(
        "ix_saml_configs_idp_entity_id",
        "saml_configs",
        ["idp_entity_id"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_saml_configs_enabled_default",
        "saml_configs",
        ["is_enabled", "is_default"],
        unique=False,
        schema="pybase",
    )

    # Create OIDC configs table
    op.create_table(
        "oidc_configs",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("issuer_url", sa.String(length=500), nullable=False),
        sa.Column("authorization_endpoint", sa.String(length=500), nullable=False),
        sa.Column("token_endpoint", sa.String(length=500), nullable=False),
        sa.Column("jwks_uri", sa.String(length=500), nullable=False),
        sa.Column("userinfo_endpoint", sa.String(length=500), nullable=True),
        sa.Column("end_session_endpoint", sa.String(length=500), nullable=True),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret", sa.String(length=500), nullable=False),
        sa.Column("scope", sa.String(length=500), nullable=False),
        sa.Column("response_type", sa.String(length=50), nullable=False),
        sa.Column("response_mode", sa.String(length=50), nullable=True),
        sa.Column("claim_mapping", sa.Text(), nullable=True),
        sa.Column("jit_provisioning_enabled", sa.Boolean(), nullable=False),
        sa.Column("role_mapping", sa.Text(), nullable=True),
        sa.Column("group_claim", sa.String(length=255), nullable=True),
        sa.Column("validate_signature", sa.Boolean(), nullable=False),
        sa.Column("validate_issuer", sa.Boolean(), nullable=False),
        sa.Column("validate_audience", sa.Boolean(), nullable=False),
        sa.Column("allowed_audiences", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="pybase",
    )
    op.create_index(
        "ix_oidc_configs_issuer_url",
        "oidc_configs",
        ["issuer_url"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_oidc_configs_enabled_default",
        "oidc_configs",
        ["is_enabled", "is_default"],
        unique=False,
        schema="pybase",
    )

    # Create user identities table
    # NOTE: Foreign key to pybase.users temporarily disabled due to missing users table
    # TODO: Add foreign key constraint after users table is properly created
    op.create_table(
        "user_identities",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("provider_type", sa.String(length=20), nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("subject_id", sa.String(length=500), nullable=False),
        sa.Column("issuer", sa.String(length=500), nullable=False),
        sa.Column("attributes", sa.Text(), nullable=True),
        sa.Column("profile_data", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("last_auth_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="pybase",
    )
    op.create_index(
        "ix_user_identities_provider_subject",
        "user_identities",
        ["provider_type", "subject_id", "issuer"],
        unique=True,
        schema="pybase",
    )
    op.create_index(
        "ix_user_identities_user_id",
        "user_identities",
        ["user_id"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_user_identities_email",
        "user_identities",
        ["email"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_user_identities_config_id",
        "user_identities",
        ["config_id"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_user_identities_provider_type",
        "user_identities",
        ["provider_type"],
        unique=False,
        schema="pybase",
    )
    op.create_index(
        "ix_user_identities_subject_id",
        "user_identities",
        ["subject_id"],
        unique=False,
        schema="pybase",
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop user identities table
    op.drop_index(
        "ix_user_identities_subject_id", table_name="user_identities", schema="pybase"
    )
    op.drop_index(
        "ix_user_identities_provider_type", table_name="user_identities", schema="pybase"
    )
    op.drop_index(
        "ix_user_identities_config_id", table_name="user_identities", schema="pybase"
    )
    op.drop_index(
        "ix_user_identities_email", table_name="user_identities", schema="pybase"
    )
    op.drop_index(
        "ix_user_identities_user_id", table_name="user_identities", schema="pybase"
    )
    op.drop_index(
        "ix_user_identities_provider_subject",
        table_name="user_identities",
        schema="pybase",
    )
    op.drop_table("user_identities", schema="pybase")

    # Drop OIDC configs table
    op.drop_index(
        "ix_oidc_configs_enabled_default", table_name="oidc_configs", schema="pybase"
    )
    op.drop_index("ix_oidc_configs_issuer_url", table_name="oidc_configs", schema="pybase")
    op.drop_table("oidc_configs", schema="pybase")

    # Drop SAML configs table
    op.drop_index(
        "ix_saml_configs_enabled_default", table_name="saml_configs", schema="pybase"
    )
    op.drop_index(
        "ix_saml_configs_idp_entity_id", table_name="saml_configs", schema="pybase"
    )
    op.drop_table("saml_configs", schema="pybase")
