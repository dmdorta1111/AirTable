---
title: "Phase 2 Completion - Core Database & Field Types"
description: "Complete remaining field types, formula engine, and link/lookup/rollup for PyBase"
status: completed
priority: P1
effort: 80h
branch: feat/phase2-completion
tags: [field-types, formula-engine, relational, engineering]
created: 2026-01-17
completed: 2026-01-17
---

# Phase 2 Completion Plan: Core Database & Field Types

## Executive Summary

PyBase Phase 2 is approximately **40% complete**. The foundation is solid with working CRUD operations, basic field types (text, number, date, checkbox), and a clean field handler architecture. This plan outlines the remaining work to complete Phase 2 over **4-5 weeks** with an estimated **80 hours** of development effort.

### Current State
- ✅ Core entities CRUD (Workspace, Base, Table, Field, Record)
- ✅ Basic field handlers (text, long_text, number, date, checkbox)
- ✅ Field registry pattern with `get_field_handler()` and `register_field_handler()`
- ✅ API endpoints with pagination and filtering
- ✅ Service layer architecture
- ✅ Integration tests for API endpoints

### Remaining Work (Prioritized)
1. **Standard Field Types** (Week 7 continuation) - 12h
2. **Advanced Field Types** (Week 8) - 18h  
3. **Link/Lookup/Rollup** (Week 8-9) - 16h
4. **Formula Engine** (Week 9) - 20h
5. **Engineering Field Types** (Week 10) - 14h

---

## Architecture Analysis

### Existing Field Handler Interface

```python
# src/pybase/fields/base.py
class BaseFieldTypeHandler(ABC):
    field_type: str
    
    @classmethod
    def serialize(cls, value: Any) -> Any
    @classmethod  
    def deserialize(cls, value: Any) -> Any
    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool
    @classmethod
    def default(cls) -> Any
```

**Gap Analysis:** The current base class is simpler than the master plan's design. Consider adding:
- `format_display()` - for UI display formatting
- `get_sort_key()` - for proper sorting
- `get_default_config()` - for field configuration defaults
- `validate_config()` - for field configuration validation
- `filter()` - for filtering operations

**Recommendation:** Keep existing interface for now; extend only when needed. YAGNI principle.

### Data Storage Pattern

Records store field values as JSON text in the `data` column:
```python
# Record.data format: {"field_id": value, ...}
```

Field options are stored as JSON text in `Field.options`.

---

## Phase 1: Standard Field Types (Week 7 Continuation)

**Duration:** 3 days | **Effort:** 12h | **Priority:** High

### 1.1 Numeric Extensions

#### CurrencyFieldHandler
**File:** `src/pybase/fields/types/currency.py`
**Effort:** 2h

```python
class CurrencyFieldHandler(BaseFieldTypeHandler):
    field_type = "currency"
    
    # Options: currency_code (USD, EUR, etc.), precision, symbol_position
    # Serialize: float with precision
    # Validate: positive by default, check precision
    # Display: $1,234.56 or 1.234,56 €
```

**Test Cases:**
- Valid currency values with different locales
- Negative values (configurable)
- Precision handling (2 decimal places default)
- Invalid currency codes

#### PercentFieldHandler  
**File:** `src/pybase/fields/types/percent.py`
**Effort:** 1.5h

```python
class PercentFieldHandler(BaseFieldTypeHandler):
    field_type = "percent"
    
    # Options: precision, display_as (decimal or percent), min/max
    # Serialize: store as decimal (0.5 for 50%)
    # Display: 50% or 0.50
```

**Test Cases:**
- Input as 50 → store as 0.5
- Input as 0.5 → store as 0.5 (configurable)
- Range validation (0-100 or 0-1)

### 1.2 DateTime Extensions

#### DateTimeFieldHandler
**File:** `src/pybase/fields/types/datetime.py`
**Effort:** 2h

```python
class DateTimeFieldHandler(BaseFieldTypeHandler):
    field_type = "datetime"
    
    # Options: timezone, include_time, time_format (12h/24h)
    # Serialize: ISO 8601 string with timezone
    # Deserialize: datetime object
```

**Test Cases:**
- ISO 8601 parsing
- Timezone handling
- Date-only vs datetime input

#### TimeFieldHandler
**File:** `src/pybase/fields/types/time.py`
**Effort:** 1.5h

```python
class TimeFieldHandler(BaseFieldTypeHandler):
    field_type = "time"
    
    # Options: time_format (12h/24h)
    # Serialize: HH:MM:SS string
    # Display: 2:30 PM or 14:30
```

#### DurationFieldHandler
**File:** `src/pybase/fields/types/duration.py`
**Effort:** 2h

```python
class DurationFieldHandler(BaseFieldTypeHandler):
    field_type = "duration"
    
    # Options: format (h:mm, h:mm:ss, compact)
    # Serialize: total seconds as integer
    # Display: 2h 30m or 2:30:00
```

**Test Cases:**
- Parse "2h 30m" → 9000 seconds
- Parse "2:30:00" → 9000 seconds
- Negative durations (error)

### 1.3 Selection Types

#### SingleSelectFieldHandler
**File:** `src/pybase/fields/types/single_select.py`
**Effort:** 2h

```python
class SingleSelectFieldHandler(BaseFieldTypeHandler):
    field_type = "single_select"
    
    # Options: choices [{id, name, color}], allow_new
    # Serialize: choice name (string)
    # Validate: must be in choices unless allow_new=True
```

**Test Cases:**
- Valid choice selection
- Invalid choice rejection
- Dynamic choice creation (allow_new)
- Color association

#### MultiSelectFieldHandler
**File:** `src/pybase/fields/types/multi_select.py`  
**Effort:** 1.5h (extends SingleSelect)

```python
class MultiSelectFieldHandler(SingleSelectFieldHandler):
    field_type = "multi_select"
    
    # Serialize: list of choice names
    # Validate: all must be valid choices
```

#### StatusFieldHandler
**File:** `src/pybase/fields/types/status.py`
**Effort:** 1.5h (extends SingleSelect)

```python
class StatusFieldHandler(SingleSelectFieldHandler):
    field_type = "status"
    
    # Options: statuses with categories (todo, in_progress, complete)
    # Special: track status transitions, timestamps
```

### 1.4 Update Field Registry

**File:** `src/pybase/fields/__init__.py`

```python
# Add new imports and register handlers
from pybase.fields.types.currency import CurrencyFieldHandler
from pybase.fields.types.percent import PercentFieldHandler
# ... etc

FIELD_HANDLERS: dict[str, type[BaseFieldTypeHandler]] = {
    # existing...
    CurrencyFieldHandler.field_type: CurrencyFieldHandler,
    PercentFieldHandler.field_type: PercentFieldHandler,
    # ... etc
}
```

### Deliverables - Phase 1
- [ ] 6 new field handlers implemented
- [ ] Unit tests for each handler (>90% coverage)
- [ ] Registry updated
- [ ] Integration tests updated

---

## Phase 2: Advanced Field Types (Week 8)

**Duration:** 4 days | **Effort:** 18h | **Priority:** High

### 2.1 Contact & Media Types

#### EmailFieldHandler
**File:** `src/pybase/fields/types/email.py`
**Effort:** 1.5h

```python
class EmailFieldHandler(BaseFieldTypeHandler):
    field_type = "email"
    
    # Validate: regex for email format
    # Options: allow_multiple (comma-separated)
```

#### PhoneFieldHandler  
**File:** `src/pybase/fields/types/phone.py`
**Effort:** 1.5h

```python
class PhoneFieldHandler(BaseFieldTypeHandler):
    field_type = "phone"
    
    # Options: default_country_code, format
    # Consider: phonenumbers library for validation
```

#### URLFieldHandler
**File:** `src/pybase/fields/types/url.py`
**Effort:** 1.5h

```python
class URLFieldHandler(BaseFieldTypeHandler):
    field_type = "url"
    
    # Validate: URL format
    # Options: allowed_protocols (http, https)
```

#### RatingFieldHandler
**File:** `src/pybase/fields/types/rating.py`
**Effort:** 1.5h

```python
class RatingFieldHandler(BaseFieldTypeHandler):
    field_type = "rating"
    
    # Options: max_rating (default 5), icon (star, heart)
    # Serialize: integer 1-max
```

### 2.2 System Fields

#### AutonumberFieldHandler
**File:** `src/pybase/fields/types/autonumber.py`
**Effort:** 3h

```python
class AutonumberFieldHandler(BaseFieldTypeHandler):
    field_type = "autonumber"
    
    # Options: prefix, start_value, padding
    # Computed: auto-increment on record creation
    # Example: "INV-0001", "INV-0002"
    
    @classmethod
    def generate_next(cls, db: AsyncSession, field_id: str) -> str:
        # Query max current value and increment
        pass
```

**Implementation Notes:**
- Need to track sequence per field
- Consider using PostgreSQL sequence or storing last value in field.options
- Thread-safe increment

#### CreatedTimeFieldHandler
**File:** `src/pybase/fields/types/created_time.py`
**Effort:** 1h

```python
class CreatedTimeFieldHandler(BaseFieldTypeHandler):
    field_type = "created_time"
    
    # Read-only: returns record.created_at
    # No validation needed (system-managed)
```

#### ModifiedTimeFieldHandler
**File:** `src/pybase/fields/types/modified_time.py`
**Effort:** 1h

```python
class ModifiedTimeFieldHandler(BaseFieldTypeHandler):
    field_type = "last_modified_time"
    
    # Read-only: returns record.updated_at
```

#### CreatedByFieldHandler
**File:** `src/pybase/fields/types/created_by.py`
**Effort:** 1h

```python
class CreatedByFieldHandler(BaseFieldTypeHandler):
    field_type = "created_by"
    
    # Read-only: returns record.created_by_id
    # Display: resolve to user name
```

#### ModifiedByFieldHandler
**File:** `src/pybase/fields/types/modified_by.py`
**Effort:** 1h

```python
class ModifiedByFieldHandler(BaseFieldTypeHandler):
    field_type = "last_modified_by"
    
    # Read-only: returns record.last_modified_by_id
```

### 2.3 Attachment Field

#### AttachmentFieldHandler
**File:** `src/pybase/fields/types/attachment.py`
**Effort:** 4h

```python
class AttachmentFieldHandler(BaseFieldTypeHandler):
    field_type = "attachment"
    
    # Options: allowed_types, max_size_mb, max_files
    # Serialize: list of attachment objects
    # [{
    #     "id": "uuid",
    #     "filename": "drawing.pdf",
    #     "url": "https://s3.../...",
    #     "size": 1024000,
    #     "mime_type": "application/pdf",
    #     "thumbnails": {...}  # optional
    # }]
```

**Implementation Notes:**
- Integrate with MinIO (S3) storage
- Generate presigned URLs for access
- Consider thumbnail generation for images
- File size and type validation

### Deliverables - Phase 2
- [ ] 10 new field handlers implemented
- [ ] MinIO integration for attachments
- [ ] Unit tests (>90% coverage)
- [ ] Integration tests updated

---

## Phase 3: Link, Lookup, Rollup (Week 8-9)

**Duration:** 4 days | **Effort:** 16h | **Priority:** Critical

This is the most complex phase - these field types enable relational data modeling.

### 3.1 LinkFieldHandler (Linked Records)

**File:** `src/pybase/fields/types/link.py`
**Effort:** 6h

```python
class LinkFieldHandler(BaseFieldTypeHandler):
    field_type = "linked_record"
    
    # Options:
    # {
    #     "linked_table_id": "uuid",
    #     "is_bidirectional": true,
    #     "inverse_field_id": "uuid",  # auto-created if bidirectional
    #     "limit_to_view": null  # optional view filter
    # }
    
    # Serialize: list of linked record IDs ["uuid1", "uuid2"]
    
    @classmethod
    def validate(cls, value: Any, options: dict) -> bool:
        # Verify all IDs exist in linked table
        pass
    
    @classmethod
    def create_inverse_field(cls, db: AsyncSession, field: Field) -> Field:
        # Create the inverse link field in the linked table
        pass
```

**Implementation Details:**

1. **Bidirectional Links:**
   - When creating a link field, optionally create inverse field in target table
   - When linking records, update both sides
   - When deleting link, clean up both sides

2. **Validation:**
   - Verify linked_table_id exists
   - Verify all record IDs in value exist
   - Check circular references (A→B→A allowed, but flag)

3. **Service Integration:**
   ```python
   # In RecordService._validate_record_data()
   if field.field_type == "linked_record":
       # Verify all linked record IDs exist
       # Update inverse relationships
   ```

### 3.2 LookupFieldHandler

**File:** `src/pybase/fields/types/lookup.py`
**Effort:** 5h

```python
class LookupFieldHandler(BaseFieldTypeHandler):
    field_type = "lookup"
    
    # Options:
    # {
    #     "link_field_id": "uuid",  # the linked_record field
    #     "target_field_id": "uuid",  # field in linked table to pull
    # }
    
    # Computed: pulls values from linked records
    # Result: list of values from target field
    
    @classmethod
    def compute(cls, record: Record, field: Field, db: AsyncSession) -> Any:
        # 1. Get linked record IDs from link_field
        # 2. Fetch those records
        # 3. Extract target_field values
        # 4. Return list of values
        pass
```

**Implementation Notes:**
- Lookup fields are read-only (computed)
- Must be recalculated when:
  - Linked records change
  - Target field values change
- Consider caching for performance

### 3.3 RollupFieldHandler

**File:** `src/pybase/fields/types/rollup.py`
**Effort:** 5h

```python
class RollupFieldHandler(BaseFieldTypeHandler):
    field_type = "rollup"
    
    # Options:
    # {
    #     "link_field_id": "uuid",
    #     "target_field_id": "uuid",
    #     "aggregation": "sum" | "avg" | "min" | "max" | "count" | "counta" |
    #                    "concat" | "array_unique"
    # }
    
    AGGREGATIONS = {
        "sum": lambda vals: sum(v for v in vals if isinstance(v, (int, float))),
        "avg": lambda vals: sum(vals) / len(vals) if vals else None,
        "min": lambda vals: min(vals) if vals else None,
        "max": lambda vals: max(vals) if vals else None,
        "count": lambda vals: len(vals),
        "counta": lambda vals: len([v for v in vals if v is not None]),
        "concat": lambda vals: ", ".join(str(v) for v in vals if v),
        "array_unique": lambda vals: list(set(vals)),
    }
    
    @classmethod
    def compute(cls, record: Record, field: Field, db: AsyncSession) -> Any:
        # 1. Get values via lookup logic
        # 2. Apply aggregation function
        pass
```

### 3.4 Computed Field Evaluation

**File:** `src/pybase/services/record.py` (update)

Add computed field evaluation to record service:

```python
async def _compute_fields(
    self,
    db: AsyncSession,
    record: Record,
    fields: list[Field],
) -> dict[str, Any]:
    """Compute values for lookup/rollup fields"""
    data = json.loads(record.data)
    
    for field in fields:
        if field.field_type == "lookup":
            handler = get_field_handler("lookup")
            data[str(field.id)] = await handler.compute(record, field, db)
        elif field.field_type == "rollup":
            handler = get_field_handler("rollup")
            data[str(field.id)] = await handler.compute(record, field, db)
    
    return data
```

### Deliverables - Phase 3
- [ ] LinkFieldHandler with bidirectional support
- [ ] LookupFieldHandler with computation
- [ ] RollupFieldHandler with 8 aggregation functions
- [ ] RecordService integration
- [ ] Unit tests for all scenarios
- [ ] Integration tests for relational queries

---

## Phase 4: Formula Engine (Week 9)

**Duration:** 5 days | **Effort:** 20h | **Priority:** Critical

### 4.1 Formula Parser Architecture

**Recommended Approach:** Use `lark` parser for grammar definition.

**File:** `src/pybase/formula/__init__.py`
**File:** `src/pybase/formula/grammar.py`
**File:** `src/pybase/formula/parser.py`
**File:** `src/pybase/formula/evaluator.py`
**File:** `src/pybase/formula/functions.py`

#### Grammar Definition
**File:** `src/pybase/formula/grammar.py`
**Effort:** 4h

```python
FORMULA_GRAMMAR = """
    ?start: expression
    
    ?expression: comparison
    
    ?comparison: sum
        | comparison "=" sum     -> eq
        | comparison "!=" sum    -> ne
        | comparison ">" sum     -> gt
        | comparison "<" sum     -> lt
        | comparison ">=" sum    -> ge
        | comparison "<=" sum    -> le
    
    ?sum: product
        | sum "+" product   -> add
        | sum "-" product   -> sub
        | sum "&" product   -> concat
    
    ?product: atom
        | product "*" atom  -> mul
        | product "/" atom  -> div
    
    ?atom: NUMBER           -> number
        | STRING            -> string
        | "TRUE"            -> true
        | "FALSE"           -> false
        | field_ref
        | function_call
        | "(" expression ")"
    
    field_ref: "{" NAME "}"
    
    function_call: NAME "(" [arguments] ")"
    arguments: expression ("," expression)*
    
    NAME: /[a-zA-Z_][a-zA-Z_0-9]*/
    NUMBER: /[-]?[0-9]+(\.[0-9]+)?/
    STRING: /"[^"]*"/
    
    %import common.WS
    %ignore WS
"""
```

#### Parser Implementation
**File:** `src/pybase/formula/parser.py`
**Effort:** 3h

```python
from lark import Lark, Transformer, v_args
from .grammar import FORMULA_GRAMMAR

class FormulaParser:
    def __init__(self):
        self.parser = Lark(FORMULA_GRAMMAR, start='start')
    
    def parse(self, formula: str) -> Tree:
        return self.parser.parse(formula)
    
    def get_field_references(self, formula: str) -> set[str]:
        """Extract all field references from formula"""
        tree = self.parse(formula)
        refs = set()
        for node in tree.find_data('field_ref'):
            refs.add(node.children[0].value)
        return refs
```

#### Evaluator Implementation
**File:** `src/pybase/formula/evaluator.py`
**Effort:** 5h

```python
from lark import Transformer, v_args
from decimal import Decimal
from datetime import date, datetime

@v_args(inline=True)
class FormulaEvaluator(Transformer):
    def __init__(self, context: dict[str, Any], functions: dict):
        self.context = context  # {field_name: value}
        self.functions = functions
    
    def number(self, token):
        return Decimal(token)
    
    def string(self, token):
        return str(token)[1:-1]  # Remove quotes
    
    def true(self):
        return True
    
    def false(self):
        return False
    
    def field_ref(self, name):
        return self.context.get(str(name))
    
    def function_call(self, name, *args):
        func = self.functions.get(str(name).upper())
        if not func:
            raise ValueError(f"Unknown function: {name}")
        return func(*args)
    
    # Operators
    def add(self, a, b): return a + b
    def sub(self, a, b): return a - b
    def mul(self, a, b): return a * b
    def div(self, a, b): return a / b if b else None
    def concat(self, a, b): return str(a or '') + str(b or '')
    
    # Comparisons
    def eq(self, a, b): return a == b
    def ne(self, a, b): return a != b
    def gt(self, a, b): return a > b
    def lt(self, a, b): return a < b
    def ge(self, a, b): return a >= b
    def le(self, a, b): return a <= b
```

### 4.2 Formula Functions

**File:** `src/pybase/formula/functions.py`
**Effort:** 6h

```python
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

# Text Functions
def CONCAT(*args) -> str:
    return ''.join(str(a) if a is not None else '' for a in args)

def LEFT(text: str, n: int) -> str:
    return str(text)[:int(n)] if text else ''

def RIGHT(text: str, n: int) -> str:
    return str(text)[-int(n):] if text else ''

def MID(text: str, start: int, length: int) -> str:
    return str(text)[int(start)-1:int(start)-1+int(length)] if text else ''

def LEN(text: str) -> int:
    return len(str(text)) if text else 0

def UPPER(text: str) -> str:
    return str(text).upper() if text else ''

def LOWER(text: str) -> str:
    return str(text).lower() if text else ''

def TRIM(text: str) -> str:
    return str(text).strip() if text else ''

def SUBSTITUTE(text: str, old: str, new: str) -> str:
    return str(text).replace(str(old), str(new)) if text else ''

# Numeric Functions
def SUM(*args) -> Decimal:
    return sum(Decimal(str(a)) for a in args if a is not None)

def AVG(*args) -> Decimal | None:
    vals = [Decimal(str(a)) for a in args if a is not None]
    return sum(vals) / len(vals) if vals else None

def MIN(*args) -> Any:
    vals = [a for a in args if a is not None]
    return min(vals) if vals else None

def MAX(*args) -> Any:
    vals = [a for a in args if a is not None]
    return max(vals) if vals else None

def ROUND(value: Any, decimals: int = 0) -> Decimal:
    return round(Decimal(str(value)), int(decimals))

def ABS(value: Any) -> Decimal:
    return abs(Decimal(str(value)))

def FLOOR(value: Any) -> int:
    import math
    return math.floor(float(value))

def CEILING(value: Any) -> int:
    import math
    return math.ceil(float(value))

# Logical Functions
def IF(condition: bool, true_val: Any, false_val: Any) -> Any:
    return true_val if condition else false_val

def AND(*args) -> bool:
    return all(bool(a) for a in args)

def OR(*args) -> bool:
    return any(bool(a) for a in args)

def NOT(value: Any) -> bool:
    return not bool(value)

def BLANK() -> None:
    return None

def ERROR(message: str = "Error") -> None:
    raise ValueError(message)

# Date Functions
def TODAY() -> date:
    return date.today()

def NOW() -> datetime:
    return datetime.now()

def YEAR(d: date) -> int:
    return d.year if d else None

def MONTH(d: date) -> int:
    return d.month if d else None

def DAY(d: date) -> int:
    return d.day if d else None

def DATEADD(d: date, num: int, unit: str) -> date:
    if unit.upper() == 'DAYS':
        return d + timedelta(days=int(num))
    elif unit.upper() == 'MONTHS':
        # Simplified - use dateutil for proper month handling
        return d.replace(month=d.month + int(num))
    elif unit.upper() == 'YEARS':
        return d.replace(year=d.year + int(num))
    return d

def DATEDIFF(d1: date, d2: date, unit: str) -> int:
    diff = d2 - d1
    if unit.upper() == 'DAYS':
        return diff.days
    # Add more units as needed
    return diff.days

# Function Registry
FORMULA_FUNCTIONS = {
    # Text
    'CONCAT': CONCAT, 'LEFT': LEFT, 'RIGHT': RIGHT, 'MID': MID,
    'LEN': LEN, 'UPPER': UPPER, 'LOWER': LOWER, 'TRIM': TRIM,
    'SUBSTITUTE': SUBSTITUTE,
    # Numeric
    'SUM': SUM, 'AVG': AVG, 'MIN': MIN, 'MAX': MAX,
    'ROUND': ROUND, 'ABS': ABS, 'FLOOR': FLOOR, 'CEILING': CEILING,
    # Logical
    'IF': IF, 'AND': AND, 'OR': OR, 'NOT': NOT, 'BLANK': BLANK,
    # Date
    'TODAY': TODAY, 'NOW': NOW, 'YEAR': YEAR, 'MONTH': MONTH,
    'DAY': DAY, 'DATEADD': DATEADD, 'DATEDIFF': DATEDIFF,
}
```

### 4.3 FormulaFieldHandler

**File:** `src/pybase/fields/types/formula.py`
**Effort:** 2h

```python
from pybase.fields.base import BaseFieldTypeHandler
from pybase.formula.parser import FormulaParser
from pybase.formula.evaluator import FormulaEvaluator
from pybase.formula.functions import FORMULA_FUNCTIONS

class FormulaFieldHandler(BaseFieldTypeHandler):
    field_type = "formula"
    
    @classmethod
    def validate(cls, value: Any, options: dict | None = None) -> bool:
        # Formula fields are computed, no input validation
        return True
    
    @classmethod
    def serialize(cls, value: Any) -> Any:
        return value
    
    @classmethod
    def deserialize(cls, value: Any) -> Any:
        return value
    
    @classmethod
    def default(cls) -> Any:
        return None
    
    @classmethod
    def compute(
        cls,
        expression: str,
        context: dict[str, Any],
    ) -> Any:
        """Evaluate formula with given field context"""
        try:
            parser = FormulaParser()
            tree = parser.parse(expression)
            evaluator = FormulaEvaluator(context, FORMULA_FUNCTIONS)
            return evaluator.transform(tree)
        except Exception as e:
            return f"#ERROR: {e}"
    
    @classmethod
    def validate_expression(cls, expression: str) -> tuple[bool, str | None]:
        """Validate formula syntax without evaluating"""
        try:
            parser = FormulaParser()
            parser.parse(expression)
            return True, None
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def get_dependencies(cls, expression: str) -> set[str]:
        """Get field names referenced in formula"""
        parser = FormulaParser()
        return parser.get_field_references(expression)
```

### 4.4 Dependency Tracking

**File:** `src/pybase/formula/dependencies.py`
**Effort:** 2h

```python
from collections import defaultdict

class FormulaDependencyGraph:
    """Track formula field dependencies for recalculation"""
    
    def __init__(self):
        self.dependencies = defaultdict(set)  # field_id -> set of dependent field_ids
        self.reverse = defaultdict(set)  # field_id -> set of fields it depends on
    
    def add_formula_field(self, field_id: str, depends_on: set[str]):
        for dep in depends_on:
            self.dependencies[dep].add(field_id)
        self.reverse[field_id] = depends_on
    
    def get_affected_fields(self, changed_field_id: str) -> list[str]:
        """Get formula fields that need recalculation when a field changes"""
        affected = []
        to_process = [changed_field_id]
        seen = set()
        
        while to_process:
            current = to_process.pop(0)
            if current in seen:
                continue
            seen.add(current)
            
            for dependent in self.dependencies[current]:
                if dependent not in seen:
                    affected.append(dependent)
                    to_process.append(dependent)
        
        return affected
    
    def detect_circular_reference(self, field_id: str, depends_on: set[str]) -> bool:
        """Check if adding this dependency would create a cycle"""
        visited = set()
        to_check = list(depends_on)
        
        while to_check:
            current = to_check.pop()
            if current == field_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            to_check.extend(self.reverse.get(current, set()))
        
        return False
```

### Deliverables - Phase 4
- [ ] Formula parser with lark grammar
- [ ] Formula evaluator with operator support
- [ ] 25+ formula functions implemented
- [ ] FormulaFieldHandler
- [ ] Dependency tracking
- [ ] Circular reference detection
- [ ] Unit tests for all functions
- [ ] Integration tests for formula fields

---

## Phase 5: Engineering Field Types (Week 10)

**Duration:** 3 days | **Effort:** 14h | **Priority:** Medium

### 5.1 DimensionFieldHandler

**File:** `src/pybase/fields/types/dimension.py`
**Effort:** 3h

```python
class DimensionFieldHandler(BaseFieldTypeHandler):
    field_type = "dimension"
    
    # Value structure:
    # {
    #     "nominal": 10.5,
    #     "tolerance_upper": 0.1,
    #     "tolerance_lower": -0.1,
    #     "tolerance_type": "symmetric" | "asymmetric" | "limits" | "fit",
    #     "fit_designation": "H7",  # for fit type
    #     "unit": "mm" | "inch"
    # }
    
    @classmethod
    def validate(cls, value: Any, options: dict | None = None) -> bool:
        if value is None:
            return True
        if not isinstance(value, dict):
            raise ValueError("Dimension must be an object")
        if "nominal" not in value:
            raise ValueError("nominal value required")
        # Validate tolerances
        return True
    
    @classmethod
    def format_display(cls, value: dict) -> str:
        if not value:
            return ""
        unit = value.get("unit", "mm")
        tol_type = value.get("tolerance_type", "symmetric")
        
        if tol_type == "symmetric":
            return f"{value['nominal']} ±{value.get('tolerance_upper', 0)} {unit}"
        elif tol_type == "fit":
            return f"Ø{value['nominal']} {value.get('fit_designation', '')} {unit}"
        else:
            return f"{value['nominal']} +{value.get('tolerance_upper', 0)}/-{abs(value.get('tolerance_lower', 0))} {unit}"
```

### 5.2 GDTFieldHandler (Geometric Tolerancing)

**File:** `src/pybase/fields/types/gdt.py`
**Effort:** 2h

```python
class GDTFieldHandler(BaseFieldTypeHandler):
    field_type = "gdt"
    
    GDT_SYMBOLS = {
        # Form
        "flatness", "straightness", "circularity", "cylindricity",
        # Orientation  
        "perpendicularity", "angularity", "parallelism",
        # Location
        "position", "concentricity", "symmetry",
        # Profile
        "profile_line", "profile_surface",
        # Runout
        "circular_runout", "total_runout",
    }
    
    # Value structure:
    # {
    #     "symbol": "position",
    #     "tolerance": 0.05,
    #     "diameter_symbol": true,  # for position
    #     "modifier": "MMC" | "LMC" | "RFS" | null,
    #     "datums": ["A", "B", "C"]
    # }
```

### 5.3 ThreadFieldHandler

**File:** `src/pybase/fields/types/thread.py`
**Effort:** 2h

```python
class ThreadFieldHandler(BaseFieldTypeHandler):
    field_type = "thread"
    
    # Value structure:
    # {
    #     "designation": "M10x1.5",
    #     "type": "metric" | "unc" | "unf" | "bsp" | "npt",
    #     "diameter": 10.0,
    #     "pitch": 1.5,
    #     "class": "6H",  # internal thread class
    #     "internal": true
    # }
    
    @classmethod
    def parse_designation(cls, designation: str) -> dict:
        """Parse thread designation string into components"""
        # M10x1.5 -> metric, 10mm, 1.5 pitch
        # 1/4-20 UNC -> imperial, 1/4", 20 TPI
        pass
```

### 5.4 Other Engineering Types

**Files:**
- `src/pybase/fields/types/surface_finish.py` (1.5h)
- `src/pybase/fields/types/material.py` (1.5h)
- `src/pybase/fields/types/drawing_ref.py` (1.5h)
- `src/pybase/fields/types/bom_item.py` (1.5h)
- `src/pybase/fields/types/revision.py` (1.5h)

Each follows similar pattern with domain-specific validation and display formatting.

### Deliverables - Phase 5
- [ ] 8 engineering field handlers
- [ ] Domain-specific validation
- [ ] Display formatting for engineering notation
- [ ] Unit tests
- [ ] Documentation for engineering fields

---

## Test Strategy

### Unit Test Requirements

**Target Coverage:** >85% for all new code

**File Structure:**
```
tests/
├── unit/
│   └── fields/
│       ├── test_currency.py
│       ├── test_percent.py
│       ├── test_datetime.py
│       ├── test_select.py
│       ├── test_link.py
│       ├── test_lookup.py
│       ├── test_rollup.py
│       ├── test_formula.py
│       └── test_dimension.py
│   └── formula/
│       ├── test_parser.py
│       ├── test_evaluator.py
│       └── test_functions.py
├── integration/
│   ├── test_linked_records.py
│   ├── test_computed_fields.py
│   └── test_formula_fields.py
└── conftest.py
```

### Test Patterns

```python
# Unit test pattern for field handlers
@pytest.mark.parametrize("value,expected", [
    ("valid@email.com", True),
    ("invalid", False),
    ("", False),
    (None, True),  # None allowed
])
def test_email_validation(value, expected):
    handler = EmailFieldHandler()
    if expected:
        assert handler.validate(value) == True
    else:
        with pytest.raises(ValueError):
            handler.validate(value)

# Integration test pattern for linked records
@pytest.mark.asyncio
async def test_bidirectional_link(db_session, test_user, auth_headers):
    # Create two tables
    # Create link field with bidirectional=True
    # Create records with links
    # Verify inverse links are updated
    pass
```

---

## Risk Assessment

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Formula engine complexity | Schedule slip | Use proven lark library; limit initial function set |
| Link field data integrity | Data corruption | Comprehensive transactions; validation tests |
| Performance with large datasets | Slow queries | Index JSONB paths; batch operations |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular formula references | Infinite loops | Dependency graph with cycle detection |
| Attachment storage | Security | Presigned URLs; file type validation |
| Engineering field complexity | Bugs | Partner with domain expert for validation |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| API compatibility | Breaking changes | Version API; deprecation warnings |
| Test coverage gaps | Regressions | CI enforcement of >80% coverage |

---

## Success Criteria

### Phase 2 Complete When:

1. **Field Types:** All 30+ field types implemented and registered
2. **Test Coverage:** >85% unit test coverage, all integration tests passing
3. **Formula Engine:** Parser, evaluator, and 25+ functions working
4. **Relational:** Link, lookup, rollup working with bidirectional support
5. **Performance:** Record CRUD <100ms for tables with <10k records
6. **Documentation:** All field types documented with examples

### Definition of Done (per field type):

- [ ] Handler class implemented
- [ ] Unit tests with >90% coverage
- [ ] Integration test created
- [ ] Registered in FIELD_HANDLERS
- [ ] Options schema documented
- [ ] Edge cases handled

---

## Implementation Schedule

```
Week 7 (Days 1-3): Standard Field Types
  - Day 1: Currency, Percent
  - Day 2: DateTime, Time, Duration
  - Day 3: SingleSelect, MultiSelect, Status

Week 8 (Days 1-4): Advanced Field Types  
  - Day 1: Email, Phone, URL, Rating
  - Day 2: Autonumber, System fields
  - Day 3: Attachment field with MinIO
  - Day 4: Link field (start)

Week 9 (Days 1-5): Link/Lookup/Rollup + Formula
  - Day 1: Link field (complete)
  - Day 2: Lookup, Rollup
  - Day 3: Formula parser
  - Day 4: Formula evaluator
  - Day 5: Formula functions + handler

Week 10 (Days 1-3): Engineering Types + Polish
  - Day 1: Dimension, GDT
  - Day 2: Thread, Surface, Material
  - Day 3: Drawing, BOM, Revision + Integration tests
```

---

## Unresolved Questions

1. **Formula recalculation trigger:** Should formulas recalculate on every read (fresh) or cache with invalidation?
   - Recommendation: Cache with invalidation via dependency graph

2. **Attachment thumbnails:** Generate server-side or client-side?
   - Recommendation: Server-side for images <5MB, skip for others

3. **Link field limits:** Max linked records per field?
   - Recommendation: Configurable, default 1000

4. **Engineering field standards:** ASME Y14.5 vs ISO 1101 for GD&T?
   - Recommendation: Support both via config option

---

*Plan generated: 2026-01-17*
*Estimated total effort: 80 hours*
*Recommended team: 1 senior backend developer + 1 junior for tests*
