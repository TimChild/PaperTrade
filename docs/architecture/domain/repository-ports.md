# Repository Ports

## Overview

Repository ports define **interfaces for persistence operations** without coupling to specific implementations. They follow the **Dependency Inversion Principle** - the domain defines what it needs, and adapters implement it.

### Port vs Adapter

```
┌─────────────────────────────────────────┐
│              Domain                     │
│  ┌─────────────────────────────────┐    │
│  │  PortfolioRepository (Port)     │    │  ◄── Interface defined by domain
│  │  - Protocol (structural typing) │    │
│  └─────────────────────────────────┘    │
└───────────────┬─────────────────────────┘
                │ implements
                ▼
┌─────────────────────────────────────────┐
│            Adapters                     │
│  ┌─────────────────────────────────┐    │
│  │ PostgresPortfolioRepository     │    │  ◄── Concrete implementation
│  │ - Actual database code          │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ InMemoryPortfolioRepository     │    │  ◄── Test implementation
│  │ - Uses dict for storage         │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**Key Points:**
- **Port**: Interface (Protocol) defined in domain layer
- **Adapter**: Implementation in infrastructure layer
- **Direction**: Domain defines the interface it needs
- **Benefits**: Domain is testable without real database

---

## Why Protocol (Not ABC)?

Python offers two approaches for defining interfaces:

### Option 1: Abstract Base Class (rejected)

```python
from abc import ABC, abstractmethod

class PortfolioRepository(ABC):
    @abstractmethod
    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        ...

# Problem: Implementations must inherit
class PostgresPortfolioRepository(PortfolioRepository):  # Must inherit!
    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        ...
```

### Option 2: Protocol (chosen)

```python
from typing import Protocol

class PortfolioRepository(Protocol):
    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        ...

# Benefit: Structural typing (duck typing with types)
class PostgresPortfolioRepository:  # No inheritance needed!
    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        ...

# Type checker verifies it matches the Protocol
def use_repo(repo: PortfolioRepository):
    # Works with any object that has the right methods
    ...
```

**Why Protocol?**
1. **Structural Typing**: No inheritance coupling
2. **Flexibility**: Can work with third-party classes
3. **Simplicity**: Clear interface without inheritance complexity
4. **Pythonic**: Matches Python's duck typing philosophy

---

## PortfolioRepository

### Purpose

Defines the contract for **Portfolio persistence operations**. Provides CRUD operations for Portfolio entities.

### Specification

```python
from typing import Protocol
from uuid import UUID

class PortfolioRepository(Protocol):
    """Port for Portfolio persistence operations.
    
    Implementations handle:
    - Database transactions
    - Error handling
    - Concurrency control
    """
    
    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        """Retrieve a portfolio by ID.
        
        Args:
            portfolio_id: Unique portfolio identifier
            
        Returns:
            Portfolio if found, None otherwise
        """
        ...
    
    async def get_by_user(self, user_id: UUID) -> list[Portfolio]:
        """Retrieve all portfolios for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of portfolios (empty if none found)
            
        Notes:
            Should return only non-archived portfolios by default.
            Use separate method for archived portfolios if needed.
        """
        ...
    
    async def save(self, portfolio: Portfolio) -> None:
        """Persist a portfolio (create or update).
        
        Args:
            portfolio: Portfolio to save
            
        Notes:
            - Creates if portfolio.id doesn't exist
            - Updates if portfolio.id exists
            - Should be idempotent
        """
        ...
    
    async def delete(self, portfolio_id: UUID) -> None:
        """Delete a portfolio.
        
        Args:
            portfolio_id: Portfolio to delete
            
        Notes:
            - Hard delete (removes from database)
            - Consider soft delete (archive) instead for audit trail
            - Should also cascade delete associated transactions
        """
        ...
```

### Method Semantics

#### get(portfolio_id: UUID)

**Purpose:** Fetch a single portfolio by ID.

**Returns:**
- `Portfolio` if found
- `None` if not found

**Does NOT raise exception** for missing portfolio - returns `None` instead.

**Example Usage:**
```python
portfolio = await repo.get(portfolio_id)
if portfolio is None:
    raise PortfolioNotFoundError(f"Portfolio {portfolio_id} not found")

# Use portfolio
print(portfolio.name)
```

#### get_by_user(user_id: UUID)

**Purpose:** Fetch all portfolios owned by a user.

**Returns:**
- `list[Portfolio]` (empty list if no portfolios)

**Filtering:**
- Should exclude archived portfolios by default
- Consider adding `include_archived: bool = False` parameter if needed

**Example Usage:**
```python
portfolios = await repo.get_by_user(user_id)
if not portfolios:
    # User has no portfolios, create default
    portfolio = Portfolio(id=uuid4(), user_id=user_id, name="My Portfolio", ...)
    await repo.save(portfolio)
```

#### save(portfolio: Portfolio)

**Purpose:** Persist a portfolio (upsert operation).

**Behavior:**
- **Create**: If `portfolio.id` doesn't exist in database
- **Update**: If `portfolio.id` exists in database

**Idempotency:** Calling `save()` multiple times with the same portfolio should have the same effect as calling it once.

**Transaction Boundary:** Implementations should ensure atomicity.

**Example Usage:**
```python
# Create new portfolio
portfolio = Portfolio(
    id=uuid4(),
    user_id=user_id,
    name="Growth Portfolio",
    created_at=datetime.now(UTC),
)
await repo.save(portfolio)

# Update existing portfolio
portfolio.rename("Aggressive Growth")
await repo.save(portfolio)  # Updates existing record
```

#### delete(portfolio_id: UUID)

**Purpose:** Remove a portfolio from the database.

**Behavior:**
- Hard delete (physical removal)
- Should cascade delete associated transactions
- **Consider soft delete (archive) instead** for audit trail

**Alternative:** Use `portfolio.archive()` + `save()` for soft delete:
```python
# Soft delete (preferred)
portfolio = await repo.get(portfolio_id)
portfolio.archive()
await repo.save(portfolio)

# Hard delete (use with caution)
await repo.delete(portfolio_id)
```

### Implementation Considerations

#### Transaction Management

```python
# Implementations should handle database transactions
class PostgresPortfolioRepository:
    async def save(self, portfolio: Portfolio) -> None:
        async with self.db.transaction():  # Atomic operation
            # Upsert portfolio
            await self.db.execute(...)
```

#### Error Handling

```python
# Implementations may raise infrastructure-specific errors
class PostgresPortfolioRepository:
    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        try:
            result = await self.db.fetch_one(...)
            return Portfolio(**result) if result else None
        except DatabaseError as e:
            # Log and re-raise as domain exception
            raise RepositoryError(f"Failed to fetch portfolio: {e}")
```

#### Concurrency Control

For updates, consider optimistic locking:

```python
# Add version field to Portfolio
@dataclass
class Portfolio:
    ...
    version: int = 1

# In repository implementation
async def save(self, portfolio: Portfolio) -> None:
    if portfolio exists in DB:
        # Check version hasn't changed
        if db_version != portfolio.version:
            raise ConcurrentModificationError()
        
        # Update and increment version
        portfolio.version += 1
    
    # Save portfolio
```

---

## TransactionRepository

### Purpose

Defines the contract for **Transaction ledger persistence**. Transactions are **immutable** - no update or delete operations.

### Specification

```python
from typing import Protocol
from uuid import UUID
from datetime import datetime

class TransactionRepository(Protocol):
    """Port for Transaction ledger persistence.
    
    Transactions are immutable (append-only ledger):
    - No UPDATE operation
    - No DELETE operation
    - Only INSERT (save) and READ (get)
    """
    
    async def get(self, transaction_id: UUID) -> Transaction | None:
        """Retrieve a transaction by ID.
        
        Args:
            transaction_id: Unique transaction identifier
            
        Returns:
            Transaction if found, None otherwise
        """
        ...
    
    async def get_by_portfolio(
        self,
        portfolio_id: UUID,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Transaction]:
        """Retrieve all transactions for a portfolio.
        
        Args:
            portfolio_id: Portfolio identifier
            since: Optional start time (inclusive)
            until: Optional end time (inclusive)
            
        Returns:
            List of transactions ordered by timestamp (oldest first)
            
        Notes:
            - Always returns chronologically ordered
            - Empty list if no transactions found
            - Time range is inclusive on both ends
        """
        ...
    
    async def save(self, transaction: Transaction) -> None:
        """Append a transaction to the ledger.
        
        Args:
            transaction: Transaction to save
            
        Raises:
            DuplicateTransactionError: If transaction.id already exists
            
        Notes:
            - Append-only (no updates)
            - Should verify transaction.id doesn't exist
            - Should be atomic
        """
        ...
```

### Immutability Constraints

**Critical:** Transactions are ledger entries and must NEVER be modified or deleted.

```python
# ✅ Allowed operations
await repo.save(transaction)  # Append to ledger
txn = await repo.get(txn_id)  # Read from ledger

# ❌ NOT allowed (methods don't exist)
# await repo.update(transaction)  # No such method!
# await repo.delete(txn_id)        # No such method!

# To "undo" a transaction, create a reversal:
original = Transaction(..., type=BUY, ticker="AAPL", quantity=10, price=150)
await repo.save(original)

# Reverse it (sell at same price)
reversal = Transaction(..., type=SELL, ticker="AAPL", quantity=10, price=150)
await repo.save(reversal)
```

**Why immutable?**
1. **Audit Trail**: Complete history preserved
2. **Compliance**: Financial regulations often require immutable ledgers
3. **Debugging**: Can replay events to understand state
4. **Simplicity**: No complex update logic needed

### Method Semantics

#### get(transaction_id: UUID)

**Purpose:** Fetch a single transaction by ID.

**Returns:**
- `Transaction` if found
- `None` if not found

**Example Usage:**
```python
txn = await repo.get(transaction_id)
if txn is None:
    raise TransactionNotFoundError()
```

#### get_by_portfolio(portfolio_id, since=None, until=None)

**Purpose:** Fetch all transactions for a portfolio, optionally filtered by time range.

**Ordering:** Always returns transactions in chronological order (oldest first).

**Time Range:**
- `since`: Inclusive start time
- `until`: Inclusive end time
- Both optional

**Example Usage:**
```python
# Get all transactions
all_txns = await repo.get_by_portfolio(portfolio_id)

# Get transactions in date range
from datetime import datetime, UTC
start = datetime(2024, 1, 1, tzinfo=UTC)
end = datetime(2024, 12, 31, tzinfo=UTC)
txns_2024 = await repo.get_by_portfolio(
    portfolio_id,
    since=start,
    until=end,
)

# Calculate state at specific time
portfolio_state_jan_1 = calculator.calculate_cash_balance(
    await repo.get_by_portfolio(portfolio_id, until=start)
)
```

**Time Travel:** This enables point-in-time portfolio reconstruction:
```python
async def get_portfolio_value_at(
    portfolio_id: UUID,
    as_of: datetime,
    repo: TransactionRepository,
) -> Money:
    # Get transactions up to specified time
    txns = await repo.get_by_portfolio(portfolio_id, until=as_of)
    
    # Calculate state at that time
    cash = calculator.calculate_cash_balance(txns)
    holdings = calculator.calculate_holdings(txns)
    
    # Get historical prices at that time
    prices = await market_data.get_prices_at(as_of, [h.ticker for h in holdings])
    
    return calculator.calculate_total_value(holdings, prices, cash)
```

#### save(transaction: Transaction)

**Purpose:** Append a new transaction to the ledger.

**Behavior:**
- Inserts new transaction
- Should reject duplicate IDs
- Should be atomic

**Error Cases:**
- `DuplicateTransactionError`: If `transaction.id` already exists
- Implementations may add validation (e.g., verify portfolio exists)

**Example Usage:**
```python
txn = Transaction(
    id=uuid4(),
    portfolio_id=portfolio.id,
    type=TransactionType.DEPOSIT,
    amount=Money(Decimal("10000"), "USD"),
    timestamp=datetime.now(UTC),
)

await repo.save(txn)

# Trying to save again should fail
try:
    await repo.save(txn)
except DuplicateTransactionError:
    # Handle duplicate
    pass
```

### Implementation Considerations

#### Indexing

Implementations should create indexes for efficient queries:

```sql
-- PostgreSQL example
CREATE INDEX idx_transactions_portfolio_id ON transactions(portfolio_id);
CREATE INDEX idx_transactions_portfolio_timestamp 
    ON transactions(portfolio_id, timestamp);
```

#### Ordering Guarantee

The `get_by_portfolio` method **must** return transactions in chronological order:

```python
class PostgresTransactionRepository:
    async def get_by_portfolio(
        self,
        portfolio_id: UUID,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Transaction]:
        query = """
            SELECT * FROM transactions
            WHERE portfolio_id = $1
            AND ($2 IS NULL OR timestamp >= $2)
            AND ($3 IS NULL OR timestamp <= $3)
            ORDER BY timestamp ASC  -- Critical: Chronological order
        """
        rows = await self.db.fetch_all(query, portfolio_id, since, until)
        return [Transaction(**row) for row in rows]
```

#### Duplicate Prevention

```python
async def save(self, transaction: Transaction) -> None:
    # Check for duplicate ID
    existing = await self.get(transaction.id)
    if existing is not None:
        raise DuplicateTransactionError(
            f"Transaction {transaction.id} already exists"
        )
    
    # Insert transaction
    await self.db.execute("INSERT INTO transactions ...", transaction)
```

**Alternative:** Use database unique constraint:
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY,  -- Enforces uniqueness at DB level
    ...
);
```

---

## Testing Repositories

### Contract Tests

Define a test suite that **any** repository implementation must pass:

```python
import pytest
from abc import ABC, abstractmethod

class PortfolioRepositoryContractTests(ABC):
    """Contract tests that all PortfolioRepository implementations must pass."""
    
    @abstractmethod
    def create_repository(self) -> PortfolioRepository:
        """Factory method for creating repository instance."""
        ...
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_portfolio_returns_none(self):
        repo = self.create_repository()
        result = await repo.get(uuid4())
        assert result is None
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_portfolio(self):
        repo = self.create_repository()
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Portfolio",
            created_at=datetime.now(UTC),
        )
        
        await repo.save(portfolio)
        retrieved = await repo.get(portfolio.id)
        
        assert retrieved == portfolio
    
    @pytest.mark.asyncio
    async def test_get_by_user_returns_all_portfolios(self):
        repo = self.create_repository()
        user_id = uuid4()
        
        # Create multiple portfolios
        p1 = Portfolio(id=uuid4(), user_id=user_id, name="P1", ...)
        p2 = Portfolio(id=uuid4(), user_id=user_id, name="P2", ...)
        await repo.save(p1)
        await repo.save(p2)
        
        # Retrieve all
        portfolios = await repo.get_by_user(user_id)
        assert len(portfolios) == 2
        assert {p.name for p in portfolios} == {"P1", "P2"}


class TestPostgresPortfolioRepository(PortfolioRepositoryContractTests):
    """Test PostgreSQL implementation against contract."""
    
    def create_repository(self) -> PortfolioRepository:
        return PostgresPortfolioRepository(database=test_db)


class TestInMemoryPortfolioRepository(PortfolioRepositoryContractTests):
    """Test in-memory implementation against contract."""
    
    def create_repository(self) -> PortfolioRepository:
        return InMemoryPortfolioRepository()
```

### In-Memory Test Implementation

For unit tests, provide a simple in-memory repository:

```python
class InMemoryPortfolioRepository:
    """In-memory repository for testing."""
    
    def __init__(self):
        self._portfolios: dict[UUID, Portfolio] = {}
    
    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        return self._portfolios.get(portfolio_id)
    
    async def get_by_user(self, user_id: UUID) -> list[Portfolio]:
        return [
            p for p in self._portfolios.values()
            if p.user_id == user_id and not p.archived
        ]
    
    async def save(self, portfolio: Portfolio) -> None:
        self._portfolios[portfolio.id] = portfolio
    
    async def delete(self, portfolio_id: UUID) -> None:
        self._portfolios.pop(portfolio_id, None)


class InMemoryTransactionRepository:
    """In-memory transaction repository for testing."""
    
    def __init__(self):
        self._transactions: dict[UUID, Transaction] = {}
    
    async def get(self, transaction_id: UUID) -> Transaction | None:
        return self._transactions.get(transaction_id)
    
    async def get_by_portfolio(
        self,
        portfolio_id: UUID,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Transaction]:
        txns = [
            t for t in self._transactions.values()
            if t.portfolio_id == portfolio_id
        ]
        
        # Filter by time range
        if since is not None:
            txns = [t for t in txns if t.timestamp >= since]
        if until is not None:
            txns = [t for t in txns if t.timestamp <= until]
        
        # Sort chronologically
        return sorted(txns, key=lambda t: t.timestamp)
    
    async def save(self, transaction: Transaction) -> None:
        if transaction.id in self._transactions:
            raise DuplicateTransactionError(f"Transaction {transaction.id} exists")
        self._transactions[transaction.id] = transaction
```

---

## Design Rationale

### Why Async Methods?

All repository methods are `async` to support:
1. **I/O operations**: Database queries are I/O-bound
2. **Concurrency**: FastAPI and modern Python are async
3. **Scalability**: Non-blocking operations improve throughput

Even in-memory implementations use `async` to match the interface:
```python
async def get(self, portfolio_id: UUID) -> Portfolio | None:
    # Even though this is instant, keep it async to match interface
    return self._portfolios.get(portfolio_id)
```

### Why No Update Method for Transactions?

**Ledger Pattern**: Transactions represent historical facts that cannot change.

```python
# ❌ If we allowed updates:
original = Transaction(..., amount=Money(1000))
await repo.save(original)

# Later: Modify it
original.amount = Money(2000)
await repo.update(original)  # History is rewritten! ❌

# Problem: Lost audit trail, breaks point-in-time reconstruction
```

**Solution:** To correct an error, create a reversal transaction:
```python
# Original (wrong amount)
wrong = Transaction(..., type=DEPOSIT, amount=Money(1000))
await repo.save(wrong)

# Reversal
reversal = Transaction(..., type=WITHDRAWAL, amount=Money(1000))
await repo.save(reversal)

# Correction
correct = Transaction(..., type=DEPOSIT, amount=Money(2000))
await repo.save(correct)

# Net effect: $2000 deposited, with full audit trail
```

### Why Return None Instead of Raising Exception?

**get() returns None** instead of raising exception for missing items:

```python
# ✅ Chosen approach
portfolio = await repo.get(portfolio_id)
if portfolio is None:
    # Handle missing case
    raise PortfolioNotFoundError()

# ❌ Alternative (not chosen)
try:
    portfolio = await repo.get(portfolio_id)
except PortfolioNotFoundError:
    # Handle missing case
    pass
```

**Rationale:**
- "Not found" is a **valid result**, not an error
- Reduces exception handling boilerplate
- Pythonic (`None` indicates absence)
- Exceptions should be for **exceptional** cases

---

## References

- **[Entities](./entities.md)**: Portfolio and Transaction entity definitions
- **[Domain Rules](./domain-rules.md)**: Validation rules enforced before persistence
- **[Services](./services.md)**: Domain services that use repositories to fetch data
