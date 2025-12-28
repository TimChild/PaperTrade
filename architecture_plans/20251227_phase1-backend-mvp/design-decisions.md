# Phase 1 Backend MVP - Design Decisions

## Overview

This document records the key architectural and design decisions made for Phase 1 Backend MVP. Each decision includes the context, alternatives considered, the decision made, and the consequences.

## ADR Format

Each decision follows the Architecture Decision Record (ADR) format:
- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: What issue prompted this decision?
- **Decision**: What change are we making?
- **Consequences**: What becomes easier or harder?

---

## ADR-001: Immutable Transaction Ledger Pattern

### Status
**Accepted**

### Context

We need to track all portfolio state changes (deposits, withdrawals, trades). There are several approaches:

**Option 1: Direct State Storage**
- Store current cash balance as a field in portfolio table
- Store current holdings as records in holdings table
- Update these on each transaction

**Option 2: Immutable Ledger (Event Sourcing Lite)**
- Store all state changes as immutable transaction records
- Derive current state by aggregating transaction history
- Never update or delete transactions

**Option 3: Hybrid Approach**
- Store both transactions AND current state
- Synchronize them on each change
- Use transactions for audit, current state for queries

### Decision

We chose **Option 2: Immutable Transaction Ledger**.

All portfolio state changes are recorded as immutable Transaction entities. Current cash balance and holdings are **derived** by aggregating the transaction log. Transactions are **append-only** - never updated or deleted.

### Rationale

1. **Complete Audit Trail**: Every state change is automatically recorded with timestamp
2. **Point-in-Time Queries**: Naturally supports "what was my balance on Jan 1?" (critical for Phase 3 backtesting)
3. **No Lost Data**: Impossible to lose transaction history
4. **No Update Anomalies**: Can't have balance and transactions out of sync
5. **Simplified Concurrency**: Append-only reduces lock contention
6. **Debugging**: Can replay full history to understand any state
7. **Regulatory Compliance**: Financial systems often require immutable audit logs

### Consequences

#### What Becomes Easier
- ✅ Audit trail (automatically maintained)
- ✅ Historical queries (replay to any point in time)
- ✅ Debugging (can inspect exact sequence of events)
- ✅ Testing (deterministic state from transaction sequence)
- ✅ Future features (event-driven architecture, CQRS)

#### What Becomes Harder
- ❌ Query performance (must aggregate transactions on each query)
- ❌ Cannot directly "fix" a transaction (must create compensating entry)
- ❌ Database size grows over time (all history retained)

#### Mitigation Strategies
- **Performance**: Add caching layer in Phase 2+ (Redis)
- **Storage**: Acceptable for MVP; archival strategy in future phases
- **Corrections**: Use WITHDRAWAL + DEPOSIT for cash corrections

---

## ADR-002: Derived Holdings (Not Persisted)

### Status
**Accepted**

### Context

Holdings represent current stock positions. We need to decide whether to:

**Option 1: Persist Holdings Table**
- Create holdings table with (portfolio_id, ticker, quantity, cost_basis)
- Update holdings on each buy/sell trade
- Query directly from holdings table

**Option 2: Derive Holdings On-Demand**
- No holdings table
- Calculate holdings by aggregating BUY/SELL transactions
- Holdings are ephemeral (exist only in memory during query)

**Option 3: Materialized View**
- Use database materialized view
- Automatically refreshed on transaction insert
- Best of both worlds?

### Decision

We chose **Option 2: Derive Holdings On-Demand**.

Holdings are calculated by processing all BUY and SELL transactions for a portfolio. No holdings table exists in the database. Holdings are constructed in memory during queries and discarded after the response.

### Rationale

1. **Single Source of Truth**: Transactions are the only persisted data
2. **No Synchronization Issues**: Can't have holdings and transactions disagree
3. **Simpler Data Model**: Fewer tables, fewer relationships
4. **Easier to Change Logic**: Cost basis calculation is just code, not database constraints
5. **Testing**: Easier to test - just verify transaction aggregation logic

### Consequences

#### What Becomes Easier
- ✅ Data consistency (one source of truth)
- ✅ Schema simplicity (fewer tables)
- ✅ Testing (pure function testing)
- ✅ Logic changes (no schema migration needed)
- ✅ Debugging (inspect transactions, recalculate holdings)

#### What Becomes Harder
- ❌ Query performance (recalculate on every request)
- ❌ Complex queries (can't JOIN on holdings)

#### Mitigation Strategies
- **Performance**: For Phase 1 MVP, acceptable (<1000 transactions)
- **Future Optimization**: Add caching in Phase 2 (cache holdings calculation result)
- **Complex Queries**: Use application-layer joins if needed

#### Why Not Materialized View?
- Adds database-specific complexity
- Refresh timing issues (immediate vs scheduled)
- Harder to test (requires real database)
- Defer optimization until proven necessary

---

## ADR-003: Clean Architecture with Dependency Inversion

### Status
**Accepted**

### Context

We need to structure the codebase to maximize testability, maintainability, and flexibility. Options:

**Option 1: Traditional Layered Architecture**
- Controllers → Services → Repositories → Database
- Each layer depends on the next
- Database schema drives domain model

**Option 2: Clean Architecture**
- Domain (center) ← Application ← Adapters ← Infrastructure
- Dependencies point inward only
- Domain defines interfaces, adapters implement them

**Option 3: Hexagonal Architecture (Ports & Adapters)**
- Similar to Clean Architecture
- Explicit "ports" (interfaces) and "adapters" (implementations)

### Decision

We chose **Clean Architecture** (which incorporates Ports & Adapters).

The system is organized in concentric layers:
- **Domain**: Pure business logic (entities, value objects, services)
- **Application**: Use cases orchestrating domain logic, defines repository ports
- **Adapters**: Implementations of ports (FastAPI, SQLModel repositories)
- **Infrastructure**: Configuration, external service wiring

Dependencies point **inward only**. The domain layer has zero external dependencies.

### Rationale

1. **Testability**: Can test domain and application layers without database or API
2. **Flexibility**: Easy to swap implementations (SQLModel → MongoDB, FastAPI → GraphQL)
3. **Independence**: Business logic doesn't depend on frameworks
4. **Clear Boundaries**: Each layer has well-defined responsibilities
5. **Future-Proof**: Easy to extract services or change infrastructure

### Consequences

#### What Becomes Easier
- ✅ Unit testing (fast, no I/O)
- ✅ Technology changes (swap FastAPI, database, etc.)
- ✅ Understanding (clear layer responsibilities)
- ✅ Parallel development (layers can be built independently)
- ✅ Onboarding (standard architecture pattern)

#### What Becomes Harder
- ❌ Initial setup (more files, more abstractions)
- ❌ Learning curve (need to understand dependency rule)
- ❌ Ceremony (more interfaces, more indirection)

#### Implementation Guidelines
- Domain layer: No imports from outer layers (enforced by tests)
- Application layer: Defines interfaces, uses dependency injection
- Adapters layer: Implements interfaces, converts between domain and external formats
- Keep domain pure and easily testable

---

## ADR-004: Repository Pattern for Persistence Abstraction

### Status
**Accepted**

### Context

We need to persist portfolios and transactions. Options:

**Option 1: Direct ORM Usage in Use Cases**
- Use cases directly use SQLModel queries
- Simple, straightforward
- Couples use cases to database

**Option 2: Repository Pattern**
- Application defines repository interfaces (ports)
- Adapters implement repositories (SQLModel, InMemory)
- Use cases depend on interfaces, not implementations

**Option 3: Active Record Pattern**
- Entities have save(), delete() methods
- Business logic and persistence mixed
- Simple for CRUD apps

### Decision

We chose **Repository Pattern**.

Application layer defines repository interfaces (PortfolioRepository, TransactionRepository). Adapters implement these interfaces with concrete classes (SQLModelPortfolioRepository, InMemoryPortfolioRepository). Use cases receive repository instances via dependency injection.

### Rationale

1. **Testability**: Use in-memory repositories for fast unit tests
2. **Flexibility**: Can swap persistence technology without changing use cases
3. **Clean Architecture**: Maintains dependency inversion
4. **Separation of Concerns**: Business logic separate from persistence logic
5. **Multiple Implementations**: InMemory for testing, SQLModel for production

### Consequences

#### What Becomes Easier
- ✅ Unit testing (use InMemory repositories)
- ✅ Integration testing (easy to setup with test database)
- ✅ Swapping databases (PostgreSQL → MySQL → MongoDB)
- ✅ Mocking (can mock entire repository)

#### What Becomes Harder
- ❌ More code (interfaces + implementations)
- ❌ Indirection (can't directly see SQL queries)

#### Repository Responsibilities
- **PortfolioRepository**: Manage portfolio persistence (CRUD)
- **TransactionRepository**: Manage transaction persistence (append-only)
- Repositories return domain entities, not database models
- Repositories handle conversion between domain and database representations

---

## ADR-005: Strong Typing with Value Objects

### Status
**Accepted**

### Context

We need to represent money, stock tickers, and share quantities. Options:

**Option 1: Primitive Types**
- Use Decimal for money amounts
- Use str for tickers
- Use Decimal for quantities
- Simple, direct

**Option 2: Value Objects**
- Create Money, Ticker, Quantity classes
- Encapsulate validation and behavior
- Type-safe

### Decision

We chose **Value Objects** (Money, Ticker, Quantity).

All financial and business concepts are represented by strongly-typed value objects, not primitives. These objects encapsulate validation rules and provide type safety.

### Rationale

1. **Type Safety**: Can't accidentally pass a ticker where money is expected
2. **Validation**: Ensures invalid values never enter the system
3. **Self-Documenting**: `Money` is more expressive than `Decimal`
4. **Encapsulation**: Business rules (e.g., currency matching) in one place
5. **Immutability**: Value objects are immutable by nature
6. **Domain-Driven Design**: Value objects are a core DDD pattern

### Consequences

#### What Becomes Easier
- ✅ Compile-time error detection (type checking)
- ✅ Validation (automatically enforced in constructor)
- ✅ Readability (clear intent)
- ✅ Consistency (same validation everywhere)
- ✅ Operations (Money.add instead of manual decimal math)

#### What Becomes Harder
- ❌ More classes to maintain
- ❌ Conversion (must create value objects from primitives)

#### Value Object Rules
- **Immutable**: Cannot modify after creation
- **Equality by Value**: Two Money(100, "USD") are equal
- **Self-Validating**: Invalid state impossible to construct
- **No Identity**: Value objects don't have IDs

### Examples
- `Money(Decimal("100.00"), "USD")` - amount with currency
- `Ticker("AAPL")` - validated stock symbol
- `Quantity(Decimal("10.5"))` - non-negative share count

---

## ADR-006: CQRS-Light Pattern (Command-Query Separation)

### Status
**Accepted**

### Context

We need to organize application layer use cases. Options:

**Option 1: Mixed Use Cases**
- All use cases in one directory
- No distinction between reads and writes

**Option 2: CQRS-Light**
- Separate Commands (writes) from Queries (reads)
- Same database for both (not full CQRS)
- Clear intent separation

**Option 3: Full CQRS**
- Separate read and write databases
- Event-driven synchronization
- Complex infrastructure

### Decision

We chose **CQRS-Light** (Command-Query Separation).

Application layer use cases are organized into:
- **Commands** (`application/commands/`): Modify state (CreatePortfolio, ExecuteTrade)
- **Queries** (`application/queries/`): Read state (GetPortfolioBalance, GetPortfolioHoldings)

Both use the same database and repository implementations.

### Rationale

1. **Clear Intent**: Immediately obvious if operation has side effects
2. **Different Patterns**: Commands validate and create entities, queries aggregate data
3. **Future-Proof**: Easy to evolve to full CQRS later if needed
4. **Optimization**: Can optimize reads and writes differently
5. **Testing**: Queries are pure (easier to test)

### Consequences

#### What Becomes Easier
- ✅ Understanding code (clear read vs write)
- ✅ Optimization (different strategies for each)
- ✅ Caching (queries can be cached, commands cannot)
- ✅ Testing (queries have no side effects)
- ✅ Evolution (can add separate read model later)

#### What Becomes Harder
- ❌ Directory structure (more directories)
- ❌ Finding code (is it a command or query?)

#### Guidelines
- **Commands**: Return minimal data (ID, success flag), modify state
- **Queries**: Return rich data, have no side effects
- **Naming**: `CreateX`, `ExecuteX` for commands; `GetX`, `CalculateX` for queries

---

## ADR-007: Mock Prices for Phase 1

### Status
**Accepted** (Temporary)

### Context

We need stock prices for trade execution and portfolio valuation. Options:

**Option 1: Real Market Data API from Day 1**
- Integrate Alpha Vantage or Finnhub immediately
- Production-ready but complex

**Option 2: Mock Prices (Provided by Client)**
- Client provides price in trade execution request
- Simple, no external dependencies
- Not realistic

**Option 3: Hardcoded Price Map**
- Application has map of ticker → fixed price
- Simple but inflexible

### Decision

We chose **Option 2: Mock Prices (Client-Provided)** for Phase 1 only.

Trade execution and portfolio value queries accept `price_per_share` and `current_prices` as input parameters. No market data API integration in Phase 1.

This is a **temporary decision** to be superseded in Phase 2.

### Rationale

1. **Simplicity**: No external API integration complexity
2. **Testing**: Easy to test with deterministic prices
3. **Focus**: Allows focus on core ledger mechanics
4. **Deferred Complexity**: Market data integration deferred to Phase 2
5. **API Rate Limits**: Avoid dealing with rate limits in MVP

### Consequences

#### What Becomes Easier (Phase 1)
- ✅ No API keys needed
- ✅ No rate limit handling
- ✅ Deterministic testing
- ✅ Faster development

#### What Becomes Harder
- ❌ Not realistic for actual trading simulation
- ❌ Client must provide prices
- ❌ Cannot calculate real portfolio value

#### Migration to Real Prices (Phase 2)
- Add `MarketDataPort` interface
- Implement `AlphaVantageAdapter`
- Change use cases to fetch prices instead of accepting them
- Frontend stops sending prices, receives real prices from backend

---

## ADR-008: PostgreSQL for Production, SQLite for Development

### Status
**Accepted**

### Context

We need to choose a database. Options:

**Option 1: PostgreSQL Everywhere**
- Production: PostgreSQL
- Development: PostgreSQL (via Docker)
- Consistent but requires Docker setup

**Option 2: SQLite for Dev, PostgreSQL for Prod**
- Production: PostgreSQL
- Development: SQLite (file-based)
- Easy setup but potential inconsistencies

**Option 3: In-Memory Only (No Persistence)**
- Development: In-memory
- Not viable for production

### Decision

We chose **PostgreSQL for production, SQLite for development**.

Production deployments use PostgreSQL. Local development defaults to SQLite (file-based). Both use the same SQLModel ORM code with minimal configuration differences.

### Rationale

1. **Developer Experience**: SQLite requires no Docker, instant startup
2. **CI/CD**: Tests run faster with SQLite
3. **Production Reliability**: PostgreSQL for ACID guarantees at scale
4. **Compatibility**: SQLModel abstracts differences
5. **Easy Setup**: New developers get running immediately

### Consequences

#### What Becomes Easier
- ✅ Local setup (no Docker required)
- ✅ Fast tests (in-memory SQLite)
- ✅ CI pipeline (simpler, faster)

#### What Becomes Harder
- ❌ Potential SQL dialect differences
- ❌ Must test with real PostgreSQL before production

#### Mitigation
- Integration tests run with PostgreSQL (via Docker or CI)
- Use common SQL subset (avoid PostgreSQL-specific features)
- Explicitly test migrations against both databases

---

## ADR-009: UUID for Entity IDs

### Status
**Accepted**

### Context

We need to choose ID types for entities. Options:

**Option 1: Auto-Increment Integers**
- 1, 2, 3, 4...
- Simple, sequential
- Database-generated

**Option 2: UUIDs**
- Globally unique identifiers
- Generated in application code
- 128-bit random values

### Decision

We chose **UUIDs (Version 4)** for all entity IDs.

Portfolios and Transactions use UUID as their primary identifier. IDs are generated in application code (not database), using Python's `uuid.uuid4()`.

### Rationale

1. **Decoupling**: Application controls ID generation, not database
2. **Testing**: Easy to create entities with known IDs in tests
3. **Distributed Systems**: Ready for future multi-instance deployments
4. **Security**: Harder to enumerate (1, 2, 3 makes it easy to guess IDs)
5. **Merging**: No ID conflicts when merging data from multiple sources
6. **Time Travel**: Can set IDs deterministically for backtesting

### Consequences

#### What Becomes Easier
- ✅ Testing (predictable IDs)
- ✅ Distributed systems (no coordination needed)
- ✅ Security (non-sequential)
- ✅ Application control (domain generates IDs)

#### What Becomes Harder
- ❌ Larger storage (128 bits vs 64 bits)
- ❌ Less human-readable
- ❌ Slightly slower indexing

#### Implementation Details
- Use `uuid.uuid4()` for random UUIDs
- Store as native UUID type in PostgreSQL
- Store as TEXT in SQLite (compatible)
- Always include in API responses for client-side caching

---

## ADR-010: Optimistic Locking for Concurrency

### Status
**Accepted**

### Context

We need to handle concurrent modifications to portfolios. Options:

**Option 1: Pessimistic Locking**
- Lock row during read (SELECT FOR UPDATE)
- Other transactions wait
- Guaranteed no conflicts but slow

**Option 2: Optimistic Locking**
- Use version column
- Detect conflicts on save
- Retry on conflict

**Option 3: No Concurrency Control**
- Last write wins
- Risk of lost updates

### Decision

We chose **Optimistic Locking** with version column.

Portfolio table includes a `version` integer column. On update, check that version hasn't changed. If changed, raise ConcurrencyError.

### Rationale

1. **Performance**: No blocking (readers don't block writers)
2. **Conflicts Rare**: In single-user portfolio app, conflicts are uncommon
3. **Failure Explicit**: Better to fail than silently lose updates
4. **Retry-Friendly**: Client can retry on conflict

### Consequences

#### What Becomes Easier
- ✅ Performance (no locks)
- ✅ Scalability (no lock contention)
- ✅ Clear errors (conflict is explicit)

#### What Becomes Harder
- ❌ Retry logic needed in adapters
- ❌ Potential for retry storms under high load

#### Implementation
- Portfolio has `version` column (starts at 1)
- On save, WHERE clause includes current version
- If no rows updated, raise ConcurrencyError
- Adapter can retry (with exponential backoff)

**Note**: Transactions don't need versioning (append-only, never updated).

---

## ADR-011: Separate DTOs for API and Domain

### Status
**Accepted**

### Context

We need to decide if API uses domain entities directly or separate DTOs. Options:

**Option 1: Expose Domain Entities**
- API returns Portfolio, Transaction entities directly
- Simple, no conversion needed
- Couples API to domain model

**Option 2: Separate DTOs**
- API has own Pydantic models
- Convert between domain and API representations
- Decoupled but more code

### Decision

We chose **Separate DTOs** (Data Transfer Objects).

FastAPI routes use Pydantic models for requests and responses. Use cases return custom result DTOs. API layer converts between DTOs and domain entities.

### Rationale

1. **Decoupling**: API can evolve independently of domain
2. **API Contracts**: Explicit, versioned API schemas
3. **Security**: Don't accidentally expose internal fields
4. **Flexibility**: Can flatten or reshape data for API needs
5. **Validation**: Pydantic handles request validation

### Consequences

#### What Becomes Easier
- ✅ API evolution (change response format without changing domain)
- ✅ Security (control what's exposed)
- ✅ Validation (Pydantic integration)
- ✅ Documentation (clear API contracts)

#### What Becomes Harder
- ❌ Conversion code (map domain to DTO)
- ❌ Duplicate-looking models

#### Naming Convention
- **Request DTOs**: `CreatePortfolioRequest`, `ExecuteTradeRequest`
- **Response DTOs**: `PortfolioResponse`, `TradeResponse`
- **Use Case DTOs**: `CreatePortfolioCommand`, `CreatePortfolioResult`

---

## ADR-012: Business Rule Validation Location

### Status
**Accepted**

### Context

We need to determine where business rule validation happens (e.g., "cannot sell shares you don't own"). Options:

**Option 1: Validation in Domain Services**
- Domain services (e.g., PortfolioCalculator) validate business rules
- Raises exceptions for invalid operations
- Domain layer enforces all business logic

**Option 2: Validation in Application Layer**
- Domain services are pure calculators (no validation)
- Application layer Use Cases validate before calling domain
- Separation of calculation from validation

**Option 3: Mixed Validation**
- Some validation in domain, some in application
- No clear separation of concerns

### Decision

We chose **Option 2: Validation in Application Layer**.

Portfolio state calculations (PortfolioCalculator) do NOT validate business rules like "cannot sell shares you don't own". Domain services are pure calculators - they derive state from inputs. Business rule enforcement belongs in Application layer Use Cases.

### Rationale

1. **Domain Services as Calculators**: Domain services compute state from transaction history without judgment
2. **Separation of Concerns**: Calculation logic separate from business rule enforcement
3. **Flexibility**: Calculators work with any transaction history (even invalid ones) for audit/analysis
4. **Clear Boundaries**: Application layer is responsible for orchestrating and validating operations
5. **Testability**: Can test calculation logic independently from validation rules

### Consequences

#### What Becomes Easier
- ✅ Testing domain services (pure functions, deterministic)
- ✅ Auditing and analysis (can calculate state from any transaction history)
- ✅ Understanding responsibilities (calculation vs validation)
- ✅ Changing business rules (no need to modify domain services)

#### What Becomes Harder
- ❌ Must remember to validate in Use Cases (not automatic)
- ❌ Potential for duplicate validation code across Use Cases

#### Implementation Guidelines

Application layer Use Cases will validate BEFORE creating transactions:

**Example Use Case Implementation:**
```python
# Application Layer (Use Case)
async def execute_sell_command(
    portfolio_id: UUID,
    ticker: Ticker,
    quantity: Quantity,
    price_per_share: Money,
    repository: PortfolioRepository,
    transaction_repository: TransactionRepository,
) -> SellResult:
    # 1. Get portfolio and transactions
    portfolio = await repository.get(portfolio_id)
    transactions = await transaction_repository.list_by_portfolio(portfolio_id)
    
    # 2. Calculate current holdings
    calculator = PortfolioCalculator()
    current_holding = calculator.calculate_holding_for_ticker(transactions, ticker)
    
    # 3. VALIDATE business rule
    if current_holding is None or current_holding.quantity < quantity:
        raise InsufficientSharesError(
            f"Cannot sell {quantity.shares} shares of {ticker.symbol}, "
            f"only {current_holding.quantity.shares if current_holding else 0} owned"
        )
    
    # 4. Create transaction (validation passed)
    transaction = Transaction.create_sell(
        portfolio_id=portfolio_id,
        ticker=ticker,
        quantity=quantity,
        price_per_share=price_per_share,
    )
    
    # 5. Persist
    await transaction_repository.save(transaction)
    return SellResult(success=True, transaction_id=transaction.id)
```

**Domain Layer Remains Pure:**
```python
# Domain Layer (Calculator) - NO validation
class PortfolioCalculator:
    def calculate_holding_for_ticker(
        self,
        transactions: list[Transaction],
        ticker: Ticker,
    ) -> Holding | None:
        """Calculate current holding for a ticker from transactions.
        
        Returns holding even if it has negative quantity (invalid state).
        Caller is responsible for validation.
        """
        # Pure calculation - no validation
        ...
```

### Related Decisions
- ADR-001: Immutable Transaction Ledger (domain services calculate from ledger)
- ADR-006: CQRS-Light (commands handle validation)

---

## Design Trade-Offs Summary

| Decision | Gain | Cost | Mitigation |
|----------|------|------|------------|
| Immutable Ledger | Audit trail, time travel | Query performance | Caching in Phase 2 |
| Derived Holdings | Data consistency | Recalculation overhead | Acceptable for MVP |
| Clean Architecture | Testability, flexibility | Initial complexity | Clear documentation |
| Repository Pattern | Test speed, flexibility | More code | Worth it for testability |
| Value Objects | Type safety | More classes | Self-documenting code |
| CQRS-Light | Clear intent | Directory overhead | Minimal cost |
| Mock Prices | Fast MVP delivery | Not production-ready | Phase 2 integration |
| UUID IDs | Distributed-ready | Larger storage | Acceptable overhead |
| Optimistic Locking | Performance | Retry logic | Conflicts rare |
| Separate DTOs | API flexibility | Conversion code | Worth decoupling |

---

## Future Decision Points

Decisions deferred to future phases:

### Phase 2 Decisions
- Which market data provider? (Alpha Vantage, Finnhub, IEX Cloud)
- Caching strategy? (Redis, in-memory, database materialized views)
- WebSocket for real-time updates? (Yes/No, which library)

### Phase 3 Decisions
- Historical data storage? (TimescaleDB, separate time-series DB)
- Backtest result persistence? (Own table, separate service)
- Batch vs streaming for historical replay?

### Phase 4 Decisions
- Fee strategy pluggability? (Strategy pattern, configuration-driven)
- Slippage modeling approach? (Simple percentage, order book simulation)

### Phase 5 Decisions
- Rule engine architecture? (Drools, custom DSL, Python eval)
- Strategy serialization format? (JSON, YAML, Python code)

---

## Deviations from Standards

None. All decisions align with:
- Modern Software Engineering principles (Dave Farley)
- Clean Architecture (Robert C. Martin)
- Domain-Driven Design (Eric Evans)
- Python best practices (PEP 8, type hints)

---

## Decision Review Process

These decisions should be reviewed:
- **After Phase 1 MVP**: Validate assumptions, measure performance
- **Before Phase 2**: Decide on caching strategy based on Phase 1 metrics
- **Before Phase 3**: Review time-series storage needs
- **Quarterly**: Review all "Accepted" decisions for deprecation

---

## References

- **project_strategy.md**: Technical philosophy and principles
- **project_plan.md**: Multi-phase roadmap
- **Modern Software Engineering** by Dave Farley
- **Clean Architecture** by Robert C. Martin
- **Domain-Driven Design** by Eric Evans
