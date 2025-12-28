# Project Backlog

This file tracks minor improvements, tech debt, and enhancement tasks that don't block main development but should be addressed soon.

## Active Backlog

### Code Quality & Linting (Post-PR #15)

**Context**: After merging adapters layer (PR #15), we have minor linting and type checking issues that don't block development.

**Tasks**:

1. **Fix remaining ruff linting warnings** - ~10 minutes
   - 3 warnings remaining after auto-fix:
     - `B904`: Exception chaining in `dependencies.py` (raise from err/None)
     - `B007`: Unused loop variable in `test_sqlmodel_transaction_repository.py`
     - `E501`: Line too long in `test_holding.py` docstring
   - Run `uv run ruff check --fix --unsafe-fixes` or fix manually
   - Files: `adapters/inbound/api/dependencies.py`, test files

2. **Resolve pyright deprecation warnings** - ~30 minutes
   - 41 warnings about SQLAlchemy's deprecated `session.execute()`
   - Should use SQLModel's `session.exec()` instead
   - Affects: Repository implementations in `adapters/outbound/database/`
   - Note: Code works fine, this is about using recommended SQLModel patterns

3. **Fix minor API test failure** - ~15 minutes
   - Test `test_api_v1_root_endpoint` expects `/api/v1/` but we have `/`
   - Either update test or add `/api/v1/` root endpoint
   - File: `backend/tests/integration/test_api.py`

**Estimated Total Time**: ~55 minutes
**Priority**: Low (cosmetic, doesn't affect functionality)

---

### Development Workflow Improvements

**Context**: Pre-commit hooks and agent environment setup need optimization.

**Tasks**:

1. **Improve pre-commit hook workflow** - ~20 minutes
   - **Problem**: Auto-fixes (trailing whitespace, line endings, ruff format) require writing commit message twice
   - **Solution**: Configure hooks to allow auto-fixes without blocking commit
   - **Options**:
     - Use `stages: [push]` for formatters instead of `commit`
     - Add `--no-verify` flag documentation
     - Create git alias that commits after auto-fixes
   - **File**: `.pre-commit-config.yaml`
   - **Research**: Best practices for developer-friendly pre-commit configs

2. **Create Copilot agent environment setup** - ~45 minutes
   - **Goal**: Agents should have pre-configured environments (uv synced, pre-commit installed, etc.)
   - **Location**: `.github/copilot-agent-setup.sh` or similar
   - **Setup tasks**:
     - Install pre-commit hooks: `task precommit:install`
     - Sync backend dependencies: `cd backend && uv sync --all-extras`
     - Sync frontend dependencies: `cd frontend && npm ci`
     - Start Docker services: `task docker:up`
   - **Consider**: Using existing `task setup` command
   - **Research**: GitHub Copilot agent environment customization (`.github/` folder)
   - **Documentation**: Update AGENT_ORCHESTRATION.md with setup instructions

**Estimated Total Time**: ~65 minutes
**Priority**: Medium (improves developer experience and agent efficiency)

---

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

### Task 008: Domain Layer Refinements - ✅ Completed 2025-12-28

**Completed Tasks**:
1. ✅ Fixed all linting warnings (E501) - 15 line-too-long issues resolved
2. ✅ Fixed Holding equality semantics - Now includes quantity and cost_basis
3. ✅ Updated Portfolio immutability documentation - Confirmed fully immutable design
4. ✅ Added explicit business rule validation - InsufficientSharesError in SellStockCommand

**PR**: #13
**Duration**: ~2 hours (including test updates and documentation)
**Test Results**: 160 passing tests, 0 linting errors, 0 type errors

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
