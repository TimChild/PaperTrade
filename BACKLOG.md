# Project Backlog

Minor improvements, tech debt, and enhancements that don't block main development.

**Last Updated**: January 19, 2026

## Active Backlog

### 🔄 High Priority

1. **Fix Weekend Cache Validation Tests** - NEW
   - **Problem**: 2 failing tests in `test_alpha_vantage_weekend_cache.py`
     - `test_historical_request_ending_saturday`
     - `test_historical_request_ending_sunday`
   - **Root Cause**: Tests expect Friday data to be complete for Saturday/Sunday requests, but `_is_cache_complete()` returns False (looking for data beyond Friday)
   - **Impact**: Non-blocking (tests only, production works correctly)
   - **Solution**: Either fix test expectations or adjust cache validation logic to recognize weekends
   - **Effort**: ~30 minutes
   - **Found**: 2026-01-19 during quality check
   - **Status**: Not started

## Monitoring & Observability ✅ COMPLETE

**Deployed Stack** (PRs #145, #151):
- ✅ **Grafana Cloud Free** - 3 dashboards (Overview, Backend, Frontend), 5 critical alerts
- ✅ **Promtail Agent** - Log shipping via systemd service
- ✅ **LogQL Queries** - Real-time log analysis and error tracking
- 📊 **Analytics**: Plausible ($9/month) - planned for beta phase

**Next Steps**:
- Consider adding Sentry for frontend error tracking (5K errors/month free)
- Set up **PostHog** analytics when ready for public beta (open-source alternative to Plausible)

---

### 🎯 UX Improvements - HIGH PRIORITY (Quick Wins!)

These are polished, user-facing features that would significantly improve the experience:

1. **Show Purchase Points on Stock Price Charts** - ~2-3 hours
   - **Problem**: Can't see when trades were executed on historical price graphs
   - **Solution**: Add markers/dots on price charts at dates where BUY/SELL occurred
   - **Implementation**:
     - Fetch transactions for ticker from backend (already available)
     - Add scatter plot layer to price charts showing BUY (green) and SELL (red) markers
     - Tooltip on hover: "Bought 10 shares at $150.00"
   - **Visual Impact**: Immediately see your entry/exit points vs price movement
   - **Benefit**: Helps evaluate timing of trades

2. **Interactive Click-to-Trade from Charts** - ~2-3 hours
   - **Problem**: Manual entry of ticker and date when looking at charts
   - **Solution**: Click on any stock chart to auto-fill trade form
   - **Implementation**:
     - Add onClick handler to price chart points
     - Extract clicked date and ticker
     - Scroll to trade form and populate ticker + date fields
     - Optional: Populate price from chart data
   - **UX Flow**: Click chart → Trade form appears with pre-filled data → Just enter quantity
   - **Benefit**: Reduces friction for "what-if" trades and backtesting

3. **Undo Transaction Feature** - ~3-4 hours
   - **Problem**: No way to fix accidental trades or test scenarios
   - **Solution**: Add "Undo" button on recent transactions
   - **Implementation**:
     - Backend validation: Check if undoing would create negative holdings
     - Walk forward from undo point to verify all subsequent holdings remain valid
     - Add `DELETE /api/v1/portfolios/{id}/transactions/{txn_id}` endpoint
     - Frontend: Add undo button on transaction rows (with confirmation dialog)
     - Disable undo for transactions that would invalidate later holdings
   - **Business Rules**:
     - Can undo BUY if selling those shares wouldn't create negative holdings later
     - Can undo SELL if we had enough shares at that point in time
     - Can undo DEPOSIT/WITHDRAW if balance stays positive
   - **Benefit**: Experimentation-friendly, forgiving UX

4. **Show Real-Time Stock Prices in Holdings** - ~1-2 hours
   - **Problem**: Holdings table shows "Using average cost (current price unavailable)" with asterisk
   - **Impact**: Users can't see if their stocks went up or down
   - **Solution**: Fetch current prices from Alpha Vantage for each holding, display in "Current Price" column
   - **Implementation**:
     - ✅ Batch price endpoint already exists: `GET /api/v1/prices/batch?tickers=AAPL,MSFT`
     - Update frontend holdings query to call batch endpoint
     - Display current prices in Holdings table
     - Show P&L indicators (green/red) for gains/losses
   - **Note**: Depends on weekend price fix being complete (PR #158 merged)
   - **Found**: Manual UI testing (2026-01-07)

5. **Add Toast Notifications for Trade Actions** - ~1 hour
   - **Problem**: Only modal alerts for trade success/failure, no persistent feedback
   - **Solution**: Add toast notifications (react-hot-toast or similar)
   - **Features**:
     - Success toast: "Bought 2 shares of MSFT at $472.85"
     - Error toast: "Trade failed: Insufficient funds"
     - Auto-dismiss after 5 seconds
     - Clickable to view transaction details
   - **Benefits**: Better UX, less intrusive than modals
   - **Found**: Manual UI testing (2026-01-07)

6. **Highlight New Transactions** - ~30 minutes
   - **Problem**: After trade execution, hard to find the new transaction in history
   - **Solution**: Briefly highlight (pulse animation) newly added transaction row
   - **Implementation**: Add CSS class for 3-second pulse animation on new items
   - **Found**: Manual UI testing (2026-01-07)

---

### 📊 Analytics Enhancements (MEDIUM PRIORITY)

These improve the analytics/insights capabilities:

1. **Stacked Area Chart - Portfolio Composition Over Time** - ~4-6 hours
   - **Problem**: Current analytics show total value over time (line chart) and current composition (pie chart), but not composition over time
   - **Current State**:
     - ✅ Backend: Daily snapshots already capture `total_value`, `cash_balance`, `holdings_value` per day
     - ✅ Backend: `PerformanceChart` shows total portfolio value over time
     - ✅ Backend: `CompositionChart` shows current asset allocation (pie chart)
   - **Goal**: Show how portfolio composition changed over time (similar to pie chart but stacked over time)
   - **Solution**: Create stacked area chart showing cash + individual stock holdings
   - **Implementation**:
     - **Backend**: Extend snapshot to include per-ticker breakdown
       - Add `holdings_breakdown: dict[str, Decimal]` to `PortfolioSnapshot`
       - Calculate value of each ticker at snapshot time
       - Store in `portfolio_snapshots` table as JSON column
     - **Backend**: Update `/portfolios/{id}/performance` endpoint to include breakdown
     - **Frontend**: New `PortfolioCompositionOverTime` component using Recharts `AreaChart`
       - Each ticker gets its own area (different color)
       - Cash at bottom, stocks stacked on top
       - Total height = portfolio value
   - **Benefit**: See how diversification changed, when you added/removed positions
   - **Note**: This is a bigger change requiring schema migration

2. **Calculate Portfolio Value Over Time in Backend** - ✅ **ALREADY IMPLEMENTED**
   - **Current State**:
     - ✅ Backend has `PortfolioSnapshot` entity (daily snapshots)
     - ✅ Daily job runs at midnight UTC (`calculate_daily_snapshots`)
     - ✅ Snapshots stored in PostgreSQL
     - ✅ `/portfolios/{id}/performance` API endpoint returns time series data
     - ✅ Frontend `PerformanceChart` displays the data
   - **What was for backtesting**: The `as_of` parameter on trade execution
   - **Status**: Working as designed! No action needed.

---

### Testing & Quality (LOW PRIORITY)

1. **E2E Tests in Agent Environment** - ✅ **COMPLETE** (PR #147, #154)
   - **Status**: E2E tests working in CI with Clerk authentication
   - **Solution**: Shared auth state via Playwright setup project, reduced API calls from 14 to 1-2
   - **Impact**: Reliable E2E tests both locally and in CI, no rate limiting issues
   - **Agent Environment**: Still uses unit tests only (browser install impractical), E2E validation in main CI

2. **Implement Skipped Scheduler Tests** - ~4-6 hours
   - 4 tests in `tests/unit/infrastructure/test_scheduler.py` are skipped
   - Reasons: "Requires database setup", "timing-dependent", "complex integration"
   - Solution: Proper mocking for market data, event-based assertions, split complex tests
   - See: Task #039 (to be created)

2. **Migrate E2E Tests to Test IDs** - ✅ **COMPLETE** (PR #55)
   - **Status**: `data-testid` attributes added throughout frontend
   - **Impact**: More reliable E2E tests, eliminated selector ambiguity
   - **Scope**: Portfolio creation, trade forms, transaction history

### Code Quality & Linting (LOW PRIORITY)

1. **React Patterns** - ✅ **COMPLETE** (PRs #134, #135)
   - **Status**: Codebase now has **0 ESLint suppressions** across all files!
   - **Achievement**: Removed last suppression from TradeForm.tsx (setState-in-useEffect → key prop pattern)
   - **Quality**: 234 frontend tests passing, exceptional code quality

2. **SQLAlchemy Deprecation** - ✅ **COMPLETE** (PR #49)
   - **Status**: Migrated from `session.execute()` to `session.exec()`
   - **Impact**: 0 deprecation warnings (was 129 warnings)

3. **Ruff Linting** - ✅ **COMPLETE**
   - **Status**: 0 ruff warnings in backend code
   - All checks passing in CI

### Code Improvements & Technical Debt (LOW PRIORITY)

1. **Admin Authentication TODOs** - ~2-4 hours
   - **Found**: 6 TODO comments in `analytics.py` endpoints
   - **Issue**: Analytics endpoints marked "Admin only" but no auth check implemented
   - **Endpoints**:
     - `/analytics/backtest` - Admin-only backtesting
     - `/analytics/recalculate/{portfolio_id}` - Manual snapshot recalculation
     - `/analytics/recalculate-all` - Batch recalculation
   - **Solution**: Add admin role check (requires extending Clerk integration or creating admin flag)
   - **Priority**: LOW (production app is single-user for now)
   - **Note**: Also add user ownership verification for portfolio-specific endpoints
**Issue**: Same 4-line pattern in 5 command handlers
   - **Solution**: Create utility function to reduce duplication
   - **Benefit**: DRY principle, easier maintenance

3. **Add Database Indexes** - ~1 hour
   - **Tables**: `Transaction.portfolio_id` and `Transaction.timestamp`
   - **Implementation**: Add to SQLModel models with proper migration
   - **Benefit**: Faster queries as transaction history grows

4. **Bundle Size Analysis** - ~30 minutes
   - **Command**: `npm run build && npx vite-bundle-visualizer`
   - **Goal**: Document findings, optimize if needed
   - **Priority**: Not urgent (app is fast), but good to baseline

---

## Recently Completed (Last 7 Days)

- ✅ **Weekend/Holiday Price Handling** (PR #158, Task #162) - Intelligent price fetching with weekend awareness
- ✅ **Grafana Cloud Monitoring** (PRs #145, #151) - 3 dashboards, 5 alerts, log shipping
- ✅ **E2E Test Infrastructure** (PR #147) - Fixed Clerk rate limiting, shared auth state
- ✅ **Mobile Responsive Layout** (PR #146) - 320px-2560px breakpoints, touch targets
- ✅ **Market Holiday Calendar** (PR #144) - 10 US holidays with observation rules
- ✅ **Cache Architecture Refactor** (PR #150) - Per-day caching, -35 LOC, better performance
- ✅ **Production Deployment** - Live at zebutrader.com with SSL
- ✅ **React Pattern Cleanup** (PR #135) - Achieved 0 ESLint suppressions

---

## Older Completed Items
 ✅ **Production Deployment** - Live at zebutrader.com with SSL
- ✅ **React Pattern Cleanup** (PR #135) - Achieved 0 ESLint suppression
4
- ✅ **CI workflow trigger fix** (PR #37) - Added `ready_for_review` event
- ✅ **Test isolation fix** (PR #38) - Reset global singletons between tests
- ✅ **Domain Layer Refinements** (Task 008, PR #13) - Linting, equality, docs

---

## Future Enhancements (Phase 2+)

**Domain**:
- User Entity (authentication)
- MarketPrice Value Object
- Position Entity (real-time P&L)
- Multiple Currencies

**Frontend**:
- WebSocket Integration (real-time updates)
- Advanced charting
- Portfolio comparison
