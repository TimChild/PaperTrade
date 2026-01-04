# Task 047: Phase 3a SELL Orders - Backend Implementation

**Agent**: backend-swe  
**Priority**: HIGH  
**Estimated Effort**: 5-6 days  
**Dependencies**: None (builds on Phase 2)  
**Parallel Work**: Task #048 (Frontend) can run simultaneously

---

## Objective

Implement SELL order functionality in the backend (Domain, Application, and API layers) to enable users to sell stocks they own. This completes the basic buy/sell trading loop and is the #1 user need from documentation analysis.

## Context

**What Currently Exists**:
- ✅ BUY orders fully implemented
- ✅ Transaction ledger with DEPOSIT and BUY types
- ✅ Holdings calculation from transactions (`portfolio_calculator.py`)
- ✅ Portfolio value calculation with real market data
- ✅ Trade API endpoint (`POST /api/v1/portfolios/{id}/trades`)
- ✅ 418 passing backend tests (87% coverage)

**What's Missing**:
- ❌ SELL transaction type
- ❌ Holdings validation (can't sell more than owned)
- ❌ Updated holdings calculation (BUY - SELL)
- ❌ SELL-specific error handling

**Critical**: Before implementing, **CHECK FOR EXISTING CODE** that might already support SELL functionality. Look for:
- Enum values in `TransactionType`
- Holdings calculation logic in portfolio calculator
- Any SELL-related validation or error handling
- Tests that might reference SELL

## Architecture Reference

**Primary Specification**: [`architecture_plans/phase3-refined/phase3a-sell-orders.md`](../architecture_plans/phase3-refined/phase3a-sell-orders.md)

**Key Sections**:
- Domain Model Changes (lines 30-76)
- Use Case Specification (lines 78-152)
- API Changes (lines 154-225)
- Testing Strategy (lines 227-320)

## Requirements

### 1. Domain Layer Changes (2 days)

**File**: `backend/src/papertrade/domain/entities/transaction.py`
- [ ] Add `SELL` value to `TransactionType` enum
- [ ] Verify Transaction entity supports SELL (should already work)

**File**: `backend/src/papertrade/domain/services/portfolio_calculator.py`
- [ ] Update `calculate_holdings()` method:
  - Separate BUY and SELL transactions
  - Calculate net quantity: `sum(buys) - sum(sells)`
  - Calculate weighted average cost basis
  - Return `None` when quantity = 0 (holding disappears)
- [ ] Add edge case handling:
  - Selling all shares → holding disappears
  - Multiple buys at different prices → weighted average
  - Sell then buy same ticker → cost basis resets

**New Domain Exception** (if not exists):
- [ ] `InsufficientHoldingsError` (inherits from `DomainException`)
  - Used when user tries to sell more than owned

**Unit Tests** (minimum 12 new tests):
- [ ] `test_holdings_after_buy_then_sell` - Reduces quantity correctly
- [ ] `test_holdings_sell_all_shares` - Holding disappears (None returned)
- [ ] `test_holdings_multiple_buys_then_sell` - Weighted average cost
- [ ] `test_holdings_sell_without_buy` - Should handle gracefully
- [ ] `test_sell_transaction_creation` - SELL type persists
- [ ] `test_sell_transaction_total_positive` - Cash received > 0
- [ ] Edge cases: concurrent sells, sell-buy-sell sequences

### 2. Application Layer Changes (2 days)

**File**: `backend/src/papertrade/application/use_cases/execute_trade.py`
- [ ] Update `ExecuteTrade` use case to handle `TradeType.SELL`
- [ ] Add SELL-specific validation logic:
  ```python
  if trade_type == TradeType.SELL:
      1. Calculate current holdings
      2. Check if holding exists for ticker
      3. Validate quantity <= holding.quantity
      4. If insufficient: raise InsufficientHoldingsError
  ```
- [ ] Create SELL transaction:
  - type: `TransactionType.SELL`
  - quantity: positive integer (for consistency)
  - total: positive (cash received)
  - price: current market price

**Integration Tests** (minimum 8 new tests):
- [ ] `test_execute_sell_with_sufficient_holdings` - Success path
- [ ] `test_execute_sell_insufficient_holdings` - Raises error
- [ ] `test_execute_sell_no_holdings_for_ticker` - Raises error
- [ ] `test_execute_sell_updates_cash_balance` - Cash increases
- [ ] `test_execute_sell_reduces_holdings` - Quantity decreases
- [ ] `test_execute_sell_all_shares` - Holding disappears
- [ ] `test_sell_then_buy_same_ticker` - Cost basis resets
- [ ] Edge case: Concurrent sells (if applicable)

### 3. API Layer Changes (1 day)

**File**: `backend/src/papertrade/adapters/api/v1/endpoints/portfolios.py`
- [ ] Update trade endpoint to accept `"SELL"` action
- [ ] Map domain exceptions to HTTP responses:
  - `InsufficientHoldingsError` → 400 Bad Request
  - Include helpful error message with current quantity
- [ ] Verify request/response models support SELL

**API Tests** (minimum 6 new tests):
- [ ] `test_api_post_sell_trade_success` - 201 Created
- [ ] `test_api_post_sell_insufficient_holdings` - 400 with error details
- [ ] `test_api_post_sell_no_holdings` - 400 with error message
- [ ] `test_api_post_sell_invalid_quantity_negative` - 400
- [ ] `test_api_post_sell_invalid_quantity_zero` - 400
- [ ] `test_api_sell_updates_holdings_endpoint` - GET holdings shows update

### 4. Documentation (integrated)

- [ ] Add docstrings to all new/modified functions
- [ ] Update type hints (ensure pyright --strict passes)
- [ ] Update API documentation (OpenAPI schema should auto-update)

## Testing Requirements

**Quality Standards**:
- All new code has 90%+ coverage
- All 418 existing tests still pass (no regressions)
- Minimum 26 new tests (12 domain + 8 application + 6 API)
- Zero pyright errors (enforced by pre-commit)
- All ruff linting rules passing

**Test Patterns to Follow**:
- Test behaviors, not implementation details
- Sociable tests (exercise Use Cases + Domain together)
- No mocking internal domain logic
- Only mock at architectural boundaries (e.g., MarketDataPort)

**Run Tests**:
```bash
task test:backend          # All backend tests
task lint:backend          # Ruff + pyright
task docker:up             # Start services if needed
```

## Success Criteria

- [ ] SELL transaction type exists in domain model
- [ ] Holdings calculation correctly handles BUY and SELL
- [ ] ExecuteTrade use case validates holdings before SELL
- [ ] API endpoint accepts SELL action and returns proper errors
- [ ] All 444+ tests pass (418 existing + 26 new minimum)
- [ ] Test coverage remains ≥ 85%
- [ ] Zero pyright errors
- [ ] No regressions in existing BUY functionality
- [ ] Code follows Clean Architecture (no domain dependencies on infrastructure)

## Implementation Sequence

**Recommended Order**:
1. **Domain Layer First**: Add SELL enum, update holdings calculation, unit tests
2. **Application Layer Second**: Update use case, add validation, integration tests
3. **API Layer Third**: Update endpoint, error mapping, API tests
4. **Verify**: Run full test suite, check coverage, test manually

**Commit Strategy**:
- Commit 1: `feat(domain): add SELL transaction type and holdings calculation`
- Commit 2: `feat(application): add SELL order validation to ExecuteTrade use case`
- Commit 3: `feat(api): add SELL action support to trade endpoint`
- Commit 4: `test: comprehensive SELL order test coverage`

## Autonomy & Flexibility

**You Have Autonomy To**:
- Choose specific validation error messages
- Decide on internal implementation details (as long as Clean Architecture is maintained)
- Add additional tests beyond the minimum
- Refactor existing code if it improves clarity (but minimize scope)

**You Must Follow**:
- Clean Architecture boundaries (Domain → Application → Adapters → Infrastructure)
- Testing conventions from `docs/TESTING_CONVENTIONS.md`
- Type safety (pyright --strict)
- Architecture spec in `phase3a-sell-orders.md`

**Ask for Clarification** (via PR comments) if:
- Architecture spec conflicts with existing code
- Unclear how to handle edge cases not in spec
- Significant scope changes needed

## Risk Mitigation

**Potential Issues**:
1. **Holdings calculation bug**: Mitigate with property-based tests, manual verification
2. **Race conditions**: Use database transactions (existing pattern)
3. **Cost basis calculation wrong**: Extensive test cases with known values
4. **Breaking existing BUY**: Run full regression suite

## References

- **Architecture Spec**: `architecture_plans/phase3-refined/phase3a-sell-orders.md`
- **Existing BUY Implementation**: `backend/src/papertrade/application/use_cases/execute_trade.py`
- **Holdings Calculator**: `backend/src/papertrade/domain/services/portfolio_calculator.py`
- **Testing Conventions**: `docs/TESTING_CONVENTIONS.md`
- **Clean Architecture Guide**: `.github/copilot-instructions.md`

## Notes

- **No database migration needed**: Enum value addition doesn't require schema change
- **Parallel frontend work**: Task #048 handles UI changes simultaneously
- **Phase 3b dependency**: Authentication will come after this
- **This enables Phase 3c**: Analytics needs realized P&L from SELL orders

---

**Ready to Start**: Once committed, use `gh agent-task create --custom-agent backend-swe -F agent_tasks/047_phase3a-sell-orders-backend.md`
