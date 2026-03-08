# Task 080: Display Structured Error Messages in Frontend

**Agent**: frontend-swe
**Status**: Not Started
**Priority**: High
**Complexity**: Medium
**Created**: 2026-01-08

## Context

PR #91 added structured error responses on the backend for trade failures (insufficient funds, insufficient shares, invalid ticker, etc.). The backend now returns detailed error objects with specific data:

```json
{
  "detail": {
    "type": "insufficient_funds",
    "message": "Insufficient funds. You have $739.67 but need $1,301.65. Shortfall: $561.98",
    "available": 739.67,
    "required": 1301.65,
    "shortfall": 561.98
  }
}
```

However, the frontend is still displaying generic error messages like "Failed to execute trade: Request failed with status code 400" instead of parsing and displaying these structured errors.

## Objective

Update the frontend to parse and display the structured error responses from the backend, providing users with clear, actionable error messages.

## Requirements

### Error Display
1. Parse structured `error.response.data.detail` objects from API errors
2. Display user-friendly messages based on error type
3. For insufficient funds/shares errors, show specific amounts:
   - Available amount
   - Required amount
   - Shortfall amount
4. Handle both structured (object) and simple (string) error formats for backward compatibility

### Error Types to Handle
- `insufficient_funds`: Show cash amounts
- `insufficient_shares`: Show share quantities and ticker
- `invalid_ticker`: Show ticker validation message
- `invalid_quantity`: Show quantity validation message
- `market_data_unavailable`: Show market data error
- Generic errors: Fall back to error message or status code

### Components to Update
- `frontend/src/components/features/portfolio/TradeForm.tsx` - Main trade form error display
- `frontend/src/pages/PortfolioDetail.tsx` - Error handling in trade submission
- Consider creating a reusable error display utility/component

### User Experience
- Error messages should be clear and actionable
- For insufficient funds: "Insufficient funds. You have $X but need $Y (shortfall: $Z)"
- For insufficient shares: "Insufficient shares. You have X shares of TICKER but need Y (shortfall: Z)"
- For other errors: Display the backend message directly

## Implementation Notes

### Current Error Handling
The frontend currently catches errors and displays generic messages:
```typescript
catch (error) {
  console.error('[TradeSubmit Error]', error);
  alert(`Failed to execute trade: ${error.message || 'Unknown error'}`);
}
```

### Proposed Approach
1. Create a utility function to format structured errors:
```typescript
function formatTradeError(error: AxiosError): string {
  const detail = error.response?.data?.detail;

  if (typeof detail === 'object' && detail.type) {
    switch (detail.type) {
      case 'insufficient_funds':
        return `Insufficient funds. You have $${detail.available.toFixed(2)} but need $${detail.required.toFixed(2)} (shortfall: $${detail.shortfall.toFixed(2)})`;
      case 'insufficient_shares':
        return `Insufficient shares. You have ${detail.available} shares of ${detail.ticker} but need ${detail.required} (shortfall: ${detail.shortfall})`;
      // ... other cases
      default:
        return detail.message || 'Unknown error';
    }
  }

  // Fallback for non-structured errors
  return error.response?.data?.detail || error.message || 'Unknown error';
}
```

2. Update error handlers to use the formatter
3. Replace `alert()` with proper UI error display (toast, inline message, etc.)

## Testing Requirements

### Manual Testing
1. Trigger insufficient funds error (buy more stock than cash available)
2. Trigger insufficient shares error (sell more shares than owned)
3. Trigger invalid ticker error (use non-existent ticker)
4. Verify error messages show specific amounts/details

### Unit Tests
1. Test `formatTradeError` with various structured error responses
2. Test fallback behavior for simple string errors
3. Test handling of missing/malformed error responses

## Validation

Backend verification (already complete):
```bash
# Backend returns structured errors
curl -X POST "http://localhost:8000/api/v1/portfolios/{id}/trades" \
  -H "Content-Type: application/json" \
  -d '{"action": "BUY", "ticker": "AAPL", "quantity": "5"}'
# Returns: {"detail": {"type": "insufficient_funds", ...}}
```

Frontend verification:
- [ ] Error messages show specific dollar amounts for insufficient funds
- [ ] Error messages show specific share quantities for insufficient shares
- [ ] Error messages display ticker symbols for invalid tickers
- [ ] Generic errors fall back to displaying the error message
- [ ] No console errors or warnings

## Related

- PR #91: Backend structured error responses (merged)
- Task 074: Better trade error messages (backend only - completed)
- Consider improving error UI beyond simple alerts (separate task)

## Notes

- This is a frontend-only task, no backend changes needed
- PR #91 already added comprehensive backend tests for structured errors
- Focus on parsing and displaying the errors correctly
- Consider using a toast library instead of `alert()` for better UX
