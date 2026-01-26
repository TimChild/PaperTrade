# Phase 3c: Portfolio Analytics & Simple Backtesting

**Duration**: 3-4 weeks
**Priority**: MEDIUM (enhances user experience)
**Dependencies**: Phase 3a (SELL orders) recommended

## Objective

Provide users with visual insights into portfolio performance and enable basic backtesting to evaluate trading strategies against historical data.

## Current State

**What Exists**:
- ✅ Historical price data in database (Phase 2b)
- ✅ Price history API endpoints
- ✅ Background scheduler for price updates
- ✅ Transaction ledger with complete history
- ✅ Holdings and balance calculations

**What's Missing**:
- ❌ Portfolio performance charts
- ❌ Gain/loss visualizations
- ❌ Asset allocation displays
- ❌ Backtesting functionality
- ❌ Chart UI components

## Analytics Architecture

### Chart Library Selection

**Decision**: **Recharts**

| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| **Recharts** | React-native, composable, responsive | Less feature-rich than TradingView | ✅ **SELECTED** |
| Chart.js | Popular, flexible, many chart types | Not React-native, requires wrapper | ❌ |
| TradingView | Professional, feature-rich, industry-standard | Heavy, expensive, complex | ⏳ Future upgrade |
| Victory | Fully featured, modular | Steeper learning curve | ❌ |

**Reasoning**:
- Recharts is React-first (easy integration)
- Already used in Phase 2b price history (consistency)
- Composable components match our architecture
- Sufficient for MVP analytics
- Can upgrade to TradingView later for advanced features

### Performance Calculation Strategy

**Approach**: **Pre-computed Daily Snapshots**

**Why NOT Real-Time Calculation**:
- Calculating portfolio value requires fetching prices for ALL holdings
- N+1 query problem for portfolios with many stocks
- Slow page loads for historical charts
- API rate limit concerns

**Why Pre-Computed Snapshots**:
- Calculate once per day (background job)
- Store in `portfolio_snapshots` table
- Fast chart rendering (single query)
- No API calls during chart display

**Trade-offs**:
- Additional storage (~1KB per portfolio per day = 365KB/year)
- Snapshot calculation complexity
- Delayed updates (next snapshot run)

**Accepted**: Storage is cheap, performance is valuable

## Domain Model Changes

### New Entity: PortfolioSnapshot

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| id | UUID | Primary key | Auto-generated |
| portfolio_id | UUID | Foreign key to portfolios | Required |
| snapshot_date | date | Date of snapshot | Unique per portfolio per day |
| total_value | Money | Portfolio value (cash + holdings) | Positive |
| cash_balance | Money | Available cash | Positive or zero |
| holdings_value | Money | Total value of all holdings | Positive or zero |
| holdings_count | int | Number of different stocks owned | >= 0 |
| created_at | datetime | When snapshot was calculated | Auto-set |

**Invariants**:
- total_value = cash_balance + holdings_value
- One snapshot per portfolio per day (unique constraint)
- snapshot_date <= today (cannot snapshot future)

**Indexes**:
- (portfolio_id, snapshot_date) - Fast range queries for charts
- snapshot_date - Batch processing by date

### New Value Object: PerformanceMetrics

| Property | Type | Description | Calculation |
|----------|------|-------------|-------------|
| period_start | date | Start of measurement period | From snapshots |
| period_end | date | End of measurement period | From snapshots |
| starting_value | Money | Portfolio value at start | First snapshot |
| ending_value | Money | Portfolio value at end | Last snapshot |
| absolute_gain | Money | Total profit/loss | ending - starting |
| percentage_gain | Decimal | ROI percentage | (ending/starting - 1) * 100 |
| highest_value | Money | Peak value in period | max(snapshots) |
| lowest_value | Money | Trough value in period | min(snapshots) |

**Example**:
- Start: $10,000 (Jan 1)
- End: $12,500 (Jan 31)
- Absolute gain: $2,500
- Percentage gain: 25%

## Analytics Features

### 1. Portfolio Value Chart (Line Chart)

**Visualization**: Line chart showing portfolio total value over time

**Data Source**: `portfolio_snapshots` table

**Time Ranges**:
- 1 Week (7 days)
- 1 Month (30 days)
- 3 Months (90 days)
- 1 Year (365 days)
- All Time (since portfolio creation)

**Chart Components**:
- X-axis: Date
- Y-axis: Portfolio value (USD)
- Tooltip: Hover shows exact value and date
- Trend line: Smooth curve
- Reference line: Starting value (horizontal)

**API Endpoint**: `GET /api/v1/portfolios/{id}/performance?range={range}`

**Response**:
```json
{
  "portfolio_id": "uuid",
  "range": "1M",
  "data_points": [
    {
      "date": "2026-01-01",
      "total_value": 10000.00,
      "cash_balance": 10000.00,
      "holdings_value": 0.00
    },
    {
      "date": "2026-01-02",
      "total_value": 10050.00,
      "cash_balance": 5000.00,
      "holdings_value": 5050.00
    }
  ],
  "metrics": {
    "starting_value": 10000.00,
    "ending_value": 12500.00,
    "absolute_gain": 2500.00,
    "percentage_gain": 25.0,
    "highest_value": 12750.00,
    "lowest_value": 9800.00
  }
}
```

### 2. Gain/Loss Summary

**Visualization**: Card/stat display showing key metrics

**Metrics Displayed**:
- Total Gain/Loss (absolute $)
- Total Gain/Loss (percentage %)
- Today's Change ($ and %)
- Best Day (highest gain)
- Worst Day (largest loss)

**Color Coding**:
- Green: Positive gains
- Red: Losses
- Gray: No change

**Data Source**: Calculated from snapshots

### 3. Holdings Composition (Pie Chart)

**Visualization**: Pie chart showing asset allocation

**Data**:
- Each holding is a slice
- Size proportional to value
- Shows ticker symbol and percentage
- Cash shown as separate slice

**Colors**: Auto-assigned by chart library

**Tooltip**: Shows ticker, value ($), percentage (%)

**API Endpoint**: `GET /api/v1/portfolios/{id}/composition`

**Response**:
```json
{
  "portfolio_id": "uuid",
  "total_value": 12500.00,
  "composition": [
    {
      "ticker": "IBM",
      "value": 5500.00,
      "percentage": 44.0,
      "quantity": 30
    },
    {
      "ticker": "AAPL",
      "value": 4000.00,
      "percentage": 32.0,
      "quantity": 20
    },
    {
      "ticker": "CASH",
      "value": 3000.00,
      "percentage": 24.0,
      "quantity": null
    }
  ]
}
```

### 4. Top Gainers/Losers

**Visualization**: Table showing best/worst performing holdings

**Columns**:
- Ticker
- Quantity
- Current Value
- Cost Basis
- Gain/Loss ($)
- Gain/Loss (%)

**Sorting**: By gain/loss percentage (descending)

**Data Source**: Current holdings with cost basis

## Backtesting Architecture

### Approach: Time-Travel Use Cases

**Core Concept**: Parameterize use cases with `as_of` datetime

**Current Design** (Phase 2):
```python
async def execute_trade(
    portfolio_id: UUID,
    ticker: Ticker,
    quantity: int,
    trade_type: TradeType,
    market_data: MarketDataPort
) -> Transaction:
    # Uses current time implicitly
    price = await market_data.get_current_price(ticker)
    ...
```

**Backtesting Design** (Phase 3c):
```python
async def execute_trade(
    portfolio_id: UUID,
    ticker: Ticker,
    quantity: int,
    trade_type: TradeType,
    market_data: MarketDataPort,
    *,
    as_of: datetime | None = None  # NEW parameter
) -> Transaction:
    effective_time = as_of or datetime.now(UTC)
    price = await market_data.get_price_at(ticker, effective_time)
    # Create transaction with timestamp = effective_time
    ...
```

**Benefits**:
- Minimal code changes (add optional parameter)
- Same validation logic for live vs backtest
- Historical prices already available (Phase 2b)
- Can replay trades at any point in time

### Backtesting Workflow

**User Flow**:
1. Create special "backtest portfolio"
2. Select start date (e.g., Jan 1, 2024)
3. Execute trades with `as_of` parameter
4. View performance as if trading in real-time
5. Compare strategy outcomes

**Example Backtest**:
- Strategy: Buy 10 IBM on Jan 1, sell on Feb 1
- Execution:
  - Create portfolio with $10,000
  - `execute_trade(BUY, IBM, 10, as_of="2024-01-01")` → $1,800 spent
  - `execute_trade(SELL, IBM, 10, as_of="2024-02-01")` → $1,950 received
  - Result: $150 profit (8.3% gain)

**Limitations** (MVP):
- Manual trade execution (no automated replay)
- No slippage simulation
- No transaction fees (Phase 4 feature)
- Uses end-of-day prices (not intraday)

**Future Enhancements**:
- Strategy scripts (automated execution)
- Monte Carlo simulations
- Risk metrics (Sharpe ratio, volatility)
- Benchmark comparisons (vs S&P 500)

## API Changes

### New Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/v1/portfolios/{id}/performance` | GET | Portfolio value over time | Yes |
| `/api/v1/portfolios/{id}/composition` | GET | Asset allocation | Yes |
| `/api/v1/portfolios/{id}/snapshots` | GET | Raw snapshot data | Yes |
| `/api/v1/portfolios/{id}/snapshots` | POST | Trigger snapshot (admin) | Yes |

### Updated Endpoints

| Endpoint | Change | Purpose |
|----------|--------|---------|
| `POST /api/v1/portfolios/{id}/trades` | Add `as_of` parameter (optional) | Backtesting support |

**Trade Request with Backtesting**:
```json
{
  "ticker": "IBM",
  "quantity": 10,
  "action": "BUY",
  "as_of": "2024-01-01T00:00:00Z"  // Optional, defaults to now
}
```

**Validation**:
- `as_of` must not be in future
- `as_of` must have historical price data available
- Normal trade validation still applies

## Frontend Changes

### New Components

**PortfolioPerformanceChart**:
- Recharts LineChart
- Time range selector (buttons: 1W, 1M, 3M, 1Y, ALL)
- Tooltip with date and value
- Loading state during fetch
- Error handling (no data, API error)

**PortfolioCompositionPieChart**:
- Recharts PieChart
- Legend with ticker symbols
- Tooltip with value and percentage
- Responsive sizing

**PerformanceMetricsCard**:
- Grid layout
- Stat displays (value, label, trend indicator)
- Green/red color coding
- Animated counters (optional enhancement)

**GainersLosersTable**:
- Sortable table (by gain/loss %)
- Color-coded rows
- Click ticker to view stock details

**BacktestPortfolioForm**:
- Date picker for start date
- Button to create backtest portfolio
- Warning: "Backtest mode active" indicator
- Trade form with `as_of` parameter

### Page Layout Updates

**Portfolio Detail Page**:
- Add "Analytics" tab (alongside "Holdings", "Transactions")
- Analytics tab contains:
  - Performance chart (top)
  - Metrics cards (middle)
  - Pie chart (right)
  - Gainers/losers table (bottom)

**Trade Form**:
- Add "Backtest Mode" toggle
- If enabled: Show date picker
- If disabled: Use current time

## Background Jobs

### Daily Snapshot Calculation

**Schedule**: Every day at midnight UTC

**Process**:
```
For each active portfolio:
  1. Get all transactions up to today
  2. Calculate cash balance (from ledger)
  3. Calculate holdings (from ledger)
  4. Fetch current prices for all holdings
  5. Calculate holdings_value (sum of holding * price)
  6. Calculate total_value (cash + holdings)
  7. Insert snapshot record
```

**Error Handling**:
- Skip portfolio if no transactions today
- Retry price fetch failures (3 attempts)
- Log errors but continue with other portfolios
- Alert if >10% of snapshots fail

**Performance**:
- Process in batches (10 portfolios at a time)
- Respect API rate limits (5 calls/min)
- Complete within 1 hour for 1000 portfolios

### Backfill Historical Snapshots

**Purpose**: Generate snapshots for past dates

**When**: One-time migration + manual admin task

**Process**:
```
For each portfolio:
  For each date from creation_date to yesterday:
    1. Calculate portfolio state at that date
    2. Fetch historical price for that date
    3. Calculate snapshot
    4. Insert snapshot
```

**Challenges**:
- Many API calls (rate limit concern)
- Long processing time (batch overnight)
- Historical prices may not exist for all dates

**Mitigation**:
- Run once, cache forever
- Use background job queue (Celery, future)
- Start with recent dates, backfill older gradually

## Database Schema Changes

### New Table: portfolio_snapshots

```sql
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    total_value DECIMAL(15, 2) NOT NULL CHECK (total_value >= 0),
    cash_balance DECIMAL(15, 2) NOT NULL CHECK (cash_balance >= 0),
    holdings_value DECIMAL(15, 2) NOT NULL CHECK (holdings_value >= 0),
    holdings_count INTEGER NOT NULL CHECK (holdings_count >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_portfolio_date UNIQUE (portfolio_id, snapshot_date),
    CONSTRAINT valid_total CHECK (total_value = cash_balance + holdings_value)
);

CREATE INDEX idx_snapshots_portfolio_date ON portfolio_snapshots(portfolio_id, snapshot_date);
CREATE INDEX idx_snapshots_date ON portfolio_snapshots(snapshot_date);
```

**Indexes Rationale**:
- (portfolio_id, snapshot_date): Fast range queries for charts
- snapshot_date: Batch processing by date

## Testing Strategy

### Unit Tests (Domain Layer)

**Snapshot Calculation**:
- `test_calculate_snapshot_only_cash` - Cash-only portfolio
- `test_calculate_snapshot_with_holdings` - Multiple stocks
- `test_calculate_snapshot_zero_holdings` - All sold
- `test_performance_metrics_calculation` - Gain/loss math

### Integration Tests (Use Cases)

**Analytics Tests**:
- `test_get_performance_data_1_month` - Returns correct snapshots
- `test_get_performance_data_no_data` - Handles missing snapshots
- `test_calculate_daily_snapshot` - Snapshot logic correct
- `test_backfill_snapshots_range` - Historical backfill

**Backtesting Tests**:
- `test_execute_trade_with_as_of` - Trade at past date
- `test_execute_trade_future_as_of` - Rejects future date
- `test_backtest_buy_sell_strategy` - Complete backtest flow

### API Tests

**Analytics Endpoint Tests**:
- `test_get_performance_success` - 200 OK with data
- `test_get_performance_invalid_range` - 400 Bad Request
- `test_get_composition_success` - 200 OK with pie data
- `test_post_snapshot_admin_only` - 403 Forbidden

### E2E Tests

**Analytics Flow**:
1. Create portfolio
2. Execute trades
3. Trigger snapshot
4. View performance chart
5. Verify data displays correctly

**Backtesting Flow**:
1. Create backtest portfolio
2. Select past date
3. Execute trades with `as_of`
4. View performance
5. Verify historical prices used

## Implementation Sequence

**Recommended Order**:

1. **Domain Layer** (~2 days)
   - PortfolioSnapshot entity
   - PerformanceMetrics value object
   - Snapshot calculation logic
   - Unit tests

2. **Database Migration** (~1 day)
   - Create portfolio_snapshots table
   - Indexes
   - Constraints

3. **Background Jobs** (~3 days)
   - Daily snapshot scheduler
   - Backfill script
   - Error handling
   - Job tests

4. **API Layer** (~3 days)
   - Performance endpoints
   - Composition endpoint
   - Update trade endpoint with `as_of`
   - API tests

5. **Frontend Charts** (~5 days)
   - Install Recharts
   - Performance chart component
   - Pie chart component
   - Metrics cards
   - Analytics page layout
   - E2E tests

6. **Backtesting UI** (~3 days)
   - Backtest mode toggle
   - Date picker
   - Validation
   - E2E tests

7. **Documentation** (~1 day)
   - Update USER_GUIDE.md (analytics section)
   - Update FEATURE_STATUS.md (analytics complete)
   - API documentation

**Total Estimate**: 18-22 days (3-4 weeks with buffer)

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Snapshot calculation bug | HIGH | MEDIUM | Comprehensive tests, manual verification |
| Chart rendering performance | MEDIUM | LOW | Recharts handles 1000+ points well |
| Historical price gaps | MEDIUM | MEDIUM | Graceful fallback, interpolation |
| Background job failures | MEDIUM | MEDIUM | Retry logic, monitoring, alerts |
| API rate limits during backfill | HIGH | HIGH | Batch processing, respect limits |

## Success Criteria

- [ ] Users can view portfolio value chart (line chart)
- [ ] Chart supports 1W, 1M, 3M, 1Y, ALL time ranges
- [ ] Users can see gain/loss metrics ($ and %)
- [ ] Users can view holdings composition (pie chart)
- [ ] Daily snapshots calculated automatically
- [ ] Users can create backtest portfolios
- [ ] Trades can be executed with `as_of` parameter
- [ ] Historical prices used for backtest trades
- [ ] All 499+ existing tests still pass
- [ ] 40+ new tests for analytics functionality
- [ ] E2E tests verify chart rendering and backtesting
- [ ] Documentation updated

## Dependencies

**Requires**:
- Phase 2b (historical prices) - complete ✅
- Phase 3a (SELL orders) - recommended for complete P&L

**Blocks**:
- Advanced analytics (Phase 4+)
- Strategy builder (Phase 5)

**Parallel Work Opportunities**:
- Can start while Phase 3b (auth) is in progress

## Notes

**Design Decisions**:
- Pre-computed snapshots over real-time calculation (performance)
- Recharts over TradingView (simplicity, cost)
- End-of-day snapshots over intraday (MVP simplicity)
- Time-travel use cases over separate backtest logic (DRY principle)

**Alternatives Considered**:
- Real-time calculation → Rejected (too slow, N+1 queries)
- WebSocket live updates → Deferred to Phase 4
- Advanced risk metrics → Deferred to future
- Strategy automation → Deferred to Phase 5

**Future Enhancements**:
- Real-time WebSocket chart updates
- Sharpe ratio, beta, volatility calculations
- Benchmark comparison (S&P 500, Dow Jones)
- Sector allocation analysis
- Custom date range selection
- Export data to CSV/Excel
- Share portfolio link (public view)

## References

- **Recharts Documentation**: https://recharts.org/
- **Historical Prices**: `../../docs/architecture/20251228_phase2-market-data/`
- **Snapshot Pattern**: Event Sourcing principles
- **Backtesting**: Similar to time-travel debugging
