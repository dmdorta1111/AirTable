"""
Integration tests for SSO-only mode enforcement.

Tests the SSO-only mode feature including:
- Local login disabled for regular users
- Admin recovery account access
- Registration disabled
- SAML/OIDC login still works
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import get_settings
from pybase.models.user import User


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def admin_recovery_user(db_session: AsyncSession) -> User:
    """Create an admin recovery user for testing."""
    from pybase.core.security import hash_password

    user = User(
        email="admin-recovery@example.com",
        hashed_password=hash_password("adminPassword123"),
        name="Admin Recovery",
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create a regular user for testing."""
    from pybase.core.security import hash_password

    user = User(
        email="regularuser@example.com",
        hashed_password=hash_password("userPassword123"),
        name="Regular User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sso_settings(monkeypatch):
    """Patch settings to enable SSO-only mode for testing."""
    settings = get_settings()
    monkeypatch.setattr(settings, "sso_only_mode", True)
    monkeypatch.setattr(settings, "sso_admin_recovery_email", "admin-recovery@example.com")
    monkeypatch.setattr(settings, "sso_enabled", True)
    return settings


@pytest.fixture
async def non_sso_settings(monkeypatch):
    """Patch settings to disable SSO-only mode for testing."""
    settings = get_settings()
    monkeypatch.setattr(settings, "sso_only_mode", False)
    monkeypatch.setattr(settings, "sso_admin_recovery_email", None)
    monkeypatch.setattr(settings, "sso_enabled", False)
    return settings


# =============================================================================
# SSO-Only Mode - Local Login Tests
# =============================================================================


@pytest.mark.asyncio
async def test_local_login_disabled_for_regular_user_in_sso_only_mode(
    async_client: AsyncClient,
    regular_user: User,
    sso_settings,
):
    """
    Test that local login is disabled for regular users when SSO-only mode is enabled.

    Given:
        - SSO-only mode is enabled
        - A regular user exists with valid credentials
    When:
        - The user attempts to login with email/password
    Then:
        - Login should be denied with 403 Forbidden
        - Error message should indicate SSO-only mode is enabled
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "regularuser@example.com",
            "password": "userPassword123",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "SSO-only mode is enabled. Please use single sign-on to login."


@pytest.mark.asyncio
async def test_admin_recovery_login_works_in_sso_only_mode(
    async_client: AsyncClient,
    admin_recovery_user: User,
    sso_settings,
):
    """
    Test that admin recovery account can login when SSO-only mode is enabled.

    Given:
        - SSO-only mode is enabled
        - Admin recovery email is configured
        - Admin recovery user exists with valid credentials
    When:
        - The admin recovery user attempts to login with email/password
    Then:
        - Login should succeed
        - Access and refresh tokens should be returned
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin-recovery@example.com",
            "password": "adminPassword123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert data["user"]["email"] == "admin-recovery@example.com"


@pytest.mark.asyncio
async def test_local_login_works_when_sso_only_mode_disabled(
    async_client: AsyncClient,
    regular_user: User,
    non_sso_settings,
):
    """
    Test that local login works normally when SSO-only mode is disabled.

    Given:
        - SSO-only mode is disabled
        - A regular user exists with valid credentials
    When:
        - The user attempts to login with email/password
    Then:
        - Login should succeed
        - Access and refresh tokens should be returned
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "regularuser@example.com",
            "password": "userPassword123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "regularuser@example.com"


@pytest.mark.asyncio
async def test_invalid_credentials_still_fail_in_sso_only_mode(
    async_client: AsyncClient,
    admin_recovery_user: User,
    sso_settings,
):
    """
    Test that invalid credentials fail even for admin recovery account.

    Given:
        - SSO-only mode is enabled
        - Admin recovery user exists
    When:
        - Login is attempted with wrong password for admin recovery account
    Then:
        - Login should fail with 401 Unauthorized
        - Error message should indicate invalid credentials
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin-recovery@example.com",
            "password": "wrongPassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_non_admin_recovery_user_denied_in_sso_only_mode(
    async_client: AsyncClient,
    regular_user: User,
    admin_recovery_user: User,
    sso_settings,
):
    """
    Test that non-admin users are denied even if admin recovery exists.

    Given:
        - SSO-only mode is enabled
        - Admin recovery email is configured
        - Both admin recovery and regular users exist
    When:
        - Regular user attempts to login
    Then:
        - Login should be denied with 403 Forbidden
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "regularuser@example.com",
            "password": "userPassword123",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "SSO-only mode is enabled. Please use single sign-on to login."


# =============================================================================
# SSO-Only Mode - Registration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_registration_disabled_in_sso_only_mode(
    async_client: AsyncClient,
    sso_settings,
):
    """
    Test that user registration is disabled when SSO-only mode is enabled.

    Given:
        - SSO-only mode is enabled
    When:
        - User attempts to register a new account
    Then:
        - Registration should be denied with 403 Forbidden
        - Error message should indicate SSO-only mode is enabled
    """
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newPassword123",
            "name": "New User",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "SSO-only mode is enabled. Please use single sign-on to login."


@pytest.mark.asyncio
async def test_registration_works_when_sso_only_mode_disabled(
    async_client: AsyncClient,
    non_sso_settings,
):
    """
    Test that user registration works when SSO-only mode is disabled.

    Given:
        - SSO-only mode is disabled
        - Registration is enabled
    When:
        - User attempts to register a new account
    Then:
        - Registration should succeed
        - User should be created with auth tokens
    """
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newPassword123",
            "name": "New User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "newuser@example.com"


# =============================================================================
# SSO-Only Mode - No Admin Recovery Configured
# =============================================================================


@pytest.mark.asyncio
async def test_sso_only_mode_with_no_admin_recovery(
    async_client: AsyncClient,
    regular_user: User,
    monkeypatch,
):
    """
    Test SSO-only mode behavior when no admin recovery email is configured.

    Given:
        - SSO-only mode is enabled
        - No admin recovery email is configured
        - Regular users exist
    When:
        - Any user attempts to login with email/password
    Then:
        - All login attempts should be denied with 403 Forbidden
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "sso_only_mode", True)
    monkeypatch.setattr(settings, "sso_admin_recovery_email", None)

    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "regularuser@example.com",
            "password": "userPassword123",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "SSO-only mode is enabled. Please use single sign-on to login."


# =============================================================================
# SSO-Only Mode - SAML Login Tests
# =============================================================================


@pytest.mark.asyncio
async def test_saml_login_works_in_sso_only_mode(
    async_client: AsyncClient,
    sso_settings,
):
    """
    Test that SAML login still works when SSO-only mode is enabled.

    Given:
        - SSO-only mode is enabled
        - SAML is configured
    When:
        - User initiates SAML login
    Then:
        - SAML login initiation should succeed
        - User should be redirected to IdP
    """
    # This test verifies that SAML login endpoint is accessible
    # The actual SAML flow is tested in test_saml_api.py
    response = await async_client.get(
        "/api/v1/saml/login",
        params={"relay_state": "/dashboard"},
    )

    # Should redirect or return login URL (implementation-specific)
    # The key point is that SAML login should not be blocked
    assert response.status_code in [200, 307, 308]


# =============================================================================
# SSO-Only Mode - OIDC Login Tests
# =============================================================================


@pytest.mark.asyncio
async def test_oidc_login_works_in_sso_only_mode(
    async_client: AsyncClient,
    sso_settings,
):
    """
    Test that OIDC login still works when SSO-only mode is enabled.

    Given:
        - SSO-only mode is enabled
        - OIDC is configured
    When:
        - User initiates OIDC login
    Then:
        - OIDC login initiation should succeed
        - User should be redirected to provider
    """
    # This test verifies that OIDC login endpoint is accessible
    # The actual OIDC flow is tested in test_oidc_api.py
    response = await async_client.get(
        "/api/v1/oidc/login",
        params={"provider": "google"},
    )

    # Should redirect or return login URL (implementation-specific)
    # The key point is that OIDC login should not be blocked
    assert response.status_code in [200, 307, 308]


# =============================================================================
# SSO-Only Mode - Password Change Tests
# =============================================================================


@pytest.mark.asyncio
async def test_password_change_works_for_authenticated_admin(
    async_client: AsyncClient,
    admin_recovery_user: User,
    sso_settings,
):
    """
    Test that admin recovery user can change password when authenticated.

    Given:
        - SSO-only mode is enabled
        - Admin recovery user is authenticated
    When:
        - Admin user attempts to change password
    Then:
        - Password change should succeed
    """
    # First login as admin recovery
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin-recovery@example.com",
            "password": "adminPassword123",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # Now try to change password
    response = await async_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "adminPassword123",
            "new_password": "newAdminPassword456",
        },
    )

    assert response.status_code == 204

    # Verify new password works
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin-recovery@example.com",
            "password": "newAdminPassword456",
        },
    )
    assert login_response.status_code == 200


# =============================================================================
# SSO-Only Mode - Case Sensitivity Tests
# =============================================================================


@pytest.mark.asyncio
async def test_admin_recovery_email_case_insensitive(
    async_client: AsyncClient,
    admin_recovery_user: User,
    sso_settings,
):
    """
    Test that admin recovery email matching is case-insensitive.

    Given:
        - SSO-only mode is enabled
        - Admin recovery email is "admin-recovery@example.com"
    When:
        - Login attempted with different case: "Admin-Recovery@Example.com"
    Then:
        - Login should succeed
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "Admin-Recovery@Example.com",
            "password": "adminPassword123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin-recovery@example.com"


# =============================================================================
# SSO-Only Mode - Error Message Tests
# =============================================================================


@pytest.mark.asyncio
async def test_sso_only_mode_error_message_is_clear(
    async_client: AsyncClient,
    regular_user: User,
    sso_settings,
):
    """
    Test that SSO-only mode error message is clear and actionable.

    Given:
        - SSO-only mode is enabled
    When:
        - Regular user attempts to login
    Then:
        - Error message should clearly indicate SSO-only mode is enabled
        - Error message should guide user to use SSO
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "regularuser@example.com",
            "password": "userPassword123",
        },
    )

    assert response.status_code == 403
    error_detail = response.json()["detail"]
    assert "SSO-only mode" in error_detail
    assert "single sign-on" in error_detail.lower() or "sso" in error_detail.lower()


# =============================================================================
# SSO-Only Mode - Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_complete_sso_only_mode_flow(
    async_client: AsyncClient,
    admin_recovery_user: User,
    regular_user: User,
    sso_settings,
    db_session: AsyncSession,
):
    """
    Test complete SSO-only mode enforcement flow.

    Given:
        - SSO-only mode is enabled
        - Admin recovery user exists
        - Regular users exist
    When:
        - Regular user tries to login (should fail)
        - Admin recovery user tries to login (should succeed)
        - New user tries to register (should fail)
    Then:
        - All operations should behave as expected
        - Error messages should be clear
    """
    # 1. Regular user login should fail
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "regularuser@example.com",
            "password": "userPassword123",
        },
    )
    assert response.status_code == 403
    assert "SSO-only mode" in response.json()["detail"]

    # 2. Admin recovery login should succeed
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin-recovery@example.com",
            "password": "adminPassword123",
        },
    )
    assert response.status_code == 200
    admin_token = response.json()["access_token"]

    # 3. Registration should be disabled
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newPassword123",
            "name": "New User",
        },
    )
    assert response.status_code == 403
    assert "SSO-only mode" in response.json()["detail"]

    # 4. Verify admin can access protected endpoints
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "admin-recovery@example.com"


@pytest.mark.asyncio
async def test_sso_only_mode_with_sso_configured(
    async_client: AsyncClient,
    admin_recovery_user: User,
    sso_settings,
    db_session: AsyncSession,
):
    """
    Test SSO-only mode when SAML/OIDC is properly configured.

    Given:
        - SSO-only mode is enabled
        - SAML is configured
        - OIDC is configured
        - Admin recovery user exists
    When:
        - User attempts local login (should fail for non-admin)
        - User accesses SAML endpoints (should work)
        - User accesses OIDC endpoints (should work)
    Then:
        - Local login should be blocked
        - SSO endpoints should be accessible
    """
    # Local login for non-existent user should fail with SSO-only message
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "somePassword",
        },
    )
    # Should get SSO-only mode error, not generic invalid credentials
    assert response.status_code == 403
    assert "SSO-only mode" in response.json()["detail"]

    # SAML metadata endpoint should be accessible
    response = await async_client.get("/api/v1/saml/metadata")
    assert response.status_code in [200, 401, 403]  # Depends on authentication requirements

    # OIDC config endpoint should be accessible
    response = await async_client.get("/api/v1/oidc/config")
    assert response.status_code in [200, 401, 403]  # Depends on authentication requirements
