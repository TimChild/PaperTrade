# Phase 1 Backend MVP - Repository Ports Specification

## Overview

Repository Ports are **interfaces** defined by the Application Layer that specify what persistence operations are needed. The Adapters Layer implements these ports with concrete repository classes (SQLModel, InMemory, etc.).

This inverts the dependency: the domain/application layers define what they need, and adapters conform to those needs.

## Dependency Direction

```
Domain Layer
     ↓ (uses)
Application Layer
     ↓ (defines ports)
Port Interfaces
     ↑ (implements)
Adapters Layer
```

## Port Principles

1. **Interface Segregation**: Each port has only the methods actually needed
2. **Repository Per Aggregate**: One repository per aggregate root (Portfolio, Transaction)
3. **No Leaky Abstractions**: Ports return domain entities, not database models
4. **Technology Agnostic**: No SQL, ORM, or database-specific concepts in port definitions
5. **Testable**: Easy to create in-memory implementations for testing

---

## PortfolioRepository (Port Interface)

### Purpose
Manages persistence of Portfolio aggregate roots. Handles creating, retrieving, and updating portfolio metadata.

### Methods

#### get

| Property | Value |
|----------|-------|
| **Method Signature** | get(portfolio_id: UUID) → Portfolio or None |
| **Operation Type** | Query (read) |
| **Description** | Retrieves a single portfolio by its unique identifier |
| **Parameters** | portfolio_id: UUID - Unique identifier of the portfolio |
| **Returns** | Portfolio entity if found, None if not found |
| **Side Effects** | None (read-only) |
| **Errors** | RepositoryError if database connection fails |
| **Performance** | O(1) lookup by primary key |

**Semantics**:
- Returns fully populated Portfolio entity
- Returns None if portfolio_id doesn't exist
- Does NOT raise exception for missing portfolio (returns None)

---

#### get_by_user

| Property | Value |
|----------|-------|
| **Method Signature** | get_by_user(user_id: UUID) → List[Portfolio] |
| **Operation Type** | Query (read) |
| **Description** | Retrieves all portfolios owned by a specific user |
| **Parameters** | user_id: UUID - Unique identifier of the user |
| **Returns** | List of Portfolio entities (may be empty) |
| **Side Effects** | None (read-only) |
| **Errors** | RepositoryError if database connection fails |
| **Performance** | O(n) where n = number of portfolios for user |

**Semantics**:
- Returns empty list if user has no portfolios
- Portfolios returned in creation order (oldest first)
- Does NOT validate that user_id exists (returns empty list for invalid user)

---

#### save

| Property | Value |
|----------|-------|
| **Method Signature** | save(portfolio: Portfolio) → None |
| **Operation Type** | Command (write) |
| **Description** | Persists a portfolio (create if new, update if exists) |
| **Parameters** | portfolio: Portfolio - Entity to persist |
| **Returns** | None |
| **Side Effects** | Creates or updates database record |
| **Errors** | RepositoryError if save fails (constraint violation, connection failure) |
| **Performance** | O(1) single record write |

**Semantics**:
- **Idempotent**: Calling save multiple times with same portfolio has same effect as calling once
- **Upsert Behavior**: Creates new record if portfolio.id doesn't exist, updates if it does
- If portfolio already exists, only mutable fields are updated (name)
- Immutable fields (id, user_id, created_at) never change after creation

---

#### exists

| Property | Value |
|----------|-------|
| **Method Signature** | exists(portfolio_id: UUID) → bool |
| **Operation Type** | Query (read) |
| **Description** | Checks if a portfolio exists without loading it |
| **Parameters** | portfolio_id: UUID - Unique identifier of the portfolio |
| **Returns** | True if portfolio exists, False otherwise |
| **Side Effects** | None (read-only) |
| **Errors** | RepositoryError if database connection fails |
| **Performance** | O(1) optimized existence check (faster than get()) |

**Semantics**:
- More efficient than `get(id) is not None` for existence checks
- Used by use cases that only need to verify existence

---

### Implementation Requirements

#### Transaction Handling
- **save()** MUST participate in active transaction if one exists
- **save()** MAY auto-commit if no active transaction (implementation choice)
- Queries (get, get_by_user, exists) do NOT require transactions

#### Caching Strategy
- Implementations SHOULD cache frequently accessed portfolios
- Cache invalidation MUST occur on save()
- Cache key: portfolio_id

#### Error Handling
- Database connection failures MUST raise RepositoryError
- Constraint violations (e.g., duplicate ID) MUST raise RepositoryError with descriptive message
- Implementations SHOULD log errors before raising

#### Concurrency
- **Optimistic Locking**: Implementations SHOULD use version column to detect concurrent modifications
- On version conflict, MUST raise RepositoryError with conflict details
- Implementations MAY retry on conflict (with exponential backoff)

---

## TransactionRepository (Port Interface)

### Purpose
Manages persistence of Transaction entities. Transactions are **immutable and append-only** - no updates or deletes allowed.

### Methods

#### get

| Property | Value |
|----------|-------|
| **Method Signature** | get(transaction_id: UUID) → Transaction or None |
| **Operation Type** | Query (read) |
| **Description** | Retrieves a single transaction by its unique identifier |
| **Parameters** | transaction_id: UUID - Unique identifier of the transaction |
| **Returns** | Transaction entity if found, None if not found |
| **Side Effects** | None (read-only) |
| **Errors** | RepositoryError if database connection fails |
| **Performance** | O(1) lookup by primary key |

**Semantics**:
- Returns fully populated Transaction entity with all fields
- Returns None if transaction_id doesn't exist
- Transaction entities are immutable - returned object cannot be modified

---

#### get_by_portfolio

| Property | Value |
|----------|-------|
| **Method Signature** | get_by_portfolio(portfolio_id: UUID, limit: int = None, offset: int = 0, transaction_type: TransactionType = None) → List[Transaction] |
| **Operation Type** | Query (read) |
| **Description** | Retrieves all transactions for a portfolio, optionally filtered and paginated |
| **Parameters** | portfolio_id: UUID<br>limit: Optional max results<br>offset: Number to skip<br>transaction_type: Optional filter |
| **Returns** | List of Transaction entities (may be empty) |
| **Side Effects** | None (read-only) |
| **Errors** | RepositoryError if database connection fails |
| **Performance** | O(n) where n = matching transactions |

**Semantics**:
- Returns empty list if portfolio has no transactions
- Transactions returned in chronological order (timestamp ascending)
- If limit is None, returns ALL transactions (use with caution)
- If transaction_type is provided, only returns transactions of that type
- Pagination: skip first `offset` transactions, return at most `limit` transactions

**Pagination Example**:
- Total transactions: 150
- Request: limit=50, offset=0 → Returns transactions 1-50
- Request: limit=50, offset=50 → Returns transactions 51-100
- Request: limit=50, offset=100 → Returns transactions 101-150

---

#### count_by_portfolio

| Property | Value |
|----------|-------|
| **Method Signature** | count_by_portfolio(portfolio_id: UUID, transaction_type: TransactionType = None) → int |
| **Operation Type** | Query (read) |
| **Description** | Counts total transactions for a portfolio, optionally filtered by type |
| **Parameters** | portfolio_id: UUID<br>transaction_type: Optional filter |
| **Returns** | Total count of matching transactions |
| **Side Effects** | None (read-only) |
| **Errors** | RepositoryError if database connection fails |
| **Performance** | O(1) optimized count (database aggregate) |

**Semantics**:
- Returns 0 if portfolio has no transactions
- If transaction_type is provided, counts only that type
- Used for pagination (to calculate total pages)

---

#### save

| Property | Value |
|----------|-------|
| **Method Signature** | save(transaction: Transaction) → None |
| **Operation Type** | Command (write) |
| **Description** | Persists a new transaction (append-only, no updates) |
| **Parameters** | transaction: Transaction - Entity to persist |
| **Returns** | None |
| **Side Effects** | Creates database record |
| **Errors** | RepositoryError if save fails (duplicate ID, constraint violation, connection failure) |
| **Performance** | O(1) single record insert |

**Semantics**:
- **Append-Only**: Only creates new records, NEVER updates existing transactions
- **Idempotency**: If transaction.id already exists, MUST raise RepositoryError (not silent success)
- Transaction is immutable after save
- All fields (including timestamp) are saved exactly as provided

---

### Implementation Requirements

#### Immutability Enforcement
- Implementations MUST NOT provide update or delete operations
- Attempting to save existing transaction_id MUST raise error
- Physical deletion MAY be allowed for administrative purposes (data retention policies)

#### Transaction Handling
- **save()** MUST participate in active database transaction
- **save()** MUST NOT auto-commit (always requires explicit transaction)
- Queries do NOT require transactions

#### Indexing Strategy
Implementations SHOULD create these indexes for performance:
- Primary key: transaction_id
- Foreign key: portfolio_id (for get_by_portfolio queries)
- Composite: (portfolio_id, timestamp) for chronological ordering
- Optional: (portfolio_id, transaction_type) for filtered queries

#### Caching Strategy
- Implementations MAY cache recent transactions per portfolio
- Cache invalidation on save() for that portfolio_id
- Cache key: `transactions:{portfolio_id}` (list of transaction IDs)

#### Error Handling
- Duplicate transaction_id MUST raise RepositoryError with "Transaction already exists" message
- Foreign key violations (invalid portfolio_id) MUST raise RepositoryError
- Constraint violations MUST provide descriptive error messages

---

## Repository Error Hierarchy

### RepositoryError (Base Exception)

| Property | Value |
|----------|-------|
| **Exception Name** | RepositoryError |
| **Base Class** | Exception |
| **Purpose** | Base class for all repository-related errors |
| **Attributes** | message: str, cause: Optional[Exception] |

**When Raised**:
- Database connection failures
- Constraint violations
- Concurrency conflicts
- Generic persistence errors

**Example Message**:
```
"Failed to save portfolio: database connection lost"
"Transaction already exists: 123e4567-e89b-12d3-a456-426614174000"
```

### Specific Error Types

| Error Type | When Raised | Example |
|------------|-------------|---------|
| PortfolioNotFoundError | get() returns None and use case requires it | "Portfolio not found: {id}" |
| TransactionNotFoundError | get() returns None and use case requires it | "Transaction not found: {id}" |
| DuplicateTransactionError | save() called with existing transaction_id | "Transaction already exists: {id}" |
| ConcurrencyError | Optimistic lock conflict detected | "Portfolio was modified by another process" |

---

## Repository Implementation Variants

### InMemoryRepository (For Testing)

**Purpose**: Fast in-memory storage for unit testing

**Characteristics**:
- Uses Python dictionaries: `Dict[UUID, Entity]`
- No persistence between test runs
- No transaction support (operations are immediate)
- Thread-safe using locks
- Fast: O(1) for all operations

**Use Cases**:
- Unit testing use cases
- Integration testing without database setup
- Local development without database

---

### SQLModelRepository (For Production)

**Purpose**: PostgreSQL/SQLite persistence using SQLModel ORM

**Characteristics**:
- Uses SQLModel/SQLAlchemy for ORM
- Supports transactions via session management
- Optimistic locking with version columns
- Connection pooling for performance
- Migrations managed by Alembic

**Use Cases**:
- Production deployment
- Staging environment
- Integration tests with real database

---

## Testing Strategy for Repositories

### Contract Tests

Create abstract test suite that both InMemory and SQLModel implementations must pass:

**Test Categories**:
1. **CRUD Operations**: Create, read, update (portfolio only)
2. **Querying**: Filter, pagination, sorting
3. **Error Handling**: Constraint violations, not found cases
4. **Concurrency**: Multiple saves, optimistic locking
5. **Transactions**: Rollback on error, commit on success

**Example Tests**:
- ✅ Save new portfolio and retrieve it
- ✅ Save existing portfolio updates it (idempotent)
- ✅ get() returns None for non-existent ID
- ✅ get_by_user() returns empty list for user with no portfolios
- ✅ save() transaction with duplicate ID raises error
- ✅ get_by_portfolio() returns transactions in chronological order
- ✅ Pagination returns correct subset of transactions

### Performance Tests

For SQLModel implementation:
- Query time for 10K transactions < 100ms
- Insertion time for 1K transactions < 1s
- Concurrent saves without data corruption

---

## Port Summary Table

| Repository | Aggregate Root | Methods | Mutability |
|------------|---------------|---------|------------|
| PortfolioRepository | Portfolio | get, get_by_user, save, exists | Mutable (name only) |
| TransactionRepository | Transaction | get, get_by_portfolio, count_by_portfolio, save | Immutable (append-only) |

---

## Transaction Isolation Levels

### Recommended Isolation Levels

| Operation | Isolation Level | Rationale |
|-----------|----------------|-----------|
| Portfolio reads | READ COMMITTED | Default, prevents dirty reads |
| Portfolio writes | READ COMMITTED | Optimistic locking handles conflicts |
| Transaction reads | READ COMMITTED | Append-only reduces contention |
| Transaction writes | SERIALIZABLE | Ensures ledger integrity |

### Concurrency Scenarios

**Scenario 1: Two users deposit to same portfolio**
- Both read current balance (separate transactions)
- Both create DEPOSIT transaction (no conflict)
- Ledger maintains both deposits correctly ✅

**Scenario 2: User withdraws while balance query runs**
- Query reads transactions up to point in time
- Concurrent withdrawal doesn't affect query (snapshot isolation)
- Next query will include the withdrawal ✅

**Scenario 3: Two trades exceed balance**
- First trade: Check balance → 100, Execute → 80 remaining
- Second trade: Check balance → 100 (stale read), Execute → should fail
- Solution: Atomic balance check + trade in single transaction ✅

---

## Schema Hints (For Adapter Implementation)

While ports are technology-agnostic, here are suggested database schema elements:

### Portfolio Table

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to users, indexed |
| name | VARCHAR(100) | Not null |
| created_at | TIMESTAMP | Not null, default now() |
| version | INTEGER | For optimistic locking |

### Transaction Table

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | Primary key |
| portfolio_id | UUID | Foreign key to portfolio, indexed |
| transaction_type | VARCHAR(20) | Not null, check constraint |
| timestamp | TIMESTAMP | Not null, indexed |
| cash_change_amount | DECIMAL(15,2) | Not null |
| cash_change_currency | VARCHAR(3) | Not null |
| ticker_symbol | VARCHAR(5) | Nullable |
| quantity_shares | DECIMAL(15,4) | Nullable |
| price_amount | DECIMAL(15,2) | Nullable |
| price_currency | VARCHAR(3) | Nullable |
| notes | VARCHAR(500) | Nullable |

**Indexes**:
- Primary: `id`
- Foreign: `portfolio_id`
- Composite: `(portfolio_id, timestamp)` for chronological queries
- Composite: `(portfolio_id, transaction_type)` for filtered queries

---

## Phase 1 Repository Completeness

### Implemented Ports
✅ PortfolioRepository with CRUD operations
✅ TransactionRepository with append-only semantics

### Implemented Adapters
✅ InMemoryPortfolioRepository (testing)
✅ InMemoryTransactionRepository (testing)
✅ SQLModelPortfolioRepository (production)
✅ SQLModelTransactionRepository (production)

### Future Repositories (Phase 2+)
- UserRepository (authentication)
- MarketDataRepository (cached price data)
- BacktestRepository (backtest results)
- OrderRepository (pending orders)
