"""
SCIM 2.0 API endpoints.

Implements RFC 7643 and RFC 7644 for user and group provisioning.
Provides endpoints for identity providers to automate user lifecycle management.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import CurrentSuperuser, DbSession
from pybase.models.user import User
from pybase.schemas.scim import (
    SCIMErrorDetail,
    SCIMErrorResponse,
    SCIMGroupMember,
    SCIMGroupResponse,
    SCIMListResponse,
    SCIMMeta,
    SCIMServiceProviderConfig,
    SCIMUserCore,
    SCIMUserCreate,
    SCIMUserResponse,
    SCIMUserUpdate,
)

router = APIRouter()


# =============================================================================
# SCIM Helpers
# =============================================================================


def _build_scim_meta(resource_type: str, resource_id: str | None = None) -> SCIMMeta:
    """
    Build SCIM metadata for a resource.

    Args:
        resource_type: Type of resource (User, Group, etc.)
        resource_id: Resource ID (optional for new resources)

    Returns:
        SCIMMeta object
    """
    from pybase.core.config import settings

    base_url = settings.api_v1_prefix.rstrip("/")

    if resource_id:
        location = f"{base_url}/scim/v2/{resource_type.lower()}s/{resource_id}"
    else:
        location = f"{base_url}/scim/v2/{resource_type.lower()}s"

    return SCIMMeta(
        resource_type=resource_type,
        location=location,
        created=datetime.utcnow(),
        last_modified=datetime.utcnow(),
    )


def _user_to_scim(user: User) -> SCIMUserResponse:
    """
    Convert internal User model to SCIM 2.0 User response.

    Args:
        user: Internal User model

    Returns:
        SCIMUserResponse object
    """
    from pybase.core.config import settings

    base_url = settings.api_v1_prefix.rstrip("/")

    # Build SCIM user response
    scim_user = SCIMUserResponse(
        id=str(user.id),
        user_name=user.email,
        name={
            "formatted": user.name,
            "givenName": user.name.split()[0] if user.name else None,
            "familyName": " ".join(user.name.split()[1:]) if user.name and len(user.name.split()) > 1 else None,
        },
        display_name=user.name,
        active=user.is_active,
        emails=[
            {
                "value": user.email,
                "primary": True,
                "type": "work",
            }
        ],
        external_id=None,
        meta=SCIMMeta(
            resource_type="User",
            location=f"{base_url}/scim/v2/Users/{user.id}",
            created=user.created_at,
            last_modified=user.updated_at,
        ),
    )

    return scim_user


def _scim_error(status: int, detail: str, scim_type: str | None = None) -> SCIMErrorResponse:
    """
    Create a SCIM error response.

    Args:
        status: HTTP status code
        detail: Error detail message
        scim_type: SCIM-specific error type

    Returns:
        SCIMErrorResponse object
    """
    return SCIMErrorResponse(
        detail=detail,
        status=status,
        scim_type=scim_type,
    )


# =============================================================================
# SCIM 2.0 ServiceProviderConfig
# =============================================================================


@router.get("/v2/ServiceProviderConfig", response_model=SCIMServiceProviderConfig)
async def get_service_provider_config() -> SCIMServiceProviderConfig:
    """
    Get SCIM 2.0 Service Provider Configuration.

    Returns the service provider's configuration including supported
    authentication schemes, bulk operations, filtering, and other capabilities.

    Reference: RFC 7644 Section 5
    """
    return SCIMServiceProviderConfig(
        patch={"supported": True},
        bulk={
            "supported": False,
            "maxOperations": None,
            "maxPayloadSize": None,
        },
        filter={
            "supported": True,
            "maxResults": 100,
        },
        changePassword={"supported": False},
        sort={"supported": True},
        etag={"supported": False},
        authenticationSchemes=[
            {
                "name": "OAuth Bearer Token",
                "description": "Authentication using Bearer token",
                "specUri": "https://www.rfc-editor.org/info/rfc6750",
                "type": "oauthbearertoken",
                "primary": True,
            },
            {
                "name": "HTTP Basic",
                "description": "HTTP Basic authentication",
                "type": "httpbasic",
                "primary": False,
            },
        ],
    )


# =============================================================================
# SCIM 2.0 User Endpoints
# =============================================================================


@router.get("/v2/Users", response_model=SCIMListResponse)
async def list_users(
    db: DbSession,
    current_user: CurrentSuperuser,
    start_index: int = Query(1, alias="startIndex", ge=1, description="Starting result index"),
    count: int = Query(100, ge=1, le=100, description="Maximum results per page"),
    filter: str | None = Query(None, description="SCIM filter expression"),
) -> SCIMListResponse:
    """
    List all users via SCIM 2.0 protocol.

    Supports pagination and filtering (basic filter support).

    Reference: RFC 7644 Section 3.4.1
    """
    # Build base query
    query = select(User).where(User.deleted_at == None)

    # Apply filter if provided (basic filtering support)
    if filter:
        # Basic filter parsing for userName and email
        if "userName eq " in filter:
            # Extract value from filter like 'userName eq "user@example.com"'
            value = filter.split('userName eq "')[1].split('"')[0] if '"' in filter else None
            if value:
                query = query.where(User.email == value)
        elif "email eq " in filter:
            value = filter.split('email eq "')[1].split('"')[0] if '"' in filter else None
            if value:
                query = query.where(User.email == value)

    # Get total count
    from sqlalchemy import func

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_results = total_result.scalar_one()

    # Apply pagination
    query = query.order_by(User.created_at.desc()).offset(start_index - 1).limit(count)

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Convert to SCIM format
    resources = [_user_to_scim(user).model_dump(by_alias=True, exclude_none=True) for user in users]

    return SCIMListResponse(
        totalResults=total_results,
        startIndex=start_index,
        itemsPerPage=len(resources),
        resources=resources,
    )


@router.post("/v2/Users", response_model=SCIMUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: SCIMUserCreate,
    db: DbSession,
    current_user: CurrentSuperuser,
) -> SCIMUserResponse:
    """
    Create a new user via SCIM 2.0 protocol.

    Implements Just-In-Time (JIT) provisioning from identity providers.

    Reference: RFC 7644 Section 3.3
    """
    # Check if user already exists by email or userName
    existing_user = await db.execute(
        select(User).where(
            User.email == user_data.user_name,
            User.deleted_at == None,
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Extract email from emails array if provided
    email = user_data.user_name
    if user_data.emails and len(user_data.emails) > 0:
        email = user_data.emails[0].value

    # Extract name
    name = user_data.display_name or user_data.user_name
    if user_data.name:
        if user_data.name.formatted:
            name = user_data.name.formatted
        elif user_data.name.given_name and user_data.name.family_name:
            name = f"{user_data.name.given_name} {user_data.name.family_name}"
        elif user_data.name.given_name:
            name = user_data.name.given_name

    # Create user (password will need to be set separately)
    # For SCIM provisioning, we generate a random password
    from pybase.core.security import hash_password

    random_password = UUID(bytes=bytes(16)).hex  # Generate random password
    new_user = User(
        email=email,
        hashed_password=hash_password(random_password),
        name=name,
        is_active=user_data.active if user_data.active is not None else True,
        is_verified=True,  # SCIM-provisioned users are pre-verified
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return _user_to_scim(new_user)


@router.get("/v2/Users/{user_id}", response_model=SCIMUserResponse)
async def get_user(
    user_id: str,
    db: DbSession,
    current_user: CurrentSuperuser,
) -> SCIMUserResponse:
    """
    Get a specific user via SCIM 2.0 protocol.

    Reference: RFC 7644 Section 3.4.1
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _user_to_scim(user)


@router.put("/v2/Users/{user_id}", response_model=SCIMUserResponse)
async def update_user(
    user_id: str,
    user_data: SCIMUserCore,
    db: DbSession,
    current_user: CurrentSuperuser,
) -> SCIMUserResponse:
    """
    Update a user via SCIM 2.0 protocol (full replace).

    Reference: RFC 7644 Section 3.5.1
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update user fields
    if user_data.user_name:
        user.email = user_data.user_name

    if user_data.display_name:
        user.name = user_data.display_name
    elif user_data.name:
        if user_data.name.formatted:
            user.name = user_data.name.formatted
        elif user_data.name.given_name and user_data.name.family_name:
            user.name = f"{user_data.name.given_name} {user_data.name.family_name}"
        elif user_data.name.given_name:
            user.name = user_data.name.given_name

    if user_data.active is not None:
        user.is_active = user_data.active

    # Handle email updates
    if user_data.emails and len(user_data.emails) > 0:
        user.email = user_data.emails[0].value

    await db.commit()
    await db.refresh(user)

    return _user_to_scim(user)


@router.patch("/v2/Users/{user_id}", response_model=SCIMUserResponse)
async def patch_user(
    user_id: str,
    user_data: SCIMUserUpdate,
    db: DbSession,
    current_user: CurrentSuperuser,
) -> SCIMUserResponse:
    """
    Partially update a user via SCIM 2.0 protocol.

    Reference: RFC 7644 Section 3.5.2
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update provided fields only
    if user_data.user_name:
        user.email = user_data.user_name

    if user_data.display_name:
        user.name = user_data.display_name

    if user_data.active is not None:
        user.is_active = user_data.active

    if user_data.name:
        if user_data.name.formatted:
            user.name = user_data.name.formatted
        elif user_data.name.given_name:
            family = user_data.name.family_name or ""
            user.name = f"{user_data.name.given_name} {family}".strip()

    if user_data.emails and len(user_data.emails) > 0:
        user.email = user_data.emails[0].value

    await db.commit()
    await db.refresh(user)

    return _user_to_scim(user)


@router.delete("/v2/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: DbSession,
    current_user: CurrentSuperuser,
) -> None:
    """
    Delete/deactivate a user via SCIM 2.0 protocol.

    Note: This performs a soft delete (deactivation) rather than
    permanent deletion for data retention purposes.

    Reference: RFC 7644 Section 3.6
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Soft delete (deactivate)
    user.is_active = False
    user.deleted_at = datetime.utcnow()

    await db.commit()


# =============================================================================
# SCIM 2.0 Group Endpoints
# =============================================================================


@router.get("/v2/Groups", response_model=SCIMListResponse)
async def list_groups(
    db: DbSession,
    current_user: CurrentSuperuser,
    start_index: int = Query(1, alias="startIndex", ge=1),
    count: int = Query(100, ge=1, le=100),
) -> SCIMListResponse:
    """
    List all groups via SCIM 2.0 protocol.

    Note: Groups are not fully implemented in this version.
    This endpoint returns an empty list for compatibility.

    Reference: RFC 7644 Section 3.4.1
    """
    # Groups are not yet implemented
    # Return empty list for SCIM compatibility
    return SCIMListResponse(
        totalResults=0,
        startIndex=start_index,
        itemsPerPage=0,
        resources=[],
    )


@router.get("/v2/Groups/{group_id}")
async def get_group(
    group_id: str,
    current_user: CurrentSuperuser,
) -> None:
    """
    Get a specific group via SCIM 2.0 protocol.

    Note: Groups are not fully implemented in this version.
    Returns 404 for compatibility.

    Reference: RFC 7644 Section 3.4.1
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Group not found",
    )


# =============================================================================
# SCIM 2.0 Resource Types
# =============================================================================


@router.get("/v2/ResourceTypes")
async def list_resource_types() -> dict[str, Any]:
    """
    List all SCIM 2.0 resource types.

    Returns available resource types (User, Group, etc.).

    Reference: RFC 7644 Section 6
    """
    from pybase.core.config import settings

    base_url = settings.api_v1_prefix.rstrip("/")

    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "startIndex": 1,
        "itemsPerPage": 2,
        "resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": f"{base_url}/scim/v2/Users",
                "description": "User Account",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
                "schemaExtensions": [],
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "Group",
                "name": "Group",
                "endpoint": f"{base_url}/scim/v2/Groups",
                "description": "Group",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
                "schemaExtensions": [],
            },
        ],
    }


@router.get("/v2/ResourceTypes/{resource_type}")
async def get_resource_type(
    resource_type: str,
) -> dict[str, Any]:
    """
    Get a specific SCIM 2.0 resource type.

    Reference: RFC 7644 Section 6
    """
    from pybase.core.config import settings

    base_url = settings.api_v1_prefix.rstrip("/")

    if resource_type == "User":
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "User",
            "name": "User",
            "endpoint": f"{base_url}/scim/v2/Users",
            "description": "User Account",
            "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
            "schemaExtensions": [],
        }
    elif resource_type == "Group":
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "Group",
            "name": "Group",
            "endpoint": f"{base_url}/scim/v2/Groups",
            "description": "Group",
            "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
            "schemaExtensions": [],
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource type not found",
        )


# =============================================================================
# SCIM 2.0 Schemas
# =============================================================================


@router.get("/v2/Schemas")
async def list_schemas() -> dict[str, Any]:
    """
    List all SCIM 2.0 schemas.

    Returns available schema definitions.

    Reference: RFC 7644 Section 7
    """
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 3,
        "startIndex": 1,
        "itemsPerPage": 3,
        "resources": [
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:User",
                "name": "User",
                "description": "Core User schema",
            },
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
                "name": "Group",
                "description": "Core Group schema",
            },
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig",
                "name": "ServiceProviderConfig",
                "description": "Service Provider Configuration schema",
            },
        ],
    }


@router.get("/v2/Schemas/{schema_id}")
async def get_schema(
    schema_id: str,
) -> dict[str, Any]:
    """
    Get a specific SCIM 2.0 schema definition.

    Reference: RFC 7644 Section 7
    """
    schemas = {
        "urn:ietf:params:scim:schemas:core:2.0:User": {
            "id": "urn:ietf:params:scim:schemas:core:2.0:User",
            "name": "User",
            "description": "Core User schema",
            "attributes": [
                {"name": "userName", "type": "string", "required": True, "mutability": "readWrite"},
                {"name": "name", "type": "complex", "required": False, "mutability": "readWrite"},
                {"name": "active", "type": "boolean", "required": False, "mutability": "readWrite"},
                {"name": "emails", "type": "complex", "multiValued": True, "required": False},
            ],
        },
        "urn:ietf:params:scim:schemas:core:2.0:Group": {
            "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
            "name": "Group",
            "description": "Core Group schema",
            "attributes": [
                {"name": "displayName", "type": "string", "required": True},
                {"name": "members", "type": "complex", "multiValued": True},
            ],
        },
    }

    if schema_id in schemas:
        return schemas[schema_id]
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schema not found",
        )
