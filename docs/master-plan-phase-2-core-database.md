# Phase 2: Core Database & Field Types
## PyBase Master Plan - Weeks 6-10

**Duration:** 5 Weeks  
**Status:** 🔄 PARTIAL COMPLETION (January 2026)  
**Team Focus:** Backend Lead + Database Engineer  
**Dependencies:** Phase 1 Complete (Foundation & Infrastructure)

---

## 📋 Phase Status Overview

**Implementation Status:** 🔄 Partial  
**Testing Coverage:** ✅ API tests implemented  
**Documentation:** 🔄 Needs updating with current status  

### ✅ Completed Components
- ✅ Complete CRUD operations for core entities (Workspace, Base, Table, Field, Record)
- ✅ Basic field type system implemented (Text, Number, Date, Checkbox)
- ✅ Comprehensive API endpoints for all entities
- ✅ Service layer architecture
- ✅ Pydantic schemas for data validation

### 🔄 Work in Progress
- 🔄 Advanced field types (dimension, gdt, material, etc.)
- 🔄 Formula engine implementation
- 🔄 Field validation system
- 🔄 Linked record relationships

---

## Phase Objectives

✅ 1. Implement complete CRUD operations for all core entities  
🟡 2. Build comprehensive field type system (30+ types) - Basic types done  
🟡 3. Create field handler architecture with validation - Architecture done, validation pending  
❌ 4. Implement formula engine basics - Not started  
❌ 5. Build record linking and relationships - Not started  
✅ 6. Create comprehensive API endpoints - Complete

---

## Week-by-Week Breakdown

### Week 6: Workspace, Base, and Table CRUD ✅

#### Tasks

| ID | Task | Status | Priority | Estimate | Notes |
|----|------|---------|----------|----------|-------|
| 2.6.1 | Create WorkspaceService with CRUD operations | ✅ | Critical | 4h | Complete CRUD operations |
| 2.6.2 | Create Workspace API endpoints | ✅ | Critical | 4h | All workspace endpoints implemented |
| 2.6.3 | Implement workspace member management | ✅ | High | 4h | Member management working |
| 2.6.4 | Create BaseService with CRUD operations | ✅ | Critical | 4h | Base service complete |
| 2.6.5 | Create Base API endpoints | ✅ | Critical | 4h | Base endpoints implemented |
| 2.6.6 | Create TableService with CRUD operations | ✅ | Critical | 4h | Table service complete |
| 2.6.7 | Create Table API endpoints | ✅ | Critical | 4h | Table endpoints implemented |
| 2.6.8 | Implement permission checking middleware | ✅ | High | 4h | Permission checking active |
| 2.6.9 | Write integration tests for all endpoints | ✅ | Critical | 6h | Integration tests implemented |
| 2.6.10 | Create Pydantic schemas for all entities | ✅ | High | 4h | Schemas created for all models |

#### Deliverables

- ✅ `POST /api/v1/workspaces` - Create workspace
- ✅ `GET /api/v1/workspaces` - List user workspaces
- ✅ `GET /api/v1/workspaces/{id}` - Get workspace details
- ✅ `PATCH /api/v1/workspaces/{id}` - Update workspace
- ✅ `DELETE /api/v1/workspaces/{id}` - Delete workspace
- ✅ `POST /api/v1/workspaces/{id}/members` - Add member
- ✅ `DELETE /api/v1/workspaces/{id}/members/{user_id}` - Remove member
- ✅ `POST /api/v1/bases` - Create base
- ✅ `GET /api/v1/bases/{id}` - Get base with tables
- [ ] `POST /api/v1/bases/{id}/tables` - Create table
- [ ] `GET /api/v1/tables/{id}` - Get table with fields

#### Service Pattern

**app/services/base_service.py**
```python
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import BaseModel
from app.models.workspace import Workspace
from app.schemas.base import BaseCreate, BaseUpdate


class BaseService:
    """Service for Base operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self, 
        workspace_id: UUID, 
        data: BaseCreate,
        created_by: UUID,
    ) -> BaseModel:
        """Create a new base"""
        base = BaseModel(
            workspace_id=workspace_id,
            name=data.name,
            description=data.description,
            color=data.color,
            icon=data.icon,
        )
        self.db.add(base)
        await self.db.commit()
        await self.db.refresh(base)
        return base
    
    async def get_by_id(
        self, 
        base_id: UUID, 
        include_tables: bool = False,
    ) -> Optional[BaseModel]:
        """Get base by ID"""
        query = select(BaseModel).where(BaseModel.id == base_id)
        
        if include_tables:
            query = query.options(selectinload(BaseModel.tables))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_workspace(
        self, 
        workspace_id: UUID,
    ) -> Sequence[BaseModel]:
        """Get all bases in a workspace"""
        query = (
            select(BaseModel)
            .where(BaseModel.workspace_id == workspace_id)
            .order_by(BaseModel.created_at)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update(
        self, 
        base_id: UUID, 
        data: BaseUpdate,
    ) -> Optional[BaseModel]:
        """Update base"""
        base = await self.get_by_id(base_id)
        if not base:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(base, field, value)
        
        await self.db.commit()
        await self.db.refresh(base)
        return base
    
    async def delete(self, base_id: UUID) -> bool:
        """Delete base and all associated data"""
        base = await self.get_by_id(base_id)
        if not base:
            return False
        
        await self.db.delete(base)
        await self.db.commit()
        return True
    
    async def get_schema(self, base_id: UUID) -> Optional[dict]:
        """Get complete base schema (tables, fields, views)"""
        query = (
            select(BaseModel)
            .where(BaseModel.id == base_id)
            .options(
                selectinload(BaseModel.tables)
                .selectinload(Table.fields),
                selectinload(BaseModel.tables)
                .selectinload(Table.views),
            )
        )
        result = await self.db.execute(query)
        base = result.scalar_one_or_none()
        
        if not base:
            return None
        
        return {
            "id": str(base.id),
            "name": base.name,
            "tables": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "fields": [
                        {
                            "id": str(f.id),
                            "name": f.name,
                            "type": f.field_type,
                            "config": f.config,
                        }
                        for f in t.fields
                    ],
                    "views": [
                        {
                            "id": str(v.id),
                            "name": v.name,
                            "type": v.view_type,
                        }
                        for v in t.views
                    ],
                }
                for t in base.tables
            ],
        }
```

---

### Week 7: Field Type System - Standard Types

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 2.7.1 | Create FieldHandler abstract base class | Critical | 3h | 2.6.* |
| 2.7.2 | Implement TextFieldHandler | Critical | 2h | 2.7.1 |
| 2.7.3 | Implement LongTextFieldHandler | Critical | 2h | 2.7.1 |
| 2.7.4 | Implement NumberFieldHandler | Critical | 3h | 2.7.1 |
| 2.7.5 | Implement CurrencyFieldHandler | High | 2h | 2.7.4 |
| 2.7.6 | Implement PercentFieldHandler | High | 2h | 2.7.4 |
| 2.7.7 | Implement DateFieldHandler | Critical | 3h | 2.7.1 |
| 2.7.8 | Implement DateTimeFieldHandler | High | 2h | 2.7.7 |
| 2.7.9 | Implement TimeFieldHandler | High | 2h | 2.7.7 |
| 2.7.10 | Implement DurationFieldHandler | Medium | 2h | 2.7.4 |
| 2.7.11 | Implement CheckboxFieldHandler | Critical | 2h | 2.7.1 |
| 2.7.12 | Implement SingleSelectFieldHandler | Critical | 4h | 2.7.1 |
| 2.7.13 | Implement MultiSelectFieldHandler | Critical | 3h | 2.7.12 |
| 2.7.14 | Implement StatusFieldHandler | High | 3h | 2.7.12 |
| 2.7.15 | Create field handler registry | Critical | 2h | 2.7.* |
| 2.7.16 | Write unit tests for all handlers | Critical | 6h | 2.7.* |

#### Deliverables

- [ ] FieldHandler base class with abstract methods
- [ ] 14 standard field type handlers implemented
- [ ] Field handler registry for dynamic lookup
- [ ] Unit tests with > 90% coverage for handlers
- [ ] Field configuration validation

#### Field Handler Architecture

**app/core/fields/base.py**
```python
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from enum import Enum


class FieldType(str, Enum):
    """All supported field types"""
    
    # Basic Types
    TEXT = "text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENT = "percent"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    DURATION = "duration"
    CHECKBOX = "checkbox"
    
    # Selection Types
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    STATUS = "status"
    
    # Relationship Types
    LINK = "link"
    LOOKUP = "lookup"
    ROLLUP = "rollup"
    
    # Media Types
    ATTACHMENT = "attachment"
    
    # Contact Types
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    
    # Computed Types
    FORMULA = "formula"
    AUTONUMBER = "autonumber"
    CREATED_TIME = "created_time"
    MODIFIED_TIME = "modified_time"
    CREATED_BY = "created_by"
    MODIFIED_BY = "modified_by"
    
    # Advanced Types
    RATING = "rating"
    BARCODE = "barcode"
    BUTTON = "button"
    
    # Engineering Types (NEW)
    DIMENSION = "dimension"
    GDT = "gdt"
    THREAD = "thread"
    SURFACE_FINISH = "surface_finish"
    MATERIAL = "material"
    DRAWING_REF = "drawing_ref"
    BOM_ITEM = "bom_item"
    REVISION_HISTORY = "revision_history"


class ValidationResult:
    """Result of field validation"""
    
    def __init__(self, valid: bool, error: Optional[str] = None):
        self.valid = valid
        self.error = error
    
    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(valid=True)
    
    @classmethod
    def failure(cls, error: str) -> "ValidationResult":
        return cls(valid=False, error=error)


class FieldHandler(ABC):
    """Abstract base class for field type handlers"""
    
    field_type: FieldType
    
    @abstractmethod
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        """Validate a value against field configuration"""
        pass
    
    @abstractmethod
    def serialize(self, value: Any, config: Dict[str, Any]) -> Any:
        """Convert value to storage format (JSONB-compatible)"""
        pass
    
    @abstractmethod
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Any:
        """Convert from storage format to Python type"""
        pass
    
    @abstractmethod
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        """Format value for display"""
        pass
    
    @abstractmethod
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> Any:
        """Return sortable representation of value"""
        pass
    
    def get_default_value(self, config: Dict[str, Any]) -> Any:
        """Get default value for this field type"""
        return None
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for this field type"""
        return {}
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate field configuration"""
        return ValidationResult.success()
    
    def filter(
        self, 
        value: Any, 
        operator: str, 
        filter_value: Any, 
        config: Dict[str, Any]
    ) -> bool:
        """Evaluate filter condition"""
        operators = {
            "equals": lambda: value == filter_value,
            "not_equals": lambda: value != filter_value,
            "is_empty": lambda: value is None or value == "",
            "is_not_empty": lambda: value is not None and value != "",
            "contains": lambda: str(filter_value).lower() in str(value or "").lower(),
            "not_contains": lambda: str(filter_value).lower() not in str(value or "").lower(),
        }
        return operators.get(operator, lambda: False)()
```

**app/core/fields/standard/number.py**
```python
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from app.core.fields.base import FieldHandler, FieldType, ValidationResult


class NumberFieldHandler(FieldHandler):
    """Handler for number fields"""
    
    field_type = FieldType.NUMBER
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        if value is None:
            return ValidationResult.success()
        
        try:
            num = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return ValidationResult.failure("Invalid number format")
        
        if not config.get("allow_negative", True) and num < 0:
            return ValidationResult.failure("Negative values not allowed")
        
        min_val = config.get("min_value")
        if min_val is not None and num < Decimal(str(min_val)):
            return ValidationResult.failure(f"Value below minimum of {min_val}")
        
        max_val = config.get("max_value")
        if max_val is not None and num > Decimal(str(max_val)):
            return ValidationResult.failure(f"Value exceeds maximum of {max_val}")
        
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Optional[float]:
        if value is None:
            return None
        return float(Decimal(str(value)))
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Optional[Decimal]:
        if value is None:
            return None
        return Decimal(str(value))
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        if value is None:
            return ""
        
        precision = config.get("precision", 2)
        format_type = config.get("format", "decimal")
        
        num = Decimal(str(value))
        
        if format_type == "integer":
            return f"{int(num):,}"
        elif format_type == "comma_separated":
            return f"{num:,.{precision}f}"
        else:
            return f"{num:.{precision}f}"
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> float:
        if value is None:
            return float("-inf")
        return float(value)
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "precision": 2,
            "allow_negative": True,
            "format": "decimal",
        }
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        precision = config.get("precision")
        if precision is not None and (precision < 0 or precision > 10):
            return ValidationResult.failure("Precision must be between 0 and 10")
        
        min_val = config.get("min_value")
        max_val = config.get("max_value")
        if min_val is not None and max_val is not None:
            if Decimal(str(min_val)) > Decimal(str(max_val)):
                return ValidationResult.failure("min_value cannot be greater than max_value")
        
        return ValidationResult.success()
    
    def filter(
        self, 
        value: Any, 
        operator: str, 
        filter_value: Any, 
        config: Dict[str, Any]
    ) -> bool:
        if value is None:
            if operator == "is_empty":
                return True
            if operator == "is_not_empty":
                return False
            return False
        
        try:
            num = Decimal(str(value))
            filter_num = Decimal(str(filter_value)) if filter_value is not None else None
        except (InvalidOperation, ValueError):
            return False
        
        operators = {
            "equals": lambda: num == filter_num,
            "not_equals": lambda: num != filter_num,
            "greater_than": lambda: num > filter_num,
            "less_than": lambda: num < filter_num,
            "greater_or_equal": lambda: num >= filter_num,
            "less_or_equal": lambda: num <= filter_num,
            "is_empty": lambda: False,
            "is_not_empty": lambda: True,
        }
        
        return operators.get(operator, lambda: False)()
```

**app/core/fields/standard/select.py**
```python
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.fields.base import FieldHandler, FieldType, ValidationResult


class SingleSelectFieldHandler(FieldHandler):
    """Handler for single select fields"""
    
    field_type = FieldType.SINGLE_SELECT
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        if value is None:
            return ValidationResult.success()
        
        if not isinstance(value, str):
            return ValidationResult.failure("Value must be a string")
        
        options = config.get("options", [])
        option_names = [opt["name"] for opt in options]
        
        if value not in option_names:
            if config.get("allow_new_options", True):
                return ValidationResult.success()
            return ValidationResult.failure(f"Invalid option: {value}")
        
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Optional[str]:
        if value is None:
            return None
        return str(value)
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Optional[str]:
        return value
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        return str(value) if value else ""
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> str:
        return (value or "").lower()
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "options": [],
            "allow_new_options": True,
        }
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        options = config.get("options", [])
        
        if not isinstance(options, list):
            return ValidationResult.failure("options must be a list")
        
        seen_names = set()
        for opt in options:
            if not isinstance(opt, dict):
                return ValidationResult.failure("Each option must be an object")
            
            name = opt.get("name")
            if not name:
                return ValidationResult.failure("Each option must have a name")
            
            if name in seen_names:
                return ValidationResult.failure(f"Duplicate option name: {name}")
            seen_names.add(name)
        
        return ValidationResult.success()
    
    def add_option(
        self, 
        config: Dict[str, Any], 
        name: str, 
        color: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a new option to the field configuration"""
        options = config.get("options", []).copy()
        
        # Check for duplicates
        if any(opt["name"] == name for opt in options):
            return config
        
        options.append({
            "id": str(uuid4()),
            "name": name,
            "color": color or "gray",
        })
        
        return {**config, "options": options}


class MultiSelectFieldHandler(SingleSelectFieldHandler):
    """Handler for multi-select fields"""
    
    field_type = FieldType.MULTI_SELECT
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        if value is None:
            return ValidationResult.success()
        
        if not isinstance(value, list):
            return ValidationResult.failure("Value must be a list")
        
        options = config.get("options", [])
        option_names = [opt["name"] for opt in options]
        allow_new = config.get("allow_new_options", True)
        
        for item in value:
            if not isinstance(item, str):
                return ValidationResult.failure("All values must be strings")
            
            if item not in option_names and not allow_new:
                return ValidationResult.failure(f"Invalid option: {item}")
        
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Optional[List[str]]:
        if value is None:
            return None
        return list(value)
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Optional[List[str]]:
        return value
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        if not value:
            return ""
        return ", ".join(value)
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> str:
        if not value:
            return ""
        return ", ".join(sorted(v.lower() for v in value))
    
    def filter(
        self, 
        value: Any, 
        operator: str, 
        filter_value: Any, 
        config: Dict[str, Any]
    ) -> bool:
        if value is None:
            value = []
        
        if operator == "is_empty":
            return len(value) == 0
        if operator == "is_not_empty":
            return len(value) > 0
        
        if operator == "contains":
            return filter_value in value
        if operator == "not_contains":
            return filter_value not in value
        
        if operator == "is_any_of":
            if not isinstance(filter_value, list):
                filter_value = [filter_value]
            return any(v in filter_value for v in value)
        
        if operator == "is_none_of":
            if not isinstance(filter_value, list):
                filter_value = [filter_value]
            return not any(v in filter_value for v in value)
        
        return False
```

---

### Week 8: Field Type System - Advanced Types

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 2.8.1 | Implement AttachmentFieldHandler | Critical | 4h | 2.7.* |
| 2.8.2 | Implement EmailFieldHandler | High | 2h | 2.7.1 |
| 2.8.3 | Implement PhoneFieldHandler | High | 2h | 2.7.1 |
| 2.8.4 | Implement URLFieldHandler | High | 2h | 2.7.1 |
| 2.8.5 | Implement RatingFieldHandler | High | 2h | 2.7.1 |
| 2.8.6 | Implement AutonumberFieldHandler | High | 3h | 2.7.1 |
| 2.8.7 | Implement CreatedTimeFieldHandler | Medium | 2h | 2.7.1 |
| 2.8.8 | Implement ModifiedTimeFieldHandler | Medium | 2h | 2.7.1 |
| 2.8.9 | Implement CreatedByFieldHandler | Medium | 2h | 2.7.1 |
| 2.8.10 | Implement ModifiedByFieldHandler | Medium | 2h | 2.7.1 |
| 2.8.11 | Implement LinkFieldHandler | Critical | 6h | 2.7.* |
| 2.8.12 | Implement LookupFieldHandler | Critical | 6h | 2.8.11 |
| 2.8.13 | Implement RollupFieldHandler | Critical | 6h | 2.8.11 |
| 2.8.14 | Write unit tests for all advanced handlers | Critical | 6h | 2.8.* |

#### Deliverables

- [ ] 13 advanced field type handlers implemented
- [ ] Link field with bidirectional support
- [ ] Lookup field resolving linked data
- [ ] Rollup field with aggregation functions
- [ ] Attachment field with MinIO integration
- [ ] Full test coverage

#### Link Field Implementation

**app/core/fields/standard/link.py**
```python
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.fields.base import FieldHandler, FieldType, ValidationResult


class LinkFieldHandler(FieldHandler):
    """Handler for link (relationship) fields"""
    
    field_type = FieldType.LINK
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        if value is None:
            return ValidationResult.success()
        
        if not isinstance(value, list):
            return ValidationResult.failure("Value must be a list of record IDs")
        
        for item in value:
            try:
                UUID(str(item))
            except (ValueError, TypeError):
                return ValidationResult.failure(f"Invalid record ID: {item}")
        
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Optional[List[str]]:
        if value is None:
            return None
        return [str(v) for v in value]
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Optional[List[UUID]]:
        if value is None:
            return None
        return [UUID(v) for v in value]
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        if not value:
            return ""
        return f"{len(value)} linked record(s)"
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> int:
        return len(value) if value else 0
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "linked_table_id": None,
            "is_bidirectional": True,
            "inverse_field_id": None,
            "limit_record_selection_to_view": None,
        }
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        linked_table_id = config.get("linked_table_id")
        
        if not linked_table_id:
            return ValidationResult.failure("linked_table_id is required")
        
        try:
            UUID(str(linked_table_id))
        except (ValueError, TypeError):
            return ValidationResult.failure("Invalid linked_table_id")
        
        return ValidationResult.success()


class LookupFieldHandler(FieldHandler):
    """Handler for lookup fields (pulling data from linked records)"""
    
    field_type = FieldType.LOOKUP
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        # Lookup fields are computed, validation happens on source
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Any:
        return value  # Already serialized from source
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Any:
        return value
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(str(v) for v in value if v is not None)
        return str(value)
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> Any:
        if value is None:
            return ""
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value)
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "linked_field_id": None,  # The link field
            "target_field_id": None,  # Field from linked table
        }
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        if not config.get("linked_field_id"):
            return ValidationResult.failure("linked_field_id is required")
        if not config.get("target_field_id"):
            return ValidationResult.failure("target_field_id is required")
        return ValidationResult.success()


class RollupFieldHandler(FieldHandler):
    """Handler for rollup fields (aggregating linked records)"""
    
    field_type = FieldType.ROLLUP
    
    AGGREGATIONS = {
        "sum", "avg", "min", "max", "count", "counta",
        "concat", "array_unique", "array_flatten",
    }
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        # Rollup fields are computed
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Any:
        return value
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Any:
        return value
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        if value is None:
            return ""
        return str(value)
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> Any:
        if value is None:
            return float("-inf")
        if isinstance(value, (int, float)):
            return value
        return str(value)
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "linked_field_id": None,
            "target_field_id": None,
            "aggregation": "count",
        }
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        if not config.get("linked_field_id"):
            return ValidationResult.failure("linked_field_id is required")
        if not config.get("target_field_id"):
            return ValidationResult.failure("target_field_id is required")
        
        aggregation = config.get("aggregation", "count")
        if aggregation not in self.AGGREGATIONS:
            return ValidationResult.failure(
                f"Invalid aggregation. Must be one of: {', '.join(self.AGGREGATIONS)}"
            )
        
        return ValidationResult.success()
    
    def compute(
        self, 
        linked_values: List[Any], 
        config: Dict[str, Any]
    ) -> Any:
        """Compute rollup value from linked records"""
        aggregation = config.get("aggregation", "count")
        
        # Filter out None values for most operations
        values = [v for v in linked_values if v is not None]
        
        if aggregation == "count":
            return len(linked_values)
        
        if aggregation == "counta":
            return len(values)
        
        if aggregation == "sum":
            try:
                return sum(float(v) for v in values)
            except (ValueError, TypeError):
                return None
        
        if aggregation == "avg":
            try:
                nums = [float(v) for v in values]
                return sum(nums) / len(nums) if nums else None
            except (ValueError, TypeError):
                return None
        
        if aggregation == "min":
            try:
                return min(values) if values else None
            except (ValueError, TypeError):
                return None
        
        if aggregation == "max":
            try:
                return max(values) if values else None
            except (ValueError, TypeError):
                return None
        
        if aggregation == "concat":
            return ", ".join(str(v) for v in values)
        
        if aggregation == "array_unique":
            return list(set(str(v) for v in values))
        
        if aggregation == "array_flatten":
            flat = []
            for v in linked_values:
                if isinstance(v, list):
                    flat.extend(v)
                else:
                    flat.append(v)
            return flat
        
        return None
```

---

### Week 9: Record Operations & Formula Engine

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 2.9.1 | Create RecordService with CRUD operations | Critical | 6h | 2.8.* |
| 2.9.2 | Implement record creation with field validation | Critical | 4h | 2.9.1 |
| 2.9.3 | Implement record update with field validation | Critical | 4h | 2.9.1 |
| 2.9.4 | Implement batch record operations | High | 4h | 2.9.1 |
| 2.9.5 | Create Record API endpoints | Critical | 4h | 2.9.* |
| 2.9.6 | Implement formula tokenizer | Critical | 6h | 2.8.* |
| 2.9.7 | Implement formula parser | Critical | 6h | 2.9.6 |
| 2.9.8 | Implement formula evaluator | Critical | 6h | 2.9.7 |
| 2.9.9 | Create FormulaFieldHandler | Critical | 4h | 2.9.8 |
| 2.9.10 | Implement basic formula functions (20+) | High | 6h | 2.9.8 |
| 2.9.11 | Write formula engine tests | Critical | 4h | 2.9.* |

#### Deliverables

- [ ] `POST /api/v1/tables/{id}/records` - Create records (batch)
- [ ] `GET /api/v1/tables/{id}/records` - List records with filtering
- [ ] `GET /api/v1/records/{id}` - Get single record
- [ ] `PATCH /api/v1/records/{id}` - Update record
- [ ] `DELETE /api/v1/records/{id}` - Delete record
- [ ] Formula engine with 20+ functions
- [ ] Formula field type working

#### Record Service

**app/services/record_service.py**
```python
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.fields.registry import get_handler
from app.models.field import Field
from app.models.record import Record
from app.schemas.record import RecordCreate, RecordUpdate


class RecordService:
    """Service for Record operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        table_id: UUID,
        data: Dict[str, Any],
        created_by: Optional[UUID] = None,
    ) -> Record:
        """Create a new record with validation"""
        
        # Get table fields
        fields = await self._get_table_fields(table_id)
        
        # Validate and serialize data
        validated_data = {}
        for field in fields:
            field_id = str(field.id)
            value = data.get(field_id) or data.get(field.name)
            
            if value is not None:
                handler = get_handler(field.field_type)
                
                # Validate
                result = handler.validate(value, field.config)
                if not result.valid:
                    raise ValueError(f"Field '{field.name}': {result.error}")
                
                # Serialize
                validated_data[field_id] = handler.serialize(value, field.config)
        
        # Handle computed fields
        validated_data = await self._compute_fields(fields, validated_data)
        
        record = Record(
            table_id=table_id,
            data=validated_data,
            created_by_id=created_by,
        )
        
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        
        return record
    
    async def create_batch(
        self,
        table_id: UUID,
        records_data: List[Dict[str, Any]],
        created_by: Optional[UUID] = None,
    ) -> List[Record]:
        """Create multiple records"""
        records = []
        
        for data in records_data:
            record = await self.create(table_id, data, created_by)
            records.append(record)
        
        return records
    
    async def get_by_id(self, record_id: UUID) -> Optional[Record]:
        """Get record by ID"""
        query = select(Record).where(Record.id == record_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list(
        self,
        table_id: UUID,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[Sequence[Record], int]:
        """List records with filtering and sorting"""
        
        # Base query
        query = select(Record).where(Record.table_id == table_id)
        count_query = select(func.count(Record.id)).where(Record.table_id == table_id)
        
        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
            count_query = self._apply_filters(count_query, filters)
        
        # Apply sorts
        if sorts:
            query = self._apply_sorts(query, sorts)
        else:
            query = query.order_by(Record.created_at.desc())
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        return records, total
    
    async def update(
        self,
        record_id: UUID,
        data: Dict[str, Any],
    ) -> Optional[Record]:
        """Update record with validation"""
        record = await self.get_by_id(record_id)
        if not record:
            return None
        
        # Get table fields
        fields = await self._get_table_fields(record.table_id)
        
        # Validate and merge data
        updated_data = record.data.copy()
        
        for field in fields:
            field_id = str(field.id)
            
            if field_id in data or field.name in data:
                value = data.get(field_id) or data.get(field.name)
                
                if value is not None:
                    handler = get_handler(field.field_type)
                    
                    result = handler.validate(value, field.config)
                    if not result.valid:
                        raise ValueError(f"Field '{field.name}': {result.error}")
                    
                    updated_data[field_id] = handler.serialize(value, field.config)
                else:
                    updated_data[field_id] = None
        
        # Recompute computed fields
        updated_data = await self._compute_fields(fields, updated_data)
        
        record.data = updated_data
        await self.db.commit()
        await self.db.refresh(record)
        
        return record
    
    async def delete(self, record_id: UUID) -> bool:
        """Delete a record"""
        record = await self.get_by_id(record_id)
        if not record:
            return False
        
        await self.db.delete(record)
        await self.db.commit()
        return True
    
    async def _get_table_fields(self, table_id: UUID) -> Sequence[Field]:
        """Get all fields for a table"""
        query = (
            select(Field)
            .where(Field.table_id == table_id)
            .order_by(Field.position)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _compute_fields(
        self,
        fields: Sequence[Field],
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute values for computed fields (formula, lookup, rollup)"""
        from app.core.formula_engine import FormulaEngine
        
        for field in fields:
            if not field.is_computed:
                continue
            
            field_id = str(field.id)
            
            if field.field_type == "formula":
                engine = FormulaEngine(
                    fields={str(f.id): {"name": f.name} for f in fields},
                    record_data=data,
                )
                data[field_id] = engine.evaluate(field.config.get("expression", ""))
            
            # Lookup and rollup would need record context
            # Implemented in separate methods
        
        return data
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply JSONB filters to query"""
        for field_id, condition in filters.items():
            if isinstance(condition, dict):
                operator = condition.get("operator", "equals")
                value = condition.get("value")
                
                if operator == "equals":
                    query = query.where(
                        Record.data[field_id].astext == str(value)
                    )
                elif operator == "contains":
                    query = query.where(
                        Record.data[field_id].astext.ilike(f"%{value}%")
                    )
                # Add more operators...
            else:
                query = query.where(
                    Record.data[field_id].astext == str(condition)
                )
        
        return query
    
    def _apply_sorts(self, query, sorts: List[Dict[str, str]]):
        """Apply sorts to query"""
        for sort in sorts:
            field_id = sort.get("field_id")
            direction = sort.get("direction", "asc")
            
            if direction == "desc":
                query = query.order_by(Record.data[field_id].desc())
            else:
                query = query.order_by(Record.data[field_id].asc())
        
        return query
```

---

### Week 10: Engineering Field Types & Integration

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 2.10.1 | Implement DimensionFieldHandler | Critical | 4h | 2.8.* |
| 2.10.2 | Implement GDTFieldHandler | Critical | 4h | 2.10.1 |
| 2.10.3 | Implement ThreadFieldHandler | High | 3h | 2.10.1 |
| 2.10.4 | Implement SurfaceFinishFieldHandler | High | 3h | 2.10.1 |
| 2.10.5 | Implement MaterialFieldHandler | High | 3h | 2.10.1 |
| 2.10.6 | Implement DrawingRefFieldHandler | High | 3h | 2.10.1 |
| 2.10.7 | Implement BOMItemFieldHandler | High | 3h | 2.10.1 |
| 2.10.8 | Implement RevisionHistoryFieldHandler | High | 3h | 2.10.1 |
| 2.10.9 | Create Field API endpoints | Critical | 4h | 2.10.* |
| 2.10.10 | End-to-end integration testing | Critical | 8h | 2.10.* |
| 2.10.11 | Performance testing and optimization | High | 4h | 2.10.10 |
| 2.10.12 | Documentation for all field types | Medium | 4h | 2.10.* |

#### Deliverables

- [ ] 8 engineering-specific field types
- [ ] Complete field CRUD API
- [ ] Integration tests passing
- [ ] Performance benchmarks established
- [ ] Field type documentation

#### Engineering Field Types

**app/core/fields/engineering/dimension.py**
```python
from decimal import Decimal
from typing import Any, Dict, Optional

from app.core.fields.base import FieldHandler, FieldType, ValidationResult


class DimensionFieldHandler(FieldHandler):
    """Handler for dimension fields with tolerances"""
    
    field_type = FieldType.DIMENSION
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        if value is None:
            return ValidationResult.success()
        
        if not isinstance(value, dict):
            return ValidationResult.failure("Value must be a dimension object")
        
        # Validate nominal value
        nominal = value.get("nominal_value")
        if nominal is None:
            return ValidationResult.failure("nominal_value is required")
        
        try:
            Decimal(str(nominal))
        except:
            return ValidationResult.failure("Invalid nominal_value")
        
        # Validate tolerance type
        tol_type = value.get("tolerance_type", "symmetric")
        valid_types = ["symmetric", "asymmetric", "limits", "fit"]
        if tol_type not in valid_types:
            return ValidationResult.failure(
                f"tolerance_type must be one of: {', '.join(valid_types)}"
            )
        
        # Validate unit
        unit = value.get("unit", "mm")
        if unit not in ["mm", "inch", "m", "cm"]:
            return ValidationResult.failure("Invalid unit")
        
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Optional[Dict]:
        if value is None:
            return None
        
        return {
            "nominal_value": float(value.get("nominal_value", 0)),
            "tolerance_upper": float(value["tolerance_upper"]) if value.get("tolerance_upper") else None,
            "tolerance_lower": float(value["tolerance_lower"]) if value.get("tolerance_lower") else None,
            "tolerance_type": value.get("tolerance_type", "symmetric"),
            "fit_designation": value.get("fit_designation"),
            "unit": value.get("unit", "mm"),
        }
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Optional[Dict]:
        return value
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        if not value:
            return ""
        
        nominal = value.get("nominal_value", 0)
        unit = value.get("unit", "mm")
        tol_type = value.get("tolerance_type", "symmetric")
        
        if tol_type == "fit" and value.get("fit_designation"):
            return f"{nominal} {value['fit_designation']} {unit}"
        
        upper = value.get("tolerance_upper")
        lower = value.get("tolerance_lower")
        
        if tol_type == "symmetric" and upper:
            return f"{nominal} ±{upper} {unit}"
        elif upper and lower:
            return f"{nominal} +{upper}/-{lower} {unit}"
        elif tol_type == "limits" and upper and lower:
            return f"{nominal + upper} / {nominal + lower} {unit}"
        
        return f"{nominal} {unit}"
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> float:
        if not value:
            return float("-inf")
        return float(value.get("nominal_value", 0))
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "default_unit": "mm",
            "precision": 3,
        }


class GDTFieldHandler(FieldHandler):
    """Handler for Geometric Dimensioning & Tolerancing fields"""
    
    field_type = FieldType.GDT
    
    GDT_SYMBOLS = {
        "position", "concentricity", "symmetry",  # Location
        "perpendicularity", "angularity", "parallelism",  # Orientation
        "flatness", "straightness", "circularity", "cylindricity",  # Form
        "profile_line", "profile_surface",  # Profile
        "circular_runout", "total_runout",  # Runout
    }
    
    MATERIAL_MODIFIERS = {"MMC", "LMC", "RFS", None}
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        if value is None:
            return ValidationResult.success()
        
        if not isinstance(value, dict):
            return ValidationResult.failure("Value must be a GD&T object")
        
        symbol = value.get("symbol")
        if not symbol or symbol not in self.GDT_SYMBOLS:
            return ValidationResult.failure(
                f"Invalid GD&T symbol. Must be one of: {', '.join(self.GDT_SYMBOLS)}"
            )
        
        tolerance = value.get("tolerance_value")
        if tolerance is None:
            return ValidationResult.failure("tolerance_value is required")
        
        try:
            if float(tolerance) < 0:
                return ValidationResult.failure("Tolerance must be positive")
        except:
            return ValidationResult.failure("Invalid tolerance_value")
        
        modifier = value.get("material_modifier")
        if modifier not in self.MATERIAL_MODIFIERS:
            return ValidationResult.failure("Invalid material_modifier")
        
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Optional[Dict]:
        if value is None:
            return None
        
        return {
            "symbol": value.get("symbol"),
            "tolerance_value": float(value.get("tolerance_value", 0)),
            "datum_references": value.get("datum_references", []),
            "material_modifier": value.get("material_modifier"),
        }
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Optional[Dict]:
        return value
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        if not value:
            return ""
        
        symbol = value.get("symbol", "").upper()
        tolerance = value.get("tolerance_value", 0)
        datums = value.get("datum_references", [])
        modifier = value.get("material_modifier", "")
        
        parts = [f"⌀{tolerance}" if symbol == "position" else str(tolerance)]
        
        if modifier:
            parts.append(f"({modifier})")
        
        if datums:
            parts.append("|")
            parts.extend(datums)
        
        return " ".join(parts)
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> float:
        if not value:
            return float("inf")
        return float(value.get("tolerance_value", 0))
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "standard": "ASME_Y14.5",  # or "ISO"
        }


class ThreadFieldHandler(FieldHandler):
    """Handler for thread specification fields"""
    
    field_type = FieldType.THREAD
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        if value is None:
            return ValidationResult.success()
        
        if not isinstance(value, dict):
            return ValidationResult.failure("Value must be a thread object")
        
        designation = value.get("designation")
        if not designation:
            return ValidationResult.failure("designation is required")
        
        thread_type = value.get("thread_type", "metric")
        if thread_type not in ["metric", "imperial_unified", "imperial_pipe"]:
            return ValidationResult.failure("Invalid thread_type")
        
        return ValidationResult.success()
    
    def serialize(self, value: Any, config: Dict[str, Any]) -> Optional[Dict]:
        if value is None:
            return None
        
        return {
            "designation": value.get("designation"),
            "thread_type": value.get("thread_type", "metric"),
            "major_diameter": float(value["major_diameter"]) if value.get("major_diameter") else None,
            "pitch": float(value["pitch"]) if value.get("pitch") else None,
            "thread_class": value.get("thread_class"),
            "internal": value.get("internal", False),
        }
    
    def deserialize(self, value: Any, config: Dict[str, Any]) -> Optional[Dict]:
        return value
    
    def format_display(self, value: Any, config: Dict[str, Any]) -> str:
        if not value:
            return ""
        
        parts = [value.get("designation", "")]
        
        if value.get("thread_class"):
            parts.append(f"-{value['thread_class']}")
        
        if value.get("internal"):
            parts.append("(INT)")
        
        return "".join(parts)
    
    def get_sort_key(self, value: Any, config: Dict[str, Any]) -> str:
        if not value:
            return ""
        return value.get("designation", "")
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "default_type": "metric",
        }
```

---

## Phase 2 Acceptance Criteria

### API Completeness

| Endpoint Category | Count | Status |
|-------------------|-------|--------|
| Workspace endpoints | 7 | Required |
| Base endpoints | 5 | Required |
| Table endpoints | 5 | Required |
| Field endpoints | 5 | Required |
| Record endpoints | 6 | Required |
| **Total** | **28** | |

### Field Type Coverage

| Category | Types | Status |
|----------|-------|--------|
| Basic | text, long_text, number, currency, percent, date, datetime, time, duration, checkbox | Required |
| Selection | single_select, multi_select, status | Required |
| Relationship | link, lookup, rollup | Required |
| Contact | email, phone, url | Required |
| Computed | formula, autonumber, created_time, modified_time, created_by, modified_by | Required |
| Media | attachment | Required |
| Advanced | rating, barcode | Optional |
| Engineering | dimension, gdt, thread, surface_finish, material, drawing_ref, bom_item, revision_history | Required |

### Test Coverage

- [ ] Unit tests: > 85% coverage
- [ ] Integration tests: All API endpoints
- [ ] Field handler tests: 100% coverage
- [ ] Formula engine tests: All functions

### Performance Benchmarks

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Record create | < 50ms | p95 latency |
| Record list (100) | < 100ms | p95 latency |
| Batch create (10) | < 200ms | p95 latency |
| Formula evaluation | < 10ms | p95 latency |

---

## Phase 2 Exit Criteria

Before proceeding to Phase 3:

1. [ ] All 28 API endpoints implemented and tested
2. [ ] All 30+ field types working
3. [ ] Formula engine with 20+ functions
4. [ ] Engineering field types complete
5. [ ] Performance benchmarks met
6. [ ] Code review completed
7. [ ] Documentation updated

---

## Dependencies for Phase 3

Phase 2 must deliver:
- Working field type system (all types)
- Record CRUD operations
- Formula engine basics
- Engineering-specific field types

Phase 3 will build the CAD/PDF extraction system that leverages these field types.

---

*Previous: [Phase 1: Foundation](master-plan-phase-1-foundation.md)*  
*Next: [Phase 3: CAD/PDF Extraction](master-plan-phase-3-extraction.md)*
