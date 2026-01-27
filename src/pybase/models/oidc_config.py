"""
OIDC configuration model.

Handles OpenID Connect Identity Provider settings for SSO authentication.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from pybase.db.base import BaseModel

if TYPE_CHECKING:
    pass


class OIDCConfig(BaseModel):
    """
    OpenID Connect configuration model for Identity Provider integration.

    Stores IdP settings, client credentials, and claim mappings for OIDC SSO.
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

    # Identity Provider (IdP) discovery endpoint
    issuer_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    # OpenID Connect endpoints (auto-discovered from issuer or manually configured)
    authorization_endpoint: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    token_endpoint: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    jwks_uri: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    userinfo_endpoint: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    end_session_endpoint: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Client credentials
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    client_secret: Mapped[str] = mapped_column(
        String(500),  # Encrypted client secret
        nullable=False,
    )

    # OAuth2/OIDC configuration
    scope: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="openid email profile",
    )
    response_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="code",
    )
    response_mode: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="query",
    )

    # Claim mappings (JSON stored as text)
    # Maps OIDC claims to user fields: {"email": "email", "name": "name", "groups": "groups"}
    claim_mapping: Mapped[str | None] = mapped_column(
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

    # Role/Group mapping from OIDC claims
    # Maps OIDC groups/roles to user roles: {"Admin": ["admin"], "User": ["user"]}
    role_mapping: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # OIDC claim name for groups/roles
    group_claim: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default="groups",
    )

    # Token validation settings
    validate_signature: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    validate_issuer: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    validate_audience: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Additional token audience validation (optional)
    allowed_audiences: Mapped[str | None] = mapped_column(
        Text,  # JSON array of audience strings
        nullable=True,
        default="[]",
    )

    # Indexes
    __table_args__ = (
        Index("ix_oidc_configs_issuer_url", "issuer_url"),
        Index("ix_oidc_configs_enabled_default", "is_enabled", "is_default"),
    )

    def __repr__(self) -> str:
        return f"<OIDCConfig {self.name} ({self.issuer_url})>"
