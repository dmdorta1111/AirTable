# Code Style & Conventions

## Formatting
- **Black**: Line length 100, Python 3.11+ target
- **Ruff**: Fast linter with many enabled rules (E, W, F, I, B, C4, UP, etc.)
- Config in `pyproject.toml`

## Type Hints
- MyPy strict mode enabled
- All functions require type annotations
- Use `from __future__ import annotations` for forward refs

## File Naming
- Use kebab-case for files: `dxf-parser.py`, `table-extractor.py`
- Long descriptive names preferred for LLM tooling

## File Size
- Keep files under 200 lines
- Split into focused modules
- Use composition over inheritance

## Imports
- isort via Ruff
- Known first-party: `pybase`
- No force-single-line

## Docstrings
- Required for public functions/classes
- Google-style docstrings preferred

## Error Handling
- Use structured error responses with proper HTTP codes
- Try/catch with specific exceptions
- Cover security standards (OWASP)

## Patterns
- **API**: FastAPI routes in `src/pybase/api/v1/`
- **Models**: SQLAlchemy in `src/pybase/models/`
- **Schemas**: Pydantic in `src/pybase/schemas/`
- **Services**: Business logic in `src/pybase/services/`
- **Fields**: Base handler pattern in `src/pybase/fields/`
