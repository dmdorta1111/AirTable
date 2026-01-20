# Code Standards

## General Principles

### 1. YAGNI (You Aren't Gonna Need It)
Do not implement features or code that are not currently required. Avoid speculative generality and over-engineering.

### 2. KISS (Keep It Simple, Stupid)
Favor simple, readable solutions over complex, "clever" ones. If a solution feels too complex, it probably is.

### 3. DRY (Don't Repeat Yourself)
Eliminate duplication by abstracting common logic into reusable functions, components, or services. However, avoid premature abstraction.

## File & Directory Conventions
- **Naming**: Use `kebab-case` for all file and directory names (e.g., `user-service.py`, `grid-view.tsx`).
- **File Size**: Keep files under **200 lines** whenever possible. Large files should be split into smaller, focused modules.
- **Organization**:
  - API routes in `src/pybase/api/`
  - Business logic in `src/pybase/services/`
  - Models in `src/pybase/models/`
  - Schemas in `src/pybase/schemas/`

## Python Standards
- **Style**: Adhere to PEP 8. Use `black` for formatting and `ruff` for linting.
- **Typing**: Use Type Hints for all function signatures and variable declarations. Run `mypy` for static type checking.
- **Async**: Use `async`/`await` for all I/O bound operations (database, redis, external APIs).

## Frontend Standards
- **Framework**: React 18 with TypeScript.
- **Components**: Use `shadcn/ui` for UI components. Follow the atomic design pattern or a modular component structure.
- **State Management**: 
  - Server state: TanStack Query (React Query).
  - Client state: Recoil or Zustand.
- **Styling**: Tailwind CSS.

## Testing Standards
- **Backend**: Use `pytest`. Aim for high coverage of services and API endpoints.
- **Frontend**: Use Vitest for unit tests and Playwright for E2E tests.
- **Verification**: All code examples in documentation must be verified and working.

## Git Workflow
- **Commits**: Use concise, descriptive commit messages.
- **PRs**: Keep PRs focused on a single feature or bug fix. Include tests and documentation updates.
