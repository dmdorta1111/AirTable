"""
User Identity model.

Links SSO identities to local users for SAML and OIDC authentication.
"""

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel, utc_now

if TYPE_CHECKING:
    from pybase.models.user import User


class UserIdentity(BaseModel):
    """
    User Identity model for linking SSO identities to local users.

    Stores the mapping between external identity providers (SAML/OIDC)
    and local user accounts, enabling SSO authentication.
    """

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity provider type
    provider_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    # Values: "saml" or "oidc"

    # Configuration reference
    config_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        index=True,
    )
    # References SAMLConfig.id or OIDCConfig.id

    # Unique identifier from the identity provider
    # For SAML: NameID value
    # For OIDC: subject ('sub') claim
    subject_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    # Identity provider entity ID or issuer URL
    # For SAML: IdP entity ID
    # For OIDC: issuer URL
    issuer: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # IdP-specific attributes/claims (JSON stored as text)
    # Stores the original SAML attributes or OIDC claims
    attributes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # User profile data from IdP (JSON stored as text)
    # Snapshot of user data at time of linking
    profile_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Email from IdP (for reference)
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Display name from IdP
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Last authentication timestamp
    last_auth_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sso_identities",
        foreign_keys=[user_id],
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_user_identities_provider_subject",
            "provider_type",
            "subject_id",
            "issuer",
            unique=True,
        ),
        Index("ix_user_identities_user_id", "user_id"),
        Index("ix_user_identities_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<UserIdentity {self.provider_type}:{self.subject_id}>"

    def update_last_auth(self) -> None:
        """Update last authentication timestamp."""
        self.last_auth_at = utc_now()

    @property
    def is_saml(self) -> bool:
        """Check if this is a SAML identity."""
        return self.provider_type == "saml"

    @property
    def is_oidc(self) -> bool:
        """Check if this is an OIDC identity."""
        return self.provider_type == "oidc"
