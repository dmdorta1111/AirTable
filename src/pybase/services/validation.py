"""Validation service for data integrity checks."""

import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from pybase.core.exceptions import ConflictError, ValidationError
from pybase.fields import get_field_handler
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.unique_constraint import UniqueConstraint, UniqueConstraintStatus


class ValidationService:
    """Service for validating record data and constraints."""

    async def validate_record_data(
        self,
        db: AsyncSession,
        table_id: str,
        data: dict[str, Any],
        exclude_record_id: Optional[str] = None,
    ) -> None:
        """Validate record data against table fields and constraints.

        Args:
            db: Database session
            table_id: Table ID
            data: Record data (field_id -> value)
            exclude_record_id: Optional record ID to exclude from uniqueness checks
                (for updates, exclude the current record)

        Raises:
            ValidationError: If validation fails with detailed error messages
            ConflictError: If unique constraint is violated

        """
        # Get all fields for table
        fields_query = select(Field).options(load_only("id", "name", "field_type", "is_required", "is_unique", "options")).where(
            Field.table_id == table_id,
            Field.deleted_at.is_(None),
        )
        result = await db.execute(fields_query)
        fields = result.scalars().all()
        fields_dict = {str(f.id): f for f in fields}

        # Get unique constraints for fields in this table
        field_ids = list(fields_dict.keys())
        if not field_ids:
            return

        constraints_query = select(UniqueConstraint).where(
            UniqueConstraint.field_id.in_(field_ids),
            UniqueConstraint.status == UniqueConstraintStatus.ACTIVE.value,
        )
        constraints_result = await db.execute(constraints_query)
        constraints = constraints_result.scalars().all()
        constraints_dict = {str(c.field_id): c for c in constraints}

        # Collect all validation errors
        validation_errors = []

        # Validate each field in data
        for field_id, value in data.items():
            if field_id not in fields_dict:
                validation_errors.append({
                    "field_id": field_id,
                    "message": f"Field {field_id} does not exist in table",
                })
                continue

            field = fields_dict[field_id]

            # Check if field is editable
            if not field.is_editable:
                validation_errors.append({
                    "field_id": field_id,
                    "field_name": field.name,
                    "message": f"Field '{field.name}' is not editable",
                })
                continue

            # Check required fields
            if field.is_required and (value is None or value == ""):
                validation_errors.append({
                    "field_id": field_id,
                    "field_name": field.name,
                    "message": f"Field '{field.name}' is required",
                })
                continue

            # Validate using field handler if available and value is not None
            if value is not None and value != "":
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
                        validation_errors.append({
                            "field_id": field_id,
                            "field_name": field.name,
                            "message": f"Invalid value for field '{field.name}': {e}",
                        })

            # Check unique constraints
            if field_id in constraints_dict:
                constraint = constraints_dict[field_id]
                is_duplicate = await self._check_unique_constraint(
                    db, table_id, field_id, value, exclude_record_id, constraint
                )
                if is_duplicate:
                    field_name = field.name
                    error_msg = f"Value '{value}' for field '{field_name}' already exists"
                    if constraint.error_message:
                        error_msg = constraint.error_message.format(
                            field_name=field_name,
                            value=value,
                        )
                    raise ConflictError(error_msg)

        # Raise validation error if any errors found
        if validation_errors:
            raise ValidationError(
                message="Validation failed",
                errors=validation_errors,
            )

    async def _check_unique_constraint(
        self,
        db: AsyncSession,
        table_id: str,
        field_id: str,
        value: Any,
        exclude_record_id: Optional[str],
        constraint: UniqueConstraint,
    ) -> bool:
        """Check if a value violates a unique constraint.

        Args:
            db: Database session
            table_id: Table ID
            field_id: Field ID to check
            value: Value to check for uniqueness
            exclude_record_id: Record ID to exclude from check
            constraint: UniqueConstraint with configuration

        Returns:
            True if value violates uniqueness, False otherwise

        """
        if value is None or value == "":
            # Null values are not considered for unique constraints
            return False

        # Get all records for the table
        records_query = select(Record).where(
            Record.table_id == table_id,
            Record.deleted_at.is_(None),
        )

        # Exclude current record if updating
        if exclude_record_id:
            records_query = records_query.where(Record.id != exclude_record_id)

        result = await db.execute(records_query)
        records = result.scalars().all()

        # Check if any record has the same value for this field
        for record in records:
            try:
                record_data = json.loads(record.data)
                record_value = record_data.get(field_id)

                # Compare values based on case sensitivity setting
                if self._values_equal(record_value, value, constraint.case_sensitive):
                    return True
            except (json.JSONDecodeError, TypeError):
                continue

        return False

    def _values_equal(
        self,
        value1: Any,
        value2: Any,
        case_sensitive: bool,
    ) -> bool:
        """Compare two values with optional case-insensitive comparison.

        Args:
            value1: First value
            value2: Second value
            case_sensitive: Whether comparison should be case-sensitive

        Returns:
            True if values are equal, False otherwise

        """
        # Handle None values
        if value1 is None and value2 is None:
            return True
        if value1 is None or value2 is None:
            return False

        # Convert to strings for comparison if needed
        str1 = str(value1)
        str2 = str(value2)

        if case_sensitive:
            return str1 == str2
        else:
            return str1.lower() == str2.lower()

    async def validate_field_update(
        self,
        db: AsyncSession,
        field_id: str,
        new_value: Any,
        exclude_record_id: Optional[str] = None,
    ) -> None:
        """Validate a single field update against constraints.

        Args:
            db: Database session
            field_id: Field ID to validate
            new_value: New value for the field
            exclude_record_id: Optional record ID to exclude from uniqueness checks

        Raises:
            ValidationError: If validation fails
            ConflictError: If unique constraint is violated

        """
        # Get field
        field = await db.get(Field, field_id)
        if not field or field.is_deleted:
            raise ValidationError(
                message="Validation failed",
                errors=[{"field_id": field_id, "message": f"Field {field_id} not found"}],
            )

        # Check if field is editable
        if not field.is_editable:
            raise ValidationError(
                message="Validation failed",
                errors=[{
                    "field_id": field_id,
                    "field_name": field.name,
                    "message": f"Field '{field.name}' is not editable",
                }],
            )

        # Check required fields
        if field.is_required and (new_value is None or new_value == ""):
            raise ValidationError(
                message="Validation failed",
                errors=[{
                    "field_id": field_id,
                    "field_name": field.name,
                    "message": f"Field '{field.name}' is required",
                }],
            )

        # Validate using field handler if available
        if new_value is not None and new_value != "":
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
                    handler.validate(new_value, options)
                except ValueError as e:
                    raise ValidationError(
                        message="Validation failed",
                        errors=[{
                            "field_id": field_id,
                            "field_name": field.name,
                            "message": f"Invalid value for field '{field.name}': {e}",
                        }],
                    )

        # Check unique constraint if it exists
        constraint_query = select(UniqueConstraint).where(
            UniqueConstraint.field_id == field_id,
            UniqueConstraint.status == UniqueConstraintStatus.ACTIVE.value,
        )
        constraint_result = await db.execute(constraint_query)
        constraint = constraint_result.scalar_one_or_none()

        if constraint:
            is_duplicate = await self._check_unique_constraint(
                db, str(field.table_id), field_id, new_value, exclude_record_id, constraint
            )
            if is_duplicate:
                field_name = field.name
                error_msg = f"Value '{new_value}' for field '{field_name}' already exists"
                if constraint.error_message:
                    error_msg = constraint.error_message.format(
                        field_name=field_name,
                        value=new_value,
                    )
                raise ConflictError(error_msg)
