# PyBase Troubleshooting Guide

> Common issues and solutions for self-hosting PyBase

## Overview

This guide covers common issues encountered when installing, configuring, and running PyBase. For each issue, we provide step-by-step solutions and verification steps.

**Related Documentation:**
- [Deployment Guide](deployment-guide.md) - Production deployment
- [Frontend Setup Guide](setup/frontend-setup-guide.md) - React/TypeScript frontend
- [README](../README.md) - Quick start and installation

---

## Installation Issues

### 1. Python Version Mismatch

**Symptoms:**
- `SyntaxError` when importing PyBase modules
- `ModuleNotFoundError` for type hints
- Errors about `|` operator in type annotations

**Cause:**
PyBase requires Python 3.11+ for modern type hint syntax (`str | None`, `list[str]`, etc.).

**Solution:**
```bash
# Check your Python version
python --version
# or
python3 --version

# Expected: Python 3.11.x or higher
```

If you have an older version:
```bash
# Install Python 3.11+ using pyenv (recommended)
pyenv install 3.11.7
pyenv local 3.11.7

# Or install from official source
# - macOS: brew install python@3.11
# - Ubuntu: sudo apt install python3.11 python3.11-venv
# - Windows: Download from python.org
```

**Verification:**
```bash
python --version
# Should output: Python 3.11.x or 3.12.x
```

---

### 2. CAD Library Installation Failures

**Symptoms:**
- `pip install` fails for `ifcopenshell` or `cadquery`
- Build errors during `ezdxf` installation
- Missing system dependencies for CAD libraries

**Cause:**
CAD libraries require system-level dependencies (build tools, geometry libraries).

**Solution:**

#### Linux (Ubuntu/Debian)
```bash
# Install build essentials and geometry libraries
sudo apt update
sudo apt install -y \
  build-essential \
  python3-dev \
  libgeos-dev \
  libspatialindex-dev \
  liboce-foundation-dev \
  liboce-modeling-dev

# Then install PyBase
pip install -e ".[all]"
```

#### macOS
```bash
# Install dependencies via Homebrew
brew install geos spatialindex opencascade

# Then install PyBase
pip install -e ".[all]"
```

#### Windows
```bash
# Install Visual C++ Build Tools from:
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Install PyBase with pre-built wheels
pip install -e ".[all]" --prefer-binary
```

**Verification:**
```bash
python -c "import ezdxf; import ifcopenshell; print('CAD libraries OK')"
```

---

### 3. Tesseract OCR Not Found

**Symptoms:**
- PDF extraction fails with OCR-related errors
- `TesseractNotFoundError` exceptions
- Environment variable `TESSERACT_CMD` not set

**Cause:**
Tesseract OCR is an optional system dependency for extracting text from scanned PDFs.

**Solution:**

#### Linux
```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-eng

# Verify installation
which tesseract
# Output: /usr/bin/tesseract
```

#### macOS
```bash
brew install tesseract

# Verify installation
which tesseract
# Output: /usr/local/bin/tesseract or /opt/homebrew/bin/tesseract
```

#### Windows
```bash
# Download installer from:
# https://github.com/UB-Mannheim/tesseract/wiki

# After installation, add to .env:
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**Update `.env`:**
```env
# Linux/macOS
TESSERACT_CMD=/usr/bin/tesseract

# Windows
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**Verification:**
```bash
tesseract --version
# Should output: tesseract 5.x.x
```

---

## Database Connection Issues

### 1. PostgreSQL Connection Refused

**Symptoms:**
- `sqlalchemy.exc.OperationalError: could not connect to server`
- `Connection refused` or `connection timeout`
- Application fails to start with database errors

**Cause:**
PostgreSQL server not running or incorrect connection string in `.env`.

**Solution:**

#### Using Docker Compose (Recommended for Development)
```bash
# Start PostgreSQL container
docker compose up -d postgres

# Verify it's running
docker compose ps
# Should show 'postgres' with state 'Up'

# Check logs if issues persist
docker compose logs postgres
```

#### Using Local PostgreSQL Installation
```bash
# Check if PostgreSQL is running
# Linux
sudo systemctl status postgresql

# macOS
brew services list | grep postgresql

# Start if not running
# Linux
sudo systemctl start postgresql

# macOS
brew services start postgresql@15
```

**Verify Connection String in `.env`:**
```env
# Format: postgresql+asyncpg://username:password@host:port/database
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase
```

**Test Connection:**
```bash
# Install psql client if needed
# Linux: sudo apt install postgresql-client
# macOS: brew install postgresql

# Test connection (replace with your credentials)
psql -h localhost -U pybase -d pybase
# If successful, you'll see: pybase=#
```

**Verification:**
```bash
# Run migrations to verify database works
alembic upgrade head
# Should complete without errors
```

---

### 2. asyncpg Driver Installation Failed

**Symptoms:**
- `ImportError: cannot import name 'asyncpg'`
- `ModuleNotFoundError: No module named 'asyncpg'`
- Database operations fail with driver errors

**Cause:**
The async PostgreSQL driver `asyncpg` is not installed or failed to build.

**Solution:**
```bash
# Install asyncpg with build dependencies
# Linux
sudo apt install -y python3-dev libpq-dev
pip install asyncpg

# macOS
brew install postgresql
pip install asyncpg

# Windows (install Visual C++ Build Tools first)
pip install asyncpg
```

**Alternative - Use psycopg (async):**
If `asyncpg` continues to fail, you can switch to `psycopg`:
```bash
pip install "psycopg[binary,pool]"
```

Update `.env`:
```env
# Change from asyncpg to psycopg
DATABASE_URL=postgresql+psycopg://pybase:pybase@localhost:5432/pybase
```

**Verification:**
```bash
python -c "import asyncpg; print('asyncpg OK')"
```

---

### 3. Database Migration Errors

**Symptoms:**
- `alembic upgrade head` fails
- `sqlalchemy.exc.ProgrammingError: relation does not exist`
- Duplicate table or column errors

**Cause:**
Database schema out of sync with migrations or corrupted migration history.

**Solution:**

#### Check Migration Status
```bash
# Show current migration version
alembic current

# Show migration history
alembic history --verbose
```

#### Reset Database (Development Only - Destroys Data!)
```bash
# Drop all tables
alembic downgrade base

# Re-run all migrations
alembic upgrade head
```

#### Fresh Database Setup
```bash
# Using Docker Compose
docker compose down -v  # Destroys volumes!
docker compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 5

# Run migrations
alembic upgrade head

# Create initial user (optional)
python -m pybase.scripts.create_admin_user
```

**Verification:**
```bash
# List all tables in database
psql -h localhost -U pybase -d pybase -c "\dt"
# Should show: users, workspaces, bases, tables, fields, records, views, etc.
```

---

## Redis Connection Issues

### 1. Redis Connection Failed

**Symptoms:**
- `redis.exceptions.ConnectionError: Error connecting to Redis`
- Session/cache operations fail
- Real-time features not working

**Cause:**
Redis server not running or incorrect connection URL.

**Solution:**

#### Using Docker Compose
```bash
# Start Redis container
docker compose up -d redis

# Verify it's running
docker compose ps redis

# Test connection
docker compose exec redis redis-cli ping
# Should output: PONG
```

#### Using Local Redis Installation
```bash
# Check if Redis is running
# Linux
sudo systemctl status redis

# macOS
brew services list | grep redis

# Start if not running
# Linux
sudo systemctl start redis

# macOS
brew services start redis
```

**Verify `.env` Configuration:**
```env
# Default (no password)
REDIS_URL=redis://localhost:6379/0

# With password
REDIS_URL=redis://:your_password@localhost:6379/0

# Remote Redis
REDIS_URL=redis://user:password@redis.example.com:6379/0
```

**Test Connection:**
```bash
# Install redis-cli if needed
# Linux: sudo apt install redis-tools
# macOS: brew install redis

redis-cli -h localhost -p 6379 ping
# Should output: PONG
```

**Verification:**
```bash
# Test Redis from Python
python -c "
import redis
r = redis.from_url('redis://localhost:6379/0')
r.ping()
print('Redis OK')
"
```

---

## Object Storage (S3/MinIO) Issues

### 1. MinIO Connection Failed

**Symptoms:**
- File upload returns 500 error
- `botocore.exceptions.EndpointConnectionError`
- Attachment field uploads fail

**Cause:**
MinIO container not running or incorrect S3 configuration.

**Solution:**

#### Using Docker Compose
```bash
# Start MinIO container
docker compose up -d minio

# Access MinIO console
# Open browser: http://localhost:9001
# Login: minioadmin / minioadmin

# Create bucket 'pybase' if not exists
# Or via CLI:
docker compose exec minio mc mb local/pybase
```

**Verify `.env` Configuration:**
```env
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=pybase
S3_REGION=us-east-1
```

**Test Connection:**
```bash
# Install boto3 if needed
pip install boto3

# Test S3 connection
python -c "
import boto3
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)
print(s3.list_buckets())
print('MinIO OK')
"
```

**Verification:**
```bash
# Upload test file via API
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"
# Should return file URL
```

---

## Application Startup Issues

### 1. SECRET_KEY Not Set

**Symptoms:**
- Application fails to start
- `ValueError: SECRET_KEY must be set`
- JWT token generation fails

**Cause:**
`SECRET_KEY` environment variable is required but not set.

**Solution:**
```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Output: xJ8v9K... (64 characters)

# Add to .env file
echo "SECRET_KEY=<generated_key>" >> .env
```

**Update `.env`:**
```env
SECRET_KEY=xJ8v9K2pL5qM3nN7rR4tT6yY8uU0iI1oO3aA5sS7dD9fF1gG3hH5jJ7kK9lL
```

**Security Note:**
- Use a different key for each environment (dev/staging/production)
- Never commit `.env` files to version control
- Rotate keys periodically in production

**Verification:**
```bash
# Start application
uvicorn pybase.main:app --reload
# Should start without SECRET_KEY errors
```

---

### 2. Import Errors on Startup

**Symptoms:**
- `ModuleNotFoundError: No module named 'pybase'`
- `ImportError: cannot import name 'X'`
- Application fails to start with import errors

**Cause:**
PyBase not installed in editable mode or virtual environment not activated.

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install PyBase in editable mode
pip install -e ".[all,dev]"

# Verify installation
pip show pybase
# Should show: Location: /path/to/pybase/src
```

**For Development:**
```bash
# Add src directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or add to .env
echo 'PYTHONPATH=./src' >> .env
```

**Verification:**
```bash
python -c "from pybase.main import app; print('Import OK')"
```

---

## Celery Worker Issues

### 1. Celery Not Installed

**Symptoms:**
- Worker script exits with: `WARNING: Celery not available. Install: pip install celery`
- `ModuleNotFoundError: No module named 'celery'`
- Background search indexing tasks not running

**Cause:**
Celery is an optional dependency and may not be installed by default.

**Solution:**
```bash
# Install Celery with Redis support
pip install celery redis

# Or install with all PyBase dependencies
pip install -e ".[all]"
```

**Verification:**
```bash
python -c "import celery; print(f'Celery {celery.__version__} installed')"
# Should output: Celery 5.x.x installed
```

---

### 2. Redis Broker/Backend Connection Failed

**Symptoms:**
- Worker fails to start with: `kombu.exceptions.OperationalError`
- `Error: No such transport: redis`
- Tasks not being queued or executed

**Cause:**
Celery worker requires Redis for both broker (task queue) and backend (result storage).

**Solution:**

#### Start Redis Service
```bash
# Using Docker Compose
docker compose up -d redis

# Verify Redis is running
docker compose ps redis
# Should show: redis with state 'Up'

# Test Redis connection
docker compose exec redis redis-cli ping
# Should output: PONG
```

#### Configure Celery URLs in `.env`
```env
# Celery broker (task queue) - uses Redis database 1
CELERY_BROKER_URL=redis://localhost:6379/1

# Celery backend (result storage) - uses Redis database 2
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Main application Redis - uses database 0
REDIS_URL=redis://localhost:6379/0
```

**Note:** Use different Redis databases (0, 1, 2) to separate concerns and avoid key collisions.

**Verification:**
```bash
# Test broker connection
python -c "
from celery import Celery
app = Celery(broker='redis://localhost:6379/1')
print(app.connection().ensure_connection(max_retries=1))
print('Celery broker connection OK')
"
```

---

### 3. Worker Import Errors

**Symptoms:**
- `ModuleNotFoundError: No module named 'pybase'`
- `ImportError: cannot import name 'get_search_service'`
- Worker crashes on startup with import errors

**Cause:**
Worker script cannot find PyBase modules due to incorrect PYTHONPATH or missing installation.

**Solution:**

#### Install PyBase in Editable Mode
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install PyBase with all dependencies
pip install -e ".[all,dev]"

# Verify installation
pip show pybase
# Should show: Location: /path/to/pybase/src
```

#### Set PYTHONPATH (Alternative)
```bash
# Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or add to .env file
echo 'PYTHONPATH=./src' >> .env
```

#### Fix Broken Import Path (Known Issue)
```python
# Edit workers/celery_search_worker.py line 34
# Change from:
include=["src.pybase.t"],  # BROKEN: incomplete module path

# To:
include=["src.pybase.tasks"],  # FIXED: complete module path
```

**Verification:**
```bash
# Test imports from worker context
python -c "
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname('.')))
from pybase.services.search import get_search_service
print('Worker imports OK')
"
```

---

### 4. Database Connection Errors in Tasks

**Symptoms:**
- Tasks fail with: `sqlalchemy.exc.OperationalError`
- Worker logs show database connection refused
- Individual tasks timeout or fail

**Cause:**
Celery tasks create new database connections and may fail if PostgreSQL is not accessible or `DATABASE_URL` is incorrect.

**Solution:**

#### Verify Database is Running
```bash
# Using Docker Compose
docker compose ps postgres
# Should show: postgres with state 'Up'

# Test database connection
psql -h localhost -U pybase -d pybase -c "SELECT 1;"
# Should output: 1 row
```

#### Configure DATABASE_URL in `.env`
```env
# Async driver (for FastAPI app)
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase

# Sync driver (for Celery tasks - some tasks may use synchronous connections)
DATABASE_SYNC_URL=postgresql://pybase:pybase@localhost:5432/pybase
```

#### Update Task to Handle Connection Errors
```python
# In workers/celery_search_worker.py
@app.task(name="index_record")
def index_record(record_id: str, table_id: str, workspace_id: str):
    from sqlalchemy import create_engine
    from sqlalchemy.exc import OperationalError

    try:
        # Use synchronous connection for Celery tasks
        engine = create_engine(os.getenv("DATABASE_URL").replace("+asyncpg", ""))
        with engine.connect() as conn:
            # Task logic here
            pass
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        raise  # Celery will retry task
```

**Verification:**
```bash
# Start worker with debug logging
celery -A workers.celery_search_worker worker --loglevel=debug

# In another terminal, trigger a test task
python -c "
from workers.celery_search_worker import index_record
result = index_record.delay('test-record-id', 'test-table-id', 'test-workspace-id')
print(f'Task ID: {result.id}')
print(f'Task status: {result.status}')
"
```

---

### 5. Starting and Managing the Celery Worker

**Basic Worker Commands:**

```bash
# Start worker in foreground (development)
celery -A workers.celery_search_worker worker --loglevel=info

# Start worker in background (production)
celery -A workers.celery_search_worker worker --loglevel=info --detach

# Start worker with concurrency
celery -A workers.celery_search_worker worker --concurrency=4 --loglevel=info

# Start worker with autoreload (development)
celery -A workers.celery_search_worker worker --loglevel=info --autoreload
```

**Monitor Worker Status:**
```bash
# Check active tasks
celery -A workers.celery_search_worker inspect active

# Check scheduled tasks
celery -A workers.celery_search_worker inspect scheduled

# Check worker stats
celery -A workers.celery_search_worker inspect stats

# Ping workers
celery -A workers.celery_search_worker inspect ping
```

**Stop Worker:**
```bash
# Graceful shutdown (wait for tasks to complete)
celery -A workers.celery_search_worker control shutdown

# Force shutdown (kill worker immediately)
pkill -f "celery worker"
```

**Verification:**
```bash
# Verify worker is running and accepting tasks
celery -A workers.celery_search_worker inspect active
# Should return worker status (even if no active tasks)
```

---

### 6. Scheduled Tasks Not Running

**Symptoms:**
- Periodic tasks (like `refresh_search_indexes`) never execute
- Celery beat scheduler not running
- No scheduled task logs in worker output

**Cause:**
Celery beat scheduler must run separately to schedule periodic tasks.

**Solution:**

#### Start Celery Beat Scheduler
```bash
# Start beat scheduler in foreground
celery -A workers.celery_search_worker beat --loglevel=info

# Start beat scheduler in background
celery -A workers.celery_search_worker beat --loglevel=info --detach

# Or combine worker + beat in one process (development only)
celery -A workers.celery_search_worker worker --beat --loglevel=info
```

#### Using Docker Compose (Recommended)
```yaml
# Add to docker-compose.yml
services:
  celery-worker:
    build: .
    command: celery -A workers.celery_search_worker worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: .
    command: celery -A workers.celery_search_worker beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
    depends_on:
      - redis
```

**Start Services:**
```bash
docker compose up -d celery-worker celery-beat
```

**Verification:**
```bash
# Check beat scheduler logs
docker compose logs -f celery-beat
# Should show: Scheduler: Sending due task refresh_search_indexes
```

---

## CAD/PDF Extraction Dependencies

### 1. ezdxf Installation and DXF Parsing Issues

**Symptoms:**
- `ImportError: No module named 'ezdxf'`
- DXF file parsing fails with encoding errors
- Missing layers or entities when extracting DXF data
- `ValueError: unsupported DXF version`

**Cause:**
ezdxf library not installed or incompatible DXF file version.

**Solution:**

#### Install ezdxf
```bash
# Install ezdxf (pure Python, no system dependencies needed)
pip install ezdxf

# Or install with all PyBase dependencies
pip install -e ".[all]"
```

#### Handle DXF Version Compatibility
```python
# Check DXF version before parsing
import ezdxf

try:
    doc = ezdxf.readfile("drawing.dxf")
    print(f"DXF version: {doc.dxfversion}")

    # PyBase supports DXF versions R12 and later
    if doc.dxfversion < "AC1009":  # R12
        print("Warning: DXF version too old, may have compatibility issues")
except ezdxf.DXFVersionError as e:
    print(f"Unsupported DXF version: {e}")
except ezdxf.DXFStructureError as e:
    print(f"Corrupted DXF file: {e}")
```

#### Common DXF Parsing Issues
```bash
# Issue: Encoding errors with international characters
# Solution: Specify encoding when reading DXF
python -c "
import ezdxf
doc = ezdxf.readfile('drawing.dxf', encoding='utf-8')  # or 'cp1252', 'latin1'
print('DXF loaded successfully')
"
```

**Verification:**
```bash
# Test ezdxf installation and basic parsing
python -c "
import ezdxf
doc = ezdxf.new('R2010')  # Create new DXF
doc.modelspace().add_line((0, 0), (10, 10))
doc.saveas('test.dxf')
print('ezdxf OK')
"
```

---

### 2. ifcopenshell Installation and IFC/BIM Parsing

**Symptoms:**
- `ImportError: No module named 'ifcopenshell'`
- `OSError: cannot load library 'libifcopenshell.so'`
- IFC file parsing fails with segmentation fault
- Missing building elements when extracting IFC data

**Cause:**
ifcopenshell requires compiled C++ libraries (Open CASCADE) which may not be available as pre-built wheels on all platforms.

**Solution:**

#### Linux (Ubuntu/Debian)
```bash
# Install Open CASCADE dependencies
sudo apt update
sudo apt install -y \
  liboce-foundation-dev \
  liboce-modeling-dev \
  liboce-ocaf-dev \
  liboce-visualization-dev

# Install ifcopenshell
pip install ifcopenshell

# If pip install fails, try conda (includes pre-built binaries)
conda install -c conda-forge ifcopenshell
```

#### macOS
```bash
# Install Open CASCADE via Homebrew
brew install opencascade

# Install ifcopenshell
pip install ifcopenshell

# If pip fails, use conda
conda install -c conda-forge ifcopenshell
```

#### Windows
```bash
# Option 1: Install pre-built wheel (easiest)
pip install ifcopenshell --prefer-binary

# Option 2: Use conda (recommended if Option 1 fails)
conda install -c conda-forge ifcopenshell

# Option 3: Download pre-built binaries from:
# https://github.com/IfcOpenShell/IfcOpenShell/releases
# Extract and add to PYTHONPATH
```

#### Docker Installation (Recommended for Production)
```dockerfile
# Add to Dockerfile
FROM python:3.11-slim

# Install Open CASCADE and build tools
RUN apt-get update && apt-get install -y \
    liboce-foundation-dev \
    liboce-modeling-dev \
    && rm -rf /var/lib/apt/lists/*

# Install ifcopenshell
RUN pip install ifcopenshell
```

**Verification:**
```bash
# Test ifcopenshell installation
python -c "
import ifcopenshell
print(f'ifcopenshell version: {ifcopenshell.version}')

# Test basic IFC parsing
ifc = ifcopenshell.file()
ifc.create_entity('IfcProject')
print('ifcopenshell OK')
"
```

---

### 3. PyPDF2/pypdf PDF Extraction Issues

**Symptoms:**
- `ImportError: No module named 'pypdf'`
- PDF table extraction returns empty results
- `PdfReadError: EOF marker not found`
- Encrypted PDF files cannot be processed

**Cause:**
Missing PDF library, corrupted PDF files, or encrypted PDFs without password.

**Solution:**

#### Install PyPDF Library
```bash
# Install pypdf (modern fork of PyPDF2)
pip install pypdf

# Or install PyPDF2 (older version)
pip install PyPDF2

# Install with all PyBase dependencies
pip install -e ".[all]"
```

#### Handle Encrypted PDFs
```python
# Decrypt password-protected PDFs
from pypdf import PdfReader

reader = PdfReader("encrypted.pdf")
if reader.is_encrypted:
    # Try empty password first (PDFs with user restrictions but no password)
    reader.decrypt("")

    # Or use actual password
    # reader.decrypt("your_password_here")

# Extract text
for page in reader.pages:
    text = page.extract_text()
    print(text)
```

#### Handle Corrupted PDFs
```bash
# Use qpdf to repair corrupted PDFs
sudo apt install qpdf  # Linux
brew install qpdf      # macOS

# Repair PDF
qpdf --check input.pdf
qpdf --linearize input.pdf output_repaired.pdf
```

#### Advanced Table Extraction (tabula-py)
```bash
# For better table extraction, install tabula-py
pip install tabula-py

# Requires Java Runtime
# Linux: sudo apt install default-jre
# macOS: brew install openjdk
# Windows: Download from https://www.java.com/

# Extract tables from PDF
python -c "
import tabula
df = tabula.read_pdf('drawing.pdf', pages='all')
print(df[0] if df else 'No tables found')
"
```

**Verification:**
```bash
# Test PDF extraction
python -c "
from pypdf import PdfReader
import io

# Create test PDF
from pypdf import PdfWriter
writer = PdfWriter()
writer.add_blank_page(width=200, height=200)
pdf_bytes = io.BytesIO()
writer.write(pdf_bytes)
pdf_bytes.seek(0)

# Read it back
reader = PdfReader(pdf_bytes)
print(f'PDF has {len(reader.pages)} pages')
print('pypdf OK')
"
```

---

### 4. cadquery/OCP STEP File Processing

**Symptoms:**
- `ImportError: No module named 'cadquery'`
- `ImportError: No module named 'OCP'` (Open CASCADE Python bindings)
- STEP file parsing fails with geometry errors
- Installation takes very long or fails with build errors

**Cause:**
cadquery requires OCP (Open CASCADE Technology Python bindings) which are large pre-compiled packages.

**Solution:**

#### Install cadquery (Recommended: conda)
```bash
# Using conda (easiest - includes pre-built OCP bindings)
conda install -c conda-forge cadquery

# Using pip (may require compilation)
pip install cadquery

# If pip fails, install OCP separately first
pip install ocp
pip install cadquery
```

#### Linux Build Dependencies (if compiling from source)
```bash
sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
  git \
  liboce-foundation-dev \
  liboce-modeling-dev \
  libgl1-mesa-dev \
  libglu1-mesa-dev

pip install cadquery
```

#### macOS Build Dependencies
```bash
brew install cmake opencascade

pip install cadquery
```

#### Docker Installation
```dockerfile
# Use conda-based image for easier cadquery installation
FROM continuumio/miniconda3

RUN conda install -c conda-forge cadquery python=3.11

# Or use pip with pre-built wheels
FROM python:3.11-slim
RUN pip install cadquery --prefer-binary
```

#### Lightweight Alternative: occwl
If full cadquery is too heavy, use `occwl` (lighter Open CASCADE wrapper):
```bash
pip install occwl

# Usage
from occwl.io import load_step
shape = load_step("part.step")
```

**Verification:**
```bash
# Test cadquery installation
python -c "
import cadquery as cq
from OCP.STEPControl import STEPControl_Reader

# Create simple shape
box = cq.Workplane('XY').box(10, 10, 10)
print(f'Created box: {box}')
print('cadquery OK')
"
```

---

### 5. Werk24 API Integration (Optional)

**Symptoms:**
- `ImportError: No module named 'werk24'`
- API requests fail with `401 Unauthorized`
- Drawing extraction returns empty results
- Rate limit errors from Werk24 API

**Cause:**
Werk24 is an optional third-party AI service for extracting data from engineering drawings.

**Solution:**

#### Install Werk24 Client
```bash
# Install werk24 Python client
pip install werk24

# Or install with PyBase
pip install -e ".[all]"
```

#### Configure API Key
```env
# Add to .env file
WERK24_API_KEY=your_api_key_here

# Get API key from: https://werk24.io/
```

#### Handle API Errors
```python
# Graceful fallback if Werk24 unavailable
from pybase.extraction.werk24.client import Werk24Client

try:
    client = Werk24Client(api_key=os.getenv("WERK24_API_KEY"))
    result = await client.extract(file_path)
except ImportError:
    logger.warning("Werk24 not available, falling back to basic extraction")
    result = await basic_pdf_extractor.extract(file_path)
except Exception as e:
    logger.error(f"Werk24 API error: {e}")
    result = None
```

#### Rate Limiting
```python
# Implement exponential backoff for rate limits
import time
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(5))
async def extract_with_werk24(file_path: str):
    client = Werk24Client()
    return await client.extract(file_path)
```

**Verification:**
```bash
# Test Werk24 client (requires valid API key)
python -c "
import os
from werk24 import Hook, W24TechreadClient, W24AskVariantPDF

# Check if API key is set
api_key = os.getenv('WERK24_API_KEY')
if api_key:
    client = W24TechreadClient.make_from_env()
    print('Werk24 client initialized OK')
else:
    print('WERK24_API_KEY not set - skipping')
"
```

---

### 6. Missing System Dependencies for CAD/PDF Extraction

**Symptoms:**
- Multiple CAD libraries fail to install
- Build errors during `pip install`
- `gcc: command not found` or similar compiler errors

**Cause:**
CAD libraries require system-level build tools and geometry libraries.

**Solution:**

#### Complete Dependency Installation

**Linux (Ubuntu/Debian):**
```bash
# Install all build dependencies at once
sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
  git \
  python3-dev \
  libpq-dev \
  libgeos-dev \
  libspatialindex-dev \
  liboce-foundation-dev \
  liboce-modeling-dev \
  liboce-ocaf-dev \
  libgl1-mesa-dev \
  libglu1-mesa-dev \
  tesseract-ocr \
  tesseract-ocr-eng \
  qpdf

# Then install PyBase
pip install -e ".[all]"
```

**macOS:**
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install all dependencies
brew install \
  python@3.11 \
  postgresql \
  redis \
  geos \
  spatialindex \
  opencascade \
  tesseract \
  qpdf

# Install PyBase
pip install -e ".[all]"
```

**Windows:**
```bash
# Install using conda (easiest on Windows)
conda create -n pybase python=3.11
conda activate pybase
conda install -c conda-forge \
  ifcopenshell \
  cadquery \
  geos \
  spatialindex

# Install remaining dependencies with pip
pip install -e ".[all]" --prefer-binary
```

**Verification:**
```bash
# Test all CAD/PDF dependencies
python -c "
import ezdxf
import ifcopenshell
from pypdf import PdfReader
import cadquery as cq

print('✓ ezdxf')
print('✓ ifcopenshell')
print('✓ pypdf')
print('✓ cadquery')
print('')
print('All CAD/PDF Extraction dependencies OK!')
"
```

---

## Known Issues & Workarounds

### 1. Extraction API Type Errors (CRITICAL)

**Status:** Known issue - 40+ type errors in extraction endpoints
**Affected File:** `src/pybase/api/v1/extraction.py`
**Impact:** CAD/PDF extraction may fail at runtime

**Symptoms:**
- Type errors when calling extraction endpoints
- Parameter mismatch errors
- Missing required parameters in extractor methods

**Temporary Workaround:**
The extraction API has type safety issues but basic functionality may still work:
```python
# When calling extraction endpoints, ensure all parameters are provided
# Example: PDF extraction
result = await pdf_extractor.extract(
    source_file=file_path,
    source_type="pdf"
)

# DXF extraction requires layer_filter
result = await dxf_parser.parse(
    layer_filter=None  # Provide default even if optional
)
```

**Permanent Fix:** In development - see [lsp-type-errors-critical.md](lsp-type-errors-critical.md)

**Affected Endpoints:**
- `POST /api/v1/extraction/pdf` - PDF table/dimension extraction
- `POST /api/v1/extraction/dxf` - AutoCAD DXF parsing
- `POST /api/v1/extraction/ifc` - IFC/BIM parsing
- `POST /api/v1/extraction/step` - STEP file parsing
- `POST /api/v1/extraction/werk24` - Werk24 AI extraction

---

### 2. Celery Worker Import Error

**Status:** Known issue - broken import path
**Affected File:** `workers/celery_search_worker.py` (line 34)
**Impact:** Background search indexing fails

**Symptoms:**
- Celery worker fails to start
- `ModuleNotFoundError` for incomplete import path
- Search indexing tasks not running

**Issue:**
```python
# Line 34 in workers/celery_search_worker.py
include=["src.pybase.t"],  # BROKEN: incomplete module path
```

**Temporary Workaround:**
Disable background search indexing until fixed:
```env
# Add to .env to disable search features
ENABLE_SEARCH=false
```

Or manually fix the import:
```python
# Edit workers/celery_search_worker.py line 34
include=["src.pybase.tasks"],  # Fixed: complete module path
```

**Start Worker After Fix:**
```bash
celery -A workers.celery_search_worker worker --loglevel=info
```

**Verification:**
```bash
# Check worker is running
celery -A workers.celery_search_worker inspect active
# Should show active worker
```

---

### 3. Meilisearch Integration Incomplete

**Status:** Known issue - optional dependency handling broken
**Affected File:** `src/pybase/services/search.py`
**Impact:** Search feature 100% non-functional if Meilisearch not installed

**Symptoms:**
- `ImportError: cannot import name 'meilisearch'`
- Application crashes when search endpoints called
- No graceful degradation when Meilisearch unavailable

**Temporary Workaround:**

**Option 1: Disable Search Feature**
```env
# Add to .env
ENABLE_SEARCH=false
```

**Option 2: Install Meilisearch**
```bash
# Using Docker Compose (recommended)
docker compose up -d meilisearch

# Verify it's running
curl http://localhost:7700/health
# Should return: {"status":"available"}

# Install Python client
pip install meilisearch

# Add to .env
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your_master_key_here
```

**Verification:**
```bash
# Test Meilisearch connection
python -c "
from meilisearch import Client
client = Client('http://localhost:7700')
print(client.health())
print('Meilisearch OK')
"
```

---

### 4. Record API Type Mismatches

**Status:** Known issue - ORM models returned instead of schemas
**Affected File:** `src/pybase/api/v1/records.py`
**Impact:** Type safety broken, potential runtime errors

**Symptoms:**
- Type errors in IDE/LSP
- Unexpected response formats
- Frontend contract violations

**Temporary Workaround:**
The API functions but responses may not match TypeScript contracts exactly. Frontend should handle defensive typing:
```typescript
// Frontend: Add runtime type validation
const response = await api.getRecord(recordId);
const record = RecordSchema.parse(response); // Use zod or similar
```

**Permanent Fix:** In development - converting ORM models to Pydantic schemas

---

## Environment Variable Reference

### Required Variables
```env
# Must be set for application to start
SECRET_KEY=<generate_with_secrets.token_urlsafe(64)>
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
REDIS_URL=redis://localhost:6379/0
```

### Optional Variables
```env
# CAD/PDF Extraction
WERK24_API_KEY=<optional_for_ai_extraction>
TESSERACT_CMD=/usr/bin/tesseract

# Search (optional)
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=<optional>

# Object Storage (required for file uploads)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=pybase

# Email (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Feature Flags
ENABLE_REGISTRATION=true
ENABLE_EXTRACTION=true
ENABLE_WEBSOCKETS=true
ENABLE_SEARCH=false  # Disable if Meilisearch not available
```

See [`.env.example`](../.env.example) for complete reference.

---

## Getting Help

### Before Asking for Help

1. **Check logs for error messages:**
   ```bash
   # Application logs
   docker compose logs -f app

   # Database logs
   docker compose logs postgres

   # Redis logs
   docker compose logs redis
   ```

2. **Verify environment configuration:**
   ```bash
   # Check .env file exists and has required variables
   cat .env | grep -E "SECRET_KEY|DATABASE_URL|REDIS_URL"
   ```

3. **Test individual components:**
   ```bash
   # Database
   psql -h localhost -U pybase -d pybase -c "SELECT 1;"

   # Redis
   redis-cli ping

   # Python imports
   python -c "from pybase.main import app"
   ```

### Support Channels

- **GitHub Issues:** [github.com/pybase/pybase/issues](https://github.com/pybase/pybase/issues)
- **Documentation:** [docs/](.) - Check related guides
- **Known Issues:** [codebase-summary.md](codebase-summary.md) - Current blockers
- **Type Errors:** [lsp-type-errors-critical.md](lsp-type-errors-critical.md) - Detailed error analysis

### Reporting Issues

When reporting a new issue, include:
1. **Environment:** OS, Python version, installation method
2. **Error Message:** Complete traceback or error output
3. **Steps to Reproduce:** Exact commands run
4. **Configuration:** Relevant `.env` variables (redact secrets!)
5. **Logs:** Application logs showing the error

Example:
```bash
# Collect diagnostic information
python --version > debug_info.txt
pip list >> debug_info.txt
docker compose ps >> debug_info.txt
cat .env | grep -v "SECRET\|PASSWORD\|KEY" >> debug_info.txt
```

---

## Additional Resources

- [Deployment Guide](deployment-guide.md) - Production deployment with Docker/K8s
- [Frontend Setup Guide](setup/frontend-setup-guide.md) - React/TypeScript setup
- [Project Roadmap](project-roadmap.md) - Upcoming features and fixes
- [Code Standards](code-standards.md) - Contributing guidelines
- [System Architecture](system-architecture.md) - Technical architecture overview
