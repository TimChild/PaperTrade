# PaperTrade 📈

[![CI](https://github.com/TimChild/PaperTrade/actions/workflows/ci.yml/badge.svg)](https://github.com/TimChild/PaperTrade/actions/workflows/ci.yml)

A stock market emulation platform for practicing trading strategies without risking real money.

> **Status**: ✅ Phase 2 Complete - Real market data integration with Alpha Vantage
>
> **Latest**: Comprehensive documentation package available (Jan 4, 2026)

## 📚 Documentation

**New Users?** Start here:
- **[Executive Summary](docs/EXECUTIVE_SUMMARY.md)** - Quick overview of current capabilities
- **[User Guide](docs/USER_GUIDE.md)** - Step-by-step instructions for using PaperTrade

**Developers & Contributors:**
- **[Feature Status Matrix](docs/FEATURE_STATUS.md)** - Complete feature implementation status
- **[Technical Boundaries](docs/TECHNICAL_BOUNDARIES.md)** - Known limitations and edge cases

**Project Information:**
- [Development Progress](PROGRESS.md) - Phase completion tracking
- [Project Plan](project_plan.md) - Roadmap and architecture
- [Backlog](BACKLOG.md) - Planned improvements

## Overview

PaperTrade allows users to:
- ✅ Start with virtual cash and practice investing
- ✅ Create unlimited portfolios with different strategies
- ✅ Execute BUY trades with real-time market data
- ✅ Track holdings, cash balances, and complete transaction history
- ✅ Trade US and international stocks (UK, Canada, Germany, China, etc.)
- 📋 SELL trades and portfolio rebalancing (Phase 3 - Q1 2026)
- 📋 Backtest strategies against historical data (Phase 3)
- 📋 Implement automated trading algorithms (Phase 4)

## Philosophy

This project follows **Modern Software Engineering** principles (Dave Farley):
- **Iterative & Incremental**: Build smallest valuable increments
- **Experimental & Empirical**: Hypothesis → Test → Learn
- **Manage Complexity**: High cohesion, loose coupling
- **Testability as Design**: If it's hard to test, the design is flawed

## Architecture

We use **Clean Architecture** to maintain separation of concerns:

```
┌─────────────────────────────────────────┐
│           Infrastructure                │
│  (Docker, AWS CDK, Database Config)     │
├─────────────────────────────────────────┤
│              Adapters                   │
│  Inbound: FastAPI, CLI                  │
│  Outbound: PostgreSQL, Market APIs      │
├─────────────────────────────────────────┤
│           Application                   │
│  Use Cases: ExecuteTrade, GetPortfolio  │
├─────────────────────────────────────────┤
│              Domain                     │
│  Entities: Portfolio, Asset, Order      │
│  Value Objects: Money, Ticker           │
└─────────────────────────────────────────┘

Dependencies point INWARD only
```

## Technology Stack

### Backend
| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| Framework | FastAPI |
| ORM | SQLModel |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Cache | Redis |
| Linting | Ruff |
| Type Checking | Pyright (strict) |
| Testing | Pytest |

### Frontend
| Component | Technology |
|-----------|------------|
| Language | TypeScript |
| Framework | React + Vite |
| State | TanStack Query, Zustand |
| Styling | Tailwind CSS |
| Testing | Vitest, Playwright |

### Infrastructure
| Component | Technology |
|-----------|------------|
| IaC | AWS CDK (Python) |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Task Runner | Taskfile |

## Getting Started

### Prerequisites

**Required:**
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose

**Optional (but recommended):**
- [Task](https://taskfile.dev/) - Task runner for development commands

#### Installing Task (Optional)

Task is used throughout this documentation for convenience. If you don't have it:

**macOS/Linux:**
```bash
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d ~/.local/bin
```

**Using Homebrew (macOS/Linux):**
```bash
brew install go-task/tap/go-task
```

**Using npm:**
```bash
npm install -g @go-task/cli
```

**Verify installation:**
```bash
task --version
```

**Alternative**: If you don't install Task, you can run commands directly from `Taskfile.yml` or use the manual setup below.

### Quick Start

```bash
# Clone the repository
git clone https://github.com/TimChild/PaperTrade.git
cd PaperTrade

# OPTION 1: Automated setup (recommended)
# This installs pre-commit hooks, dependencies, and starts Docker services
./.github/copilot-setup.sh

# Note: The setup script will create .env from .env.example automatically

# OPTION 2: Manual setup (see below)

# Start development servers (in separate terminals)
task dev:backend   # Backend API on http://localhost:8000
task dev:frontend  # Frontend on http://localhost:5173
```

### Manual Setup

If you prefer to set up manually or don't have Task installed:

```bash
# 1. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install pre-commit hooks
pip install pre-commit  # or: uv tool install pre-commit
pre-commit install
pre-commit install --hook-type pre-push

# 3. Backend setup
cd backend
uv sync --all-extras  # Install dependencies with uv
cd ..

# 4. Frontend setup
cd frontend
npm ci
cd ..

# 5. Start Docker services (PostgreSQL, Redis)
docker compose up -d

# 6. Start backend development server
cd backend
uv run uvicorn papertrade.main:app --reload
```

## Docker Development

PaperTrade includes full Docker support for running the entire stack (PostgreSQL, Redis, Backend, Frontend) in containers.

### Quick Start with Docker

Run the entire stack with one command:

```bash
# Development mode (with hot-reload)
task docker:up:all

# View logs
task docker:logs

# Stop all services
task docker:down
```

**Access the application:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production Mode

Build and run the production-optimized stack:

```bash
# Build production images
task docker:build:prod

# Start production stack
task docker:up:prod
```

**Access the application:**
- Frontend: http://localhost:80
- Backend API: http://localhost:8000

### Environment Variables

Copy `.env.example` to `.env` for development (safe defaults included):

```bash
cp .env.example .env
```

For production, use `.env.production.example` as a template:

```bash
cp .env.production.example .env
# Then edit .env and fill in secure values
```

**Required variables:**
- `ALPHA_VANTAGE_API_KEY`: Get from https://www.alphavantage.co/support/#api-key (free tier available)

**Optional variables** (defaults provided for development):
- `POSTGRES_PASSWORD`: Database password (default: papertrade_dev_password)
- `SECRET_KEY`: App secret key (default: dev-secret-key-change-in-production)

**Production-only variables:**
- `APP_LOG_LEVEL`: Logging level (default: INFO)
- Generate secure secrets:
  ```bash
  # PostgreSQL password
  openssl rand -base64 32

  # Application secret key
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

### Docker Commands

```bash
# Development
task docker:up:all          # Start all services (PostgreSQL, Redis, Backend, Frontend)
task docker:build           # Rebuild development images
task docker:logs            # View all logs
task docker:logs:backend    # Backend logs only
task docker:logs:frontend   # Frontend logs only
task docker:restart         # Restart all services
task docker:restart:backend # Restart backend only
task docker:restart:frontend # Restart frontend only

# Production
task docker:build:prod      # Build production images
task docker:up:prod         # Start production stack
task docker:down:prod       # Stop production stack

# Maintenance
task docker:down            # Stop all services
task docker:clean           # Remove volumes (⚠️ deletes data)
```

### Hot-Reload in Development

Both backend and frontend support hot-reload when running in Docker development mode:

- **Backend**: File changes in `./backend/src` automatically restart the uvicorn server
- **Frontend**: File changes in `./frontend/src` trigger Vite's Hot Module Replacement (HMR)

No need to rebuild images during development - just edit and save!

### Troubleshooting

**Services won't start:**
```bash
# Check container status
docker compose ps

# View detailed logs
docker compose logs backend
docker compose logs frontend

# Restart services
task docker:restart
```

**Database connection errors:**
```bash
# Ensure PostgreSQL is healthy
docker compose ps db

# Restart only the database service
docker compose restart db

# If the database volume is corrupted and needs a reset (⚠️ deletes DB data only)
docker compose down
docker volume rm papertrade_postgres_data
task docker:up:all

# Full reset of all Docker data (DB, Redis, etc.) (⚠️ deletes ALL data)
task docker:clean
task docker:up:all
```

**Port conflicts:**

If ports 5432, 6379, 8000, or 5173 are already in use:

```bash
# First, see what's using the ports (verify before killing)
lsof -i:5432 -i:6379 -i:8000 -i:5173

# Gracefully stop processes on each port (no-op if none found)
lsof -ti:5432 | xargs -r kill 2>/dev/null || echo "No process on port 5432"
lsof -ti:6379 | xargs -r kill 2>/dev/null || echo "No process on port 6379"
lsof -ti:8000 | xargs -r kill 2>/dev/null || echo "No process on port 8000"
lsof -ti:5173 | xargs -r kill 2>/dev/null || echo "No process on port 5173"

# If a process really refuses to stop, you can force kill it as a *last resort*:
# lsof -ti:5432 | xargs -r kill -9 2>/dev/null || echo "No process on port 5432"
```

Or modify the port mappings in `docker-compose.yml`.

**Backend hot-reload not working:**

If file changes don't trigger backend restarts:
1. Ensure you're editing files in `./backend/src/` (mounted volume)
2. Check backend logs: `docker compose logs backend --tail 50`
3. Verify watchfiles is working: Look for "Watching for file changes" in logs
4. Try restarting: `task docker:restart:backend`

**Frontend hot-reload not working:**

If Vite HMR isn't working:
1. Check browser console for HMR connection errors
2. Verify frontend logs: `docker compose logs frontend --tail 50`
3. Try a hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
4. Restart frontend: `task docker:restart:frontend`

### Image Sizes

Development and production images are optimized differently:

| Image | Type | Approximate Size |
|-------|------|------------------|
| Backend (dev) | python:3.12-slim | ~586 MB |
| Backend (prod) | Multi-stage build | ~186 MB* |
| Frontend (dev) | node:20-alpine + Vite | ~135 MB |
| Frontend (prod) | nginx:alpine | ~50 MB* |

*Production image sizes may vary depending on build environment and dependencies.

Production images use multi-stage builds to minimize size and attack surface.

## Project Structure

```
PaperTrade/
├── .github/
│   ├── agents/              # Copilot agent instructions
│   ├── workflows/           # CI/CD pipelines
│   └── copilot-instructions.md
├── backend/
│   ├── src/papertrade/
│   │   ├── domain/          # Pure business logic
│   │   ├── application/     # Use cases
│   │   ├── adapters/        # Interface implementations
│   │   └── infrastructure/  # External concerns
│   └── tests/
├── frontend/
│   ├── src/
│   └── tests/
├── infrastructure/          # AWS CDK
├── agent_progress_docs/     # AI agent work documentation
├── project_plan.md
├── project_strategy.md
└── README.md
```

## Development Workflow

### Available Tasks

```bash
# Setup & Installation
task setup              # Complete development environment setup
task setup:backend      # Install backend dependencies only
task setup:frontend     # Install frontend dependencies only

# Development
task dev:backend        # Start backend dev server
task dev:frontend       # Start frontend dev server

# Testing
task test              # Run all tests
task test:backend      # Run backend tests with coverage
task test:frontend     # Run frontend tests

# Code Quality
task lint              # Run all linters
task lint:backend      # Run ruff and pyright
task lint:frontend     # Run ESLint and TypeScript check
task format            # Auto-format all code
task format:backend    # Format backend with ruff
task format:frontend   # Format frontend

# Docker Services
task docker:up         # Start PostgreSQL and Redis
task docker:down       # Stop Docker services
task docker:logs       # Show service logs
task docker:clean      # Stop and remove volumes (⚠️ deletes data)

# CI & Build
task ci                # Run all CI checks locally (same as GitHub Actions)
task ci:fast           # Run fast checks (lint only, skip tests)
task build             # Build all production artifacts
task build:backend     # Check backend imports and structure
task build:frontend    # Build frontend for production
task test:e2e          # Run end-to-end tests with Playwright

# Utilities
task clean             # Clean build artifacts and caches
task precommit:install # Install pre-commit hooks
task precommit:run     # Run pre-commit on all files
```

### Running Tests

PaperTrade follows the **Test Pyramid** approach with unit, integration, and E2E tests. See [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) for details.

```bash
# All tests (backend + frontend)
task test

# Backend tests
cd backend
uv run pytest                    # All tests (unit + integration)
uv run pytest tests/unit/        # Unit tests only
uv run pytest tests/integration/ # Integration tests only

# Frontend tests
cd frontend
npm test                         # Unit tests
npm run test:e2e                 # E2E tests with Playwright
npm run test:e2e:ui              # E2E tests in interactive mode

# With coverage report
cd backend
uv run pytest --cov=papertrade --cov-report=html
# Open htmlcov/index.html in browser
```

#### Test Statistics

- **Backend**: 220+ tests (195 unit, 26 integration)
- **Frontend**: 30+ tests (23 unit, 7 E2E)
- **Total**: 250+ tests ensuring quality
- **Coverage**: 90%+ on critical paths

### Linting & Type Checking

```bash
# Run all linters and type checkers
task lint

# Backend only (ruff + pyright)
task lint:backend

# Frontend only (ESLint + tsc)
task lint:frontend

# Auto-fix issues
task format
```

### Pre-commit Hooks

Pre-commit hooks run automatically on **push** (not commit) to format code and catch issues:

```bash
# Installation (already done if you ran 'task setup')
task precommit:install
# or
pre-commit install && pre-commit install --hook-type pre-push

# Commits work immediately without triggering formatters
git commit -m "feat: add new feature"

# Push triggers auto-formatters and type checking
git push  # Runs ruff, pyright, etc.

# Run manually on all files
task precommit:run
# or
pre-commit run --all-files

# Skip hooks if needed (not recommended)
git push --no-verify
```

**Why pre-push instead of pre-commit?**
This prevents the "double commit" problem where auto-formatters modify files, requiring you to write the same commit message twice. With pre-push, you commit immediately and formatters run before pushing.

### Running CI Checks Locally

Before pushing, you can run the same checks that CI runs in GitHub Actions:

```bash
# Run all CI checks (lint + test + build)
task ci

# Or run specific checks
task lint           # All linters
task test           # All tests
task build          # Build checks

# Fast checks (lint only, skip tests)
task ci:fast
```

**Why this matters**: These are the **exact same commands** that run in GitHub Actions CI. If `task ci` passes locally, CI should pass too.

**CI Job Mapping:**
- `backend-checks` job → `task setup:backend && task lint:backend && task test:backend`
- `frontend-checks` job → `task setup:frontend && task lint:frontend && task test:frontend && task build:frontend`
- `e2e-tests` job → `task docker:up && task test:e2e`

**Additional CI Checks:**
- Frontend security audit (`npm audit`) runs in CI to detect dependency vulnerabilities
- Coverage reports are uploaded to Codecov for both backend and frontend
- E2E tests include Playwright test reports uploaded as artifacts

### Creating a PR

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make changes following our [coding standards](.github/copilot-instructions.md)
3. Ensure all tests pass
4. Submit PR using our [template](.github/PULL_REQUEST_TEMPLATE.md)

## Roadmap

See [project_plan.md](project_plan.md) for detailed development phases:

1. **Phase 0**: Foundation (current) - Project setup, CI/CD, tooling
2. **Phase 1**: The Ledger MVP - Basic portfolio and trade tracking
3. **Phase 2**: Reality Injection - Real market data integration
4. **Phase 3**: Time Machine - Historical backtesting
5. **Phase 4**: Automation - Algorithmic trading support

## Contributing

We welcome contributions! Please:
1. Read the [copilot instructions](.github/copilot-instructions.md) for coding standards
2. Check the [project strategy](project_strategy.md) for architectural guidance
3. Follow our PR template when submitting changes

## License

[MIT License](LICENSE) - see LICENSE file for details

## Acknowledgments

- Inspired by "Modern Software Engineering" by Dave Farley
- Clean Architecture by Robert C. Martin
