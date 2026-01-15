# Task 081: Show Real-Time Stock Prices in Holdings

**Agent**: backend-swe
**Status**: Not Started
**Priority**: Medium-High (UX Improvement)
**Complexity**: Medium
**Estimated Effort**: 2-3 hours
**Created**: 2026-01-08

## Context

Currently, the Holdings table shows "Using average cost (current price unavailable)" with an asterisk for the "Current Price" column. This prevents users from seeing whether their stocks have gone up or down in value.

**Example Issue**:
- User buys 1 AAPL at $260.33
- Stock rises to $275.00
- Holdings table shows: "Current Price: $260.33 *" (average cost)
- User can't see the actual gain/loss

## Objective

Fetch and display real-time current prices for all holdings, showing users accurate market values and gain/loss calculations.

## Requirements

### Backend API
1. **Batch Price Endpoint**
   - Create `GET /api/v1/prices/batch?tickers=AAPL,MSFT,GOOGL`
   - Returns current prices for multiple tickers in single request
   - Reuse existing `MarketDataPort` and `AlphaVantageAdapter`
   - Cache results in Redis with 5-minute TTL

2. **Update Holdings Endpoint**
   - Modify `GET /api/v1/portfolios/{id}/holdings` to include current prices
   - Calculate accurate market values: `quantity * current_price`
   - Calculate accurate gain/loss: `market_value - (quantity * avg_cost)`
   - Fallback: Use average cost if current price unavailable

3. **Response Structure**
```json
{
  "holdings": [
    {
      "ticker": "AAPL",
      "shares": 1,
      "average_cost": 260.33,
      "current_price": 275.00,
      "current_price_source": "live",  // "live" or "average_cost_fallback"
      "market_value": 275.00,
      "gain_loss": 14.67,
      "gain_loss_percent": 5.64
    }
  ]
}
```

### Caching Strategy
- Cache individual ticker prices in Redis: `price:AAPL` → `{"price": 275.00, "timestamp": "..."}`
- TTL: 5 minutes (Alpha Vantage free tier: 5 calls/min, 500/day)
- Batch endpoint checks cache first, only fetches uncached tickers
- If cache miss and API quota exceeded, fall back to average cost

### Frontend Updates (Optional - Can be separate task)
- Remove asterisk and fallback message when live price available
- Add timestamp or indicator for price freshness
- Show "Last updated: X minutes ago"
- Consider adding refresh button

## Implementation Notes

### Existing Infrastructure
- `MarketDataPort` interface already exists
- `AlphaVantageAdapter` already implements real-time price fetching
- Redis already configured and available
- Existing endpoint: `GET /api/v1/prices/{ticker}` (single ticker)

### Alpha Vantage API
- Free tier limits: 5 requests/min, 500/day
- Use `GLOBAL_QUOTE` function for current prices
- API key already configured in environment

### Files to Modify

**Backend**:
- `backend/src/zebu/application/queries/get_holdings.py` - Add current price fetching
- `backend/src/zebu/adapters/inbound/api/routes/prices.py` - Add batch endpoint
- `backend/src/zebu/adapters/outbound/cache/redis_cache.py` - Price caching logic
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` - Batch price support

**Frontend** (if included):
- `frontend/src/components/features/portfolio/HoldingsTable.tsx` - Display live prices
- `frontend/src/hooks/usePortfolio.ts` - Handle new response structure

## Testing Requirements

### Unit Tests
1. Test batch price endpoint with multiple tickers
2. Test cache hit/miss scenarios
3. Test fallback to average cost when API unavailable
4. Test gain/loss calculations with live prices

### Integration Tests
1. Test full flow: API → cache → response
2. Test quota exhaustion fallback
3. Test cache expiration and refresh

### Manual Testing
1. View portfolio with holdings - should show live prices
2. Wait 5 minutes - prices should refresh
3. Simulate API failure - should fall back gracefully
4. Check different portfolios - should handle multiple tickers

## Success Criteria

- [ ] Batch price endpoint returns current prices for multiple tickers
- [ ] Holdings endpoint includes live current prices when available
- [ ] Prices cached in Redis with 5-minute TTL
- [ ] Falls back to average cost when API unavailable
- [ ] Gain/loss calculated with live prices
- [ ] Frontend displays current prices without asterisk (if frontend updated)
- [ ] All unit and integration tests pass
- [ ] No performance degradation (batch requests should be fast)

## Dependencies

- Alpha Vantage API key (already configured)
- Redis (already running)
- Existing `MarketDataPort` and `AlphaVantageAdapter`

## Related

- BACKLOG: "Show Real-Time Stock Prices in Holdings"
- Task 075: Auto-populate price field (similar price fetching pattern)
- Task 077: Fix total value calculation (may benefit from accurate market values)

## Notes

- Consider rate limiting to avoid hitting Alpha Vantage API limits
- May want to add admin endpoint to manually refresh all cached prices
- Future enhancement: WebSocket for real-time price updates
- Future enhancement: Support multiple market data providers for redundancy
