# PaperTrade 📈

A stock market emulation platform for practicing trading strategies without risking real money.

> **Status**: 🚧 Early Development - Setting up foundations

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

# Set up development environment
task setup  # or follow manual steps below

# Start development servers
task dev
```

### Manual Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd ../frontend
npm install

# Start services
docker compose up -d  # PostgreSQL, Redis
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

### Running Tests

```bash
# Backend
task test:backend
# or
cd backend && pytest

# Frontend
task test:frontend
# or
cd frontend && npm test
```

### Linting & Type Checking

```bash
# Backend
task lint:backend
# or
cd backend && ruff check . && pyright

# Frontend
task lint:frontend
# or
cd frontend && npm run lint && npm run typecheck
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
