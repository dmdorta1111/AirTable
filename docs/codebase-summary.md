# PyBase Codebase Summary

> Last updated: January 2026

## Overview

PyBase is a self-hosted Airtable alternative with CAD/PDF extraction capabilities. Built with FastAPI, SQLAlchemy, and PostgreSQL.

## Project Structure

```
src/pybase/
├── api/                     # FastAPI routes
│   ├── v1/                  # API version 1
│   │   ├── __init__.py      # Router registration
│   │   ├── auth.py          # Authentication (login, register, tokens)
│   │   ├── users.py         # User management
│   │   ├── workspaces.py    # Workspace CRUD
│   │   ├── bases.py         # Base CRUD
│   │   ├── tables.py        # Table CRUD
│   │   ├── fields.py        # Field CRUD (30+ types)
│   │   ├── records.py       # Record CRUD
│   │   ├── views.py         # View CRUD (7 view types)
│   │   ├── extraction.py    # CAD/PDF extraction endpoints
│   │   ├── realtime.py      # WebSocket & presence endpoints
│   │   ├── automations.py   # Automation CRUD & execution
│   │   └── webhooks.py      # Webhook management
│   └── deps.py              # Dependency injection (auth, db session)
│
├── core/                    # Core configuration
│   ├── config.py            # Settings (env vars, secrets)
│   ├── security.py          # JWT, password hashing, API keys
│   ├── exceptions.py        # Custom exception classes
│   └── logging.py           # Logging configuration
│
├── db/                      # Database layer
│   ├── base.py              # SQLAlchemy declarative base
│   ├── session.py           # Async session factory
│   └── migrations/          # Alembic migrations
│
├── models/                  # SQLAlchemy ORM models
│   ├── __init__.py          # Model exports
│   ├── user.py              # User, APIKey models
│   ├── workspace.py         # Workspace model
│   ├── base.py              # Base model
│   ├── table.py             # Table model
│   ├── field.py             # Field model (FieldType enum)
│   ├── record.py            # Record model (JSONB data)
│   ├── view.py              # View model (7 ViewTypes)
│   └── automation.py        # Automation, Action, Run, Webhook
│
├── schemas/                 # Pydantic schemas
│   ├── user.py              # User request/response schemas
│   ├── workspace.py         # Workspace schemas
│   ├── base.py              # Base schemas
│   ├── table.py             # Table schemas
│   ├── field.py             # Field schemas with type options
│   ├── record.py            # Record schemas
│   ├── view.py              # View schemas with type configs
│   ├── extraction.py        # CAD/PDF extraction schemas
│   ├── realtime.py          # WebSocket event schemas (40+ events)
│   └── automation.py        # Automation, action, webhook schemas
│
├── services/                # Business logic layer
│   ├── view.py              # View service (CRUD, filtering)
│   └── automation.py        # AutomationService, WebhookService
│
├── fields/                  # Field type implementations
│   ├── base.py              # BaseFieldHandler abstract class
│   ├── text.py              # Text, LongText, RichText
│   ├── number.py            # Number, Currency, Percent
│   ├── date.py              # Date, DateTime, Duration
│   ├── attachment.py        # File attachments
│   ├── linked_record.py     # Relations between tables
│   ├── formula.py           # Calculated fields
│   ├── lookup.py            # Cross-table lookups
│   ├── rollup.py            # Aggregations
│   └── engineering/         # Engineering-specific fields
│       ├── dimension.py     # Value with tolerance
│       ├── gdt.py           # GD&T symbols
│       ├── thread.py        # Thread specifications
│       └── material.py      # Material properties
│
├── extraction/              # CAD/PDF extraction
│   ├── pdf/                 # PDF processing
│   │   ├── extractor.py     # Main PDF extractor
│   │   ├── table_extractor.py
│   │   └── ocr.py           # OCR for scanned PDFs
│   ├── cad/                 # CAD file parsers
│   │   ├── dxf_parser.py    # AutoCAD DXF
│   │   ├── ifc_parser.py    # IFC/BIM
│   │   └── step_parser.py   # STEP files
│   └── werk24/              # Werk24 API integration
│
├── realtime/                # WebSocket infrastructure
│   ├── __init__.py          # Module exports
│   ├── manager.py           # ConnectionManager (pub/sub)
│   └── presence.py          # PresenceService (tracking)
│
├── formula/                 # Formula evaluation
│   ├── parser.py            # Formula parser (Lark)
│   └── evaluator.py         # Formula evaluator
│
└── main.py                  # FastAPI application entry
```

## Completed Phases

### Phase 1: Foundation ✅
- User authentication (JWT, API keys)
- Database models (User, Workspace, Base, Table, Field, Record)
- Core configuration and security

### Phase 2: Core Database Features ✅
- **30 field types** implemented:
  - Basic: Text, LongText, RichText, Number, Currency, Percent, Checkbox
  - Date/Time: Date, DateTime, Duration, CreatedTime, ModifiedTime
  - Selection: SingleSelect, MultiSelect, Status
  - Relations: LinkedRecord, Lookup, Rollup, Count
  - Media: Attachment, URL, Email, Phone
  - User: User, CreatedBy, ModifiedBy
  - Advanced: Formula, Autonumber, Barcode, Rating
  - Engineering: Dimension, GDT, Thread, SurfaceFinish, Material

### Phase 3: CAD/PDF Extraction ✅
- PDF extraction (tables, text, metadata)
- DXF/DWG parsing (layers, blocks, dimensions)
- IFC/BIM parsing (building elements, properties)
- STEP parsing (3D geometry, assemblies)
- Werk24 API integration

### Phase 4: Views ✅
- **7 view types**:
  - Grid (spreadsheet)
  - Kanban (board)
  - Calendar
  - Gallery
  - Form
  - Gantt
  - Timeline
- View filters, sorts, groups
- Personal and locked views

### Phase 5: Real-time Collaboration ✅
- WebSocket connection management
- Channel-based pub/sub
- User presence tracking
- Cell focus/blur events
- Cursor movement broadcasting
- Selection change events
- 40+ event types defined

### Phase 6: Automations & Webhooks ✅
- **11 trigger types**: record_created, record_updated, record_deleted, record_matches_conditions, field_changed, form_submitted, scheduled, at_scheduled_time, webhook_received, button_clicked
- **12 action types**: create_record, update_record, delete_record, send_email, send_slack_message, send_webhook, link_records, unlink_records, run_script, conditional, loop, delay
- Template engine with variable substitution
- Automation execution engine with run history
- Incoming/outgoing webhook support

## API Endpoints Summary

| Module | Prefix | Endpoints |
|--------|--------|-----------|
| Health | `/` | `GET /health` |
| Auth | `/auth` | login, register, refresh, logout |
| Users | `/users` | CRUD, profile, API keys |
| Workspaces | `/workspaces` | CRUD, members |
| Bases | `/bases` | CRUD, sharing |
| Tables | `/tables` | CRUD, schema |
| Fields | `/fields` | CRUD, reorder |
| Records | `/records` | CRUD, batch ops, search |
| Views | `/views` | CRUD, duplicate, reorder, data |
| Extraction | `/extraction` | PDF, DXF, IFC, STEP, Werk24 |
| Realtime | `/realtime` | WebSocket, stats, presence |
| Automations | `/automations` | CRUD, actions, triggers, runs |
| Webhooks | `/webhooks` | CRUD, incoming, outgoing, test |

## Key Dependencies

- **FastAPI** - Web framework
- **SQLAlchemy 2.0** - Async ORM
- **PostgreSQL** - Primary database (JSONB for record data)
- **Redis** - Caching, pub/sub
- **Celery** - Background tasks
- **python-jose** - JWT handling
- **passlib** - Password hashing
- **ezdxf** - DXF file processing
- **ifcopenshell** - IFC/BIM processing

## Database Schema

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────<│  Workspace  │────<│    Base     │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────┐           │
                    │    View     │<──────────┤
                    └─────────────┘           │
                                              ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Record    │────<│    Table    │
                    └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                        ┌─────────────┐
                                        │    Field    │
                                        └─────────────┘
```

## Next Phase: Frontend (React + TypeScript)

Phase 7 will add:
- Vite + React 18 + TypeScript setup
- TailwindCSS + shadcn/ui components
- React Query for API state management
- Zustand for client state
- Grid view with virtual scrolling (react-virtual)
- Kanban view
- Form view
- Real-time collaboration UI (presence indicators, cursors)
- Authentication flows
