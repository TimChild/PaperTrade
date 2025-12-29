# Task 024: Portfolio Use Cases with Real Prices

**Created**: 2025-12-29  
**Agent**: backend-swe  
**Estimated Effort**: 3-4 hours  
**Dependencies**: Task 020 (Alpha Vantage Adapter), Task 021 (PostgreSQL Repository recommended but not required)  
**Phase**: Phase 2a - Market Data Integration

## Objective

Update portfolio use cases to fetch and display real-time stock prices, calculating accurate portfolio valuations and individual holding performance metrics.

## Context

Currently, portfolio queries return static mock data. This task integrates the MarketDataPort (from Task 020) into the application layer, enabling real portfolio valuations with live market data.

### Architecture References
- [implementation-guide.md](../architecture_plans/20251228_phase2-market-data/implementation-guide.md#task-019-update-portfolio-use-cases-3-4-hours)
- [interfaces.md](../architecture_plans/20251228_phase2-market-data/interfaces.md#marketdataport-interface)

## Success Criteria

- [ ] GetPortfolioBalance query uses real prices
- [ ] GetHoldings query includes current prices and gain/loss
- [ ] MarketDataPort injected via FastAPI dependencies
- [ ] Graceful error handling for missing prices
- [ ] All tests updated and passing
- [ ] Integration test with AlphaVantageAdapter

## Implementation Details

### 1. Update GetPortfolioBalance Query

**File**: `backend/src/papertrade/application/queries/get_portfolio_balance.py`

**Current Signature**:
```python
class GetPortfolioBalance:
    async def execute(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        portfolio_repository: PortfolioRepository,
    ) -> PortfolioBalanceDTO:
```

**Updated Signature**:
```python
class GetPortfolioBalance:
    async def execute(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        portfolio_repository: PortfolioRepository,
        market_data: MarketDataPort,  # NEW
    ) -> PortfolioBalanceDTO:
```

**Implementation Changes**:

```python
async def execute(...) -> PortfolioBalanceDTO:
    # Get portfolio and holdings (existing logic)
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
    holdings = await portfolio_repository.get_holdings(portfolio_id)
    
    # Calculate holdings value with REAL prices
    holdings_value = Money(Decimal("0"), "USD")
    
    for holding in holdings:
        try:
            # Fetch current price from market data
            price_point = await market_data.get_current_price(holding.ticker)
            holding_value = Money(
                price_point.price.amount * Decimal(str(holding.quantity)),
                price_point.price.currency
            )
            holdings_value += holding_value
            
        except TickerNotFoundError:
            # Ticker not found - skip this holding (value = 0)
            logger.warning(f"Ticker {holding.ticker} not found in market data")
            continue
            
        except MarketDataUnavailableError as e:
            # API down or rate limited - skip but log
            logger.error(f"Market data unavailable for {holding.ticker}: {e}")
            continue
    
    # Calculate total value
    total_value = portfolio.cash_balance + holdings_value
    
    return PortfolioBalanceDTO(
        portfolio_id=portfolio_id,
        cash_balance=portfolio.cash_balance,
        holdings_value=holdings_value,
        total_value=total_value,
    )
```

**Error Handling Strategy**:
- **TickerNotFoundError**: Skip holding, value = 0, log warning
- **MarketDataUnavailableError**: Skip holding, value = 0, log error
- **Other errors**: Let propagate (will be caught by API layer)

### 2. Update GetHoldings Query

**File**: `backend/src/papertrade/application/queries/get_portfolio_holdings.py`

**Update HoldingDTO** (in `backend/src/papertrade/application/dtos/holding.py`):

```python
@dataclass(frozen=True)
class HoldingDTO:
    """DTO for holding with market data."""
    
    ticker: str
    quantity: Decimal
    average_cost: Money
    cost_basis: Money  # quantity * average_cost
    
    # NEW: Market data fields
    current_price: Money | None = None
    market_value: Money | None = None  # quantity * current_price
    unrealized_gain_loss: Money | None = None  # market_value - cost_basis
    unrealized_gain_loss_percent: Decimal | None = None
    
    # NEW: Price metadata
    price_timestamp: datetime | None = None
    price_source: str | None = None
```

**Updated Query**:

```python
class GetHoldings:
    async def execute(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        portfolio_repository: PortfolioRepository,
        market_data: MarketDataPort,  # NEW
    ) -> list[HoldingDTO]:
        # Get holdings (existing logic)
        holdings = await portfolio_repository.get_holdings(portfolio_id)
        
        # Enrich with market data
        enriched_holdings = []
        for holding in holdings:
            try:
                # Fetch current price
                price_point = await market_data.get_current_price(holding.ticker)
                
                # Calculate metrics
                market_value = Money(
                    price_point.price.amount * Decimal(str(holding.quantity)),
                    price_point.price.currency
                )
                cost_basis = Money(
                    holding.average_cost.amount * Decimal(str(holding.quantity)),
                    holding.average_cost.currency
                )
                unrealized_gain_loss = Money(
                    market_value.amount - cost_basis.amount,
                    market_value.currency
                )
                gain_loss_percent = (
                    (unrealized_gain_loss.amount / cost_basis.amount) * 100
                    if cost_basis.amount > 0 
                    else Decimal("0")
                )
                
                # Create enriched DTO
                enriched_holdings.append(HoldingDTO(
                    ticker=holding.ticker.symbol,
                    quantity=holding.quantity,
                    average_cost=holding.average_cost,
                    cost_basis=cost_basis,
                    current_price=price_point.price,
                    market_value=market_value,
                    unrealized_gain_loss=unrealized_gain_loss,
                    unrealized_gain_loss_percent=gain_loss_percent,
                    price_timestamp=price_point.timestamp,
                    price_source=price_point.source,
                ))
                
            except (TickerNotFoundError, MarketDataUnavailableError) as e:
                # Price unavailable - return holding without market data
                logger.warning(f"Price unavailable for {holding.ticker}: {e}")
                enriched_holdings.append(HoldingDTO(
                    ticker=holding.ticker.symbol,
                    quantity=holding.quantity,
                    average_cost=holding.average_cost,
                    cost_basis=Money(
                        holding.average_cost.amount * Decimal(str(holding.quantity)),
                        holding.average_cost.currency
                    ),
                    # Market data fields = None (indicates unavailable)
                ))
        
        return enriched_holdings
```

### 3. Dependency Injection

**File**: `backend/src/papertrade/adapters/inbound/api/dependencies.py`

**Add MarketData Dependency**:

```python
from papertrade.adapters.outbound.market_data.alpha_vantage_adapter import AlphaVantageAdapter
from papertrade.infrastructure.rate_limiter import RateLimiter
from papertrade.infrastructure.cache.price_cache import PriceCache
from redis.asyncio import Redis
import httpx

async def get_market_data() -> AlphaVantageAdapter:
    """Provide MarketDataPort implementation (AlphaVantageAdapter)."""
    
    # Get config
    from papertrade.config import settings
    
    # Create Redis client for rate limiter and cache
    redis = await Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    
    # Create rate limiter (5 calls/min, 500/day)
    rate_limiter = RateLimiter(
        redis=redis,
        key_prefix="papertrade:ratelimit:alphavantage",
        calls_per_minute=5,
        calls_per_day=500,
    )
    
    # Create price cache
    price_cache = PriceCache(
        redis=redis,
        key_prefix="papertrade:price",
        default_ttl=3600,  # 1 hour
    )
    
    # Create HTTP client
    http_client = httpx.AsyncClient(timeout=5.0)
    
    # Create adapter
    adapter = AlphaVantageAdapter(
        rate_limiter=rate_limiter,
        price_cache=price_cache,
        http_client=http_client,
        api_key=settings.alpha_vantage_api_key,
    )
    
    return adapter
```

**Update Portfolio Routes**:

**File**: `backend/src/papertrade/adapters/inbound/api/routes/portfolios.py`

```python
from papertrade.adapters.inbound.api.dependencies import get_market_data
from papertrade.application.ports.market_data_port import MarketDataPort

@router.get("/{portfolio_id}/balance")
async def get_portfolio_balance(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
    market_data: MarketDataPort = Depends(get_market_data),  # NEW
):
    query = GetPortfolioBalance()
    result = await query.execute(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        portfolio_repository=portfolio_repo,
        market_data=market_data,  # NEW
    )
    return result

@router.get("/{portfolio_id}/holdings")
async def get_holdings(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
    market_data: MarketDataPort = Depends(get_market_data),  # NEW
):
    query = GetHoldings()
    result = await query.execute(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        portfolio_repository=portfolio_repo,
        market_data=market_data,  # NEW
    )
    return result
```

### 4. Configuration Updates

**File**: `backend/settings.toml`

```toml
[redis]
url = "redis://localhost:6379/0"

[market_data.alpha_vantage]
api_key = "your_api_key_here"  # Or load from environment variable
base_url = "https://www.alphavantage.co/query"
```

**File**: `backend/src/papertrade/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing settings...
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Alpha Vantage
    alpha_vantage_api_key: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 5. Testing Updates

**Update Unit Tests** - Mock MarketDataPort:

**File**: `backend/tests/unit/application/queries/test_get_portfolio_balance.py`

```python
import pytest
from unittest.mock import AsyncMock
from papertrade.application.queries.get_portfolio_balance import GetPortfolioBalance

@pytest.fixture
def mock_market_data():
    """Mock MarketDataPort."""
    mock = AsyncMock()
    mock.get_current_price.return_value = PricePoint(
        ticker=Ticker("AAPL"),
        price=Money(Decimal("150.00"), "USD"),
        timestamp=datetime.now(timezone.utc),
        source="alpha_vantage",
        interval="1day",
    )
    return mock

@pytest.mark.asyncio
async def test_portfolio_balance_with_real_prices(
    mock_portfolio_repository,
    mock_market_data,
):
    """Test portfolio balance calculation with real prices."""
    query = GetPortfolioBalance()
    
    result = await query.execute(
        portfolio_id=UUID("..."),
        user_id=UUID("..."),
        portfolio_repository=mock_portfolio_repository,
        market_data=mock_market_data,
    )
    
    # Verify price was fetched
    assert mock_market_data.get_current_price.called
    
    # Verify portfolio value includes holdings value
    assert result.total_value.amount > result.cash_balance.amount

@pytest.mark.asyncio
async def test_portfolio_balance_handles_ticker_not_found(
    mock_portfolio_repository,
    mock_market_data,
):
    """Test graceful handling when ticker not found."""
    from papertrade.application.exceptions import TickerNotFoundError
    
    # Mock ticker not found
    mock_market_data.get_current_price.side_effect = TickerNotFoundError("INVALID")
    
    query = GetPortfolioBalance()
    result = await query.execute(...)
    
    # Should not raise error, just exclude that holding
    # Holdings value should be 0
    assert result.holdings_value.amount == Decimal("0")
```

**Integration Test with Real Adapter**:

**File**: `backend/tests/integration/api/test_portfolio_routes_with_market_data.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_holdings_with_real_prices(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Integration test with AlphaVantageAdapter (uses respx mocks)."""
    
    # Mock Alpha Vantage API response
    import respx
    respx.get("https://www.alphavantage.co/query").mock(
        return_value=httpx.Response(200, json={
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "192.53",
                "07. latest trading day": "2025-12-29",
            }
        })
    )
    
    # Make request
    response = await async_client.get(
        "/api/v1/portfolios/{portfolio_id}/holdings",
        headers=auth_headers,
    )
    
    # Verify response
    assert response.status_code == 200
    holdings = response.json()
    
    # Verify market data included
    assert holdings[0]["current_price"]["amount"] == 192.53
    assert holdings[0]["market_value"] is not None
    assert holdings[0]["unrealized_gain_loss"] is not None
```

## Files to Create/Modify

### Modified Files

**Application Layer**:
- `backend/src/papertrade/application/queries/get_portfolio_balance.py`
- `backend/src/papertrade/application/queries/get_portfolio_holdings.py`
- `backend/src/papertrade/application/dtos/holding.py` (add market data fields)

**Adapters Layer**:
- `backend/src/papertrade/adapters/inbound/api/dependencies.py` (add get_market_data)
- `backend/src/papertrade/adapters/inbound/api/routes/portfolios.py` (inject market_data)

**Configuration**:
- `backend/src/papertrade/config.py` (add redis_url, alpha_vantage_api_key)
- `backend/settings.toml` (add redis and alpha_vantage sections)
- `backend/.env.example` (add ALPHA_VANTAGE_API_KEY)

**Tests**:
- `backend/tests/unit/application/queries/test_get_portfolio_balance.py`
- `backend/tests/unit/application/queries/test_get_portfolio_holdings.py`
- `backend/tests/integration/api/test_portfolio_routes_with_market_data.py` (create)

## Testing Checklist

- [ ] Unit tests with mocked MarketDataPort pass
- [ ] Error handling tests (ticker not found, API unavailable)
- [ ] Integration test with AlphaVantageAdapter (respx mocks)
- [ ] Manual test with real API key (optional, not in CI)
- [ ] Portfolio balance endpoint returns real values
- [ ] Holdings endpoint includes current prices and gain/loss
- [ ] Type checking passes (pyright --strict)
- [ ] Linting passes (ruff check, ruff format)
- [ ] All tests pass (~374 existing + ~15 new = ~389 total)

## Manual Testing

```bash
# Start services
task docker:up
task dev:backend

# Test portfolio balance endpoint
curl http://localhost:8000/api/v1/portfolios/{id}/balance \
  -H "Authorization: Bearer {token}"

# Expected response:
{
  "portfolio_id": "...",
  "cash_balance": {"amount": 25000.00, "currency": "USD"},
  "holdings_value": {"amount": 15750.00, "currency": "USD"},
  "total_value": {"amount": 40750.00, "currency": "USD"}
}

# Test holdings endpoint
curl http://localhost:8000/api/v1/portfolios/{id}/holdings \
  -H "Authorization: Bearer {token}"

# Expected response:
[
  {
    "ticker": "AAPL",
    "quantity": 100,
    "average_cost": {"amount": 150.00, "currency": "USD"},
    "cost_basis": {"amount": 15000.00, "currency": "USD"},
    "current_price": {"amount": 192.53, "currency": "USD"},
    "market_value": {"amount": 19253.00, "currency": "USD"},
    "unrealized_gain_loss": {"amount": 4253.00, "currency": "USD"},
    "unrealized_gain_loss_percent": 28.35,
    "price_timestamp": "2025-12-29T21:00:00Z",
    "price_source": "alpha_vantage"
  }
]
```

## Definition of Done

- [ ] All success criteria met
- [ ] All tests passing
- [ ] Type checking passes
- [ ] Linting passes
- [ ] API endpoints return real market data
- [ ] Error handling verified
- [ ] PR created with clear description
- [ ] Progress document created
- [ ] Ready for frontend integration (Task 023 already complete!)

## Next Steps

After this task:
- **Frontend Integration**: Task 023 (Real Price Display UI) is already complete and will automatically work with this backend
- **Phase 2b**: Historical price queries for charts
- **Phase 3**: Backtesting with historical data

This task completes the **MVP for Phase 2a** - real-time portfolio valuation with live market data!
