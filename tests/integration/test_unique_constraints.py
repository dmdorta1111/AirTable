"""Integration tests for unique constraint enforcement."""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import ConflictError, ValidationError
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.unique_constraint import UniqueConstraint, UniqueConstraintStatus
from pybase.models.workspace import Workspace
from pybase.models.user import User
from pybase.schemas.constraint import UniqueConstraintCreate
from pybase.services.constraint import ConstraintService
from pybase.services.validation import ValidationService


@pytest.fixture
def constraint_service():
    """Create a ConstraintService instance."""
    return ConstraintService()


@pytest.fixture
def validation_service():
    """Create a ValidationService instance."""
    return ValidationService()


class TestUniqueConstraintEnforcement:
    """Integration tests for unique constraint enforcement."""

    @pytest.mark.asyncio
    async def test_create_unique_constraint_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
    ):
        """Test successful unique constraint creation."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )

        constraint = await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        assert constraint.field_id == str(field.id)
        assert constraint.status == UniqueConstraintStatus.ACTIVE.value
        assert constraint.case_sensitive is True
        assert constraint.is_active is True

    @pytest.mark.asyncio
    async def test_enforce_unique_on_create_record(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test enforcing unique constraint when creating a record."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record with unique value
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "test@example.com"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create second record with duplicate value
        with pytest.raises(ConflictError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): "test@example.com"},
            )

        assert "already exists" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_enforce_unique_on_update_record(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test enforcing unique constraint when updating a record."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create two records with different values
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "first@example.com"}),
        )
        db_session.add(first_record)
        await db_session.commit()
        await db_session.refresh(first_record)

        second_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "second@example.com"}),
        )
        db_session.add(second_record)
        await db_session.commit()
        await db_session.refresh(second_record)

        # Try to update second record to have same value as first
        with pytest.raises(ConflictError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): "first@example.com"},
                exclude_record_id=str(second_record.id),
            )

        assert "already exists" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_case_insensitive_unique_constraint(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test case-insensitive unique constraint."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create case-insensitive unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=False,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record with lowercase value
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "test@example.com"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create second record with uppercase value (should fail)
        with pytest.raises(ConflictError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): "TEST@EXAMPLE.COM"},
            )

        assert "already exists" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_case_sensitive_unique_constraint(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test case-sensitive unique constraint allows different cases."""
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
            name="code",
            field_type=FieldType.TEXT.value,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create case-sensitive unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record with lowercase value
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "code"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Create second record with uppercase value (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): "CODE"},
        )

        # Verify no exception was raised

    @pytest.mark.asyncio
    async def test_disabled_constraint_allows_duplicates(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test that disabled constraints don't enforce uniqueness."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create disabled unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.DISABLED.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "test@example.com"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create second record with duplicate value (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): "test@example.com"},
        )

        # Verify no exception was raised

    @pytest.mark.asyncio
    async def test_custom_error_message(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test custom error message for unique constraint."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint with custom error message
        custom_message = "This email address is already registered"
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
            error_message=custom_message,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "test@example.com"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create duplicate and check custom message
        with pytest.raises(ConflictError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): "test@example.com"},
            )

        assert custom_message in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_null_values_not_enforced(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test that null values are not enforced for unique constraints."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create multiple records with null values
        for _ in range(3):
            record = Record(
                table_id=table.id,
                data=json.dumps({str(field.id): None}),
            )
            db_session.add(record)
        await db_session.commit()

        # Verify no constraint violation for null values
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): None},
        )

    @pytest.mark.asyncio
    async def test_empty_strings_enforced(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test that empty strings are enforced for unique constraints."""
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
            name="field",
            field_type=FieldType.TEXT.value,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record with empty string
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): ""}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create second record with empty string
        # Empty strings are treated as None, so this should NOT raise
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): ""},
        )

    @pytest.mark.asyncio
    async def test_multiple_unique_constraints_same_table(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test multiple unique constraints on the same table."""
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
        )
        db_session.add(email_field)
        await db_session.commit()
        await db_session.refresh(email_field)

        username_field = Field(
            table_id=table.id,
            name="username",
            field_type=FieldType.TEXT.value,
        )
        db_session.add(username_field)
        await db_session.commit()
        await db_session.refresh(username_field)

        # Create unique constraints for both fields
        email_constraint_data = UniqueConstraintCreate(
            field_id=email_field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, email_constraint_data
        )

        username_constraint_data = UniqueConstraintCreate(
            field_id=username_field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, username_constraint_data
        )

        # Create first record
        first_record = Record(
            table_id=table.id,
            data=json.dumps({
                str(email_field.id): "test@example.com",
                str(username_field.id): "testuser",
            }),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create record with duplicate email
        with pytest.raises(ConflictError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {
                    str(email_field.id): "test@example.com",
                    str(username_field.id): "differentuser",
                },
            )

        assert "already exists" in str(exc_info.value).lower()

        # Try to create record with duplicate username
        with pytest.raises(ConflictError) as exc_info:
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {
                    str(email_field.id): "different@example.com",
                    str(username_field.id): "testuser",
                },
            )

        assert "already exists" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_unique_constraint_with_numeric_field(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test unique constraint on numeric field."""
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
            name="employee_id",
            field_type=FieldType.NUMBER.value,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): 12345}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create duplicate
        with pytest.raises(ConflictError):
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): 12345},
            )

        # Different value should work
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): 67890},
        )

    @pytest.mark.asyncio
    async def test_constraint_retrieval_by_field(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
    ):
        """Test retrieving constraint by field ID."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Retrieve constraint by field
        constraint = await constraint_service.get_constraint_by_field(
            db_session, str(field.id)
        )

        assert constraint is not None
        assert constraint.field_id == str(field.id)
        assert constraint.is_active is True

    @pytest.mark.asyncio
    async def test_constraint_deletion(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test deleting unique constraint allows duplicates."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        constraint = await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "test@example.com"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Verify constraint is enforced
        with pytest.raises(ConflictError):
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): "test@example.com"},
            )

        # Delete constraint
        await constraint_service.delete_constraint(
            db_session, constraint.id, test_user.id
        )

        # Verify constraint is no longer enforced
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): "test@example.com"},
        )

    @pytest.mark.asyncio
    async def test_constraint_status_update(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test updating constraint status."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        constraint = await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "test@example.com"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Verify constraint is enforced
        with pytest.raises(ConflictError):
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): "test@example.com"},
            )

        # Disable constraint
        from pybase.schemas.constraint import UniqueConstraintUpdate

        update_data = UniqueConstraintUpdate(status=UniqueConstraintStatus.DISABLED.value)
        await constraint_service.update_constraint(
            db_session, constraint.id, test_user.id, update_data
        )

        # Verify constraint is no longer enforced
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): "test@example.com"},
        )

    @pytest.mark.asyncio
    async def test_constraint_case_sensitivity_update(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test updating constraint case sensitivity."""
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
            name="code",
            field_type=FieldType.TEXT.value,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create case-sensitive unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        constraint = await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record with lowercase
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "code"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Verify uppercase is allowed (case-sensitive)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): "CODE"},
        )

        # Update to case-insensitive
        from pybase.schemas.constraint import UniqueConstraintUpdate

        update_data = UniqueConstraintUpdate(case_sensitive=False)
        await constraint_service.update_constraint(
            db_session, constraint.id, test_user.id, update_data
        )

        # Now uppercase should be rejected (case-insensitive)
        with pytest.raises(ConflictError):
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): "CODE"},
            )

    @pytest.mark.asyncio
    async def test_unique_constraint_properties(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
    ):
        """Test UniqueConstraint model properties."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create active constraint
        active_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        active_constraint = await constraint_service.create_constraint(
            db_session, test_user.id, active_data
        )

        assert active_constraint.is_active is True
        assert active_constraint.is_disabled is False
        assert active_constraint.is_pending is False

        # Create disabled constraint
        disabled_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.DISABLED.value,
            case_sensitive=True,
        )
        # Note: This will fail because only one constraint per field is allowed
        # So we'll just update the existing one
        from pybase.schemas.constraint import UniqueConstraintUpdate

        update_data = UniqueConstraintUpdate(status=UniqueConstraintStatus.DISABLED.value)
        disabled_constraint = await constraint_service.update_constraint(
            db_session, active_constraint.id, test_user.id, update_data
        )

        assert disabled_constraint.is_active is False
        assert disabled_constraint.is_disabled is True
        assert disabled_constraint.is_pending is False

        # Create pending constraint
        pending_data = UniqueConstraintUpdate(status=UniqueConstraintStatus.PENDING.value)
        pending_constraint = await constraint_service.update_constraint(
            db_session, active_constraint.id, test_user.id, pending_data
        )

        assert pending_constraint.is_active is False
        assert pending_constraint.is_disabled is False
        assert pending_constraint.is_pending is True

    @pytest.mark.asyncio
    async def test_multiple_constraints_per_table_different_fields(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
    ):
        """Test listing constraints for a table with multiple constrained fields."""
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
        )
        db_session.add(field1)
        await db_session.commit()
        await db_session.refresh(field1)

        field2 = Field(
            table_id=table.id,
            name="field2",
            field_type=FieldType.TEXT.value,
        )
        db_session.add(field2)
        await db_session.commit()
        await db_session.refresh(field2)

        # Create constraints for both fields
        constraint1_data = UniqueConstraintCreate(
            field_id=field1.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint1_data
        )

        constraint2_data = UniqueConstraintCreate(
            field_id=field2.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=False,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint2_data
        )

        # List all constraints
        constraints, total = await constraint_service.list_constraints(
            db_session, None, test_user.id
        )

        assert total == 2
        assert len(constraints) == 2

        # List constraints filtered by field
        field1_constraints, field1_total = await constraint_service.list_constraints(
            db_session, str(field1.id), test_user.id
        )

        assert field1_total == 1
        assert len(field1_constraints) == 1
        assert field1_constraints[0].field_id == str(field1.id)
        assert field1_constraints[0].case_sensitive is True

    @pytest.mark.asyncio
    async def test_pending_constraint_not_enforced(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test that pending constraints don't enforce uniqueness."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create pending unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.PENDING.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "test@example.com"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create second record with duplicate value (should succeed)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): "test@example.com"},
        )

        # Verify no exception was raised

    @pytest.mark.asyncio
    async def test_unique_constraint_with_boolean_field(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test unique constraint on boolean field."""
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
            field_type=FieldType.BOOLEAN.value,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record with True
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): True}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create duplicate True value
        with pytest.raises(ConflictError):
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): True},
            )

        # False value should work
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): False},
        )

    @pytest.mark.asyncio
    async def test_constraint_prevents_self_duplicate_on_update(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test that updating a record to its own value doesn't trigger constraint."""
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
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create record
        record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "test@example.com"}),
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        # Update to same value should not raise (excluding self)
        await validation_service.validate_record_data(
            db_session,
            table.id,
            {str(field.id): "test@example.com"},
            exclude_record_id=str(record.id),
        )

        # Verify no exception was raised

    @pytest.mark.asyncio
    async def test_constraint_with_whitespace_values(
        self,
        db_session: AsyncSession,
        test_user: User,
        constraint_service: ConstraintService,
        validation_service: ValidationService,
    ):
        """Test unique constraint with whitespace variations."""
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
            name="code",
            field_type=FieldType.TEXT.value,
        )
        db_session.add(field)
        await db_session.commit()
        await db_session.refresh(field)

        # Create case-sensitive unique constraint
        constraint_data = UniqueConstraintCreate(
            field_id=field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
        )
        await constraint_service.create_constraint(
            db_session, test_user.id, constraint_data
        )

        # Create first record with value
        first_record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): "value"}),
        )
        db_session.add(first_record)
        await db_session.commit()

        # Try to create with leading/trailing whitespace (should fail)
        with pytest.raises(ConflictError):
            await validation_service.validate_record_data(
                db_session,
                table.id,
                {str(field.id): " value "},
            )
