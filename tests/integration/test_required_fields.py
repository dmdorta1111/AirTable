"""Integration tests for required field validation."""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import ValidationError
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace
from pybase.models.user import User
from pybase.services.validation import ValidationService


@pytest.fixture
def validation_service():
    """Create a ValidationService instance."""
    return ValidationService()


class TestRequiredFieldValidation:
    """Integration tests for required field validation."""

    @pytest.mark.asyncio
    async def test_required_field_validation_on_create(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test required field validation when creating a record."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="email",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test with None value (should fail)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): None},
            )

        assert "Field 'email' is required" in str(exc_info.value)
        errors = exc_info.value.errors if hasattr(exc_info.value, 'errors') else []
        assert any("email" in str(error.get("field_name", "")) for error in errors)

    @pytest.mark.asyncio
    async def test_required_field_with_empty_string(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test required field validation with empty string."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="name",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test with empty string (should fail)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): ""},
            )

        assert "Field 'name' is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_required_field_with_valid_value(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test required field validation with valid value."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="username",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test with valid value (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): "testuser"},
        )

        # Verify no exception was raised

    @pytest.mark.asyncio
    async def test_multiple_required_fields(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test validation with multiple required fields."""
        # Create workspace, base, table, and fields
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        email_field = Field(
            table_id=table.id,
            name="email",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(email_field)
        await db_session.commit()
        await db_session.refresh(email_field)

        name_field = Field(
            table_id=table.id,
            name="name",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(name_field)
        await db_session.commit()
        await db_session.refresh(name_field)

        # Test with only one field provided (should fail)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(email_field.id): "test@example.com"},
            )

        errors = exc_info.value.errors if hasattr(exc_info.value, 'errors') else []
        assert len(errors) == 1
        assert "name" in str(errors[0].get("field_name", ""))

    @pytest.mark.asyncio
    async def test_optional_field_allows_none(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test that optional fields allow None values."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="optional_field",
            field_type=FieldType.TEXT.value,
            is_required=False,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test with None value (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): None},
        )

    @pytest.mark.asyncio
    async def test_optional_field_allows_empty_string(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test that optional fields allow empty strings."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="optional_field",
            field_type=FieldType.TEXT.value,
            is_required=False,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test with empty string (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): ""},
        )

    @pytest.mark.asyncio
    async def test_required_field_with_number_type(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test required field validation with number field type."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="age",
            field_type=FieldType.NUMBER.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test with None (should fail)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): None},
            )

        assert "Field 'age' is required" in str(exc_info.value)

        # Test with valid number (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): 25},
        )

    @pytest.mark.asyncio
    async def test_required_field_with_boolean_type(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test required field validation with boolean field type."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="is_active",
            field_type=FieldType.CHECKBOX.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test with None (should fail)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): None},
            )

        assert "Field 'is_active' is required" in str(exc_info.value)

        # Test with False (should succeed - False is a valid boolean value)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): False},
        )

        # Test with True (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): True},
        )

    @pytest.mark.asyncio
    async def test_validate_field_update_required_with_none(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test validate_field_update with required field set to None."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="username",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test updating to None (should fail)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_field_update(
                db_session,
                str(field.id),
                None,
            )

        assert "Field 'username' is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_field_update_required_with_valid_value(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test validate_field_update with required field set to valid value."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="username",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test updating to valid value (should succeed)
        await validation_service.validate_field_update(
            db_session,
            str(field.id),
            "new_username",
        )

    @pytest.mark.asyncio
    async def test_mixed_required_and_optional_fields(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test validation with mix of required and optional fields."""
        # Create workspace, base, table, and fields
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        required_field = Field(
            table_id=table.id,
            name="required_field",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(required_field)
        await db_session.commit()
        await db_session.refresh(required_field)

        optional_field = Field(
            table_id=table.id,
            name="optional_field",
            field_type=FieldType.TEXT.value,
            is_required=False,
        )
        db_session.add(optional_field)
        await db_session.commit()
        await db_session.refresh(optional_field)

        # Test with required field provided and optional field as None (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {
                str(required_field.id): "value",
                str(optional_field.id): None,
            },
        )

    @pytest.mark.asyncio
    async def test_required_field_update_to_empty_string(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test updating required field to empty string."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="username",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test updating to empty string (should fail)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_field_update(
                db_session,
                str(field.id),
                "",
            )

        assert "Field 'username' is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_required_field_not_editable(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test required field that is not editable."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="auto_field",
            field_type=FieldType.TEXT.value,
            is_required=True,
            is_editable=False,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test editing non-editable field (should fail with not editable error)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): "value"},
            )

        assert "not editable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_required_field_with_zero_number(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test required field with number value of zero."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="count",
            field_type=FieldType.NUMBER.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test with zero (should succeed - zero is a valid number)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): 0},
        )

    @pytest.mark.asyncio
    async def test_required_field_error_message_format(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test error message format for required field validation."""
        # Create workspace, base, table, and field
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field = Field(
            table_id=table.id,
            name="test_field",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Test error message format
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): None},
            )

        error = exc_info.value
        assert hasattr(error, 'message')
        assert error.message == "Validation failed"

        if hasattr(error, 'errors'):
            errors = error.errors
            assert len(errors) == 1
            assert errors[0]["field_id"] == str(field.id)
            assert errors[0]["field_name"] == "test_field"
            assert "is required" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_multiple_missing_required_fields(
        self,
        db_session: AsyncSession,
        test_user: User,
        validation_service: ValidationService,
    ):
        """Test validation with multiple missing required fields."""
        # Create workspace, base, table, and fields
        workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        base = Base(workspace_id=workspace.id, name="Test Base")
        db_session.add(base)
        await db_session.commit()
        await db_session.refresh(base)

        table = Table(base_id=base.id, name="Test Table")
        db_session.add(table)
        await db_session.commit()
        await db_session.refresh(table)

        field1 = Field(
            table_id=table.id,
            name="field1",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field1)
        await db_session.commit()
        await db_session.refresh(field1)

        field2 = Field(
            table_id=table.id,
            name="field2",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field2)
        await db_session.commit()
        await db_session.refresh(field2)

        field3 = Field(
            table_id=table.id,
            name="field3",
            field_type=FieldType.TEXT.value,
            is_required=True,
        )
        db_session.add(field3)
        await db_session.commit()
        await db_session.refresh(field3)

        # Test with all fields missing (should fail with 3 errors)
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {
                    str(field1.id): None,
                    str(field2.id): None,
                    str(field3.id): "",
                },
            )

        errors = exc_info.value.errors if hasattr(exc_info.value, 'errors') else []
        assert len(errors) == 3
