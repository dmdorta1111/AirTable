# PyBase

> Self-hosted Airtable alternative with CAD/PDF extraction capabilities

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a393.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

PyBase is a powerful, self-hosted database platform that combines the flexibility of spreadsheets with the power of a real database. Built for engineering teams, it includes specialized features for extracting data from CAD files (DXF, IFC, STEP) and PDFs.

### Key Features

- **30+ Field Types**: Text, number, date, attachments, linked records, formulas, and engineering-specific fields
- **Multiple Views**: Grid, Kanban, Calendar, Gallery, Form, Gantt, and Timeline views
- **CAD/PDF Extraction**: Extract tables, dimensions, and metadata from engineering drawings
- **Real-time Collaboration**: WebSocket-based live updates and presence
- **Automations**: Trigger-based workflows with webhooks and integrations
- **Self-hosted**: Full control over your data with Docker deployment

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### Installation

```bash
# Clone the repository
git clone https://github.com/pybase/pybase.git
cd pybase

# Start services with Docker Compose
docker compose up -d

# Install dependencies
pip install -e ".[all]"

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn pybase.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# Database
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase

# Redis
REDIS_URL=redis://localhost:6379/0

# Object Storage (MinIO)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=pybase

# Optional: Werk24 API for engineering drawing extraction
WERK24_API_KEY=your-werk24-api-key
```

## Project Structure

```
pybase/
├── src/pybase/
│   ├── api/                 # FastAPI routes
│   │   ├── v1/
│   │   │   ├── auth.py      # Authentication endpoints
│   │   │   ├── users.py     # User management
│   │   │   ├── workspaces.py
│   │   │   ├── bases.py
│   │   │   ├── tables.py
│   │   │   ├── fields.py
│   │   │   ├── records.py
│   │   │   └── extraction.py # CAD/PDF extraction endpoints
│   │   └── deps.py          # Dependency injection
│   ├── core/                # Core configuration
│   │   ├── config.py        # Settings management
│   │   ├── security.py      # JWT & password hashing
│   │   └── logging.py       # Logging configuration
│   ├── db/                  # Database layer
│   │   ├── base.py          # SQLAlchemy base
│   │   ├── session.py       # Database session
│   │   └── migrations/      # Alembic migrations
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py
│   │   ├── workspace.py
│   │   ├── base.py
│   │   ├── table.py
│   │   ├── field.py
│   │   └── record.py
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── fields/              # Field type implementations
│   │   ├── base.py          # Base field handler
│   │   ├── text.py
│   │   ├── number.py
│   │   ├── date.py
│   │   ├── attachment.py
│   │   ├── linked_record.py
│   │   ├── formula.py
│   │   └── engineering/     # Engineering-specific fields
│   │       ├── dimension.py
│   │       ├── gdt.py       # GD&T (Geometric Tolerancing)
│   │       ├── thread.py
│   │       └── material.py
│   ├── extraction/          # CAD/PDF extraction
│   │   ├── pdf/
│   │   │   ├── extractor.py
│   │   │   ├── table_extractor.py
│   │   │   └── ocr.py
│   │   ├── cad/
│   │   │   ├── dxf_parser.py
│   │   │   ├── ifc_parser.py
│   │   │   └── step_parser.py
│   │   └── werk24/          # Werk24 API integration
│   └── main.py              # FastAPI application
├── tests/                   # Test suite
├── docker/                  # Docker configurations
├── docs/                    # Documentation
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Documentation

- [API Reference](docs/api.md)
- [Field Types](docs/fields.md)
- [CAD/PDF Extraction](docs/extraction.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing](CONTRIBUTING.md)

## Engineering-Specific Features

### Supported CAD Formats

| Format | Extension | Library | Features |
|--------|-----------|---------|----------|
| AutoCAD | .dxf, .dwg | ezdxf | Layers, blocks, dimensions, text |
| IFC/BIM | .ifc | ifcopenshell | Building elements, properties, geometry |
| STEP | .stp, .step | cadquery | 3D geometry, assemblies, metadata |

### Engineering Field Types

- **Dimension**: Value with tolerance (e.g., `10.5 ±0.1 mm`)
- **GD&T**: Geometric dimensioning and tolerancing symbols
- **Thread**: Thread specifications (e.g., `M8x1.25`)
- **Surface Finish**: Surface roughness values (e.g., `Ra 1.6`)
- **Material**: Material specifications with properties
- **Drawing Reference**: Links to drawing files with revision tracking

## API Examples

### Create a Table

```bash
curl -X POST "http://localhost:8000/api/v1/bases/{base_id}/tables" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Parts",
    "fields": [
      {"name": "Part Number", "type": "text"},
      {"name": "Description", "type": "long_text"},
      {"name": "Dimension", "type": "dimension", "options": {"unit": "mm"}},
      {"name": "Material", "type": "material"}
    ]
  }'
```

### Extract Data from PDF

```bash
curl -X POST "http://localhost:8000/api/v1/extraction/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@drawing.pdf" \
  -F "extract_tables=true" \
  -F "extract_dimensions=true"
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=pybase --cov-report=html

# Format code
black src tests
ruff check src tests --fix

# Type checking
mypy src

# Run pre-commit hooks
pre-commit run --all-files
```

## Roadmap

- [x] Phase 1: Foundation (Auth, Database, Core Models) - **COMPLETE**
- [x] Phase 2: Core Database Features (Field Types, Records) - **COMPLETE: 30+ field types**
- [x] Phase 3: CAD/PDF Extraction - **COMPLETE: PDF, DXF, IFC, STEP parsers + Werk24 API**
- [x] Phase 4: Views - **COMPLETE: Grid, Kanban, Calendar, Gallery, Form, Gantt, Timeline**
- [x] Phase 5: Real-time Collaboration - **COMPLETE: WebSocket connections, presence, cell focus, cursor tracking**
- [x] Phase 6: Automations & Webhooks - **COMPLETE: 11 trigger types, 12 action types, execution engine, webhooks**
- [~] Phase 7: Frontend (React + TypeScript) - **IN PROGRESS: Vite, TypeScript project scaffold initialized**
- [ ] Phase 8: Search & AI Features
- [ ] Phase 9: Production Deployment

**Backend is feature-complete!** All 6 backend phases (1-6) are fully implemented with comprehensive APIs. Frontend development (Phase 7) is currently in progress.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [ezdxf](https://ezdxf.mozman.at/) - DXF file processing
- [ifcopenshell](http://ifcopenshell.org/) - IFC/BIM processing
- [Werk24](https://werk24.io/) - Engineering drawing AI extraction
