# Task 038: Developer Experience & Tooling Improvements

**Agent**: quality-infra
**Priority**: MEDIUM
**Created**: 2026-01-03
**Status**: Not Started
**Estimated Effort**: 2-3 hours

## Objective

Improve developer experience by adding database management tasks, creating comprehensive developer documentation (CONTRIBUTING.md), and implementing convenience tooling. This work can proceed in parallel with type safety fixes (Task #037).

## Context

From foundation evaluation (2026-01-03), several developer experience gaps were identified:
- No database management tasks (reset, shell, seed)
- Missing CONTRIBUTING.md for onboarding
- No quick status/health check commands
- Database seeding script needed for local development

These improvements don't block Phase 3 but significantly improve developer productivity.

## Requirements

### 1. Add Database Management Tasks to Taskfile.yml

**Add to Taskfile.yml**:
```yaml
  # =========================================================================
  # Database Management
  # =========================================================================
  db:reset:
    desc: "Reset database to clean state (WARNING: deletes all data)"
    cmds:
      - task: docker:down
      - task: docker:clean
      - task: docker:up
      - echo "✓ Database reset complete"

  db:shell:
    desc: "Open PostgreSQL shell"
    cmd: docker compose exec db psql -U zebu -d zebu_dev

  db:shell:prod:
    desc: "Open PostgreSQL shell (production database)"
    cmd: docker compose -f docker-compose.prod.yml exec db psql -U zebu -d zebu

  db:migrate:
    desc: "Run database migrations"
    cmd: cd backend && uv run alembic upgrade head

  db:migrate:create:
    desc: "Create a new database migration (usage: task db:migrate:create MESSAGE='description')"
    cmd: cd backend && uv run alembic revision --autogenerate -m "{{.MESSAGE}}"

  db:seed:
    desc: "Seed database with sample data"
    cmds:
      - cd backend && uv run python scripts/seed_db.py
      - echo "✓ Database seeded with sample data"
```

### 2. Create Database Seeding Script

**Create `backend/scripts/seed_db.py`**:
```python
"""Seed the database with sample data for local development.

Usage:
    uv run python scripts/seed_db.py
    # Or via task: task db:seed
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from zebu.domain.value_objects.currency import Currency
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker
from zebu.application.dtos.price_point import PricePoint
from zebu.infrastructure.database import engine, init_db
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# Import repository classes
from zebu.adapters.outbound.repositories.portfolio_repository import (
    PortfolioRepository,
)
from zebu.adapters.outbound.repositories.price_repository import (
    PriceRepository,
)


async def seed_portfolios(session: AsyncSession) -> None:
    """Create sample portfolios."""
    repo = PortfolioRepository(session)

    print("📁 Creating sample portfolios...")

    # Portfolio 1: Beginner's Portfolio
    p1 = await repo.create(
        name="Beginner's Portfolio",
        initial_cash=Money(Decimal("10000.00"), Currency.USD),
    )
    print(f"  ✓ Created: {p1.name} (${p1.cash_balance.amount})")

    # Portfolio 2: Tech Investor
    p2 = await repo.create(
        name="Tech Growth Portfolio",
        initial_cash=Money(Decimal("50000.00"), Currency.USD),
    )
    print(f"  ✓ Created: {p2.name} (${p2.cash_balance.amount})")

    # Portfolio 3: Dividend Focus
    p3 = await repo.create(
        name="Dividend Income Portfolio",
        initial_cash=Money(Decimal("100000.00"), Currency.USD),
    )
    print(f"  ✓ Created: {p3.name} (${p3.cash_balance.amount})")

    await session.commit()


async def seed_price_history(session: AsyncSession) -> None:
    """Create sample price history for common tickers."""
    repo = PriceRepository(session)

    print("📈 Seeding price history...")

    tickers = [
        (Ticker("AAPL"), Decimal("175.50")),
        (Ticker("GOOGL"), Decimal("142.30")),
        (Ticker("MSFT"), Decimal("378.20")),
        (Ticker("TSLA"), Decimal("238.50")),
        (Ticker("NVDA"), Decimal("495.80")),
    ]

    now = datetime.now(UTC)

    for ticker, base_price in tickers:
        print(f"  Adding history for {ticker.symbol}...")

        # Last 30 days of daily prices
        for days_ago in range(30, -1, -1):
            timestamp = now - timedelta(days=days_ago)

            # Simulate price variation (±3%)
            variation = Decimal(1.0) + (Decimal(days_ago % 7 - 3) / Decimal(100))
            price = base_price * variation

            price_point = PricePoint(
                ticker=ticker,
                price=Money(price, Currency.USD),
                timestamp=timestamp,
                source="seed_data",
                interval="1day",
            )

            await repo.save_price(price_point)

        print(f"    ✓ Added 31 days of data for {ticker.symbol}")

    await session.commit()


async def main() -> None:
    """Run all seeding operations."""
    print("🌱 Starting database seeding...")
    print()

    # Initialize database (creates tables if needed)
    await init_db()

    async with AsyncSession(engine) as session:
        # Check if database is already seeded
        from zebu.adapters.outbound.database.models import PortfolioModel

        result = await session.exec(select(PortfolioModel))
        if result.first():
            print("⚠️  Database already contains data.")
            response = input("   Clear and re-seed? (yes/no): ")
            if response.lower() != "yes":
                print("   Cancelled.")
                return

            # Clear existing data
            print("   Clearing existing data...")
            # (Add deletion logic if needed)

        # Seed data
        await seed_portfolios(session)
        print()
        await seed_price_history(session)
        print()

    print("✅ Database seeding complete!")
    print()
    print("Sample portfolios created:")
    print("  • Beginner's Portfolio ($10,000)")
    print("  • Tech Growth Portfolio ($50,000)")
    print("  • Dividend Income Portfolio ($100,000)")
    print()
    print("Price history added for:")
    print("  • AAPL, GOOGL, MSFT, TSLA, NVDA (30 days)")


if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Create CONTRIBUTING.md

**Create `CONTRIBUTING.md` at root**:
```markdown
# Contributing to Zebu

Thank you for your interest in contributing to Zebu! This document provides guidelines and instructions for developers.

## Quick Start

### Prerequisites

- Python 3.12+ (Python 3.13 recommended)
- Node.js 20+
- Docker & Docker Compose
- Task (task runner) - [Installation instructions](https://taskfile.dev/installation/)
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/TimChild/Zebu.git
cd Zebu

# Automated setup (recommended)
./github/copilot-setup.sh

# Or manual setup
task setup

# Start development
task dev
```

Full setup details in [README.md](README.md).

## Development Workflow

### Starting Work

1. **Check current status**:
   ```bash
   cat PROGRESS.md
   gh pr list  # Check open PRs
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```

3. **Make changes**, run tests frequently:
   ```bash
   task test          # All tests
   task test:backend  # Backend only
   task test:frontend # Frontend only
   ```

4. **Commit with conventional commits**:
   ```bash
   git commit -m "feat(scope): description"
   ```

### Conventional Commits

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Build process, tooling changes
- `ci`: CI/CD changes

**Scopes**: `backend`, `frontend`, `docker`, `ci`, `docs`

**Examples**:
```bash
git commit -m "feat(backend): add portfolio analytics endpoint"
git commit -m "fix(frontend): resolve price chart rendering issue"
git commit -m "docs: update API documentation"
```

## Code Quality Standards

### Python (Backend)

- **Type hints**: Complete type annotations on all functions
- **No `Any` type**: Except justified with comment
- **Testing**: Write tests before/alongside code
- **Docstrings**: Public APIs must have docstrings
- **Line length**: 88 characters (ruff default)

**Pre-commit checks**:
```bash
task lint:backend   # Ruff + Pyright
task test:backend   # Pytest
```

### TypeScript (Frontend)

- **Strict TypeScript**: No implicit any
- **Explicit return types**: On all functions
- **Component typing**: Props interfaces required
- **Testing**: Vitest for components

**Pre-commit checks**:
```bash
task lint:frontend  # ESLint + tsc
task test:frontend  # Vitest
```

## Architecture

Zebu follows **Clean Architecture**:

```
Domain       → Pure business logic (no I/O)
Application  → Use cases (orchestration)
Adapters     → Interface implementations
Infrastructure → External concerns (DB, API, cache)
```

**Key Principles**:
- Dependencies point inwards
- Domain layer is pure (no side effects)
- Test behavior, not implementation
- High cohesion, loose coupling

See [project_strategy.md](project_strategy.md) for details.

## Testing Guidelines

### Test Philosophy

- **Behavior over implementation**: Test what the system does
- **Sociable tests**: Exercise Use Cases and Domain together
- **No mocking internal logic**: Only mock at boundaries
- **Fast feedback**: Tests should run in <1 minute

### Test Structure

```python
# Arrange
portfolio = create_portfolio()

# Act
result = await handler.execute(command)

# Assert
assert result.status == "success"
```

### Running Tests

```bash
task test           # All tests
task test:backend   # Backend (402 tests)
task test:frontend  # Frontend (81 tests)
task test:e2e       # End-to-end (Playwright)
```

## Pull Request Process

1. **Create PR** with clear description
2. **Reference issues**: Closes #123
3. **Ensure CI passes**: All checks green
4. **Request review** if needed
5. **Squash merge** to main

**PR Checklist**:
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CI passing
- [ ] No type errors
- [ ] Conventional commit format

## Database Management

```bash
task db:reset      # Reset to clean state
task db:shell      # PostgreSQL shell
task db:seed       # Add sample data
task db:migrate    # Run migrations
```

## Docker Development

```bash
task docker:up:all     # Start all services
task docker:logs       # View logs
task docker:restart    # Restart services
```

## Common Tasks

```bash
task setup         # Complete environment setup
task dev           # Start all dev servers
task test          # Run all tests
task lint          # Run all linters
task format        # Auto-format code
task ci            # Run full CI locally
```

Full task list: `task --list`

## Getting Help

- **Documentation**: Start with [README.md](README.md)
- **Architecture**: See [project_strategy.md](project_strategy.md)
- **Current Status**: Check [PROGRESS.md](PROGRESS.md)
- **Issues**: Browse [GitHub Issues](https://github.com/TimChild/Zebu/issues)
- **Discussions**: Use GitHub Discussions for questions

## Project Structure

```
Zebu/
├── backend/               # Python/FastAPI backend
│   ├── src/zebu/
│   │   ├── domain/       # Pure business logic
│   │   ├── application/  # Use cases
│   │   ├── adapters/     # Interface implementations
│   │   └── infrastructure/ # External services
│   └── tests/
├── frontend/             # React/TypeScript frontend
│   ├── src/
│   └── tests/
├── docs/                 # Documentation
├── agent_tasks/          # AI agent task definitions
└── Taskfile.yml         # Task runner configuration
```

## Code Review Guidelines

**What reviewers look for**:
- Architectural compliance (Clean Architecture rules)
- Test quality (behavior testing, not implementation)
- Type safety (complete type hints)
- No forbidden dependencies (domain → infrastructure)
- Clear, maintainable code

## Resources

- [Modern Software Engineering](https://www.davefarley.net/) - Dave Farley
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - Uncle Bob
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

---

Thank you for contributing! 🚀
```

### 4. Add Convenience Tasks to Taskfile.yml

**Add health check and status tasks**:
```yaml
  # =========================================================================
  # Quick Status & Health Checks
  # =========================================================================
  health:
    desc: "Check health of all running services"
    cmds:
      - |
        echo "🏥 Checking service health..."
        echo ""
        curl -f http://localhost:8000/health && echo "  ✅ Backend healthy" || echo "  ❌ Backend down"
        curl -f http://localhost:5173/ > /dev/null 2>&1 && echo "  ✅ Frontend healthy" || echo "  ❌ Frontend down"
        docker compose ps | grep -E "(db.*healthy|redis.*healthy)" && echo "  ✅ Docker services healthy" || echo "  ❌ Docker services down"

  status:
    desc: "Show development environment status"
    cmds:
      - echo "📊 Development Environment Status"
      - echo "=================================="
      - echo ""
      - echo "📂 Git Status:"
      - git status --short | head -10 || echo "  (clean)"
      - echo ""
      - echo "🐳 Docker Services:"
      - docker compose ps
      - echo ""
      - echo "🔧 Running Servers:"
      - lsof -i:8000,5173,5432,6379 2>/dev/null || echo "  No servers running"
      - echo ""
      - echo "📋 Recent PRs:"
      - gh pr list --limit 3 2>/dev/null || echo "  (gh not configured)"
```

## Testing Methodology

### Test Each Addition

1. **Database tasks**:
   ```bash
   task db:reset      # Should work
   task db:shell      # Should open psql
   task db:seed       # Should populate data
   ```

2. **Seed script**:
   ```bash
   cd backend && uv run python scripts/seed_db.py
   # Should create 3 portfolios and price history
   ```

3. **CONTRIBUTING.md**:
   - Read through for clarity
   - Verify all links work
   - Test example commands

4. **Convenience tasks**:
   ```bash
   task health   # Should check all services
   task status   # Should show overview
   ```

## Success Criteria

- [ ] Database management tasks work correctly
- [ ] Seed script creates sample data successfully
- [ ] CONTRIBUTING.md is comprehensive and clear
- [ ] Convenience tasks provide useful information
- [ ] All existing tests still pass
- [ ] Documentation is accurate

## Files to Create/Modify

**New Files**:
1. `backend/scripts/seed_db.py` - Database seeding script
2. `CONTRIBUTING.md` - Developer guide

**Modified Files**:
3. `Taskfile.yml` - Add database and convenience tasks

## Non-Goals

- ❌ Complex data relationships in seed script (keep simple)
- ❌ Production database tooling (development only)
- ❌ Automated changelog generation (future work)
- ❌ Performance benchmarking (future work)

## Notes for Agent

- Keep seed script simple and maintainable
- CONTRIBUTING.md should be beginner-friendly
- Test all tasks before committing
- Ensure backward compatibility with existing workflow
- This work is independent of type safety fixes (Task #037)
