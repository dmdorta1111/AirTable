"""
Unit tests for ExportService.

Tests export format generation, field selection, view filters,
attachment handling, and error scenarios.
"""

import csv
import json
import zipfile
from io import BytesIO, StringIO
from xml.etree import ElementTree as ET

import pytest
from openpyxl import load_workbook
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.view import View, FilterCondition, Sort
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.models.user import User
from pybase.services.export_service import ExportService
from pybase.core.exceptions import NotFoundError, PermissionDeniedError


@pytest.fixture
def export_service():
    """Create ExportService instance."""
    return ExportService()


class TestExportServiceBasics:
    """Test basic service initialization and configuration."""

    def test_export_service_init(self, export_service):
        """Test ExportService can be initialized."""
        assert export_service is not None
        assert hasattr(export_service, 'export_records')

    @pytest.mark.asyncio
    async def test_export_service_init_with_db(self, export_service, db_session):
        """Test ExportService works with database session."""
        assert export_service is not None
        # Service should be able to use db_session
        assert db_session is not None


class TestCSVExport:
    """Test CSV format export generation."""

    @pytest.mark.asyncio
    async def test_csv_export_basic(self, export_service, db_session, test_user):
        """Test basic CSV export generates valid CSV."""
        # Create workspace, base, and table
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        # Add user as workspace member
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        # Create a text field
        field = Field(
            table_id=table.id,
            name="Name",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create test records
        record1 = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Alice"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record1)

        record2 = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Bob"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record2)
        await db_session.commit()

        # Export to CSV
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="csv"
        ):
            chunks.append(chunk)

        # Verify CSV content
        csv_data = b''.join(chunks).decode('utf-8')
        reader = csv.reader(StringIO(csv_data))
        rows = list(reader)

        assert len(rows) == 3  # Header + 2 data rows
        assert rows[0] == ["Name"]
        assert rows[1] == ["Alice"]
        assert rows[2] == ["Bob"]

    @pytest.mark.asyncio
    async def test_csv_export_with_field_selection(self, export_service, db_session, test_user):
        """Test CSV export with specific field selection."""
        # Setup workspace, base, table
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        # Create multiple fields
        field1 = Field(
            table_id=table.id,
            name="Name",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field1)
        await db_session.commit()
        await db_session.refresh(field1)

        field2 = Field(
            table_id=table.id,
            name="Email",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field2)
        await db_session.commit()
        await db_session.refresh(field2)

        # Create test record
        record = Record(
            table_id=table.id,
            data=f'{{"{field1.id}": "Alice", "{field2.id}": "alice@example.com"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record)
        await db_session.commit()

        # Export only first field
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="csv",
            field_ids=[field1.id]
        ):
            chunks.append(chunk)

        # Verify only selected field is exported
        csv_data = b''.join(chunks).decode('utf-8')
        reader = csv.reader(StringIO(csv_data))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0] == ["Name"]
        assert rows[1] == ["Alice"]
        # Email should not be in export


class TestJSONExport:
    """Test JSON format export generation."""

    @pytest.mark.asyncio
    async def test_json_export_basic(self, export_service, db_session, test_user):
        """Test basic JSON export generates valid JSON."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="Name",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        record = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Alice"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record)
        await db_session.commit()

        # Export to JSON
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="json"
        ):
            chunks.append(chunk)

        # Verify JSON content
        json_data = json.loads(b''.join(chunks).decode('utf-8'))
        assert isinstance(json_data, list)
        assert len(json_data) == 1
        assert json_data[0]["Name"] == "Alice"


class TestExcelExport:
    """Test Excel (.xlsx) format export generation."""

    @pytest.mark.asyncio
    async def test_excel_export_basic(self, export_service, db_session, test_user):
        """Test basic Excel export generates valid .xlsx file."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="Name",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        record = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Alice"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record)
        await db_session.commit()

        # Export to Excel
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="xlsx"
        ):
            chunks.append(chunk)

        # Verify Excel file
        excel_data = BytesIO(b''.join(chunks))
        workbook = load_workbook(excel_data)
        sheet = workbook.active

        assert sheet["A1"].value == "Name"
        assert sheet["A2"].value == "Alice"


class TestXMLExport:
    """Test XML format export generation."""

    @pytest.mark.asyncio
    async def test_xml_export_basic(self, export_service, db_session, test_user):
        """Test basic XML export generates valid XML."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="Name",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        record = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Alice"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record)
        await db_session.commit()

        # Export to XML
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="xml"
        ):
            chunks.append(chunk)

        # Verify XML content
        xml_data = b''.join(chunks).decode('utf-8')
        root = ET.fromstring(xml_data)

        assert root.tag == "records"
        records = root.findall("record")
        assert len(records) == 1

        # Check field data
        name_elem = records[0].find("Name")
        assert name_elem is not None
        assert name_elem.text == "Alice"


class TestFieldSelection:
    """Test field selection functionality."""

    @pytest.mark.asyncio
    async def test_export_with_invalid_field_id(self, export_service, db_session, test_user):
        """Test export handles invalid field IDs gracefully."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="Name",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        record = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Alice"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record)
        await db_session.commit()

        # Export with invalid field ID (should ignore invalid ID)
        invalid_field_id = uuid4()
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="csv",
            field_ids=[invalid_field_id]
        ):
            chunks.append(chunk)

        # Should export empty (no valid fields)
        csv_data = b''.join(chunks).decode('utf-8')
        reader = csv.reader(StringIO(csv_data))
        rows = list(reader)

        # Should have header but no data columns
        assert len(rows) >= 1


class TestViewFilters:
    """Test view filter application."""

    @pytest.mark.asyncio
    async def test_export_applies_view_filters(self, export_service, db_session, test_user):
        """Test export respects view filter conditions."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="Status",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create records with different statuses
        record1 = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "active"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record1)

        record2 = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "inactive"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record2)
        await db_session.commit()

        # Create view with filter
        view = View(
            table_id=table.id,
            name="Active View",
            filters=json.dumps([{
                "field_id": str(field.id),
                "operator": "equals",
                "value": "active"
            }])
        )
        db_session.add(view)
        await db_session.commit()
        await db_session.refresh(view)

        # Export with view filter
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="csv",
            view_id=view.id
        ):
            chunks.append(chunk)

        # Verify only active records exported
        csv_data = b''.join(chunks).decode('utf-8')
        reader = csv.reader(StringIO(csv_data))
        rows = list(reader)

        # Should have header + 1 active record
        assert len(rows) == 2
        assert rows[1] == ["active"]


class TestViewSorts:
    """Test view sort application."""

    @pytest.mark.asyncio
    async def test_export_applies_view_sorts(self, export_service, db_session, test_user):
        """Test export respects view sort order."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="Name",
            field_type=FieldType.TEXT.value
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create records
        record1 = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Charlie"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record1)

        record2 = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Alice"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record2)

        record3 = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "Bob"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record3)
        await db_session.commit()

        # Create view with sort
        view = View(
            table_id=table.id,
            name="Sorted View",
            sorts=json.dumps([{
                "field_id": str(field.id),
                "order": "asc"
            }])
        )
        db_session.add(view)
        await db_session.commit()
        await db_session.refresh(view)

        # Export with view sort
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="csv",
            view_id=view.id
        ):
            chunks.append(chunk)

        # Verify records are sorted
        csv_data = b''.join(chunks).decode('utf-8')
        reader = csv.reader(StringIO(csv_data))
        rows = list(reader)

        # Check sort order (excluding header)
        data_rows = rows[1:]
        assert data_rows[0] == ["Alice"]
        assert data_rows[1] == ["Bob"]
        assert data_rows[2] == ["Charlie"]


class TestLinkedRecordFlattening:
    """Test linked record flattening."""

    @pytest.mark.asyncio
    async def test_export_flattens_linked_records(self, export_service, db_session, test_user):
        """Test export includes flattened linked record data."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        # Create linked table
        linked_table = Table(base_id=base.id, name="Linked Table")
        db_session.add(linked_table)
        await db_session.commit()
        await db_session.refresh(linked_table)

        linked_field = Field(
            table_id=linked_table.id,
            name="Category",
            field_type=FieldType.TEXT.value
        )
        db_session.add(linked_field)
        await db_session.commit()
        await db_session.refresh(linked_field)

        # Create linked record
        linked_record = Record(
            table_id=linked_table.id,
            data=f'{{"{linked_field.id}": "Electronics"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(linked_record)
        await db_session.commit()
        await db_session.refresh(linked_record)

        # Create main table
        table = Table(base_id=base.id, name="Main Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        link_field = Field(
            table_id=table.id,
            name="Category Link",
            field_type=FieldType.LINK.value,
            linked_table_id=linked_table.id
        )
        db_session.add(link_field)
        await db_session.commit()
        await db_session.refresh(link_field)

        # Create record with link
        record = Record(
            table_id=table.id,
            data=f'{{"{link_field.id}": ["{linked_record.id}"]}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record)
        await db_session.commit()

        # Export with flattening
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="csv",
            flatten_linked_records=True
        ):
            chunks.append(chunk)

        # Verify flattened data
        csv_data = b''.join(chunks).decode('utf-8')
        reader = csv.reader(StringIO(csv_data))
        rows = list(reader)

        # Should have flattened column with linked record data
        assert len(rows) >= 1
        # Check for flattened column name (Category Link.Category)
        header = rows[0]
        assert any("Category" in col for col in header)


class TestAttachmentExport:
    """Test attachment export and ZIP creation."""

    @pytest.mark.asyncio
    async def test_export_creates_zip_with_attachments(self, export_service, db_session, test_user):
        """Test export creates ZIP file when attachments included."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="Document",
            field_type=FieldType.ATTACHMENT.value
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        record = Record(
            table_id=table.id,
            data=f'{{"{field.id}": []}}',  # Empty attachment list for now
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id
        )
        db_session.add(record)
        await db_session.commit()

        # Export with attachments (CSV format should return ZIP)
        chunks = []
        async for chunk in export_service.export_records(
            db=db_session,
            table_id=table.id,
            user_id=str(test_user.id),
            format="csv",
            include_attachments=True
        ):
            chunks.append(chunk)

        # Verify ZIP file created
        zip_data = BytesIO(b''.join(chunks))
        assert zipfile.is_zipfile(zip_data)

        with zipfile.ZipFile(zip_data, 'r') as zip_file:
            # Should contain CSV file
            files = zip_file.namelist()
            assert any(f.endswith('.csv') for f in files)

    @pytest.mark.asyncio
    async def test_zip_structure_matches_records(self, export_service, db_session, test_user):
        """Test ZIP file structure matches record/field organization."""
        # This is a simplified test - real implementation would need actual attachments
        # The structure should organize files by record/field
        pass


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_format_raises_error(self, export_service, db_session, test_user):
        """Test invalid export format raises appropriate error."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        # Try invalid format
        with pytest.raises(ValueError):
            async for _ in export_service.export_records(
                db=db_session,
                table_id=table.id,
                user_id=str(test_user.id),
                format="invalid_format"
            ):
                pass

    @pytest.mark.asyncio
    async def test_invalid_table_id_raises_error(self, export_service, db_session, test_user):
        """Test non-existent table ID raises appropriate error."""
        # Setup workspace
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()

        # Try non-existent table
        fake_table_id = uuid4()
        with pytest.raises(NotFoundError):
            async for _ in export_service.export_records(
                db=db_session,
                table_id=fake_table_id,
                user_id=str(test_user.id),
                format="csv"
            ):
                pass

    @pytest.mark.asyncio
    async def test_permission_denied_for_non_member(self, export_service, db_session, test_user):
        """Test non-workspace members get permission denied."""
        # Create workspace owned by different user
        other_user = User(
            email="other@example.com",
            hashed_password="hash",
            name="Other User"
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        workspace = Workspace(owner_id=other_user.id, name="Other Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Other Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Other Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        # Try to export as non-member
        with pytest.raises(PermissionDeniedError):
            async for _ in export_service.export_records(
                db=db_session,
                table_id=table.id,
                user_id=str(test_user.id),
                format="csv"
            ):
                pass

    @pytest.mark.asyncio
    async def test_invalid_view_id_raises_error(self, export_service, db_session, test_user):
        """Test invalid view ID raises appropriate error."""
        # Setup
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=test_user.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        await db_session.commit()

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        # Try non-existent view
        fake_view_id = uuid4()
        with pytest.raises(NotFoundError):
            async for _ in export_service.export_records(
                db=db_session,
                table_id=table.id,
                user_id=str(test_user.id),
                format="csv",
                view_id=fake_view_id
            ):
                pass
