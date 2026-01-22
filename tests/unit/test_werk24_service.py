"""Unit tests for Werk24Service."""

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError, PermissionDeniedError
from pybase.db.base import utc_now
from pybase.models.user import User
from pybase.models.werk24_usage import Werk24Usage
from pybase.models.workspace import Workspace, WorkspaceMember
from pybase.services.werk24 import Werk24Service


@pytest_asyncio.fixture
async def werk24_service() -> Werk24Service:
    """Create a Werk24Service instance."""
    return Werk24Service()


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace."""
    workspace = Workspace(
        name="Test Workspace",
        owner_id=str(test_user.id),
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add user as workspace member
    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role="owner",
    )
    db_session.add(member)
    await db_session.commit()

    return workspace


@pytest_asyncio.fixture
async def test_usage_record(
    db_session: AsyncSession,
    test_user: User,
    test_workspace: Workspace,
) -> Werk24Usage:
    """Create a test usage record."""
    usage = Werk24Usage(
        user_id=str(test_user.id),
        workspace_id=str(test_workspace.id),
        request_type="extract_async",
        ask_types=json.dumps(["dimensions", "gdts"]),
        source_file="test_drawing.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        api_key_used="test_key_123",
        request_ip="127.0.0.1",
        user_agent="pytest",
    )
    db_session.add(usage)
    await db_session.commit()
    await db_session.refresh(usage)
    return usage


@pytest.mark.asyncio
async def test_create_usage_record(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_workspace: Workspace,
):
    """Test creating a usage record."""
    usage = await werk24_service.create_usage_record(
        db=db_session,
        user_id=str(test_user.id),
        request_type="extract_async",
        ask_types=["dimensions", "gdts", "title_block"],
        workspace_id=str(test_workspace.id),
        source_file="drawing.pdf",
        file_size_bytes=2048,
        file_type="pdf",
        api_key_used="key_abc123",
        request_ip="192.168.1.1",
        user_agent="TestClient/1.0",
    )

    assert usage.id is not None
    assert usage.user_id == str(test_user.id)
    assert usage.workspace_id == str(test_workspace.id)
    assert usage.request_type == "extract_async"
    assert json.loads(usage.ask_types) == ["dimensions", "gdts", "title_block"]
    assert usage.source_file == "drawing.pdf"
    assert usage.file_size_bytes == 2048
    assert usage.file_type == "pdf"
    assert usage.api_key_used == "key_abc123"
    assert usage.request_ip == "192.168.1.1"
    assert usage.user_agent == "TestClient/1.0"
    assert usage.success is False  # Default value
    assert usage.created_at is not None


@pytest.mark.asyncio
async def test_create_usage_record_minimal(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
):
    """Test creating a usage record with minimal data."""
    usage = await werk24_service.create_usage_record(
        db=db_session,
        user_id=str(test_user.id),
        request_type="extract_async",
        ask_types=["dimensions"],
    )

    assert usage.id is not None
    assert usage.user_id == str(test_user.id)
    assert usage.workspace_id is None
    assert usage.request_type == "extract_async"
    assert json.loads(usage.ask_types) == ["dimensions"]


@pytest.mark.asyncio
async def test_update_usage_record_success(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_usage_record: Werk24Usage,
):
    """Test updating a usage record with success status."""
    updated = await werk24_service.update_usage_record(
        db=db_session,
        usage_id=str(test_usage_record.id),
        user_id=str(test_user.id),
        success=True,
        status_code=200,
        processing_time_ms=1500,
        tokens_used=100,
        cost_units=0.5,
        quota_remaining=1000,
        dimensions_extracted=5,
        gdts_extracted=3,
        materials_extracted=1,
        threads_extracted=2,
    )

    assert updated.id == test_usage_record.id
    assert updated.success is True
    assert updated.status_code == 200
    assert updated.processing_time_ms == 1500
    assert updated.tokens_used == 100
    assert updated.cost_units == 0.5
    assert updated.quota_remaining == 1000
    assert updated.dimensions_extracted == 5
    assert updated.gdts_extracted == 3
    assert updated.materials_extracted == 1
    assert updated.threads_extracted == 2
    assert updated.completed_at is not None
    assert updated.error_message is None


@pytest.mark.asyncio
async def test_update_usage_record_failure(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_usage_record: Werk24Usage,
):
    """Test updating a usage record with failure status."""
    error_msg = "API rate limit exceeded"
    updated = await werk24_service.update_usage_record(
        db=db_session,
        usage_id=str(test_usage_record.id),
        user_id=str(test_user.id),
        success=False,
        status_code=429,
        error_message=error_msg,
        processing_time_ms=500,
    )

    assert updated.success is False
    assert updated.status_code == 429
    assert updated.error_message == error_msg
    assert updated.processing_time_ms == 500
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_update_usage_record_not_found(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
):
    """Test updating a non-existent usage record."""
    fake_id = str(uuid4())

    with pytest.raises(NotFoundError) as exc_info:
        await werk24_service.update_usage_record(
            db=db_session,
            usage_id=fake_id,
            user_id=str(test_user.id),
            success=True,
        )

    assert "Usage record not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_usage_record_permission_denied(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_usage_record: Werk24Usage,
):
    """Test updating usage record without permission."""
    other_user_id = str(uuid4())

    with pytest.raises(PermissionDeniedError) as exc_info:
        await werk24_service.update_usage_record(
            db=db_session,
            usage_id=str(test_usage_record.id),
            user_id=other_user_id,
            success=True,
        )

    assert "don't have access" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_usage_by_id(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_usage_record: Werk24Usage,
):
    """Test getting a usage record by ID."""
    usage = await werk24_service.get_usage_by_id(
        db=db_session,
        usage_id=str(test_usage_record.id),
        user_id=str(test_user.id),
    )

    assert usage.id == test_usage_record.id
    assert usage.user_id == str(test_user.id)
    assert usage.request_type == "extract_async"


@pytest.mark.asyncio
async def test_get_usage_by_id_not_found(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
):
    """Test getting a non-existent usage record."""
    fake_id = str(uuid4())

    with pytest.raises(NotFoundError) as exc_info:
        await werk24_service.get_usage_by_id(
            db=db_session,
            usage_id=fake_id,
            user_id=str(test_user.id),
        )

    assert "Usage record not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_usage_by_id_permission_denied(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_usage_record: Werk24Usage,
):
    """Test getting usage record without permission."""
    other_user_id = str(uuid4())

    with pytest.raises(PermissionDeniedError) as exc_info:
        await werk24_service.get_usage_by_id(
            db=db_session,
            usage_id=str(test_usage_record.id),
            user_id=other_user_id,
        )

    assert "don't have access" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_usage_basic(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_usage_record: Werk24Usage,
):
    """Test listing usage records."""
    records, total = await werk24_service.list_usage(
        db=db_session,
        user_id=str(test_user.id),
    )

    assert total >= 1
    assert len(records) >= 1
    assert any(r.id == test_usage_record.id for r in records)


@pytest.mark.asyncio
async def test_list_usage_with_workspace_filter(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_workspace: Workspace,
    test_usage_record: Werk24Usage,
):
    """Test listing usage records filtered by workspace."""
    records, total = await werk24_service.list_usage(
        db=db_session,
        user_id=str(test_user.id),
        workspace_id=str(test_workspace.id),
    )

    assert total >= 1
    assert all(r.workspace_id == str(test_workspace.id) for r in records)


@pytest.mark.asyncio
async def test_list_usage_with_request_type_filter(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_usage_record: Werk24Usage,
):
    """Test listing usage records filtered by request type."""
    records, total = await werk24_service.list_usage(
        db=db_session,
        user_id=str(test_user.id),
        request_type="extract_async",
    )

    assert total >= 1
    assert all(r.request_type == "extract_async" for r in records)


@pytest.mark.asyncio
async def test_list_usage_success_only(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_usage_record: Werk24Usage,
):
    """Test listing only successful usage records."""
    # Mark test record as successful
    await werk24_service.update_usage_record(
        db=db_session,
        usage_id=str(test_usage_record.id),
        user_id=str(test_user.id),
        success=True,
    )

    records, total = await werk24_service.list_usage(
        db=db_session,
        user_id=str(test_user.id),
        success_only=True,
    )

    assert all(r.success is True for r in records)


@pytest.mark.asyncio
async def test_list_usage_with_date_filters(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_usage_record: Werk24Usage,
):
    """Test listing usage records with date filters."""
    start_date = utc_now() - timedelta(days=1)
    end_date = utc_now() + timedelta(days=1)

    records, total = await werk24_service.list_usage(
        db=db_session,
        user_id=str(test_user.id),
        start_date=start_date,
        end_date=end_date,
    )

    assert total >= 1
    assert all(start_date <= r.created_at <= end_date for r in records)


@pytest.mark.asyncio
async def test_list_usage_pagination(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
):
    """Test pagination of usage records."""
    # Create multiple records
    for i in range(5):
        await werk24_service.create_usage_record(
            db=db_session,
            user_id=str(test_user.id),
            request_type=f"type_{i}",
            ask_types=[f"ask_{i}"],
        )

    # Get first page
    page1_records, total = await werk24_service.list_usage(
        db=db_session,
        user_id=str(test_user.id),
        page=1,
        page_size=2,
    )

    assert len(page1_records) == 2
    assert total >= 5

    # Get second page
    page2_records, _ = await werk24_service.list_usage(
        db=db_session,
        user_id=str(test_user.id),
        page=2,
        page_size=2,
    )

    assert len(page2_records) >= 1
    # Ensure different records on different pages
    page1_ids = {r.id for r in page1_records}
    page2_ids = {r.id for r in page2_records}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_get_usage_statistics(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
):
    """Test getting usage statistics."""
    # Create successful record
    usage1 = await werk24_service.create_usage_record(
        db=db_session,
        user_id=str(test_user.id),
        request_type="extract_async",
        ask_types=["dimensions"],
    )
    await werk24_service.update_usage_record(
        db=db_session,
        usage_id=str(usage1.id),
        user_id=str(test_user.id),
        success=True,
        processing_time_ms=1000,
        cost_units=0.5,
        dimensions_extracted=5,
        gdts_extracted=2,
    )

    # Create failed record
    usage2 = await werk24_service.create_usage_record(
        db=db_session,
        user_id=str(test_user.id),
        request_type="extract_async",
        ask_types=["gdts"],
    )
    await werk24_service.update_usage_record(
        db=db_session,
        usage_id=str(usage2.id),
        user_id=str(test_user.id),
        success=False,
        error_message="API error",
        processing_time_ms=500,
    )

    stats = await werk24_service.get_usage_statistics(
        db=db_session,
        user_id=str(test_user.id),
        days=30,
    )

    assert stats["period_days"] == 30
    assert stats["total_requests"] >= 2
    assert stats["successful_requests"] >= 1
    assert stats["failed_requests"] >= 1
    assert 0 <= stats["success_rate"] <= 1.0
    assert "total_extractions" in stats
    assert stats["total_extractions"]["dimensions"] >= 5
    assert stats["total_extractions"]["gdts"] >= 2
    assert "cost" in stats
    assert stats["cost"]["total_units"] >= 0.5
    assert "performance" in stats
    assert "quota" in stats
    assert "request_types" in stats


@pytest.mark.asyncio
async def test_get_usage_statistics_empty(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
):
    """Test getting statistics with no usage records."""
    new_user_id = str(uuid4())

    stats = await werk24_service.get_usage_statistics(
        db=db_session,
        user_id=new_user_id,
        days=30,
    )

    assert stats["total_requests"] == 0
    assert stats["successful_requests"] == 0
    assert stats["failed_requests"] == 0
    assert stats["success_rate"] == 0.0
    assert stats["total_extractions"]["total"] == 0


@pytest.mark.asyncio
async def test_get_workspace_usage_statistics(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_workspace: Workspace,
):
    """Test getting workspace usage statistics."""
    # Create usage records for workspace
    usage = await werk24_service.create_usage_record(
        db=db_session,
        user_id=str(test_user.id),
        workspace_id=str(test_workspace.id),
        request_type="extract_async",
        ask_types=["dimensions"],
    )
    await werk24_service.update_usage_record(
        db=db_session,
        usage_id=str(usage.id),
        user_id=str(test_user.id),
        success=True,
        cost_units=1.0,
        dimensions_extracted=10,
    )

    stats = await werk24_service.get_workspace_usage_statistics(
        db=db_session,
        workspace_id=str(test_workspace.id),
        user_id=str(test_user.id),
        days=30,
    )

    assert stats["workspace_id"] == str(test_workspace.id)
    assert stats["period_days"] == 30
    assert stats["total_requests"] >= 1
    assert stats["successful_requests"] >= 1
    assert "total_extractions" in stats
    assert stats["total_extractions"]["dimensions"] >= 10
    assert "cost" in stats
    assert "user_breakdown" in stats
    assert str(test_user.id) in stats["user_breakdown"]


@pytest.mark.asyncio
async def test_get_workspace_usage_statistics_permission_denied(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_workspace: Workspace,
):
    """Test getting workspace statistics without permission."""
    other_user_id = str(uuid4())

    with pytest.raises(PermissionDeniedError) as exc_info:
        await werk24_service.get_workspace_usage_statistics(
            db=db_session,
            workspace_id=str(test_workspace.id),
            user_id=other_user_id,
            days=30,
        )

    assert "don't have access" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_workspace_usage_statistics_user_breakdown(
    werk24_service: Werk24Service,
    db_session: AsyncSession,
    test_user: User,
    test_workspace: Workspace,
):
    """Test workspace statistics includes user breakdown."""
    # Create multiple records with different success states
    for i in range(3):
        usage = await werk24_service.create_usage_record(
            db=db_session,
            user_id=str(test_user.id),
            workspace_id=str(test_workspace.id),
            request_type="extract_async",
            ask_types=["dimensions"],
        )
        await werk24_service.update_usage_record(
            db=db_session,
            usage_id=str(usage.id),
            user_id=str(test_user.id),
            success=(i % 2 == 0),  # Alternate success/failure
            cost_units=0.5,
        )

    stats = await werk24_service.get_workspace_usage_statistics(
        db=db_session,
        workspace_id=str(test_workspace.id),
        user_id=str(test_user.id),
        days=30,
    )

    user_breakdown = stats["user_breakdown"][str(test_user.id)]
    assert user_breakdown["requests"] >= 3
    assert user_breakdown["successful"] >= 1
    assert user_breakdown["cost_units"] >= 1.5
