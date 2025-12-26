# PaperTrade Backend

Backend API for the PaperTrade stock market emulation platform.

## Architecture

This backend follows Clean Architecture principles with clear separation of concerns:

```
src/papertrade/
├── domain/           # Pure business logic (entities, value objects)
├── application/      # Use cases (commands, queries)
├── adapters/
│   ├── inbound/      # HTTP routers, CLI commands
│   └── outbound/     # Repository implementations
└── infrastructure/   # Database config, external services
```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- uv (Install with `curl -LsSf https://astral.sh/uv/install.sh | sh` or see [uv documentation](https://docs.astral.sh/uv/))

### Installation

```bash
# uv will automatically create and use a virtual environment
# Use --extra dev to include development dependencies
uv sync --dev
```

### Running the Server

```bash
# If you activated the virtual environment manually
uvicorn papertrade.main:app --reload

# Or use uv run to automatically use the virtual environment
uv run uvicorn papertrade.main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Health check: http://localhost:8000/health
- OpenAPI docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Code Quality

```bash
# Run linter
ruff check .
# Or with uv: uv run ruff check .

# Run type checker
pyright
# Or with uv: uv run pyright

# Run tests
pytest
# Or with uv: uv run pytest

# Run tests with coverage
pytest --cov=papertrade --cov-report=html
# Or with uv: uv run pytest --cov=papertrade --cov-report=html
```

## Project Structure

- `src/papertrade/` - Main application code
- `tests/` - Test suite
  - `unit/` - Unit tests (domain and application logic)
  - `integration/` - Integration tests (API, database)
- `pyproject.toml` - Project configuration and dependencies

## Technology Stack

- **Framework**: FastAPI
- **ORM**: SQLModel
- **Type Checking**: Pyright (strict mode)
- **Linting**: Ruff
- **Testing**: Pytest
