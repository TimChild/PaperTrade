# Value Objects

## Overview

Value objects are **immutable objects defined by their values**, not their identity. Two `Money` objects with the same amount and currency are considered equal, regardless of when or where they were created.

### Characteristics

| Characteristic | Explanation |
|---------------|-------------|
| **Immutable** | Cannot be changed after creation (use Pydantic frozen BaseModel) |
| **Value Equality** | Equal if all fields match |
| **No Identity** | No unique ID needed |
| **Side-Effect Free** | Operations return new instances |

### Why Value Objects?

Value objects solve "primitive obsession" by wrapping simple types with validation and domain meaning:
- **Type Safety**: Can't accidentally pass wrong values
- **Precision**: Use Decimal for financial calculations
- **Validation**: Invalid states are impossible to construct

---

## Money

### Purpose

Represents a **monetary amount with currency** for financial calculations. Ensures precision and prevents accidental currency mismatches.

### Properties

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `amount` | `Decimal` | The monetary value (max 2 decimal places) | Required |
| `currency` | `str` | ISO 4217 currency code | `"USD"` |

### Invariants

1. **Precision Constraint**: Amount must not exceed 2 decimal places
   - Round or reject values with higher precision

2. **Currency Validation**: Currency must be valid ISO 4217 code
   - Common codes: `"USD"`, `"EUR"`, `"GBP"`, `"JPY"`
   - Reject invalid or empty codes

3. **Sign**: Amount can be positive or zero (negative only for internal calculations)

### Operations

Money must support these operations, all returning new Money instances:

- `add(other: Money) -> Money` - Add two Money values (must have same currency)
- `subtract(other: Money) -> Money` - Subtract Money values (same currency)
- `multiply(factor: Decimal) -> Money` - Scale by a factor
- `divide(divisor: Decimal) -> Money` - Divide by a scalar
- Comparison operators: `<`, `<=`, `>`, `>=`, `==` (same currency only)

### Error Cases

Define custom exceptions for:
- `CurrencyMismatchError` - When operating on different currencies
- `InvalidPrecisionError` - When amount has too many decimal places
- `InvalidCurrencyError` - When currency code is invalid

### Implementation Notes

- Use `Decimal` from Python's decimal module (NEVER use `float`)
- Round results to 2 decimal places after arithmetic operations
- Validate on construction (fail fast principle)
- Implement as Pydantic BaseModel with `frozen=True`

---

## Ticker

### Purpose

Represents a **stock ticker symbol** with validation and normalization. Ensures consistent format across the system.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `symbol` | `str` | Stock ticker symbol (1-5 uppercase letters) |

### Invariants

1. **Length**: 1 to 5 characters

2. **Format**: Uppercase letters only
   - Automatically normalize lowercase input to uppercase

3. **Characters**: Letters only (no numbers or symbols)

### Validation Rules

- Reject empty strings
- Reject symbols longer than 5 characters
- Reject symbols with numbers or special characters
- Auto-normalize to uppercase before validation

### Error Cases

Define custom exception:
- `InvalidTickerError` - When ticker symbol fails validation

### Implementation Notes

- Normalize to uppercase in validator (Pydantic `@field_validator`)
- Implement as Pydantic BaseModel with `frozen=True`
- Consider adding exchange suffix in future (e.g., "AAPL.NASDAQ")

---

## Quantity

### Purpose

Represents a **quantity of shares**, supporting fractional shares for modern brokerages. Ensures quantities are always positive.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `value` | `Decimal` | Number of shares (must be positive, max 8 decimal places) |

### Invariants

1. **Positive**: Quantity must be greater than zero
   - Zero and negative values are invalid

2. **Precision**: Maximum 8 decimal places
   - Precision limit based on typical broker support for fractional shares

### Operations

Quantity must support these operations:

- `add(other: Quantity) -> Quantity` - Add two quantities
- `subtract(other: Quantity) -> Quantity` - Subtract (result must be positive)
- `multiply(factor: Decimal) -> Quantity` - Scale by a factor
- Comparison operators: `<`, `<=`, `>`, `>=`, `==`

### Error Cases

Define custom exception:
- `InvalidQuantityError` - When quantity is zero, negative, or has invalid precision

### Implementation Notes

- Use `Decimal` for precision (never `float`)
- Validate positivity on construction
- Implement as Pydantic BaseModel with `frozen=True`
- Consider different precision limits per asset type in future (stocks vs crypto)

---

## Design Rationale

### Why Use Pydantic BaseModel?

For all value objects, we use **Pydantic BaseModel** instead of dataclasses because:

1. **Built-in Validation**: Pydantic automatically validates field types and constraints
2. **Field Validators**: Easy to add custom validation with `@field_validator`
3. **JSON Serialization**: Built-in `.model_dump()` and `.model_validate()` for API integration
4. **Immutability**: Supports `frozen=True` like dataclasses
5. **Better Error Messages**: Clear validation errors for API responses

### Why Decimal Instead of Float?

Financial calculations require precision:
- `0.1 + 0.2` with floats = `0.30000000000000004`
- `Decimal("0.1") + Decimal("0.2")` = `Decimal("0.3")`

For money and quantities, we **must** use `Decimal` to avoid rounding errors.

### Why Immutable (Frozen)?

1. **Value Semantics**: Value objects are defined by their values, not identity
2. **Hashable**: Can be used as dictionary keys or in sets
3. **Thread-safe**: No synchronization needed
4. **Prevents Bugs**: Can't accidentally modify a value that's used elsewhere

### Why Validate on Construction?

**Fail Fast Principle**: Invalid states should be impossible to create. Better to catch errors at construction time than during business logic execution.

---

## Testing Guidelines

### Unit Tests Should Cover

For each value object:
1. **Valid Construction**: Creating with valid values
2. **Validation**: All invariants are enforced
3. **Normalization**: Auto-normalization works (e.g., Ticker uppercase)
4. **Operations**: Arithmetic and comparison operations
5. **Error Cases**: Invalid inputs raise appropriate exceptions
6. **Equality**: Value equality works correctly
7. **Immutability**: Cannot be modified after creation

### Example Test Structure

```
test_money.py:
  - test_create_with_valid_amount
  - test_add_same_currency
  - test_add_different_currency_raises_error
  - test_multiply_by_decimal
  - test_precision_validation
  - test_immutability

test_ticker.py:
  - test_normalize_to_uppercase
  - test_reject_empty_symbol
  - test_reject_too_long_symbol
  - test_reject_non_alpha_characters

test_quantity.py:
  - test_create_valid_quantity
  - test_reject_zero
  - test_reject_negative
  - test_precision_validation
```

---

## References

- [Domain Rules](domain-rules.md) - Business rules using value objects
- [Entities](entities.md) - Entities that compose value objects
- [Services](services.md) - Domain services operating on value objects
