# Task 007b: Implement Application Layer

## Objective
Implement the complete application layer for Phase 1 Backend MVP according to the architecture plan. This layer orchestrates domain logic, enforces business rules, and defines repository interfaces.

## Context
This task implements the **second layer** of Clean Architecture - the application layer that sits between the pure domain and the outer adapters/infrastructure.

**Dependencies**: Task 007 (Domain Layer) - ✅ MERGED (PR #12)

## Architecture Plan Reference
📐 **REQUIRED READING**: `architecture_plans/20251227_phase1-backend-mvp/`

Read these documents IN ORDER before starting:
1. `overview.md` - System context and architecture layers
2. `application-layer.md` - Complete specifications for application components
3. `repository-ports.md` - Repository interface contracts
4. `implementation-sequence.md` - Step-by-step guide (Phase 2)
5. `design-decisions.md` - Rationale for key decisions

## Implementation Scope

### File Structure to Create
```
backend/src/zebu/application/
├── __init__.py
├── commands/
│   ├── __init__.py
│   ├── create_portfolio.py
│   ├── deposit_cash.py
│   ├── withdraw_cash.py
│   ├── buy_stock.py
│   └── sell_stock.py
├── queries/
│   ├── __init__.py
│   ├── get_portfolio.py
│   ├── get_portfolio_balance.py
│   ├── get_portfolio_holdings.py
│   └── list_transactions.py
├── dtos/
│   ├── __init__.py
│   ├── portfolio_dto.py
│   ├── transaction_dto.py
│   └── holding_dto.py
└── ports/
    ├── __init__.py
    ├── portfolio_repository.py
    └── transaction_repository.py
```

### Test Structure to Create
```
backend/tests/unit/application/
├── __init__.py
├── commands/
│   ├── __init__.py
│   ├── test_create_portfolio.py
│   ├── test_deposit_cash.py
│   ├── test_withdraw_cash.py
│   ├── test_buy_stock.py
│   └── test_sell_stock.py
└── queries/
    ├── __init__.py
    ├── test_get_portfolio.py
    ├── test_get_portfolio_balance.py
    ├── test_get_portfolio_holdings.py
    └── test_list_transactions.py
```

## Implementation Requirements

### 1. Follow Architecture Plan Exactly
- Implement ALL specifications from `application-layer.md` and `repository-ports.md`
- Use the structured tables as your specification
- Use CQRS-Light pattern (separate Commands and Queries)

### 2. Test-Driven Development
- Write tests BEFORE implementation for each component
- Follow test cases specified in `implementation-sequence.md`
- Mock repository ports (use Protocol for type safety)
- Aim for 90%+ test coverage on application layer

### 3. Dependency Rules
- ✅ CAN import from domain layer (`zebu.domain`)
- ✅ CAN import from Python stdlib
- ✅ CAN define interfaces (Protocols) for repositories
- ❌ NO imports from adapters or infrastructure layers
- ❌ NO imports from FastAPI, SQLModel, or any framework
- ❌ NO direct database access

### 4. Business Rule Validation
- Validate BEFORE calling domain operations
- Examples:
  - `WithdrawCashCommand`: Check sufficient balance before creating transaction
  - `SellStockCommand`: Check sufficient shares before creating transaction
  - Raise appropriate exceptions: `InsufficientFundsError`, `InsufficientSharesError`

### 5. DTOs (Data Transfer Objects)
- Create immutable DTOs for crossing layer boundaries
- Convert domain entities → DTOs (outbound)
- Accept primitive types/DTOs (inbound)
- Never expose domain entities directly to outer layers

## Implementation Order

Follow this sequence from `implementation-sequence.md` Section 2:

### Step 1: Repository Ports (1 hour)
Define interfaces using `typing.Protocol`:
1. **PortfolioRepository** - CRUD for portfolios
2. **TransactionRepository** - Store and retrieve transactions

### Step 2: DTOs (1 hour)
Create immutable dataclasses for data transfer:
1. **PortfolioDTO** - Portfolio data for API responses
2. **TransactionDTO** - Transaction data for API responses
3. **HoldingDTO** - Holding data for API responses

### Step 3: Commands (3-4 hours)
Implement command handlers (write operations):
1. **CreatePortfolioCommand** - Create new portfolio
2. **DepositCashCommand** - Add cash to portfolio
3. **WithdrawCashCommand** - Remove cash (validate balance)
4. **BuyStockCommand** - Purchase shares (validate balance)
5. **SellStockCommand** - Sell shares (validate holdings)

### Step 4: Queries (2-3 hours)
Implement query handlers (read operations):
1. **GetPortfolioQuery** - Retrieve portfolio details
2. **GetPortfolioBalanceQuery** - Calculate current cash balance
3. **GetPortfolioHoldingsQuery** - Calculate current holdings
4. **ListTransactionsQuery** - List portfolio transactions

## Success Criteria

Before considering this task complete:

### Functional
- [ ] All repository ports defined with complete interfaces
- [ ] All DTOs implemented with conversion methods
- [ ] All 5 commands implemented with validation
- [ ] All 4 queries implemented with calculations
- [ ] Business rules enforced (insufficient funds, insufficient shares)

### Testing
- [ ] All unit tests pass: `pytest tests/unit/application -v`
- [ ] Test coverage > 90%: `pytest --cov=zebu.application --cov-report=term-missing`
- [ ] Mock repositories used in tests (no real database)
- [ ] All test cases from implementation-sequence.md covered

### Code Quality
- [ ] Type checking passes: `pyright src/zebu/application`
- [ ] Linting passes: `ruff check src/zebu/application`
- [ ] Formatting correct: `ruff format --check src/zebu/application`
- [ ] NO imports from adapters/infrastructure layers

### Validation
- [ ] Commands validate before executing
- [ ] Insufficient funds raises `InsufficientFundsError`
- [ ] Insufficient shares raises `InsufficientSharesError`
- [ ] DTOs correctly convert domain entities
- [ ] Repositories called with correct parameters

## Key Design Principles to Follow

From `design-decisions.md`:

1. **CQRS-Light** - Separate commands (write) from queries (read)
2. **Dependency Inversion** - Application defines ports, adapters implement
3. **Business Rules in Use Cases** - Validate before domain operations
4. **DTOs for Boundaries** - Never expose domain entities
5. **Repository Abstraction** - Work with interfaces, not implementations

## Architecture Compliance

From `application-layer.md`:

- Commands are stateless functions that orchestrate domain operations
- Queries are stateless functions that calculate derived state
- All commands/queries accept repository interfaces via dependency injection
- Business rules validated BEFORE creating domain entities
- DTOs used for all inputs/outputs crossing layer boundaries

## Notes

- This layer has NO knowledge of databases, HTTP, or frameworks
- Repositories are INTERFACES only (implementations in adapters layer)
- Use `typing.Protocol` for repository interfaces (structural typing)
- Commands/Queries can be functions or classes (prefer functions for simplicity)
- This work is **independent** of task 008 (domain refinements) - can run in parallel

## Estimated Time

**Total**: 7-9 hours

Breakdown:
- Repository Ports: 1 hour
- DTOs: 1 hour
- Commands: 3-4 hours
- Queries: 2-3 hours

## Dependencies

**Depends on**: Task 007 (Domain Layer) - ✅ MERGED
**Blocks**: Task 007c (Adapters Layer)
**Can run in parallel with**: Task 008 (Domain Layer Refinements)

## Related

- Architecture Plan: `architecture_plans/20251227_phase1-backend-mvp/application-layer.md`
- Repository Ports: `architecture_plans/20251227_phase1-backend-mvp/repository-ports.md`
- Task 007: Domain Layer (completed)
- Task 007c: Adapters Layer (next after this)
