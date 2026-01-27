"""
SSO JIT (Just-In-Time) provisioning service.

Handles automatic user creation and identity linking from SSO providers.
Supports both SAML and OIDC authentication flows.
"""

import json
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.core.security import create_token_pair, hash_password
from pybase.models.user import User
from pybase.models.user_identity import UserIdentity


# =============================================================================
# Provisioning Data Models
# =============================================================================


class SSOUserAttributes(BaseModel):
    """User attributes from SSO provider."""

    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    picture: str | None = None
    roles: list[str] | None = None
    groups: list[str] | None = None


class ProvisioningResult(BaseModel):
    """Result of user provisioning operation."""

    user: User
    identity: UserIdentity
    was_created: bool
    tokens: Any  # TokenPair from security.py


# =============================================================================
# JIT Provisioning Service
# =============================================================================


class SSOProvisioningService:
    """
    Just-In-Time provisioning service for SSO authentication.

    Automatically creates user accounts on first SSO login,
    links SSO identities to existing users, and updates user profiles.
    """

    def __init__(
        self,
        db: AsyncSession,
        jit_provisioning_enabled: bool = True,
        auto_update_profile: bool = True,
        default_role: str = "viewer",
        allowed_domains: list[str] | None = None,
    ):
        """
        Initialize JIT provisioning service.

        Args:
            db: Database session
            jit_provisioning_enabled: Enable automatic user creation
            auto_update_profile: Update user profile on each login
            default_role: Default role for provisioned users
            allowed_domains: List of allowed email domains for auto-provisioning
        """
        self.db = db
        self.jit_provisioning_enabled = jit_provisioning_enabled
        self.auto_update_profile = auto_update_profile
        self.default_role = default_role
        self.allowed_domains = allowed_domains or settings.sso_allowed_domains

    # =========================================================================
    # Main Provisioning Flow
    # =========================================================================

    async def provision_or_link_user(
        self,
        provider_type: str,
        subject_id: str,
        issuer: str,
        config_id: str,
        user_attributes: SSOUserAttributes,
        raw_attributes: dict[str, Any],
    ) -> ProvisioningResult:
        """
        Provision or link user from SSO authentication.

        This is the main entry point for JIT provisioning.
        Handles three scenarios:
        1. Existing user with linked SSO identity -> login
        2. Existing user by email without SSO identity -> link
        3. New user -> create account (if JIT enabled)

        Args:
            provider_type: SSO provider type ("saml" or "oidc")
            subject_id: Unique subject ID from IdP (NameID or sub claim)
            issuer: IdP entity ID or issuer URL
            config_id: SSO configuration ID
            user_attributes: Mapped user attributes
            raw_attributes: Raw attributes/claims from IdP

        Returns:
            ProvisioningResult with user, identity, creation status, and tokens

        Raises:
            ValueError: If provisioning is disabled or user cannot be created
        """
        # Try to find existing SSO identity
        identity = await self._find_identity(provider_type, subject_id, issuer)

        if identity:
            # Existing SSO identity found - login and update
            return await self._handle_existing_identity(
                identity=identity,
                user_attributes=user_attributes,
                raw_attributes=raw_attributes,
            )

        # No existing identity - try to find user by email
        user = None
        if user_attributes.email:
            user = await self._find_user_by_email(user_attributes.email)

        if user:
            # User exists but no SSO identity - link them
            return await self._link_existing_user(
                user=user,
                provider_type=provider_type,
                subject_id=subject_id,
                issuer=issuer,
                config_id=config_id,
                user_attributes=user_attributes,
                raw_attributes=raw_attributes,
            )

        # New user - create account if JIT provisioning is enabled
        if not self.jit_provisioning_enabled:
            raise ValueError(
                "JIT provisioning is disabled. User must be created manually "
                "or by an administrator before SSO login."
            )

        # Verify allowed domain if configured
        if not self._is_domain_allowed(user_attributes.email):
            raise ValueError(
                f"Email domain not in allowed list. "
                f"Cannot auto-provision user: {user_attributes.email}"
            )

        # Create new user
        return await self._create_and_link_user(
            provider_type=provider_type,
            subject_id=subject_id,
            issuer=issuer,
            config_id=config_id,
            user_attributes=user_attributes,
            raw_attributes=raw_attributes,
        )

    async def _handle_existing_identity(
        self,
        identity: UserIdentity,
        user_attributes: SSOUserAttributes,
        raw_attributes: dict[str, Any],
    ) -> ProvisioningResult:
        """
        Handle login for existing SSO identity.

        Args:
            identity: Existing UserIdentity
            user_attributes: Mapped user attributes
            raw_attributes: Raw attributes from IdP

        Returns:
            ProvisioningResult
        """
        user = identity.user

        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is deactivated")

        # Update user profile if enabled
        if self.auto_update_profile:
            self._update_user_profile(user, user_attributes)

        # Update identity with latest data
        identity.update_last_auth()
        identity.attributes = json.dumps(raw_attributes)
        identity.profile_data = json.dumps(user_attributes.model_dump())
        if user_attributes.email:
            identity.email = user_attributes.email
        if user_attributes.display_name:
            identity.display_name = user_attributes.display_name

        # Update user's last login
        user.update_last_login()

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(identity)

        # Generate auth tokens
        tokens = create_token_pair(user.id)

        return ProvisioningResult(
            user=user,
            identity=identity,
            was_created=False,
            tokens=tokens,
        )

    async def _link_existing_user(
        self,
        user: User,
        provider_type: str,
        subject_id: str,
        issuer: str,
        config_id: str,
        user_attributes: SSOUserAttributes,
        raw_attributes: dict[str, Any],
    ) -> ProvisioningResult:
        """
        Link SSO identity to existing user.

        Args:
            user: Existing user
            provider_type: SSO provider type
            subject_id: Subject ID from IdP
            issuer: IdP issuer
            config_id: SSO config ID
            user_attributes: Mapped user attributes
            raw_attributes: Raw attributes from IdP

        Returns:
            ProvisioningResult
        """
        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is deactivated")

        # Update user profile if enabled
        if self.auto_update_profile:
            self._update_user_profile(user, user_attributes)

        # Create new identity link
        identity = UserIdentity(
            user_id=user.id,
            provider_type=provider_type,
            config_id=config_id,
            subject_id=subject_id,
            issuer=issuer,
            attributes=json.dumps(raw_attributes),
            profile_data=json.dumps(user_attributes.model_dump()),
            email=user_attributes.email,
            display_name=user_attributes.display_name,
        )

        self.db.add(identity)

        # Update user's last login
        user.update_last_login()

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(identity)

        # Generate auth tokens
        tokens = create_token_pair(user.id)

        return ProvisioningResult(
            user=user,
            identity=identity,
            was_created=False,
            tokens=tokens,
        )

    async def _create_and_link_user(
        self,
        provider_type: str,
        subject_id: str,
        issuer: str,
        config_id: str,
        user_attributes: SSOUserAttributes,
        raw_attributes: dict[str, Any],
    ) -> ProvisioningResult:
        """
        Create new user and link SSO identity.

        Args:
            provider_type: SSO provider type
            subject_id: Subject ID from IdP
            issuer: IdP issuer
            config_id: SSO config ID
            user_attributes: Mapped user attributes
            raw_attributes: Raw attributes from IdP

        Returns:
            ProvisioningResult

        Raises:
            ValueError: If email is required but missing
        """
        # Email is required for user creation
        if not user_attributes.email:
            raise ValueError(
                "Email is required for JIT provisioning. "
                "Ensure your IdP sends the email claim/attribute."
            )

        # Build user name from attributes
        name = user_attributes.display_name
        if not name:
            if user_attributes.first_name and user_attributes.last_name:
                name = f"{user_attributes.first_name} {user_attributes.last_name}"
            else:
                # Fallback to email local part
                name = user_attributes.email.split("@")[0]

        # Create new user with random password (SSO-only user)
        random_password = self._generate_random_password()

        # Determine if user should be verified
        is_verified = True  # SSO users are pre-verified

        user = User(
            email=user_attributes.email.lower(),
            hashed_password=hash_password(random_password),
            name=name,
            avatar_url=user_attributes.picture,
            is_active=True,
            is_verified=is_verified,
            is_superuser=False,
            preferences=json.dumps({"sso_only": True}),
        )

        self.db.add(user)
        await self.db.flush()  # Flush to get user ID
        await self.db.refresh(user)

        # Create SSO identity link
        identity = UserIdentity(
            user_id=user.id,
            provider_type=provider_type,
            config_id=config_id,
            subject_id=subject_id,
            issuer=issuer,
            attributes=json.dumps(raw_attributes),
            profile_data=json.dumps(user_attributes.model_dump()),
            email=user_attributes.email,
            display_name=user_attributes.display_name or name,
        )

        self.db.add(identity)

        # Update user's last login
        user.update_last_login()

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(identity)

        # Generate auth tokens
        tokens = create_token_pair(user.id)

        return ProvisioningResult(
            user=user,
            identity=identity,
            was_created=True,
            tokens=tokens,
        )

    # =========================================================================
    # Database Queries
    # =========================================================================

    async def _find_identity(
        self,
        provider_type: str,
        subject_id: str,
        issuer: str,
    ) -> UserIdentity | None:
        """
        Find existing SSO identity.

        Args:
            provider_type: SSO provider type
            subject_id: Subject ID from IdP
            issuer: IdP issuer

        Returns:
            UserIdentity if found, None otherwise
        """
        result = await self.db.execute(
            select(UserIdentity).where(
                UserIdentity.provider_type == provider_type,
                UserIdentity.subject_id == subject_id,
                UserIdentity.issuer == issuer,
            )
        )
        return result.scalar_one_or_none()

    async def _find_user_by_email(self, email: str) -> User | None:
        """
        Find user by email address.

        Args:
            email: User email address

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(
                User.email == email.lower(),
                User.deleted_at == None,
            )
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # User Profile Management
    # =========================================================================

    def _update_user_profile(
        self,
        user: User,
        attributes: SSOUserAttributes,
    ) -> None:
        """
        Update user profile from SSO attributes.

        Args:
            user: User to update
            attributes: SSO user attributes
        """
        # Update name if changed
        if attributes.display_name:
            user.name = attributes.display_name
        elif attributes.first_name and attributes.last_name:
            user.name = f"{attributes.first_name} {attributes.last_name}"

        # Update avatar if provided
        if attributes.picture:
            user.avatar_url = attributes.picture

        # Note: We don't update email as it's the account identifier

    # =========================================================================
    # Domain Validation
    # =========================================================================

    def _is_domain_allowed(self, email: str | None) -> bool:
        """
        Check if email domain is in allowed list.

        Args:
            email: Email address to check

        Returns:
            True if domain is allowed or no allowed domains configured
        """
        if not self.allowed_domains:
            # No domain restriction
            return True

        if not email:
            return False

        domain = email.split("@")[-1].lower()

        return domain in self.allowed_domains

    # =========================================================================
    # Utility Functions
    # =========================================================================

    @staticmethod
    def _generate_random_password() -> str:
        """
        Generate a random password for SSO-only users.

        These users authenticate via SSO, so the password is only
        used as a fallback or if SSO is disabled.

        Returns:
            Random password string
        """
        import secrets

        # Generate 32-byte random string
        return secrets.token_urlsafe(32)

    async def get_user_identities(
        self,
        user_id: str,
    ) -> list[UserIdentity]:
        """
        Get all SSO identities linked to a user.

        Args:
            user_id: User ID

        Returns:
            List of UserIdentity records
        """
        result = await self.db.execute(
            select(UserIdentity).where(
                UserIdentity.user_id == user_id,
            )
        )
        return list(result.scalars().all())

    async def unlink_identity(
        self,
        identity_id: str,
    ) -> bool:
        """
        Unlink SSO identity from user.

        Args:
            identity_id: UserIdentity ID to unlink

        Returns:
            True if unlinked, False if not found
        """
        result = await self.db.execute(
            select(UserIdentity).where(UserIdentity.id == identity_id)
        )
        identity = result.scalar_one_or_none()

        if identity is None:
            return False

        await self.db.delete(identity)
        await self.db.commit()

        return True


# =============================================================================
# Convenience Functions
# =============================================================================


def create_provisioning_service(db: AsyncSession) -> SSOProvisioningService:
    """
    Create JIT provisioning service instance.

    Args:
        db: Database session

    Returns:
        Configured provisioning service
    """
    return SSOProvisioningService(
        db=db,
        jit_provisioning_enabled=settings.sso_jit_provisioning,
        auto_update_profile=True,  # Always update profile on login
        default_role=settings.sso_auto_provision_default_role,
        allowed_domains=settings.sso_allowed_domains,
    )
