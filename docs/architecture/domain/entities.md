# Entities

## Overview

Entities are **domain objects with identity** that can change over time. Unlike value objects, two entities with the same field values but different IDs are considered different objects.

### Entity vs Value Object

| Aspect | Entity | Value Object |
|--------|--------|--------------|
| **Identity** | Has unique ID | No identity, defined by values |
| **Mutability** | Can change over time | Immutable |
| **Equality** | By ID | By value |
| **Lifecycle** | Created, modified, archived | Created, never modified |
| **Example** | Portfolio, User | Money, Ticker |

### Entity Characteristics

```python
# Entities have identity
portfolio1 = Portfolio(id=UUID("..."), name="Growth Portfolio")
portfolio2 = Portfolio(id=UUID("..."), name="Growth Portfolio")
assert portfolio1 != portfolio2  # Different IDs = different entities

# Entities can be modified (through proper methods)
portfolio1.rename("Aggressive Growth")

# Value objects have no identity
money1 = Money(Decimal("100"), "USD")
money2 = Money(Decimal("100"), "USD")
assert money1 == money2  # Same values = equal
```

---

## Portfolio

### Purpose

Represents a **user's trading account** - the primary aggregate root for trading operations. Contains metadata about the portfolio but derives its state (cash, holdings) from the transaction ledger.

### Specification

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class Portfolio:
    """A user's trading portfolio.
    
    The Portfolio is an aggregate root that owns Transactions.
    Current state (cash, holdings) is derived from transaction history.
    
    Examples:
        >>> portfolio = Portfolio(
        ...     id=uuid4(),
        ...     user_id=uuid4(),
        ...     name="Growth Portfolio",
        ...     created_at=datetime.now(UTC)
        ... )
    """
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    archived: bool = False
```

### Properties

| Property | Type | Description | Mutable? |
|----------|------|-------------|----------|
| `id` | `UUID` | Unique portfolio identifier | No (identity) |
| `user_id` | `UUID` | Owner's user ID | No |
| `name` | `str` | User-defined portfolio name | Yes |
| `created_at` | `datetime` | Creation timestamp (UTC) | No |
| `archived` | `bool` | Soft delete flag | Yes |

### Identity

The `id` field provides identity. Two portfolios with the same name and user but different IDs are distinct entities.

```python
def __eq__(self, other: object) -> bool:
    """Portfolios are equal if they have the same ID."""
    if not isinstance(other, Portfolio):
        return NotImplemented
    return self.id == other.id

def __hash__(self) -> int:
    """Hash by ID for use in sets/dicts."""
    return hash(self.id)
```

### Lifecycle

```
┌─────────────┐
│   Created   │  (name, user_id provided)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Active    │  (can execute trades, rename)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Archived   │  (read-only, soft deleted)
└─────────────┘
```

**States:**
1. **Created**: New portfolio, no transactions yet
2. **Active**: Normal state, can execute trades
3. **Archived**: Soft-deleted, read-only

### Domain Methods

```python
def rename(self, new_name: str) -> None:
    """Change portfolio name.
    
    Args:
        new_name: New portfolio name (non-empty)
        
    Raises:
        ValueError: If name is empty
    """
    if not new_name or not new_name.strip():
        raise ValueError("Portfolio name cannot be empty")
    self.name = new_name.strip()

def archive(self) -> None:
    """Archive (soft delete) the portfolio.
    
    Archived portfolios are read-only and hidden from active lists.
    """
    self.archived = True

def unarchive(self) -> None:
    """Restore an archived portfolio."""
    self.archived = False
```

### Derived State

The Portfolio's **financial state is NOT stored** in the entity itself. Instead, it's calculated from the transaction ledger:

```python
# NOT part of the Portfolio entity:
# - cash_balance: Calculated by PortfolioCalculator
# - holdings: Calculated by PortfolioCalculator
# - total_value: Calculated by PortfolioCalculator (requires prices)

# Example usage (in Application layer)
async def get_portfolio_state(
    portfolio: Portfolio,
    calculator: PortfolioCalculator,
    transaction_repo: TransactionRepository,
    market_data: MarketDataPort,
) -> PortfolioState:
    """Get current portfolio state."""
    transactions = await transaction_repo.get_by_portfolio(portfolio.id)
    
    cash = calculator.calculate_cash_balance(transactions)
    holdings = calculator.calculate_holdings(transactions)
    
    prices = await market_data.get_current_prices(
        [h.ticker for h in holdings]
    )
    
    total_value = calculator.calculate_total_value(holdings, prices, cash)
    
    return PortfolioState(
        portfolio=portfolio,
        cash_balance=cash,
        holdings=holdings,
        total_value=total_value,
    )
```

**Why derive instead of store?**
- **Single Source of Truth**: Ledger is authoritative
- **Time Travel**: Can calculate state at any point in time
- **Consistency**: No sync issues between balance and transactions
- **Audit Trail**: Complete history always available

### Invariants

1. **Name Required**: Portfolio name cannot be empty
2. **User Ownership**: Portfolio belongs to exactly one user
3. **Created Timestamp**: Must be valid UTC datetime
4. **Archive Constraint**: Archived portfolios should not accept new trades (enforced by use cases)

### Validation

```python
def __post_init__(self) -> None:
    """Validate portfolio invariants."""
    if not self.name or not self.name.strip():
        raise ValueError("Portfolio name cannot be empty")
    
    if not self.user_id:
        raise ValueError("Portfolio must belong to a user")
    
    # Ensure created_at is timezone-aware UTC
    if self.created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware (UTC)")
```

---

## Transaction

### Purpose

Represents an **immutable ledger entry** recording a financial event. Transactions are the foundation of the ledger pattern - they are never modified or deleted.

### Specification

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Optional

class TransactionType(Enum):
    """Types of financial transactions."""
    DEPOSIT = "deposit"        # Add cash to portfolio
    WITHDRAWAL = "withdrawal"  # Remove cash from portfolio
    BUY = "buy"               # Purchase shares
    SELL = "sell"             # Sell shares
    DIVIDEND = "dividend"     # Dividend payment (future)
    FEE = "fee"              # Trading fee (future)

@dataclass(frozen=True)
class Transaction:
    """Immutable ledger entry recording a financial event.
    
    Examples:
        >>> # Deposit
        >>> Transaction(
        ...     id=uuid4(),
        ...     portfolio_id=uuid4(),
        ...     type=TransactionType.DEPOSIT,
        ...     amount=Money(Decimal("10000"), "USD"),
        ...     ticker=None,
        ...     quantity=None,
        ...     price_per_share=None,
        ...     timestamp=datetime.now(UTC),
        ... )
        
        >>> # Buy
        >>> Transaction(
        ...     id=uuid4(),
        ...     portfolio_id=uuid4(),
        ...     type=TransactionType.BUY,
        ...     amount=Money(Decimal("1500"), "USD"),
        ...     ticker=Ticker("AAPL"),
        ...     quantity=Quantity(Decimal("10")),
        ...     price_per_share=Money(Decimal("150"), "USD"),
        ...     timestamp=datetime.now(UTC),
        ... )
    """
    id: UUID
    portfolio_id: UUID
    type: TransactionType
    amount: Money
    ticker: Optional[Ticker] = None
    quantity: Optional[Quantity] = None
    price_per_share: Optional[Money] = None
    timestamp: datetime
    notes: Optional[str] = None
```

### Properties

| Property | Type | Description | Required For |
|----------|------|-------------|--------------|
| `id` | `UUID` | Unique transaction ID | All |
| `portfolio_id` | `UUID` | Portfolio this belongs to | All |
| `type` | `TransactionType` | Transaction type | All |
| `amount` | `Money` | Monetary amount (always positive) | All |
| `ticker` | `Ticker \| None` | Stock symbol | BUY, SELL |
| `quantity` | `Quantity \| None` | Number of shares | BUY, SELL |
| `price_per_share` | `Money \| None` | Price per share | BUY, SELL |
| `timestamp` | `datetime` | When transaction occurred (UTC) | All |
| `notes` | `str \| None` | Optional notes | All |

### Transaction Types

#### DEPOSIT
Add cash to the portfolio.

```python
Transaction(
    id=uuid4(),
    portfolio_id=portfolio.id,
    type=TransactionType.DEPOSIT,
    amount=Money(Decimal("10000"), "USD"),
    ticker=None,
    quantity=None,
    price_per_share=None,
    timestamp=datetime.now(UTC),
    notes="Initial deposit",
)
```

**Effect:**
- Cash balance: `+amount`
- Holdings: No change

#### WITHDRAWAL
Remove cash from the portfolio.

```python
Transaction(
    id=uuid4(),
    portfolio_id=portfolio.id,
    type=TransactionType.WITHDRAWAL,
    amount=Money(Decimal("5000"), "USD"),
    ticker=None,
    quantity=None,
    price_per_share=None,
    timestamp=datetime.now(UTC),
)
```

**Effect:**
- Cash balance: `-amount`
- Holdings: No change

#### BUY
Purchase shares of a stock.

```python
Transaction(
    id=uuid4(),
    portfolio_id=portfolio.id,
    type=TransactionType.BUY,
    amount=Money(Decimal("1500"), "USD"),  # total cost
    ticker=Ticker("AAPL"),
    quantity=Quantity(Decimal("10")),
    price_per_share=Money(Decimal("150"), "USD"),
    timestamp=datetime.now(UTC),
    notes="AAPL looks undervalued",
)
```

**Effect:**
- Cash balance: `-amount`
- Holdings: `+quantity` of `ticker`
- Cost basis: `price_per_share`

**Invariant:** `amount == quantity.value * price_per_share.amount`

#### SELL
Sell shares of a stock.

```python
Transaction(
    id=uuid4(),
    portfolio_id=portfolio.id,
    type=TransactionType.SELL,
    amount=Money(Decimal("1600"), "USD"),  # total proceeds
    ticker=Ticker("AAPL"),
    quantity=Quantity(Decimal("10")),
    price_per_share=Money(Decimal("160"), "USD"),
    timestamp=datetime.now(UTC),
)
```

**Effect:**
- Cash balance: `+amount`
- Holdings: `-quantity` of `ticker`

**Invariant:** `amount == quantity.value * price_per_share.amount`

### Immutability

Transactions are **frozen dataclasses** - they cannot be modified after creation.

```python
# This is the ledger pattern:
# - Never UPDATE transactions
# - Never DELETE transactions
# - Only APPEND new transactions

# To "undo" a trade, create a reverse transaction:
# Original: BUY 10 AAPL @ $150
# Undo: SELL 10 AAPL @ $150 (same price, zero realized gain)
```

**Why immutable?**
1. **Audit Trail**: Complete history is preserved
2. **Time Travel**: Can reconstruct portfolio at any point
3. **Consistency**: No risk of lost updates or race conditions
4. **Simplicity**: No complex state management

### Validation

Transactions must satisfy type-specific invariants:

```python
def __post_init__(self) -> None:
    """Validate transaction invariants."""
    
    # All transactions need positive amount
    if self.amount.amount <= 0:
        raise InvalidTransactionError("Amount must be positive")
    
    # Timestamp must be timezone-aware UTC
    if self.timestamp.tzinfo is None:
        raise InvalidTransactionError("Timestamp must be timezone-aware (UTC)")
    
    # Trade transactions need ticker, quantity, price
    if self.type in (TransactionType.BUY, TransactionType.SELL):
        if self.ticker is None:
            raise InvalidTransactionError(f"{self.type.value} requires ticker")
        if self.quantity is None:
            raise InvalidTransactionError(f"{self.type.value} requires quantity")
        if self.price_per_share is None:
            raise InvalidTransactionError(f"{self.type.value} requires price_per_share")
        
        # Verify amount = quantity * price
        expected_amount = self.price_per_share.multiply(self.quantity.value)
        if self.amount != expected_amount:
            raise InvalidTransactionError(
                f"Amount mismatch: {self.amount} != {expected_amount}"
            )
    
    # Cash transactions should NOT have ticker/quantity/price
    elif self.type in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL):
        if self.ticker is not None:
            raise InvalidTransactionError(f"{self.type.value} should not have ticker")
        if self.quantity is not None:
            raise InvalidTransactionError(f"{self.type.value} should not have quantity")
        if self.price_per_share is not None:
            raise InvalidTransactionError(f"{self.type.value} should not have price")
```

### Identity

```python
def __eq__(self, other: object) -> bool:
    """Transactions are equal if they have the same ID."""
    if not isinstance(other, Transaction):
        return NotImplemented
    return self.id == other.id

def __hash__(self) -> int:
    """Hash by ID."""
    return hash(self.id)
```

---

## Holding

### Purpose

Represents a **current position in a stock** - a derived/computed view aggregated from the transaction ledger. Not stored directly, but calculated on demand.

### Specification

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Holding:
    """Current position in a stock (derived from transactions).
    
    Examples:
        >>> Holding(
        ...     ticker=Ticker("AAPL"),
        ...     quantity=Quantity(Decimal("10")),
        ...     average_cost=Money(Decimal("150"), "USD"),
        ... )
    """
    ticker: Ticker
    quantity: Quantity
    average_cost: Money  # Cost basis per share
    
    @property
    def total_cost(self) -> Money:
        """Total cost basis for this holding.
        
        Returns:
            Total amount paid for all shares (quantity × average_cost)
            
        Examples:
            >>> holding = Holding(
            ...     ticker=Ticker("AAPL"),
            ...     quantity=Quantity(Decimal("10")),
            ...     average_cost=Money(Decimal("150"), "USD"),
            ... )
            >>> holding.total_cost
            Money(amount=Decimal('1500.00'), currency='USD')
        """
        return self.average_cost.multiply(self.quantity.value)
```

### Properties

| Property | Type | Description | Computed? |
|----------|------|-------------|-----------|
| `ticker` | `Ticker` | Stock symbol | No |
| `quantity` | `Quantity` | Current shares owned | No |
| `average_cost` | `Money` | Cost basis per share | No |
| `total_cost` | `Money` | Total cost basis | Yes (property) |

### Derived Nature

Holdings are **NOT stored** as entities in the database. They are calculated from the transaction ledger by the `PortfolioCalculator`:

```python
# Example: How holdings are derived
transactions = [
    # BUY 10 AAPL @ $150
    Transaction(..., type=BUY, ticker="AAPL", quantity=10, price=150),
    # BUY 5 AAPL @ $160
    Transaction(..., type=BUY, ticker="AAPL", quantity=5, price=160),
    # SELL 5 AAPL @ $170
    Transaction(..., type=SELL, ticker="AAPL", quantity=5, price=170),
]

# Result: 10 shares remaining
# Average cost (FIFO): First 5 @ $150, next 5 @ $160 = avg $155
holding = Holding(
    ticker=Ticker("AAPL"),
    quantity=Quantity(Decimal("10")),
    average_cost=Money(Decimal("155"), "USD"),  # Weighted average
)
```

### Cost Basis Calculation

**FIFO (First In, First Out)** method:

```
Purchases:
1. BUY 10 @ $150 = $1,500
2. BUY 5 @ $160 = $800
Total: 15 shares for $2,300

Sell:
3. SELL 5 @ $170
   → Removes first 5 shares @ $150 (FIFO)
   → Realized gain: 5 × ($170 - $150) = $100

Remaining:
- 5 shares @ $150 (from first batch)
- 5 shares @ $160 (from second batch)
- Average cost: ($750 + $800) / 10 = $155
```

**Why FIFO?**
- Standard accounting method
- Tax-compliant in most jurisdictions
- Predictable and auditable

### Valuation

```python
def calculate_value(self, current_price: Money) -> Money:
    """Calculate current market value of holding.
    
    Args:
        current_price: Current market price per share
        
    Returns:
        Total market value (quantity × current_price)
        
    Examples:
        >>> holding = Holding(
        ...     ticker=Ticker("AAPL"),
        ...     quantity=Quantity(Decimal("10")),
        ...     average_cost=Money(Decimal("150"), "USD"),
        ... )
        >>> current_price = Money(Decimal("170"), "USD")
        >>> holding.calculate_value(current_price)
        Money(amount=Decimal('1700.00'), currency='USD')
    """
    return current_price.multiply(self.quantity.value)

def calculate_unrealized_gain_loss(self, current_price: Money) -> Money:
    """Calculate unrealized gain/loss.
    
    Args:
        current_price: Current market price per share
        
    Returns:
        Unrealized gain/loss (positive = gain, negative = loss)
        
    Examples:
        >>> holding = Holding(
        ...     ticker=Ticker("AAPL"),
        ...     quantity=Quantity(Decimal("10")),
        ...     average_cost=Money(Decimal("150"), "USD"),
        ... )
        >>> current_price = Money(Decimal("170"), "USD")
        >>> holding.calculate_unrealized_gain_loss(current_price)
        Money(amount=Decimal('200.00'), currency='USD')  # $20 × 10 shares
    """
    current_value = self.calculate_value(current_price)
    return current_value.subtract(self.total_cost)
```

### Immutability

Holdings are **value objects** - frozen and immutable. To update holdings, recalculate from the ledger.

```python
# Don't do this:
# holding.quantity = Quantity(Decimal("15"))  # Error: frozen!

# Instead:
# Add a new transaction to the ledger
new_transaction = Transaction(..., type=BUY, quantity=5, ...)
# Recalculate holdings from updated ledger
new_holdings = calculator.calculate_holdings(all_transactions)
```

---

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                          User                               │
│  (not in domain layer - lives in auth/user context)        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ owns (1:N)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Portfolio                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ id: UUID                                             │   │
│  │ user_id: UUID                                        │   │
│  │ name: str                                            │   │
│  │ created_at: datetime                                 │   │
│  │ archived: bool                                       │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ contains (1:N)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Transaction                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ id: UUID                                             │   │
│  │ portfolio_id: UUID                                   │   │
│  │ type: TransactionType                                │   │
│  │ amount: Money                                        │   │
│  │ ticker: Ticker | None                                │   │
│  │ quantity: Quantity | None                            │   │
│  │ price_per_share: Money | None                        │   │
│  │ timestamp: datetime                                  │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ aggregates to (N:M)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        Holding                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ticker: Ticker                                       │   │
│  │ quantity: Quantity                                   │   │
│  │ average_cost: Money                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  (Derived - not stored)                                     │
└─────────────────────────────────────────────────────────────┘
```

### Aggregate Boundaries

**Portfolio is the Aggregate Root:**
- Transactions belong to exactly one Portfolio
- External entities interact with Portfolio, not Transactions directly
- Portfolio enforces consistency boundaries

**Invariants enforced by Portfolio aggregate:**
- All Transactions must have valid portfolio_id
- Transaction timestamps must be sequential (for audit)
- Business rules (sufficient funds, shares) checked before adding Transaction

---

## Testing Entities

### Unit Tests

```python
import pytest
from datetime import datetime, UTC
from uuid import uuid4
from domain.entities import Portfolio, Transaction, Holding, TransactionType

class TestPortfolio:
    def test_create_portfolio(self):
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Portfolio",
            created_at=datetime.now(UTC),
        )
        assert portfolio.name == "Test Portfolio"
        assert not portfolio.archived
    
    def test_rename_portfolio(self):
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Old Name",
            created_at=datetime.now(UTC),
        )
        portfolio.rename("New Name")
        assert portfolio.name == "New Name"
    
    def test_archive_portfolio(self):
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            created_at=datetime.now(UTC),
        )
        portfolio.archive()
        assert portfolio.archived

class TestTransaction:
    def test_create_deposit(self):
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.DEPOSIT,
            amount=Money(Decimal("1000"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert txn.type == TransactionType.DEPOSIT
        assert txn.ticker is None
    
    def test_create_buy_with_all_required_fields(self):
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.BUY,
            amount=Money(Decimal("1500"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            price_per_share=Money(Decimal("150"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert txn.ticker == Ticker("AAPL")
        assert txn.quantity == Quantity(Decimal("10"))
    
    def test_buy_without_ticker_raises_error(self):
        with pytest.raises(InvalidTransactionError):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.BUY,
                amount=Money(Decimal("1500"), "USD"),
                ticker=None,  # Missing!
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150"), "USD"),
                timestamp=datetime.now(UTC),
            )

class TestHolding:
    def test_total_cost_calculation(self):
        holding = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            average_cost=Money(Decimal("150"), "USD"),
        )
        assert holding.total_cost == Money(Decimal("1500"), "USD")
    
    def test_calculate_value(self):
        holding = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            average_cost=Money(Decimal("150"), "USD"),
        )
        current_price = Money(Decimal("170"), "USD")
        assert holding.calculate_value(current_price) == Money(Decimal("1700"), "USD")
```

---

## Design Rationale

### Why Derive Holdings Instead of Storing?

**Option 1: Store Holdings (rejected)**
```python
# Portfolio table: id, name, cash_balance
# Holding table: portfolio_id, ticker, quantity, avg_cost
# Problem: Must keep in sync with transactions!
```

**Option 2: Derive Holdings (chosen)**
```python
# Portfolio table: id, name (metadata only)
# Transaction table: ledger entries (immutable)
# Holdings: Calculated from transactions when needed
```

**Benefits of derivation:**
- Single source of truth (transactions)
- No synchronization issues
- Time-travel capability
- Simpler consistency model

### Why Immutable Transactions?

The **ledger pattern** requires immutability:

1. **Audit Compliance**: Required for financial regulations
2. **Debugging**: Can replay events to understand state
3. **Consistency**: No lost updates or race conditions
4. **Simplicity**: Append-only data structure

### Why Portfolio Has No Balance Field?

```python
# Bad: Stored balance
@dataclass
class Portfolio:
    cash_balance: Money  # Risk: Out of sync with transactions!

# Good: Derived balance
# Calculate from transactions when needed
calculator.calculate_cash_balance(transactions)
```

**Problem with stored balance:**
- Transaction adds $100, but balance not updated → inconsistency
- Requires complex synchronization logic
- Can't reconstruct historical state

---

## References

- **[Value Objects](./value-objects.md)**: Money, Ticker, Quantity used by entities
- **[Services](./services.md)**: PortfolioCalculator derives entity state
- **[Domain Rules](./domain-rules.md)**: Business rules for entity validation
- **[Repository Ports](./repository-ports.md)**: Persistence interfaces for entities
