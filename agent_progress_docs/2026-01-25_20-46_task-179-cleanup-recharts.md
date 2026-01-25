# Task 179: Clean Up Recharts Price Chart Code

**Date**: 2026-01-25  
**Agent**: frontend-swe  
**Status**: ✅ Complete  
**PR Branch**: copilot/remove-recharts-price-chart

## Objective

Remove redundant Recharts-based price chart implementation and evaluation UI now that we've standardized on TradingView Lightweight Charts as our financial charting solution.

## Changes Made

### Files Deleted (992 lines removed)
1. `frontend/src/components/features/PriceChart/PriceChart.tsx` - Recharts implementation (had XAxis bug with trade markers)
2. `frontend/src/components/features/PriceChart/PriceChart.test.tsx` - Associated tests (505 lines)
3. `frontend/src/components/features/PriceChart/PriceChartWrapper.tsx` - Toggle UI between implementations (82 lines)

### Files Modified
1. **`frontend/src/components/features/PriceChart/index.ts`**
   - Removed exports for `PriceChart` and `PriceChartWrapper`
   - Kept `LightweightPriceChart` and other chart utilities

2. **`frontend/src/pages/PortfolioDetail.tsx`**
   - Changed import from `PriceChartWrapper` to `LightweightPriceChart`
   - Removed wrapper props (`defaultImplementation`, `showToggle`)
   - Direct usage of TradingView implementation

### Files Moved
1. `IMPLEMENTATION_SUMMARY_TASK_178.md` → `docs/IMPLEMENTATION_SUMMARY_TASK_178.md` (archived for reference)

## Technical Details

### Why This Cleanup Was Needed
- PR #178 introduced TradingView Lightweight Charts as an alternative to Recharts
- After evaluation, TradingView was chosen as the standard because:
  - Purpose-built for financial data
  - Native trade marker support (no XAxis bug)
  - Better future-proofing (candlesticks, indicators, annotations)
  - Industry-standard library (273K weekly downloads)

### What Was Preserved
- **Recharts dependency** - Still used for Analytics page pie charts
- **LightweightPriceChart.tsx** - The TradingView implementation
- **All other chart components** - TimeRangeSelector, PriceStats, ChartSkeleton, etc.

## Testing & Validation

### ✅ Frontend Quality Checks
```bash
task quality:frontend
```
- **Tests**: 263 passed, 1 skipped
- **Linting**: Passed (4 pre-existing warnings, unrelated to changes)
- **TypeScript**: No errors

### ✅ Code Review
- No issues found
- Clean deletion with proper index.ts updates

### ✅ Security Check (CodeQL)
- 0 alerts found
- No vulnerabilities introduced

### ✅ Recharts Still Available
```bash
npm list recharts
# zebu-frontend@0.0.0 /path/to/frontend
# └── recharts@3.6.0
```
Still used in:
- `CompositionChart.tsx` (Analytics pie chart)
- `PerformanceChart.tsx` (Analytics performance chart)

## Key Code Changes

### Before (PortfolioDetail.tsx)
```tsx
import { PriceChartWrapper } from '@/components/features/PriceChart'
...
<PriceChartWrapper
  key={holding.ticker}
  ticker={holding.ticker}
  initialTimeRange="1M"
  portfolioId={portfolioId}
  defaultImplementation="lightweight"
  showToggle={true}
/>
```

### After (PortfolioDetail.tsx)
```tsx
import { LightweightPriceChart } from '@/components/features/PriceChart'
...
<LightweightPriceChart
  key={holding.ticker}
  ticker={holding.ticker}
  initialTimeRange="1M"
  portfolioId={portfolioId}
/>
```

## Impact

### User Experience
- ✅ No implementation toggle visible to users
- ✅ Consistent TradingView charts across all portfolios
- ✅ Better trade marker visualization (native support)

### Code Quality
- ✅ Removed 992 lines of redundant code
- ✅ Simplified component hierarchy (no wrapper layer)
- ✅ Single source of truth for price charts

### Bundle Size
- ✅ Slightly reduced (removed duplicate charting code)
- ✅ No impact on Analytics (Recharts still available)

## Lessons Learned

1. **Evaluation UI is important** - The PriceChartWrapper allowed us to compare implementations side-by-side before committing
2. **Clean separation** - Having separate files made the cleanup straightforward
3. **Preserve shared dependencies** - Recharts is used elsewhere, so only removed the price chart implementation

## Success Criteria

All requirements from the problem statement were met:

1. ✅ PriceChart.tsx (Recharts price chart) is deleted
2. ✅ PriceChartWrapper.tsx (toggle UI) is deleted
3. ✅ PortfolioDetail uses LightweightPriceChart directly
4. ✅ No toggle visible to users
5. ✅ Recharts remains installed (used elsewhere)
6. ✅ All tests pass
7. ✅ No TypeScript errors
8. ✅ Price charts work correctly (verified via unit tests)

## Next Steps

This cleanup is complete. Future work:
- All new price chart features should be added to `LightweightPriceChart.tsx`
- Consider adding candlestick view option
- Consider adding technical indicators (moving averages, etc.)

---

**Agent**: frontend-swe  
**Completion Time**: ~30 minutes  
**Lines Changed**: +2 / -992
