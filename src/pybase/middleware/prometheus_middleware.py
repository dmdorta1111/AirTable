"""
Prometheus middleware for automatic HTTP metrics collection.

Provides FastAPI middleware that automatically tracks HTTP request
metrics including request counts, latency, and error rates.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from pybase.core.logging import get_logger
from pybase.metrics import api_latency_histogram, api_request_counter

logger = get_logger(__name__)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Prometheus metrics middleware for FastAPI.

    Automatically records metrics for all HTTP requests including:
    - Request count (labeled by method, endpoint, status)
    - Request latency (labeled by method, endpoint)

    This middleware follows the standard Starlette middleware pattern
    and integrates with Prometheus metrics defined in pybase.metrics.

    Example:
        ```python
        from fastapi import FastAPI
        from pybase.middleware.prometheus_middleware import PrometheusMiddleware

        app = FastAPI()
        app.add_middleware(PrometheusMiddleware)
        ```
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        skip_paths: list[str] | None = None,
        skip_options: bool = True,
    ) -> None:
        """
        Initialize the Prometheus middleware.

        Args:
            app: The ASGI application to wrap
            skip_paths: List of paths to skip metrics collection (e.g., ["/health", "/metrics"])
            skip_options: Whether to skip OPTIONS requests (default: True to reduce noise)
        """
        super().__init__(app)
        self.skip_paths = set(skip_paths or [])
        self.skip_options = skip_options

        if self.skip_paths:
            logger.debug(
                "Prometheus middleware initialized",
                extra={
                    "skip_paths": list(self.skip_paths),
                    "skip_options": self.skip_options,
                },
            )

    def _should_skip_request(self, request: Request) -> bool:
        """
        Determine if a request should be skipped from metrics collection.

        Args:
            request: The incoming HTTP request

        Returns:
            True if the request should be skipped, False otherwise
        """
        # Skip specific paths (e.g., /health, /metrics)
        if request.url.path in self.skip_paths:
            return True

        # Skip OPTIONS requests if configured (reduces metric noise)
        if self.skip_options and request.method == "OPTIONS":
            return True

        return False

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and record Prometheus metrics.

        Measures request duration and records metrics for:
        - Total request count (by method, endpoint, status)
        - Request latency histogram (by method, endpoint)

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler in the chain

        Returns:
            The HTTP response from the next handler

        Note:
            Errors in metrics collection are logged but don't prevent
            the request from being processed. This ensures the middleware
            is non-blocking and doesn't impact application availability.
        """
        # Check if we should skip metrics for this request
        if self._should_skip_request(request):
            return await call_next(request)

        # Start timer for request duration
        start_time = time.time()

        # Process request through the middleware chain
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            # Catch any exceptions to ensure we record the error
            # The exception will be re-raised after recording metrics
            status_code = 500
            error = e
            # Create a minimal response for metrics purposes
            # The actual error will be handled by FastAPI's exception handlers
            response = Response(
                content="Internal Server Error",
                status_code=status_code,
            )

        # Calculate request duration in seconds
        duration = time.time() - start_time

        # Extract method and endpoint for labels
        method = request.method
        endpoint = self._get_endpoint_label(request)

        # Record metrics with error handling
        try:
            # Record request count with method, endpoint, and status labels
            api_request_counter.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code),
            ).inc()

            # Record request latency with method and endpoint labels
            api_latency_histogram.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

        except Exception as metrics_error:
            # Log metrics errors but don't fail the request
            logger.error(
                "Failed to record Prometheus metrics",
                extra={
                    "error": str(metrics_error),
                    "method": method,
                    "endpoint": endpoint,
                    "status": status_code,
                    "duration": duration,
                },
                exc_info=True,
            )

        # Re-raise any exception that occurred during request processing
        if error:
            raise error

        return response

    def _get_endpoint_label(self, request: Request) -> str:
        """
        Get a normalized endpoint label for the request.

        Converts request paths into normalized endpoint names by:
        1. Using the route pattern if available (e.g., /api/v1/records/{id})
        2. Falling back to the path if no route pattern exists
        3. Trailing slashes are normalized

        Args:
            request: The incoming HTTP request

        Returns:
            A string label representing the endpoint
        """
        # Try to get the route pattern from the request scope
        # FastAPI stores the matched route in request.scope
        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            endpoint = route.path
        else:
            # Fallback to the actual path
            endpoint = request.url.path

        # Normalize trailing slashes
        if endpoint.endswith("/") and len(endpoint) > 1:
            endpoint = endpoint[:-1]

        # Replace empty path with "/"
        if not endpoint:
            endpoint = "/"

        return endpoint


__all__ = ["PrometheusMiddleware"]
