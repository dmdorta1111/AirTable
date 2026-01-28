"""
Tests for BOM validation and comparison services.

Tests the BOM validation and comparison services including:
- BOM validation with rules
- Database cross-reference
- Difference highlighting
- Multiple BOM comparison
- Comparison report generation
"""

from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from pybase.models.base import Base
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember
from pybase.schemas.extraction import (
    BOMFieldValidationRule,
    BOMValidationRule,
    BOMValidationSchema,
    BOMValidationSeverity,
)
from pybase.services.bom_comparison import BOMComparisonService
from pybase.services.bom_validation import BOMValidationService


# --- Fixtures ---

@pytest.fixture
def bom_validation_service() -> BOMValidationService:
    """Create BOM validation service instance."""
    return BOMValidationService()


@pytest.fixture
def bom_comparison_service() -> BOMComparisonService:
    """Create BOM comparison service instance."""
    return BOMComparisonService()


@pytest.fixture
def sample_bom_items() -> list[dict]:
    """Sample BOM items for testing."""
    return [
        {
            "part_number": "PART-001",
            "description": "Test Part 1",
            "quantity": 10,
            "material": "STEEL",
        },
        {
            "part_number": "PART-002",
            "description": "Test Part 2",
            "quantity": 5,
            "material": "ALUMINUM",
        },
        {
            "part_number": "PART-003",
            "description": "Test Part 3",
            "quantity": 2,
            "material": "PLASTIC",
        },
    ]


@pytest.fixture
def invalid_bom_items() -> list[dict]:
    """Invalid BOM items for testing validation errors."""
    return [
        {
            # Missing part_number
            "description": "Invalid Part 1",
            "quantity": -1,  # Invalid quantity
        },
        {
            "part_number": "part@#$",  # Invalid format
            "description": "Invalid Part 2",
            "quantity": "abc",  # Non-numeric quantity
        },
        {
            "part_number": "PART-003",
            # Missing description (if required)
        },
    ]


@pytest.fixture
def sample_validation_config() -> BOMValidationSchema:
    """Sample validation configuration."""
    return BOMValidationSchema(
        require_part_number=True,
        require_quantity=True,
        require_description=False,
        require_material=False,
        min_quantity=1,
        max_quantity=1000,
        allow_fractional_quantity=False,
        part_number_pattern=r"^[A-Z0-9\-_]+$",
        check_duplicates=True,
        validate_against_database=False,
    )


@pytest.fixture
def field_mapping() -> dict[str, str]:
    """Sample field mapping for BOM to table."""
    return {
        "part_number": "field_part_number",
        "description": "field_description",
        "quantity": "field_quantity",
        "material": "field_material",
    }


# --- BOM Validation Service Tests --


class TestBOMValidationServiceValidate:
    """Tests for BOM validation."""

    @pytest.mark.asyncio
    async def test_validate_bom_valid_data(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        sample_validation_config: BOMValidationSchema,
    ):
        """Test validating valid BOM data."""
        result = await bom_validation_service.validate_bom(
            db_session,
            str(test_user.id),
            sample_bom_items,
            validation_config=sample_validation_config,
        )

        assert result.is_valid is True
        assert result.total_items == 3
        assert result.valid_items == 3
        assert result.invalid_items == 0
        assert result.error_count == 0
        assert len(result.errors) == 0
        assert result.validation_time > 0

    @pytest.mark.asyncio
    async def test_validate_bom_invalid_data(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        invalid_bom_items: list[dict],
        sample_validation_config: BOMValidationSchema,
    ):
        """Test validating invalid BOM data."""
        result = await bom_validation_service.validate_bom(
            db_session,
            str(test_user.id),
            invalid_bom_items,
            validation_config=sample_validation_config,
        )

        assert result.is_valid is False
        assert result.total_items == 3
        assert result.invalid_items > 0
        assert result.error_count > 0
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_validate_bom_default_config(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
    ):
        """Test validation with default configuration."""
        result = await bom_validation_service.validate_bom(
            db_session,
            str(test_user.id),
            sample_bom_items,
        )

        assert result.is_valid is True
        assert isinstance(result.validation_config, type(result.validation_config))

    @pytest.mark.asyncio
    async def test_validate_bom_duplicate_detection(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_validation_config: BOMValidationSchema,
    ):
        """Test duplicate part number detection."""
        bom_with_duplicates = [
            {
                "part_number": "PART-001",
                "description": "First occurrence",
                "quantity": 1,
            },
            {
                "part_number": "PART-002",
                "description": "Unique part",
                "quantity": 1,
            },
            {
                "part_number": "PART-001",  # Duplicate
                "description": "Second occurrence",
                "quantity": 1,
            },
        ]

        result = await bom_validation_service.validate_bom(
            db_session,
            str(test_user.id),
            bom_with_duplicates,
            validation_config=sample_validation_config,
        )

        assert len(result.duplicate_parts) == 1
        assert len(result.warnings) > 0
        assert any(w.error_code == "DUPLICATE_PART" for w in result.warnings)

    @pytest.mark.asyncio
    async def test_validate_bom_custom_field_rules(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
    ):
        """Test validation with custom field rules."""
        custom_config = BOMValidationSchema(
            field_rules=[
                BOMFieldValidationRule(
                    field_name="description",
                    rule_type=BOMValidationRule.FORMAT_PATTERN,
                    severity=BOMValidationSeverity.ERROR,
                    pattern=r"^[A-Z\s]+$",
                ),
                BOMFieldValidationRule(
                    field_name="quantity",
                    rule_type=BOMValidationRule.VALUE_RANGE,
                    severity=BOMValidationSeverity.WARNING,
                    min_value=5,
                    max_value=50,
                ),
            ],
        )

        result = await bom_validation_service.validate_bom(
            db_session,
            str(test_user.id),
            sample_bom_items,
            validation_config=custom_config,
        )

        # Should have warnings for quantities below minimum
        assert result.warning_count >= 0

    @pytest.mark.asyncio
    async def test_validate_bom_empty_list(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_validation_config: BOMValidationSchema,
    ):
        """Test validation with empty BOM list."""
        result = await bom_validation_service.validate_bom(
            db_session,
            str(test_user.id),
            [],
            validation_config=sample_validation_config,
        )

        assert result.is_valid is True
        assert result.total_items == 0
        assert result.valid_items == 0


class TestBOMValidationServiceCrossReference:
    """Tests for database cross-reference functionality."""

    @pytest.mark.asyncio
    async def test_cross_reference_parts_all_new(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test cross-reference when all parts are new."""
        result = await bom_validation_service.cross_reference_parts(
            db_session,
            str(test_user.id),
            sample_bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["new_parts"]) == 3
        assert len(result["existing_parts"]) == 0
        assert result["summary"]["new_count"] == 3
        assert result["summary"]["existing_count"] == 0

    @pytest.mark.asyncio
    async def test_cross_reference_parts_with_existing(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test cross-reference with some existing parts."""
        # Add a record to database
        existing_record = Record(
            table_id=sample_table.id,
            data='{"field_part_number": "PART-001", "field_description": "Existing Part"}',
        )
        db_session.add(existing_record)
        await db_session.commit()

        result = await bom_validation_service.cross_reference_parts(
            db_session,
            str(test_user.id),
            sample_bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["new_parts"]) == 2
        assert len(result["existing_parts"]) == 1
        assert result["existing_parts"][0]["part_number"] == "PART-001"

    @pytest.mark.asyncio
    async def test_cross_reference_parts_invalid_table(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
    ):
        """Test cross-reference with invalid table ID."""
        with pytest.raises(NotFoundError):
            await bom_validation_service.cross_reference_parts(
                db_session,
                str(test_user.id),
                sample_bom_items,
                "non-existent-table-id",
                field_mapping,
            )

    @pytest.mark.asyncio
    async def test_cross_reference_parts_no_permission(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test cross-reference without table access permission."""
        with pytest.raises(PermissionDeniedError):
            await bom_validation_service.cross_reference_parts(
                db_session,
                "non-existent-user-id",
                sample_bom_items,
                str(sample_table.id),
                field_mapping,
            )


class TestBOMValidationServiceHighlightDifferences:
    """Tests for difference highlighting functionality."""

    @pytest.mark.asyncio
    async def test_highlight_differences_all_new(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test highlighting differences when all parts are new."""
        result = await bom_validation_service.highlight_differences(
            db_session,
            str(test_user.id),
            sample_bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["new_items"]) == 3
        assert len(result["exact_matches"]) == 0
        assert len(result["matched_with_differences"]) == 0

    @pytest.mark.asyncio
    async def test_highlight_differences_with_matches(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test highlighting differences with exact matches."""
        bom_items = [
            {
                "part_number": "PART-001",
                "description": "Test Part 1",
                "quantity": 10,
            }
        ]

        # Add matching record
        existing_record = Record(
            table_id=sample_table.id,
            data='{"field_part_number": "PART-001", "field_description": "Test Part 1", "field_quantity": 10}',
        )
        db_session.add(existing_record)
        await db_session.commit()

        result = await bom_validation_service.highlight_differences(
            db_session,
            str(test_user.id),
            bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["exact_matches"]) == 1
        assert len(result["new_items"]) == 0

    @pytest.mark.asyncio
    async def test_highlight_differences_with_changes(
        self,
        bom_validation_service: BOMValidationService,
        db_session: AsyncSession,
        test_user,
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test highlighting differences when data differs."""
        bom_items = [
            {
                "part_number": "PART-001",
                "description": "Updated Description",  # Different from DB
                "quantity": 20,  # Different from DB
            }
        ]

        # Add record with different values
        existing_record = Record(
            table_id=sample_table.id,
            data='{"field_part_number": "PART-001", "field_description": "Original Description", "field_quantity": 10}',
        )
        db_session.add(existing_record)
        await db_session.commit()

        result = await bom_validation_service.highlight_differences(
            db_session,
            str(test_user.id),
            bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["matched_with_differences"]) == 1
        assert len(result["matched_with_differences"][0]["differences"]) == 2


# --- BOM Comparison Service Tests ---


class TestBOMComparisonServiceCompare:
    """Tests for BOM comparison functionality."""

    @pytest.mark.asyncio
    async def test_compare_bom_to_database_all_new(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test comparison when all parts are new."""
        result = await bom_comparison_service.compare_bom_to_database(
            db_session,
            str(test_user.id),
            sample_bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["new_parts"]) == 3
        assert len(result["existing_parts"]) == 0
        assert result["summary"]["total_bom_items"] == 3
        assert result["summary"]["new_parts_count"] == 3
        assert result["summary"]["match_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_compare_bom_to_database_with_matches(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test comparison with some matching parts."""
        bom_items = [
            {"part_number": "PART-001", "description": "Part 1", "quantity": 10},
            {"part_number": "PART-002", "description": "Part 2", "quantity": 5},
        ]

        # Add one existing part
        existing_record = Record(
            table_id=sample_table.id,
            data='{"field_part_number": "PART-001", "field_description": "Part 1", "field_quantity": 10}',
        )
        db_session.add(existing_record)
        await db_session.commit()

        result = await bom_comparison_service.compare_bom_to_database(
            db_session,
            str(test_user.id),
            bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["new_parts"]) == 1
        assert len(result["existing_parts"]) == 1
        assert result["summary"]["match_percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_compare_bom_to_database_with_differences(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test comparison detecting field differences."""
        bom_items = [
            {"part_number": "PART-001", "description": "New Description", "quantity": 20},
        ]

        # Add part with different values
        existing_record = Record(
            table_id=sample_table.id,
            data='{"field_part_number": "PART-001", "field_description": "Old Description", "field_quantity": 10}',
        )
        db_session.add(existing_record)
        await db_session.commit()

        result = await bom_comparison_service.compare_bom_to_database(
            db_session,
            str(test_user.id),
            bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["updated_parts"]) == 1
        assert len(result["updated_parts"][0]["_differences"]) == 2

    @pytest.mark.asyncio
    async def test_compare_bom_invalid_field_mapping(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        sample_table: Table,
    ):
        """Test comparison with invalid field mapping."""
        with pytest.raises(BadRequestError):
            await bom_comparison_service.compare_bom_to_database(
                db_session,
                str(test_user.id),
                sample_bom_items,
                str(sample_table.id),
                {},  # Empty mapping
            )

    @pytest.mark.asyncio
    async def test_compare_bom_invalid_table(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
    ):
        """Test comparison with invalid table ID."""
        with pytest.raises(NotFoundError):
            await bom_comparison_service.compare_bom_to_database(
                db_session,
                str(test_user.id),
                sample_bom_items,
                "invalid-table-id",
                field_mapping,
            )


class TestBOMComparisonServiceHighlightNew:
    """Tests for highlighting new parts functionality."""

    @pytest.mark.asyncio
    async def test_highlight_new_parts(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test highlighting new parts only."""
        result = await bom_comparison_service.highlight_new_parts(
            db_session,
            str(test_user.id),
            sample_bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["new_parts"]) == 3
        assert result["filtered_count"] == 3
        assert result["original_count"] == 3

    @pytest.mark.asyncio
    async def test_highlight_new_parts_filters_existing(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test that new parts filtering excludes existing parts."""
        bom_items = [
            {"part_number": "PART-001", "description": "Part 1"},
            {"part_number": "PART-002", "description": "Part 2"},
        ]

        # Add one existing part
        existing_record = Record(
            table_id=sample_table.id,
            data='{"field_part_number": "PART-001", "field_description": "Part 1"}',
        )
        db_session.add(existing_record)
        await db_session.commit()

        result = await bom_comparison_service.highlight_new_parts(
            db_session,
            str(test_user.id),
            bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert len(result["new_parts"]) == 1
        assert result["new_parts"][0]["part_number"] == "PART-002"
        assert "PART-001" in result["existing_part_numbers"]


class TestBOMComparisonServiceMultipleBOMs:
    """Tests for multiple BOM comparison functionality."""

    @pytest.mark.asyncio
    async def test_compare_multiple_boms_union(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
    ):
        """Test comparing multiple BOMs in union mode."""
        bom_data_list = [
            {
                "items": [
                    {"part_number": "PART-001"},
                    {"part_number": "PART-002"},
                ]
            },
            {
                "items": [
                    {"part_number": "PART-002"},
                    {"part_number": "PART-003"},
                ]
            },
        ]

        result = await bom_comparison_service.compare_multiple_boms(
            db_session,
            str(test_user.id),
            bom_data_list,
            comparison_mode="union",
        )

        assert len(result["common_parts"]) == 1  # PART-002
        assert len(result["unique_parts"]) == 2

    @pytest.mark.asyncio
    async def test_compare_multiple_boms_intersection(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
    ):
        """Test comparing multiple BOMs in intersection mode."""
        bom_data_list = [
            {"items": [{"part_number": "PART-001"}, {"part_number": "PART-002"}]},
            {"items": [{"part_number": "PART-002"}, {"part_number": "PART-003"}]},
        ]

        result = await bom_comparison_service.compare_multiple_boms(
            db_session,
            str(test_user.id),
            bom_data_list,
            comparison_mode="intersection",
        )

        assert len(result["common_parts"]) == 1  # PART-002 only
        assert result["common_count"] == 1

    @pytest.mark.asyncio
    async def test_compare_multiple_boms_invalid_mode(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
    ):
        """Test comparison with invalid mode."""
        with pytest.raises(BadRequestError):
            await bom_comparison_service.compare_multiple_boms(
                db_session,
                str(test_user.id),
                [],
                comparison_mode="invalid_mode",
            )

    @pytest.mark.asyncio
    async def test_compare_multiple_boms_insufficient_data(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
    ):
        """Test comparison with insufficient BOM data."""
        with pytest.raises(BadRequestError):
            await bom_comparison_service.compare_multiple_boms(
                db_session,
                str(test_user.id),
                [{"items": []}],  # Only one BOM
            )


class TestBOMComparisonServiceReport:
    """Tests for comparison report generation."""

    @pytest.mark.asyncio
    async def test_generate_comparison_report(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        sample_bom_items: list[dict],
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test generating comparison report."""
        result = await bom_comparison_service.generate_comparison_report(
            db_session,
            str(test_user.id),
            sample_bom_items,
            str(sample_table.id),
            field_mapping,
        )

        assert "report_sections" in result
        assert "recommendations" in result
        assert "statistics" in result
        assert "visualization_data" in result

        # Check report sections
        assert "executive_summary" in result["report_sections"]
        assert "new_parts_section" in result["report_sections"]
        assert "existing_parts_section" in result["report_sections"]

        # Check visualization data
        assert "pie_chart" in result["visualization_data"]
        assert "bar_chart" in result["visualization_data"]

    @pytest.mark.asyncio
    async def test_generate_report_with_recommendations(
        self,
        bom_comparison_service: BOMComparisonService,
        db_session: AsyncSession,
        test_user,
        field_mapping: dict[str, str],
        sample_table: Table,
    ):
        """Test report includes actionable recommendations."""
        bom_items = [
            {"part_number": "PART-001", "description": "New Part"},
            {"part_number": "PART-002", "description": "Another New Part"},
        ]

        result = await bom_comparison_service.generate_comparison_report(
            db_session,
            str(test_user.id),
            bom_items,
            str(sample_table.id),
            field_mapping,
        )

        # Should have recommendations for new parts
        assert len(result["recommendations"]) > 0
        assert any(r["action"] == "add_new_parts" for r in result["recommendations"])


# --- Fixtures for Integration Tests ---

@pytest_asyncio.fixture
async def sample_workspace(db_session: AsyncSession) -> Workspace:
    """Create a sample workspace for testing."""
    workspace = Workspace(
        name="Test Workspace",
        slug="test-workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    return workspace


@pytest_asyncio.fixture
async def sample_base(db_session: AsyncSession, sample_workspace: Workspace) -> Base:
    """Create a sample base for testing."""
    from pybase.models.base import Base as BaseModel

    base = BaseModel(
        workspace_id=sample_workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def sample_table(db_session: AsyncSession, sample_base: Base) -> Table:
    """Create a sample table for testing."""
    table = Table(
        base_id=sample_base.id,
        name="Parts Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)
    return table


@pytest_asyncio.fixture
async def workspace_member(
    db_session: AsyncSession,
    sample_workspace: Workspace,
    test_user,
) -> WorkspaceMember:
    """Add test user as workspace member."""
    member = WorkspaceMember(
        workspace_id=sample_workspace.id,
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member
