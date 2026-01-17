"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient

from pybase.core.config import settings


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the basic health check endpoint."""
    response = await client.get(f"{settings.api_v1_prefix}/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == settings.environment
    assert data["version"] == settings.app_version


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """Test the readiness check endpoint."""
    response = await client.get(f"{settings.api_v1_prefix}/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_app_info(client: AsyncClient):
    """Test the application info endpoint."""
    response = await client.get(f"{settings.api_v1_prefix}/info")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == settings.app_name
    assert data["version"] == settings.app_version
    assert "features" in data
