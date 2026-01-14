# Contributing to PaperTrade

Thank you for your interest in contributing to PaperTrade! This document provides guidelines and instructions for developers.

## Quick Start

### Prerequisites

- **Python 3.12+** (Python 3.13 recommended)
- **Node.js 20+**
- **Docker & Docker Compose**
- **Task** (task runner) - [Installation instructions](https://taskfile.dev/installation/)
- **Git**

### Setup

```bash
# Clone repository
git clone https://github.com/TimChild/PaperTrade.git
cd PaperTrade

# Automated setup (recommended)
./.github/copilot-setup.sh

# Or manual setup
task setup

# Start development servers
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
- **No `Any` type**: Except justified with comment explaining why
- **Testing**: Write tests before/alongside code (TDD encouraged)
- **Docstrings**: Public APIs must have docstrings
- **Line length**: 88 characters (ruff default)

**Pre-commit checks**:
```bash
task lint:backend   # Ruff + Pyright
task test:backend   # Pytest
```

**Example**:
```python
from decimal import Decimal
from papertrade.domain.value_objects.money import Money

def calculate_total(prices: list[Money]) -> Money:
    """Calculate the total of all prices.

    Args:
        prices: List of Money values to sum

    Returns:
        Total as Money object
    """
    total = sum(p.amount for p in prices)
    return Money(Decimal(total), prices[0].currency)
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

**Example**:
```typescript
interface PortfolioCardProps {
  portfolioId: string;
  onSelect: (id: string) => void;
}

export function PortfolioCard({ portfolioId, onSelect }: PortfolioCardProps): JSX.Element {
  // Implementation
}
```

## Architecture

PaperTrade follows **Clean Architecture**:

```
Domain       → Pure business logic (no I/O)
Application  → Use cases (orchestration)
Adapters     → Interface implementations
Infrastructure → External concerns (DB, API, cache)
```

**Key Principles**:
- **Dependencies point inwards**: Domain doesn't know about Infrastructure
- **Domain layer is pure**: No side effects, no database calls
- **Test behavior, not implementation**: Test what the system does
- **High cohesion, loose coupling**: Related things together, minimal dependencies

See [project_strategy.md](docs/planning/project_strategy.md) for detailed architecture documentation.

### Forbidden Dependencies

```python
# ❌ WRONG: Domain importing from Infrastructure
from papertrade.infrastructure.database import engine  # NO!

# ✅ CORRECT: Infrastructure implementing Domain interface
from papertrade.domain.ports.portfolio_repository import PortfolioRepository
```

## Testing Guidelines

### Test Philosophy

- **Behavior over implementation**: Test what the system does, not how
- **Sociable tests**: Exercise Use Cases and Domain together
- **No mocking internal logic**: Only mock at architectural boundaries
- **Fast feedback**: Tests should run in <1 minute

### Test Pyramid

PaperTrade follows the standard testing pyramid:

```
        /\
       /  \   E2E (~20 tests) - Critical user journeys
      /    \  - 5-8 min runtime
     /------\  Integration (~50 tests) - Component interactions
    /--------\ - 1-2 min runtime
   /----------\ Unit (~200+ tests) - Pure logic, components
  /------------\ - <10s runtime
```

**Key Principle**: Write tests at the lowest level possible. E2E tests are expensive; prefer component and unit tests.

### When to Write E2E Tests

✅ **DO write E2E tests for**:
- Critical user journeys (signup, trading, portfolio creation)
- Third-party integrations (Clerk auth, payment gateways)
- Multi-step workflows spanning multiple pages

❌ **DON'T write E2E tests for**:
- CSS/styling (use Tailwind + visual regression tools)
- Accessibility (use `jest-axe` in component tests)
- Form validation (use component tests)
- Simple routes (use React Router tests)

See [docs/E2E_TESTING_STANDARDS.md](docs/E2E_TESTING_STANDARDS.md) for complete E2E testing guidelines.

### Test Structure

```python
# Arrange
portfolio = create_portfolio()
command = CreateTradeCommand(...)

# Act
result = await handler.execute(command)

# Assert
assert result.status == "success"
assert result.trade_id is not None
```

### Running Tests

```bash
task test           # All tests (483 total)
task test:backend   # Backend (402 tests)
task test:frontend  # Frontend (81 tests)
task test:e2e       # End-to-end (Playwright)
```

### What to Test

✅ **Do test**:
- Business logic in Domain layer
- Use Case orchestration in Application layer
- API endpoints (integration tests)
- UI components (user interactions)

❌ **Don't test**:
- Private methods
- Framework code
- Database queries (test the behavior, not the SQL)

## Pull Request Process

1. **Create PR** with clear description:
   ```bash
   gh pr create --fill
   ```

2. **Reference issues**: "Closes #123"

3. **Ensure CI passes**: All checks green

4. **Request review** if needed

5. **Squash merge** to main

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CI passing (all checks green)
- [ ] No type errors (`task lint:backend`)
- [ ] Conventional commit format
- [ ] Follows Clean Architecture principles

## Database Management

```bash
task db:reset      # Reset to clean state (deletes all data)
task db:shell      # Open PostgreSQL shell
task db:seed       # Add sample data for development
task db:migrate    # Run pending migrations
```

**Creating a migration**:
```bash
task db:migrate:create MESSAGE="add user table"
```

## Docker Development

```bash
task docker:up:all     # Start all services (db, redis, backend, frontend)
task docker:logs       # View logs
task docker:restart    # Restart services
task docker:clean      # Remove volumes (fresh start)
```

## Common Tasks

```bash
task setup         # Complete environment setup
task dev           # Start all dev servers
task test          # Run all tests
task lint          # Run all linters
task format        # Auto-format code
task ci            # Run full CI locally
task health        # Check service health
task status        # Show environment status
```

Full task list: `task --list`

## Getting Help

- **Documentation**: Start with [README.md](README.md)
- **Architecture**: See [project_strategy.md](docs/planning/project_strategy.md)
- **Current Status**: Check [PROGRESS.md](PROGRESS.md)
- **Agent Orchestration**: See [AGENT_ORCHESTRATION.md](AGENT_ORCHESTRATION.md) for AI agent workflow
- **Issues**: Browse [GitHub Issues](https://github.com/TimChild/PaperTrade/issues)
- **Discussions**: Use GitHub Discussions for questions

## Project Structure

```
PaperTrade/
├── backend/               # Python/FastAPI backend
│   ├── src/papertrade/
│   │   ├── domain/       # Pure business logic
│   │   ├── application/  # Use cases
│   │   ├── adapters/     # Interface implementations
│   │   └── infrastructure/ # External services
│   └── tests/
├── frontend/             # React/TypeScript frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── hooks/       # Custom hooks
│   │   ├── services/    # API clients
│   │   └── types/       # TypeScript types
│   └── tests/
├── docs/                 # Documentation
├── agent_tasks/          # AI agent task definitions
├── Taskfile.yml         # Task runner configuration
└── CONTRIBUTING.md      # This file
```

## Code Review Guidelines

### What Reviewers Look For

- **Architectural compliance**: Follows Clean Architecture rules
- **Test quality**: Behavior testing, not implementation
- **Type safety**: Complete type hints (Python) / strict TypeScript
- **No forbidden dependencies**: Domain doesn't import Infrastructure
- **Clear, maintainable code**: Self-documenting with good names

### Common Review Comments

- "This should be in Domain, not Infrastructure"
- "Add type hints to this function"
- "Test the behavior, not the implementation"
- "Extract this into a Use Case"

## Common Patterns

### Creating a New Use Case

1. **Define Command/Query** (Application layer):
   ```python
   @dataclass
   class CreatePortfolioCommand:
       name: str
       initial_cash: Money
   ```

2. **Create Handler** (Application layer):
   ```python
   class CreatePortfolioHandler:
       def __init__(self, repo: PortfolioRepository):
           self._repo = repo

       async def execute(self, cmd: CreatePortfolioCommand) -> PortfolioId:
           portfolio = Portfolio.create(cmd.name, cmd.initial_cash)
           return await self._repo.save(portfolio)
   ```

3. **Implement Repository** (Adapters layer):
   ```python
   class SqlModelPortfolioRepository(PortfolioRepository):
       async def save(self, portfolio: Portfolio) -> PortfolioId:
           # SQLModel implementation
   ```

4. **Wire in API** (Infrastructure layer):
   ```python
   @router.post("/portfolios")
   async def create_portfolio(cmd: CreatePortfolioCommand) -> PortfolioResponse:
       handler = CreatePortfolioHandler(get_portfolio_repo())
       portfolio_id = await handler.execute(cmd)
       return PortfolioResponse(id=portfolio_id)
   ```

### Adding a New Endpoint

1. Create domain logic (if needed)
2. Create Use Case handler
3. Add API route
4. Write integration test
5. Update OpenAPI docs

## Resources

- [Modern Software Engineering](https://www.davefarley.net/) - Dave Farley
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - Uncle Bob
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)

---

Thank you for contributing! 🚀

**Questions?** Open a [Discussion](https://github.com/TimChild/PaperTrade/discussions) or ask in the PR.
