# Task 004b: Implement Domain Layer

## Objective
Implement the Zebu domain layer based on the architecture documentation in `docs/architecture/domain/`.

## Prerequisites
- Architecture documentation must exist in `docs/architecture/domain/`
- Read ALL architecture docs before starting implementation

## Implementation Scope

### File Structure
```
backend/src/zebu/domain/
├── __init__.py
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
├── services/
│   ├── __init__.py
│   └── portfolio_calculator.py
├── repositories/
│   ├── __init__.py
│   ├── portfolio_repository.py
│   └── transaction_repository.py
└── exceptions.py
```

### Implementation Requirements
1. Follow specifications in `docs/architecture/domain/` exactly
2. All domain classes must have complete type hints
3. Value objects must be immutable (frozen dataclasses)
4. Domain has ZERO imports from adapters/infrastructure
5. Use Protocol for repository interfaces (ports)

## Testing Requirements

Create tests in `backend/tests/domain/`:
```
backend/tests/domain/
├── __init__.py
├── test_value_objects/
│   ├── __init__.py
│   ├── test_money.py
│   ├── test_ticker.py
│   └── test_quantity.py
├── test_entities/
│   ├── __init__.py
│   ├── test_transaction.py
│   └── test_holding.py
└── test_services/
    ├── __init__.py
    └── test_portfolio_calculator.py
```

### Test Coverage Requirements
- [ ] Money arithmetic and validation
- [ ] Ticker validation and normalization
- [ ] Quantity validation
- [ ] Transaction creation and validation
- [ ] PortfolioCalculator.calculate_cash_balance
- [ ] PortfolioCalculator.calculate_holdings
- [ ] PortfolioCalculator.calculate_total_value

### Property-Based Testing (Hypothesis)
Include property-based tests for:
- Money arithmetic properties
- Portfolio balance calculations
- Holdings aggregation

## Success Criteria
- [ ] All domain classes implemented per architecture docs
- [ ] 100% test coverage on domain logic
- [ ] pyright passes in strict mode
- [ ] ruff passes with no errors
- [ ] All tests pass

## References
- `docs/architecture/domain/` - **Primary reference - read first!**
- `agent_tasks/004_define-domain-entities-and-value-objects.md` - Original specifications
- `.github/copilot-instructions.md` - General guidelines

## Notes
- Keep the domain PURE - no I/O, no side effects
- Make invalid states unrepresentable through types
- The ledger pattern means we never delete or modify transactions
