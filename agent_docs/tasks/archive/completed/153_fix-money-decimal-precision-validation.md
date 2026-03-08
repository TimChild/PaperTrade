# Task 153: Fix Money Value Object Decimal Precision Validation

**Agent**: backend-swe
**Priority**: High
**Type**: Bug Fix
**Depends On**: Task 151 (cache completeness - merged)
**Blocks**: Price data backfill workflow

## Objective

Fix `InvalidMoneyError` when parsing Alpha Vantage price data by rounding prices to 2 decimal places before creating Money value objects.

## Context

**Discovered During**: Task 151 deployment validation
**Status**: Blocking price data import from Alpha Vantage

**The Bug**:
Alpha Vantage returns stock prices with >2 decimal places (e.g., `123.4567`), but our `Money` value object enforces maximum 2 decimal places. This causes all API fetches to fail.

**Error**:
```
File "/app/src/zebu/domain/value_objects/money.py", line 58, in __post_init__
    raise InvalidMoneyError("Amount must have maximum 2 decimal places")
zebu.domain.exceptions.InvalidMoneyError: Amount must have maximum 2 decimal places
```

**Current Code** (`alpha_vantage_adapter.py:894`):
```python
open_value = Money(Decimal(str(open_str)), "USD")  # Fails if >2 decimals
```

**Why This Happens**:
- Alpha Vantage API returns prices like: `"150.4567"`
- Stock market prices can have fractional cents in some markets
- Our Money domain object enforces 2 decimal precision for USD

## Requirements

### 1. Round Prices to 2 Decimal Places

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

**Method**: `_parse_daily_history_response()` (lines ~890-920)

**Change**:
```python
# Before
open_value = Money(Decimal(str(open_str)), "USD")
high_value = Money(Decimal(str(high_str)), "USD")
low_value = Money(Decimal(str(low_str)), "USD")
close_value = Money(Decimal(str(close_str)), "USD")

# After
from decimal import ROUND_HALF_UP

open_value = Money(
    Decimal(str(open_str)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    "USD"
)
high_value = Money(
    Decimal(str(high_str)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    "USD"
)
low_value = Money(
    Decimal(str(low_str)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    "USD"
)
close_value = Money(
    Decimal(str(close_str)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    "USD"
)
```

**Rationale**:
- Stock prices are quoted to 2 decimal places in practice
- Extra precision from Alpha Vantage isn't meaningful for our use case
- `ROUND_HALF_UP` is standard for financial rounding
- Keeps Money value object validation strict (good domain enforcement)

### 2. Add Helper Method (Optional but Recommended)

Extract rounding logic to reduce duplication:

```python
def _round_to_cents(self, amount_str: str) -> Decimal:
    """Round decimal string to 2 places (cents) for USD prices.

    Args:
        amount_str: String representation of price (e.g., "123.4567")

    Returns:
        Decimal rounded to 2 decimal places using banker's rounding
    """
    return Decimal(str(amount_str)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

# Usage
open_value = Money(self._round_to_cents(open_str), "USD")
high_value = Money(self._round_to_cents(high_str), "USD")
low_value = Money(self._round_to_cents(low_str), "USD")
close_value = Money(self._round_to_cents(close_str), "USD")
```

### 3. Testing

**File**: `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py`

**Add Test**:
```python
async def test_parse_response_rounds_decimal_precision(
    alpha_vantage_adapter: AlphaVantageAdapter,
) -> None:
    """Should round prices with >2 decimals to 2 decimal places."""
    # Arrange
    ticker = Ticker("AAPL")

    # API response with >2 decimal precision
    api_response = {
        "Meta Data": {"2. Symbol": "AAPL"},
        "Time Series (Daily)": {
            "2026-01-17": {
                "1. open": "150.4567",    # 4 decimals
                "2. high": "152.8912",    # 4 decimals
                "3. low": "148.1234",     # 4 decimals
                "4. close": "151.5678",   # 4 decimals
                "5. volume": "1000000",
            },
        },
    }

    # Act
    price_points = alpha_vantage_adapter._parse_daily_history_response(
        api_response, ticker
    )

    # Assert
    assert len(price_points) == 1
    point = price_points[0]

    # Should be rounded to 2 decimals
    assert point.open.amount == Decimal("150.46")   # 150.4567 → 150.46
    assert point.high.amount == Decimal("152.89")   # 152.8912 → 152.89
    assert point.low.amount == Decimal("148.12")    # 148.1234 → 148.12
    assert point.close.amount == Decimal("151.57")  # 151.5678 → 151.57
    assert point.price.amount == Decimal("151.57")  # Same as close
```

### 4. Validation

**After Fix**:
```bash
# Run backfill script
ssh root@192.168.4.112 "docker exec zebu-backend-prod python scripts/backfill_prices.py --days=7"

# Should succeed and show:
# "✓ Got 5-7 price points for AAPL (2026-01-10 to 2026-01-17)"

# Check debug endpoint
curl http://192.168.4.112:8000/api/v1/debug/price-cache/TSLA | jq '.gaps'
# Expected: [] (no gaps)
```

## Success Criteria

1. ✅ Alpha Vantage prices with >2 decimals parsed successfully
2. ✅ Prices rounded to 2 decimal places using `ROUND_HALF_UP`
3. ✅ Test added for decimal precision handling
4. ✅ CI passes (format, lint, type check, tests)
5. ✅ Backfill script completes without errors
6. ✅ Production verification: TSLA and MU show complete data (no gaps)

## Quality Standards

### Code Quality
- ✅ Complete type hints
- ✅ Docstring for helper method (if added)
- ✅ Use `ROUND_HALF_UP` (banker's rounding)
- ✅ Import `ROUND_HALF_UP` from `decimal` module

### Testing
- ✅ Test with >2 decimal precision input
- ✅ Verify rounding behavior (up/down)
- ✅ Existing tests still pass

### Architecture
- ✅ Changes isolated to adapter layer
- ✅ Money value object validation unchanged (still enforces 2 decimals)
- ✅ No domain layer changes

## Out of Scope

- ❌ Changing Money value object to allow >2 decimals (violates domain rules)
- ❌ Storing raw unrounded data (not needed for our use case)
- ❌ Currency-specific decimal handling (USD is always 2 decimals)

## Estimated Effort

- Implementation: 30 minutes
- Testing: 30 minutes
- Validation: 15 minutes
- **Total**: ~1-2 hours

## Notes

- This is a **quick fix** for an immediate blocker
- Rounding is appropriate for stock prices (quoted to 2 decimals)
- Helper method reduces duplication and improves readability
- Consider adding similar rounding for intraday data parsing if needed later
