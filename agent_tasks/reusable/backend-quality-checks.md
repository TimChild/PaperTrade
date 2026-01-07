# Backend Quality Checks

**Run these checks before completing backend work to catch issues early.**

## Format Code (Fixes 80% of lint errors)

```bash
cd backend && uv run ruff format .
```

This auto-formats Python code to match the project style (88 char line length, PEP 8).

## Linting & Type Checking

Run the CI validation task:
```bash
task lint:backend
```

This runs:
- **Ruff**: Fast Python linter
- **Pyright**: Strict type checking (no `Any` types allowed)

## Testing

Run the full test suite with coverage:
```bash
task test:backend
```

This runs:
- All unit tests
- All integration tests
- Generates coverage reports (HTML, XML, terminal)

## Quick Validation

Run all backend quality checks at once:
```bash
cd backend && uv run ruff format . && task lint:backend && task test:backend
```

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "Would reformat" error | Run `uv run ruff format .` |
| Type error `Any` not allowed | Add explicit type hints |
| Missing import | Check error message, add proper import |
| Test failures | Fix code or test, then re-run |

## Requirements

- **Type hints**: All functions must have complete type hints
- **Docstrings**: Public APIs need docstrings
- **Tests**: New functionality requires tests
- **No `Any`**: No `Any` type except rare, documented cases
