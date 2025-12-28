# Project Backlog

This file tracks minor improvements, tech debt, and enhancement tasks that don't block main development but should be addressed soon.

## Active Backlog

### Domain Layer Refinements (Post-PR #12)

**Context**: Domain layer implementation in PR #12 is excellent (9/10) but has minor issues to clean up.

**Tasks**:

1. **Fix linting warnings (E501)** - ~5 minutes
   - 15 line-too-long warnings in domain layer
   - All in docstrings/error messages
   - Run `uv run ruff check --fix` and `uv run ruff format`
   - Files affected: `transaction.py`, `money.py`

2. **Fix Holding equality semantics** - ~15 minutes
   - Current: Equality based on ticker only (value-based but incomplete)
   - Issue: `Holding(AAPL, qty=10, cost=1000) == Holding(AAPL, qty=20, cost=2000)` returns True
   - Fix: Include quantity and cost_basis in equality comparison
   - File: `backend/src/papertrade/domain/entities/holding.py`
   - Update test: `backend/tests/unit/domain/entities/test_holding.py`

3. **Resolve Portfolio immutability documentation** - ~10 minutes
   - Architecture plan says "name can change" but implementation is fully immutable
   - Decision: Keep fully immutable (safer), update architecture docs
   - Files to update:
     - `architecture_plans/20251227_phase1-backend-mvp/domain-layer.md`
     - Architecture plan note in Portfolio entity docs

4. **Add business rule validation: Cannot sell shares you don't own** - ~30 minutes
   - Current: `PortfolioCalculator.calculate_holdings()` has comment "shouldn't happen in valid data"
   - Fix: Add explicit validation in Application layer Use Cases
   - Create `InsufficientSharesError` exception (already exists!)
   - Add validation in `SellStockCommand` handler (task 007b scope)
   - Note: Domain layer is correct as-is; this is Application layer concern

**Estimated Total Time**: ~1 hour

**Priority**: Low (non-blocking for Application layer development)

**Assigned**: See `agent_tasks/008_domain-layer-refinements.md`

---

## Completed

_(Items moved here after completion)_

---

## Future Enhancements (Phase 2+)

From domain layer progress doc:

1. **User Entity**: Add user authentication and ownership
2. **MarketPrice Value Object**: Dedicated type for prices
3. **Position Entity**: Real-time P&L tracking
4. **Multiple Currencies**: Extend Money to support conversions
5. **Split Handling**: Adjust prices for stock splits
6. **Performance**: Cache holdings calculations

**Status**: Deferred to Phase 2
