"""
SSO configuration management endpoints.

Handles CRUD operations for SAML and OIDC configurations (admin only).
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from pybase.api.deps import CurrentSuperuser, DbSession
from pybase.models.oidc_config import OIDCConfig
from pybase.models.saml_config import SAMLConfig

router = APIRouter()


# =============================================================================
# Request/Response Models - SAML
# =============================================================================


class SAMLConfigCreateRequest(BaseModel):
    """Create SAML configuration request."""

    name: str = Field(..., min_length=1, max_length=255)
    idp_entity_id: str = Field(..., max_length=500)
    idp_sso_url: str = Field(..., max_length=500)
    idp_slo_url: str | None = Field(None, max_length=500)
    idp_x509_cert: str = Field(..., description="X.509 certificate in PEM format")
    sp_entity_id: str = Field(..., max_length=500)
    sp_acs_url: str = Field(..., max_length=500)
    sp_slo_url: str | None = Field(None, max_length=500)
    name_id_format: str = Field(
        "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        max_length=255,
    )
    attribute_mapping: dict[str, str] | None = None
    jit_provisioning_enabled: bool = False
    role_mapping: dict[str, list[str]] | None = None
    group_attribute: str | None = Field("groups", max_length=255)
    is_enabled: bool = False
    is_default: bool = False


class SAMLConfigUpdateRequest(BaseModel):
    """Update SAML configuration request."""

    name: str | None = Field(None, min_length=1, max_length=255)
    idp_entity_id: str | None = Field(None, max_length=500)
    idp_sso_url: str | None = Field(None, max_length=500)
    idp_slo_url: str | None = Field(None, max_length=500)
    idp_x509_cert: str | None = Field(None, description="X.509 certificate in PEM format")
    sp_entity_id: str | None = Field(None, max_length=500)
    sp_acs_url: str | None = Field(None, max_length=500)
    sp_slo_url: str | None = Field(None, max_length=500)
    name_id_format: str | None = Field(None, max_length=255)
    attribute_mapping: dict[str, str] | None = None
    jit_provisioning_enabled: bool | None = None
    role_mapping: dict[str, list[str]] | None = None
    group_attribute: str | None = Field(None, max_length=255)
    is_enabled: bool | None = None
    is_default: bool | None = None


class SAMLConfigResponse(BaseModel):
    """SAML configuration response."""

    id: str
    name: str
    is_enabled: bool
    is_default: bool
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: str | None
    idp_x509_cert: str
    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: str | None
    name_id_format: str
    attribute_mapping: dict[str, str] | None
    jit_provisioning_enabled: bool
    role_mapping: dict[str, list[str]] | None
    group_attribute: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


# =============================================================================
# Request/Response Models - OIDC
# =============================================================================


class OIDCConfigCreateRequest(BaseModel):
    """Create OIDC configuration request."""

    name: str = Field(..., min_length=1, max_length=255)
    issuer_url: str = Field(..., max_length=500)
    authorization_endpoint: str = Field(..., max_length=500)
    token_endpoint: str = Field(..., max_length=500)
    jwks_uri: str = Field(..., max_length=500)
    userinfo_endpoint: str | None = Field(None, max_length=500)
    end_session_endpoint: str | None = Field(None, max_length=500)
    client_id: str = Field(..., max_length=255)
    client_secret: str = Field(..., max_length=500, description="Client secret")
    scope: str = Field("openid email profile", max_length=500)
    response_type: str = Field("code", max_length=50)
    response_mode: str | None = Field("query", max_length=50)
    claim_mapping: dict[str, str] | None = None
    jit_provisioning_enabled: bool = False
    role_mapping: dict[str, list[str]] | None = None
    group_claim: str | None = Field("groups", max_length=255)
    validate_signature: bool = True
    validate_issuer: bool = True
    validate_audience: bool = True
    allowed_audiences: list[str] | None = None
    is_enabled: bool = False
    is_default: bool = False


class OIDCConfigUpdateRequest(BaseModel):
    """Update OIDC configuration request."""

    name: str | None = Field(None, min_length=1, max_length=255)
    issuer_url: str | None = Field(None, max_length=500)
    authorization_endpoint: str | None = Field(None, max_length=500)
    token_endpoint: str | None = Field(None, max_length=500)
    jwks_uri: str | None = Field(None, max_length=500)
    userinfo_endpoint: str | None = Field(None, max_length=500)
    end_session_endpoint: str | None = Field(None, max_length=500)
    client_id: str | None = Field(None, max_length=255)
    client_secret: str | None = Field(None, max_length=500)
    scope: str | None = Field(None, max_length=500)
    response_type: str | None = Field(None, max_length=50)
    response_mode: str | None = Field(None, max_length=50)
    claim_mapping: dict[str, str] | None = None
    jit_provisioning_enabled: bool | None = None
    role_mapping: dict[str, list[str]] | None = None
    group_claim: str | None = Field(None, max_length=255)
    validate_signature: bool | None = None
    validate_issuer: bool | None = None
    validate_audience: bool | None = None
    allowed_audiences: list[str] | None = None
    is_enabled: bool | None = None
    is_default: bool | None = None


class OIDCConfigResponse(BaseModel):
    """OIDC configuration response."""

    id: str
    name: str
    is_enabled: bool
    is_default: bool
    issuer_url: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str | None
    end_session_endpoint: str | None
    client_id: str
    # client_secret is excluded from response for security
    scope: str
    response_type: str
    response_mode: str | None
    claim_mapping: dict[str, str] | None
    jit_provisioning_enabled: bool
    role_mapping: dict[str, list[str]] | None
    group_claim: str | None
    validate_signature: bool
    validate_issuer: bool
    validate_audience: bool
    allowed_audiences: dict[str, list[str]] | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


# =============================================================================
# SAML Configuration Endpoints
# =============================================================================


@router.get("/saml", response_model=list[SAMLConfigResponse])
async def list_saml_configs(
    current_user: CurrentSuperuser,
    db: DbSession,
) -> list[SAMLConfig]:
    """
    List all SAML configurations (superuser only).
    """
    result = await db.execute(
        select(SAMLConfig).order_by(SAMLConfig.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/saml/{config_id}", response_model=SAMLConfigResponse)
async def get_saml_config(
    config_id: str,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> SAMLConfig:
    """
    Get a specific SAML configuration (superuser only).
    """
    result = await db.execute(
        select(SAMLConfig).where(SAMLConfig.id == config_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found",
        )

    return config


@router.post(
    "/saml", response_model=SAMLConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_saml_config(
    request: SAMLConfigCreateRequest,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> SAMLConfig:
    """
    Create a new SAML configuration (superuser only).
    """
    # If this is set as default, unset other defaults
    if request.is_default:
        await db.execute(
            select(SAMLConfig).where(SAMLConfig.is_default == True)
        )
        # We'll update after creation

    # Convert dict to JSON string for storage
    attribute_mapping_str = (
        str(request.attribute_mapping)
        if request.attribute_mapping
        else '{"email": "email", "name": "name"}'
    )
    role_mapping_str = (
        str(request.role_mapping) if request.role_mapping else "{}"
    )

    config = SAMLConfig(
        name=request.name,
        is_enabled=request.is_enabled,
        is_default=request.is_default,
        idp_entity_id=request.idp_entity_id,
        idp_sso_url=request.idp_sso_url,
        idp_slo_url=request.idp_slo_url,
        idp_x509_cert=request.idp_x509_cert,
        sp_entity_id=request.sp_entity_id,
        sp_acs_url=request.sp_acs_url,
        sp_slo_url=request.sp_slo_url,
        name_id_format=request.name_id_format,
        attribute_mapping=attribute_mapping_str,
        jit_provisioning_enabled=request.jit_provisioning_enabled,
        role_mapping=role_mapping_str,
        group_attribute=request.group_attribute,
    )

    # If setting as default, unset other defaults
    if request.is_default:
        result = await db.execute(
            select(SAMLConfig).where(SAMLConfig.is_default == True)
        )
        for existing_config in result.scalars().all():
            existing_config.is_default = False

    db.add(config)
    await db.commit()
    await db.refresh(config)

    return config


@router.patch("/saml/{config_id}", response_model=SAMLConfigResponse)
async def update_saml_config(
    config_id: str,
    request: SAMLConfigUpdateRequest,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> SAMLConfig:
    """
    Update a SAML configuration (superuser only).
    """
    result = await db.execute(
        select(SAMLConfig).where(SAMLConfig.id == config_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found",
        )

    # Update fields if provided
    if request.name is not None:
        config.name = request.name
    if request.is_enabled is not None:
        config.is_enabled = request.is_enabled
    if request.is_default is not None:
        # If setting as default, unset other defaults
        if request.is_default:
            result = await db.execute(
                select(SAMLConfig).where(
                    SAMLConfig.is_default == True,
                    SAMLConfig.id != config_id,
                )
            )
            for existing_config in result.scalars().all():
                existing_config.is_default = False
        config.is_default = request.is_default
    if request.idp_entity_id is not None:
        config.idp_entity_id = request.idp_entity_id
    if request.idp_sso_url is not None:
        config.idp_sso_url = request.idp_sso_url
    if request.idp_slo_url is not None:
        config.idp_slo_url = request.idp_slo_url
    if request.idp_x509_cert is not None:
        config.idp_x509_cert = request.idp_x509_cert
    if request.sp_entity_id is not None:
        config.sp_entity_id = request.sp_entity_id
    if request.sp_acs_url is not None:
        config.sp_acs_url = request.sp_acs_url
    if request.sp_slo_url is not None:
        config.sp_slo_url = request.sp_slo_url
    if request.name_id_format is not None:
        config.name_id_format = request.name_id_format
    if request.attribute_mapping is not None:
        config.attribute_mapping = str(request.attribute_mapping)
    if request.jit_provisioning_enabled is not None:
        config.jit_provisioning_enabled = request.jit_provisioning_enabled
    if request.role_mapping is not None:
        config.role_mapping = str(request.role_mapping)
    if request.group_attribute is not None:
        config.group_attribute = request.group_attribute

    await db.commit()
    await db.refresh(config)

    return config


@router.delete("/saml/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saml_config(
    config_id: str,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """
    Delete a SAML configuration (superuser only).
    """
    result = await db.execute(
        select(SAMLConfig).where(SAMLConfig.id == config_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found",
        )

    await db.delete(config)
    await db.commit()


# =============================================================================
# OIDC Configuration Endpoints
# =============================================================================


@router.get("/oidc", response_model=list[OIDCConfigResponse])
async def list_oidc_configs(
    current_user: CurrentSuperuser,
    db: DbSession,
) -> list[OIDCConfig]:
    """
    List all OIDC configurations (superuser only).
    """
    result = await db.execute(
        select(OIDCConfig).order_by(OIDCConfig.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/oidc/{config_id}", response_model=OIDCConfigResponse)
async def get_oidc_config(
    config_id: str,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> OIDCConfig:
    """
    Get a specific OIDC configuration (superuser only).
    """
    result = await db.execute(
        select(OIDCConfig).where(OIDCConfig.id == config_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OIDC configuration not found",
        )

    return config


@router.post(
    "/oidc", response_model=OIDCConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_oidc_config(
    request: OIDCConfigCreateRequest,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> OIDCConfig:
    """
    Create a new OIDC configuration (superuser only).
    """
    # If this is set as default, unset other defaults
    if request.is_default:
        result = await db.execute(
            select(OIDCConfig).where(OIDCConfig.is_default == True)
        )
        for existing_config in result.scalars().all():
            existing_config.is_default = False

    # Convert dict to JSON string for storage
    claim_mapping_str = (
        str(request.claim_mapping)
        if request.claim_mapping
        else '{"email": "email", "name": "name"}'
    )
    role_mapping_str = (
        str(request.role_mapping) if request.role_mapping else "{}"
    )
    allowed_audiences_str = (
        str(request.allowed_audiences) if request.allowed_audiences else "[]"
    )

    config = OIDCConfig(
        name=request.name,
        is_enabled=request.is_enabled,
        is_default=request.is_default,
        issuer_url=request.issuer_url,
        authorization_endpoint=request.authorization_endpoint,
        token_endpoint=request.token_endpoint,
        jwks_uri=request.jwks_uri,
        userinfo_endpoint=request.userinfo_endpoint,
        end_session_endpoint=request.end_session_endpoint,
        client_id=request.client_id,
        client_secret=request.client_secret,  # Note: Should be encrypted in production
        scope=request.scope,
        response_type=request.response_type,
        response_mode=request.response_mode,
        claim_mapping=claim_mapping_str,
        jit_provisioning_enabled=request.jit_provisioning_enabled,
        role_mapping=role_mapping_str,
        group_claim=request.group_claim,
        validate_signature=request.validate_signature,
        validate_issuer=request.validate_issuer,
        validate_audience=request.validate_audience,
        allowed_audiences=allowed_audiences_str,
    )

    db.add(config)
    await db.commit()
    await db.refresh(config)

    return config


@router.patch("/oidc/{config_id}", response_model=OIDCConfigResponse)
async def update_oidc_config(
    config_id: str,
    request: OIDCConfigUpdateRequest,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> OIDCConfig:
    """
    Update an OIDC configuration (superuser only).
    """
    result = await db.execute(
        select(OIDCConfig).where(OIDCConfig.id == config_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OIDC configuration not found",
        )

    # Update fields if provided
    if request.name is not None:
        config.name = request.name
    if request.is_enabled is not None:
        config.is_enabled = request.is_enabled
    if request.is_default is not None:
        # If setting as default, unset other defaults
        if request.is_default:
            result = await db.execute(
                select(OIDCConfig).where(
                    OIDCConfig.is_default == True,
                    OIDCConfig.id != config_id,
                )
            )
            for existing_config in result.scalars().all():
                existing_config.is_default = False
        config.is_default = request.is_default
    if request.issuer_url is not None:
        config.issuer_url = request.issuer_url
    if request.authorization_endpoint is not None:
        config.authorization_endpoint = request.authorization_endpoint
    if request.token_endpoint is not None:
        config.token_endpoint = request.token_endpoint
    if request.jwks_uri is not None:
        config.jwks_uri = request.jwks_uri
    if request.userinfo_endpoint is not None:
        config.userinfo_endpoint = request.userinfo_endpoint
    if request.end_session_endpoint is not None:
        config.end_session_endpoint = request.end_session_endpoint
    if request.client_id is not None:
        config.client_id = request.client_id
    if request.client_secret is not None:
        config.client_secret = request.client_secret  # Note: Should be encrypted
    if request.scope is not None:
        config.scope = request.scope
    if request.response_type is not None:
        config.response_type = request.response_type
    if request.response_mode is not None:
        config.response_mode = request.response_mode
    if request.claim_mapping is not None:
        config.claim_mapping = str(request.claim_mapping)
    if request.jit_provisioning_enabled is not None:
        config.jit_provisioning_enabled = request.jit_provisioning_enabled
    if request.role_mapping is not None:
        config.role_mapping = str(request.role_mapping)
    if request.group_claim is not None:
        config.group_claim = request.group_claim
    if request.validate_signature is not None:
        config.validate_signature = request.validate_signature
    if request.validate_issuer is not None:
        config.validate_issuer = request.validate_issuer
    if request.validate_audience is not None:
        config.validate_audience = request.validate_audience
    if request.allowed_audiences is not None:
        config.allowed_audiences = str(request.allowed_audiences)

    await db.commit()
    await db.refresh(config)

    return config


@router.delete("/oidc/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_oidc_config(
    config_id: str,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """
    Delete an OIDC configuration (superuser only).
    """
    result = await db.execute(
        select(OIDCConfig).where(OIDCConfig.id == config_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OIDC configuration not found",
        )

    await db.delete(config)
    await db.commit()
