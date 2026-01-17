# Phase 4: Views & Data Presentation
## PyBase Master Plan - Weeks 19-23

**Duration:** 5 Weeks  
**Status:** ❌ NOT STARTED (January 2026)  
**Team Focus:** Backend Lead + Frontend Engineer  
**Dependencies:** Phase 3 Complete (Extraction System)

---

## 📋 Phase Status Overview

**Implementation Status:** ❌ Planned  
**Dependencies:** ❌ Phase 3 not started

---

## Phase Objectives

1. Implement complete view system with 7 view types
2. Build filtering, sorting, and grouping engine
3. Create view configuration management
4. Implement view-specific APIs
5. Build data export functionality

---

## View Types

| View Type | Description | Priority |
|-----------|-------------|----------|
| Grid | Spreadsheet-like table view | Critical |
| Kanban | Card-based board with columns | Critical |
| Calendar | Date-based event display | High |
| Gallery | Card grid with images | High |
| Form | Public data collection | Critical |
| Gantt | Timeline/project planning | Medium |
| List | Simplified record list | Medium |

---

## Week-by-Week Breakdown

### Week 19: View Engine Core

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 4.19.1 | Create ViewEngine base class | Critical | 4h | Phase 3 |
| 4.19.2 | Implement filter builder | Critical | 6h | 4.19.1 |
| 4.19.3 | Implement sort builder | Critical | 4h | 4.19.1 |
| 4.19.4 | Implement grouping engine | High | 6h | 4.19.1 |
| 4.19.5 | Create view configuration schemas | Critical | 4h | 4.19.1 |
| 4.19.6 | Build JSONB query optimization | High | 6h | 4.19.2 |
| 4.19.7 | Create view CRUD service | Critical | 4h | 4.19.5 |
| 4.19.8 | Build view API endpoints | Critical | 4h | 4.19.7 |
| 4.19.9 | Write view engine tests | Critical | 4h | 4.19.* |

#### Filter System

```python
class FilterOperator(str, Enum):
    # Text
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    
    # Number
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    BETWEEN = "between"
    
    # Date
    IS_TODAY = "is_today"
    IS_BEFORE = "is_before"
    IS_AFTER = "is_after"
    IS_WITHIN = "is_within"
    IS_PAST = "is_past"
    IS_FUTURE = "is_future"
    
    # Select
    IS_ANY_OF = "is_any_of"
    IS_NONE_OF = "is_none_of"


class FilterGroup(BaseModel):
    conjunction: str = "and"  # and, or
    conditions: List[FilterCondition] = []
    groups: List["FilterGroup"] = []
```

---

### Week 20: Grid & Kanban Views

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 4.20.1 | Implement GridView configuration | Critical | 4h | 4.19.* |
| 4.20.2 | Build grid data serialization | Critical | 4h | 4.20.1 |
| 4.20.3 | Implement column resizing/reordering | High | 4h | 4.20.1 |
| 4.20.4 | Build row height settings | Medium | 2h | 4.20.1 |
| 4.20.5 | Implement frozen columns | Medium | 3h | 4.20.1 |
| 4.20.6 | Create KanbanView configuration | Critical | 4h | 4.19.* |
| 4.20.7 | Implement kanban column aggregation | High | 4h | 4.20.6 |
| 4.20.8 | Build kanban card configuration | High | 4h | 4.20.6 |
| 4.20.9 | Implement drag-drop record moving | High | 6h | 4.20.6 |
| 4.20.10 | Write Grid/Kanban view tests | Critical | 4h | 4.20.* |

---

### Week 21: Calendar & Gallery Views

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 4.21.1 | Create CalendarView configuration | High | 4h | 4.19.* |
| 4.21.2 | Implement date range queries | High | 4h | 4.21.1 |
| 4.21.3 | Build calendar event serialization | High | 4h | 4.21.1 |
| 4.21.4 | Support date range events | Medium | 4h | 4.21.1 |
| 4.21.5 | Create GalleryView configuration | High | 4h | 4.19.* |
| 4.21.6 | Implement cover image selection | High | 3h | 4.21.5 |
| 4.21.7 | Build gallery card fields | High | 3h | 4.21.5 |
| 4.21.8 | Implement gallery layout options | Medium | 3h | 4.21.5 |
| 4.21.9 | Write Calendar/Gallery tests | High | 4h | 4.21.* |

---

### Week 22: Form & Gantt Views

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 4.22.1 | Create FormView configuration | Critical | 4h | 4.19.* |
| 4.22.2 | Implement form field visibility | Critical | 3h | 4.22.1 |
| 4.22.3 | Build form field requirements | Critical | 3h | 4.22.1 |
| 4.22.4 | Create public form submission API | Critical | 4h | 4.22.1 |
| 4.22.5 | Implement form submission notifications | High | 3h | 4.22.4 |
| 4.22.6 | Build form redirect/thank you page | Medium | 2h | 4.22.4 |
| 4.22.7 | Create GanttView configuration | Medium | 4h | 4.19.* |
| 4.22.8 | Implement timeline calculations | Medium | 6h | 4.22.7 |
| 4.22.9 | Build dependency relationships | Medium | 4h | 4.22.7 |
| 4.22.10 | Write Form/Gantt view tests | High | 4h | 4.22.* |

---

### Week 23: Export & Integration

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 4.23.1 | Build CSV export | Critical | 4h | 4.19.* |
| 4.23.2 | Build Excel export | High | 4h | 4.23.1 |
| 4.23.3 | Build JSON export | High | 2h | 4.23.1 |
| 4.23.4 | Implement view-based export | High | 3h | 4.23.* |
| 4.23.5 | Build import from CSV | Critical | 6h | Phase 2 |
| 4.23.6 | Build import from Excel | High | 6h | 4.23.5 |
| 4.23.7 | End-to-end view testing | Critical | 6h | 4.19-22.* |
| 4.23.8 | Performance optimization | High | 4h | 4.23.7 |
| 4.23.9 | API documentation | Medium | 3h | 4.23.* |

---

## View Configuration Schema

```python
class ViewConfig(BaseModel):
    """Complete view configuration"""
    
    # Common
    filters: Optional[FilterGroup] = None
    sorts: List[SortConfig] = []
    hidden_fields: List[UUID] = []
    field_order: List[UUID] = []
    
    # Grid
    field_widths: Dict[str, int] = {}
    row_height: str = "medium"
    frozen_fields: List[UUID] = []
    
    # Kanban
    kanban_field_id: Optional[UUID] = None
    kanban_hide_empty: bool = False
    kanban_card_cover_field: Optional[UUID] = None
    kanban_card_fields: List[UUID] = []
    
    # Calendar
    calendar_date_field: Optional[UUID] = None
    calendar_end_date_field: Optional[UUID] = None
    calendar_label_field: Optional[UUID] = None
    
    # Gallery
    gallery_cover_field: Optional[UUID] = None
    gallery_cover_fit: str = "cover"
    gallery_card_fields: List[UUID] = []
    
    # Form
    form_title: Optional[str] = None
    form_description: Optional[str] = None
    form_fields: List[FormFieldConfig] = []
    form_redirect_url: Optional[str] = None
    
    # Gantt
    gantt_start_field: Optional[UUID] = None
    gantt_end_field: Optional[UUID] = None
    gantt_dependency_field: Optional[UUID] = None
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tables/{id}/views` | GET | List table views |
| `/api/v1/tables/{id}/views` | POST | Create view |
| `/api/v1/views/{id}` | GET | Get view config |
| `/api/v1/views/{id}` | PATCH | Update view |
| `/api/v1/views/{id}` | DELETE | Delete view |
| `/api/v1/views/{id}/records` | GET | Get records for view |
| `/api/v1/views/{id}/export` | GET | Export view data |
| `/api/v1/forms/{view_id}` | GET | Get public form |
| `/api/v1/forms/{view_id}/submit` | POST | Submit form |

---

## Phase 4 Exit Criteria

1. [ ] All 7 view types implemented
2. [ ] Filter/sort/group working correctly
3. [ ] Export to CSV/Excel/JSON
4. [ ] Import from CSV/Excel
5. [ ] Public form submissions working
6. [ ] Performance: < 200ms for 1000 records
7. [ ] Test coverage > 80%

---

*Previous: [Phase 3: CAD/PDF Extraction](master-plan-phase-3-extraction.md)*  
*Next: [Phase 5: Real-time & Collaboration](master-plan-phase-5-collaboration.md)*
