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
- uv (Install with `pip install uv` or see [uv documentation](https://docs.astral.sh/uv/))

### Installation

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
uv pip install -e ".[dev]"
```

### Running the Server

```bash
uvicorn papertrade.main:app --reload
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

# Run type checker
pyright

# Run tests
pytest

# Run tests with coverage
pytest --cov=papertrade --cov-report=html
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
