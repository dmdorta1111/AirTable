# Project Overview - Product Development Requirements (PDR)

## Executive Summary
PyBase is a self-hosted, high-performance database platform designed specifically for engineering and technical teams. It provides a flexible, spreadsheet-like interface backed by a robust relational database, with specialized capabilities for CAD and PDF data extraction.

## Problem Statement
Engineering teams often struggle to manage technical data across disconnected spreadsheets, CAD files, and legacy databases. There is a need for a unified platform that can handle complex data types (dimensions, tolerances, materials) and automatically extract this information from technical drawings.

## Target Users
- **Design Engineers**: Managing part libraries and specifications.
- **Manufacturing Engineers**: Tracking production data and surface finishes.
- **Project Managers**: Coordinating complex engineering projects with Gantt and Timeline views.
- **Quality Assurance**: Monitoring GD&T and inspection data.

## Product Requirements

### 1. Data Management
- Support for 30+ field types, including engineering-specific types (Dimension, GD&T, Thread).
- Real-time collaboration with multi-user presence and cell-level tracking.
- Robust relational capabilities (Linked Records, Lookups, Rollups).

### 2. Engineering Intelligence
- Automated extraction of tables, dimensions, and metadata from PDF drawings.
- Parsing of DXF (AutoCAD), IFC (BIM), and STEP (3D) files.
- Integration with Werk24 API for advanced drawing analysis.

### 3. Workflow & Automation
- Flexible view system (Grid, Kanban, Gantt, Timeline).
- Trigger-based automation engine (11 triggers, 12 actions).
- Webhook support for third-party integrations.

### 4. Technical Constraints
- **Self-hosted**: Must be deployable via Docker for data privacy.
- **Scalability**: High-performance backend using FastAPI and PostgreSQL.
- **Real-time**: Low-latency updates using WebSockets and Redis.

## Success Metrics (Technical KPIs)
- API response time < 100ms for 95% of requests.
- WebSocket message latency < 50ms.
- CAD extraction accuracy > 90% for standard technical drawings.
- Support for tables with > 100,000 records.
