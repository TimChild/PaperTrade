# Task 074: Better Trade Error Messages

**Agent**: backend-swe  
**Session**: 20260108_034630  
**Status**: ✅ Complete  
**Branch**: copilot/improve-trade-error-handling

## Problem Statement

When trades failed (e.g., due to insufficient funds), users received generic error messages like "Request failed with status code 400" with no actionable information about:
- Why the trade failed
- How much money they have vs. need
- How many shares they have vs. need
- What specific validation failed

This made it difficult for users to understand and fix their trading errors.

## Solution Overview

Implemented structured error responses with detailed, actionable information for all trade failure scenarios:

1. **Enhanced Domain Exceptions** - Added structured data to exceptions
2. **Updated Use Cases** - Modified handlers to provide detailed error info
3. **Structured API Responses** - FastAPI returns JSON with type, message, and amounts
4. **Comprehensive Testing** - Unit and integration tests for all error scenarios

## Technical Implementation

### 1. Enhanced Domain Exceptions

**InsufficientFundsError** - Now includes:
```python
class InsufficientFundsError(BusinessRuleViolationError):
    def __init__(
        self,
        available: Money,  # Current balance
        required: Money,   # Amount needed
        message: str | None = None,
    ) -> None:
        # Auto-calculates shortfall and generates user-friendly message
```

**InsufficientSharesError** - Now includes:
```python
class InsufficientSharesError(BusinessRuleViolationError):
    def __init__(
        self,
        ticker: str,       # Stock symbol
        available: Quantity,  # Shares owned
        required: Quantity,   # Shares needed
        message: str | None = None,
    ) -> None:
        # Auto-calculates shortfall and generates user-friendly message
```

### 2. Updated Use Cases

**BuyStockHandler**:
```python
# Before
raise InsufficientFundsError(
    f"Cannot buy {quantity.shares} shares of {ticker.symbol} "
    f"for {total_cost} - current balance is {current_balance}"
)

# After
raise InsufficientFundsError(
    available=current_balance,
    required=total_cost,
)
```

**SellStockHandler**:
```python
# Before
raise InsufficientSharesError(
    f"Cannot sell {quantity.shares} shares of {ticker.symbol} "
    f"- only {owned_quantity} shares owned"
)

# After
raise InsufficientSharesError(
    ticker=ticker.symbol,
    available=owned_quantity,
    required=quantity,
)
```

**WithdrawCashHandler** - Similar updates for consistency.

### 3. Structured API Error Responses

**FastAPI Exception Handlers** - Return structured JSON:

```python
@app.exception_handler(InsufficientFundsError)
async def handle_insufficient_funds(request: Request, exc: InsufficientFundsError):
    shortfall = exc.required.subtract(exc.available)
    return JSONResponse(
        status_code=400,
        content={
            "detail": {
                "type": "insufficient_funds",
                "message": exc.message,
                "available": float(exc.available.amount),
                "required": float(exc.required.amount),
                "shortfall": float(shortfall.amount),
            }
        }
    )
```

**Error Response Examples**:

Insufficient Funds:
```json
{
  "detail": {
    "type": "insufficient_funds",
    "message": "Insufficient funds. You have $1,000.00 but need $1,500.00 for this trade (shortfall: $500.00)",
    "available": 1000.00,
    "required": 1500.00,
    "shortfall": 500.00
  }
}
```

Insufficient Shares:
```json
{
  "detail": {
    "type": "insufficient_shares",
    "message": "Insufficient shares of AAPL. You have 10 shares but need 20 shares (shortfall: 10)",
    "ticker": "AAPL",
    "available": 10.0,
    "required": 20.0,
    "shortfall": 10.0
  }
}
```

Invalid Ticker:
```json
{
  "detail": {
    "type": "ticker_not_found",
    "message": "Invalid ticker symbol: XYZ",
    "ticker": "XYZ"
  }
}
```

Market Data Unavailable:
```json
{
  "detail": {
    "type": "market_data_unavailable",
    "message": "Unable to fetch market data. Please try again later.",
    "reason": "API rate limit exceeded"
  }
}
```

### 4. Testing

**Unit Tests** (13 new tests in `test_enhanced_exceptions.py`):
- Exception creation with Money/Quantity objects
- Auto-generated error messages
- Custom error messages
- Shortfall calculation
- Currency/type validation
- Error handling for invalid inputs

**Integration Tests** (4 updated tests in `test_error_handling.py`):
- Buy with insufficient funds → structured 400 response
- Sell without owning shares → structured 400 response
- Sell more shares than owned → structured 400 response
- Withdraw more than balance → structured 400 response
- Invalid ticker → structured 404 response

**Test Results**:
- ✅ 514 tests passed
- ✅ 4 tests skipped (scheduler tests)
- ✅ 82% code coverage
- ✅ 100% coverage on domain exceptions

## Files Modified

### Core Changes
1. `backend/src/papertrade/domain/exceptions.py`
   - Enhanced `InsufficientFundsError` with structured data
   - Enhanced `InsufficientSharesError` with structured data

2. `backend/src/papertrade/adapters/inbound/api/error_handlers.py`
   - Updated exception handlers to return structured JSON
   - Added handlers for all domain/application exceptions

3. `backend/src/papertrade/adapters/inbound/api/portfolios.py`
   - Updated market data error handling to use structured format

### Use Case Updates
4. `backend/src/papertrade/application/commands/buy_stock.py`
   - Updated to use new exception signature

5. `backend/src/papertrade/application/commands/sell_stock.py`
   - Updated to use new exception signature

6. `backend/src/papertrade/application/commands/withdraw_cash.py`
   - Updated to use new exception signature

### Test Updates
7. `backend/tests/unit/domain/test_enhanced_exceptions.py` (NEW)
   - 13 comprehensive tests for enhanced exceptions

8. `backend/tests/unit/domain/test_exceptions.py`
   - Updated for new exception signatures

9. `backend/tests/integration/test_error_handling.py`
   - Updated to verify structured error responses

10. `backend/tests/unit/application/commands/test_withdraw_cash.py`
    - Updated for new error message format

## Quality Assurance

### Linting & Type Checking
```bash
✅ Ruff formatting: 142 files formatted
✅ Ruff linting: All checks passed
✅ Pyright: 0 errors, 0 warnings, 0 informations
```

### Testing
```bash
✅ Unit tests: All passed
✅ Integration tests: All passed
✅ Total: 514 passed, 4 skipped
✅ Coverage: 82% overall, 100% domain exceptions
```

### CI/CD
- All pre-commit hooks passed
- Code follows Clean Architecture principles
- Type hints complete with forward references
- Documentation updated

## User Impact

**Before**:
- Generic error: "Request failed with status code 400"
- No information about the failure
- Users must guess what went wrong

**After**:
- Specific error type: `insufficient_funds`, `insufficient_shares`, etc.
- Clear message: "You have $1,000.00 but need $1,500.00"
- Actionable data: available, required, shortfall amounts
- Frontend can display rich error UI with exact amounts

## Next Steps

Frontend implementation can now:
1. Parse structured error responses
2. Display specific error types with appropriate icons/colors
3. Show exact amounts (available vs. required)
4. Provide actionable suggestions (e.g., "Deposit $500.00 more")
5. Format currency and share counts appropriately

## Lessons Learned

1. **Type Safety**: Using Money and Quantity value objects in exceptions ensures type safety and prevents errors
2. **Auto-Generation**: Auto-generating user-friendly messages from structured data reduces maintenance
3. **Structured Responses**: Returning JSON objects instead of strings enables rich frontend UX
4. **Backward Compatibility**: Maintaining string message field ensures existing error handling still works
5. **Testing**: Comprehensive tests for both exception creation and API response format ensure reliability

## References

- **Problem Statement**: Task 074 in BACKLOG.md
- **Architecture**: Clean Architecture - domain exceptions, structured errors
- **Testing**: Unit + Integration tests with 100% domain exception coverage
- **Code Style**: Ruff formatting, Pyright strict type checking
