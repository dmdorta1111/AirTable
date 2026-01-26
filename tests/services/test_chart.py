"""Tests for chart service."""

import json
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from pybase.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from pybase.models.chart import Chart, ChartType
from pybase.schemas.chart import (
    ChartCreate,
    ChartUpdate,
    ChartDuplicate,
    ChartDataRequest,
    DataConfig,
    FilterCondition,
    SortRule,
    AggregationType,
    FilterOperator,
    SortDirection,
)
from pybase.services.chart import ChartService


@pytest.fixture
def chart_service():
    """Create chart service instance."""
    return ChartService()


@pytest.fixture
def mock_dashboard(mocker):
    """Mock dashboard."""
    dashboard = mocker.MagicMock()
    dashboard.id = str(uuid4())
    dashboard.base_id = str(uuid4())
    dashboard.is_deleted = False
    dashboard.is_personal = False
    dashboard.created_by_id = "user-1"
    return dashboard


@pytest.fixture
def mock_table(mocker):
    """Mock table."""
    table = mocker.MagicMock()
    table.id = str(uuid4())
    table.is_deleted = False
    table.base = mocker.MagicMock()
    table.base.workspace_id = str(uuid4())
    return table


@pytest.fixture
def mock_base(mocker):
    """Mock base."""
    base = mocker.MagicMock()
    base.id = str(uuid4())
    base.workspace_id = str(uuid4())
    base.is_deleted = False
    return base


@pytest.fixture
def mock_chart(mocker, mock_dashboard, mock_table):
    """Mock chart."""
    chart = mocker.MagicMock(spec=Chart)
    chart.id = str(uuid4())
    chart.dashboard_id = mock_dashboard.id
    chart.table_id = mock_table.id
    chart.name = "Test Chart"
    chart.description = "Test Description"
    chart.chart_type = ChartType.BAR.value
    chart.position = 0
    chart.width = 6
    chart.height = 4
    chart.is_deleted = False
    chart.created_by_id = "user-1"
    chart.auto_refresh = False
    chart.refresh_interval = None
    chart.cache_duration = None
    chart.last_refreshed_at = None
    chart.needs_refresh = True
    chart.data_config = json.dumps({
        "x_field_id": str(uuid4()),
        "y_field_id": str(uuid4()),
        "aggregation": "count",
        "limit": 100
    })
    chart.filters = "[]"
    chart.sorts = "[]"
    chart.visual_config = "{}"
    chart.axis_config = "{}"
    chart.drilldown_config = "{}"
    chart.get_data_config_dict = lambda: json.loads(chart.data_config)
    chart.get_filters_list = lambda: json.loads(chart.filters)
    chart.get_sorts_list = lambda: json.loads(chart.sorts)
    chart.update_last_refreshed = lambda: None
    chart.soft_delete = lambda: setattr(chart, "is_deleted", True)
    return chart


@pytest.mark.asyncio
async def test_create_chart(chart_service, mocker, mock_dashboard, mock_table, mock_base):
    """Test creating a chart."""
    db = mocker.AsyncMock()
    user_id = "user-1"

    # Mock dependencies
    mocker.patch.object(
        chart_service, "_get_dashboard_with_access", return_value=mock_dashboard
    )
    mocker.patch.object(chart_service, "_get_table_with_access", return_value=mock_table)

    # Mock max position query
    mock_result = mocker.MagicMock()
    mock_result.scalar.return_value = 5
    db.execute.return_value = mock_result

    chart_data = ChartCreate(
        dashboard_id=mock_dashboard.id,
        table_id=mock_table.id,
        name="Sales Chart",
        description="Monthly sales data",
        chart_type=ChartType.LINE,
        position=6,
        width=8,
        height=4,
        data_config=DataConfig(
            x_field_id=uuid4(),
            y_field_id=uuid4(),
            aggregation=AggregationType.SUM,
            limit=50,
        ),
        filters=[],
        sorts=[],
    )

    chart = await chart_service.create_chart(db, user_id, chart_data)

    # Verify chart was added to db
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_get_chart_by_id(chart_service, mocker, mock_chart, mock_dashboard):
    """Test getting a chart by ID."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    chart_id = mock_chart.id

    db.get.return_value = mock_chart
    mocker.patch.object(
        chart_service, "_get_dashboard_with_access", return_value=mock_dashboard
    )

    chart = await chart_service.get_chart_by_id(db, chart_id, user_id)

    assert chart == mock_chart
    db.get.assert_called_once_with(Chart, chart_id)


@pytest.mark.asyncio
async def test_get_chart_by_id_not_found(chart_service, mocker):
    """Test getting a non-existent chart."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    chart_id = str(uuid4())

    db.get.return_value = None

    with pytest.raises(NotFoundError, match="Chart not found"):
        await chart_service.get_chart_by_id(db, chart_id, user_id)


@pytest.mark.asyncio
async def test_list_charts(chart_service, mocker, mock_chart, mock_dashboard):
    """Test listing charts for a dashboard."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    dashboard_id = uuid4()

    mocker.patch.object(
        chart_service, "_get_dashboard_with_access", return_value=mock_dashboard
    )

    # Mock count query
    count_result = mocker.MagicMock()
    count_result.scalar.return_value = 10

    # Mock data query
    data_result = mocker.MagicMock()
    data_result.scalars.return_value.all.return_value = [mock_chart]

    db.execute.side_effect = [count_result, data_result]

    charts, total = await chart_service.list_charts(db, dashboard_id, user_id)

    assert len(charts) == 1
    assert total == 10
    assert charts[0] == mock_chart


@pytest.mark.asyncio
async def test_update_chart(chart_service, mocker, mock_chart, mock_dashboard):
    """Test updating a chart."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    chart_id = mock_chart.id

    mocker.patch.object(chart_service, "get_chart_by_id", return_value=mock_chart)
    mocker.patch.object(chart_service, "_check_dashboard_edit_permission")

    update_data = ChartUpdate(
        name="Updated Chart Name",
        description="Updated description",
        width=12,
    )

    chart = await chart_service.update_chart(db, chart_id, user_id, update_data)

    assert chart.name == "Updated Chart Name"
    assert chart.description == "Updated description"
    assert chart.width == 12
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_delete_chart(chart_service, mocker, mock_chart):
    """Test deleting a chart."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    chart_id = mock_chart.id

    mocker.patch.object(chart_service, "get_chart_by_id", return_value=mock_chart)
    mocker.patch.object(chart_service, "_check_dashboard_edit_permission")

    await chart_service.delete_chart(db, chart_id, user_id)

    # Verify soft delete was called
    assert mock_chart.is_deleted is True
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_duplicate_chart(chart_service, mocker, mock_chart, mock_dashboard):
    """Test duplicating a chart."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    chart_id = mock_chart.id

    mocker.patch.object(chart_service, "get_chart_by_id", return_value=mock_chart)
    mocker.patch.object(
        chart_service, "_get_dashboard_with_access", return_value=mock_dashboard
    )

    # Mock max position query
    mock_result = mocker.MagicMock()
    mock_result.scalar.return_value = 3
    db.execute.return_value = mock_result

    duplicate_data = ChartDuplicate(
        name="Duplicated Chart",
        include_data_config=True,
        include_visual_config=True,
        include_filters=True,
        include_drilldown=True,
    )

    duplicate = await chart_service.duplicate_chart(db, chart_id, user_id, duplicate_data)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_get_chart_data(chart_service, mocker, mock_chart):
    """Test generating chart data."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    chart_id = mock_chart.id

    mocker.patch.object(chart_service, "get_chart_by_id", return_value=mock_chart)

    # Mock analytics service
    mock_analytics_result = {
        "data": [
            {"label": "January", "value": 100},
            {"label": "February", "value": 150},
            {"label": "March", "value": 200},
        ],
        "total_records": 3,
    }
    mocker.patch.object(
        chart_service.analytics_service,
        "compute_chart_data",
        return_value=mock_analytics_result,
    )

    response = await chart_service.get_chart_data(db, chart_id, user_id)

    assert response.chart_id == uuid4(chart_id)
    assert response.chart_type == ChartType.BAR
    assert len(response.data) == 3
    assert response.data[0].label == "January"
    assert response.data[0].value == 100
    assert response.metadata["total_records"] == 3
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_chart_data_with_overrides(chart_service, mocker, mock_chart):
    """Test generating chart data with request overrides."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    chart_id = mock_chart.id

    mocker.patch.object(chart_service, "get_chart_by_id", return_value=mock_chart)

    # Mock analytics service
    mock_analytics_result = {
        "data": [
            {"label": "Active", "value": 50},
            {"label": "Inactive", "value": 25},
        ],
        "total_records": 2,
    }
    mocker.patch.object(
        chart_service.analytics_service,
        "compute_chart_data",
        return_value=mock_analytics_result,
    )

    data_request = ChartDataRequest(
        filters=[
            FilterCondition(
                field_id=uuid4(), operator=FilterOperator.EQUALS, value="Active"
            )
        ],
        limit=10,
        bypass_cache=True,
    )

    response = await chart_service.get_chart_data(db, chart_id, user_id, data_request)

    assert len(response.data) == 2
    assert response.metadata["total_records"] == 2


@pytest.mark.asyncio
async def test_compute_chart_data_single_series(chart_service, mocker):
    """Test computing single series chart data."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    table_id = str(uuid4())
    x_field_id = str(uuid4())
    y_field_id = str(uuid4())

    data_config = {
        "x_field_id": x_field_id,
        "y_field_id": y_field_id,
        "aggregation": "sum",
        "limit": 100,
    }

    # Mock analytics service
    mock_analytics_result = {
        "data": [
            {"label": "Q1", "value": 1000},
            {"label": "Q2", "value": 1500},
            {"label": "Q3", "value": 2000},
            {"label": "Q4", "value": 2500},
        ],
        "total_records": 4,
    }
    mocker.patch.object(
        chart_service.analytics_service,
        "compute_chart_data",
        return_value=mock_analytics_result,
    )

    result = await chart_service._compute_chart_data(
        db=db,
        user_id=user_id,
        table_id=table_id,
        chart_type="line",
        data_config=data_config,
        filters=[],
        sorts=[],
    )

    assert len(result["data"]) == 4
    assert result["series"] is None
    assert len(result["labels"]) == 4
    assert result["total_records"] == 4


@pytest.mark.asyncio
async def test_compute_chart_data_multi_series(chart_service, mocker):
    """Test computing multi-series chart data."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    table_id = str(uuid4())
    x_field_id = str(uuid4())

    data_config = {
        "x_field_id": x_field_id,
        "series": [
            {"y_field_id": str(uuid4()), "name": "Revenue", "aggregation": "sum"},
            {"y_field_id": str(uuid4()), "name": "Cost", "aggregation": "sum"},
        ],
    }

    # Mock analytics service to return different data for each series
    mock_results = [
        {
            "data": [
                {"label": "Q1", "value": 1000},
                {"label": "Q2", "value": 1500},
            ],
            "total_records": 2,
        },
        {
            "data": [
                {"label": "Q1", "value": 500},
                {"label": "Q2", "value": 750},
            ],
            "total_records": 2,
        },
    ]

    mocker.patch.object(
        chart_service.analytics_service,
        "compute_chart_data",
        side_effect=mock_results,
    )

    result = await chart_service._compute_chart_data(
        db=db,
        user_id=user_id,
        table_id=table_id,
        chart_type="line",
        data_config=data_config,
        filters=[],
        sorts=[],
    )

    assert result["data"] == []
    assert len(result["series"]) == 2
    assert result["series"][0].name == "Revenue"
    assert result["series"][1].name == "Cost"
    assert len(result["labels"]) == 2
    assert "Q1" in result["labels"]
    assert "Q2" in result["labels"]


@pytest.mark.asyncio
async def test_check_dashboard_edit_permission_owner(chart_service, mocker, mock_dashboard, mock_base):
    """Test edit permission for dashboard owner."""
    db = mocker.AsyncMock()
    user_id = "user-1"
    dashboard_id = mock_dashboard.id

    mock_dashboard.created_by_id = user_id
    db.get.side_effect = [mock_dashboard, mock_base]

    # Should not raise
    await chart_service._check_dashboard_edit_permission(db, dashboard_id, user_id)


@pytest.mark.asyncio
async def test_check_dashboard_edit_permission_locked(chart_service, mocker, mock_dashboard, mock_base):
    """Test edit permission for locked dashboard."""
    db = mocker.AsyncMock()
    user_id = "user-2"
    dashboard_id = mock_dashboard.id

    mock_dashboard.created_by_id = "user-1"
    mock_dashboard.is_locked = True
    db.get.side_effect = [mock_dashboard, mock_base]

    with pytest.raises(PermissionDeniedError, match="Dashboard is locked"):
        await chart_service._check_dashboard_edit_permission(db, dashboard_id, user_id)
