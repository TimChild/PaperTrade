# Entities

## Overview

Entities are **domain objects with identity** that can change over time. Unlike value objects, two entities with the same field values but different IDs are considered different objects.

### Entity vs Value Object

| Aspect | Entity | Value Object |
|--------|--------|--------------|
| **Identity** | Has unique ID | No identity, defined by values |
| **Mutability** | Can change over time | Immutable |
| **Equality** | By ID | By value |
| **Lifecycle** | Created, modified, archived | Created, never modified |
| **Example** | Portfolio, User | Money, Ticker |

### Entity Characteristics

- **Identity**: Two entities with the same attribute values but different IDs represent **different** domain objects.
- **Mutability**: Entity state can change over time through well-defined domain operations (e.g., renaming a portfolio, archiving it).
- **Value objects**: Do not have identity; two value objects with the same values are considered equal and interchangeable (e.g., two amounts of money with the same currency and quantity).

---

## Portfolio

### Purpose

Represents a **user's trading account** - the primary aggregate root for trading operations. Contains metadata about the portfolio but derives its state (cash, holdings) from the transaction ledger.

### Specification

The `Portfolio` entity:

- Is an **aggregate root** for trading-related operations.
- Owns and organizes the set of **transactions** associated with a user.
- Does **not** directly store derived values like current cash balance or open positions; those are computed from the transaction history.

**Fields**

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `id` | UUID | Unique identifier of the portfolio | — |
| `user_id` | UUID | Identifier of the user who owns the portfolio | — |
| `name` | String | Human-readable name for the portfolio | — |
| `created_at` | DateTime (UTC) | When the portfolio was created | — |
| `archived` | Boolean | Whether the portfolio is no longer actively used | `false` |

**Behavioral notes**

- Portfolios can be **renamed** without changing their identity.
- Portfolios can be **archived**; archiving does not delete historical transactions, but prevents new trading activity in that portfolio.
- Invariants:
  - `name` should be non-empty and meaningful to the end user.
  - Once created, `user_id` and `id` must not change.

### Identity

The `id` field provides identity. Two portfolios with the same name and user but different IDs are distinct entities.

**Equality semantics:**
- Portfolios are equal if they have the same ID
- Hash by ID for use in sets/dicts

### Lifecycle

```
┌─────────────┐
│   Created   │  (name, user_id provided)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Active    │  (can execute trades, rename)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Archived   │  (read-only, soft deleted)
└─────────────┘
```

**States:**
1. **Created**: New portfolio, no transactions yet
2. **Active**: Normal state, can execute trades
3. **Archived**: Soft-deleted, read-only

### Domain Operations

**Rename Portfolio**
- Operation: Change portfolio name
- Input: New name (non-empty string)
- Validates: Name is non-empty after trimming
- Effect: Updates `name` field

**Archive Portfolio**
- Operation: Soft delete the portfolio
- Effect: Sets `archived = true`
- Note: Archived portfolios are read-only and hidden from active lists

**Unarchive Portfolio**
- Operation: Restore an archived portfolio
- Effect: Sets `archived = false`

### Derived State

The Portfolio's **financial state is NOT stored** in the entity itself. Instead, it's calculated from the transaction ledger by the `PortfolioCalculator` service.

**Derived properties (computed at runtime):**
- Cash balance
- Holdings (positions in stocks)
- Total value (requires current market prices)

**Why derive instead of store?**
- **Single Source of Truth**: Ledger is authoritative
- **Time Travel**: Can calculate state at any point in time
- **Consistency**: No sync issues between balance and transactions
- **Audit Trail**: Complete history always available

### Invariants

1. **Name Required**: Portfolio name cannot be empty
2. **User Ownership**: Portfolio belongs to exactly one user
3. **Created Timestamp**: Must be valid UTC datetime
4. **Archive Constraint**: Archived portfolios should not accept new trades (enforced by use cases)

### Validation

**Construction validation:**
- Name must be non-empty and non-whitespace
- User ID must be provided
- Created timestamp must be timezone-aware UTC

---

## Transaction

### Purpose

Represents an **immutable ledger entry** recording a financial event. Transactions are the foundation of the ledger pattern - they are never modified or deleted.

### Specification

**Transaction Types:**
- `DEPOSIT` - Add cash to portfolio
- `WITHDRAWAL` - Remove cash from portfolio
- `BUY` - Purchase shares
- `SELL` - Sell shares
- `DIVIDEND` - Dividend payment (future)
- `FEE` - Trading fee (future)

**Fields**

| Property | Type | Description | Required For |
|----------|------|-------------|--------------|
| `id` | UUID | Unique transaction ID | All |
| `portfolio_id` | UUID | Portfolio this belongs to | All |
| `type` | TransactionType | Transaction type | All |
| `amount` | Money | Monetary amount (always positive) | All |
| `ticker` | Ticker \| None | Stock symbol | BUY, SELL |
| `quantity` | Quantity \| None | Number of shares | BUY, SELL |
| `price_per_share` | Money \| None | Price per share | BUY, SELL |
| `timestamp` | DateTime | When transaction occurred (UTC) | All |
| `notes` | String \| None | Optional notes | All |

### Transaction Type Details

#### DEPOSIT
Add cash to the portfolio.

**Required fields:**
- `amount`: Cash amount to add

**Optional fields:**
- `notes`: Description

**Fields that must be None:**
- `ticker`, `quantity`, `price_per_share`

**Effect:**
- Cash balance: `+amount`
- Holdings: No change

#### WITHDRAWAL
Remove cash from the portfolio.

**Required fields:**
- `amount`: Cash amount to remove

**Optional fields:**
- `notes`: Description

**Fields that must be None:**
- `ticker`, `quantity`, `price_per_share`

**Effect:**
- Cash balance: `-amount`
- Holdings: No change

#### BUY
Purchase shares of a stock.

**Required fields:**
- `amount`: Total cost (must equal `quantity × price_per_share`)
- `ticker`: Stock symbol
- `quantity`: Number of shares
- `price_per_share`: Price paid per share

**Optional fields:**
- `notes`: Trade rationale

**Effect:**
- Cash balance: `-amount`
- Holdings: `+quantity` of `ticker`
- Cost basis: `price_per_share`

**Invariant:** `amount == quantity × price_per_share`

#### SELL
Sell shares of a stock.

**Required fields:**
- `amount`: Total proceeds (must equal `quantity × price_per_share`)
- `ticker`: Stock symbol
- `quantity`: Number of shares
- `price_per_share`: Price received per share

**Optional fields:**
- `notes`: Trade rationale

**Effect:**
- Cash balance: `+amount`
- Holdings: `-quantity` of `ticker`

**Invariant:** `amount == quantity × price_per_share`

### Immutability

Transactions are **immutable** - they cannot be modified after creation.

**The ledger pattern:**
- Never UPDATE transactions
- Never DELETE transactions
- Only APPEND new transactions

**To "undo" a trade:** Create a reverse transaction (e.g., SELL to undo a BUY)

**Why immutable?**
1. **Audit Trail**: Complete history is preserved
2. **Time Travel**: Can reconstruct portfolio at any point
3. **Consistency**: No risk of lost updates or race conditions
4. **Simplicity**: No complex state management

### Validation

Transactions must satisfy type-specific invariants:

**All transactions:**
- Amount must be positive
- Timestamp must be timezone-aware UTC

**Trade transactions (BUY, SELL):**
- Must have `ticker`, `quantity`, and `price_per_share`
- Amount must equal `quantity × price_per_share`

**Cash transactions (DEPOSIT, WITHDRAWAL):**
- Must NOT have `ticker`, `quantity`, or `price_per_share`

### Identity

**Equality semantics:**
- Transactions are equal if they have the same ID
- Hash by ID

---

## Holding

### Purpose

Represents a **current position in a stock** - a derived/computed view aggregated from the transaction ledger. Not stored directly, but calculated on demand.

### Specification

**Fields**

| Property | Type | Description | Computed? |
|----------|------|-------------|-----------|
| `ticker` | Ticker | Stock symbol | No |
| `quantity` | Quantity | Current shares owned | No |
| `average_cost` | Money | Cost basis per share | No |
| `total_cost` | Money | Total cost basis | Yes (property) |

**Computed properties:**
- `total_cost`: Total amount paid for all shares (`quantity × average_cost`)

### Derived Nature

Holdings are **NOT stored** as entities in the database. They are calculated from the transaction ledger by the `PortfolioCalculator`.

**Example calculation:**

```
Transactions:
1. BUY 10 AAPL @ $150
2. BUY 5 AAPL @ $160
3. SELL 5 AAPL @ $170

Result: 10 shares remaining
Average cost (FIFO): First 5 @ $150, next 5 @ $160 = avg $155
```

### Cost Basis Calculation

**FIFO (First In, First Out)** method:

```
Purchases:
1. BUY 10 @ $150 = $1,500
2. BUY 5 @ $160 = $800
Total: 15 shares for $2,300

Sell:
3. SELL 5 @ $170
   → Removes first 5 shares @ $150 (FIFO)
   → Realized gain: 5 × ($170 - $150) = $100

Remaining:
- 5 shares @ $150 (from first batch)
- 5 shares @ $160 (from second batch)
- Average cost: ($750 + $800) / 10 = $155
```

**Why FIFO?**
- Standard accounting method
- Tax-compliant in most jurisdictions
- Predictable and auditable

### Valuation Operations

**Calculate Market Value**
- Input: Current market price per share
- Output: Total market value (`quantity × current_price`)

**Calculate Unrealized Gain/Loss**
- Input: Current market price per share
- Output: Unrealized gain/loss (positive = gain, negative = loss)
- Formula: `(current_price - average_cost) × quantity`

### Immutability

Holdings are **value objects** - frozen and immutable. To update holdings, recalculate from the ledger.

**Don't modify holdings directly.** Instead:
1. Add a new transaction to the ledger
2. Recalculate holdings from updated ledger

---

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                          User                               │
│  (not in domain layer - lives in auth/user context)        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ owns (1:N)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Portfolio                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ id: UUID                                             │   │
│  │ user_id: UUID                                        │   │
│  │ name: str                                            │   │
│  │ created_at: datetime                                 │   │
│  │ archived: bool                                       │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ contains (1:N)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Transaction                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ id: UUID                                             │   │
│  │ portfolio_id: UUID                                   │   │
│  │ type: TransactionType                                │   │
│  │ amount: Money                                        │   │
│  │ ticker: Ticker | None                                │   │
│  │ quantity: Quantity | None                            │   │
│  │ price_per_share: Money | None                        │   │
│  │ timestamp: datetime                                  │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ aggregates to (N:M)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        Holding                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ticker: Ticker                                       │   │
│  │ quantity: Quantity                                   │   │
│  │ average_cost: Money                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  (Derived - not stored)                                     │
└─────────────────────────────────────────────────────────────┘
```

### Aggregate Boundaries

**Portfolio is the Aggregate Root:**
- Transactions belong to exactly one Portfolio
- External entities interact with Portfolio, not Transactions directly
- Portfolio enforces consistency boundaries

**Invariants enforced by Portfolio aggregate:**
- All Transactions must have valid portfolio_id
- Transaction timestamps should be sequential (for audit)
- Business rules (sufficient funds, shares) checked before adding Transaction

---

## Testing Entities

### Unit Test Coverage

**For each entity, test:**
1. **Valid Construction**: Creating with valid values
2. **Validation**: All invariants are enforced
3. **Domain Operations**: Rename, archive operations work correctly
4. **Equality**: Entities are equal by ID, not by values
5. **Immutability** (Transaction, Holding): Cannot be modified after creation
6. **Type-Specific Rules**: BUY requires ticker, DEPOSIT does not, etc.

### Example Test Scenarios

**Portfolio Tests:**
- Create portfolio with valid data
- Rename portfolio (valid and invalid names)
- Archive and unarchive portfolio
- Identity equality (same ID = equal, different ID = not equal)

**Transaction Tests:**
- Create valid DEPOSIT (no ticker)
- Create valid BUY (with ticker, quantity, price)
- Reject BUY without ticker
- Reject DEPOSIT with ticker
- Validate amount equals quantity × price for trades
- Immutability (cannot modify after creation)

**Holding Tests:**
- Calculate total cost (quantity × average_cost)
- Calculate market value (quantity × current_price)
- Calculate unrealized gain/loss
- Immutability

---

## Design Rationale

### Why Derive Holdings Instead of Storing?

**Option 1: Store Holdings (rejected)**
- Portfolio table: id, name, cash_balance
- Holding table: portfolio_id, ticker, quantity, avg_cost
- **Problem**: Must keep in sync with transactions!

**Option 2: Derive Holdings (chosen)**
- Portfolio table: id, name (metadata only)
- Transaction table: ledger entries (immutable)
- Holdings: Calculated from transactions when needed

**Benefits of derivation:**
- Single source of truth (transactions)
- No synchronization issues
- Time-travel capability
- Simpler consistency model

### Why Immutable Transactions?

The **ledger pattern** requires immutability:

1. **Audit Compliance**: Required for financial regulations
2. **Debugging**: Can replay events to understand state
3. **Consistency**: No lost updates or race conditions
4. **Simplicity**: Append-only data structure

### Why Portfolio Has No Balance Field?

**Problem with stored balance:**
- Transaction adds $100, but balance not updated → inconsistency
- Requires complex synchronization logic
- Can't reconstruct historical state

**Solution: Derive balance from transactions**
- Calculate from ledger when needed
- Always consistent with transaction history
- Supports point-in-time queries

---

## References

- **[Value Objects](./value-objects.md)**: Money, Ticker, Quantity used by entities
- **[Services](./services.md)**: PortfolioCalculator derives entity state
- **[Domain Rules](./domain-rules.md)**: Business rules for entity validation
- **[Repository Ports](./repository-ports.md)**: Persistence interfaces for entities
