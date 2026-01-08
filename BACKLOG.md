# Project Backlog

Minor improvements, tech debt, and enhancements that don't block main development.

**Last Updated**: January 7, 2026

## Active Backlog

### UX Improvements (MEDIUM-HIGH PRIORITY)

1. **Show Real-Time Stock Prices in Holdings** - ~2-3 hours
   - **Problem**: Holdings table shows "Using average cost (current price unavailable)" with asterisk
   - **Impact**: Users can't see if their stocks went up or down
   - **Solution**: Fetch current prices from Alpha Vantage for each holding, display in "Current Price" column
   - **Implementation**:
     - Reuse existing `MarketDataPort` and `AlphaVantageAdapter`
     - Add batch price fetch endpoint: `GET /api/v1/prices/batch?tickers=AAPL,MSFT`
     - Update holdings query to include current prices
     - Cache prices in Redis (5-minute TTL)
   - **Depends On**: Task 075 (auto-populate price field) should be complete to avoid conflicts
   - **Found**: Manual UI testing (2026-01-07)

2. **Add Toast Notifications for Trade Actions** - ~1 hour
   - **Problem**: Only modal alerts for trade success/failure, no persistent feedback
   - **Solution**: Add toast notifications (react-hot-toast or similar)
   - **Features**:
     - Success toast: "Bought 2 shares of MSFT at $472.85"
     - Error toast: "Trade failed: Insufficient funds"
     - Auto-dismiss after 5 seconds
     - Clickable to view transaction details
   - **Benefits**: Better UX, less intrusive than modals
   - **Found**: Manual UI testing (2026-01-07)

3. **Highlight New Transactions** - ~30 minutes
   - **Problem**: After trade execution, hard to find the new transaction in history
   - **Solution**: Briefly highlight (pulse animation) newly added transaction row
   - **Implementation**: Add CSS class for 3-second pulse animation on new items
   - **Found**: Manual UI testing (2026-01-07)

### Testing & Quality (MEDIUM PRIORITY)

1. **Fix E2E Tests in Agent Environment** - ~2-4 hours
   - **Problem**: E2E tests fail at runtime in agent environment despite Clerk auth fix (PR #83)
   - **Root Cause**: Frontend container not accessible at `localhost:5173` + Playwright browser download blocked by firewall
   - **Findings from PR #83**:
     - ✅ Clerk authentication tokens now work (switched from `@clerk/backend` SDK to direct axios API calls)
     - ✅ `.env` file created correctly with secrets
     - ❌ Playwright can't download Chrome (firewall blocks `storage.googleapis.com`)
     - ❌ Frontend container not reachable from test runner
   - **Solution Options**:
     - Add `storage.googleapis.com` to Copilot agent firewall allowlist
     - Pre-install Playwright browsers in `copilot-setup-steps.yml`
     - Investigate Docker networking for frontend accessibility
   - **Reference**: `agent_progress_docs/2026-01-07_05-47-05_verify-e2e-tests-agent-environment.md`

2. **Implement Skipped Scheduler Tests** - ~4-6 hours
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

1. **React Patterns Audit & Refactoring** - ~2-3 days (phased)
   - **Problem**: After fixing PR #90, identified potential useEffect anti-patterns and ESLint suppressions in codebase
   - **Goal**: Systematically audit and refactor to idiomatic React patterns
   - **Scope**:
     - Audit all ESLint suppressions (especially `react-hooks/*`)
     - Identify setState-in-effect anti-patterns
     - Refactor to use key prop pattern, controlled components, derived state
     - Improve test reliability and reduce race conditions
   - **Phases**:
     1. Discovery & assessment (create findings document)
     2. High-priority refactoring (ESLint suppressions, performance issues)
     3. Medium-priority improvements (form libraries, error boundaries, code splitting)
     4. Documentation & prevention (style guide, examples)
   - **Benefits**: Better code quality, more reliable tests, easier maintenance, prevent future anti-patterns
   - **Detailed Plan**: `docs/planning/react-patterns-audit.md`
   - **Note**: Low priority tech debt - schedule during slower periods or allocate 10-20% sprint capacity

2. **Fix remaining ruff linting warnings** - ~10 minutes
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
