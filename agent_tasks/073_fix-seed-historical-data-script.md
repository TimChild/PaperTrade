# Task 073: Fix Historical Data Seeding Script

**Agent**: backend-swe  
**Priority**: High  
**Estimated Effort**: 2-3 hours  

## Objective

Fix the `backend/scripts/seed_historical_data.py` script so it can successfully fetch and store historical price data from Alpha Vantage API without errors or hanging.

## Context

The backtesting feature (Phase 3c) requires historical price data to be seeded in the database. The current seed script has multiple issues preventing it from working:

1. **MockRedis incomplete**: Missing `eval()` method needed by RateLimiter
2. **Script hangs at end**: Database engine not properly disposed, requires Ctrl+C to exit
3. **Environment loading**: Doesn't load .env file automatically

Current error when running:
```
✗ Error: 'MockRedis' object has no attribute 'eval'
```

## Requirements

### 1. Fix MockRedis Implementation

The MockRedis class needs to implement the `eval()` method used by RateLimiter:

**Current code** (lines 127-136):
```python
class MockRedis:
    """Mock Redis client for script usage."""

    async def get(self, key: str) -> None:
        return None

    async def setex(self, key: str, ttl: int, value: str) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass
```

**Required**: Add `eval()` method that the RateLimiter expects. Check `backend/src/papertrade/infrastructure/rate_limiter.py` to see how it's used.

**Alternative approach**: Since this is a one-off script with manual 12-second delays between API calls, consider bypassing the RateLimiter entirely by creating a simpler adapter or mocking it differently.

### 2. Fix Database Engine Disposal

The script hangs after completion because the SQLAlchemy engine isn't properly disposed.

**Current**: Script just ends after printing success message
**Required**: Properly dispose the database engine before exit

Suggested fix:
```python
from papertrade.infrastructure.database import engine

# At end of main(), before final print:
await engine.dispose()
```

### 3. Load Environment Variables

Add automatic .env file loading so API key is available:

```python
from dotenv import load_dotenv

# At top of main():
load_dotenv()  # Load from repository root .env
```

### 4. Improve Error Handling

- Catch and report API errors gracefully
- Show meaningful messages for common failures (rate limit, invalid ticker, network errors)
- Don't let one ticker failure stop the entire script

### 5. Testing Requirements

**CRITICAL**: Thoroughly test the script before submitting PR:

1. **With Demo API Key** (if real key not available):
   - Test with `IBM` ticker only (demo key supports this)
   - Run: `uv run python scripts/seed_historical_data.py --tickers IBM --days 3`
   - Verify it fetches data successfully
   - Verify script exits cleanly (no hanging, no Ctrl+C needed)

2. **With Real API Key** (if available):
   - Test with default tickers: `AAPL,MSFT,GOOGL,TSLA,NVDA`
   - Run: `uv run python scripts/seed_historical_data.py --days 3`
   - Verify all tickers fetch successfully
   - Verify script exits cleanly

3. **Verify Database Storage**:
   - After running script, check data is in database:
   ```python
   # Quick verification script
   from papertrade.infrastructure.database import async_session_maker
   from sqlalchemy import select
   from papertrade.adapters.outbound.repositories.models import PriceHistoryModel
   
   async with async_session_maker() as session:
       result = await session.execute(
           select(PriceHistoryModel).limit(10)
       )
       prices = result.scalars().all()
       print(f"Found {len(prices)} price records")
       for p in prices:
           print(f"  {p.ticker}: ${p.price_amount} at {p.timestamp}")
   ```

4. **Clean Exit Test**:
   - Script must exit with code 0
   - No "Exception ignored in threading" messages
   - No need for Ctrl+C

## Success Criteria

- [ ] Script runs without errors with demo API key and IBM ticker
- [ ] Script runs without errors with real API key and default tickers
- [ ] MockRedis or alternative solution works with RateLimiter
- [ ] Database engine properly disposed, no hanging
- [ ] Environment variables loaded automatically from .env
- [ ] Historical price data successfully stored in database
- [ ] Script exits cleanly with exit code 0
- [ ] All existing tests still pass
- [ ] Added test or verification script to confirm data seeding works

## Files to Modify

- `backend/scripts/seed_historical_data.py` - Main fixes
- `backend/pyproject.toml` - Add `python-dotenv` if not already there

## Testing Commands

```bash
# Test with demo key and IBM
cd backend
uv run python scripts/seed_historical_data.py --tickers IBM --days 3

# Test with real key and multiple tickers
ALPHA_VANTAGE_API_KEY=your_key uv run python scripts/seed_historical_data.py --days 3

# Via task (after fixing)
task db:seed:historical-data -- --days 3
```

## References

- RateLimiter: `backend/src/papertrade/infrastructure/rate_limiter.py`
- Database setup: `backend/src/papertrade/infrastructure/database.py`
- Alpha Vantage adapter: `backend/src/papertrade/adapters/outbound/market_data/alpha_vantage_adapter.py`

## Notes

- The script is used for development/testing, not production
- Rate limiting is handled by 12-second delays between tickers, so RateLimiter might be overkill
- Demo API key only works with IBM ticker, test with that if no real key available
- The backtesting feature depends on this data being available
