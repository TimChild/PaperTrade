# Task 033: Phase 2b - Price History Charts (Frontend)

## Priority

**MEDIUM** - User-facing feature for Phase 2b

## Dependencies

- ⚠️  **BLOCKED** until PR #40 (Task 030 - Trade API fix) is merged
- Requires Task 031 (Historical Price Data backend) to be completed first

## Objective

Add interactive price history charts to the frontend, allowing users to visualize stock price movements over time.

## Context

With historical price data available from the backend (Task 031), we can now display price charts in the UI.

**User Stories**:
- As a user, I want to see a price chart for each stock in my portfolio
- As a user, I want to select different time ranges (1D, 1W, 1M, 3M, 1Y, ALL)
- As a user, I want to see the stock's historical performance before buying

## Requirements

### 1. Chart Library Selection

Evaluate and choose a charting library:
- **Recharts** (recommended): React-friendly, declarative API
- **Chart.js**: Popular, well-documented
- **Lightweight-charts** (TradingView): Professional trading charts
- **Victory**: React-native compatible if mobile is future goal

**Recommendation**: Start with Recharts for simplicity, can upgrade later.

### 2. Price History API Integration

Add API client method:
```typescript
// frontend/src/services/api/prices.ts
export const pricesApi = {
  getPriceHistory: async (
    ticker: string,
    startDate: string,
    endDate: string
  ): Promise<PriceHistory> => {
    const response = await apiClient.get<PriceHistory>(
      `/prices/${ticker}/history`,
      { params: { start: startDate, end: endDate } }
    )
    return response.data
  }
}
```

### 3. Chart Component

Create `PriceChart.tsx`:
```tsx
interface PriceChartProps {
  ticker: string
  timeRange: '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL'
}

export function PriceChart({ ticker, timeRange }: PriceChartProps) {
  const { data, isLoading } = usePriceHistory(ticker, timeRange)
  
  return (
    <div className="price-chart">
      <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      <LineChart data={data} />
      <PriceStats current={data.current} change={data.change} />
    </div>
  )
}
```

### 4. React Query Hook

```typescript
// frontend/src/hooks/usePriceHistory.ts
export function usePriceHistory(ticker: string, range: TimeRange) {
  const { start, end } = getDateRange(range)
  
  return useQuery({
    queryKey: ['priceHistory', ticker, range],
    queryFn: () => pricesApi.getPriceHistory(ticker, start, end),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!ticker
  })
}
```

### 5. UI/UX Features

- Time range selector buttons (1D, 1W, 1M, etc.)
- Loading state with skeleton chart
- Error state with retry button
- Price stats: current price, change %, change amount
- Hover tooltip showing price at specific time
- Color coding: green for gains, red for losses
- Responsive design (mobile-friendly)

### 6. Integration Points

Add charts to:
1. **Portfolio Detail Page**: Chart for each holding
2. **Stock Detail Modal/Page**: Full-screen chart before trading
3. **Trade Form**: Mini chart showing recent price action

## Implementation Plan

### Step 1: Setup Chart Library

```bash
cd frontend
npm install recharts
npm install --save-dev @types/recharts
```

### Step 2: API Integration

1. Add types in `frontend/src/types/prices.ts`:
```typescript
export interface PricePoint {
  timestamp: string
  price: number
}

export interface PriceHistory {
  ticker: string
  prices: PricePoint[]
  source: string
  cached: boolean
}

export type TimeRange = '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL'
```

2. Add API method in `frontend/src/services/api/prices.ts`
3. Create hook in `frontend/src/hooks/usePriceHistory.ts`

### Step 3: Build Chart Component

1. Create `frontend/src/components/PriceChart/`
   - `PriceChart.tsx` - Main component
   - `TimeRangeSelector.tsx` - Button group for ranges
   - `PriceStats.tsx` - Current price, change, %
   - `ChartSkeleton.tsx` - Loading state
   - `types.ts` - Component-specific types
   - `utils.ts` - Helper functions (date formatting, etc.)

### Step 4: Styling

Use Tailwind for styling:
- Chart container with proper aspect ratio
- Responsive breakpoints
- Color scheme matching app theme
- Smooth animations on data load

### Step 5: Testing

- Component tests with MSW mocking price history API
- Test all time ranges
- Test loading and error states
- Test hover interactions
- Visual regression tests (optional)

## Success Criteria

- [ ] Price charts display for all holdings
- [ ] Time range selector works (1D, 1W, 1M, 3M, 1Y, ALL)
- [ ] Chart updates when user switches ranges
- [ ] Loading skeleton displays while fetching
- [ ] Error state shows retry button
- [ ] Hover tooltip shows price at specific time
- [ ] Price stats display current price and change
- [ ] Colors indicate gains (green) vs losses (red)
- [ ] Charts are responsive on mobile
- [ ] All component tests pass

## Example Chart Component

```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export function PriceChart({ ticker, timeRange }: PriceChartProps) {
  const { data, isLoading, error } = usePriceHistory(ticker, timeRange)
  
  if (isLoading) return <ChartSkeleton />
  if (error) return <ChartError onRetry={() => refetch()} />
  if (!data || data.prices.length === 0) return <NoData />
  
  const chartData = formatDataForChart(data.prices)
  const isPositive = data.prices[data.prices.length - 1].price > data.prices[0].price
  
  return (
    <div className="price-chart">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">{ticker}</h3>
        <TimeRangeSelector selected={timeRange} onChange={onRangeChange} />
      </div>
      
      <PriceStats
        currentPrice={data.prices[data.prices.length - 1].price}
        change={calculateChange(data.prices)}
        changePercent={calculateChangePercent(data.prices)}
      />
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis domain={['dataMin', 'dataMax']} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="price"
            stroke={isPositive ? '#10b981' : '#ef4444'}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

## Files to Change

- [ ] `frontend/package.json` - Add recharts dependency
- [ ] `frontend/src/types/prices.ts` - Add PriceHistory types
- [ ] `frontend/src/services/api/prices.ts` - Add getPriceHistory method
- [ ] `frontend/src/hooks/usePriceHistory.ts` - New file
- [ ] `frontend/src/components/PriceChart/` - New directory with components
- [ ] `frontend/src/pages/PortfolioDetail.tsx` - Integrate charts
- [ ] Tests for all new components

## Optional Enhancements

- [ ] Compare multiple stocks on one chart
- [ ] Add volume bars below price chart
- [ ] Add technical indicators (moving averages, RSI, etc.)
- [ ] Export chart as image
- [ ] Full-screen chart mode

## References

- [Recharts Documentation](https://recharts.org/)
- [TanStack Query - useQuery](https://tanstack.com/query/latest/docs/framework/react/reference/useQuery)

---

**Created**: January 1, 2026
**Estimated Time**: 5-6 hours
**Agent**: frontend-swe
