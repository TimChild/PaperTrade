# Task 007: Implement Phase 1 Domain Layer

## Objective
Implement the complete domain layer for Phase 1 Backend MVP according to the architecture plan. This is the foundation that all other layers depend on.

## Context
This task implements the **innermost layer** of Clean Architecture - pure business logic with zero external dependencies. Everything else (application, adapters, infrastructure) will be built on top of this foundation.

## Architecture Plan Reference
📐 **REQUIRED READING**: `docs/architecture/20251227_phase1-backend-mvp/`

Read these documents IN ORDER before starting:
1. `overview.md` - System context and architecture layers
2. `domain-layer.md` - Complete specifications for domain components
3. `implementation-sequence.md` - Step-by-step guide (Phase 1 only)
4. `design-decisions.md` - Rationale for key decisions

## Implementation Scope

### File Structure to Create
```
backend/src/zebu/domain/
├── __init__.py
├── exceptions.py
├── value_objects/
│   ├── __init__.py
│   ├── money.py
│   ├── ticker.py
│   └── quantity.py
├── entities/
│   ├── __init__.py
│   ├── portfolio.py
│   ├── transaction.py
│   └── holding.py
└── services/
    ├── __init__.py
    └── portfolio_calculator.py
```

### Test Structure to Create
```
backend/tests/unit/domain/
├── __init__.py
├── test_exceptions.py
├── value_objects/
│   ├── __init__.py
│   ├── test_money.py
│   ├── test_ticker.py
│   └── test_quantity.py
├── entities/
│   ├── __init__.py
│   ├── test_portfolio.py
│   ├── test_transaction.py
│   └── test_holding.py
└── services/
    ├── __init__.py
    └── test_portfolio_calculator.py
```

## Implementation Requirements

### 1. Follow Architecture Plan Exactly
- Implement ALL specifications from `domain-layer.md`
- Use the structured tables as your specification
- Do NOT deviate from the documented designs

### 2. Test-Driven Development
- Write tests BEFORE implementation for each component
- Follow test cases specified in `implementation-sequence.md`
- Verify tests fail first (red), then implement (green)
- Aim for 90%+ test coverage on domain layer

### 3. Domain Purity
- ✅ ONLY import from Python standard library
- ✅ Use `decimal.Decimal`, `datetime`, `uuid`, `typing`
- ❌ NO imports from application, adapters, or infrastructure layers
- ❌ NO imports from FastAPI, SQLModel, or any framework
- ❌ NO I/O operations (file, network, database)

### 4. Type Safety
- Complete type hints on ALL functions and methods
- Use strict type checking (Pyright strict mode)
- No `Any` types allowed
- Use Protocol for interfaces if needed

### 5. Immutability Where Required
- Value Objects: Completely immutable (frozen dataclasses)
- Transaction Entity: Completely immutable after creation
- Portfolio Entity: Mostly immutable (only name can change)

## Implementation Order

Follow this sequence from `implementation-sequence.md` Section 1:

### Step 1: Value Objects (2-3 hours)
1. **Money** - Amount with currency, arithmetic operations
2. **Ticker** - Stock symbol validation
3. **Quantity** - Share count, non-negative

### Step 2: Domain Exceptions (30 minutes)
Create exception hierarchy in `exceptions.py`

### Step 3: Entities (2-3 hours)
1. **Portfolio** - Aggregate root with identity
2. **Transaction** - Immutable ledger entry (DEPOSIT, WITHDRAWAL, BUY, SELL)
3. **Holding** - Derived entity (calculated, not persisted)

### Step 4: Domain Services (1-2 hours)
1. **PortfolioCalculator** - Pure functions for state calculation
   - calculate_cash_balance
   - calculate_holdings
   - calculate_holding_for_ticker

## Success Criteria

Before considering this task complete:

### Functional
- [ ] All value objects implemented with validation
- [ ] All entities implemented with invariants
- [ ] PortfolioCalculator implements all required methods
- [ ] Domain exceptions hierarchy complete

### Testing
- [ ] All unit tests pass: `pytest tests/unit/domain -v`
- [ ] Test coverage > 90%: `pytest --cov=zebu.domain --cov-report=term-missing`
- [ ] All test cases from implementation-sequence.md covered

### Code Quality
- [ ] Type checking passes: `pyright src/zebu/domain`
- [ ] Linting passes: `ruff check src/zebu/domain`
- [ ] Formatting correct: `ruff format --check src/zebu/domain`
- [ ] NO external dependencies in domain layer (verify imports)

### Validation
- [ ] Money arithmetic works correctly (add, subtract, multiply)
- [ ] Money enforces currency matching
- [ ] Ticker validates symbol format
- [ ] Quantity enforces non-negativity
- [ ] Transaction validates type-specific constraints
- [ ] PortfolioCalculator derives correct balance from transactions
- [ ] PortfolioCalculator derives correct holdings from buy/sell transactions
- [ ] Cost basis reduces proportionally on SELL transactions

## Key Design Principles to Follow

From `design-decisions.md`:

1. **Immutable Ledger** - Transactions never change after creation
2. **Derived State** - Holdings calculated, not stored
3. **Value Objects** - Strong typing for Money, Ticker, Quantity
4. **Pure Functions** - PortfolioCalculator has no side effects
5. **Type Safety** - Prevents mixing incompatible types

## Common Pitfalls to Avoid

From `implementation-sequence.md`:

1. ❌ **Don't**: Import outer layers in domain
   ✅ **Do**: Keep domain pure Python

2. ❌ **Don't**: Allow transaction mutations
   ✅ **Do**: Make transactions completely immutable

3. ❌ **Don't**: Skip tests
   ✅ **Do**: Write tests first (TDD)

4. ❌ **Don't**: Use `float` for money
   ✅ **Do**: Use `Decimal` for precision

5. ❌ **Don't**: Store holdings
   ✅ **Do**: Calculate holdings from transactions

## Testing Strategy

### Value Object Tests
For each value object (Money, Ticker, Quantity):
- Valid construction
- Invalid construction raises appropriate exception
- Arithmetic operations (where applicable)
- Equality and comparison
- Immutability (cannot modify after creation)
- String representation

### Entity Tests
For each entity (Portfolio, Transaction, Holding):
- Valid construction
- Invalid construction raises exception
- Invariants are maintained
- Equality based on identity (Portfolio, Transaction) or ticker (Holding)
- Immutability where required

### Domain Service Tests
For PortfolioCalculator:
- Empty transaction list edge cases
- Single transaction types
- Multiple transaction sequences
- Buy/sell cycles for same ticker
- Cost basis calculations with partial sells
- Property-based tests: balance = sum(all cash_change)

## Reference Material

### From Architecture Plan
- `domain-layer.md` - Complete specifications (MAIN REFERENCE)
- `implementation-sequence.md` - Step-by-step guide (Phase 1, Steps 1.1-1.4)
- `design-decisions.md` - ADR-005 (Value Objects), ADR-002 (Derived Holdings)

### From Project Docs
- `project_strategy.md` - Clean Architecture principles
- `.github/copilot-instructions.md` - General coding guidelines
- `.github/agents/backend-swe.md` - Your role and responsibilities

## Progress Documentation

After completion, create progress document:
```bash
date "+%Y-%m-%d_%H-%M-%S"  # Get timestamp
# Create: agent_tasks/progress/TIMESTAMP_domain-layer-implementation.md
```

Document:
- Task completion summary
- Any deviations from architecture plan (with justification)
- Test coverage achieved
- Challenges encountered and solutions
- Verification checklist results

## Next Steps After Completion

Once this task is complete and PR is merged:
- Task 007b: Implement Application Layer (use cases, repository ports)
- Task 007c: Implement Adapters Layer (repositories, FastAPI routes)

The domain layer is the foundation - everything else builds on this!
