# Task 004: Define Domain Entities and Value Objects

## Objective
Design and implement the core domain layer for PaperTrade following Clean Architecture and Domain-Driven Design principles.

## Context
This is the first Phase 1 task. The domain layer is the heart of the application and must be pure Python with no dependencies on infrastructure (databases, APIs, frameworks).

## Requirements

### Value Objects (Immutable)

#### Money
```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    # Operations: add, subtract, multiply (by scalar)
    # Validation: amount precision, currency codes
    # Comparison: equality, less than, greater than
```

#### Ticker
```python
@dataclass(frozen=True)
class Ticker:
    symbol: str

    # Validation: 1-5 uppercase letters
    # Normalization: uppercase on creation
```

#### Quantity
```python
@dataclass(frozen=True)
class Quantity:
    value: Decimal

    # Validation: must be positive
    # Support fractional shares
```

### Entities

#### Portfolio
```python
@dataclass
class Portfolio:
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime

    # Methods to calculate:
    # - cash_balance (derived from transactions)
    # - holdings (derived from transactions)
    # - total_value (requires current prices)
```

#### Transaction (Ledger Entry)
```python
class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"  # Future use
    FEE = "fee"  # Future use

@dataclass(frozen=True)  # Immutable ledger entry
class Transaction:
    id: UUID
    portfolio_id: UUID
    type: TransactionType
    amount: Money  # Always positive, type determines direction
    ticker: Ticker | None  # Required for BUY/SELL
    quantity: Quantity | None  # Required for BUY/SELL
    price_per_share: Money | None  # Required for BUY/SELL
    timestamp: datetime
    notes: str | None = None
```

#### Holding (Derived/Computed)
```python
@dataclass(frozen=True)
class Holding:
    ticker: Ticker
    quantity: Quantity
    average_cost: Money  # Cost basis per share

    @property
    def total_cost(self) -> Money:
        ...
```

### Domain Services

#### PortfolioCalculator
```python
class PortfolioCalculator:
    """Calculates portfolio state from transaction history."""

    @staticmethod
    def calculate_cash_balance(transactions: list[Transaction]) -> Money:
        """Sum all cash movements."""
        ...

    @staticmethod
    def calculate_holdings(transactions: list[Transaction]) -> list[Holding]:
        """Aggregate buy/sell transactions into current holdings."""
        ...

    @staticmethod
    def calculate_total_value(
        holdings: list[Holding],
        prices: dict[Ticker, Money],
        cash_balance: Money,
    ) -> Money:
        """Calculate total portfolio value at given prices."""
        ...
```

### Domain Exceptions
```python
class DomainError(Exception):
    """Base class for domain errors."""
    pass

class InsufficientFundsError(DomainError):
    """Raised when a trade exceeds available cash."""
    pass

class InsufficientSharesError(DomainError):
    """Raised when selling more shares than owned."""
    pass

class InvalidTransactionError(DomainError):
    """Raised when a transaction violates business rules."""
    pass
```

### Repository Interfaces (Ports)

Define as Protocols in the domain layer:
```python
class PortfolioRepository(Protocol):
    async def get(self, portfolio_id: UUID) -> Portfolio | None: ...
    async def get_by_user(self, user_id: UUID) -> list[Portfolio]: ...
    async def save(self, portfolio: Portfolio) -> None: ...
    async def delete(self, portfolio_id: UUID) -> None: ...

class TransactionRepository(Protocol):
    async def get(self, transaction_id: UUID) -> Transaction | None: ...
    async def get_by_portfolio(self, portfolio_id: UUID) -> list[Transaction]: ...
    async def save(self, transaction: Transaction) -> None: ...
    # Note: No delete - ledger is immutable
```

## File Structure
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
│   ├── portfolio_repository.py
│   └── transaction_repository.py
└── exceptions.py
```

## Testing Requirements

Create comprehensive unit tests for:
- [ ] Money arithmetic and validation
- [ ] Ticker validation and normalization
- [ ] Quantity validation
- [ ] Transaction creation and validation
- [ ] PortfolioCalculator.calculate_cash_balance
- [ ] PortfolioCalculator.calculate_holdings
- [ ] PortfolioCalculator.calculate_total_value

Use property-based testing (Hypothesis) for:
- Money arithmetic properties (associative, commutative for add)
- Portfolio balance should never be negative after valid transactions
- Holdings quantity should match sum of buy - sell transactions

## Success Criteria
- [ ] All domain classes have complete type hints
- [ ] All value objects are immutable (frozen dataclasses)
- [ ] Domain has ZERO imports from adapters/infrastructure
- [ ] 100% test coverage on domain logic
- [ ] pyright passes in strict mode
- [ ] ruff passes with no errors

## References
- See `.github/agents/architect.md` for design principles
- See `project_strategy.md` for architecture decisions
- See `.github/copilot-instructions.md` for general guidelines

## Notes
- Keep the domain PURE - no I/O, no side effects
- Prefer composition over inheritance
- Make invalid states unrepresentable through types
- The ledger pattern means we never delete or modify transactions
