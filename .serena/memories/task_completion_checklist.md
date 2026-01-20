# Task Completion Checklist

Before marking a task as complete, ensure:

## Code Quality
- [ ] Run `black src tests` - formatting
- [ ] Run `ruff check src tests --fix` - linting
- [ ] Run `mypy src` - type checking
- [ ] No syntax errors, code compiles

## Testing
- [ ] Run `pytest` - all tests pass
- [ ] Add tests for new functionality
- [ ] Don't ignore failing tests
- [ ] No mocks/fakes just to pass tests

## Pre-commit
- [ ] Run `pre-commit run --all-files`
- [ ] No secrets or credentials in code
- [ ] No .env files committed

## Documentation
- [ ] Update docstrings for new public APIs
- [ ] Update `./docs/` if architecture changed
- [ ] Update roadmap if milestone reached

## Git
- [ ] Conventional commit messages
- [ ] No AI references in commits
- [ ] Focused, clean commits
