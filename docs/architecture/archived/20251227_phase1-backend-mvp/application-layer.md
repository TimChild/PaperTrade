# Phase 1 Backend MVP - Application Layer Specification

## Overview

The Application Layer orchestrates the domain logic to fulfill user requests. It contains **Use Cases** (also called Application Services) that implement specific business workflows. This layer defines **Repository Ports** (interfaces) that the domain needs, which are implemented by the Adapters layer.

## Dependency Rules

The Application Layer:
- ✅ MAY depend on the Domain layer
- ✅ MAY define Port interfaces (contracts for adapters)
- ✅ MAY use dependency injection to receive repository implementations
- ❌ MUST NOT depend on Adapters or Infrastructure layers
- ❌ MUST NOT import FastAPI, SQLModel, or framework code
- ❌ MUST NOT perform I/O directly (delegates to repositories)

## Architecture Pattern: CQRS-Light

We separate **Commands** (write operations) from **Queries** (read operations):

- **Commands**: Modify state, return minimal data (ID or success indicator)
- **Queries**: Read state, return comprehensive data, have no side effects

This separation provides:
- Clear intent (is this changing state?)
- Different optimization strategies (commands need transactions, queries can be cached)
- Easier testing (queries are pure, commands have clear side effects)

---

## Use Cases - Commands (Write Operations)

Commands modify portfolio state by creating transactions.

### CreatePortfolio

#### Purpose
Creates a new portfolio for a user with an initial cash deposit. This is the only way to create a portfolio - it enforces that every portfolio starts with some cash.

#### Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| user_id | UUID | ID of the user creating the portfolio | Must reference valid user |
| name | String | Display name for the portfolio | 1-100 characters, not empty/whitespace |
| initial_deposit | Money | Starting cash amount | Must be positive, typically USD |

#### Returns

| Field | Type | Description |
|-------|------|-------------|
| portfolio_id | UUID | ID of newly created portfolio |

#### Business Rules

1. **Initial Deposit Required**: Portfolio MUST be created with positive initial deposit
2. **Unique Names Per User**: User SHOULD NOT have duplicate portfolio names (warning, not error)
3. **Currency Consistency**: initial_deposit currency becomes the portfolio's base currency

#### Process Flow

1. Validate input parameters
2. Create Portfolio entity with generated UUID
3. Create initial DEPOSIT Transaction for initial_deposit
4. Save Portfolio using PortfolioRepository
5. Save Transaction using TransactionRepository
6. Emit PortfolioCreated domain event
7. Return portfolio_id

#### Error Conditions

| Error | When | HTTP Status |
|-------|------|-------------|
| InvalidMoneyError | initial_deposit is zero or negative | 400 Bad Request |
| InvalidPortfolioError | name is empty or too long | 400 Bad Request |
| UserNotFoundError | user_id doesn't exist | 404 Not Found |
| RepositoryError | Database failure | 500 Internal Server Error |

#### Repository Dependencies

- **PortfolioRepository**: save(portfolio)
- **TransactionRepository**: save(transaction)

#### Domain Service Dependencies

None

---

### DepositCash

#### Purpose
Adds cash to an existing portfolio. Records a DEPOSIT transaction.

#### Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| portfolio_id | UUID | Target portfolio | Must exist |
| amount | Money | Cash to deposit | Must be positive |
| notes | String (optional) | Reason for deposit | Max 500 characters |

#### Returns

| Field | Type | Description |
|-------|------|-------------|
| transaction_id | UUID | ID of the created transaction |

#### Business Rules

1. **Positive Amount**: Deposit amount MUST be positive
2. **Currency Match**: Deposit currency SHOULD match portfolio's base currency (warning if different)
3. **No Limit**: No maximum deposit amount in Phase 1

#### Process Flow

1. Validate input parameters
2. Retrieve Portfolio using PortfolioRepository
3. Create DEPOSIT Transaction with positive cash_change
4. Save Transaction using TransactionRepository
5. Emit CashDeposited domain event
6. Return transaction_id

#### Error Conditions

| Error | When | HTTP Status |
|-------|------|-------------|
| PortfolioNotFoundError | portfolio_id doesn't exist | 404 Not Found |
| InvalidMoneyError | amount is zero or negative | 400 Bad Request |
| RepositoryError | Database failure | 500 Internal Server Error |

#### Repository Dependencies

- **PortfolioRepository**: get(portfolio_id)
- **TransactionRepository**: save(transaction)

#### Domain Service Dependencies

None

---

### WithdrawCash

#### Purpose
Removes cash from a portfolio. Records a WITHDRAWAL transaction. Validates sufficient funds are available.

#### Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| portfolio_id | UUID | Target portfolio | Must exist |
| amount | Money | Cash to withdraw | Must be positive |
| notes | String (optional) | Reason for withdrawal | Max 500 characters |

#### Returns

| Field | Type | Description |
|-------|------|-------------|
| transaction_id | UUID | ID of the created transaction |

#### Business Rules

1. **Positive Amount**: Withdrawal amount MUST be positive
2. **Sufficient Funds**: Portfolio MUST have enough cash balance (checked before withdrawal)
3. **Currency Match**: Withdrawal currency MUST match portfolio's currency

#### Process Flow

1. Validate input parameters
2. Retrieve Portfolio using PortfolioRepository
3. Get all Transactions using TransactionRepository
4. Calculate current cash balance using PortfolioCalculator
5. Validate: current_balance >= amount (else raise InsufficientFundsError)
6. Create WITHDRAWAL Transaction with negative cash_change
7. Save Transaction using TransactionRepository
8. Emit CashWithdrawn domain event
9. Return transaction_id

#### Error Conditions

| Error | When | HTTP Status |
|-------|------|-------------|
| PortfolioNotFoundError | portfolio_id doesn't exist | 404 Not Found |
| InvalidMoneyError | amount is zero or negative | 400 Bad Request |
| InsufficientFundsError | amount > current cash balance | 400 Bad Request |
| RepositoryError | Database failure | 500 Internal Server Error |

#### Repository Dependencies

- **PortfolioRepository**: get(portfolio_id)
- **TransactionRepository**: get_by_portfolio(portfolio_id), save(transaction)

#### Domain Service Dependencies

- **PortfolioCalculator**: calculate_cash_balance(transactions)

---

### ExecuteTrade

#### Purpose
Executes a buy or sell trade for a stock. Records a BUY or SELL transaction. Validates sufficient cash (for buy) or shares (for sell).

#### Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| portfolio_id | UUID | Target portfolio | Must exist |
| ticker | Ticker | Stock symbol to trade | Valid ticker format |
| quantity | Quantity | Number of shares | Must be positive |
| trade_type | TradeType | BUY or SELL | Enum value |
| price_per_share | Money | Execution price per share | Must be positive (mock price in Phase 1) |
| notes | String (optional) | Trade notes | Max 500 characters |

#### Returns

| Field | Type | Description |
|-------|------|-------------|
| transaction_id | UUID | ID of the created transaction |
| total_cost | Money | Total transaction amount (quantity × price) |

#### Business Rules

##### BUY Rules
1. **Positive Quantity**: quantity MUST be positive
2. **Positive Price**: price_per_share MUST be positive
3. **Sufficient Cash**: Portfolio MUST have enough cash for (quantity × price_per_share)
4. **Currency Match**: price_per_share currency MUST match portfolio currency

##### SELL Rules
1. **Positive Quantity**: quantity MUST be positive
2. **Positive Price**: price_per_share MUST be positive
3. **Sufficient Shares**: Portfolio MUST hold at least quantity shares of ticker
4. **Currency Match**: price_per_share currency MUST match portfolio currency

#### Process Flow

**For BUY**:
1. Validate input parameters
2. Retrieve Portfolio using PortfolioRepository
3. Get all Transactions using TransactionRepository
4. Calculate current cash balance using PortfolioCalculator
5. Calculate total_cost = quantity × price_per_share
6. Validate: current_balance >= total_cost (else raise InsufficientFundsError)
7. Create BUY Transaction with negative cash_change = -total_cost
8. Save Transaction using TransactionRepository
9. Emit TradeExecuted domain event
10. Return transaction_id and total_cost

**For SELL**:
1. Validate input parameters
2. Retrieve Portfolio using PortfolioRepository
3. Get all Transactions using TransactionRepository
4. Calculate holdings using PortfolioCalculator
5. Find holding for ticker (else raise InsufficientSharesError)
6. Validate: holding.quantity >= quantity (else raise InsufficientSharesError)
7. Calculate total_proceeds = quantity × price_per_share
8. Create SELL Transaction with positive cash_change = +total_proceeds
9. Save Transaction using TransactionRepository
10. Emit TradeExecuted domain event
11. Return transaction_id and total_proceeds

#### Error Conditions

| Error | When | HTTP Status |
|-------|------|-------------|
| PortfolioNotFoundError | portfolio_id doesn't exist | 404 Not Found |
| InvalidTickerError | ticker format invalid | 400 Bad Request |
| InvalidQuantityError | quantity is zero or negative | 400 Bad Request |
| InvalidMoneyError | price_per_share is zero or negative | 400 Bad Request |
| InsufficientFundsError | BUY: not enough cash | 400 Bad Request |
| InsufficientSharesError | SELL: not enough shares | 400 Bad Request |
| RepositoryError | Database failure | 500 Internal Server Error |

#### Repository Dependencies

- **PortfolioRepository**: get(portfolio_id)
- **TransactionRepository**: get_by_portfolio(portfolio_id), save(transaction)

#### Domain Service Dependencies

- **PortfolioCalculator**: calculate_cash_balance(transactions), calculate_holdings(transactions)

---

## Use Cases - Queries (Read Operations)

Queries read portfolio state without modifying it. They derive current state from the transaction ledger.

### GetPortfolioBalance

#### Purpose
Retrieves the current cash balance of a portfolio by aggregating all transaction cash changes.

#### Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| portfolio_id | UUID | Target portfolio | Must exist |

#### Returns

| Field | Type | Description |
|-------|------|-------------|
| portfolio_id | UUID | Same as input |
| cash_balance | Money | Current available cash |
| currency | String | Base currency of portfolio |
| as_of | DateTime | Timestamp of calculation (now) |

#### Business Rules

1. **Real-Time Calculation**: Balance is calculated on-demand from transactions
2. **No Caching in Phase 1**: Every call recalculates (optimization in Phase 2+)

#### Process Flow

1. Validate portfolio_id
2. Retrieve Portfolio using PortfolioRepository (confirms it exists)
3. Get all Transactions using TransactionRepository
4. Calculate cash balance using PortfolioCalculator.calculate_cash_balance()
5. Return result with current timestamp

#### Error Conditions

| Error | When | HTTP Status |
|-------|------|-------------|
| PortfolioNotFoundError | portfolio_id doesn't exist | 404 Not Found |
| RepositoryError | Database failure | 500 Internal Server Error |

#### Repository Dependencies

- **PortfolioRepository**: get(portfolio_id)
- **TransactionRepository**: get_by_portfolio(portfolio_id)

#### Domain Service Dependencies

- **PortfolioCalculator**: calculate_cash_balance(transactions)

---

### GetPortfolioHoldings

#### Purpose
Retrieves current stock positions (holdings) by aggregating buy/sell transactions for each ticker.

#### Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| portfolio_id | UUID | Target portfolio | Must exist |

#### Returns

| Field | Type | Description |
|-------|------|-------------|
| portfolio_id | UUID | Same as input |
| holdings | List[HoldingDTO] | Current positions |
| as_of | DateTime | Timestamp of calculation (now) |

**HoldingDTO Structure**:

| Field | Type | Description |
|-------|------|-------------|
| ticker | String | Stock symbol |
| quantity | Decimal | Number of shares |
| cost_basis | Decimal | Total cost paid |
| average_cost_per_share | Decimal | cost_basis / quantity |
| currency | String | Currency of costs |

#### Business Rules

1. **Real-Time Calculation**: Holdings are calculated on-demand from transactions
2. **Only Active Positions**: Only returns holdings with quantity > 0
3. **Cost Basis Tracking**: Maintains FIFO-style cost basis through buy/sell cycles

#### Process Flow

1. Validate portfolio_id
2. Retrieve Portfolio using PortfolioRepository
3. Get all Transactions using TransactionRepository
4. Calculate holdings using PortfolioCalculator.calculate_holdings()
5. Filter out holdings with zero quantity
6. Convert to HoldingDTO format
7. Return result with current timestamp

#### Error Conditions

| Error | When | HTTP Status |
|-------|------|-------------|
| PortfolioNotFoundError | portfolio_id doesn't exist | 404 Not Found |
| RepositoryError | Database failure | 500 Internal Server Error |

#### Repository Dependencies

- **PortfolioRepository**: get(portfolio_id)
- **TransactionRepository**: get_by_portfolio(portfolio_id)

#### Domain Service Dependencies

- **PortfolioCalculator**: calculate_holdings(transactions)

---

### GetPortfolioValue

#### Purpose
Calculates total portfolio value (cash + holdings at current prices). In Phase 1, prices are provided as input (mock prices). Phase 2+ will fetch from market data API.

#### Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| portfolio_id | UUID | Target portfolio | Must exist |
| current_prices | Dict[Ticker, Money] | Current price for each held stock | Required in Phase 1 |

#### Returns

| Field | Type | Description |
|-------|------|-------------|
| portfolio_id | UUID | Same as input |
| cash_balance | Money | Current cash |
| holdings_value | Money | Total value of all holdings |
| total_value | Money | cash_balance + holdings_value |
| holdings_breakdown | List[HoldingValueDTO] | Per-stock breakdown |
| as_of | DateTime | Timestamp of calculation |

**HoldingValueDTO Structure**:

| Field | Type | Description |
|-------|------|-------------|
| ticker | String | Stock symbol |
| quantity | Decimal | Number of shares |
| current_price | Decimal | Price per share |
| market_value | Decimal | quantity × current_price |
| cost_basis | Decimal | Total cost paid |
| unrealized_gain_loss | Decimal | market_value - cost_basis |
| unrealized_gain_loss_percent | Decimal | (market_value - cost_basis) / cost_basis × 100 |

#### Business Rules

1. **All Holdings Must Have Prices**: If current_prices is missing a ticker, raise error
2. **Currency Consistency**: All prices must be in same currency as portfolio
3. **Real-Time Calculation**: Value calculated on-demand

#### Process Flow

1. Validate portfolio_id and current_prices
2. Retrieve Portfolio using PortfolioRepository
3. Get all Transactions using TransactionRepository
4. Calculate cash balance using PortfolioCalculator
5. Calculate holdings using PortfolioCalculator
6. For each holding:
   - Get current_price from input
   - Calculate market_value = quantity × current_price
   - Calculate unrealized_gain_loss = market_value - cost_basis
   - Calculate unrealized_gain_loss_percent
7. Sum all market_values to get holdings_value
8. Calculate total_value = cash_balance + holdings_value
9. Return comprehensive result

#### Error Conditions

| Error | When | HTTP Status |
|-------|------|-------------|
| PortfolioNotFoundError | portfolio_id doesn't exist | 404 Not Found |
| MissingPriceError | current_prices missing a held ticker | 400 Bad Request |
| InvalidMoneyError | Price has wrong currency | 400 Bad Request |
| RepositoryError | Database failure | 500 Internal Server Error |

#### Repository Dependencies

- **PortfolioRepository**: get(portfolio_id)
- **TransactionRepository**: get_by_portfolio(portfolio_id)

#### Domain Service Dependencies

- **PortfolioCalculator**: calculate_cash_balance(transactions), calculate_holdings(transactions), calculate_portfolio_value(holdings, prices)

---

### GetTransactionHistory

#### Purpose
Retrieves the complete transaction ledger for a portfolio, ordered chronologically. Supports pagination for large histories.

#### Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| portfolio_id | UUID | Target portfolio | Must exist |
| limit | Integer (optional) | Max transactions to return | Default 100, max 1000 |
| offset | Integer (optional) | Number to skip (pagination) | Default 0 |
| transaction_type | TransactionType (optional) | Filter by type | DEPOSIT, WITHDRAWAL, BUY, or SELL |

#### Returns

| Field | Type | Description |
|-------|------|-------------|
| portfolio_id | UUID | Same as input |
| transactions | List[TransactionDTO] | Transaction records |
| total_count | Integer | Total matching transactions (for pagination) |
| limit | Integer | Applied limit |
| offset | Integer | Applied offset |

**TransactionDTO Structure**:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Transaction ID |
| timestamp | DateTime | When transaction occurred |
| transaction_type | String | DEPOSIT, WITHDRAWAL, BUY, or SELL |
| cash_change | Decimal | Change in cash (positive or negative) |
| ticker | String or None | Stock symbol (for trades) |
| quantity | Decimal or None | Number of shares (for trades) |
| price_per_share | Decimal or None | Price per share (for trades) |
| notes | String or None | Optional description |
| currency | String | Currency of amounts |

#### Business Rules

1. **Chronological Order**: Transactions returned oldest-first by default
2. **Immutable History**: Transaction list is read-only
3. **Pagination**: Large histories require pagination for performance

#### Process Flow

1. Validate portfolio_id and pagination parameters
2. Retrieve Portfolio using PortfolioRepository (confirms existence)
3. Get transactions using TransactionRepository with filters and pagination
4. Get total count using TransactionRepository
5. Convert Transaction entities to TransactionDTO
6. Return paginated result

#### Error Conditions

| Error | When | HTTP Status |
|-------|------|-------------|
| PortfolioNotFoundError | portfolio_id doesn't exist | 404 Not Found |
| InvalidPaginationError | limit > 1000 or offset < 0 | 400 Bad Request |
| RepositoryError | Database failure | 500 Internal Server Error |

#### Repository Dependencies

- **PortfolioRepository**: get(portfolio_id)
- **TransactionRepository**: get_by_portfolio(portfolio_id, limit, offset, type_filter), count_by_portfolio(portfolio_id, type_filter)

#### Domain Service Dependencies

None

---

## Use Case Summary Table

| Use Case | Type | Modifies State? | Returns | Primary Repository |
|----------|------|-----------------|---------|-------------------|
| CreatePortfolio | Command | Yes (creates Portfolio + Transaction) | portfolio_id | PortfolioRepository, TransactionRepository |
| DepositCash | Command | Yes (creates Transaction) | transaction_id | TransactionRepository |
| WithdrawCash | Command | Yes (creates Transaction) | transaction_id | TransactionRepository |
| ExecuteTrade | Command | Yes (creates Transaction) | transaction_id, total_cost | TransactionRepository |
| GetPortfolioBalance | Query | No | cash_balance | TransactionRepository |
| GetPortfolioHoldings | Query | No | holdings list | TransactionRepository |
| GetPortfolioValue | Query | No | total_value, breakdown | TransactionRepository |
| GetTransactionHistory | Query | No | transaction list | TransactionRepository |

---

## Transaction Management

### Transactional Boundaries

**Commands** that create transactions require database transactions to ensure atomicity:

| Use Case | Transaction Scope |
|----------|------------------|
| CreatePortfolio | Portfolio save + Transaction save (atomic) |
| DepositCash | Transaction save (single operation) |
| WithdrawCash | Balance check + Transaction save (atomic) |
| ExecuteTrade | Balance/holdings check + Transaction save (atomic) |

**Queries** do not require transactions (read-only).

### Concurrency Strategy

Phase 1 uses **optimistic concurrency** at the database level:
- Portfolio and Transaction tables have version columns
- Concurrent modifications detected by version mismatch
- Retry logic in adapters (not in use cases)

### Idempotency

**Commands** are **not idempotent** by design - calling CreatePortfolio twice creates two portfolios.

Future phases may add:
- Idempotency keys for commands
- Deduplication based on client-provided request IDs

---

## Error Handling Strategy

### Exception Types

Use cases raise domain exceptions:

| Exception | Layer | Meaning | HTTP Status |
|-----------|-------|---------|-------------|
| InvalidMoneyError | Domain | Value object validation failed | 400 |
| InvalidTickerError | Domain | Value object validation failed | 400 |
| InvalidQuantityError | Domain | Value object validation failed | 400 |
| InsufficientFundsError | Domain | Business rule violation | 400 |
| InsufficientSharesError | Domain | Business rule violation | 400 |
| PortfolioNotFoundError | Application | Resource not found | 404 |
| UserNotFoundError | Application | Resource not found | 404 |
| RepositoryError | Infrastructure | Database/persistence failure | 500 |

### Error Response Structure

Adapters (FastAPI) convert exceptions to HTTP responses with this structure:

```
{
  "error": "InsufficientFundsError",
  "message": "Cannot withdraw $5,000.00 - current balance is $3,500.00",
  "details": {
    "requested_amount": "5000.00",
    "available_balance": "3500.00",
    "currency": "USD"
  }
}
```

---

## Testing Strategy for Use Cases

### Unit Testing (InMemory Repositories)

Each use case should have unit tests using in-memory repository implementations:

**Test Categories**:
1. **Happy Path**: Valid inputs produce expected results
2. **Validation**: Invalid inputs raise appropriate exceptions
3. **Business Rules**: Rule violations raise appropriate exceptions
4. **Edge Cases**: Empty portfolios, zero balances, exact balance matches

**Example Test Cases for ExecuteTrade (BUY)**:
- ✅ Valid buy with sufficient funds succeeds
- ✅ Buy with insufficient funds raises InsufficientFundsError
- ✅ Buy with zero quantity raises InvalidQuantityError
- ✅ Buy with negative price raises InvalidMoneyError
- ✅ Buy creates correct DEPOSIT transaction
- ✅ Multiple buys accumulate correctly
- ✅ Buy with exact balance (edge case) succeeds

### Integration Testing (Real Repositories)

Integration tests use real database (SQLite or PostgreSQL):

**Test Categories**:
1. **Persistence**: Data survives round-trip to database
2. **Transactions**: Atomic operations succeed or roll back together
3. **Concurrency**: Multiple operations don't corrupt state
4. **Performance**: Queries complete within acceptable time

---

## Validation Rules Summary

### Input Validation

| Use Case | Parameter | Validation Rule |
|----------|-----------|----------------|
| CreatePortfolio | name | Not empty, not only whitespace, 1-100 chars |
| CreatePortfolio | initial_deposit | Positive amount, valid currency |
| DepositCash | amount | Positive amount |
| WithdrawCash | amount | Positive amount, <= current balance |
| ExecuteTrade | quantity | Positive quantity |
| ExecuteTrade | price_per_share | Positive amount |
| GetPortfolioValue | current_prices | Contains price for every held ticker |

### Business Rule Validation

| Use Case | Business Rule |
|----------|--------------|
| WithdrawCash | Current balance >= withdrawal amount |
| ExecuteTrade (BUY) | Current balance >= (quantity × price) |
| ExecuteTrade (SELL) | Current holdings >= quantity |

---

## Data Transfer Objects (DTOs)

Use cases return DTOs, not domain entities, to decouple the API from the domain model.

### DTO Naming Convention
- **Input DTOs**: `{UseCaseName}Command` (e.g., `ExecuteTradeCommand`)
- **Output DTOs**: `{UseCaseName}Result` (e.g., `ExecuteTradeResult`)
- **Nested DTOs**: `{EntityName}DTO` (e.g., `HoldingDTO`, `TransactionDTO`)

### DTO Principles
- DTOs are **immutable data containers**
- DTOs do **not contain business logic**
- DTOs can be **serialized to JSON** (for API responses)
- DTOs may have **different structure** than domain entities

---

## Dependency Injection

Use cases receive their dependencies through constructor injection:

**Example Constructor Signature**:
```
ExecuteTrade(
    portfolio_repository: PortfolioRepository,
    transaction_repository: TransactionRepository,
    portfolio_calculator: PortfolioCalculator
)
```

**Benefits**:
- Testable (inject mock repositories)
- Flexible (swap implementations)
- Explicit dependencies (no hidden global state)

---

## Phase 1 Application Layer Completeness

### Implemented Use Cases
✅ CreatePortfolio (with initial deposit)
✅ DepositCash
✅ WithdrawCash
✅ ExecuteTrade (BUY and SELL)
✅ GetPortfolioBalance
✅ GetPortfolioHoldings
✅ GetPortfolioValue (with provided prices)
✅ GetTransactionHistory (with pagination)

### Future Use Cases (Phase 2+)
- UpdatePortfolio (rename)
- ArchivePortfolio (soft delete)
- GetPortfolioPerformance (time-series value)
- GetPortfolioStatistics (Sharpe ratio, volatility, etc.)
- CreateOrder (pending orders, not immediate execution)
- CancelOrder
- GetMarketQuote (fetch real-time price)
