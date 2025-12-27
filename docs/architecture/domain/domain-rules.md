# Domain Rules and Invariants

## Overview

Domain rules are **business constraints** that must always be satisfied. They represent the core business logic and ensure the system maintains valid states.

### Types of Rules

| Type | Description | Enforced By |
|------|-------------|-------------|
| **Invariants** | Conditions that must always be true | Entity validation, value object construction |
| **Preconditions** | Must be true before an operation | Use case validation, domain services |
| **Postconditions** | Must be true after an operation | Entity methods, use case logic |
| **Business Rules** | Domain-specific constraints | Domain services, use cases |

---

## Value Object Rules

### Money Rules

#### MR-1: Precision Constraint
**Rule:** All monetary amounts must not exceed 2 decimal places.

**Rationale:** Standard precision for USD and most fiat currencies.

**Enforcement:** Value object validation at construction time.

```python
# ✅ Valid
Money(Decimal("100.00"), "USD")  # Exactly 2 decimals
Money(Decimal("100.5"), "USD")   # Normalized to 100.50
Money(Decimal("100"), "USD")     # Normalized to 100.00

# ❌ Invalid
Money(Decimal("100.123"), "USD")  # Too many decimals → Raises InvalidPrecisionError
```

**Implementation:**
```python
def __post_init__(self) -> None:
    # Quantize to 2 decimal places
    quantized = self.amount.quantize(Decimal("0.01"))
    
    # Check if precision was lost
    if quantized != self.amount:
        raise InvalidPrecisionError(
            f"Amount {self.amount} exceeds 2 decimal places"
        )
    
    object.__setattr__(self, 'amount', quantized)
```

#### MR-2: Currency Consistency
**Rule:** Arithmetic operations require matching currencies.

**Rationale:** Cannot add USD and EUR without conversion.

**Enforcement:** Operation methods check currency match.

```python
# ✅ Valid
usd_1 = Money(Decimal("100"), "USD")
usd_2 = Money(Decimal("50"), "USD")
total = usd_1.add(usd_2)  # OK: Same currency

# ❌ Invalid
usd = Money(Decimal("100"), "USD")
eur = Money(Decimal("100"), "EUR")
usd.add(eur)  # Raises CurrencyMismatchError
```

**Implementation:**
```python
def add(self, other: Money) -> Money:
    if self.currency != other.currency:
        raise CurrencyMismatchError(
            f"Cannot add {self.currency} and {other.currency}"
        )
    return Money(self.amount + other.amount, self.currency)
```

#### MR-3: Valid Currency Code
**Rule:** Currency must be a valid ISO 4217 code.

**Rationale:** Standardization and future multi-currency support.

**Enforcement:** Value object validation.

```python
# Valid codes (examples)
VALID_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", ...}

def __post_init__(self) -> None:
    if self.currency not in VALID_CURRENCIES:
        raise InvalidCurrencyError(f"Invalid currency: {self.currency}")
```

---

### Ticker Rules

#### TR-1: Symbol Format
**Rule:** Ticker symbol must be 1-5 uppercase letters.

**Rationale:** Standard stock ticker format (US exchanges).

**Enforcement:** Value object validation with normalization.

```python
# ✅ Valid (auto-normalized to uppercase)
Ticker("AAPL")   # Valid
Ticker("aapl")   # Normalized to "AAPL"
Ticker("GOOGL")  # Valid
Ticker("F")      # Valid (single letter)

# ❌ Invalid
Ticker("")         # Empty → Raises InvalidTickerError
Ticker("TOOLONG")  # More than 5 chars → Raises InvalidTickerError
Ticker("AA123")    # Contains numbers → Raises InvalidTickerError
Ticker("AA-PL")    # Contains symbols → Raises InvalidTickerError
```

**Implementation:**
```python
def __post_init__(self) -> None:
    # Normalize to uppercase
    object.__setattr__(self, 'symbol', self.symbol.upper())
    
    # Validate
    if not self.symbol:
        raise InvalidTickerError("Ticker cannot be empty")
    
    if len(self.symbol) > 5:
        raise InvalidTickerError(f"Ticker too long: {self.symbol}")
    
    if not self.symbol.isalpha():
        raise InvalidTickerError(f"Ticker must be letters only: {self.symbol}")
```

---

### Quantity Rules

#### QR-1: Positive Quantity
**Rule:** Share quantity must be strictly positive (> 0).

**Rationale:** Cannot own zero or negative shares.

**Enforcement:** Value object validation.

```python
# ✅ Valid
Quantity(Decimal("1"))      # Whole share
Quantity(Decimal("0.5"))    # Fractional share
Quantity(Decimal("100.25")) # Valid

# ❌ Invalid
Quantity(Decimal("0"))    # Zero → Raises InvalidQuantityError
Quantity(Decimal("-1"))   # Negative → Raises InvalidQuantityError
```

**Implementation:**
```python
def __post_init__(self) -> None:
    if self.value <= 0:
        raise InvalidQuantityError(
            f"Quantity must be positive, got {self.value}"
        )
```

#### QR-2: Precision Limit
**Rule:** Quantity precision limited to 8 decimal places.

**Rationale:** Brokers typically support up to 8 decimals for fractional shares.

**Enforcement:** Value object validation.

```python
# ✅ Valid
Quantity(Decimal("0.12345678"))  # Max precision

# ❌ Invalid
Quantity(Decimal("0.123456789"))  # Too precise → Raises InvalidQuantityError
```

---

## Entity Rules

### Portfolio Rules

#### PR-1: Non-Empty Name
**Rule:** Portfolio name cannot be empty or whitespace-only.

**Rationale:** Every portfolio needs a meaningful identifier.

**Enforcement:** Entity validation and rename method.

```python
# ✅ Valid
Portfolio(..., name="Growth Portfolio")
Portfolio(..., name="My Stocks")

# ❌ Invalid
Portfolio(..., name="")           # Empty → Raises ValueError
Portfolio(..., name="   ")        # Whitespace → Raises ValueError
```

**Implementation:**
```python
def __post_init__(self) -> None:
    if not self.name or not self.name.strip():
        raise ValueError("Portfolio name cannot be empty")

def rename(self, new_name: str) -> None:
    if not new_name or not new_name.strip():
        raise ValueError("Portfolio name cannot be empty")
    self.name = new_name.strip()
```

#### PR-2: Timezone-Aware Timestamps
**Rule:** All timestamps must be timezone-aware (UTC).

**Rationale:** Prevent timezone confusion and ensure consistency.

**Enforcement:** Entity validation.

```python
# ✅ Valid
from datetime import datetime, UTC
Portfolio(..., created_at=datetime.now(UTC))
Portfolio(..., created_at=datetime(2024, 1, 1, tzinfo=UTC))

# ❌ Invalid
Portfolio(..., created_at=datetime.now())  # Naive → Raises ValueError
Portfolio(..., created_at=datetime(2024, 1, 1))  # Naive → Raises ValueError
```

**Implementation:**
```python
def __post_init__(self) -> None:
    if self.created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware (UTC)")
```

---

### Transaction Rules

#### TR-1: Positive Amount
**Rule:** Transaction amount must be positive.

**Rationale:** Transaction type (DEPOSIT/WITHDRAWAL) determines direction, amount is always magnitude.

**Enforcement:** Entity validation.

```python
# ✅ Valid
Transaction(..., type=DEPOSIT, amount=Money(Decimal("1000"), "USD"))
Transaction(..., type=WITHDRAWAL, amount=Money(Decimal("500"), "USD"))

# ❌ Invalid
Transaction(..., type=DEPOSIT, amount=Money(Decimal("0"), "USD"))  # Zero
Transaction(..., type=DEPOSIT, amount=Money(Decimal("-100"), "USD"))  # Negative
```

**Implementation:**
```python
def __post_init__(self) -> None:
    if self.amount.amount <= 0:
        raise InvalidTransactionError("Amount must be positive")
```

#### TR-2: Trade Transactions Require Ticker
**Rule:** BUY and SELL transactions must have ticker, quantity, and price_per_share.

**Rationale:** Cannot trade without knowing what, how much, and at what price.

**Enforcement:** Entity validation.

```python
# ✅ Valid
Transaction(
    ...,
    type=TransactionType.BUY,
    amount=Money(Decimal("1500"), "USD"),
    ticker=Ticker("AAPL"),
    quantity=Quantity(Decimal("10")),
    price_per_share=Money(Decimal("150"), "USD"),
)

# ❌ Invalid
Transaction(
    ...,
    type=TransactionType.BUY,
    amount=Money(Decimal("1500"), "USD"),
    ticker=None,  # Missing! → Raises InvalidTransactionError
    quantity=Quantity(Decimal("10")),
    price_per_share=Money(Decimal("150"), "USD"),
)
```

**Implementation:**
```python
def __post_init__(self) -> None:
    if self.type in (TransactionType.BUY, TransactionType.SELL):
        if self.ticker is None:
            raise InvalidTransactionError(f"{self.type.value} requires ticker")
        if self.quantity is None:
            raise InvalidTransactionError(f"{self.type.value} requires quantity")
        if self.price_per_share is None:
            raise InvalidTransactionError(f"{self.type.value} requires price_per_share")
```

#### TR-3: Cash Transactions Must Not Have Ticker
**Rule:** DEPOSIT and WITHDRAWAL transactions must NOT have ticker, quantity, or price_per_share.

**Rationale:** Cash transactions don't involve stock trades.

**Enforcement:** Entity validation.

```python
# ✅ Valid
Transaction(
    ...,
    type=TransactionType.DEPOSIT,
    amount=Money(Decimal("1000"), "USD"),
    ticker=None,
    quantity=None,
    price_per_share=None,
)

# ❌ Invalid
Transaction(
    ...,
    type=TransactionType.DEPOSIT,
    amount=Money(Decimal("1000"), "USD"),
    ticker=Ticker("AAPL"),  # Should not have ticker! → Raises InvalidTransactionError
)
```

#### TR-4: Amount Matches Price × Quantity
**Rule:** For trades, `amount == price_per_share × quantity`.

**Rationale:** Mathematical consistency (total cost = price × shares).

**Enforcement:** Entity validation.

```python
# ✅ Valid
Transaction(
    ...,
    type=TransactionType.BUY,
    amount=Money(Decimal("1500"), "USD"),  # 150 × 10 = 1500
    ticker=Ticker("AAPL"),
    quantity=Quantity(Decimal("10")),
    price_per_share=Money(Decimal("150"), "USD"),
)

# ❌ Invalid
Transaction(
    ...,
    type=TransactionType.BUY,
    amount=Money(Decimal("1000"), "USD"),  # Wrong! Should be 1500
    ticker=Ticker("AAPL"),
    quantity=Quantity(Decimal("10")),
    price_per_share=Money(Decimal("150"), "USD"),
)  # Raises InvalidTransactionError (amount mismatch)
```

**Implementation:**
```python
def __post_init__(self) -> None:
    if self.type in (TransactionType.BUY, TransactionType.SELL):
        expected_amount = self.price_per_share.multiply(self.quantity.value)
        if self.amount != expected_amount:
            raise InvalidTransactionError(
                f"Amount mismatch: {self.amount} != {expected_amount}"
            )
```

---

## Business Rules (Use Case Level)

These rules are enforced at the **Use Case (Application) layer** before creating transactions.

### BR-1: Sufficient Funds for Withdrawal

**Rule:** Cannot withdraw more cash than currently available.

**Rationale:** Prevent negative cash balance (no overdraft).

**Enforcement:** Use case validation before creating withdrawal transaction.

```python
async def withdraw_cash(
    portfolio_id: UUID,
    amount: Money,
    transaction_repo: TransactionRepository,
    calculator: PortfolioCalculator,
) -> Transaction:
    # Fetch transaction history
    transactions = await transaction_repo.get_by_portfolio(portfolio_id)
    
    # Calculate current cash balance
    current_cash = calculator.calculate_cash_balance(transactions)
    
    # Business rule: Check sufficient funds
    if current_cash < amount:
        raise InsufficientFundsError(
            f"Cannot withdraw {amount}, only {current_cash} available"
        )
    
    # Create withdrawal transaction
    transaction = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        type=TransactionType.WITHDRAWAL,
        amount=amount,
        timestamp=datetime.now(UTC),
    )
    
    await transaction_repo.save(transaction)
    return transaction
```

**Exception:**
```python
class InsufficientFundsError(DomainError):
    """Raised when attempting to withdraw more than available balance."""
    pass
```

---

### BR-2: Sufficient Funds for Buy

**Rule:** Cannot buy shares if cost exceeds available cash.

**Rationale:** Prevent negative cash balance.

**Enforcement:** Use case validation before creating buy transaction.

```python
async def buy_shares(
    portfolio_id: UUID,
    ticker: Ticker,
    quantity: Quantity,
    price_per_share: Money,
    transaction_repo: TransactionRepository,
    calculator: PortfolioCalculator,
) -> Transaction:
    # Calculate total cost
    total_cost = price_per_share.multiply(quantity.value)
    
    # Fetch transaction history
    transactions = await transaction_repo.get_by_portfolio(portfolio_id)
    
    # Calculate current cash balance
    current_cash = calculator.calculate_cash_balance(transactions)
    
    # Business rule: Check sufficient funds
    if current_cash < total_cost:
        raise InsufficientFundsError(
            f"Cannot buy {quantity.value} shares of {ticker.symbol} "
            f"for {total_cost}, only {current_cash} available"
        )
    
    # Create buy transaction
    transaction = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        type=TransactionType.BUY,
        amount=total_cost,
        ticker=ticker,
        quantity=quantity,
        price_per_share=price_per_share,
        timestamp=datetime.now(UTC),
    )
    
    await transaction_repo.save(transaction)
    return transaction
```

---

### BR-3: Sufficient Shares for Sell

**Rule:** Cannot sell more shares than currently owned.

**Rationale:** Cannot short sell in paper trading (no borrowing).

**Enforcement:** Use case validation before creating sell transaction.

```python
async def sell_shares(
    portfolio_id: UUID,
    ticker: Ticker,
    quantity: Quantity,
    price_per_share: Money,
    transaction_repo: TransactionRepository,
    calculator: PortfolioCalculator,
) -> Transaction:
    # Fetch transaction history
    transactions = await transaction_repo.get_by_portfolio(portfolio_id)
    
    # Calculate current holdings
    holdings = calculator.calculate_holdings(transactions)
    
    # Find holding for this ticker
    current_holding = next(
        (h for h in holdings if h.ticker == ticker),
        None
    )
    
    # Business rule: Check sufficient shares
    if current_holding is None or current_holding.quantity < quantity:
        owned = current_holding.quantity if current_holding else Quantity(Decimal("0"))
        raise InsufficientSharesError(
            f"Cannot sell {quantity.value} shares of {ticker.symbol}, "
            f"only {owned.value} owned"
        )
    
    # Calculate proceeds
    total_proceeds = price_per_share.multiply(quantity.value)
    
    # Create sell transaction
    transaction = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        type=TransactionType.SELL,
        amount=total_proceeds,
        ticker=ticker,
        quantity=quantity,
        price_per_share=price_per_share,
        timestamp=datetime.now(UTC),
    )
    
    await transaction_repo.save(transaction)
    return transaction
```

**Exception:**
```python
class InsufficientSharesError(DomainError):
    """Raised when attempting to sell more shares than owned."""
    pass
```

---

### BR-4: No Trading in Archived Portfolios

**Rule:** Cannot execute trades in archived portfolios.

**Rationale:** Archived portfolios are read-only historical records.

**Enforcement:** Use case validation.

```python
async def execute_trade(
    portfolio_id: UUID,
    ...
    portfolio_repo: PortfolioRepository,
) -> Transaction:
    # Fetch portfolio
    portfolio = await portfolio_repo.get(portfolio_id)
    if portfolio is None:
        raise PortfolioNotFoundError(f"Portfolio {portfolio_id} not found")
    
    # Business rule: Check not archived
    if portfolio.archived:
        raise ArchivedPortfolioError(
            f"Cannot execute trades in archived portfolio {portfolio.name}"
        )
    
    # Proceed with trade...
```

**Exception:**
```python
class ArchivedPortfolioError(DomainError):
    """Raised when attempting to modify an archived portfolio."""
    pass
```

---

## Validation Strategy

### Where to Enforce Rules?

| Rule Type | Enforcement Point | Example |
|-----------|-------------------|---------|
| **Value Object Invariants** | `__post_init__` of value object | Money precision, Ticker format |
| **Entity Invariants** | `__post_init__` of entity | Transaction amount > 0 |
| **Business Rules** | Use case before creating entity | Sufficient funds check |
| **Cross-Aggregate Rules** | Domain service | Portfolio-wide constraints |

### Fail Fast Principle

**Validate as early as possible:**

```python
# ✅ Good: Validation at construction
money = Money(Decimal("100.123"), "USD")  # Raises InvalidPrecisionError immediately

# ❌ Bad: Late validation
money = Money(Decimal("100.123"), "USD")  # No error
# ... 100 lines later ...
# money.validate()  # Error here is hard to debug
```

### Explicit vs Implicit Validation

**Explicit (chosen):**
```python
def __post_init__(self) -> None:
    if self.amount <= 0:
        raise InvalidTransactionError("Amount must be positive")
```

**Implicit (not chosen):**
```python
# Use type system or constraints library
amount: Annotated[Decimal, Gt(0)]  # Hard to customize error messages
```

**Rationale:** Explicit validation provides:
- Clear error messages
- Easier debugging
- Full control over validation logic

---

## Domain Exceptions

### Exception Hierarchy

```python
class DomainError(Exception):
    """Base class for all domain errors."""
    pass

# Value Object Errors
class MoneyError(DomainError):
    """Base for Money-related errors."""
    pass

class InvalidPrecisionError(MoneyError):
    """Amount exceeds allowed precision."""
    pass

class CurrencyMismatchError(MoneyError):
    """Arithmetic on different currencies."""
    pass

class InvalidCurrencyError(MoneyError):
    """Invalid currency code."""
    pass

class InvalidTickerError(DomainError):
    """Invalid ticker symbol."""
    pass

class InvalidQuantityError(DomainError):
    """Invalid share quantity."""
    pass

# Entity Errors
class InvalidTransactionError(DomainError):
    """Transaction violates invariants."""
    pass

# Business Rule Errors
class InsufficientFundsError(DomainError):
    """Insufficient cash for operation."""
    pass

class InsufficientSharesError(DomainError):
    """Insufficient shares for sale."""
    pass

class ArchivedPortfolioError(DomainError):
    """Operation not allowed on archived portfolio."""
    pass

class PortfolioNotFoundError(DomainError):
    """Portfolio does not exist."""
    pass
```

### Error Messages

Provide **actionable, user-friendly** error messages:

```python
# ✅ Good: Clear, actionable
raise InsufficientFundsError(
    f"Cannot buy 10 shares of AAPL for $1,500.00. "
    f"Only $1,000.00 available in portfolio."
)

# ❌ Bad: Vague, technical
raise DomainError("Validation failed")
```

---

## Testing Domain Rules

### Unit Tests for Invariants

```python
import pytest

class TestMoneyRules:
    def test_money_precision_validation(self):
        # Valid precision
        Money(Decimal("100.00"), "USD")  # OK
        Money(Decimal("100.5"), "USD")   # OK
        
        # Invalid precision
        with pytest.raises(InvalidPrecisionError):
            Money(Decimal("100.123"), "USD")
    
    def test_currency_mismatch_on_add(self):
        usd = Money(Decimal("100"), "USD")
        eur = Money(Decimal("100"), "EUR")
        
        with pytest.raises(CurrencyMismatchError):
            usd.add(eur)

class TestTickerRules:
    def test_ticker_normalization(self):
        ticker = Ticker("aapl")
        assert ticker.symbol == "AAPL"
    
    def test_ticker_length_validation(self):
        Ticker("F")      # OK (1 char)
        Ticker("AAPL")   # OK (4 chars)
        Ticker("GOOGL")  # OK (5 chars)
        
        with pytest.raises(InvalidTickerError):
            Ticker("")  # Too short
        
        with pytest.raises(InvalidTickerError):
            Ticker("TOOLONG")  # Too long
```

### Unit Tests for Business Rules

```python
class TestBusinessRules:
    @pytest.mark.asyncio
    async def test_cannot_withdraw_more_than_balance(self):
        # Setup
        portfolio_id = uuid4()
        repo = InMemoryTransactionRepository()
        calculator = PortfolioCalculator()
        
        # Deposit $1000
        await repo.save(Transaction(
            ..., type=DEPOSIT, amount=Money(Decimal("1000"), "USD")
        ))
        
        # Try to withdraw $2000 (should fail)
        with pytest.raises(InsufficientFundsError):
            await withdraw_cash(portfolio_id, Money(Decimal("2000"), "USD"), repo, calculator)
    
    @pytest.mark.asyncio
    async def test_cannot_sell_more_shares_than_owned(self):
        # Setup
        portfolio_id = uuid4()
        repo = InMemoryTransactionRepository()
        calculator = PortfolioCalculator()
        
        # Buy 10 shares
        await repo.save(Transaction(
            ..., type=BUY, ticker=Ticker("AAPL"), quantity=Quantity(Decimal("10")), ...
        ))
        
        # Try to sell 20 shares (should fail)
        with pytest.raises(InsufficientSharesError):
            await sell_shares(
                portfolio_id,
                Ticker("AAPL"),
                Quantity(Decimal("20")),
                Money(Decimal("150"), "USD"),
                repo,
                calculator,
            )
```

---

## References

- **[Value Objects](./value-objects.md)**: Detailed value object specifications
- **[Entities](./entities.md)**: Entity definitions and constraints
- **[Services](./services.md)**: Domain services for validation and calculation
- **[Repository Ports](./repository-ports.md)**: Data access for rule validation
