# Zebu Backend

Backend API for the Zebu stock market emulation platform.

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
- `scripts/` - Utility scripts for development
  - `seed_db.py` - Seed database with sample portfolios and recent price data
  - `seed_historical_data.py` - Fetch historical price data from Alpha Vantage
- `pyproject.toml` - Project configuration and dependencies

## Development Utilities

### Database Seeding

Seed the database with sample portfolios and recent price data:

```bash
# Using task
task db:seed

# Or directly
uv run python scripts/seed_db.py
```

### Historical Price Data Seeding

For testing backtest mode, fetch historical price data from Alpha Vantage:

```bash
# Fetch 30 days of history for default tickers (AAPL, MSFT, GOOGL, TSLA, NVDA)
task seed-historical-data

# Fetch specific tickers with custom date range
task seed-historical-data -- --tickers AAPL,IBM,MSFT --days 365

# Or directly
uv run python scripts/seed_historical_data.py --tickers AAPL,IBM --days 365
```

**Note**: Requires `ALPHA_VANTAGE_API_KEY` environment variable. Get a free API key at [alphavantage.co](https://www.alphavantage.co/support/#api-key). The free tier allows 5 API calls per minute and 500 per day.

## Environment Variables

Backend env vars (set in `.env`, never committed):

| Variable | Required? | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes | — | Postgres / SQLite DSN. |
| `ALPHA_VANTAGE_API_KEY` | yes | — | Market-data adapter (free tier OK). |
| `CLERK_SECRET_KEY` | yes | — | Clerk Bearer auth verification. |
| `API_KEY_HMAC_SECRET` | yes | — | HMAC-SHA256 secret for hashing API keys at rest. |
| `CORS_ORIGINS` | yes (prod) | — | Comma-separated allowed origins. |
| `REDIS_URL` | optional | `redis://localhost:6379` | Price-cache backend. |
| `ANTHROPIC_API_KEY` | conditional | — | **Phase F-3.** Required when `ZEBU_TRIGGER_FIRES_ENABLED=true`; the trigger-fire orchestrator calls the Anthropic Messages API. Without it (and with fires enabled), every fire records `INVOCATION_FAILED`. |
| `ZEBU_AGENT_MODEL` | optional | `claude-haiku-4-5-20251001` | **Phase F-3.** Model the trigger-fire orchestrator invokes. Haiku 4.5 is the right tier for the small trigger-fire prompt; override to Sonnet/Opus if latency-vs-quality calls for it. |
| `ZEBU_TRIGGER_FIRES_ENABLED` | optional | `false` | **Phase F-3.** Feature flag for the agent-invocation path. While `false`, the F-2 evaluator runs (detects fires + logs them) but the orchestrator is not invoked. Set to `true` / `1` / `yes` (case-insensitive) once F-7's smoke test passes. |

## Technology Stack

- **Framework**: FastAPI
- **ORM**: SQLModel
- **Type Checking**: Pyright (strict mode)
- **Linting**: Ruff
- **Testing**: Pytest
