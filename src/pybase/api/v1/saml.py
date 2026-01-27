"""
SAML 2.0 authentication endpoints.

Handles SAML SSO flow including login initiation, callback processing,
and service provider metadata generation.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.config import settings
from pybase.core.security import create_token_pair, generate_random_string
from pybase.models.saml_config import SAMLConfig
from pybase.models.user import User
from pybase.services.saml_service import SAMLService, create_saml_service
from pybase.services.sso_provisioning import (
    SSOProvisioningService,
    SSOUserAttributes,
    create_provisioning_service,
)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class SAMLLoginRequest(BaseModel):
    """SAML login initiation request."""

    idp_id: str | None = Field(
        default=None,
        description="SAML configuration ID (optional, uses default if not provided)",
    )
    relay_state: str | None = Field(
        default=None,
        description="Custom relay state for CSRF protection",
    )
    force_authn: bool = Field(
        default=False,
        description="Force re-authentication at IdP",
    )


class SAMLAuthResponse(BaseModel):
    """SAML authentication response."""

    user: dict
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    was_created: bool = Field(
        description="True if user was auto-provisioned on first login",
    )


class SAMLErrorResponse(BaseModel):
    """SAML error response."""

    error: str
    message: str
    details: str | None = None


# =============================================================================
# SAML Login Flow
# =============================================================================


@router.get("/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def saml_login_init(
    request: Request,
    idp_id: Annotated[str | None, Query(description="SAML config ID")] = None,
    relay_state: Annotated[str | None, Query(description="Custom relay state")] = None,
    force_authn: Annotated[bool, Query(description="Force re-authentication")] = False,
    db: DbSession = Depends(),
) -> RedirectResponse:
    """
    Initiate SAML SSO login flow.

    Generates SAML authentication request and redirects user to IdP login page.
    Uses the default SAML configuration or the specified one.

    Args:
        request: FastAPI request
        idp_id: Optional SAML configuration ID
        relay_state: Optional custom relay state
        force_authn: Force re-authentication at IdP
        db: Database session

    Returns:
        Redirect to IdP SSO URL with SAML request

    Raises:
        HTTPException: If SAML is not configured or IdP not found
    """
    # Check if SSO is enabled
    if not settings.sso_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is disabled",
        )

    # Get SAML configuration
    saml_config = await _get_saml_config(db, idp_id)

    if not saml_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found",
        )

    if not saml_config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SAML configuration is disabled",
        )

    # Create SAML service
    saml_service = create_saml_service(saml_config)

    # Generate relay state if not provided
    if not relay_state:
        relay_state = generate_random_string(32)

    # Store relay state in session for validation on callback
    # In production, use Redis or another session store
    request.state.saml_relay_state = relay_state
    request.state.saml_config_id = str(saml_config.id)

    # Generate SAML auth request
    auth_request = saml_service.generate_auth_request(
        relay_state=relay_state,
        force_authn=force_authn,
    )

    # Build redirect URL to IdP
    # SAML request is sent via POST binding (typically)
    # For GET binding, include SAMLRequest and RelayState as query params
    idp_url = auth_request.destination_url

    # For HTTP-Redirect binding (GET)
    from urllib.parse import urlencode

    params = {
        "SAMLRequest": auth_request.saml_request,
        "RelayState": auth_request.relay_state,
    }
    redirect_url = f"{idp_url}?{urlencode(params)}"

    return RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.post("/acs", response_model=SAMLAuthResponse)
async def saml_acs(
    request: Request,
    saml_response: Annotated[str, Query(description="SAML response from IdP")],
    relay_state: Annotated[str, Query(description="Relay state parameter")],
    db: DbSession = Depends(),
) -> SAMLAuthResponse:
    """
    SAML Assertion Consumer Service (callback) endpoint.

    Processes SAML response from IdP, authenticates user, and returns tokens.
    Handles JIT provisioning for new users.

    Args:
        request: FastAPI request
        saml_response: Base64-encoded SAML response from IdP
        relay_state: Relay state for CSRF protection
        db: Database session

    Returns:
        Authentication tokens with user info

    Raises:
        HTTPException: If SAML response is invalid or authentication fails
    """
    # Check if SSO is enabled
    if not settings.sso_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is disabled",
        )

    # In production, validate relay state from session
    # stored_state = request.session.pop("saml_relay_state", None)
    # config_id = request.session.pop("saml_config_id", None)

    # For now, we'll get the config from the default or first enabled
    saml_config = await _get_default_saml_config(db)

    if not saml_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found",
        )

    # Create SAML service
    saml_service = create_saml_service(saml_config)

    try:
        # Decode and validate SAML response
        saml_resp = saml_service.decode_saml_response(saml_response)

        # Map user attributes from SAML
        user_attrs = saml_service.map_user_attributes(saml_resp.attributes)

        # Map user roles from SAML groups
        user_roles = saml_service.map_user_roles(user_attrs.groups)

        # Create provisioning service
        provisioning_service = create_provisioning_service(db)

        # Provision or link user
        sso_user_attrs = SSOUserAttributes(
            email=user_attrs.email,
            first_name=user_attrs.first_name,
            last_name=user_attrs.last_name,
            display_name=user_attrs.display_name,
            roles=user_roles or [],
            groups=user_attrs.groups or [],
        )

        provisioning_result = await provisioning_service.provision_or_link_user(
            provider_type="saml",
            subject_id=saml_resp.name_id,
            issuer=saml_resp.issuer,
            config_id=str(saml_config.id),
            user_attributes=sso_user_attrs,
            raw_attributes=saml_resp.attributes,
        )

        # Return authentication response
        return SAMLAuthResponse(
            user={
                "id": str(provisioning_result.user.id),
                "email": provisioning_result.user.email,
                "name": provisioning_result.user.name,
                "avatar_url": provisioning_result.user.avatar_url,
                "is_active": provisioning_result.user.is_active,
                "is_verified": provisioning_result.user.is_verified,
                "created_at": provisioning_result.user.created_at.isoformat(),
            },
            access_token=provisioning_result.tokens.access_token,
            refresh_token=provisioning_result.tokens.refresh_token,
            token_type=provisioning_result.tokens.token_type,
            expires_in=provisioning_result.tokens.expires_in,
            was_created=provisioning_result.was_created,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SAML authentication failed: {str(e)}",
        ) from e


@router.get("/metadata")
async def saml_metadata(
    idp_id: Annotated[str | None, Query(description="SAML config ID")] = None,
    db: DbSession = Depends(),
) -> Response:
    """
    Generate SAML 2.0 Service Provider metadata.

    Returns SP metadata XML for configuring the IdP.
    This endpoint is called by IdP administrators during setup.

    Args:
        idp_id: Optional SAML configuration ID
        db: Database session

    Returns:
        XML metadata response

    Raises:
        HTTPException: If SAML configuration not found
    """
    # Get SAML configuration
    saml_config = await _get_saml_config(db, idp_id)

    if not saml_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found",
        )

    # Create SAML service
    saml_service = create_saml_service(saml_config)

    try:
        # Generate SP metadata
        metadata_xml = saml_service.generate_sp_metadata()

        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={
                "Content-Disposition": 'attachment; filename="saml-metadata.xml"',
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate metadata: {str(e)}",
        ) from e


@router.get("/config")
async def saml_config_info(
    current_user: CurrentUser,
    db: DbSession = Depends(),
) -> dict:
    """
    Get SAML configuration information for the current user.

    Returns available SAML configurations for login.
    Does not expose sensitive configuration data.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of available SAML configurations
    """
    # Get enabled SAML configurations
    result = await db.execute(
        select(SAMLConfig).where(
            SAMLConfig.is_enabled == True,
        )
    )
    configs = result.scalars().all()

    return {
        "sso_enabled": settings.sso_enabled,
        "saml_configs": [
            {
                "id": str(config.id),
                "name": config.name,
                "is_default": config.is_default,
                "idp_entity_id": config.idp_entity_id,
            }
            for config in configs
        ],
    }


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_saml_config(
    db: AsyncSession,
    config_id: str | None = None,
) -> SAMLConfig | None:
    """
    Get SAML configuration by ID or default.

    Args:
        db: Database session
        config_id: Optional configuration ID

    Returns:
        SAMLConfig if found, None otherwise
    """
    if config_id:
        # Get specific configuration
        result = await db.execute(
            select(SAMLConfig).where(
                SAMLConfig.id == config_id,
            )
        )
        return result.scalar_one_or_none()
    else:
        # Get default configuration
        return await _get_default_saml_config(db)


async def _get_default_saml_config(db: AsyncSession) -> SAMLConfig | None:
    """
    Get the default SAML configuration.

    Args:
        db: Database session

    Returns:
        Default SAMLConfig if found, None otherwise
    """
    # Try to get marked default first
    result = await db.execute(
        select(SAMLConfig).where(
            SAMLConfig.is_default == True,
            SAMLConfig.is_enabled == True,
        )
    )
    config = result.scalar_one_or_none()

    if config:
        return config

    # Fall back to first enabled configuration
    result = await db.execute(
        select(SAMLConfig).where(
            SAMLConfig.is_enabled == True,
        ).order_by(SAMLConfig.created_at)
    )
    return result.scalar_one_or_none()
