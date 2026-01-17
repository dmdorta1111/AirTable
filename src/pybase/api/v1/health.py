"""
Health check endpoints.

Provides endpoints for monitoring application health and readiness.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import DbSession
from pybase.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    environment: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    status: str
    database: str
    details: dict[str, str] | None = None


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns application status without checking dependencies.
    Used by load balancers for basic health monitoring.
    """
    return HealthResponse(
        status="healthy",
        environment=settings.environment,
        version=settings.app_version,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(db: DbSession) -> ReadinessResponse:
    """
    Readiness check endpoint.

    Checks that all dependencies (database, etc.) are available.
    Used by Kubernetes for readiness probes.
    """
    details: dict[str, str] = {}

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        return ReadinessResponse(
            status="unhealthy",
            database=db_status,
            details=details,
        )

    return ReadinessResponse(
        status="ready",
        database=db_status,
        details=details,
    )


@router.get("/info")
async def app_info() -> dict:
    """
    Application information endpoint.

    Returns non-sensitive configuration information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "features": {
            "registration_enabled": settings.enable_registration,
            "api_keys_enabled": settings.enable_api_keys,
            "extraction_enabled": settings.enable_extraction,
            "websockets_enabled": settings.enable_websockets,
            "search_enabled": settings.search_enabled,
            "emails_enabled": settings.emails_enabled,
        },
    }
