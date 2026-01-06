# Task 060: Phase 3c Analytics - Frontend Charts

**Status**: Not Started
**Depends On**: Tasks 056-059 (Backend complete with API endpoints)
**Blocks**: Task 061 (Backtesting UI)
**Estimated Effort**: 4-5 days

## Objective

Implement portfolio analytics UI with performance charts (line chart), composition pie chart, and performance metrics cards using Recharts.

## Reference Architecture

Full specification: `architecture_plans/phase3-refined/phase3c-analytics.md` (see "Frontend Changes" section)

## Success Criteria

- [ ] Performance line chart with time range selector
- [ ] Portfolio composition pie chart
- [ ] Performance metrics cards (gain/loss, etc.)
- [ ] Responsive design for mobile/desktop
- [ ] Loading and error states
- [ ] Component tests pass
- [ ] E2E tests verify chart rendering
- [ ] All existing tests still pass

## Implementation Details

### 1. API Client Functions

**Location**: `frontend/src/api/analytics.ts` (new file)

```typescript
import { api } from './client';

export interface DataPoint {
  date: string;
  total_value: number;
  cash_balance: number;
  holdings_value: number;
}

export interface PerformanceMetrics {
  starting_value: number;
  ending_value: number;
  absolute_gain: number;
  percentage_gain: number;
  highest_value: number;
  lowest_value: number;
}

export interface PerformanceResponse {
  portfolio_id: string;
  range: string;
  data_points: DataPoint[];
  metrics: PerformanceMetrics | null;
}

export interface CompositionItem {
  ticker: string;
  value: number;
  percentage: number;
  quantity: number | null;
}

export interface CompositionResponse {
  portfolio_id: string;
  total_value: number;
  composition: CompositionItem[];
}

export type TimeRange = '1W' | '1M' | '3M' | '1Y' | 'ALL';

export async function getPerformance(
  portfolioId: string,
  range: TimeRange = '1M'
): Promise<PerformanceResponse> {
  const response = await api.get(`/portfolios/${portfolioId}/performance`, {
    params: { range },
  });
  return response.data;
}

export async function getComposition(
  portfolioId: string
): Promise<CompositionResponse> {
  const response = await api.get(`/portfolios/${portfolioId}/composition`);
  return response.data;
}
```

### 2. React Query Hooks

**Location**: `frontend/src/hooks/useAnalytics.ts` (new file)

```typescript
import { useQuery } from '@tanstack/react-query';
import { getPerformance, getComposition, TimeRange } from '../api/analytics';

export function usePerformance(portfolioId: string, range: TimeRange = '1M') {
  return useQuery({
    queryKey: ['performance', portfolioId, range],
    queryFn: () => getPerformance(portfolioId, range),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!portfolioId,
  });
}

export function useComposition(portfolioId: string) {
  return useQuery({
    queryKey: ['composition', portfolioId],
    queryFn: () => getComposition(portfolioId),
    staleTime: 60 * 1000, // 1 minute (live prices)
    enabled: !!portfolioId,
  });
}
```

### 3. Performance Line Chart Component

**Location**: `frontend/src/components/analytics/PerformanceChart.tsx`

```typescript
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { usePerformance, TimeRange } from '../../hooks/useAnalytics';
import { formatCurrency, formatDate } from '../../utils/formatters';

interface PerformanceChartProps {
  portfolioId: string;
}

const TIME_RANGES: TimeRange[] = ['1W', '1M', '3M', '1Y', 'ALL'];

export function PerformanceChart({ portfolioId }: PerformanceChartProps) {
  const [range, setRange] = useState<TimeRange>('1M');
  const { data, isLoading, error } = usePerformance(portfolioId, range);

  if (isLoading) {
    return <div data-testid="performance-chart-loading">Loading chart...</div>;
  }

  if (error) {
    return (
      <div data-testid="performance-chart-error" className="text-red-500">
        Failed to load performance data
      </div>
    );
  }

  if (!data || data.data_points.length === 0) {
    return (
      <div data-testid="performance-chart-empty">
        No performance data available. Snapshots will be generated daily.
      </div>
    );
  }

  const chartData = data.data_points.map((point) => ({
    date: point.date,
    value: point.total_value,
  }));

  const startValue = data.metrics?.starting_value ?? chartData[0]?.value;

  return (
    <div data-testid="performance-chart">
      {/* Time Range Selector */}
      <div className="flex gap-2 mb-4">
        {TIME_RANGES.map((r) => (
          <button
            key={r}
            data-testid={`range-${r}`}
            className={`px-3 py-1 rounded ${
              range === r ? 'bg-blue-500 text-white' : 'bg-gray-200'
            }`}
            onClick={() => setRange(r)}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tickFormatter={(date) => formatDate(date, 'short')}
          />
          <YAxis
            tickFormatter={(value) => formatCurrency(value, 'compact')}
          />
          <Tooltip
            formatter={(value: number) => [formatCurrency(value), 'Value']}
            labelFormatter={(label) => formatDate(label, 'long')}
          />
          {startValue && (
            <ReferenceLine
              y={startValue}
              stroke="gray"
              strokeDasharray="3 3"
              label="Start"
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### 4. Composition Pie Chart Component

**Location**: `frontend/src/components/analytics/CompositionChart.tsx`

```typescript
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useComposition } from '../../hooks/useAnalytics';
import { formatCurrency } from '../../utils/formatters';

interface CompositionChartProps {
  portfolioId: string;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6b7280'];

export function CompositionChart({ portfolioId }: CompositionChartProps) {
  const { data, isLoading, error } = useComposition(portfolioId);

  if (isLoading) {
    return <div data-testid="composition-chart-loading">Loading...</div>;
  }

  if (error) {
    return (
      <div data-testid="composition-chart-error" className="text-red-500">
        Failed to load composition data
      </div>
    );
  }

  if (!data || data.composition.length === 0) {
    return <div data-testid="composition-chart-empty">No holdings data</div>;
  }

  const chartData = data.composition.map((item) => ({
    name: item.ticker,
    value: Number(item.value),
    percentage: item.percentage,
  }));

  return (
    <div data-testid="composition-chart">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={({ name, percentage }) => `${name} (${percentage}%)`}
          >
            {chartData.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => formatCurrency(value)}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### 5. Metrics Cards Component

**Location**: `frontend/src/components/analytics/MetricsCards.tsx`

```typescript
import { usePerformance } from '../../hooks/useAnalytics';
import { formatCurrency, formatPercent } from '../../utils/formatters';
import { cn } from '../../utils/cn';

interface MetricsCardsProps {
  portfolioId: string;
}

export function MetricsCards({ portfolioId }: MetricsCardsProps) {
  const { data, isLoading } = usePerformance(portfolioId, '1M');

  if (isLoading || !data?.metrics) {
    return <div data-testid="metrics-cards-loading">Loading metrics...</div>;
  }

  const { metrics } = data;
  const isPositive = metrics.absolute_gain >= 0;

  const cards = [
    {
      label: 'Total Gain/Loss',
      value: formatCurrency(Math.abs(metrics.absolute_gain)),
      trend: isPositive ? 'up' : 'down',
    },
    {
      label: 'Return',
      value: formatPercent(Math.abs(metrics.percentage_gain)),
      trend: isPositive ? 'up' : 'down',
    },
    {
      label: 'Starting Value',
      value: formatCurrency(metrics.starting_value),
    },
    {
      label: 'Current Value',
      value: formatCurrency(metrics.ending_value),
    },
    {
      label: 'Highest Value',
      value: formatCurrency(metrics.highest_value),
    },
    {
      label: 'Lowest Value',
      value: formatCurrency(metrics.lowest_value),
    },
  ];

  return (
    <div
      data-testid="metrics-cards"
      className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
    >
      {cards.map((card, index) => (
        <div
          key={index}
          className="bg-white rounded-lg shadow p-4"
          data-testid={`metric-${card.label.toLowerCase().replace(/\//g, '-')}`}
        >
          <p className="text-sm text-gray-500">{card.label}</p>
          <p
            className={cn(
              'text-xl font-semibold',
              card.trend === 'up' && 'text-green-600',
              card.trend === 'down' && 'text-red-600'
            )}
          >
            {card.trend === 'down' && '-'}
            {card.value}
          </p>
        </div>
      ))}
    </div>
  );
}
```

### 6. Analytics Page/Tab

**Location**: `frontend/src/pages/PortfolioAnalytics.tsx` or add to existing portfolio detail page

```typescript
import { useParams } from 'react-router-dom';
import { PerformanceChart } from '../components/analytics/PerformanceChart';
import { CompositionChart } from '../components/analytics/CompositionChart';
import { MetricsCards } from '../components/analytics/MetricsCards';

export function PortfolioAnalytics() {
  const { portfolioId } = useParams<{ portfolioId: string }>();

  if (!portfolioId) {
    return <div>Portfolio not found</div>;
  }

  return (
    <div className="space-y-8" data-testid="portfolio-analytics">
      <h2 className="text-2xl font-bold">Portfolio Analytics</h2>

      {/* Metrics Summary */}
      <section>
        <h3 className="text-lg font-semibold mb-4">Performance Summary</h3>
        <MetricsCards portfolioId={portfolioId} />
      </section>

      {/* Performance Chart */}
      <section>
        <h3 className="text-lg font-semibold mb-4">Portfolio Value Over Time</h3>
        <div className="bg-white rounded-lg shadow p-4">
          <PerformanceChart portfolioId={portfolioId} />
        </div>
      </section>

      {/* Composition Chart */}
      <section>
        <h3 className="text-lg font-semibold mb-4">Holdings Composition</h3>
        <div className="bg-white rounded-lg shadow p-4">
          <CompositionChart portfolioId={portfolioId} />
        </div>
      </section>
    </div>
  );
}
```

### 7. Component Tests

**Location**: `frontend/src/components/analytics/__tests__/`

Required tests:
- `PerformanceChart.test.tsx`
  - `renders loading state`
  - `renders error state`
  - `renders empty state when no data`
  - `renders chart with data`
  - `time range buttons work`
- `CompositionChart.test.tsx`
  - `renders loading state`
  - `renders error state`
  - `renders pie chart with holdings`
- `MetricsCards.test.tsx`
  - `renders all metric cards`
  - `shows positive gains in green`
  - `shows negative gains in red`

### 8. E2E Tests

**Location**: `frontend/e2e/analytics.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { clerk, clerkSetup } from '@clerk/testing/playwright';

test.describe('Portfolio Analytics', () => {
  test.beforeAll(async () => {
    await clerkSetup();
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clerk.signIn({
      page,
      signInParams: { strategy: 'email_code', emailAddress: process.env.E2E_CLERK_USER_EMAIL! },
    });
  });

  test('displays analytics page with charts', async ({ page }) => {
    // Navigate to portfolio
    await page.click('[data-testid="portfolio-link"]');
    await page.click('[data-testid="analytics-tab"]');

    // Verify metrics cards
    await expect(page.getByTestId('metrics-cards')).toBeVisible();

    // Verify performance chart
    await expect(page.getByTestId('performance-chart')).toBeVisible();

    // Verify composition chart
    await expect(page.getByTestId('composition-chart')).toBeVisible();
  });

  test('time range selector works', async ({ page }) => {
    await page.goto('/portfolios/test-portfolio-id/analytics');

    // Click different time ranges
    await page.click('[data-testid="range-1W"]');
    await expect(page.getByTestId('performance-chart')).toBeVisible();

    await page.click('[data-testid="range-1Y"]');
    await expect(page.getByTestId('performance-chart')).toBeVisible();
  });
});
```

## Implementation Order

1. Create API client functions
2. Create React Query hooks
3. Implement PerformanceChart component
4. Implement CompositionChart component
5. Implement MetricsCards component
6. Create Analytics page/tab
7. Add route/navigation to analytics
8. Write component tests
9. Write E2E tests
10. Run full test suite

## Commands

```bash
# Run frontend tests
task test:frontend

# Run specific component tests
cd frontend && npm test -- --testPathPattern=analytics

# Run E2E tests
task test:e2e

# Start dev server
task dev:frontend
```

## Notes

- Recharts is already available (used in Phase 2b price charts)
- Use existing formatter utilities from `frontend/src/utils/formatters.ts`
- Add data-testid attributes for E2E testing
- Charts need backend snapshot data - may show empty initially
- Consider adding MSW handlers for component tests
- Follow existing component patterns in `frontend/src/components/`
