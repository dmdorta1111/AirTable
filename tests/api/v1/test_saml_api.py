"""
Integration tests for SAML 2.0 authentication endpoints.

Tests the complete SAML authentication flow including:
- SAML login initiation
- SAML callback processing
- SAML metadata generation
- JIT user provisioning
- Error handling
"""

import base64
import zlib
from xml.etree import ElementTree as ET

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.saml_config import SAMLConfig
from pybase.models.user import User
from pybase.models.user_identity import UserIdentity


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def saml_config(db_session: AsyncSession) -> SAMLConfig:
    """Create a test SAML configuration."""
    config = SAMLConfig(
        name="Test SAML IdP",
        is_enabled=True,
        is_default=True,
        # Identity Provider settings
        idp_entity_id="https://idp.example.com/entityid",
        idp_sso_url="https://idp.example.com/sso",
        idp_slo_url="https://idp.example.com/slo",
        idp_x509_cert="""MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1234567890abcdefghijklmnopqrstuv
        wxyz1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890ABCDEFGHIJK
        LMNOPQRSTUVWXYZ==""",
        # Service Provider settings
        sp_entity_id="https://pybase.example.com/sp/entityid",
        sp_acs_url="https://pybase.example.com/api/v1/saml/acs",
        sp_slo_url="https://pybase.example.com/api/v1/saml/slo",
        name_id_format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
        # Attribute mapping
        attribute_email="email",
        attribute_first_name="firstName",
        attribute_last_name="lastName",
        attribute_display_name="displayName",
        attribute_groups="groups",
        # Role mapping
        role_mapping_admin="Admins",
        role_mapping_user="Users",
        # JIT provisioning
        enable_jit_provisioning=True,
        default_role="user",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest_asyncio.fixture
async def saml_config_disabled(db_session: AsyncSession) -> SAMLConfig:
    """Create a disabled SAML configuration for testing."""
    config = SAMLConfig(
        name="Disabled SAML IdP",
        is_enabled=False,
        is_default=False,
        idp_entity_id="https://disabled-idp.example.com/entityid",
        idp_sso_url="https://disabled-idp.example.com/sso",
        idp_x509_cert="""MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1234567890""",
        sp_entity_id="https://pybase.example.com/sp/entityid",
        sp_acs_url="https://pybase.example.com/api/v1/saml/acs",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


def create_mock_saml_response(
    name_id: str = "testuser@example.com",
    email: str = "testuser@example.com",
    first_name: str = "Test",
    last_name: str = "User",
    issuer: str = "https://idp.example.com/entityid",
) -> str:
    """
    Create a mock SAML response for testing.

    Returns a base64-encoded SAML response XML.
    """
    saml_assertion = f"""
    <saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                    ID="_{hash(name_id)}"
                    IssueInstant="2024-01-27T12:00:00Z"
                    Version="2.0">
        <saml:Issuer>{issuer}</saml:Issuer>
        <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
            <ds:SignedInfo>
                <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
                <ds:Reference URI="#_{hash(name_id)}">
                    <ds:Transforms>
                        <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                        <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:Transforms>
                    <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmlenc#sha1"/>
                    <ds:DigestValue>1234567890abcdef</ds:DigestValue>
                </ds:Reference>
            </ds:SignedInfo>
            <ds:SignatureValue>mocksignaturevalue</ds:SignatureValue>
        </ds:Signature>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified">{name_id}</saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData NotOnOrAfter="2024-01-27T12:05:00Z"
                                               Recipient="https://pybase.example.com/api/v1/saml/acs"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="2024-01-27T11:55:00Z" NotOnOrAfter="2024-01-27T12:05:00Z">
            <saml:AudienceRestriction>
                <saml:Audience>https://pybase.example.com/sp/entityid</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AttributeStatement>
            <saml:Attribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{email}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="firstName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{first_name}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="lastName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{last_name}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="displayName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>{first_name} {last_name}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="groups" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                <saml:AttributeValue>Users</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
    """

    saml_response = f"""
    <samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                   ID="_mock-response-id"
                   InResponseTo="_mock-request-id"
                   IssueInstant="2024-01-27T12:00:00Z"
                   Version="2.0"
                   Destination="https://pybase.example.com/api/v1/saml/acs">
        <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">{issuer}</saml:Issuer>
        <samlp:Status>
            <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
        </samlp:Status>
        {saml_assertion}
    </samlp:Response>
    """

    # Encode SAML response (deflate + base64)
    deflated = zlib.compress(saml_response.strip().encode("utf-8"))
    encoded = base64.b64encode(deflated).decode("utf-8")

    return encoded


# =============================================================================
# SAML Metadata Tests
# =============================================================================


async def test_saml_metadata_returns_xml(client, saml_config: SAMLConfig):
    """Test that SAML metadata endpoint returns valid XML."""
    response = await client.get("/api/v1/saml/metadata")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml; charset=utf-8"
    assert "content-disposition" in response.headers

    # Verify XML content
    xml_content = response.text
    assert "<?xml" in xml_content
    assert "EntityDescriptor" in xml_content
    assert saml_config.sp_entity_id in xml_content
    assert saml_config.sp_acs_url in xml_content


async def test_saml_metadata_with_specific_config(client, saml_config: SAMLConfig):
    """Test SAML metadata endpoint with specific config ID."""
    response = await client.get(
        f"/api/v1/saml/metadata?idp_id={saml_config.id}"
    )

    assert response.status_code == 200
    assert saml_config.sp_entity_id in response.text


async def test_saml_metadata_missing_config(client, db_session: AsyncSession):
    """Test SAML metadata endpoint with non-existent config."""
    response = await client.get("/api/v1/saml/metadata?idp_id=00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


# =============================================================================
# SAML Login Initiation Tests
# =============================================================================


async def test_saml_login_init_redirects(client, saml_config: SAMLConfig):
    """Test that SAML login initiation returns redirect."""
    response = await client.get(
        f"/api/v1/saml/login?idp_id={saml_config.id}",
        follow_redirects=False
    )

    assert response.status_code == 307
    assert "location" in response.headers

    # Verify redirect URL contains IdP SSO URL
    redirect_url = response.headers["location"]
    assert saml_config.idp_sso_url in redirect_url
    assert "SAMLRequest=" in redirect_url
    assert "RelayState=" in redirect_url


async def test_saml_login_init_disabled_config(
    client,
    saml_config_disabled: SAMLConfig,
):
    """Test that disabled SAML config returns 403."""
    response = await client.get(
        f"/api/v1/saml/login?idp_id={saml_config_disabled.id}"
    )

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


async def test_saml_login_init_missing_config(client):
    """Test SAML login with non-existent config."""
    response = await client.get(
        "/api/v1/saml/login?idp_id=00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


async def test_saml_login_init_default_config(
    client,
    saml_config: SAMLConfig,
):
    """Test SAML login with default config (no idp_id specified)."""
    response = await client.get("/api/v1/saml/login", follow_redirects=False)

    assert response.status_code == 307
    assert saml_config.idp_sso_url in response.headers["location"]


# =============================================================================
# SAML Callback (ACS) Tests
# =============================================================================


async def test_saml_acs_creates_user_on_first_login(
    client,
    saml_config: SAMLConfig,
    db_session: AsyncSession,
):
    """Test that SAML callback creates new user via JIT provisioning."""
    # Create mock SAML response
    saml_response = create_mock_saml_response(
        name_id="newuser@example.com",
        email="newuser@example.com",
        first_name="New",
        last_name="User",
    )

    # Send SAML response to ACS endpoint
    response = await client.post(
        "/api/v1/saml/acs",
        params={
            "SAMLResponse": saml_response,
            "RelayState": "test-relay-state",
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
    assert "New" in user.name
    assert user.is_active is True

    # Verify user identity was linked
    result = await db_session.execute(
        select(UserIdentity).where(
            UserIdentity.provider_type == "saml",
            UserIdentity.subject_id == "newuser@example.com",
        )
    )
    identity = result.scalar_one_or_none()

    assert identity is not None
    assert identity.user_id == str(user.id)


async def test_saml_acs_links_existing_user(
    client,
    saml_config: SAMLConfig,
    db_session: AsyncSession,
):
    """Test that SAML callback links to existing user on subsequent login."""
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
        provider_type="saml",
        config_id=str(saml_config.id),
        subject_id="existing@example.com",
        issuer="https://idp.example.com/entityid",
    )
    db_session.add(identity)
    await db_session.commit()

    # Create mock SAML response for existing user
    saml_response = create_mock_saml_response(
        name_id="existing@example.com",
        email="existing@example.com",
        first_name="Updated",
        last_name="Name",
    )

    # Send SAML response to ACS endpoint
    response = await client.post(
        "/api/v1/saml/acs",
        params={
            "SAMLResponse": saml_response,
            "RelayState": "test-relay-state",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["was_created"] is False
    assert data["user"]["email"] == "existing@example.com"


async def test_saml_acs_invalid_saml_response(
    client,
    saml_config: SAMLConfig,
):
    """Test that invalid SAML response returns 400."""
    response = await client.post(
        "/api/v1/saml/acs",
        params={
            "SAMLResponse": "invalid-base64-encoded-response",
            "RelayState": "test-relay-state",
        },
    )

    assert response.status_code == 400


async def test_saml_acs_missing_saml_response(client):
    """Test that missing SAML response parameter returns 422."""
    response = await client.post("/api/v1/saml/acs", params={"RelayState": "test"})

    assert response.status_code == 422  # Unprocessable Entity (validation error)


# =============================================================================
# SAML Config Info Tests
# =============================================================================


async def test_saml_config_info_unauthenticated(client):
    """Test that config info endpoint requires authentication."""
    response = await client.get("/api/v1/saml/config")

    assert response.status_code == 401


async def test_saml_config_info_authenticated(
    client,
    auth_headers: dict,
    saml_config: SAMLConfig,
):
    """Test that authenticated user can get SAML config info."""
    response = await client.get(
        "/api/v1/saml/config",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert "sso_enabled" in data
    assert "saml_configs" in data
    assert len(data["saml_configs"]) > 0

    # Verify sensitive data is not exposed
    config = data["saml_configs"][0]
    assert "idp_x509_cert" not in config
    assert "idp_sso_url" not in config
    assert "idp_entity_id" in config
    assert "name" in config


# =============================================================================
# SAML Error Handling Tests
# =============================================================================


async def test_saml_login_with_sso_disabled(
    client,
    saml_config: SAMLConfig,
    monkeypatch,
):
    """Test that SAML login returns 403 when SSO is disabled globally."""
    # Temporarily disable SSO
    from pybase.core import config

    monkeypatch.setattr(config.settings, "sso_enabled", False)

    response = await client.get(f"/api/v1/saml/login?idp_id={saml_config.id}")

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


# =============================================================================
# Integration Tests
# =============================================================================


async def test_complete_saml_flow(
    client,
    saml_config: SAMLConfig,
    db_session: AsyncSession,
):
    """Test the complete SAML authentication flow from start to finish."""
    # Step 1: Initiate SAML login
    login_response = await client.get(
        f"/api/v1/saml/login?idp_id={saml_config.id}",
        follow_redirects=False,
    )

    assert login_response.status_code == 307
    redirect_url = login_response.headers["location"]
    assert saml_config.idp_sso_url in redirect_url

    # Step 2: Simulate IdP authentication and callback
    # (In real flow, user authenticates at IdP and is redirected back)
    saml_response = create_mock_saml_response(
        name_id="flowtest@example.com",
        email="flowtest@example.com",
        first_name="Flow",
        last_name="Test",
    )

    # Step 3: Process SAML response at ACS endpoint
    acs_response = await client.post(
        "/api/v1/saml/acs",
        params={
            "SAMLResponse": saml_response,
            "RelayState": "test-relay-state",
        },
    )

    assert acs_response.status_code == 200

    auth_data = acs_response.json()
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
            UserIdentity.subject_id == "flowtest@example.com",
            UserIdentity.provider_type == "saml",
        )
    )
    identity = result.scalar_one_or_none()

    assert identity is not None
    assert identity.issuer == "https://idp.example.com/entityid"
