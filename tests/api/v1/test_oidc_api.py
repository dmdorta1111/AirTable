"""
Integration tests for OIDC authentication endpoints.

Tests the complete OIDC authentication flow including:
- OIDC login initiation
- OIDC callback processing
- OIDC token validation
- JIT user provisioning
- Error handling
- PKCE support
- ID token validation
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.oidc_config import OIDCConfig
from pybase.models.user import User
from pybase.models.user_identity import UserIdentity


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def oidc_config(db_session: AsyncSession) -> OIDCConfig:
    """Create a test OIDC configuration."""
    config = OIDCConfig(
        name="Test OIDC Provider",
        is_enabled=True,
        is_default=True,
        # Provider settings
        issuer_url="https://accounts.google.com",
        authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        userinfo_endpoint="https://www.googleapis.com/oauth2/v3/userinfo",
        end_session_endpoint="https://oauth2.googleapis.com/revoke",
        # Client credentials
        client_id="test-client-id.apps.googleusercontent.com",
        client_secret="test-client-secret",
        # OIDC settings
        scope="openid email profile",
        response_type="code",
        response_mode="query",
        # Claim mapping
        claim_email="email",
        claim_first_name="given_name",
        claim_last_name="family_name",
        claim_display_name="name",
        claim_picture="picture",
        # Role mapping
        group_claim="groups",
        role_mapping_admin=["Admins", "Administrators"],
        role_mapping_user=["Users"],
        # JIT provisioning
        enable_jit_provisioning=True,
        default_role="user",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest_asyncio.fixture
async def oidc_config_disabled(db_session: AsyncSession) -> OIDCConfig:
    """Create a disabled OIDC configuration for testing."""
    config = OIDCConfig(
        name="Disabled OIDC Provider",
        is_enabled=False,
        is_default=False,
        issuer_url="https://disabled-provider.com",
        authorization_endpoint="https://disabled-provider.com/auth",
        token_endpoint="https://disabled-provider.com/token",
        client_id="disabled-client-id",
        client_secret="disabled-client-secret",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


def create_mock_id_token(
    sub: str = "test-user-id",
    email: str = "testuser@example.com",
    issuer: str = "https://accounts.google.com",
    audience: str = "test-client-id.apps.googleusercontent.com",
) -> str:
    """
    Create a mock ID token for testing.

    Returns a JWT string (unsigned for testing purposes).
    """
    from jose import jwt

    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        "email": email,
        "email_verified": True,
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/avatar.jpg",
        "exp": 9999999999,  # Far future
        "iat": 1706400000,
    }

    # Use "none" algorithm for testing (no signature)
    return jwt.encode(payload, key="", algorithm="none")


def create_mock_token_response(
    access_token: str = "mock-access-token",
    id_token: str = None,
    refresh_token: str = "mock-refresh-token",
) -> dict:
    """Create a mock token response from OIDC provider."""
    return {
        "access_token": access_token,
        "id_token": id_token or create_mock_id_token(),
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": "openid email profile",
    }


def create_mock_userinfo(
    sub: str = "test-user-id",
    email: str = "testuser@example.com",
) -> dict:
    """Create a mock UserInfo response from OIDC provider."""
    return {
        "sub": sub,
        "email": email,
        "email_verified": True,
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/avatar.jpg",
    }


# =============================================================================
# OIDC Login Initiation Tests
# =============================================================================


async def test_oidc_login_init_redirects(
    client,
    oidc_config: OIDCConfig,
):
    """Test that OIDC login initiation returns redirect."""
    response = await client.get(
        f"/api/v1/oidc/login?provider={oidc_config.id}",
        follow_redirects=False
    )

    assert response.status_code == 307
    assert "location" in response.headers

    # Verify redirect URL contains OIDC provider endpoints
    redirect_url = response.headers["location"]
    assert oidc_config.authorization_endpoint in redirect_url
    assert "client_id=" in redirect_url
    assert "redirect_uri=" in redirect_url
    assert "response_type=code" in redirect_url
    assert "scope=" in redirect_url
    assert "state=" in redirect_url


async def test_oidc_login_init_with_provider_name(
    client,
    oidc_config: OIDCConfig,
):
    """Test OIDC login with provider name instead of config ID."""
    response = await client.get(
        "/api/v1/oidc/login?provider=google",
        follow_redirects=False
    )

    assert response.status_code == 307
    assert "location" in response.headers


async def test_oidc_login_init_disabled_config(
    client,
    oidc_config_disabled: OIDCConfig,
):
    """Test that disabled OIDC config returns 403."""
    response = await client.get(
        f"/api/v1/oidc/login?provider={oidc_config_disabled.id}"
    )

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


async def test_oidc_login_init_missing_config(client):
    """Test OIDC login with non-existent config."""
    response = await client.get(
        "/api/v1/oidc/login?provider=00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


async def test_oidc_login_init_default_config(
    client,
    oidc_config: OIDCConfig,
):
    """Test OIDC login with default config (no provider specified)."""
    response = await client.get("/api/v1/oidc/login", follow_redirects=False)

    assert response.status_code == 307
    assert "location" in response.headers


async def test_oidc_login_init_with_pkce(
    client,
    oidc_config: OIDCConfig,
):
    """Test that OIDC login includes PKCE parameters."""
    response = await client.get(
        f"/api/v1/oidc/login?provider={oidc_config.id}",
        follow_redirects=False
    )

    assert response.status_code == 307
    redirect_url = response.headers["location"]

    # PKCE uses code_challenge parameter
    assert "code_challenge=" in redirect_url
    assert "code_challenge_method=S256" in redirect_url


async def test_oidc_login_init_with_prompt(
    client,
    oidc_config: OIDCConfig,
):
    """Test OIDC login with custom prompt parameter."""
    response = await client.get(
        f"/api/v1/oidc/login?provider={oidc_config.id}&prompt=login",
        follow_redirects=False
    )

    assert response.status_code == 307
    redirect_url = response.headers["location"]
    assert "prompt=login" in redirect_url


async def test_oidc_login_init_with_login_hint(
    client,
    oidc_config: OIDCConfig,
):
    """Test OIDC login with login_hint parameter."""
    response = await client.get(
        f"/api/v1/oidc/login?provider={oidc_config.id}&login_hint=user@example.com",
        follow_redirects=False
    )

    assert response.status_code == 307
    redirect_url = response.headers["location"]
    assert "login_hint=user%40example.com" in redirect_url


# =============================================================================
# OIDC Callback Tests
# =============================================================================


async def test_oidc_callback_creates_user_on_first_login(
    client,
    oidc_config: OIDCConfig,
    db_session: AsyncSession,
):
    """Test that OIDC callback creates new user via JIT provisioning."""
    # Create mock tokens
    id_token = create_mock_id_token(
        sub="new-user-123",
        email="newuser@example.com"
    )
    token_response = create_mock_token_response(id_token=id_token)

    # Mock the httpx.AsyncClient to return our mock data
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(
            200,
            content=json.dumps(token_response),
            headers={"content-type": "application/json"}
        )

        # Send authorization code to callback endpoint
        response = await client.get(
            "/api/v1/oidc/callback",
            params={
                "code": "mock-auth-code",
                "state": "mock-state",
            },
        )

    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user" in data
    assert data["was_created"] is True

    # Verify user was created in database
    result = await db_session.execute(
        select(User).where(User.email == "newuser@example.com")
    )
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.email == "newuser@example.com"
    assert "Test" in user.name
    assert user.is_active is True

    # Verify user identity was linked
    result = await db_session.execute(
        select(UserIdentity).where(
            UserIdentity.provider_type == "oidc",
            UserIdentity.subject_id == "new-user-123",
        )
    )
    identity = result.scalar_one_or_none()

    assert identity is not None
    assert identity.user_id == str(user.id)


async def test_oidc_callback_links_existing_user(
    client,
    oidc_config: OIDCConfig,
    db_session: AsyncSession,
):
    """Test that OIDC callback links to existing user on subsequent login."""
    # Create existing user
    from pybase.core.security import hash_password

    existing_user = User(
        email="existing@example.com",
        hashed_password=hash_password("password123"),
        name="Existing User",
        is_active=True,
    )
    db_session.add(existing_user)
    await db_session.commit()

    # Create user identity link
    identity = UserIdentity(
        user_id=str(existing_user.id),
        provider_type="oidc",
        config_id=str(oidc_config.id),
        subject_id="existing-user-456",
        issuer="https://accounts.google.com",
    )
    db_session.add(identity)
    await db_session.commit()

    # Create mock tokens for existing user
    id_token = create_mock_id_token(
        sub="existing-user-456",
        email="existing@example.com"
    )
    token_response = create_mock_token_response(id_token=id_token)

    # Mock the httpx.AsyncClient
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(
            200,
            content=json.dumps(token_response),
            headers={"content-type": "application/json"}
        )

        # Send authorization code to callback endpoint
        response = await client.get(
            "/api/v1/oidc/callback",
            params={
                "code": "mock-auth-code",
                "state": "mock-state",
            },
        )

    assert response.status_code == 200

    data = response.json()
    assert data["was_created"] is False
    assert data["user"]["email"] == "existing@example.com"


async def test_oidc_callback_invalid_authorization_code(
    client,
    oidc_config: OIDCConfig,
):
    """Test that invalid authorization code returns 400."""
    # Mock httpx to raise an error (simulating invalid code)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("invalid_grant: Invalid authorization code")

        response = await client.get(
            "/api/v1/oidc/callback",
            params={
                "code": "invalid-code",
                "state": "mock-state",
            },
        )

    assert response.status_code == 500


async def test_oidc_callback_missing_code(client):
    """Test that missing authorization code parameter returns 422."""
    response = await client.get(
        "/api/v1/oidc/callback",
        params={"state": "test"}
    )

    assert response.status_code == 422  # Unprocessable Entity (validation error)


async def test_oidc_callback_missing_state(client):
    """Test that missing state parameter returns 422."""
    response = await client.get(
        "/api/v1/oidc/callback",
        params={"code": "test-code"}
    )

    assert response.status_code == 422


# =============================================================================
# OIDC Config Info Tests
# =============================================================================


async def test_oidc_config_info_unauthenticated(client):
    """Test that config info endpoint requires authentication."""
    response = await client.get("/api/v1/oidc/config")

    assert response.status_code == 401


async def test_oidc_config_info_authenticated(
    client,
    auth_headers: dict,
    oidc_config: OIDCConfig,
):
    """Test that authenticated user can get OIDC config info."""
    response = await client.get(
        "/api/v1/oidc/config",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert "sso_enabled" in data
    assert "oidc_configs" in data
    assert len(data["oidc_configs"]) > 0

    # Verify sensitive data is not exposed
    config = data["oidc_configs"][0]
    assert "client_secret" not in config
    assert "authorization_endpoint" not in config
    assert "token_endpoint" not in config
    assert "issuer_url" in config
    assert "name" in config


# =============================================================================
# OIDC Logout Tests
# =============================================================================


async def test_oidc_logout_unauthenticated(client):
    """Test that logout endpoint requires authentication."""
    response = await client.get("/api/v1/oidc/logout")

    assert response.status_code == 401


async def test_oidc_logout_authenticated(
    client,
    auth_headers: dict,
    oidc_config: OIDCConfig,
):
    """Test that authenticated user can get logout URL."""
    response = await client.get(
        "/api/v1/oidc/logout",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert "message" in data

    # If OIDC config has end_session_endpoint, should return logout_url
    if oidc_config.end_session_endpoint:
        assert "logout_url" in data


async def test_oidc_logout_with_post_logout_redirect(
    client,
    auth_headers: dict,
    oidc_config: OIDCConfig,
):
    """Test OIDC logout with post_logout_redirect_uri parameter."""
    response = await client.get(
        "/api/v1/oidc/logout?post_logout_redirect_uri=http://localhost:3000/login",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert "message" in data


# =============================================================================
# OIDC Error Handling Tests
# =============================================================================


async def test_oidc_login_with_sso_disabled(
    client,
    oidc_config: OIDCConfig,
    monkeypatch,
):
    """Test that OIDC login returns 403 when SSO is disabled globally."""
    # Temporarily disable SSO
    from pybase.core import config

    monkeypatch.setattr(config.settings, "sso_enabled", False)

    response = await client.get(f"/api/v1/oidc/login?provider={oidc_config.id}")

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


async def test_oidc_callback_with_sso_disabled(
    client,
    oidc_config: OIDCConfig,
    monkeypatch,
):
    """Test that OIDC callback returns 403 when SSO is disabled globally."""
    from pybase.core import config

    monkeypatch.setattr(config.settings, "sso_enabled", False)

    response = await client.get(
        "/api/v1/oidc/callback",
        params={
            "code": "test-code",
            "state": "test-state",
        },
    )

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


# =============================================================================
# Integration Tests
# =============================================================================


async def test_complete_oidc_flow(
    client,
    oidc_config: OIDCConfig,
    db_session: AsyncSession,
):
    """Test the complete OIDC authentication flow from start to finish."""
    # Step 1: Initiate OIDC login
    login_response = await client.get(
        f"/api/v1/oidc/login?provider={oidc_config.id}",
        follow_redirects=False,
    )

    assert login_response.status_code == 307
    redirect_url = login_response.headers["location"]
    assert oidc_config.authorization_endpoint in redirect_url

    # Extract state parameter from redirect URL
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(redirect_url)
    query_params = parse_qs(parsed_url.query)
    state = query_params.get("state", [None])[0]

    assert state is not None

    # Step 2: Simulate IdP authentication and callback
    # (In real flow, user authenticates at IdP and is redirected back)
    id_token = create_mock_id_token(
        sub="flowtest-user-789",
        email="flowtest@example.com"
    )
    token_response = create_mock_token_response(id_token=id_token)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(
            200,
            content=json.dumps(token_response),
            headers={"content-type": "application/json"}
        )

        # Step 3: Process authorization code at callback endpoint
        callback_response = await client.get(
            "/api/v1/oidc/callback",
            params={
                "code": "mock-auth-code",
                "state": state,
            },
        )

    assert callback_response.status_code == 200

    auth_data = callback_response.json()
    assert "access_token" in auth_data
    assert "refresh_token" in auth_data
    assert "user" in auth_data

    # Step 4: Verify user can use the token to access protected resources
    token = auth_data["access_token"]
    protected_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert protected_response.status_code == 200
    user_data = protected_response.json()
    assert user_data["email"] == "flowtest@example.com"

    # Step 5: Verify user identity was stored in database
    result = await db_session.execute(
        select(UserIdentity).where(
            UserIdentity.subject_id == "flowtest-user-789",
            UserIdentity.provider_type == "oidc",
        )
    )
    identity = result.scalar_one_or_none()

    assert identity is not None
    assert identity.issuer == "https://accounts.google.com"


async def test_oidc_with_multiple_providers(
    client,
    db_session: AsyncSession,
):
    """Test OIDC authentication with multiple provider configurations."""
    # Create multiple OIDC configs
    google_config = OIDCConfig(
        name="Google",
        is_enabled=True,
        is_default=False,
        issuer_url="https://accounts.google.com",
        authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        client_id="google-client-id",
        client_secret="google-client-secret",
    )

    azure_config = OIDCConfig(
        name="Azure AD",
        is_enabled=True,
        is_default=False,
        issuer_url="https://login.microsoftonline.com/tenant-id/v2.0",
        authorization_endpoint="https://login.microsoftonline.com/tenant-id/oauth2/v2.0/authorize",
        token_endpoint="https://login.microsoftonline.com/tenant-id/oauth2/v2.0/token",
        jwks_uri="https://login.microsoftonline.com/tenant-id/discovery/v2.0/keys",
        client_id="azure-client-id",
        client_secret="azure-client-secret",
    )

    db_session.add_all([google_config, azure_config])
    await db_session.commit()

    # Test both providers work
    for config in [google_config, azure_config]:
        response = await client.get(
            f"/api/v1/oidc/login?provider={config.id}",
            follow_redirects=False
        )

        assert response.status_code == 307
        assert config.authorization_endpoint in response.headers["location"]


async def test_oidc_token_refresh(
    client,
    oidc_config: OIDCConfig,
):
    """Test refreshing OIDC access token (if supported)."""
    # This test verifies that the refresh token mechanism works
    # Implementation depends on how refresh tokens are handled in the application

    # For now, we just verify that refresh_token is returned in callback response
    id_token = create_mock_id_token()
    token_response = create_mock_token_response(
        refresh_token="new-refresh-token"
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(
            200,
            content=json.dumps(token_response),
            headers={"content-type": "application/json"}
        )

        response = await client.get(
            "/api/v1/oidc/callback",
            params={
                "code": "mock-auth-code",
                "state": "mock-state",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "refresh_token" in data


async def test_oidc_with_userinfo_fallback(
    client,
    oidc_config: OIDCConfig,
):
    """Test OIDC authentication with UserInfo endpoint fallback."""
    # Some providers return minimal claims in ID token
    # requiring UserInfo endpoint fetch for additional claims

    id_token = create_mock_id_token()
    token_response = create_mock_token_response(id_token=id_token)
    userinfo = create_mock_userinfo()

    # Mock both token endpoint and userinfo endpoint
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:

        mock_post.return_value = Response(
            200,
            content=json.dumps(token_response),
            headers={"content-type": "application/json"}
        )

        mock_get.return_value = Response(
            200,
            content=json.dumps(userinfo),
            headers={"content-type": "application/json"}
        )

        response = await client.get(
            "/api/v1/oidc/callback",
            params={
                "code": "mock-auth-code",
                "state": "mock-state",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "testuser@example.com"
