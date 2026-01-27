"""BOM validation service for database cross-reference and validation."""

import json
import re
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.extraction import (
    BOMValidationError,
    BOMValidationResult,
    BOMValidationSchema,
    BOMValidationSeverity,
    BOMValidationRule,
)


class BOMValidationService:
    """Service for validating BOM data against database and validation rules."""

    async def validate_bom(
        self,
        db: AsyncSession,
        user_id: str,
        bom_items: list[dict[str, Any]],
        validation_config: Optional[BOMValidationSchema] = None,
        table_id: Optional[str] = None,
        field_mapping: Optional[dict[str, str]] = None,
    ) -> BOMValidationResult:
        """
        Validate BOM items against validation rules and database.

        Performs comprehensive validation including:
        - Required field checks
        - Format pattern validation
        - Value range validation
        - Database cross-reference
        - Duplicate detection

        Args:
            db: Database session
            user_id: User ID requesting validation
            bom_items: List of BOM items to validate
            validation_config: Validation configuration (uses defaults if None)
            table_id: Optional table ID to cross-reference against
            field_mapping: Optional mapping of BOM fields to table field IDs

        Returns:
            BOMValidationResult with validation status, errors, warnings, and cross-reference results

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table

        """
        start_time = datetime.now()

        # Use default validation config if not provided
        if validation_config is None:
            validation_config = BOMValidationSchema()

        # Verify table access if table_id provided
        if table_id:
            await self._get_table_with_access(db, table_id, user_id)

        # Initialize result
        errors = []
        warnings = []
        valid_items = 0
        invalid_items = 0

        # Track parts for cross-reference
        new_parts = []
        existing_parts = []
        duplicate_parts = []
        seen_part_numbers = {}

        # Validate each item
        for idx, item in enumerate(bom_items):
            item_errors = []
            item_warnings = []

            # Validate required fields
            required_errors = self._validate_required_fields(
                item, validation_config, idx
            )
            item_errors.extend(required_errors)

            # Validate format patterns
            format_errors = self._validate_format_patterns(
                item, validation_config, idx
            )
            item_errors.extend(format_errors)

            # Validate value ranges
            range_warnings = self._validate_value_ranges(
                item, validation_config, idx
            )
            item_warnings.extend(range_warnings)

            # Validate custom field rules
            custom_errors = self._validate_custom_rules(
                item, validation_config, idx
            )
            item_errors.extend(custom_errors)

            # Database cross-reference
            if validation_config.validate_against_database and table_id:
                cross_ref_result = await self._cross_reference_item(
                    db, item, table_id, field_mapping, idx
                )

                if cross_ref_result["is_new"]:
                    new_parts.append(item)
                else:
                    existing_parts.append(item)

                # Add warnings for cross-reference
                item_warnings.extend(cross_ref_result.get("warnings", []))

            # Check duplicates
            if validation_config.check_duplicates:
                dup_result = self._check_duplicate_item(
                    item, seen_part_numbers, idx
                )
                if dup_result:
                    duplicate_parts.append(item)
                    item_warnings.append(dup_result)

            # Categorize item
            if item_errors or any(
                e.severity == BOMValidationSeverity.ERROR for e in item_errors
            ):
                invalid_items += 1
            else:
                valid_items += 1

            errors.extend([e for e in item_errors if e.severity == BOMValidationSeverity.ERROR])
            warnings.extend(item_warnings)
            warnings.extend([e for e in item_errors if e.severity == BOMValidationSeverity.WARNING])

        # Calculate validation time
        validation_time = (datetime.now() - start_time).total_seconds()

        # Build result
        return BOMValidationResult(
            is_valid=invalid_items == 0,
            total_items=len(bom_items),
            valid_items=valid_items,
            invalid_items=invalid_items,
            warning_count=len(warnings),
            error_count=len(errors),
            errors=errors,
            warnings=warnings,
            new_parts=new_parts,
            existing_parts=existing_parts,
            duplicate_parts=duplicate_parts,
            validation_time=validation_time,
            validated_at=datetime.utcnow(),
        )

    async def cross_reference_parts(
        self,
        db: AsyncSession,
        user_id: str,
        bom_items: list[dict[str, Any]],
        table_id: str,
        field_mapping: dict[str, str],
    ) -> dict[str, Any]:
        """
        Cross-reference BOM items against existing parts database.

        Identifies which parts are new vs existing in the database.

        Args:
            db: Database session
            user_id: User ID requesting cross-reference
            bom_items: List of BOM items to cross-reference
            table_id: Table ID to cross-reference against
            field_mapping: Mapping of BOM fields to table field IDs

        Returns:
            Dict containing:
                - new_parts: Parts not found in database
                - existing_parts: Parts found in database
                - summary: Cross-reference statistics

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table

        """
        # Verify table access
        await self._get_table_with_access(db, table_id, user_id)

        new_parts = []
        existing_parts = []

        # Get all existing records from table
        records = await self._get_table_records(db, table_id)

        # Build lookup index from existing records
        record_index = self._build_record_index(records, field_mapping)

        # Cross-reference each item
        for item in bom_items:
            part_number = item.get("part_number") or item.get("Part Number")
            if not part_number:
                new_parts.append(item)
                continue

            if part_number in record_index:
                existing_parts.append({
                    **item,
                    "_existing_record": record_index[part_number],
                })
            else:
                new_parts.append(item)

        return {
            "new_parts": new_parts,
            "existing_parts": existing_parts,
            "summary": {
                "total_items": len(bom_items),
                "new_count": len(new_parts),
                "existing_count": len(existing_parts),
            },
        }

    async def highlight_differences(
        self,
        db: AsyncSession,
        user_id: str,
        bom_items: list[dict[str, Any]],
        table_id: str,
        field_mapping: dict[str, str],
    ) -> dict[str, Any]:
        """
        Highlight differences between BOM items and existing database records.

        Compares BOM item fields with existing parts and identifies differences.

        Args:
            db: Database session
            user_id: User ID requesting comparison
            bom_items: List of BOM items to compare
            table_id: Table ID to compare against
            field_mapping: Mapping of BOM fields to table field IDs

        Returns:
            Dict containing:
                - matched_with_differences: Items with differences highlighted
                - exact_matches: Items that match exactly
                - new_items: Items not in database

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table

        """
        # Verify table access
        await self._get_table_with_access(db, table_id, user_id)

        # Get existing records
        records = await self._get_table_records(db, table_id)
        record_index = self._build_record_index(records, field_mapping)

        matched_with_differences = []
        exact_matches = []
        new_items = []

        for item in bom_items:
            part_number = item.get("part_number") or item.get("Part Number")
            if not part_number or part_number not in record_index:
                new_items.append(item)
                continue

            existing_record = record_index[part_number]
            differences = self._compare_item_to_record(
                item, existing_record, field_mapping
            )

            if differences:
                matched_with_differences.append({
                    "bom_item": item,
                    "existing_record": existing_record,
                    "differences": differences,
                })
            else:
                exact_matches.append(item)

        return {
            "matched_with_differences": matched_with_differences,
            "exact_matches": exact_matches,
            "new_items": new_items,
            "summary": {
                "total_items": len(bom_items),
                "differences_count": len(matched_with_differences),
                "exact_match_count": len(exact_matches),
                "new_count": len(new_items),
            },
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
            raise NotFoundError("Table", table_id)

        # Check workspace access
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        return table

    async def _get_base(self, db: AsyncSession, base_id: str) -> Any:
        """Get base by ID."""
        from pybase.models.base import Base
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base", base_id)
        return base

    async def _get_workspace(self, db: AsyncSession, workspace_id: str) -> Workspace:
        """Get workspace by ID."""
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
        """Get workspace member."""
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_table_records(
        self,
        db: AsyncSession,
        table_id: str,
    ) -> list[Record]:
        """Get all records for a table."""
        query = select(Record).where(
            Record.table_id == table_id,
            Record.is_deleted.is_(False),
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    def _build_record_index(
        self,
        records: list[Record],
        field_mapping: dict[str, str],
    ) -> dict[str, dict[str, Any]]:
        """Build lookup index from records by part number."""
        index = {}

        # Find the part number field ID
        part_number_field_id = None
        for bom_field, table_field_id in field_mapping.items():
            if bom_field.lower() in ["part_number", "part number", "part-number"]:
                part_number_field_id = table_field_id
                break

        if not part_number_field_id:
            return index

        for record in records:
            try:
                data = json.loads(record.data) if isinstance(record.data, str) else record.data
                part_number = data.get(part_number_field_id)

                if part_number:
                    index[part_number] = {
                        "id": str(record.id),
                        "data": data,
                    }
            except (json.JSONDecodeError, TypeError):
                continue

        return index

    def _validate_required_fields(
        self,
        item: dict[str, Any],
        config: BOMValidationSchema,
        row_index: int,
    ) -> list[BOMValidationError]:
        """Validate required fields are present."""
        errors = []

        # Check standard required fields
        required_checks = [
            ("part_number", config.require_part_number, ["part_number", "Part Number", "PART_NUMBER"]),
            ("quantity", config.require_quantity, ["quantity", "Quantity", "QUANTITY", "qty"]),
            ("description", config.require_description, ["description", "Description", "DESCRIPTION"]),
            ("material", config.require_material, ["material", "Material", "MATERIAL"]),
        ]

        for field_name, is_required, possible_keys in required_checks:
            if not is_required:
                continue

            if not any(item.get(key) for key in possible_keys):
                errors.append(
                    BOMValidationError(
                        row_index=row_index,
                        field_name=field_name,
                        error_code="REQUIRED_FIELD",
                        message=f"Required field '{field_name}' is missing",
                        severity=BOMValidationSeverity.ERROR,
                        suggestion=f"Provide a value for '{field_name}'",
                    )
                )

        # Check custom field rules
        for rule in config.field_rules:
            if rule.is_required and not item.get(rule.field_name):
                errors.append(
                    BOMValidationError(
                        row_index=row_index,
                        field_name=rule.field_name,
                        error_code="REQUIRED_FIELD",
                        message=f"Required field '{rule.field_name}' is missing",
                        severity=BOMValidationSeverity.ERROR,
                        custom_message=rule.custom_message,
                    )
                )

        return errors

    def _validate_format_patterns(
        self,
        item: dict[str, Any],
        config: BOMValidationSchema,
        row_index: int,
    ) -> list[BOMValidationError]:
        """Validate field formats match patterns."""
        errors = []

        # Validate part number pattern
        part_number = item.get("part_number") or item.get("Part Number")
        if part_number and config.part_number_pattern:
            if not re.match(config.part_number_pattern, str(part_number)):
                errors.append(
                    BOMValidationError(
                        row_index=row_index,
                        field_name="part_number",
                        error_code="FORMAT_PATTERN",
                        message=f"Part number '{part_number}' doesn't match required format",
                        severity=BOMValidationSeverity.ERROR,
                        current_value=part_number,
                        expected_format=config.part_number_pattern,
                        suggestion="Use uppercase letters, numbers, hyphens, and underscores only",
                    )
                )

        # Validate quantity pattern
        quantity = item.get("quantity") or item.get("Quantity")
        if quantity and config.quantity_pattern:
            if not re.match(config.quantity_pattern, str(quantity)):
                errors.append(
                    BOMValidationError(
                        row_index=row_index,
                        field_name="quantity",
                        error_code="FORMAT_PATTERN",
                        message=f"Quantity '{quantity}' doesn't match required format",
                        severity=BOMValidationSeverity.ERROR,
                        current_value=quantity,
                        expected_format=config.quantity_pattern,
                    )
                )

        # Validate material code pattern
        material = item.get("material") or item.get("Material")
        if material and config.material_code_pattern:
            if not re.match(config.material_code_pattern, str(material)):
                errors.append(
                    BOMValidationError(
                        row_index=row_index,
                        field_name="material",
                        error_code="FORMAT_PATTERN",
                        message=f"Material code '{material}' doesn't match required format",
                        severity=BOMValidationSeverity.WARNING,
                        current_value=material,
                        expected_format=config.material_code_pattern,
                    )
                )

        # Validate custom field rules
        for rule in config.field_rules:
            if rule.rule_type == BOMValidationRule.FORMAT_PATTERN and rule.pattern:
                value = item.get(rule.field_name)
                if value and not re.match(rule.pattern, str(value)):
                    errors.append(
                        BOMValidationError(
                            row_index=row_index,
                            field_name=rule.field_name,
                            error_code="FORMAT_PATTERN",
                            message=f"Field '{rule.field_name}' value doesn't match required format",
                            severity=rule.severity,
                            current_value=value,
                            expected_format=rule.pattern,
                            custom_message=rule.custom_message,
                        )
                    )

        return errors

    def _validate_value_ranges(
        self,
        item: dict[str, Any],
        config: BOMValidationSchema,
        row_index: int,
    ) -> list[BOMValidationError]:
        """Validate value ranges."""
        warnings = []

        # Validate quantity range
        quantity = item.get("quantity") or item.get("Quantity")
        if quantity:
            try:
                qty_value = float(quantity)

                if qty_value < config.min_quantity:
                    warnings.append(
                        BOMValidationError(
                            row_index=row_index,
                            field_name="quantity",
                            error_code="VALUE_RANGE",
                            message=f"Quantity {qty_value} is below minimum {config.min_quantity}",
                            severity=BOMValidationSeverity.WARNING,
                            current_value=quantity,
                            expected_format=f"Minimum: {config.min_quantity}",
                        )
                    )

                if config.max_quantity and qty_value > config.max_quantity:
                    warnings.append(
                        BOMValidationError(
                            row_index=row_index,
                            field_name="quantity",
                            error_code="VALUE_RANGE",
                            message=f"Quantity {qty_value} exceeds maximum {config.max_quantity}",
                            severity=BOMValidationSeverity.WARNING,
                            current_value=quantity,
                            expected_format=f"Maximum: {config.max_quantity}",
                        )
                    )

                # Check for fractional quantities
                if not config.allow_fractional_quantity and qty_value != int(qty_value):
                    warnings.append(
                        BOMValidationError(
                            row_index=row_index,
                            field_name="quantity",
                            error_code="VALUE_RANGE",
                            message=f"Fractional quantity {qty_value} not allowed",
                            severity=BOMValidationSeverity.WARNING,
                            current_value=quantity,
                            suggestion="Use whole numbers for quantity",
                        )
                    )

            except (ValueError, TypeError):
                pass

        # Validate custom field rules
        for rule in config.field_rules:
            if rule.rule_type == BOMValidationRule.VALUE_RANGE:
                value = item.get(rule.field_name)
                if value:
                    try:
                        num_value = float(value)

                        if rule.min_value is not None and num_value < rule.min_value:
                            warnings.append(
                                BOMValidationError(
                                    row_index=row_index,
                                    field_name=rule.field_name,
                                    error_code="VALUE_RANGE",
                                    message=f"Value {num_value} is below minimum {rule.min_value}",
                                    severity=rule.severity,
                                    current_value=value,
                                    expected_format=f"Minimum: {rule.min_value}",
                                    custom_message=rule.custom_message,
                                )
                            )

                        if rule.max_value is not None and num_value > rule.max_value:
                            warnings.append(
                                BOMValidationError(
                                    row_index=row_index,
                                    field_name=rule.field_name,
                                    error_code="VALUE_RANGE",
                                    message=f"Value {num_value} exceeds maximum {rule.max_value}",
                                    severity=rule.severity,
                                    current_value=value,
                                    expected_format=f"Maximum: {rule.max_value}",
                                    custom_message=rule.custom_message,
                                )
                            )

                    except (ValueError, TypeError):
                        pass

            # Validate allowed values
            if rule.rule_type == BOMValidationRule.ALLOWED_VALUES and rule.allowed_values:
                value = item.get(rule.field_name)
                if value and str(value) not in rule.allowed_values:
                    warnings.append(
                        BOMValidationError(
                            row_index=row_index,
                            field_name=rule.field_name,
                            error_code="ALLOWED_VALUES",
                            message=f"Value '{value}' not in allowed values",
                            severity=rule.severity,
                            current_value=value,
                            expected_format=f"Allowed: {', '.join(rule.allowed_values)}",
                            custom_message=rule.custom_message,
                        )
                    )

        return warnings

    def _validate_custom_rules(
        self,
        item: dict[str, Any],
        config: BOMValidationSchema,
        row_index: int,
    ) -> list[BOMValidationError]:
        """Validate custom field rules."""
        errors = []

        for rule in config.field_rules:
            value = item.get(rule.field_name)

            # Check string length constraints
            if value:
                str_value = str(value)

                if rule.min_length and len(str_value) < rule.min_length:
                    errors.append(
                        BOMValidationError(
                            row_index=row_index,
                            field_name=rule.field_name,
                            error_code="MIN_LENGTH",
                            message=f"Value length {len(str_value)} is below minimum {rule.min_length}",
                            severity=rule.severity,
                            current_value=value,
                            expected_format=f"Minimum length: {rule.min_length}",
                            custom_message=rule.custom_message,
                        )
                    )

                if rule.max_length and len(str_value) > rule.max_length:
                    errors.append(
                        BOMValidationError(
                            row_index=row_index,
                            field_name=rule.field_name,
                            error_code="MAX_LENGTH",
                            message=f"Value length {len(str_value)} exceeds maximum {rule.max_length}",
                            severity=rule.severity,
                            current_value=value,
                            expected_format=f"Maximum length: {rule.max_length}",
                            custom_message=rule.custom_message,
                        )
                    )

        return errors

    async def _cross_reference_item(
        self,
        db: AsyncSession,
        item: dict[str, Any],
        table_id: str,
        field_mapping: Optional[dict[str, str]],
        row_index: int,
    ) -> dict[str, Any]:
        """Cross-reference single item against database."""
        result = {
            "is_new": True,
            "warnings": [],
        }

        if not field_mapping:
            return result

        # Get part number from item
        part_number = item.get("part_number") or item.get("Part Number")
        if not part_number:
            return result

        # Find part number field in mapping
        part_number_field_id = None
        for bom_field, table_field_id in field_mapping.items():
            if bom_field.lower() in ["part_number", "part number", "part-number"]:
                part_number_field_id = table_field_id
                break

        if not part_number_field_id:
            return result

        # Query database for matching part
        query = select(Record).where(
            Record.table_id == table_id,
            Record.is_deleted.is_(False),
        )
        result_records = await db.execute(query)
        records = result_records.scalars().all()

        for record in records:
            try:
                data = json.loads(record.data) if isinstance(record.data, str) else record.data
                if data.get(part_number_field_id) == part_number:
                    result["is_new"] = False
                    result["existing_record"] = {
                        "id": str(record.id),
                        "data": data,
                    }
                    break
            except (json.JSONDecodeError, TypeError):
                continue

        return result

    def _check_duplicate_item(
        self,
        item: dict[str, Any],
        seen_part_numbers: dict[str, int],
        row_index: int,
    ) -> Optional[BOMValidationError]:
        """Check if item is a duplicate within BOM."""
        part_number = item.get("part_number") or item.get("Part Number")
        if not part_number:
            return None

        if part_number in seen_part_numbers:
            return BOMValidationError(
                row_index=row_index,
                field_name="part_number",
                error_code="DUPLICATE_PART",
                message=f"Duplicate part number '{part_number}' found in BOM",
                severity=BOMValidationSeverity.WARNING,
                current_value=part_number,
                suggestion=f"This part also appears at row {seen_part_numbers[part_number]}",
            )

        seen_part_numbers[part_number] = row_index
        return None

    def _compare_item_to_record(
        self,
        item: dict[str, Any],
        existing_record: dict[str, Any],
        field_mapping: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Compare BOM item to existing record and return differences."""
        differences = []
        record_data = existing_record.get("data", {})

        for bom_field, table_field_id in field_mapping.items():
            bom_value = item.get(bom_field)
            record_value = record_data.get(table_field_id)

            if bom_value != record_value:
                differences.append({
                    "field": bom_field,
                    "bom_value": bom_value,
                    "record_value": record_value,
                })

        return differences
