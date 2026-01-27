"""
OIDC authentication endpoints.

Handles OpenID Connect SSO flow including login initiation,
callback processing, and token validation.
Supports Google, Azure AD, Okta, Auth0, and other OIDC-compliant providers.
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
from pybase.models.oidc_config import OIDCConfig
from pybase.models.user import User
from pybase.services.oidc_service import OIDCService, create_oidc_service
from pybase.services.sso_provisioning import (
    SSOProvisioningService,
    SSOUserAttributes,
    create_provisioning_service,
)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class OIDCLoginRequest(BaseModel):
    """OIDC login initiation request."""

    provider: str | None = Field(
        default=None,
        description="OIDC provider name (optional, uses default if not provided)",
    )
    config_id: str | None = Field(
        default=None,
        description="OIDC configuration ID (optional, uses default if not provided)",
    )
    redirect_uri: str | None = Field(
        default=None,
        description="Custom redirect URI for callback (optional)",
    )
    prompt: str | None = Field(
        default=None,
        description="OIDC prompt parameter (login, consent, none)",
    )
    login_hint: str | None = Field(
        default=None,
        description="Hint for the user's identifier",
    )


class OIDCAuthResponse(BaseModel):
    """OIDC authentication response."""

    user: dict
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    was_created: bool = Field(
        description="True if user was auto-provisioned on first login",
    )


class OIDCErrorResponse(BaseModel):
    """OIDC error response."""

    error: str
    message: str
    details: str | None = None


class OIDCConfigInfo(BaseModel):
    """OIDC configuration info (non-sensitive)."""

    id: str
    name: str
    is_default: bool
    issuer_url: str


# =============================================================================
# OIDC Login Flow
# =============================================================================


@router.get("/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def oidc_login_init(
    request: Request,
    provider: Annotated[str | None, Query(description="Provider name or config ID")] = None,
    redirect_uri: Annotated[str | None, Query(description="Custom redirect URI")] = None,
    prompt: Annotated[str | None, Query(description="OIDC prompt parameter")] = None,
    login_hint: Annotated[str | None, Query(description="Login hint")] = None,
    db: DbSession = Depends(),
) -> RedirectResponse:
    """
    Initiate OIDC SSO login flow.

    Generates OIDC authorization URL and redirects user to IdP login page.
    Uses the default OIDC configuration or the specified one.

    Args:
        request: FastAPI request
        provider: Optional provider name or OIDC config ID
        redirect_uri: Optional custom redirect URI
        prompt: Optional OIDC prompt parameter (login, consent, none)
        login_hint: Optional hint for user's identifier
        db: Database session

    Returns:
        Redirect to IdP authorization endpoint

    Raises:
        HTTPException: If OIDC is not configured or provider not found
    """
    # Check if SSO is enabled
    if not settings.sso_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is disabled",
        )

    # Get OIDC configuration
    oidc_config = await _get_oidc_config(db, provider)

    if not oidc_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OIDC configuration not found",
        )

    if not oidc_config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OIDC configuration is disabled",
        )

    # Create OIDC service
    oidc_service = create_oidc_service(oidc_config)

    # Override redirect URI if provided
    if redirect_uri:
        oidc_service.redirect_uri = redirect_uri

    # Generate state and nonce
    state = generate_random_string(32)
    nonce = generate_random_string(32)

    # Store state and nonce in session for validation on callback
    # In production, use Redis or another session store
    request.state.oidc_state = state
    request.state.oidc_nonce = nonce
    request.state.oidc_config_id = str(oidc_config.id)

    # Generate authorization URL
    auth_request = oidc_service.generate_authorization_url(
        state=state,
        nonce=nonce,
        use_pkce=True,  # Always use PKCE for security
        prompt=prompt,
        login_hint=login_hint,
    )

    return RedirectResponse(
        url=auth_request.authorization_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.get("/callback", response_model=OIDCAuthResponse)
async def oidc_callback(
    request: Request,
    code: Annotated[str, Query(description="Authorization code from IdP")],
    state: Annotated[str, Query(description="State parameter for CSRF protection")],
    db: DbSession = Depends(),
) -> OIDCAuthResponse:
    """
    OIDC callback endpoint.

    Processes authorization code from IdP, exchanges it for tokens,
    validates ID token, and authenticates user.
    Handles JIT provisioning for new users.

    Args:
        request: FastAPI request
        code: Authorization code from IdP
        state: State parameter for CSRF protection
        db: Database session

    Returns:
        Authentication tokens with user info

    Raises:
        HTTPException: If OIDC callback is invalid or authentication fails
    """
    # Check if SSO is enabled
    if not settings.sso_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is disabled",
        )

    # In production, validate state from session
    # stored_state = request.session.pop("oidc_state", None)
    # nonce = request.session.pop("oidc_nonce", None)
    # config_id = request.session.pop("oidc_config_id", None)

    # For now, we'll get the config from the default or first enabled
    oidc_config = await _get_default_oidc_config(db)

    if not oidc_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OIDC configuration not found",
        )

    # Create OIDC service
    oidc_service = create_oidc_service(oidc_config)

    try:
        # Exchange authorization code for tokens
        token_response = await oidc_service.exchange_code_for_token(
            code=code,
            # Note: In production, retrieve code_verifier from session
            # For now, PKCE is optional but recommended
        )

        # Validate ID token and extract user info
        # Note: In production, retrieve nonce from session
        userinfo = await oidc_service.validate_id_token(
            id_token=token_response.id_token,
            nonce=None,  # In production: nonce from session
        )

        # Map user attributes from OIDC claims
        user_attrs = oidc_service.map_user_attributes(userinfo)

        # Map user roles from OIDC groups
        user_roles = oidc_service.map_user_roles(user_attrs.groups)

        # Create provisioning service
        provisioning_service = create_provisioning_service(db)

        # Provision or link user
        sso_user_attrs = SSOUserAttributes(
            email=user_attrs.email,
            first_name=user_attrs.first_name,
            last_name=user_attrs.last_name,
            display_name=user_attrs.display_name,
            picture=user_attrs.picture,
            roles=user_roles or [],
            groups=user_attrs.groups or [],
        )

        provisioning_result = await provisioning_service.provision_or_link_user(
            provider_type="oidc",
            subject_id=userinfo.sub,
            issuer=oidc_service.issuer_url or "",
            config_id=str(oidc_config.id),
            user_attributes=sso_user_attrs,
            raw_attributes=userinfo.model_dump(),
        )

        # Return authentication response
        return OIDCAuthResponse(
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
            detail=f"OIDC authentication failed: {str(e)}",
        ) from e


@router.get("/config")
async def oidc_config_info(
    current_user: CurrentUser,
    db: DbSession = Depends(),
) -> dict:
    """
    Get OIDC configuration information for the current user.

    Returns available OIDC configurations for login.
    Does not expose sensitive configuration data.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of available OIDC configurations
    """
    # Get enabled OIDC configurations
    result = await db.execute(
        select(OIDCConfig).where(
            OIDCConfig.is_enabled == True,
        )
    )
    configs = result.scalars().all()

    return {
        "sso_enabled": settings.sso_enabled,
        "oidc_configs": [
            {
                "id": str(config.id),
                "name": config.name,
                "is_default": config.is_default,
                "issuer_url": config.issuer_url,
            }
            for config in configs
        ],
    }


@router.get("/logout")
async def oidc_logout(
    current_user: CurrentUser,
    post_logout_redirect_uri: Annotated[
        str | None, Query(description="Post-logout redirect URI")
    ] = None,
    db: DbSession = Depends(),
) -> dict:
    """
    Initiate OIDC logout flow.

    Returns logout URL for ending IdP session (if configured).
    The client should redirect the user to this URL to complete logout.

    Args:
        current_user: Current authenticated user
        post_logout_redirect_uri: Optional URL to redirect after logout
        db: Database session

    Returns:
        Logout URL or redirect information
    """
    # Get default OIDC configuration
    oidc_config = await _get_default_oidc_config(db)

    if not oidc_config:
        # No OIDC config, return basic logout info
        return {
            "message": "Logout successful",
            "redirect_url": post_logout_redirect_uri,
        }

    # Create OIDC service
    oidc_service = create_oidc_service(oidc_config)

    # Generate logout URL
    logout_url = oidc_service.generate_logout_url(
        id_token_hint=None,  # In production, pass current ID token
        post_logout_redirect_uri=post_logout_redirect_uri,
    )

    if logout_url:
        return {
            "message": "Redirect to IdP for logout",
            "logout_url": logout_url,
        }
    else:
        return {
            "message": "Logout successful",
            "redirect_url": post_logout_redirect_uri,
        }


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_oidc_config(
    db: AsyncSession,
    config_id: str | None = None,
) -> OIDCConfig | None:
    """
    Get OIDC configuration by ID or default.

    Args:
        db: Database session
        config_id: Optional configuration ID

    Returns:
        OIDCConfig if found, None otherwise
    """
    if config_id:
        # Get specific configuration
        result = await db.execute(
            select(OIDCConfig).where(
                OIDCConfig.id == config_id,
            )
        )
        return result.scalar_one_or_none()
    else:
        # Get default configuration
        return await _get_default_oidc_config(db)


async def _get_default_oidc_config(db: AsyncSession) -> OIDCConfig | None:
    """
    Get the default OIDC configuration.

    Args:
        db: Database session

    Returns:
        Default OIDCConfig if found, None otherwise
    """
    # Try to get marked default first
    result = await db.execute(
        select(OIDCConfig).where(
            OIDCConfig.is_default == True,
            OIDCConfig.is_enabled == True,
        )
    )
    config = result.scalar_one_or_none()

    if config:
        return config

    # Fall back to first enabled configuration
    result = await db.execute(
        select(OIDCConfig).where(
            OIDCConfig.is_enabled == True,
        ).order_by(OIDCConfig.created_at)
    )
    return result.scalar_one_or_none()
