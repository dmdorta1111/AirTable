"""Import service for business logic."""

import json
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.extraction import ImportRequest, ImportResponse
from pybase.schemas.field import FieldCreate
from pybase.schemas.record import RecordCreate
from pybase.services.field import FieldService
from pybase.services.record import RecordService


class ImportService:
    """Service for import operations."""

    def __init__(self) -> None:
        """Initialize import service with dependent services."""
        self.field_service = FieldService()
        self.record_service = RecordService()

    async def import_records(
        self,
        db: AsyncSession,
        user_id: str,
        import_data: ImportRequest,
        extraction_result: dict[str, Any],
    ) -> ImportResponse:
        """Import extracted data into a table.

        Args:
            db: Database session
            user_id: User ID performing import
            import_data: Import request parameters
            extraction_result: Extraction result data

        Returns:
            Import response with success/failure counts

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If field mapping is invalid

        """
        # Check if table exists
        table = await db.get(Table, str(import_data.table_id))
        if not table or table.is_deleted:
            raise NotFoundError("Table", str(import_data.table_id))

        # Check if user has access to workspace
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        # Check if user has edit permission
        if member.role not in [
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.EDITOR,
        ]:
            raise PermissionDeniedError("Only owners, admins, and editors can import records")

        # Create missing fields if requested
        created_field_ids = []
        if import_data.create_missing_fields:
            created_field_ids = await self._create_missing_fields(
                db,
                user_id,
                str(import_data.table_id),
                import_data.field_mapping,
                extraction_result,
            )

        # Validate field mapping (after creating missing fields)
        await self._validate_field_mapping(
            db,
            str(import_data.table_id),
            import_data.field_mapping,
        )

        # Parse extraction result into records
        records_data = self._parse_extraction_result(extraction_result)

        # Import records in batch
        records_imported = 0
        records_failed = 0
        errors = []

        for idx, record_data in enumerate(records_data):
            try:
                # Map source fields to target fields
                mapped_data = self._map_record_data(
                    record_data,
                    import_data.field_mapping,
                )

                # Create record
                record_create = RecordCreate(
                    table_id=str(import_data.table_id),
                    data=mapped_data,
                )
                await self.record_service.create_record(
                    db,
                    user_id,
                    record_create,
                )
                records_imported += 1

            except Exception as e:
                records_failed += 1
                errors.append({
                    "row": idx + 1,
                    "data": record_data,
                    "error": str(e),
                })

                if not import_data.skip_errors:
                    # Rollback and raise if not skipping errors
                    await db.rollback()
                    raise ValidationError(
                        message=f"Import failed at row {idx + 1}: {str(e)}",
                        errors=errors,
                    )

        # Commit all successful imports
        await db.commit()

        return ImportResponse(
            success=records_failed == 0,
            records_imported=records_imported,
            records_failed=records_failed,
            errors=errors,
            created_field_ids=[UUID(fid) for fid in created_field_ids],
        )

    async def _validate_field_mapping(
        self,
        db: AsyncSession,
        table_id: str,
        field_mapping: dict[str, str],
    ) -> None:
        """Validate that all target fields exist in the table.

        Args:
            db: Database session
            table_id: Target table ID
            field_mapping: Mapping of source to target field IDs

        Raises:
            ValidationError: If any target field doesn't exist

        """
        # Get all fields for the table
        query = select(Field).where(
            Field.table_id == table_id,
            Field.deleted_at.is_(None),
        )
        result = await db.execute(query)
        table_fields = {str(field.id): field for field in result.scalars().all()}

        # Check that all mapped target fields exist
        invalid_fields = []
        for source_field, target_field_id in field_mapping.items():
            if target_field_id not in table_fields:
                invalid_fields.append({
                    "source_field": source_field,
                    "target_field_id": target_field_id,
                    "error": "Target field not found in table",
                })

        if invalid_fields:
            raise ValidationError(
                message="Invalid field mapping",
                errors=invalid_fields,
            )

    async def _create_missing_fields(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        field_mapping: dict[str, str],
        extraction_result: dict[str, Any],
    ) -> list[str]:
        """Create fields that don't exist in the target table.

        Args:
            db: Database session
            user_id: User ID creating fields
            table_id: Target table ID
            field_mapping: Field mapping
            extraction_result: Extraction result for type inference

        Returns:
            List of created field IDs

        """
        created_field_ids = []

        # Get existing fields
        query = select(Field).where(
            Field.table_id == table_id,
            Field.deleted_at.is_(None),
        )
        result = await db.execute(query)
        existing_field_ids = {str(field.id) for field in result.scalars().all()}

        # Find fields that need to be created
        for source_field, target_field_id in field_mapping.items():
            if target_field_id not in existing_field_ids:
                # Infer field type from extraction result
                field_type = self._infer_field_type(
                    source_field,
                    extraction_result,
                )

                # Create new field
                field_create = FieldCreate(
                    table_id=UUID(table_id),
                    name=source_field,
                    field_type=field_type,
                    description=f"Auto-created from import",
                )

                field = await self.field_service.create_field(
                    db,
                    user_id,
                    field_create,
                )
                created_field_ids.append(str(field.id))

                # Update mapping with actual field ID
                field_mapping[source_field] = str(field.id)

        return created_field_ids

    def _infer_field_type(
        self,
        field_name: str,
        extraction_result: dict[str, Any],
    ) -> FieldType:
        """Infer field type from extraction result data.

        Args:
            field_name: Field name
            extraction_result: Extraction result

        Returns:
            Inferred field type

        """
        # Parse sample data to infer type
        records_data = self._parse_extraction_result(extraction_result)

        if not records_data:
            return FieldType.TEXT

        # Get first non-null value for this field
        sample_value = None
        for record in records_data:
            if field_name in record and record[field_name] is not None:
                sample_value = record[field_name]
                break

        if sample_value is None:
            return FieldType.TEXT

        # Infer type from value
        if isinstance(sample_value, bool):
            return FieldType.CHECKBOX
        elif isinstance(sample_value, (int, float)):
            return FieldType.NUMBER
        elif isinstance(sample_value, str):
            # Check for special patterns
            if len(sample_value) > 500:
                return FieldType.LONG_TEXT
            return FieldType.TEXT
        else:
            return FieldType.TEXT

    def _parse_extraction_result(
        self,
        extraction_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Parse extraction result into list of record data.

        Args:
            extraction_result: Extraction result

        Returns:
            List of record data dictionaries

        """
        records_data = []

        # Handle different extraction formats
        if "tables" in extraction_result and extraction_result["tables"]:
            # PDF table extraction
            for table in extraction_result["tables"]:
                headers = table.get("headers", [])
                rows = table.get("rows", [])

                for row in rows:
                    record = {}
                    for idx, header in enumerate(headers):
                        if idx < len(row):
                            record[header] = row[idx]
                    records_data.append(record)

        elif "dimensions" in extraction_result and extraction_result["dimensions"]:
            # DXF/CAD dimensions
            for dim in extraction_result["dimensions"]:
                record = {
                    "value": dim.get("value"),
                    "unit": dim.get("unit", "mm"),
                    "tolerance_plus": dim.get("tolerance_plus"),
                    "tolerance_minus": dim.get("tolerance_minus"),
                    "dimension_type": dim.get("dimension_type", "linear"),
                    "label": dim.get("label"),
                }
                records_data.append(record)

        elif "entities" in extraction_result and extraction_result["entities"]:
            # Generic CAD entities
            records_data = extraction_result["entities"]

        elif "bom" in extraction_result and extraction_result["bom"]:
            # Bill of Materials
            bom = extraction_result["bom"]
            items = bom.get("items", [])
            records_data = items

        return records_data

    def _map_record_data(
        self,
        source_data: dict[str, Any],
        field_mapping: dict[str, str],
    ) -> dict[str, Any]:
        """Map source field names to target field IDs.

        Args:
            source_data: Source record data
            field_mapping: Field mapping

        Returns:
            Mapped record data

        """
        mapped_data = {}

        for source_field, target_field_id in field_mapping.items():
            if source_field in source_data:
                mapped_data[target_field_id] = source_data[source_field]

        return mapped_data

    async def _get_base(self, db: AsyncSession, base_id: str) -> Base:
        """Get base by ID.

        Args:
            db: Database session
            base_id: Base ID

        Returns:
            Base

        Raises:
            NotFoundError: If base not found

        """
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base", base_id)
        return base

    async def _get_workspace(self, db: AsyncSession, workspace_id: str) -> Workspace:
        """Get workspace by ID.

        Args:
            db: Database session
            workspace_id: Workspace ID

        Returns:
            Workspace

        Raises:
            NotFoundError: If workspace not found

        """
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or workspace.is_deleted:
            raise NotFoundError("Workspace", workspace_id)
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
            Workspace member or None if not found

        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.deleted_at.is_(None),
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
