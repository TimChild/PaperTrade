# Testing Strategy

## Overview

PaperTrade follows the **Test Pyramid** approach to ensure comprehensive test coverage at multiple levels. This strategy was established in **Task 017** after manual testing in Task 016 revealed critical integration bugs that unit tests alone couldn't catch.

## The Test Pyramid

```
         /\
        /E2E\        ← Few tests, full user workflows (7 tests)
       /------\
      /  INT  \      ← Some tests, API contracts (26 tests)
     /----------\
    /   UNIT     \   ← Many tests, component logic (200+ tests)
   /--------------\
```

### Distribution

- **Unit Tests**: ~70% (200+ tests) - Fast, isolated component testing
- **Integration Tests**: ~20% (26 tests) - API endpoints with real database
- **E2E Tests**: ~10% (7 tests) - Complete user workflows

## Test Levels

### Unit Tests

**Purpose**: Verify component behavior in isolation

**Scope**: 
- Domain entities and value objects
- Application layer handlers
- Individual React components
- Utility functions

**Speed**: Very fast (<1s for all tests)

**Location**: 
- `backend/tests/unit/`
- `frontend/tests/unit/`

**Tools**: 
- Backend: `pytest`
- Frontend: `vitest`, React Testing Library

**Example**:
```python
def test_money_addition():
    money1 = Money(Decimal("100.00"), "USD")
    money2 = Money(Decimal("50.00"), "USD")
    result = money1 + money2
    assert result.amount == Decimal("150.00")
```

### Integration Tests

**Purpose**: Verify components work together correctly

**Scope**:
- API endpoints end-to-end
- Database operations
- Request/response mapping
- Error handling
- Authentication flow

**Speed**: Fast (<5s for all tests)

**Location**: `backend/tests/integration/`

**Tools**: FastAPI `TestClient`, in-memory SQLite database

**Key Features**:
- Uses real database (SQLite in-memory for speed)
- Tests full HTTP request → response flow
- Verifies DTO mapping between layers
- Catches field name mismatches
- Tests business rule enforcement

**Example**:
```python
def test_get_portfolio_balance_after_creation(client, default_user_id):
    # Create portfolio
    response = client.post("/api/v1/portfolios", ...)
    portfolio_id = response.json()["portfolio_id"]
    
    # Get balance
    balance_response = client.get(f"/api/v1/portfolios/{portfolio_id}/balance")
    
    assert balance_response.status_code == 200
    assert balance_response.json()["amount"] == "10000.00"
```

### E2E Tests

**Purpose**: Verify complete user workflows

**Scope**:
- Full application workflows
- Frontend + Backend integration
- User interactions
- Multi-step processes

**Speed**: Moderate (<30s for all tests)

**Location**: `frontend/tests/e2e/`

**Tools**: Playwright

**Key Features**:
- Runs both backend and frontend servers
- Tests real browser interactions
- Verifies complete user journeys
- Catches UI/API integration issues

**Example**:
```typescript
test('should create portfolio and show it in dashboard', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /create portfolio/i }).click()
  await page.getByLabel(/portfolio name/i).fill('My Portfolio')
  await page.getByLabel(/initial deposit/i).fill('10000')
  await page.getByRole('button', { name: /create portfolio/i }).last().click()
  
  await expect(page.getByText('My Portfolio')).toBeVisible()
})
```

## Running Tests

### Backend Tests

```bash
cd backend

# All tests (unit + integration)
uv run pytest

# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# With coverage
uv run pytest --cov=papertrade --cov-report=html

# Specific test file
uv run pytest tests/integration/test_portfolio_api.py -v
```

### Frontend Tests

```bash
cd frontend

# Unit tests
npm test
npm run test:watch  # Watch mode

# E2E tests
npm run test:e2e
npm run test:e2e:ui  # Interactive mode
npm run test:e2e:headed  # With browser visible

# All tests
npm test && npm run test:e2e
```

### Full Test Suite

```bash
# Run everything from repository root
cd backend && uv run pytest && cd ../frontend && npm test && npm run test:e2e
```

## Writing Tests

### Guidelines

1. **Test Behavior, Not Implementation**
   - Focus on what the system does, not how it does it
   - Test public interfaces, not internal state
   - Use meaningful assertions

2. **Clear Test Names**
   - Describe what, when, and expected outcome
   - Good: `test_create_portfolio_with_negative_deposit_fails`
   - Bad: `test_portfolio_1`

3. **Arrange-Act-Assert Pattern**
   ```python
   def test_example():
       # Arrange: Set up test data
       portfolio = create_test_portfolio()
       
       # Act: Perform action
       result = portfolio.deposit(Money(Decimal("100"), "USD"))
       
       # Assert: Verify outcome
       assert result.balance == Money(Decimal("100"), "USD")
   ```

4. **One Assertion Per Concept**
   - Each test should verify one behavior
   - Multiple assertions are OK if testing one concept
   - Split unrelated checks into separate tests

5. **No Test Interdependencies**
   - Each test should be independent
   - Tests should work in any order
   - Use fixtures for common setup

### Test Naming Convention

**Backend (Python)**:
```python
def test_<action>_<condition>_<expected_result>():
    """Descriptive docstring explaining the test."""
```

Examples:
- `test_buy_stock_with_insufficient_funds_fails()`
- `test_get_balance_returns_correct_amount_after_deposit()`

**Frontend (TypeScript)**:
```typescript
test('should <expected behavior> when <condition>', async () => {
  // Test code
})
```

Examples:
- `test('should show validation error when portfolio name is empty')`
- `test('should persist portfolio after page refresh')`

## Coverage Goals

### Quantitative

- **Unit Tests**: 90%+ code coverage
- **Integration Tests**: 100% API endpoint coverage
- **E2E Tests**: Critical user paths covered

### Qualitative

- All business rules tested
- Error cases handled
- Edge cases covered
- Security validations tested

## CI/CD Integration

### Pull Request Checks

Every PR must pass:

1. **Linting** (Ruff, ESLint)
2. **Type Checking** (Pyright, TypeScript)
3. **Unit Tests** (Backend + Frontend)
4. **Integration Tests** (Backend)
5. **E2E Tests** (Full stack)
6. **Build Check**

### Workflow

```yaml
jobs:
  backend-quality:        # Linting, typing, unit tests
  backend-integration:    # Integration tests
  frontend-quality:       # Linting, typing, unit tests
  e2e-tests:             # End-to-end tests
```

## Testing Anti-Patterns to Avoid

❌ **Don't Mock Internal Logic**
```python
# BAD: Mocking internal dependencies
def test_create_portfolio(mocker):
    mocker.patch('portfolio_repo.save')  # Testing mock, not real behavior
```

✅ **Do Test Real Behavior**
```python
# GOOD: Using real (test) database
def test_create_portfolio(client, default_user_id):
    response = client.post("/api/v1/portfolios", ...)
    assert response.status_code == 201
```

❌ **Don't Test Implementation Details**
```python
# BAD: Testing internal state
assert portfolio._balance == 100
```

✅ **Do Test Public Behavior**
```python
# GOOD: Testing observable behavior
assert portfolio.get_balance() == Money(Decimal("100"), "USD")
```

❌ **Don't Create Flaky Tests**
```python
# BAD: Time-dependent test
time.sleep(1)  # Race condition
assert something_happened
```

✅ **Do Make Tests Deterministic**
```python
# GOOD: Explicit synchronization
await wait_for_event()
assert something_happened
```

## Lessons Learned from Task 016

### What Went Wrong

During manual testing in Task 016, we discovered **3 critical bugs** that 218 unit tests missed:

1. **Balance Endpoint Crash**: Field name mismatch (`cash_balance` vs `balance`)
2. **Portfolio Creation Broken**: User ID persistence issues
3. **Trading Page Broken**: Command parameter mapping errors

### Root Cause

- **Unit tests passed**: Each component worked in isolation
- **Integration missing**: Components didn't work together
- **No E2E tests**: User workflows weren't validated

### The Fix

Task 017 added:
- 26 integration tests catching API contract issues
- 7 E2E tests validating user workflows
- Fixed 5 critical bugs in API endpoints

**Key Insight**: Tests passing ≠ System working

## Test Maintenance

### When to Update Tests

- **Always**: When adding new features
- **Always**: When fixing bugs (write test that reproduces it first)
- **Sometimes**: When refactoring (if public behavior changes)
- **Never**: When only changing internal implementation

### Keeping Tests Fast

- Use in-memory databases for integration tests
- Parallelize test execution
- Keep E2E tests focused on critical paths
- Use test fixtures to avoid duplication

### Debugging Failed Tests

```bash
# Run specific test with verbose output
pytest tests/integration/test_portfolio_api.py::test_name -vv

# Run with debugger
pytest --pdb

# Show print statements
pytest -s
```

## Future Enhancements

After Task 017, potential improvements:

1. **Visual Regression Tests**: Screenshot comparisons (Phase 2)
2. **Performance Tests**: API response time benchmarks (Phase 2)
3. **Contract Tests**: Pact or similar for API schema validation (Phase 2)
4. **Mutation Testing**: Test the tests with `mutmut` (Phase 3)
5. **Load Testing**: Concurrent user simulation with Locust (Phase 3)
6. **Property-Based Testing**: Use Hypothesis for domain logic (Phase 3)

## Resources

- [Modern Software Engineering (Dave Farley)](https://www.davefarley.net/)
- [Testing Pyramid (Martin Fowler)](https://martinfowler.com/bliki/TestPyramid.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/)
- [React Testing Library](https://testing-library.com/react)

---

**Last Updated**: 2025-12-29 (Task 017)
**Status**: Active
**Owners**: Quality & Infrastructure Team
