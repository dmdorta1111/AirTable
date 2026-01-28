"""
Metrics endpoints.

Provides endpoints for exposing Prometheus metrics.
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, CollectorRegistry
from prometheus_client.core import REGISTRY as DEFAULT_REGISTRY

from pybase.core.config import settings

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Exposes application metrics in Prometheus text format.
    Used by Prometheus for scraping application metrics.

    The endpoint returns metrics collected by the prometheus_client library,
    including:
    - HTTP request counts and latency (from PrometheusMiddleware)
    - CAD extraction task metrics
    - Database query metrics
    - Cache operation metrics
    - WebSocket connection metrics

    Returns:
        Response with Prometheus metrics in text format and appropriate
        Content-Type header for Prometheus to consume.

    Example:
        ```bash
        curl http://localhost:8000/api/v1/metrics
        ```
    """
    # Check if metrics are enabled in settings
    if not settings.prometheus_enabled:
        return Response(
            content="Metrics are disabled",
            status_code=503,
            media_type="text/plain",
        )

    # Generate the latest metrics in Prometheus text format
    metrics_output = generate_latest(DEFAULT_REGISTRY)

    return Response(
        content=metrics_output,
        status_code=200,
        media_type=CONTENT_TYPE_LATEST,
    )
