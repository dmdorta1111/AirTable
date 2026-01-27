"""
SAML configuration model.

Handles SAML 2.0 Identity Provider settings for SSO authentication.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from pybase.db.base import BaseModel

if TYPE_CHECKING:
    pass


class SAMLConfig(BaseModel):
    """
    SAML 2.0 configuration model for Identity Provider integration.

    Stores IdP settings, certificates, and attribute mappings for SAML SSO.
    """

    # Configuration name and status
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Identity Provider (IdP) settings
    idp_entity_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    idp_sso_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    idp_slo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    idp_x509_cert: Mapped[str] = mapped_column(
        Text,  # X.509 certificate in PEM format
        nullable=False,
    )

    # Service Provider (SP) settings
    sp_entity_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    sp_acs_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    sp_slo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Security settings
    name_id_format: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    )

    # Attribute mappings (JSON stored as text)
    # Maps SAML attributes to user fields: {"email": "email", "name": "displayName"}
    attribute_mapping: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default='{"email": "email", "name": "name"}',
    )

    # JIT (Just-In-Time) provisioning
    jit_provisioning_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Role/Group mapping from SAML attributes
    # Maps SAML groups/roles to user roles: {"Admin": ["admin"], "User": ["user"]}
    role_mapping: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # SAML attribute name for groups/roles
    group_attribute: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default="groups",
    )

    # Indexes
    __table_args__ = (
        Index("ix_saml_configs_idp_entity_id", "idp_entity_id"),
        Index("ix_saml_configs_enabled_default", "is_enabled", "is_default"),
    )

    def __repr__(self) -> str:
        return f"<SAMLConfig {self.name} ({self.idp_entity_id})>"
