"""
PyBase FastAPI Application Entry Point.

This module creates and configures the FastAPI application instance.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pybase.api.v1 import router as v1_router
from pybase.core.audit_middleware import AuditLoggingMiddleware
from pybase.core.config import settings
from pybase.core.exceptions import PyBaseException
from pybase.core.logging import get_logger, setup_logging
from pybase.db.session import close_db, init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # Initialize database connection
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    # Setup logging
    setup_logging(
        log_level=settings.log_level,
        json_logs=settings.environment == "production",
    )

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description="Self-hosted Airtable alternative with CAD/PDF extraction",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register audit logging middleware
    if settings.audit_enabled:
        app.add_middleware(AuditLoggingMiddleware)
        logger.info("Audit logging middleware registered")

    # Register exception handlers
    register_exception_handlers(app)

    # Register routes
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers."""

    @app.exception_handler(PyBaseException)
    async def pybase_exception_handler(
        request: Request,
        exc: PyBaseException,
    ) -> JSONResponse:
        """Handle PyBase custom exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": errors},
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception(f"Unexpected error: {exc}")

        # In production, don't expose internal error details
        if settings.environment == "production":
            message = "An unexpected error occurred"
        else:
            message = str(exc)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": message,
                }
            },
        )


# Create the application instance
app = create_app()


# Add a simple root endpoint
@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Root endpoint - redirects to docs or returns basic info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_v1_prefix}/docs" if settings.debug else None,
    }
