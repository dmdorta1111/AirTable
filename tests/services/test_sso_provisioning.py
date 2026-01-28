"""
Integration tests for SSO JIT (Just-In-Time) provisioning service.

Tests the complete JIT provisioning flow including:
- New user creation on first SSO login
- User identity linking on subsequent logins
- Attribute mapping from SSO claims
- Role mapping from SSO groups
- Domain validation
- Profile updates
- Error handling
"""

import json
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.user import User
from pybase.models.user_identity import UserIdentity
from pybase.services.sso_provisioning import (
    SSOProvisioningService,
    SSOUserAttributes,
    create_provisioning_service,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def provisioning_service(db_session: AsyncSession) -> SSOProvisioningService:
    """Create JIT provisioning service instance."""
    return SSOProvisioningService(
        db=db_session,
        jit_provisioning_enabled=True,
        auto_update_profile=True,
        default_role="viewer",
        allowed_domains=None,  # No domain restriction
    )


@pytest_asyncio.fixture
async def provisioning_service_with_domain_restriction(
    db_session: AsyncSession,
) -> SSOProvisioningService:
    """Create JIT provisioning service with domain restriction."""
    return SSOProvisioningService(
        db=db_session,
        jit_provisioning_enabled=True,
        auto_update_profile=True,
        default_role="viewer",
        allowed_domains=["example.com", "trusted.com"],
    )


@pytest_asyncio.fixture
async def provisioning_service_jit_disabled(
    db_session: AsyncSession,
) -> SSOProvisioningService:
    """Create JIT provisioning service with JIT disabled."""
    return SSOProvisioningService(
        db=db_session,
        jit_provisioning_enabled=False,
        auto_update_profile=True,
        default_role="viewer",
        allowed_domains=None,
    )


def create_saml_attributes(
    email: str = "testuser@example.com",
    first_name: str = "Test",
    last_name: str = "User",
    display_name: str | None = None,
    groups: list[str] | None = None,
    roles: list[str] | None = None,
) -> SSOUserAttributes:
    """Create SAML user attributes for testing."""
    return SSOUserAttributes(
        email=email,
        first_name=first_name,
        last_name=last_name,
        display_name=display_name or f"{first_name} {last_name}",
        roles=roles or [],
        groups=groups or [],
    )


def create_oidc_attributes(
    email: str = "testuser@example.com",
    name: str = "Test User",
    picture: str | None = None,
    groups: list[str] | None = None,
) -> SSOUserAttributes:
    """Create OIDC user attributes for testing."""
    return SSOUserAttributes(
        email=email,
        display_name=name,
        picture=picture,
        groups=groups or [],
        roles=[],
    )


# =============================================================================
# New User Provisioning Tests (SAML)
# =============================================================================


async def test_provision_new_user_from_saml(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test automatic user creation on first SAML login."""
    # Arrange
    subject_id = str(uuid4())
    issuer = "https://idp.example.com/entityid"
    config_id = str(uuid4())
    attributes = create_saml_attributes(
        email="newuser@example.com",
        first_name="New",
        last_name="User",
    )
    raw_attributes = {
        "email": "newuser@example.com",
        "firstName": "New",
        "lastName": "User",
        "displayName": "New User",
    }

    # Act
    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=subject_id,
        issuer=issuer,
        config_id=config_id,
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    # Assert
    assert result.was_created is True
    assert result.user.email == "newuser@example.com"
    assert result.user.name == "New User"
    assert result.user.is_active is True
    assert result.user.is_verified is True  # SSO users are pre-verified
    assert result.identity.provider_type == "saml"
    assert result.identity.subject_id == subject_id
    assert result.identity.issuer == issuer
    assert result.identity.email == "newuser@example.com"

    # Verify database state
    user_count = await db_session.execute(select(User).where(User.email == "newuser@example.com"))
    assert user_count.scalar_one_or_none() is not None

    identity_count = await db_session.execute(
        select(UserIdentity).where(UserIdentity.subject_id == subject_id)
    )
    assert identity_count.scalar_one_or_none() is not None


async def test_provision_new_user_saml_with_display_name(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test user creation with display name from SAML."""
    subject_id = str(uuid4())
    attributes = create_saml_attributes(
        email="displayuser@example.com",
        first_name="Display",
        last_name="User",
        display_name="Display Name Override",
    )
    raw_attributes = {
        "email": "displayuser@example.com",
        "firstName": "Display",
        "lastName": "User",
        "displayName": "Display Name Override",
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.was_created is True
    assert result.user.name == "Display Name Override"


async def test_provision_new_user_saml_with_picture(
    provisioning_service: SSOProvisioningService,
):
    """Test user creation with profile picture."""
    subject_id = str(uuid4())
    attributes = SSOUserAttributes(
        email="pictureuser@example.com",
        display_name="Picture User",
        picture="https://example.com/avatar.jpg",
    )
    raw_attributes = {
        "email": "pictureuser@example.com",
        "displayName": "Picture User",
        "picture": "https://example.com/avatar.jpg",
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.was_created is True
    assert result.user.avatar_url == "https://example.com/avatar.jpg"


async def test_provision_new_user_saml_fallback_name(
    provisioning_service: SSOProvisioningService,
):
    """Test user name falls back to email local part if no name provided."""
    subject_id = str(uuid4())
    attributes = SSOUserAttributes(
        email="emaillocal@example.com",
    )
    raw_attributes = {
        "email": "emaillocal@example.com",
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.was_created is True
    assert result.user.name == "emaillocal"


# =============================================================================
# New User Provisioning Tests (OIDC)
# =============================================================================


async def test_provision_new_user_from_oidc(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test automatic user creation on first OIDC login."""
    subject_id = str(uuid4())
    issuer = "https://accounts.google.com"
    config_id = str(uuid4())
    attributes = create_oidc_attributes(
        email="oidcuser@example.com",
        name="OIDC User",
    )
    raw_attributes = {
        "sub": subject_id,
        "email": "oidcuser@example.com",
        "name": "OIDC User",
        "picture": "https://example.com/photo.jpg",
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="oidc",
        subject_id=subject_id,
        issuer=issuer,
        config_id=config_id,
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.was_created is True
    assert result.user.email == "oidcuser@example.com"
    assert result.user.name == "OIDC User"
    assert result.user.avatar_url == "https://example.com/photo.jpg"
    assert result.identity.provider_type == "oidc"
    assert result.identity.subject_id == subject_id
    assert result.identity.issuer == issuer


# =============================================================================
# Existing User Linking Tests
# =============================================================================


async def test_link_existing_user_by_email(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test linking SSO identity to existing user by email."""
    # Arrange - create existing user
    existing_user = User(
        email="existing@example.com",
        hashed_password="hashed_password",
        name="Existing User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(existing_user)
    await db_session.commit()
    await db_session.refresh(existing_user)

    # Act - link SSO identity
    subject_id = str(uuid4())
    attributes = create_saml_attributes(
        email="existing@example.com",  # Same email as existing user
        first_name="Existing",
        last_name="User",
    )
    raw_attributes = {
        "email": "existing@example.com",
        "firstName": "Existing",
        "lastName": "User",
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    # Assert
    assert result.was_created is False
    assert result.user.id == existing_user.id
    assert result.identity.user_id == existing_user.id
    assert result.identity.provider_type == "saml"
    assert result.identity.subject_id == subject_id

    # Verify identity was created
    identity_count = await db_session.execute(
        select(UserIdentity).where(UserIdentity.subject_id == subject_id)
    )
    assert identity_count.scalar_one_or_none() is not None


async def test_login_with_existing_sso_identity(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test login with previously linked SSO identity."""
    # Arrange - create user and identity
    user = User(
        email="returning@example.com",
        hashed_password="hashed_password",
        name="Returning User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    subject_id = str(uuid4())
    identity = UserIdentity(
        user_id=user.id,
        provider_type="saml",
        config_id=str(uuid4()),
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        attributes='{}',
        profile_data='{}',
    )
    db_session.add(identity)
    await db_session.commit()

    # Act - login with existing identity
    attributes = create_saml_attributes(
        email="returning@example.com",
        first_name="Returning",
        last_name="User",
    )
    raw_attributes = {
        "email": "returning@example.com",
        "firstName": "Returning",
        "lastName": "User",
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    # Assert
    assert result.was_created is False
    assert result.user.id == user.id
    assert result.identity.id == identity.id
    assert result.tokens is not None  # Should receive auth tokens


async def test_profile_update_on_subsequent_login(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test user profile update on subsequent SSO login."""
    # Arrange - create user with old profile data
    user = User(
        email="updater@example.com",
        hashed_password="hashed_password",
        name="Old Name",
        is_active=True,
        is_verified=True,
        avatar_url="https://old.example.com/avatar.jpg",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    subject_id = str(uuid4())
    identity = UserIdentity(
        user_id=user.id,
        provider_type="saml",
        config_id=str(uuid4()),
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        email="updater@example.com",
        attributes='{}',
        profile_data='{}',
    )
    db_session.add(identity)
    await db_session.commit()

    # Act - login with updated profile data
    attributes = SSOUserAttributes(
        email="updater@example.com",
        display_name="New Name",
        picture="https://new.example.com/avatar.jpg",
    )
    raw_attributes = {
        "email": "updater@example.com",
        "displayName": "New Name",
        "picture": "https://new.example.com/avatar.jpg",
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    # Assert
    assert result.was_created is False
    assert result.user.name == "New Name"  # Name updated
    assert result.user.avatar_url == "https://new.example.com/avatar.jpg"  # Avatar updated


# =============================================================================
# Domain Validation Tests
# =============================================================================


async def test_provision_with_allowed_domain(
    provisioning_service_with_domain_restriction: SSOProvisioningService,
):
    """Test JIT provisioning with allowed domain."""
    attributes = create_saml_attributes(email="user@trusted.com")
    raw_attributes = {"email": "user@trusted.com"}

    result = await provisioning_service_with_domain_restriction.provision_or_link_user(
        provider_type="saml",
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.was_created is True


async def test_provision_with_disallowed_domain_fails(
    provisioning_service_with_domain_restriction: SSOProvisioningService,
):
    """Test JIT provisioning fails with disallowed domain."""
    attributes = create_saml_attributes(email="user@hacker.com")
    raw_attributes = {"email": "user@hacker.com"}

    with pytest.raises(ValueError, match="Email domain not in allowed list"):
        await provisioning_service_with_domain_restriction.provision_or_link_user(
            provider_type="saml",
            subject_id=str(uuid4()),
            issuer="https://idp.example.com/entityid",
            config_id=str(uuid4()),
            user_attributes=attributes,
            raw_attributes=raw_attributes,
        )


async def test_provision_without_domain_restriction(
    provisioning_service: SSOProvisioningService,
):
    """Test JIT provisioning without domain restriction allows any domain."""
    attributes = create_saml_attributes(email="user@anydomain.com")
    raw_attributes = {"email": "user@anydomain.com"}

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.was_created is True


# =============================================================================
# JIT Disabled Tests
# =============================================================================


async def test_provision_when_jit_disabled_fails(
    provisioning_service_jit_disabled: SSOProvisioningService,
):
    """Test that new user creation fails when JIT is disabled."""
    attributes = create_saml_attributes(email="newuser@example.com")
    raw_attributes = {"email": "newuser@example.com"}

    with pytest.raises(ValueError, match="JIT provisioning is disabled"):
        await provisioning_service_jit_disabled.provision_or_link_user(
            provider_type="saml",
            subject_id=str(uuid4()),
            issuer="https://idp.example.com/entityid",
            config_id=str(uuid4()),
            user_attributes=attributes,
            raw_attributes=raw_attributes,
        )


async def test_link_existing_user_when_jit_disabled_succeeds(
    provisioning_service_jit_disabled: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test that linking existing user works even when JIT is disabled."""
    # Arrange - create existing user
    existing_user = User(
        email="existing@example.com",
        hashed_password="hashed_password",
        name="Existing User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(existing_user)
    await db_session.commit()
    await db_session.refresh(existing_user)

    # Act - should still allow linking
    attributes = create_saml_attributes(email="existing@example.com")
    raw_attributes = {"email": "existing@example.com"}

    result = await provisioning_service_jit_disabled.provision_or_link_user(
        provider_type="saml",
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    # Assert - user was linked, not created
    assert result.was_created is False
    assert result.user.id == existing_user.id


# =============================================================================
# Role and Group Mapping Tests
# =============================================================================


async def test_provision_with_saml_groups(
    provisioning_service: SSOProvisioningService,
):
    """Test user provisioning with SAML group membership."""
    attributes = SSOUserAttributes(
        email="groupuser@example.com",
        display_name="Group User",
        groups=["Admins", "Users", "Developers"],
    )
    raw_attributes = {
        "email": "groupuser@example.com",
        "displayName": "Group User",
        "groups": ["Admins", "Users", "Developers"],
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.was_created is True
    # Groups are stored in identity attributes
    identity_data = json.loads(result.identity.attributes)
    assert identity_data["groups"] == ["Admins", "Users", "Developers"]


async def test_provision_with_saml_roles(
    provisioning_service: SSOProvisioningService,
):
    """Test user provisioning with SAML role claims."""
    attributes = SSOUserAttributes(
        email="roleuser@example.com",
        display_name="Role User",
        roles=["admin", "editor"],
    )
    raw_attributes = {
        "email": "roleuser@example.com",
        "displayName": "Role User",
        "roles": ["admin", "editor"],
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.was_created is True
    # Roles are stored in identity attributes
    identity_data = json.loads(result.identity.attributes)
    assert identity_data["roles"] == ["admin", "editor"]


# =============================================================================
# Error Handling Tests
# =============================================================================


async def test_provision_without_email_fails(
    provisioning_service: SSOProvisioningService,
):
    """Test that provisioning without email fails."""
    attributes = SSOUserAttributes(
        email=None,  # Missing email
        display_name="No Email User",
    )
    raw_attributes = {"displayName": "No Email User"}

    with pytest.raises(ValueError, match="Email is required for JIT provisioning"):
        await provisioning_service.provision_or_link_user(
            provider_type="saml",
            subject_id=str(uuid4()),
            issuer="https://idp.example.com/entityid",
            config_id=str(uuid4()),
            user_attributes=attributes,
            raw_attributes=raw_attributes,
        )


async def test_login_with_deactivated_user_fails(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test that deactivated user cannot login via SSO."""
    # Arrange - create deactivated user
    user = User(
        email="inactive@example.com",
        hashed_password="hashed_password",
        name="Inactive User",
        is_active=False,  # Deactivated
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Act/Assert
    attributes = create_saml_attributes(email="inactive@example.com")
    raw_attributes = {"email": "inactive@example.com"}

    with pytest.raises(ValueError, match="User account is deactivated"):
        await provisioning_service.provision_or_link_user(
            provider_type="saml",
            subject_id=str(uuid4()),
            issuer="https://idp.example.com/entityid",
            config_id=str(uuid4()),
            user_attributes=attributes,
            raw_attributes=raw_attributes,
        )


async def test_login_with_deactivated_identity_fails(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test that user with deactivated identity cannot login."""
    # Arrange - create active user but with previous identity
    user = User(
        email="activeuser@example.com",
        hashed_password="hashed_password",
        name="Active User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    subject_id = str(uuid4())
    identity = UserIdentity(
        user_id=user.id,
        provider_type="saml",
        config_id=str(uuid4()),
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        email="activeuser@example.com",
        attributes='{}',
        profile_data='{}',
    )
    db_session.add(identity)
    await db_session.commit()

    # Now deactivate the user
    user.is_active = False
    await db_session.commit()

    # Act/Assert
    attributes = create_saml_attributes(email="activeuser@example.com")
    raw_attributes = {"email": "activeuser@example.com"}

    with pytest.raises(ValueError, match="User account is deactivated"):
        await provisioning_service.provision_or_link_user(
            provider_type="saml",
            subject_id=subject_id,
            issuer="https://idp.example.com/entityid",
            config_id=str(uuid4()),
            user_attributes=attributes,
            raw_attributes=raw_attributes,
        )


# =============================================================================
# Multiple Identity Tests
# =============================================================================


async def test_user_with_multiple_sso_identities(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test user can have multiple SSO identities linked."""
    # Arrange - create user
    user = User(
        email="multiuser@example.com",
        hashed_password="hashed_password",
        name="Multi Identity User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Act - link first SAML identity
    result1 = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id="saml-id-1",
        issuer="https://idp1.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=create_saml_attributes(email="multiuser@example.com"),
        raw_attributes={"email": "multiuser@example.com"},
    )

    # Act - link second OIDC identity
    result2 = await provisioning_service.provision_or_link_user(
        provider_type="oidc",
        subject_id="oidc-id-1",
        issuer="https://accounts.google.com",
        config_id=str(uuid4()),
        user_attributes=create_oidc_attributes(email="multiuser@example.com"),
        raw_attributes={"email": "multiuser@example.com"},
    )

    # Assert - both identities linked to same user
    assert result1.user.id == user.id
    assert result2.user.id == user.id
    assert result1.identity.subject_id == "saml-id-1"
    assert result2.identity.subject_id == "oidc-id-1"

    # Verify both identities exist
    identities = await provisioning_service.get_user_identities(user.id)
    assert len(identities) == 2
    assert any(i.subject_id == "saml-id-1" for i in identities)
    assert any(i.subject_id == "oidc-id-1" for i in identities)


# =============================================================================
# Token Generation Tests
# =============================================================================


async def test_tokens_generated_on_provision(
    provisioning_service: SSOProvisioningService,
):
    """Test that auth tokens are generated after provisioning."""
    attributes = create_saml_attributes(email="tokenuser@example.com")
    raw_attributes = {"email": "tokenuser@example.com"}

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.tokens is not None
    assert "access_token" in result.tokens
    assert "refresh_token" in result.tokens


async def test_tokens_generated_on_existing_login(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test that auth tokens are generated on existing user login."""
    user = User(
        email="tokenexisting@example.com",
        hashed_password="hashed_password",
        name="Token Existing User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    attributes = create_saml_attributes(email="tokenexisting@example.com")
    raw_attributes = {"email": "tokenexisting@example.com"}

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    assert result.tokens is not None
    assert "access_token" in result.tokens
    assert "refresh_token" in result.tokens


# =============================================================================
# Identity Management Tests
# =============================================================================


async def test_unlink_identity(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test unlinking SSO identity from user."""
    # Arrange - create user with identity
    user = User(
        email="unlinkuser@example.com",
        hashed_password="hashed_password",
        name="Unlink User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    identity = UserIdentity(
        user_id=user.id,
        provider_type="saml",
        config_id=str(uuid4()),
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        email="unlinkuser@example.com",
        attributes='{}',
        profile_data='{}',
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    # Act - unlink identity
    result = await provisioning_service.unlink_identity(identity.id)

    # Assert
    assert result is True

    # Verify identity is deleted
    deleted_identity = await db_session.execute(
        select(UserIdentity).where(UserIdentity.id == identity.id)
    )
    assert deleted_identity.scalar_one_or_none() is None


async def test_unlink_nonexistent_identity(
    provisioning_service: SSOProvisioningService,
):
    """Test unlinking non-existent identity returns False."""
    result = await provisioning_service.unlink_identity(str(uuid4()))
    assert result is False


async def test_get_user_identities(
    provisioning_service: SSOProvisioningService,
    db_session: AsyncSession,
):
    """Test getting all identities for a user."""
    # Arrange - create user with multiple identities
    user = User(
        email="getidentities@example.com",
        hashed_password="hashed_password",
        name="Get Identities User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    identity1 = UserIdentity(
        user_id=user.id,
        provider_type="saml",
        config_id=str(uuid4()),
        subject_id="saml-123",
        issuer="https://idp1.example.com",
        email="getidentities@example.com",
        attributes='{}',
        profile_data='{}',
    )
    identity2 = UserIdentity(
        user_id=user.id,
        provider_type="oidc",
        config_id=str(uuid4()),
        subject_id="oidc-456",
        issuer="https://accounts.google.com",
        email="getidentities@example.com",
        attributes='{}',
        profile_data='{}',
    )
    db_session.add_all([identity1, identity2])
    await db_session.commit()

    # Act
    identities = await provisioning_service.get_user_identities(user.id)

    # Assert
    assert len(identities) == 2
    assert any(i.subject_id == "saml-123" for i in identities)
    assert any(i.subject_id == "oidc-456" for i in identities)


# =============================================================================
# Profile Data Snapshot Tests
# =============================================================================


async def test_profile_data_snapshot_on_creation(
    provisioning_service: SSOProvisioningService,
):
    """Test that profile data is snapshotted on user creation."""
    attributes = SSOUserAttributes(
        email="snapshot@example.com",
        display_name="Snapshot User",
        first_name="Snapshot",
        last_name="User",
        picture="https://example.com/photo.jpg",
    )
    raw_attributes = {
        "email": "snapshot@example.com",
        "displayName": "Snapshot User",
        "firstName": "Snapshot",
        "lastName": "User",
        "picture": "https://example.com/photo.jpg",
    }

    result = await provisioning_service.provision_or_link_user(
        provider_type="saml",
        subject_id=str(uuid4()),
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    # Check profile data snapshot
    profile_data = json.loads(result.identity.profile_data)
    assert profile_data["email"] == "snapshot@example.com"
    assert profile_data["display_name"] == "Snapshot User"
    assert profile_data["first_name"] == "Snapshot"
    assert profile_data["last_name"] == "User"
    assert profile_data["picture"] == "https://example.com/photo.jpg"

    # Check raw attributes
    attributes = json.loads(result.identity.attributes)
    assert attributes["displayName"] == "Snapshot User"


# =============================================================================
# Auto Update Profile Disabled Tests
# =============================================================================


async def test_auto_update_profile_disabled(
    db_session: AsyncSession,
):
    """Test that profile is not updated when auto_update_profile is False."""
    # Create service with auto-update disabled
    service = SSOProvisioningService(
        db=db_session,
        jit_provisioning_enabled=True,
        auto_update_profile=False,  # Disable auto-update
        default_role="viewer",
        allowed_domains=None,
    )

    # Create user
    user = User(
        email="noupdate@example.com",
        hashed_password="hashed_password",
        name="Original Name",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create identity
    subject_id = str(uuid4())
    identity = UserIdentity(
        user_id=user.id,
        provider_type="saml",
        config_id=str(uuid4()),
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        email="noupdate@example.com",
        attributes='{}',
        profile_data='{}',
    )
    db_session.add(identity)
    await db_session.commit()

    # Login with updated name
    attributes = SSOUserAttributes(
        email="noupdate@example.com",
        display_name="Updated Name",
    )
    raw_attributes = {"email": "noupdate@example.com", "displayName": "Updated Name"}

    result = await service.provision_or_link_user(
        provider_type="saml",
        subject_id=subject_id,
        issuer="https://idp.example.com/entityid",
        config_id=str(uuid4()),
        user_attributes=attributes,
        raw_attributes=raw_attributes,
    )

    # Assert - name should NOT be updated
    assert result.user.name == "Original Name"


# =============================================================================
# Factory Function Tests
# =============================================================================


async def test_create_provisioning_service_factory(
    db_session: AsyncSession,
):
    """Test factory function for creating provisioning service."""
    service = create_provisioning_service(db_session)

    assert service is not None
    assert isinstance(service, SSOProvisioningService)
    assert service.db == db_session
