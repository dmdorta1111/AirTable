# Codebase Structure

```
pybase/
├── src/pybase/
│   ├── api/v1/          # FastAPI route handlers
│   │   ├── auth.py      # Authentication endpoints
│   │   ├── users.py     # User management
│   │   ├── workspaces.py
│   │   ├── bases.py
│   │   ├── tables.py
│   │   ├── fields.py
│   │   ├── records.py
│   │   └── extraction.py
│   ├── core/            # Configuration, security, logging
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── db/              # SQLAlchemy base, sessions, migrations
│   │   ├── base.py
│   │   └── session.py
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic layer
│   ├── fields/          # Field type implementations
│   │   ├── base.py      # Base field handler
│   │   └── engineering/ # Engineering-specific fields
│   ├── extraction/      # CAD/PDF data extraction
│   │   ├── pdf/
│   │   ├── cad/
│   │   └── werk24/
│   ├── realtime/        # WebSocket handlers
│   ├── formula/         # Formula field parsing
│   └── main.py          # FastAPI application
├── tests/               # Test suite
├── frontend/            # React + TypeScript frontend
├── migrations/          # Alembic migrations
├── docker/              # Docker configurations
├── docs/                # Documentation
├── plans/               # Implementation plans
└── scripts/             # Utility scripts
```

## Key Files
- `src/pybase/main.py` - FastAPI app entrypoint
- `pyproject.toml` - Project config, dependencies, tool settings
- `alembic.ini` - Database migration config
- `docker-compose.yml` - Local dev services
