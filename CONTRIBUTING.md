# Contributing to PyBase

Thank you for your interest in contributing to PyBase! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Development Environment Setup](#development-environment-setup)
  - [Environment Configuration](#environment-configuration)
- [Development Workflow](#development-workflow)
  - [Branching Strategy](#branching-strategy)
  - [Making Changes](#making-changes)
  - [Commit Messages](#commit-messages)
- [Code Standards](#code-standards)
  - [General Principles](#general-principles)
  - [Python Code Style](#python-code-style)
  - [Frontend Code Style](#frontend-code-style)
  - [File and Directory Conventions](#file-and-directory-conventions)
- [Code Quality Tools](#code-quality-tools)
  - [Pre-commit Hooks](#pre-commit-hooks)
  - [Black (Code Formatter)](#black-code-formatter)
  - [Ruff (Linter)](#ruff-linter)
  - [MyPy (Type Checker)](#mypy-type-checker)
  - [Security Tools](#security-tools)
- [Testing](#testing)
  - [Running Tests](#running-tests)
  - [Writing Tests](#writing-tests)
  - [Coverage Requirements](#coverage-requirements)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
  - [PR Guidelines](#pr-guidelines)
  - [PR Description Template](#pr-description-template)
  - [Code Review Process](#code-review-process)
- [Engineering-Specific Contributions](#engineering-specific-contributions)
  - [CAD/PDF Extraction](#cadpdf-extraction)
  - [Field Type Development](#field-type-development)
- [Questions and Help](#questions-and-help)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please be respectful, inclusive, and professional in all interactions.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** (Python 3.12 is also supported)
- **Git** for version control
- **Docker & Docker Compose** for running PostgreSQL, Redis, and MinIO
- **PostgreSQL 15+** (can run via Docker)
- **Redis 7+** (can run via Docker)

### Development Environment Setup

1. **Fork and Clone the Repository**

   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/pybase.git
   cd pybase
   ```

2. **Create a Virtual Environment**

   ```bash
   # Create virtual environment
   python3.11 -m venv venv

   # Activate virtual environment
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   # Install all dependencies including development tools
   pip install -e ".[all]"
   ```

4. **Install Pre-commit Hooks**

   ```bash
   # Install pre-commit hooks for code quality checks
   pre-commit install
   ```

5. **Start Docker Services**

   ```bash
   # Start PostgreSQL, Redis, and MinIO
   docker compose up -d
   ```

6. **Run Database Migrations**

   ```bash
   # Apply all database migrations
   alembic upgrade head
   ```

7. **Verify Installation**

   ```bash
   # Run tests to verify setup
   pytest

   # Start development server
   uvicorn pybase.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API should now be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive API documentation.

### Environment Configuration

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

## Development Workflow

### Branching Strategy

- **main**: Production-ready code
- **feature/**: Feature branches (e.g., `feature/add-gantt-view`)
- **fix/**: Bug fix branches (e.g., `fix/field-validation-error`)
- **docs/**: Documentation updates (e.g., `docs/api-reference`)
- **refactor/**: Code refactoring (e.g., `refactor/extraction-module`)

### Making Changes

1. **Configure Upstream Remote** (if not already done)

   ```bash
   # Add the upstream repository (the official PyBase repo)
   git remote add upstream https://github.com/pybase/pybase.git

   # Verify remotes
   git remote -v
   ```

2. **Create a Feature Branch**

   ```bash
   # Update your local main branch
   git checkout main
   git pull upstream main

   # Create and checkout a new feature branch
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**

   - Follow the [Code Standards](#code-standards)
   - Write tests for new functionality
   - Update documentation as needed
   - Run pre-commit hooks: `pre-commit run --all-files`

4. **Test Your Changes**

   ```bash
   # Run all tests
   pytest

   # Run tests with coverage
   pytest --cov=pybase --cov-report=html

   # Run specific test file
   pytest tests/test_fields.py
   ```

### Commit Messages

Use clear, descriptive commit messages following this format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
# Good commit messages
git commit -m "feat(fields): add GD&T field type with tolerance validation"
git commit -m "fix(extraction): handle malformed DXF layer names"
git commit -m "docs(api): add examples for record creation endpoints"
git commit -m "test(services): add unit tests for table service"

# Keep commits focused and atomic
git commit -m "refactor(models): split large models into separate files"
```

## Code Standards

### General Principles

1. **YAGNI (You Aren't Gonna Need It)**
   - Do not implement features or code that are not currently required
   - Avoid speculative generality and over-engineering

2. **KISS (Keep It Simple, Stupid)**
   - Favor simple, readable solutions over complex ones
   - If a solution feels too complex, it probably is

3. **DRY (Don't Repeat Yourself)**
   - Eliminate duplication by abstracting common logic
   - However, avoid premature abstraction

### Python Code Style

- **Style Guide**: Follow PEP 8
- **Line Length**: Maximum 100 characters
- **Formatting**: Use Black (configured in `pyproject.toml`)
- **Linting**: Use Ruff for fast, comprehensive linting
- **Type Hints**: Use type hints for all function signatures and variables
- **Type Checking**: Use MyPy in strict mode
- **Async/Await**: Use `async`/`await` for all I/O-bound operations

**Example:**

```python
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

async def get_record_by_id(
    db: AsyncSession,
    record_id: UUID,
    include_deleted: bool = False
) -> Optional[Record]:
    """
    Retrieve a record by ID.

    Args:
        db: Database session
        record_id: Unique identifier of the record
        include_deleted: Whether to include soft-deleted records

    Returns:
        Record if found, None otherwise
    """
    query = select(Record).where(Record.id == record_id)
    if not include_deleted:
        query = query.where(Record.deleted_at.is_(None))
    result = await db.execute(query)
    return result.scalar_one_or_none()
```

### Frontend Code Style

- **Framework**: React 18 with TypeScript
- **Components**: Use `shadcn/ui` for UI components
- **State Management**:
  - Server state: TanStack Query (React Query)
  - Client state: Recoil or Zustand
- **Styling**: Tailwind CSS
- **Testing**: Vitest for unit tests, Playwright for E2E tests

### File and Directory Conventions

- **Naming**: Use `kebab-case` for all file and directory names
  - ✅ `user-service.py`, `grid-view.tsx`, `pdf-extractor.py`
  - ❌ `UserService.py`, `GridView.tsx`, `PDFExtractor.py`

- **File Size**: Keep files under **200 lines** of code when possible
  - If a file exceeds 200 lines, consider splitting into smaller modules

- **Organization**:
  - API routes: `src/pybase/api/v1/`
  - Business logic: `src/pybase/services/`
  - Database models: `src/pybase/models/`
  - Pydantic schemas: `src/pybase/schemas/`
  - Field types: `src/pybase/fields/`
  - Extraction logic: `src/pybase/extraction/`

## Code Quality Tools

### Pre-commit Hooks

Pre-commit hooks automatically run code quality checks before each commit.

**Installation:**

```bash
pre-commit install
```

**Manual Execution:**

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

**Hooks Configured:**
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON/TOML validation
- Large file detection
- Merge conflict detection
- Private key detection
- Black formatting
- Ruff linting
- MyPy type checking
- Bandit security scanning
- Secrets detection

### Black (Code Formatter)

Black is an opinionated code formatter that ensures consistent code style.

**Configuration:** (`pyproject.toml`)
- Line length: 100
- Target versions: Python 3.11, 3.12

**Usage:**

```bash
# Format all Python files
black src tests

# Check formatting without making changes
black --check src tests

# Format specific file
black src/pybase/models/user.py
```

### Ruff (Linter)

Ruff is a fast Python linter that replaces Flake8, isort, and more.

**Configuration:** (`pyproject.toml`)
- Line length: 100
- Enabled rules: E, F, W, I, N, UP, S, B, A, C4, DTZ, ISC, ICN, PIE, PT, Q, RSE, RET, SIM, TID, ARG, PTH, PD, PGH, PL, RUF

**Usage:**

```bash
# Lint all files
ruff check src tests

# Lint with auto-fix
ruff check src tests --fix

# Lint specific file
ruff check src/pybase/api/v1/records.py
```

### MyPy (Type Checker)

MyPy performs static type checking to catch type-related errors.

**Configuration:** (`pyproject.toml`)
- Strict mode enabled
- Plugins: pydantic.mypy, sqlalchemy.ext.mypy.plugin

**Usage:**

```bash
# Type check all files
mypy src

# Type check specific module
mypy src/pybase/services

# Generate coverage report
mypy --html-report mypy-report src
```

### Security Tools

**Bandit** - Security linting for Python code

```bash
# Run security scan
bandit -c pyproject.toml -r src
```

**detect-secrets** - Prevent secrets from being committed

```bash
# Scan for secrets
detect-secrets scan

# Update baseline
detect-secrets scan --baseline .secrets.baseline
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=pybase --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_fields.py

# Run specific test function
pytest tests/test_fields.py::test_dimension_field_validation

# Run tests matching a keyword
pytest -k "field"

# Run tests with verbose output
pytest -v

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

### Writing Tests

- **Location**: Place tests in the `tests/` directory, mirroring the `src/pybase/` structure
- **Naming**: Test files should start with `test_` (e.g., `test_user_service.py`)
- **Test Functions**: Test function names should start with `test_` (e.g., `test_create_user`)
- **Fixtures**: Use pytest fixtures for setup and teardown
- **Async Tests**: Use `pytest-asyncio` for async test functions

**Example:**

```python
import pytest
from uuid import uuid4
from pybase.services.record_service import RecordService
from pybase.schemas.record import RecordCreate

@pytest.mark.asyncio
async def test_create_record(db_session, sample_table):
    """Test record creation with valid data."""
    service = RecordService(db_session)
    record_data = RecordCreate(
        table_id=sample_table.id,
        fields={"name": "Test Record", "value": 42}
    )

    record = await service.create_record(record_data)

    assert record.id is not None
    assert record.fields["name"] == "Test Record"
    assert record.fields["value"] == 42

@pytest.mark.asyncio
async def test_create_record_invalid_field(db_session, sample_table):
    """Test record creation with invalid field type."""
    service = RecordService(db_session)
    record_data = RecordCreate(
        table_id=sample_table.id,
        fields={"number_field": "not a number"}  # Should be int
    )

    with pytest.raises(ValidationError):
        await service.create_record(record_data)
```

### Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Critical Paths**: 90%+ coverage for services, models, and business logic
- **View Coverage Report**: After running tests with coverage, open `htmlcov/index.html`

## Documentation

### When to Update Documentation

- Adding new features or endpoints
- Changing existing functionality
- Adding new field types or extraction formats
- Updating configuration or environment variables
- Making architectural changes

### Documentation Files

- **README.md**: Project overview, quick start, features
- **docs/**: Detailed documentation
  - `project-overview-pdr.md`: Product requirements and design
  - `system-architecture.md`: Architecture diagrams and decisions
  - `code-standards.md`: Coding conventions and standards
  - `codebase-summary.md`: Summary of the codebase structure
  - `project-roadmap.md`: Future plans and development roadmap
  - `deployment-guide.md`: Instructions for deploying PyBase
  - `design-guidelines.md`: UI/UX design principles and guidelines
  - `api.md`: API reference and examples
  - `fields.md`: Field type documentation
  - `extraction.md`: CAD/PDF extraction guide
- **Docstrings**: All public functions, classes, and modules should have docstrings

### Docstring Format

Use Google-style docstrings:

```python
from typing import Optional

def extract_tables(pdf_path: str, pages: Optional[list[int]] = None) -> list[Table]:
    """
    Extract tables from a PDF file.

    Args:
        pdf_path: Path to the PDF file
        pages: Specific pages to extract from (None = all pages)

    Returns:
        List of extracted tables with cells and formatting

    Raises:
        FileNotFoundError: If the PDF file does not exist
        PDFExtractionError: If extraction fails

    Example:
        >>> tables = extract_tables("drawing.pdf", pages=[1, 2])
        >>> print(tables[0].cells)
    """
```

## Pull Request Process

### PR Guidelines

1. **One PR = One Feature/Fix**
   - Keep PRs focused on a single feature, bug fix, or improvement
   - Avoid mixing unrelated changes

2. **Update Documentation**
   - Update relevant documentation in the same PR
   - Add docstrings for new functions/classes

3. **Add Tests**
   - Include unit tests for new functionality
   - Ensure all tests pass
   - Maintain or improve code coverage

4. **Pass All Checks**
   - Pre-commit hooks must pass
   - All CI checks must pass (linting, type checking, tests)
   - No merge conflicts with main branch

5. **Link Issues**
   - Reference related issues in the PR description (e.g., "Fixes #123")

### PR Description Template

```markdown
## Description

Brief description of what this PR does and why.

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Changes Made

- List the specific changes made
- Include technical details as needed
- Mention any architectural decisions

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

**Test Coverage:**
- Current coverage: XX%
- Files changed: list key files

**Manual Testing:**
- Describe manual testing steps
- Include screenshots if applicable

## Documentation

- [ ] Code comments added/updated
- [ ] Docstrings added/updated
- [ ] README.md updated (if needed)
- [ ] docs/ updated (if needed)

## Checklist

- [ ] Code follows project style guidelines
- [ ] Pre-commit hooks pass
- [ ] All tests pass
- [ ] No console.log/print debugging statements
- [ ] Documentation updated
- [ ] No merge conflicts

## Related Issues

Fixes #(issue number)
Relates to #(issue number)

## Screenshots (if applicable)

[Add screenshots here]

## Additional Notes

Any additional context or notes for reviewers.
```

### Code Review Process

1. **Automated Checks**
   - CI runs automated checks (linting, type checking, tests)
   - All checks must pass before review

2. **Peer Review**
   - At least one approving review required
   - Reviewers check for:
     - Code quality and style
     - Test coverage
     - Documentation completeness
     - Security considerations
     - Performance implications

3. **Address Feedback**
   - Respond to all review comments
   - Make requested changes or discuss alternatives
   - Re-request review after updates

4. **Merge**
   - Maintainers will merge after approval
   - Squash merge for feature branches
   - Delete branch after merge

## Engineering-Specific Contributions

### CAD/PDF Extraction

PyBase includes specialized features for extracting data from engineering files. When contributing to extraction features:

**Supported Formats:**
- **PDF**: Table extraction, text parsing, OCR (via pytesseract)
- **DXF**: AutoCAD files (layers, blocks, dimensions, text)
- **IFC**: Building Information Modeling files
- **STEP**: 3D CAD files (geometry, assemblies, metadata)

**Adding New Extraction Formats:**

1. Create parser in `src/pybase/extraction/`
2. Implement extraction interface
3. Add format-specific logic and validation
4. Create comprehensive tests with sample files
5. Update documentation in `docs/extraction.md`

**Example Structure:**

```python
# src/pybase/extraction/cad/new_format_parser.py

from typing import Any
from pathlib import Path

class NewFormatParser:
    """Parser for NEW_FORMAT CAD files."""

    def __init__(self):
        """Initialize parser with configuration."""
        pass

    async def parse(self, file_path: Path) -> dict[str, Any]:
        """
        Parse NEW_FORMAT file and extract data.

        Args:
            file_path: Path to the NEW_FORMAT file

        Returns:
            Extracted data as dictionary
        """
        # Implementation
        pass

    async def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from file."""
        pass
```

### Field Type Development

When adding new field types (especially engineering-specific ones):

1. **Create Field Handler**
   - Location: `src/pybase/fields/` or `src/pybase/fields/engineering/`
   - Inherit from `BaseFieldHandler`

2. **Implement Required Methods**
   - `validate()`: Validate field value
   - `serialize()`: Convert to database format
   - `deserialize()`: Convert from database format

3. **Add Tests**
   - Test validation logic
   - Test edge cases
   - Test serialization/deserialization

4. **Update Documentation**
   - Add to `docs/fields.md`
   - Include usage examples

**Example:**

```python
# src/pybase/fields/engineering/material.py

import json
from typing import Any
from src.pybase.fields.base import BaseFieldHandler

class MaterialFieldHandler(BaseFieldHandler):
    """Handler for material specification fields."""

    field_type = "material"

    async def validate(self, value: Any) -> dict[str, Any]:
        """
        Validate material specification.

        Expected format:
        {
            "name": "Steel 4140",
            "grade": "AISI 4140",
            "properties": {
                "tensile_strength": 655,  # MPa
                "hardness": "HRC 28-32"
            }
        }
        """
        if not isinstance(value, dict):
            raise ValueError("Material field must be a dictionary")

        if "name" not in value:
            raise ValueError("Material name is required")

        return value

    async def serialize(self, value: dict[str, Any]) -> str:
        """Serialize to JSON for database storage."""
        return json.dumps(value)

    async def deserialize(self, value: str) -> dict[str, Any]:
        """Deserialize from database JSON."""
        return json.loads(value)
```

## Questions and Help

### Getting Help

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Search [existing issues](https://github.com/pybase/pybase/issues) for similar questions
- **Discussions**: Use [GitHub Discussions](https://github.com/pybase/pybase/discussions) for questions
- **Discord**: Join our Discord community (link in README)

### Reporting Bugs

When reporting bugs, include:
- PyBase version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/stack traces
- Minimal reproducible example

### Suggesting Features

When suggesting features:
- Check if it already exists or is planned
- Describe the use case and problem it solves
- Provide examples or mockups if applicable
- Consider if it fits PyBase's scope and architecture

---

Thank you for contributing to PyBase! Your efforts help make this project better for everyone. 🚀
