# Task 001: Setup Backend Project Scaffolding

## Objective
Create the initial backend project structure with FastAPI, SQLModel, and proper tooling configuration.

## Context
This is Phase 0 work - establishing the foundation before implementing features. The backend should follow Clean Architecture principles as outlined in `project_strategy.md`.

## Requirements

### Project Structure
Create the following directory structure:
```
backend/
├── src/
│   └── papertrade/
│       ├── __init__.py
│       ├── domain/           # Pure domain logic
│       │   ├── __init__.py
│       │   ├── entities/
│       │   └── value_objects/
│       ├── application/      # Use cases
│       │   ├── __init__.py
│       │   ├── commands/
│       │   └── queries/
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── inbound/      # FastAPI routers
│       │   └── outbound/     # Repository implementations
│       └── infrastructure/   # DB config, external services
│           └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml
└── README.md
```

### pyproject.toml Configuration
- Use `hatchling` or `setuptools` as build backend
- Python >= 3.13
- Dependencies:
  - fastapi
  - uvicorn[standard]
  - sqlmodel
  - pydantic-settings
- Dev dependencies:
  - pytest
  - pytest-asyncio
  - pytest-cov
  - ruff
  - pyright
  - httpx (for testing)

### Ruff Configuration
In pyproject.toml, configure ruff with:
- Line length: 88
- Target Python 3.13
- Enable recommended rule sets (E, F, W, I, UP, B, SIM)

### Pyright Configuration
- Strict mode
- Include src directory
- Exclude tests from strict checking if needed

### Initial FastAPI App
Create a minimal FastAPI application with:
- Health check endpoint (`GET /health`)
- API versioning structure (`/api/v1/`)
- Proper CORS configuration (configurable)
- OpenAPI documentation enabled

### Basic Tests
- Test that the health endpoint returns 200
- Test that OpenAPI docs are accessible

## Success Criteria
- [ ] `pip install -e ".[dev]"` works from backend directory
- [ ] `ruff check .` passes with no errors
- [ ] `pyright` passes with no errors
- [ ] `pytest` runs and passes
- [ ] `uvicorn papertrade.main:app` starts the server
- [ ] Health check endpoint responds

## References
- See `.github/agents/backend-swe.md` for coding standards
- See `project_strategy.md` for architecture decisions
- See `.github/copilot-instructions.md` for general guidelines

## Notes
- Keep it minimal - we're just scaffolding, not implementing features yet
- Focus on getting the structure and tooling right
- This enables future agents to have a working baseline to build on
