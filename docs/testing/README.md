# Testing Guide

This guide covers Zebu's testing philosophy, test types, and how to run them.

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
task quality                   # Run all quality checks (lint + test)
```

## Test Philosophy

- **Test Behavior, Not Implementation**: Test what the system does, not how
- **Sociable Tests**: Exercise Use Cases and Domain together
- **No Mocking Internal Logic**: Only mock at architectural boundaries
- **Persistence Ignorance**: 90% of tests should run without a database

> 📖 **Based on**: Modern Software Engineering principles (Dave Farley)

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
| Unit | ~550 | <2s | `backend/tests/unit/`, `frontend/tests/unit/` |
| Integration | ~30 | <5s | `backend/tests/integration/` |
| E2E | ~20 | <30s | `frontend/tests/e2e/` |

**Total**: 796+ tests (571 backend + 225 frontend)

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
uv run pytest --cov=zebu --cov-report=html

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

# E2E tests (requires services running)
npm run test:e2e            # Headless
npm run test:e2e:headed     # With browser
npm run test:e2e:ui         # Interactive UI

# Type checking
npm run typecheck
```

## Local Integration Testing

### 1. Start Infrastructure

```bash
# Start Docker services (PostgreSQL, Redis)
task docker:up

# Verify services are healthy
docker compose ps
```

### 2. Start Backend

```bash
# Terminal 1: Backend
task dev:backend

# Or manually:
cd backend
uv sync --all-extras
uv run uvicorn zebu.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify**: http://localhost:8000/docs (Swagger UI)

### 3. Start Frontend

```bash
# Terminal 2: Frontend
task dev:frontend

# Or manually:
cd frontend
npm install
npm run dev
```

**Verify**: http://localhost:5173 (Frontend app)

### 4. Manual API Testing

```bash
# Health check
curl http://localhost:8000/health

# Create portfolio
curl -X POST http://localhost:8000/api/v1/portfolios \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{"name": "Test", "initial_deposit": 10000.00, "currency": "USD"}'

# Get balance (replace {id} with portfolio_id from response)
curl http://localhost:8000/api/v1/portfolios/{id}/balance \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001"
```

**Quick E2E API Script**: `scripts/quick_e2e_test.sh` automates the above.

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
| Database errors | Ensure `docker compose up -d` |
| Port conflicts | Check `lsof -i :8000` or `lsof -i :5173` |

## CI Integration

Every PR runs:
1. Linting (Ruff, ESLint)
2. Type checking (Pyright, TypeScript)
3. Unit tests (Backend + Frontend)
4. Integration tests (Backend)
5. E2E tests (Full stack)

**CI Configuration**: `.github/workflows/ci.yml`

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

- [E2E Testing Guide](./e2e-guide.md) - Manual testing, Playwright, QA procedures
- [Testing Standards](./standards.md) - Best practices, conventions, accessibility

## External References

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [Playwright documentation](https://playwright.dev/)
- [Testing Library](https://testing-library.com/)
