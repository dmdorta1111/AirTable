"""
Application configuration management using Pydantic Settings.

Loads configuration from environment variables and .env files.
"""

from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application Settings
    # ==========================================================================
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    app_name: str = Field(default="PyBase", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")

    # Secret key for JWT - REQUIRED in production!
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    # WARNING: The default value is for development only!
    # Set SECRET_KEY environment variable in production.
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-abc123xyz789",
        description="Secret key for JWT tokens - MUST be set in production",
    )

    @field_validator("secret_key", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Ensure secret key is properly set in production."""
        environment = info.data.get("environment", "development")
        if environment == "production":
            if v.startswith("dev-") or "change-this" in v:
                raise ValueError(
                    "SECRET_KEY must be set to a secure random string in production. "
                    'Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                )
        return v

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ==========================================================================
    # Database Configuration
    # ==========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://pybase:pybase@localhost:5432/pybase",
        description="PostgreSQL connection string",
    )
    db_pool_size: int = Field(default=20, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Max overflow connections")
    db_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str, info) -> str:
        """Ensure database URL uses asyncpg driver and credentials are safe for production."""
        # Convert to asyncpg driver if needed
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Check production credentials
        environment = info.data.get("environment", "development")
        if environment == "production":
            # Check for common placeholder/default patterns
            placeholder_patterns = [
                "pybase:pybase@",  # Default username:password
                "localhost:5432",  # Default host:port
                "change-this",  # Generic placeholder
                "placeholder",  # Generic placeholder
            ]
            v_lower = v.lower()
            for pattern in placeholder_patterns:
                if pattern in v_lower:
                    raise ValueError(
                        "DATABASE_URL must be set to a production database in production. "
                        "Default credentials detected. Set DATABASE_URL environment variable."
                    )
        return v

    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")

    # ==========================================================================
    # Redis Configuration
    # ==========================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string",
    )
    redis_max_connections: int = Field(default=50, description="Max Redis connections")

    @field_validator("redis_url", mode="before")
    @classmethod
    def validate_redis_url(cls, v: str, info) -> str:
        """Ensure Redis URL is not using localhost in production."""
        environment = info.data.get("environment", "development")
        if environment == "production":
            # Check for localhost or default credentials
            placeholder_patterns = [
                "localhost:6379",
                "127.0.0.1:6379",
                "change-this",
                "placeholder",
            ]
            v_lower = v.lower()
            for pattern in placeholder_patterns:
                if pattern in v_lower:
                    raise ValueError(
                        "REDIS_URL must be set to a production Redis instance in production. "
                        "Localhost detected. Set REDIS_URL environment variable."
                    )
        return v

    # ==========================================================================
    # Object Storage (S3/MinIO)
    # ==========================================================================
    s3_endpoint_url: str | None = Field(
        default="http://localhost:9000",
        description="S3/MinIO endpoint URL",
    )
    s3_access_key: str = Field(default="minioadmin", description="S3 access key")
    s3_secret_key: str = Field(default="minioadmin", description="S3 secret key")
    s3_bucket_name: str = Field(default="pybase", description="S3 bucket name")
    s3_region: str = Field(default="us-east-1", description="S3 region")

    @field_validator("s3_access_key", mode="before")
    @classmethod
    def validate_s3_access_key(cls, v: str, info) -> str:
        """Ensure S3 access key is not using placeholder values in production."""
        environment = info.data.get("environment", "development")
        if environment == "production":
            placeholder_patterns = ["minioadmin", "change-this", "placeholder", "your-access-key"]
            v_lower = v.lower()
            for pattern in placeholder_patterns:
                if pattern in v_lower:
                    raise ValueError(
                        "S3_ACCESS_KEY must be set to a real access key in production. "
                        "Default/placeholder value detected. Set S3_ACCESS_KEY environment variable."
                    )
        return v

    @field_validator("s3_secret_key", mode="before")
    @classmethod
    def validate_s3_secret_key(cls, v: str, info) -> str:
        """Ensure S3 secret key is not using placeholder values in production."""
        environment = info.data.get("environment", "development")
        if environment == "production":
            placeholder_patterns = ["minioadmin", "change-this", "placeholder", "your-secret-key"]
            v_lower = v.lower()
            for pattern in placeholder_patterns:
                if pattern in v_lower:
                    raise ValueError(
                        "S3_SECRET_KEY must be set to a real secret key in production. "
                        "Default/placeholder value detected. Set S3_SECRET_KEY environment variable."
                    )
        return v

    # File uploads
    max_upload_size_mb: int = Field(default=100, description="Max upload size in MB")
    allowed_extensions: list[str] = Field(
        default=[
            "pdf",
            "dxf",
            "dwg",
            "ifc",
            "stp",
            "step",
            "png",
            "jpg",
            "jpeg",
            "gif",
            "webp",
            "xlsx",
            "csv",
            "json",
        ],
        description="Allowed file extensions",
    )

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v: Any) -> list[str]:
        """Parse allowed extensions from comma-separated string."""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",") if ext.strip()]
        return v

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    # ==========================================================================
    # Authentication Settings
    # ==========================================================================
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )
    password_min_length: int = Field(default=8, description="Minimum password length")
    api_key_prefix: str = Field(default="pybase_", description="API key prefix")

    # ==========================================================================
    # SSO Configuration (SAML/OIDC)
    # ==========================================================================
    sso_enabled: bool = Field(default=False, description="Enable SSO authentication")
    sso_only_mode: bool = Field(
        default=False, description="Enforce SSO-only authentication (disable local login)"
    )
    sso_jit_provisioning: bool = Field(
        default=True, description="Enable Just-In-Time user provisioning from SSO"
    )
    sso_auto_provision_default_role: str = Field(
        default="viewer", description="Default role for JIT-provisioned users"
    )
    sso_admin_recovery_email: str | None = Field(
        default=None, description="Admin email for local login recovery in SSO-only mode"
    )
    sso_allowed_domains: list[str] = Field(
        default=[], description="Allowed email domains for SSO authentication"
    )
    sso_role_mapping_enabled: bool = Field(
        default=True, description="Enable role/group mapping from IdP claims"
    )
    sso_role_claim_name: str = Field(
        default="roles", description="Claim name for user roles in IdP token"
    )
    sso_group_claim_name: str = Field(
        default="groups", description="Claim name for user groups in IdP token"
    )
    sso_session_timeout_minutes: int = Field(
        default=480, description="SSO session timeout in minutes (default: 8 hours)"
    )

    @field_validator("sso_allowed_domains", mode="before")
    @classmethod
    def parse_sso_allowed_domains(cls, v: Any) -> list[str]:
        """Parse SSO allowed domains from comma-separated string."""
        if isinstance(v, str):
            return [domain.strip().lower() for domain in v.split(",") if domain.strip()]
        return v

    # ==========================================================================
    # SAML Configuration
    # ==========================================================================
    saml_sp_entity_id: str = Field(
        default="pybase", description="SAML Service Provider entity ID"
    )
    saml_sp_acs_url: str | None = Field(
        default=None, description="SAML Assertion Consumer Service URL (auto-generated if None)"
    )
    saml_sp_slo_url: str | None = Field(
        default=None, description="SAML Single Logout Service URL (auto-generated if None)"
    )
    saml_idp_metadata_url: str | None = Field(
        default=None, description="SAML Identity Provider metadata URL"
    )
    saml_idp_metadata_file: str | None = Field(
        default=None, description="Path to SAML IdP metadata XML file"
    )
    saml_idp_sso_url: str | None = Field(
        default=None, description="SAML IdP Single Sign-On URL (overrides metadata)"
    )
    saml_idp_slo_url: str | None = Field(
        default=None, description="SAML IdP Single Logout URL (overrides metadata)"
    )
    saml_idp_cert_file: str | None = Field(
        default=None, description="Path to SAML IdP X.509 certificate file"
    )
    saml_sp_cert_file: str | None = Field(
        default=None, description="Path to SAML SP X.509 certificate file"
    )
    saml_sp_key_file: str | None = Field(
        default=None, description="Path to SAML SP private key file"
    )
    saml_nameid_format: str = Field(
        default="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
        description="SAML NameID format",
    )
    saml_want_assertions_signed: bool = Field(
        default=True, description="Require signed SAML assertions"
    )
    saml_want_response_signed: bool = Field(
        default=True, description="Require signed SAML responses"
    )
    saml_want_assertions_encrypted: bool = Field(
        default=False, description="Require encrypted SAML assertions"
    )
    saml_attribute_mapping: dict[str, str] = Field(
        default={
            "email": "email",
            "first_name": "firstName",
            "last_name": "lastName",
            "roles": "roles",
            "groups": "groups",
        },
        description="SAML attribute to user field mapping",
    )

    @field_validator("saml_attribute_mapping", mode="before")
    @classmethod
    def parse_saml_attribute_mapping(cls, v: Any) -> dict[str, str]:
        """Parse SAML attribute mapping from JSON string or return dict."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("SAML_ATTRIBUTE_MAPPING must be valid JSON")
        return v

    @property
    def saml_enabled(self) -> bool:
        """Check if SAML authentication is enabled."""
        return self.sso_enabled and bool(
            self.saml_idp_metadata_url or self.saml_idp_metadata_file
        )

    # ==========================================================================
    # OIDC Configuration
    # ==========================================================================
    oidc_client_id: str | None = Field(
        default=None, description="OIDC client ID"
    )
    oidc_client_secret: str | None = Field(
        default=None, description="OIDC client secret"
    )
    oidc_discovery_url: str | None = Field(
        default=None, description="OIDC discovery URL (well-known configuration)"
    )
    oidc_auth_endpoint: str | None = Field(
        default=None, description="OIDC authorization endpoint (overrides discovery)"
    )
    oidc_token_endpoint: str | None = Field(
        default=None, description="OIDC token endpoint (overrides discovery)"
    )
    oidc_userinfo_endpoint: str | None = Field(
        default=None, description="OIDC userinfo endpoint (overrides discovery)"
    )
    oidc_jwks_uri: str | None = Field(
        default=None, description="OIDC JWKS URI for token verification (overrides discovery)"
    )
    oidc_scopes: list[str] = Field(
        default=["openid", "email", "profile"], description="OIDC scopes to request"
    )
    oidc_response_type: str = Field(
        default="code", description="OIDC response type (code or token)"
    )
    oidc_response_mode: str = Field(
        default="query", description="OIDC response mode (query, form_post, or fragment)"
    )
    oidc_prompt: str | None = Field(
        default=None, description="OIDC prompt (login, consent, etc.)"
    )
    oidc_acr_values: str | None = Field(
        default=None, description="OIDC ACR values for authentication context"
    )
    oidc_claims_mapping: dict[str, str] = Field(
        default={
            "email": "email",
            "first_name": "given_name",
            "last_name": "family_name",
            "roles": "roles",
            "groups": "groups",
        },
        description="OIDC claims to user field mapping",
    )

    @field_validator("oidc_scopes", mode="before")
    @classmethod
    def parse_oidc_scopes(cls, v: Any) -> list[str]:
        """Parse OIDC scopes from space-separated string."""
        if isinstance(v, str):
            return [scope.strip() for scope in v.split() if scope.strip()]
        return v

    @field_validator("oidc_claims_mapping", mode="before")
    @classmethod
    def parse_oidc_claims_mapping(cls, v: Any) -> dict[str, str]:
        """Parse OIDC claims mapping from JSON string or return dict."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("OIDC_CLAIMS_MAPPING must be valid JSON")
        return v

    @property
    def oidc_enabled(self) -> bool:
        """Check if OIDC authentication is enabled."""
        return self.sso_enabled and bool(self.oidc_client_id and self.oidc_client_secret)

    # ==========================================================================
    # Email Configuration
    # ==========================================================================
    smtp_host: str | None = Field(default=None, description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str | None = Field(default=None, description="SMTP username")
    smtp_password: str | None = Field(default=None, description="SMTP password")
    smtp_from_email: str = Field(default="noreply@pybase.dev", description="From email address")
    smtp_from_name: str = Field(default="PyBase", description="From name")
    smtp_tls: bool = Field(default=True, description="Use TLS for SMTP")

    @property
    def emails_enabled(self) -> bool:
        """Check if email sending is enabled."""
        return bool(self.smtp_host and self.smtp_user)

    # ==========================================================================
    # CAD/PDF Extraction Settings
    # ==========================================================================
    werk24_api_key: str | None = Field(
        default=None, description="Werk24 API key for engineering drawing extraction"
    )
    tesseract_cmd: str = Field(
        default="/usr/bin/tesseract", description="Tesseract OCR command path"
    )
    extraction_max_pages: int = Field(default=100, description="Max pages to extract from PDF")
    extraction_dpi: int = Field(default=300, description="DPI for PDF rendering")
    extraction_timeout_seconds: int = Field(
        default=300, description="Extraction timeout in seconds"
    )

    @property
    def werk24_enabled(self) -> bool:
        """Check if Werk24 extraction is enabled."""
        return bool(self.werk24_api_key)

    # ==========================================================================
    # Search Settings (Meilisearch)
    # ==========================================================================
    meilisearch_url: str | None = Field(default=None, description="Meilisearch URL")
    meilisearch_api_key: str | None = Field(default=None, description="Meilisearch API key")

    @property
    def search_enabled(self) -> bool:
        """Check if search is enabled."""
        return bool(self.meilisearch_url)

    # ==========================================================================
    # Celery / Background Tasks
    # ==========================================================================
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend"
    )

    # ==========================================================================
    # Monitoring
    # ==========================================================================
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, description="OpenTelemetry OTLP endpoint"
    )
    otel_service_name: str = Field(default="pybase", description="OpenTelemetry service name")

    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    rate_limit_per_minute: int = Field(default=100, description="Rate limit per minute")
    rate_limit_per_hour: int = Field(default=1000, description="Rate limit per hour")

    # ==========================================================================
    # Feature Flags
    # ==========================================================================
    enable_registration: bool = Field(default=True, description="Enable user registration")
    enable_api_keys: bool = Field(default=True, description="Enable API keys")
    enable_extraction: bool = Field(default=True, description="Enable CAD/PDF extraction")
    enable_websockets: bool = Field(default=True, description="Enable WebSockets")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
