# Repository Ports

## Overview

Repository ports define **interfaces for persistence operations** without coupling to specific implementations. They follow the **Dependency Inversion Principle** - the domain defines what it needs, and infrastructure adapters implement it.

### Port vs Adapter Pattern

```
┌─────────────────────────────────────────┐
│              Domain Layer               │
│  ┌─────────────────────────────────┐    │
│  │  PortfolioRepository (Port)     │    │  ◄── Interface (Protocol)
│  └─────────────────────────────────┘    │
└───────────────┬─────────────────────────┘
                │ implements
                ▼
┌─────────────────────────────────────────┐
│         Infrastructure Layer            │
│  ┌─────────────────────────────────┐    │
│  │ PostgresPortfolioRepository     │    │  ◄── Real implementation
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ InMemoryPortfolioRepository     │    │  ◄── Test implementation
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**Key Points:**
- **Port**: Interface defined by domain (what it needs)
- **Adapter**: Implementation in infrastructure (how it works)
- **Direction**: Dependencies point inward to domain
- **Benefits**: Domain is testable without real database

---

## Why Use Protocol?

Use Python's `Protocol` (from `typing`) instead of Abstract Base Classes (ABC):

**Advantages of Protocol:**
1. **Structural Typing**: No inheritance required - duck typing with type safety
2. **Flexibility**: Can work with third-party classes
3. **Simplicity**: Clean interfaces without inheritance complexity
4. **Pythonic**: Matches Python's duck typing philosophy

**Implementation:**
- Define repository interfaces using `Protocol` in domain layer
- Concrete implementations don't need to inherit from the protocol
- Type checkers verify implementations match the protocol structure

---

## PortfolioRepository

### Purpose

Defines the contract for **Portfolio persistence operations**. Provides CRUD operations for Portfolio entities.

### Methods

#### get(portfolio_id: UUID) -> Portfolio | None
Retrieve a single portfolio by ID.

**Returns:**
- `Portfolio` if found
- `None` if not found (does NOT raise exception)

#### get_by_user(user_id: UUID) -> list[Portfolio]
Retrieve all portfolios owned by a user.

**Returns:**
- List of Portfolio entities (empty list if none found)

**Behavior:**
- Should exclude archived portfolios by default
- Order by created_at descending (newest first)

#### save(portfolio: Portfolio) -> None
Persist a portfolio (create or update).

**Behavior:**
- Creates new record if `portfolio.id` doesn't exist
- Updates existing record if `portfolio.id` exists
- Should be idempotent

#### delete(portfolio_id: UUID) -> None
Delete a portfolio.

**Considerations:**
- Hard delete removes from database permanently
- Consider soft delete (archive flag) instead for audit trail
- Should cascade delete associated transactions

### Implementation Notes

- All methods should be async (`async def`)
- Use Protocol from `typing` module
- Implementations handle database transactions and error handling
- Consider adding methods like `exists(portfolio_id)` if needed

---

## TransactionRepository

### Purpose

Defines the contract for **Transaction persistence operations**. Transactions are append-only (ledger pattern).

### Methods

#### get(transaction_id: UUID) -> Transaction | None
Retrieve a single transaction by ID.

**Returns:**
- `Transaction` if found
- `None` if not found

#### get_by_portfolio(portfolio_id: UUID) -> list[Transaction]
Retrieve all transactions for a portfolio.

**Returns:**
- List of Transaction entities ordered by timestamp (oldest first)
- Empty list if no transactions found

**Notes:**
- Order is critical for calculating derived state
- May want to add pagination for portfolios with many transactions

#### save(transaction: Transaction) -> None
Persist a new transaction.

**Behavior:**
- Always creates (never updates - transactions are immutable)
- Raise error if transaction.id already exists

#### get_by_portfolio_and_ticker(portfolio_id: UUID, ticker: Ticker) -> list[Transaction]
Retrieve all BUY/SELL transactions for a specific ticker in a portfolio.

**Returns:**
- List of Transaction entities (only BUY and SELL types)
- Ordered by timestamp (for FIFO calculation)

**Use Case:**
- Calculate holdings and cost basis for a specific ticker

### Implementation Notes

- Transactions are immutable - no update or delete operations
- All queries should order by timestamp for deterministic results
- Consider indexes on `portfolio_id` and `timestamp`
- No CASCADE DELETE - transactions are permanent audit log

---

## Repository Design Principles

### Single Responsibility

Each repository handles one aggregate root:
- **PortfolioRepository**: Manages Portfolio entities
- **TransactionRepository**: Manages Transaction entities

Do NOT create generic repositories that handle multiple entity types.

### Query Methods

Add query methods as needed by use cases:
- `get_by_<field>` for simple queries
- `find_<criteria>` for complex queries
- Keep queries focused on domain needs, not generic CRUD

### Error Handling

**Repository Layer:**
- Convert infrastructure exceptions to domain exceptions
- Example: `DatabaseError` → `RepositoryError`

**Return Values:**
- Return `None` for "not found" (not an error condition)
- Raise exceptions for actual errors (connection failures, constraint violations)

### Transactions

Repositories should NOT manage database transactions themselves. Instead:
- Application layer (use cases) manages transaction boundaries
- Use Unit of Work pattern if needed
- Repositories operate within existing transactions

---

## Testing with Repositories

### In-Memory Implementation

Create `InMemoryPortfolioRepository` and `InMemoryTransactionRepository` for tests:

**Characteristics:**
- Use dictionaries for storage
- Implement same Protocol interface
- No database required
- Fast and deterministic

**Example Structure:**
```
InMemoryPortfolioRepository:
  - _storage: dict[UUID, Portfolio]
  - Methods implement same protocol
  - Can be used in tests instead of real repository
```

### Testing Strategy

**Unit Tests (Domain Layer):**
- Use in-memory repositories
- Test domain logic without database

**Integration Tests (Repository Layer):**
- Test real repository implementations
- Verify database operations work correctly
- Use test database or transactions that roll back

---

## Future Enhancements

Consider adding these repository patterns as needed:

### Specification Pattern
For complex queries:
- Define query specifications as objects
- `find(spec: Specification) -> list[Entity]`

### Pagination
For large result sets:
- `get_by_user(user_id, limit: int, offset: int)`
- Or cursor-based pagination

### Bulk Operations
For performance:
- `save_many(portfolios: list[Portfolio])`
- `save_transactions_batch(transactions: list[Transaction])`

---

## References

- [Entities](entities.md) - Domain entities persisted by repositories
- [Value Objects](value-objects.md) - Composed within entities
- [Services](services.md) - Use repositories for persistence
