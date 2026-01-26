# Task 150: Price History System - Observability & Completeness Analysis

**Agent**: backend-swe
**Priority**: High
**Type**: Investigation + Improvements

## Problem Statement

We're experiencing a challenging debugging scenario with the price history system:

1. **Symptoms**: Frontend shows fewer data points than expected (e.g., only 2-3 points for a week when daily data should have 5-7 points)
2. **Known Issues Already Fixed**:
   - ✅ Scheduler event loop issue (now running)
   - ✅ Timezone boundary bug (midnight cutoff excluding same-day data)
3. **Remaining Problem**: Still missing historical data despite:
   - Backfill script running successfully
   - Database containing some data
   - API returning data (but not all expected points)

## Root Cause Hypothesis

The caching logic in `AlphaVantageAdapter.get_price_history()` (lines 529-531) is suspect:

```python
# If we have data, return it
if history:
    return history
```

This returns cached data immediately if **ANY** data exists, without checking if it covers the full requested date range. This means:
- If database has Jan 12 data
- Frontend requests Jan 10-17 range
- API returns only Jan 12 (incomplete) instead of fetching missing days

## Objectives

### 1. Critical Analysis (Must Do)

Analyze the **complete data flow** from API request to frontend display:

**Backend Flow**:
- `GET /api/v1/prices/{ticker}/history` endpoint → [prices.py](../backend/src/zebu/adapters/inbound/api/prices.py)
- `AlphaVantageAdapter.get_price_history()` → [alpha_vantage_adapter.py](../backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py)
- `PriceRepository.get_price_history()` → [price_repository.py](../backend/src/zebu/adapters/outbound/repositories/price_repository.py)
- Database query and data retrieval

**Questions to Answer**:
1. **Caching Strategy**: Should cached data be returned if incomplete? What's the right balance between API rate limits and data completeness?
2. **Data Gaps**: How should we detect when cached data has gaps in the requested range?
3. **Deduplication**: Are we correctly handling multiple entries for the same date (from scheduler running multiple times)?
4. **Alpha Vantage API**: What does `outputsize=compact` return? Is it limited to 100 days? Are we fetching the right data?

### 2. Observability Gaps (Must Do)

Identify what logging/metrics would have made this problem obvious:

**Current State**: We can't easily answer:
- "What data did the backfill script actually fetch from Alpha Vantage?"
- "What's in the database vs what the API returns vs what the frontend requests?"
- "Are there gaps in our cached data for a ticker?"
- "Did we hit rate limits during backfill?"

**Required Analysis**:
- What log statements are missing in the critical path?
- What debug endpoints would help diagnose data completeness?
- What tests would have caught this caching bug?

### 3. Testing Gaps (Must Do)

This bug exists because our tests don't cover:
- Partial cache scenarios (database has some but not all requested dates)
- Date range completeness validation
- Cache invalidation strategies

**Required**:
- List specific test cases that should exist but don't
- Identify which tests are too implementation-focused vs behavior-focused
- Recommend integration test scenarios

### 4. Proposed Solutions (Must Do)

Provide **3 different approaches** to fixing the caching issue, with pros/cons:

**Option A**: Always check data completeness before returning cache
**Option B**: Merge cached data with fresh API data
**Option C**: Cache invalidation strategy (TTL-based or event-based)

For each option, specify:
- Code changes required
- Performance impact
- Rate limit considerations
- Testing strategy

## Deliverables

### 1. Analysis Document (Primary Deliverable)

Create `agent_tasks/progress/YYYY-MM-DD_HH-MM-SS_price-history-observability-analysis.md` with:

```markdown
# Price History System Analysis

## Data Flow Audit
[Complete trace from frontend request to database and back]

## Critical Issues Found
[Specific code issues with line numbers and evidence]

## Observability Gaps
[Missing logs, metrics, debug capabilities]

## Testing Gaps
[Missing test scenarios with examples]

## Recommended Solutions
[3 options with detailed pros/cons and implementation guidance]

## Quick Wins
[Immediate improvements that can be made without major refactor]
```

### 2. Code Improvements (Secondary - Only if Clear Quick Wins)

**ONLY** if you find obvious quick wins (e.g., adding critical log statements), implement them in a PR:

**Allowed Changes** (require NO architecture changes):
- Add structured logging to critical paths
- Add debug endpoint (e.g., `/api/v1/debug/price-cache/{ticker}`)
- Fix obvious bugs you discover
- Add missing type hints or documentation

**NOT Allowed** (require orchestrator approval):
- Changing caching strategy
- Modifying core business logic
- Large refactors

## Quality Standards

### Code Quality
- Follow Clean Architecture (no shortcuts)
- Complete type hints (no `Any`)
- Structured logging with context (ticker, date range, source)
- Self-documenting code

### Testing
- If you add code, add tests
- Behavior-focused tests (not implementation-focused)
- Test edge cases (partial cache, empty cache, full cache)

### Documentation
- All analysis backed by code evidence (file paths, line numbers)
- Solutions include implementation pseudo-code
- Clear reasoning for recommendations

## Success Criteria

✅ **Complete understanding** of why data is missing
✅ **Clear recommendations** for 3+ solution approaches
✅ **Actionable observability improvements** (logs, metrics, debug endpoints)
✅ **Test coverage gaps** identified with specific scenarios
✅ **Quick wins** implemented (if any found)

## Context Files

**Critical Files**:
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` (lines 475-565)
- `backend/src/zebu/adapters/outbound/repositories/price_repository.py` (lines 199-260)
- `backend/src/zebu/adapters/inbound/api/prices.py` (lines 244-300)
- `backend/scripts/backfill_prices.py`

**Test Files**:
- `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py`
- `backend/tests/unit/adapters/outbound/repositories/test_price_repository.py`

**Database Schema**:
- Check `price_history` table structure and indexes

## Constraints

- **Rate Limits**: Alpha Vantage free tier = 5 calls/min, 500 calls/day
- **Data Volume**: Daily data only (1day interval)
- **Backwards Compatibility**: Don't break existing frontend code

## References

- Clean Architecture: `agent_tasks/reusable/architecture-principles.md`
- Testing Philosophy: `agent_tasks/reusable/architecture-principles.md`
- Current Issue: Multiple data points missing from last week despite backfill running
