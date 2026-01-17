# Resume From Here: Price History Data Completeness Issue

**Date**: January 17, 2026
**Status**: ✅ Root cause fixed (observability deployed), implementation task created
**Priority**: High - User-facing data accuracy issue (fix ready for implementation)

---

## Problem Statement

Frontend displays incomplete historical price data:
- **AAPL**: Shows 6 data points ✅ (correct)
- **TSLA**: Shows only 2 data points ❌ (should be ~7 for last week)
- **MU**: Shows only 2 data points ❌ (should be ~7 for last week)

**User Impact**: Stock price charts show insufficient historical data for analysis.

---

## Root Cause Identified ✅

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
**Lines**: 529-531

```python
# If we have data, return it
if history:
    return history
```

**The Bug**: Caching logic returns **any** cached data immediately without checking if it covers the full requested date range.

**How it Breaks**:
1. First backfill (Jan 12): Fetches from API → stores Jan 12 data for all tickers
2. Second backfill (Jan 17): Queries database for Jan 10-17 range → finds Jan 12 data → returns immediately
3. Result: Never fetches missing Jan 13, 14, 15, 16, 17 data
4. Frontend requests same range → gets same incomplete cached data

**Database Evidence** (from production):
```sql
-- Query: SELECT ticker, COUNT(DISTINCT DATE(timestamp)) as unique_dates,
--        MIN(timestamp), MAX(timestamp) FROM price_history
--        WHERE ticker IN ('AAPL', 'TSLA', 'MU') GROUP BY ticker;

AAPL  | 6 unique dates | Jan 12 - Jan 17 ✅
TSLA  | 2 unique dates | Jan 12, Jan 17 only ❌ (missing 13, 14, 15, 16)
MU    | 2 unique dates | Jan 12, Jan 17 only ❌ (missing 13, 14, 15, 16)
```

---

## Fixes Already Applied ✅

### 1. Timezone Boundary Bug (Commit: `6f6aa5f`)
**File**: `backend/src/zebu/adapters/inbound/api/prices.py`

**Issue**: When frontend sends `end=2026-01-17` (date only), FastAPI parses as midnight `00:00:00`, excluding same-day timestamps like `14:47:59`.

**Fix**: Detect midnight timestamps and adjust to end-of-day (`23:59:59.999999`).

**Result**: API now returns all data points for the requested end date.

### 2. Scheduler Event Loop (Previous Session)
**Issue**: AsyncIOScheduler wasn't running because event loop wasn't passed explicitly.

**Fix**: Pass `asyncio.get_running_loop()` to scheduler constructor.

**Result**: Daily price refresh jobs now execute at midnight UTC.

---

## Observability Improvements Added ✅

### Debug Endpoint: `/api/v1/debug/price-cache/{ticker}` (Commit: `e970ba8`)

**Purpose**: Diagnose data completeness without manual database queries.

**Returns**:
- Total records and unique dates
- Date coverage (all dates with data)
- **Gaps** (missing dates between min/max, excluding weekends)
- Sample records

**Usage**:
```bash
curl http://192.168.4.112:8000/api/v1/debug/price-cache/TSLA | jq '.gaps'
```

**Example Output**:
```json
{
  "ticker": "TSLA",
  "has_data": true,
  "unique_dates": 2,
  "earliest_date": "2026-01-12",
  "latest_date": "2026-01-17",
  "date_coverage": ["2026-01-12", "2026-01-17"],
  "gaps": [
    {
      "after": "2026-01-12",
      "before": "2026-01-17",
      "missing_dates": ["2026-01-13", "2026-01-14", "2026-01-15", "2026-01-16"]
    }
  ]
}
```

---

## Background Agent Task Running 🔄

**Task**: `agent_tasks/150_price-history-observability-analysis.md`
**Agent**: backend-swe
**Status**: ✅ **COMPLETE** - PR #137 merged to main
**PR**: https://github.com/TimChild/PaperTrade/pull/137

### What Was Delivered

1. **✅ Comprehensive Analysis Document**: `agent_progress_docs/2026-01-17_19-42-08_price-history-observability-analysis.md`
   - Complete data flow audit with line numbers
   - Root cause identified (lines 529-531 in `alpha_vantage_adapter.py`)
   - 3 solution options with detailed pros/cons
   - Test scenarios and implementation specs
   - Migration path for recommended solution

2. **✅ Observability Improvements** (merged):
   - Structured logging throughout price history flow
   - Debug endpoint `/api/v1/debug/price-cache/{ticker}`
   - Request/response logging in API endpoints
   - Cache hit/miss logging in adapter
   - Query result logging in repository

3. **✅ Documentation**:
   - Alpha Vantage `outputsize=compact` limitations documented
   - Data completeness validation requirements
   - Testing gaps identified

### Orchestrator Decision

**Approved Option A: Cache Completeness Check** ✅

**Rationale**:
- Fixes root cause directly
- Respects rate limits (5 calls/min, 500/day)
- Minimal complexity with graceful degradation
- Migration path provided with feature flag option

### Follow-Up Tasks Created

1. **Task 151**: Implement cache completeness check (HIGH PRIORITY)
   - Fix the incomplete data bug
   - 7 comprehensive test scenarios
   - Estimated: 10-14 hours

2. **Task 152**: Migrate to structlog (MEDIUM PRIORITY)
   - Better structured logging
   - Request correlation IDs
   - Prepares for Grafana integration
   - Estimated: 7-10 hours

---

## Why This is Hard to Debug (Lessons Learned)

### Missing Observability
- ❌ No logging when cache hits vs API fetches
- ❌ No metrics on cache completeness
- ❌ No visibility into what backfill script actually fetched
- ❌ Hard to see data flow without manual DB queries

### Architectural Issues
- **Cache Strategy**: "All or nothing" - doesn't handle partial data
- **No Gap Detection**: System doesn't know when data is incomplete
- **Rate Limits**: Can't "always fetch fresh" (5 calls/min, 500/day)
- **Backfill Script**: Uses same buggy `get_price_history()` code path

### Testing Gaps
- ❌ No tests for partial cache scenarios
- ❌ No tests for data completeness validation
- ❌ No integration tests for backfill workflow
- ❌ Tests too implementation-focused vs behavior-focused

---

## Current State Summary

### ✅ Working
- Scheduler running (daily refresh at midnight UTC)
- API correctly handles timezone boundaries
- Debug endpoint deployed for diagnostics
- Database schema and queries correct

### ❌ Broken
- Cache returns incomplete data (root cause identified)
- Backfill script affected by same caching bug
- Missing data for TSLA and MU (Jan 13-16)

### 🔄 In Progress
- Background agent analyzing caching architecture
- Waiting for solution recommendations

---

## Immediate Next Steps for New Orchestrator

### 1. ✅ Agent Analysis Complete

PR #137 merged with:
- Comprehensive root cause analysis
- Structured logging throughout price history flow
- Debug endpoint for cache diagnostics
- 3 solution options evaluated

### 2. Start Implementation (Task 151)

**High Priority** - Fixes user-facing data issue

```bash
GH_PAGER="" gh agent-task create --custom-agent backend-swe -F agent_tasks/151_implement-price-cache-completeness-check.md
```

**Why Task 151 First**:
- Fixes the actual bug (incomplete price data for TSLA/MU)
- Clear implementation spec from Option A
- Well-defined test scenarios (7 cases)
- Estimated 10-14 hours

**Expected Outcome**:
- Cache validates completeness before returning
- Fetches from API when cache is incomplete
- Users see full 5-7 data points for last week

### 3. After Task 151 Merges: Structlog Migration (Task 152)

**Medium Priority** - Quality improvement

```bash
# Wait for Task 151 to complete first
GH_PAGER="" gh agent-task create --custom-agent backend-swe -F agent_tasks/152_migrate-to-structlog.md
```

**Why Task 152 Second**:
- Builds on PR #137's structured logging patterns
- Prepares for Grafana/Loki integration
- Better developer experience (less code duplication)
- JSON logs ready for machine parsing

**Expected Outcome**:
- JSON-formatted logs in production
- Request correlation IDs for tracing
- Incremental context binding (cleaner code)

### 4. Monitoring & Validation

**After Task 151 deploys**:
```bash
# Check production for data completeness
curl http://192.168.4.112:8000/api/v1/debug/price-cache/TSLA | jq '.gaps'
# Expected: [] (no gaps)

curl http://192.168.4.112:8000/api/v1/debug/price-cache/MU | jq '.gaps'
# Expected: [] (no gaps)

# Verify frontend shows 5-7 data points
# Navigate to portfolio page, check TSLA/MU charts
```

**Monitor Logs for**:
- "Cached data incomplete" messages (should trigger API fetches)
- "Returning complete cached data" (cache working correctly)
- API call rate (should not exceed 5/min)

---

## Key Files Reference

### Critical Backend Files
- **Caching Bug**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py:529-531`
- **Price API**: `backend/src/zebu/adapters/inbound/api/prices.py:244-290`
- **Price Repository**: `backend/src/zebu/adapters/outbound/repositories/price_repository.py:199-260`
- **Backfill Script**: `backend/scripts/backfill_prices.py`

### Debug & Diagnostics
- **Debug Endpoints**: `backend/src/zebu/adapters/inbound/api/debug.py`
  - `/api/v1/debug/scheduler` - Scheduler status
  - `/api/v1/debug/price-cache/{ticker}` - Cache diagnostics

### Test Files (Need Enhancement)
- `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py`
- `backend/tests/unit/adapters/outbound/repositories/test_price_repository.py`

### Documentation
- **Orchestration Guide**: `docs/ai-agents/orchestration-guide.md`
- **Architecture Principles**: `agent_tasks/reusable/architecture-principles.md`
- **Agent Task**: `agent_tasks/150_price-history-observability-analysis.md`

---

## Production Environment

**Server**: http://192.168.4.112
**Frontend**: http://192.168.4.112
**Backend API**: http://192.168.4.112:8000
**API Docs**: http://192.168.4.112:8000/docs

**Database Access**:
```bash
ssh root@192.168.4.112
docker exec -e PGPASSWORD=papertrade_dev_password \
  zebu-postgres-prod psql -U papertrade -d papertrade_dev
```

**Deployment**:
```bash
export PROXMOX_HOST=root@proxmox
task proxmox-vm:deploy
```

---

## Quality Standards Reminder

From `docs/ai-agents/orchestration-guide.md`:

**Merge Criteria** (Score 9/10 or higher):
- ✅ Clean Architecture compliance
- ✅ Complete type hints (no `Any`)
- ✅ Behavior-focused tests (not implementation-focused)
- ✅ Test coverage 80%+ for new code
- ✅ No ESLint/Pyright suppressions without justification
- ✅ Self-documenting code
- ✅ Proper error handling

**Reject if**:
- ❌ Breaks Clean Architecture
- ❌ No tests or mocks internal logic
- ❌ Type suppressions without reason
- ❌ Introduces tech debt

---

## Success Criteria for Resolution

### Immediate Goals
1. ✅ Root cause identified with evidence
2. ✅ Debug capabilities added
3. 🔄 Agent analysis in progress
4. ⏳ Solution options evaluated
5. ⏳ Implementation task created
6. ⏳ Fix deployed and verified

### Long-term Goals
1. ✅ Root cause identified and solution designed
2. ✅ Observability infrastructure deployed
3. ⏳ All tickers show complete historical data (7+ days) - **Task 151**
4. ⏳ Backfill script works correctly for new tickers - **Task 151**
5. ✅ System detects and logs data gaps - **PR #137 merged**
6. ⏳ Tests prevent regression (partial cache scenarios) - **Task 151**
7. ✅ Clear observability (logs, debug endpoints) - **PR #137 merged**
8. ⏳ JSON logs ready for Grafana/Loki - **Task 152**

### Validation Tests
```bash
# 1. Check database has complete data
curl http://192.168.4.112:8000/api/v1/debug/price-cache/TSLA | jq '.gaps'
# Expected: [] (no gaps)

# 2. Frontend displays all data points
# Navigate to portfolio page, check TSLA/MU charts show 7+ points

# 3. Backfill works for new tickers
# Add new ticker to watchlist, run backfill, verify complete data
```

---

## Critical Context Not to Lose

1. **Alpha Vantage Limits**: Free tier = 5 calls/min, 500/day, compact output = 100 days
2. **Database Schema**: `price_history` table with UNIQUE constraint on `(ticker, timestamp, source, interval)`
3. **Scheduler Jobs**: Run at midnight UTC daily (price refresh + portfolio snapshots)
4. **Current Data**: AAPL has 6 days (working), TSLA/MU have 2 days (broken)
5. **Weekend Handling**: Debug endpoint skips weekends when detecting gaps
6. **Rate Limiting**: System uses Redis-based rate limiter with key prefix `papertrade:ratelimit:alphavantage`

---

## Agent Feedback for Improvement

**What went well**:
- Clear problem identification (missing data points)
- Good use of debug endpoints for diagnostics
- Background agent task delegation

**What to improve**:
- Earlier observability investment (logs, metrics)
- Test for partial cache scenarios from start
- Document caching assumptions and limitations
- Add monitoring alerts for data gaps

---

## Quick Command Reference

```bash
# Check agent status
GH_PAGER="" gh agent-task list

# View production data gaps
curl http://192.168.4.112:8000/api/v1/debug/price-cache/TSLA | jq '.gaps'

# Query database directly
ssh root@192.168.4.112 "docker exec -e PGPASSWORD=papertrade_dev_password \
  zebu-postgres-prod psql -U papertrade -d papertrade_dev \
  -c \"SELECT ticker, COUNT(DISTINCT DATE(timestamp)), MIN(timestamp), MAX(timestamp) \
  FROM price_history GROUP BY ticker;\""

# Run backfill manually (after fix)
ssh root@192.168.4.112 "docker exec zebu-backend-prod \
  python scripts/backfill_prices.py --days=7"

# Deploy changes
export PROXMOX_HOST=root@proxmox && task proxmox-vm:deploy
```

---

**Ready to Resume**: New orchestrator should start by checking agent task progress and reviewing analysis document when ready.
