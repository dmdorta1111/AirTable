"""
Unit tests for AnalyticsService business logic.
"""

import json
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.services.analytics import AnalyticsService


@pytest.fixture
def analytics_service():
    """Create an instance of AnalyticsService."""
    return AnalyticsService()


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add owner as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    return workspace


@pytest_asyncio.fixture
async def test_base(db_session: AsyncSession, test_workspace: Workspace) -> Base:
    """Create a test base."""
    base = Base(
        workspace_id=test_workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def test_table(db_session: AsyncSession, test_base: Base) -> Table:
    """Create a test table."""
    table = Table(
        base_id=test_base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)
    return table


@pytest_asyncio.fixture
async def test_fields(db_session: AsyncSession, test_table: Table) -> dict[str, Field]:
    """Create test fields for pivot table testing."""
    # Status field (for rows)
    status_field = Field(
        table_id=test_table.id,
        name="status",
        field_type=FieldType.TEXT.value,
        is_required=False,
    )
    db_session.add(status_field)

    # Priority field (for columns)
    priority_field = Field(
        table_id=test_table.id,
        name="priority",
        field_type=FieldType.TEXT.value,
        is_required=False,
    )
    db_session.add(priority_field)

    # Cost field (for values)
    cost_field = Field(
        table_id=test_table.id,
        name="cost",
        field_type=FieldType.NUMBER.value,
        is_required=False,
    )
    db_session.add(cost_field)

    await db_session.commit()
    await db_session.refresh(status_field)
    await db_session.refresh(priority_field)
    await db_session.refresh(cost_field)

    return {
        "status": status_field,
        "priority": priority_field,
        "cost": cost_field,
    }


@pytest_asyncio.fixture
async def test_records(
    db_session: AsyncSession,
    test_table: Table,
    test_fields: dict[str, Field],
) -> list[Record]:
    """Create test records with pivot table data."""
    records_data = [
        {"status": "Open", "priority": "High", "cost": 1000},
        {"status": "Open", "priority": "High", "cost": 1500},
        {"status": "Open", "priority": "Low", "cost": 500},
        {"status": "In Progress", "priority": "High", "cost": 2000},
        {"status": "In Progress", "priority": "Medium", "cost": 800},
        {"status": "In Progress", "priority": "Low", "cost": 300},
        {"status": "Done", "priority": "High", "cost": 1200},
        {"status": "Done", "priority": "Medium", "cost": 600},
        {"status": "Done", "priority": "Low", "cost": 200},
    ]

    records = []
    for data in records_data:
        record = Record(
            table_id=test_table.id,
            data=json.dumps(data),
        )
        db_session.add(record)
        records.append(record)

    await db_session.commit()
    for record in records:
        await db_session.refresh(record)

    return records


@pytest.mark.asyncio
async def test_pivot_table_aggregation(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    test_fields: dict[str, Field],
    test_records: list[Record],
    analytics_service: AnalyticsService,
):
    """Test pivot table data aggregation with various aggregation types."""
    # Test COUNT aggregation (no value field needed)
    result = await analytics_service.pivot_table(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        row_field_id=str(test_fields["status"].id),
        column_field_id=str(test_fields["priority"].id),
        value_field_id=None,
        aggregation_type="count",
    )

    # Verify response structure
    assert result["table_id"] == str(test_table.id)
    assert result["row_field"]["id"] == str(test_fields["status"].id)
    assert result["row_field"]["name"] == "status"
    assert result["column_field"]["id"] == str(test_fields["priority"].id)
    assert result["column_field"]["name"] == "priority"
    assert result["aggregation_type"] == "count"
    assert result["record_count"] == 9
    assert "data" in result
    assert "timestamp" in result

    # Verify pivot data structure
    pivot_data = result["data"]
    assert "rows" in pivot_data
    assert "columns" in pivot_data
    assert "values" in pivot_data
    assert len(pivot_data["rows"]) == 3  # Open, In Progress, Done
    assert len(pivot_data["columns"]) == 3  # High, Low, Medium

    # Verify count values
    # Should have 3 rows (statuses) and 3 columns (priorities)
    assert len(pivot_data["values"]) == 3
    for row_values in pivot_data["values"]:
        assert len(row_values) == 3

    # Test SUM aggregation
    result_sum = await analytics_service.pivot_table(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        row_field_id=str(test_fields["status"].id),
        column_field_id=str(test_fields["priority"].id),
        value_field_id=str(test_fields["cost"].id),
        aggregation_type="sum",
    )

    assert result_sum["aggregation_type"] == "sum"
    assert result_sum["value_field"]["id"] == str(test_fields["cost"].id)
    assert result_sum["value_field"]["name"] == "cost"

    pivot_data_sum = result_sum["data"]
    assert "rows" in pivot_data_sum
    assert "columns" in pivot_data_sum
    assert "values" in pivot_data_sum

    # Verify sum values are numeric and greater than count values
    for row_idx, row_values in enumerate(pivot_data_sum["values"]):
        for col_idx, value in enumerate(row_values):
            if value > 0:
                # Sum values should be >= count values since costs are positive
                assert value >= pivot_data["values"][row_idx][col_idx]

    # Test AVG aggregation
    result_avg = await analytics_service.pivot_table(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        row_field_id=str(test_fields["status"].id),
        column_field_id=str(test_fields["priority"].id),
        value_field_id=str(test_fields["cost"].id),
        aggregation_type="avg",
    )

    assert result_avg["aggregation_type"] == "avg"
    pivot_data_avg = result_avg["data"]
    assert len(pivot_data_avg["values"]) == 3

    # Test MIN aggregation
    result_min = await analytics_service.pivot_table(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        row_field_id=str(test_fields["status"].id),
        column_field_id=str(test_fields["priority"].id),
        value_field_id=str(test_fields["cost"].id),
        aggregation_type="min",
    )

    assert result_min["aggregation_type"] == "min"
    assert "data" in result_min

    # Test MAX aggregation
    result_max = await analytics_service.pivot_table(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        row_field_id=str(test_fields["status"].id),
        column_field_id=str(test_fields["priority"].id),
        value_field_id=str(test_fields["cost"].id),
        aggregation_type="max",
    )

    assert result_max["aggregation_type"] == "max"
    assert "data" in result_max


@pytest.mark.asyncio
async def test_pivot_table_one_dimension(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    test_fields: dict[str, Field],
    test_records: list[Record],
    analytics_service: AnalyticsService,
):
    """Test pivot table with only row field (one-dimensional)."""
    result = await analytics_service.pivot_table(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        row_field_id=str(test_fields["status"].id),
        column_field_id=None,  # No column field
        value_field_id=str(test_fields["cost"].id),
        aggregation_type="sum",
    )

    assert result["column_field"] is None
    pivot_data = result["data"]
    assert "rows" in pivot_data
    assert "columns" in pivot_data
    assert "values" in pivot_data
    assert len(pivot_data["rows"]) == 3  # Three statuses
    assert pivot_data["columns"] == ["value"]  # Single column for values


@pytest.mark.asyncio
async def test_pivot_table_permission_denied(
    db_session: AsyncSession,
    test_table: Table,
    test_fields: dict[str, Field],
    test_records: list[Record],
    analytics_service: AnalyticsService,
):
    """Test pivot table with unauthorized user."""
    unauthorized_user_id = str(uuid4())

    with pytest.raises(PermissionDeniedError):
        await analytics_service.pivot_table(
            db=db_session,
            user_id=unauthorized_user_id,
            table_id=str(test_table.id),
            row_field_id=str(test_fields["status"].id),
            column_field_id=str(test_fields["priority"].id),
            value_field_id=str(test_fields["cost"].id),
            aggregation_type="sum",
        )


@pytest.mark.asyncio
async def test_pivot_table_table_not_found(
    db_session: AsyncSession,
    test_user: User,
    test_fields: dict[str, Field],
    analytics_service: AnalyticsService,
):
    """Test pivot table with non-existent table."""
    fake_table_id = str(uuid4())

    with pytest.raises(NotFoundError, match="Table not found"):
        await analytics_service.pivot_table(
            db=db_session,
            user_id=str(test_user.id),
            table_id=fake_table_id,
            row_field_id=str(test_fields["status"].id),
            column_field_id=str(test_fields["priority"].id),
            value_field_id=str(test_fields["cost"].id),
            aggregation_type="sum",
        )


@pytest.mark.asyncio
async def test_pivot_table_field_not_found(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    test_fields: dict[str, Field],
    test_records: list[Record],
    analytics_service: AnalyticsService,
):
    """Test pivot table with non-existent field."""
    fake_field_id = str(uuid4())

    with pytest.raises(NotFoundError, match="Field not found"):
        await analytics_service.pivot_table(
            db=db_session,
            user_id=str(test_user.id),
            table_id=str(test_table.id),
            row_field_id=fake_field_id,
            column_field_id=str(test_fields["priority"].id),
            value_field_id=str(test_fields["cost"].id),
            aggregation_type="sum",
        )


@pytest.mark.asyncio
async def test_pivot_table_value_field_required(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    test_fields: dict[str, Field],
    test_records: list[Record],
    analytics_service: AnalyticsService,
):
    """Test that value_field_id is required for non-count aggregations."""
    with pytest.raises(ValidationError, match="value_field_id is required"):
        await analytics_service.pivot_table(
            db=db_session,
            user_id=str(test_user.id),
            table_id=str(test_table.id),
            row_field_id=str(test_fields["status"].id),
            column_field_id=str(test_fields["priority"].id),
            value_field_id=None,  # Missing value field for sum
            aggregation_type="sum",
        )


@pytest.mark.asyncio
async def test_chart_data_computation(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    test_fields: dict[str, Field],
    test_records: list[Record],
    analytics_service: AnalyticsService,
):
    """Test chart data computation with grouping, summing, and counting."""
    # Test COUNT aggregation (single series, no grouping)
    result = await analytics_service.compute_chart_data(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        x_field_id=str(test_fields["status"].id),
        y_field_id=None,
        group_field_id=None,
        aggregation_type="count",
    )

    # Verify response structure
    assert result["table_id"] == str(test_table.id)
    assert result["x_field"]["id"] == str(test_fields["status"].id)
    assert result["x_field"]["name"] == "status"
    assert result["y_field"] is None
    assert result["group_field"] is None
    assert result["aggregation_type"] == "count"
    assert result["record_count"] == 9
    assert "data" in result
    assert "timestamp" in result

    # Verify chart data structure
    chart_data = result["data"]
    assert "labels" in chart_data
    assert "series" in chart_data
    assert len(chart_data["labels"]) == 3  # Three statuses: Open, In Progress, Done
    assert len(chart_data["series"]) == 1  # Single series (no grouping)
    assert chart_data["series"][0]["name"] == "Value"
    assert len(chart_data["series"][0]["data"]) == 3

    # Verify count values sum to total records
    total_count = sum(chart_data["series"][0]["data"])
    assert total_count == 9

    # Test SUM aggregation (single series)
    result_sum = await analytics_service.compute_chart_data(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        x_field_id=str(test_fields["status"].id),
        y_field_id=str(test_fields["cost"].id),
        group_field_id=None,
        aggregation_type="sum",
    )

    assert result_sum["aggregation_type"] == "sum"
    assert result_sum["y_field"]["id"] == str(test_fields["cost"].id)
    assert result_sum["y_field"]["name"] == "cost"

    chart_data_sum = result_sum["data"]
    assert len(chart_data_sum["labels"]) == 3
    assert len(chart_data_sum["series"]) == 1

    # Verify sum values are greater than count values
    for i, sum_value in enumerate(chart_data_sum["series"][0]["data"]):
        count_value = chart_data["series"][0]["data"][i]
        assert sum_value >= count_value

    # Test AVG aggregation (single series)
    result_avg = await analytics_service.compute_chart_data(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        x_field_id=str(test_fields["status"].id),
        y_field_id=str(test_fields["cost"].id),
        group_field_id=None,
        aggregation_type="avg",
    )

    assert result_avg["aggregation_type"] == "avg"
    chart_data_avg = result_avg["data"]
    assert len(chart_data_avg["labels"]) == 3
    assert len(chart_data_avg["series"]) == 1

    # Test with GROUPING (multiple series)
    result_grouped = await analytics_service.compute_chart_data(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        x_field_id=str(test_fields["status"].id),
        y_field_id=str(test_fields["cost"].id),
        group_field_id=str(test_fields["priority"].id),
        aggregation_type="sum",
    )

    assert result_grouped["group_field"]["id"] == str(test_fields["priority"].id)
    assert result_grouped["group_field"]["name"] == "priority"

    chart_data_grouped = result_grouped["data"]
    assert "labels" in chart_data_grouped
    assert "series" in chart_data_grouped
    assert len(chart_data_grouped["labels"]) == 3  # Three statuses
    assert len(chart_data_grouped["series"]) == 3  # Three priorities (High, Low, Medium)

    # Verify each series has data for all labels
    for series in chart_data_grouped["series"]:
        assert "name" in series
        assert "data" in series
        assert len(series["data"]) == len(chart_data_grouped["labels"])
        # Verify all values are numeric
        for value in series["data"]:
            assert isinstance(value, (int, float))

    # Test MIN aggregation
    result_min = await analytics_service.compute_chart_data(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        x_field_id=str(test_fields["status"].id),
        y_field_id=str(test_fields["cost"].id),
        group_field_id=None,
        aggregation_type="min",
    )

    assert result_min["aggregation_type"] == "min"
    assert "data" in result_min

    # Test MAX aggregation
    result_max = await analytics_service.compute_chart_data(
        db=db_session,
        user_id=str(test_user.id),
        table_id=str(test_table.id),
        x_field_id=str(test_fields["status"].id),
        y_field_id=str(test_fields["cost"].id),
        group_field_id=None,
        aggregation_type="max",
    )

    assert result_max["aggregation_type"] == "max"
    assert "data" in result_max

    # Verify min <= avg <= max for each status
    for i in range(len(chart_data_avg["labels"])):
        min_val = result_min["data"]["series"][0]["data"][i]
        avg_val = chart_data_avg["series"][0]["data"][i]
        max_val = result_max["data"]["series"][0]["data"][i]
        if min_val > 0 and avg_val > 0 and max_val > 0:
            assert min_val <= avg_val <= max_val


@pytest.mark.asyncio
async def test_chart_data_computation_permission_denied(
    db_session: AsyncSession,
    test_table: Table,
    test_fields: dict[str, Field],
    test_records: list[Record],
    analytics_service: AnalyticsService,
):
    """Test chart data computation with unauthorized user."""
    unauthorized_user_id = str(uuid4())

    with pytest.raises(PermissionDeniedError):
        await analytics_service.compute_chart_data(
            db=db_session,
            user_id=unauthorized_user_id,
            table_id=str(test_table.id),
            x_field_id=str(test_fields["status"].id),
            y_field_id=str(test_fields["cost"].id),
            aggregation_type="sum",
        )


@pytest.mark.asyncio
async def test_chart_data_computation_y_field_required(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    test_fields: dict[str, Field],
    test_records: list[Record],
    analytics_service: AnalyticsService,
):
    """Test that y_field_id is required for non-count aggregations."""
    with pytest.raises(ValidationError, match="y_field_id is required"):
        await analytics_service.compute_chart_data(
            db=db_session,
            user_id=str(test_user.id),
            table_id=str(test_table.id),
            x_field_id=str(test_fields["status"].id),
            y_field_id=None,  # Missing y field for sum
            group_field_id=None,
            aggregation_type="sum",
        )
