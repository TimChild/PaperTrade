# Task 193: Frontend UX Improvements

**Agent**: frontend-swe
**Priority**: High
**Estimated Effort**: 3-5 hours

## Objective

Improve the trading UX with two features: verify real-time holdings prices are working properly, and add interactive click-to-trade from price charts.

## Part 1: Verify & Polish Real-Time Holdings Prices (~1-2h)

### Current State

The `HoldingsTable` component (`src/components/features/portfolio/HoldingsTable.tsx`) **already has** substantial real-time price integration:
- Extracts tickers from holdings and calls `useBatchPricesQuery(tickers)` (from `src/hooks/usePriceQuery.ts`)
- Computes market value and gain/loss from real-time prices
- Shows fallback asterisk `*` with "Using average cost" tooltip when prices unavailable
- Backend `GET /api/v1/prices/batch?tickers=AAPL,MSFT` endpoint is fully implemented

### What Needs Verification/Polish

1. **Verify the feature works end-to-end** — confirm batch prices load correctly for a portfolio with holdings. The backlog says users "can't see if their stocks went up or down" which may be a stale backlog item.

2. **Improve error/loading states** — when prices fail to load (rate limiting, weekend), the asterisk fallback is functional but could be more informative. Consider:
   - A loading skeleton/spinner for the price column while batch prices load
   - Better differentiation between "loading" and "unavailable"
   - Periodic refetching (TanStack Query `refetchInterval`) for live price updates while user is viewing

3. **P&L visibility** — the gain/loss column is `hidden md:table-cell` (hidden on mobile). Consider making the most important P&L indicator (like a colored arrow or percentage) visible even on mobile.

4. **Write/update tests** to cover the batch price integration in `HoldingsTable`.

### Key Files
- `src/components/features/portfolio/HoldingsTable.tsx` — main component
- `src/hooks/usePriceQuery.ts` — `useBatchPricesQuery()` hook
- `src/pages/PortfolioDetail.tsx` — parent page

## Part 2: Interactive Click-to-Trade from Charts (~2-3h)

### Problem

Users manually enter ticker and date when they see something interesting on a chart. This creates friction for "what-if" trades and backtesting.

### Solution

Add click handling to price charts that auto-fills the trade form with the clicked ticker and date.

### Implementation Plan

**1. LightweightPriceChart** (`src/components/features/PriceChart/LightweightPriceChart.tsx`):
- Add an `onChartClick?: (data: { ticker: string; date: string; price?: number }) => void` callback prop
- Use the TradingView Lightweight Charts `subscribeClick` API on the chart instance
- Map the clicked time coordinate back to a date and pass the ticker (already a prop)
- Visual feedback on click (e.g., brief highlight or crosshair snap)

**2. PortfolioDetail** (`src/pages/PortfolioDetail.tsx`):
- Already has a pattern for this! The `quickSellState` + `handleQuickSell` + `tradeFormRef` with `scrollIntoView` is used for the "Quick Sell" button in `HoldingsTable`
- Reuse this pattern: pass a click handler to each `LightweightPriceChart` → on click, update trade form initial props → scroll to form
- The click should populate ticker + date and switch to backtest mode (since chart clicks represent historical dates)

**3. TradeForm** (`src/components/features/portfolio/TradeForm.tsx`):
- Already accepts `initialAction`, `initialTicker`, `initialQuantity` props
- Already has `backtestMode` and `backtestDate` state
- May need a new `initialDate` prop to support pre-filling the backtest date
- Uses `key` prop pattern for state reset, so parent just needs to change the key

**4. UX Flow**:
- User clicks a point on any holding's price chart
- Trade form auto-populates: ticker from chart, date from clicked point
- Form switches to backtest mode with the date pre-filled
- Page scrolls to the trade form
- User just enters quantity and submits
- If clicked date is today, normal (non-backtest) mode

### Key Considerations
- Only enable click-to-trade when viewing charts within a portfolio context (not standalone)
- Handle edge cases: clicking on trade markers, clicking outside data range
- Mobile UX: ensure the scroll-to-form works well on mobile viewports

### Validation
- All existing frontend tests pass (`npx vitest run --config vitest.config.ts`)
- New tests for:
  - Chart click callback fires with correct data
  - Trade form populates from chart click
  - Scroll behavior works
  - Edge cases (no data at click point, mobile)
- Manual verification: click a chart point → trade form populates and scrolls into view

## References
- TradingView Lightweight Charts API: https://tradingview.github.io/lightweight-charts/
- Existing quick-sell pattern in `PortfolioDetail.tsx` (line ~29, ~86)
- Backlog items: `BACKLOG.md` - UX Improvements section
