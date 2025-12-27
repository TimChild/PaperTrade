# Value Objects

## Overview

Value objects are **immutable objects defined by their values**, not their identity. Two `Money` objects with the same amount and currency are considered equal, regardless of when or where they were created.

### Characteristics

| Characteristic | Explanation | Example |
|---------------|-------------|---------|
| **Immutable** | Cannot be changed after creation | Frozen dataclass |
| **Value Equality** | Equal if all fields match | `Money(10, "USD") == Money(10, "USD")` |
| **No Identity** | No unique ID needed | Not stored in a table with primary key |
| **Side-Effect Free** | Operations return new instances | `a.add(b)` returns new Money |

### Why Value Objects?

```python
# Without value objects (primitive obsession)
def calculate_total(price: float, quantity: float) -> float:
    return price * quantity

# Problems:
calculate_total(10.123456789, 5)  # Precision issues!
calculate_total("invalid", 5)     # Runtime error!
calculate_total(10, -5)           # Negative quantity allowed!

# With value objects
def calculate_total(price: Money, quantity: Quantity) -> Money:
    return price.multiply(quantity.value)

# Benefits:
calculate_total(
    Money(Decimal("10.12"), "USD"),  # Explicit precision
    Quantity(Decimal("5"))            # Type-safe, validated
)
```

---

## Money

### Purpose

Represents a **monetary amount with currency** for financial calculations. Ensures precision and prevents accidental currency mismatches.

### Specification

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    """Immutable monetary value with currency.
    
    Examples:
        >>> price = Money(Decimal("150.00"), "USD")
        >>> total = price.multiply(10)
        >>> total
        Money(amount=Decimal('1500.00'), currency='USD')
    """
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        ...
```

### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| `amount` | `Decimal` | The monetary value | Max 2 decimal places |
| `currency` | `str` | ISO 4217 currency code | Default: "USD" |

### Invariants

1. **Precision Constraint**: Amount must not exceed 2 decimal places
   - ✅ `Money(Decimal("100.00"), "USD")` - Valid
   - ✅ `Money(Decimal("100.5"), "USD")` - Valid (normalized to 100.50)
   - ❌ `Money(Decimal("100.123"), "USD")` - Invalid (too precise)

2. **Currency Validation**: Currency must be valid ISO 4217 code
   - ✅ `"USD"`, `"EUR"`, `"GBP"`, `"JPY"` - Valid
   - ❌ `"INVALID"`, `"usd"` (lowercase), `""` - Invalid

3. **Positive or Zero**: Amount can be positive or zero (negative for internal calculations only)

### Operations

#### Arithmetic Operations

```python
def add(self, other: Money) -> Money:
    """Add two money values.
    
    Args:
        other: Money to add (must have same currency)
        
    Returns:
        New Money with sum of amounts
        
    Raises:
        CurrencyMismatchError: If currencies differ
        
    Examples:
        >>> a = Money(Decimal("10.50"), "USD")
        >>> b = Money(Decimal("5.25"), "USD")
        >>> a.add(b)
        Money(amount=Decimal('15.75'), currency='USD')
    """
    ...

def subtract(self, other: Money) -> Money:
    """Subtract other money from this.
    
    Args:
        other: Money to subtract (must have same currency)
        
    Returns:
        New Money with difference
        
    Raises:
        CurrencyMismatchError: If currencies differ
        
    Examples:
        >>> a = Money(Decimal("10.50"), "USD")
        >>> b = Money(Decimal("5.25"), "USD")
        >>> a.subtract(b)
        Money(amount=Decimal('5.25'), currency='USD')
    """
    ...

def multiply(self, factor: Decimal) -> Money:
    """Multiply money by a scalar factor.
    
    Args:
        factor: Decimal multiplier
        
    Returns:
        New Money with scaled amount (rounded to 2 decimals)
        
    Examples:
        >>> price = Money(Decimal("10.00"), "USD")
        >>> price.multiply(Decimal("1.5"))
        Money(amount=Decimal('15.00'), currency='USD')
    """
    ...

def divide(self, divisor: Decimal) -> Money:
    """Divide money by a scalar.
    
    Args:
        divisor: Decimal divisor (must be non-zero)
        
    Returns:
        New Money with divided amount (rounded to 2 decimals)
        
    Raises:
        ValueError: If divisor is zero
    """
    ...
```

#### Comparison Operations

```python
def __eq__(self, other: object) -> bool:
    """Check equality by value."""
    ...

def __lt__(self, other: Money) -> bool:
    """Less than comparison (same currency only)."""
    ...

def __le__(self, other: Money) -> bool:
    """Less than or equal."""
    ...

def __gt__(self, other: Money) -> bool:
    """Greater than comparison."""
    ...

def __ge__(self, other: Money) -> bool:
    """Greater than or equal."""
    ...
```

### Error Cases

```python
class MoneyError(DomainError):
    """Base class for Money-related errors."""
    pass

class InvalidPrecisionError(MoneyError):
    """Raised when amount has more than 2 decimal places."""
    pass

class CurrencyMismatchError(MoneyError):
    """Raised when operating on different currencies."""
    pass

class InvalidCurrencyError(MoneyError):
    """Raised when currency code is invalid."""
    pass
```

### Usage Examples

```python
# Creating Money
price_per_share = Money(Decimal("150.00"), "USD")
total_investment = Money(Decimal("10000"), "USD")

# Arithmetic
shares_bought = Decimal("10")
cost = price_per_share.multiply(shares_bought)  # $1500.00

remaining_cash = total_investment.subtract(cost)  # $8500.00

# Comparison
if remaining_cash >= Money(Decimal("1000"), "USD"):
    print("Sufficient funds for another trade")

# Error: Currency mismatch
usd = Money(Decimal("100"), "USD")
eur = Money(Decimal("100"), "EUR")
# usd.add(eur)  # Raises CurrencyMismatchError!
```

### Implementation Notes

- Use `Decimal` for precise arithmetic (never `float`)
- Round results to 2 decimal places after operations
- Validate on construction (fail fast)
- Consider supporting currency conversion in future (requires exchange rates)

---

## Ticker

### Purpose

Represents a **stock ticker symbol** with validation and normalization. Ensures consistent format across the system.

### Specification

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Ticker:
    """Stock ticker symbol.
    
    Examples:
        >>> Ticker("AAPL")
        Ticker(symbol='AAPL')
        >>> Ticker("googl")  # Auto-normalized
        Ticker(symbol='GOOGL')
    """
    symbol: str
    
    def __post_init__(self) -> None:
        """Validate and normalize symbol."""
        ...
```

### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| `symbol` | `str` | Stock ticker symbol | 1-5 uppercase letters |

### Invariants

1. **Length**: 1 to 5 characters
   - ✅ `"F"`, `"AAPL"`, `"GOOGL"` - Valid
   - ❌ `""`, `"TOOLONG"` - Invalid

2. **Format**: Uppercase letters only
   - ✅ `"AAPL"`, `"MSFT"` - Valid
   - ❌ `"aapl"` (gets normalized to `"AAPL"`)
   - ❌ `"AA123"`, `"AA-PL"` - Invalid (numbers/symbols)

3. **Normalization**: Always stored in uppercase
   - Input: `"aapl"` → Stored: `"AAPL"`
   - Input: `"GoOgL"` → Stored: `"GOOGL"`

### Validation

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

### Error Cases

```python
class InvalidTickerError(DomainError):
    """Raised when ticker symbol is invalid."""
    pass
```

### Usage Examples

```python
# Creating Tickers
apple = Ticker("AAPL")
google = Ticker("googl")  # Normalized to "GOOGL"

# Use as dictionary keys (hashable)
prices = {
    Ticker("AAPL"): Money(Decimal("150.00"), "USD"),
    Ticker("GOOGL"): Money(Decimal("140.00"), "USD"),
}

# Equality
assert Ticker("AAPL") == Ticker("aapl")  # True (both normalized)

# Error cases
# Ticker("")        # Raises InvalidTickerError (empty)
# Ticker("TOOLONG") # Raises InvalidTickerError (too long)
# Ticker("AA123")   # Raises InvalidTickerError (contains numbers)
```

### Implementation Notes

- Normalize in `__post_init__` before validation
- Use `object.__setattr__` to modify frozen dataclass during init
- Consider adding exchange suffix in future (e.g., "AAPL.NASDAQ")

---

## Quantity

### Purpose

Represents a **quantity of shares**, supporting fractional shares for modern brokerages. Ensures quantities are always positive.

### Specification

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Quantity:
    """Quantity of shares (supports fractional).
    
    Examples:
        >>> Quantity(Decimal("10"))
        Quantity(value=Decimal('10'))
        >>> Quantity(Decimal("0.5"))  # Fractional share
        Quantity(value=Decimal('0.5'))
    """
    value: Decimal
    
    def __post_init__(self) -> None:
        """Validate quantity is positive."""
        ...
```

### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| `value` | `Decimal` | Number of shares | Must be positive, max 8 decimal places |

### Invariants

1. **Positive**: Quantity must be greater than zero
   - ✅ `Quantity(Decimal("1"))` - Valid
   - ✅ `Quantity(Decimal("0.5"))` - Valid (fractional)
   - ❌ `Quantity(Decimal("0"))` - Invalid (zero not allowed)
   - ❌ `Quantity(Decimal("-1"))` - Invalid (negative not allowed)

2. **Precision**: Maximum 8 decimal places (broker-dependent)
   - ✅ `Quantity(Decimal("0.12345678"))` - Valid
   - ❌ `Quantity(Decimal("0.123456789"))` - Invalid (too precise)

### Operations

```python
def add(self, other: Quantity) -> Quantity:
    """Add two quantities.
    
    Examples:
        >>> a = Quantity(Decimal("10"))
        >>> b = Quantity(Decimal("5.5"))
        >>> a.add(b)
        Quantity(value=Decimal('15.5'))
    """
    ...

def subtract(self, other: Quantity) -> Quantity:
    """Subtract quantities.
    
    Raises:
        InvalidQuantityError: If result would be negative
        
    Examples:
        >>> a = Quantity(Decimal("10"))
        >>> b = Quantity(Decimal("5"))
        >>> a.subtract(b)
        Quantity(value=Decimal('5'))
    """
    ...

def multiply(self, factor: Decimal) -> Quantity:
    """Scale quantity by a factor.
    
    Raises:
        InvalidQuantityError: If result would be non-positive
    """
    ...
```

### Comparison

```python
def __eq__(self, other: object) -> bool:
    """Check equality by value."""
    ...

def __lt__(self, other: Quantity) -> bool:
    """Less than comparison."""
    ...

def __le__(self, other: Quantity) -> bool:
    """Less than or equal."""
    ...

def __gt__(self, other: Quantity) -> bool:
    """Greater than comparison."""
    ...

def __ge__(self, other: Quantity) -> bool:
    """Greater than or equal."""
    ...
```

### Error Cases

```python
class InvalidQuantityError(DomainError):
    """Raised when quantity is invalid."""
    pass
```

### Usage Examples

```python
# Creating Quantities
shares = Quantity(Decimal("10"))
fractional = Quantity(Decimal("0.5"))

# Arithmetic
total_shares = shares.add(fractional)  # 10.5 shares

# Comparison
if shares > Quantity(Decimal("5")):
    print("More than 5 shares")

# Use with Money
price_per_share = Money(Decimal("150.00"), "USD")
total_cost = price_per_share.multiply(shares.value)

# Error cases
# Quantity(Decimal("0"))   # Raises InvalidQuantityError (zero)
# Quantity(Decimal("-5"))  # Raises InvalidQuantityError (negative)
```

### Implementation Notes

- Use `Decimal` for precision (never `float`)
- Validate positivity on construction
- Consider max precision based on broker limitations
- Future: Support different precision per asset type (stocks vs crypto)

---

## Testing Value Objects

### Unit Tests

```python
import pytest
from decimal import Decimal
from domain.value_objects import Money, Ticker, Quantity

class TestMoney:
    def test_create_money_with_valid_amount(self):
        money = Money(Decimal("100.50"), "USD")
        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"
    
    def test_add_same_currency(self):
        a = Money(Decimal("10.00"), "USD")
        b = Money(Decimal("5.50"), "USD")
        result = a.add(b)
        assert result == Money(Decimal("15.50"), "USD")
    
    def test_add_different_currency_raises_error(self):
        usd = Money(Decimal("10.00"), "USD")
        eur = Money(Decimal("10.00"), "EUR")
        with pytest.raises(CurrencyMismatchError):
            usd.add(eur)
    
    def test_multiply_by_decimal(self):
        money = Money(Decimal("10.00"), "USD")
        result = money.multiply(Decimal("2.5"))
        assert result == Money(Decimal("25.00"), "USD")

class TestTicker:
    def test_normalize_to_uppercase(self):
        ticker = Ticker("aapl")
        assert ticker.symbol == "AAPL"
    
    def test_reject_empty_symbol(self):
        with pytest.raises(InvalidTickerError):
            Ticker("")
    
    def test_reject_too_long_symbol(self):
        with pytest.raises(InvalidTickerError):
            Ticker("TOOLONG")

class TestQuantity:
    def test_create_valid_quantity(self):
        qty = Quantity(Decimal("10"))
        assert qty.value == Decimal("10")
    
    def test_reject_zero_quantity(self):
        with pytest.raises(InvalidQuantityError):
            Quantity(Decimal("0"))
    
    def test_reject_negative_quantity(self):
        with pytest.raises(InvalidQuantityError):
            Quantity(Decimal("-5"))
```

### Property-Based Tests

```python
from hypothesis import given, assume
from hypothesis.strategies import decimals

@given(decimals(min_value=0, max_value=1_000_000, places=2))
def test_money_addition_commutative(amount: Decimal):
    a = Money(amount, "USD")
    b = Money(amount, "USD")
    assert a.add(b) == b.add(a)

@given(decimals(min_value=0, max_value=1_000_000, places=2))
def test_money_addition_associative(a: Decimal, b: Decimal, c: Decimal):
    ma = Money(a, "USD")
    mb = Money(b, "USD")
    mc = Money(c, "USD")
    assert ma.add(mb).add(mc) == ma.add(mb.add(mc))

@given(decimals(min_value=0.00000001, max_value=1_000_000, places=8))
def test_quantity_always_positive(value: Decimal):
    assume(value > 0)
    qty = Quantity(value)
    assert qty.value > 0
```

---

## Design Rationale

### Why Decimal Instead of Float?

```python
# Float precision issues
>>> 0.1 + 0.2
0.30000000000000004

# Decimal precision
>>> Decimal("0.1") + Decimal("0.2")
Decimal('0.3')
```

For financial calculations, we **must** use `Decimal` to avoid rounding errors that compound over time.

### Why Frozen Dataclasses?

1. **Immutability**: Value objects should never change
2. **Hashable**: Can be used as dictionary keys
3. **Thread-safe**: No synchronization needed
4. **Clear Intent**: Signals "this is a value, not an entity"

### Why Validate on Construction?

**Fail Fast Principle**: Invalid states should be impossible to create.

```python
# Good: Validation on construction
try:
    ticker = Ticker("INVALID123")
except InvalidTickerError:
    # Handle error immediately
    pass

# Bad: Late validation
ticker = Ticker("INVALID123")  # No error yet
# ... 100 lines later ...
# Error when trying to use ticker - hard to debug!
```

---

## References

- **[Domain Rules](./domain-rules.md)**: Business rules using value objects
- **[Entities](./entities.md)**: Entities that compose value objects
- **[Services](./services.md)**: Domain services operating on value objects
