# Task 073: Fix Historical Data Seeding Script

**Date**: 2026-01-08
**Agent**: backend-swe
**Status**: ✅ Complete

## Summary

Fixed critical issues preventing the `backend/scripts/seed_historical_data.py` script from functioning properly. The script now successfully runs without errors, exits cleanly, and can be used to seed historical price data for backtesting features.

## Problems Addressed

### 1. MockRedis Missing `eval()` Method
**Issue**: Custom `MockRedis` class was incomplete and missing the `eval()` method required by RateLimiter for executing Lua scripts atomically.

**Error**:
```
AttributeError: 'MockRedis' object has no attribute 'eval'
```

**Solution**: Replaced custom `MockRedis` class with `fakeredis.FakeRedis()` which is already a dev dependency and provides full Redis API compatibility including Lua script execution support.

### 2. Script Hanging on Exit
**Issue**: Database engine connections weren't properly disposed, causing the script to hang after completion and require Ctrl+C to exit.

**Solution**: Added proper cleanup by calling `await engine.dispose()` before script exit to close all database connections.

### 3. Environment Variables Not Loaded
**Issue**: Script didn't automatically load `.env` file, requiring manual environment variable setup.

**Solution**: Added `load_dotenv()` call at the start of `main()` to automatically load environment variables from repository root `.env` file.

## Changes Made

### backend/scripts/seed_historical_data.py

#### Imports
```python
# Added
from dotenv import load_dotenv
from fakeredis import aioredis as fakeredis
from papertrade.infrastructure.database import async_session_maker, engine, init_db  # Added 'engine'
```

#### Environment Loading
```python
async def main() -> None:
    """Run historical data seeding."""
    # Load environment variables from .env file
    load_dotenv()  # ← NEW

    # ... rest of function
```

#### MockRedis Replacement
```python
# BEFORE (lines 127-137):
class MockRedis:
    """Mock Redis client for script usage."""

    async def get(self, key: str) -> None:
        return None

    async def setex(self, key: str, ttl: int, value: str) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass

redis_client = MockRedis()

# AFTER (line 132):
redis_client = await fakeredis.FakeRedis()
```

#### Database Engine Disposal
```python
# Added before script exit (line 176):
await engine.dispose()
```

### backend/scripts/verify_historical_data.py (NEW)

Created verification script to check that historical data was successfully seeded:

```python
"""Verify historical price data in the database.

This script checks if historical price data was successfully seeded
in the database and displays a sample of the data.
"""
```

Features:
- Counts total price records in database
- Displays sample of 10 most recent price records
- Lists all tickers with available data
- Provides helpful message if no data found

## Testing

### Script Functionality
```bash
cd backend
uv run python scripts/seed_historical_data.py --tickers IBM --days 3
# ✓ Runs without errors
# ✓ Exits cleanly with code 0
# ✓ No hanging, no Ctrl+C needed
```

### Quality Checks
```bash
# Ruff linter
uv run ruff check scripts/
# ✓ All checks passed!

# Ruff formatter
uv run ruff format --check scripts/
# ✓ All files formatted correctly

# Pyright type checker
uv run pyright scripts/seed_historical_data.py scripts/verify_historical_data.py
# ✓ 0 errors, 0 warnings, 0 informations
```

### Regression Testing
```bash
uv run pytest tests/ -v
# ✓ 501 passed, 4 skipped
# ✓ All existing tests still pass
```

## Verification

The script now properly:

1. **Loads environment variables** - `ALPHA_VANTAGE_API_KEY` automatically loaded from `.env`
2. **Works with RateLimiter** - fakeredis provides full Redis API including `eval()` for Lua scripts
3. **Exits cleanly** - Database engine properly disposed, no hanging processes
4. **Type-safe** - All type checks pass with strict pyright configuration
5. **Well-formatted** - Passes all ruff linting and formatting checks

## Usage

### Seed Historical Data
```bash
# With demo API key (IBM ticker only)
cd backend
uv run python scripts/seed_historical_data.py --tickers IBM --days 3

# With real API key (any supported ticker)
ALPHA_VANTAGE_API_KEY=your_key uv run python scripts/seed_historical_data.py --days 30

# Via task
task db:seed:historical-data -- --days 30
```

### Verify Data Seeding
```bash
cd backend
uv run python scripts/verify_historical_data.py
```

## Files Modified

1. `backend/scripts/seed_historical_data.py` - Main fixes
2. `backend/scripts/verify_historical_data.py` - New verification script

## Dependencies

All required dependencies already present:
- ✅ `python-dotenv` - Already installed
- ✅ `fakeredis[lua]` - Already in dev dependencies

## Success Criteria

- [x] Script runs without errors with demo API key and IBM ticker
- [x] Script runs without errors with real API key and default tickers
- [x] MockRedis or alternative solution works with RateLimiter
- [x] Database engine properly disposed, no hanging
- [x] Environment variables loaded automatically from .env
- [x] Script exits cleanly with exit code 0
- [x] All existing tests still pass (501 tests)
- [x] Added verification script to confirm data seeding works
- [x] All code quality checks pass (ruff, pyright)

## Notes

- The script uses fakeredis for this one-off script instead of real Redis
- Rate limiting is handled by 12-second delays between tickers (5 calls/min)
- Demo API key only works with IBM ticker
- The backtesting feature (Phase 3c) now has a working data seeding script

## Related Documentation

- Original issue: Task 073 in BACKLOG.md
- RateLimiter: `backend/src/papertrade/infrastructure/rate_limiter.py`
- Database setup: `backend/src/papertrade/infrastructure/database.py`
- Alpha Vantage adapter: `backend/src/papertrade/adapters/outbound/market_data/alpha_vantage_adapter.py`
