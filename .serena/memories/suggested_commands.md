# Suggested Commands

## Development Server
```bash
# Start with Docker
docker compose up -d

# Start FastAPI dev server
uvicorn pybase.main:app --reload --host 0.0.0.0 --port 8000
```

## Database
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Query database (debugging)
psql postgresql://pybase:pybase@localhost:5432/pybase
```

## Testing
```bash
# Run all tests
pytest

# With coverage
pytest --cov=pybase --cov-report=html

# Specific test types
pytest tests/unit/
pytest tests/integration/
pytest -m "not slow"
```

## Code Quality
```bash
# Format code
black src tests

# Lint with auto-fix
ruff check src tests --fix

# Type checking
mypy src

# Run all pre-commit hooks
pre-commit run --all-files
```

## Installation
```bash
# Full install with all deps
pip install -e ".[all]"

# Dev only
pip install -e ".[dev]"
```

## Windows-specific Utils
```bash
# List files
dir /B
Get-ChildItem

# Search in files
Select-String -Path "*.py" -Pattern "pattern"

# Git operations
git status
git diff
git log --oneline -10
```
