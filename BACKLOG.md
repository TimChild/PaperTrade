# Project Backlog

Minor improvements, tech debt, and enhancements that don't block main development.

**Last Updated**: January 6, 2026

## 🚨 Critical Issues (Task #062)

**Must fix before continuing new features:**

1. **Multi-Portfolio Dashboard Bug** - CRITICAL
   - Dashboard only shows first portfolio when user has multiple
   - Other portfolios hidden with no way to access through UI
   - File: `frontend/src/pages/Dashboard.tsx`

2. **Trade Execution 400 Error** - CRITICAL
   - BUY trades failing with 400 Bad Request
   - Root cause TBD (validation? auth? market data?)
   - Files: `TradeForm.tsx`, `portfolios.py`

## Active Backlog

### Testing & Quality (MEDIUM PRIORITY)

1. **Implement Skipped Scheduler Tests** - ~4-6 hours
   - 4 tests in `tests/unit/infrastructure/test_scheduler.py` are skipped
   - Reasons: "Requires database setup", "timing-dependent", "complex integration"
   - Solution: Proper mocking for market data, event-based assertions, split complex tests
   - See: Task #039 (to be created)

2. **Migrate E2E Tests to Test IDs** - ~8-12 hours
   - **Problem**: Current Playwright tests use text matching (`.getByText()`, `.getByRole()` with name)
   - **Risk**: Brittle tests that break when UI copy changes; difficult to target specific elements
   - **Solution**: Add `data-testid` attributes throughout frontend, update all E2E tests to use `.getByTestId()`
   - **Scope**:
     - Add test IDs to all interactive elements (buttons, inputs, links, etc.)
     - Add test IDs to key content areas (portfolio cards, transaction rows, etc.)
     - Update existing E2E tests: `frontend/tests/e2e/*.spec.ts`
     - Document test ID naming conventions (e.g., `portfolio-card-{id}`, `trade-form-ticker-input`)
   - **Benefits**: More reliable tests, easier debugging, clearer test intent
   - **References**:
     - Playwright best practices: https://playwright.dev/docs/locators#locate-by-test-id
     - Testing Library: https://testing-library.com/docs/queries/bytestid/
   - **Note**: Alpha Vantage provides a `demo` API key for E2E testing (see: https://www.alphavantage.co/documentation/)

### Code Quality & Linting (LOW PRIORITY)

1. **Fix remaining ruff linting warnings** - ~10 minutes
   - 3 warnings: `B904` (exception chaining), `B007` (unused loop var), `E501` (long line)
   - Run `uv run ruff check --fix --unsafe-fixes`

2. **Resolve pyright deprecation warnings** - ~30 minutes
   - 41 warnings about SQLAlchemy's deprecated `session.execute()`
   - Should use SQLModel's `session.exec()` instead

### Code Improvements (P3)

1. **Extract Portfolio Verification Helper** - ~30 minutes
   - Same 4-line pattern in 5 command handlers
   - Create utility function to reduce duplication

2. **Add Database Indexes** - ~1 hour
   - `Transaction.portfolio_id` and `Transaction.timestamp`
   - Add to SQLModel models with proper migration

3. **Bundle Size Analysis** - ~30 minutes
   - `npm run build && npx vite-bundle-visualizer`
   - Document findings, optimize if needed

---

## Recently Completed

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
