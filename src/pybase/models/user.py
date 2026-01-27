"""
User and API Key models.

Handles user authentication, profile, and API key management.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel, SoftDeleteModel, utc_now

if TYPE_CHECKING:
    from pybase.models.comment import Comment
    from pybase.models.workspace import WorkspaceMember
    from pybase.models.dashboard import DashboardMember
    from pybase.models.user_identity import UserIdentity


class User(SoftDeleteModel):
    """
    User model for authentication and profile.

    Supports email/password authentication and stores user preferences.
    """

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Profile
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Email verification
    verification_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Password reset
    password_reset_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    password_reset_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Last login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Preferences (JSON stored as text)
    preferences: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Relationships
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[WorkspaceMember.user_id]",
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    dashboard_memberships: Mapped[list["DashboardMember"]] = relationship(
        "DashboardMember",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[DashboardMember.user_id]",
    )
    sso_identities: Mapped[list["UserIdentity"]] = relationship(
        "UserIdentity",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[UserIdentity.user_id]",
    )

    # Indexes
    __table_args__ = (Index("ix_users_email_active", "email", "is_active"),)

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login_at = utc_now()


class APIKey(BaseModel):
    """
    API Key model for programmatic access.

    API keys provide authentication without username/password.
    The actual key is hashed before storage.
    """

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Key details
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    key_prefix: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    hashed_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Status and permissions
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    scopes: Mapped[str | None] = mapped_column(
        Text,  # JSON array of scope strings
        nullable=True,
        default="[]",
    )

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_used_ip: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_keys",
    )

    # Indexes
    __table_args__ = (
        Index("ix_api_keys_prefix", "key_prefix"),
        Index("ix_api_keys_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<APIKey {self.key_prefix}... ({self.name})>"

    @property
    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if self.expires_at is None:
            return False
        return self.expires_at < utc_now()

    def update_usage(self, ip_address: str | None = None) -> None:
        """Update last used timestamp and IP."""
        self.last_used_at = utc_now()
        if ip_address:
            self.last_used_ip = ip_address
