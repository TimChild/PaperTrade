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

```python
# Domain Service (stateless, pure function)
class PortfolioCalculator:
    @staticmethod
    def calculate_cash_balance(transactions: list[Transaction]) -> Money:
        # Pure calculation, no side effects
        ...

# NOT a domain service (has state, does I/O)
class PortfolioManager:
    def __init__(self, database: Database):  # Has dependencies!
        self.db = database
    
    async def save_portfolio(self, portfolio: Portfolio):  # Does I/O!
        await self.db.save(portfolio)
```

**Domain services should:**
- Be stateless (no instance variables)
- Be pure functions where possible
- Have no dependencies on infrastructure (no DB, no APIs)
- Accept domain objects as parameters
- Return domain objects or primitives

---

## PortfolioCalculator

### Purpose

Calculates **portfolio state from the transaction ledger**. This is the core domain service that implements the ledger pattern - deriving current cash, holdings, and value from immutable transaction history.

### Specification

```python
from typing import Protocol
from decimal import Decimal

class PortfolioCalculator(Protocol):
    """Calculates portfolio state from transaction history.
    
    This is a stateless service - all methods are pure functions
    that take transactions and return calculated state.
    """
    
    @staticmethod
    def calculate_cash_balance(transactions: list[Transaction]) -> Money:
        """Calculate current cash balance from transaction history."""
        ...
    
    @staticmethod
    def calculate_holdings(transactions: list[Transaction]) -> list[Holding]:
        """Aggregate buy/sell transactions into current holdings (FIFO)."""
        ...
    
    @staticmethod
    def calculate_total_value(
        holdings: list[Holding],
        prices: dict[Ticker, Money],
        cash_balance: Money,
    ) -> Money:
        """Calculate total portfolio value at given prices."""
        ...
```

### Why Static Methods?

Domain services are **stateless**, so we use static methods:

```python
# Pure function - same inputs always give same output
cash = PortfolioCalculator.calculate_cash_balance(transactions)

# No state to manage:
# - No __init__ needed
# - No instance variables
# - Thread-safe by default
# - Easy to test (no setup/teardown)
```

---

## calculate_cash_balance

### Purpose

Calculates the **current cash balance** by summing all cash movements in the transaction history.

### Signature

```python
@staticmethod
def calculate_cash_balance(transactions: list[Transaction]) -> Money:
    """Calculate current cash balance from transaction history.
    
    Args:
        transactions: All transactions for a portfolio (any order)
        
    Returns:
        Current cash balance (can be negative if over-withdrawn)
        
    Examples:
        >>> transactions = [
        ...     Transaction(..., type=DEPOSIT, amount=Money(Decimal("10000"), "USD")),
        ...     Transaction(..., type=BUY, amount=Money(Decimal("1500"), "USD")),
        ...     Transaction(..., type=SELL, amount=Money(Decimal("1600"), "USD")),
        ... ]
        >>> PortfolioCalculator.calculate_cash_balance(transactions)
        Money(amount=Decimal('10100.00'), currency='USD')
    """
```

### Algorithm

```
For each transaction:
  - DEPOSIT: +amount
  - WITHDRAWAL: -amount
  - BUY: -amount (cash used to purchase)
  - SELL: +amount (cash received from sale)
  - DIVIDEND: +amount
  - FEE: -amount

Result: Sum of all movements
```

### Pseudocode

```python
def calculate_cash_balance(transactions: list[Transaction]) -> Money:
    if not transactions:
        return Money(Decimal("0"), "USD")
    
    # Start with zero balance
    balance = Decimal("0")
    currency = transactions[0].amount.currency
    
    for txn in transactions:
        match txn.type:
            case TransactionType.DEPOSIT | TransactionType.SELL | TransactionType.DIVIDEND:
                # Cash increases
                balance += txn.amount.amount
            
            case TransactionType.WITHDRAWAL | TransactionType.BUY | TransactionType.FEE:
                # Cash decreases
                balance -= txn.amount.amount
    
    return Money(balance, currency)
```

### Edge Cases

```python
# Empty transaction list
assert calculate_cash_balance([]) == Money(Decimal("0"), "USD")

# Single deposit
txns = [Transaction(..., type=DEPOSIT, amount=Money(Decimal("1000"), "USD"))]
assert calculate_cash_balance(txns) == Money(Decimal("1000"), "USD")

# Negative balance (over-withdrawn - business rule should prevent this)
txns = [
    Transaction(..., type=DEPOSIT, amount=Money(Decimal("100"), "USD")),
    Transaction(..., type=WITHDRAWAL, amount=Money(Decimal("200"), "USD")),
]
result = calculate_cash_balance(txns)
assert result.amount < 0  # Negative balance possible in calculation
```

### Currency Handling

**Assumption:** All transactions in a portfolio use the same currency.

```python
# If transactions have different currencies, raise error
def calculate_cash_balance(transactions: list[Transaction]) -> Money:
    if not transactions:
        return Money(Decimal("0"), "USD")
    
    currency = transactions[0].amount.currency
    
    for txn in transactions:
        if txn.amount.currency != currency:
            raise CurrencyMismatchError(
                f"All transactions must use {currency}, found {txn.amount.currency}"
            )
    
    # ... proceed with calculation
```

---

## calculate_holdings

### Purpose

Aggregates **buy and sell transactions** into current holdings per ticker, calculating average cost basis using **FIFO (First In, First Out)** accounting.

### Signature

```python
@staticmethod
def calculate_holdings(transactions: list[Transaction]) -> list[Holding]:
    """Aggregate buy/sell transactions into current holdings (FIFO).
    
    Args:
        transactions: All transactions for a portfolio (any order)
        
    Returns:
        List of current holdings (only tickers with quantity > 0)
        
    Examples:
        >>> transactions = [
        ...     Transaction(..., type=BUY, ticker="AAPL", quantity=10, price=150),
        ...     Transaction(..., type=BUY, ticker="AAPL", quantity=5, price=160),
        ...     Transaction(..., type=SELL, ticker="AAPL", quantity=5, price=170),
        ... ]
        >>> holdings = PortfolioCalculator.calculate_holdings(transactions)
        >>> holdings[0].ticker == Ticker("AAPL")
        True
        >>> holdings[0].quantity == Quantity(Decimal("10"))
        True
        >>> holdings[0].average_cost  # FIFO: 5@150 + 5@160 = avg 155
        Money(amount=Decimal('155.00'), currency='USD')
    """
```

### Algorithm: FIFO Cost Basis

**FIFO (First In, First Out)**: When selling shares, we sell the oldest shares first.

```
Purchases (lots):
1. BUY 10 @ $150 → [Lot1: 10@150]
2. BUY 5 @ $160  → [Lot1: 10@150, Lot2: 5@160]

Sale:
3. SELL 5 @ $170
   → Remove from Lot1 first (FIFO)
   → Lot1: 10 - 5 = 5 remaining
   → Realized gain: 5 × ($170 - $150) = $100
   → Remaining lots: [Lot1: 5@150, Lot2: 5@160]

Current holding:
- Quantity: 10 shares (5 + 5)
- Average cost: ($750 + $800) / 10 = $155
```

### Pseudocode

```python
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class Lot:
    """A batch of shares purchased at the same time/price."""
    quantity: Decimal
    cost_per_share: Decimal

def calculate_holdings(transactions: list[Transaction]) -> list[Holding]:
    # Sort transactions by timestamp (oldest first for FIFO)
    sorted_txns = sorted(transactions, key=lambda t: t.timestamp)
    
    # Track lots per ticker (FIFO queue)
    ticker_lots: dict[Ticker, list[Lot]] = defaultdict(list)
    
    for txn in sorted_txns:
        # Skip non-trade transactions
        if txn.type not in (TransactionType.BUY, TransactionType.SELL):
            continue
        
        ticker = txn.ticker
        
        if txn.type == TransactionType.BUY:
            # Add new lot to the end (newest)
            lot = Lot(
                quantity=txn.quantity.value,
                cost_per_share=txn.price_per_share.amount,
            )
            ticker_lots[ticker].append(lot)
        
        elif txn.type == TransactionType.SELL:
            # Remove shares from oldest lots first (FIFO)
            remaining_to_sell = txn.quantity.value
            
            while remaining_to_sell > 0 and ticker_lots[ticker]:
                oldest_lot = ticker_lots[ticker][0]
                
                if oldest_lot.quantity <= remaining_to_sell:
                    # Sell entire lot
                    remaining_to_sell -= oldest_lot.quantity
                    ticker_lots[ticker].pop(0)  # Remove lot
                else:
                    # Sell partial lot
                    oldest_lot.quantity -= remaining_to_sell
                    remaining_to_sell = 0
    
    # Convert lots to holdings
    holdings = []
    for ticker, lots in ticker_lots.items():
        if not lots:
            continue  # No shares remaining
        
        # Calculate total quantity and weighted average cost
        total_quantity = sum(lot.quantity for lot in lots)
        total_cost = sum(lot.quantity * lot.cost_per_share for lot in lots)
        average_cost = total_cost / total_quantity
        
        holding = Holding(
            ticker=ticker,
            quantity=Quantity(total_quantity),
            average_cost=Money(average_cost, "USD"),
        )
        holdings.append(holding)
    
    return holdings
```

### Examples

#### Example 1: Simple Buy-Sell

```python
transactions = [
    # BUY 10 AAPL @ $150
    Transaction(
        id=uuid4(),
        portfolio_id=uuid4(),
        type=TransactionType.BUY,
        amount=Money(Decimal("1500"), "USD"),
        ticker=Ticker("AAPL"),
        quantity=Quantity(Decimal("10")),
        price_per_share=Money(Decimal("150"), "USD"),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
    ),
    # SELL 5 AAPL @ $160
    Transaction(
        id=uuid4(),
        portfolio_id=uuid4(),
        type=TransactionType.SELL,
        amount=Money(Decimal("800"), "USD"),
        ticker=Ticker("AAPL"),
        quantity=Quantity(Decimal("5")),
        price_per_share=Money(Decimal("160"), "USD"),
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
    ),
]

holdings = PortfolioCalculator.calculate_holdings(transactions)

# Expected:
# - 5 shares remaining
# - Average cost: $150 (all from original lot)
assert holdings[0].ticker == Ticker("AAPL")
assert holdings[0].quantity == Quantity(Decimal("5"))
assert holdings[0].average_cost == Money(Decimal("150"), "USD")
```

#### Example 2: Multiple Lots

```python
transactions = [
    # BUY 10 AAPL @ $150 (Lot 1)
    Transaction(..., type=BUY, ticker="AAPL", quantity=10, price=150, timestamp=T1),
    # BUY 5 AAPL @ $160 (Lot 2)
    Transaction(..., type=BUY, ticker="AAPL", quantity=5, price=160, timestamp=T2),
    # SELL 7 AAPL @ $170 (removes all of Lot 1 + 2 from Lot 2)
    Transaction(..., type=SELL, ticker="AAPL", quantity=7, price=170, timestamp=T3),
]

holdings = PortfolioCalculator.calculate_holdings(transactions)

# Remaining:
# - 3 shares from Lot 2 @ $160
# - 5 shares from Lot 1 @ $150
# Wait, we sold 7 shares using FIFO:
#   - First 10 from Lot 1 @ $150 (but we only need 7)
#   - Actually: Remove 7 from Lot 1, leaving 3 from Lot 1 + all 5 from Lot 2
# Correction:
# - 3 shares @ $150 (remaining from Lot 1)
# - 5 shares @ $160 (all of Lot 2)
# - Total: 8 shares
# - Average cost: (3×150 + 5×160) / 8 = (450 + 800) / 8 = $156.25

assert holdings[0].quantity == Quantity(Decimal("8"))
assert holdings[0].average_cost == Money(Decimal("156.25"), "USD")
```

#### Example 3: Sell All Shares

```python
transactions = [
    Transaction(..., type=BUY, ticker="AAPL", quantity=10, price=150),
    Transaction(..., type=SELL, ticker="AAPL", quantity=10, price=160),
]

holdings = PortfolioCalculator.calculate_holdings(transactions)

# Expected: No holdings (all sold)
assert holdings == []
```

### Edge Cases

```python
# No trade transactions
transactions = [
    Transaction(..., type=DEPOSIT, amount=Money(Decimal("1000"), "USD")),
]
assert calculate_holdings(transactions) == []

# Buy without sell
transactions = [
    Transaction(..., type=BUY, ticker="AAPL", quantity=10, price=150),
]
holdings = calculate_holdings(transactions)
assert holdings[0].quantity == Quantity(Decimal("10"))
assert holdings[0].average_cost == Money(Decimal("150"), "USD")

# Multiple tickers
transactions = [
    Transaction(..., type=BUY, ticker="AAPL", quantity=10, price=150),
    Transaction(..., type=BUY, ticker="GOOGL", quantity=5, price=140),
]
holdings = calculate_holdings(transactions)
assert len(holdings) == 2
```

---

## calculate_total_value

### Purpose

Calculates the **total portfolio value** by summing the market value of all holdings plus cash balance.

### Signature

```python
@staticmethod
def calculate_total_value(
    holdings: list[Holding],
    prices: dict[Ticker, Money],
    cash_balance: Money,
) -> Money:
    """Calculate total portfolio value at given prices.
    
    Args:
        holdings: Current holdings
        prices: Current market prices per ticker
        cash_balance: Current cash balance
        
    Returns:
        Total portfolio value (sum of holdings + cash)
        
    Raises:
        ValueError: If price missing for a holding
        
    Examples:
        >>> holdings = [
        ...     Holding(ticker=Ticker("AAPL"), quantity=Quantity(Decimal("10")), ...),
        ...     Holding(ticker=Ticker("GOOGL"), quantity=Quantity(Decimal("5")), ...),
        ... ]
        >>> prices = {
        ...     Ticker("AAPL"): Money(Decimal("170"), "USD"),
        ...     Ticker("GOOGL"): Money(Decimal("150"), "USD"),
        ... }
        >>> cash = Money(Decimal("1000"), "USD")
        >>> PortfolioCalculator.calculate_total_value(holdings, prices, cash)
        Money(amount=Decimal('3450.00'), currency='USD')
        # 10×170 + 5×150 + 1000 = 1700 + 750 + 1000 = 3450
    """
```

### Algorithm

```
total_value = cash_balance

For each holding:
  price = prices[holding.ticker]
  holding_value = holding.quantity × price
  total_value += holding_value

Return total_value
```

### Pseudocode

```python
def calculate_total_value(
    holdings: list[Holding],
    prices: dict[Ticker, Money],
    cash_balance: Money,
) -> Money:
    total = cash_balance
    
    for holding in holdings:
        if holding.ticker not in prices:
            raise ValueError(f"Price not found for {holding.ticker}")
        
        price = prices[holding.ticker]
        holding_value = price.multiply(holding.quantity.value)
        total = total.add(holding_value)
    
    return total
```

### Examples

```python
# Portfolio with cash only
holdings = []
cash = Money(Decimal("10000"), "USD")
prices = {}
total = calculate_total_value(holdings, prices, cash)
assert total == Money(Decimal("10000"), "USD")

# Portfolio with one holding
holdings = [
    Holding(
        ticker=Ticker("AAPL"),
        quantity=Quantity(Decimal("10")),
        average_cost=Money(Decimal("150"), "USD"),
    )
]
prices = {Ticker("AAPL"): Money(Decimal("170"), "USD")}
cash = Money(Decimal("8500"), "USD")
total = calculate_total_value(holdings, prices, cash)
# 10 × $170 + $8500 = $1700 + $8500 = $10200
assert total == Money(Decimal("10200"), "USD")

# Multiple holdings
holdings = [
    Holding(ticker=Ticker("AAPL"), quantity=Quantity(Decimal("10")), ...),
    Holding(ticker=Ticker("GOOGL"), quantity=Quantity(Decimal("5")), ...),
]
prices = {
    Ticker("AAPL"): Money(Decimal("170"), "USD"),
    Ticker("GOOGL"): Money(Decimal("150"), "USD"),
}
cash = Money(Decimal("1000"), "USD")
total = calculate_total_value(holdings, prices, cash)
# (10×170) + (5×150) + 1000 = 1700 + 750 + 1000 = 3450
assert total == Money(Decimal("3450"), "USD")
```

### Error Handling

```python
# Missing price for a holding
holdings = [Holding(ticker=Ticker("AAPL"), ...)]
prices = {}  # No price for AAPL!
cash = Money(Decimal("1000"), "USD")

# Should raise error
with pytest.raises(ValueError, match="Price not found for AAPL"):
    calculate_total_value(holdings, prices, cash)
```

---

## Additional Domain Services (Future)

### PortfolioValidator

```python
class PortfolioValidator:
    """Validates business rules before executing transactions."""
    
    @staticmethod
    def can_withdraw(
        transactions: list[Transaction],
        amount: Money,
    ) -> bool:
        """Check if portfolio has sufficient cash for withdrawal."""
        cash_balance = PortfolioCalculator.calculate_cash_balance(transactions)
        return cash_balance >= amount
    
    @staticmethod
    def can_buy(
        transactions: list[Transaction],
        cost: Money,
    ) -> bool:
        """Check if portfolio has sufficient cash for purchase."""
        cash_balance = PortfolioCalculator.calculate_cash_balance(transactions)
        return cash_balance >= cost
    
    @staticmethod
    def can_sell(
        transactions: list[Transaction],
        ticker: Ticker,
        quantity: Quantity,
    ) -> bool:
        """Check if portfolio has sufficient shares for sale."""
        holdings = PortfolioCalculator.calculate_holdings(transactions)
        
        for holding in holdings:
            if holding.ticker == ticker:
                return holding.quantity >= quantity
        
        return False  # Ticker not found = can't sell
```

### ReturnsCalculator

```python
class ReturnsCalculator:
    """Calculates investment returns and performance metrics."""
    
    @staticmethod
    def calculate_realized_gains(
        transactions: list[Transaction],
    ) -> Money:
        """Calculate total realized gains/losses from closed positions."""
        ...
    
    @staticmethod
    def calculate_unrealized_gains(
        holdings: list[Holding],
        prices: dict[Ticker, Money],
    ) -> Money:
        """Calculate unrealized gains/losses on open positions."""
        ...
    
    @staticmethod
    def calculate_total_return(
        initial_value: Money,
        current_value: Money,
    ) -> Decimal:
        """Calculate percentage return."""
        return (current_value.amount - initial_value.amount) / initial_value.amount
```

---

## Testing Domain Services

### Unit Tests

```python
import pytest
from decimal import Decimal
from datetime import datetime, UTC
from uuid import uuid4

class TestPortfolioCalculator:
    def test_calculate_cash_balance_empty(self):
        result = PortfolioCalculator.calculate_cash_balance([])
        assert result == Money(Decimal("0"), "USD")
    
    def test_calculate_cash_balance_single_deposit(self):
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("10000"), "USD"),
                timestamp=datetime.now(UTC),
            )
        ]
        result = PortfolioCalculator.calculate_cash_balance(txns)
        assert result == Money(Decimal("10000"), "USD")
    
    def test_calculate_cash_balance_with_trades(self):
        txns = [
            Transaction(..., type=DEPOSIT, amount=Money(Decimal("10000"), "USD")),
            Transaction(..., type=BUY, amount=Money(Decimal("1500"), "USD")),
            Transaction(..., type=SELL, amount=Money(Decimal("1600"), "USD")),
        ]
        result = PortfolioCalculator.calculate_cash_balance(txns)
        # 10000 - 1500 + 1600 = 10100
        assert result == Money(Decimal("10100"), "USD")
    
    def test_calculate_holdings_empty(self):
        result = PortfolioCalculator.calculate_holdings([])
        assert result == []
    
    def test_calculate_holdings_single_buy(self):
        txns = [
            Transaction(
                ...,
                type=BUY,
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150"), "USD"),
                timestamp=datetime.now(UTC),
            )
        ]
        holdings = PortfolioCalculator.calculate_holdings(txns)
        assert len(holdings) == 1
        assert holdings[0].ticker == Ticker("AAPL")
        assert holdings[0].quantity == Quantity(Decimal("10"))
        assert holdings[0].average_cost == Money(Decimal("150"), "USD")
    
    def test_calculate_holdings_fifo(self):
        txns = [
            Transaction(..., type=BUY, ticker="AAPL", quantity=10, price=150, timestamp=T1),
            Transaction(..., type=BUY, ticker="AAPL", quantity=5, price=160, timestamp=T2),
            Transaction(..., type=SELL, ticker="AAPL", quantity=7, price=170, timestamp=T3),
        ]
        holdings = PortfolioCalculator.calculate_holdings(txns)
        # Sold 7 from first lot (10@150), leaving 3@150 + 5@160 = 8 total
        # Average: (3×150 + 5×160) / 8 = (450 + 800) / 8 = 156.25
        assert holdings[0].quantity == Quantity(Decimal("8"))
        assert holdings[0].average_cost == Money(Decimal("156.25"), "USD")
    
    def test_calculate_total_value(self):
        holdings = [
            Holding(ticker=Ticker("AAPL"), quantity=Quantity(Decimal("10")), ...),
        ]
        prices = {Ticker("AAPL"): Money(Decimal("170"), "USD")}
        cash = Money(Decimal("8500"), "USD")
        
        total = PortfolioCalculator.calculate_total_value(holdings, prices, cash)
        # 10×170 + 8500 = 10200
        assert total == Money(Decimal("10200"), "USD")
```

### Property-Based Tests

```python
from hypothesis import given, assume
from hypothesis.strategies import lists, decimals

@given(lists(decimals(min_value=0, max_value=10000, places=2)))
def test_cash_balance_sum_property(amounts):
    """Cash balance should equal sum of deposits minus withdrawals."""
    txns = []
    expected_balance = Decimal("0")
    
    for amount in amounts:
        txn = Transaction(
            ...,
            type=TransactionType.DEPOSIT,
            amount=Money(amount, "USD"),
            timestamp=datetime.now(UTC),
        )
        txns.append(txn)
        expected_balance += amount
    
    result = PortfolioCalculator.calculate_cash_balance(txns)
    assert result.amount == expected_balance
```

---

## Design Rationale

### Why Separate Calculator from Entity?

**Option 1: Methods on Portfolio (rejected)**
```python
class Portfolio:
    def get_cash_balance(self, transactions: list[Transaction]) -> Money:
        # Portfolio knows too much about transaction processing
        ...
```

**Option 2: Separate Service (chosen)**
```python
class PortfolioCalculator:
    @staticmethod
    def calculate_cash_balance(transactions: list[Transaction]) -> Money:
        # Clear separation: Portfolio is data, Calculator is logic
        ...
```

**Benefits:**
- **Single Responsibility**: Portfolio is data container, Calculator is computation
- **Testability**: Can test calculations without creating Portfolios
- **Reusability**: Can use calculator for hypothetical scenarios
- **Clarity**: Clear that this is derived, not stored

### Why FIFO Instead of LIFO?

**FIFO (First In, First Out)** is the standard for several reasons:

1. **Tax Compliance**: Required in many jurisdictions
2. **Conservatism**: Realizes lower cost basis first (higher taxes)
3. **Predictability**: Intuitive for users
4. **Audit Trail**: Clear which lots were sold

**Alternative methods** (not implemented):
- **LIFO** (Last In, First Out): Tax optimization in some regions
- **Specific Lot**: User selects which shares to sell
- **Average Cost**: Simplified calculation

### Why Pass Holdings to calculate_total_value?

**Option 1: Calculate holdings inside (rejected)**
```python
def calculate_total_value(
    transactions: list[Transaction],  # Recalculate holdings every time
    prices: dict[Ticker, Money],
    cash_balance: Money,
) -> Money:
    holdings = calculate_holdings(transactions)  # Wasteful if already calculated
    ...
```

**Option 2: Accept holdings (chosen)**
```python
def calculate_total_value(
    holdings: list[Holding],  # Reuse if already calculated
    prices: dict[Ticker, Money],
    cash_balance: Money,
) -> Money:
    ...
```

**Benefits:**
- Avoid redundant calculations
- Composability (can inspect holdings first)
- Clear dependencies

---

## References

- **[Value Objects](./value-objects.md)**: Money, Ticker, Quantity used in calculations
- **[Entities](./entities.md)**: Portfolio, Transaction, Holding definitions
- **[Domain Rules](./domain-rules.md)**: Business rules validated by services
- **[Repository Ports](./repository-ports.md)**: How to fetch transactions for calculations
