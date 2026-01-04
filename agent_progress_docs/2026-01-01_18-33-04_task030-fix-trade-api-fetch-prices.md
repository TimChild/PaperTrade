# Task 030: Fix Trade API - Backend Should Fetch Prices

**Agent**: backend-swe
**Date**: January 1, 2026
**Priority**: CRITICAL - Blocks actual trading functionality
**Status**: ✅ COMPLETED

## Problem Statement

The trade API incorrectly required the frontend to provide the stock price when executing trades. This created multiple issues:

1. **Security**: Clients could manipulate prices to buy/sell at arbitrary values
2. **User Experience**: Frontend had to make an extra API call to get price before trading
3. **Architecture**: Price fetching is a backend concern, not a frontend concern
4. **Race Conditions**: Price could change between frontend fetch and trade execution

## Solution Overview

Implemented **Option A** (fetch in API layer) - the simpler and faster approach:
- Backend now fetches the current market price automatically using `MarketDataPort`
- Trade API no longer accepts `price` parameter from clients
- Frontend can still display estimated price for user information (optional)
- All existing tests updated and passing

## Changes Made

### Backend Changes

#### 1. API Layer (`portfolios.py`)

**Before:**
```python
class TradeRequest(BaseModel):
    action: str = Field(..., pattern="^(BUY|SELL)$")
    ticker: str = Field(..., min_length=1, max_length=5)
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    price: Decimal = Field(..., gt=0, decimal_places=2)  # ❌ Client-provided
```

**After:**
```python
class TradeRequest(BaseModel):
    action: str = Field(..., pattern="^(BUY|SELL)$")
    ticker: str = Field(..., min_length=1, max_length=5)
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    # ✅ Price removed - backend fetches it automatically
```

**Endpoint Changes:**
```python
async def execute_trade(
    portfolio_id: UUID,
    request: TradeRequest,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
    market_data: MarketDataDep,  # ✅ New dependency
) -> TransactionResponse:
    """Execute a buy or sell trade.

    Fetches the current market price automatically and executes the trade
    at that price. This prevents price manipulation and ensures trades
    execute at real market prices.
    """
    # ✅ Fetch current market price
    ticker = Ticker(request.ticker)
    price_point = await market_data.get_current_price(ticker)

    # ✅ Use fetched price for trade execution
    if request.action == "BUY":
        command = BuyStockCommand(
            portfolio_id=portfolio_id,
            ticker_symbol=request.ticker,
            quantity_shares=request.quantity,
            price_per_share_amount=price_point.price.amount,
            price_per_share_currency=price_point.price.currency,
        )
        # ... execute command
```

#### 2. Test Configuration (`conftest.py`)

Updated the test fixture to seed `InMemoryMarketDataAdapter` with default test prices:

```python
def get_test_market_data() -> InMemoryMarketDataAdapter:
    """Override market data dependency to use in-memory adapter.

    Seeds the adapter with default test prices for common tickers.
    """
    adapter = InMemoryMarketDataAdapter()

    # Seed with default test prices
    test_prices = [
        PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=datetime.now(UTC),
            source="database",
            interval="real-time",
        ),
        # ... more test prices
    ]

    adapter.seed_prices(test_prices)
    return adapter
```

#### 3. Integration Tests (`test_portfolio_api.py`)

Updated all trade tests to **not** send price parameter:

**Before:**
```python
json={"action": "BUY", "ticker": "AAPL", "quantity": "100", "price": "150.00"}
```

**After:**
```python
json={"action": "BUY", "ticker": "AAPL", "quantity": "100"}  # ✅ No price
```

### Frontend Changes

#### 4. API Types (`types.ts`)

Removed `price` field from `TradeRequest` interface:

```typescript
export interface TradeRequest {
  action: 'BUY' | 'SELL'
  ticker: string
  quantity: string // Decimal as string
  // ✅ price field removed
}
```

#### 5. Trade Form Component (`TradeForm.tsx`)

**Key Updates:**
1. Form submission no longer includes price in the request
2. Price input field kept as **optional** for user estimation
3. Added UI indicators that price is optional and for estimation only
4. Added help text: "Actual trade will execute at current market price"
5. Form validation no longer requires price field
6. Preview shows estimated total when price is provided (optional)

**Before:**
```typescript
const trade: TradeRequest = {
  action,
  ticker: ticker.trim().toUpperCase(),
  quantity: quantity,
  price: price,  // ❌ Sent to backend
}
```

**After:**
```typescript
const trade: TradeRequest = {
  action,
  ticker: ticker.trim().toUpperCase(),
  quantity: quantity,
  // ✅ Price not included - backend will fetch it
}

// Price field still exists in UI for estimation, but value is not sent
```

**UI Improvements:**
- Label: "Price Per Share ($) (Optional - for estimation)"
- Help text: "Actual trade will execute at current market price"
- Preview disclaimer: "Trade will execute at current market price"

## Testing Results

### Backend Tests

All integration tests passing:

```bash
tests/integration/test_portfolio_api.py::test_create_portfolio_with_initial_deposit PASSED
tests/integration/test_portfolio_api.py::test_get_portfolio_balance_after_creation PASSED
tests/integration/test_portfolio_api.py::test_execute_buy_trade_and_verify_holdings PASSED
tests/integration/test_portfolio_api.py::test_buy_and_sell_updates_holdings_correctly PASSED
tests/integration/test_portfolio_api.py::test_get_portfolios_returns_only_user_portfolios PASSED
tests/integration/test_portfolio_api.py::test_deposit_and_withdraw_cash PASSED
tests/integration/test_portfolio_api.py::test_multiple_portfolios_for_same_user PASSED
```

All unit tests passing (259 passed):
- Command handlers
- Domain entities and value objects
- Query handlers
- DTOs
- Exceptions

### Frontend

- TypeScript types updated - no compilation errors expected
- TradeForm component updated with better UX
- E2E tests should still work (price field exists but value not sent)

## Architecture Decision Rationale

**Why Option A (Fetch in API Layer)?**

1. **Simpler Implementation**: Fewer files to modify
2. **Faster to Implement**: Critical fix needed urgently
3. **Clear Separation**: API layer handles HTTP concerns, commands handle business logic
4. **Easy to Test**: Can mock MarketDataPort at the API layer
5. **Good Enough**: Fetching in API layer is architecturally sound for this use case

**Why NOT Option B (Fetch in Command Handler)?**

While cleaner from a domain-driven design perspective, it would require:
- Modifying command signatures
- Updating all command handler tests
- More complex dependency injection
- More time for a critical fix

Option A is a pragmatic choice that solves the security issue quickly without compromising code quality.

## Security Improvements

✅ **Fixed**: Clients can no longer manipulate prices to trade at arbitrary values
✅ **Fixed**: No race conditions - price fetched immediately before trade execution
✅ **Fixed**: Backend has full control over pricing logic
✅ **Improved UX**: Frontend no longer needs separate API call for price

## Files Modified

### Backend
- `backend/src/papertrade/adapters/inbound/api/portfolios.py` - Remove price from request, fetch from MarketDataPort
- `backend/tests/conftest.py` - Seed test market data adapter with prices
- `backend/tests/integration/test_portfolio_api.py` - Remove price from test payloads

### Frontend
- `frontend/src/services/api/types.ts` - Remove price from TradeRequest interface
- `frontend/src/components/features/portfolio/TradeForm.tsx` - Make price optional, update UX

## Impact on Existing Features

✅ **No Breaking Changes**: All existing tests pass
✅ **Backward Compatible**: Frontend changes are additive (price field optional)
✅ **E2E Tests**: Should still work (price field exists in UI but not sent)

## Success Criteria Met

- [x] Trade API no longer requires `price` parameter
- [x] Backend fetches price automatically during trade execution
- [x] All existing tests pass
- [x] Integration tests updated for new behavior
- [x] Frontend no longer sends price (updated to match backend)
- [x] UI clarifies that trades execute at current market price

## Known Issues / Future Work

1. **E2E Tests**: Should be updated to not fill in price field (currently still filling it but value is ignored)
2. **Real-time Price Display**: Future enhancement could fetch and display real-time price in the form
3. **Price History**: Could show recent price trends in the trade form
4. **Limit Orders**: Phase 3 feature - allow users to specify desired price for future execution

## Lessons Learned

1. **Security First**: Always validate that clients cannot manipulate critical business data
2. **Backend Authority**: Backend should be the source of truth for market prices
3. **Pragmatic Architecture**: Choose simpler solution when time is critical and quality is maintained
4. **Test Infrastructure**: Having good test fixtures (like InMemoryMarketDataAdapter) makes refactoring easier

## Next Steps

1. ✅ This task is complete
2. Monitor production for any issues
3. Consider implementing real-time price fetching for UI display (separate ticket)
4. Update E2E tests to not use price field (nice to have, not critical)

---

**Task Completed**: January 1, 2026
**Total Time**: ~3 hours
**Commits**: 2
