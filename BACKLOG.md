# Project Backlog

Minor improvements, tech debt, and enhancements that don't block main development.

**Last Updated**: January 1, 2026

## Active Backlog

### Testing & Quality (MEDIUM PRIORITY)

1. **Implement Skipped Scheduler Tests** - ~4-6 hours
   - 4 tests in `tests/unit/infrastructure/test_scheduler.py` are skipped
   - Reasons: "Requires database setup", "timing-dependent", "complex integration"
   - Solution: Proper mocking for market data, event-based assertions, split complex tests
   - See: Task #039 (to be created)

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
