# Task 207: Frontend — Backtesting & Strategy Comparison UI

## Context

Phase 4 backend (Trading Strategies & Backtesting) is fully implemented and deployed. The backend provides:
- CRUD for strategies (`POST/GET/DELETE /api/v1/strategies`)
- CRUD for backtests (`POST/GET/DELETE /api/v1/backtests`)
- Backtests create portfolios with `portfolio_type=BACKTEST`
- Existing `/api/v1/portfolios/{id}/performance` works for backtest portfolios
- Portfolio filtering: `GET /api/v1/portfolios?include_backtest=true`

**No frontend for strategies or backtests exists yet.** This task builds the complete frontend experience.

## Objective

Build the full backtesting UI: strategy management, backtest execution, results visualization, and — most importantly — **strategy comparison** as the key differentiating feature.

## Priority

**Strategy comparison is the highest-priority UX feature.** The ability to visually compare backtest results side-by-side with normalized % return charts and metrics tables is what will drive demand for this platform. Design every decision with this in mind.

---

## Requirements

### 1. Navigation — Add Top-Level Tabs

The app currently has no persistent navigation (just "Zebu" header + UserButton). Add a simple horizontal nav bar with tabs:

- **Portfolios** → `/dashboard` (existing)
- **Strategies** → `/strategies` (new)
- **Backtests** → `/backtests` (new)

Place this nav inside the authenticated layout in `App.tsx`, below the existing header. Use a simple tab/link bar that highlights the active route. Keep it minimal — match the existing design system (Tailwind, dark mode support).

### 2. API Layer — Types, Services, Hooks

Create the full data layer following existing patterns.

#### 2a. Types (`frontend/src/services/api/types.ts`)

Add these types to the existing types file:

```typescript
// Strategy types
export type StrategyType = 'BUY_AND_HOLD' | 'DOLLAR_COST_AVERAGING' | 'MOVING_AVERAGE_CROSSOVER';

export interface StrategyResponse {
  id: string;
  user_id: string;
  name: string;
  strategy_type: StrategyType;
  tickers: string[];
  parameters: Record<string, unknown>;
  created_at: string;
}

export interface CreateStrategyRequest {
  name: string;
  strategy_type: StrategyType;
  tickers: string[];
  parameters: Record<string, unknown>;
}

// Backtest types
export type BacktestStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface BacktestRunResponse {
  id: string;
  user_id: string;
  strategy_id: string | null;
  portfolio_id: string;
  backtest_name: string;
  start_date: string;
  end_date: string;
  initial_cash: string; // decimal string
  status: BacktestStatus;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  total_return_pct: string | null; // decimal string
  max_drawdown_pct: string | null;
  annualized_return_pct: string | null;
  total_trades: number | null;
}

export interface RunBacktestRequest {
  strategy_id: string;
  backtest_name: string;
  start_date: string; // YYYY-MM-DD
  end_date: string;
  initial_cash: number;
}
```

#### 2b. API Service (`frontend/src/services/api/strategies.ts` and `backtests.ts`)

Follow existing patterns in `portfolios.ts`:

**strategies.ts:**
- `listStrategies(): Promise<StrategyResponse[]>` → GET `/strategies`
- `getStrategy(id: string): Promise<StrategyResponse>` → GET `/strategies/{id}`
- `createStrategy(data: CreateStrategyRequest): Promise<StrategyResponse>` → POST `/strategies`
- `deleteStrategy(id: string): Promise<void>` → DELETE `/strategies/{id}`

**backtests.ts:**
- `listBacktests(): Promise<BacktestRunResponse[]>` → GET `/backtests`
- `getBacktest(id: string): Promise<BacktestRunResponse>` → GET `/backtests/{id}`
- `runBacktest(data: RunBacktestRequest): Promise<BacktestRunResponse>` → POST `/backtests`
- `deleteBacktest(id: string): Promise<void>` → DELETE `/backtests/{id}`

#### 2c. Hooks (`frontend/src/hooks/`)

Follow TanStack Query patterns from existing hooks:

**useStrategies.ts:**
- `useStrategies()` — list all strategies (queryKey: `['strategies']`)
- `useStrategy(id)` — single strategy
- `useCreateStrategy()` — mutation, invalidates `['strategies']` on success
- `useDeleteStrategy()` — mutation, invalidates `['strategies']` on success

**useBacktests.ts:**
- `useBacktests()` — list all backtests (queryKey: `['backtests']`)
- `useBacktest(id)` — single backtest
- `useRunBacktest()` — mutation, invalidates `['backtests']` on success
- `useDeleteBacktest()` — mutation, invalidates `['backtests']` on success

### 3. Strategy Management Page (`/strategies`)

**Route:** `/strategies`
**Page:** `frontend/src/pages/Strategies.tsx`

**Features:**
- List all user's strategies in a card grid or table
- Each card shows: name, strategy type (as badge), tickers, created date
- "Create Strategy" button opens a form (inline or dialog)
- Delete with confirmation dialog

**Create Strategy Form:**
- Name (text input, required)
- Strategy Type (select dropdown: Buy & Hold, Dollar Cost Averaging, Moving Average Crossover)
- Tickers (comma-separated input or multi-input, required)
- Dynamic parameters section based on strategy type:
  - **Buy & Hold**: Allocation per ticker (must sum to ~1.0). Auto-populate inputs based on tickers entered.
  - **DCA**: Frequency days (number), Amount per period (currency), Allocation per ticker
  - **MA Crossover**: Fast window (number, 2-200), Slow window (number, must be > fast), Invest fraction (0-1)
- Client-side validation matching backend constraints
- Show validation errors inline

### 4. Backtests Page (`/backtests`)

**Route:** `/backtests`
**Page:** `frontend/src/pages/Backtests.tsx`

**Features:**
- List all backtests in a table/card layout
- Columns: Name, Strategy Name, Status (badge: green=COMPLETED, yellow=PENDING, red=FAILED), Return %, Dates, Actions
- Status badge coloring: COMPLETED=green, PENDING/RUNNING=yellow, FAILED=red
- "Run Backtest" button opens a form
- Click a completed backtest → navigate to `/backtests/:id`
- Delete with confirmation
- **"Compare" button**: When 2+ completed backtests are selected (checkboxes), show a "Compare Selected" button that navigates to `/compare?ids=id1,id2,...`

**Run Backtest Form:**
- Strategy (select from user's strategies — use `useStrategies()`)
- Backtest Name (text, required)
- Start Date & End Date (date inputs)
- Initial Cash (number input, > 0)
- Validation: end_date ≤ today, end_date > start_date, range ≤ 3 years
- On submit: POST, navigate to backtests list, show toast

### 5. Backtest Results Page (`/backtests/:id`)

**Route:** `/backtests/:id`
**Page:** `frontend/src/pages/BacktestResult.tsx`

**Features:**
- Fetch backtest details via `useBacktest(id)`
- Header: backtest name, strategy name, date range, status badge
- **Metrics cards** (reuse MetricsCards-style layout):
  - Initial Cash
  - Total Return %
  - Annualized Return %
  - Max Drawdown %
  - Total Trades
  - Final Portfolio Value (if available from performance endpoint)
- **Performance chart**: Fetch from `/portfolios/{portfolio_id}/performance` using the backtest's `portfolio_id`. Reuse the existing `PerformanceChart` component or create a variant.
- If status is FAILED, show error message prominently
- If status is PENDING/RUNNING, show a message (backtests complete synchronously on current backend, so this is mainly for UX completeness)
- Link back to backtests list

### 6. Strategy Comparison Page (`/compare`) — KEY FEATURE

**Route:** `/compare?ids=id1,id2,id3`
**Page:** `frontend/src/pages/CompareBacktests.tsx`

This is the crown jewel. Make it visually impressive and informative.

**Data fetching:**
- Parse `ids` from query params
- Fetch each backtest via `useBacktest(id)` for each ID
- Fetch performance data via existing `/portfolios/{portfolio_id}/performance?range=ALL` for each backtest's `portfolio_id`

**Comparison Chart (top section):**
- **Normalized % return line chart**: Overlay all backtests on one Recharts LineChart
- Each line starts at 0% and shows cumulative % return over time
- Why normalize: Backtests may have different initial_cash amounts; % return makes them comparable
- Each backtest gets a distinct color from a palette
- Legend shows backtest name + color
- Tooltip shows date + all values
- Use `ResponsiveContainer` (height ~400px for impact)

**Normalization formula:**
```
normalized_return[i] = ((data_points[i].total_value - data_points[0].total_value) / data_points[0].total_value) * 100
```

**Metrics Comparison Table (below chart):**
- Table with columns: Metric | Backtest A | Backtest B | Backtest C | ...
- Rows:
  - Strategy Type
  - Date Range
  - Initial Cash
  - Total Return %
  - Annualized Return %
  - Max Drawdown %
  - Total Trades
- Color-code: best value in each metric row gets green highlight, worst gets red
- Use `formatPercent()` and `formatCurrency()` from existing formatters

**Future-proofing for S&P 500 benchmark:**
- Design the chart component to accept an array of `{ name: string, data: {date, value}[] }` series
- This makes it trivial to add a benchmark line later (just add another series)
- Optionally add a "Show S&P 500 Benchmark" toggle (disabled/grayed out with "Coming soon" tooltip)

### 7. Component Organization

Follow existing patterns:

```
frontend/src/
├── components/features/
│   ├── strategies/
│   │   ├── StrategyCard.tsx
│   │   ├── CreateStrategyForm.tsx
│   │   └── __tests__/
│   ├── backtests/
│   │   ├── BacktestCard.tsx (or BacktestRow.tsx)
│   │   ├── RunBacktestForm.tsx
│   │   ├── BacktestMetrics.tsx
│   │   ├── ComparisonChart.tsx
│   │   ├── ComparisonTable.tsx
│   │   └── __tests__/
├── pages/
│   ├── Strategies.tsx
│   ├── Backtests.tsx
│   ├── BacktestResult.tsx
│   └── CompareBacktests.tsx
├── hooks/
│   ├── useStrategies.ts
│   └── useBacktests.ts
├── services/api/
│   ├── strategies.ts
│   └── backtests.ts
```

### 8. Dark Mode & Responsive Design

- All new components MUST support dark mode (use existing Tailwind dark: variants)
- Chart backgrounds: `bg-white dark:bg-gray-800`
- Text: `text-gray-900 dark:text-gray-100`
- Cards: Use existing Card components which handle dark mode
- Responsive: mobile-first, use sm:/md:/lg: breakpoints
- Charts should use `ResponsiveContainer` for sizing

### 9. Tests

Write Vitest unit tests for:
- API service functions (mock axios)
- Key components (strategy form validation, comparison table rendering)
- Hook behavior (query key structure)

Follow existing test patterns in `frontend/src/components/features/analytics/__tests__/` and `frontend/src/components/features/portfolio/__tests__/`.

---

## Backend API Reference (Quick Reference)

### Strategy Endpoints
```
POST   /api/v1/strategies          → CreateStrategyRequest → StrategyResponse (201)
GET    /api/v1/strategies          → StrategyResponse[] (200)
GET    /api/v1/strategies/{id}     → StrategyResponse (200)
DELETE /api/v1/strategies/{id}     → 204
```

### Backtest Endpoints
```
POST   /api/v1/backtests           → RunBacktestRequest → BacktestRunResponse (201)
GET    /api/v1/backtests           → BacktestRunResponse[] (200)
GET    /api/v1/backtests/{id}      → BacktestRunResponse (200)
DELETE /api/v1/backtests/{id}      → 204
```

### Performance Data (for backtest portfolios)
```
GET    /api/v1/portfolios/{portfolio_id}/performance?range=ALL → PerformanceResponse
```

The `portfolio_id` is available in `BacktestRunResponse.portfolio_id`.

### Portfolios (with type filter)
```
GET    /api/v1/portfolios?include_backtest=true  → PortfolioResponse[]
```

### Supported Strategy Parameters

| Type | Parameters |
|------|-----------|
| BUY_AND_HOLD | `{ allocation: { "AAPL": 0.6, "MSFT": 0.4 } }` (must sum to 1.0) |
| DOLLAR_COST_AVERAGING | `{ frequency_days: 30, amount_per_period: 500, allocation: { "AAPL": 1.0 } }` |
| MOVING_AVERAGE_CROSSOVER | `{ fast_window: 20, slow_window: 50, invest_fraction: 0.95 }` |

---

## Acceptance Criteria

1. ✅ Navigation tabs visible on all authenticated pages (Portfolios, Strategies, Backtests)
2. ✅ `/strategies` page: list, create (with dynamic params form per type), delete strategies
3. ✅ `/backtests` page: list with status badges, run new backtest, delete, checkbox selection
4. ✅ `/backtests/:id` page: metrics + performance chart for single backtest
5. ✅ `/compare?ids=...` page: normalized % return overlay chart + metrics comparison table
6. ✅ Comparison chart uses distinct colors per series, with legend
7. ✅ Metrics table highlights best/worst values per row
8. ✅ All pages support dark mode and are responsive
9. ✅ API types, services, and hooks follow existing codebase patterns
10. ✅ Unit tests for key components and services
11. ✅ `task quality:frontend` passes (ESLint, Prettier, TypeScript, Vitest)
12. ✅ No regressions to existing pages
