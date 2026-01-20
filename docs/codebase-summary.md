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

## Codebase Metrics (as of January 2026)

| Category | LOC | Description |
|----------|-----|-------------|
| **Total Python Backend** | **~18,000** | Core logic, API, services |
| API Routes | 4,913 | 17 files in `src/pybase/api/` |
| Core Components | 9,037 | Models, schemas, services, core, db |
| Extraction Services | 4,038 | PDF/CAD parsers, Werk24 |
| Field Implementations | 5,534 | 31 field types |
| **Frontend** | **4,181** | React/TypeScript (42 files) |
| **Tests** | **4,831** | 16 test files |

## Project Status

### Backend: Feature-Complete ✅ (Phases 1-6)
The backend implementation is fully completed, covering foundation, core database features, extraction services, views, real-time collaboration, and automations.

### Frontend: In-Progress 🔄 (~80% Complete)
- **Implemented**: Vite scaffold, Auth, Base/Table management, Grid, Kanban, Form, Calendar views.
- **Pending**: Gallery, Gantt, Timeline views.

### Search & AI: Partial Implementation ⚠️ (~20% Complete)
- Search API skeleton and Meilisearch integration service exists (`src/pybase/services/search.py`).
- Background indexing and advanced AI features pending.

### Production: Early Stage ⚠️ (~10% Complete)
- Docker Compose configuration exists.
- K8s manifests, monitoring (Prometheus/Grafana), and security hardening pending.

## Current Issues & Blockers
1. **Extraction API**: Identified 40+ type errors and security/type safety issues.
2. **Search Worker**: Import errors in `workers/celery_search_worker.py`.
3. **Meilisearch**: Background indexing not yet fully implemented.
4. **Missing UI**: Gallery, Gantt, and Timeline views missing in the frontend.

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

## Roadmap Status

- **Phase 1-6**: Complete ✅
- **Phase 7 (Frontend)**: ~80% Complete 🔄
- **Phase 8 (Search & AI)**: ~20% Complete ⚠️
- **Phase 9 (Production)**: ~10% Complete ⚠️
