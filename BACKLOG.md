# Project Backlog

Minor improvements, tech debt, and enhancements that don't block main development.

**Last Updated**: March 7, 2026

## Active Backlog

### ✅ Recently Completed (This Session - March 7, 2026)

1. **Backend Quality Fixes** — PR #192 (merged)
   - Deterministic weekend cache tests (fixed date mocking)
   - Batch portfolio balances endpoint (eliminates N+1 queries)

2. **Frontend UX Improvements** — PR #193 (merged)
   - Click-to-trade from price charts
   - Holdings price loading polish (separate skeletons, mobile P&L)
   - 5-min auto-refetch for batch prices

3. **Snapshot Job Bug Fix** — pushed to main
   - Fixed silent data loss when price lookups fail
   - Cleaned 75 bad snapshots from production DB

4. **Analytics Decimal Serialization** — pushed to main
   - Fixed Decimal→string JSON serialization (chart, tooltip, stats all broken)
   - Added Y-axis auto-scaling to performance chart

### 🔄 Medium Priority

1. **Documentation Reorganization** — PR #194 (In Progress)
   - Separate human-facing docs (`docs/`) from agent-facing docs (`agent_docs/`)
   - Add MkDocs configuration and deploy docs site to GitHub Pages
   - Establish clear conventions that all agents follow
   - **Status**: Agent task launched (quality-infra agent)

2. **Phase 4: Automated Trading Strategies** — Planning needed
   - Architecture design for strategy definition and execution
   - Backtesting integration (partially exists with `as_of` trades)
   - Scheduling/execution engine
   - Risk management / position limits
   - **Status**: Needs architect design doc before implementation

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

1. ~~**Show Purchase Points on Stock Price Charts**~~ ✅ **COMPLETE** (PR #161, #166)
   - **Status**: Implemented with scatter plot markers (green BUY, red SELL)
   - **Fixed**: Tooltip type safety issue and Y-axis domain calculation (PR #166)
   - **Quality**: 122 new tests added, comprehensive edge case coverage

2. ~~**Interactive Click-to-Trade from Charts**~~ ✅ **COMPLETE** (PR #193)
   - **Status**: Click any chart point → trade form auto-populates with ticker + date
   - **Implementation**: `subscribeClick` on Lightweight Charts, reuses quickSellState pattern
   - **Quality**: Tests added for chart click callback and TradeForm date prop

2. ~~**Show Real-Time Stock Prices in Holdings**~~ ✅ **COMPLETE** (PR #193)
   - **Status**: Batch prices load with separate skeleton, 5-min auto-refetch
   - **Features**: Mobile P&L indicator (▲/▼), better price unavailable tooltip
   - **Quality**: Tests for loading states and price display

3. ~~**Add Toast Notifications for Trade Actions**~~ ✅ **COMPLETE** (PR #163)
   - **Status**: Centralized toast utility with react-hot-toast
   - **Features**: Trade success/error, deposit/withdraw, portfolio management
   - **Quality**: 18 tests, E2E compatibility verified

4. ~~**Highlight New Transactions**~~ ✅ **COMPLETE** (PR #164)
   - **Status**: 3-second pulse animation on new transaction rows
   - **Implementation**: TanStack Query cache manipulation with isNew flag
   - **Quality**: 12 tests, accessibility features (aria-live)

---

### 📊 Analytics Enhancements (MEDIUM PRIORITY)

These improve the analytics/insights capabilities:

1. **Stacked Area Chart - Portfolio Composition Over Time** — PR #195 backend (In Progress), #196 frontend (Waiting)
   - **Problem**: Current analytics show total value over time (line chart) and current composition (pie chart), but not composition over time
   - **Status**: Backend agent task (#195) launched — adds per-holding breakdown to snapshots. Frontend task (#196) will launch after #195 merges.

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

- ✅ **Release v1.2.0** (Jan 29, 2026) - Production deployment to Proxmox
- ✅ **Chart & Stats Fixes** (PRs #180, #181) - Fixed daily change calculation, weekend handling, and 1M chart scaling
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
