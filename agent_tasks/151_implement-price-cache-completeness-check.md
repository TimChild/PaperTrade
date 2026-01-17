# Task 151: Implement Price Cache Completeness Check

**Agent**: backend-swe  
**Priority**: High  
**Type**: Bug Fix + Enhancement  
**Depends On**: Task 150 (✅ Complete)  
**Related**: PR #137 (observability improvements merged)

## Objective

Fix the incomplete price data bug by implementing cache completeness validation before returning cached data. This implements **Option A** from the Task 150 analysis document.

## Context

**Root Cause** (identified in Task 150):
- Lines 529-531 in `alpha_vantage_adapter.py` return ANY cached data without validating completeness
- Frontend requests Jan 10-17 (8 days) → Database has only Jan 12 → Returns 1 point instead of fetching missing 6 days
- Users see incomplete charts with mysterious gaps

**Why This Approach**:
- Option A (completeness check) approved by orchestrator
- Respects Alpha Vantage rate limits (5 calls/min, 500/day)
- Minimal complexity, graceful degradation
- Migration path provided

## Requirements

### 1. Implement Cache Completeness Check

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

**Changes**:
1. Add `_is_cache_complete()` helper method (see implementation spec below)
2. Modify `get_price_history()` to validate cache before returning
3. Add structured logging for cache hit/miss decisions

**Implementation Spec** (from Task 150 analysis):

```python
async def get_price_history(
    self,
    ticker: Ticker,
    start: datetime,
    end: datetime,
    interval: str = "1day",
) -> list[PricePoint]:
    # ... (existing validation code)
    
    # Try to get cached data first
    cached_history = await self.price_repository.get_price_history(
        ticker, start, end, interval
    )
    
    # Check if cached data is complete for requested range
    if cached_history and interval == "1day":
        if self._is_cache_complete(cached_history, start, end):
            logger.info(
                "Returning complete cached data",
                extra={
                    "ticker": ticker.symbol,
                    "cached_points": len(cached_history),
                    "date_range": f"{start.date()} to {end.date()}",
                }
            )
            return cached_history
        else:
            logger.info(
                "Cached data incomplete, fetching from API",
                extra={
                    "ticker": ticker.symbol,
                    "cached_points": len(cached_history),
                    "requested_range": f"{start.date()} to {end.date()}",
                    "cached_range": f"{cached_history[0].timestamp.date()} to {cached_history[-1].timestamp.date()}",
                }
            )
            # Fall through to API fetch
    
    # No cached data or incomplete - fetch from API
    if interval == "1day":
        # ... (existing API fetch logic)
    
    # For other intervals, return cached data or empty
    return cached_history or []

def _is_cache_complete(
    self,
    cached_data: list[PricePoint],
    start: datetime,
    end: datetime,
) -> bool:
    """Check if cached data is complete for the requested date range.
    
    For daily data, validates:
    1. Boundary coverage: Cache spans from start to end (±1 day tolerance)
    2. Density check: Has at least 70% of expected trading days (for ranges ≤30 days)
    
    Args:
        cached_data: List of cached price points (assumed sorted by timestamp)
        start: Start of requested range (UTC)
        end: End of requested range (UTC)
    
    Returns:
        True if cached data appears complete, False if likely incomplete
    """
    if not cached_data:
        return False
    
    # Get boundary timestamps
    first_cached = cached_data[0].timestamp.replace(tzinfo=UTC)
    last_cached = cached_data[-1].timestamp.replace(tzinfo=UTC)
    
    # Check boundary coverage (allow 1-day tolerance for timezone/market timing)
    if first_cached > start + timedelta(days=1):
        logger.debug(
            "Cache incomplete: missing early dates",
            extra={
                "first_cached": first_cached.date().isoformat(),
                "requested_start": start.date().isoformat(),
            }
        )
        return False
    
    if last_cached < end - timedelta(days=1):
        logger.debug(
            "Cache incomplete: missing recent dates",
            extra={
                "last_cached": last_cached.date().isoformat(),
                "requested_end": end.date().isoformat(),
            }
        )
        return False
    
    # For short date ranges (≤30 days), verify density
    # This catches major gaps in the middle of the range
    days_requested = (end - start).days
    if days_requested <= 30:
        # Estimate expected trading days (rough: 5/7 of calendar days)
        expected_trading_days = days_requested * 5 / 7
        # Require at least 70% of expected days (allows for holidays, minor gaps)
        min_required_points = int(expected_trading_days * 0.7)
        
        if len(cached_data) < min_required_points:
            logger.debug(
                "Cache incomplete: insufficient density",
                extra={
                    "cached_points": len(cached_data),
                    "min_required": min_required_points,
                    "days_requested": days_requested,
                }
            )
            return False
    
    # Cache appears complete
    return True
```

### 2. Comprehensive Testing

**File**: `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py`

**Required Test Scenarios**:

1. **Complete cache** - returns cached data
   ```python
   # Cache has Jan 10-17 (full range)
   # Request Jan 12-15
   # Expected: Return cached data (no API call)
   ```

2. **Empty cache** - fetches from API
   ```python
   # Cache is empty
   # Request Jan 10-17
   # Expected: Fetch from API
   ```

3. **Partial cache (missing early dates)** - fetches from API
   ```python
   # Cache has Jan 15-17 only
   # Request Jan 10-17
   # Expected: Fetch from API (cache incomplete)
   ```

4. **Partial cache (missing recent dates)** - fetches from API
   ```python
   # Cache has Jan 10-12 only
   # Request Jan 10-17
   # Expected: Fetch from API (cache incomplete)
   ```

5. **Partial cache (sparse/gaps in middle)** - fetches from API
   ```python
   # Cache has Jan 10, 11, 17 (missing 12-16)
   # Request Jan 10-17
   # Expected: Fetch from API (insufficient density)
   ```

6. **Boundary tolerance** - returns cached data
   ```python
   # Cache has Jan 11-16 (1 day tolerance on each side)
   # Request Jan 10-17
   # Expected: Return cached data (within tolerance)
   ```

7. **Long date range** (>30 days) - less strict validation
   ```python
   # Cache has most but not all days over 60-day range
   # Expected: Return cached data (density check only for ≤30 days)
   ```

**Test Structure**:
```python
async def test_cache_completeness_partial_early_dates_missing(
    alpha_vantage_adapter,
    mock_price_repository,
):
    """Should fetch from API when cache is missing early dates."""
    # Arrange
    ticker = Ticker("AAPL")
    start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)
    
    # Cache only has Jan 15-17 (missing Jan 10-14)
    cached_data = [
        PricePoint(ticker=ticker, timestamp=datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC), ...),
        PricePoint(ticker=ticker, timestamp=datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC), ...),
        PricePoint(ticker=ticker, timestamp=datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC), ...),
    ]
    mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)
    
    # Mock API response (will be called because cache incomplete)
    mock_api_response = {...}  # Full data
    
    # Act
    result = await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")
    
    # Assert
    # Should NOT return partial cache
    assert len(result) > 3, "Should fetch from API, not return incomplete cache"
    # Verify API was called
    assert mock_rate_limiter.consume_token.called
```

**Integration Test**:
```python
# File: backend/tests/integration/adapters/test_alpha_vantage_adapter.py

async def test_partial_cache_fetches_from_api(session):
    """Integration: Partial cache triggers API fetch."""
    # 1. Seed database with partial data (Jan 15-17 only)
    # 2. Request Jan 10-17
    # 3. Verify API is called (check rate limiter consumed token)
    # 4. Verify result has full date range
```

### 3. Validation & Monitoring

**Before Deployment**:
- Run `task quality:backend` (format, lint, test)
- Verify all 7 test scenarios pass
- Check coverage for `_is_cache_complete()` method (should be 100%)

**After Deployment**:
- Monitor logs for "Cached data incomplete" messages
- Check debug endpoint `/api/v1/debug/price-cache/{ticker}` shows no gaps
- Verify frontend displays complete data for TSLA and MU

## Success Criteria

1. ✅ `_is_cache_complete()` method implemented with proper validation
2. ✅ All 7 test scenarios pass (unit tests)
3. ✅ Integration test passes
4. ✅ CI passes (format, lint, type check, tests)
5. ✅ Code coverage 80%+ for new code
6. ✅ Structured logging uses `extra={}` (compatible with future structlog migration)
7. ✅ Production verification: TSLA and MU show 5-7 data points for last week

## Quality Standards

### Architecture
- ✅ Clean Architecture maintained (no domain → infrastructure dependencies)
- ✅ Changes isolated to adapter layer
- ✅ Repository interface unchanged

### Code Quality
- ✅ Complete type hints (no `Any`)
- ✅ Docstrings for `_is_cache_complete()` method
- ✅ Structured logging with `extra={}` dicts
- ✅ No ESLint/Pyright suppressions

### Testing
- ✅ Behavior-focused tests (test what system does, not how)
- ✅ No mocking internal logic (only mock repository and rate limiter)
- ✅ Test names describe scenarios, not implementation
- ✅ Edge cases covered (empty cache, boundaries, sparse data)

## References

- **Analysis Document**: `agent_progress_docs/2026-01-17_19-42-08_price-history-observability-analysis.md`
- **Option A Detailed Spec**: Lines 600-700 in analysis doc
- **Test Scenarios**: Lines 800-1000 in analysis doc
- **Current Code**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` (lines 475-565)

## Constraints

- **Alpha Vantage Rate Limits**: 5 calls/min, 500/day
- **Compact Output**: Max 100 trading days (~4-5 months)
- **Backwards Compatibility**: Don't break existing API contracts

## Out of Scope

- ❌ TTL-based cache invalidation (defer to future task)
- ❌ Trading day calendar integration (heuristic is sufficient)
- ❌ Migration to structlog (separate task 152)
- ❌ Metrics/monitoring infrastructure (separate task)

## Estimated Effort

- Implementation: 4-6 hours
- Testing: 4-6 hours
- Validation: 1-2 hours
- **Total**: ~10-14 hours

## Notes

- Use existing structured logging pattern (standard library `logging` with `extra={}`)
- Follow migration path from analysis doc (deploy with monitoring, validate behavior)
- Consider adding feature flag if you want ability to disable completeness check
