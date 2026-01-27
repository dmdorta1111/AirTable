"""
Integration tests for SCIM 2.0 provisioning endpoints.

Tests the complete SCIM 2.0 user provisioning flow including:
- User creation (JIT provisioning from IdP)
- User retrieval and listing
- User updates (full and partial)
- User deactivation
- ServiceProviderConfig
- Resource types and schemas
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.user import User
from pybase.schemas.scim import (
    SCIMEmail,
    SCIMListResponse,
    SCIMMeta,
    SCIMName,
    SCIMServiceProviderConfig,
    SCIMUserCreate,
    SCIMUserResponse,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def scim_user_create() -> SCIMUserCreate:
    """Create a SCIM user creation request."""
    return SCIMUserCreate(
        schemas=["urn:ietf:params:scim:schemas:core:2.0:User"],
        user_name="john.doe@example.com",
        external_id="okta-12345",
        name=SCIMName(
            given_name="John",
            family_name="Doe",
            formatted="John Doe",
        ),
        display_name="John Doe",
        active=True,
        emails=[
            SCIMEmail(
                value="john.doe@example.com",
                type="work",
                primary=True,
            )
        ],
    )


@pytest.fixture
def scim_user_update() -> dict:
    """Create a SCIM user update request."""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "john.doe@example.com",
        "name": {
            "givenName": "John",
            "familyName": "Smith",
            "formatted": "John Smith",
        },
        "displayName": "John Smith",
        "active": True,
        "emails": [
            {
                "value": "john.doe@example.com",
                "type": "work",
                "primary": True,
            }
        ],
    }


@pytest.fixture
def scim_user_patch() -> dict:
    """Create a SCIM user patch request (partial update)."""
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "userName": "john.doe@example.com",
        "active": False,
        "displayName": "John Doe (Inactive)",
    }


# =============================================================================
# SCIM 2.0 ServiceProviderConfig
# =============================================================================


async def test_get_service_provider_config(async_client):
    """Test getting SCIM service provider configuration."""
    response = await async_client.get("/api/v1/scim/v2/ServiceProviderConfig")

    assert response.status_code == 200
    config = SCIMServiceProviderConfig(**response.json())

    # Verify authentication schemes
    assert config.patch is not None
    assert config.patch.supported is True
    assert config.bulk.supported is False
    assert config.filter.supported is True
    assert config.filter.max_results == 100
    assert config.change_password.supported is False
    assert config.sort.supported is True
    assert config.etag.supported is False

    # Verify authentication schemes
    assert len(config.authentication_schemes) > 0
    oauth_scheme = next(
        (s for s in config.authentication_schemes if s.type == "oauthbearertoken"),
        None,
    )
    assert oauth_scheme is not None
    assert oauth_scheme.primary is True


# =============================================================================
# SCIM 2.0 User Creation
# =============================================================================


async def test_create_user_via_scim(
    async_client, superuser_token_headers: dict, scim_user_create: SCIMUserCreate
):
    """Test creating a user via SCIM 2.0 protocol."""
    response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )

    assert response.status_code == 201
    user_data = response.json()

    # Verify SCIM response structure
    assert "schemas" in user_data
    assert "id" in user_data
    assert user_data["userName"] == "john.doe@example.com"
    assert user_data["displayName"] == "John Doe"
    assert user_data["active"] is True
    assert "emails" in user_data
    assert len(user_data["emails"]) > 0
    assert user_data["emails"][0]["value"] == "john.doe@example.com"
    assert "meta" in user_data
    assert user_data["meta"]["resourceType"] == "User"

    # Verify user was created in database
    user_id = user_data["id"]
    response = await async_client.get(f"/api/v1/users/{user_id}", headers=superuser_token_headers)
    assert response.status_code == 200
    db_user = response.json()
    assert db_user["email"] == "john.doe@example.com"
    assert db_user["name"] == "John Doe"
    assert db_user["is_active"] is True


async def test_create_user_duplicate_email(
    async_client, superuser_token_headers: dict, scim_user_create: SCIMUserCreate
):
    """Test creating a duplicate user via SCIM returns 409 Conflict."""
    # Create user first time
    await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )

    # Try to create same user again
    response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_create_user_with_minimal_fields(async_client, superuser_token_headers: dict):
    """Test creating a user with minimal required fields via SCIM."""
    minimal_user = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "minimal@example.com",
    }

    response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=minimal_user,
        headers=superuser_token_headers,
    )

    assert response.status_code == 201
    user_data = response.json()
    assert user_data["userName"] == "minimal@example.com"
    assert user_data["active"] is True  # Default to active


async def test_create_user_with_external_id(
    async_client, superuser_token_headers: dict
):
    """Test creating a user with external ID from IdP."""
    user_data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "external@example.com",
        "externalId": "okta-67890",
        "displayName": "External User",
    }

    response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=user_data,
        headers=superuser_token_headers,
    )

    assert response.status_code == 201
    result = response.json()
    assert result["userName"] == "external@example.com"
    # Note: external_id is stored but may not be returned in response


# =============================================================================
# SCIM 2.0 User Retrieval
# =============================================================================


async def test_get_user_by_id(
    async_client, superuser_token_headers: dict, scim_user_create: SCIMUserCreate
):
    """Test retrieving a user by ID via SCIM 2.0."""
    # Create user first
    create_response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )
    user_id = create_response.json()["id"]

    # Get user by ID
    response = await async_client.get(
        f"/api/v1/scim/v2/Users/{user_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    user_data = response.json()
    assert user_data["id"] == user_id
    assert user_data["userName"] == "john.doe@example.com"
    assert "meta" in user_data


async def test_get_nonexistent_user(async_client, superuser_token_headers: dict):
    """Test retrieving a non-existent user returns 404."""
    response = await async_client.get(
        "/api/v1/scim/v2/Users/00000000-0000-0000-0000-000000000000",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404


# =============================================================================
# SCIM 2.0 User Listing
# =============================================================================


async def test_list_users_empty(async_client, superuser_token_headers: dict):
    """Test listing users when database is empty (except superuser)."""
    response = await async_client.get(
        "/api/v1/scim/v2/Users",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    list_data = SCIMListResponse(**response.json())

    assert list_data.schemas == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    assert list_data.total_results >= 1  # At least the superuser
    assert list_data.start_index == 1
    assert isinstance(list_data.resources, list)


async def test_list_users_with_pagination(
    async_client, superuser_token_headers: dict
):
    """Test listing users with pagination parameters."""
    response = await async_client.get(
        "/api/v1/scim/v2/Users?startIndex=1&count=10",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    list_data = response.json()

    assert "totalResults" in list_data
    assert "startIndex" in list_data
    assert list_data["startIndex"] == 1
    assert "itemsPerPage" in list_data
    assert list_data["itemsPerPage"] <= 10
    assert "resources" in list_data


async def test_list_users_with_filter(async_client, superuser_token_headers: dict):
    """Test listing users with SCIM filter expression."""
    # Create a test user
    user_data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "filterable@example.com",
        "displayName": "Filterable User",
    }
    await async_client.post(
        "/api/v1/scim/v2/Users",
        json=user_data,
        headers=superuser_token_headers,
    )

    # Filter by userName
    response = await async_client.get(
        '/api/v1/scim/v2/Users?filter=userName eq "filterable@example.com"',
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    list_data = response.json()
    assert "resources" in list_data

    # Find our user in results
    users = list_data["resources"]
    found = any(u.get("userName") == "filterable@example.com" for u in users)
    assert found, "User not found in filtered results"


# =============================================================================
# SCIM 2.0 User Update (PUT)
# =============================================================================


async def test_update_user_full_replace(
    async_client,
    superuser_token_headers: dict,
    scim_user_create: SCIMUserCreate,
    scim_user_update: dict,
):
    """Test full user update via SCIM PUT (replace operation)."""
    # Create user first
    create_response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )
    user_id = create_response.json()["id"]

    # Update user with new data
    response = await async_client.put(
        f"/api/v1/scim/v2/Users/{user_id}",
        json=scim_user_update,
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["id"] == user_id
    assert updated_user["displayName"] == "John Smith"
    assert updated_user["name"]["formatted"] == "John Smith"
    assert updated_user["name"]["familyName"] == "Smith"

    # Verify update in database
    db_response = await async_client.get(
        f"/api/v1/users/{user_id}",
        headers=superuser_token_headers,
    )
    db_user = db_response.json()
    assert db_user["name"] == "John Smith"


async def test_update_user_deactivate(
    async_client,
    superuser_token_headers: dict,
    scim_user_create: SCIMUserCreate,
):
    """Test deactivating a user via SCIM PUT."""
    # Create active user
    create_response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )
    user_id = create_response.json()["id"]

    # Deactivate user
    update_data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "john.doe@example.com",
        "active": False,
    }
    response = await async_client.put(
        f"/api/v1/scim/v2/Users/{user_id}",
        json=update_data,
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["active"] is False


# =============================================================================
# SCIM 2.0 User Patch (PATCH)
# =============================================================================


async def test_patch_user_partial_update(
    async_client,
    superuser_token_headers: dict,
    scim_user_create: SCIMUserCreate,
    scim_user_patch: dict,
):
    """Test partial user update via SCIM PATCH."""
    # Create user first
    create_response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )
    user_id = create_response.json()["id"]

    # Patch user (partial update)
    response = await async_client.patch(
        f"/api/v1/scim/v2/Users/{user_id}",
        json=scim_user_patch,
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    patched_user = response.json()
    assert patched_user["id"] == user_id
    assert patched_user["active"] is False
    assert patched_user["displayName"] == "John Doe (Inactive)"


async def test_patch_user_display_name(
    async_client,
    superuser_token_headers: dict,
    scim_user_create: SCIMUserCreate,
):
    """Test patching only display name."""
    # Create user
    create_response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )
    user_id = create_response.json()["id"]

    # Patch only display name
    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "displayName": "Updated Name",
    }
    response = await async_client.patch(
        f"/api/v1/scim/v2/Users/{user_id}",
        json=patch_data,
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    patched_user = response.json()
    assert patched_user["displayName"] == "Updated Name"
    # Other fields should remain unchanged
    assert patched_user["active"] is True  # Was originally True


# =============================================================================
# SCIM 2.0 User Deletion
# =============================================================================


async def test_delete_user_soft_delete(
    async_client, superuser_token_headers: dict, scim_user_create: SCIMUserCreate
):
    """Test soft deleting a user via SCIM DELETE."""
    # Create user first
    create_response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=scim_user_create.model_dump(by_alias=True, exclude_none=True),
        headers=superuser_token_headers,
    )
    user_id = create_response.json()["id"]

    # Delete user
    response = await async_client.delete(
        f"/api/v1/scim/v2/Users/{user_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 204

    # Verify user is deactivated (soft delete)
    get_response = await async_client.get(
        f"/api/v1/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert get_response.status_code == 200
    user_data = get_response.json()
    assert user_data["is_active"] is False
    # deleted_at should be set
    assert user_data.get("deleted_at") is not None


async def test_delete_nonexistent_user(async_client, superuser_token_headers: dict):
    """Test deleting a non-existent user returns 404."""
    response = await async_client.delete(
        "/api/v1/scim/v2/Users/00000000-0000-0000-0000-000000000000",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404


# =============================================================================
# SCIM 2.0 Resource Types
# =============================================================================


async def test_list_resource_types(async_client):
    """Test listing SCIM resource types."""
    response = await async_client.get("/api/v1/scim/v2/ResourceTypes")

    assert response.status_code == 200
    data = response.json()

    assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    assert data["totalResults"] == 2
    assert len(data["resources"]) == 2

    # Verify User resource type
    user_resource = next((r for r in data["resources"] if r["id"] == "User"), None)
    assert user_resource is not None
    assert user_resource["name"] == "User"
    assert "endpoint" in user_resource
    assert "schema" in user_resource

    # Verify Group resource type
    group_resource = next((r for r in data["resources"] if r["id"] == "Group"), None)
    assert group_resource is not None
    assert group_resource["name"] == "Group"


async def test_get_user_resource_type(async_client):
    """Test getting User resource type details."""
    response = await async_client.get("/api/v1/scim/v2/ResourceTypes/User")

    assert response.status_code == 200
    resource_type = response.json()

    assert resource_type["id"] == "User"
    assert resource_type["name"] == "User"
    assert "endpoint" in resource_type
    assert resource_type["schema"] == "urn:ietf:params:scim:schemas:core:2.0:User"


async def test_get_group_resource_type(async_client):
    """Test getting Group resource type details."""
    response = await async_client.get("/api/v1/scim/v2/ResourceTypes/Group")

    assert response.status_code == 200
    resource_type = response.json()

    assert resource_type["id"] == "Group"
    assert resource_type["name"] == "Group"
    assert "endpoint" in resource_type


async def test_get_nonexistent_resource_type(async_client):
    """Test getting non-existent resource type returns 404."""
    response = await async_client.get("/api/v1/scim/v2/ResourceTypes/InvalidType")

    assert response.status_code == 404


# =============================================================================
# SCIM 2.0 Schemas
# =============================================================================


async def test_list_schemas(async_client):
    """Test listing SCIM schemas."""
    response = await async_client.get("/api/v1/scim/v2/Schemas")

    assert response.status_code == 200
    data = response.json()

    assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    assert data["totalResults"] == 3
    assert len(data["resources"]) == 3

    # Verify core schemas exist
    schema_ids = [r["id"] for r in data["resources"]]
    assert "urn:ietf:params:scim:schemas:core:2.0:User" in schema_ids
    assert "urn:ietf:params:scim:schemas:core:2.0:Group" in schema_ids
    assert "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig" in schema_ids


async def test_get_user_schema(async_client):
    """Test getting User schema definition."""
    response = await async_client.get(
        "/api/v1/scim/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:User"
    )

    assert response.status_code == 200
    schema = response.json()

    assert schema["id"] == "urn:ietf:params:scim:schemas:core:2.0:User"
    assert schema["name"] == "User"
    assert "attributes" in schema
    assert len(schema["attributes"]) > 0

    # Verify core attributes
    attribute_names = [a["name"] for a in schema["attributes"]]
    assert "userName" in attribute_names
    assert "name" in attribute_names
    assert "active" in attribute_names
    assert "emails" in attribute_names


async def test_get_group_schema(async_client):
    """Test getting Group schema definition."""
    response = await async_client.get(
        "/api/v1/scim/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group"
    )

    assert response.status_code == 200
    schema = response.json()

    assert schema["id"] == "urn:ietf:params:scim:schemas:core:2.0:Group"
    assert schema["name"] == "Group"
    assert "attributes" in schema


async def test_get_nonexistent_schema(async_client):
    """Test getting non-existent schema returns 404."""
    response = await async_client.get(
        "/api/v1/scim/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:Invalid"
    )

    assert response.status_code == 404


# =============================================================================
# SCIM 2.0 Groups (Not Implemented)
# =============================================================================


async def test_list_groups_returns_empty(async_client, superuser_token_headers: dict):
    """Test that group listing returns empty list (not yet implemented)."""
    response = await async_client.get(
        "/api/v1/scim/v2/Groups",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["totalResults"] == 0
    assert data["itemsPerPage"] == 0
    assert len(data["resources"]) == 0


async def test_get_group_returns_404(async_client, superuser_token_headers: dict):
    """Test that getting a specific group returns 404 (not yet implemented)."""
    response = await async_client.get(
        "/api/v1/scim/v2/Groups/some-group-id",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404


# =============================================================================
# SCIM 2.0 Authentication
# =============================================================================


async def test_scim_endpoints_require_authentication(async_client):
    """Test that SCIM endpoints require superuser authentication."""
    endpoints = [
        ("GET", "/api/v1/scim/v2/Users"),
        ("POST", "/api/v1/scim/v2/Users"),
        ("GET", "/api/v1/scim/v2/Users/some-id"),
        ("PUT", "/api/v1/scim/v2/Users/some-id"),
        ("PATCH", "/api/v1/scim/v2/Users/some-id"),
        ("DELETE", "/api/v1/scim/v2/Users/some-id"),
    ]

    for method, endpoint in endpoints:
        if method == "GET":
            response = await async_client.get(endpoint)
        elif method == "POST":
            response = await async_client.post(endpoint, json={})
        elif method == "PUT":
            response = await async_client.put(endpoint, json={})
        elif method == "PATCH":
            response = await async_client.patch(endpoint, json={})
        elif method == "DELETE":
            response = await async_client.delete(endpoint)

        # All should require authentication
        assert response.status_code == 401, f"{method} {endpoint} should require authentication"


# =============================================================================
# End-to-End SCIM Provisioning Flow
# =============================================================================


async def test_complete_scim_provisioning_flow(
    async_client, superuser_token_headers: dict
):
    """
    Test complete SCIM 2.0 provisioning lifecycle:
    1. Create user via SCIM
    2. Retrieve user via SCIM
    3. Update user via SCIM
    4. Deactivate user via SCIM
    """
    # Step 1: Create user
    user_data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "lifecycle@example.com",
        "displayName": "Lifecycle Test User",
        "active": True,
        "emails": [
            {
                "value": "lifecycle@example.com",
                "type": "work",
                "primary": True,
            }
        ],
    }

    create_response = await async_client.post(
        "/api/v1/scim/v2/Users",
        json=user_data,
        headers=superuser_token_headers,
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    # Step 2: Retrieve user
    get_response = await async_client.get(
        f"/api/v1/scim/v2/Users/{user_id}",
        headers=superuser_token_headers,
    )
    assert get_response.status_code == 200
    retrieved_user = get_response.json()
    assert retrieved_user["userName"] == "lifecycle@example.com"
    assert retrieved_user["active"] is True

    # Step 3: Update user
    update_data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "lifecycle@example.com",
        "displayName": "Updated Lifecycle User",
        "active": True,
    }
    update_response = await async_client.put(
        f"/api/v1/scim/v2/Users/{user_id}",
        json=update_data,
        headers=superuser_token_headers,
    )
    assert update_response.status_code == 200
    updated_user = update_response.json()
    assert updated_user["displayName"] == "Updated Lifecycle User"

    # Step 4: Deactivate user
    deactivate_data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "lifecycle@example.com",
        "active": False,
    }
    deactivate_response = await async_client.put(
        f"/api/v1/scim/v2/Users/{user_id}",
        json=deactivate_data,
        headers=superuser_token_headers,
    )
    assert deactivate_response.status_code == 200
    deactivated_user = deactivate_response.json()
    assert deactivated_user["active"] is False

    # Verify final state in database
    db_response = await async_client.get(
        f"/api/v1/users/{user_id}",
        headers=superuser_token_headers,
    )
    db_user = db_response.json()
    assert db_user["is_active"] is False
    assert db_user["name"] == "Updated Lifecycle User"
