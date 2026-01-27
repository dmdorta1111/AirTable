"""
End-to-end tests for synchronous export workflows.

This test suite validates the complete synchronous export workflow:
1. Create test table with sample data including attachments and linked records
2. Export to CSV format and verify data integrity
3. Export to JSON format and verify structure
4. Export to Excel format and verify .xlsx file validity
5. Export to XML format and verify XML structure
"""

import asyncio
import io
import json
import zipfile
from datetime import datetime, UTC
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from openpyxl import load_workbook
from sqlalchemy.ext.asyncio import AsyncSession
from xml.etree import ElementTree as ET

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.table import Table
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.user import User
from pybase.models.view import View
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.extraction import ExportFormat, ExportJobStatus


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Export Test Workspace",
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
    """Create a test base for export testing."""
    base = Base(
        workspace_id=test_workspace.id,
        name="Export Test Base",
        description="Base for export E2E testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def linked_table(db_session: AsyncSession, test_base: Base, test_user: User) -> Table:
    """Create a linked table for testing linked record flattening."""
    table = Table(
        base_id=test_base.id,
        name="Categories",
        description="Categories table for linked records",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    category_name_field = Field(
        table_id=table.id,
        name="Category Name",
        field_type=FieldType.TEXT,
        order=0,
    )
    description_field = Field(
        table_id=table.id,
        name="Description",
        field_type=FieldType.TEXT,
        order=1,
    )
    db_session.add(category_name_field)
    db_session.add(description_field)
    await db_session.commit()
    await db_session.refresh(category_name_field)
    await db_session.refresh(description_field)

    # Create sample records
    categories = [
        {"Category Name": "Electronics", "Description": "Electronic devices"},
        {"Category Name": "Furniture", "Description": "Office furniture"},
        {"Category Name": "Supplies", "Description": "Office supplies"},
    ]

    for category_data in categories:
        # Map field names to field IDs
        record_data = {
            str(category_name_field.id): category_data["Category Name"],
            str(description_field.id): category_data["Description"],
        }
        record = Record(
            table_id=table.id,
            created_by_id=test_user.id,
            data=json.dumps(record_data),
        )
        db_session.add(record)
    await db_session.commit()

    return table


@pytest_asyncio.fixture
async def test_table(
    db_session: AsyncSession,
    test_base: Base,
    test_user: User,
    linked_table: Table
) -> Table:
    """Create a test table with sample data for export testing."""
    # Create table
    table = Table(
        base_id=test_base.id,
        name="Products",
        description="Sample product data for export testing",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    name_field = Field(
        table_id=table.id,
        name="Product Name",
        field_type=FieldType.TEXT,
        order=0,
    )
    price_field = Field(
        table_id=table.id,
        name="Price",
        field_type=FieldType.NUMBER,
        order=1,
    )
    quantity_field = Field(
        table_id=table.id,
        name="Quantity",
        field_type=FieldType.NUMBER,
        order=2,
    )
    in_stock_field = Field(
        table_id=table.id,
        name="In Stock",
        field_type=FieldType.BOOLEAN,
        order=3,
    )
    category_field = Field(
        table_id=table.id,
        name="Category",
        field_type=FieldType.LINKED_RECORD,
        order=4,
        options=json.dumps({
            "linked_table_id": str(linked_table.id),
        }),
    )
    attachment_field = Field(
        table_id=table.id,
        name="Attachments",
        field_type=FieldType.ATTACHMENT,
        order=5,
    )

    for field in [name_field, price_field, quantity_field, in_stock_field, category_field, attachment_field]:
        db_session.add(field)
    await db_session.commit()

    # Refresh to get field IDs
    for field in [name_field, price_field, quantity_field, in_stock_field, category_field, attachment_field]:
        await db_session.refresh(field)

    # Get linked records for category field
    from sqlalchemy import select
    linked_records_result = await db_session.execute(
        select(Record).where(Record.table_id == str(linked_table.id))
    )
    linked_records = linked_records_result.scalars().all()

    # Create sample records
    sample_data = [
        {
            "Product Name": "Laptop",
            "Price": 999.99,
            "Quantity": 10,
            "In Stock": True,
            "Category": linked_records[0].id if len(linked_records) > 0 else None,
            "Attachments": [
                {
                    "id": str(uuid4()),
                    "filename": "laptop_spec.pdf",
                    "url": "http://example.com/laptop_spec.pdf",
                    "size": 1024,
                    "mime_type": "application/pdf"
                }
            ]
        },
        {
            "Product Name": "Desk Chair",
            "Price": 249.99,
            "Quantity": 25,
            "In Stock": True,
            "Category": linked_records[1].id if len(linked_records) > 1 else None,
            "Attachments": []
        },
        {
            "Product Name": "Notebook",
            "Price": 4.99,
            "Quantity": 100,
            "In Stock": True,
            "Category": linked_records[2].id if len(linked_records) > 2 else None,
            "Attachments": [
                {
                    "id": str(uuid4()),
                    "filename": "notebook.jpg",
                    "url": "http://example.com/notebook.jpg",
                    "size": 512,
                    "mime_type": "image/jpeg"
                }
            ]
        },
        {
            "Product Name": "Monitor",
            "Price": 399.99,
            "Quantity": 0,
            "In Stock": False,
            "Category": linked_records[0].id if len(linked_records) > 0 else None,
            "Attachments": []
        },
        {
            "Product Name": "Pen Set",
            "Price": 12.99,
            "Quantity": 50,
            "In Stock": True,
            "Category": linked_records[2].id if len(linked_records) > 2 else None,
            "Attachments": []
        },
    ]

    for data in sample_data:
        # Map field names to field IDs
        record_data = {
            str(name_field.id): data["Product Name"],
            str(price_field.id): data["Price"],
            str(quantity_field.id): data["Quantity"],
            str(in_stock_field.id): data["In Stock"],
            str(category_field.id): [str(data["Category"])] if data["Category"] else [],
            str(attachment_field.id): data["Attachments"],
        }
        record = Record(
            table_id=table.id,
            created_by_id=test_user.id,
            data=json.dumps(record_data),
        )
        db_session.add(record)
    await db_session.commit()

    return table


@pytest_asyncio.fixture
async def test_view(db_session: AsyncSession, test_table: Table) -> View:
    """Create a test view with filters and sorts."""
    view = View(
        table_id=test_table.id,
        name="In Stock Products",
        type="grid",
        sort=json.dumps([
            {
                "field_id": None,  # Will be set after getting field IDs
                "direction": "desc"
            }
        ]),
        filter=json.dumps([]),
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)
    return view


@pytest.mark.asyncio
class TestSynchronousExportWorkflows:
    """End-to-end test suite for synchronous export workflows."""

    async def test_export_to_csv_format(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
        test_user: User,
    ):
        """
        Test synchronous export to CSV format.

        Workflow:
        1. Create table with sample data
        2. Export to CSV format via API
        3. Verify CSV structure and data integrity
        4. Verify headers match field names
        5. Verify all records are present
        """
        # Export to CSV
        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
            headers=auth_headers,
            params={"format": "csv"},
        )

        assert response.status_code == 200, f"CSV export failed: {response.text}"
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        # Parse CSV content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")

        # Verify header row exists
        assert len(lines) >= 1, "CSV should have at least a header row"
        headers = lines[0].split(",")

        # Verify expected headers are present
        expected_headers = ["Product Name", "Price", "Quantity", "In Stock", "Category", "Attachments"]
        for expected in expected_headers:
            assert expected in headers, f"Expected header '{expected}' not found in CSV"

        # Verify data rows exist (5 sample records + 1 header = 6 lines)
        assert len(lines) >= 6, f"CSV should have at least 6 lines (header + 5 records), got {len(lines)}"

        # Verify data integrity - check first data row
        first_row = lines[1].split(",")
        assert "Laptop" in first_row[0] or "Laptop" in content, "First product should be 'Laptop'"
        assert "999.99" in content, "Price 999.99 should be in CSV"
        assert "100" in content, "Quantity 100 should be in CSV"

    async def test_export_to_json_format(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """
        Test synchronous export to JSON format.

        Workflow:
        1. Export to JSON format via API
        2. Verify JSON structure is valid
        3. Verify data integrity
        4. Verify all fields are present
        """
        # Export to JSON
        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
            headers=auth_headers,
            params={"format": "json"},
        )

        assert response.status_code == 200, f"JSON export failed: {response.text}"
        assert response.headers["content-type"] == "application/json"

        # Parse JSON content
        data = response.json()
        assert isinstance(data, list), "JSON export should return an array"
        assert len(data) >= 5, f"Should have at least 5 records, got {len(data)}"

        # Verify first record structure
        first_record = data[0]
        assert "Product Name" in first_record, "Record should have 'Product Name' field"
        assert "Price" in first_record, "Record should have 'Price' field"
        assert "Quantity" in first_record, "Record should have 'Quantity' field"
        assert "In Stock" in first_record, "Record should have 'In Stock' field"

        # Verify data integrity
        product_names = [r.get("Product Name") for r in data]
        expected_products = ["Laptop", "Desk Chair", "Notebook", "Monitor", "Pen Set"]
        for expected in expected_products:
            assert expected in product_names, f"Expected product '{expected}' not found in export"

    async def test_export_to_excel_format(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """
        Test synchronous export to Excel (.xlsx) format.

        Workflow:
        1. Export to Excel format via API
        2. Verify .xlsx file validity
        3. Verify workbook structure
        4. Verify data integrity in cells
        """
        # Export to Excel
        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
            headers=auth_headers,
            params={"format": "xlsx"},
        )

        assert response.status_code == 200, f"Excel export failed: {response.text}"
        assert "application/vnd.openxmlformats" in response.headers["content-type"]

        # Load Excel workbook from content
        workbook_content = io.BytesIO(response.content)
        workbook = load_workbook(workbook_content)

        # Verify workbook structure
        assert "Export" in workbook.sheetnames, "Excel file should have 'Export' sheet"
        worksheet = workbook["Export"]

        # Verify headers in first row
        headers = [cell.value for cell in worksheet[1]]
        assert "Product Name" in headers, "Header 'Product Name' should be present"
        assert "Price" in headers, "Header 'Price' should be present"
        assert "Quantity" in headers, "Header 'Quantity' should be present"

        # Verify data rows exist
        row_count = sum(1 for row in worksheet.iter_rows() if any(cell.value for cell in row))
        assert row_count >= 6, f"Should have at least 6 rows (header + 5 records), got {row_count}"

        # Verify data in first data row
        first_row_values = [cell.value for cell in worksheet[2]]
        assert "Laptop" in first_row_values, "First product should be 'Laptop'"

        workbook.close()

    async def test_export_to_xml_format(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """
        Test synchronous export to XML format.

        Workflow:
        1. Export to XML format via API
        2. Verify XML structure is valid
        3. Verify XML elements and attributes
        4. Verify data integrity
        """
        # Export to XML
        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
            headers=auth_headers,
            params={"format": "xml"},
        )

        assert response.status_code == 200, f"XML export failed: {response.text}"
        assert "application/xml" in response.headers["content-type"]

        # Parse XML content
        content = response.content.decode("utf-8")
        root = ET.fromstring(content)

        # Verify root element
        assert root.tag == "records", "Root element should be 'records'"

        # Verify records exist
        record_elements = list(root.findall("record"))
        assert len(record_elements) >= 5, f"Should have at least 5 record elements, got {len(record_elements)}"

        # Verify first record structure
        first_record = record_elements[0]
        assert first_record.find("Product Name") is not None, "Record should have 'Product Name' field"
        assert first_record.find("Price") is not None, "Record should have 'Price' field"
        assert first_record.find("Quantity") is not None, "Record should have 'Quantity' field"

        # Verify data integrity
        product_names = [
            record.find("Product Name").text
            for record in record_elements
            if record.find("Product Name") is not None
        ]
        assert "Laptop" in product_names, "Product 'Laptop' should be in export"
        assert "Desk Chair" in product_names, "Product 'Desk Chair' should be in export"

    async def test_export_with_field_selection(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """
        Test export with specific field selection.

        Workflow:
        1. Export only selected fields (Product Name, Price)
        2. Verify only selected fields are in export
        3. Verify other fields are excluded
        """
        # Get field IDs for Product Name and Price fields
        from sqlalchemy import select
        fields_response = await client.get(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/fields",
            headers=auth_headers,
        )
        assert fields_response.status_code == 200

        fields_data = fields_response.json()

        fields_data = response.json()
        product_name_field = next((f for f in fields_data if f["name"] == "Product Name"), None)
        price_field = next((f for f in fields_data if f["name"] == "Price"), None)

        assert product_name_field is not None, "Product Name field should exist"
        assert price_field is not None, "Price field should exist"

        # Export with field selection
        fields_param = f"{product_name_field['id']},{price_field['id']}"
        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
            headers=auth_headers,
            params={
                "format": "csv",
                "fields": fields_param,
            },
        )

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")

        # Verify headers only include selected fields
        headers = lines[0].split(",")
        assert "Product Name" in headers, "Product Name should be in export"
        assert "Price" in headers, "Price should be in export"
        assert "Quantity" not in headers, "Quantity should not be in export (not selected)"
        assert "In Stock" not in headers, "In Stock should not be in export (not selected)"

    async def test_export_with_linked_record_flattening(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
        linked_table: Table,
    ):
        """
        Test export with linked record flattening.

        Workflow:
        1. Export with flatten_linked_records=true
        2. Verify linked record data is embedded
        3. Verify column naming convention (Category.Category Name)
        """
        # Export with linked record flattening
        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
            headers=auth_headers,
            params={
                "format": "json",
                "flatten_linked_records": "true",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Should have at least one record"

        # Verify linked record fields are flattened
        first_record = data[0]
        assert "Category.Category Name" in first_record, "Linked record should be flattened with 'Category.Category Name' field"
        assert "Category.Description" in first_record, "Linked record should be flattened with 'Category.Description' field"

        # Verify flattened data values
        category_name = first_record.get("Category.Category Name")
        assert category_name in ["Electronics", "Furniture", "Supplies"], f"Category name should be valid, got: {category_name}"

    async def test_export_with_attachments_as_zip(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """
        Test export with attachments included as ZIP.

        Workflow:
        1. Export with include_attachments=true
        2. Verify ZIP file is returned
        3. Verify ZIP structure and contents
        """
        # Export with attachments
        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
            headers=auth_headers,
            params={
                "format": "csv",
                "include_attachments": "true",
            },
        )

        assert response.status_code == 200
        assert "application/zip" in response.headers["content-type"], "Should return ZIP file"

        # Verify ZIP structure
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content, "r") as zip_file:
            file_list = zip_file.namelist()

            # ZIP should contain at least the CSV export file
            assert len(file_list) > 0, "ZIP should contain files"

            # Verify README if no actual attachments were downloaded (mock URLs)
            if "README.txt" in file_list:
                readme_content = zip_file.read("README.txt").decode("utf-8")
                assert "no attachments" in readme_content.lower() or "empty" in readme_content.lower()

    async def test_export_unsupported_format_raises_error(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """
        Test that requesting an unsupported format returns proper error.

        Workflow:
        1. Request export with invalid format
        2. Verify 400 error response
        3. Verify error message is descriptive
        """
        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
            headers=auth_headers,
            params={"format": "pdf"},
        )

        assert response.status_code == 400, "Should return 400 for unsupported format"
        error_detail = response.json()
        assert "detail" in error_detail, "Error response should have 'detail' field"
        assert "format" in error_detail["detail"].lower(), "Error should mention format issue"

    async def test_export_with_invalid_table_id_raises_error(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """
        Test that exporting from non-existent table returns proper error.

        Workflow:
        1. Request export with invalid table_id
        2. Verify 404 error response
        """
        fake_table_id = uuid4()

        response = await client.post(
            f"{settings.api_v1_prefix}/tables/{fake_table_id}/records/export",
            headers=auth_headers,
            params={"format": "csv"},
        )

        assert response.status_code == 404, "Should return 404 for non-existent table"

    async def test_export_all_formats_from_same_table(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """
        Test exporting the same table data to all supported formats.

        Workflow:
        1. Export to all 4 formats (CSV, JSON, XLSX, XML)
        2. Verify all exports succeed
        3. Verify data consistency across formats
        """
        formats = ["csv", "json", "xlsx", "xml"]
        export_results = {}

        for fmt in formats:
            response = await client.post(
                f"{settings.api_v1_prefix}/tables/{test_table.id}/records/export",
                headers=auth_headers,
                params={"format": fmt},
            )
            assert response.status_code == 200, f"Export to {fmt.upper()} failed"
            export_results[fmt] = response

        # Verify CSV export
        csv_content = export_results["csv"].content.decode("utf-8")
        assert "Laptop" in csv_content, "CSV should contain 'Laptop'"
        assert "999.99" in csv_content, "CSV should contain price 999.99"

        # Verify JSON export
        json_data = export_results["json"].json()
        assert len(json_data) >= 5, "JSON should have at least 5 records"
        assert any(r.get("Product Name") == "Laptop" for r in json_data), "JSON should contain Laptop"

        # Verify Excel export
        excel_content = io.BytesIO(export_results["xlsx"].content)
        workbook = load_workbook(excel_content)
        assert "Export" in workbook.sheetnames, "Excel should have Export sheet"
        workbook.close()

        # Verify XML export
        xml_content = export_results["xml"].content.decode("utf-8")
        root = ET.fromstring(xml_content)
        records = root.findall("record")
        assert len(records) >= 5, "XML should have at least 5 record elements"


@pytest_asyncio.fixture
async def large_test_table(
    db_session: AsyncSession,
    test_base: Base,
    test_user: User
) -> Table:
    """Create a test table with 10,000+ records for background export testing."""
    # Create table
    table = Table(
        base_id=test_base.id,
        name="Large Dataset",
        description="Large dataset for background export testing",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    name_field = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT,
        order=0,
    )
    value_field = Field(
        table_id=table.id,
        name="Value",
        field_type=FieldType.NUMBER,
        order=1,
    )
    active_field = Field(
        table_id=table.id,
        name="Active",
        field_type=FieldType.BOOLEAN,
        order=2,
    )

    for field in [name_field, value_field, active_field]:
        db_session.add(field)
    await db_session.commit()

    # Refresh to get field IDs
    for field in [name_field, value_field, active_field]:
        await db_session.refresh(field)

    # Create 10,000 records
    batch_size = 500
    total_records = 10000

    for batch_start in range(0, total_records, batch_size):
        batch_end = min(batch_start + batch_size, total_records)
        records = []

        for i in range(batch_start, batch_end):
            record_data = {
                str(name_field.id): f"Record {i}",
                str(value_field.id): i * 1.5,
                str(active_field.id): i % 2 == 0,
            }
            record = Record(
                table_id=table.id,
                created_by_id=test_user.id,
                data=json.dumps(record_data),
            )
            records.append(record)

        db_session.add_all(records)
        await db_session.commit()

    print(f"Created {total_records} records for background export testing")

    return table


@pytest.mark.asyncio
class TestBackgroundExportWorkflows:
    """End-to-end test suite for background export workflows."""

    async def test_background_export_large_dataset_csv(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        large_test_table: Table,
    ):
        """
        Test background export workflow with large dataset (10,000+ records) to CSV.

        Workflow:
        1. Create table with 10,000+ records
        2. Trigger background export job via POST /exports
        3. Poll job status until completed (with timeout)
        4. Verify job transitions from PENDING to PROCESSING to COMPLETED
        5. Verify download link is generated
        6. Download file and verify data integrity
        """
        # Step 1: Create background export job
        export_request = {
            "format": "csv",
            "table_id": str(large_test_table.id),
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/exports",
            json=export_request,
            headers=auth_headers,
        )

        assert response.status_code == 201, f"Failed to create export job: {response.text}"
        job_data = response.json()

        # Verify initial job response
        assert "id" in job_data, "Job response should include job ID"
        job_id = job_data["id"]
        assert job_data["status"] in ["PENDING", "PROCESSING"], \
            f"Initial status should be PENDING or PROCESSING, got {job_data['status']}"
        assert job_data["format"] == "csv"
        assert job_data["table_id"] == str(large_test_table.id)
        assert job_data["total_records"] >= 10000, \
            f"Expected at least 10,000 records, got {job_data['total_records']}"

        # Step 2: Poll job status until completion (with timeout)
        max_wait_time = 300  # 5 minutes
        poll_interval = 2  # 2 seconds
        elapsed_time = 0
        previous_status = None

        while elapsed_time < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            # Poll job status
            status_response = await client.get(
                f"{settings.api_v1_prefix}/exports/{job_id}",
                headers=auth_headers,
            )

            assert status_response.status_code == 200, f"Failed to get job status: {status_response.text}"
            job_status = status_response.json()

            current_status = job_status["status"]

            # Log status transitions
            if current_status != previous_status:
                print(f"Job {job_id[:8]} status: {previous_status} -> {current_status}, "
                      f"Progress: {job_status.get('progress', 0)}%, "
                      f"Records: {job_status.get('records_processed', 0)}/{job_status.get('total_records', 0)}")
                previous_status = current_status

            # Check for completion
            if current_status == "COMPLETED":
                # Verify completion details
                assert job_status["progress"] == 100, "Completed job should have 100% progress"
                assert job_status["records_processed"] >= 10000, \
                    f"Expected at least 10,000 processed records, got {job_status['records_processed']}"
                assert "file_url" in job_status and job_status["file_url"], \
                    "Completed job should have a download URL"
                assert job_status["file_size"] > 0, \
                    f"File size should be positive, got {job_status['file_size']}"
                assert job_status["completed_at"] is not None, \
                    "Completed job should have completion timestamp"

                print(f"Job completed successfully in {elapsed_time}s")
                break

            elif current_status == "FAILED":
                error_msg = job_status.get("error_message", "Unknown error")
                pytest.fail(f"Export job failed: {error_msg}")

            # Verify progress during processing
            if current_status == "PROCESSING":
                assert 0 <= job_status["progress"] <= 100, \
                    f"Progress should be 0-100, got {job_status['progress']}"
                assert job_status["records_processed"] >= 0, \
                    "Records processed should be non-negative"

        else:
            pytest.fail(f"Export job did not complete within {max_wait_time}s")

        # Step 3: Download exported file
        download_response = await client.get(
            f"{settings.api_v1_prefix}/exports/{job_id}/download",
            headers=auth_headers,
        )

        assert download_response.status_code == 200, f"Failed to download file: {download_response.text}"
        assert download_response.headers["content-type"] == "text/csv; charset=utf-8"

        # Step 4: Verify downloaded file content
        content = download_response.content.decode("utf-8")
        lines = content.strip().split("\n")

        # Verify header + data rows
        assert len(lines) >= 10001, \
            f"Expected at least 10,001 lines (header + 10,000 records), got {len(lines)}"

        # Verify CSV structure
        headers = lines[0].split(",")
        assert "Name" in headers, "CSV should have 'Name' column"
        assert "Value" in headers, "CSV should have 'Value' column"
        assert "Active" in headers, "CSV should have 'Active' column"

        # Verify data integrity (sample checks)
        assert "Record 0" in content, "First record should be present"
        assert "Record 9999" in content, "Last record should be present"

        print(f"Successfully downloaded and verified CSV with {len(lines)} lines")

    async def test_background_export_status_transitions(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """
        Test that background export job properly transitions through all statuses.

        Workflow:
        1. Create export job
        2. Verify initial PENDING status
        3. Poll and verify transition to PROCESSING
        4. Poll and verify transition to COMPLETED
        5. Verify final state has all required fields
        """
        # Create export job
        export_request = {
            "format": "json",
            "table_id": str(test_table.id),
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/exports",
            json=export_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        job_id = response.json()["id"]

        # Track status transitions
        statuses_seen = []

        # Poll for status transitions
        max_wait_time = 60  # 1 minute
        poll_interval = 1  # 1 second
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            status_response = await client.get(
                f"{settings.api_v1_prefix}/exports/{job_id}",
                headers=auth_headers,
            )

            assert status_response.status_code == 200
            job_status = status_response.json()
            current_status = job_status["status"]

            # Record status if not seen before
            if current_status not in statuses_seen:
                statuses_seen.append(current_status)
                print(f"Status transition: {current_status}")

            # Stop when completed
            if current_status == "COMPLETED":
                break

            elif current_status == "FAILED":
                pytest.fail(f"Export job failed: {job_status.get('error_message')}")

        # Verify status transitions
        assert "PENDING" in statuses_seen or "PROCESSING" in statuses_seen, \
            "Job should start with PENDING or PROCESSING status"
        assert "COMPLETED" in statuses_seen, \
            "Job should reach COMPLETED status"

        # Verify final job state
        final_response = await client.get(
            f"{settings.api_v1_prefix}/exports/{job_id}",
            headers=auth_headers,
        )
        final_state = final_response.json()

        assert final_state["status"] == "COMPLETED"
        assert final_state["progress"] == 100
        assert final_state["file_url"] is not None
        assert final_state["completed_at"] is not None
        assert final_state["records_processed"] > 0

    async def test_background_export_multiple_formats(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        large_test_table: Table,
    ):
        """
        Test background export for all supported formats with large dataset.

        Workflow:
        1. Create export jobs for CSV, JSON, XLSX, XML
        2. Poll all jobs to completion
        3. Verify all jobs complete successfully
        4. Verify download links work for all formats
        """
        formats = ["csv", "json", "xlsx", "xml"]
        job_ids = {}

        # Create export jobs for all formats
        for fmt in formats:
            export_request = {
                "format": fmt,
                "table_id": str(large_test_table.id),
            }

            response = await client.post(
                f"{settings.api_v1_prefix}/exports",
                json=export_request,
                headers=auth_headers,
            )

            assert response.status_code == 201, f"Failed to create {fmt} export job"
            job_ids[fmt] = response.json()["id"]
            print(f"Created {fmt.upper()} export job: {job_ids[fmt][:8]}")

        # Wait for all jobs to complete
        max_wait_time = 300  # 5 minutes
        poll_interval = 3  # 3 seconds
        elapsed_time = 0
        completed_jobs = set()

        while elapsed_time < max_wait_time and len(completed_jobs) < len(formats):
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            for fmt in formats:
                if fmt in completed_jobs:
                    continue

                job_id = job_ids[fmt]

                # Check job status
                status_response = await client.get(
                    f"{settings.api_v1_prefix}/exports/{job_id}",
                    headers=auth_headers,
                )

                assert status_response.status_code == 200
                job_status = status_response.json()

                if job_status["status"] == "COMPLETED":
                    completed_jobs.add(fmt)
                    print(f"{fmt.upper()} export job completed: {job_status['records_processed']} records, "
                          f"{job_status['file_size']} bytes")

                elif job_status["status"] == "FAILED":
                    pytest.fail(f"{fmt.upper()} export job failed: {job_status.get('error_message')}")

        # Verify all jobs completed
        assert len(completed_jobs) == len(formats), \
            f"Not all jobs completed: {completed_jobs}/{len(formats)}"

        # Verify download links work for all formats
        for fmt in formats:
            job_id = job_ids[fmt]

            download_response = await client.get(
                f"{settings.api_v1_prefix}/exports/{job_id}/download",
                headers=auth_headers,
            )

            assert download_response.status_code == 200, \
                f"Failed to download {fmt.upper()} file"

            # Verify content type
            content_types = {
                "csv": "text/csv",
                "json": "application/json",
                "xlsx": "application/vnd.openxmlformats",
                "xml": "application/xml",
            }
            expected_type = content_types[fmt]
            assert expected_type in download_response.headers["content-type"], \
                f"{fmt.upper()} file should have {expected_type} content type"

            print(f"Successfully downloaded {fmt.upper()} file")

    async def test_background_export_with_field_selection(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        large_test_table: Table,
    ):
        """
        Test background export with specific field selection.

        Workflow:
        1. Create export job with only specific fields
        2. Wait for job completion
        3. Verify exported file contains only selected fields
        """
        # Get table fields
        fields_response = await client.get(
            f"{settings.api_v1_prefix}/tables/{large_test_table.id}/fields",
            headers=auth_headers,
        )
        assert fields_response.status_code == 200
        fields = fields_response.json()

        # Select only 'Name' and 'Active' fields (exclude 'Value')
        name_field = next((f for f in fields if f["name"] == "Name"), None)
        active_field = next((f for f in fields if f["name"] == "Active"), None)

        assert name_field is not None
        assert active_field is not None

        # Create export job with field selection
        export_request = {
            "format": "csv",
            "table_id": str(large_test_table.id),
            "field_ids": [str(name_field["id"]), str(active_field["id"])],
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/exports",
            json=export_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        job_id = response.json()["id"]

        # Wait for completion
        max_wait_time = 120  # 2 minutes
        poll_interval = 2
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            status_response = await client.get(
                f"{settings.api_v1_prefix}/exports/{job_id}",
                headers=auth_headers,
            )

            job_status = status_response.json()

            if job_status["status"] == "COMPLETED":
                break
            elif job_status["status"] == "FAILED":
                pytest.fail(f"Export failed: {job_status.get('error_message')}")
        else:
            pytest.fail("Export did not complete in time")

        # Download and verify field selection
        download_response = await client.get(
            f"{settings.api_v1_prefix}/exports/{job_id}/download",
            headers=auth_headers,
        )

        assert download_response.status_code == 200
        content = download_response.content.decode("utf-8")
        lines = content.strip().split("\n")

        headers = lines[0].split(",")

        # Verify only selected fields are present
        assert "Name" in headers, "Name field should be in export"
        assert "Active" in headers, "Active field should be in export"
        assert "Value" not in headers, "Value field should NOT be in export (not selected)"

        print(f"Successfully verified field selection: {headers}")
