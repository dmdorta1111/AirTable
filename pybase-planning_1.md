# PyBase - A Comprehensive Airtable Clone in Python

## Executive Summary

**PyBase** is a full-featured, self-hosted database management platform built entirely in Python. It combines the flexibility of spreadsheets with the power of relational databases, featuring PDF extraction, rich field types, views, automations, and a robust API.

---

## 1. Core Architecture

### 1.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Backend Framework** | FastAPI | Async support, automatic OpenAPI docs, high performance |
| **Database** | PostgreSQL + SQLAlchemy | JSONB for flexible schemas, mature ecosystem |
| **Task Queue** | Celery + Redis | Background jobs, automations, PDF processing |
| **Real-time** | WebSockets (FastAPI) | Live collaboration, instant updates |
| **Frontend** | React + TypeScript | Rich UI, component ecosystem (or NiceGUI for Python-only) |
| **File Storage** | MinIO (S3-compatible) | Self-hosted, scalable attachments |
| **Cache** | Redis | Session management, query caching |
| **Search** | PostgreSQL FTS + Meilisearch | Full-text search across records |
| **PDF Processing** | pdfplumber + tabula-py + PyMuPDF | Table extraction, OCR support |
| **Auth** | JWT + OAuth2 | Secure, standard authentication |

### 1.2 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Web App (React)  │  Mobile Apps  │  API Clients  │  Integrations           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI Application                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ REST API    │ │ WebSocket   │ │ GraphQL     │ │ Webhooks    │            │
│  │ Endpoints   │ │ Handler     │ │ (Optional)  │ │ Manager     │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BUSINESS LOGIC LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Table       │ │ View        │ │ Automation  │ │ Formula     │            │
│  │ Manager     │ │ Engine      │ │ Engine      │ │ Engine      │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Field       │ │ Record      │ │ Permission  │ │ Collaboration│           │
│  │ Handler     │ │ CRUD        │ │ Manager     │ │ Manager      │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │ PostgreSQL          │  │ Redis               │  │ MinIO               │  │
│  │ - Base/Table Schema │  │ - Cache             │  │ - Attachments       │  │
│  │ - Records (JSONB)   │  │ - Sessions          │  │ - Exports           │  │
│  │ - Metadata          │  │ - Real-time PubSub  │  │ - Thumbnails        │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKGROUND SERVICES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │ Celery Workers      │  │ PDF Processor       │  │ Search Indexer      │  │
│  │ - Automations       │  │ - Table Extraction  │  │ - Meilisearch Sync  │  │
│  │ - Bulk Operations   │  │ - OCR Pipeline      │  │ - Full-text Index   │  │
│  │ - Webhooks          │  │ - Data Import       │  │                     │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema Design

### 2.1 Core Tables

```sql
-- Workspaces (Organizations)
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bases (Databases)
CREATE TABLE bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7),
    icon VARCHAR(50),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tables
CREATE TABLE tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_id UUID REFERENCES bases(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    primary_field_id UUID,  -- References fields.id
    position INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fields (Columns)
CREATE TABLE fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID REFERENCES tables(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    field_type VARCHAR(50) NOT NULL,  -- text, number, date, select, etc.
    config JSONB DEFAULT '{}',        -- Field-specific configuration
    position INTEGER DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    is_computed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Records (Rows) - Using JSONB for flexible schema
CREATE TABLE records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID REFERENCES tables(id) ON DELETE CASCADE,
    data JSONB NOT NULL DEFAULT '{}',  -- {field_id: value, ...}
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast JSONB queries
CREATE INDEX idx_records_data ON records USING GIN (data);
CREATE INDEX idx_records_table_id ON records(table_id);

-- Views
CREATE TABLE views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID REFERENCES tables(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    view_type VARCHAR(50) NOT NULL,  -- grid, kanban, calendar, gallery, form, gantt
    config JSONB NOT NULL DEFAULT '{}',
    -- Config includes: filters, sorts, hidden_fields, field_widths, groupings
    is_default BOOLEAN DEFAULT FALSE,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Attachments
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id UUID REFERENCES records(id) ON DELETE CASCADE,
    field_id UUID REFERENCES fields(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    thumbnail_path VARCHAR(500),
    metadata JSONB DEFAULT '{}',  -- width, height, duration, extracted_text
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Link Records (Many-to-Many relationships)
CREATE TABLE record_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_id UUID REFERENCES fields(id) ON DELETE CASCADE,
    source_record_id UUID REFERENCES records(id) ON DELETE CASCADE,
    target_record_id UUID REFERENCES records(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(field_id, source_record_id, target_record_id)
);

-- Automations
CREATE TABLE automations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_id UUID REFERENCES bases(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_config JSONB NOT NULL,   -- {type: "record_created", table_id: "...", conditions: [...]}
    action_config JSONB NOT NULL,    -- [{type: "send_email", config: {...}}, ...]
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMPTZ,
    run_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    avatar_url VARCHAR(500),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workspace Members
CREATE TABLE workspace_members (
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- owner, admin, editor, viewer
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

-- Comments
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id UUID REFERENCES records(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    parent_id UUID REFERENCES comments(id),  -- For threaded comments
    mentions JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Activity Log
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    entity_type VARCHAR(50) NOT NULL,  -- record, table, field, view
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,       -- create, update, delete
    changes JSONB,                      -- {field: {old: x, new: y}}
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. Field Types System

### 3.1 Supported Field Types

```python
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel
from datetime import datetime, date, time
from decimal import Decimal

class FieldType(str, Enum):
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
    LINK = "link"              # Link to another table
    LOOKUP = "lookup"          # Pull fields from linked records
    ROLLUP = "rollup"          # Aggregate linked records
    
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
    AI_TEXT = "ai_text"  # AI-generated content


class FieldConfig(BaseModel):
    """Configuration for each field type"""
    
    # Text
    class TextConfig(BaseModel):
        max_length: Optional[int] = None
        validation_regex: Optional[str] = None
    
    # Number
    class NumberConfig(BaseModel):
        precision: int = 2
        allow_negative: bool = True
        min_value: Optional[Decimal] = None
        max_value: Optional[Decimal] = None
        format: str = "decimal"  # decimal, integer, comma_separated
    
    # Currency
    class CurrencyConfig(BaseModel):
        currency_code: str = "USD"
        precision: int = 2
        symbol_position: str = "before"  # before, after
    
    # Date
    class DateConfig(BaseModel):
        date_format: str = "YYYY-MM-DD"
        include_time: bool = False
        time_format: str = "HH:mm"
        timezone: Optional[str] = None
    
    # Select
    class SelectConfig(BaseModel):
        options: List[Dict[str, Any]] = []  # [{id, name, color}]
        allow_new_options: bool = True
    
    # Link
    class LinkConfig(BaseModel):
        linked_table_id: str
        is_bidirectional: bool = True
        inverse_field_id: Optional[str] = None
        limit_record_selection_to_view: Optional[str] = None
    
    # Lookup
    class LookupConfig(BaseModel):
        linked_field_id: str     # The link field
        target_field_id: str     # Field from linked table to display
    
    # Rollup
    class RollupConfig(BaseModel):
        linked_field_id: str
        target_field_id: str
        aggregation: str  # sum, avg, count, min, max, concat, etc.
    
    # Formula
    class FormulaConfig(BaseModel):
        expression: str
        result_type: str = "text"  # text, number, date, boolean
    
    # Rating
    class RatingConfig(BaseModel):
        max_rating: int = 5
        icon: str = "star"  # star, heart, thumb, flag
        color: str = "#FFD700"
    
    # Attachment
    class AttachmentConfig(BaseModel):
        allowed_types: List[str] = []  # empty = all types
        max_file_size_mb: int = 20
        max_files: Optional[int] = None
```

### 3.2 Field Type Handler Interface

```python
from abc import ABC, abstractmethod
from typing import Any, Optional, List

class FieldHandler(ABC):
    """Base class for all field type handlers"""
    
    @abstractmethod
    def validate(self, value: Any, config: dict) -> tuple[bool, Optional[str]]:
        """Validate a value against field configuration"""
        pass
    
    @abstractmethod
    def serialize(self, value: Any, config: dict) -> Any:
        """Convert value to storage format (JSONB-compatible)"""
        pass
    
    @abstractmethod
    def deserialize(self, value: Any, config: dict) -> Any:
        """Convert from storage format to Python type"""
        pass
    
    @abstractmethod
    def format_display(self, value: Any, config: dict) -> str:
        """Format value for display"""
        pass
    
    @abstractmethod
    def get_sort_key(self, value: Any, config: dict) -> Any:
        """Return sortable representation of value"""
        pass
    
    def filter_operation(self, operation: str, value: Any, filter_value: Any, config: dict) -> bool:
        """Evaluate filter operation (default implementations)"""
        ops = {
            "equals": lambda: value == filter_value,
            "not_equals": lambda: value != filter_value,
            "is_empty": lambda: value is None or value == "",
            "is_not_empty": lambda: value is not None and value != "",
            "contains": lambda: str(filter_value).lower() in str(value).lower(),
            "not_contains": lambda: str(filter_value).lower() not in str(value).lower(),
        }
        return ops.get(operation, lambda: False)()


class TextFieldHandler(FieldHandler):
    def validate(self, value: Any, config: dict) -> tuple[bool, Optional[str]]:
        if value is None:
            return True, None
        if not isinstance(value, str):
            return False, "Value must be a string"
        max_len = config.get("max_length")
        if max_len and len(value) > max_len:
            return False, f"Value exceeds maximum length of {max_len}"
        return True, None
    
    def serialize(self, value: Any, config: dict) -> Any:
        return str(value) if value is not None else None
    
    def deserialize(self, value: Any, config: dict) -> Any:
        return value
    
    def format_display(self, value: Any, config: dict) -> str:
        return str(value) if value else ""
    
    def get_sort_key(self, value: Any, config: dict) -> Any:
        return (value or "").lower()


class NumberFieldHandler(FieldHandler):
    def validate(self, value: Any, config: dict) -> tuple[bool, Optional[str]]:
        if value is None:
            return True, None
        try:
            num = Decimal(str(value))
            if not config.get("allow_negative", True) and num < 0:
                return False, "Negative values not allowed"
            min_val = config.get("min_value")
            max_val = config.get("max_value")
            if min_val is not None and num < Decimal(str(min_val)):
                return False, f"Value below minimum of {min_val}"
            if max_val is not None and num > Decimal(str(max_val)):
                return False, f"Value exceeds maximum of {max_val}"
            return True, None
        except:
            return False, "Invalid number format"
    
    def serialize(self, value: Any, config: dict) -> Any:
        if value is None:
            return None
        return float(Decimal(str(value)))
    
    def deserialize(self, value: Any, config: dict) -> Any:
        return Decimal(str(value)) if value is not None else None
    
    def format_display(self, value: Any, config: dict) -> str:
        if value is None:
            return ""
        precision = config.get("precision", 2)
        return f"{value:,.{precision}f}"
    
    def get_sort_key(self, value: Any, config: dict) -> Any:
        return float(value) if value is not None else float('-inf')


# Registry of field handlers
FIELD_HANDLERS: Dict[FieldType, FieldHandler] = {
    FieldType.TEXT: TextFieldHandler(),
    FieldType.NUMBER: NumberFieldHandler(),
    # ... additional handlers
}
```

---

## 4. Views System

### 4.1 View Types

```python
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ViewType(str, Enum):
    GRID = "grid"
    KANBAN = "kanban"
    CALENDAR = "calendar"
    GALLERY = "gallery"
    FORM = "form"
    GANTT = "gantt"
    TIMELINE = "timeline"
    LIST = "list"


class FilterOperator(str, Enum):
    # Text operators
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    
    # Number operators
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    BETWEEN = "between"
    
    # Date operators
    IS_TODAY = "is_today"
    IS_BEFORE = "is_before"
    IS_AFTER = "is_after"
    IS_WITHIN = "is_within"
    
    # Select operators
    IS_ANY_OF = "is_any_of"
    IS_NONE_OF = "is_none_of"


class FilterCondition(BaseModel):
    field_id: str
    operator: FilterOperator
    value: Any
    

class FilterGroup(BaseModel):
    conjunction: str = "and"  # and, or
    conditions: List[FilterCondition] = []
    groups: List["FilterGroup"] = []


class SortConfig(BaseModel):
    field_id: str
    direction: str = "asc"  # asc, desc


class GroupConfig(BaseModel):
    field_id: str
    order: str = "asc"
    collapsed_groups: List[str] = []


class ViewConfig(BaseModel):
    # Common config
    filters: Optional[FilterGroup] = None
    sorts: List[SortConfig] = []
    hidden_fields: List[str] = []
    field_order: List[str] = []
    
    # Grid-specific
    field_widths: Dict[str, int] = {}
    row_height: str = "medium"  # short, medium, tall, extra_tall
    frozen_fields: List[str] = []
    
    # Kanban-specific
    kanban_field_id: Optional[str] = None
    kanban_hide_empty: bool = False
    kanban_card_cover_field: Optional[str] = None
    kanban_card_fields: List[str] = []
    
    # Calendar-specific
    calendar_date_field_id: Optional[str] = None
    calendar_end_date_field_id: Optional[str] = None
    calendar_label_field_id: Optional[str] = None
    
    # Gallery-specific
    gallery_cover_field_id: Optional[str] = None
    gallery_cover_fit: str = "cover"  # cover, contain
    gallery_card_fields: List[str] = []
    
    # Gantt-specific
    gantt_start_field_id: Optional[str] = None
    gantt_end_field_id: Optional[str] = None
    gantt_dependency_field_id: Optional[str] = None
    gantt_progress_field_id: Optional[str] = None
    
    # Form-specific
    form_title: Optional[str] = None
    form_description: Optional[str] = None
    form_cover_image: Optional[str] = None
    form_submit_button_label: str = "Submit"
    form_show_branding: bool = True
    form_redirect_url: Optional[str] = None
    form_fields: List[Dict[str, Any]] = []  # Field configs with required, description


class ViewEngine:
    """Engine for applying view configurations to record queries"""
    
    def __init__(self, session, table_id: str, view_config: ViewConfig):
        self.session = session
        self.table_id = table_id
        self.config = view_config
    
    def build_query(self):
        """Build SQLAlchemy query with filters, sorts, groupings"""
        from sqlalchemy import and_, or_, func
        
        query = self.session.query(Record).filter(Record.table_id == self.table_id)
        
        # Apply filters
        if self.config.filters:
            query = self._apply_filter_group(query, self.config.filters)
        
        # Apply sorts
        for sort in self.config.sorts:
            direction = "asc" if sort.direction == "asc" else "desc"
            # Use JSONB extraction with proper typing
            query = query.order_by(
                getattr(Record.data[sort.field_id].astext, direction)()
            )
        
        return query
    
    def _apply_filter_group(self, query, group: FilterGroup):
        """Recursively apply filter groups"""
        conditions = []
        
        for condition in group.conditions:
            sql_condition = self._build_condition(condition)
            if sql_condition is not None:
                conditions.append(sql_condition)
        
        for subgroup in group.groups:
            subquery = self._apply_filter_group(query, subgroup)
            conditions.append(subquery)
        
        if group.conjunction == "and":
            return query.filter(and_(*conditions))
        else:
            return query.filter(or_(*conditions))
    
    def _build_condition(self, condition: FilterCondition):
        """Build SQL condition from filter condition"""
        field_data = Record.data[condition.field_id]
        
        operators = {
            FilterOperator.EQUALS: lambda: field_data.astext == str(condition.value),
            FilterOperator.NOT_EQUALS: lambda: field_data.astext != str(condition.value),
            FilterOperator.CONTAINS: lambda: field_data.astext.ilike(f"%{condition.value}%"),
            FilterOperator.IS_EMPTY: lambda: or_(field_data.is_(None), field_data.astext == ""),
            FilterOperator.GREATER_THAN: lambda: field_data.astext.cast(Float) > condition.value,
            # ... more operators
        }
        
        return operators.get(condition.operator, lambda: None)()
```

---

## 5. PDF Extraction System

### 5.1 PDF Processing Pipeline

```python
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import pdfplumber
import tabula
import fitz  # PyMuPDF
from PIL import Image
import pytesseract


class ExtractionMethod(Enum):
    PDFPLUMBER = "pdfplumber"
    TABULA = "tabula"
    PYMUPDF = "pymupdf"
    OCR = "ocr"
    HYBRID = "hybrid"


@dataclass
class ExtractedTable:
    page_number: int
    table_index: int
    headers: List[str]
    rows: List[List[Any]]
    confidence: float
    bounding_box: Optional[Dict[str, float]] = None
    extraction_method: ExtractionMethod = ExtractionMethod.PDFPLUMBER


@dataclass
class ExtractedText:
    page_number: int
    text: str
    bounding_box: Optional[Dict[str, float]] = None


@dataclass
class ExtractionResult:
    filename: str
    page_count: int
    tables: List[ExtractedTable]
    text_blocks: List[ExtractedText]
    metadata: Dict[str, Any]
    errors: List[str]


class PDFExtractor:
    """Comprehensive PDF extraction with multiple methods"""
    
    def __init__(self, pdf_path: str | Path | bytes):
        if isinstance(pdf_path, bytes):
            self.pdf_bytes = pdf_path
            self.pdf_path = None
        else:
            self.pdf_path = Path(pdf_path)
            with open(self.pdf_path, 'rb') as f:
                self.pdf_bytes = f.read()
    
    def extract_all(
        self, 
        method: ExtractionMethod = ExtractionMethod.HYBRID,
        ocr_enabled: bool = True
    ) -> ExtractionResult:
        """Extract tables and text from PDF"""
        
        tables = []
        text_blocks = []
        errors = []
        
        # Get metadata and page count
        metadata = self._extract_metadata()
        page_count = metadata.get('page_count', 0)
        
        try:
            if method in [ExtractionMethod.PDFPLUMBER, ExtractionMethod.HYBRID]:
                tables.extend(self._extract_with_pdfplumber())
                text_blocks.extend(self._extract_text_with_pdfplumber())
            
            if method in [ExtractionMethod.TABULA, ExtractionMethod.HYBRID]:
                tabula_tables = self._extract_with_tabula()
                # Merge with existing tables, preferring higher confidence
                tables = self._merge_tables(tables, tabula_tables)
            
            if method == ExtractionMethod.OCR or (ocr_enabled and not tables):
                # Use OCR for scanned PDFs
                ocr_tables, ocr_text = self._extract_with_ocr()
                tables.extend(ocr_tables)
                text_blocks.extend(ocr_text)
                
        except Exception as e:
            errors.append(str(e))
        
        return ExtractionResult(
            filename=str(self.pdf_path) if self.pdf_path else "uploaded.pdf",
            page_count=page_count,
            tables=tables,
            text_blocks=text_blocks,
            metadata=metadata,
            errors=errors
        )
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract PDF metadata using PyMuPDF"""
        doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
        metadata = {
            'page_count': len(doc),
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'creator': doc.metadata.get('creator', ''),
            'creation_date': doc.metadata.get('creationDate', ''),
            'modification_date': doc.metadata.get('modDate', ''),
        }
        doc.close()
        return metadata
    
    def _extract_with_pdfplumber(self) -> List[ExtractedTable]:
        """Extract tables using pdfplumber (best for most PDFs)"""
        tables = []
        
        with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_tables = page.extract_tables()
                
                for table_idx, table in enumerate(page_tables):
                    if not table or len(table) < 2:
                        continue
                    
                    # Clean and process table
                    headers = [str(h).strip() if h else f"Column_{i}" 
                              for i, h in enumerate(table[0])]
                    rows = [
                        [self._clean_cell(cell) for cell in row]
                        for row in table[1:]
                    ]
                    
                    # Calculate confidence based on cell consistency
                    confidence = self._calculate_confidence(headers, rows)
                    
                    tables.append(ExtractedTable(
                        page_number=page_num,
                        table_index=table_idx,
                        headers=headers,
                        rows=rows,
                        confidence=confidence,
                        extraction_method=ExtractionMethod.PDFPLUMBER
                    ))
        
        return tables
    
    def _extract_with_tabula(self) -> List[ExtractedTable]:
        """Extract tables using Tabula (good for complex tables)"""
        tables = []
        
        # Save to temp file if needed (tabula requires file path)
        if self.pdf_path:
            dfs = tabula.read_pdf(str(self.pdf_path), pages='all', multiple_tables=True)
        else:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(self.pdf_bytes)
                tmp_path = tmp.name
            dfs = tabula.read_pdf(tmp_path, pages='all', multiple_tables=True)
            Path(tmp_path).unlink()
        
        for idx, df in enumerate(dfs):
            if df.empty:
                continue
            
            headers = [str(col) for col in df.columns.tolist()]
            rows = df.values.tolist()
            
            tables.append(ExtractedTable(
                page_number=1,  # Tabula doesn't always provide page number
                table_index=idx,
                headers=headers,
                rows=rows,
                confidence=0.7,  # Tabula typically has good accuracy
                extraction_method=ExtractionMethod.TABULA
            ))
        
        return tables
    
    def _extract_text_with_pdfplumber(self) -> List[ExtractedText]:
        """Extract text blocks from PDF"""
        text_blocks = []
        
        with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    text_blocks.append(ExtractedText(
                        page_number=page_num,
                        text=text.strip()
                    ))
        
        return text_blocks
    
    def _extract_with_ocr(self) -> tuple[List[ExtractedTable], List[ExtractedText]]:
        """Extract from scanned PDFs using OCR"""
        tables = []
        text_blocks = []
        
        doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
        
        for page_num, page in enumerate(doc, 1):
            # Convert page to image
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # OCR the image
            ocr_text = pytesseract.image_to_string(img)
            
            if ocr_text.strip():
                text_blocks.append(ExtractedText(
                    page_number=page_num,
                    text=ocr_text.strip()
                ))
            
            # Try to extract tables from OCR text
            # (Basic implementation - could use more sophisticated table detection)
            ocr_tables = self._detect_tables_from_text(ocr_text, page_num)
            tables.extend(ocr_tables)
        
        doc.close()
        return tables, text_blocks
    
    def _clean_cell(self, cell: Any) -> Any:
        """Clean and normalize cell value"""
        if cell is None:
            return None
        cell_str = str(cell).strip()
        if not cell_str:
            return None
        
        # Try to convert to number
        try:
            if '.' in cell_str or ',' in cell_str:
                return float(cell_str.replace(',', ''))
            return int(cell_str.replace(',', ''))
        except ValueError:
            pass
        
        return cell_str
    
    def _calculate_confidence(self, headers: List[str], rows: List[List]) -> float:
        """Calculate extraction confidence score"""
        if not rows:
            return 0.0
        
        # Check for consistent column counts
        expected_cols = len(headers)
        consistent_rows = sum(1 for row in rows if len(row) == expected_cols)
        consistency_score = consistent_rows / len(rows)
        
        # Check for non-empty cells
        total_cells = sum(len(row) for row in rows)
        non_empty_cells = sum(1 for row in rows for cell in row if cell)
        fill_score = non_empty_cells / total_cells if total_cells else 0
        
        return (consistency_score * 0.6 + fill_score * 0.4)
    
    def _merge_tables(
        self, 
        tables1: List[ExtractedTable], 
        tables2: List[ExtractedTable]
    ) -> List[ExtractedTable]:
        """Merge tables from different extraction methods, preferring higher confidence"""
        # Simple merge - could be more sophisticated with overlap detection
        all_tables = tables1 + tables2
        # Sort by confidence and remove duplicates based on similarity
        all_tables.sort(key=lambda t: t.confidence, reverse=True)
        return all_tables
    
    def _detect_tables_from_text(self, text: str, page_num: int) -> List[ExtractedTable]:
        """Detect tables from OCR text (basic implementation)"""
        # This is a simplified implementation
        # A production version would use more sophisticated pattern matching
        tables = []
        lines = text.split('\n')
        
        # Look for lines with consistent delimiters
        potential_tables = []
        current_table = []
        
        for line in lines:
            # Check for tab or multiple space delimiters
            if '\t' in line or '  ' in line:
                cells = [c.strip() for c in line.split('\t') if c.strip()]
                if not cells:
                    cells = [c.strip() for c in line.split('  ') if c.strip()]
                if len(cells) >= 2:
                    current_table.append(cells)
            else:
                if len(current_table) >= 3:  # Minimum 3 rows to be a table
                    potential_tables.append(current_table)
                current_table = []
        
        if len(current_table) >= 3:
            potential_tables.append(current_table)
        
        for idx, table in enumerate(potential_tables):
            # Normalize column counts
            max_cols = max(len(row) for row in table)
            normalized_table = [
                row + [None] * (max_cols - len(row)) for row in table
            ]
            
            tables.append(ExtractedTable(
                page_number=page_num,
                table_index=idx,
                headers=[f"Column_{i}" for i in range(max_cols)],
                rows=normalized_table,
                confidence=0.5,  # Lower confidence for OCR-detected tables
                extraction_method=ExtractionMethod.OCR
            ))
        
        return tables
    
    def create_table_from_extraction(
        self,
        table: ExtractedTable,
        table_name: str
    ) -> Dict[str, Any]:
        """Convert extracted table to PyBase table schema"""
        fields = []
        
        for idx, header in enumerate(table.headers):
            # Infer field type from data
            field_type = self._infer_field_type(table.rows, idx)
            
            fields.append({
                'name': header,
                'field_type': field_type,
                'position': idx
            })
        
        return {
            'name': table_name,
            'fields': fields,
            'records': [
                {f'field_{i}': cell for i, cell in enumerate(row)}
                for row in table.rows
            ]
        }
    
    def _infer_field_type(self, rows: List[List], col_idx: int) -> str:
        """Infer field type from column data"""
        values = [row[col_idx] for row in rows if col_idx < len(row) and row[col_idx]]
        
        if not values:
            return FieldType.TEXT.value
        
        # Check for numbers
        num_count = sum(1 for v in values if isinstance(v, (int, float)))
        if num_count / len(values) > 0.8:
            return FieldType.NUMBER.value
        
        # Check for dates
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}-\d{2}-\d{4}'
        ]
        import re
        date_count = sum(
            1 for v in values 
            if any(re.match(p, str(v)) for p in date_patterns)
        )
        if date_count / len(values) > 0.8:
            return FieldType.DATE.value
        
        # Check for emails
        email_count = sum(1 for v in values if '@' in str(v))
        if email_count / len(values) > 0.8:
            return FieldType.EMAIL.value
        
        # Check for URLs
        url_count = sum(1 for v in values if str(v).startswith(('http://', 'https://')))
        if url_count / len(values) > 0.8:
            return FieldType.URL.value
        
        # Default to text
        return FieldType.TEXT.value
```

---

## 6. Formula Engine

### 6.1 Formula Parser and Evaluator

```python
import ast
import operator
from typing import Any, Dict, List, Callable
from datetime import datetime, date, timedelta
from decimal import Decimal
import re


class FormulaFunction:
    """Registry of formula functions"""
    
    @staticmethod
    def IF(condition: bool, true_val: Any, false_val: Any) -> Any:
        return true_val if condition else false_val
    
    @staticmethod
    def AND(*args: bool) -> bool:
        return all(args)
    
    @staticmethod
    def OR(*args: bool) -> bool:
        return any(args)
    
    @staticmethod
    def NOT(val: bool) -> bool:
        return not val
    
    @staticmethod
    def SUM(*args) -> Decimal:
        return sum(Decimal(str(a)) for a in args if a is not None)
    
    @staticmethod
    def AVERAGE(*args) -> Decimal:
        values = [Decimal(str(a)) for a in args if a is not None]
        return sum(values) / len(values) if values else Decimal(0)
    
    @staticmethod
    def MIN(*args) -> Any:
        values = [a for a in args if a is not None]
        return min(values) if values else None
    
    @staticmethod
    def MAX(*args) -> Any:
        values = [a for a in args if a is not None]
        return max(values) if values else None
    
    @staticmethod
    def COUNT(*args) -> int:
        return sum(1 for a in args if a is not None)
    
    @staticmethod
    def COUNTA(*args) -> int:
        return sum(1 for a in args if a is not None and a != "")
    
    @staticmethod
    def CONCAT(*args) -> str:
        return "".join(str(a) for a in args if a is not None)
    
    @staticmethod
    def CONCATENATE(*args) -> str:
        return FormulaFunction.CONCAT(*args)
    
    @staticmethod
    def LEN(text: str) -> int:
        return len(str(text)) if text else 0
    
    @staticmethod
    def LEFT(text: str, num_chars: int = 1) -> str:
        return str(text)[:int(num_chars)] if text else ""
    
    @staticmethod
    def RIGHT(text: str, num_chars: int = 1) -> str:
        return str(text)[-int(num_chars):] if text else ""
    
    @staticmethod
    def MID(text: str, start: int, num_chars: int) -> str:
        return str(text)[int(start)-1:int(start)-1+int(num_chars)] if text else ""
    
    @staticmethod
    def LOWER(text: str) -> str:
        return str(text).lower() if text else ""
    
    @staticmethod
    def UPPER(text: str) -> str:
        return str(text).upper() if text else ""
    
    @staticmethod
    def TRIM(text: str) -> str:
        return str(text).strip() if text else ""
    
    @staticmethod
    def SUBSTITUTE(text: str, old: str, new: str) -> str:
        return str(text).replace(old, new) if text else ""
    
    @staticmethod
    def ROUND(number: Any, decimals: int = 0) -> Decimal:
        return round(Decimal(str(number)), int(decimals))
    
    @staticmethod
    def FLOOR(number: Any) -> int:
        import math
        return math.floor(float(number))
    
    @staticmethod
    def CEILING(number: Any) -> int:
        import math
        return math.ceil(float(number))
    
    @staticmethod
    def ABS(number: Any) -> Decimal:
        return abs(Decimal(str(number)))
    
    @staticmethod
    def POWER(base: Any, exponent: Any) -> Decimal:
        return Decimal(str(base)) ** Decimal(str(exponent))
    
    @staticmethod
    def SQRT(number: Any) -> Decimal:
        import math
        return Decimal(str(math.sqrt(float(number))))
    
    @staticmethod
    def TODAY() -> date:
        return date.today()
    
    @staticmethod
    def NOW() -> datetime:
        return datetime.now()
    
    @staticmethod
    def YEAR(date_val: date) -> int:
        return date_val.year if date_val else None
    
    @staticmethod
    def MONTH(date_val: date) -> int:
        return date_val.month if date_val else None
    
    @staticmethod
    def DAY(date_val: date) -> int:
        return date_val.day if date_val else None
    
    @staticmethod
    def DATEADD(date_val: date, num: int, unit: str) -> date:
        units = {
            'days': timedelta(days=int(num)),
            'weeks': timedelta(weeks=int(num)),
            'months': timedelta(days=int(num) * 30),  # Approximate
            'years': timedelta(days=int(num) * 365),  # Approximate
        }
        return date_val + units.get(unit.lower(), timedelta(days=int(num)))
    
    @staticmethod
    def DATEDIF(start: date, end: date, unit: str) -> int:
        delta = end - start
        units = {
            'd': delta.days,
            'm': delta.days // 30,
            'y': delta.days // 365,
        }
        return units.get(unit.lower(), delta.days)
    
    @staticmethod
    def BLANK() -> None:
        return None
    
    @staticmethod
    def ERROR(message: str = "Error") -> None:
        raise ValueError(message)


class FormulaEngine:
    """Parse and evaluate Airtable-style formulas"""
    
    FUNCTIONS = {
        name: getattr(FormulaFunction, name)
        for name in dir(FormulaFunction)
        if not name.startswith('_') and callable(getattr(FormulaFunction, name))
    }
    
    OPERATORS = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '%': operator.mod,
        '^': operator.pow,
        '&': lambda a, b: str(a) + str(b),  # Concatenation
        '=': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
    }
    
    def __init__(self, fields: Dict[str, Any], record_data: Dict[str, Any]):
        """
        Initialize formula engine with field definitions and record data
        
        Args:
            fields: Dict mapping field_id to field definition
            record_data: Dict mapping field_id to value
        """
        self.fields = fields
        self.record_data = record_data
        self._field_name_to_id = {f['name']: fid for fid, f in fields.items()}
    
    def evaluate(self, formula: str) -> Any:
        """Evaluate a formula string"""
        try:
            # Parse and evaluate the formula
            tokens = self._tokenize(formula)
            result = self._evaluate_tokens(tokens)
            return result
        except Exception as e:
            return f"#ERROR: {str(e)}"
    
    def _tokenize(self, formula: str) -> List[Any]:
        """Tokenize formula into components"""
        tokens = []
        i = 0
        
        while i < len(formula):
            char = formula[i]
            
            # Skip whitespace
            if char.isspace():
                i += 1
                continue
            
            # Field reference: {Field Name}
            if char == '{':
                end = formula.index('}', i)
                field_name = formula[i+1:end]
                tokens.append(('FIELD', field_name))
                i = end + 1
                continue
            
            # String literal
            if char in '"\'':
                quote = char
                end = formula.index(quote, i + 1)
                tokens.append(('STRING', formula[i+1:end]))
                i = end + 1
                continue
            
            # Number
            if char.isdigit() or (char == '.' and i + 1 < len(formula) and formula[i+1].isdigit()):
                match = re.match(r'[\d.]+', formula[i:])
                tokens.append(('NUMBER', Decimal(match.group())))
                i += len(match.group())
                continue
            
            # Function or identifier
            if char.isalpha() or char == '_':
                match = re.match(r'[a-zA-Z_][a-zA-Z0-9_]*', formula[i:])
                name = match.group().upper()
                if name in ('TRUE', 'FALSE'):
                    tokens.append(('BOOL', name == 'TRUE'))
                elif name in self.FUNCTIONS:
                    tokens.append(('FUNC', name))
                else:
                    tokens.append(('IDENT', name))
                i += len(match.group())
                continue
            
            # Operators
            if char in '+-*/%^&':
                tokens.append(('OP', char))
                i += 1
                continue
            
            # Comparison operators
            if char in '=<>!':
                if i + 1 < len(formula) and formula[i+1] == '=':
                    tokens.append(('OP', char + '='))
                    i += 2
                else:
                    tokens.append(('OP', char))
                    i += 1
                continue
            
            # Parentheses
            if char in '()':
                tokens.append(('PAREN', char))
                i += 1
                continue
            
            # Comma
            if char == ',':
                tokens.append(('COMMA', ','))
                i += 1
                continue
            
            i += 1
        
        return tokens
    
    def _evaluate_tokens(self, tokens: List[tuple]) -> Any:
        """Evaluate tokenized formula"""
        pos = [0]  # Mutable position counter
        
        def parse_expression():
            """Parse full expression with operators"""
            left = parse_term()
            
            while pos[0] < len(tokens):
                if tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] in ('=', '!=', '<', '<=', '>', '>=', '&'):
                    op = tokens[pos[0]][1]
                    pos[0] += 1
                    right = parse_term()
                    left = self.OPERATORS[op](left, right)
                else:
                    break
            
            return left
        
        def parse_term():
            """Parse term with +/-"""
            left = parse_factor()
            
            while pos[0] < len(tokens):
                if tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] in ('+', '-'):
                    op = tokens[pos[0]][1]
                    pos[0] += 1
                    right = parse_factor()
                    left = self.OPERATORS[op](left, right)
                else:
                    break
            
            return left
        
        def parse_factor():
            """Parse factor with */%"""
            left = parse_power()
            
            while pos[0] < len(tokens):
                if tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] in ('*', '/', '%'):
                    op = tokens[pos[0]][1]
                    pos[0] += 1
                    right = parse_power()
                    left = self.OPERATORS[op](left, right)
                else:
                    break
            
            return left
        
        def parse_power():
            """Parse power with ^"""
            left = parse_unary()
            
            if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '^':
                pos[0] += 1
                right = parse_power()  # Right associative
                return self.OPERATORS['^'](left, right)
            
            return left
        
        def parse_unary():
            """Parse unary operators"""
            if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '-':
                pos[0] += 1
                return -parse_primary()
            return parse_primary()
        
        def parse_primary():
            """Parse primary values and function calls"""
            if pos[0] >= len(tokens):
                return None
            
            token_type, token_value = tokens[pos[0]]
            
            if token_type == 'NUMBER':
                pos[0] += 1
                return token_value
            
            if token_type == 'STRING':
                pos[0] += 1
                return token_value
            
            if token_type == 'BOOL':
                pos[0] += 1
                return token_value
            
            if token_type == 'FIELD':
                pos[0] += 1
                # Look up field value
                field_id = self._field_name_to_id.get(token_value)
                if field_id:
                    return self.record_data.get(field_id)
                return None
            
            if token_type == 'FUNC':
                func_name = token_value
                pos[0] += 1
                
                # Expect opening paren
                if pos[0] < len(tokens) and tokens[pos[0]] == ('PAREN', '('):
                    pos[0] += 1
                    args = []
                    
                    # Parse arguments
                    while pos[0] < len(tokens):
                        if tokens[pos[0]] == ('PAREN', ')'):
                            pos[0] += 1
                            break
                        
                        args.append(parse_expression())
                        
                        if pos[0] < len(tokens) and tokens[pos[0]] == ('COMMA', ','):
                            pos[0] += 1
                    
                    # Call function
                    func = self.FUNCTIONS.get(func_name)
                    if func:
                        return func(*args)
                
                return None
            
            if token_type == 'PAREN' and token_value == '(':
                pos[0] += 1
                result = parse_expression()
                if pos[0] < len(tokens) and tokens[pos[0]] == ('PAREN', ')'):
                    pos[0] += 1
                return result
            
            pos[0] += 1
            return None
        
        return parse_expression()
    
    def get_dependencies(self, formula: str) -> List[str]:
        """Get list of field IDs that this formula depends on"""
        tokens = self._tokenize(formula)
        dependencies = []
        
        for token_type, token_value in tokens:
            if token_type == 'FIELD':
                field_id = self._field_name_to_id.get(token_value)
                if field_id:
                    dependencies.append(field_id)
        
        return dependencies
```

---

## 7. Automation System

### 7.1 Automation Engine

```python
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio
import httpx


class TriggerType(str, Enum):
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    RECORD_ENTERS_VIEW = "record_enters_view"
    RECORD_MATCHES_CONDITIONS = "record_matches_conditions"
    FORM_SUBMITTED = "form_submitted"
    SCHEDULED = "scheduled"
    WEBHOOK_RECEIVED = "webhook_received"
    BUTTON_CLICKED = "button_clicked"


class ActionType(str, Enum):
    SEND_EMAIL = "send_email"
    SEND_SLACK_MESSAGE = "send_slack_message"
    SEND_WEBHOOK = "send_webhook"
    CREATE_RECORD = "create_record"
    UPDATE_RECORD = "update_record"
    DELETE_RECORD = "delete_record"
    LINK_RECORDS = "link_records"
    RUN_SCRIPT = "run_script"
    SEND_SMS = "send_sms"
    NOTIFY_USER = "notify_user"


class TriggerConfig(BaseModel):
    type: TriggerType
    table_id: Optional[str] = None
    view_id: Optional[str] = None
    field_id: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None  # For scheduled triggers


class ActionConfig(BaseModel):
    type: ActionType
    config: Dict[str, Any]
    # Config varies by action type


class AutomationRun(BaseModel):
    automation_id: str
    trigger_data: Dict[str, Any]
    status: str  # pending, running, success, failed
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    action_results: List[Dict[str, Any]] = []


class AutomationEngine:
    """Engine for running automations"""
    
    def __init__(self, session, celery_app):
        self.session = session
        self.celery = celery_app
        self._trigger_handlers: Dict[TriggerType, Callable] = {}
        self._action_handlers: Dict[ActionType, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """Register built-in trigger and action handlers"""
        # Action handlers
        self._action_handlers = {
            ActionType.SEND_EMAIL: self._action_send_email,
            ActionType.SEND_WEBHOOK: self._action_send_webhook,
            ActionType.CREATE_RECORD: self._action_create_record,
            ActionType.UPDATE_RECORD: self._action_update_record,
            ActionType.SEND_SLACK_MESSAGE: self._action_send_slack,
            ActionType.NOTIFY_USER: self._action_notify_user,
        }
    
    async def on_record_created(self, table_id: str, record: Dict[str, Any]):
        """Handle record creation event"""
        automations = self._get_automations_for_trigger(
            TriggerType.RECORD_CREATED, table_id
        )
        
        for automation in automations:
            if self._check_conditions(automation.trigger_config, record):
                await self._run_automation(automation, {'record': record})
    
    async def on_record_updated(
        self, 
        table_id: str, 
        record: Dict[str, Any], 
        changes: Dict[str, Any]
    ):
        """Handle record update event"""
        automations = self._get_automations_for_trigger(
            TriggerType.RECORD_UPDATED, table_id
        )
        
        for automation in automations:
            trigger_config = automation.trigger_config
            
            # Check if monitored fields changed
            if trigger_config.get('field_id'):
                if trigger_config['field_id'] not in changes:
                    continue
            
            if self._check_conditions(trigger_config, record):
                await self._run_automation(
                    automation, 
                    {'record': record, 'changes': changes}
                )
    
    async def _run_automation(
        self, 
        automation: Any, 
        trigger_data: Dict[str, Any]
    ):
        """Execute automation actions"""
        run = AutomationRun(
            automation_id=str(automation.id),
            trigger_data=trigger_data,
            status="running",
            started_at=datetime.utcnow()
        )
        
        try:
            for action_config in automation.action_config:
                action_type = ActionType(action_config['type'])
                handler = self._action_handlers.get(action_type)
                
                if handler:
                    # Resolve template variables in config
                    resolved_config = self._resolve_templates(
                        action_config['config'],
                        trigger_data
                    )
                    
                    result = await handler(resolved_config, trigger_data)
                    run.action_results.append({
                        'action': action_type.value,
                        'success': True,
                        'result': result
                    })
            
            run.status = "success"
            
        except Exception as e:
            run.status = "failed"
            run.error = str(e)
        
        finally:
            run.completed_at = datetime.utcnow()
            # Save run to database
            self._save_automation_run(run)
        
        return run
    
    def _resolve_templates(
        self, 
        config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve template variables like {{record.field_name}}"""
        import re
        
        def replace_var(match):
            path = match.group(1).split('.')
            value = context
            for key in path:
                if isinstance(value, dict):
                    value = value.get(key, '')
                else:
                    value = ''
                    break
            return str(value) if value else ''
        
        def resolve_value(val):
            if isinstance(val, str):
                return re.sub(r'\{\{([^}]+)\}\}', replace_var, val)
            elif isinstance(val, dict):
                return {k: resolve_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [resolve_value(v) for v in val]
            return val
        
        return resolve_value(config)
    
    async def _action_send_email(
        self, 
        config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email action"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = config.get('from', 'noreply@pybase.app')
        msg['To'] = config['to']
        msg['Subject'] = config['subject']
        
        body = config.get('body', '')
        msg.attach(MIMEText(body, 'html'))
        
        # Send via SMTP (configure from settings)
        # ... SMTP sending logic
        
        return {'sent_to': config['to']}
    
    async def _action_send_webhook(
        self, 
        config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send webhook action"""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=config.get('method', 'POST'),
                url=config['url'],
                json=config.get('body', context),
                headers=config.get('headers', {}),
                timeout=30.0
            )
            
            return {
                'status_code': response.status_code,
                'response': response.text[:500]  # Truncate response
            }
    
    async def _action_create_record(
        self, 
        config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create record action"""
        table_id = config['table_id']
        fields = config['fields']
        
        # Create record via service
        record = await RecordService(self.session).create_record(
            table_id=table_id,
            data=fields
        )
        
        return {'record_id': str(record.id)}
    
    async def _action_update_record(
        self, 
        config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update record action"""
        record_id = config.get('record_id') or context.get('record', {}).get('id')
        fields = config['fields']
        
        # Update record via service
        await RecordService(self.session).update_record(
            record_id=record_id,
            data=fields
        )
        
        return {'record_id': record_id}
    
    async def _action_send_slack(
        self, 
        config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send Slack message action"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config['webhook_url'],
                json={
                    'text': config['message'],
                    'channel': config.get('channel'),
                    'username': config.get('username', 'PyBase')
                }
            )
            return {'status': 'sent' if response.status_code == 200 else 'failed'}
    
    async def _action_notify_user(
        self, 
        config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send in-app notification"""
        # Create notification in database
        # Push via WebSocket
        return {'notified': config['user_id']}
    
    def _get_automations_for_trigger(
        self, 
        trigger_type: TriggerType, 
        table_id: str
    ) -> List[Any]:
        """Get active automations matching trigger type and table"""
        from sqlalchemy import and_
        
        return self.session.query(Automation).filter(
            and_(
                Automation.is_active == True,
                Automation.trigger_config['type'].astext == trigger_type.value,
                Automation.trigger_config['table_id'].astext == table_id
            )
        ).all()
    
    def _check_conditions(
        self, 
        trigger_config: Dict[str, Any], 
        record: Dict[str, Any]
    ) -> bool:
        """Check if record matches trigger conditions"""
        conditions = trigger_config.get('conditions')
        if not conditions:
            return True
        
        # Use ViewEngine's filter logic
        filter_group = FilterGroup(**conditions)
        # ... evaluate conditions
        return True
    
    def _save_automation_run(self, run: AutomationRun):
        """Save automation run to database"""
        # Implementation
        pass
```

---

## 8. API Design

### 8.1 REST API Endpoints

```python
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from pydantic import BaseModel
import uuid

app = FastAPI(title="PyBase API", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# === BASES ===

class BaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_id: uuid.UUID


class BaseResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    workspace_id: uuid.UUID
    created_at: datetime
    tables: List["TableSummary"] = []


router = APIRouter(prefix="/api/v1")


@router.post("/bases", response_model=BaseResponse)
async def create_base(base: BaseCreate, user=Depends(get_current_user)):
    """Create a new base"""
    pass


@router.get("/bases/{base_id}", response_model=BaseResponse)
async def get_base(base_id: uuid.UUID, user=Depends(get_current_user)):
    """Get base details"""
    pass


@router.get("/bases/{base_id}/schema")
async def get_base_schema(base_id: uuid.UUID, user=Depends(get_current_user)):
    """Get complete schema (tables, fields, views)"""
    pass


# === TABLES ===

class TableCreate(BaseModel):
    name: str
    description: Optional[str] = None
    fields: List["FieldCreate"] = []


class FieldCreate(BaseModel):
    name: str
    field_type: str
    config: Optional[dict] = {}


@router.post("/bases/{base_id}/tables", response_model="TableResponse")
async def create_table(
    base_id: uuid.UUID, 
    table: TableCreate, 
    user=Depends(get_current_user)
):
    """Create a new table"""
    pass


@router.patch("/tables/{table_id}")
async def update_table(
    table_id: uuid.UUID, 
    updates: dict, 
    user=Depends(get_current_user)
):
    """Update table properties"""
    pass


@router.delete("/tables/{table_id}")
async def delete_table(table_id: uuid.UUID, user=Depends(get_current_user)):
    """Delete a table"""
    pass


# === FIELDS ===

@router.post("/tables/{table_id}/fields")
async def create_field(
    table_id: uuid.UUID, 
    field: FieldCreate, 
    user=Depends(get_current_user)
):
    """Add a new field to table"""
    pass


@router.patch("/fields/{field_id}")
async def update_field(
    field_id: uuid.UUID, 
    updates: dict, 
    user=Depends(get_current_user)
):
    """Update field configuration"""
    pass


@router.delete("/fields/{field_id}")
async def delete_field(field_id: uuid.UUID, user=Depends(get_current_user)):
    """Delete a field"""
    pass


# === RECORDS ===

class RecordCreate(BaseModel):
    fields: dict  # {field_id: value}


class RecordListResponse(BaseModel):
    records: List[dict]
    offset: Optional[str]
    total: int


@router.get("/tables/{table_id}/records", response_model=RecordListResponse)
async def list_records(
    table_id: uuid.UUID,
    view_id: Optional[uuid.UUID] = None,
    filter_by_formula: Optional[str] = None,
    sort: Optional[List[str]] = Query(None),
    fields: Optional[List[str]] = Query(None),
    max_records: int = Query(100, le=1000),
    offset: Optional[str] = None,
    user=Depends(get_current_user)
):
    """List records with filtering, sorting, pagination"""
    pass


@router.post("/tables/{table_id}/records")
async def create_records(
    table_id: uuid.UUID,
    records: List[RecordCreate],
    user=Depends(get_current_user)
):
    """Create one or more records (max 10 per request)"""
    pass


@router.get("/records/{record_id}")
async def get_record(record_id: uuid.UUID, user=Depends(get_current_user)):
    """Get single record"""
    pass


@router.patch("/records/{record_id}")
async def update_record(
    record_id: uuid.UUID, 
    fields: dict, 
    user=Depends(get_current_user)
):
    """Update record fields"""
    pass


@router.delete("/records/{record_id}")
async def delete_record(record_id: uuid.UUID, user=Depends(get_current_user)):
    """Delete a record"""
    pass


# === VIEWS ===

@router.get("/tables/{table_id}/views")
async def list_views(table_id: uuid.UUID, user=Depends(get_current_user)):
    """List all views for a table"""
    pass


@router.post("/tables/{table_id}/views")
async def create_view(
    table_id: uuid.UUID, 
    view: "ViewCreate", 
    user=Depends(get_current_user)
):
    """Create a new view"""
    pass


# === ATTACHMENTS ===

@router.post("/records/{record_id}/fields/{field_id}/attachments")
async def upload_attachment(
    record_id: uuid.UUID,
    field_id: uuid.UUID,
    file: UploadFile,
    user=Depends(get_current_user)
):
    """Upload attachment to record field"""
    pass


# === PDF EXTRACTION ===

@router.post("/extract/pdf")
async def extract_pdf(
    file: UploadFile,
    method: str = "hybrid",
    ocr: bool = True,
    user=Depends(get_current_user)
):
    """Extract tables and text from PDF"""
    extractor = PDFExtractor(await file.read())
    result = extractor.extract_all(
        method=ExtractionMethod(method),
        ocr_enabled=ocr
    )
    return result


@router.post("/extract/pdf/to-table")
async def pdf_to_table(
    base_id: uuid.UUID,
    file: UploadFile,
    table_name: str,
    table_index: int = 0,
    user=Depends(get_current_user)
):
    """Extract PDF table directly into a new PyBase table"""
    extractor = PDFExtractor(await file.read())
    result = extractor.extract_all()
    
    if table_index >= len(result.tables):
        raise HTTPException(400, "Table index out of range")
    
    table_schema = extractor.create_table_from_extraction(
        result.tables[table_index],
        table_name
    )
    
    # Create table and records
    # ...
    return {"table_id": "...", "record_count": len(table_schema['records'])}


# === IMPORT/EXPORT ===

@router.post("/tables/{table_id}/import")
async def import_data(
    table_id: uuid.UUID,
    file: UploadFile,
    format: str = "csv",  # csv, xlsx, json
    user=Depends(get_current_user)
):
    """Import data into existing table"""
    pass


@router.get("/tables/{table_id}/export")
async def export_data(
    table_id: uuid.UUID,
    view_id: Optional[uuid.UUID] = None,
    format: str = "csv",
    user=Depends(get_current_user)
):
    """Export table data"""
    pass


# === AUTOMATIONS ===

@router.get("/bases/{base_id}/automations")
async def list_automations(base_id: uuid.UUID, user=Depends(get_current_user)):
    """List automations for a base"""
    pass


@router.post("/bases/{base_id}/automations")
async def create_automation(
    base_id: uuid.UUID, 
    automation: "AutomationCreate", 
    user=Depends(get_current_user)
):
    """Create new automation"""
    pass


@router.post("/automations/{automation_id}/test")
async def test_automation(
    automation_id: uuid.UUID, 
    test_data: dict, 
    user=Depends(get_current_user)
):
    """Test automation with sample data"""
    pass


# === WEBHOOKS ===

@router.post("/webhooks")
async def create_webhook(
    table_id: uuid.UUID,
    events: List[str],  # record.created, record.updated, etc.
    url: str,
    user=Depends(get_current_user)
):
    """Create webhook subscription"""
    pass


# === SEARCH ===

@router.get("/bases/{base_id}/search")
async def search_base(
    base_id: uuid.UUID,
    q: str,
    table_ids: Optional[List[uuid.UUID]] = Query(None),
    user=Depends(get_current_user)
):
    """Full-text search across base"""
    pass


app.include_router(router)
```

---

## 9. Real-time Collaboration

### 9.1 WebSocket Handler

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Any
import json
import asyncio
from dataclasses import dataclass
from datetime import datetime
import redis.asyncio as redis


@dataclass
class Connection:
    websocket: WebSocket
    user_id: str
    subscriptions: Set[str]  # table_ids, view_ids
    connected_at: datetime


class ConnectionManager:
    """Manage WebSocket connections and real-time updates"""
    
    def __init__(self, redis_url: str):
        self.connections: Dict[str, Connection] = {}
        self.table_subscribers: Dict[str, Set[str]] = {}  # table_id -> connection_ids
        self.redis = redis.from_url(redis_url)
    
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        
        self.connections[connection_id] = Connection(
            websocket=websocket,
            user_id=user_id,
            subscriptions=set(),
            connected_at=datetime.utcnow()
        )
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        if connection_id in self.connections:
            conn = self.connections[connection_id]
            
            # Remove from all subscriptions
            for table_id in conn.subscriptions:
                if table_id in self.table_subscribers:
                    self.table_subscribers[table_id].discard(connection_id)
            
            del self.connections[connection_id]
    
    async def subscribe(self, connection_id: str, table_id: str):
        """Subscribe connection to table updates"""
        if connection_id in self.connections:
            self.connections[connection_id].subscriptions.add(table_id)
            
            if table_id not in self.table_subscribers:
                self.table_subscribers[table_id] = set()
            self.table_subscribers[table_id].add(connection_id)
            
            # Also subscribe to Redis channel for cross-server updates
            await self._subscribe_redis(table_id)
    
    async def unsubscribe(self, connection_id: str, table_id: str):
        """Unsubscribe connection from table updates"""
        if connection_id in self.connections:
            self.connections[connection_id].subscriptions.discard(table_id)
            
            if table_id in self.table_subscribers:
                self.table_subscribers[table_id].discard(connection_id)
    
    async def broadcast_table_update(
        self, 
        table_id: str, 
        event_type: str, 
        data: Dict[str, Any],
        exclude_connection: Optional[str] = None
    ):
        """Broadcast update to all subscribers of a table"""
        message = {
            'type': event_type,
            'table_id': table_id,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Publish to Redis for cross-server distribution
        await self.redis.publish(f"table:{table_id}", json.dumps(message))
        
        # Send to local connections
        if table_id in self.table_subscribers:
            for connection_id in self.table_subscribers[table_id]:
                if connection_id != exclude_connection:
                    await self._send_to_connection(connection_id, message)
    
    async def _send_to_connection(self, connection_id: str, message: dict):
        """Send message to specific connection"""
        if connection_id in self.connections:
            try:
                await self.connections[connection_id].websocket.send_json(message)
            except:
                await self.disconnect(connection_id)
    
    async def _subscribe_redis(self, table_id: str):
        """Subscribe to Redis channel for cross-server updates"""
        # Implementation with Redis PubSub
        pass


# WebSocket endpoint
manager = ConnectionManager(redis_url="redis://localhost:6379")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Verify token and get user
    user = await verify_token(token)
    if not user:
        await websocket.close(code=4001)
        return
    
    connection_id = await manager.connect(websocket, str(user.id))
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data['type'] == 'subscribe':
                await manager.subscribe(connection_id, data['table_id'])
                await websocket.send_json({
                    'type': 'subscribed',
                    'table_id': data['table_id']
                })
            
            elif data['type'] == 'unsubscribe':
                await manager.unsubscribe(connection_id, data['table_id'])
            
            elif data['type'] == 'ping':
                await websocket.send_json({'type': 'pong'})
            
            elif data['type'] == 'cell_edit':
                # Handle collaborative editing
                await handle_cell_edit(connection_id, data)
                
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)


async def handle_cell_edit(connection_id: str, data: dict):
    """Handle real-time cell editing"""
    record_id = data['record_id']
    field_id = data['field_id']
    value = data['value']
    table_id = data['table_id']
    
    # Update database
    # ... update logic
    
    # Broadcast to other users
    await manager.broadcast_table_update(
        table_id=table_id,
        event_type='cell_updated',
        data={
            'record_id': record_id,
            'field_id': field_id,
            'value': value,
            'updated_by': manager.connections[connection_id].user_id
        },
        exclude_connection=connection_id
    )
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Weeks 1-4)
- [ ] Project setup, Docker configuration
- [ ] Database schema implementation
- [ ] Core models (Workspace, Base, Table, Field, Record)
- [ ] Basic REST API (CRUD operations)
- [ ] Authentication (JWT)
- [ ] Basic field types (text, number, date, checkbox, select)

### Phase 2: Core Features (Weeks 5-8)
- [ ] Advanced field types (link, lookup, rollup, formula)
- [ ] Formula engine implementation
- [ ] Views system (Grid, Kanban, Calendar)
- [ ] Filtering, sorting, grouping
- [ ] File attachments (MinIO integration)

### Phase 3: PDF & Import/Export (Weeks 9-10)
- [ ] PDF extraction pipeline
- [ ] CSV/Excel import
- [ ] Export functionality
- [ ] Data validation

### Phase 4: Real-time & Collaboration (Weeks 11-12)
- [ ] WebSocket infrastructure
- [ ] Real-time updates
- [ ] Comments system
- [ ] Activity log

### Phase 5: Automations (Weeks 13-14)
- [ ] Automation engine
- [ ] Trigger types
- [ ] Action types
- [ ] Webhook support

### Phase 6: UI & Polish (Weeks 15-18)
- [ ] React frontend implementation
- [ ] View renderers (Grid, Kanban, etc.)
- [ ] Field editors
- [ ] Form builder
- [ ] User settings

### Phase 7: Advanced Features (Weeks 19-22)
- [ ] Full-text search (Meilisearch)
- [ ] Form views with public access
- [ ] Gantt view
- [ ] Gallery view
- [ ] API rate limiting

### Phase 8: Production Readiness (Weeks 23-24)
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation
- [ ] Deployment scripts
- [ ] Monitoring & logging

---

## 11. Project Structure

```
pybase/
├── alembic/                    # Database migrations
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings/configuration
│   ├── database.py             # Database connection
│   │
│   ├── api/                    # API routes
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependencies (auth, db)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── bases.py
│   │   │   ├── tables.py
│   │   │   ├── fields.py
│   │   │   ├── records.py
│   │   │   ├── views.py
│   │   │   ├── automations.py
│   │   │   ├── attachments.py
│   │   │   └── extraction.py
│   │   └── websocket.py
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── workspace.py
│   │   ├── table.py
│   │   ├── field.py
│   │   ├── record.py
│   │   ├── view.py
│   │   ├── automation.py
│   │   ├── attachment.py
│   │   └── user.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── table.py
│   │   ├── record.py
│   │   └── ...
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── base_service.py
│   │   ├── table_service.py
│   │   ├── record_service.py
│   │   ├── view_service.py
│   │   └── automation_service.py
│   │
│   ├── core/                   # Core engines
│   │   ├── __init__.py
│   │   ├── fields/             # Field type handlers
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── text.py
│   │   │   ├── number.py
│   │   │   ├── date.py
│   │   │   ├── select.py
│   │   │   ├── link.py
│   │   │   ├── formula.py
│   │   │   └── ...
│   │   ├── formula_engine.py
│   │   ├── view_engine.py
│   │   ├── automation_engine.py
│   │   └── pdf_extractor.py
│   │
│   ├── realtime/               # WebSocket/real-time
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── handlers.py
│   │
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── storage.py          # MinIO client
│       ├── search.py           # Meilisearch client
│       └── security.py
│
├── worker/                     # Celery workers
│   ├── __init__.py
│   ├── celery_app.py
│   └── tasks/
│       ├── automation.py
│       ├── export.py
│       └── pdf_processing.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── test_core/
│
├── frontend/                   # React frontend (or separate repo)
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── hooks/
│   │   ├── stores/
│   │   └── api/
│   └── package.json
│
├── scripts/                    # Utility scripts
│   ├── seed_data.py
│   └── migrate.py
│
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   └── docker-compose.yml
│
├── docs/
│   ├── api.md
│   ├── architecture.md
│   └── deployment.md
│
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── alembic.ini
├── .env.example
└── README.md
```

---

## 12. Dependencies (requirements.txt)

```
# Core Framework
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0

# Database
sqlalchemy>=2.0.0
asyncpg>=0.28.0
alembic>=1.11.0
psycopg2-binary>=2.9.0

# Async/Background Tasks
celery>=5.3.0
redis>=4.6.0

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# PDF Extraction
pdfplumber>=0.10.0
tabula-py>=2.8.0
PyMuPDF>=1.23.0
pytesseract>=0.3.10
Pillow>=10.0.0

# File Storage
minio>=7.1.0

# Search
meilisearch>=0.28.0

# HTTP Client
httpx>=0.24.0

# Data Processing
pandas>=2.0.0
openpyxl>=3.1.0
python-magic>=0.4.27

# Utilities
python-dotenv>=1.0.0
tenacity>=8.2.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.24.0
```

---

## Summary

This comprehensive plan covers building a full-featured Airtable alternative with:

1. **Flexible Schema** - JSONB-based records with typed field handlers
2. **Rich Field Types** - 20+ field types including formulas, links, rollups
3. **Multiple Views** - Grid, Kanban, Calendar, Gallery, Form, Gantt
4. **PDF Extraction** - Multi-method extraction with OCR support
5. **Formula Engine** - 50+ functions, field references, operators
6. **Automations** - Triggers, actions, webhooks
7. **Real-time Collaboration** - WebSockets, Redis PubSub
8. **REST API** - Complete CRUD with filtering, sorting, pagination
9. **File Management** - S3-compatible storage with thumbnails
10. **Search** - Full-text search across all data

Estimated development time: **24 weeks** for a full-featured MVP.

Would you like me to start implementing any specific component, or create the initial project scaffolding?
