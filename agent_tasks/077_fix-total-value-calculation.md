# Task 077: Fix Total Value Calculation

**Agent**: backend-swe  
**Priority**: High (Critical Bug)  
**Estimated Effort**: 30-60 minutes  

## Problem

On the Dashboard and Portfolio pages, "Total Value" shows the same amount as "Cash Balance", completely ignoring the market value of holdings.

**Example**:
- Portfolio has:
  - Cash: $3,793.97
  - Holdings: 1 AAPL ($260.33) + 2 MSFT ($945.70) = $1,206.03
  - **Expected Total**: $5,000.00
  - **Actual Total**: $3,793.97 (just cash!)

This is a critical bug preventing users from seeing their actual portfolio value.

## Root Cause Investigation

Check these areas:

1. **Portfolio balance calculation** - `/api/v1/portfolios/{id}/balance`
   - Likely returns only cash balance
   - Should return: `cash_balance + sum(holdings.market_value)`

2. **Holdings market value** - May not be calculated or included
   - Check if current prices are fetched
   - Check if `quantity * current_price` is calculated

3. **Frontend display** - Could be displaying wrong field
   - Check if using `cash_balance` instead of `total_value`

## Requirements

1. **Backend API Fix**
   - Ensure `/api/v1/portfolios/{id}/balance` returns correct total value
   - Include both `cash_balance` and `total_value` in response
   - `total_value = cash_balance + sum(holdings[].market_value)`

2. **Ensure Holdings Market Value**
   - Each holding should have `market_value = quantity * current_price`
   - If current price unavailable, use average cost as fallback

3. **Frontend Display**
   - Ensure "Total Value" displays `total_value` field
   - Ensure "Cash Balance" displays `cash_balance` field
   - Both should be distinct values

## Implementation Notes

### Expected API Response Structure

```json
{
  "portfolio_id": "uuid",
  "cash_balance": 3793.97,
  "holdings_value": 1206.03,
  "total_value": 5000.00,
  "updated_at": "2026-01-07T..."
}
```

### Likely Files

**Backend**:
- `backend/src/application/use_cases/get_portfolio_balance.py`
- `backend/src/adapters/inbound/api/routes/portfolios.py`
- `backend/src/domain/entities/portfolio.py`

**Frontend** (if needed):
- `frontend/src/components/Dashboard/PortfolioCard.tsx`
- `frontend/src/components/Portfolio/PortfolioSummary.tsx`

## Testing

1. **Unit Tests**
   - Test portfolio balance calculation with holdings
   - Test portfolio balance with no holdings (should equal cash)
   - Test market value calculation for each holding

2. **Integration Test**
   - Create portfolio with $5,000
   - Buy 1 AAPL @ $260
   - Verify total value = $5,000 (cash $4,740 + holdings $260)

3. **Manual Test**
   - Check dashboard shows correct total value
   - Check portfolio page shows correct total value
   - Verify cash balance and total value are different when holdings exist

## Acceptance Criteria

- [ ] Total Value = Cash + Holdings market value
- [ ] Dashboard displays correct total value for each portfolio
- [ ] Portfolio page displays correct total value
- [ ] Holdings market value is calculated correctly
- [ ] All tests pass
- [ ] Documentation updated (if API contract changed)

## Related

- Found during manual UI testing session (2026-01-07)
- High impact - core functionality broken
- Affects dashboard and portfolio detail pages
- May be related to balance query or holdings aggregation
