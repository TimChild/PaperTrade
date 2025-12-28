# Phase 1 Backend MVP - Implementation Sequence Guide

## Overview

This guide provides a step-by-step implementation sequence for the backend-swe agent. The order is carefully chosen to:
1. Build from the inside-out (domain → application → adapters)
2. Enable early testing at each layer
3. Minimize dependencies between components
4. Allow incremental validation

## Implementation Principles

### 1. Test-Driven Development
- Write tests BEFORE implementation for each component
- Use in-memory repositories for fast testing
- Verify tests fail before implementing (red-green-refactor)

### 2. Domain-First Approach
- Domain layer has zero external dependencies
- Can be tested immediately without database or API
- Establishes solid foundation for outer layers

### 3. Incremental Integration
- Each layer integrates with inner layers as soon as they're complete
- Validate integration with tests before moving outward

### 4. Parallel Opportunities
Some components can be implemented in parallel (noted below)

---

## Phase 1: Domain Layer Implementation

Start with the innermost layer - pure business logic with zero external dependencies.

### Step 1.1: Create Value Objects

**Order of Implementation**:
1. Money
2. Ticker
3. Quantity

**Why This Order**: Money is the most foundational (used by others), Ticker and Quantity are independent of each other.

#### Money Value Object

**File**: `backend/src/papertrade/domain/value_objects/money.py`

**Implementation Checklist**:
- [ ] Create Money class with amount (Decimal) and currency (str) properties
- [ ] Implement constructor with validation (2 decimal places, valid currency)
- [ ] Implement arithmetic operations (add, subtract, multiply, divide)
- [ ] Implement comparison operations (__eq__, __lt__, __le__, __gt__, __ge__)
- [ ] Implement helper methods (is_positive, is_negative, is_zero, negate, absolute)
- [ ] Implement __str__ and __repr__ for readable output
- [ ] Raise InvalidMoneyError for invalid operations (different currencies)

**Test File**: `backend/tests/unit/domain/value_objects/test_money.py`

**Test Cases**:
- ✅ Valid construction with valid amount and currency
- ✅ Invalid construction raises error (NaN, Infinity, >2 decimals, invalid currency)
- ✅ Addition with same currency succeeds
- ✅ Addition with different currency raises error
- ✅ Subtraction, multiplication, division work correctly
- ✅ Equality compares both amount and currency
- ✅ Comparison operators work (>, <, etc.)
- ✅ Immutability (cannot modify after creation)

---

#### Ticker Value Object

**File**: `backend/src/papertrade/domain/value_objects/ticker.py`

**Implementation Checklist**:
- [ ] Create Ticker class with symbol (str) property
- [ ] Implement constructor with validation (1-5 uppercase letters)
- [ ] Auto-convert input to uppercase
- [ ] Implement __eq__ for equality (case-insensitive)
- [ ] Implement __hash__ for use in dicts/sets
- [ ] Implement __str__ and __repr__
- [ ] Raise InvalidTickerError for invalid formats

**Test File**: `backend/tests/unit/domain/value_objects/test_ticker.py`

**Test Cases**:
- ✅ Valid tickers (AAPL, MSFT, F, GOOGL)
- ✅ Case conversion (aapl → AAPL)
- ✅ Invalid tickers raise error (empty, too long, numbers, special chars)
- ✅ Equality works (AAPL == aapl)
- ✅ Usable as dict key (hashable)

---

#### Quantity Value Object

**File**: `backend/src/papertrade/domain/value_objects/quantity.py`

**Implementation Checklist**:
- [ ] Create Quantity class with shares (Decimal) property
- [ ] Implement constructor with validation (non-negative, max 4 decimals)
- [ ] Implement arithmetic operations (add, subtract, multiply)
- [ ] Implement comparison operations
- [ ] Implement helper methods (is_zero, is_positive)
- [ ] Implement __str__ and __repr__
- [ ] Raise InvalidQuantityError for invalid values

**Test File**: `backend/tests/unit/domain/value_objects/test_quantity.py`

**Test Cases**:
- ✅ Valid quantities (0, 10, 10.5, 10.5000)
- ✅ Invalid quantities raise error (negative, >4 decimals, NaN)
- ✅ Arithmetic operations work correctly
- ✅ Subtraction that goes negative raises error
- ✅ Zero quantity is valid

---

### Step 1.2: Create Domain Entities

**Order of Implementation**:
1. Portfolio
2. Transaction
3. Holding (derived entity)

#### Portfolio Entity

**File**: `backend/src/papertrade/domain/entities/portfolio.py`

**Implementation Checklist**:
- [ ] Create Portfolio class with id (UUID), user_id (UUID), name (str), created_at (datetime)
- [ ] Implement constructor with validation (name not empty, created_at not in future)
- [ ] Implement __eq__ based on id only
- [ ] Implement __hash__ based on id
- [ ] Implement __repr__
- [ ] Raise InvalidPortfolioError for invalid data

**Test File**: `backend/tests/unit/domain/entities/test_portfolio.py`

**Test Cases**:
- ✅ Valid construction
- ✅ Invalid name raises error (empty, whitespace-only, too long)
- ✅ Equality based on id (same id = same portfolio)
- ✅ Different portfolios with different ids are not equal
- ✅ created_at in future raises error

---

#### Transaction Entity

**File**: `backend/src/papertrade/domain/entities/transaction.py`

**Implementation Checklist**:
- [ ] Create TransactionType enum (DEPOSIT, WITHDRAWAL, BUY, SELL)
- [ ] Create Transaction class with all properties (id, portfolio_id, type, timestamp, cash_change, ticker, quantity, price_per_share, notes)
- [ ] Implement constructor with type-specific validation:
  - DEPOSIT: cash_change positive, ticker/quantity/price None
  - WITHDRAWAL: cash_change negative, ticker/quantity/price None
  - BUY: cash_change negative, ticker/quantity/price required, cash_change = -(quantity × price)
  - SELL: cash_change positive, ticker/quantity/price required, cash_change = (quantity × price)
- [ ] Make completely immutable (frozen dataclass or property-based)
- [ ] Implement __eq__ based on id
- [ ] Implement __lt__ for sorting by timestamp
- [ ] Raise InvalidTransactionError for constraint violations

**Test File**: `backend/tests/unit/domain/entities/test_transaction.py`

**Test Cases**:
- ✅ Valid DEPOSIT transaction
- ✅ Valid WITHDRAWAL transaction
- ✅ Valid BUY transaction
- ✅ Valid SELL transaction
- ✅ Invalid DEPOSIT (negative amount) raises error
- ✅ Invalid BUY (missing ticker) raises error
- ✅ Invalid BUY (cash_change doesn't match quantity × price) raises error
- ✅ Transaction is immutable (cannot modify after creation)
- ✅ Sorting by timestamp works

---

#### Holding Entity

**File**: `backend/src/papertrade/domain/entities/holding.py`

**Implementation Checklist**:
- [ ] Create Holding class with ticker (Ticker), quantity (Quantity), cost_basis (Money)
- [ ] Implement average_cost_per_share as computed property (cost_basis / quantity)
- [ ] Handle division by zero for average_cost (return None or raise)
- [ ] Implement __eq__ based on ticker only (one holding per ticker)
- [ ] Implement __repr__
- [ ] Note: This is a derived entity, never persisted directly

**Test File**: `backend/tests/unit/domain/entities/test_holding.py`

**Test Cases**:
- ✅ Valid holding construction
- ✅ Average cost calculation works
- ✅ Zero quantity holding (closed position)
- ✅ Equality based on ticker

---

### Step 1.3: Create Domain Services

**Order of Implementation**:
1. PortfolioCalculator (only one service in Phase 1)

#### PortfolioCalculator Service

**File**: `backend/src/papertrade/domain/services/portfolio_calculator.py`

**Implementation Checklist**:
- [ ] Implement calculate_cash_balance(transactions: List[Transaction]) → Money
- [ ] Implement calculate_holdings(transactions: List[Transaction]) → List[Holding]
- [ ] Implement calculate_holding_for_ticker(transactions: List[Transaction], ticker: Ticker) → Holding or None
- [ ] All functions are pure (no side effects, no I/O)
- [ ] Handle edge cases (empty transaction list, all sells)

**Test File**: `backend/tests/unit/domain/services/test_portfolio_calculator.py`

**Test Cases**:
- ✅ Empty transaction list returns zero balance
- ✅ Single DEPOSIT returns deposit amount
- ✅ DEPOSIT + WITHDRAWAL calculates correctly
- ✅ BUY transaction reduces cash
- ✅ SELL transaction increases cash
- ✅ Holdings calculated from BUY transactions
- ✅ Holdings reduced by SELL transactions
- ✅ Cost basis reduces proportionally on SELL
- ✅ Multiple buy/sell cycles for same ticker
- ✅ Complete sell closes position (quantity = 0, filtered out)
- ✅ Holdings for non-existent ticker returns None
- ✅ Property-based test: balance = sum(all cash_change)

---

### Step 1.4: Create Domain Exceptions

**File**: `backend/src/papertrade/domain/exceptions.py`

**Implementation Checklist**:
- [ ] Create DomainException base class
- [ ] Create InvalidValueObjectError and subclasses (InvalidMoneyError, InvalidTickerError, InvalidQuantityError)
- [ ] Create InvalidEntityError and subclasses (InvalidPortfolioError, InvalidTransactionError)
- [ ] Create BusinessRuleViolationError and subclasses (InsufficientFundsError, InsufficientSharesError)
- [ ] All exceptions have descriptive messages

**Test File**: `backend/tests/unit/domain/test_exceptions.py`

**Test Cases**:
- ✅ All exceptions can be raised and caught
- ✅ Exception hierarchy works (can catch DomainException to catch all)
- ✅ Error messages are descriptive

---

## Phase 2: Application Layer Implementation

Now implement use cases that orchestrate domain logic.

### Step 2.1: Define Repository Ports

**Order of Implementation**:
1. PortfolioRepository (interface)
2. TransactionRepository (interface)

#### PortfolioRepository Port

**File**: `backend/src/papertrade/application/ports/portfolio_repository.py`

**Implementation Checklist**:
- [ ] Create Protocol class defining interface
- [ ] Define methods: get, get_by_user, save, exists
- [ ] Use type hints (UUID → Portfolio | None, etc.)
- [ ] Add docstrings explaining contract

**No tests needed** - this is just an interface definition.

---

#### TransactionRepository Port

**File**: `backend/src/papertrade/application/ports/transaction_repository.py`

**Implementation Checklist**:
- [ ] Create Protocol class defining interface
- [ ] Define methods: get, get_by_portfolio, count_by_portfolio, save
- [ ] Use type hints correctly
- [ ] Add docstrings

**No tests needed** - interface only.

---

### Step 2.2: Create In-Memory Repository Implementations (For Testing)

These are concrete implementations used for fast unit testing.

**Order of Implementation**:
1. InMemoryPortfolioRepository
2. InMemoryTransactionRepository

#### InMemoryPortfolioRepository

**File**: `backend/src/papertrade/application/ports/in_memory_portfolio_repository.py`

**Implementation Checklist**:
- [ ] Implement using Dict[UUID, Portfolio]
- [ ] Implement all methods from PortfolioRepository protocol
- [ ] Save creates copy of portfolio (immutability)
- [ ] Thread-safe using locks (if needed)

**Test File**: `backend/tests/unit/application/ports/test_in_memory_portfolio_repository.py`

**Test Cases**:
- ✅ Save and get portfolio
- ✅ Get non-existent portfolio returns None
- ✅ get_by_user returns all portfolios for user
- ✅ get_by_user returns empty list for user with no portfolios
- ✅ exists returns True/False correctly
- ✅ Save updates existing portfolio (idempotent)

---

#### InMemoryTransactionRepository

**File**: `backend/src/papertrade/application/ports/in_memory_transaction_repository.py`

**Implementation Checklist**:
- [ ] Implement using Dict[UUID, Transaction]
- [ ] Implement all methods from TransactionRepository protocol
- [ ] Save raises error if transaction already exists (append-only)
- [ ] get_by_portfolio returns sorted by timestamp
- [ ] Support filtering and pagination

**Test File**: `backend/tests/unit/application/ports/test_in_memory_transaction_repository.py`

**Test Cases**:
- ✅ Save and get transaction
- ✅ Save duplicate transaction raises error
- ✅ get_by_portfolio returns chronological order
- ✅ get_by_portfolio with limit and offset (pagination)
- ✅ get_by_portfolio with type filter
- ✅ count_by_portfolio returns correct count
- ✅ count_by_portfolio with type filter

---

### Step 2.3: Implement Use Cases - Commands

**Order of Implementation**:
1. CreatePortfolio
2. DepositCash
3. WithdrawCash
4. ExecuteTrade

#### CreatePortfolio Use Case

**File**: `backend/src/papertrade/application/commands/create_portfolio.py`

**Implementation Checklist**:
- [ ] Create CreatePortfolioCommand DTO (input)
- [ ] Create CreatePortfolioResult DTO (output)
- [ ] Create CreatePortfolio use case class
- [ ] Inject PortfolioRepository and TransactionRepository
- [ ] Implement execute method:
  - Validate inputs
  - Create Portfolio entity
  - Create initial DEPOSIT Transaction
  - Save both using repositories
  - Return result with portfolio_id
- [ ] Handle errors appropriately

**Test File**: `backend/tests/unit/application/commands/test_create_portfolio.py`

**Test Cases**:
- ✅ Valid creation succeeds
- ✅ Invalid name raises error
- ✅ Zero initial deposit raises error
- ✅ Portfolio and transaction both saved
- ✅ Can retrieve created portfolio
- ✅ Initial transaction recorded correctly

---

#### DepositCash Use Case

**File**: `backend/src/papertrade/application/commands/deposit_cash.py`

**Implementation Checklist**:
- [ ] Create DepositCashCommand DTO
- [ ] Create DepositCashResult DTO
- [ ] Create DepositCash use case class
- [ ] Inject repositories
- [ ] Implement execute method
- [ ] Validate portfolio exists
- [ ] Create DEPOSIT transaction
- [ ] Save transaction

**Test File**: `backend/tests/unit/application/commands/test_deposit_cash.py`

**Test Cases**:
- ✅ Valid deposit succeeds
- ✅ Portfolio not found raises error
- ✅ Zero amount raises error
- ✅ Negative amount raises error
- ✅ Transaction saved correctly

---

#### WithdrawCash Use Case

**File**: `backend/src/papertrade/application/commands/withdraw_cash.py`

**Implementation Checklist**:
- [ ] Create WithdrawCashCommand DTO
- [ ] Create WithdrawCashResult DTO
- [ ] Create WithdrawCash use case class
- [ ] Inject repositories and PortfolioCalculator
- [ ] Implement execute method:
  - Validate portfolio exists
  - Get all transactions
  - Calculate current balance
  - Validate sufficient funds
  - Create WITHDRAWAL transaction
  - Save transaction

**Test File**: `backend/tests/unit/application/commands/test_withdraw_cash.py`

**Test Cases**:
- ✅ Valid withdrawal succeeds
- ✅ Insufficient funds raises error
- ✅ Exact balance withdrawal succeeds
- ✅ Portfolio not found raises error
- ✅ Transaction saved with negative cash_change

---

#### ExecuteTrade Use Case

**File**: `backend/src/papertrade/application/commands/execute_trade.py`

**Implementation Checklist**:
- [ ] Create ExecuteTradeCommand DTO
- [ ] Create ExecuteTradeResult DTO
- [ ] Create ExecuteTrade use case class
- [ ] Inject repositories and PortfolioCalculator
- [ ] Implement execute method for BUY:
  - Validate portfolio exists
  - Calculate current balance
  - Validate sufficient funds
  - Create BUY transaction
  - Save transaction
- [ ] Implement execute method for SELL:
  - Validate portfolio exists
  - Calculate current holdings
  - Validate sufficient shares
  - Create SELL transaction
  - Save transaction

**Test File**: `backend/tests/unit/application/commands/test_execute_trade.py`

**Test Cases**:
- ✅ Valid BUY succeeds
- ✅ BUY with insufficient funds raises error
- ✅ Valid SELL succeeds
- ✅ SELL with insufficient shares raises error
- ✅ SELL more than owned raises error
- ✅ Multiple trades accumulate correctly
- ✅ Buy then sell leaves correct balance and holdings

---

### Step 2.4: Implement Use Cases - Queries

**Order of Implementation**:
1. GetPortfolioBalance
2. GetPortfolioHoldings
3. GetPortfolioValue
4. GetTransactionHistory

#### GetPortfolioBalance Query

**File**: `backend/src/papertrade/application/queries/get_portfolio_balance.py`

**Implementation Checklist**:
- [ ] Create GetPortfolioBalanceQuery DTO
- [ ] Create GetPortfolioBalanceResult DTO
- [ ] Create GetPortfolioBalance use case class
- [ ] Inject repositories and PortfolioCalculator
- [ ] Implement execute method

**Test File**: `backend/tests/unit/application/queries/test_get_portfolio_balance.py`

**Test Cases**:
- ✅ Balance after deposit
- ✅ Balance after withdrawal
- ✅ Balance after buy trade
- ✅ Balance after sell trade
- ✅ Balance after multiple operations

---

#### GetPortfolioHoldings Query

**File**: `backend/src/papertrade/application/queries/get_portfolio_holdings.py`

**Implementation Checklist**:
- [ ] Create GetPortfolioHoldingsQuery DTO
- [ ] Create HoldingDTO (nested)
- [ ] Create GetPortfolioHoldingsResult DTO
- [ ] Create GetPortfolioHoldings use case class
- [ ] Implement execute method
- [ ] Convert Holding entities to DTOs

**Test File**: `backend/tests/unit/application/queries/test_get_portfolio_holdings.py`

**Test Cases**:
- ✅ Empty holdings after creation
- ✅ Holdings after buy
- ✅ Holdings after sell
- ✅ Cost basis calculated correctly
- ✅ Multiple holdings for different tickers

---

#### GetPortfolioValue Query

**File**: `backend/src/papertrade/application/queries/get_portfolio_value.py`

**Implementation Checklist**:
- [ ] Create GetPortfolioValueQuery DTO (with current_prices)
- [ ] Create HoldingValueDTO (nested)
- [ ] Create GetPortfolioValueResult DTO
- [ ] Create GetPortfolioValue use case class
- [ ] Implement execute method
- [ ] Calculate unrealized gains/losses

**Test File**: `backend/tests/unit/application/queries/test_get_portfolio_value.py`

**Test Cases**:
- ✅ Total value = cash + holdings value
- ✅ Unrealized gain calculated correctly
- ✅ Unrealized loss calculated correctly
- ✅ Missing price for held ticker raises error

---

#### GetTransactionHistory Query

**File**: `backend/src/papertrade/application/queries/get_transaction_history.py`

**Implementation Checklist**:
- [ ] Create GetTransactionHistoryQuery DTO
- [ ] Create TransactionDTO (nested)
- [ ] Create GetTransactionHistoryResult DTO
- [ ] Create GetTransactionHistory use case class
- [ ] Implement execute method with pagination

**Test File**: `backend/tests/unit/application/queries/test_get_transaction_history.py`

**Test Cases**:
- ✅ Returns all transactions in chronological order
- ✅ Pagination works correctly
- ✅ Filtering by type works
- ✅ Total count correct

---

## Phase 3: Adapters Layer Implementation

Now implement concrete adapters for persistence and API.

### Step 3.1: Implement SQLModel Repositories

**Order of Implementation**:
1. Database models (SQLModel)
2. SQLModelPortfolioRepository
3. SQLModelTransactionRepository

#### Database Models

**File**: `backend/src/papertrade/adapters/outbound/database/models.py`

**Implementation Checklist**:
- [ ] Create PortfolioModel with SQLModel
- [ ] Create TransactionModel with SQLModel
- [ ] Map domain entities to/from database models
- [ ] Add version column for optimistic locking
- [ ] Create indexes

**No direct tests** - tested via repository tests.

---

#### SQLModelPortfolioRepository

**File**: `backend/src/papertrade/adapters/outbound/database/portfolio_repository.py`

**Implementation Checklist**:
- [ ] Implement PortfolioRepository protocol
- [ ] Convert between Portfolio entity and PortfolioModel
- [ ] Use SQLModel session for database operations
- [ ] Implement optimistic locking

**Test File**: `backend/tests/integration/adapters/test_sqlmodel_portfolio_repository.py`

**Test Cases**:
- ✅ Same tests as InMemoryPortfolioRepository
- ✅ Plus: Data persists across sessions
- ✅ Plus: Concurrent modification detected

---

#### SQLModelTransactionRepository

**File**: `backend/src/papertrade/adapters/outbound/database/transaction_repository.py`

**Implementation Checklist**:
- [ ] Implement TransactionRepository protocol
- [ ] Convert between Transaction entity and TransactionModel
- [ ] Enforce append-only constraint
- [ ] Implement efficient pagination

**Test File**: `backend/tests/integration/adapters/test_sqlmodel_transaction_repository.py`

**Test Cases**:
- ✅ Same tests as InMemoryTransactionRepository
- ✅ Plus: Duplicate save raises error
- ✅ Plus: Large dataset pagination performance

---

### Step 3.2: Implement FastAPI Routes

**Order of Implementation**:
1. Portfolio routes
2. Transaction routes

#### Portfolio API Routes

**File**: `backend/src/papertrade/adapters/inbound/api/portfolios.py`

**Implementation Checklist**:
- [ ] POST /api/v1/portfolios - Create portfolio
- [ ] GET /api/v1/portfolios - List user's portfolios
- [ ] GET /api/v1/portfolios/{id} - Get portfolio details
- [ ] POST /api/v1/portfolios/{id}/deposit - Deposit cash
- [ ] POST /api/v1/portfolios/{id}/withdraw - Withdraw cash
- [ ] POST /api/v1/portfolios/{id}/trades - Execute trade
- [ ] GET /api/v1/portfolios/{id}/balance - Get balance
- [ ] GET /api/v1/portfolios/{id}/holdings - Get holdings
- [ ] GET /api/v1/portfolios/{id}/value - Get total value
- [ ] Map domain exceptions to HTTP status codes
- [ ] Use Pydantic models for request/response validation

**Test File**: `backend/tests/integration/api/test_portfolio_routes.py`

**Test Cases**:
- ✅ Create portfolio returns 201
- ✅ Create with invalid data returns 400
- ✅ Get non-existent portfolio returns 404
- ✅ Deposit succeeds returns 201
- ✅ Withdraw with insufficient funds returns 400
- ✅ Execute buy trade succeeds
- ✅ Get balance returns current balance
- ✅ Get holdings returns list
- ✅ Get value with prices returns total

---

#### Transaction API Routes

**File**: `backend/src/papertrade/adapters/inbound/api/transactions.py`

**Implementation Checklist**:
- [ ] GET /api/v1/portfolios/{id}/transactions - Get transaction history
- [ ] Support pagination query params
- [ ] Support filtering by type

**Test File**: `backend/tests/integration/api/test_transaction_routes.py`

**Test Cases**:
- ✅ Get history returns paginated results
- ✅ Filtering works
- ✅ Invalid pagination params return 400

---

## Phase 4: Integration and End-to-End Testing

### Step 4.1: Integration Tests

**File**: `backend/tests/integration/test_full_workflow.py`

**Test Scenarios**:
- ✅ Complete user journey: Create portfolio → Deposit → Buy → Sell → Withdraw
- ✅ Multiple portfolios for same user
- ✅ Concurrent trades don't corrupt data

---

### Step 4.2: End-to-End API Tests

**File**: `backend/tests/e2e/test_api_workflows.py`

**Test Scenarios**:
- ✅ Full portfolio lifecycle via API
- ✅ Error responses have correct format
- ✅ OpenAPI docs accessible

---

## Phase 5: Database Migrations and Setup

### Step 5.1: Alembic Migrations

**Implementation Checklist**:
- [ ] Initialize Alembic
- [ ] Create initial migration (portfolio and transaction tables)
- [ ] Add indexes
- [ ] Test migration up/down

---

### Step 5.2: Database Configuration

**File**: `backend/src/papertrade/infrastructure/database.py`

**Implementation Checklist**:
- [ ] Configure SQLModel engine
- [ ] Setup connection pooling
- [ ] Session management
- [ ] Health check endpoint

---

## Testing Strategy Summary

### Unit Tests (Fast, No I/O)
- **Domain Layer**: Test all value objects, entities, services
- **Application Layer**: Test all use cases with in-memory repositories
- **Coverage Target**: 90%+ for domain and application

### Integration Tests (Real Database)
- **Repository Implementations**: Test SQLModel repositories
- **API Routes**: Test FastAPI endpoints
- **Coverage Target**: 80%+

### End-to-End Tests (Full Stack)
- **User Journeys**: Test complete workflows
- **Coverage Target**: Critical paths only

---

## Verification Checklist

After each phase, verify:

### After Domain Layer
- [ ] All tests pass: `pytest tests/unit/domain`
- [ ] Type checking passes: `pyright src/papertrade/domain`
- [ ] Linting passes: `ruff check src/papertrade/domain`
- [ ] No external dependencies imported

### After Application Layer
- [ ] All tests pass: `pytest tests/unit`
- [ ] Use cases work with in-memory repositories
- [ ] Type checking passes
- [ ] Linting passes

### After Adapters Layer
- [ ] All tests pass: `pytest`
- [ ] Database migrations apply cleanly
- [ ] API starts without errors: `uvicorn papertrade.main:app`
- [ ] OpenAPI docs accessible: http://localhost:8000/docs

### Final Verification
- [ ] Full test suite passes: `pytest -v`
- [ ] Test coverage report: `pytest --cov=papertrade --cov-report=html`
- [ ] Type checking: `pyright`
- [ ] Linting: `ruff check .`
- [ ] Format check: `ruff format --check .`
- [ ] All integration tests pass with real database
- [ ] Manual API testing with curl/Postman

---

## Parallel Implementation Opportunities

Components that can be implemented in parallel:

**Parallel Group 1** (after domain value objects done):
- Portfolio entity
- Transaction entity
- Holding entity

**Parallel Group 2** (after domain layer done):
- Repository ports definition
- In-memory repository implementations

**Parallel Group 3** (after use cases done):
- SQLModel repositories
- FastAPI routes

---

## Estimated Implementation Time

| Phase | Components | Estimated Time |
|-------|-----------|----------------|
| Phase 1: Domain Layer | 3 VOs + 3 Entities + 1 Service | 6-8 hours |
| Phase 2: Application Layer | 2 Ports + 8 Use Cases | 10-12 hours |
| Phase 3: Adapters Layer | 2 SQL Repos + API Routes | 8-10 hours |
| Phase 4: Integration Testing | Full workflows | 4-6 hours |
| Phase 5: Database Setup | Migrations + Config | 2-3 hours |
| **Total** | | **30-39 hours** |

*Note: Times are estimates for an experienced developer with TDD approach.*

---

## Common Pitfalls to Avoid

### 1. Importing Outer Layers in Inner Layers
❌ **Don't**: Import FastAPI or SQLModel in domain layer
✅ **Do**: Keep domain pure Python

### 2. Storing Derived State
❌ **Don't**: Create a holdings table in database
✅ **Do**: Calculate holdings from transactions on query

### 3. Mutable Transactions
❌ **Don't**: Allow transaction updates
✅ **Do**: Make transactions completely immutable

### 4. Skipping Tests
❌ **Don't**: Implement without tests
✅ **Do**: Write tests first (TDD)

### 5. Premature Optimization
❌ **Don't**: Add caching or complex indexing in Phase 1
✅ **Do**: Get it working correctly first, optimize later

---

## Success Criteria Checklist

Before considering Phase 1 complete:

### Functional
- [ ] Can create portfolio with initial deposit
- [ ] Can deposit cash
- [ ] Can withdraw cash (with validation)
- [ ] Can execute buy trade (with validation)
- [ ] Can execute sell trade (with validation)
- [ ] Can query current balance
- [ ] Can query current holdings
- [ ] Can query portfolio value (with provided prices)
- [ ] Can query transaction history

### Technical
- [ ] All tests pass (unit + integration + e2e)
- [ ] Test coverage > 80%
- [ ] Type checking passes (strict mode)
- [ ] Linting passes
- [ ] No domain layer external dependencies
- [ ] Repository pattern correctly implemented
- [ ] API follows RESTful conventions
- [ ] OpenAPI docs auto-generated and accurate
- [ ] Database migrations work up and down
- [ ] Clean Architecture dependency rule maintained

### Documentation
- [ ] All public APIs have docstrings
- [ ] README explains how to run locally
- [ ] Architecture plan followed exactly
- [ ] Any deviations documented with rationale

---

## Next Steps After Phase 1

Once Phase 1 backend is complete:

1. **Frontend Integration**: Connect React frontend to backend API
2. **Phase 2 Planning**: Design market data integration architecture
3. **Performance Baseline**: Measure query performance for optimization planning
4. **User Feedback**: Deploy to staging and gather feedback
