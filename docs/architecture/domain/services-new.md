# Domain Services

## Overview

Domain services contain **business logic that doesn't naturally belong to a single entity or value object**. They are stateless operations that coordinate between multiple domain objects.

### When to Use Domain Services

| Use Domain Service When | Use Entity Method When |
|------------------------|------------------------|
| Logic involves multiple entities | Logic operates on single entity |
| Operation is stateless | Operation modifies entity state |
| Represents a process or calculation | Represents object behavior |
| No natural owner (pure function) | Clear ownership (method on object) |

### Characteristics

**Domain services should:**
- Be stateless (no instance variables)
- Be pure functions where possible
- Have NO dependencies on infrastructure (no DB, no APIs)
- Accept domain objects as parameters
- Return domain objects or primitives
- Use static methods or module-level functions

---

## PortfolioCalculator

### Purpose

Calculates **portfolio state from the transaction ledger**. This is the core domain service that implements the ledger pattern - deriving current cash, holdings, and value from immutable transaction history.

### Why a Service?

This logic doesn't belong in Portfolio or Transaction:
- Operates on collections of Transactions
- Pure calculation with no side effects
- Stateless - same inputs always give same outputs

### Methods

All methods should be static/stateless:

#### calculate_cash_balance(transactions: list[Transaction]) -> Money

Calculate current cash balance by summing all cash movements.

**Algorithm:**
```
For each transaction:
  - DEPOSIT: +amount
  - WITHDRAWAL: -amount
  - BUY: -amount (cash spent)
  - SELL: +amount (cash received)
  - DIVIDEND: +amount
  - FEE: -amount

Result: Sum of all movements
```

**Returns:** Current cash balance (can be negative if over-withdrawn)

#### calculate_holdings(transactions: list[Transaction]) -> list[Holding]

Aggregate BUY/SELL transactions into current holdings using FIFO cost basis.

**Algorithm:**
```
1. Group transactions by ticker
2. For each ticker:
   a. Create cost lots from BUY transactions (oldest first)
   b. Remove shares from cost lots for SELL transactions (FIFO)
   c. Calculate remaining quantity and average cost basis
3. Return holdings with quantity > 0
```

**FIFO (First In, First Out):**
- When selling, remove shares from oldest purchases first
- Tracks realized gain/loss per sale
- Remaining lots determine average cost basis

**Returns:** List of Holding objects (only tickers with shares > 0)

#### calculate_total_value(holdings: list[Holding], prices: dict[Ticker, Money], cash_balance: Money) -> Money

Calculate total portfolio value at current market prices.

**Algorithm:**
```
total = cash_balance
for each holding:
    market_value = holding.quantity × prices[holding.ticker]
    total += market_value
return total
```

**Returns:** Total portfolio value (cash + holdings at current prices)

### Implementation Notes

- Use static methods or module-level functions (both are fine)
- All calculations should be pure functions
- Use Decimal for all arithmetic
- Validate all transactions use same currency
- Consider caching holdings calculation for performance

---

## Trade Validation Service

### Purpose

Validates trade operations before creating transactions. Ensures business rules are enforced.

### Methods

#### can_buy(portfolio_state: PortfolioState, ticker: Ticker, quantity: Quantity, price: Money) -> ValidationResult

Check if portfolio has sufficient cash to execute a buy order.

**Validation:**
- Calculate total cost: `quantity × price`
- Check: `cash_balance >= total_cost`
- Return validation result with error message if insufficient funds

#### can_sell(holdings: list[Holding], ticker: Ticker, quantity: Quantity) -> ValidationResult

Check if portfolio has sufficient shares to execute a sell order.

**Validation:**
- Find holding for ticker
- Check: `holding.quantity >= quantity`
- Return validation result with error message if insufficient shares

#### can_withdraw(cash_balance: Money, amount: Money) -> ValidationResult

Check if portfolio has sufficient cash to withdraw.

**Validation:**
- Check: `cash_balance >= amount`
- Return validation result with error message if insufficient funds

### ValidationResult

Simple return type for validation:

**Properties:**
- `is_valid: bool` - Whether validation passed
- `error_message: str | None` - Error description if invalid

**Usage:**
```
result = TradeValidationService.can_buy(state, ticker, quantity, price)
if not result.is_valid:
    raise InsufficientFundsError(result.error_message)
```

---

## FIFO Cost Basis Algorithm (Detailed)

The FIFO (First In, First Out) algorithm is critical for accurate holdings and tax calculations.

### Data Structures

**Cost Lot:**
- `quantity: Quantity` - Number of shares in this lot
- `price_per_share: Money` - Purchase price
- `total_cost: Money` - Total cost of lot
- `purchase_date: datetime` - When shares were bought

### Algorithm Steps

**Step 1: Create Cost Lots from BUY Transactions**
```
cost_lots = []
for each BUY transaction (chronological order):
    create cost_lot:
        quantity = transaction.quantity
        price_per_share = transaction.price_per_share
        total_cost = transaction.amount
        purchase_date = transaction.timestamp
    add cost_lot to list
```

**Step 2: Remove Shares from Cost Lots for SELL Transactions**
```
for each SELL transaction (chronological order):
    remaining_to_sell = transaction.quantity

    while remaining_to_sell > 0:
        oldest_lot = cost_lots[0]

        if oldest_lot.quantity <= remaining_to_sell:
            # Sell entire lot
            realize_gain(oldest_lot, transaction.price_per_share)
            remove oldest_lot from cost_lots
            remaining_to_sell -= oldest_lot.quantity
        else:
            # Partial lot sale
            sell_quantity = remaining_to_sell
            realize_gain(partial_lot, transaction.price_per_share)
            oldest_lot.quantity -= sell_quantity
            oldest_lot.total_cost = oldest_lot.quantity × oldest_lot.price_per_share
            remaining_to_sell = 0
```

**Step 3: Calculate Holdings from Remaining Lots**
```
for each ticker with remaining cost_lots:
    total_quantity = sum(lot.quantity for lot in cost_lots)
    total_cost = sum(lot.total_cost for lot in cost_lots)
    average_cost_basis = total_cost / total_quantity

    create Holding:
        ticker = ticker
        quantity = total_quantity
        average_cost_basis = average_cost_basis
        total_cost = total_cost
```

### Realized Gain/Loss Calculation

When selling shares from a cost lot:
```
sale_proceeds = sell_quantity × sale_price_per_share
cost_basis = sell_quantity × lot_purchase_price_per_share
realized_gain = sale_proceeds - cost_basis
```

Track realized gains separately from unrealized gains in holdings.

---

## Service Dependencies

### Pure Domain Services (No Dependencies)

- `PortfolioCalculator` - Pure functions, no dependencies
- `TradeValidationService` - Uses calculator, but no infrastructure

### Application Services (Use Repositories)

These are NOT domain services - they belong in the application layer:
- `PortfolioService` - Uses repositories for persistence
- `TradeExecutionService` - Coordinates domain logic with persistence

**Key Distinction:**
- **Domain Service**: Pure business logic, no I/O
- **Application Service**: Orchestrates domain + infrastructure

---

## Testing Domain Services

### Test Strategy

**Pure Function Tests:**
- Input → Service → Output
- No mocking needed (pure functions)
- Test with real domain objects

**Example Test Structure:**
```
test_calculate_cash_balance:
  - Empty transactions → $0
  - Single deposit → deposit amount
  - Deposit + buy → deposit - buy amount
  - Complex sequence → correct sum
  - Different currencies → error

test_calculate_holdings_fifo:
  - No transactions → empty list
  - Single buy → one holding
  - Buy then sell (partial) → reduced holding
  - Buy then sell (full) → no holding
  - Multiple buys then sell → FIFO applied correctly
  - Fractional shares → correct calculations
```

### Property-Based Testing

Use hypothesis for FIFO algorithm:
```
Property: Total shares in + total shares sold = remaining holdings + sold shares
Property: FIFO always sells oldest lots first
Property: Average cost basis is always total_cost / total_quantity
```

---

## Design Rationale

### Why Not Put This in Entities?

**Option 1: Portfolio.get_cash_balance()** ❌
- Portfolio doesn't have transactions (only id/name)
- Would need to load transactions each time
- Violates single responsibility

**Option 2: Transaction.calculate_balance()** ❌
- Individual transaction doesn't know about portfolio state
- Requires operating on collection, not single transaction

**Option 3: PortfolioCalculator.calculate_cash_balance(transactions)** ✅
- Clear responsibility: calculations
- Stateless and testable
- Works with any list of transactions

### Why Static Methods vs Instance Methods?

Both are acceptable:

**Static Methods:**
```
cash = PortfolioCalculator.calculate_cash_balance(transactions)
```

**Module-Level Functions:**
```
from domain.services.portfolio_calculator import calculate_cash_balance
cash = calculate_cash_balance(transactions)
```

Choose based on team preference. Static methods group related calculations; module functions are more Pythonic.

---

## References

- [Entities](entities.md) - Domain entities processed by services
- [Value Objects](value-objects.md) - Types used in calculations
- [Domain Rules](domain-rules.md) - Business rules enforced by services
- [Repository Ports](repository-ports.md) - Not used by domain services (application layer uses these)
