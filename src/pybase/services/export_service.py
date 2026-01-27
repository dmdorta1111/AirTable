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
    ) -> AsyncGenerator[bytes, None]:
        """Stream export of records from a table.

        Args:
            db: Database session
            table_id: Table ID to export from
            user_id: User ID requesting export
            format: Export format ('csv', 'json', 'xlsx', or 'xml')
            batch_size: Number of records to fetch per batch
            field_ids: Optional list of field IDs to export. If None, exports all fields.

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
            async for chunk in self._stream_csv(db, table_id, fields, batch_size):
                yield chunk
        elif format.lower() == "json":
            async for chunk in self._stream_json(db, table_id, fields, batch_size):
                yield chunk
        elif format.lower() in ("xlsx", "excel"):
            async for chunk in self._stream_excel(db, table_id, fields, batch_size):
                yield chunk
        elif format.lower() == "xml":
            async for chunk in self._stream_xml(db, table_id, fields, batch_size):
                yield chunk
        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def _stream_csv(
        self,
        db: AsyncSession,
        table_id: UUID,
        fields: list[Field],
        batch_size: int,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as CSV.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records

        Yields:
            CSV data chunks as bytes

        """
        output = StringIO()
        field_names = [f.name for f in fields]

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

                row = {}
                for field in fields:
                    field_id = str(field.id)
                    value = data.get(field_id, "")
                    # Convert complex values to strings
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    row[field.name] = value

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
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as JSON array.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records

        Yields:
            JSON data chunks as bytes

        """
        # Start JSON array
        yield b"["

        first_record = True
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

            # Convert records to JSON
            for record in records:
                try:
                    data = json.loads(record.data) if isinstance(record.data, str) else record.data
                except (json.JSONDecodeError, TypeError):
                    data = {}

                # Build record object with field names
                record_obj = {}
                for field in fields:
                    field_id = str(field.id)
                    record_obj[field.name] = data.get(field_id)

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
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as Excel (.xlsx) file.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records

        Yields:
            Excel file data as bytes

        """
        # Create workbook and worksheet
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Export"

        # Write headers
        field_names = [f.name for f in fields]
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

                row = []
                for field in fields:
                    field_id = str(field.id)
                    value = data.get(field_id, "")
                    # Convert complex values to strings
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    row.append(value)

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
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as XML.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records

        Yields:
            XML data chunks as bytes

        """
        # Create root element
        root = ET.Element("records")

        # Start XML document
        yield b'<?xml version="1.0" encoding="UTF-8"?>\n'
        yield b"<records>\n"

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

                # Create record element
                record_elem = ET.Element("record")

                # Add fields as child elements
                for field in fields:
                    field_id = str(field.id)
                    value = data.get(field_id, "")

                    # Create field element
                    field_elem = ET.Element(field.name)

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
