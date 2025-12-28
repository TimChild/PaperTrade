# Domain Rules and Invariants

## Overview

Domain rules are **business constraints** that must always be satisfied. They represent core business logic and ensure the system maintains valid states.

### Types of Rules

| Type | Description | Enforced By |
|------|-------------|-------------|
| **Invariants** | Conditions that must always be true | Entity/value object validation |
| **Preconditions** | Must be true before an operation | Use case validation, services |
| **Postconditions** | Must be true after an operation | Entity methods, use case logic |
| **Business Rules** | Domain-specific constraints | Domain services, use cases |

---

## Value Object Rules

### Money Rules

**MR-1: Precision Constraint**
- All monetary amounts must not exceed 2 decimal places
- Rationale: Standard precision for USD and most fiat currencies
- Enforcement: Pydantic field validator on construction

**MR-2: Currency Consistency**
- Arithmetic operations require matching currencies
- Cannot add/subtract different currencies without conversion
- Enforcement: Check currency in operation methods

**MR-3: Valid Currency Code**
- Currency must be valid ISO 4217 code
- Enforcement: Pydantic validator with allowed currency list

### Ticker Rules

**TR-1: Symbol Format**
- Ticker symbol must be 1-5 uppercase letters only
- Auto-normalize lowercase to uppercase
- Reject empty, too long, or non-alpha symbols
- Enforcement: Pydantic field validator with normalization

### Quantity Rules

**QR-1: Positive Quantity**
- Share quantity must be strictly positive (> 0)
- Zero and negative values are invalid
- Enforcement: Pydantic field validator

**QR-2: Precision Limit**
- Maximum 8 decimal places for fractional shares
- Enforcement: Pydantic field validator

---

## Entity Rules

### Portfolio Rules

**PR-1: Non-Empty Name**
- Portfolio name cannot be empty or whitespace-only
- Enforcement: Pydantic field validator and domain method validation

**PR-2: Valid User Ownership**
- Portfolio must have a valid user_id
- Enforcement: Pydantic field validator (UUID type)

**PR-3: Timezone-Aware Timestamps**
- created_at must be timezone-aware (UTC)
- Enforcement: Pydantic field validator

**PR-4: Equality by ID**
- Two portfolios are equal only if they have the same id
- Enforcement: Implement `__eq__` and `__hash__` based on id

### Transaction Rules

**TR-1: Amount Always Positive**
- All transaction amounts must be positive
- Use transaction type to indicate direction (deposit vs withdrawal)
- Enforcement: Pydantic field validator

**TR-2: Consistent Trade Data**
- For BUY/SELL: `amount == quantity × price_per_share` (allow small rounding)
- Enforcement: Pydantic model validator

**TR-3: Required Fields by Type**
- DEPOSIT/WITHDRAWAL: ticker, quantity, price_per_share must be None
- BUY/SELL: ticker, quantity, price_per_share must be present
- Enforcement: Pydantic model validator

**TR-4: Immutability**
- Transactions cannot be modified after creation
- Use `frozen=True` on Pydantic model
- To "undo", create reverse transaction

**TR-5: Timezone-Aware Timestamps**
- timestamp must be timezone-aware (UTC)
- Enforcement: Pydantic field validator

---

## Business Rules (Use Case Level)

### BR-1: Sufficient Funds for Withdrawal

**Rule:** Cannot withdraw more cash than available in portfolio.

**Validation:**
```
current_cash = calculate_cash_balance(transactions)
if withdrawal_amount > current_cash:
    raise InsufficientFundsError
```

**Where to check:** Before creating WITHDRAWAL transaction

### BR-2: Sufficient Funds for Buy

**Rule:** Cannot buy shares if total cost exceeds available cash.

**Validation:**
```
total_cost = quantity × price_per_share
current_cash = calculate_cash_balance(transactions)
if total_cost > current_cash:
    raise InsufficientFundsError
```

**Where to check:** Before creating BUY transaction

### BR-3: Sufficient Shares for Sell

**Rule:** Cannot sell more shares than currently owned.

**Validation:**
```
holdings = calculate_holdings(transactions)
current_quantity = find_holding(ticker).quantity
if sell_quantity > current_quantity:
    raise InsufficientSharesError
```

**Where to check:** Before creating SELL transaction

**Note:** This prevents short selling (which we don't support yet)

### BR-4: No Trading in Archived Portfolios

**Rule:** Cannot execute trades in archived portfolios.

**Validation:**
```
if portfolio.archived:
    raise PortfolioArchivedError
```

**Where to check:** Before any transaction creation

### BR-5: Positive Transaction Amounts

**Rule:** All trade prices and quantities must be positive.

**Validation:**
```
if price_per_share <= 0 or quantity <= 0:
    raise InvalidTradeError
```

**Where to check:** Use case validation before transaction creation

---

## Validation Strategy

### Where to Enforce Rules?

**Level 1: Value Objects & Entities (Construction)**
- Invariants that must ALWAYS be true
- Examples: Money precision, Ticker format, Portfolio name non-empty
- Use Pydantic validators

**Level 2: Domain Services (Calculations)**
- Multi-entity invariants
- Examples: FIFO cost basis consistency
- Pure function validation

**Level 3: Use Cases (Business Rules)**
- Context-dependent rules
- Examples: Sufficient funds for withdrawal, sufficient shares for sell
- Validate before creating entities/transactions

### Fail Fast Principle

**Invalid states should be impossible to create.**

Good:
```
# Validation at construction
ticker = Ticker("INVALID123")  # Raises InvalidTickerError immediately
```

Bad:
```
# No validation at construction
ticker = Ticker("INVALID123")  # Silently accepts invalid data
# ... 100 lines later ...
# Error when trying to use ticker - hard to debug!
```

### Validation Order

1. **Field-level**: Pydantic field validators (type, format, range)
2. **Model-level**: Pydantic model validators (cross-field consistency)
3. **Business-level**: Use case validation (business rules)

---

## Domain Exceptions

### Exception Hierarchy

Define custom exceptions for domain errors:

```
DomainError (base)
├── ValueObjectError
│   ├── MoneyError
│   │   ├── InvalidPrecisionError
│   │   ├── CurrencyMismatchError
│   │   └── InvalidCurrencyError
│   ├── InvalidTickerError
│   └── InvalidQuantityError
├── EntityError
│   ├── PortfolioError
│   │   ├── InvalidPortfolioNameError
│   │   └── PortfolioArchivedError
│   └── TransactionError
│       ├── InvalidTransactionTypeError
│       └── InconsistentTransactionDataError
└── BusinessRuleError
    ├── InsufficientFundsError
    ├── InsufficientSharesError
    └── InvalidTradeError
```

### Error Messages

**Be specific and actionable:**

Good:
```
raise InsufficientFundsError(
    f"Cannot buy {quantity} shares of {ticker} at ${price}. "
    f"Total cost: ${total_cost}, Available: ${cash_balance}"
)
```

Bad:
```
raise ValueError("Invalid trade")  # Too vague!
```

### Exception Guidelines

1. **Inherit from custom base** (`DomainError`) not generic exceptions
2. **Include context** in error messages (values, constraints)
3. **Raise early** (fail fast at construction/validation)
4. **Don't catch domain exceptions** in domain layer - let them bubble up

---

## Testing Domain Rules

### Test Structure

For each rule, test:
1. **Valid cases**: Rule is satisfied
2. **Invalid cases**: Rule violation raises expected exception
3. **Edge cases**: Boundary values

**Example Test:**
```
test_money_precision_rule:
  - Valid: 2 decimal places → OK
  - Valid: 1 decimal place → OK (normalized)
  - Valid: 0 decimal places → OK (normalized)
  - Invalid: 3 decimal places → InvalidPrecisionError
  - Invalid: 5 decimal places → InvalidPrecisionError

test_sufficient_funds_for_buy:
  - Cash: $1000, Cost: $500 → OK
  - Cash: $1000, Cost: $1000 → OK (exact)
  - Cash: $1000, Cost: $1000.01 → InsufficientFundsError
  - Cash: $1000, Cost: $2000 → InsufficientFundsError
```

### Property-Based Testing

Use Hypothesis for invariants:

```
Property: Money amount always has ≤ 2 decimal places
Property: Ticker symbol always uppercase and 1-5 chars
Property: Transaction amount = quantity × price (for BUY/SELL)
Property: Total shares bought = holdings + shares sold
```

---

## Design Rationale

### Why Validate in Value Objects?

**Benefits:**
- Invalid states impossible to create
- Type system provides guarantees
- Validation logic centralized
- Easier to test and maintain

**Alternative (worse):**
- Validate in use cases every time
- Duplicated validation logic
- Easy to miss edge cases
- Invalid objects can exist temporarily

### Why Use Pydantic?

Pydantic provides:
1. **Automatic validation** on construction
2. **Clear error messages** with field names
3. **Field validators** for custom logic
4. **Model validators** for cross-field validation
5. **JSON serialization** for API integration

Perfect fit for domain objects that need validation.

### Why Separate Domain Exceptions?

**Benefits:**
- Clear semantic meaning
- Easy to handle specific errors
- Domain layer is self-contained
- API layer can map to HTTP status codes

**Example:**
```
try:
    execute_trade(...)
except InsufficientFundsError as e:
    return JSONResponse(status_code=400, content={"error": str(e)})
except DomainError as e:
    return JSONResponse(status_code=422, content={"error": str(e)})
```

---

## References

- [Value Objects](value-objects.md) - Invariants enforced by value objects
- [Entities](entities.md) - Entity-level rules and validation
- [Services](services.md) - Business rule validation in domain services
