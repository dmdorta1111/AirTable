"""
Audit logging middleware for PyBase.

Intercepts all HTTP requests and logs them to the audit trail.
"""

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from pybase.core.config import settings
from pybase.core.logging import get_logger
from pybase.models.audit_log import AuditAction
from pybase.models.user import User

logger = get_logger(__name__)


# Paths to exclude from audit logging (health checks, metrics, etc.)
EXCLUDED_PATHS = {
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic audit logging of HTTP requests.

    Logs all API access with user context, request details, and response status.
    Tamper-evident storage is handled by AuditService.
    """

    def __init__(
        self,
        app: ASGIApp,
        audit_service: Optional["AuditService"] = None,  # type: ignore
    ) -> None:
        """
        Initialize the audit logging middleware.

        Args:
            app: ASGI application
            audit_service: Optional AuditService instance (injected if available)
        """
        super().__init__(app)
        self.audit_service = audit_service

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request and log to audit trail.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler in the chain

        Returns:
            HTTP response from the next handler
        """
        # Check if audit logging is enabled
        if not settings.audit_enabled:
            return await call_next(request)

        # Skip excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Generate request ID for correlation
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Get request start time for duration tracking
        start_time = time.time()

        # Extract user info from request state (set by auth dependency)
        user: Optional[User] = getattr(request.state, "user", None)

        # Extract request context
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)

        # Prepare metadata
        meta = {
            "query_params": query_params,
            "referer": request.headers.get("referer", ""),
            "origin": request.headers.get("origin", ""),
        }

        # Process request and capture response
        response = None
        status_code = None
        error_detail = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception as e:
            # Capture error details
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_detail = str(e)
            logger.exception(f"Request failed: {method} {path}")
            raise

        finally:
            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000
            meta["duration_ms"] = round(duration_ms, 2)

            # Log the request asynchronously (fire and forget)
            # We don't want audit logging to block the response
            if status_code is not None:
                await self._log_request(
                    request=request,
                    user=user,
                    request_id=request_id,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    method=method,
                    path=path,
                    status_code=status_code,
                    error_detail=error_detail,
                    meta=meta,
                )

    async def _log_request(
        self,
        request: Request,
        user: Optional[User],
        request_id: str,
        client_ip: str,
        user_agent: str,
        method: str,
        path: str,
        status_code: int,
        error_detail: Optional[str],
        meta: dict,
    ) -> None:
        """
        Log the request to the audit trail.

        Args:
            request: HTTP request object
            user: Authenticated user (if any)
            request_id: Request correlation ID
            client_ip: Client IP address
            user_agent: User agent string
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            error_detail: Error message (if request failed)
            meta: Additional metadata
        """
        try:
            # Import here to avoid circular imports
            from pybase.db.session import get_db_context
            from pybase.services.audit_service import AuditService

            # Determine action type based on method and status
            action = self._determine_audit_action(method, status_code)

            # Get user info
            user_id = user.id if user else None
            user_email = user.email if user else None

            # Create audit service instance if not provided
            audit_service = self.audit_service or AuditService()

            # Log to database using a separate DB session
            async with get_db_context() as db:
                await audit_service.log_action(
                    db=db,
                    action=action,
                    resource_type="api_request",
                    user_id=user_id,
                    user_email=user_email,
                    resource_id=request_id,
                    old_value=None,
                    new_value={
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "error": error_detail,
                    },
                    ip_address=client_ip,
                    user_agent=user_agent,
                    request_id=request_id,
                    meta=meta,
                )

        except Exception as e:
            # Don't let audit logging failures break the application
            logger.error(f"Failed to log audit entry: {e}")

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request headers.

        Handles proxy headers (X-Forwarded-For, X-Real-IP).

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check for forwarded IP (behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _determine_audit_action(self, method: str, status_code: int) -> AuditAction:
        """
        Determine the audit action type based on HTTP method and status.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            status_code: HTTP status code

        Returns:
            AuditAction enum value
        """
        # Error actions
        if status_code >= 400:
            if status_code >= 500:
                return AuditAction.API_REQUEST_ERROR
            else:
                return AuditAction.API_REQUEST_CLIENT_ERROR

        # Success actions by method
        if method in ("GET", "HEAD", "OPTIONS"):
            return AuditAction.API_REQUEST_READ
        elif method in ("POST", "PUT", "PATCH"):
            return AuditAction.API_REQUEST_WRITE
        elif method == "DELETE":
            return AuditAction.API_REQUEST_DELETE
        else:
            return AuditAction.API_REQUEST_READ
