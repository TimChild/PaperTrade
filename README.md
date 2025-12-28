# PaperTrade 📈

[![CI](https://github.com/TimChild/PaperTrade/actions/workflows/pr.yml/badge.svg)](https://github.com/TimChild/PaperTrade/actions/workflows/pr.yml)

A stock market emulation platform for practicing trading strategies without risking real money.

> **Status**: � Phase 1 "The Ledger" - Domain layer complete, Application layer in progress
>
> **Latest**: Domain layer with 158 passing tests merged to main (Dec 28, 2025)

## Overview

PaperTrade allows users to:
- Start with virtual cash ($10K default) and practice investing
- Track portfolio performance with real market data
- Backtest strategies against historical data
- (Future) Implement automated trading algorithms

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
| Language | Python 3.13+ |
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

- Python 3.13+
- Node.js 20+
- Docker & Docker Compose
- [Task](https://taskfile.dev/) (optional but recommended)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/TimChild/PaperTrade.git
cd PaperTrade

# Copy environment variables template
cp .env.example .env

# Set up development environment (installs dependencies and starts Docker services)
task setup  # or follow manual steps below

# Start development servers (in separate terminals)
task dev:backend   # Backend API on http://localhost:8000
task dev:frontend  # Frontend (when available)
```

### Manual Setup

If you don't have Task installed, you can set up manually:

```bash
# 1. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Backend setup
cd backend
uv sync --all-extras  # Install dependencies with uv

# 3. Frontend setup (when available)
cd ../frontend
npm ci

# 4. Start Docker services (PostgreSQL, Redis)
cd ..
docker compose up -d

# 5. Start backend development server
cd backend
uv run uvicorn papertrade.main:app --reload
```

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

# Utilities
task clean             # Clean build artifacts and caches
task precommit:install # Install pre-commit hooks
task precommit:run     # Run pre-commit on all files
```

### Running Tests

```bash
# All tests
task test

# Backend only
task test:backend

# Frontend only
task test:frontend

# With coverage report
cd backend && uv run pytest --cov=papertrade --cov-report=html
# Open htmlcov/index.html in browser
```

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

Install pre-commit hooks to automatically check code quality before commits:

```bash
task precommit:install
# or
pip install pre-commit && pre-commit install

# Run manually on all files
task precommit:run
```

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
