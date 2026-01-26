# Task 030: Fix Trade API - Backend Should Fetch Prices

## Priority

**CRITICAL** - This blocks actual trading functionality

## Problem

The trade API currently requires the frontend to provide the stock price when executing trades:

```python
class TradeRequest(BaseModel):
    action: str = Field(..., pattern="^(BUY|SELL)$")
    ticker: str = Field(..., min_length=1, max_length=5)
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    price: Decimal = Field(..., gt=0, decimal_places=2)  # ❌ SHOULD NOT BE REQUIRED
```

**Why this is wrong**:
1. **Security**: Client could manipulate prices to buy/sell at arbitrary values
2. **User Experience**: Frontend has to make an extra API call to get price before trading
3. **Architecture**: Price fetching is a backend concern, not a frontend concern
4. **Race Conditions**: Price could change between frontend fetch and trade execution

**Discovered During**: E2E testing on Jan 1, 2026

## Expected Behavior

Trade endpoint should:
1. Accept only: `action`, `ticker`, `quantity` from client
2. Backend fetches current price using `MarketDataPort`
3. Backend executes trade with fetched price
4. Returns transaction with the actual price used

## Files to Change

### Backend Changes

1. **API Layer** ([backend/src/zebu/adapters/inbound/api/portfolios.py](cci:7://file:///Users/timchild/github/Zebu/backend/src/zebu/adapters/inbound/api/portfolios.py:0:0-0:0))
   - Remove `price` field from `TradeRequest`
   - Update endpoint handler to fetch price before calling command

2. **Application Layer Commands** ([backend/src/zebu/application/commands/](cci:7://file:///Users/timchild/github/Zebu/backend/src/zebu/application/commands/:0:0-0:0))
   - Check if `ExecuteBuyCommand` and `ExecuteSellCommand` expect price
   - If they do, update command handlers to fetch price via `MarketDataPort`
   - If they don't, update API layer to call market data before command

3. **Tests**
   - Update all trade-related tests
   - Add test for price fetching during trade execution
   - Test error handling when price fetch fails

### Frontend Changes (if needed)

1. Check [frontend/src/services/api/types.ts](cci:7://file:///Users/timchild/github/Zebu/frontend/src/services/api/types.ts:0:0-0:0)
   - Remove `price` from `TradeRequest` interface

2. Check components that call `executeTrade`
   - Remove any price-fetching logic before trade execution
   - UI can still display estimated price, but shouldn't send it

## Implementation Approach

### Option A: Fetch in API Layer (Simpler)
```python
@router.post("/{portfolio_id}/trades")
async def execute_trade(
    portfolio_id: UUID,
    request: TradeRequest,  # No price field
    user_id: UUID = Depends(get_user_id),
):
    # Fetch current price
    price_point = await market_data_service.get_current_price(request.ticker)

    # Execute command with fetched price
    if request.action == "BUY":
        command = ExecuteBuyCommand(
            portfolio_id=portfolio_id,
            ticker=request.ticker,
            quantity=request.quantity,
            price=price_point.price
        )
    # ... etc
```

### Option B: Fetch in Command Handler (Better Architecture)
```python
class ExecuteBuyCommandHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepositoryPort,
        market_data: MarketDataPort  # Inject market data
    ):
        self.portfolio_repo = portfolio_repo
        self.market_data = market_data

    async def handle(self, command: ExecuteBuyCommand) -> Transaction:
        # Fetch price inside handler
        price_point = await self.market_data.get_current_price(command.ticker)

        # Use price for trade
        # ...
```

**Recommendation**: Option B (command handler) is cleaner architecture, but Option A (API layer) is faster to implement. Choose based on time constraints.

## Success Criteria

- [ ] Trade API no longer requires `price` parameter
- [ ] Backend fetches price automatically during trade execution
- [ ] All existing tests pass
- [ ] New tests added for price fetching logic
- [ ] E2E test script successfully executes trades
- [ ] Frontend works without sending price (or frontend updated if needed)

## Testing

1. **Unit Tests**: Mock `MarketDataPort` in command handler tests
2. **Integration Tests**: Test with real `AlphaVantageAdapter`
3. **E2E Test**: Run `scripts/quick_e2e_test.sh` - should execute trades successfully

## References

- API Spec: `GET /api/v1/portfolios/{id}/trades` endpoint
- Market Data Port: [backend/src/zebu/application/ports/market_data.py](cci:7://file:///Users/timchild/github/Zebu/backend/src/zebu/application/ports/market_data.py:0:0-0:0)
- Command Handlers: [backend/src/zebu/application/commands/](cci:7://file:///Users/timchild/github/Zebu/backend/src/zebu/application/commands/:0:0-0:0)

## Notes

This is a critical fix that should be done before Phase 2b work begins, as it affects the core trading functionality that Phase 2a was supposed to deliver.

---

**Created**: January 1, 2026
**Estimated Time**: 3-4 hours
**Agent**: backend-swe
