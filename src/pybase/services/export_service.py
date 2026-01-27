"""Export service for streaming large datasets."""

import csv
import hashlib
import io
import json
import os
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
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
        view_id: Optional[UUID] = None,
        include_attachments: bool = False,
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
            view_id: Optional view ID to apply filters and sorts from.
            include_attachments: If True, include attachment files in export (as ZIP for non-JSON formats).

        Yields:
            Chunks of export data as bytes

        Raises:
            NotFoundError: If table or view not found
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

        # Get view filters and sorts if view_id is provided
        view_filters = None
        view_sorts = None
        if view_id is not None:
            from pybase.models.view import View

            view = await db.get(View, str(view_id))
            if not view or view.is_deleted:
                raise NotFoundError("View not found")

            # Verify view belongs to the table
            if view.table_id != str(table_id):
                raise NotFoundError("View does not belong to this table")

            # Get filters and sorts from view
            view_filters = view.get_filters_list()
            view_sorts = view.get_sorts_list()

        if format.lower() == "csv":
            async for chunk in self._stream_csv(
                db, table_id, fields, batch_size, flatten_linked_records, view_filters, view_sorts, include_attachments
            ):
                yield chunk
        elif format.lower() == "json":
            async for chunk in self._stream_json(
                db, table_id, fields, batch_size, flatten_linked_records, view_filters, view_sorts, include_attachments
            ):
                yield chunk
        elif format.lower() in ("xlsx", "excel"):
            async for chunk in self._stream_excel(
                db, table_id, fields, batch_size, flatten_linked_records, view_filters, view_sorts, include_attachments
            ):
                yield chunk
        elif format.lower() == "xml":
            async for chunk in self._stream_xml(
                db, table_id, fields, batch_size, flatten_linked_records, view_filters, view_sorts, include_attachments
            ):
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
        view_filters: Optional[list[dict]] = None,
        view_sorts: Optional[list[dict]] = None,
        include_attachments: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as CSV.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records
            flatten_linked_records: If True, fetch and embed linked record data.
            view_filters: Optional filters from view to apply.
            view_sorts: Optional sorts from view to apply.
            include_attachments: If True, include attachment files in export.

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

        # Fetch all records and apply view filters/sorts if provided
        records_data = await self._fetch_and_filter_records(
            db, table_id, view_filters, view_sorts
        )

        # Stream records in batches
        offset = 0
        while offset < len(records_data):
            batch = records_data[offset : offset + batch_size]

            # Write records to CSV
            for record_dict in batch:
                data = record_dict.get("data", {})

                row = await self._build_export_row(
                    db, data, fields, linked_field_map, flatten_linked_records
                )

                writer.writerow(row)
                csv_data = output.getvalue()
                if csv_data:
                    yield csv_data.encode("utf-8")
                    output.seek(0)
                    output.truncate(0)

            offset += len(batch)

    async def _stream_json(
        self,
        db: AsyncSession,
        table_id: UUID,
        fields: list[Field],
        batch_size: int,
        flatten_linked_records: bool = False,
        view_filters: Optional[list[dict]] = None,
        view_sorts: Optional[list[dict]] = None,
        include_attachments: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as JSON array.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records
            flatten_linked_records: If True, fetch and embed linked record data.
            view_filters: Optional filters from view to apply.
            view_sorts: Optional sorts from view to apply.
            include_attachments: If True, include attachment files in export.

        Yields:
            JSON data chunks as bytes

        """
        # Start JSON array
        yield b"["

        # Build field name map for flattening
        _, linked_field_map = await self._build_export_field_names(
            db, fields, flatten_linked_records
        )

        # Fetch all records and apply view filters/sorts if provided
        records_data = await self._fetch_and_filter_records(
            db, table_id, view_filters, view_sorts
        )

        first_record = True
        offset = 0

        while offset < len(records_data):
            batch = records_data[offset : offset + batch_size]

            # Convert records to JSON
            for record_dict in batch:
                data = record_dict.get("data", {})

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

            offset += len(batch)

        # End JSON array
        yield b"]"

    async def _stream_excel(
        self,
        db: AsyncSession,
        table_id: UUID,
        fields: list[Field],
        batch_size: int,
        flatten_linked_records: bool = False,
        view_filters: Optional[list[dict]] = None,
        view_sorts: Optional[list[dict]] = None,
        include_attachments: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as Excel (.xlsx) file.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records
            flatten_linked_records: If True, fetch and embed linked record data.
            view_filters: Optional filters from view to apply.
            view_sorts: Optional sorts from view to apply.
            include_attachments: If True, include attachment files in export.

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

        # Fetch all records and apply view filters/sorts if provided
        records_data = await self._fetch_and_filter_records(
            db, table_id, view_filters, view_sorts
        )

        # Write all records to worksheet
        for record_dict in records_data:
            data = record_dict.get("data", {})

            row_dict = await self._build_export_row(
                db, data, fields, linked_field_map, flatten_linked_records
            )

            row = [row_dict.get(field_name, "") for field_name in field_names]
            worksheet.append(row)

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
        view_filters: Optional[list[dict]] = None,
        view_sorts: Optional[list[dict]] = None,
        include_attachments: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """Stream records as XML.

        Args:
            db: Database session
            table_id: Table ID
            fields: List of table fields
            batch_size: Batch size for fetching records
            flatten_linked_records: If True, fetch and embed linked record data.
            view_filters: Optional filters from view to apply.
            view_sorts: Optional sorts from view to apply.
            include_attachments: If True, include attachment files in export.

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

        # Fetch all records and apply view filters/sorts if provided
        records_data = await self._fetch_and_filter_records(
            db, table_id, view_filters, view_sorts
        )

        # Stream records in batches
        offset = 0
        while offset < len(records_data):
            batch = records_data[offset : offset + batch_size]

            # Write records to XML
            for record_dict in batch:
                data = record_dict.get("data", {})

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

            offset += len(batch)

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

    async def _fetch_and_filter_records(
        self,
        db: AsyncSession,
        table_id: UUID,
        view_filters: Optional[list[dict]] = None,
        view_sorts: Optional[list[dict]] = None,
    ) -> list[dict[str, Any]]:
        """Fetch all records and apply view filters and sorts.

        Args:
            db: Database session
            table_id: Table ID
            view_filters: Optional filters from view to apply.
            view_sorts: Optional sorts from view to apply.

        Returns:
            List of record dicts with applied filters and sorts

        """
        # Fetch all records from the table
        query = select(Record).where(
            Record.table_id == str(table_id),
            Record.deleted_at.is_(None),
        )
        result = await db.execute(query)
        records = result.scalars().all()

        # Convert records to dict format
        records_data = []
        for record in records:
            try:
                data = json.loads(record.data) if isinstance(record.data, str) else record.data
            except (json.JSONDecodeError, TypeError):
                data = {}

            record_dict = {
                "id": str(record.id),
                "table_id": str(record.table_id),
                "data": data,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }
            records_data.append(record_dict)

        # Apply view filters if provided
        if view_filters:
            records_data = self._apply_filters(records_data, view_filters)

        # Apply view sorts if provided
        if view_sorts:
            records_data = self._apply_sorts(records_data, view_sorts)

        return records_data

    def _apply_filters(
        self,
        records: list[dict[str, Any]],
        filters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply filters to records.

        Args:
            records: List of record dicts
            filters: List of filter conditions

        Returns:
            Filtered records

        """
        if not filters:
            return records

        filtered_records = []
        for record in records:
            if self._record_matches_filters(record, filters):
                filtered_records.append(record)

        return filtered_records

    def _record_matches_filters(
        self,
        record: dict[str, Any],
        filters: list[dict[str, Any]],
    ) -> bool:
        """Check if a record matches all filter conditions.

        Args:
            record: Record dict
            filters: List of filter conditions

        Returns:
            True if record matches filters

        """
        and_conditions = []
        or_conditions = []

        for filter_cond in filters:
            field_id = str(filter_cond.get("field_id", ""))
            operator = filter_cond.get("operator", "")
            value = filter_cond.get("value")
            conjunction = filter_cond.get("conjunction", "and")

            # Get field value from record
            field_value = record.get("data", {}).get(field_id)

            # Evaluate condition
            matches = self._evaluate_filter(field_value, operator, value)

            if conjunction == "or":
                or_conditions.append(matches)
            else:
                and_conditions.append(matches)

        # All AND conditions must be true
        all_ands = all(and_conditions) if and_conditions else True
        # At least one OR condition must be true (if any OR conditions exist)
        any_ors = any(or_conditions) if or_conditions else True

        return all_ands and (any_ors if or_conditions else True)

    def _evaluate_filter(
        self,
        field_value: Any,
        operator: str,
        filter_value: Any,
    ) -> bool:
        """Evaluate a single filter condition.

        Args:
            field_value: Value from record
            operator: Filter operator
            filter_value: Value to compare against

        Returns:
            True if condition matches

        """
        if operator == "equals":
            return field_value == filter_value
        elif operator == "not_equals":
            return field_value != filter_value
        elif operator == "contains":
            return filter_value in str(field_value) if field_value else False
        elif operator == "not_contains":
            return filter_value not in str(field_value) if field_value else True
        elif operator == "is_empty":
            return field_value is None or field_value == "" or field_value == []
        elif operator == "is_not_empty":
            return field_value is not None and field_value != "" and field_value != []
        elif operator == "gt":
            return field_value > filter_value if field_value is not None else False
        elif operator == "lt":
            return field_value < filter_value if field_value is not None else False
        elif operator == "gte":
            return field_value >= filter_value if field_value is not None else False
        elif operator == "lte":
            return field_value <= filter_value if field_value is not None else False
        elif operator == "in":
            return field_value in filter_value if filter_value else False
        elif operator == "not_in":
            return field_value not in filter_value if filter_value else True
        elif operator == "starts_with":
            return str(field_value).startswith(str(filter_value)) if field_value else False
        elif operator == "ends_with":
            return str(field_value).endswith(str(filter_value)) if field_value else False
        else:
            # Unsupported operator, default to True
            return True

    def _apply_sorts(
        self,
        records: list[dict[str, Any]],
        sorts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply sort rules to records.

        Args:
            records: List of record dicts
            sorts: List of sort rules

        Returns:
            Sorted records

        """
        if not sorts:
            return records

        # Apply sorts in reverse order (last sort first) for stable multi-column sorting
        for sort_rule in reversed(sorts):
            field_id = str(sort_rule.get("field_id", ""))
            direction = sort_rule.get("direction", "asc")

            reverse = direction == "desc"

            def sort_key(record: dict[str, Any]) -> tuple[int, Any]:
                """Generate sort key handling None/missing values and type consistency.

                Returns tuple of (is_none, value) where:
                - is_none: 0 for non-None values, 1 for None/missing (sorts to end)
                - value: the actual value for comparison

                """
                value = record.get("data", {}).get(field_id)

                # Handle None or missing values - sort to end
                if value is None or value == "":
                    return (1, "")

                # Return (0, value) for non-None values to sort them first
                return (0, value)

            records = sorted(records, key=sort_key, reverse=reverse)

        return records

    # ==========================================================================
    # Attachment Export Methods
    # ==========================================================================

    async def create_attachments_zip(
        self,
        db: AsyncSession,
        table_id: UUID,
        user_id: str,
        field_ids: Optional[list[UUID]] = None,
        view_id: Optional[UUID] = None,
        view_filters: Optional[list[dict]] = None,
        view_sorts: Optional[list[dict]] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Create ZIP archive of all attachments from table records.

        Args:
            db: Database session
            table_id: Table ID to export attachments from
            user_id: User ID requesting export
            field_ids: Optional list of field IDs to export. If None, exports all attachment fields.
            view_id: Optional view ID to apply filters from.
            view_filters: Optional filters from view to apply.
            view_sorts: Optional sorts from view to apply.

        Yields:
            Chunks of ZIP file data as bytes

        Raises:
            NotFoundError: If table or view not found
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

        # Get table fields
        fields = await self._get_table_fields(db, str(table_id))

        # Filter to only attachment fields
        attachment_fields = [f for f in fields if f.field_type == "attachment"]

        if not attachment_fields:
            # No attachment fields, yield empty ZIP
            yield self._create_empty_zip()
            return

        # Filter fields if field_ids is provided
        if field_ids is not None:
            field_ids_str = {str(fid) for fid in field_ids}
            attachment_fields = [f for f in attachment_fields if str(f.id) in field_ids_str]

        if not attachment_fields:
            yield self._create_empty_zip()
            return

        # Fetch all records with filters/sorts
        records_data = await self._fetch_and_filter_records(
            db, table_id, view_filters, view_sorts
        )

        # Extract all attachments
        attachments = await self._extract_attachments_from_records(
            records_data, attachment_fields
        )

        if not attachments:
            yield self._create_empty_zip()
            return

        # Create ZIP and yield chunks
        async for chunk in self._create_zip_stream(attachments):
            yield chunk

    async def _extract_attachments_from_records(
        self,
        records: list[dict[str, Any]],
        attachment_fields: list[Field],
    ) -> list[dict[str, Any]]:
        """Extract all attachments from records.

        Args:
            records: List of record dicts
            attachment_fields: List of attachment field objects

        Returns:
            List of attachment dicts with metadata

        """
        attachments = []
        field_map = {str(f.id): f for f in attachment_fields}

        for record in records:
            record_id = record.get("id", "unknown")
            data = record.get("data", {})

            for field_id, field in field_map.items():
                field_name = field.name
                value = data.get(field_id)

                if not value:
                    continue

                # Normalize to list
                if isinstance(value, dict):
                    value = [value]
                elif not isinstance(value, list):
                    continue

                # Extract each attachment
                for attachment in value:
                    if not isinstance(attachment, dict):
                        continue

                    url = attachment.get("url")
                    filename = attachment.get("filename", "unnamed")
                    attachment_id = attachment.get("id", "unknown")

                    if not url:
                        continue

                    attachments.append({
                        "record_id": record_id,
                        "field_name": field_name,
                        "attachment_id": attachment_id,
                        "filename": filename,
                        "url": url,
                        "size": attachment.get("size", 0),
                        "mime_type": attachment.get("mime_type", ""),
                    })

        return attachments

    async def _create_zip_stream(
        self,
        attachments: list[dict[str, Any]],
    ) -> AsyncGenerator[bytes, None]:
        """Create ZIP archive stream from attachments.

        Args:
            attachments: List of attachment dicts with metadata

        Yields:
            ZIP file data chunks as bytes

        """
        # Create in-memory ZIP
        zip_buffer = BytesIO()

        with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zip_file:
            # Download attachments and add to ZIP
            with ThreadPoolExecutor(max_workers=5) as executor:
                for attachment in attachments:
                    try:
                        # Download file content
                        content = await self._download_attachment(attachment["url"])

                        if content:
                            # Create safe filename path: record_id/field_name/filename
                            safe_record_id = self._sanitize_filename(attachment["record_id"])
                            safe_field_name = self._sanitize_filename(attachment["field_name"])
                            safe_filename = self._sanitize_filename(attachment["filename"])

                            zip_path = f"{safe_record_id}/{safe_field_name}/{safe_filename}"

                            # Write to ZIP
                            zip_file.writestr(zip_path, content)

                    except Exception as e:
                        # Log error but continue with other attachments
                        pass

        # Get ZIP data
        zip_data = zip_buffer.getvalue()
        zip_buffer.close()

        # Yield in chunks
        chunk_size = 8192
        for i in range(0, len(zip_data), chunk_size):
            yield zip_data[i : i + chunk_size]

    async def _download_attachment(self, url: str) -> Optional[bytes]:
        """Download attachment file from URL.

        Args:
            url: URL to download from

        Returns:
            File content as bytes, or None if failed

        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except Exception as e:
            return None

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe ZIP entry path.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename

        """
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")

        # Remove control characters
        filename = "".join(c for c in filename if ord(c) >= 32)

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[: 255 - len(ext)] + ext

        return filename

    def _create_empty_zip(self) -> bytes:
        """Create an empty ZIP file.

        Returns:
            Empty ZIP file as bytes

        """
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zip_file:
            # Add README
            zip_file.writestr(
                "README.txt",
                "This export contains no attachments or the attachment fields were empty.\n"
            )
        return zip_buffer.getvalue()
