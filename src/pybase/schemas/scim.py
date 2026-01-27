"""
SCIM 2.0 Schema definitions.

Implements SCIM 2.0 protocol schemas as defined in RFC 7643 and RFC 7644.
Provides schemas for users, groups, and service provider configuration.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic import EmailStr


# ============================================================================
# Core SCIM 2.0 Common Attributes
# ============================================================================


class SCIMMeta(BaseModel):
    """SCIM 2.0 metadata containing resource information."""

    resource_type: str = Field(..., description="Resource type name")
    created: Optional[datetime] = Field(None, description="Resource creation timestamp")
    last_modified: Optional[datetime] = Field(None, description="Last modification timestamp")
    location: str = Field(..., description="Resource URI endpoint")


class SCIMReference(BaseModel):
    """SCIM 2.0 reference to another resource."""

    value: Optional[str] = Field(None, description="Reference identifier")
    ref: Optional[str] = Field(None, alias="$ref", description="Reference URI")
    display: Optional[str] = Field(None, description="Human-readable display name")


class SCIMEmail(BaseModel):
    """SCIM 2.0 email attribute."""

    value: EmailStr = Field(..., description="Email address")
    type: Optional[str] = Field(None, description="Email type (work, home, other)")
    primary: Optional[bool] = Field(None, description="Whether this is the primary email")


class SCIMPhoneNumber(BaseModel):
    """SCIM 2.0 phone number attribute."""

    value: str = Field(..., description="Phone number")
    type: Optional[str] = Field(None, description="Phone type (work, home, mobile, etc.)")


class SCIMName(BaseModel):
    """SCIM 2.0 name attribute."""

    given_name: Optional[str] = Field(None, alias="givenName", description="First name")
    family_name: Optional[str] = Field(None, alias="familyName", description="Last name")
    middle_name: Optional[str] = Field(None, alias="middleName", description="Middle name")
    honorific_prefix: Optional[str] = Field(
        None, alias="honorificPrefix", description="Title (Mr., Mrs., etc.)"
    )
    honorific_suffix: Optional[str] = Field(
        None, alias="honorificSuffix", description="Suffix (Jr., III, etc.)"
    )
    formatted: Optional[str] = Field(None, description="Full formatted name")


class SCIMAddress(BaseModel):
    """SCIM 2.0 address attribute."""

    street_address: Optional[str] = Field(None, alias="streetAddress", description="Street address")
    locality: Optional[str] = Field(None, description="City")
    region: Optional[str] = Field(None, description="State/Province")
    postal_code: Optional[str] = Field(None, alias="postalCode", description="Postal code")
    country: Optional[str] = Field(None, description="Country name")
    formatted: Optional[str] = Field(None, description="Full formatted address")
    type: Optional[str] = Field(None, description="Address type (work, home, etc.)")
    primary: Optional[bool] = Field(None, description="Whether this is the primary address")


class SCIMEnterpriseUserExtension(BaseModel):
    """SCIM 2.0 enterprise user extension."""

    employee_number: Optional[str] = Field(None, alias="employeeNumber", description="Employee ID")
    cost_center: Optional[str] = Field(None, alias="costCenter", description="Cost center code")
    organization: Optional[str] = Field(None, description="Organization name")
    division: Optional[str] = Field(None, description="Division name")
    department: Optional[str] = Field(None, description="Department name")
    manager: Optional[SCIMReference] = Field(None, description="User's manager")


# ============================================================================
# SCIM 2.0 User Schema
# ============================================================================


class SCIMUserCore(BaseModel):
    """SCIM 2.0 User core attributes (RFC 7643 Section 4.1)."""

    user_name: str = Field(..., alias="userName", description="Unique user identifier")
    name: Optional[SCIMName] = Field(None, description="User's name")
    display_name: Optional[str] = Field(None, alias="displayName", description="Display name")
    nick_name: Optional[str] = Field(None, alias="nickName", description="Nickname")
    profile_url: Optional[str] = Field(None, alias="profileUrl", description="Profile URL")
    title: Optional[str] = Field(None, description="Job title")
    user_type: Optional[str] = Field(None, alias="userType", description="User type/category")
    preferred_language: Optional[str] = Field(
        None, alias="preferredLanguage", description="Preferred language"
    )
    locale: Optional[str] = Field(None, description="Geographic locale")
    timezone: Optional[str] = Field(None, description="Timezone")
    active: Optional[bool] = Field(None, description="Account active status")
    password: Optional[str] = Field(None, description="Password (for create/update only)")
    emails: Optional[list[SCIMEmail]] = Field(None, description="Email addresses")
    phone_numbers: Optional[list[SCIMPhoneNumber]] = Field(
        None, alias="phoneNumbers", description="Phone numbers"
    )
    addresses: Optional[list[SCIMAddress]] = Field(None, description="Postal addresses")
    photos: Optional[list[dict]] = Field(None, description="Profile photos")
    groups: Optional[list[SCIMReference]] = Field(None, description="Group memberships")


class SCIMUserCreate(SCIMUserCore):
    """SCIM 2.0 User creation schema."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:schemas:core:2.0:User"],
        description="SCIM schemas used",
    )
    external_id: Optional[str] = Field(
        None, alias="externalId", description="External identifier from IdP"
    )


class SCIMUserUpdate(BaseModel):
    """SCIM 2.0 User update schema (partial updates)."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        description="SCIM schemas used",
    )
    user_name: Optional[str] = Field(None, alias="userName")
    name: Optional[SCIMName] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    active: Optional[bool] = None
    emails: Optional[list[SCIMEmail]] = None
    phone_numbers: Optional[list[SCIMPhoneNumber]] = Field(None, alias="phoneNumbers")
    addresses: Optional[list[SCIMAddress]] = None


class SCIMUserResponse(SCIMUserCore):
    """SCIM 2.0 User response schema."""

    id: str = Field(..., description="User unique identifier")
    external_id: Optional[str] = Field(None, alias="externalId", description="External identifier")
    meta: SCIMMeta = Field(..., description="Resource metadata")
    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:schemas:core:2.0:User"],
        description="SCIM schemas used",
    )

    model_config = {"from_attributes": True, "populate_by_name": True}


# ============================================================================
# SCIM 2.0 Group Schema
# ============================================================================


class SCIMGroupMember(BaseModel):
    """SCIM 2.0 Group member reference."""

    value: str = Field(..., description="Member unique identifier")
    ref: Optional[str] = Field(None, alias="$ref", description="Member resource URI")
    display: Optional[str] = Field(None, description="Member display name")
    type: str = Field(..., description="Member resource type (User or Group)")


class SCIMGroupCore(BaseModel):
    """SCIM 2.0 Group core attributes (RFC 7643 Section 4.2)."""

    display_name: str = Field(..., alias="displayName", description="Group display name")
    members: Optional[list[SCIMGroupMember]] = Field(None, description="Group members")


class SCIMGroupCreate(SCIMGroupCore):
    """SCIM 2.0 Group creation schema."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:schemas:core:2.0:Group"],
        description="SCIM schemas used",
    )
    external_id: Optional[str] = Field(
        None, alias="externalId", description="External identifier from IdP"
    )


class SCIMGroupUpdate(BaseModel):
    """SCIM 2.0 Group update schema (partial updates)."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        description="SCIM schemas used",
    )
    display_name: Optional[str] = Field(None, alias="displayName")
    members: Optional[list[SCIMGroupMember]] = None


class SCIMGroupResponse(SCIMGroupCore):
    """SCIM 2.0 Group response schema."""

    id: str = Field(..., description="Group unique identifier")
    external_id: Optional[str] = Field(None, alias="externalId", description="External identifier")
    meta: SCIMMeta = Field(..., description="Resource metadata")
    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:schemas:core:2.0:Group"],
        description="SCIM schemas used",
    )

    model_config = {"from_attributes": True, "populate_by_name": True}


# ============================================================================
# SCIM 2.0 List Response
# ============================================================================


class SCIMListResponse(BaseModel):
    """SCIM 2.0 List query response (RFC 7644 Section 3.4.2)."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        description="SCIM schemas used",
    )
    total_results: int = Field(..., alias="totalResults", description="Total resource count")
    start_index: int = Field(..., alias="startIndex", description="Starting result index")
    items_per_page: int = Field(..., alias="itemsPerPage", description="Results per page")
    resources: list[dict] = Field(..., description="List of resources")

    model_config = {"populate_by_name": True}


# ============================================================================
# SCIM 2.0 Service Provider Configuration
# ============================================================================


class SCIMAuthenticationScheme(BaseModel):
    """SCIM 2.0 authentication scheme."""

    name: str = Field(..., description="Authentication scheme name")
    description: Optional[str] = Field(None, description="Scheme description")
    spec_uri: Optional[str] = Field(
        None, alias="specUri", description="Specification URI reference"
    )
    documentation_uri: Optional[str] = Field(
        None, alias="documentationUri", description="Documentation URI"
    )
    type: str = Field(..., description="Scheme type (oauthbearertoken, etc.)")
    primary: Optional[bool] = Field(None, description="Whether this is the primary scheme")


class SCIMBulkConfig(BaseModel):
    """SCIM 2.0 bulk operations configuration."""

    supported: bool = Field(..., description="Whether bulk is supported")
    max_operations: Optional[int] = Field(None, alias="maxOperations", description="Max operations")
    max_payload_size: Optional[int] = Field(
        None, alias="maxPayloadSize", description="Max payload size (bytes)"
    )


class SCIMFilterConfig(BaseModel):
    """SCIM 2.0 filter configuration."""

    supported: bool = Field(..., description="Whether filtering is supported")
    max_results: Optional[int] = Field(None, alias="maxResults", description="Max results")


class SCIMEtagConfig(BaseModel):
    """SCIM 2.0 ETag configuration."""

    supported: bool = Field(..., description="Whether ETags are supported")


class SCIMChangePasswordConfig(BaseModel):
    """SCIM 2.0 change password configuration."""

    supported: bool = Field(..., description="Whether password change is supported")


class SCIMSortConfig(BaseModel):
    """SCIM 2.0 sort configuration."""

    supported: bool = Field(..., description="Whether sorting is supported")


class SCIMSupported(BaseModel):
    """SCIM 2.0 supported operations."""

    supported: bool = Field(..., description="Whether operation is supported")


class SCIMServiceProviderConfig(BaseModel):
    """SCIM 2.0 Service Provider Config (RFC 7644 Section 5)."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        description="SCIM schemas used",
    )
    patch: SCIMSupported = Field(..., description="Patch operation support")
    bulk: SCIMBulkConfig = Field(..., description="Bulk operation support")
    filter: SCIMFilterConfig = Field(..., description="Filter support")
    change_password: SCIMChangePasswordConfig = Field(
        None, alias="changePassword", description="Password change support"
    )
    sort: SCIMSortConfig = Field(..., description="Sort support")
    etag: SCIMEtagConfig = Field(..., description="ETag support")
    authentication_schemes: list[SCIMAuthenticationScheme] = Field(
        None, alias="authenticationSchemes", description="Supported authentication schemes"
    )

    model_config = {"populate_by_name": True}


# ============================================================================
# SCIM 2.0 Resource Types
# ============================================================================


class SCIMResourceTypeSchema(BaseModel):
    """SCIM 2.0 resource type schema definition."""

    name: str = Field(..., description="Schema name")
    description: Optional[str] = Field(None, description="Schema description")


class SCIMResourceTypeEndpoint(BaseModel):
    """SCIM 2.0 resource type endpoint."""

    capabilities: Optional[list[str]] = Field(None, description="Endpoint capabilities")
    description: Optional[str] = Field(None, description="Endpoint description")


class SCIMResourceType(BaseModel):
    """SCIM 2.0 resource type definition (RFC 7644 Section 6)."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
        description="SCIM schemas used",
    )
    id: str = Field(..., description="Resource type identifier")
    name: str = Field(..., description="Resource type name")
    endpoint: str = Field(..., description="Resource endpoint")
    description: Optional[str] = Field(None, description="Resource type description")
    schema: str = Field(..., description="Primary schema URI")
    schema_extensions: Optional[list[SCIMResourceTypeSchema]] = Field(
        None, alias="schemaExtensions", description="Extended schema definitions"
    )

    model_config = {"populate_by_name": True}


# ============================================================================
# SCIM 2.0 Schema Definitions
# ============================================================================


class SCIMSchemaAttribute(BaseModel):
    """SCIM 2.0 schema attribute definition."""

    name: str = Field(..., description="Attribute name")
    type: str = Field(..., description="Attribute type (string, boolean, etc.)")
    multi_valued: bool = Field(..., alias="multiValued", description="Multi-valued attribute")
    description: Optional[str] = Field(None, description="Attribute description")
    required: Optional[bool] = Field(None, description="Required attribute")
    case_exact: Optional[bool] = Field(None, alias="caseExact", description="Case-sensitive matching")
    mutability: Optional[str] = Field(None, description="Mutability (readWrite, readOnly, etc.)")
    returned: Optional[str] = Field(None, description="When returned (always, never, etc.)")
    uniqueness: Optional[str] = Field(None, description="Uniqueness constraint")


class SCIMSchema(BaseModel):
    """SCIM 2.0 schema definition (RFC 7644 Section 7)."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:schemas:core:2.0:Schema"],
        description="SCIM schemas used",
    )
    id: str = Field(..., description="Schema identifier URI")
    name: str = Field(..., description="Schema name")
    description: Optional[str] = Field(None, description="Schema description")
    attributes: list[SCIMSchemaAttribute] = Field(..., description="Schema attributes")

    model_config = {"populate_by_name": True}


# ============================================================================
# SCIM 2.0 Patch Operation
# ============================================================================


class SCIMPatchOperation(BaseModel):
    """SCIM 2.0 patch operation (RFC 7644 Section 3.5.2)."""

    op: str = Field(..., description="Operation (add, replace, remove)")
    path: Optional[str] = Field(None, description="Target path")
    value: Optional[Any] = Field(None, description="Operation value")


class SCIMPatchRequest(BaseModel):
    """SCIM 2.0 patch request body."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        description="SCIM schemas used",
    )
    operations: list[SCIMPatchOperation] = Field(..., description="Patch operations")

    model_config = {"populate_by_name": True}


# ============================================================================
# SCIM 2.0 Search Request
# ============================================================================


class SCIMSearchRequest(BaseModel):
    """SCIM 2.0 search request (RFC 7644 Section 3.4.3)."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
        description="SCIM schemas used",
    )
    attributes: Optional[list[str]] = Field(None, description="Attributes to return")
    excluded_attributes: Optional[list[str]] = Field(
        None, alias="excludedAttributes", description="Attributes to exclude"
    )
    filter: Optional[str] = Field(None, description="Search filter expression")
    start_index: Optional[int] = Field(None, alias="startIndex", description="Starting index")
    count: Optional[int] = Field(None, description="Maximum results")
    sort_by: Optional[str] = Field(None, alias="sortBy", description="Sort attribute")
    sort_order: Optional[str] = Field(None, alias="sortOrder", description="Sort order (ascending/descending)")

    model_config = {"populate_by_name": True}


# ============================================================================
# SCIM 2.0 Error Response
# ============================================================================


class SCIMErrorDetail(BaseModel):
    """SCIM 2.0 error detail."""

    scim_type: Optional[str] = Field(None, alias="scimType", description="SCIM error type")
    detail: str = Field(..., description="Error description")
    status: int = Field(..., description="HTTP status code")


class SCIMErrorResponse(BaseModel):
    """SCIM 2.0 error response (RFC 7644 Section 3.12)."""

    schemas: list[str] = Field(
        default=["urn:ietf:params:scim:api:messages:2.0:Error"],
        description="SCIM schemas used",
    )
    scim_type: Optional[str] = Field(None, alias="scimType", description="SCIM error type")
    detail: str = Field(..., description="Error description")
    status: int = Field(..., description="HTTP status code")

    model_config = {"populate_by_name": True}
