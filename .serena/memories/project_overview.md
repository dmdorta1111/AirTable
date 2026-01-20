# PyBase Project Overview

## Purpose
Self-hosted Airtable alternative with CAD/PDF extraction capabilities, built for engineering teams. Combines spreadsheet flexibility with database power.

## Tech Stack
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy (async), PostgreSQL 15+
- **Caching**: Redis 7+
- **CAD/PDF Processing**: ezdxf, ifcopenshell, cadquery, PyPDF2, pdfplumber
- **API Integration**: Werk24 for engineering drawing AI extraction
- **Real-time**: WebSocket connections for live collaboration
- **Frontend**: React + TypeScript (in progress)

## Key Features
- 30+ field types including engineering-specific (dimension, GD&T, thread, material)
- Multiple views: Grid, Kanban, Calendar, Gallery, Form, Gantt, Timeline
- CAD/PDF extraction from DXF, IFC, STEP, PDF formats
- Real-time collaboration via WebSockets
- Automations with triggers and webhooks

## Project Status
- Backend: Feature-complete (Phases 1-6 done)
- Frontend: 80% complete (Phase 7 in progress)
- Search/AI: 20% complete (Phase 8)
- Deployment: 10% complete (Phase 9)
