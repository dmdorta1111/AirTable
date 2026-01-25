# PyBase Data Integrity Examples

> Practical code examples for using unique constraints, field validation, and transaction management

## Table of Contents

- [Unique Constraints](#unique-constraints)
- [Field Validation](#field-validation)
- [Transaction Management](#transaction-management)
- [Error Handling](#error-handling)
- [Common Patterns](#common-patterns)

---

## Unique Constraints

### Creating a Unique Constraint via API

```bash
# Create a unique constraint on Email field
POST /constraints
{
  "field_id": "uuid-of-email-field",
  "case_sensitive": false,
  "error_message": "This email address is already registered"
}

# Response
{
  "id": "constraint-uuid",
  "field_id": "uuid-of-email-field",
  "case_sensitive": false,
  "status": "active",
  "error_message": "This email address is already registered",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Case-Insensitive Unique Constraint

```bash
POST /constraints
{
  "field_id": "uuid-of-username-field",
  "case_sensitive": false,
  "error_message": "Username '{value}' is already taken"
}

# These will conflict:
# "JohnDoe" = "johndoe" ✓ (case-insensitive match)
```

### Using the ConstraintService in Python

```python
from pybase.services.constraint import ConstraintService
from pybase.schemas.constraint import UniqueConstraintCreate
from pybase.models.unique_constraint import UniqueConstraintStatus

# Create service instance
constraint_service = ConstraintService()

# Prepare constraint data
constraint_data = UniqueConstraintCreate(
    field_id="uuid-of-email-field",
    status=UniqueConstraintStatus.ACTIVE.value,
    case_sensitive=True,
    error_message="This email is already registered"
)

# Create constraint
constraint = await constraint_service.create_constraint(
    db=db_session,
    user_id=current_user.id,
    constraint_data=constraint_data
)

print(f"Constraint created: {constraint.id}")
```

### Updating a Constraint Status

```bash
# Disable constraint temporarily
PATCH /constraints/{constraint_id}
{
  "status": "disabled"
}

# Re-enable constraint
PATCH /constraints/{constraint_id}
{
  "status": "active"
}
```

### Python: Update Constraint

```python
from pybase.schemas.constraint import UniqueConstraintUpdate

# Update constraint
updated_constraint = await constraint_service.update_constraint(
    db=db_session,
    constraint_id=constraint_id,
    user_id=current_user.id,
    constraint_data=UniqueConstraintUpdate(
        status=UniqueConstraintStatus.DISABLED.value,
        case_sensitive=False
    )
)
```

### Listing Constraints

```bash
# Get all constraints for a field
GET /constraints?field_id={field_id}

# Get all constraints in table (via field list)
GET /fields?table_id={table_id}
# Then check each field for constraints
```

### Python: List Constraints

```python
# List constraints for a specific field
constraints, total = await constraint_service.list_constraints(
    db=db_session,
    field_id=field_id,
    user_id=current_user.id,
    page=1,
    page_size=20
)

for constraint in constraints:
    print(f"Field: {constraint.field_id}, Status: {constraint.status}")
```

---

## Field Validation

### Creating a Required Field

```bash
# Create a required field
POST /fields
{
  "table_id": "table-uuid",
  "name": "Email",
  "field_type": "text",
  "is_required": true,
  "is_editable": true
}
```

### Python: Validating Record Data

```python
from pybase.services.validation import ValidationService

# Create service instance
validation_service = ValidationService()

# Validate record data before creation
try:
    await validation_service.validate_record_data(
        db=db_session,
        table_id=table_id,
        data={
            "field-id-1": "value1",
            "field-id-2": "value2"
        }
    )
    print("Validation passed")
except ValidationError as e:
    print(f"Validation failed: {e}")
    for error in e.errors:
        print(f"  Field: {error.get('field_name')}")
        print(f"  Message: {error.get('message')}")
```

### Validating Single Field Update

```python
# Validate field update
try:
    await validation_service.validate_field_update(
        db=db_session,
        field_id=field_id,
        new_value="new value",
        exclude_record_id=record_id  # Exclude current record for unique checks
    )
    print("Field validation passed")
except ValidationError as e:
    print(f"Validation failed: {e}")
except ConflictError as e:
    print(f"Duplicate value: {e}")
```

### Required Field Validation

```python
# This will raise ValidationError
await validation_service.validate_record_data(
    db=db_session,
    table_id=table_id,
    data={
        "required-field-id": None  # Required field with None
    }
)

# This will also raise ValidationError
await validation_service.validate_record_data(
    db=db_session,
    table_id=table_id,
    data={
        "required-field-id": ""  # Required field with empty string
    }
)
```

### Custom Error Messages

```bash
# Create constraint with custom error message
POST /constraints
{
  "field_id": "field-uuid",
  "error_message": "SKU {value} already exists in inventory"
}

# When duplicate is entered:
{
  "detail": "SKU ABC-123 already exists in inventory",
  "code": "DUPLICATE_VALUE"
}
```

---

## Transaction Management

### Automatic Rollback on Error

```bash
# Try to create multiple records
POST /records/batch
{
  "table_id": "table-uuid",
  "records": [
    {"fields": {"Name": "Record 1", "Email": "valid1@example.com"}},
    {"fields": {"Name": "Record 2", "Email": "valid2@example.com"}},
    {"fields": {"Name": "Record 3", "Email": "duplicate@example.com"}}  # Violates unique constraint
  ]
}

# Response (409 Conflict)
{
  "detail": "A record with this value already exists",
  "code": "DUPLICATE_VALUE",
  "field": "Email",
  "index": 2
}

# Database state: Zero new records (all rolled back)
```

### Python: Transaction Rollback Example

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def create_multiple_records(db: AsyncSession, table_id: str, records_data: list):
    """Create multiple records with automatic rollback on error."""
    try:
        for record_data in records_data:
            # Validate first
            await validation_service.validate_record_data(
                db=db,
                table_id=table_id,
                data=record_data
            )

            # Create record
            record = Record(table_id=table_id, data=json.dumps(record_data))
            db.add(record)

        # If we get here, all validations passed
        # The dependency layer will commit automatically
        # If any error occurred, it will rollback everything

    except (ValidationError, ConflictError) as e:
        # Transaction will be rolled back by dependency layer
        raise e
```

### Batch Update with Rollback

```bash
PATCH /records/batch
{
  "table_id": "table-uuid",
  "updates": [
    {"record_id": "uuid1", "fields": {"Status": "Active"}},
    {"record_id": "uuid2", "fields": {"Email": null}},  # Violates required field
    {"record_id": "uuid3", "fields": {"Status": "Pending"}}
  ]
}

# Response (422 Validation Error)
{
  "detail": "Field is required",
  "code": "REQUIRED_FIELD",
  "field": "Email",
  "record_id": "uuid2"
}

# Database state: All records unchanged (transaction rolled back)
```

### Python: Transaction Isolation

```python
# All operations share the same transaction
async def update_field_and_records(
    db: AsyncSession,
    field_id: str,
    updates: list
):
    """Update field definition and records in one transaction."""
    # Both operations share the same db session
    # If any fails, both are rolled back

    # Update field
    field = await db.get(Field, field_id)
    field.is_required = True

    # Update records
    for update in updates:
        record = await db.get(Record, update['record_id'])
        data = json.loads(record.data)
        data.update(update['fields'])
        record.data = json.dumps(data)

    # Commit happens at dependency layer
    # If any error occurs, everything is rolled back
```

---

## Error Handling

### Handling Unique Constraint Violations

```python
from pybase.core.exceptions import ConflictError

try:
    await record_service.create_record(
        db=db_session,
        table_id=table_id,
        data={"email": "duplicate@example.com"}
    )
except ConflictError as e:
    if "already exists" in str(e):
        print(f"Duplicate value error: {e}")
        # Handle duplicate gracefully
        return {
            "success": False,
            "error": "duplicate_value",
            "message": str(e)
        }
```

### Handling Validation Errors

```python
from pybase.core.exceptions import ValidationError

try:
    await validation_service.validate_record_data(
        db=db_session,
        table_id=table_id,
        data={"name": "", "email": None}
    )
except ValidationError as e:
    # Extract field-specific errors
    field_errors = {}
    for error in e.errors:
        field_name = error.get('field_name', error.get('field_id'))
        field_errors[field_name] = error.get('message')

    return {
        "success": False,
        "error": "validation_failed",
        "fields": field_errors
    }
```

### API Error Response Format

```json
{
  "detail": "Validation failed",
  "code": "VALIDATION_ERROR",
  "errors": [
    {
      "loc": ["Email"],
      "msg": "Field is required",
      "type": "value_error.required"
    },
    {
      "loc": ["Name"],
      "msg": "Field 'Name' is required",
      "type": "value_error.required"
    }
  ]
}
```

### Error Codes Reference

| Code | Status | Description |
|------|--------|-------------|
| `DUPLICATE_VALUE` | 409 | Unique constraint violated |
| `REQUIRED_FIELD` | 422 | Required field missing or empty |
| `VALIDATION_ERROR` | 422 | Field value validation failed |
| `FOREIGN_KEY_VIOLATION` | 409 | Referenced record doesn't exist |
| `CONSTRAINT_DISABLED` | 423 | Constraint is currently disabled |
| `CONSTRAINT_PENDING` | 423 | Constraint creation in progress |

---

## Common Patterns

### Email Uniqueness Pattern

```python
# 1. Create email field
email_field = Field(
    table_id=table_id,
    name="Email",
    field_type=FieldType.TEXT.value,
    is_required=True,
    is_unique=True
)

# 2. Add unique constraint (case-insensitive)
constraint = UniqueConstraintCreate(
    field_id=email_field.id,
    case_sensitive=False,
    error_message="Email {value} is already registered"
)

await constraint_service.create_constraint(db, user_id, constraint)

# 3. Handle in application
try:
    await record_service.create_record(
        db=db,
        table_id=table_id,
        data={str(email_field.id): "user@example.com"}
    )
except ConflictError as e:
    if "already registered" in str(e):
        # Handle duplicate email
        pass
```

### SKU/Product Code Pattern

```python
# Ensure product codes are unique
sku_field = Field(
    table_id=table_id,
    name="SKU",
    field_type=FieldType.TEXT.value,
    is_required=True
)

# Case-sensitive unique constraint
constraint = UniqueConstraintCreate(
    field_id=sku_field.id,
    case_sensitive=True,  # SKU-123 != sku-123
    error_message="Product SKU {value} already exists"
)
```

### Slug/URL Pattern with Validation

```python
# Create slug field with validation
slug_field = Field(
    table_id=table_id,
    name="Slug",
    field_type=FieldType.TEXT.value,
    is_required=True,
    options=json.dumps({
        "pattern": "^[a-z0-9-]+$",  # Only lowercase, numbers, hyphens
        "max_length": 100
    })
)

# Add unique constraint
constraint = UniqueConstraintCreate(
    field_id=slug_field.id,
    case_sensitive=False,  # URLs are typically case-insensitive
    error_message="URL slug {value} is already in use"
)
```

### Conditional Validation Pattern

```python
# Validate based on other field values
async def validate_record_with_logic(db: AsyncSession, table_id: str, data: dict):
    """Custom validation with business logic."""

    # Standard validation
    await validation_service.validate_record_data(db, table_id, data)

    # Custom logic: if status is "published", require publish_date
    if data.get("status") == "published":
        if not data.get("publish_date"):
            raise ValidationError(
                message="Validation failed",
                errors=[{
                    "field_id": "publish_date",
                    "message": "Publish date is required when status is 'published'"
                }]
            )
```

### Bulk Import with Validation

```python
async def import_records_safe(
    db: AsyncSession,
    table_id: str,
    records_data: list[dict]
):
    """Import multiple records with full validation and rollback."""

    results = {
        "success": [],
        "failed": [],
        "total": len(records_data)
    }

    # Validate all records first (no database writes)
    validation_errors = []
    for idx, record_data in enumerate(records_data):
        try:
            await validation_service.validate_record_data(
                db=db,
                table_id=table_id,
                data=record_data
            )
            results["success"].append(idx)
        except (ValidationError, ConflictError) as e:
            validation_errors.append({
                "index": idx,
                "error": str(e),
                "data": record_data
            })
            results["failed"].append(idx)

    if validation_errors:
        # Return validation results without writing anything
        return {
            **results,
            "validation_errors": validation_errors,
            "committed": False
        }

    # All validations passed - create records in one transaction
    try:
        for record_data in records_data:
            record = Record(
                table_id=table_id,
                data=json.dumps(record_data)
            )
            db.add(record)

        # Commit happens at dependency layer
        return {**results, "committed": True}

    except Exception as e:
        # Transaction rolled back automatically
        return {
            **results,
            "committed": False,
            "error": str(e)
        }
```

### Testing Constraints

```python
import pytest
from pybase.core.exceptions import ConflictError

async def test_unique_constraint_enforcement():
    """Test that unique constraint prevents duplicates."""

    # Create first record
    await record_service.create_record(
        db=db,
        table_id=table_id,
        data={"email": "test@example.com"}
    )

    # Try to create duplicate
    with pytest.raises(ConflictError) as exc:
        await record_service.create_record(
            db=db,
            table_id=table_id,
            data={"email": "test@example.com"}
        )

    assert "already exists" in str(exc.value)
```

---

## Best Practices

### 1. Always Validate Before Database Operations

```python
# Good: Validate first
await validation_service.validate_record_data(db, table_id, data)
record = Record(table_id=table_id, data=json.dumps(data))
db.add(record)

# Avoid: Direct creation without validation
record = Record(table_id=table_id, data=json.dumps(data))
db.add(record)  # May fail after transaction starts
```

### 2. Use Custom Error Messages

```python
# Good: Clear, actionable error messages
constraint = UniqueConstraintCreate(
    field_id=email_field.id,
    error_message="The email {value} is already registered. Please use a different email or log in."
)

# Avoid: Generic errors
constraint = UniqueConstraintCreate(
    field_id=email_field.id,
    error_message="Duplicate value"
)
```

### 3. Leverage Case Sensitivity

```python
# Use case-insensitive for user-facing identifiers
username_constraint = UniqueConstraintCreate(
    field_id=username_field.id,
    case_sensitive=False  # "JohnDoe" = "johndoe"
)

# Use case-sensitive for codes/IDs
sku_constraint = UniqueConstraintCreate(
    field_id=sku_field.id,
    case_sensitive=True  # "ABC-123" != "abc-123"
)
```

### 4. Handle Errors Gracefully

```python
try:
    record = await record_service.create_record(db, table_id, data)
except ConflictError as e:
    # User-friendly error
    return {"error": "duplicate", "message": str(e)}
except ValidationError as e:
    # Detailed field errors
    return {"error": "invalid", "fields": e.errors}
except Exception as e:
    # Unexpected error
    logger.error(f"Unexpected error: {e}")
    return {"error": "server_error"}
```

### 5. Test Transaction Rollback

```python
async def test_transaction_rollback():
    """Verify that errors roll back all changes."""

    initial_count = await count_records(db, table_id)

    # Try to create invalid record
    try:
        await record_service.create_record(
            db=db,
            table_id=table_id,
            data={"required_field": None}  # Invalid
        )
    except ValidationError:
        pass

    # Verify no records were created
    final_count = await count_records(db, table_id)
    assert initial_count == final_count
```

---

## Additional Resources

- [API Reference](./api.md) - Complete API documentation
- [System Architecture](./system-architecture.md) - Architecture overview
- [Code Standards](./code-standards.md) - Coding guidelines
- [Testing Guide](./deployment-guide.md) - Testing strategies
