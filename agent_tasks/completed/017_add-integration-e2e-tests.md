# Task 017: Add Integration & E2E Test Coverage

**Created**: 2025-12-28 19:26 PST
**Priority**: P1 - HIGH (prevents future regressions)
**Estimated Effort**: 6-8 hours
**Agent**: Quality-Infra (primary), Backend-SWE (supporting)

## Objective

Add comprehensive integration and end-to-end (E2E) test coverage to prevent bugs like those found during manual testing (Task 016) from reaching production. Establish a complete test pyramid with unit, integration, and E2E tests.

## Context

### The Problem

During manual testing, we discovered **3 critical bugs** that all 218 unit tests missed:
1. Balance endpoint crashes (field name mismatch)
2. Portfolio creation breaks user workflow (ID persistence)
3. Trading page broken (TBD investigation)

**Root Cause**: No integration or E2E tests. Unit tests verify components work in isolation but don't verify they work together.

See: [Manual Testing Bug Report](../agent_tasks/progress/2025-12-28_18-55-40_manual-testing-bug-report.md)

### The Goal

Build a robust testing strategy following the **Test Pyramid**:

```
         /\
        /E2E\        ← Few tests, full user workflows (5-10 tests)
       /------\
      /  INT  \      ← Some tests, API contracts (20-30 tests)
     /----------\
    /   UNIT     \   ← Many tests, component logic (200+ tests) ✅ DONE
   /--------------\
```

**Current State**: Only bottom layer exists
**Target State**: All three layers working together

---

## Requirements

### 1. Backend Integration Tests (~4 hours)

#### 1.1 Test Infrastructure Setup

**File**: `backend/tests/integration/conftest.py`

Create fixtures for integration testing:

```python
"""Integration test fixtures and configuration."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from uuid import uuid4, UUID

from zebu.main import app
from zebu.adapters.inbound.api.dependencies import (
    get_portfolio_repository,
    get_transaction_repository,
)
from zebu.adapters.outbound.database.sqlmodel_repositories import (
    SQLModelPortfolioRepository,
    SQLModelTransactionRepository,
)


@pytest.fixture(name="test_db_engine")
def test_db_engine_fixture():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="test_session")
def test_session_fixture(test_db_engine):
    """Create database session for testing."""
    with Session(test_db_engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(test_db_engine):
    """Create TestClient with test database."""

    def get_test_portfolio_repo():
        with Session(test_db_engine) as session:
            yield SQLModelPortfolioRepository(session)

    def get_test_transaction_repo():
        with Session(test_db_engine) as session:
            yield SQLModelTransactionRepository(session)

    # Override dependencies
    app.dependency_overrides[get_portfolio_repository] = get_test_portfolio_repo
    app.dependency_overrides[get_transaction_repository] = get_test_transaction_repo

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture(name="default_user_id")
def default_user_id_fixture() -> UUID:
    """Provide a default user ID for tests."""
    return uuid4()
```

#### 1.2 Portfolio API Integration Tests

**File**: `backend/tests/integration/test_portfolio_api.py`

```python
"""Integration tests for portfolio API endpoints."""
import pytest
from fastapi.testclient import TestClient
from uuid import UUID


def test_create_portfolio_with_initial_deposit(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test creating a portfolio with initial deposit creates portfolio and transaction."""
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "My Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "portfolio_id" in data
    assert "transaction_id" in data

    portfolio_id = data["portfolio_id"]

    # Verify portfolio was created
    list_response = client.get(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert list_response.status_code == 200
    portfolios = list_response.json()
    assert len(portfolios) == 1
    assert portfolios[0]["id"] == portfolio_id
    assert portfolios[0]["name"] == "My Portfolio"


def test_get_portfolio_balance_after_creation(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test balance endpoint returns correct amount after portfolio creation."""
    # Create portfolio with $10,000 deposit
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Balance Test Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Get balance
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )

    # This would have FAILED before Bug #1 fix!
    assert balance_response.status_code == 200

    balance_data = balance_response.json()
    assert "amount" in balance_data
    assert "currency" in balance_data
    assert "as_of" in balance_data
    assert balance_data["amount"] == "10000.00"
    assert balance_data["currency"] == "USD"


def test_execute_buy_trade_and_verify_holdings(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test buying stock updates holdings correctly."""
    # Create portfolio with cash
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Trading Portfolio",
            "initial_deposit": "50000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute buy trade
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "action": "BUY",
            "ticker": "AAPL",
            "quantity": "10",
            "price": "150.00",
        },
    )

    # This would have FAILED before Bug #3 fix!
    assert trade_response.status_code == 201
    trade_data = trade_response.json()
    assert "transaction_id" in trade_data

    # Verify holdings
    holdings_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert holdings_response.status_code == 200

    holdings_data = holdings_response.json()
    assert "holdings" in holdings_data
    holdings = holdings_data["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "10.0000"

    # Verify balance decreased
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )
    balance_data = balance_response.json()
    # $50,000 - (10 shares * $150) = $48,500
    assert balance_data["amount"] == "48500.00"


def test_buy_and_sell_updates_holdings_correctly(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test buy followed by sell updates holdings and balance correctly."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Trading Portfolio",
            "initial_deposit": "100000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Buy 100 shares of AAPL at $150
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100", "price": "150.00"},
    )

    # Sell 30 shares of AAPL at $155
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "SELL", "ticker": "AAPL", "quantity": "30", "price": "155.00"},
    )

    # Verify holdings: 100 - 30 = 70 shares
    holdings_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers={"X-User-Id": str(default_user_id)},
    )
    holdings = holdings_response.json()["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "70.0000"

    # Verify balance
    # Start: $100,000
    # Buy: -$15,000 (100 * $150)
    # Sell: +$4,650 (30 * $155)
    # End: $89,650
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )
    balance_data = balance_response.json()
    assert balance_data["amount"] == "89650.00"


def test_get_transactions_returns_all_trades(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test transaction history includes all deposits and trades."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Transaction Test",
            "initial_deposit": "25000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute trades
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "50", "price": "150.00"},
    )
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "GOOGL", "quantity": "10", "price": "140.00"},
    )

    # Get transactions
    tx_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers={"X-User-Id": str(default_user_id)},
    )

    assert tx_response.status_code == 200
    tx_data = tx_response.json()
    transactions = tx_data["transactions"]

    # Should have 3 transactions: 1 DEPOSIT + 2 BUY
    assert len(transactions) == 3

    # Verify types
    types = [tx["transaction_type"] for tx in transactions]
    assert "DEPOSIT" in types
    assert types.count("BUY") == 2
```

#### 1.3 Error Handling Integration Tests

**File**: `backend/tests/integration/test_error_handling.py`

```python
"""Integration tests for error handling and edge cases."""
from fastapi.testclient import TestClient
from uuid import UUID, uuid4


def test_get_nonexistent_portfolio_returns_404(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test accessing non-existent portfolio returns 404."""
    fake_portfolio_id = uuid4()

    response = client.get(
        f"/api/v1/portfolios/{fake_portfolio_id}",
        headers={"X-User-Id": str(default_user_id)},
    )

    assert response.status_code == 404


def test_create_portfolio_without_user_id_returns_400(
    client: TestClient,
) -> None:
    """Test creating portfolio without X-User-Id header fails."""
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Test", "initial_deposit": "1000.00", "currency": "USD"},
    )

    assert response.status_code in (400, 403)  # Expect auth error


def test_buy_with_insufficient_funds_fails(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test buying stocks with insufficient cash returns error."""
    # Create portfolio with only $1000
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Poor Portfolio",
            "initial_deposit": "1000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to buy $10,000 worth of stock
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100", "price": "100.00"},
    )

    assert trade_response.status_code == 400
    error = trade_response.json()
    assert "insufficient" in error["detail"].lower()


def test_sell_stock_not_owned_fails(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test selling stock that's not in holdings returns error."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Empty Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to sell stock we don't own
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "SELL", "ticker": "AAPL", "quantity": "10", "price": "150.00"},
    )

    assert trade_response.status_code == 400
    error = trade_response.json()
    assert "not found" in error["detail"].lower() or "insufficient" in error["detail"].lower()
```

#### Success Criteria (Backend Integration)
- [ ] All integration tests pass (target: 15-20 tests)
- [ ] Tests use real database (in-memory SQLite)
- [ ] Tests verify full request → response flow
- [ ] Edge cases and error handling covered
- [ ] Tests run in <5 seconds
- [ ] Can run independently or with unit tests

---

### 2. Frontend End-to-End Tests (~3 hours)

#### 2.1 Setup Playwright

**File**: `frontend/package.json` (add to devDependencies)

```json
{
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  },
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

**File**: `frontend/playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command: 'cd ../backend && uv run uvicorn zebu.main:app --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      port: 5173,
      reuseExistingServer: !process.env.CI,
    },
  ],
})
```

#### 2.2 Portfolio Creation E2E Test

**File**: `frontend/tests/e2e/portfolio-creation.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test.describe('Portfolio Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage to start fresh
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()
  })

  test('should create portfolio and show it in dashboard', async ({ page }) => {
    // This would have FAILED before Bug #2 fix!

    // 1. Navigate to app
    await page.goto('/')

    // 2. Should see empty state
    await expect(page.getByText(/no portfolios found/i)).toBeVisible()

    // 3. Click create portfolio button
    await page.getByRole('button', { name: /create.*portfolio/i }).click()

    // 4. Fill out form
    await page.getByLabel(/portfolio name/i).fill('My Test Portfolio')
    await page.getByLabel(/initial deposit/i).fill('10000')

    // 5. Submit
    await page.getByRole('button', { name: /create portfolio/i }).click()

    // 6. Verify modal closes
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 })

    // 7. Verify portfolio appears in dashboard
    await expect(page.getByText('My Test Portfolio')).toBeVisible()
    await expect(page.getByText(/\$10,000/)).toBeVisible()
  })

  test('should persist portfolio after page refresh', async ({ page }) => {
    // This would have FAILED before Bug #2 fix!

    // Create portfolio
    await page.goto('/')
    await page.getByRole('button', { name: /create.*portfolio/i }).click()
    await page.getByLabel(/portfolio name/i).fill('Persistent Portfolio')
    await page.getByLabel(/initial deposit/i).fill('25000')
    await page.getByRole('button', { name: /create portfolio/i }).click()

    // Wait for portfolio to appear
    await expect(page.getByText('Persistent Portfolio')).toBeVisible()

    // Refresh page
    await page.reload()

    // Portfolio should still be visible
    await expect(page.getByText('Persistent Portfolio')).toBeVisible()
    await expect(page.getByText(/\$25,000/)).toBeVisible()
  })
})
```

#### 2.3 Trading Flow E2E Test

**File**: `frontend/tests/e2e/trading.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test.describe('Trading Flow', () => {
  test('should execute buy trade and update holdings', async ({ page }) => {
    // This would have FAILED before Bug #3 fix!

    // 1. Create portfolio
    await page.goto('/')
    await page.getByRole('button', { name: /create.*portfolio/i }).click()
    await page.getByLabel(/portfolio name/i).fill('Trading Portfolio')
    await page.getByLabel(/initial deposit/i).fill('50000')
    await page.getByRole('button', { name: /create portfolio/i }).click()

    // 2. Navigate to portfolio detail
    await page.getByText('Trading Portfolio').click()

    // 3. Execute buy trade
    await page.getByLabel(/ticker/i).fill('AAPL')
    await page.getByLabel(/quantity/i).fill('10')
    await page.getByLabel(/price/i).fill('150')
    await page.getByRole('button', { name: /buy/i }).click()

    // 4. Verify success message
    await expect(page.getByText(/order executed successfully/i)).toBeVisible()

    // 5. Verify holdings updated
    await expect(page.getByText('AAPL')).toBeVisible()
    await expect(page.getByText(/10.*shares/i)).toBeVisible()

    // 6. Verify balance decreased
    await expect(page.getByText(/\$48,500/)).toBeVisible()
  })

  test('should show error when buying with insufficient funds', async ({ page }) => {
    // Create portfolio with only $1000
    await page.goto('/')
    await page.getByRole('button', { name: /create.*portfolio/i }).click()
    await page.getByLabel(/portfolio name/i).fill('Poor Portfolio')
    await page.getByLabel(/initial deposit/i).fill('1000')
    await page.getByRole('button', { name: /create portfolio/i }).click()

    // Navigate to detail
    await page.getByText('Poor Portfolio').click()

    // Try to buy $10,000 worth of stock
    await page.getByLabel(/ticker/i).fill('AAPL')
    await page.getByLabel(/quantity/i).fill('100')
    await page.getByLabel(/price/i).fill('100')
    await page.getByRole('button', { name: /buy/i }).click()

    // Should see error
    await expect(page.getByText(/insufficient.*fund/i)).toBeVisible()
  })
})
```

#### Success Criteria (Frontend E2E)
- [ ] Playwright installed and configured
- [ ] E2E tests run both backend and frontend automatically
- [ ] Tests verify real user workflows
- [ ] Tests catch the bugs from Task 016
- [ ] Tests run in <30 seconds
- [ ] Can run in CI/CD pipeline

---

### 3. CI/CD Integration (~1 hour)

#### 3.1 Update GitHub Actions Workflow

**File**: `.github/workflows/ci.yml` (add integration and E2E stages)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  # ... existing jobs (unit tests, linting) ...

  integration-tests:
    name: Integration Tests (Backend)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          cd backend
          pip install uv
          uv sync --all-extras

      - name: Run integration tests
        run: |
          cd backend
          uv run pytest tests/integration -v --cov=src --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./backend/coverage.xml

  e2e-tests:
    name: E2E Tests (Frontend + Backend)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install backend dependencies
        run: |
          cd backend
          pip install uv
          uv sync --all-extras

      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci

      - name: Install Playwright
        run: |
          cd frontend
          npx playwright install --with-deps

      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

#### Success Criteria (CI/CD)
- [ ] Integration tests run on every PR
- [ ] E2E tests run on every PR
- [ ] Tests must pass before merge
- [ ] Coverage reports uploaded
- [ ] Playwright reports available on failure

---

## Files to Create/Modify

### Backend
- **Create**: `backend/tests/integration/conftest.py` - Test fixtures
- **Create**: `backend/tests/integration/test_portfolio_api.py` - ~15-20 tests
- **Create**: `backend/tests/integration/test_error_handling.py` - ~5-10 tests
- **Modify**: `backend/pyproject.toml` - Add pytest-integration marker

### Frontend
- **Create**: `frontend/playwright.config.ts` - Playwright configuration
- **Create**: `frontend/tests/e2e/portfolio-creation.spec.ts` - ~5 tests
- **Create**: `frontend/tests/e2e/trading.spec.ts` - ~5 tests
- **Modify**: `frontend/package.json` - Add Playwright dependency and scripts

### CI/CD
- **Modify**: `.github/workflows/ci.yml` - Add integration and E2E test stages

### Documentation
- **Create**: `docs/TESTING_STRATEGY.md` - Document the test pyramid
- **Update**: `README.md` - Add testing commands
- **Update**: `PROGRESS.md` - Document testing improvements

---

## Testing Requirements

### Integration Tests
```bash
# Run integration tests only
cd backend
uv run pytest tests/integration -v

# Run with coverage
uv run pytest tests/integration --cov=src --cov-report=html
```

**Expected**:
- All integration tests pass (15-20 tests)
- Coverage for API endpoints: 90%+
- Tests run in <5 seconds

### E2E Tests
```bash
# Run E2E tests
cd frontend
npm run test:e2e

# Run with UI
npm run test:e2e:ui
```

**Expected**:
- All E2E tests pass (10+ tests)
- Tests verify real user workflows
- Tests run in <30 seconds

### Full Test Suite
```bash
# Backend: unit + integration
cd backend
uv run pytest -v

# Frontend: unit + E2E
cd frontend
npm test
npm run test:e2e
```

**Expected**:
- Backend: 195 unit + 20 integration = 215 tests ✅
- Frontend: 23 unit + 10 E2E = 33 tests ✅
- Total: 248 tests passing

---

## Success Criteria

### Functional Requirements
- [ ] Integration tests verify API contract compliance
- [ ] Integration tests catch bugs from Task 016
- [ ] E2E tests verify complete user workflows
- [ ] E2E tests run both frontend and backend
- [ ] Error cases properly tested
- [ ] All tests pass locally and in CI

### Code Quality
- [ ] Tests follow existing patterns
- [ ] Clear test names describing behavior
- [ ] Good assertions with helpful messages
- [ ] No flaky tests
- [ ] Fast execution (<5 min total)

### Documentation
- [ ] Testing strategy documented
- [ ] Commands in README
- [ ] CI/CD pipeline documented
- [ ] Future testing improvements noted

---

## Test Pyramid Adherence

Target distribution:
- **Unit Tests**: 70% (195 → 200+)
- **Integration Tests**: 20% (0 → 20-30)
- **E2E Tests**: 10% (0 → 10-15)

**Total Tests**: 218 → 250+ tests

**Confidence Level**: Low → High
- Before: Unit tests only, integration bugs slip through
- After: Full pyramid, bugs caught early

---

## Estimated Time Breakdown

| Task | Time | Agent |
|------|------|-------|
| Backend integration test infrastructure | 1 hour | Quality-Infra |
| Portfolio API integration tests | 1.5 hours | Backend-SWE |
| Error handling integration tests | 1 hour | Backend-SWE |
| Playwright setup | 30 min | Quality-Infra |
| Portfolio creation E2E tests | 1 hour | Quality-Infra |
| Trading flow E2E tests | 1 hour | Quality-Infra |
| CI/CD integration | 1 hour | Quality-Infra |
| Documentation | 1 hour | Quality-Infra |
| **Total** | **8 hours** | |

---

## Constraints

1. **No Breaking Changes**: Tests should not require code changes (bugs already fixed in Task 016)
2. **Fast Execution**: All tests must run in <5 minutes
3. **CI Compatible**: Tests must work in GitHub Actions
4. **No External Dependencies**: Use in-memory database and mock servers
5. **Maintainable**: Clear test structure, good naming, minimal duplication

---

## Related Issues

- Task 016: Fix Critical Integration Bugs (these tests prevent regression)
- Manual Testing Bug Report: Documents the bugs these tests catch
- BACKLOG.md: Remove "Add integration tests" item (addressed here)

---

## Future Enhancements

After this task:
1. **Visual Regression Tests**: Screenshot comparisons (Phase 2)
2. **Performance Tests**: API response time benchmarks (Phase 2)
3. **Contract Tests**: Schema validation (Phase 2)
4. **Mutation Testing**: Test the tests (Phase 3)
5. **Load Testing**: Concurrent user simulation (Phase 3)

---

## Documentation to Create

### TESTING_STRATEGY.md

```markdown
# Testing Strategy

## Test Pyramid

We follow the test pyramid approach:

### Unit Tests (70%)
- **Purpose**: Verify component behavior in isolation
- **Scope**: Single functions, classes, components
- **Speed**: Very fast (<1s for all)
- **Location**: Next to source code
- **Tools**: pytest (backend), Vitest (frontend)

### Integration Tests (20%)
- **Purpose**: Verify components work together
- **Scope**: API endpoints, database operations
- **Speed**: Fast (<5s for all)
- **Location**: `tests/integration/`
- **Tools**: TestClient, in-memory SQLite

### E2E Tests (10%)
- **Purpose**: Verify user workflows
- **Scope**: Complete user journeys
- **Speed**: Moderate (<30s for all)
- **Location**: `tests/e2e/`
- **Tools**: Playwright

## Running Tests

### Backend
```bash
# All tests
uv run pytest

# Unit only
uv run pytest tests/unit

# Integration only
uv run pytest tests/integration

# With coverage
uv run pytest --cov=src --cov-report=html
```

### Frontend
```bash
# Unit tests
npm test

# E2E tests
npm run test:e2e
```

## Writing Tests

### Guidelines
1. **Test behavior, not implementation**
2. **Clear test names** (describe what, when, then)
3. **Arrange-Act-Assert** pattern
4. **One assertion per concept**
5. **No test interdependencies**

### Examples
Good: `test_create_portfolio_with_deposit_saves_to_database`
Bad: `test_portfolio_1`
```

---

**This task establishes a robust testing foundation that prevents bugs like those in Task 016 from ever reaching production. The test pyramid ensures we have confidence at all levels of the application.**
