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
        created_records = []

        # Validate and prepare all records first
        for idx, record_data in enumerate(records_data):
            try:
                # Map source fields to target fields
                mapped_data = self._map_record_data(
                    record_data,
                    import_data.field_mapping,
                )

                # Validate record data against fields
                await self._validate_record_data(
                    db,
                    str(import_data.table_id),
                    mapped_data,
                )

                # Create record object (don't commit yet)
                record = Record(
                    table_id=str(import_data.table_id),
                    data=json.dumps(mapped_data),
                    created_by_id=user_id,
                    last_modified_by_id=user_id,
                    row_height=32,
                )
                db.add(record)
                created_records.append(record)
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

        # Commit all successful imports in a single transaction
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

        Handles multiple extraction formats and can combine data from multiple sources
        in a single extraction result (e.g., both tables and dimensions from a PDF).

        Args:
            extraction_result: Extraction result

        Returns:
            List of record data dictionaries

        """
        records_data = []

        # Get source type to determine parsing strategy
        source_type = extraction_result.get("source_type", "")

        # Parse PDF table data (highest priority for structured data)
        if "tables" in extraction_result and extraction_result["tables"]:
            for table_idx, table in enumerate(extraction_result["tables"]):
                headers = table.get("headers", [])
                rows = table.get("rows", [])
                page = table.get("page")
                confidence = table.get("confidence", 1.0)

                for row_idx, row in enumerate(rows):
                    record = {}
                    # Map headers to row values
                    for idx, header in enumerate(headers):
                        if idx < len(row):
                            # Clean up None values
                            value = row[idx]
                            if value is not None:
                                record[header] = value

                    # Add metadata fields if available
                    if page is not None:
                        record["_page"] = page
                    if confidence < 1.0:
                        record["_confidence"] = confidence
                    record["_source_table"] = table_idx
                    record["_source_row"] = row_idx

                    if record:  # Only add non-empty records
                        records_data.append(record)

        # Parse Bill of Materials (structured part data)
        if "bom" in extraction_result and extraction_result["bom"]:
            bom = extraction_result["bom"]
            items = bom.get("items", [])
            headers = bom.get("headers", [])
            confidence = bom.get("confidence", 1.0)

            for item_idx, item in enumerate(items):
                record = dict(item)  # Copy item data
                if confidence < 1.0:
                    record["_confidence"] = confidence
                record["_source_type"] = "bom"
                record["_source_index"] = item_idx
                records_data.append(record)

        # Parse dimensions (for CAD/PDF drawings)
        if "dimensions" in extraction_result and extraction_result["dimensions"]:
            for dim_idx, dim in enumerate(extraction_result["dimensions"]):
                record = {
                    "dimension_value": dim.get("value"),
                    "unit": dim.get("unit", "mm"),
                    "dimension_type": dim.get("dimension_type", "linear"),
                }
                # Optional dimension fields
                if dim.get("tolerance_plus") is not None:
                    record["tolerance_plus"] = dim.get("tolerance_plus")
                if dim.get("tolerance_minus") is not None:
                    record["tolerance_minus"] = dim.get("tolerance_minus")
                if dim.get("label"):
                    record["label"] = dim.get("label")
                if dim.get("page") is not None:
                    record["_page"] = dim.get("page")
                if dim.get("confidence", 1.0) < 1.0:
                    record["_confidence"] = dim.get("confidence")

                record["_source_type"] = "dimension"
                record["_source_index"] = dim_idx
                records_data.append(record)

        # Parse title block (drawing metadata)
        if "title_block" in extraction_result and extraction_result["title_block"]:
            title_block = extraction_result["title_block"]
            record = {}

            # Standard title block fields
            title_block_fields = [
                "drawing_number",
                "title",
                "revision",
                "date",
                "author",
                "company",
                "scale",
                "sheet",
                "material",
                "finish",
            ]

            for field in title_block_fields:
                if title_block.get(field):
                    record[field] = title_block[field]

            # Custom fields from title block
            custom_fields = title_block.get("custom_fields", {})
            record.update(custom_fields)

            # Add confidence if available
            if title_block.get("confidence", 1.0) < 1.0:
                record["_confidence"] = title_block["confidence"]

            record["_source_type"] = "title_block"

            if record:  # Only add if there's actual data
                records_data.append(record)

        # Parse CAD layers
        if "layers" in extraction_result and extraction_result["layers"]:
            for layer_idx, layer in enumerate(extraction_result["layers"]):
                record = {
                    "layer_name": layer.get("name"),
                    "layer_color": layer.get("color"),
                    "linetype": layer.get("linetype"),
                    "lineweight": layer.get("lineweight"),
                    "is_on": layer.get("is_on", True),
                    "is_frozen": layer.get("is_frozen", False),
                    "is_locked": layer.get("is_locked", False),
                    "entity_count": layer.get("entity_count", 0),
                }
                record["_source_type"] = "layer"
                record["_source_index"] = layer_idx
                records_data.append(record)

        # Parse CAD blocks
        if "blocks" in extraction_result and extraction_result["blocks"]:
            for block_idx, block in enumerate(extraction_result["blocks"]):
                record = {
                    "block_name": block.get("name"),
                    "insert_count": block.get("insert_count", 0),
                    "entity_count": block.get("entity_count", 0),
                }
                if block.get("base_point"):
                    record["base_point"] = str(block["base_point"])
                if block.get("attributes"):
                    # Flatten attributes into record
                    for attr_idx, attr in enumerate(block["attributes"]):
                        if isinstance(attr, dict):
                            for key, value in attr.items():
                                record[f"attr_{key}"] = value

                record["_source_type"] = "block"
                record["_source_index"] = block_idx
                records_data.append(record)

        # Parse text blocks
        if "text_blocks" in extraction_result and extraction_result["text_blocks"]:
            for text_idx, text_block in enumerate(extraction_result["text_blocks"]):
                record = {
                    "text": text_block.get("text"),
                }
                if text_block.get("page") is not None:
                    record["_page"] = text_block["page"]
                if text_block.get("confidence", 1.0) < 1.0:
                    record["_confidence"] = text_block["confidence"]
                if text_block.get("font_size"):
                    record["font_size"] = text_block["font_size"]
                if text_block.get("is_title"):
                    record["is_title"] = text_block["is_title"]

                record["_source_type"] = "text_block"
                record["_source_index"] = text_idx
                records_data.append(record)

        # Parse Werk24-specific data (GD&T annotations)
        if "gdt_annotations" in extraction_result and extraction_result["gdt_annotations"]:
            for gdt_idx, gdt in enumerate(extraction_result["gdt_annotations"]):
                record = dict(gdt)  # Copy GD&T data
                record["_source_type"] = "gdt_annotation"
                record["_source_index"] = gdt_idx
                records_data.append(record)

        # Parse threads
        if "threads" in extraction_result and extraction_result["threads"]:
            for thread_idx, thread in enumerate(extraction_result["threads"]):
                record = dict(thread)  # Copy thread data
                record["_source_type"] = "thread"
                record["_source_index"] = thread_idx
                records_data.append(record)

        # Parse surface finishes
        if "surface_finishes" in extraction_result and extraction_result["surface_finishes"]:
            for finish_idx, finish in enumerate(extraction_result["surface_finishes"]):
                record = dict(finish)  # Copy finish data
                record["_source_type"] = "surface_finish"
                record["_source_index"] = finish_idx
                records_data.append(record)

        # Parse materials
        if "materials" in extraction_result and extraction_result["materials"]:
            for material_idx, material in enumerate(extraction_result["materials"]):
                record = dict(material)  # Copy material data
                record["_source_type"] = "material"
                record["_source_index"] = material_idx
                records_data.append(record)

        # Parse generic entities (fallback for custom extraction formats)
        if "entities" in extraction_result and extraction_result["entities"]:
            for entity_idx, entity in enumerate(extraction_result["entities"]):
                if isinstance(entity, dict):
                    record = dict(entity)
                    if "_source_type" not in record:
                        record["_source_type"] = "entity"
                    if "_source_index" not in record:
                        record["_source_index"] = entity_idx
                    records_data.append(record)

        # If no data was parsed, return empty list
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

    async def _validate_record_data(
        self,
        db: AsyncSession,
        table_id: str,
        data: dict[str, Any],
    ) -> None:
        """Validate record data against table fields.

        Args:
            db: Database session
            table_id: Table ID
            data: Record data (field_id -> value)

        Raises:
            ConflictError: If validation fails

        """
        # Get all fields for table
        fields_query = select(Field).where(
            Field.table_id == table_id,
            Field.deleted_at.is_(None),
        )
        result = await db.execute(fields_query)
        fields = result.scalars().all()
        fields_dict = {str(f.id): f for f in fields}

        # Validate each field in data
        for field_id, value in data.items():
            if field_id not in fields_dict:
                raise ConflictError(f"Field {field_id} does not exist in table")

            field = fields_dict[field_id]

            # Check required fields
            if field.is_required and value is None:
                raise ConflictError(f"Field '{field.name}' is required")

            # Validate using field handler if available
            from pybase.fields import get_field_handler

            handler = get_field_handler(field.field_type)
            if handler:
                # Parse field options
                options = None
                if field.options:
                    try:
                        options = json.loads(field.options)
                    except (json.JSONDecodeError, TypeError):
                        options = {}

                # Validate value
                try:
                    handler.validate(value, options)
                except ValueError as e:
                    raise ConflictError(f"Invalid value for field '{field.name}': {e}")
