# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PyBase** is a self-hosted Airtable alternative with specialized CAD/PDF extraction capabilities, built for engineering teams. It combines spreadsheet flexibility with database power, featuring 30+ field types, multiple views, real-time collaboration, and engineering-specific data extraction.

**Tech Stack:**
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy, PostgreSQL 15+
- **Database**: PostgreSQL with async support
- **Caching**: Redis 7+
- **CAD/PDF Processing**: ezdxf, ifcopenshell, cadquery, PyPDF2
- **API Integration**: Werk24 for engineering drawing AI extraction
- **Real-time**: WebSocket connections for live collaboration
- **Frontend**: React + TypeScript (in progress)

## Role & Responsibilities

Your role is to analyze user requirements, delegate tasks to appropriate sub-agents, and ensure cohesive delivery of features that meet specifications and architectural standards for this engineering-focused database platform.

## Workflows

- Primary workflow: `./.claude/rules/primary-workflow.md`
- Development rules: `./.claude/rules/development-rules.md`
- Orchestration protocols: `./.claude/rules/orchestration-protocol.md`
- Documentation management: `./.claude/rules/documentation-management.md`
- And other workflows: `./.claude/rules/*`

**IMPORTANT:** Analyze the skills catalog and activate the skills that are needed for the task during the process.
**IMPORTANT:** You must follow strictly the development rules in `./.claude/rules/development-rules.md` file.
**IMPORTANT:** Before you plan or proceed any implementation, always read the `./README.md` file first to get context.
**IMPORTANT:** Sacrifice grammar for the sake of concision when writing reports.
**IMPORTANT:** In reports, list any unresolved questions at the end, if any.

## Project Architecture

### Core Structure
```
src/pybase/
├── api/v1/              # FastAPI route handlers
├── core/                # Configuration, security, logging
├── db/                  # SQLAlchemy base, sessions, migrations
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── services/            # Business logic layer
├── fields/              # Custom field type implementations
│   ├── base.py         # Base field handler
│   ├── text.py         # Text field types
│   ├── engineering/    # Engineering-specific fields
│   │   ├── dimension.py
│   │   ├── gdt.py      # GD&T symbols
│   │   ├── thread.py
│   │   └── material.py
├── extraction/          # CAD/PDF data extraction
│   ├── pdf/            # PDF processing
│   ├── cad/            # CAD file parsers
│   └── werk24/         # AI extraction integration
└── main.py             # FastAPI application
```

### Key Components

1. **Field System**: Modular field types with base handler pattern
2. **Extraction Engine**: Multi-format CAD/PDF data extraction
3. **Real-time Layer**: WebSocket-based collaboration
4. **View System**: Grid, Kanban, Calendar, Gallery, Form, Gantt, Timeline
5. **Automation Engine**: Trigger-based workflows with webhooks

## Development Guidelines

### Code Standards
- **Python**: Black formatting, Ruff linting, MyPy type checking
- **API Design**: RESTful endpoints with consistent naming
- **Database**: Async SQLAlchemy with proper migrations
- **Error Handling**: Structured error responses with proper HTTP codes
- **Documentation**: Docstrings for all public functions/classes

### Database Patterns
- **Models**: SQLAlchemy declarative models in `src/pybase/models/`
- **Schemas**: Pydantic schemas in `src/pybase/schemas/`
- **Migrations**: Alembic migrations in `alembic/versions/`
- **Sessions**: Async session management with proper cleanup

### Field Type Development
```python
# Field types follow base pattern
from src.pybase.fields.base import BaseFieldHandler

class CustomFieldHandler(BaseFieldHandler):
    field_type = "custom_field"
    
    async def validate(self, value: Any) -> Any:
        # Validation logic
        pass
    
    async def serialize(self, value: Any) -> Any:
        # Database serialization
        pass
    
    async def deserialize(self, value: Any) -> Any:
        # Database deserialization
        pass
```

### API Endpoint Pattern
```python
# All endpoints follow FastAPI best practices
@router.post("/tables/{table_id}/records")
async def create_record(
    table_id: UUID,
    record_data: RecordCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RecordSchema:
    # Business logic with proper error handling
    pass
```

## Testing Strategy

- **Unit Tests**: pytest for business logic
- **Integration Tests**: API endpoint testing with TestClient
- **Database Tests**: TestDatabase for model testing
- **Extraction Tests**: File-based tests for CAD/PDF processing

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=pybase --cov-report=html

# Specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/extraction/
```

## Extraction System

### Supported Formats
- **PDF**: Table extraction, text parsing, OCR integration
- **DXF**: Layer parsing, blocks, dimensions, text extraction
- **IFC**: Building elements, properties, geometry metadata
- **STEP**: 3D geometry, assemblies, manufacturing data

### Usage Pattern
```python
from src.pybase.extraction.pdf.extractor import PDFExtractor
from src.pybase.extraction.cad.dxf_parser import DXFParser

# PDF extraction
extractor = PDFExtractor()
tables = await extractor.extract_tables(file_path)

# CAD parsing
parser = DXFParser()
entities = await parser.parse_layers(file_path)
```

## Real-time Features

### WebSocket Integration
- **Connection Management**: WebSocket connections for live updates
- **Presence Tracking**: User cursor and cell focus tracking
- **Live Updates**: Real-time record and field updates
- **Conflict Resolution**: Operational transform for concurrent edits

### Usage Pattern
```python
# WebSocket endpoint for real-time updates
@router.websocket("/ws/table/{table_id}")
async def websocket_endpoint(websocket: WebSocket, table_id: UUID):
    await manager.connect(websocket, table_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle real-time updates
    except WebSocketDisconnect:
        manager.disconnect(websocket, table_id)
```

## Hook Response Protocol

### Privacy Block Hook (`@@PRIVACY_PROMPT@@`)

When a tool call is blocked by the privacy-block hook, the output contains a JSON marker between `@@PRIVACY_PROMPT_START@@` and `@@PRIVACY_PROMPT_END@@`. **You MUST use the `AskUserQuestion` tool** to get proper user approval.

**Required Flow:**

1. Parse the JSON from the hook output
2. Use `AskUserQuestion` with the question data from the JSON
3. Based on user's selection:
   - **"Yes, approve access"** → Use `bash cat "filepath"` to read the file (bash is auto-approved)
   - **"No, skip this file"** → Continue without accessing the file

**Example AskUserQuestion call:**
```json
{
  "questions": [{
    "question": "I need to read \".env\" which may contain sensitive data. Do you approve?",
    "header": "File Access",
    "options": [
      { "label": "Yes, approve access", "description": "Allow reading .env this time" },
      { "label": "No, skip this file", "description": "Continue without accessing this file" }
    ],
    "multiSelect": false
  }]
}
```

**IMPORTANT:** Always ask the user via `AskUserQuestion` first. Never try to work around the privacy block without explicit user approval.

## Python Scripts (Skills)

When running Python scripts from `.claude/skills/`, use the venv Python interpreter:
- **Linux/macOS:** `.claude/skills/.venv/bin/python3 scripts/xxx.py`
- **Windows:** `.claude\skills\.venv\Scripts\python.exe scripts\xxx.py`

This ensures packages installed by `install.sh` (google-genai, pypdf, etc.) are available.

**IMPORTANT:** When scripts of skills failed, don't stop, try to fix them directly.

## Environment & Dependencies

### Core Dependencies
- **FastAPI**: Web framework with async support
- **SQLAlchemy**: ORM with async driver (asyncpg)
- **Alembic**: Database migrations
- **Pydantic**: Data validation and serialization
- **Redis**: Caching and session storage
- **WebSocket**: Real-time communication

### Extraction Dependencies
- **PyPDF2/pypdf**: PDF processing
- **ezdxf**: AutoCAD DXF file processing
- **ifcopenshell**: IFC/BIM file processing
- **cadquery**: STEP file processing
- **Werk24 API**: AI-powered drawing extraction (optional)

### Installation Commands
```bash
# Install with all dependencies
pip install -e ".[all]"

# Development installation
pip install -e ".[dev]"

# Testing dependencies
pip install -e ".[test]"
```

## [IMPORTANT] Consider Modularization
- If a code file exceeds 200 lines of code, consider modularizing it
- Check existing modules before creating new
- Analyze logical separation boundaries (functions, classes, concerns)
- Use kebab-case naming with long descriptive names, it's fine if the file name is long because this ensures file names are self-documenting for LLM tools (Grep, Glob, Search)
- Write descriptive code comments
- After modularization, continue with main task
- When not to modularize: Markdown files, plain text files, bash scripts, configuration files, environment variables files, etc.

## Documentation Management

We keep all important docs in `./docs` folder and keep updating them, structure like below:

```
./docs
├── project-overview-pdr.md
├── code-standards.md
├── codebase-summary.md
├── design-guidelines.md
├── deployment-guide.md
├── system-architecture.md
└── project-roadmap.md
```

## Common Development Tasks

### Database Changes
1. Create migration: `alembic revision --autogenerate -m "description"`
2. Review migration file
3. Apply migration: `alembic upgrade head`
4. Test with `pytest tests/test_migrations.py`

### Adding Field Types
1. Create handler in `src/pybase/fields/`
2. Add to field registry
3. Create validation and serialization logic
4. Add tests in `tests/fields/`
5. Update API documentation

### Adding Extraction Formats
1. Create parser in `src/pybase/extraction/`
2. Implement extraction interface
3. Add format-specific logic
4. Create integration tests
5. Update documentation

**IMPORTANT:** *MUST READ* and *MUST COMPLY* all *INSTRUCTIONS* in project `./CLAUDE.md`, especially *WORKFLOWS* section is *CRITICALLY IMPORTANT*, this rule is *MANDATORY. NON-NEGOTIABLE. NO EXCEPTIONS. MUST REMEMBER AT ALL TIMES!!!*