# Phase 1 Backend MVP - Data Flow Specification

## Overview

This document illustrates the detailed data flows through the system using sequence diagrams. It shows how requests flow from the API layer through use cases to the domain and repositories, and how responses flow back.

## Key Architectural Patterns

### 1. The Ledger Pattern
All state changes are recorded as immutable transactions. Current state is **derived** by aggregating the transaction history.

### 2. Command-Query Separation
- **Commands** modify state (create transactions)
- **Queries** read state (aggregate transactions)

### 3. Dependency Inversion
- Application layer defines repository interfaces (ports)
- Adapters layer implements those interfaces
- Domain layer knows nothing about persistence

---

## Data Flow 1: Create Portfolio with Initial Deposit

This is the entry point - how a user creates a new portfolio.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as CreatePortfolio<br>UseCase
    participant Portfolio as Portfolio<br>Entity
    participant Transaction as Transaction<br>Entity
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant DB as Database

    User->>API: POST /api/v1/portfolios<br>{user_id, name, initial_deposit}

    API->>API: Validate request schema
    API->>API: Parse Money value object

    API->>UC: execute(user_id, name, initial_deposit)

    Note over UC: Validate business rules
    UC->>UC: Check initial_deposit > 0
    UC->>UC: Check name is valid

    Note over UC: Create domain entities
    UC->>Portfolio: new(id=uuid, user_id, name, created_at=now)
    Portfolio-->>UC: Portfolio instance

    UC->>Transaction: new(id=uuid,<br>type=DEPOSIT,<br>cash_change=initial_deposit)
    Transaction-->>UC: Transaction instance

    Note over UC: Persist to database
    UC->>PortRepo: save(portfolio)
    PortRepo->>DB: INSERT INTO portfolio
    DB-->>PortRepo: Success
    PortRepo-->>UC: None

    UC->>TxRepo: save(transaction)
    TxRepo->>DB: INSERT INTO transaction
    DB-->>TxRepo: Success
    TxRepo-->>UC: None

    Note over UC: Emit domain event (for audit)
    UC->>UC: emit(PortfolioCreated)

    UC-->>API: Result(portfolio_id)
    API-->>User: 201 Created<br>{portfolio_id, name, created_at}
```

### Key Points
1. **Atomic Operation**: Portfolio and initial transaction saved in same database transaction
2. **Initial Deposit Required**: Cannot create portfolio without cash
3. **UUID Generation**: IDs generated in use case, not database
4. **Timestamp Control**: Use case controls timestamp (important for Phase 3 backtesting)

---

## Data Flow 2: Execute Buy Trade

Shows validation of sufficient funds and creation of BUY transaction.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as ExecuteTrade<br>UseCase
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant Calc as Portfolio<br>Calculator
    participant DB as Database

    User->>API: POST /api/v1/portfolios/{id}/trades<br>{ticker: "AAPL", quantity: 10,<br>type: BUY, price: 150}

    API->>API: Validate request
    API->>API: Create Ticker("AAPL")
    API->>API: Create Quantity(10)
    API->>API: Create Money(150, "USD")

    API->>UC: execute(portfolio_id, ticker,<br>quantity, BUY, price)

    Note over UC: Verify portfolio exists
    UC->>PortRepo: get(portfolio_id)
    PortRepo->>DB: SELECT * FROM portfolio WHERE id=?
    DB-->>PortRepo: Portfolio record
    PortRepo-->>UC: Portfolio entity

    Note over UC: Check sufficient funds
    UC->>TxRepo: get_by_portfolio(portfolio_id)
    TxRepo->>DB: SELECT * FROM transaction<br>WHERE portfolio_id=?
    DB-->>TxRepo: Transaction records
    TxRepo-->>UC: List[Transaction]

    UC->>Calc: calculate_cash_balance(transactions)
    Calc->>Calc: sum(tx.cash_change for tx in transactions)
    Calc-->>UC: current_balance = Money(5000, "USD")

    UC->>UC: total_cost = quantity × price = 1500
    UC->>UC: Validate: current_balance >= total_cost
    Note over UC: 5000 >= 1500 ✓

    Note over UC: Create BUY transaction
    UC->>UC: new Transaction(<br>type=BUY,<br>cash_change=-1500,<br>ticker="AAPL",<br>quantity=10,<br>price=150)

    UC->>TxRepo: save(transaction)
    TxRepo->>DB: INSERT INTO transaction
    DB-->>TxRepo: Success
    TxRepo-->>UC: None

    Note over UC: Emit event
    UC->>UC: emit(TradeExecuted)

    UC-->>API: Result(transaction_id, total_cost=1500)
    API-->>User: 201 Created<br>{transaction_id, total_cost}
```

### Key Points
1. **Balance Check**: Current balance calculated from all transactions
2. **Validation Before Save**: Insufficient funds detected before database write
3. **Negative Cash Change**: BUY reduces cash (negative value)
4. **No Holding Update**: Holdings not stored - derived from transactions

---

## Data Flow 3: Execute Sell Trade

Shows validation of sufficient shares and creation of SELL transaction.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as ExecuteTrade<br>UseCase
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant Calc as Portfolio<br>Calculator
    participant DB as Database

    User->>API: POST /api/v1/portfolios/{id}/trades<br>{ticker: "AAPL", quantity: 5,<br>type: SELL, price: 160}

    API->>API: Validate request and create VOs
    API->>UC: execute(portfolio_id, ticker,<br>quantity, SELL, price)

    UC->>PortRepo: get(portfolio_id)
    PortRepo->>DB: SELECT portfolio
    DB-->>PortRepo: Portfolio record
    PortRepo-->>UC: Portfolio entity

    Note over UC: Check sufficient shares
    UC->>TxRepo: get_by_portfolio(portfolio_id)
    TxRepo->>DB: SELECT transactions
    DB-->>TxRepo: All transactions
    TxRepo-->>UC: List[Transaction]

    UC->>Calc: calculate_holdings(transactions)

    Note over Calc: Aggregate by ticker
    loop For each unique ticker
        Calc->>Calc: Process BUY transactions<br>(add shares, add cost)
        Calc->>Calc: Process SELL transactions<br>(subtract shares, reduce cost)
    end

    Calc-->>UC: List[Holding]<br>AAPL: 10 shares @ $150 avg

    UC->>UC: Find holding for AAPL
    UC->>UC: Validate: holding.quantity (10) >= quantity (5)
    Note over UC: 10 >= 5 ✓

    UC->>UC: total_proceeds = quantity × price = 800
    UC->>UC: new Transaction(<br>type=SELL,<br>cash_change=+800,<br>ticker="AAPL",<br>quantity=5,<br>price=160)

    UC->>TxRepo: save(transaction)
    TxRepo->>DB: INSERT INTO transaction
    DB-->>TxRepo: Success
    TxRepo-->>UC: None

    UC->>UC: emit(TradeExecuted)
    UC-->>API: Result(transaction_id, total_proceeds=800)
    API-->>User: 201 Created
```

### Key Points
1. **Share Check**: Current holdings calculated from transactions
2. **Cost Basis**: Holding includes average cost (for unrealized gain calculation)
3. **Positive Cash Change**: SELL increases cash (positive value)
4. **Partial Sale**: Can sell part of holding (5 of 10 shares)

---

## Data Flow 4: Withdraw Cash (With Validation)

Shows how withdrawal validates sufficient balance before proceeding.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as WithdrawCash<br>UseCase
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant Calc as Portfolio<br>Calculator
    participant DB as Database

    User->>API: POST /api/v1/portfolios/{id}/withdraw<br>{amount: 2000}

    API->>UC: execute(portfolio_id, amount)

    UC->>PortRepo: get(portfolio_id)
    PortRepo->>DB: SELECT portfolio
    DB-->>PortRepo: Portfolio record
    PortRepo-->>UC: Portfolio entity

    UC->>TxRepo: get_by_portfolio(portfolio_id)
    TxRepo->>DB: SELECT transactions
    DB-->>TxRepo: All transactions
    TxRepo-->>UC: List[Transaction]

    UC->>Calc: calculate_cash_balance(transactions)
    Calc->>Calc: sum(tx.cash_change)
    Calc-->>UC: current_balance = Money(1500, "USD")

    UC->>UC: Validate: current_balance >= amount
    Note over UC: 1500 >= 2000 ✗<br>FAIL!

    UC-->>API: raise InsufficientFundsError
    API-->>User: 400 Bad Request<br>{error: "Insufficient funds"}
```

### Key Points
1. **Validation Prevents Invalid State**: No transaction created if insufficient funds
2. **Balance Derived**: Real-time balance calculated from all transactions
3. **Clear Error**: User gets descriptive error message
4. **No Database Write**: Failed validation means no database modification

---

## Data Flow 5: Get Portfolio Balance (Query)

Shows how queries derive state from the ledger without modifying it.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as GetPortfolio<br>Balance
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant Calc as Portfolio<br>Calculator
    participant DB as Database

    User->>API: GET /api/v1/portfolios/{id}/balance

    API->>UC: execute(portfolio_id)

    UC->>PortRepo: get(portfolio_id)
    PortRepo->>DB: SELECT portfolio
    DB-->>PortRepo: Portfolio record
    PortRepo-->>UC: Portfolio entity

    UC->>TxRepo: get_by_portfolio(portfolio_id)
    TxRepo->>DB: SELECT * FROM transaction<br>WHERE portfolio_id=?<br>ORDER BY timestamp
    DB-->>TxRepo: All transactions (chronological)
    TxRepo-->>UC: List[Transaction]

    UC->>Calc: calculate_cash_balance(transactions)

    Note over Calc: Pure calculation
    Calc->>Calc: balance = Money(0, "USD")
    loop For each transaction
        Calc->>Calc: balance += tx.cash_change
    end

    Calc-->>UC: final_balance = Money(3500, "USD")

    UC-->>API: BalanceResult(portfolio_id,<br>cash_balance=3500,<br>currency="USD",<br>as_of=now())

    API-->>User: 200 OK<br>{cash_balance: 3500.00,<br>currency: "USD"}
```

### Key Points
1. **Read-Only**: No database writes
2. **Derived State**: Balance calculated from sum of cash_change
3. **Always Current**: Reflects all transactions up to query time
4. **Pure Function**: Calculator has no side effects

---

## Data Flow 6: Get Portfolio Holdings (Query)

Shows how holdings are derived by aggregating buy/sell transactions per ticker.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as GetPortfolio<br>Holdings
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant Calc as Portfolio<br>Calculator
    participant DB as Database

    User->>API: GET /api/v1/portfolios/{id}/holdings

    API->>UC: execute(portfolio_id)

    UC->>PortRepo: get(portfolio_id)
    PortRepo->>DB: SELECT portfolio
    DB-->>PortRepo: Portfolio
    PortRepo-->>UC: Portfolio entity

    UC->>TxRepo: get_by_portfolio(portfolio_id)
    TxRepo->>DB: SELECT transactions
    DB-->>TxRepo: All transactions
    TxRepo-->>UC: List[Transaction]

    UC->>Calc: calculate_holdings(transactions)

    Note over Calc: Group by ticker and aggregate
    Calc->>Calc: holdings_map = {}

    loop For each transaction
        alt transaction.type == BUY
            Calc->>Calc: holdings[ticker].quantity += tx.quantity
            Calc->>Calc: holdings[ticker].cost += tx.quantity × tx.price
        else transaction.type == SELL
            Calc->>Calc: holdings[ticker].quantity -= tx.quantity
            Calc->>Calc: holdings[ticker].cost ×= remaining/original
        end
    end

    Note over Calc: Calculate averages
    loop For each holding
        Calc->>Calc: avg_cost = cost_basis / quantity
    end

    Calc-->>UC: List[Holding]<br>AAPL: 5 shares, $750 cost, $150 avg<br>MSFT: 10 shares, $3000 cost, $300 avg

    UC-->>API: HoldingsResult(portfolio_id,<br>holdings=[...],<br>as_of=now())

    API-->>User: 200 OK<br>[{ticker: "AAPL", quantity: 5, ...},<br>{ticker: "MSFT", quantity: 10, ...}]
```

### Key Points
1. **Aggregation Logic**: Holdings calculated by replaying all trades
2. **Cost Basis Tracking**: Maintains average cost through buy/sell cycles
3. **Proportional Reduction**: SELL reduces cost basis proportionally
4. **No Storage**: Holdings never written to database

---

## Data Flow 7: Get Portfolio Value (With Current Prices)

Shows how total portfolio value is calculated from cash + holdings × prices.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as GetPortfolio<br>Value
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant Calc as Portfolio<br>Calculator
    participant DB as Database

    User->>API: GET /api/v1/portfolios/{id}/value<br>?prices=AAPL:160,MSFT:350

    Note over API: In Phase 1, prices provided in request<br>In Phase 2+, fetched from market data API
    API->>API: Parse prices:<br>{AAPL: $160, MSFT: $350}

    API->>UC: execute(portfolio_id, current_prices)

    UC->>PortRepo: get(portfolio_id)
    PortRepo->>DB: SELECT portfolio
    DB-->>PortRepo: Portfolio
    PortRepo-->>UC: Portfolio entity

    UC->>TxRepo: get_by_portfolio(portfolio_id)
    TxRepo->>DB: SELECT transactions
    DB-->>TxRepo: All transactions
    TxRepo-->>UC: List[Transaction]

    Note over UC: Calculate cash balance
    UC->>Calc: calculate_cash_balance(transactions)
    Calc-->>UC: cash_balance = $1500

    Note over UC: Calculate holdings
    UC->>Calc: calculate_holdings(transactions)
    Calc-->>UC: holdings = [<br>AAPL: 5 shares @ $150 cost,<br>MSFT: 10 shares @ $300 cost]

    Note over UC: Calculate market values
    loop For each holding
        UC->>UC: market_value = holding.quantity × current_prices[ticker]
        UC->>UC: unrealized_gain = market_value - holding.cost_basis
    end

    Note over UC: AAPL: 5 × $160 = $800 (cost: $750, gain: +$50)<br>MSFT: 10 × $350 = $3500 (cost: $3000, gain: +$500)

    UC->>UC: holdings_value = $800 + $3500 = $4300
    UC->>UC: total_value = cash + holdings = $1500 + $4300 = $5800

    UC-->>API: ValueResult(<br>cash: $1500,<br>holdings_value: $4300,<br>total_value: $5800,<br>holdings_breakdown=[...])

    API-->>User: 200 OK<br>{total_value: 5800.00,<br>unrealized_gain: 550.00}
```

### Key Points
1. **Composite Calculation**: Cash + Holdings value
2. **Current Prices Required**: Must provide price for each held ticker
3. **Unrealized Gain**: Difference between market value and cost basis
4. **Per-Holding Breakdown**: Detailed gain/loss for each position

---

## Data Flow 8: Get Transaction History (With Pagination)

Shows how transaction history is retrieved with pagination support.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as GetTransaction<br>History
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant DB as Database

    User->>API: GET /api/v1/portfolios/{id}/transactions<br>?limit=50&offset=0

    API->>UC: execute(portfolio_id, limit=50, offset=0)

    UC->>PortRepo: get(portfolio_id)
    PortRepo->>DB: SELECT portfolio
    DB-->>PortRepo: Portfolio
    PortRepo-->>UC: Portfolio entity (confirms exists)

    Note over UC: Get total count for pagination
    UC->>TxRepo: count_by_portfolio(portfolio_id)
    TxRepo->>DB: SELECT COUNT(*)<br>FROM transaction<br>WHERE portfolio_id=?
    DB-->>TxRepo: total_count = 237
    TxRepo-->>UC: 237

    Note over UC: Get paginated transactions
    UC->>TxRepo: get_by_portfolio(portfolio_id,<br>limit=50, offset=0)
    TxRepo->>DB: SELECT * FROM transaction<br>WHERE portfolio_id=?<br>ORDER BY timestamp ASC<br>LIMIT 50 OFFSET 0
    DB-->>TxRepo: First 50 transactions
    TxRepo-->>UC: List[Transaction] (50 items)

    UC-->>API: HistoryResult(<br>transactions=[...],<br>total_count=237,<br>limit=50, offset=0)

    Note over API: Client can calculate:<br>total_pages = ceil(237 / 50) = 5

    API-->>User: 200 OK<br>{transactions: [...],<br>total: 237,<br>page: 1 of 5}
```

### Key Points
1. **Pagination**: Limits memory usage for large histories
2. **Total Count**: Allows client to calculate total pages
3. **Chronological Order**: Always oldest-first (timestamp ASC)
4. **Immutable History**: Transactions never change after creation

---

## Ledger Accumulation Pattern

This diagram shows how the ledger accumulates over time and how state is derived.

```mermaid
graph TD
    subgraph "Transaction Ledger (Immutable)"
        T1[T1: DEPOSIT +$10,000]
        T2[T2: BUY AAPL -$1,500<br>10 shares @ $150]
        T3[T3: BUY MSFT -$3,000<br>10 shares @ $300]
        T4[T4: SELL AAPL +$800<br>5 shares @ $160]
        T5[T5: WITHDRAWAL -$2,000]
    end

    subgraph "Derived State (Calculated On-Demand)"
        Cash[Cash Balance<br>$10,000 - $1,500 - $3,000<br>+ $800 - $2,000<br>= $4,300]

        H1[AAPL Holding<br>Bought: 10 @ $150<br>Sold: 5 @ $160<br>Remaining: 5 shares<br>Cost: $750<br>Avg: $150]

        H2[MSFT Holding<br>Bought: 10 @ $300<br>Sold: 0<br>Remaining: 10 shares<br>Cost: $3,000<br>Avg: $300]
    end

    T1 --> Cash
    T2 --> Cash
    T2 --> H1
    T3 --> Cash
    T3 --> H2
    T4 --> Cash
    T4 --> H1
    T5 --> Cash

    style T1 fill:#90EE90
    style T2 fill:#FFB6C1
    style T3 fill:#FFB6C1
    style T4 fill:#ADD8E6
    style T5 fill:#FFA07A
    style Cash fill:#FFEB3B
    style H1 fill:#FFEB3B
    style H2 fill:#FFEB3B
```

### Legend
- **Green**: DEPOSIT (adds cash)
- **Pink**: BUY (reduces cash, adds shares)
- **Blue**: SELL (adds cash, reduces shares)
- **Orange**: WITHDRAWAL (reduces cash)
- **Yellow**: Derived state (calculated from transactions)

---

## Error Flow: Insufficient Funds

Shows what happens when a command violates business rules.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant UC as WithdrawCash
    participant PortRepo as Portfolio<br>Repository
    participant TxRepo as Transaction<br>Repository
    participant Calc as Portfolio<br>Calculator
    participant DB as Database

    User->>API: POST /withdraw {amount: 10000}
    API->>UC: execute(portfolio_id, amount=10000)

    UC->>PortRepo: get(portfolio_id)
    PortRepo->>DB: SELECT portfolio
    DB-->>PortRepo: Portfolio
    PortRepo-->>UC: Portfolio entity

    UC->>TxRepo: get_by_portfolio(portfolio_id)
    TxRepo->>DB: SELECT transactions
    DB-->>TxRepo: All transactions
    TxRepo-->>UC: List[Transaction]

    UC->>Calc: calculate_cash_balance(transactions)
    Calc-->>UC: current_balance = $4300

    UC->>UC: Validate: 4300 >= 10000?
    Note over UC: Validation FAILS!

    UC-->>API: raise InsufficientFundsError(<br>"Cannot withdraw $10,000 -<br>current balance is $4,300")

    Note over API: Convert domain exception<br>to HTTP response
    API->>API: Map to 400 Bad Request

    API-->>User: 400 Bad Request<br>{<br>"error": "InsufficientFundsError",<br>"message": "Cannot withdraw...",<br>"details": {<br>"requested": 10000,<br>"available": 4300<br>}<br>}

    Note over DB: No database writes occurred
```

### Key Points
1. **Early Validation**: Business rules checked before database write
2. **No Side Effects**: Failed validation means no state change
3. **Descriptive Errors**: User gets clear explanation
4. **Exception Translation**: Domain exceptions mapped to HTTP status codes

---

## Performance Considerations

### Query Optimization

**Problem**: Calculating holdings requires processing all transactions

**Solutions**:
1. **Phase 1**: Acceptable for MVP (< 1000 transactions)
2. **Phase 2**: Add caching layer (Redis) for frequently accessed portfolios
3. **Phase 3**: Materialized views for holdings (updated on transaction save)

### Pagination Strategy

Large transaction histories use cursor-based pagination:
- First page: `GET /transactions?limit=50`
- Next page: `GET /transactions?limit=50&offset=50`

### Index Strategy

Critical indexes for performance:
- `transaction(portfolio_id, timestamp)` - chronological queries
- `transaction(portfolio_id, transaction_type)` - filtered queries
- `portfolio(user_id)` - user's portfolios

---

## Phase 1 Data Flow Completeness

### Covered Flows
✅ Create portfolio with initial deposit
✅ Execute buy trade (with validation)
✅ Execute sell trade (with validation)
✅ Deposit cash
✅ Withdraw cash (with validation)
✅ Get portfolio balance
✅ Get portfolio holdings
✅ Get portfolio value
✅ Get transaction history
✅ Error handling (insufficient funds/shares)

### Future Flows (Phase 2+)
- Real-time price updates via WebSocket
- Market data API integration
- Cache invalidation on transaction save
- Backtest mode (query at historical timestamp)
