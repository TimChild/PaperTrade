# Domain Layer Architecture

## Overview

The Domain layer is the heart of PaperTrade and contains the core business logic. It follows **Clean Architecture** principles, maintaining complete independence from infrastructure concerns (databases, APIs, frameworks).

### Key Principles

1. **Pure Python**: Minimal dependencies on external frameworks or infrastructure
2. **Immutable by Default**: Value objects and ledger entries use Pydantic with frozen=True
3. **Explicit Invariants**: Business rules enforced through types and validation
4. **Testability**: Pure functions and domain logic testable without I/O

## Architecture Layers

```
┌─────────────────────────────────────────┐
│           Infrastructure                │
│  (Docker, AWS CDK, DB Config)           │
├─────────────────────────────────────────┤
│              Adapters                   │
│  ┌─────────────┐    ┌─────────────┐     │
│  │   Inbound   │    │  Outbound   │     │
│  │  (FastAPI,  │    │ (Postgres,  │     │
│  │    CLI)     │    │  APIs)      │     │
│  └─────────────┘    └─────────────┘     │
├─────────────────────────────────────────┤
│           Application                   │
│  (Use Cases: ExecuteTrade,              │
│   GetPortfolioValue, etc.)              │
├─────────────────────────────────────────┤
│              Domain                     │  ◄── YOU ARE HERE
│  (Entities: Portfolio, Transaction)     │
│  (Value Objects: Money, Ticker)         │
│  (Domain Services)                      │
└─────────────────────────────────────────┘

Dependencies point INWARD only.
```

## Domain Components

### Value Objects
Immutable objects defined by their values, not identity.

- **[Money](./value-objects.md#money)**: Monetary amounts with currency
- **[Ticker](./value-objects.md#ticker)**: Stock ticker symbols
- **[Quantity](./value-objects.md#quantity)**: Share quantities (supports fractional)

→ **[Full Value Objects Documentation](./value-objects.md)**

### Entities
Objects with identity that can change over time.

- **[Portfolio](./entities.md#portfolio)**: A user's trading account
- **[Transaction](./entities.md#transaction)**: Immutable ledger entries
- **[Holding](./entities.md#holding)**: Derived view of current positions

→ **[Full Entities Documentation](./entities.md)**

### Domain Services
Stateless services encapsulating domain logic that doesn't belong to a single entity.

- **[PortfolioCalculator](./services.md#portfoliocalculator)**: Calculates portfolio state from transactions

→ **[Full Services Documentation](./services.md)**

### Repository Ports
Interfaces defining contracts for persistence (implemented by adapters).

- **[PortfolioRepository](./repository-ports.md#portfoliorepository)**: Portfolio persistence
- **[TransactionRepository](./repository-ports.md#transactionrepository)**: Transaction ledger persistence

→ **[Full Repository Ports Documentation](./repository-ports.md)**

### Business Rules
Core invariants and validation rules.

→ **[Full Business Rules Documentation](./domain-rules.md)**

## The Ledger Pattern

PaperTrade uses an **event-sourced ledger** for financial transactions:

```
┌─────────────────────────────────────────┐
│        Transaction Ledger               │
│  (Immutable, Append-Only)               │
├─────────────────────────────────────────┤
│ 1. DEPOSIT: +$10,000                    │
│ 2. BUY: 10 AAPL @ $150 = -$1,500        │
│ 3. BUY: 5 GOOGL @ $140 = -$700          │
│ 4. SELL: 5 AAPL @ $160 = +$800          │
│ 5. DIVIDEND: +$8.50 (from AAPL)         │
└─────────────────────────────────────────┘
           ↓
    PortfolioCalculator
           ↓
┌─────────────────────────────────────────┐
│      Current Portfolio State            │
│  (Derived from Ledger)                  │
├─────────────────────────────────────────┤
│ Cash Balance: $8,608.50                 │
│ Holdings:                               │
│   - AAPL: 5 shares @ $150 avg cost      │
│   - GOOGL: 5 shares @ $140 avg cost     │
└─────────────────────────────────────────┘
```

**Benefits:**
- Complete audit trail
- Point-in-time portfolio reconstruction
- Natural support for backtesting
- No balance synchronization issues

## File Organization

```
backend/src/papertrade/domain/
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
│   ├── portfolio_repository.py  (Protocol)
│   └── transaction_repository.py  (Protocol)
└── exceptions.py
```

## Design Decisions

### Why Value Objects?

Value objects provide:
- **Immutability**: No accidental mutations
- **Type Safety**: Can't accidentally use a string where Money is expected
- **Domain Semantics**: `Money(100, "USD")` is clearer than `100.0`
- **Validation**: Rules enforced at construction time

### Why Pydantic BaseModel?

We use Pydantic BaseModel (with `frozen=True` for value objects) instead of dataclasses:

Benefits:
- **Built-in Validation**: Automatic field type and constraint validation
- **Field Validators**: Custom validation logic with `@field_validator`
- **Model Validators**: Cross-field validation with `@model_validator`
- **JSON Serialization**: Built-in `.model_dump()` and `.model_validate()`
- **Immutability**: Supports `frozen=True` like dataclasses
- **Clear Error Messages**: Detailed validation errors for API responses

Perfect for domain objects that need strong validation and API integration.

### Why Protocol for Repository Interfaces?

```python
class PortfolioRepository(Protocol):
    async def get(self, portfolio_id: UUID) -> Portfolio | None: ...
```

Benefits:
- Structural typing (duck typing with types)
- No runtime overhead
- Clear contract without coupling to implementation
- Multiple implementations (in-memory, PostgreSQL, mock)

## Core Invariants

These invariants are **always** maintained by the domain:

1. **Money Precision**: All monetary amounts limited to 2 decimal places
2. **Positive Quantities**: Share quantities must be positive
3. **Ledger Immutability**: Transactions never modified after creation
4. **Portfolio Consistency**: Cash/holdings always derivable from transactions
5. **Transaction Validity**: Buy/sell must include ticker, quantity, price

## Testing Strategy

### Unit Tests
- Test value object validation and operations
- Test entity invariants
- Test domain service calculations
- **No I/O**: All domain tests are pure

### Property-Based Tests
Using Hypothesis to verify:
- Money arithmetic properties (commutativity, associativity)
- Portfolio balance consistency
- Holdings quantity = Σ(buys) - Σ(sells)

### Example
```python
from hypothesis import given
from hypothesis.strategies import decimals

@given(decimals(min_value=0, max_value=1_000_000, places=2))
def test_money_addition_commutative(amount: Decimal):
    a = Money(amount, "USD")
    b = Money(amount, "USD")
    assert a + b == b + a
```

## Implementation Guidelines

### For Backend Engineers

1. **Start with Value Objects**: Implement Money, Ticker, Quantity first
2. **Then Entities**: Portfolio, Transaction, Holding
3. **Then Services**: PortfolioCalculator
4. **Define Ports**: Repository interfaces as Protocols
5. **Write Tests**: Unit tests for every domain class
6. **Validate Types**: Run `pyright --strict` - should pass with zero errors

### Type Annotations
All domain code must have complete type hints:

```python
def calculate_total_value(
    holdings: list[Holding],
    prices: dict[Ticker, Money],
    cash_balance: Money,
) -> Money:
    """Calculate total portfolio value.

    Args:
        holdings: Current holdings
        prices: Current market prices per ticker
        cash_balance: Available cash

    Returns:
        Total portfolio value (holdings + cash)
    """
    ...
```

### No `Any` Types
The domain should never use `Any`. If you need flexibility, use:
- `Union` types
- Generics (`TypeVar`)
- Protocols

## Related Documentation

- **[project_strategy.md](../../../project_strategy.md)**: Overall architecture decisions
- **[agent_tasks/004_define-domain-entities-and-value-objects.md](../../../agent_tasks/004_define-domain-entities-and-value-objects.md)**: Original implementation specs
- **[DOCUMENTATION.md](../../../DOCUMENTATION.md)**: External references

## Next Steps

After reviewing this documentation:

1. Implement value objects (`backend/src/papertrade/domain/value_objects/`)
2. Implement entities (`backend/src/papertrade/domain/entities/`)
3. Implement domain services (`backend/src/papertrade/domain/services/`)
4. Define repository ports (`backend/src/papertrade/domain/repositories/`)
5. Write comprehensive unit tests

See **[agent_tasks/004b_implement-domain-layer.md](../../../agent_tasks/004b_implement-domain-layer.md)** for implementation task.
