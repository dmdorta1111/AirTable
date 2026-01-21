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

### 4. Meilisearch Search Engine (Optional)

**Symptoms:**
- `ImportError: cannot import name 'meilisearch'`
- Search endpoints fail with module not found errors
- `TypeError: 'NoneType' object is not callable` when accessing search service
- No graceful degradation when Meilisearch unavailable

**Cause:**
Meilisearch is an optional dependency for full-text search functionality. PyBase can run without it, but search features will be unavailable.

**Solution:**

#### Option 1: Install Meilisearch Server (Recommended for Production)

**Using Docker Compose (Easiest):**
```bash
# Start Meilisearch container
docker compose up -d meilisearch

# Verify it's running
docker compose ps meilisearch
# Should show: meilisearch with state 'Up'

# Check health
curl http://localhost:7700/health
# Should return: {"status":"available"}
```

**Using Docker Standalone:**
```bash
# Run Meilisearch container
docker run -d \
  --name meilisearch \
  -p 7700:7700 \
  -e MEILI_MASTER_KEY=your_master_key_here \
  -v $(pwd)/meili_data:/meili_data \
  getmeili/meilisearch:v1.5

# Verify
curl http://localhost:7700/health
```

**Linux (Native Installation):**
```bash
# Download and install Meilisearch
curl -L https://install.meilisearch.com | sh

# Move to system path
sudo mv ./meilisearch /usr/local/bin/

# Run as service
meilisearch --master-key your_master_key_here
```

**macOS:**
```bash
# Install via Homebrew
brew install meilisearch

# Start service
brew services start meilisearch

# Or run manually
meilisearch --master-key your_master_key_here
```

#### Option 2: Install Python Client Only

If you have a remote Meilisearch instance or want to install just the client:
```bash
# Install meilisearch Python client
pip install meilisearch

# Or install with all PyBase dependencies
pip install -e ".[all]"
```

#### Configure Environment Variables

Add to `.env`:
```env
# Meilisearch configuration
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your_master_key_here

# Enable search features
ENABLE_SEARCH=true
```

#### Option 3: Disable Search Features

If you don't need search functionality:
```env
# Add to .env to disable search
ENABLE_SEARCH=false
```

**Note:** With `ENABLE_SEARCH=false`, PyBase will skip Meilisearch initialization and search endpoints will return 404 or gracefully degrade.

#### Handle Optional Dependency in Code

For developers: Ensure proper lazy import handling:
```python
# Correct pattern for optional dependency
try:
    from meilisearch import Client
    MEILISEARCH_AVAILABLE = True
except ImportError:
    MEILISEARCH_AVAILABLE = False
    Client = None

# Usage with graceful fallback
def get_search_service():
    if not MEILISEARCH_AVAILABLE or not settings.ENABLE_SEARCH:
        return None
    return SearchService(client=Client(settings.MEILISEARCH_URL))
```

**Common Issues:**

**Issue 1: `TypeError: 'NoneType' object is not callable`**
```bash
# Cause: meilisearch_client factory returns None when unavailable
# Solution: Set ENABLE_SEARCH=false or install Meilisearch
```

**Issue 2: `AttributeError: 'Record' object has no attribute 'values'`**
```bash
# Cause: Incorrect Record model API usage in search indexing
# Workaround: Disable search until fix is deployed
ENABLE_SEARCH=false
```

**Issue 3: Connection Refused**
```bash
# Verify Meilisearch is running
curl http://localhost:7700/health

# Check Docker container status
docker compose ps meilisearch

# View logs
docker compose logs meilisearch
```

**Verification:**
```bash
# Test Meilisearch server
curl http://localhost:7700/health
# Should return: {"status":"available"}

# Test Python client
python -c "
from meilisearch import Client
client = Client('http://localhost:7700', 'your_master_key_here')
print(client.health())
print('Meilisearch client OK')
"

# Test PyBase integration
python -c "
import os
os.environ['MEILISEARCH_URL'] = 'http://localhost:7700'
os.environ['ENABLE_SEARCH'] = 'true'
from pybase.services.search import get_search_service
service = get_search_service()
print('PyBase search service OK' if service else 'Search disabled')
"
```

**Production Considerations:**
- **Master Key:** Always set a strong master key in production
- **Indexing:** Background indexing requires Celery worker (see Celery Worker Issues section)
- **Performance:** Meilisearch indexes are stored on disk, ensure sufficient storage
- **Scaling:** For large datasets, consider dedicated Meilisearch instance with SSD storage

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

## Docker Container Issues

### 1. Containers Fail to Start

**Symptoms:**
- `docker compose up` fails with exit codes
- Services immediately restart in a loop
- Health checks continuously failing
- Container exits with error messages

**Cause:**
Incorrect configuration, missing dependencies, or resource constraints.

**Solution:**

#### Check Container Status
```bash
# View all containers and their status
docker compose ps

# Check specific service
docker compose ps postgres
# Should show: State 'Up' and healthy

# View logs for failing service
docker compose logs postgres
docker compose logs api
docker compose logs redis
```

#### Common Exit Codes
```bash
# Exit code 1: Application error
docker compose logs api
# Look for Python tracebacks or startup errors

# Exit code 137: Out of memory (OOM killed)
# Solution: Increase Docker memory limit
# Docker Desktop: Settings → Resources → Memory (increase to 4GB+)

# Exit code 139: Segmentation fault
# Solution: Check CAD library dependencies in Dockerfile
```

#### Verify Docker Compose Configuration
```bash
# Validate docker-compose.yml syntax
docker compose config

# Should output parsed configuration without errors
```

#### Restart Specific Service
```bash
# Restart single service
docker compose restart postgres

# Restart all services
docker compose restart

# Force recreate containers
docker compose up -d --force-recreate
```

**Verification:**
```bash
# All services should be 'Up' and healthy
docker compose ps
# Expected: postgres, redis, minio, api all showing 'Up (healthy)'
```

---

### 2. Port Already in Use Conflicts

**Symptoms:**
- `Bind for 0.0.0.0:5432 failed: port is already allocated`
- `Error starting userland proxy: listen tcp4 0.0.0.0:6379: bind: address already in use`
- Cannot access services on expected ports

**Cause:**
Another process is using the same port (local PostgreSQL, Redis, or previous containers).

**Solution:**

#### Identify Process Using Port
```bash
# Linux/macOS - Find process on port 5432
sudo lsof -i :5432
# or
sudo netstat -tlnp | grep 5432

# Windows - Find process on port 5432
netstat -ano | findstr :5432

# Kill process if it's a stale service
# Linux/macOS
sudo kill -9 <PID>

# Windows
taskkill /PID <PID> /F
```

#### Stop Local Database Services
```bash
# Stop local PostgreSQL
# Linux
sudo systemctl stop postgresql

# macOS
brew services stop postgresql

# Stop local Redis
# Linux
sudo systemctl stop redis

# macOS
brew services stop redis
```

#### Change Docker Compose Ports
If you want to keep local services running, modify `docker-compose.yml`:
```yaml
services:
  postgres:
    ports:
      - "5433:5432"  # Changed from 5432:5432

  redis:
    ports:
      - "6380:6379"  # Changed from 6379:6379
```

Then update `.env`:
```env
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5433/pybase
REDIS_URL=redis://localhost:6380/0
```

#### Stop and Remove Previous Containers
```bash
# Stop all containers
docker compose down

# Stop and remove volumes (WARNING: deletes data!)
docker compose down -v

# Remove orphaned containers
docker compose down --remove-orphans
```

**Verification:**
```bash
# Check ports are accessible
nc -zv localhost 5432  # PostgreSQL
nc -zv localhost 6379  # Redis
nc -zv localhost 9000  # MinIO
nc -zv localhost 8000  # API

# Or use curl
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

---

### 3. Container Network Connectivity Issues

**Symptoms:**
- API cannot connect to PostgreSQL: `connection refused` or `no route to host`
- Services cannot communicate with each other
- `getaddrinfo ENOTFOUND postgres` errors
- Worker cannot connect to Redis broker

**Cause:**
Network configuration issues, DNS resolution failures, or incorrect service hostnames.

**Solution:**

#### Verify Docker Network Exists
```bash
# List Docker networks
docker network ls
# Should show: pybase-network

# Inspect network
docker network inspect pybase-network
# Should show all services attached
```

#### Check Service DNS Resolution
```bash
# Test DNS resolution from api container
docker compose exec api ping postgres
# Should resolve and ping successfully

docker compose exec api ping redis
docker compose exec api ping minio
```

#### Verify Service Hostnames in Environment
```bash
# Inside containers, services use container names as hostnames
# NOT 'localhost'

# ❌ Wrong - will not work inside containers
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase

# ✓ Correct - use service name from docker-compose.yml
DATABASE_URL=postgresql+asyncpg://pybase:pybase@postgres:5432/pybase
REDIS_URL=redis://redis:6379/0
S3_ENDPOINT_URL=http://minio:9000
```

#### Recreate Network
```bash
# Remove all containers and networks
docker compose down

# Recreate with new network
docker compose up -d

# Verify network connectivity
docker compose exec api ping postgres
```

#### Check Firewall Rules
```bash
# Linux - check if Docker chains exist in iptables
sudo iptables -L DOCKER

# If Docker network issues persist, restart Docker daemon
# Linux
sudo systemctl restart docker

# macOS/Windows
# Restart Docker Desktop application
```

**Verification:**
```bash
# Test database connection from api container
docker compose exec api python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test():
    engine = create_async_engine('postgresql+asyncpg://pybase:pybase@postgres:5432/pybase')
    async with engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print('Database connection OK')

asyncio.run(test())
"
```

---

### 4. Volume Permission Errors

**Symptoms:**
- PostgreSQL fails with: `initdb: could not change permissions`
- Redis fails with: `Can't open or create append-only dir`
- MinIO fails with: `Unable to write to data directory`
- Permission denied errors in container logs

**Cause:**
Volume mount permission mismatches between host and container user IDs.

**Solution:**

#### Check Volume Ownership
```bash
# List Docker volumes
docker volume ls
# Should show: pybase_postgres-data, pybase_redis-data, pybase_minio-data

# Inspect volume location
docker volume inspect pybase_postgres-data
# Note the "Mountpoint" path

# Check permissions (Linux only - requires root)
sudo ls -la /var/lib/docker/volumes/pybase_postgres-data/_data
```

#### Fix PostgreSQL Volume Permissions
```bash
# Stop containers
docker compose down

# Remove volumes (WARNING: deletes data!)
docker volume rm pybase_postgres-data pybase_redis-data pybase_minio-data

# Restart with fresh volumes
docker compose up -d postgres redis minio

# Verify containers start successfully
docker compose logs postgres
# Should NOT show permission errors
```

#### Using Bind Mounts (Alternative)
If you need host access to data, modify `docker-compose.yml`:
```yaml
services:
  postgres:
    volumes:
      - ./data/postgres:/var/lib/postgresql/data  # Bind mount instead of volume
```

Then fix permissions:
```bash
# Create data directory with correct permissions
mkdir -p ./data/postgres
chmod 777 ./data/postgres  # Or use specific user ID

# Start container
docker compose up -d postgres
```

#### SELinux Issues (Linux Only)
```bash
# If using SELinux, add :z or :Z suffix to volume mounts
services:
  postgres:
    volumes:
      - postgres-data:/var/lib/postgresql/data:z

# Or disable SELinux for Docker (not recommended for production)
sudo setenforce 0
```

**Verification:**
```bash
# Check if containers are running without restart loops
docker compose ps
# All should show 'Up' without constant restarts

# Verify data persistence
docker compose exec postgres psql -U pybase -d pybase -c "CREATE TABLE test (id INT);"
docker compose restart postgres
docker compose exec postgres psql -U pybase -d pybase -c "\dt"
# Should show 'test' table still exists
```

---

### 5. Health Check Failures

**Symptoms:**
- Container status shows `Up (unhealthy)`
- Dependent services don't start
- `docker compose ps` shows health: starting for extended time
- API cannot start due to unhealthy dependencies

**Cause:**
Service not ready, health check command failing, or timeout too short.

**Solution:**

#### Check Health Status
```bash
# View health status of all services
docker compose ps

# Inspect specific container health
docker inspect pybase-postgres --format='{{json .State.Health}}' | jq

# View health check logs
docker inspect pybase-postgres --format='{{range .State.Health.Log}}{{.Output}}{{end}}'
```

#### PostgreSQL Health Check
```bash
# Test health check command manually
docker compose exec postgres pg_isready -U pybase -d pybase

# Should output: postgres:5432/pybase - accepting connections

# If failing, check PostgreSQL logs
docker compose logs postgres
# Look for startup errors or initialization issues
```

#### Redis Health Check
```bash
# Test health check manually
docker compose exec redis redis-cli ping

# Should output: PONG

# If failing, check Redis logs
docker compose logs redis
```

#### MinIO Health Check
```bash
# Test health check manually
docker compose exec minio mc ready local

# Check MinIO API accessibility
curl http://localhost:9000/minio/health/live
# Should return: OK
```

#### Increase Health Check Timeout
If services are slow to start, modify `docker-compose.yml`:
```yaml
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pybase -d pybase"]
      interval: 10s
      timeout: 5s
      retries: 10  # Increased from 5
      start_period: 30s  # Add startup grace period
```

#### Disable Health Checks (Debugging Only)
```yaml
services:
  postgres:
    healthcheck:
      disable: true  # Temporary - remove after debugging
```

**Verification:**
```bash
# All services should show 'healthy' status
docker compose ps
# Expected: postgres (healthy), redis (healthy), minio (healthy)

# Test dependent service can start
docker compose up -d api
docker compose logs api
# Should show successful startup without waiting errors
```

---

### 6. Service Dependency Issues

**Symptoms:**
- API starts before database is ready: `connection refused`
- Celery worker fails with: `Database connection not available`
- `depends_on` not waiting for service readiness
- Race conditions during startup

**Cause:**
Services starting before dependencies are fully initialized.

**Solution:**

#### Use Health Check Conditions
Ensure `docker-compose.yml` uses `condition: service_healthy`:
```yaml
services:
  api:
    depends_on:
      postgres:
        condition: service_healthy  # Wait for health check to pass
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
```

#### Verify Dependencies Are Configured
```bash
# Check docker-compose.yml for depends_on
grep -A 5 "depends_on:" docker-compose.yml

# Should show condition: service_healthy for critical dependencies
```

#### Start Services in Order (Manual)
```bash
# Start infrastructure services first
docker compose up -d postgres redis minio

# Wait for health checks to pass
docker compose ps
# Verify all show 'healthy'

# Then start application services
docker compose up -d api celery-worker
```

#### Implement Retry Logic in Application
For production resilience, add connection retry in application code:
```python
# In pybase/db/session.py or similar
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(10))
async def get_db_connection():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        await conn.execute("SELECT 1")
    return engine
```

#### Use Docker Compose Wait Utility (Advanced)
```dockerfile
# Add to Dockerfile
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.9.0/wait /wait
RUN chmod +x /wait

# In docker-compose.yml
services:
  api:
    environment:
      WAIT_HOSTS=postgres:5432,redis:6379,minio:9000
      WAIT_TIMEOUT=60
    command: sh -c "/wait && uvicorn pybase.main:app --host 0.0.0.0"
```

**Verification:**
```bash
# Stop all services
docker compose down

# Start all services fresh
docker compose up -d

# Watch logs for startup order
docker compose logs -f

# Should see:
# 1. postgres: database system is ready to accept connections
# 2. redis: Ready to accept connections
# 3. minio: API server started
# 4. api: Application startup complete
```

---

### 7. Docker Compose Commands Reference

**Basic Commands:**
```bash
# Start all services in background
docker compose up -d

# Start specific service
docker compose up -d postgres

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes data!)
docker compose down -v

# View running containers
docker compose ps

# View logs (all services)
docker compose logs

# Follow logs in real-time
docker compose logs -f api

# View logs for specific service
docker compose logs postgres

# Restart service
docker compose restart api

# Rebuild containers after Dockerfile changes
docker compose up -d --build

# Pull latest images
docker compose pull

# Execute command in running container
docker compose exec api python -c "print('Hello')"

# Open shell in container
docker compose exec api bash

# View resource usage
docker stats
```

**Debugging Commands:**
```bash
# Validate configuration
docker compose config

# View container processes
docker compose top

# Inspect service configuration
docker compose config postgres

# Remove stopped containers
docker compose rm

# Force recreate containers
docker compose up -d --force-recreate

# Scale service (multiple instances)
docker compose up -d --scale api=3
```

**Cleanup Commands:**
```bash
# Remove all stopped containers
docker compose down

# Remove volumes
docker volume prune

# Remove unused images
docker image prune

# Full cleanup (WARNING: removes all Docker resources!)
docker system prune -a --volumes
```

**Verification:**
```bash
# Check Docker installation
docker --version
docker compose --version

# Verify Docker daemon is running
docker info

# Test Docker with hello-world
docker run hello-world
```

---

### 8. Docker Resource Issues

**Symptoms:**
- Containers randomly crash or restart
- Slow performance or freezing
- `Cannot allocate memory` errors
- Database queries timeout

**Cause:**
Insufficient CPU, memory, or disk space allocated to Docker.

**Solution:**

#### Check Resource Usage
```bash
# View real-time resource usage
docker stats

# Should show CPU%, MEM USAGE / LIMIT for each container
# Watch for containers using near 100% of allocated resources
```

#### Increase Docker Resources (Docker Desktop)
```bash
# macOS/Windows: Docker Desktop Settings
# Settings → Resources → Advanced
# - CPUs: 4+ cores (recommended)
# - Memory: 4GB minimum, 8GB+ recommended
# - Swap: 1GB
# - Disk image size: 60GB+

# Apply & Restart Docker Desktop
```

#### Check Disk Space
```bash
# View Docker disk usage
docker system df

# Should show available space for Images, Containers, Volumes

# Clean up unused resources
docker system prune -a --volumes
# WARNING: This removes all unused containers, images, and volumes!
```

#### Limit Container Memory (Production)
```yaml
# Add to docker-compose.yml to prevent runaway containers
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

#### Monitor Logs Size
```bash
# Check log sizes
docker ps -qa | xargs docker inspect --format='{{.Name}} {{.HostConfig.LogConfig.Type}}' | grep json

# Limit log file size in docker-compose.yml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Verification:**
```bash
# Check resource allocation is sufficient
docker stats --no-stream

# All containers should show stable memory usage
# CPU% should be low during idle
# No containers should show memory near limit
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

## Environment Variables

### 1. Missing or Invalid SECRET_KEY

**Symptoms:**
- Application fails to start with: `ValueError: SECRET_KEY must be set`
- JWT token generation/validation fails
- Authentication endpoints return 500 errors
- Configuration validation errors on startup

**Cause:**
`SECRET_KEY` is required for cryptographic operations (JWT tokens, session encryption). It must be set and non-empty.

**Solution:**

#### Generate Secure SECRET_KEY
```bash
# Generate a cryptographically secure random key
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Output: xJ8v9K2pL5qM3nN7rR4tT6yY8uU0iI1oO3aA5sS7dD9fF1gG3hH5jJ7kK9lL
```

#### Add to .env File
```bash
# Create or edit .env in project root
echo "SECRET_KEY=xJ8v9K2pL5qM3nN7rR4tT6yY8uU0iI1oO3aA5sS7dD9fF1gG3hH5jJ7kK9lL" >> .env
```

#### Verify .env is Loaded
```bash
# Check if .env exists and contains SECRET_KEY
cat .env | grep SECRET_KEY
# Should output: SECRET_KEY=<your_key>

# Test loading from Python
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('SECRET_KEY is set!' if os.getenv('SECRET_KEY') else 'SECRET_KEY missing!')
"
```

**Security Best Practices:**
```env
# ✓ Good - long, random, unique per environment
SECRET_KEY=xJ8v9K2pL5qM3nN7rR4tT6yY8uU0iI1oO3aA5sS7dD9fF1gG3hH5jJ7kK9lL

# ❌ Bad - too short, predictable
SECRET_KEY=mysecret

# ❌ Bad - same key in dev and production
# Always use different keys per environment!
```

**Important Notes:**
- **Never commit** `.env` files to version control
- Use different `SECRET_KEY` for each environment (dev/staging/production)
- Rotate keys periodically in production (requires re-authentication)
- Key length should be at least 32 characters, 64+ recommended

**Verification:**
```bash
# Start application and check for SECRET_KEY errors
uvicorn pybase.main:app --reload
# Should start without "SECRET_KEY must be set" errors
```

---

### 2. Incorrect DATABASE_URL Format

**Symptoms:**
- `ValueError: Invalid DATABASE_URL format`
- `sqlalchemy.exc.ArgumentError: Could not parse rfc1738 URL`
- Application fails to connect to PostgreSQL
- Migration commands fail with database URL errors

**Cause:**
DATABASE_URL must follow specific format for SQLAlchemy async driver.

**Solution:**

#### Correct URL Format
```env
# Format: postgresql+asyncpg://username:password@host:port/database
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase

# For Docker containers (use service name as host)
DATABASE_URL=postgresql+asyncpg://pybase:pybase@postgres:5432/pybase

# For remote PostgreSQL (e.g., Neon, Supabase)
DATABASE_URL=postgresql+asyncpg://user:pass@host.region.provider.com/db?sslmode=require
```

#### Common Format Issues

**Issue 1: Missing async driver**
```env
# ❌ Wrong - missing +asyncpg
DATABASE_URL=postgresql://pybase:pybase@localhost:5432/pybase

# ✓ Correct - includes +asyncpg for async support
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase
```

**Issue 2: Special characters in password**
```bash
# If password contains special characters, URL-encode them
# Example: password "p@ss:word!" becomes "p%40ss%3Aword%21"

# Use Python to encode password
python -c "
import urllib.parse
password = 'p@ss:word!'
print(urllib.parse.quote(password, safe=''))
"
# Output: p%40ss%3Aword%21

# Then use in DATABASE_URL
DATABASE_URL=postgresql+asyncpg://pybase:p%40ss%3Aword%21@localhost:5432/pybase
```

**Issue 3: Missing database name**
```env
# ❌ Wrong - no database name
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/

# ✓ Correct - includes database name
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase
```

**Issue 4: Wrong port**
```env
# Default PostgreSQL port is 5432
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase

# If using custom port (e.g., 5433 to avoid conflicts)
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5433/pybase
```

**Test Database Connection:**
```bash
# Extract connection details and test with psql
psql -h localhost -U pybase -d pybase -c "SELECT version();"
# Should connect and show PostgreSQL version
```

**Verification:**
```bash
# Test SQLAlchemy can parse the URL
python -c "
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url

url = 'postgresql+asyncpg://pybase:pybase@localhost:5432/pybase'
parsed = make_url(url)
print(f'Driver: {parsed.drivername}')
print(f'Host: {parsed.host}')
print(f'Database: {parsed.database}')
print('DATABASE_URL format OK')
"
```

---

### 3. Missing Required Environment Variables

**Symptoms:**
- Application starts but features don't work
- File uploads fail: "S3 credentials not configured"
- Email notifications don't send
- Features silently disabled

**Cause:**
Some features require specific environment variables to function.

**Solution:**

#### Core Required Variables
These must be set for basic functionality:
```env
# Application (REQUIRED)
SECRET_KEY=<generate_with_secrets.token_urlsafe(64)>
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
REDIS_URL=redis://localhost:6379/0

# Object Storage (REQUIRED for file uploads)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=pybase
```

#### Optional Feature Variables
These enable specific features:
```env
# CAD/PDF Extraction (optional)
WERK24_API_KEY=<optional_for_ai_extraction>
TESSERACT_CMD=/usr/bin/tesseract

# Search (optional - disable if not using Meilisearch)
ENABLE_SEARCH=false
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=<optional>

# Email (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@pybase.dev

# Celery (optional - for background tasks)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

#### Check Which Variables Are Set
```bash
# List all environment variables PyBase uses
cat .env.example | grep -E "^[A-Z_]+" | cut -d= -f1

# Check which are currently set
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['SECRET_KEY', 'DATABASE_URL', 'REDIS_URL']
optional = ['WERK24_API_KEY', 'TESSERACT_CMD', 'MEILISEARCH_URL']

print('Required Variables:')
for var in required:
    status = '✓' if os.getenv(var) else '✗ MISSING'
    print(f'  {status} {var}')

print('\nOptional Variables:')
for var in optional:
    status = '✓' if os.getenv(var) else '○ not set'
    print(f'  {status} {var}')
"
```

**Verification:**
```bash
# Start app and check logs for missing variable warnings
uvicorn pybase.main:app --reload 2>&1 | grep -i "not set\|missing\|required"
```

---

### 4. .env File Not Being Loaded

**Symptoms:**
- Environment variables set in `.env` but not recognized
- Application uses default values instead of `.env` values
- `os.getenv()` returns `None` for variables in `.env`
- Works with `export VAR=value` but not from `.env`

**Cause:**
`.env` file not in correct location, wrong filename, or not being loaded by application.

**Solution:**

#### Verify .env File Location
```bash
# .env must be in project root (same directory as pyproject.toml)
ls -la .env
# Should show: -rw------- 1 user group size date .env

# Check file is not named incorrectly
ls -la | grep env
# Should show: .env (not env.txt, .env.local, etc.)

# Verify file has content
cat .env | head -5
# Should show your environment variables
```

#### Verify File Permissions (Linux/macOS)
```bash
# .env should be readable
chmod 600 .env  # Owner read/write only (secure)

# Or make readable by group if needed
chmod 640 .env
```

#### Test Manual Loading
```bash
# Test if python-dotenv can load the file
python -c "
from dotenv import load_dotenv, find_dotenv
import os

# Find .env file
env_path = find_dotenv()
print(f'.env file found at: {env_path}')

# Load it
load_dotenv()

# Check if variables loaded
secret_key = os.getenv('SECRET_KEY')
print(f'SECRET_KEY loaded: {\"Yes\" if secret_key else \"No\"}')
"
```

#### Common Issues

**Issue 1: .env in wrong directory**
```bash
# ❌ Wrong - .env in subdirectory
project/
  src/
    .env  # Wrong location!
  pyproject.toml

# ✓ Correct - .env in project root
project/
  .env  # Correct location
  src/
  pyproject.toml
```

**Issue 2: .env.example instead of .env**
```bash
# Copy .env.example to .env
cp .env.example .env

# Then edit .env with your values
nano .env  # or vim, code, etc.
```

**Issue 3: Hidden file not visible**
```bash
# On Linux/macOS, files starting with . are hidden
# Use ls -a to see hidden files
ls -a | grep env
# Should show: .env .env.example

# On Windows, enable "Show hidden files" in File Explorer
```

**Issue 4: python-dotenv not installed**
```bash
# Install python-dotenv
pip install python-dotenv

# Verify installation
python -c "import dotenv; print(dotenv.__version__)"
```

**Verification:**
```bash
# Full test: Load .env and verify variables
python -c "
from dotenv import load_dotenv
import os

print('Before load_dotenv():')
print(f'  SECRET_KEY: {os.getenv(\"SECRET_KEY\")}')

load_dotenv()

print('\nAfter load_dotenv():')
print(f'  SECRET_KEY: {os.getenv(\"SECRET_KEY\", \"STILL NOT SET\")}')
print(f'  DATABASE_URL: {os.getenv(\"DATABASE_URL\", \"STILL NOT SET\")}')
"
```

---

### 5. Environment Variable Naming Errors

**Symptoms:**
- Variable set but application doesn't recognize it
- Configuration uses default values
- Typo in variable name

**Cause:**
Environment variable names are case-sensitive and must match exactly.

**Solution:**

#### Common Naming Mistakes
```env
# ❌ Wrong - typos or wrong case
SECERT_KEY=...           # Typo: SECERT instead of SECRET
Secret_Key=...           # Wrong case: should be all caps
DATABASE_URI=...         # Wrong name: should be DATABASE_URL
REDIS_URI=...            # Wrong name: should be REDIS_URL

# ✓ Correct - exact names from .env.example
SECRET_KEY=...
DATABASE_URL=...
REDIS_URL=...
```

#### Check Exact Variable Names
```bash
# List all valid variable names from .env.example
grep -E "^[A-Z_]+=" .env.example | cut -d= -f1 | sort

# Compare with your .env
grep -E "^[A-Z_]+=" .env | cut -d= -f1 | sort

# Find differences
diff <(grep -E "^[A-Z_]+=" .env.example | cut -d= -f1 | sort) \
     <(grep -E "^[A-Z_]+=" .env | cut -d= -f1 | sort)
```

#### Validate Against .env.example
```bash
# Use this script to check for typos
python -c "
import re

# Read expected variable names
with open('.env.example') as f:
    expected = set(re.findall(r'^([A-Z_]+)=', f.read(), re.MULTILINE))

# Read actual variable names
with open('.env') as f:
    actual = set(re.findall(r'^([A-Z_]+)=', f.read(), re.MULTILINE))

# Find typos (variables in .env not in .env.example)
typos = actual - expected
if typos:
    print('⚠️  Possible typos in .env:')
    for var in sorted(typos):
        print(f'  - {var}')
else:
    print('✓ All variable names match .env.example')

# Find missing required variables
required = {'SECRET_KEY', 'DATABASE_URL', 'REDIS_URL'}
missing = required - actual
if missing:
    print('\n✗ Missing required variables:')
    for var in sorted(missing):
        print(f'  - {var}')
"
```

**Verification:**
```bash
# Test specific variable is recognized
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Test exact variable name
var_name = 'SECRET_KEY'  # Change to test other variables
value = os.getenv(var_name)

if value:
    print(f'✓ {var_name} is set')
else:
    print(f'✗ {var_name} is NOT set - check spelling!')
"
```

---

### 6. Docker Environment Variable Issues

**Symptoms:**
- Variables work locally but not in Docker containers
- `.env` file exists but containers don't see variables
- Different behavior between `docker compose` and `docker run`

**Cause:**
Docker containers need explicit environment configuration via `docker-compose.yml` or `-e` flags.

**Solution:**

#### Using docker-compose.yml (Recommended)
```yaml
# docker-compose.yml
services:
  api:
    build: .
    env_file:
      - .env  # Load all variables from .env
    environment:
      # Override or set specific variables
      - DATABASE_URL=postgresql+asyncpg://pybase:pybase@postgres:5432/pybase
      - REDIS_URL=redis://redis:6379/0
    # Variables from .env are automatically available
```

#### Verify Variables in Container
```bash
# Check if container sees environment variables
docker compose exec api env | grep SECRET_KEY
# Should output: SECRET_KEY=<your_key>

# Test from Python inside container
docker compose exec api python -c "
import os
print('Variables in container:')
print(f'  SECRET_KEY: {\"SET\" if os.getenv(\"SECRET_KEY\") else \"NOT SET\"}')
print(f'  DATABASE_URL: {\"SET\" if os.getenv(\"DATABASE_URL\") else \"NOT SET\"}')
"
```

#### Important Docker-Specific Variables
```env
# In containers, use service names as hostnames (NOT localhost)

# ❌ Wrong - localhost doesn't work between containers
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase
REDIS_URL=redis://localhost:6379/0

# ✓ Correct - use Docker service names
DATABASE_URL=postgresql+asyncpg://pybase:pybase@postgres:5432/pybase
REDIS_URL=redis://redis:6379/0
S3_ENDPOINT_URL=http://minio:9000
```

#### Create Separate .env for Docker
```bash
# Option 1: Use .env.docker
cp .env.example .env.docker

# Edit with Docker-specific values
nano .env.docker

# Update docker-compose.yml
services:
  api:
    env_file:
      - .env.docker
```

#### Pass Variables at Runtime
```bash
# Pass individual variables
docker compose run -e SECRET_KEY=xyz api python -c "import os; print(os.getenv('SECRET_KEY'))"

# Load from .env file
docker compose --env-file .env up -d
```

**Verification:**
```bash
# Start container and verify all required variables are set
docker compose up -d api

# Check application logs for missing variable errors
docker compose logs api | grep -i "not set\|missing\|required"

# Should not show any missing variable errors
```

---

### 7. Quick Reference: Common Environment Variables

**Minimal Working Configuration:**
```env
# Absolute minimum to start PyBase
SECRET_KEY=<64_char_random_string>
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase
REDIS_URL=redis://localhost:6379/0
```

**Development Configuration:**
```env
# Basic setup for local development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
SECRET_KEY=<generate_unique_key>
DATABASE_URL=postgresql+asyncpg://pybase:pybase@localhost:5432/pybase
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=pybase
```

**Production Configuration:**
```env
# Secure production setup
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
SECRET_KEY=<strong_unique_production_key>
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db.example.com/pybase?sslmode=require
REDIS_URL=redis://:password@prod-redis.example.com:6379/0
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=<aws_access_key>
S3_SECRET_KEY=<aws_secret_key>
S3_BUCKET_NAME=pybase-prod
ENABLE_REGISTRATION=false  # Disable public registration
```

**Quick Validation Script:**
```bash
# Save as scripts/validate_env.py
python << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

required = {
    'SECRET_KEY': 'Cryptographic key for JWT tokens',
    'DATABASE_URL': 'PostgreSQL connection string',
    'REDIS_URL': 'Redis connection string'
}

optional = {
    'S3_ENDPOINT_URL': 'Object storage for file uploads',
    'WERK24_API_KEY': 'AI-powered drawing extraction',
    'TESSERACT_CMD': 'OCR for scanned PDFs',
    'MEILISEARCH_URL': 'Full-text search'
}

print('=== Required Variables ===')
all_set = True
for var, desc in required.items():
    value = os.getenv(var)
    if value:
        print(f'✓ {var:<20} {desc}')
    else:
        print(f'✗ {var:<20} {desc} - MISSING!')
        all_set = False

print('\n=== Optional Variables ===')
for var, desc in optional.items():
    value = os.getenv(var)
    status = '✓' if value else '○'
    print(f'{status} {var:<20} {desc}')

if all_set:
    print('\n✓ All required variables are set!')
else:
    print('\n✗ Missing required variables - application may not start')
    exit(1)
EOF
```

**See Also:**
- [.env.example](../.env.example) - Complete variable reference
- [Environment Variable Reference](#environment-variable-reference) - Full variable list
- [Application Startup Issues](#application-startup-issues) - Related startup problems

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

## Type Checking and LSP Setup

### Overview

PyBase uses strict type checking to catch errors before runtime. Setting up type checkers (mypy, basedpyright) and LSP (Language Server Protocol) in your IDE helps identify type errors, missing parameters, and API contract violations during development.

**Why This Matters:**
- Catches 40+ type errors found in extraction APIs (see [lsp-type-errors-critical.md](lsp-type-errors-critical.md))
- Prevents runtime failures from type mismatches
- Ensures API contract compliance
- Improves code quality and maintainability

---

### 1. Setting Up mypy (Recommended)

**What is mypy?**
mypy is Python's standard static type checker that validates type annotations.

**Installation:**
```bash
# Install mypy (included in dev dependencies)
pip install -e ".[dev]"

# Or install standalone
pip install mypy
```

**Configuration:**
PyBase includes a `pyproject.toml` with mypy settings. Verify it exists:

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_reexport = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true
```

**Running mypy:**
```bash
# Check entire codebase
mypy src/pybase

# Check specific file
mypy src/pybase/api/v1/extraction.py

# Check with verbose output
mypy --show-error-codes --pretty src/pybase
```

**Expected Output (Clean):**
```
Success: no issues found in 145 source files
```

**With Errors:**
```
src/pybase/api/v1/extraction.py:169: error: Missing positional arguments "source_file", "source_type" in call to "extract"  [call-arg]
src/pybase/api/v1/records.py:65: error: Incompatible return value type (got "Record", expected "RecordResponse")  [return-value]
Found 40 errors in 3 files (checked 145 source files)
```

**Verification:**
```bash
# Run mypy and check exit code
mypy src/pybase && echo "✓ Type checking passed" || echo "✗ Type errors found"
```

---

### 2. Setting Up basedpyright (Modern Alternative)

**What is basedpyright?**
basedpyright is a community-maintained fork of Pyright with enhanced type checking. It's faster than mypy and provides better IDE integration.

**Installation:**
```bash
# Install basedpyright
pip install basedpyright

# Or via npm (if you have Node.js)
npm install -g basedpyright
```

**Configuration:**
Create or verify `pyproject.toml` has basedpyright settings:

```toml
# pyproject.toml
[tool.basedpyright]
pythonVersion = "3.11"
typeCheckingMode = "standard"  # or "strict" for maximum safety
reportMissingTypeStubs = false
reportUnknownMemberType = false
reportUnknownArgumentType = false
reportUnknownVariableType = false
include = ["src/pybase"]
exclude = ["**/__pycache__", "**/.venv"]
```

**Running basedpyright:**
```bash
# Check entire codebase
basedpyright src/pybase

# Check specific file
basedpyright src/pybase/api/v1/extraction.py

# Watch mode (re-check on file changes)
basedpyright --watch src/pybase
```

**Verification:**
```bash
basedpyright --version
# Expected: basedpyright 1.x.x
```

---

### 3. LSP Setup in VSCode

**What is LSP?**
Language Server Protocol provides real-time type checking, autocomplete, and error highlighting in your editor.

**Option A: Pylance (Microsoft - Uses Pyright)**

1. **Install Extension:**
   - Open VSCode
   - Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
   - Search for "Pylance"
   - Click Install

2. **Configure Settings:**
Create `.vscode/settings.json`:
```json
{
  "python.languageServer": "Pylance",
  "python.analysis.typeCheckingMode": "standard",
  "python.analysis.diagnosticMode": "workspace",
  "python.analysis.autoImportCompletions": true,
  "python.analysis.inlayHints.functionReturnTypes": true,
  "python.analysis.inlayHints.variableTypes": true
}
```

3. **Verify:**
   - Open `src/pybase/api/v1/extraction.py`
   - You should see red squiggly lines under type errors
   - Hover to see error messages

**Option B: Pyright LSP (Community)**

1. **Install Extension:**
   - Search for "Pyright" in VSCode extensions
   - Or use basedpyright extension for enhanced version

2. **Configure:**
```json
{
  "python.languageServer": "Pyright",
  "pyright.disableLanguageServices": false,
  "pyright.disableOrganizeImports": false
}
```

**Option C: mypy LSP (via mypy-ls)**

```bash
# Install mypy language server
pip install python-lsp-server python-lsp-mypy

# Install VSCode extension: "Python LSP Server"
```

**Verification:**
```bash
# Check if LSP is working
# 1. Open a Python file with type errors
# 2. You should see:
#    - Red squiggly lines under errors
#    - Error count in status bar
#    - Hover tooltips with error details
```

---

### 4. LSP Setup in Other Editors

#### Neovim / Vim

```lua
-- Using nvim-lspconfig
require('lspconfig').pyright.setup{
  settings = {
    python = {
      analysis = {
        typeCheckingMode = "standard",
        autoSearchPaths = true,
        useLibraryCodeForTypes = true
      }
    }
  }
}
```

#### Emacs

```elisp
;; Using lsp-mode
(use-package lsp-pyright
  :ensure t
  :hook (python-mode . (lambda ()
                          (require 'lsp-pyright)
                          (lsp))))
```

#### Sublime Text

```bash
# Install LSP package
# Package Control -> Install Package -> LSP
# Package Control -> Install Package -> LSP-pyright
```

---

### 5. Common Type Checking Issues

#### Issue 1: Missing Type Stubs for Third-Party Libraries

**Symptoms:**
```
error: Library stubs not installed for "meilisearch"  [import]
note: Hint: "python3 -m pip install types-meilisearch"
```

**Solution:**
```bash
# Install type stubs
pip install types-meilisearch types-redis types-requests

# Or use mypy's stubgen to generate stubs
stubgen -p meilisearch -o stubs/
```

#### Issue 2: Return Type Mismatch

**Symptoms:**
```
src/pybase/api/v1/records.py:65: error: Incompatible return value type (got "Record", expected "RecordResponse")
```

**Cause:**
Returning SQLAlchemy model instead of Pydantic schema.

**Solution:**
```python
# ❌ Wrong - returns ORM model
async def create_record(...) -> RecordResponse:
    record = Record(...)
    db.add(record)
    await db.commit()
    return record  # Type error!

# ✓ Correct - convert to schema
async def create_record(...) -> RecordResponse:
    record = Record(...)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return RecordResponse.model_validate(record)  # Correct!
```

#### Issue 3: Missing Function Parameters

**Symptoms:**
```
src/pybase/api/v1/extraction.py:169: error: Missing positional arguments "source_file", "source_type" in call to "extract"
```

**Cause:**
Method signature doesn't match implementation.

**Solution:**
```python
# Check method definition
class PDFExtractor:
    async def extract(self, source_file: Path, source_type: str) -> ExtractionResult:
        ...

# ❌ Wrong - missing parameters
result = extractor.extract()

# ✓ Correct - provide all required parameters
result = await extractor.extract(
    source_file=Path("document.pdf"),
    source_type="pdf"
)
```

#### Issue 4: Non-existent Attributes

**Symptoms:**
```
error: Cannot access attribute "extract" for class "DXFParser"
note: "extract" is not a known member of "DXFParser"
```

**Cause:**
Using wrong method name or attribute doesn't exist.

**Solution:**
```python
# Check class definition
class DXFParser:
    async def parse(self, file_path: Path) -> DXFParseResult:  # Method is "parse", not "extract"
        ...

# ✓ Correct - use right method name
result = await dxf_parser.parse(file_path=Path("drawing.dxf"))
```

#### Issue 5: Invariant Type Parameter (List vs Sequence)

**Symptoms:**
```
error: Argument of type "list[Record]" cannot be assigned to parameter "items" of type "list[RecordResponse]"
note: "list" is invariant; consider using "Sequence" which is covariant
```

**Cause:**
Using `list` in type hint when you need covariance.

**Solution:**
```python
from collections.abc import Sequence

# ❌ Wrong - list is invariant
class RecordListResponse(BaseModel):
    items: list[RecordResponse]

# ✓ Correct - Sequence is covariant
class RecordListResponse(BaseModel):
    items: Sequence[RecordResponse]

# Or convert at call site
RecordListResponse(
    items=[RecordResponse.model_validate(r) for r in records]
)
```

---

### 6. Integrating Type Checks into Development Workflow

#### Pre-commit Hooks

Add type checking to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--strict, --show-error-codes]
```

Install hooks:
```bash
pre-commit install
```

#### CI/CD Integration

Add to GitHub Actions (`.github/workflows/type-check.yml`):

```yaml
name: Type Check

on: [push, pull_request]

jobs:
  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run mypy
        run: mypy src/pybase
      - name: Run basedpyright
        run: basedpyright src/pybase
```

#### Make Targets

Add to `Makefile`:

```makefile
.PHONY: type-check
type-check:
	mypy src/pybase
	basedpyright src/pybase

.PHONY: type-check-strict
type-check-strict:
	mypy --strict src/pybase
```

Usage:
```bash
make type-check
```

---

### 7. Troubleshooting Type Checker Issues

#### Issue: Type Checker Not Finding Modules

**Symptoms:**
```
error: Cannot find implementation or library stub for module named "pybase"
```

**Solution:**
```bash
# Ensure package is installed in editable mode
pip install -e .

# Verify PYTHONPATH
echo $PYTHONPATH

# Add to .env if needed
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

#### Issue: Conflicting Type Checkers

**Symptoms:**
Different errors from mypy vs basedpyright.

**Solution:**
Choose one as primary:
```bash
# Use mypy as source of truth
mypy src/pybase

# Or use basedpyright
basedpyright src/pybase

# Configure IDE to match (use same checker in LSP)
```

#### Issue: Too Many Errors to Fix at Once

**Solution:**
Use incremental strictness:

```toml
# pyproject.toml - Start lenient
[tool.mypy]
check_untyped_defs = false
disallow_untyped_defs = false

# Gradually enable stricter checks
warn_return_any = true
warn_unused_configs = true
```

Or use selective ignoring:
```python
# Ignore specific error types temporarily
result = extractor.extract()  # type: ignore[call-arg]
```

---

### 8. Resources

**Official Documentation:**
- [mypy documentation](https://mypy.readthedocs.io/)
- [basedpyright documentation](https://docs.basedpyright.com/)
- [Pylance documentation](https://github.com/microsoft/pylance-release)

**PyBase-Specific:**
- [lsp-type-errors-critical.md](lsp-type-errors-critical.md) - Known type errors in codebase
- [Code Standards](code-standards.md) - Type annotation guidelines

**Type Checking Best Practices:**
- Use `strict = true` in mypy for new code
- Add return type annotations to all functions
- Use Pydantic schemas for API boundaries
- Prefer `Sequence` over `list` for covariance
- Convert ORM models to schemas at API layer

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
