# Task 196: Frontend — Stacked Area Chart for Portfolio Composition Over Time

**Agent**: frontend-swe
**Priority**: Medium
**Estimated Effort**: 3-4 hours
**Depends On**: Task 195 (backend snapshot breakdown) must be merged first

## Objective

Add a stacked area chart to the portfolio analytics page showing how portfolio composition changed over time — how much value was in each stock vs cash on each date.

## Context

After Task 195, the performance API response includes a `holdings_breakdown` array in each data point:
```json
{
  "data_points": [
    {
      "date": "2026-01-20",
      "total_value": 10500.0,
      "cash_balance": 2000.0,
      "holdings_value": 8500.0,
      "holdings_breakdown": [
        { "ticker": "AAPL", "quantity": 10, "price_per_share": 250.0, "value": 2500.0 },
        { "ticker": "MSFT", "quantity": 15, "price_per_share": 400.0, "value": 6000.0 }
      ]
    }
  ]
}

```

## Implementation Plan

### 1. Update TypeScript API types

**File**: `frontend/src/services/api/analytics.ts`

Add to the existing types:
```typescript
interface HoldingBreakdown {
  ticker: string
  quantity: number
  price_per_share: number
  value: number
}

// Update existing DataPoint interface
interface DataPoint {
  date: string
  total_value: number
  cash_balance: number
  holdings_value: number
  holdings_breakdown: HoldingBreakdown[]  // NEW
}
```

### 2. Create CompositionOverTimeChart component

**File**: `frontend/src/components/features/analytics/CompositionOverTimeChart.tsx`

Use Recharts `AreaChart` with stacked areas:
- X-axis: dates (same as PerformanceChart)
- Y-axis: dollar values (auto-scaled)
- One area per ticker + one for "Cash"
- Areas are stacked so the top of the stack = total portfolio value
- Cash at the bottom (most stable), stocks stacked on top
- Each ticker gets a distinct color from a predefined palette
- Legend showing ticker names
- Tooltip showing date + all component values

Data transformation:
```typescript
// Transform API data into Recharts-friendly format
// From: [{ date, cash_balance, holdings_breakdown: [{ticker, value}] }]
// To: [{ date, Cash: 2000, AAPL: 2500, MSFT: 6000 }]  (one key per ticker)
```

Handle edge cases:
- Old snapshots with empty `holdings_breakdown` — show just cash + a single "Holdings" area using `holdings_value`
- Tickers that appear/disappear over time (bought/sold) — value is 0 for dates where they don't appear
- Empty data — show "No data" message

### 3. Add to Analytics page

**File**: `frontend/src/pages/PortfolioAnalytics.tsx` (or wherever the analytics page is)

Add the new chart below the existing performance chart. Use a Card wrapper consistent with the existing layout.

### 4. Color palette for tickers

Create a small utility for consistent ticker colors:
```typescript
const TICKER_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
]
const CASH_COLOR = '#6b7280' // gray

function getTickerColor(index: number): string {
  return TICKER_COLORS[index % TICKER_COLORS.length]
}
```

### 5. Tests

- Component renders with data (shows stacked areas)
- Component handles empty breakdown (fallback to aggregate holdings_value)
- Component handles no data (shows empty message)
- Tooltip displays correctly
- Color assignment is consistent

## Key Files
- `frontend/src/services/api/analytics.ts` — types
- `frontend/src/components/features/analytics/CompositionOverTimeChart.tsx` — NEW
- `frontend/src/pages/PortfolioAnalytics.tsx` — integration
- `frontend/src/components/features/analytics/CompositionOverTimeChart.test.tsx` — NEW

## Validation
- All existing frontend tests pass: `npx vitest run --config vitest.config.ts`
- ESLint + TypeScript pass
- New chart renders correctly with mock data in tests
- Handles backward compatibility (old snapshots with no breakdown)

## Design Notes
- Use the same Card/CardHeader/CardContent pattern as PerformanceChart
- Match the existing dark/light theme styling
- The chart should be responsive (use ResponsiveContainer)
- Consider adding a time range selector (can reuse the same pattern as PerformanceChart, or share the same range state if both charts are on the same page)
