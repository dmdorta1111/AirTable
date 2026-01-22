"""
Unit tests for ImportService business logic.
"""

import json
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.table import Table
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.extraction import ImportRequest, ImportResponse
from pybase.services.import_service import ImportService


@pytest.fixture
def import_service():
    """Create an instance of ImportService."""
    return ImportService()


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
async def test_field(db_session: AsyncSession, test_table: Table) -> Field:
    """Create a test field."""
    field = Field(
        table_id=test_table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)
    return field


@pytest.mark.asyncio
async def test_import_records_table_not_found(
    db_session: AsyncSession,
    test_user: User,
    import_service: ImportService,
) -> None:
    """Test import with non-existent table."""
    import_request = ImportRequest(
        job_id=uuid4(),
        table_id=uuid4(),
        field_mapping={},
    )

    with pytest.raises(NotFoundError) as exc_info:
        await import_service.import_records(
            db_session,
            str(test_user.id),
            import_request,
            {},
        )
    assert "Table" in str(exc_info.value)


@pytest.mark.asyncio
async def test_import_records_no_workspace_access(
    db_session: AsyncSession,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test import when user doesn't have workspace access."""
    # Create a different user who is not a workspace member
    other_user = User(
        email="other@example.com",
        hashed_password="hashed_password",
        name="Other User",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    import_request = ImportRequest(
        job_id=uuid4(),
        table_id=test_table.id,
        field_mapping={},
    )

    with pytest.raises(PermissionDeniedError) as exc_info:
        await import_service.import_records(
            db_session,
            str(other_user.id),
            import_request,
            {},
        )
    assert "don't have access" in str(exc_info.value)


@pytest.mark.asyncio
async def test_import_records_viewer_permission_denied(
    db_session: AsyncSession,
    test_user: User,
    test_workspace: Workspace,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test import when user is only a viewer."""
    # Create a viewer user
    viewer_user = User(
        email="viewer@example.com",
        hashed_password="hashed_password",
        name="Viewer User",
        is_active=True,
    )
    db_session.add(viewer_user)
    await db_session.commit()
    await db_session.refresh(viewer_user)

    # Add viewer as workspace member with VIEWER role
    member = WorkspaceMember(
        workspace_id=test_workspace.id,
        user_id=viewer_user.id,
        role=WorkspaceRole.VIEWER,
    )
    db_session.add(member)
    await db_session.commit()

    import_request = ImportRequest(
        job_id=uuid4(),
        table_id=test_table.id,
        field_mapping={},
    )

    with pytest.raises(PermissionDeniedError) as exc_info:
        await import_service.import_records(
            db_session,
            str(viewer_user.id),
            import_request,
            {},
        )
    assert "editors can import" in str(exc_info.value)


@pytest.mark.asyncio
async def test_import_records_invalid_field_mapping(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test import with invalid field mapping."""
    import_request = ImportRequest(
        job_id=uuid4(),
        table_id=test_table.id,
        field_mapping={"source_field": str(uuid4())},  # Non-existent field ID
    )

    extraction_result = {
        "tables": [
            {
                "headers": ["source_field"],
                "rows": [["value1"]],
            }
        ]
    }

    with pytest.raises(ValidationError) as exc_info:
        await import_service.import_records(
            db_session,
            str(test_user.id),
            import_request,
            extraction_result,
        )
    assert "Invalid field mapping" in str(exc_info.value)


@pytest.mark.asyncio
async def test_import_records_success(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    test_field: Field,
    import_service: ImportService,
) -> None:
    """Test successful import of records."""
    import_request = ImportRequest(
        job_id=uuid4(),
        table_id=test_table.id,
        field_mapping={"source_field": str(test_field.id)},
    )

    extraction_result = {
        "tables": [
            {
                "headers": ["source_field"],
                "rows": [["value1"], ["value2"]],
            }
        ]
    }

    result = await import_service.import_records(
        db_session,
        str(test_user.id),
        import_request,
        extraction_result,
    )

    assert isinstance(result, ImportResponse)
    assert result.success is True
    assert result.records_imported == 2
    assert result.records_failed == 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_import_records_with_errors_skip(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test import with errors and skip_errors=True."""
    # Create a required field
    required_field = Field(
        table_id=test_table.id,
        name="Required Field",
        field_type=FieldType.TEXT.value,
        is_required=True,
    )
    db_session.add(required_field)
    await db_session.commit()
    await db_session.refresh(required_field)

    import_request = ImportRequest(
        job_id=uuid4(),
        table_id=test_table.id,
        field_mapping={"source_field": str(required_field.id)},
        skip_errors=True,
    )

    extraction_result = {
        "tables": [
            {
                "headers": ["source_field"],
                "rows": [["value1"], [None], ["value3"]],  # Middle row has None for required field
            }
        ]
    }

    result = await import_service.import_records(
        db_session,
        str(test_user.id),
        import_request,
        extraction_result,
    )

    assert result.success is False
    assert result.records_imported == 2
    assert result.records_failed == 1
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_import_records_with_errors_no_skip(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test import with errors and skip_errors=False."""
    # Create a required field
    required_field = Field(
        table_id=test_table.id,
        name="Required Field",
        field_type=FieldType.TEXT.value,
        is_required=True,
    )
    db_session.add(required_field)
    await db_session.commit()
    await db_session.refresh(required_field)

    import_request = ImportRequest(
        job_id=uuid4(),
        table_id=test_table.id,
        field_mapping={"source_field": str(required_field.id)},
        skip_errors=False,
    )

    extraction_result = {
        "tables": [
            {
                "headers": ["source_field"],
                "rows": [["value1"], [None]],  # Second row has None for required field
            }
        ]
    }

    with pytest.raises(ValidationError) as exc_info:
        await import_service.import_records(
            db_session,
            str(test_user.id),
            import_request,
            extraction_result,
        )
    assert "Import failed at row 2" in str(exc_info.value)


@pytest.mark.asyncio
async def test_import_records_create_missing_fields(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test import with create_missing_fields=True."""
    new_field_id = str(uuid4())
    import_request = ImportRequest(
        job_id=uuid4(),
        table_id=test_table.id,
        field_mapping={"new_field": new_field_id},
        create_missing_fields=True,
    )

    extraction_result = {
        "tables": [
            {
                "headers": ["new_field"],
                "rows": [["value1"]],
            }
        ]
    }

    result = await import_service.import_records(
        db_session,
        str(test_user.id),
        import_request,
        extraction_result,
    )

    assert result.success is True
    assert result.records_imported == 1
    assert len(result.created_field_ids) == 1


@pytest.mark.asyncio
async def test_validate_field_mapping_success(
    db_session: AsyncSession,
    test_table: Table,
    test_field: Field,
    import_service: ImportService,
) -> None:
    """Test successful field mapping validation."""
    field_mapping = {"source_field": str(test_field.id)}

    # Should not raise any exception
    await import_service._validate_field_mapping(
        db_session,
        str(test_table.id),
        field_mapping,
    )


@pytest.mark.asyncio
async def test_validate_field_mapping_invalid_field(
    db_session: AsyncSession,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test field mapping validation with invalid field."""
    field_mapping = {"source_field": str(uuid4())}

    with pytest.raises(ValidationError) as exc_info:
        await import_service._validate_field_mapping(
            db_session,
            str(test_table.id),
            field_mapping,
        )
    assert "Invalid field mapping" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_missing_fields(
    db_session: AsyncSession,
    test_user: User,
    test_table: Table,
    test_field: Field,
    import_service: ImportService,
) -> None:
    """Test creating missing fields during import."""
    new_field_id = str(uuid4())
    field_mapping = {
        "existing_field": str(test_field.id),
        "new_field": new_field_id,
    }

    extraction_result = {
        "tables": [
            {
                "headers": ["existing_field", "new_field"],
                "rows": [["value1", "value2"]],
            }
        ]
    }

    created_field_ids = await import_service._create_missing_fields(
        db_session,
        str(test_user.id),
        str(test_table.id),
        field_mapping,
        extraction_result,
    )

    assert len(created_field_ids) == 1
    # The field mapping should be updated with actual created field ID
    assert field_mapping["new_field"] != new_field_id


def test_infer_field_type_text(import_service: ImportService) -> None:
    """Test field type inference for text."""
    extraction_result = {
        "tables": [
            {
                "headers": ["field1"],
                "rows": [["text value"]],
            }
        ]
    }

    field_type = import_service._infer_field_type("field1", extraction_result)
    assert field_type == FieldType.TEXT


def test_infer_field_type_long_text(import_service: ImportService) -> None:
    """Test field type inference for long text."""
    long_text = "a" * 600
    extraction_result = {
        "tables": [
            {
                "headers": ["field1"],
                "rows": [[long_text]],
            }
        ]
    }

    field_type = import_service._infer_field_type("field1", extraction_result)
    assert field_type == FieldType.LONG_TEXT


def test_infer_field_type_number(import_service: ImportService) -> None:
    """Test field type inference for number."""
    extraction_result = {
        "tables": [
            {
                "headers": ["field1"],
                "rows": [[42]],
            }
        ]
    }

    field_type = import_service._infer_field_type("field1", extraction_result)
    assert field_type == FieldType.NUMBER


def test_infer_field_type_checkbox(import_service: ImportService) -> None:
    """Test field type inference for checkbox (boolean)."""
    extraction_result = {
        "tables": [
            {
                "headers": ["field1"],
                "rows": [[True]],
            }
        ]
    }

    field_type = import_service._infer_field_type("field1", extraction_result)
    assert field_type == FieldType.CHECKBOX


def test_infer_field_type_null_default(import_service: ImportService) -> None:
    """Test field type inference defaults to TEXT for null values."""
    extraction_result = {
        "tables": [
            {
                "headers": ["field1"],
                "rows": [[None]],
            }
        ]
    }

    field_type = import_service._infer_field_type("field1", extraction_result)
    assert field_type == FieldType.TEXT


def test_parse_extraction_result_pdf_tables(import_service: ImportService) -> None:
    """Test parsing PDF table extraction results."""
    extraction_result = {
        "tables": [
            {
                "headers": ["col1", "col2"],
                "rows": [["val1", "val2"], ["val3", "val4"]],
                "page": 1,
                "confidence": 0.95,
            }
        ]
    }

    records = import_service._parse_extraction_result(extraction_result)
    assert len(records) == 2
    assert records[0]["col1"] == "val1"
    assert records[0]["col2"] == "val2"
    assert records[0]["_page"] == 1
    assert records[0]["_confidence"] == 0.95


def test_parse_extraction_result_dimensions(import_service: ImportService) -> None:
    """Test parsing dimension extraction results."""
    extraction_result = {
        "dimensions": [
            {
                "value": 10.5,
                "unit": "mm",
                "tolerance_plus": 0.1,
                "tolerance_minus": 0.1,
                "dimension_type": "linear",
                "label": "Length",
            }
        ]
    }

    records = import_service._parse_extraction_result(extraction_result)
    assert len(records) == 1
    assert records[0]["dimension_value"] == 10.5
    assert records[0]["unit"] == "mm"
    assert records[0]["tolerance_plus"] == 0.1
    assert records[0]["label"] == "Length"
    assert records[0]["_source_type"] == "dimension"


def test_parse_extraction_result_title_block(import_service: ImportService) -> None:
    """Test parsing title block extraction results."""
    extraction_result = {
        "title_block": {
            "drawing_number": "DWG-001",
            "title": "Test Drawing",
            "revision": "A",
            "date": "2024-01-01",
            "author": "John Doe",
            "custom_fields": {"Project": "Test Project"},
        }
    }

    records = import_service._parse_extraction_result(extraction_result)
    assert len(records) == 1
    assert records[0]["drawing_number"] == "DWG-001"
    assert records[0]["title"] == "Test Drawing"
    assert records[0]["Project"] == "Test Project"
    assert records[0]["_source_type"] == "title_block"


def test_parse_extraction_result_layers(import_service: ImportService) -> None:
    """Test parsing CAD layer extraction results."""
    extraction_result = {
        "layers": [
            {
                "name": "Layer1",
                "color": "red",
                "linetype": "continuous",
                "lineweight": 0.5,
                "is_on": True,
                "is_frozen": False,
                "is_locked": False,
                "entity_count": 100,
            }
        ]
    }

    records = import_service._parse_extraction_result(extraction_result)
    assert len(records) == 1
    assert records[0]["layer_name"] == "Layer1"
    assert records[0]["layer_color"] == "red"
    assert records[0]["entity_count"] == 100
    assert records[0]["_source_type"] == "layer"


def test_parse_extraction_result_blocks(import_service: ImportService) -> None:
    """Test parsing CAD block extraction results."""
    extraction_result = {
        "blocks": [
            {
                "name": "Block1",
                "insert_count": 5,
                "entity_count": 10,
                "base_point": (0.0, 0.0, 0.0),
                "attributes": [{"attr1": "value1"}],
            }
        ]
    }

    records = import_service._parse_extraction_result(extraction_result)
    assert len(records) == 1
    assert records[0]["block_name"] == "Block1"
    assert records[0]["insert_count"] == 5
    assert records[0]["attr_attr1"] == "value1"
    assert records[0]["_source_type"] == "block"


def test_parse_extraction_result_bom(import_service: ImportService) -> None:
    """Test parsing Bill of Materials extraction results."""
    extraction_result = {
        "bom": {
            "items": [
                {"part_number": "P001", "quantity": 10},
                {"part_number": "P002", "quantity": 5},
            ],
            "headers": ["part_number", "quantity"],
            "confidence": 0.9,
        }
    }

    records = import_service._parse_extraction_result(extraction_result)
    assert len(records) == 2
    assert records[0]["part_number"] == "P001"
    assert records[0]["quantity"] == 10
    assert records[0]["_confidence"] == 0.9
    assert records[0]["_source_type"] == "bom"


def test_parse_extraction_result_empty(import_service: ImportService) -> None:
    """Test parsing empty extraction results."""
    extraction_result = {}

    records = import_service._parse_extraction_result(extraction_result)
    assert len(records) == 0


def test_parse_extraction_result_multiple_sources(import_service: ImportService) -> None:
    """Test parsing extraction results with multiple data sources."""
    extraction_result = {
        "tables": [
            {
                "headers": ["col1"],
                "rows": [["val1"]],
            }
        ],
        "dimensions": [
            {
                "value": 10.0,
                "unit": "mm",
            }
        ],
    }

    records = import_service._parse_extraction_result(extraction_result)
    assert len(records) == 2
    assert records[0]["col1"] == "val1"
    assert records[1]["dimension_value"] == 10.0


def test_map_record_data(import_service: ImportService) -> None:
    """Test mapping source data to target field IDs."""
    source_data = {
        "source_field1": "value1",
        "source_field2": "value2",
        "unmapped_field": "value3",
    }

    field_mapping = {
        "source_field1": "target_id_1",
        "source_field2": "target_id_2",
    }

    mapped_data = import_service._map_record_data(source_data, field_mapping)

    assert len(mapped_data) == 2
    assert mapped_data["target_id_1"] == "value1"
    assert mapped_data["target_id_2"] == "value2"
    assert "unmapped_field" not in mapped_data


def test_map_record_data_missing_source_fields(import_service: ImportService) -> None:
    """Test mapping when source data is missing some fields."""
    source_data = {
        "source_field1": "value1",
    }

    field_mapping = {
        "source_field1": "target_id_1",
        "source_field2": "target_id_2",  # Missing in source
    }

    mapped_data = import_service._map_record_data(source_data, field_mapping)

    assert len(mapped_data) == 1
    assert mapped_data["target_id_1"] == "value1"
    assert "target_id_2" not in mapped_data


@pytest.mark.asyncio
async def test_validate_record_data_success(
    db_session: AsyncSession,
    test_table: Table,
    test_field: Field,
    import_service: ImportService,
) -> None:
    """Test successful record data validation."""
    data = {str(test_field.id): "test value"}

    # Should not raise any exception
    await import_service._validate_record_data(
        db_session,
        str(test_table.id),
        data,
    )


@pytest.mark.asyncio
async def test_validate_record_data_invalid_field_id(
    db_session: AsyncSession,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test validation with invalid field ID."""
    data = {str(uuid4()): "test value"}

    with pytest.raises(ConflictError) as exc_info:
        await import_service._validate_record_data(
            db_session,
            str(test_table.id),
            data,
        )
    assert "does not exist in table" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_record_data_required_field_missing(
    db_session: AsyncSession,
    test_table: Table,
    import_service: ImportService,
) -> None:
    """Test validation when required field value is None."""
    required_field = Field(
        table_id=test_table.id,
        name="Required Field",
        field_type=FieldType.TEXT.value,
        is_required=True,
    )
    db_session.add(required_field)
    await db_session.commit()
    await db_session.refresh(required_field)

    data = {str(required_field.id): None}

    with pytest.raises(ConflictError) as exc_info:
        await import_service._validate_record_data(
            db_session,
            str(test_table.id),
            data,
        )
    assert "is required" in str(exc_info.value)
