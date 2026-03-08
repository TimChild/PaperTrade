# Task 179: Clean Up Recharts Price Chart Code

## Objective

Remove the redundant Recharts-based price chart code and evaluation UI now that we've committed to TradingView Lightweight Charts as our financial charting solution.

## Background

PR #178 added TradingView Lightweight Charts as an alternative to Recharts for displaying price history with trade markers. After evaluation, we've decided to standardize on TradingView because:

1. **Purpose-built**: TradingView is designed for financial data visualization
2. **Trade markers work natively**: No workarounds needed for buy/sell indicators
3. **Future-proof**: Supports candlesticks, technical indicators, annotations
4. **Well-maintained**: 273K weekly downloads, industry-standard library
5. **Lightweight**: ~40KB gzipped

The current codebase has:
- `PriceChart.tsx` - Recharts implementation (has known Scatter/XAxis bug with trade markers)
- `LightweightPriceChart.tsx` - TradingView implementation (working correctly)
- `PriceChartWrapper.tsx` - Toggle between implementations (evaluation UI)
- PortfolioDetail shows the toggle to users

## Requirements

### Remove Evaluation UI

1. **Remove PriceChartWrapper.tsx** - No longer needed
2. **Update PortfolioDetail.tsx** - Use `LightweightPriceChart` directly instead of wrapper
3. **Remove toggle visibility** - Users shouldn't see implementation toggle

### Remove Redundant Recharts Price Chart

1. **Delete PriceChart.tsx** - The Recharts implementation of price history chart
2. **Delete PriceChart.test.tsx** - Associated tests
3. **Update index.ts** - Remove `PriceChart` and `PriceChartWrapper` exports

### Keep Recharts for Other Uses

**DO NOT remove Recharts entirely** - We still use it for:
- Pie charts in Analytics page
- Potentially other non-financial chart types

Only remove the price chart implementation, not the recharts dependency.

## Files to Modify/Delete

### Delete
- `frontend/src/components/features/PriceChart/PriceChart.tsx`
- `frontend/src/components/features/PriceChart/PriceChart.test.tsx`
- `frontend/src/components/features/PriceChart/PriceChartWrapper.tsx`

### Modify
- `frontend/src/components/features/PriceChart/index.ts` - Remove PriceChart and PriceChartWrapper exports
- `frontend/src/pages/PortfolioDetail.tsx` - Import and use `LightweightPriceChart` directly

### Optional Cleanup
- `IMPLEMENTATION_SUMMARY_TASK_178.md` - Can be moved to docs or deleted (implementation notes)

## Success Criteria

1. ✅ `PriceChart.tsx` (Recharts price chart) is deleted
2. ✅ `PriceChartWrapper.tsx` (toggle UI) is deleted
3. ✅ PortfolioDetail uses `LightweightPriceChart` directly
4. ✅ No toggle visible to users
5. ✅ Recharts remains installed (used elsewhere)
6. ✅ All tests pass
7. ✅ No TypeScript errors
8. ✅ Price charts still work correctly in the app

## Testing Instructions

1. Run `task quality:frontend` - All tests pass
2. Navigate to a portfolio with holdings
3. Verify price chart renders (TradingView)
4. Verify NO toggle/switcher is visible
5. Check Analytics page - Pie charts still work

## Notes

- The Recharts price chart had a bug where the Scatter component for trade markers broke the XAxis calculation
- TradingView handles markers natively via `createSeriesMarkers` plugin API
- This cleanup reduces bundle size slightly (removes duplicate charting code)
- Future price chart features should be added to `LightweightPriceChart.tsx`
