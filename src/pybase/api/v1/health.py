"""
Health check endpoints.

Provides endpoints for monitoring application health and readiness.
"""

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import DbSession
from pybase.core.config import settings
from pybase.core.logging import get_logger
from pybase.realtime import get_connection_manager

logger = get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    environment: str
    version: str


class LivenessResponse(BaseModel):
    """Liveness check response model."""

    status: str


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    status: str
    database: str
    redis: str
    details: dict[str, str] | None = None


class MetricsResponse(BaseModel):
    """Application metrics for auto-scaling decisions."""

    websocket_connections: int = Field(
        ..., description="Total active WebSocket connections"
    )
    websocket_unique_users: int = Field(
        ..., description="Total unique users connected via WebSocket"
    )
    websocket_channels: int = Field(
        ..., description="Total active channels with subscribers"
    )
    database_status: str = Field(
        ..., description="Database connection status"
    )
    database_pool_size: int = Field(
        ..., description="Database connection pool size"
    )
    database_pool_checked_out: int = Field(
        ..., description="Number of database connections currently checked out"
    )
    database_pool_overflow: int = Field(
        ..., description="Number of overflow connections in use"
    )
    database_pool_available: int = Field(
        ..., description="Number of available connections in pool"
    )
    redis_status: str = Field(
        ..., description="Redis connection status"
    )
    redis_connected: bool = Field(
        ..., description="Whether Redis is connected"
    )


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


@router.get("/live", response_model=LivenessResponse)
async def liveness_check() -> LivenessResponse:
    """
    Liveness check endpoint.

    Simple check to verify the application is running.
    Used by Kubernetes for liveness probes - if this fails, the container
    will be restarted.
    """
    return LivenessResponse(status="alive")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(db: DbSession) -> ReadinessResponse:
    """
    Readiness check endpoint.

    Checks that all dependencies (database, Redis, etc.) are available.
    Used by Kubernetes for readiness probes - if this fails, traffic will
    not be routed to this instance.
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
            redis="unknown",
            details=details,
        )

    # Check Redis connection
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            max_connections=1,
            decode_responses=True,
        )
        await redis_client.ping()
        await redis_client.close()
        redis_status = "connected"
    except Exception as e:
        logger.warning(f"Redis readiness check failed: {e}")
        redis_status = f"error: {str(e)}"
        return ReadinessResponse(
            status="unhealthy",
            database=db_status,
            redis=redis_status,
            details=details,
        )

    return ReadinessResponse(
        status="ready",
        database=db_status,
        redis=redis_status,
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


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: DbSession) -> MetricsResponse:
    """
    Get application metrics for auto-scaling decisions.

    Returns connection counts, queue depths, and resource utilization metrics.
    Used by auto-scaling systems to make scaling decisions.

    Includes:
    - WebSocket connection statistics
    - Database connection pool status
    - Redis connection status
    """
    # Get WebSocket connection stats
    manager = get_connection_manager()
    ws_stats = manager.get_stats()

    # Check database status and pool metrics
    db_status = "unknown"
    pool_size = settings.db_pool_size
    pool_checked_out = 0
    pool_overflow = 0
    pool_available = 0

    try:
        # Verify database is accessible
        await db.execute(text("SELECT 1"))
        db_status = "connected"

        # Get connection pool metrics
        from pybase.db.session import engine
        pool = engine.pool

        # Get pool statistics
        pool_checked_out = pool.checkedout()
        pool_overflow = pool.overflow()
        pool_available = pool.size() - pool_checked_out

    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.warning(f"Database metrics check failed: {e}")

    # Check Redis status
    redis_status = "unknown"
    redis_connected = False
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            max_connections=1,
            decode_responses=True,
        )
        await redis_client.ping()
        await redis_client.close()
        redis_status = "connected"
        redis_connected = True
    except Exception as e:
        redis_status = f"error: {str(e)}"
        logger.warning(f"Redis metrics check failed: {e}")

    return MetricsResponse(
        websocket_connections=ws_stats["total_connections"],
        websocket_unique_users=ws_stats["total_users"],
        websocket_channels=len(ws_stats["channels"]),
        database_status=db_status,
        database_pool_size=pool_size,
        database_pool_checked_out=pool_checked_out,
        database_pool_overflow=pool_overflow,
        database_pool_available=pool_available,
        redis_status=redis_status,
        redis_connected=redis_connected,
    )

