# Testing Guide

This guide covers PaperTrade's testing philosophy, test types, and how to run them.

## Quick Reference

```bash
# Backend tests
task test:backend              # All backend tests
task lint:backend              # Linting and type checking

# Frontend tests
task test:frontend             # Unit tests (Vitest)
task test:e2e                  # E2E tests (Playwright)

# All tests
task test                      # Run everything
```

## Test Philosophy

- **Test Behavior, Not Implementation**: Test what the system does, not how
- **Sociable Tests**: Exercise Use Cases and Domain together
- **No Mocking Internal Logic**: Only mock at architectural boundaries
- **Persistence Ignorance**: 90% of tests should run without a database

## Test Pyramid

```
         /\
        /E2E\        ← Few: Full user workflows (Playwright)
       /------\
      /  INT  \      ← Some: API contracts (FastAPI TestClient)
     /----------\
    /   UNIT     \   ← Many: Component logic (pytest/vitest)
   /--------------\
```

| Level | Count | Speed | Location |
|-------|-------|-------|----------|
| Unit | ~350 | <2s | `backend/tests/unit/`, `frontend/tests/unit/` |
| Integration | ~30 | <5s | `backend/tests/integration/` |
| E2E | ~7 | <30s | `frontend/tests/e2e/` |

## Running Tests

### Backend (Python)

```bash
cd backend

# All tests
uv run pytest

# Specific test type
uv run pytest tests/unit/
uv run pytest tests/integration/

# With coverage
uv run pytest --cov=papertrade --cov-report=html

# Verbose output
uv run pytest -v

# Specific test
uv run pytest tests/unit/domain/test_money.py -v
```

### Frontend (TypeScript)

```bash
cd frontend

# Unit tests
npm test                    # Run once
npm run test:watch          # Watch mode

# E2E tests
npm run test:e2e            # Headless
npm run test:e2e:headed     # With browser
npm run test:e2e:ui         # Interactive UI

# Type checking
npm run typecheck
```

## Local Integration Testing

### 1. Start Infrastructure

```bash
docker-compose up -d
docker-compose ps  # Verify healthy
```

### 2. Start Backend

```bash
cd backend
uv sync --all-extras
uv run uvicorn papertrade.main:app --reload --host 0.0.0.0 --port 8000
# API docs: http://localhost:8000/docs
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

### 4. Manual Testing

```bash
# Create portfolio
curl -X POST http://localhost:8000/api/v1/portfolios \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{"name": "Test", "initial_deposit": 10000.00, "currency": "USD"}'

# Get balance (replace {id} with portfolio_id from response)
curl http://localhost:8000/api/v1/portfolios/{id}/balance \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001"
```

## Writing Tests

### Naming Conventions

**Python**: `test_<action>_<condition>_<expected>()`
```python
def test_buy_stock_with_insufficient_funds_raises_error():
    ...
```

**TypeScript**: `test('should <outcome> when <condition>')`
```typescript
test('should show error when portfolio name is empty', async () => {
  ...
})
```

### Arrange-Act-Assert Pattern

```python
def test_deposit_increases_balance():
    # Arrange
    portfolio = create_test_portfolio(initial_balance=Money(0, "USD"))

    # Act
    portfolio.deposit(Money(Decimal("100"), "USD"))

    # Assert
    assert portfolio.get_balance() == Money(Decimal("100"), "USD")
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Tests pass individually, fail in suite | Check for global state/singletons |
| Flaky E2E tests | Use explicit waits, not `sleep()` |
| Import errors | Run `uv sync` or `npm install` |
| Database errors | Ensure `docker-compose up -d` |

## CI Integration

Every PR runs:
1. Linting (Ruff, ESLint)
2. Type checking (Pyright, TypeScript)
3. Unit tests (Backend + Frontend)
4. Integration tests (Backend)
5. E2E tests (Full stack)

## Anti-Patterns to Avoid

❌ **Don't mock internal logic** - Test real behavior with test databases
❌ **Don't test implementation details** - Test public interfaces only
❌ **Don't create flaky tests** - Use explicit waits, not `time.sleep()`
❌ **Don't couple tests** - Each test should be independent

## Lessons Learned

**Task 016 revealed**: 218 unit tests passed but 3 critical bugs existed in production paths.
**Root cause**: No integration tests verifying API contracts.
**Solution**: Task 017 added 26 integration + 7 E2E tests, catching field name mismatches and DTO mapping errors.

**Key insight**: Tests passing ≠ System working. Need all pyramid levels.

## Related Documentation

- [E2E Testing Standards](./e2e-testing-standards.md) - When and how to write E2E tests
- [Testing Conventions](./testing-conventions.md) - Test ID naming patterns for stable E2E tests
- [QA Accessibility Guide](./qa-accessibility-guide.md) - Accessibility testing and manual QA
