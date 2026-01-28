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
- **Werk24 AI Integration**: AI-powered extraction of technical drawings with intelligent recognition of dimensions, tolerances, and GD&T symbols
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

# Optional: Meilisearch for fast full-text search
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your-meilisearch-master-key  # Optional for dev, required for prod
```

> ⚠️ **IMPORTANT**: Never commit your `.env` file to version control. It contains sensitive credentials including database passwords, API keys, and secret keys. See [Security Setup](#security-setup) below for proper handling.

## Security Setup

### Environment Variable Protection

PyBase relies on environment variables for sensitive configuration. Proper handling of these variables is critical for security.

#### 1. Never Commit `.env` Files

The `.env` file contains sensitive information and should **never** be committed to version control. PyBase includes a `.gitignore` entry for `.env` files by default.

```bash
# Verify .env is in .gitignore
cat .gitignore | grep "\.env"
```

If you accidentally commit a `.env` file, consider all exposed credentials compromised and immediately:
- Change all passwords and API keys
- Rotate database credentials
- Regenerate SECRET_KEY
- Revoke and regenerate API keys (WERK24_API_KEY, S3 keys, etc.)

#### 2. Use Environment-Specific Configuration

**Development:**
```env
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-for-local-only
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase
```

**Production:**
```env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-strong-random-production-secret-key-min-32-chars
DATABASE_URL=postgresql+asyncpg://user:STRONG_PASSWORD@db-host:5432/dbname
```

Always use strong, unique values for production:
- **SECRET_KEY**: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- **Database passwords**: Use strong random passwords (minimum 16 characters)
- **API keys**: Obtain from respective services and never share

#### 3. Production Deployment Best Practices

For production deployments, use one of these secure methods:

**Option A: Environment Variables (Recommended for Docker/K8s)**
```bash
# Docker Compose
docker compose -f docker-compose.prod.yml up -d

# Kubernetes (use Secrets)
kubectl create secret generic pybase-secrets \
  --from-literal=secret-key=$(openssl rand -base64 32) \
  --from-literal=database-url="postgresql+asyncpg://..."
```

**Option B: CI/CD Environment Variables**
Store secrets in your CI/CD platform (GitHub Actions, GitLab CI, etc.) and inject at deploy time.

**Option C: Secrets Management Service**
For enterprise deployments, use dedicated secrets management:
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

#### 4. Database Security

**Database Connection Security:**
- Use strong passwords for database users
- Restrict database access to specific IP addresses
- Enable SSL for database connections in production
- Use separate database users for different environments

**Example Production DATABASE_URL with SSL:**
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require
```

#### 5. Object Storage Security

When using S3-compatible storage (MinIO, AWS S3, etc.):
- Create dedicated IAM users with least-privilege access
- Rotate access keys regularly
- Enable bucket encryption
- Use lifecycle policies for sensitive data

#### 6. Regular Security Audits

Perform regular security reviews:
- Rotate SECRET_KEY and credentials periodically
- Review access logs for unauthorized attempts
- Keep dependencies updated: `pip install --upgrade -e ".[all]"`
- Monitor for security advisories in dependencies

#### 7. Example `.env.example` Template

PyBase provides a `.env.example` file as a safe template. Copy it to create your `.env`:

```bash
cp .env.example .env
# Edit .env with your actual values (never commit this file)
```

The `.env.example` file contains placeholder values only and is safe to commit.

### Verification Checklist

Before deploying to production, verify:
- [ ] `.env` is in `.gitignore`
- [ ] `.env` file is not tracked by git (`git status`)
- [ ] All passwords are strong (16+ characters, mixed case, numbers, symbols)
- [ ] `SECRET_KEY` is unique and not shared with other projects
- [ ] Database connections use SSL in production
- [ ] DEBUG mode is disabled (`DEBUG=false`)
- [ ] API keys are from official sources
- [ ] Backup and restore procedures are tested

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

### General
- [Project Overview (PDR)](docs/project-overview-pdr.md)
- [System Architecture](docs/system-architecture.md)
- [Codebase Summary](docs/codebase-summary.md)
- [Code Standards](docs/code-standards.md)
- [Project Roadmap](docs/project-roadmap.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Design Guidelines](docs/design-guidelines.md)

### Frontend
- [Frontend Architecture](docs/frontend-architecture.md) - Tech stack, folder structure, and architecture decisions
- [Component Patterns](docs/frontend-component-patterns.md) - UI components, field editors, views, and composition patterns
- [State Management](docs/frontend-state-management.md) - TanStack Query, Zustand, and API integration patterns

### API & Features
- [API Reference](docs/api.md)
- [Field Types](docs/fields.md)
- [CAD/PDF Extraction](docs/extraction.md)


## Engineering-Specific Features

### Supported CAD Formats

| Format | Extension | Library | Features |
|--------|-----------|---------|----------|
| AutoCAD | .dxf, .dwg | ezdxf | Layers, blocks, dimensions, text |
| IFC/BIM | .ifc | ifcopenshell | Building elements, properties, geometry |
| STEP | .stp, .step | cadquery | 3D geometry, assemblies, metadata |

### Werk24 AI Extraction

PyBase integrates with [Werk24](https://werk24.io/), an AI-powered service for automated extraction of technical data from engineering drawings. This feature enables intelligent recognition and extraction of:

- **Dimensions & Tolerances**: Automatically extract linear, radial, and angular dimensions with their associated tolerances
- **GD&T Symbols**: Recognize and parse geometric dimensioning and tolerancing callouts
- **Part Information**: Extract title blocks, part numbers, material specifications, and revision information
- **Manufacturing Data**: Identify surface finish requirements, thread specifications, and heat treatment notes

The Werk24 integration requires an API key (optional). When configured, PyBase can automatically process uploaded PDF drawings and populate database fields with extracted technical data, significantly reducing manual data entry for engineering teams.

### Meilisearch Full-Text Search

PyBase integrates with [Meilisearch](https://www.meilisearch.com/), an open-source search engine that provides lightning-fast, typo-tolerant full-text search across all records and fields.

**Key Features:**
- **Sub-100ms Search**: Fast search responses even with 100K+ records
- **Typo Tolerance**: Finds results even with misspellings (e.g., "dimenson" finds "dimension")
- **Faceted Filtering**: Filter results by any field type (string, number, boolean, date, array)
- **Result Highlighting**: Highlights matching terms in search results
- **Real-time Indexing**: Background indexing keeps search up-to-date without blocking writes
- **Relevance Ranking**: Intelligent ranking based on word frequency, proximity, and exactness

**Getting Started with Meilisearch:**

```bash
# Start Meilisearch with Docker Compose
docker compose --profile search up -d meilisearch

# Verify Meilisearch is running
curl http://localhost:7700/health

# Set environment variables
export MEILISEARCH_URL=http://localhost:7700
# For production, also set MEILISEARCH_API_KEY
```

Once configured, search is automatically enabled for all bases. Records are indexed in the background as they are created, updated, or deleted. For detailed setup instructions, see [Meilisearch Setup Guide](docs/meilisearch-setup.md).

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

## Monitoring

PyBase includes a comprehensive monitoring stack with Prometheus and Grafana for production deployments. The monitoring system provides real-time insights into application performance, database health, and system metrics.

### Components

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and alerting dashboards
- **Node Exporter**: System-level metrics (CPU, memory, disk)
- **Postgres Exporter**: Database performance metrics
- **Redis Exporter**: Redis cache metrics

### Quick Start with Monitoring

```bash
# Start all services including monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Access Grafana dashboard
open http://localhost:3000
# Default credentials: admin / admin (change on first login)

# Access Prometheus
open http://localhost:9090
```

### Available Dashboards

Grafana comes pre-configured with several dashboards:

- **PyBase Application Overview**: Request rate, error rate, latency histograms
- **Database Performance**: Connection pool, query performance, transaction stats
- **Redis Cache**: Hit rate, memory usage, key statistics
- **System Resources**: CPU, memory, disk I/O, network traffic
- **FastAPI Metrics**: Endpoint performance, active requests, response times

### Metrics Collected

PyBase exposes the following metrics:

- **HTTP Metrics**: Request count, latency, error rate by endpoint and method
- **Database Metrics**: Query execution time, connection pool usage, transaction rate
- **Cache Metrics**: Redis hit/miss ratio, operation timing, key count
- **Business Metrics**: Active users, record operations, extraction jobs
- **System Metrics**: CPU, memory, disk, network usage

### Configuration

Monitoring is configured via environment variables:

```env
# Enable Prometheus metrics endpoint
ENABLE_METRICS=true
METRICS_PORT=9090

# Prometheus retention (default: 15 days)
PROMETHEUS_RETENTION=15d

# Grafana credentials
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change-me-in-production

# Alert configuration
ENABLE_ALERTS=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Alerting

The monitoring stack includes pre-configured alerts for:

- High error rate (> 5% over 5 minutes)
- Elevated latency (p95 > 1 second)
- Database connection pool exhaustion
- Redis cache miss rate > 50%
- High memory usage (> 85%)
- Disk space low (< 15% remaining)

Alerts can be sent to Slack, email, or PagerDuty via Grafana notification channels.

### Production Deployment

For production, consider:

1. **Persistent Storage**: Use Docker volumes for Prometheus and Grafana data
2. **Retention**: Adjust Prometheus retention based on storage capacity
3. **Security**: Change default Grafana credentials and enable authentication
4. **Backups**: Regularly backup Grafana dashboards and Prometheus data
5. **High Availability**: Run Prometheus with remote storage andThanos for long-term retention

Example production deployment:

```bash
# Deploy monitoring stack with persistent storage
docker compose -f docker-compose.monitoring.yml \
  -f docker-compose.monitoring.prod.yml up -d
```

### Custom Metrics

To add custom metrics in your code:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter(
    'pybase_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'pybase_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

active_users = Gauge(
    'pybase_active_users',
    'Active users',
    ['workspace_id']
)

# Use in your endpoints
@app.get("/api/v1/records")
async def get_records():
    with request_duration.labels('GET', '/records').time():
        # Your logic here
        request_count.labels('GET', '/records', '200').inc()
        return records
```

## Roadmap

- [x] Phase 1: Foundation (Auth, Database, Core Models) - **COMPLETE**
- [x] Phase 2: Core Database Features (Field Types, Records) - **COMPLETE: 30+ field types**
- [x] Phase 3: CAD/PDF Extraction - **COMPLETE: PDF, DXF, IFC, STEP parsers + Werk24 API**
- [x] Phase 4: Views - **COMPLETE: Grid, Kanban, Calendar, Gallery, Form, Gantt, Timeline**
- [x] Phase 5: Real-time Collaboration - **COMPLETE: WebSocket connections, presence, cell focus, cursor tracking**
- [x] Phase 6: Automations & Webhooks - **COMPLETE: 11 trigger types, 12 action types, execution engine, webhooks**
- [ ] Phase 7: Frontend (React + TypeScript) - **IN PROGRESS: 80% complete (Auth, Base, Table, Grid/Kanban/Form/Calendar views done)**
- [x] Phase 8: Search & AI Features - **COMPLETE: Meilisearch integration with typo-tolerant full-text search, faceted filtering, instant search UI**
- [ ] Phase 9: Production Deployment - **IN PROGRESS: 10% complete (Docker Compose exists, K8s/Monitoring pending)**


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
