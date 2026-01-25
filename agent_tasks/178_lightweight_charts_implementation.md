# Task 178: Implement Price Chart with TradingView Lightweight Charts

## Objective

Create an alternative PriceChart implementation using TradingView's lightweight-charts library as a proof-of-concept. This library is purpose-built for financial data visualization and should handle our use case (price lines with trade markers) more elegantly than Recharts.

## Background

We're currently experiencing issues with Recharts where adding trade markers (via Scatter component) breaks the price line rendering. TradingView's lightweight-charts is:
- Purpose-built for financial charting (used by TradingView, the industry leader)
- Lightweight (~40KB gzipped)
- Has built-in support for markers and annotations
- Actively maintained (273K weekly downloads, updated monthly)
- Extensible via plugin system

## Requirements

### Phase 1: Basic Implementation

1. Install `lightweight-charts` package
2. Create new component `LightweightPriceChart.tsx` alongside existing `PriceChart.tsx`
3. Implement basic price line chart with:
   - Same data source (usePriceHistory hook)
   - Time range selector (1D, 1W, 1M, 3M, 1Y, ALL)
   - Price statistics display (current price, change, % change)
   - Responsive container
   - Dark/light theme support

### Phase 2: Trade Markers

1. Add trade markers using lightweight-charts' built-in marker API
2. Buy markers: Green upward arrow or circle
3. Sell markers: Red downward arrow or circle
4. Markers should show details on hover (price, quantity, date)

### Phase 3: Integration

1. Create feature flag or toggle to switch between Recharts and Lightweight Charts
2. Add to PortfolioDetail page as alternative view
3. Ensure both implementations can coexist

## Technical Specifications

### Installation
```bash
cd frontend && npm install lightweight-charts
```

### Key API Points

```typescript
import { createChart, LineSeries, IChartApi } from 'lightweight-charts';

// Create chart
const chart = createChart(container, {
  width: containerWidth,
  height: 250,
  layout: {
    background: { type: ColorType.Solid, color: 'transparent' },
    textColor: '#999',
  },
  timeScale: {
    timeVisible: true,
  },
});

// Add line series
const lineSeries = chart.addSeries(LineSeries, {
  color: '#2962ff',
  lineWidth: 2,
});

// Set data
lineSeries.setData([
  { time: '2026-01-15', value: 297.95 },
  { time: '2026-01-16', value: 305.67 },
  // ...
]);

// Add markers
lineSeries.setMarkers([
  {
    time: '2026-01-15',
    position: 'belowBar',
    color: '#10b981',
    shape: 'arrowUp',
    text: 'BUY 1 @ $297.95',
  },
]);
```

### React Integration

Since lightweight-charts is vanilla JS, wrap it in a React component with proper cleanup:

```typescript
export function LightweightPriceChart({ ticker, portfolioId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    
    const chart = createChart(containerRef.current, options);
    chartRef.current = chart;
    
    return () => {
      chart.remove();
    };
  }, []);

  // Update data when it changes
  useEffect(() => {
    if (!chartRef.current || !data) return;
    // Update series data
  }, [data]);

  return <div ref={containerRef} />;
}
```

### Attribution Requirement

TradingView lightweight-charts requires attribution. Options:
1. Use `attributionLogo` chart option (displays TradingView link on chart)
2. Add link to TradingView somewhere on the page

Choose option 1 (attributionLogo) for simplicity.

## File Structure

```
frontend/src/components/features/PriceChart/
├── PriceChart.tsx           # Existing Recharts implementation
├── PriceChart.test.tsx      # Existing tests
├── LightweightPriceChart.tsx    # NEW: lightweight-charts implementation
├── LightweightPriceChart.test.tsx # NEW: tests
├── PriceChartWrapper.tsx    # NEW: Wrapper to switch between implementations
├── TimeRangeSelector.tsx    # Existing (reuse)
├── PriceStats.tsx           # Existing (reuse)
├── ChartSkeleton.tsx        # Existing (reuse)
└── ChartError.tsx           # Existing (reuse)
```

## Success Criteria

1. LightweightPriceChart renders price data correctly
2. Time range selector works (1D, 1W, 1M, 3M, 1Y, ALL)
3. Trade markers display correctly at trade positions
4. Chart handles edge cases:
   - No data
   - Loading state
   - Error state
   - No trade markers
   - Multiple trade markers
5. Dark/light theme support
6. Responsive to container size
7. TradingView attribution displayed
8. All tests pass
9. No TypeScript errors or ESLint warnings

## Testing Instructions

1. Navigate to a portfolio with holdings
2. Verify price chart loads with price line
3. Verify time range selector changes displayed data
4. Create a backtest trade within visible range
5. Verify trade marker appears at correct position
6. Switch themes - verify chart adapts
7. Resize browser - verify chart is responsive

## References

- Lightweight Charts Docs: https://tradingview.github.io/lightweight-charts/docs
- Markers API: https://tradingview.github.io/lightweight-charts/docs/api/interfaces/ISeriesApi#setmarkers
- React Integration Guide: https://tradingview.github.io/lightweight-charts/tutorials/react
- GitHub: https://github.com/tradingview/lightweight-charts

## Notes

- This is a parallel implementation to the Recharts fix (Task 177)
- Goal is to evaluate which approach works better for our use case
- Keep implementations independent so we can compare and choose
