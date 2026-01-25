# Task 061: Phase 3c Analytics - Backtesting Feature

**Status**: Not Started
**Depends On**: Tasks 056-060 (All analytics backend and frontend complete)
**Blocks**: None (Phase 3c final task)
**Estimated Effort**: 3-4 days

## Objective

Implement simple backtesting functionality that allows users to execute trades with historical dates (`as_of` parameter) to simulate past trading strategies.

## Reference Architecture

Full specification: `docs/architecture/phase3-refined/phase3c-analytics.md` (see "Backtesting Architecture" section)

## Success Criteria

- [ ] Trade endpoint accepts optional `as_of` parameter
- [ ] Trades executed with `as_of` use historical prices
- [ ] Backtest portfolios can be created and distinguished
- [ ] Frontend UI for backtest mode (date picker, indicator)
- [ ] Validation: `as_of` cannot be in future
- [ ] E2E tests verify backtest workflow
- [ ] All existing tests still pass

## Implementation Details

### 1. Backend: Update Trade Endpoint

**Location**: `backend/app/adapters/api/routes/trades.py`

Update the trade request schema:

```python
from datetime import datetime
from pydantic import BaseModel, field_validator

class TradeRequest(BaseModel):
    ticker: str
    quantity: int
    action: str  # "BUY" or "SELL"
    as_of: datetime | None = None  # NEW: Optional backtest timestamp

    @field_validator('as_of')
    @classmethod
    def validate_as_of_not_future(cls, v: datetime | None) -> datetime | None:
        if v and v > datetime.now():
            raise ValueError("as_of cannot be in the future")
        return v
```

Update the trade endpoint:

```python
@router.post("/{portfolio_id}/trades")
async def execute_trade(
    portfolio_id: UUID,
    request: TradeRequest,
    trade_use_case=Depends(get_execute_trade_use_case),
):
    # Pass as_of to use case
    result = await trade_use_case.execute(
        portfolio_id=portfolio_id,
        ticker=request.ticker,
        quantity=request.quantity,
        trade_type=request.action,
        as_of=request.as_of,  # NEW parameter
    )
    return TradeResponse.from_domain(result)
```

### 2. Backend: Update Execute Trade Use Case

**Location**: `backend/app/application/use_cases/execute_trade.py`

```python
from datetime import datetime

class ExecuteTradeUseCase:
    async def execute(
        self,
        portfolio_id: UUID,
        ticker: str,
        quantity: int,
        trade_type: str,
        as_of: datetime | None = None,  # NEW parameter
    ) -> Transaction:
        effective_time = as_of or datetime.now()

        # Get price at effective time
        if as_of:
            # Use historical price
            price = await self._market_data.get_price_at(ticker, as_of)
        else:
            # Use current price
            price = await self._market_data.get_current_price(ticker)

        # Create transaction with the effective timestamp
        transaction = Transaction.create(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            price=price.price,
            trade_type=trade_type,
            timestamp=effective_time,  # Use effective_time
        )

        # ... rest of validation and saving
```

### 3. Backend: MarketDataPort Extension

**Location**: `backend/app/application/ports/market_data.py`

Add method for historical prices:

```python
class MarketDataPort(ABC):
    @abstractmethod
    async def get_current_price(self, ticker: str) -> PricePoint:
        """Get current price."""
        pass

    @abstractmethod
    async def get_price_at(self, ticker: str, timestamp: datetime) -> PricePoint:
        """Get historical price at a specific timestamp.

        For backtesting - returns the closing price for that date.
        """
        pass
```

Update implementations (AlphaVantageAdapter, etc.) to implement `get_price_at`.

### 4. Frontend: Backtest Mode Toggle

**Location**: `frontend/src/components/trading/TradeForm.tsx`

Add backtest mode to the trade form:

```typescript
interface TradeFormProps {
  portfolioId: string;
}

export function TradeForm({ portfolioId }: TradeFormProps) {
  const [backtestMode, setBacktestMode] = useState(false);
  const [backtestDate, setBacktestDate] = useState<Date | null>(null);

  const handleSubmit = async (formData: TradeFormData) => {
    const payload = {
      ticker: formData.ticker,
      quantity: formData.quantity,
      action: formData.action,
      as_of: backtestMode && backtestDate
        ? backtestDate.toISOString()
        : undefined,
    };

    await executeTrade(portfolioId, payload);
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Existing form fields... */}

      {/* Backtest Mode Section */}
      <div className="mt-4 p-4 border rounded-lg bg-gray-50">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            data-testid="backtest-mode-toggle"
            checked={backtestMode}
            onChange={(e) => setBacktestMode(e.target.checked)}
          />
          <span className="font-medium">Backtest Mode</span>
        </label>

        {backtestMode && (
          <div className="mt-3">
            <label className="block text-sm text-gray-600 mb-1">
              Trade Date
            </label>
            <input
              type="date"
              data-testid="backtest-date-picker"
              className="border rounded px-3 py-2"
              max={new Date().toISOString().split('T')[0]}
              value={backtestDate?.toISOString().split('T')[0] ?? ''}
              onChange={(e) => setBacktestDate(new Date(e.target.value))}
            />

            {/* Warning indicator */}
            <div className="mt-2 text-amber-600 text-sm flex items-center gap-1">
              ⚠️ Backtest mode: Trade will use historical prices
            </div>
          </div>
        )}
      </div>

      <button type="submit" data-testid="execute-trade-btn">
        {backtestMode ? 'Execute Backtest Trade' : 'Execute Trade'}
      </button>
    </form>
  );
}
```

### 5. Frontend: Backtest Indicator

Show when viewing a portfolio that has backtest trades:

**Location**: `frontend/src/components/portfolio/PortfolioHeader.tsx`

```typescript
export function PortfolioHeader({ portfolio }) {
  const hasBacktestTrades = portfolio.transactions?.some(
    (t) => t.is_backtest
  );

  return (
    <div>
      <h1>{portfolio.name}</h1>
      {hasBacktestTrades && (
        <span
          data-testid="backtest-indicator"
          className="bg-amber-100 text-amber-800 px-2 py-1 rounded text-sm"
        >
          Contains backtest trades
        </span>
      )}
    </div>
  );
}
```

### 6. API Client Update

**Location**: `frontend/src/api/trades.ts`

```typescript
interface ExecuteTradeRequest {
  ticker: string;
  quantity: number;
  action: 'BUY' | 'SELL';
  as_of?: string;  // ISO datetime string
}

export async function executeTrade(
  portfolioId: string,
  request: ExecuteTradeRequest
): Promise<Transaction> {
  const response = await api.post(
    `/portfolios/${portfolioId}/trades`,
    request
  );
  return response.data;
}
```

### 7. Backend Tests

**Location**: `backend/tests/api/test_trades_api.py`

Add tests:
- `test_trade_with_as_of_uses_historical_price`
- `test_trade_with_future_as_of_rejected`
- `test_trade_without_as_of_uses_current_price`
- `test_backtest_trade_has_correct_timestamp`

**Location**: `backend/tests/application/test_execute_trade.py`

Add tests:
- `test_execute_trade_with_as_of_parameter`
- `test_get_price_at_called_for_backtest`

### 8. E2E Tests

**Location**: `frontend/e2e/backtest.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { clerk, clerkSetup } from '@clerk/testing/playwright';

test.describe('Backtesting', () => {
  test.beforeAll(async () => {
    await clerkSetup();
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clerk.signIn({
      page,
      signInParams: { strategy: 'email_code', emailAddress: process.env.E2E_CLERK_USER_EMAIL! },
    });
  });

  test('can enable backtest mode and select date', async ({ page }) => {
    await page.goto('/portfolios/test-id');

    // Enable backtest mode
    await page.click('[data-testid="backtest-mode-toggle"]');

    // Verify date picker appears
    await expect(page.getByTestId('backtest-date-picker')).toBeVisible();

    // Verify warning indicator
    await expect(page.getByText('Backtest mode')).toBeVisible();
  });

  test('executes backtest trade with historical price', async ({ page }) => {
    await page.goto('/portfolios/test-id');

    // Enable backtest mode
    await page.click('[data-testid="backtest-mode-toggle"]');

    // Select past date
    await page.fill('[data-testid="backtest-date-picker"]', '2024-01-15');

    // Fill trade form
    await page.fill('[data-testid="ticker-input"]', 'IBM');
    await page.fill('[data-testid="quantity-input"]', '10');
    await page.click('[data-testid="action-buy"]');

    // Execute trade
    await page.click('[data-testid="execute-trade-btn"]');

    // Verify success
    await expect(page.getByText('Trade executed')).toBeVisible();

    // Verify transaction has correct date
    const transactionRow = page.locator('[data-testid="transaction-row"]').first();
    await expect(transactionRow).toContainText('Jan 15, 2024');
  });

  test('cannot select future date for backtest', async ({ page }) => {
    await page.goto('/portfolios/test-id');

    await page.click('[data-testid="backtest-mode-toggle"]');

    // Date picker should have max attribute preventing future dates
    const datePicker = page.getByTestId('backtest-date-picker');
    const maxDate = await datePicker.getAttribute('max');

    const today = new Date().toISOString().split('T')[0];
    expect(maxDate).toBe(today);
  });
});
```

## Implementation Order

1. Update MarketDataPort with `get_price_at` method
2. Implement `get_price_at` in adapters
3. Update ExecuteTradeUseCase to accept `as_of`
4. Update trade API endpoint and schema
5. Write backend tests
6. Update frontend TradeForm with backtest mode
7. Update API client
8. Add backtest indicator to portfolio header
9. Write frontend component tests
10. Write E2E tests
11. Run full test suite

## Commands

```bash
# Run backend tests
task test:backend

# Run frontend tests
task test:frontend

# Run E2E tests
task test:e2e

# Full test suite
task test
```

## Limitations (MVP)

- Manual trade execution only (no automated strategy replay)
- No slippage simulation
- No transaction fees
- Uses end-of-day prices (not intraday)
- No benchmark comparison
- No risk metrics

## Future Enhancements

- Strategy scripts (automated execution)
- Monte Carlo simulations
- Risk metrics (Sharpe ratio, volatility)
- Benchmark comparisons (vs S&P 500)
- Transaction fee simulation
- Intraday price support

## Notes

- Backtest trades use historical prices from `price_history` table (Phase 2b)
- Validation must prevent future dates
- Consider adding a "backtest portfolio" flag for clearer separation
- UI should clearly indicate when in backtest mode
- Follow existing patterns for form validation and error handling
