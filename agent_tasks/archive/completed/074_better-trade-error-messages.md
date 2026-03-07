# Task 074: Better Trade Error Messages

**Agent**: backend-swe
**Priority**: Medium
**Estimated Effort**: 1-2 hours

## Problem

When a trade fails due to insufficient funds, users get a generic error message:
- "Request failed with status code 400"

This provides no actionable information about why the trade failed or how much more money is needed.

## Requirements

Improve trade execution error handling to provide specific, helpful error messages:

1. **Insufficient Funds Error**
   - Detect when cash balance is too low for purchase
   - Calculate exact shortfall amount
   - Return structured error with details:
     ```json
     {
       "detail": {
         "type": "insufficient_funds",
         "message": "Insufficient funds. You have $1,000.00 but need $1,301.65 for this trade",
         "available": 1000.00,
         "required": 1301.65,
         "shortfall": 301.65
       }
     }
     ```

2. **Invalid Ticker Error**
   - Detect when ticker symbol doesn't exist
   - Return clear message: "Invalid ticker symbol: XYZ"

3. **Invalid Quantity Error**
   - Detect negative or zero quantities
   - Return clear message: "Quantity must be greater than zero"

4. **Market Data Unavailable**
   - Detect when price data can't be fetched
   - Return clear message: "Unable to fetch current price for AAPL. Please try again later."

## Implementation Notes

- Create custom exception classes in domain layer:
  - `InsufficientFundsError(available, required)`
  - `InvalidTickerError(ticker)`
  - `InvalidQuantityError(quantity)`
  - `MarketDataUnavailableError(ticker)`

- Update `ExecuteTradeUseCase` to raise these exceptions

- Add exception handlers in FastAPI adapter to convert to appropriate HTTP responses

- Frontend should display these error messages in the toast/alert

## Testing

- Unit tests for each exception type
- Integration tests for error scenarios:
  - Buy with insufficient funds
  - Buy invalid ticker
  - Buy with 0 or negative quantity
  - Buy when market data unavailable

## Acceptance Criteria

- [ ] Custom domain exceptions created
- [ ] Use case raises specific exceptions
- [ ] FastAPI returns structured error responses
- [ ] Error messages are user-friendly and actionable
- [ ] All error scenarios have test coverage
- [ ] Frontend displays specific error messages correctly

## Related

- Found during manual testing in session 2026-01-07
- Complements UX improvements for trade execution
