# Phase 1 Backend MVP - Domain Layer Specification

## Overview

The Domain Layer contains the core business logic and rules of PaperTrade. It has **zero dependencies** on external frameworks, databases, or infrastructure. All types are pure Python with strong type safety.

## Dependency Rules

The Domain Layer:
- ✅ MAY depend on Python standard library
- ✅ MAY use type hints from `typing` module
- ✅ MAY use `decimal.Decimal` for precise financial calculations
- ✅ MAY use `datetime` for timestamps
- ❌ MUST NOT import from Application, Adapters, or Infrastructure layers
- ❌ MUST NOT have any I/O operations (file, network, database)
- ❌ MUST NOT depend on FastAPI, SQLModel, or any framework

## Value Objects

Value objects are immutable types that represent domain concepts without identity. Two value objects with the same properties are considered equal.

### Money (Value Object)

#### Purpose
Represents a monetary amount with currency. Ensures type safety and prevents mixing of different currencies.

#### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| amount | Decimal | The monetary value | Must have maximum 2 decimal places |
| currency | String | ISO 4217 currency code | Must be valid 3-letter code, default "USD" |

#### Invariants
- Amount precision MUST NOT exceed 2 decimal places
- Currency MUST be a valid ISO 4217 code (USD, EUR, GBP, etc.)
- Amount MUST be finite (not NaN or Infinity)
- Amount MAY be negative (for representing debts or losses)

#### Operations

| Operation | Parameters | Returns | Description | Constraints |
|-----------|-----------|---------|-------------|-------------|
| add | other: Money | Money | Adds two monetary amounts | Both MUST have same currency |
| subtract | other: Money | Money | Subtracts other from self | Both MUST have same currency |
| multiply | factor: Decimal | Money | Multiplies amount by factor | Result MUST maintain 2 decimal precision |
| divide | divisor: Decimal | Money | Divides amount by divisor | Divisor MUST NOT be zero |
| negate | none | Money | Returns negative of amount | N/A |
| absolute | none | Money | Returns absolute value | N/A |
| is_positive | none | bool | Checks if amount > 0 | N/A |
| is_negative | none | bool | Checks if amount < 0 | N/A |
| is_zero | none | bool | Checks if amount == 0 | N/A |

#### Equality Semantics
Two Money objects are equal if and only if:
- Both have the same currency code (case-sensitive)
- Both have the same amount value

#### Ordering Semantics
Money objects can be compared (>, <, >=, <=) if and only if they have the same currency. Comparison raises an error for different currencies.

#### String Representation
Format: `"$1,234.56"` (currency symbol + formatted amount)

---

### Ticker (Value Object)

#### Purpose
Represents a stock ticker symbol with validation. Ensures only valid ticker formats are used throughout the system.

#### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| symbol | String | Stock ticker symbol | 1-5 uppercase letters, alphanumeric |

#### Invariants
- Symbol MUST be 1 to 5 characters long
- Symbol MUST contain only uppercase letters A-Z
- Symbol MUST NOT be empty or whitespace
- Symbol is automatically converted to uppercase on creation

#### Operations

| Operation | Parameters | Returns | Description | Constraints |
|-----------|-----------|---------|-------------|-------------|
| None | N/A | N/A | Ticker is immutable after creation | N/A |

#### Equality Semantics
Two Ticker objects are equal if their symbols match (case-insensitive comparison).

#### String Representation
Format: The symbol itself (e.g., `"AAPL"`)

#### Validation Examples

| Input | Valid? | Reason |
|-------|--------|--------|
| "AAPL" | ✅ Yes | Valid 4-letter symbol |
| "MSFT" | ✅ Yes | Valid 4-letter symbol |
| "F" | ✅ Yes | Valid 1-letter symbol |
| "GOOGL" | ✅ Yes | Valid 5-letter symbol (max length) |
| "aapl" | ✅ Yes | Converted to "AAPL" |
| "" | ❌ No | Empty string |
| "GOOGLE" | ❌ No | Too long (6 characters) |
| "APL123" | ❌ No | Contains numbers |
| "APL-B" | ❌ No | Contains special character |

---

### Quantity (Value Object)

#### Purpose
Represents a number of shares in a holding or trade. Ensures shares are always non-negative and properly validated.

#### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| shares | Decimal | Number of shares | Must be non-negative, max 4 decimal places |

#### Invariants
- Shares MUST be non-negative (>= 0)
- Shares MUST have maximum 4 decimal places (supports fractional shares)
- Shares MUST be finite (not NaN or Infinity)
- Zero shares is valid (for closed positions)

#### Operations

| Operation | Parameters | Returns | Description | Constraints |
|-----------|-----------|---------|-------------|-------------|
| add | other: Quantity | Quantity | Adds two quantities | Both MUST be non-negative |
| subtract | other: Quantity | Quantity | Subtracts other from self | Result MUST be non-negative |
| multiply | factor: Decimal | Quantity | Multiplies shares by factor | Factor MUST be non-negative |
| is_zero | none | bool | Checks if shares == 0 | N/A |
| is_positive | none | bool | Checks if shares > 0 | N/A |

#### Equality Semantics
Two Quantity objects are equal if their share values match exactly.

#### Ordering Semantics
Quantity objects can be compared using standard comparison operators (>, <, >=, <=).

#### String Representation
Format: `"123.5000 shares"` (value with 4 decimal places + " shares")

---

## Entities

Entities have identity and lifecycle. Two entities with the same ID are considered the same entity, even if their properties differ.

### Portfolio (Entity)

#### Purpose
Represents a user's investment portfolio. Serves as the aggregate root for all trading activity.

#### Identity

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| id | UUID | Unique portfolio identifier | Generated on creation, immutable |

#### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| user_id | UUID | Owner of the portfolio | Immutable after creation |
| name | String | Display name for portfolio | 1-100 characters, not empty |
| created_at | DateTime | When portfolio was created | UTC timezone, immutable |

#### Invariants
- ID MUST be unique across all portfolios
- user_id MUST reference a valid user (enforced at application layer)
- name MUST NOT be empty or only whitespace
- created_at MUST NOT be in the future
- Portfolio MUST be created with initial deposit (enforced by CreatePortfolio use case)

#### Lifecycle States
Portfolios do not have explicit state transitions in Phase 1. Future phases may add:
- Active (can trade)
- Suspended (view-only)
- Archived (historical record)

#### Relationships

| Relationship | Target | Cardinality | Description |
|--------------|--------|-------------|-------------|
| owns | Transaction | 1:N | Portfolio has many transactions |
| belongs_to | User | N:1 | Portfolio belongs to one user |

#### Operations

Portfolio entities are mostly data holders. Business logic is in Use Cases and Domain Services.

| Operation | Parameters | Returns | Description | Constraints |
|-----------|-----------|---------|-------------|-------------|
| None | N/A | N/A | Portfolio is largely immutable | Only name can be updated |

#### Equality Semantics
Two Portfolio entities are equal if they have the same ID.

---

### Transaction (Entity)

#### Purpose
Represents a single immutable entry in the portfolio ledger. Records all state changes (deposits, withdrawals, trades).

#### Identity

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| id | UUID | Unique transaction identifier | Generated on creation, immutable |

#### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| portfolio_id | UUID | Portfolio this transaction belongs to | Immutable, must reference valid portfolio |
| transaction_type | TransactionType | Type of transaction | One of: DEPOSIT, WITHDRAWAL, BUY, SELL |
| timestamp | DateTime | When transaction occurred | UTC timezone, immutable |
| cash_change | Money | Change in cash balance | Can be positive or negative |
| ticker | Ticker or None | Stock symbol for trades | Required for BUY/SELL, None for DEPOSIT/WITHDRAWAL |
| quantity | Quantity or None | Number of shares for trades | Required for BUY/SELL, None for DEPOSIT/WITHDRAWAL |
| price_per_share | Money or None | Share price at execution | Required for BUY/SELL, None for DEPOSIT/WITHDRAWAL |
| notes | String or None | Optional description | Max 500 characters, may be empty |

#### Transaction Types

| Type | Description | cash_change | ticker | quantity | price_per_share |
|------|-------------|-------------|--------|----------|-----------------|
| DEPOSIT | Add cash to portfolio | Positive | None | None | None |
| WITHDRAWAL | Remove cash from portfolio | Negative | None | None | None |
| BUY | Purchase shares | Negative | Required | Required | Required |
| SELL | Sell shares | Positive | Required | Required | Required |

#### Invariants
- Transaction is **completely immutable** after creation
- ID MUST be unique across all transactions
- portfolio_id MUST reference an existing portfolio
- timestamp MUST NOT be in the future
- For DEPOSIT: cash_change MUST be positive
- For WITHDRAWAL: cash_change MUST be negative
- For BUY: cash_change MUST be negative, ticker/quantity/price_per_share MUST be provided
- For SELL: cash_change MUST be positive, ticker/quantity/price_per_share MUST be provided
- For BUY: cash_change MUST equal -(quantity.shares × price_per_share.amount)
- For SELL: cash_change MUST equal (quantity.shares × price_per_share.amount)

#### Relationships

| Relationship | Target | Cardinality | Description |
|--------------|--------|-------------|-------------|
| belongs_to | Portfolio | N:1 | Transaction belongs to one portfolio |

#### Operations

Transactions are **completely immutable**. No operations allowed after creation.

#### Equality Semantics
Two Transaction entities are equal if they have the same ID.

#### Ordering Semantics
Transactions are ordered by timestamp (ascending = chronological order).

---

### Holding (Entity - Derived, Not Persisted)

#### Purpose
Represents the current position in a specific stock within a portfolio. **This is a derived entity** - it is calculated from transactions, not stored in the database.

#### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| ticker | Ticker | Stock symbol | Required |
| quantity | Quantity | Current number of shares held | Non-negative |
| cost_basis | Money | Total amount paid for shares | Non-negative |
| average_cost_per_share | Money | Cost basis divided by quantity | Derived, read-only |

#### Invariants
- quantity MUST be non-negative
- cost_basis MUST be non-negative
- If quantity is zero, cost_basis MUST be zero
- average_cost_per_share = cost_basis / quantity (undefined if quantity is zero)

#### Derivation Algorithm
Holding is calculated by processing all BUY and SELL transactions for a given ticker:

**High-Level Algorithm**:
1. Filter all transactions for the portfolio by ticker
2. Order transactions by timestamp (chronological)
3. For each BUY transaction:
   - Add quantity to total shares
   - Add (quantity × price) to total cost
4. For each SELL transaction:
   - Subtract quantity from total shares
   - Reduce cost basis proportionally: new_cost = cost × (remaining_shares / original_shares)
5. If final quantity > 0, create Holding; otherwise, position is closed

#### Equality Semantics
Two Holdings are equal if they have the same ticker (holdings are unique per ticker per portfolio).

---

## Domain Services

Domain Services contain business logic that doesn't naturally fit within a single entity.

### PortfolioCalculator (Domain Service)

#### Purpose
Pure functions for calculating portfolio state from transaction history. All functions are **side-effect free** - they don't modify input data or perform I/O.

#### Responsibilities

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| calculate_cash_balance | transactions: List[Transaction] | Money | Sums all cash_change values to get current cash balance |
| calculate_holdings | transactions: List[Transaction] | List[Holding] | Derives current stock positions from transaction history |
| calculate_holding_for_ticker | transactions: List[Transaction], ticker: Ticker | Holding or None | Calculates position for a specific stock |
| calculate_portfolio_value | holdings: List[Holding], prices: Dict[Ticker, Money] | Money | Calculates total value of all holdings at given prices |
| calculate_total_value | cash_balance: Money, holdings_value: Money | Money | Adds cash and holdings value |

#### Calculation Rules

**Cash Balance**:
- Start with zero
- Add cash_change from each transaction in chronological order
- Result is current cash available

**Holdings**:
- For each unique ticker in transactions:
  - Process BUY transactions: accumulate shares and cost
  - Process SELL transactions: reduce shares and cost proportionally
  - If final quantity > 0, create Holding
- Return list of all non-zero holdings

**Cost Basis Reduction (SELL)**:
When selling shares, reduce cost basis proportionally:
```
new_cost_basis = old_cost_basis × (remaining_quantity / original_quantity)
```

**Portfolio Value**:
Sum of:
- Cash balance (from calculate_cash_balance)
- Value of all holdings (sum of quantity × current_price for each holding)

---

## Domain Events

Domain events represent significant occurrences in the domain. In Phase 1, these are recorded but not actively published. Future phases will use these for event-driven architecture.

### Domain Event Structure

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| event_id | UUID | Unique event identifier | Generated on creation |
| aggregate_id | UUID | ID of the entity that raised the event | Immutable |
| event_type | String | Type of event | Immutable |
| occurred_at | DateTime | When event occurred | UTC timezone, immutable |
| data | Dict | Event-specific payload | Immutable |

### Event Types for Phase 1

| Event Type | Aggregate | Triggered When | Data Payload |
|------------|-----------|----------------|--------------|
| PortfolioCreated | Portfolio | New portfolio created | portfolio_id, user_id, name, initial_deposit |
| CashDeposited | Portfolio | Cash added to portfolio | portfolio_id, amount, transaction_id |
| CashWithdrawn | Portfolio | Cash removed from portfolio | portfolio_id, amount, transaction_id |
| TradeExecuted | Portfolio | Buy or sell trade completed | portfolio_id, ticker, quantity, price, trade_type, transaction_id |

**Note**: In Phase 1, events are logged but not actively consumed. Phase 2+ will use events for:
- Audit logging
- Real-time notifications
- Cache invalidation
- Analytics and reporting

---

## Type System Summary

### Primitive Types Used
- `UUID`: Unique identifiers (from Python `uuid` module)
- `Decimal`: Precise numeric calculations (from Python `decimal` module)
- `String`: Text values (Python `str`)
- `DateTime`: Timestamps with timezone (from Python `datetime` module, always UTC)
- `bool`: Boolean flags

### Custom Types
- `TransactionType`: Enumeration (DEPOSIT, WITHDRAWAL, BUY, SELL)
- `Money`: Value object (amount: Decimal, currency: String)
- `Ticker`: Value object (symbol: String)
- `Quantity`: Value object (shares: Decimal)

### Collection Types
- `List[T]`: Ordered sequence of items
- `Dict[K, V]`: Key-value mapping
- `Optional[T]`: Value that may be None

---

## Validation Summary

### Value Object Validation
All value objects validate their constraints in their constructor:
- **Money**: Validates currency code and decimal precision
- **Ticker**: Validates symbol format and length
- **Quantity**: Validates non-negativity and decimal precision

### Entity Validation
Entities validate their invariants on creation:
- **Portfolio**: Validates name length and non-emptiness
- **Transaction**: Validates type-specific constraints (e.g., BUY requires ticker)

### Domain Service Validation
Domain services assume valid inputs (garbage in = exception):
- Input transactions MUST be valid Transaction entities
- Invalid data raises descriptive exceptions

---

## Error Handling Strategy

### Domain Exceptions

| Exception Type | When Raised | Example |
|----------------|-------------|---------|
| InvalidMoneyError | Money construction fails | Different currencies in arithmetic |
| InvalidTickerError | Ticker validation fails | Symbol too long or contains numbers |
| InvalidQuantityError | Quantity validation fails | Negative shares |
| InvalidTransactionError | Transaction invariant violated | BUY without ticker |
| InsufficientSharesError | Cannot sell shares you don't own | Selling 100 shares when holding 50 |
| InsufficientFundsError | Cannot withdraw more cash than available | Withdrawal exceeds balance |

### Exception Hierarchy
```
DomainException (base class)
├── InvalidValueObjectError
│   ├── InvalidMoneyError
│   ├── InvalidTickerError
│   └── InvalidQuantityError
├── InvalidEntityError
│   ├── InvalidPortfolioError
│   └── InvalidTransactionError
└── BusinessRuleViolationError
    ├── InsufficientSharesError
    └── InsufficientFundsError
```

---

## Testing Strategy

### Value Object Tests
- Test valid construction
- Test invalid construction raises appropriate exception
- Test arithmetic operations
- Test equality and comparison
- Test immutability (cannot modify after creation)

### Entity Tests
- Test valid construction
- Test invalid construction raises exception
- Test invariants are maintained
- Test equality based on ID
- Test immutability where applicable

### Domain Service Tests
- Test calculation correctness with various transaction sequences
- Test edge cases (empty transaction list, zero balances)
- Test cost basis calculations with multiple buy/sell cycles
- Property-based testing for invariants (e.g., "balance = sum of all cash_change")

---

## Phase 1 Domain Completeness

### Implemented
✅ Money value object with currency safety
✅ Ticker value object with validation
✅ Quantity value object with non-negativity
✅ Portfolio entity with identity
✅ Transaction entity with immutability
✅ Holding entity (derived, not persisted)
✅ PortfolioCalculator service for pure calculations
✅ Domain events for audit trail

### Future Enhancements (Phase 2+)
- User entity and authentication
- MarketPrice value object
- Position entity with real-time P&L tracking
- TradeOrder entity (pending orders)
- Watchlist entity
- Multiple currency support in Money
- Split-adjusted price calculations
