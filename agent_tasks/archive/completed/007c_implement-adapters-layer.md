# Task 007c: Implement Adapters Layer

## Objective
Implement the complete adapters layer for Phase 1 Backend MVP according to the architecture plan. This layer provides concrete implementations for repository interfaces and exposes the API via FastAPI.

## Context
This task implements the **outermost layer** of Clean Architecture - adapters that connect our application to external systems (database, HTTP).

**Dependencies**:
- Task 007 (Domain Layer) - ✅ MERGED (PR #12)
- Task 007b (Application Layer) - ⏳ IN PROGRESS (PR #14)

## Architecture Plan Reference
📐 **REQUIRED READING**: `docs/architecture/20251227_phase1-backend-mvp/`

Read these documents IN ORDER before starting:
1. `overview.md` - System context and architecture layers
2. `implementation-sequence.md` - Step-by-step guide (Phase 3)
3. `repository-ports.md` - Repository interface contracts (from 007b)
4. `design-decisions.md` - Rationale for key decisions

## Implementation Scope

### File Structure to Create
```
backend/src/zebu/adapters/
├── __init__.py
├── inbound/
│   ├── __init__.py
│   └── api/
│       ├── __init__.py
│       ├── dependencies.py         # FastAPI dependency injection
│       ├── error_handlers.py       # Map domain exceptions to HTTP
│       ├── portfolios.py           # Portfolio API routes
│       └── transactions.py         # Transaction API routes
└── outbound/
    ├── __init__.py
    └── database/
        ├── __init__.py
        ├── models.py               # SQLModel database models
        ├── portfolio_repository.py # SQLModel portfolio repo
        └── transaction_repository.py # SQLModel transaction repo

backend/src/zebu/infrastructure/
├── __init__.py
└── database.py                     # Database session management
```

### Test Structure to Create
```
backend/tests/integration/
├── __init__.py
├── conftest.py                     # Fixtures for DB session
├── adapters/
│   ├── __init__.py
│   ├── test_sqlmodel_portfolio_repository.py
│   └── test_sqlmodel_transaction_repository.py
└── api/
    ├── __init__.py
    ├── test_portfolio_routes.py
    └── test_transaction_routes.py

backend/tests/e2e/
├── __init__.py
└── test_full_workflow.py          # Complete user journey
```

## Implementation Requirements

### 1. Follow Architecture Plan Exactly
- Implement ALL specifications from `implementation-sequence.md` Phase 3
- Repository implementations must satisfy Protocol from application layer
- API routes map to application commands/queries

### 2. Integration Testing
- Use real SQLite database for tests (in-memory)
- Test repository implementations thoroughly
- Test API routes end-to-end
- Aim for 80%+ test coverage on adapters layer

### 3. Dependency Rules
- ✅ CAN import from domain and application layers
- ✅ CAN import from SQLModel, FastAPI, Pydantic
- ✅ CAN import from Python stdlib
- ❌ NO business logic in adapters (delegate to application layer)
- ❌ NO domain logic in API routes

### 4. Error Handling
- Map domain exceptions to HTTP status codes:
  - `InvalidPortfolioError` → 400 Bad Request
  - `InvalidTransactionError` → 400 Bad Request
  - `InsufficientFundsError` → 400 Bad Request
  - `InsufficientSharesError` → 400 Bad Request
  - `PortfolioNotFoundError` → 404 Not Found
- Consistent error response format (Pydantic model)

### 5. Database Models
- Use SQLModel for ORM
- Map domain entities ↔ database models
- Add database-specific fields (created_at, updated_at, version)
- Create indexes for performance
- Version column for optimistic locking

## Implementation Order

Follow this sequence from `implementation-sequence.md` Phase 3:

### Step 1: Database Models (1-2 hours)
Create SQLModel models in `models.py`:
1. **PortfolioModel** - Maps Portfolio entity
2. **TransactionModel** - Maps Transaction entity
3. Conversion functions: `to_domain()`, `from_domain()`

### Step 2: SQLModel Repositories (3-4 hours)
Implement repository protocols:
1. **SQLModelPortfolioRepository** - CRUD operations
2. **SQLModelTransactionRepository** - Append-only operations
3. Handle optimistic locking
4. Efficient queries with indexes

### Step 3: Database Infrastructure (1 hour)
Setup database configuration:
1. **database.py** - Engine, session factory, session dependency
2. Connection pooling configuration
3. Database initialization (create tables)

### Step 4: FastAPI Routes (3-4 hours)
Implement API endpoints:

**Portfolio Routes** (`portfolios.py`):
- `POST /api/v1/portfolios` - Create portfolio
- `GET /api/v1/portfolios` - List user's portfolios
- `GET /api/v1/portfolios/{id}` - Get portfolio details
- `POST /api/v1/portfolios/{id}/deposit` - Deposit cash
- `POST /api/v1/portfolios/{id}/withdraw` - Withdraw cash
- `POST /api/v1/portfolios/{id}/trades` - Execute trade
- `GET /api/v1/portfolios/{id}/balance` - Get balance
- `GET /api/v1/portfolios/{id}/holdings` - Get holdings
- `GET /api/v1/portfolios/{id}/value` - Get total value

**Transaction Routes** (`transactions.py`):
- `GET /api/v1/portfolios/{id}/transactions` - Get transaction history

### Step 5: Error Handling (1 hour)
Implement exception handlers:
1. **error_handlers.py** - FastAPI exception handlers
2. Map domain exceptions to HTTP status codes
3. Consistent error response format

### Step 6: Dependency Injection (1 hour)
Setup FastAPI dependencies:
1. **dependencies.py** - Repository factory functions
2. Database session dependency
3. User authentication dependency (mock for now)

## Success Criteria

Before considering this task complete:

### Functional
- [ ] All database models created with proper mapping
- [ ] Both repository implementations complete
- [ ] All API routes implemented (10 endpoints)
- [ ] Error handling for all domain exceptions
- [ ] Dependency injection configured

### Testing
- [ ] Integration tests pass: `pytest tests/integration -v`
- [ ] E2E tests pass: `pytest tests/e2e -v`
- [ ] Test coverage > 80%: `pytest --cov=zebu.adapters --cov-report=term-missing`
- [ ] Real database operations tested

### Code Quality
- [ ] Type checking passes: `pyright src/zebu/adapters`
- [ ] Linting passes: `ruff check src/zebu/adapters`
- [ ] Formatting correct: `ruff format --check src/zebu/adapters`
- [ ] OpenAPI docs generated correctly

### Integration Validation
- [ ] Repository implementations satisfy Protocol from application layer
- [ ] API routes correctly call application commands/queries
- [ ] Domain exceptions properly mapped to HTTP status codes
- [ ] Database transactions work correctly
- [ ] Optimistic locking prevents concurrent modification

## Key Design Principles to Follow

From `design-decisions.md`:

1. **Hexagonal Architecture** - Adapters are interchangeable
2. **Dependency Inversion** - Adapters implement application ports
3. **Thin Adapters** - No business logic, only translation
4. **Repository Pattern** - Encapsulate data access
5. **API as Adapter** - HTTP is just another adapter

## Database Schema

### PortfolioModel
```sql
CREATE TABLE portfolios (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    INDEX idx_user_id (user_id)
);
```

### TransactionModel
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    transaction_type VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    cash_change_amount DECIMAL(15, 2) NOT NULL,
    cash_change_currency VARCHAR(3) NOT NULL,
    ticker VARCHAR(5),
    quantity_shares DECIMAL(15, 4),
    price_per_share_amount DECIMAL(15, 2),
    price_per_share_currency VARCHAR(3),
    notes TEXT,
    created_at TIMESTAMP NOT NULL,
    INDEX idx_portfolio_id (portfolio_id),
    INDEX idx_timestamp (timestamp)
);
```

## API Examples

### Create Portfolio
```http
POST /api/v1/portfolios
Content-Type: application/json

{
  "name": "My Trading Portfolio",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}

Response 201:
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Trading Portfolio",
  "created_at": "2025-12-28T20:00:00Z"
}
```

### Execute Buy Trade
```http
POST /api/v1/portfolios/{id}/trades
Content-Type: application/json

{
  "action": "BUY",
  "ticker": "AAPL",
  "quantity": "10.0000",
  "price": "150.00"
}

Response 201:
{
  "transaction_id": "789e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-12-28T20:00:00Z"
}
```

## Notes

- This layer has KNOWLEDGE of databases, HTTP, and frameworks
- Repositories IMPLEMENT interfaces defined in application layer
- API routes are THIN - they call application commands/queries
- Use SQLModel for ORM (combines Pydantic + SQLAlchemy)
- Use FastAPI dependency injection for repositories
- Integration tests require database setup/teardown

## Estimated Time

**Total**: 10-12 hours

Breakdown:
- Database Models: 1-2 hours
- SQLModel Repositories: 3-4 hours
- Database Infrastructure: 1 hour
- FastAPI Routes: 3-4 hours
- Error Handling: 1 hour
- Dependency Injection: 1 hour

## Dependencies

**Depends on**:
- Task 007 (Domain Layer) - ✅ MERGED
- Task 007b (Application Layer) - ⏳ IN PROGRESS

**Blocks**: E2E testing, frontend integration

**Cannot run in parallel with**: Task 007b (requires application ports to exist)

## Related

- Architecture Plan: `docs/architecture/20251227_phase1-backend-mvp/implementation-sequence.md`
- Task 007: Domain Layer (completed)
- Task 007b: Application Layer (in progress)
- Task 008: Domain Layer Refinements (in progress, independent)
