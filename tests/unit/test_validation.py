"""Unit tests for ValidationService."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from pybase.core.exceptions import ConflictError, ValidationError
from pybase.fields import get_field_handler
from pybase.models.field import FieldType
from pybase.models.unique_constraint import UniqueConstraint, UniqueConstraintStatus
from pybase.services.validation import ValidationService


class TestValuesEqual:
    """Test _values_equal method."""

    def test_values_equal_both_none(self):
        """Test comparison when both values are None."""
        service = ValidationService()
        result = service._values_equal(None, None, case_sensitive=True)
        assert result is True

    def test_values_equal_one_none(self):
        """Test comparison when one value is None."""
        service = ValidationService()
        result = service._values_equal(None, "test", case_sensitive=True)
        assert result is False

        result = service._values_equal("test", None, case_sensitive=True)
        assert result is False

    def test_values_equal_case_sensitive_true(self):
        """Test case-sensitive comparison."""
        service = ValidationService()
        result = service._values_equal("Test", "Test", case_sensitive=True)
        assert result is True

        result = service._values_equal("Test", "test", case_sensitive=True)
        assert result is False

    def test_values_equal_case_sensitive_false(self):
        """Test case-insensitive comparison."""
        service = ValidationService()
        result = service._values_equal("Test", "test", case_sensitive=False)
        assert result is True

        result = service._values_equal("Test", "TEST", case_sensitive=False)
        assert result is True

        result = service._values_equal("Test", "Other", case_sensitive=False)
        assert result is False

    def test_values_equal_numeric_conversion(self):
        """Test comparison with numeric values."""
        service = ValidationService()
        result = service._values_equal(123, "123", case_sensitive=True)
        assert result is True

        result = service._values_equal(123.5, "123.5", case_sensitive=True)
        assert result is True

    def test_values_equal_boolean_conversion(self):
        """Test comparison with boolean values."""
        service = ValidationService()
        result = service._values_equal(True, "True", case_sensitive=True)
        assert result is True

        result = service._values_equal(False, "False", case_sensitive=True)
        assert result is True


class TestCheckUniqueConstraint:
    """Test _check_unique_constraint method."""

    @pytest.mark.asyncio
    async def test_check_unique_null_value(self):
        """Test that null values don't violate uniqueness."""
        service = ValidationService()
        db = AsyncMock()

        result = await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value=None,
            exclude_record_id=None,
            constraint=MagicMock(case_sensitive=True),
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_unique_empty_string(self):
        """Test that empty strings don't violate uniqueness."""
        service = ValidationService()
        db = AsyncMock()

        result = await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value="",
            exclude_record_id=None,
            constraint=MagicMock(case_sensitive=True),
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_unique_no_duplicates(self):
        """Test when no duplicates exist."""
        service = ValidationService()
        db = AsyncMock()

        # Mock database query result
        mock_record = MagicMock()
        mock_record.data = json.dumps({"field-1": "other-value"})

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        db.execute.return_value = mock_result

        result = await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value="test-value",
            exclude_record_id=None,
            constraint=MagicMock(case_sensitive=True),
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_unique_with_duplicate(self):
        """Test when duplicate exists."""
        service = ValidationService()
        db = AsyncMock()

        # Mock database query result with duplicate
        mock_record = MagicMock()
        mock_record.data = json.dumps({"field-1": "test-value"})

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        db.execute.return_value = mock_result

        result = await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value="test-value",
            exclude_record_id=None,
            constraint=MagicMock(case_sensitive=True),
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_unique_case_insensitive_duplicate(self):
        """Test case-insensitive duplicate detection."""
        service = ValidationService()
        db = AsyncMock()

        # Mock database query result with different case
        mock_record = MagicMock()
        mock_record.data = json.dumps({"field-1": "TEST-VALUE"})

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        db.execute.return_value = mock_result

        result = await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value="test-value",
            exclude_record_id=None,
            constraint=MagicMock(case_sensitive=False),
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_unique_with_exclusion(self):
        """Test unique check with record exclusion."""
        service = ValidationService()
        db = AsyncMock()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        # Mock database query to verify exclusion is applied
        result = await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value="test-value",
            exclude_record_id="record-1",
            constraint=MagicMock(case_sensitive=True),
        )

        # Verify the query was called
        assert db.execute.called

    @pytest.mark.asyncio
    async def test_check_unique_invalid_json(self):
        """Test handling of invalid JSON in record data."""
        service = ValidationService()
        db = AsyncMock()

        # Mock database query result with invalid JSON
        mock_record1 = MagicMock()
        mock_record1.data = "invalid-json"
        mock_record2 = MagicMock()
        mock_record2.data = json.dumps({"field-1": "other-value"})

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_record1, mock_record2]
        db.execute.return_value = mock_result

        result = await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value="test-value",
            exclude_record_id=None,
            constraint=MagicMock(case_sensitive=True),
        )

        # Should skip invalid JSON and return False (no duplicate found)
        assert result is False


class TestValidateRecordData:
    """Test validate_record_data method."""

    def _create_mock_field(
        self,
        field_id="field-1",
        name="Test Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
        is_computed=False,
        is_editable=True,
        options=None,
    ):
        """Helper to create a mock field."""
        mock_field = MagicMock()
        mock_field.id = field_id
        mock_field.name = name
        mock_field.field_type = field_type
        mock_field.is_required = is_required
        mock_field.is_computed = is_computed
        mock_field.is_locked = False
        mock_field.is_editable = is_editable
        mock_field.options = options
        return mock_field

    @pytest.mark.asyncio
    async def test_validate_record_data_empty_table(self):
        """Test validation with table that has no fields."""
        service = ValidationService()
        db = AsyncMock()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        # Should not raise any error
        await service.validate_record_data(
            db=db,
            table_id="table-1",
            data={"field-1": "value"},
        )

    @pytest.mark.asyncio
    async def test_validate_record_data_nonexistent_field(self):
        """Test validation with non-existent field."""
        service = ValidationService()
        db = AsyncMock()

        # Mock fields query to return empty
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        with pytest.raises(ValidationError) as exc_info:
            await service.validate_record_data(
                db=db,
                table_id="table-1",
                data={"field-1": "value"},
            )

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) == 1
        assert "does not exist in table" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_record_data_not_editable_field(self):
        """Test validation with non-editable field."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a computed field (not editable)
        mock_field = self._create_mock_field(
            name="Formula Field",
            field_type=FieldType.FORMULA.value,
            is_computed=True,
            is_editable=False,
        )

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_field]
        db.execute.return_value = mock_result

        with pytest.raises(ValidationError) as exc_info:
            await service.validate_record_data(
                db=db,
                table_id="table-1",
                data={"field-1": "value"},
            )

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) == 1
        assert "not editable" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_record_data_required_field_missing(self):
        """Test validation with missing required field."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a required field
        mock_field = self._create_mock_field(
            name="Required Field",
            is_required=True,
        )

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.side_effect = [
            [mock_field],  # Fields
            [],  # Constraints
        ]
        db.execute.return_value = mock_result

        with pytest.raises(ValidationError) as exc_info:
            await service.validate_record_data(
                db=db,
                table_id="table-1",
                data={"field-1": None},
            )

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) == 1
        assert "is required" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_record_data_required_field_empty_string(self):
        """Test validation with empty string for required field."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a required field
        mock_field = self._create_mock_field(
            name="Required Field",
            is_required=True,
        )

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.side_effect = [
            [mock_field],  # Fields
            [],  # Constraints
        ]
        db.execute.return_value = mock_result

        with pytest.raises(ValidationError) as exc_info:
            await service.validate_record_data(
                db=db,
                table_id="table-1",
                data={"field-1": ""},
            )

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) == 1
        assert "is required" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_record_data_field_validation_error(self):
        """Test field handler validation error."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with validation
        mock_field = self._create_mock_field(
            name="Email Field",
            field_type=FieldType.EMAIL.value,
        )

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_field]
        db.execute.return_value = mock_result

        # Mock field handler to raise validation error
        with patch("pybase.services.validation.get_field_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.validate.side_effect = ValueError("Invalid email format")
            mock_get_handler.return_value = mock_handler

            with pytest.raises(ValidationError) as exc_info:
                await service.validate_record_data(
                    db=db,
                    table_id="table-1",
                    data={"field-1": "not-an-email"},
                )

            errors = exc_info.value.details.get("errors", [])
            assert len(errors) == 1
            assert "Invalid value for field" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_record_data_unique_constraint_violation(self):
        """Test unique constraint violation."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with unique constraint
        mock_field = self._create_mock_field(
            name="Unique Field",
        )

        mock_constraint = UniqueConstraint(
            id="constraint-1",
            field_id="field-1",
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
            error_message=None,
        )

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            if "fields" in str(query):
                result.scalars.return_value.all.return_value = [mock_field]
            elif "unique_constraints" in str(query):
                result.scalars.return_value.all.return_value = [mock_constraint]
            return result

        db.execute.side_effect = mock_execute_side_effect

        # Mock duplicate check to return True
        with patch.object(service, "_check_unique_constraint", return_value=True):
            with pytest.raises(ConflictError) as exc_info:
                await service.validate_record_data(
                    db=db,
                    table_id="table-1",
                    data={"field-1": "duplicate-value"},
                )

            assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_record_data_custom_error_message(self):
        """Test unique constraint with custom error message."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with unique constraint and custom error
        mock_field = self._create_mock_field(
            name="SKU",
        )

        mock_constraint = UniqueConstraint(
            id="constraint-1",
            field_id="field-1",
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
            error_message="SKU {value} is already taken",
        )

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            if "fields" in str(query):
                result.scalars.return_value.all.return_value = [mock_field]
            elif "unique_constraints" in str(query):
                result.scalars.return_value.all.return_value = [mock_constraint]
            return result

        db.execute.side_effect = mock_execute_side_effect

        # Mock duplicate check to return True
        with patch.object(service, "_check_unique_constraint", return_value=True):
            with pytest.raises(ConflictError) as exc_info:
                await service.validate_record_data(
                    db=db,
                    table_id="table-1",
                    data={"field-1": "SKU-123"},
                )

            assert "SKU-123 is already taken" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_record_data_multiple_errors(self):
        """Test validation with multiple errors."""
        service = ValidationService()
        db = AsyncMock()

        # Mock multiple fields
        mock_field1 = self._create_mock_field(
            field_id="field-1",
            name="Required Field",
            is_required=True,
        )
        mock_field2 = self._create_mock_field(
            field_id="field-2",
            name="Non Editable",
            field_type=FieldType.FORMULA.value,
            is_computed=True,
            is_editable=False,
        )

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_field1, mock_field2]
        db.execute.return_value = mock_result

        with pytest.raises(ValidationError) as exc_info:
            await service.validate_record_data(
                db=db,
                table_id="table-1",
                data={
                    "field-1": None,
                    "field-2": "value",
                    "field-3": "non-existent",
                },
            )

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) == 3  # Required, not editable, non-existent

    @pytest.mark.asyncio
    async def test_validate_record_data_with_valid_data(self):
        """Test validation with valid data."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a valid field
        mock_field = self._create_mock_field(
            name="Text Field",
        )

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            if "fields" in str(query):
                result.scalars.return_value.all.return_value = [mock_field]
            elif "unique_constraints" in str(query):
                result.scalars.return_value.all.return_value = []
            return result

        db.execute.side_effect = mock_execute_side_effect

        # Should not raise any error
        await service.validate_record_data(
            db=db,
            table_id="table-1",
            data={"field-1": "valid text"},
        )

    @pytest.mark.asyncio
    async def test_validate_record_data_with_field_options(self):
        """Test validation with field options."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with JSON options
        mock_field = self._create_mock_field(
            name="Number Field",
            field_type=FieldType.NUMBER.value,
            options='{"min": 0, "max": 100}',
        )

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            if "fields" in str(query):
                result.scalars.return_value.all.return_value = [mock_field]
            elif "unique_constraints" in str(query):
                result.scalars.return_value.all.return_value = []
            return result

        db.execute.side_effect = mock_execute_side_effect

        # Mock field handler
        with patch("pybase.services.validation.get_field_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.validate.return_value = None  # Valid
            mock_get_handler.return_value = mock_handler

            # Should not raise any error
            await service.validate_record_data(
                db=db,
                table_id="table-1",
                data={"field-1": 50},
            )

            # Verify handler was called with parsed options
            mock_handler.validate.assert_called_once_with(50, {"min": 0, "max": 100})

    @pytest.mark.asyncio
    async def test_validate_record_data_invalid_field_options(self):
        """Test handling of invalid field options JSON."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with invalid JSON options
        mock_field = self._create_mock_field(
            name="Number Field",
            field_type=FieldType.NUMBER.value,
            options="invalid-json",
        )

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            if "fields" in str(query):
                result.scalars.return_value.all.return_value = [mock_field]
            elif "unique_constraints" in str(query):
                result.scalars.return_value.all.return_value = []
            return result

        db.execute.side_effect = mock_execute_side_effect

        # Mock field handler
        with patch("pybase.services.validation.get_field_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.validate.return_value = None  # Valid
            mock_get_handler.return_value = mock_handler

            # Should not raise any error (options should default to {})
            await service.validate_record_data(
                db=db,
                table_id="table-1",
                data={"field-1": 50},
            )

            # Verify handler was called with empty options
            mock_handler.validate.assert_called_once_with(50, {})

    @pytest.mark.asyncio
    async def test_validate_record_data_skip_none_values(self):
        """Test that None values skip field handler validation."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field
        mock_field = self._create_mock_field(
            name="Text Field",
        )

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            if "fields" in str(query):
                result.scalars.return_value.all.return_value = [mock_field]
            elif "unique_constraints" in str(query):
                result.scalars.return_value.all.return_value = []
            return result

        db.execute.side_effect = mock_execute_side_effect

        # Mock field handler
        with patch("pybase.services.validation.get_field_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_get_handler.return_value = mock_handler

            # Should not call handler.validate for None
            await service.validate_record_data(
                db=db,
                table_id="table-1",
                data={"field-1": None},
            )

            # Handler should not be called for None value
            mock_handler.validate.assert_not_called()


class TestValidateFieldUpdate:
    """Test validate_field_update method."""

    def _create_mock_field(
        self,
        field_id="field-1",
        name="Test Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
        is_computed=False,
        is_editable=True,
        is_locked=False,
        options=None,
        table_id="table-1",
    ):
        """Helper to create a mock field."""
        mock_field = MagicMock()
        mock_field.id = field_id
        mock_field.name = name
        mock_field.field_type = field_type
        mock_field.is_required = is_required
        mock_field.is_computed = is_computed
        mock_field.is_locked = is_locked
        mock_field.is_editable = is_editable
        mock_field.options = options
        mock_field.table_id = table_id
        mock_field.is_deleted = False
        return mock_field

    @pytest.mark.asyncio
    async def test_validate_field_update_field_not_found(self):
        """Test validation with non-existent field."""
        service = ValidationService()
        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            await service.validate_field_update(
                db=db,
                field_id="field-1",
                new_value="test",
            )

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) == 1
        assert "not found" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_field_update_field_not_editable(self):
        """Test validation with non-editable field."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a computed field
        mock_field = self._create_mock_field(
            name="Formula Field",
            field_type=FieldType.FORMULA.value,
            is_computed=True,
            is_editable=False,
        )
        db.get.return_value = mock_field

        with pytest.raises(ValidationError) as exc_info:
            await service.validate_field_update(
                db=db,
                field_id="field-1",
                new_value="test",
            )

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) == 1
        assert "not editable" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_field_update_required_field_empty(self):
        """Test validation with empty required field."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a required field
        mock_field = self._create_mock_field(
            name="Required Field",
            is_required=True,
        )
        db.get.return_value = mock_field

        with pytest.raises(ValidationError) as exc_info:
            await service.validate_field_update(
                db=db,
                field_id="field-1",
                new_value="",
            )

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) == 1
        assert "is required" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_field_update_validation_error(self):
        """Test field validation error."""
        service = ValidationService()
        db = AsyncMock()

        # Mock an email field
        mock_field = self._create_mock_field(
            name="Email Field",
            field_type=FieldType.EMAIL.value,
        )
        db.get.return_value = mock_field

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        # Mock field handler to raise validation error
        with patch("pybase.services.validation.get_field_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.validate.side_effect = ValueError("Invalid email")
            mock_get_handler.return_value = mock_handler

            with pytest.raises(ValidationError) as exc_info:
                await service.validate_field_update(
                    db=db,
                    field_id="field-1",
                    new_value="not-an-email",
                )

            errors = exc_info.value.details.get("errors", [])
            assert len(errors) == 1
            assert "Invalid value for field" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_validate_field_update_unique_violation(self):
        """Test unique constraint violation on field update."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with unique constraint
        mock_field = self._create_mock_field(
            name="Unique Field",
        )

        mock_constraint = UniqueConstraint(
            id="constraint-1",
            field_id="field-1",
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
            error_message=None,
        )

        db.get.return_value = mock_field

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_constraint
        db.execute.return_value = mock_result

        # Mock duplicate check to return True
        with patch.object(service, "_check_unique_constraint", return_value=True):
            with pytest.raises(ConflictError):
                await service.validate_field_update(
                    db=db,
                    field_id="field-1",
                    new_value="duplicate-value",
                )

    @pytest.mark.asyncio
    async def test_validate_field_update_with_exclusion(self):
        """Test field update with record exclusion."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with unique constraint
        mock_field = self._create_mock_field(
            name="Unique Field",
        )

        mock_constraint = UniqueConstraint(
            id="constraint-1",
            field_id="field-1",
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
            error_message=None,
        )

        db.get.return_value = mock_field

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_constraint
        db.execute.return_value = mock_result

        # Mock duplicate check to return False (no duplicate)
        with patch.object(service, "_check_unique_constraint", return_value=False) as mock_check:
            # Should not raise any error
            await service.validate_field_update(
                db=db,
                field_id="field-1",
                new_value="test-value",
                exclude_record_id="current-record-id",
            )

            # Verify exclusion was passed
            mock_check.assert_called_once()
            call_kwargs = mock_check.call_args[1]
            assert call_kwargs["exclude_record_id"] == "current-record-id"

    @pytest.mark.asyncio
    async def test_validate_field_update_valid_update(self):
        """Test valid field update."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a valid field
        mock_field = self._create_mock_field(
            name="Text Field",
        )

        db.get.return_value = mock_field

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        # Mock field handler
        with patch("pybase.services.validation.get_field_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.validate.return_value = None  # Valid
            mock_get_handler.return_value = mock_handler

            # Should not raise any error
            await service.validate_field_update(
                db=db,
                field_id="field-1",
                new_value="valid text",
            )

    @pytest.mark.asyncio
    async def test_validate_field_update_with_options(self):
        """Test field update validation with field options."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with options
        mock_field = self._create_mock_field(
            name="Number Field",
            field_type=FieldType.NUMBER.value,
            options='{"min": 0, "max": 100}',
        )

        db.get.return_value = mock_field

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        # Mock field handler
        with patch("pybase.services.validation.get_field_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.validate.return_value = None  # Valid
            mock_get_handler.return_value = mock_handler

            # Should not raise any error
            await service.validate_field_update(
                db=db,
                field_id="field-1",
                new_value=50,
            )

            # Verify handler was called with parsed options
            mock_handler.validate.assert_called_once_with(50, {"min": 0, "max": 100})

    @pytest.mark.asyncio
    async def test_validate_field_update_custom_error_message(self):
        """Test field update with custom error message."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a field with custom error message
        mock_field = self._create_mock_field(
            name="SKU",
        )

        mock_constraint = UniqueConstraint(
            id="constraint-1",
            field_id="field-1",
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
            error_message="Custom error: {value}",
        )

        db.get.return_value = mock_field

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_constraint
        db.execute.return_value = mock_result

        # Mock duplicate check to return True
        with patch.object(service, "_check_unique_constraint", return_value=True):
            with pytest.raises(ConflictError) as exc_info:
                await service.validate_field_update(
                    db=db,
                    field_id="field-1",
                    new_value="SKU-123",
                )

            assert "Custom error: SKU-123" in str(exc_info.value)
