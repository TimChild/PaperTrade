# Fix Frontend Visual & UX Issues

**Date**: January 25, 2026
**Agent**: frontend-swe
**Context**: Several visual and UX issues were identified during a review of the charts and portfolio workflow.

## Objectives
Fix visual regressions in the Charts and ensure empty states are handled gracefully.

## Tasks

### 1. Fix TradingView Chart X-Axis (1M View)
- **Issue**: In 1M view, data is compressed to the right side of the chart. The x-axis domain or scale seems incorrect.
- **Reference**: Screenshot `chart-1m-issue.png` (in `.playwright-mcp/` if available).
- **Requirement**: ensuring the time scale properly fills the available width for the selected range. verify `timeScale.rightOffset` and `fitContent()` usage.

### 2. Improve Chart Empty States (1D View)
- **Issue**: On weekends (e.g., Sunday), 1D view shows "No price data available" blank state.
- **Requirement**: If today has no data (weekend/holiday), the 1D view should either:
    - Show the **last available trading session** (Friday).
    - Or display a more helpful message like "Market Closed - No intraday data for today".
    - Prefer showing the last session if possible, or defaulting to "1W" if 1D is empty? No, better to show the last session or a friendly message.

### 3. Analytics Page UX
- **Issue**: "No performance data available yet" message appears even after backdated trades.
- **Requirement**:
    - Add a "Refresh" button or similar if possible to trigger a re-fetch (though backend snapshot generation might need to run).
    - Improve the empty state copy to explain *when* data appears (e.g., "Performance charts update daily after market close").

### 4. Fix Console Errors
- **Delete Portfolio**: Fix `invalid_quantity` error when deleting a portfolio.
    - Check `PortfolioCard.tsx` or `api/client.ts`. It seems to be sending an invalid value during the delete operation (or maybe fetching balance for a deleted portfolio?).
    - Error: `API error: {type: invalid_quantity, message: Shares must be non-negative, got: -1.0000}`.

## Success Criteria
- [ ] 1M Chart view fills the width correctly.
- [ ] 1D View handles weekends gracefully (no scary errors).
- [ ] Portfolio deletion does not throw console errors.

## References
- `src/components/charts/LightweightPriceChart.tsx`
- `src/services/api/client.ts`
