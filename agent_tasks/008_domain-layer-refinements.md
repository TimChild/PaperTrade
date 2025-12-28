# Task 008: Domain Layer Refinements

## Objective
Clean up minor issues in domain layer implementation (PR #12) identified during code review. These are non-blocking improvements that will make the codebase cleaner and more maintainable.

## Context
PR #12 delivered excellent domain layer implementation (9/10 score, 158 passing tests, zero external dependencies). However, code review identified 4 minor issues to address:

1. Linting warnings (E501 line-too-long)
2. Holding equality semantics incomplete
3. Portfolio mutability documentation mismatch
4. Missing business rule validation for overselling

**Review Document**: See comprehensive review in chat history (December 28, 2025)

## Tasks

### 1. Fix Linting Warnings (~5 min)

**Issue**: 15 E501 (line too long) warnings in domain layer
- All in docstrings/error messages exceeding 88 characters
- Non-functional but affects code quality metrics

**Action**:
```bash
cd backend
uv run ruff check --fix src/papertrade/domain
uv run ruff format src/papertrade/domain
```

**Verify**:
```bash
uv run ruff check src/papertrade/domain
# Should show 0 errors
```

**Files affected**:
- `src/papertrade/domain/entities/transaction.py`
- Possibly others flagged by ruff

### 2. Fix Holding Equality Semantics (~15 min)

**Issue**: Current equality is based on ticker only:
```python
# Current behavior
h1 = Holding(ticker=AAPL, quantity=10, cost=1000)
h2 = Holding(ticker=AAPL, quantity=20, cost=2000)
assert h1 == h2  # Returns True (wrong!)
```

**Expected**: Holdings should be equal only if ticker, quantity, AND cost_basis all match

**Fix**: Update `backend/src/papertrade/domain/entities/holding.py`:

```python
def __eq__(self, other: object) -> bool:
    """Equality based on ticker, quantity, and cost_basis.

    Args:
        other: Object to compare

    Returns:
        True if other is Holding with same ticker, quantity, and cost_basis
    """
    if not isinstance(other, Holding):
        return False
    return (
        self.ticker == other.ticker
        and self.quantity == other.quantity
        and self.cost_basis == other.cost_basis
    )

def __hash__(self) -> int:
    """Hash based on ticker, quantity, and cost_basis for use in dicts/sets.

    Returns:
        Hash of (ticker, quantity, cost_basis)
    """
    return hash((self.ticker, self.quantity.shares, self.cost_basis.amount))
```

**Update tests**: `backend/tests/unit/domain/entities/test_holding.py`
- Update `test_equality_based_on_ticker` test name and implementation
- Test should verify holdings with same ticker but different quantity/cost are NOT equal

**Verify**:
```bash
uv run pytest tests/unit/domain/entities/test_holding.py -v
```

### 3. Resolve Portfolio Immutability Documentation (~10 min)

**Issue**: Architecture plan says Portfolio "name can change" but implementation is fully immutable (frozen dataclass)

**Decision**: Keep implementation as-is (fully immutable is safer). Update documentation to match.

**Files to update**:

1. `architecture_plans/20251227_phase1-backend-mvp/domain-layer.md`:
   - Find text about Portfolio mutability
   - Update to state Portfolio is fully immutable

2. `backend/src/papertrade/domain/entities/portfolio.py` docstring:
   - Update to clarify: "Portfolio is fully immutable after creation"
   - Remove any mention of name being changeable

**Note**: If name changes are truly needed later, implement via:
- New Portfolio instance with updated name
- Repository method `update_portfolio_name()` that creates new instance

### 4. Document Business Rule Validation Strategy (~10 min)

**Issue**: No validation prevents selling shares you don't own at domain level

**Decision**: This is CORRECT for domain layer (it's a calculator, not a validator). Validation belongs in Application layer.

**Action**: Document this design decision

**Update**: `architecture_plans/20251227_phase1-backend-mvp/design-decisions.md`

Add new section:

```markdown
### ADR-012: Business Rule Validation Location

**Decision**: Portfolio state calculations (PortfolioCalculator) do NOT validate business rules like "cannot sell shares you don't own"

**Rationale**:
- Domain services are pure calculators - they derive state from inputs
- Business rule enforcement belongs in Application layer Use Cases
- Separation allows calculator to work with any transaction history (even invalid ones) for audit/analysis
- Use Cases will validate BEFORE creating transactions

**Implementation**:
- Application layer `SellStockCommand` handler will:
  1. Calculate current holdings
  2. Validate sufficient shares exist
  3. Raise `InsufficientSharesError` if validation fails
  4. Only create Transaction if validation passes

**Example**:
```python
# Application Layer (Use Case)
current_holding = portfolio_calculator.calculate_holding_for_ticker(txns, ticker)
if current_holding is None or current_holding.quantity < quantity_to_sell:
    raise InsufficientSharesError(f"Cannot sell {quantity_to_sell} shares of {ticker}, only {current_holding.quantity if current_holding else 0} owned")
```
```

## Success Criteria

- [ ] All ruff linting errors fixed (0 errors on `ruff check`)
- [ ] Code formatted with ruff (`ruff format`)
- [ ] Holding equality includes ticker, quantity, and cost_basis
- [ ] Holding hash function updated accordingly
- [ ] All tests pass: `pytest tests/unit/domain/ -v` (158/158 passing)
- [ ] Architecture plan updated to reflect Portfolio full immutability
- [ ] Design decision documented for business rule validation strategy
- [ ] No breaking changes to existing API

## Validation

```bash
# Run from backend/
uv run ruff check src/papertrade/domain
uv run ruff format --check src/papertrade/domain
uv run pytest tests/unit/domain/ -v --tb=short
```

All should pass with no errors.

## Estimated Time

**Total**: 40 minutes - 1 hour

## Notes

- These changes are **non-breaking** - they fix bugs and clarify documentation
- All tests should continue to pass (may need minor test updates for Holding equality)
- This can run **in parallel** with task 007b (Application Layer implementation)
- Commit message: `refactor(domain): Fix linting, Holding equality, and documentation`

## Dependencies

**Depends on**: Task 007 (Domain Layer) - PR #12 merged
**Blocks**: Nothing - can run in parallel with 007b

## Related

- PR #12: Initial domain layer implementation
- Task 007b: Application Layer implementation (can proceed in parallel)
- BACKLOG.md: Tracks all minor refinements
