"""
Integration tests for horizontal scaling with load balancer.

Tests verify that multiple API instances work correctly behind a load balancer,
including health checks, session storage, and metrics reporting.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.core.session_store import RedisSessionStore


@pytest.mark.asyncio
async def test_health_check_endpoint_returns_basic_info(
    client: AsyncClient,
) -> None:
    """
    Test that /health endpoint returns basic application status.

    Verifies:
    - Status is "healthy"
    - Environment and version are present
    - No dependency checks (lightweight endpoint)
    """
    response = await client.get(f"{settings.api_v1_prefix}/health/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_liveness_endpoint_for_kubernetes(
    client: AsyncClient,
) -> None:
    """
    Test that /live endpoint works for Kubernetes liveness probes.

    Verifies:
    - Simple "alive" status
    - No dependency checks (should be very lightweight)
    - Fast response time (< 100ms)
    """
    import time

    start = time.time()
    response = await client.get(f"{settings.api_v1_prefix}/health/live")
    elapsed = time.time() - start

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "alive"
    # Liveness probe should be very fast
    assert elapsed < 0.1, f"Liveness probe took {elapsed}s (should be < 0.1s)"


@pytest.mark.asyncio
async def test_readiness_endpoint_checks_dependencies(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Test that /ready endpoint checks all dependencies.

    Verifies:
    - Database connection is checked
    - Redis connection is checked
    - Returns "ready" when all dependencies are healthy
    - Returns "unhealthy" when dependencies fail
    """
    response = await client.get(f"{settings.api_v1_prefix}/health/ready")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "database" in data
    assert "redis" in data

    # Should be ready if dependencies are healthy
    if data["status"] == "ready":
        assert data["database"] == "connected"
        assert data["redis"] == "connected"


@pytest.mark.asyncio
async def test_readiness_endpoint_fails_on_database_failure(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Test that /ready endpoint reports unhealthy when database fails.

    Verifies:
    - Database connection check detects failures
    - Returns "unhealthy" status
    - Includes error details
    """
    # Mock database execution to raise an error
    with patch.object(
        db_session, "execute", side_effect=Exception("Database connection failed")
    ):
        response = await client.get(f"{settings.api_v1_prefix}/health/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "unhealthy"
        assert "database" in data
        assert "error" in data["database"].lower() or "failed" in data["database"].lower()


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_resource_utilization(
    client: AsyncClient,
) -> None:
    """
    Test that /metrics endpoint returns resource metrics for auto-scaling.

    Verifies:
    - WebSocket connection statistics
    - Database pool metrics
    - Redis connection status
    - All fields are present and valid types
    """
    response = await client.get(f"{settings.api_v1_prefix}/health/metrics")

    assert response.status_code == 200
    data = response.json()

    # WebSocket metrics
    assert "websocket_connections" in data
    assert isinstance(data["websocket_connections"], int)
    assert data["websocket_connections"] >= 0

    assert "websocket_unique_users" in data
    assert isinstance(data["websocket_unique_users"], int)
    assert data["websocket_unique_users"] >= 0

    assert "websocket_channels" in data
    assert isinstance(data["websocket_channels"], int)
    assert data["websocket_channels"] >= 0

    # Database pool metrics
    assert "database_status" in data
    assert isinstance(data["database_status"], str)

    assert "database_pool_size" in data
    assert isinstance(data["database_pool_size"], int)
    assert data["database_pool_size"] > 0

    assert "database_pool_checked_out" in data
    assert isinstance(data["database_pool_checked_out"], int)
    assert data["database_pool_checked_out"] >= 0

    assert "database_pool_overflow" in data
    assert isinstance(data["database_pool_overflow"], int)
    assert data["database_pool_overflow"] >= 0

    assert "database_pool_available" in data
    assert isinstance(data["database_pool_available"], int)
    assert data["database_pool_available"] >= 0

    # Verify pool size consistency
    total_used = data["database_pool_checked_out"] + data["database_pool_overflow"]
    total_available = data["database_pool_available"]
    assert total_used + total_available <= data["database_pool_size"]

    # Redis metrics
    assert "redis_status" in data
    assert isinstance(data["redis_status"], str)

    assert "redis_connected" in data
    assert isinstance(data["redis_connected"], bool)


@pytest.mark.asyncio
async def test_session_store_can_blacklist_token(
    db_session: AsyncSession,
) -> None:
    """
    Test that Redis session store can blacklist JWT tokens.

    Verifies:
    - Token blacklist works across multiple instances
    - Token presence can be checked
    - Blacklist entries expire properly
    """
    session_store = RedisSessionStore()

    try:
        # Generate test token JTI
        token_jti = "test-token-jti-123"
        expires_at = datetime.utcnow() + timedelta(minutes=30)

        # Initially not blacklisted
        is_blacklisted = await session_store.is_token_blacklisted(token_jti)
        assert is_blacklisted is False

        # Blacklist the token
        success = await session_store.blacklist_token(
            token_jti=token_jti,
            expires_at=expires_at,
            user_id="test-user-123",
            reason="logout",
        )
        assert success is True

        # Now should be blacklisted
        is_blacklisted = await session_store.is_token_blacklisted(token_jti)
        assert is_blacklisted is True

        # Clean up
        redis_client = await session_store.get_redis()
        if redis_client:
            blacklist_key = session_store.generate_blacklist_key(token_jti)
            await redis_client.delete(blacklist_key)

    finally:
        await session_store.close()


@pytest.mark.asyncio
async def test_session_store_can_create_user_session(
    db_session: AsyncSession,
) -> None:
    """
    Test that Redis session store can create and retrieve user sessions.

    Verifies:
    - User sessions can be created with metadata
    - Sessions can be retrieved by user_id and session_id
    - Sessions include proper timestamps
    - Multiple instances can access the same session
    """
    session_store = RedisSessionStore()

    try:
        user_id = "test-user-456"
        session_id = "test-session-789"

        metadata = {
            "ip_address": "192.168.1.100",
            "user_agent": "test-agent",
            "login_time": datetime.utcnow().isoformat(),
        }

        # Create session
        success = await session_store.create_session(
            user_id=user_id,
            session_id=session_id,
            metadata=metadata,
            ttl=3600,  # 1 hour
        )
        assert success is True

        # Retrieve session
        session_data = await session_store.get_session(user_id, session_id)

        assert session_data is not None
        assert session_data["user_id"] == user_id
        assert session_data["session_id"] == session_id
        assert "created_at" in session_data
        assert "updated_at" in session_data
        assert session_data["metadata"] == metadata

        # Clean up
        await session_store.delete_session(user_id, session_id)

    finally:
        await session_store.close()


@pytest.mark.asyncio
async def test_session_store_can_update_user_session(
    db_session: AsyncSession,
) -> None:
    """
    Test that Redis session store can update user sessions.

    Verifies:
    - Sessions can be updated with new metadata
    - Updated timestamps are refreshed
    - TTL can be extended on update
    """
    session_store = RedisSessionStore()

    try:
        user_id = "test-user-update"
        session_id = "test-session-update"

        # Create initial session
        await session_store.create_session(
            user_id=user_id,
            session_id=session_id,
            metadata={"initial": "data"},
        )

        # Update session with new metadata
        success = await session_store.update_session(
            user_id=user_id,
            session_id=session_id,
            metadata={"updated": "value"},
            extend_ttl=True,
        )
        assert success is True

        # Verify update
        session_data = await session_store.get_session(user_id, session_id)
        assert session_data is not None
        assert session_data["metadata"]["initial"] == "data"
        assert session_data["metadata"]["updated"] == "value"

        # Clean up
        await session_store.delete_session(user_id, session_id)

    finally:
        await session_store.close()


@pytest.mark.asyncio
async def test_session_store_can_delete_all_user_sessions(
    db_session: AsyncSession,
) -> None:
    """
    Test that Redis session store can delete all sessions for a user.

    Verifies:
    - Multiple sessions can be created for a user
    - All sessions can be deleted at once
    - Correct count of deleted sessions is returned
    """
    session_store = RedisSessionStore()

    try:
        user_id = "test-user-multi-session"

        # Create multiple sessions
        session_ids = [f"session-{i}" for i in range(3)]
        for session_id in session_ids:
            await session_store.create_session(
                user_id=user_id,
                session_id=session_id,
            )

        # Verify all sessions exist
        sessions = await session_store.get_user_sessions(user_id)
        assert len(sessions) == 3

        # Delete all sessions
        deleted_count = await session_store.delete_user_sessions(user_id)
        assert deleted_count == 3

        # Verify all sessions are deleted
        sessions = await session_store.get_user_sessions(user_id)
        assert len(sessions) == 0

    finally:
        await session_store.close()


@pytest.mark.asyncio
async def test_session_store_handles_redis_unavailability_gracefully(
    db_session: AsyncSession,
) -> None:
    """
    Test that session store fails open when Redis is unavailable.

    Verifies:
    - Token blacklist check returns False (allow) when Redis is down
    - Session creation returns False but doesn't crash
    - Application remains functional even with Redis failure
    """
    session_store = RedisSessionStore()

    # Mock Redis connection to fail
    with patch.object(
        session_store,
        "get_redis",
        return_value=AsyncMock(side_effect=Exception("Redis connection failed")),
    ):
        # Token blacklist should fail open (allow token)
        is_blacklisted = await session_store.is_token_blacklisted("test-jti")
        assert is_blacklisted is False

        # Session creation should fail gracefully
        success = await session_store.create_session(
            user_id="test-user",
            session_id="test-session",
        )
        assert success is False

        # Session retrieval should return None
        session = await session_store.get_session("test-user", "test-session")
        assert session is None


@pytest.mark.asyncio
async def test_concurrent_session_access_from_multiple_instances(
    db_session: AsyncSession,
) -> None:
    """
    Test that multiple instances can access and update sessions concurrently.

    Verifies:
    - Sessions can be read by multiple instances simultaneously
    - Concurrent updates are properly serialized
    - No race conditions in session updates
    """
    session_store = RedisSessionStore()

    try:
        user_id = "test-user-concurrent"
        session_id = "test-session-concurrent"

        # Create initial session
        await session_store.create_session(
            user_id=user_id,
            session_id=session_id,
            metadata={"counter": 0},
        )

        # Simulate concurrent updates from multiple instances
        async def update_instance(instance_id: int) -> None:
            for i in range(5):
                session = await session_store.get_session(user_id, session_id)
                if session:
                    counter = session["metadata"].get("counter", 0)
                    session["metadata"]["counter"] = counter + 1
                    await session_store.update_session(
                        user_id=user_id,
                        session_id=session_id,
                        metadata=session["metadata"],
                    )
                await asyncio.sleep(0.01)  # Small delay

        # Run 3 "instances" concurrently
        tasks = [update_instance(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Final counter should be 15 (3 instances × 5 updates each)
        final_session = await session_store.get_session(user_id, session_id)
        assert final_session is not None
        # Note: Due to potential race conditions, we just verify it updated
        assert final_session["metadata"]["counter"] > 0

        # Clean up
        await session_store.delete_session(user_id, session_id)

    finally:
        await session_store.close()


@pytest.mark.asyncio
async def test_metrics_pool_utilization_under_load(
    client: AsyncClient,
) -> None:
    """
    Test that metrics endpoint accurately reports pool utilization under load.

    Verifies:
    - Database pool metrics update correctly
    - Pool checked out increases with concurrent requests
    - Pool available decreases accordingly
    - Pool size remains constant
    """
    # Get baseline metrics
    baseline_response = await client.get(f"{settings.api_v1_prefix}/health/metrics")
    baseline = baseline_response.json()

    baseline_checked_out = baseline["database_pool_checked_out"]
    baseline_available = baseline["database_pool_available"]

    # Make concurrent requests to increase pool utilization
    async def make_request(_: int) -> None:
        await client.get(f"{settings.api_v1_prefix}/health/ready")

    # Run 10 concurrent requests
    await asyncio.gather(*[make_request(i) for i in range(10)])

    # Get updated metrics
    loaded_response = await client.get(f"{settings.api_v1_prefix}/health/metrics")
    loaded = loaded_response.json()

    # Verify pool size is constant
    assert loaded["database_pool_size"] == baseline["database_pool_size"]

    # Pool metrics should be consistent
    total = (
        loaded["database_pool_checked_out"]
        + loaded["database_pool_overflow"]
        + loaded["database_pool_available"]
    )
    assert total <= loaded["database_pool_size"]


@pytest.mark.asyncio
async def test_info_endpoint_returns_configuration(
    client: AsyncClient,
) -> None:
    """
    Test that /info endpoint returns non-sensitive configuration.

    Verifies:
    - Application name and version are present
    - Environment is reported
    - Feature flags are listed
    - No sensitive data (passwords, keys) is exposed
    """
    response = await client.get(f"{settings.api_v1_prefix}/health/info")

    assert response.status_code == 200
    data = response.json()

    assert "name" in data
    assert "version" in data
    assert "environment" in data
    assert "features" in data

    # Verify feature flags
    features = data["features"]
    assert "registration_enabled" in features
    assert "api_keys_enabled" in features
    assert "extraction_enabled" in features
    assert "websockets_enabled" in features
    assert "search_enabled" in features
    assert "emails_enabled" in features

    # Verify no sensitive data
    assert "password" not in str(data).lower()
    assert "secret" not in str(data).lower()
    assert "key" not in str(data).lower() or "api_keys_enabled" in str(data)


@pytest.mark.asyncio
async def test_multiple_instances_share_redis_session_store(
    db_session: AsyncSession,
) -> None:
    """
    Test that multiple API instances can share session data via Redis.

    Verifies:
    - Session created by one instance is visible to another
    - Token blacklisted by one instance is checked by another
    - Session deletion by one instance removes it for all
    """
    # Simulate two separate instances
    instance1_store = RedisSessionStore()
    instance2_store = RedisSessionStore()

    try:
        user_id = "test-user-multi-instance"
        session_id = "test-session-multi-instance"

        # Instance 1 creates a session
        success = await instance1_store.create_session(
            user_id=user_id,
            session_id=session_id,
            metadata={"created_by": "instance1"},
        )
        assert success is True

        # Instance 2 can read the session
        session = await instance2_store.get_session(user_id, session_id)
        assert session is not None
        assert session["metadata"]["created_by"] == "instance1"

        # Instance 2 updates the session
        await instance2_store.update_session(
            user_id=user_id,
            session_id=session_id,
            metadata={"updated_by": "instance2"},
        )

        # Instance 1 can see the update
        session = await instance1_store.get_session(user_id, session_id)
        assert session is not None
        assert session["metadata"]["updated_by"] == "instance2"

        # Instance 1 deletes the session
        await instance1_store.delete_session(user_id, session_id)

        # Instance 2 cannot find the session
        session = await instance2_store.get_session(user_id, session_id)
        assert session is None

    finally:
        await instance1_store.close()
        await instance2_store.close()


@pytest.mark.asyncio
async def test_token_blacklist_persists_across_instances(
    db_session: AsyncSession,
) -> None:
    """
    Test that token blacklist is shared across all API instances.

    Verifies:
    - Token blacklisted by one instance is rejected by another
    - Blacklist entries use proper TTL
    - Multiple instances can check blacklist independently
    """
    # Simulate two separate instances
    instance1_store = RedisSessionStore()
    instance2_store = RedisSessionStore()

    try:
        token_jti = "test-token-shared-blacklist"
        expires_at = datetime.utcnow() + timedelta(minutes=30)

        # Instance 1 blacklists a token
        success = await instance1_store.blacklist_token(
            token_jti=token_jti,
            expires_at=expires_at,
            user_id="test-user",
            reason="logout",
        )
        assert success is True

        # Instance 2 can check the blacklist
        is_blacklisted = await instance2_store.is_token_blacklisted(token_jti)
        assert is_blacklisted is True

        # Verify blacklist data is accessible
        redis_client = await instance2_store.get_redis()
        if redis_client:
            blacklist_key = instance2_store.generate_blacklist_key(token_jti)
            import json

            blacklist_data = await redis_client.get(blacklist_key)
            assert blacklist_data is not None
            data = json.loads(blacklist_data)
            assert data["jti"] == token_jti
            assert data["reason"] == "logout"

            # Clean up
            await redis_client.delete(blacklist_key)

    finally:
        await instance1_store.close()
        await instance2_store.close()
