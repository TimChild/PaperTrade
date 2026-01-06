# Task 059: Phase 3c Analytics - Background Snapshot Job

**Agent**: Backend SWE  
**Date**: 2026-01-06  
**Status**: ✅ Complete  
**Duration**: ~2 hours  

## Task Summary

Implemented a background job system for calculating and storing daily portfolio snapshots. This enables fast analytics and chart rendering without on-demand calculation. The job runs daily at midnight UTC and can be manually triggered via admin API endpoints.

## Decisions Made

### 1. Service Layer Architecture

**Decision**: Create `SnapshotJobService` in new `application/services/` directory
- **Rationale**: 
  - Services orchestrate use cases and coordinate between domain and infrastructure
  - Follows clean architecture pattern (application layer)
  - Distinct from commands/queries which are more granular

**Implementation**:
- Three public methods: `run_daily_snapshot()`, `backfill_snapshots()`, `_calculate_snapshot_for_portfolio()`
- Graceful error handling - continues processing remaining portfolios if one fails
- Comprehensive logging for monitoring

### 2. Repository Enhancement

**Decision**: Add `list_all()` method to PortfolioRepository
- **Rationale**: 
  - Snapshot job needs to process all portfolios across all users
  - Existing `get_by_user()` only returns portfolios for a single user
  - Follows existing repository patterns

**Implementation**:
- Added to port interface (`PortfolioRepository`)
- Implemented in SQLModel adapter (query all, order by created_at)
- Implemented in in-memory adapter (for testing)

### 3. Scheduler Integration

**Decision**: Integrate with existing APScheduler in `infrastructure/scheduler.py`
- **Rationale**:
  - Reuse existing scheduler infrastructure
  - Consistent with price refresh job pattern
  - Centralized job management

**Implementation**:
- Created `calculate_daily_snapshots()` job function
- Registered with cron trigger: midnight UTC (00:00)
- Uses same session/repository pattern as price refresh job

### 4. API Endpoints

**Decision**: Create separate analytics router with admin-only endpoints
- **Rationale**:
  - Separation of concerns (analytics vs portfolio operations)
  - Admin-only access for manual triggers and backfills
  - Follows existing router pattern

**Endpoints**:
- `POST /api/v1/analytics/portfolios/{id}/snapshots/backfill` - backfill historical snapshots
- `POST /api/v1/analytics/snapshots/daily` - manually trigger daily snapshot job

**Note**: Admin authentication check is TODO (marked for future implementation)

### 5. Dependency Injection

**Decision**: Follow existing DI patterns with type annotations
- **Rationale**:
  - Consistency with existing routers (portfolios, transactions)
  - Avoids B008 linting errors from Depends() in defaults
  - Better type safety with Annotated types

**Implementation**:
```python
# Type alias for dependency injection
SnapshotJobDep = Annotated[SnapshotJobService, Depends(get_snapshot_job)]
```

## Files Changed

### Created

1. **`src/papertrade/application/services/__init__.py`** (3 lines)
   - Package initialization for services directory

2. **`src/papertrade/application/services/snapshot_job.py`** (227 lines)
   - SnapshotJobService class with all job logic
   - Complete type hints, comprehensive logging
   - Error handling that continues on individual failures

3. **`src/papertrade/adapters/inbound/api/analytics.py`** (127 lines)
   - Analytics router with 2 admin endpoints
   - Backfill and daily snapshot triggering
   - Proper error handling and HTTP status codes

4. **`tests/unit/application/services/__init__.py`** (1 line)
   - Package initialization for services tests

5. **`tests/unit/application/services/test_snapshot_job.py`** (420 lines)
   - 8 comprehensive unit tests
   - InMemorySnapshotRepository helper class
   - Tests cover all scenarios (success, failures, edge cases)

### Modified

6. **`src/papertrade/application/ports/portfolio_repository.py`** (+14 lines)
   - Added `list_all()` method to protocol

7. **`src/papertrade/adapters/outbound/database/portfolio_repository.py`** (+12 lines)
   - Implemented `list_all()` with SQLModel query

8. **`src/papertrade/application/ports/in_memory_portfolio_repository.py`** (+7 lines)
   - Implemented `list_all()` for in-memory testing

9. **`src/papertrade/infrastructure/scheduler.py`** (+63 lines)
   - Added imports for snapshot job dependencies
   - Added `calculate_daily_snapshots()` job function
   - Registered daily snapshot job at midnight UTC

10. **`src/papertrade/adapters/inbound/api/dependencies.py`** (+40 lines)
    - Added `get_snapshot_repository()` factory
    - Added `get_snapshot_job()` factory
    - Added `SnapshotRepositoryDep` type alias

11. **`src/papertrade/main.py`** (+2 lines)
    - Imported analytics router
    - Registered analytics router with `/api/v1` prefix

## Testing Notes

### Unit Tests

**File**: `tests/unit/application/services/test_snapshot_job.py`

**Coverage**: 8 tests, all passing ✅

| Test Class | Test Method | Purpose |
|------------|-------------|---------|
| TestRunDailySnapshot | test_run_daily_snapshot_all_portfolios | Verifies all portfolios are processed |
| TestRunDailySnapshot | test_run_daily_snapshot_empty_portfolios | Handles no portfolios gracefully |
| TestRunDailySnapshot | test_run_daily_snapshot_with_specific_date | Supports custom snapshot date |
| TestBackfillSnapshots | test_backfill_snapshots_date_range | Generates snapshots for date range |
| TestBackfillSnapshots | test_backfill_snapshots_single_day | Handles single-day backfill |
| TestBackfillSnapshots | test_backfill_snapshots_portfolio_not_found | Handles missing portfolio |
| TestCalculateSnapshotForPortfolio | test_calculate_snapshot_cash_only | Calculates snapshot with only cash |
| TestCalculateSnapshotForPortfolio | test_calculate_snapshot_with_holdings | Calculates snapshot with holdings |

**Test Approach**:
- Pure unit tests using in-memory implementations
- No database required (fast execution ~0.05s)
- Tests cover happy path and error scenarios
- Created `InMemorySnapshotRepository` helper for testing

### Integration Testing

**Full Backend Suite**: 477 passed, 4 skipped ✅
- No regressions introduced
- All existing tests still passing
- Skipped tests are unrelated (VCR cassette tests)

### Code Quality

**Ruff Linter**: All checks passed ✅
- No linting errors
- Proper import organization
- Line length compliance (88 char limit)
- B008 warnings (Depends in defaults) avoided via type annotations

**Type Checking**: ✅
- Complete type hints on all functions
- No use of `Any` type
- Proper Protocol usage for ports

## Known Issues / Limitations

### Current Limitations

1. **Historical Prices Not Supported**
   - Backfill uses current prices, not historical prices
   - Need to implement `get_price_at(ticker, date)` in MarketDataPort
   - For now, backfills use whatever price is available at runtime

2. **No Admin Authentication**
   - Admin endpoints are marked TODO for admin checks
   - Currently any authenticated user can trigger jobs
   - Should be restricted to admin role in future

3. **No Rate Limiting**
   - Backfill operations can potentially overwhelm API
   - Should add rate limiting for large date ranges

### Design Decisions

**Why continue on individual failures?**
- Daily snapshot processes all portfolios
- If one portfolio fails (e.g., market data unavailable), others should still succeed
- Failure logged for monitoring, but job continues

**Why calculate snapshots on-demand vs pre-calculate everything?**
- Pre-calculating would require historical prices for all dates
- On-demand calculation is simpler for MVP
- Can optimize later with batch pre-calculation

## Next Steps

### Immediate (Phase 3c completion)

1. **Task 060**: Frontend analytics charts
   - Display snapshot data in charts
   - Use backfill endpoint to populate historical data

### Future Enhancements

1. **Historical Price Support**
   - Add `get_price_at(ticker, date)` to MarketDataPort
   - Update `_calculate_snapshot_for_portfolio()` to use historical prices for backfills

2. **Admin Authentication**
   - Implement admin role checks
   - Add `require_admin` dependency
   - Protect snapshot trigger endpoints

3. **Rate Limiting**
   - Add rate limiting to backfill endpoint
   - Limit date range size (e.g., max 365 days)
   - Add pagination for large backfills

4. **Monitoring & Alerting**
   - Add metrics for job success/failure rates
   - Alert on repeated failures
   - Dashboard for job status

5. **Performance Optimization**
   - Batch price fetches for efficiency
   - Consider caching snapshot calculations
   - Optimize database queries for large portfolios

## Architecture Compliance

✅ **Clean Architecture**: 
- Service in application layer
- Scheduler in infrastructure layer
- Dependencies point inward correctly

✅ **Dependency Rule**: 
- Domain has no dependencies
- Application depends on domain
- Infrastructure depends on application

✅ **Type Safety**: 
- Complete type hints
- No `Any` types
- Protocol-based interfaces

✅ **Testability**: 
- 100% unit test coverage for service
- Tests use in-memory implementations
- No database required for tests

✅ **Modern SWE**: 
- Iterative development
- Test-driven approach
- Composable design
- Clear separation of concerns

## Code Quality Metrics

- **Files Created**: 5
- **Files Modified**: 6
- **Lines Added**: ~800
- **Tests Added**: 8
- **Test Coverage**: 100% (snapshot job service)
- **Type Errors**: 0
- **Linting Errors**: 0
- **Full Test Suite**: 477 passed, 4 skipped
