# Task 159: Fix Backend Weekend Price Fetching

**Agent**: backend-swe
**Priority**: Critical
**Estimated Effort**: 2-3 hours
**Created**: 2026-01-18

## Problem Statement

**Confirmed Bug**: On weekends, the backend returns "Ticker not found" errors instead of serving cached prices from the last trading day.

**Manual Test Results** (Sunday, Jan 18, 2026):
```bash
# Single ticker endpoint
curl "http://localhost:8000/api/v1/prices/AAPL"
→ {"detail":"Ticker not found: AAPL"}  ❌

# Batch endpoint
curl "http://localhost:8000/api/v1/prices/batch?tickers=AAPL"
→ {"prices": {}, "requested": 1, "returned": 0}  ❌

# Database has cached data from Friday
psql> SELECT ticker, timestamp, price_amount FROM price_history
      WHERE ticker = 'AAPL' ORDER BY timestamp DESC LIMIT 1;
→ AAPL | 2026-01-15 01:36:08 | 259.96  ✅
```

**Impact**:
- Trade form shows "Unable to fetch market data" on weekends
- Batch prices returns empty → Frontend Total Value shows only cash
- Poor user experience on 2/7 days of the week

## Root Cause Analysis

The backend **has** the correct infrastructure:
- ✅ `_get_last_trading_day()` helper in `AlphaVantageAdapter` (line 762)
- ✅ `MarketCalendar.is_trading_day()` for weekend/holiday detection
- ✅ 3-tier caching (Redis → PostgreSQL → Alpha Vantage API)
- ✅ Database contains cached prices from Friday

**The problem**: The weekend logic isn't being applied in the price fetching flow.

When `get_current_price` is called on Sunday:
1. ✅ Checks Redis cache (empty or expired)
2. ✅ Checks PostgreSQL for recent data (finds Friday's price but considers it "too old")
3. ❌ Tries to fetch from Alpha Vantage API
4. ❌ API returns data indicating markets closed
5. ❌ Backend interprets as "Ticker not found" error instead of falling back to cached data

**Expected behavior**: On weekends, should automatically use last trading day's cached price.

## Required Changes

### 1. Fix `get_current_price()` Weekend Handling

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

**Current Code** (Lines 114-196):
```python
async def get_current_price(self, ticker: Ticker) -> PricePoint:
    # Tier 1: Check Redis cache
    cached = await self.price_cache.get(ticker)
    if cached and not cached.is_stale(max_age=timedelta(hours=1)):
        return cached.with_source("cache")

    # Tier 2: Check PostgreSQL
    if self.price_repository:
        db_price = await self.price_repository.get_latest_price(
            ticker, max_age=timedelta(hours=4)
        )
        if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
            await self.price_cache.set(db_price, ttl=3600)
            return db_price.with_source("database")

    # Tier 3: Fetch from Alpha Vantage API
    # (tries to fetch even on weekends)
```

**Fix**: Add weekend/holiday check before attempting API fetch:

```python
async def get_current_price(self, ticker: Ticker) -> PricePoint:
    """Get the most recent available price for a ticker.

    Implements tiered caching strategy with weekend/holiday awareness:
    1. Check Redis cache (return if fresh)
    2. Check PostgreSQL (return if reasonably fresh)
    3. **NEW**: If weekend/holiday, get last trading day's cached price
    4. Fetch from Alpha Vantage API (if rate limit allows)
    5. Serve stale cached data if rate limited

    Args:
        ticker: Stock ticker symbol to get price for

    Returns:
        PricePoint with latest available price

    Raises:
        TickerNotFoundError: Ticker doesn't exist in data source
        MarketDataUnavailableError: Cannot fetch price and no cached data available
    """
    from datetime import UTC, datetime

    # Tier 1: Check Redis cache
    cached = await self.price_cache.get(ticker)
    if cached and not cached.is_stale(max_age=timedelta(hours=1)):
        # Fresh cached data, return it
        return cached.with_source("cache")

    # Tier 2: Check PostgreSQL
    if self.price_repository:
        db_price = await self.price_repository.get_latest_price(
            ticker, max_age=timedelta(hours=4)
        )
        if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
            # Warm the cache with database price
            await self.price_cache.set(db_price, ttl=3600)
            return db_price.with_source("database")

    # NEW: Weekend/Holiday Check - Don't fetch from API if markets are closed
    now = datetime.now(UTC)
    if not MarketCalendar.is_trading_day(now.date()):
        # Markets are closed - get last trading day's cached price
        last_trading_day = self._get_last_trading_day(now)

        if self.price_repository:
            # Get price at last trading day's close (21:00 UTC = 4:00 PM ET)
            historical_price = await self.price_repository.get_price_at(
                ticker, last_trading_day
            )
            if historical_price:
                # Warm cache with last trading day price (longer TTL on weekends)
                await self.price_cache.set(historical_price, ttl=7200)  # 2 hours
                return historical_price.with_source("database")

        # Fallback: Check if we have any stale cached data
        if cached:
            return cached.with_source("cache")

        # No data available for this ticker
        raise TickerNotFoundError(
            f"No cached data available for {ticker.symbol} (markets closed)"
        )

    # Tier 3: Fetch from Alpha Vantage API (only on trading days)
    if not await self.rate_limiter.can_make_request():
        # Rate limited - serve stale data if available
        if cached:
            return cached.with_source("cache")

        wait_time = await self.rate_limiter.wait_time()
        raise MarketDataUnavailableError(
            f"Rate limit exceeded. No cached data available. "
            f"Retry in {wait_time:.0f} seconds."
        )

    # Consume rate limit token before making API call
    consumed = await self.rate_limiter.consume_token()
    if not consumed:
        if cached:
            return cached.with_source("cache")
        raise MarketDataUnavailableError("Rate limit exceeded, no cached data")

    # Make API request
    try:
        price = await self._fetch_from_api(ticker)

        # Store in cache for future requests
        await self.price_cache.set(price, ttl=3600)  # 1 hour TTL

        # Store in database for Tier 2 caching
        if self.price_repository:
            await self.price_repository.upsert_price(price)

        return price

    except Exception:
        # API call failed - serve stale cached data if available
        if cached:
            return cached.with_source("cache")

        # No fallback available, re-raise the error
        raise
```

### 2. Fix `get_batch_prices()` Weekend Handling

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

**Current Code** (Lines 198-280): Batch fetching doesn't check for weekends before fetching uncached tickers.

**Fix**: Add weekend check in batch loop:

```python
async def get_batch_prices(self, tickers: list[Ticker]) -> dict[Ticker, PricePoint]:
    """Get current prices for multiple tickers in a single batch request.

    With weekend/holiday awareness - fetches from cache/database instead
    of attempting API calls when markets are closed.

    Args:
        tickers: List of stock ticker symbols to get prices for

    Returns:
        Dictionary mapping tickers to their price points.
    """
    from datetime import UTC, datetime

    result: dict[Ticker, PricePoint] = {}

    if not tickers:
        return result

    # Check if today is a trading day
    now = datetime.now(UTC)
    is_trading_day = MarketCalendar.is_trading_day(now.date())
    last_trading_day = None if is_trading_day else self._get_last_trading_day(now)

    # Step 1: Check cache for all tickers
    uncached_tickers: list[Ticker] = []
    for ticker in tickers:
        cached = await self.price_cache.get(ticker)
        if cached and not cached.is_stale(max_age=timedelta(hours=1)):
            result[ticker] = cached.with_source("cache")
        else:
            uncached_tickers.append(ticker)

    # Step 2: Check database for uncached tickers
    if self.price_repository and uncached_tickers:
        db_uncached: list[Ticker] = []
        for ticker in uncached_tickers:
            if not is_trading_day and last_trading_day:
                # Weekend/Holiday: Get last trading day's price
                db_price = await self.price_repository.get_price_at(
                    ticker, last_trading_day
                )
            else:
                # Trading day: Get latest price (4 hour max age)
                db_price = await self.price_repository.get_latest_price(
                    ticker, max_age=timedelta(hours=4)
                )

            if db_price:
                # Warm the cache
                ttl = 7200 if not is_trading_day else 3600  # Longer TTL on weekends
                await self.price_cache.set(db_price, ttl=ttl)
                result[ticker] = db_price.with_source("database")
            else:
                db_uncached.append(ticker)

        uncached_tickers = db_uncached

    # Step 3: Fetch from API (only on trading days)
    if uncached_tickers and is_trading_day:
        # Only fetch from API if markets are open
        for ticker in uncached_tickers:
            try:
                price = await self.get_current_price(ticker)
                result[ticker] = price
            except (TickerNotFoundError, MarketDataUnavailableError):
                # Skip ticker if fetch fails
                continue

    # If markets are closed and we have uncached tickers, they won't be in result
    # (This is expected - no data available)

    return result
```

### 3. Add Logging for Weekend Behavior

Add structured logging to help debug weekend behavior:

```python
# In get_current_price(), after weekend check:
if not MarketCalendar.is_trading_day(now.date()):
    logger.info(
        "Markets closed, using last trading day price",
        ticker=ticker.symbol,
        current_date=now.date().isoformat(),
        last_trading_day=last_trading_day.date().isoformat(),
    )
```

## Testing Requirements

### Unit Tests

**File**: `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py`

```python
@pytest.mark.asyncio
async def test_get_current_price_on_weekend(mocker):
    """Test that get_current_price returns cached price on weekends."""
    # Mock today as Sunday, Jan 18, 2026
    mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)  # Sunday 3PM UTC
    mocker.patch('zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime')
    mocker.patch.object(
        alpha_vantage_adapter.datetime, 'now', return_value=mock_now
    )

    # Mock MarketCalendar to return False for Sunday
    mocker.patch(
        'zebu.adapters.outbound.market_data.alpha_vantage_adapter.MarketCalendar.is_trading_day',
        return_value=False
    )

    # Setup: Cached Friday price exists in database
    friday_price = PricePoint(
        ticker=Ticker("AAPL"),
        price=Money(Decimal("259.96"), "USD"),
        timestamp=datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),  # Friday close
        source="database",
        interval="1day",
    )

    mock_repo = mocker.Mock()
    mock_repo.get_price_at.return_value = friday_price

    adapter = AlphaVantageAdapter(
        api_key="test_key",
        price_repository=mock_repo,
        rate_limiter=mocker.Mock(),
        price_cache=mocker.Mock(),
    )
    adapter.price_cache.get.return_value = None  # No Redis cache

    # Execute
    result = await adapter.get_current_price(Ticker("AAPL"))

    # Assert
    assert result.price.amount == Decimal("259.96")
    assert result.source == "database"
    mock_repo.get_price_at.assert_called_once()
    # Verify it didn't try to fetch from API
    assert mock_repo.get_latest_price.call_count == 0


@pytest.mark.asyncio
async def test_get_batch_prices_on_weekend(mocker):
    """Test batch prices returns cached data on weekends."""
    # Mock Sunday
    mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)
    mocker.patch.object(datetime, 'now', return_value=mock_now)
    mocker.patch(
        'zebu.adapters.outbound.market_data.alpha_vantage_adapter.MarketCalendar.is_trading_day',
        return_value=False
    )

    # Setup cached prices for multiple tickers
    friday_prices = {
        Ticker("AAPL"): PricePoint(...),
        Ticker("MSFT"): PricePoint(...),
    }

    mock_repo = mocker.Mock()
    mock_repo.get_price_at.side_effect = lambda t, d: friday_prices.get(t)

    adapter = AlphaVantageAdapter(...)

    # Execute
    result = await adapter.get_batch_prices([Ticker("AAPL"), Ticker("MSFT")])

    # Assert
    assert len(result) == 2
    assert Ticker("AAPL") in result
    assert Ticker("MSFT") in result
    # Should not have attempted API fetch
    assert mock_repo.get_latest_price.call_count == 0
```

### Integration Tests

**File**: `backend/tests/integration/test_prices_api.py`

```python
def test_get_current_price_weekend_returns_cached(client, db, mocker):
    """Verify /prices/{ticker} returns Friday's price on Sunday."""
    # Setup: Insert Friday's price into database
    # (Use existing test fixtures)

    # Mock current time as Sunday
    with freeze_time("2026-01-18 15:00:00"):  # Sunday
        response = client.get("/api/v1/prices/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["price"] == "259.96"  # Friday's price
        assert data["source"] in ["cache", "database"]
        # Timestamp should be from Friday
        timestamp = datetime.fromisoformat(data["timestamp"])
        assert timestamp.date() == date(2026, 1, 16)  # Friday


def test_batch_prices_weekend_returns_cached(client, db):
    """Verify /prices/batch returns cached prices on Sunday."""
    with freeze_time("2026-01-18 15:00:00"):  # Sunday
        response = client.get("/api/v1/prices/batch?tickers=AAPL,MSFT")

        assert response.status_code == 200
        data = response.json()
        assert data["requested"] == 2
        assert data["returned"] == 2  # Should return both from cache
        assert "AAPL" in data["prices"]
        assert "MSFT" in data["prices"]
```

### Manual Testing (Weekend)

**Test on Sunday, Jan 18, 2026** (after fix is deployed):

```bash
# 1. Single ticker should return Friday's price
curl "http://localhost:8000/api/v1/prices/AAPL" | jq
# Expected:
# {
#   "ticker": "AAPL",
#   "price": "259.96",
#   "timestamp": "2026-01-16T21:00:00Z",  # Friday close
#   "source": "database"
# }

# 2. Batch prices should work
curl "http://localhost:8000/api/v1/prices/batch?tickers=AAPL,MSFT" | jq
# Expected:
# {
#   "prices": {
#     "AAPL": { "price": "259.96", ... },
#     "MSFT": { "price": "123.45", ... }
#   },
#   "requested": 2,
#   "returned": 2
# }

# 3. Verify no API calls on weekends (check logs)
docker compose logs backend | grep "alpha_vantage"
# Should show NO new API calls on Sunday
```

## Success Criteria

- [ ] `get_current_price()` returns cached price on weekends (no API calls)
- [ ] `get_batch_prices()` returns cached prices on weekends
- [ ] Markets closed on holidays (MLK Day, etc.) also use cached prices
- [ ] No "Ticker not found" errors when cached data exists
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual testing confirms weekend behavior
- [ ] Logging shows "Markets closed" messages on weekends
- [ ] No Alpha Vantage API calls made on weekends/holidays

## Files to Modify

- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` - Add weekend checks
- `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py` - Add weekend tests
- `backend/tests/integration/test_prices_api.py` - Add weekend integration tests

## References

- `MarketCalendar.is_trading_day()`: `backend/src/zebu/infrastructure/market_calendar.py`
- `_get_last_trading_day()`: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py:762`
- Current price endpoint: `backend/src/zebu/adapters/inbound/api/prices.py:202`

## Architecture Compliance

- ✅ Clean Architecture: Business logic in domain/application layers
- ✅ No changes to API contracts (transparent to frontend)
- ✅ Proper error handling with fallbacks
- ✅ Structured logging for observability
- ✅ Type safety maintained
- ✅ Repository pattern for data access

## Notes

- This fix is **backend only** - no frontend changes needed
- API contract stays the same - existing frontend code will automatically work better
- Frontend Task 158 is complementary (UI improvements)
- After this fix, weekend user experience will match weekday experience
