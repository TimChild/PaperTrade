# Task 086: Implement Daily Change Calculation

**Priority**: HIGH
**Estimated Effort**: 2-3 hours
**Agent**: backend-swe (primary), frontend-swe (display)
**Related**: Pre-deployment polish, user-facing feature

## Objective

Implement Daily Change calculation for portfolios, showing the dollar amount and percentage change since the previous day's close.

## Problem Description

**Current Behavior**:
- Daily Change always displays "$0.00 (0.00%)" in PortfolioSummaryCard
- Users cannot see intraday performance
- Important metric for tracking daily gains/losses

**Desired Behavior**:
- Show actual daily change: "+$45.32 (+2.14%)" or "-$23.10 (-1.05%)"
- Green for positive change, red for negative
- Calculated as: Current Value - Previous Close Value

## Architecture Design

This feature spans multiple layers following Clean Architecture:

### Backend Changes

**1. Domain Layer** - Portfolio value calculation

**File**: `backend/src/zebu/domain/services/portfolio_value_calculator.py`

Add new method:

```python
from datetime import datetime, timedelta

class PortfolioValueCalculator:
    """Existing service for portfolio value calculations."""

    def calculate_daily_change(
        self,
        portfolio: Portfolio,
        current_prices: dict[str, Money],
        previous_close_prices: dict[str, Money],
    ) -> tuple[Money, Decimal]:
        """
        Calculate daily change in portfolio value.

        Args:
            portfolio: Portfolio entity
            current_prices: Current market prices by ticker
            previous_close_prices: Previous day close prices by ticker

        Returns:
            Tuple of (change_amount, change_percent)
            Example: (Money(Decimal("45.32"), "USD"), Decimal("2.14"))
        """
        current_value = self.calculate_total_value(portfolio, current_prices)
        previous_value = self.calculate_total_value(portfolio, previous_close_prices)

        change_amount = Money(
            amount=current_value.amount - previous_value.amount,
            currency=current_value.currency
        )

        # Avoid division by zero
        if previous_value.amount == Decimal("0"):
            change_percent = Decimal("0")
        else:
            change_percent = (
                (change_amount.amount / previous_value.amount) * Decimal("100")
            ).quantize(Decimal("0.01"))

        return change_amount, change_percent
```

**2. Application Layer** - Use case orchestration

**File**: `backend/src/zebu/application/use_cases/get_portfolio_value.py`

Update existing use case to include daily change:

```python
@dataclass
class PortfolioValueResult:
    """Existing result class."""
    total_value: Money
    cash: Money
    holdings_value: Money
    daily_change: Money  # NEW
    daily_change_percent: Decimal  # NEW


class GetPortfolioValue(UseCase[GetPortfolioValueQuery, PortfolioValueResult]):
    """Existing use case - UPDATE to fetch previous close prices."""

    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        market_data_port: MarketDataPort,
        value_calculator: PortfolioValueCalculator,
    ):
        self._portfolio_repo = portfolio_repo
        self._market_data = market_data_port
        self._calculator = value_calculator

    def execute(self, query: GetPortfolioValueQuery) -> PortfolioValueResult:
        portfolio = self._portfolio_repo.find_by_id(query.portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(query.portfolio_id)

        tickers = [h.ticker for h in portfolio.holdings]

        # Fetch current prices
        current_prices = {
            ticker: self._market_data.get_current_price(ticker)
            for ticker in tickers
        }

        # Fetch previous day close prices (NEW)
        previous_date = self._get_previous_trading_day()
        previous_prices = {
            ticker: self._market_data.get_historical_price(ticker, previous_date)
            for ticker in tickers
        }

        # Calculate values
        total_value = self._calculator.calculate_total_value(portfolio, current_prices)
        holdings_value = self._calculator.calculate_holdings_value(portfolio, current_prices)

        # Calculate daily change (NEW)
        daily_change, daily_change_pct = self._calculator.calculate_daily_change(
            portfolio, current_prices, previous_prices
        )

        return PortfolioValueResult(
            total_value=total_value,
            cash=portfolio.cash,
            holdings_value=holdings_value,
            daily_change=daily_change,
            daily_change_percent=daily_change_pct,
        )

    def _get_previous_trading_day(self) -> datetime:
        """Get previous trading day (skip weekends)."""
        today = datetime.now().date()
        day_of_week = today.weekday()

        # If Monday, go back 3 days to Friday
        if day_of_week == 0:
            return today - timedelta(days=3)
        # If Sunday, go back 2 days to Friday
        elif day_of_week == 6:
            return today - timedelta(days=2)
        # Otherwise, go back 1 day
        else:
            return today - timedelta(days=1)
```

**3. Adapters Layer** - API endpoint

**File**: `backend/src/zebu/adapters/inbound/api/portfolios.py`

Update response model:

```python
class PortfolioValueResponse(BaseModel):
    """Existing response model - ADD daily change fields."""
    total_value: str
    cash: str
    holdings_value: str
    daily_change: str  # NEW - e.g., "45.32" or "-23.10"
    daily_change_percent: str  # NEW - e.g., "2.14" or "-1.05"


@router.get("/{portfolio_id}/value", response_model=PortfolioValueResponse)
async def get_portfolio_value(
    portfolio_id: int,
    use_case: Annotated[GetPortfolioValue, Depends(get_portfolio_value_use_case)],
) -> PortfolioValueResponse:
    """Existing endpoint - UPDATE to include daily change."""
    result = use_case.execute(GetPortfolioValueQuery(portfolio_id=portfolio_id))

    return PortfolioValueResponse(
        total_value=str(result.total_value.amount),
        cash=str(result.cash.amount),
        holdings_value=str(result.holdings_value.amount),
        daily_change=str(result.daily_change.amount),  # NEW
        daily_change_percent=str(result.daily_change_percent),  # NEW
    )
```

**4. Adapters Layer** - Market data port implementation

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

Add method for historical price fetch:

```python
class AlphaVantageAdapter(MarketDataPort):
    """Existing adapter - ADD historical price method."""

    def get_historical_price(self, ticker: str, date: datetime) -> Money:
        """
        Get closing price for a specific date.

        Args:
            ticker: Stock ticker symbol
            date: Date to fetch price for

        Returns:
            Money object with closing price

        Raises:
            MarketDataError: If price cannot be fetched
        """
        # Check cache first
        cache_key = f"historical:{ticker}:{date.isoformat()}"
        cached = self._cache.get(cache_key)
        if cached:
            return Money(amount=Decimal(cached), currency="USD")

        # Fetch from Alpha Vantage TIME_SERIES_DAILY
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker,
            "apikey": self._api_key,
            "outputsize": "compact",  # Last 100 days
        }

        response = self._http_client.get(url, params=params)
        data = response.json()

        if "Error Message" in data:
            raise MarketDataError(f"Invalid ticker: {ticker}")

        if "Note" in data:
            raise RateLimitError("Alpha Vantage rate limit exceeded")

        # Extract closing price for the date
        time_series = data.get("Time Series (Daily)", {})
        date_str = date.strftime("%Y-%m-%d")

        if date_str not in time_series:
            # If exact date not found (holiday/weekend), use most recent
            available_dates = sorted(time_series.keys(), reverse=True)
            if not available_dates:
                raise MarketDataError(f"No historical data for {ticker}")
            date_str = available_dates[0]

        price_data = time_series[date_str]
        close_price = Decimal(price_data["4. close"])

        # Cache for 24 hours (historical data doesn't change)
        self._cache.set(cache_key, str(close_price), ttl=86400)

        return Money(amount=close_price, currency="USD")
```

**5. Domain Port Interface**

**File**: `backend/src/zebu/domain/ports/market_data_port.py`

Update interface:

```python
from abc import ABC, abstractmethod
from datetime import datetime

class MarketDataPort(ABC):
    """Existing port - ADD historical price method."""

    @abstractmethod
    def get_current_price(self, ticker: str) -> Money:
        """Existing method."""
        ...

    @abstractmethod
    def get_historical_price(self, ticker: str, date: datetime) -> Money:
        """
        Get closing price for a specific historical date.

        Args:
            ticker: Stock ticker symbol
            date: Date to fetch closing price for

        Returns:
            Money object with closing price for that date

        Raises:
            MarketDataError: If price cannot be fetched
        """
        ...
```

### Frontend Changes

**File**: `frontend/src/services/api/portfolios.ts`

Update TypeScript types:

```typescript
export interface PortfolioValue {
  totalValue: number
  cash: number
  holdingsValue: number
  dailyChange: number  // NEW
  dailyChangePercent: number  // NEW
}

export async function getPortfolioValue(portfolioId: number): Promise<PortfolioValue> {
  const response = await apiClient.get<{
    total_value: string
    cash: string
    holdings_value: string
    daily_change: string  // NEW
    daily_change_percent: string  // NEW
  }>(`/portfolios/${portfolioId}/value`)

  return {
    totalValue: parseFloat(response.data.total_value),
    cash: parseFloat(response.data.cash),
    holdingsValue: parseFloat(response.data.holdings_value),
    dailyChange: parseFloat(response.data.daily_change),  // NEW
    dailyChangePercent: parseFloat(response.data.daily_change_percent),  // NEW
  }
}
```

**File**: `frontend/src/components/features/portfolio/PortfolioSummaryCard.tsx`

Update display:

```typescript
export function PortfolioSummaryCard({ portfolio }: PortfolioSummaryCardProps) {
  const { data: portfolioValue } = usePortfolioValueQuery(portfolio.id)

  const dailyChange = portfolioValue?.dailyChange ?? 0
  const dailyChangePct = portfolioValue?.dailyChangePercent ?? 0
  const isPositive = dailyChange >= 0

  return (
    <div className="...">
      {/* Total Value */}
      <div>
        <p className="text-sm text-gray-500">Total Value</p>
        <p className="text-2xl font-bold">
          ${portfolioValue?.totalValue.toFixed(2) ?? '0.00'}
        </p>
      </div>

      {/* Daily Change */}
      <div>
        <p className="text-sm text-gray-500">Daily Change</p>
        <p className={`text-lg font-semibold ${
          isPositive ? 'text-green-600' : 'text-red-600'
        }`}>
          {isPositive ? '+' : ''}${Math.abs(dailyChange).toFixed(2)}
          {' '}
          <span className="text-sm">
            ({isPositive ? '+' : ''}{dailyChangePct.toFixed(2)}%)
          </span>
        </p>
      </div>

      {/* Other fields... */}
    </div>
  )
}
```

## Testing Requirements

### Backend Tests

**File**: `backend/tests/unit/domain/services/test_portfolio_value_calculator.py`

```python
def test_calculate_daily_change_positive():
    """Test positive daily change."""
    calculator = PortfolioValueCalculator()
    portfolio = create_test_portfolio()  # Has 10 shares AAPL

    current_prices = {"AAPL": Money(Decimal("150.00"), "USD")}
    previous_prices = {"AAPL": Money(Decimal("145.00"), "USD")}

    change, change_pct = calculator.calculate_daily_change(
        portfolio, current_prices, previous_prices
    )

    # 10 shares * ($150 - $145) = $50 gain
    assert change.amount == Decimal("50.00")
    # ($50 / $1450) * 100 = 3.45%
    assert change_pct == Decimal("3.45")


def test_calculate_daily_change_negative():
    """Test negative daily change."""
    # Similar test for loss scenario


def test_calculate_daily_change_zero_previous_value():
    """Test edge case: zero previous value (avoid division by zero)."""
    # Should return 0% change
```

**File**: `backend/tests/integration/adapters/outbound/test_alpha_vantage_adapter.py`

```python
@pytest.mark.vcr  # Use VCR.py for API mocking
def test_get_historical_price():
    """Test fetching historical price from Alpha Vantage."""
    adapter = AlphaVantageAdapter(api_key="test_key", cache=mock_cache)

    price = adapter.get_historical_price("AAPL", datetime(2024, 1, 15))

    assert isinstance(price, Money)
    assert price.amount > Decimal("0")
    assert price.currency == "USD"
```

### Frontend Tests

**File**: `frontend/src/components/features/portfolio/PortfolioSummaryCard.test.tsx`

```typescript
it('should display positive daily change in green', () => {
  const mockValue = {
    totalValue: 10000,
    dailyChange: 45.32,
    dailyChangePercent: 2.14,
    // ...
  }

  const { getByText } = render(<PortfolioSummaryCard portfolio={mockPortfolio} />)

  expect(getByText(/\+\$45\.32/)).toHaveClass('text-green-600')
  expect(getByText(/\+2\.14%/)).toBeInTheDocument()
})

it('should display negative daily change in red', () => {
  const mockValue = {
    totalValue: 10000,
    dailyChange: -23.10,
    dailyChangePercent: -1.05,
    // ...
  }

  const { getByText } = render(<PortfolioSummaryCard portfolio={mockPortfolio} />)

  expect(getByText(/-\$23\.10/)).toHaveClass('text-red-600')
  expect(getByText(/-1\.05%/)).toBeInTheDocument()
})
```

### E2E Tests

**File**: `frontend/tests/e2e/portfolio.spec.ts`

```typescript
test('should display daily change on portfolio dashboard', async ({ page }) => {
  await page.goto('/portfolios/1')

  // Wait for data to load
  await page.waitForSelector('[data-testid="portfolio-summary-card"]')

  // Verify daily change is displayed
  const dailyChange = page.locator('[data-testid="daily-change"]')
  await expect(dailyChange).toBeVisible()

  // Should match pattern: ±$XX.XX (±X.XX%)
  await expect(dailyChange).toHaveText(/[+-]\$\d+\.\d{2}\s+\([+-]\d+\.\d{2}%\)/)
})
```

## Files to Create/Modify

**Backend**:
- `backend/src/zebu/domain/services/portfolio_value_calculator.py` - Add calculate_daily_change method
- `backend/src/zebu/domain/ports/market_data_port.py` - Add get_historical_price to interface
- `backend/src/zebu/application/use_cases/get_portfolio_value.py` - Fetch previous close prices
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` - Implement historical price fetch
- `backend/src/zebu/adapters/inbound/api/portfolios.py` - Add fields to response
- `backend/tests/unit/domain/services/test_portfolio_value_calculator.py` - Add tests
- `backend/tests/integration/adapters/outbound/test_alpha_vantage_adapter.py` - Add tests

**Frontend**:
- `frontend/src/services/api/portfolios.ts` - Update types and parsing
- `frontend/src/components/features/portfolio/PortfolioSummaryCard.tsx` - Display daily change
- `frontend/src/components/features/portfolio/PortfolioSummaryCard.test.tsx` - Add tests
- `frontend/tests/e2e/portfolio.spec.ts` - Add E2E test

## Success Criteria

- [ ] Backend calculates daily change correctly (positive, negative, zero cases)
- [ ] Historical price fetching works via Alpha Vantage API
- [ ] Weekend/holiday handling (use most recent trading day)
- [ ] API returns daily_change and daily_change_percent fields
- [ ] Frontend displays daily change with correct formatting
- [ ] Green for positive, red for negative
- [ ] All backend unit tests pass (526+ total)
- [ ] All frontend unit tests pass (166+ total)
- [ ] E2E test verifies display on portfolio page
- [ ] No performance degradation (caching used effectively)

## Edge Cases to Handle

1. **Market Closed**: If current time is before market open, use previous close for "current" price
2. **New Portfolio**: If portfolio created today, daily change should be $0.00 (0.00%)
3. **Weekends/Holidays**: Use most recent trading day for previous close
4. **No Holdings**: Portfolio with only cash should show $0.00 change
5. **Alpha Vantage Rate Limit**: Gracefully degrade (show "N/A" or cached value)

## References

- **Alpha Vantage TIME_SERIES_DAILY**: [API Docs](https://www.alphavantage.co/documentation/#daily)
- **Related Tasks**: Task 085 (TradeForm fix), Task 087 (UX improvements)
- **Architecture**: `docs/planning/project_strategy.md` - Clean Architecture principles
- **Deployment**: `docs/planning/deployment_strategy.md` - Pre-deployment checklist

## Notes

- This feature uses 2 Alpha Vantage API calls per ticker (current + historical)
- Cache historical prices aggressively (24-hour TTL)
- Consider batch historical endpoint for multiple tickers (future optimization)
- Daily change is calculated from portfolio holdings value, not total value (cash doesn't change)
