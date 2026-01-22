"""Extraction service for preview/import logic."""

import json
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


class ExtractionService:
    """Service for extraction preview and import operations."""

    async def preview_import(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        extracted_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Preview how extracted data will map to table fields.

        Analyzes extracted data structure and suggests field mappings
        to existing table columns.

        Args:
            db: Database session
            user_id: User ID requesting preview
            table_id: Target table ID
            extracted_data: Extracted data from CAD/PDF file

        Returns:
            Dict containing:
                - source_fields: Fields available in extracted data
                - target_fields: Fields in target table
                - suggested_mapping: Auto-suggested field mapping
                - sample_data: Sample rows to preview
                - total_records: Total records to import

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table

        """
        # Verify table exists and user has access
        table = await self._get_table_with_access(db, table_id, user_id)

        # Get table fields
        target_fields = await self._get_table_fields(db, table_id)

        # Extract source fields from data
        source_fields = self._extract_source_fields(extracted_data)

        # Suggest field mappings based on name similarity and type compatibility
        suggested_mapping = self._suggest_field_mapping(
            source_fields, target_fields, extracted_data
        )

        # Prepare sample data (first 5 rows)
        sample_data = self._prepare_sample_data(extracted_data, limit=5)

        # Count total records
        total_records = self._count_records(extracted_data)

        return {
            "source_fields": source_fields,
            "target_fields": [
                {
                    "id": str(f.id),
                    "name": f.name,
                    "type": f.type,
                    "description": f.description,
                }
                for f in target_fields
            ],
            "suggested_mapping": suggested_mapping,
            "sample_data": sample_data,
            "total_records": total_records,
        }

    async def import_data(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        extracted_data: dict[str, Any],
        field_mapping: dict[str, str],
        create_missing_fields: bool = False,
        skip_errors: bool = True,
    ) -> dict[str, Any]:
        """
        Import extracted data into a table.

        Creates records based on field mapping, optionally creating
        missing fields and handling errors gracefully.

        Args:
            db: Database session
            user_id: User ID performing import
            table_id: Target table ID
            extracted_data: Extracted data from CAD/PDF file
            field_mapping: Mapping of source fields to target field IDs
            create_missing_fields: Whether to create fields that don't exist
            skip_errors: Continue import on row errors

        Returns:
            Dict containing:
                - success: Overall success status
                - records_imported: Number of records created
                - records_failed: Number of failed records
                - errors: List of error details
                - created_field_ids: IDs of newly created fields

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have permission
            ConflictError: If field mapping is invalid

        """
        # Verify table exists and user has edit access
        table = await self._get_table_with_access(db, table_id, user_id)
        await self._verify_edit_permission(db, table, user_id)

        # Validate field mapping
        await self._validate_field_mapping(db, table_id, field_mapping)

        # Create missing fields if requested
        created_field_ids = []
        if create_missing_fields:
            created_field_ids = await self._create_missing_fields(
                db, table_id, extracted_data, field_mapping
            )

        # Import records
        records_imported = 0
        records_failed = 0
        errors = []

        rows = self._extract_rows(extracted_data)

        for idx, row_data in enumerate(rows):
            try:
                # Transform row data according to field mapping
                record_data = self._transform_row_data(row_data, field_mapping)

                # Create record
                record = Record(
                    table_id=table_id,
                    data=json.dumps(record_data),
                    created_by_id=user_id,
                    last_modified_by_id=user_id,
                    row_height=32,
                )
                db.add(record)
                records_imported += 1

            except Exception as e:
                records_failed += 1
                errors.append(
                    {
                        "row_index": idx,
                        "error": str(e),
                        "row_data": row_data,
                    }
                )
                if not skip_errors:
                    await db.rollback()
                    raise ConflictError(f"Failed to import row {idx}: {str(e)}")

        # Commit all records
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise ConflictError(f"Failed to commit import: {str(e)}")

        return {
            "success": records_failed == 0 or skip_errors,
            "records_imported": records_imported,
            "records_failed": records_failed,
            "errors": errors,
            "created_field_ids": created_field_ids,
        }

    # --- Helper Methods ---

    async def _get_table_with_access(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
    ) -> Table:
        """Get table and verify user has access."""
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check workspace access
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        return table

    async def _verify_edit_permission(
        self,
        db: AsyncSession,
        table: Table,
        user_id: str,
    ) -> None:
        """Verify user has edit permission."""
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), user_id)

        if not member or member.role not in [
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.EDITOR,
        ]:
            raise PermissionDeniedError(
                "Only owners, admins, and editors can import data"
            )

    async def _get_base(self, db: AsyncSession, base_id: str) -> Base:
        """Get base by ID."""
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")
        return base

    async def _get_workspace(self, db: AsyncSession, workspace_id: str) -> Workspace:
        """Get workspace by ID."""
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
        """Get workspace member."""
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_table_fields(
        self,
        db: AsyncSession,
        table_id: str,
    ) -> list[Field]:
        """Get all fields for a table."""
        query = (
            select(Field)
            .where(
                Field.table_id == table_id,
                Field.is_deleted.is_(False),
            )
            .order_by(Field.position)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    def _extract_source_fields(self, extracted_data: dict[str, Any]) -> list[str]:
        """Extract field names from extracted data."""
        source_fields = []

        # Handle different extraction formats
        if "tables" in extracted_data and extracted_data["tables"]:
            # PDF/CAD table extraction
            first_table = extracted_data["tables"][0]
            if "headers" in first_table:
                source_fields = first_table["headers"]

        elif "dimensions" in extracted_data:
            # Dimension extraction
            source_fields = ["dimension_value", "dimension_unit", "dimension_type"]

        elif "entities" in extracted_data:
            # IFC/STEP entity extraction
            if extracted_data["entities"]:
                first_entity = extracted_data["entities"][0]
                source_fields = list(first_entity.keys())

        return source_fields

    def _suggest_field_mapping(
        self,
        source_fields: list[str],
        target_fields: list[Field],
        extracted_data: dict[str, Any],
    ) -> dict[str, str]:
        """Suggest field mapping based on name similarity and type compatibility."""
        suggested_mapping = {}

        for source_field in source_fields:
            source_lower = source_field.lower().replace("_", " ").replace("-", " ")

            # Find best match in target fields
            best_match = None
            best_score = 0.0

            for target_field in target_fields:
                target_lower = target_field.name.lower()

                # Simple similarity score (exact match > contains > starts with)
                score = 0.0
                if source_lower == target_lower:
                    score = 1.0
                elif source_lower in target_lower or target_lower in source_lower:
                    score = 0.7
                elif target_lower.startswith(source_lower) or source_lower.startswith(
                    target_lower
                ):
                    score = 0.5

                if score > best_score:
                    best_score = score
                    best_match = target_field

            # Only suggest if confidence is high enough
            if best_match and best_score >= 0.5:
                suggested_mapping[source_field] = str(best_match.id)

        return suggested_mapping

    def _prepare_sample_data(
        self,
        extracted_data: dict[str, Any],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Prepare sample data for preview."""
        sample_data = []

        rows = self._extract_rows(extracted_data)
        for row in rows[:limit]:
            sample_data.append(row)

        return sample_data

    def _count_records(self, extracted_data: dict[str, Any]) -> int:
        """Count total records in extracted data."""
        rows = self._extract_rows(extracted_data)
        return len(rows)

    def _extract_rows(self, extracted_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract rows from various extraction formats."""
        rows = []

        # Handle table extraction
        if "tables" in extracted_data and extracted_data["tables"]:
            for table in extracted_data["tables"]:
                if "rows" in table and "headers" in table:
                    headers = table["headers"]
                    for row_values in table["rows"]:
                        row_dict = {}
                        for idx, header in enumerate(headers):
                            if idx < len(row_values):
                                row_dict[header] = row_values[idx]
                        rows.append(row_dict)

        # Handle dimension extraction
        elif "dimensions" in extracted_data:
            for dim in extracted_data["dimensions"]:
                rows.append(
                    {
                        "dimension_value": dim.get("value"),
                        "dimension_unit": dim.get("unit", "mm"),
                        "dimension_type": dim.get("dimension_type", "linear"),
                        "label": dim.get("label"),
                    }
                )

        # Handle entity extraction (IFC/STEP)
        elif "entities" in extracted_data:
            rows = extracted_data["entities"]

        return rows

    async def _validate_field_mapping(
        self,
        db: AsyncSession,
        table_id: str,
        field_mapping: dict[str, str],
    ) -> None:
        """Validate that all mapped field IDs exist in the table."""
        for source_field, target_field_id in field_mapping.items():
            field = await db.get(Field, target_field_id)
            if not field or field.is_deleted:
                raise NotFoundError(f"Field {target_field_id} not found")
            if str(field.table_id) != table_id:
                raise ConflictError(
                    f"Field {target_field_id} does not belong to table {table_id}"
                )

    async def _create_missing_fields(
        self,
        db: AsyncSession,
        table_id: str,
        extracted_data: dict[str, Any],
        field_mapping: dict[str, str],
    ) -> list[str]:
        """Create fields that are in source data but not mapped."""
        created_field_ids = []

        source_fields = self._extract_source_fields(extracted_data)
        mapped_sources = set(field_mapping.keys())
        unmapped_fields = [f for f in source_fields if f not in mapped_sources]

        # Get current max position
        existing_fields = await self._get_table_fields(db, table_id)
        max_position = max([f.position for f in existing_fields], default=0)

        for idx, field_name in enumerate(unmapped_fields):
            # Infer field type from data
            field_type = self._infer_field_type(extracted_data, field_name)

            # Create field
            new_field = Field(
                table_id=table_id,
                name=field_name,
                type=field_type,
                description=f"Auto-created from extraction",
                position=max_position + idx + 1,
                config={},
            )
            db.add(new_field)
            await db.flush()
            created_field_ids.append(str(new_field.id))

            # Add to field mapping
            field_mapping[field_name] = str(new_field.id)

        return created_field_ids

    def _infer_field_type(
        self,
        extracted_data: dict[str, Any],
        field_name: str,
    ) -> FieldType:
        """Infer field type from sample data."""
        # Default to text
        field_type = FieldType.TEXT

        # Check field name patterns
        field_lower = field_name.lower()
        if "dimension" in field_lower or "size" in field_lower:
            field_type = FieldType.DIMENSION
        elif "date" in field_lower:
            field_type = FieldType.DATE
        elif "number" in field_lower or "qty" in field_lower or "count" in field_lower:
            field_type = FieldType.NUMBER
        elif "url" in field_lower or "link" in field_lower:
            field_type = FieldType.URL
        elif "email" in field_lower:
            field_type = FieldType.EMAIL

        return field_type

    def _transform_row_data(
        self,
        row_data: dict[str, Any],
        field_mapping: dict[str, str],
    ) -> dict[str, Any]:
        """Transform row data according to field mapping."""
        transformed = {}

        for source_field, target_field_id in field_mapping.items():
            if source_field in row_data:
                transformed[target_field_id] = row_data[source_field]

        return transformed
