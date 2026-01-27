"""
OpenID Connect service for Single Sign-On authentication.

Handles OIDC authentication flow including authorization URL generation,
token exchange, ID token validation, and claim extraction from Identity Providers.
Supports Google, Azure AD, Okta, Auth0, and other OIDC-compliant providers.
"""

import json
import secrets
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import jwk, jwt
from jose.exceptions import JWTError
from pydantic import BaseModel

from pybase.core.config import settings
from pybase.core.security import create_token_pair, generate_random_string


# =============================================================================
# OIDC Data Models
# =============================================================================


class OIDCAuthRequest(BaseModel):
    """OIDC authentication request data."""

    authorization_url: str  # Full authorization URL
    state: str  # State parameter for CSRF protection
    code_verifier: str | None = None  # PKCE code verifier (optional)
    nonce: str  # Nonce for ID token replay protection


class OIDCTokenResponse(BaseModel):
    """OIDC token response from IdP."""

    access_token: str
    id_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    scope: str | None = None


class OIDCUserInfo(BaseModel):
    """OIDC user information claims."""

    sub: str  # Subject (unique user ID)
    email: str | None = None
    email_verified: bool | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
    locale: str | None = None
    roles: list[str] | None = None
    groups: list[str] | None = None


class OIDCUserAttributes(BaseModel):
    """Extracted user attributes from OIDC claims."""

    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    picture: str | None = None
    roles: list[str] | None = None
    groups: list[str] | None = None


# =============================================================================
# OIDC Service
# =============================================================================


class OIDCService:
    """
    OpenID Connect authentication service.

    Handles OIDC authentication flow with Identity Providers.
    Supports Authorization Code flow with PKCE.
    Supports OIDC-compliant providers (Google, Azure AD, Okta, Auth0, etc.).
    """

    # OIDC standard scopes
    SCOPE_OPENID = "openid"
    SCOPE_PROFILE = "profile"
    SCOPE_EMAIL = "email"
    SCOPE_ADDRESS = "address"
    SCOPE_PHONE = "phone"

    # OIDC standard claims
    CLAIM_SUB = "sub"
    CLAIM_NAME = "name"
    CLAIM_GIVEN_NAME = "given_name"
    CLAIM_FAMILY_NAME = "family_name"
    CLAIM_EMAIL = "email"
    CLAIM_EMAIL_VERIFIED = "email_verified"
    CLAIM_PICTURE = "picture"
    CLAIM_LOCALE = "locale"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        issuer_url: str | None = None,
        authorization_endpoint: str | None = None,
        token_endpoint: str | None = None,
        jwks_uri: str | None = None,
        userinfo_endpoint: str | None = None,
        end_session_endpoint: str | None = None,
        scope: str = "openid email profile",
        response_type: str = "code",
        response_mode: str | None = None,
        redirect_uri: str | None = None,
        claim_mapping: dict[str, str] | None = None,
        role_mapping: dict[str, list[str]] | None = None,
        group_claim: str = "groups",
        validate_signature: bool = True,
        validate_issuer: bool = True,
        validate_audience: bool = True,
        allowed_audiences: list[str] | None = None,
    ):
        """
        Initialize OIDC service with configuration.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            issuer_url: OIDC issuer URL (for discovery)
            authorization_endpoint: OAuth2 authorization endpoint
            token_endpoint: OAuth2 token endpoint
            jwks_uri: JWKS endpoint for token verification
            userinfo_endpoint: UserInfo endpoint (optional)
            end_session_endpoint: End session endpoint for logout (optional)
            scope: OAuth2 scopes to request
            response_type: OAuth2 response type (code for auth code flow)
            response_mode: OAuth2 response mode (query, form_post, fragment)
            redirect_uri: Redirect URI after authentication
            claim_mapping: OIDC claims to user field mapping
            role_mapping: OIDC groups to user roles mapping
            group_claim: Claim name for groups/roles
            validate_signature: Validate ID token signature
            validate_issuer: Validate ID token issuer
            validate_audience: Validate ID token audience
            allowed_audiences: Allowed token audiences
        """
        self.client_id = client_id or settings.oidc_client_id
        self.client_secret = client_secret or settings.oidc_client_secret
        self.issuer_url = issuer_url or settings.oidc_discovery_url
        self.authorization_endpoint = authorization_endpoint or settings.oidc_auth_endpoint
        self.token_endpoint = token_endpoint or settings.oidc_token_endpoint
        self.jwks_uri = jwks_uri or settings.oidc_jwks_uri
        self.userinfo_endpoint = userinfo_endpoint or settings.oidc_userinfo_endpoint
        self.end_session_endpoint = end_session_endpoint
        self.scope = scope
        self.response_type = response_type
        self.response_mode = response_mode or settings.oidc_response_mode
        self.redirect_uri = redirect_uri or f"{settings.api_v1_prefix}/oidc/callback"
        self.claim_mapping = claim_mapping or settings.oidc_claims_mapping
        self.role_mapping = role_mapping or {}
        self.group_claim = group_claim
        self.validate_signature = validate_signature
        self.validate_issuer = validate_issuer
        self.validate_audience = validate_audience
        self.allowed_audiences = allowed_audiences or []

        # Cache for JWKS keys
        self._jwks_keys: list[dict[str, Any]] | None = None

    # =========================================================================
    # Provider Discovery
    # =========================================================================

    async def discover_provider(self, issuer_url: str | None = None) -> dict[str, str]:
        """
        Discover OIDC provider endpoints from .well-known configuration.

        Args:
            issuer_url: OIDC issuer URL (defaults to configured issuer)

        Returns:
            Dictionary of discovered endpoints

        Raises:
            ValueError: If discovery fails or response is invalid
        """
        issuer = issuer_url or self.issuer_url

        if not issuer:
            raise ValueError("Issuer URL is required for discovery")

        # Ensure issuer ends with /
        if not issuer.endswith("/"):
            issuer += "/"

        discovery_url = f"{issuer}.well-known/openid-configuration"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(discovery_url)
                response.raise_for_status()

                config = response.json()

                # Extract endpoints
                self.issuer_url = config.get("issuer", issuer)
                self.authorization_endpoint = config.get("authorization_endpoint")
                self.token_endpoint = config.get("token_endpoint")
                self.jwks_uri = config.get("jwks_uri")
                self.userinfo_endpoint = config.get("userinfo_endpoint")
                self.end_session_endpoint = config.get("end_session_endpoint")

                return {
                    "issuer": self.issuer_url,
                    "authorization_endpoint": self.authorization_endpoint,
                    "token_endpoint": self.token_endpoint,
                    "jwks_uri": self.jwks_uri,
                    "userinfo_endpoint": self.userinfo_endpoint,
                    "end_session_endpoint": self.end_session_endpoint,
                }

            except httpx.HTTPError as e:
                raise ValueError(f"Failed to discover OIDC configuration: {e}") from e

    # =========================================================================
    # Authorization Flow
    # =========================================================================

    def generate_authorization_url(
        self,
        state: str | None = None,
        nonce: str | None = None,
        use_pkce: bool = True,
        additional_scopes: list[str] | None = None,
        prompt: str | None = None,
        login_hint: str | None = None,
    ) -> OIDCAuthRequest:
        """
        Generate OIDC authorization URL for redirecting user to IdP.

        Args:
            state: State parameter for CSRF protection
            nonce: Nonce for ID token replay protection
            use_pkce: Use PKCE (Proof Key for Code Exchange)
            additional_scopes: Additional scopes to request
            prompt: OIDC prompt parameter (login, consent, none)
            login_hint: Hint for the user's identifier

        Returns:
            OIDCAuthRequest with authorization URL and state/nonce

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.client_id:
            raise ValueError("Client ID is required")

        if not self.authorization_endpoint:
            raise ValueError("Authorization endpoint is required. Call discover_provider() first.")

        # Generate state and nonce if not provided
        if not state:
            state = generate_random_string(32)
        if not nonce:
            nonce = generate_random_string(32)

        # Build query parameters
        params = {
            "response_type": self.response_type,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self._build_scope(additional_scopes),
            "state": state,
            "nonce": nonce,
        }

        # Add response_mode if specified (not for all providers)
        if self.response_mode:
            params["response_mode"] = self.response_mode

        # Add prompt if specified
        if prompt:
            params["prompt"] = prompt

        # Add login_hint if specified
        if login_hint:
            params["login_hint"] = login_hint

        # Generate PKCE code verifier and challenge if enabled
        code_verifier = None
        if use_pkce:
            code_verifier = self._generate_code_verifier()
            code_challenge = self._generate_code_challenge(code_verifier)
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        # Build authorization URL
        authorization_url = f"{self.authorization_endpoint}?{urlencode(params)}"

        return OIDCAuthRequest(
            authorization_url=authorization_url,
            state=state,
            code_verifier=code_verifier,
            nonce=nonce,
        )

    def _build_scope(self, additional_scopes: list[str] | None = None) -> str:
        """Build OAuth2 scope string."""
        scopes = self.scope.split()

        if additional_scopes:
            scopes.extend(additional_scopes)

        # Remove duplicates while preserving order
        seen = set()
        unique_scopes = []
        for scope in scopes:
            if scope not in seen:
                seen.add(scope)
                unique_scopes.append(scope)

        return " ".join(unique_scopes)

    @staticmethod
    def _generate_code_verifier() -> str:
        """
        Generate PKCE code verifier.

        Returns:
            URL-safe random string (43-128 characters)
        """
        import secrets
        import base64

        # Generate 32 random bytes, base64url encode (no padding)
        random_bytes = secrets.token_bytes(32)
        code_verifier = base64.urlsafe_b64encode(random_bytes).decode("utf-8").rstrip("=")

        return code_verifier

    @staticmethod
    def _generate_code_challenge(code_verifier: str) -> str:
        """
        Generate PKCE code challenge from verifier.

        Args:
            code_verifier: PKCE code verifier

        Returns:
            Base64url-encoded SHA256 hash of verifier
        """
        import hashlib
        import base64

        # SHA256 hash the verifier
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()

        # Base64url encode (no padding)
        code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

        return code_challenge

    # =========================================================================
    # Token Exchange
    # =========================================================================

    async def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str | None = None,
    ) -> OIDCTokenResponse:
        """
        Exchange authorization code for access and ID tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier (if PKCE was used)

        Returns:
            OIDCTokenResponse with tokens

        Raises:
            ValueError: If token exchange fails
        """
        if not self.client_id:
            raise ValueError("Client ID is required")

        if not self.token_endpoint:
            raise ValueError("Token endpoint is required. Call discover_provider() first.")

        # Prepare token request body
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
        }

        # Add client secret for confidential clients
        if self.client_secret:
            data["client_secret"] = self.client_secret

        # Add PKCE code verifier if using PKCE
        if code_verifier:
            data["code_verifier"] = code_verifier

        # Make token request
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    self.token_endpoint,
                    data=data,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()

                token_data = response.json()

                return OIDCTokenResponse(
                    access_token=token_data.get("access_token", ""),
                    id_token=token_data.get("id_token", ""),
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "bearer"),
                    expires_in=token_data.get("expires_in"),
                    scope=token_data.get("scope"),
                )

            except httpx.HTTPError as e:
                raise ValueError(f"Failed to exchange code for token: {e}") from e

    async def refresh_token(self, refresh_token: str) -> OIDCTokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from initial authentication

        Returns:
            OIDCTokenResponse with new tokens

        Raises:
            ValueError: If token refresh fails
        """
        if not self.client_id:
            raise ValueError("Client ID is required")

        if not self.token_endpoint:
            raise ValueError("Token endpoint is required. Call discover_provider() first.")

        # Prepare refresh request body
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        # Add client secret for confidential clients
        if self.client_secret:
            data["client_secret"] = self.client_secret

        # Make refresh request
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    self.token_endpoint,
                    data=data,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()

                token_data = response.json()

                return OIDCTokenResponse(
                    access_token=token_data.get("access_token", ""),
                    id_token=token_data.get("id_token", ""),
                    refresh_token=token_data.get("refresh_token", refresh_token),
                    token_type=token_data.get("token_type", "bearer"),
                    expires_in=token_data.get("expires_in"),
                    scope=token_data.get("scope"),
                )

            except httpx.HTTPError as e:
                raise ValueError(f"Failed to refresh token: {e}") from e

    # =========================================================================
    # Token Validation
    # =========================================================================

    async def validate_id_token(
        self,
        id_token: str,
        nonce: str | None = None,
    ) -> OIDCUserInfo:
        """
        Validate and decode ID token.

        Args:
            id_token: JWT ID token from IdP
            nonce: Nonce used in auth request (for replay protection)

        Returns:
            OIDCUserInfo with claims from ID token

        Raises:
            ValueError: If token is invalid or validation fails
        """
        # Decode token without verification first to get headers
        try:
            unverified_header = jwt.get_unverified_header(id_token)
        except JWTError as e:
            raise ValueError(f"Failed to decode ID token header: {e}") from e

        # Get kid (key ID) from header
        kid = unverified_header.get("kid")
        if not kid:
            raise ValueError("ID token missing kid (key ID) in header")

        # Fetch JWKS if not cached
        if self._jwks_keys is None:
            await self._fetch_jwks()

        # Find matching key
        key_data = None
        for key in self._jwks_keys or []:
            if key.get("kid") == kid:
                key_data = key
                break

        if not key_data:
            raise ValueError(f"Unable to find matching key for kid: {kid}")

        # Build public key from JWK
        try:
            public_key = jwk.construct(key_data).to_pem()
        except Exception as e:
            raise ValueError(f"Failed to construct public key from JWK: {e}") from e

        # Validate token
        validation_options: dict[str, Any] = {}

        if self.validate_issuer and self.issuer_url:
            validation_options["issuer"] = self.issuer_url

        if self.validate_audience:
            if self.allowed_audiences:
                validation_options["audience"] = self.allowed_audiences
            else:
                validation_options["audience"] = self.client_id

        try:
            # Decode and verify token
            payload = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                options=validation_options,
            )

            # Verify nonce if provided
            if nonce and payload.get("nonce") != nonce:
                raise ValueError("ID token nonce mismatch")

            # Check expiration
            if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
                raise ValueError("ID token has expired")

            return self._parse_user_info(payload)

        except JWTError as e:
            raise ValueError(f"Failed to validate ID token: {e}") from e

    async def _fetch_jwks(self) -> None:
        """
        Fetch JWKS (JSON Web Key Set) from IdP.

        Raises:
            ValueError: If JWKS fetch fails
        """
        if not self.jwks_uri:
            raise ValueError("JWKS URI is required. Call discover_provider() first.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.jwks_uri)
                response.raise_for_status()

                jwks_data = response.json()
                self._jwks_keys = jwks_data.get("keys", [])

            except httpx.HTTPError as e:
                raise ValueError(f"Failed to fetch JWKS: {e}") from e

    def _parse_user_info(self, claims: dict[str, Any]) -> OIDCUserInfo:
        """
        Parse user info from ID token claims.

        Args:
            claims: ID token claims

        Returns:
            OIDCUserInfo
        """
        return OIDCUserInfo(
            sub=claims.get(self.CLAIM_SUB, ""),
            email=claims.get(self.CLAIM_EMAIL),
            email_verified=claims.get(self.CLAIM_EMAIL_VERIFIED),
            name=claims.get(self.CLAIM_NAME),
            given_name=claims.get(self.CLAIM_GIVEN_NAME),
            family_name=claims.get(self.CLAIM_FAMILY_NAME),
            picture=claims.get(self.CLAIM_PICTURE),
            locale=claims.get(self.CLAIM_LOCALE),
        )

    # =========================================================================
    # User Info Endpoint
    # =========================================================================

    async def fetch_userinfo(self, access_token: str) -> OIDCUserInfo:
        """
        Fetch user info from UserInfo endpoint.

        Args:
            access_token: Access token from IdP

        Returns:
            OIDCUserInfo with user claims

        Raises:
            ValueError: If userinfo fetch fails or endpoint not configured
        """
        if not self.userinfo_endpoint:
            raise ValueError("UserInfo endpoint not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    self.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()

                claims = response.json()
                return self._parse_user_info(claims)

            except httpx.HTTPError as e:
                raise ValueError(f"Failed to fetch userinfo: {e}") from e

    # =========================================================================
    # User Attribute Mapping
    # =========================================================================

    def map_user_attributes(self, userinfo: OIDCUserInfo) -> OIDCUserAttributes:
        """
        Map OIDC claims to user profile fields.

        Args:
            userinfo: User info from ID token or userinfo endpoint

        Returns:
            Mapped user attributes
        """
        user_attrs = OIDCUserAttributes()

        # Extract claims as dict for easier mapping
        claims = userinfo.model_dump()

        # Map attributes using configured mapping
        for field, claim_name in self.claim_mapping.items():
            if claim_name in claims:
                value = claims[claim_name]

                if field == "email":
                    user_attrs.email = str(value) if value else None
                elif field == "first_name":
                    user_attrs.first_name = str(value) if value else None
                elif field == "last_name":
                    user_attrs.last_name = str(value) if value else None
                elif field == "name":
                    user_attrs.display_name = str(value) if value else None
                elif field == "picture":
                    user_attrs.picture = str(value) if value else None

        # Fallback: split name into first/last if not set
        if not user_attrs.first_name and not user_attrs.last_name and userinfo.name:
            parts = userinfo.name.split(" ", 1)
            user_attrs.first_name = parts[0]
            if len(parts) > 1:
                user_attrs.last_name = parts[1]

        # Extract groups/roles from group_claim
        if self.group_claim and self.group_claim in claims:
            groups_value = claims[self.group_claim]
            if isinstance(groups_value, list):
                user_attrs.groups = groups_value
            elif isinstance(groups_value, str):
                user_attrs.groups = [g.strip() for g in groups_value.split(",") if g.strip()]

        return user_attrs

    def map_user_roles(self, oidc_groups: list[str] | None) -> list[str]:
        """
        Map OIDC groups to user roles.

        Args:
            oidc_groups: List of groups from OIDC claims

        Returns:
            List of user roles
        """
        if not oidc_groups or not self.role_mapping:
            return []

        roles: set[str] = set()

        for group in oidc_groups:
            if group in self.role_mapping:
                roles.update(self.role_mapping[group])

        return list(roles)

    # =========================================================================
    # Logout
    # =========================================================================

    def generate_logout_url(
        self,
        id_token_hint: str | None = None,
        post_logout_redirect_uri: str | None = None,
    ) -> str | None:
        """
        Generate logout URL for ending IdP session.

        Args:
            id_token_hint: ID token from current session
            post_logout_redirect_uri: URL to redirect after logout

        Returns:
            Logout URL or None if end_session_endpoint not configured
        """
        if not self.end_session_endpoint:
            return None

        params = {}

        if id_token_hint:
            params["id_token_hint"] = id_token_hint

        if post_logout_redirect_uri:
            params["post_logout_redirect_uri"] = post_logout_redirect_uri

        query_string = urlencode(params)
        return f"{self.end_session_endpoint}?{query_string}" if params else self.end_session_endpoint

    # =========================================================================
    # Utility Functions
    # =========================================================================

    def validate_state(self, state: str, stored_state: str) -> bool:
        """
        Validate state parameter for CSRF protection.

        Args:
            state: State from callback
            stored_state: Stored state from request

        Returns:
            True if state is valid
        """
        return state == stored_state

    @staticmethod
    def get_user_id_from_claims(userinfo: OIDCUserInfo) -> str:
        """
        Generate a stable user ID from OIDC claims.

        Args:
            userinfo: User info from IdP

        Returns:
            User ID string
        """
        # Use subject (sub) claim as unique ID
        return f"oidc:{userinfo.sub}"


# =============================================================================
# Convenience Functions
# =============================================================================


def create_oidc_service(oidc_config: Any | None = None) -> OIDCService:
    """
    Create an OIDC service instance from configuration.

    Args:
        oidc_config: OIDCConfig model or dict with OIDC settings

    Returns:
        Configured OIDC service instance
    """
    if oidc_config is None:
        # Use default configuration from settings
        return OIDCService()

    # Extract configuration from OIDCConfig model or dict
    if hasattr(oidc_config, "issuer_url"):
        # OIDCConfig model
        config_dict = {
            "client_id": oidc_config.client_id,
            "client_secret": oidc_config.client_secret,
            "issuer_url": oidc_config.issuer_url,
            "authorization_endpoint": oidc_config.authorization_endpoint,
            "token_endpoint": oidc_config.token_endpoint,
            "jwks_uri": oidc_config.jwks_uri,
            "userinfo_endpoint": oidc_config.userinfo_endpoint,
            "end_session_endpoint": oidc_config.end_session_endpoint,
            "scope": oidc_config.scope,
            "response_type": oidc_config.response_type,
            "response_mode": oidc_config.response_mode,
            "claim_mapping": json.loads(oidc_config.claim_mapping) if oidc_config.claim_mapping else None,
            "role_mapping": json.loads(oidc_config.role_mapping) if oidc_config.role_mapping else None,
            "group_claim": oidc_config.group_claim,
            "validate_signature": oidc_config.validate_signature,
            "validate_issuer": oidc_config.validate_issuer,
            "validate_audience": oidc_config.validate_audience,
            "allowed_audiences": json.loads(oidc_config.allowed_audiences) if oidc_config.allowed_audiences else None,
        }
    else:
        # Dict-like configuration
        config_dict = dict(oidc_config)

    return OIDCService(**config_dict)
