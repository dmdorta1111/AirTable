"""Export service for streaming large datasets."""

import csv
import json
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO
from typing import Any, AsyncGenerator, Optional
from uuid import UUID

from openpyxl import Workbook

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError, PermissionDeniedError
from pybase.models.base import Base
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


class ExportService:
    """Service for exporting large datasets with streaming."""

    async def export_records(
        self,
        db: AsyncSession,
        table_id: UUID,
        user_id: str,
        format: str = "csv",
        batch_size: int = 1000,
        field_ids: Optional[list[UUID]] = None,
        flatten_linked_records: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream export of records from a table.

        Args:
            db: Database session
            table_id: Table ID to export from
            user_id: User ID requesting export
            format: Export format ('csv', 'json', 'xlsx', or 'xml')
            batch_size: Number of records to fetch per batch
            field_ids: Optional list of field IDs to export. If None, exports all fields.
            flatten_linked_records: If True, fetch and embed linked record data in exports.

        Yields:
            Chunks of export data as bytes

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table

        """
        # Verify table exists and user has access
        table = await db.get(Table, str(table_id))
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        # Get table fields for column headers
        fields = await self._get_table_fields(db, str(table_id))

        # Filter fields if field_ids is provided
        if field_ids is not None:
            field_ids_str = {str(fid) for fid in field_ids}
            fields = [f for f in fields if str(f.id) in field_ids_str]

        if format.lower() == "csv":
            async for chunk in self._stream_csv(db, table_id, fields, batch_size, flatten_linked_records):
                yield chunk
        elif format.lower() == "json":
            async for chunk in self._stream_json(db, table_id, fields, batch_size, flatten_linked_records):
                yield chunk
        elif format.lower() in ("xlsx", "excel"):
            async for chunk in self._stream_excel(db, table_id, fields, batch_size, flatten_linked_records):
                yield chunk
        elif format.lower() == "xml":
            async for chunk in self._stream_xml(db, table_id, fields, batch_size, flatten_linked_records):
                yield chunk
        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def _stream_csv(
        self,
        db: AsyncSession,
        table_id: UUID,
        fields: list[Field],
        batch_size: int,
        flatten_linked_records: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as CSV.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records
            flatten_linked_records: If True, fetch and embed linked record data.

        Yields:
            CSV data chunks as bytes

        """
        output = StringIO()

        # Build field names, expanding linked records if flattening enabled
        field_names, linked_field_map = await self._build_export_field_names(
            db, fields, flatten_linked_records
        )

        # Write CSV header
        writer = csv.DictWriter(output, fieldnames=field_names)
        writer.writeheader()
        header = output.getvalue()
        output.seek(0)
        output.truncate(0)

        yield header.encode("utf-8")

        # Stream records in batches
        offset = 0
        while True:
            # Fetch batch of records
            query = (
                select(Record)
                .where(Record.table_id == str(table_id))
                .where(Record.deleted_at.is_(None))
                .order_by(Record.created_at)
                .offset(offset)
                .limit(batch_size)
            )
            result = await db.execute(query)
            records = result.scalars().all()

            if not records:
                break

            # Write records to CSV
            for record in records:
                try:
                    data = json.loads(record.data) if isinstance(record.data, str) else record.data
                except (json.JSONDecodeError, TypeError):
                    data = {}

                row = await self._build_export_row(
                    db, data, fields, linked_field_map, flatten_linked_records
                )

                writer.writerow(row)
                csv_data = output.getvalue()
                if csv_data:
                    yield csv_data.encode("utf-8")
                    output.seek(0)
                    output.truncate(0)

            offset += len(records)

            if len(records) < batch_size:
                break

    async def _stream_json(
        self,
        db: AsyncSession,
        table_id: UUID,
        fields: list[Field],
        batch_size: int,
        flatten_linked_records: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as JSON array.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records
            flatten_linked_records: If True, fetch and embed linked record data.

        Yields:
            JSON data chunks as bytes

        """
        # Start JSON array
        yield b"["

        first_record = True
        offset = 0

        # Build field name map for flattening
        _, linked_field_map = await self._build_export_field_names(
            db, fields, flatten_linked_records
        )

        while True:
            # Fetch batch of records
            query = (
                select(Record)
                .where(Record.table_id == str(table_id))
                .where(Record.deleted_at.is_(None))
                .order_by(Record.created_at)
                .offset(offset)
                .limit(batch_size)
            )
            result = await db.execute(query)
            records = result.scalars().all()

            if not records:
                break

            # Convert records to JSON
            for record in records:
                try:
                    data = json.loads(record.data) if isinstance(record.data, str) else record.data
                except (json.JSONDecodeError, TypeError):
                    data = {}

                # Build record object with field names, flattening linked records if enabled
                record_obj = await self._build_export_row(
                    db, data, fields, linked_field_map, flatten_linked_records
                )

                # Add comma separator if not first record
                if not first_record:
                    yield b","
                first_record = False

                # Yield JSON record
                record_json = json.dumps(record_obj, ensure_ascii=False)
                yield record_json.encode("utf-8")

            offset += len(records)

            if len(records) < batch_size:
                break

        # End JSON array
        yield b"]"

    async def _stream_excel(
        self,
        db: AsyncSession,
        table_id: UUID,
        fields: list[Field],
        batch_size: int,
        flatten_linked_records: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as Excel (.xlsx) file.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records
            flatten_linked_records: If True, fetch and embed linked record data.

        Yields:
            Excel file data as bytes

        """
        # Create workbook and worksheet
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Export"

        # Build field names, expanding linked records if flattening enabled
        field_names, linked_field_map = await self._build_export_field_names(
            db, fields, flatten_linked_records
        )

        # Write headers
        worksheet.append(field_names)

        # Fetch and write all records
        offset = 0
        while True:
            # Fetch batch of records
            query = (
                select(Record)
                .where(Record.table_id == str(table_id))
                .where(Record.deleted_at.is_(None))
                .order_by(Record.created_at)
                .offset(offset)
                .limit(batch_size)
            )
            result = await db.execute(query)
            records = result.scalars().all()

            if not records:
                break

            # Write records to worksheet
            for record in records:
                try:
                    data = json.loads(record.data) if isinstance(record.data, str) else record.data
                except (json.JSONDecodeError, TypeError):
                    data = {}

                row_dict = await self._build_export_row(
                    db, data, fields, linked_field_map, flatten_linked_records
                )

                row = [row_dict.get(field_name, "") for field_name in field_names]
                worksheet.append(row)

            offset += len(records)

            if len(records) < batch_size:
                break

        # Save workbook to BytesIO
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        # Yield the entire Excel file
        yield output.read()

    async def _stream_xml(
        self,
        db: AsyncSession,
        table_id: UUID,
        fields: list[Field],
        batch_size: int,
        flatten_linked_records: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as XML.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records
            flatten_linked_records: If True, fetch and embed linked record data.

        Yields:
            XML data chunks as bytes

        """
        # Create root element
        root = ET.Element("records")

        # Start XML document
        yield b'<?xml version="1.0" encoding="UTF-8"?>\n'
        yield b"<records>\n"

        # Build field name map for flattening
        _, linked_field_map = await self._build_export_field_names(
            db, fields, flatten_linked_records
        )

        # Stream records in batches
        offset = 0
        while True:
            # Fetch batch of records
            query = (
                select(Record)
                .where(Record.table_id == str(table_id))
                .where(Record.deleted_at.is_(None))
                .order_by(Record.created_at)
                .offset(offset)
                .limit(batch_size)
            )
            result = await db.execute(query)
            records = result.scalars().all()

            if not records:
                break

            # Write records to XML
            for record in records:
                try:
                    data = json.loads(record.data) if isinstance(record.data, str) else record.data
                except (json.JSONDecodeError, TypeError):
                    data = {}

                # Build row dict with flattened linked records if enabled
                row_dict = await self._build_export_row(
                    db, data, fields, linked_field_map, flatten_linked_records
                )

                # Create record element
                record_elem = ET.Element("record")

                # Add fields as child elements
                for field_name, value in row_dict.items():
                    # Create field element
                    field_elem = ET.Element(field_name)

                    # Handle complex values
                    if isinstance(value, (dict, list)):
                        field_elem.text = json.dumps(value)
                    elif value is None:
                        field_elem.text = ""
                    else:
                        field_elem.text = str(value)

                    record_elem.append(field_elem)

                # Convert element to string and yield
                xml_string = ET.tostring(record_elem, encoding="unicode")
                yield f"  {xml_string}\n".encode("utf-8")

            offset += len(records)

            if len(records) < batch_size:
                break

        # End XML document
        yield b"</records>\n"

    async def _build_export_field_names(
        self,
        db: AsyncSession,
        fields: list[Field],
        flatten_linked_records: bool,
    ) -> tuple[list[str], dict[str, Any]]:
        """Build field names for export, expanding linked records if flattening enabled.

        Args:
            db: Database session
            fields: List of table fields
            flatten_linked_records: Whether to expand linked record fields

        Returns:
            Tuple of (field_names list, linked_field_map dict)

        """
        field_names = []
        linked_field_map = {}

        for field in fields:
            if flatten_linked_records and field.field_type == "linked_record":
                # Parse options to get linked table ID
                try:
                    options = json.loads(field.options) if field.options else {}
                except (json.JSONDecodeError, TypeError):
                    options = {}

                linked_table_id = options.get("linked_table_id")
                if linked_table_id:
                    # Fetch fields from linked table
                    linked_fields = await self._get_table_fields(db, linked_table_id)

                    # Create expanded field names like "Customer.Name", "Customer.Email"
                    expanded_names = []
                    for linked_field in linked_fields:
                        expanded_name = f"{field.name}.{linked_field.name}"
                        expanded_names.append(expanded_name)
                        linked_field_map[expanded_name] = {
                            "field": field,
                            "linked_field": linked_field,
                            "linked_table_id": linked_table_id,
                        }

                    field_names.extend(expanded_names)
                else:
                    # No linked table, just use field name
                    field_names.append(field.name)
            else:
                # Non-linked field or flattening disabled
                field_names.append(field.name)

        return field_names, linked_field_map

    async def _build_export_row(
        self,
        db: AsyncSession,
        data: dict[str, Any],
        fields: list[Field],
        linked_field_map: dict[str, Any],
        flatten_linked_records: bool,
    ) -> dict[str, Any]:
        """Build export row dict, flattening linked records if enabled.

        Args:
            db: Database session
            data: Record data dict
            fields: List of table fields
            linked_field_map: Mapping of expanded field names to field info
            flatten_linked_records: Whether to flatten linked records

        Returns:
            Row dict with field names as keys

        """
        row = {}

        if not flatten_linked_records:
            # Simple case: just map field IDs to field names
            for field in fields:
                field_id = str(field.id)
                value = data.get(field_id, "")
                # Convert complex values to strings
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                row[field.name] = value
        else:
            # Flattening enabled: handle linked records specially
            for field in fields:
                field_id = str(field.id)
                value = data.get(field_id, "")

                if field.field_type == "linked_record" and linked_field_map:
                    # Fetch linked record data and expand it
                    linked_records = await self._get_linked_records_data(
                        db, value, field, linked_field_map, field.name
                    )

                    # Add expanded fields to row
                    row.update(linked_records)
                else:
                    # Non-linked field: just add the value
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    row[field.name] = value

        return row

    async def _get_linked_records_data(
        self,
        db: AsyncSession,
        linked_record_ids: Any,
        field: Field,
        linked_field_map: dict[str, Any],
        field_name: str,
    ) -> dict[str, Any]:
        """Fetch and flatten linked record data.

        Args:
            db: Database session
            linked_record_ids: List or dict of linked record IDs
            field: The linked record field
            linked_field_map: Mapping of expanded field names
            field_name: Name of the linked record field

        Returns:
            Dict of flattened linked record data

        """
        result = {}

        # Parse linked record IDs
        if isinstance(linked_record_ids, str):
            try:
                linked_record_ids = json.loads(linked_record_ids)
            except (json.JSONDecodeError, TypeError):
                linked_record_ids = []

        if not linked_record_ids:
            linked_record_ids = []

        # Ensure it's a list
        if isinstance(linked_record_ids, dict):
            linked_record_ids = list(linked_record_ids.keys())
        elif not isinstance(linked_record_ids, list):
            linked_record_ids = [linked_record_ids] if linked_record_ids else []

        if not linked_record_ids:
            # No linked records, return empty values for all expanded fields
            for expanded_name, field_info in linked_field_map.items():
                if expanded_name.startswith(f"{field_name}."):
                    result[expanded_name] = ""
            return result

        # Get the first linked record (for single value exports)
        # For multiple linked records, we could concatenate or create multiple rows
        # For now, just use the first one
        record_id = str(linked_record_ids[0]) if linked_record_ids else None

        if not record_id:
            for expanded_name in linked_field_map.keys():
                if expanded_name.startswith(f"{field_name}."):
                    result[expanded_name] = ""
            return result

        # Find the linked table ID from field map
        linked_table_id = None
        for field_info in linked_field_map.values():
            if field_info["field"].id == field.id:
                linked_table_id = field_info["linked_table_id"]
                break

        if not linked_table_id:
            return result

        # Fetch the linked record
        query = (
            select(Record)
            .where(Record.table_id == str(linked_table_id))
            .where(Record.id == record_id)
            .where(Record.deleted_at.is_(None))
        )
        record_result = await db.execute(query)
        linked_record = record_result.scalar_one_or_none()

        if not linked_record:
            # Record not found, return empty values
            for expanded_name in linked_field_map.keys():
                if expanded_name.startswith(f"{field_name}."):
                    result[expanded_name] = ""
            return result

        # Parse linked record data
        try:
            linked_data = (
                json.loads(linked_record.data)
                if isinstance(linked_record.data, str)
                else linked_record.data
            )
        except (json.JSONDecodeError, TypeError):
            linked_data = {}

        # Map linked record fields to expanded field names
        for expanded_name, field_info in linked_field_map.items():
            if expanded_name.startswith(f"{field_name}."):
                linked_field = field_info["linked_field"]
                linked_field_id = str(linked_field.id)
                value = linked_data.get(linked_field_id, "")

                # Convert complex values to strings
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)

                result[expanded_name] = value

        return result

    async def _get_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> Workspace:
        """Get workspace by ID.

        Args:
            db: Database session
            workspace_id: Workspace ID

        Returns:
            Workspace

        """
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or workspace.is_deleted:
            raise NotFoundError("Workspace not found")
        return workspace

    async def _get_workspace_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> Optional[WorkspaceMember]:
        """Get workspace member.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID

        Returns:
            WorkspaceMember or None

        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_base(
        self,
        db: AsyncSession,
        base_id: str,
    ) -> Base:
        """Get base by ID.

        Args:
            db: Database session
            base_id: Base ID

        Returns:
            Base

        """
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")
        return base

    async def _get_table_fields(
        self,
        db: AsyncSession,
        table_id: str,
    ) -> list[Field]:
        """Get all fields for a table.

        Args:
            db: Database session
            table_id: Table ID

        Returns:
            List of Field objects

        """
        query = select(Field).where(
            Field.table_id == table_id,
            Field.deleted_at.is_(None),
        )
        query = query.order_by(Field.created_at)
        result = await db.execute(query)
        return list(result.scalars().all())
