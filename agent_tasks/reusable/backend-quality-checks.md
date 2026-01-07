# Backend Quality Checks

**Run these checks before completing backend work.**

## Format Code (Fixes ~80% of lint errors)

```bash
cd backend && uv run ruff format .
```

## Linting & Type Checking

```bash
task lint:backend
```

Runs:
- **Ruff**: Fast Python linter
- **Pyright**: Strict type checking (no `Any` allowed)

## Testing

```bash
task test:backend
```

Runs all tests with coverage reports.

## Quick Validation

```bash
cd backend && uv run ruff format . && task lint:backend && task test:backend
```

## Common Issues

| Issue | Fix |
|-------|-----|
| "Would reformat" | Run `uv run ruff format .` |
| Type error `Any` | Add explicit type hints |
| Missing import | Check error, add import |
| Test failures | Fix code/test, re-run |

## Requirements

- Complete type hints on all functions
- Docstrings for public APIs
- Tests for new functionality
- No `Any` type (except rare, documented cases)
