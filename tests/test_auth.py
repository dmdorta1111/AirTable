"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.models.user import User


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    """Test user registration."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePassword123",
            "name": "New User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "New User"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    """Test that duplicate email registration fails."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/register",
        json={
            "email": test_user.email,
            "password": "SecurePassword123",
            "name": "Another User",
        },
    )

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test that weak password registration fails."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/register",
        json={
            "email": "weak@example.com",
            "password": "weak",
            "name": "Weak User",
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """Test successful login."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User):
    """Test login with wrong password."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/login",
        json={
            "email": test_user.email,
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "anypassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers: dict[str, str]):
    """Test getting current user info."""
    response = await client.get(
        f"{settings.api_v1_prefix}/auth/me",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test getting current user without authentication."""
    response = await client.get(f"{settings.api_v1_prefix}/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user: User):
    """Test token refresh."""
    # First login to get tokens
    login_response = await client.post(
        f"{settings.api_v1_prefix}/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh the token
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Test token refresh with invalid token."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, auth_headers: dict[str, str]):
    """Test password change."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": "testpassword123",
            "new_password": "NewSecurePassword456",
        },
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, auth_headers: dict[str, str]):
    """Test password change with wrong current password."""
    response = await client.post(
        f"{settings.api_v1_prefix}/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": "wrongpassword",
            "new_password": "NewSecurePassword456",
        },
    )

    assert response.status_code == 400
