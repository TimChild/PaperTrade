# Trading Activity Dashboard

Monitor user trading behavior, portfolio operations, and trading patterns.

## Dashboard Structure

**Refresh**: Auto (1m)  
**Time Range**: Last 24 hours (configurable)

## Panels

### Row 1: Trading Volume

#### Panel 1.1: Trades Executed (24h)
- **Type**: Stat (big number)
- **Query**:
  ```logql
  count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h])
  ```
- **Display**: Large number with trend arrow
- **Comparison**: vs previous 24h period

#### Panel 1.2: Trade Volume Over Time
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Trade executed" [5m]))
  ```
- **Unit**: trades/minute
- **Legend**: Trades per Minute
- **Fill**: Under line (area chart)

#### Panel 1.3: Trades by Action (Buy vs Sell)
- **Type**: Time series (stacked)
- **Queries**:
  ```logql
  # Buy orders
  sum(rate({container="zebu-backend-prod"} | json | event="Trade executed" | action="BUY" [5m]))
  
  # Sell orders
  sum(rate({container="zebu-backend-prod"} | json | event="Trade executed" | action="SELL" [5m]))
  ```
- **Display**: Stacked area
- **Legend**: Buy (green), Sell (red)

### Row 2: Popular Tickers

#### Panel 2.1: Top 10 Traded Tickers
- **Type**: Bar chart (horizontal)
- **Query**:
  ```logql
  topk(10, sum by (ticker) (count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h])))
  ```
- **Display**: Horizontal bars
- **Sort**: By count (descending)
- **Color**: Gradient based on volume

#### Panel 2.2: Trade Volume by Ticker (Time Series)
- **Type**: Time series
- **Query**:
  ```logql
  sum by (ticker) (rate({container="zebu-backend-prod"} | json | event="Trade executed" [5m]))
  ```
- **Display**: Multiple lines (top 10 tickers)
- **Legend**: Show ticker symbols

#### Panel 2.3: Unique Tickers Traded
- **Type**: Stat
- **Query**:
  ```logql
  count(count by (ticker) (count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h])))
  ```
- **Display**: Count of unique tickers

### Row 3: Portfolio Operations

#### Panel 3.1: New Portfolios Created
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Portfolio created" [1h]))
  ```
- **Unit**: portfolios/hour
- **Display**: Bar chart (hourly buckets)

#### Panel 3.2: Active Portfolios
- **Type**: Stat
- **Query**:
  ```logql
  count(count by (portfolio_id) (count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h])))
  ```
- **Display**: Count with trend

#### Panel 3.3: Portfolio Value Calculations
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Portfolio value calculated" [5m]))
  ```
- **Unit**: calculations/minute

### Row 4: Trade Performance

#### Panel 4.1: Average Trade Execution Time
- **Type**: Time series
- **Query**:
  ```logql
  avg_over_time({container="zebu-backend-prod"} | json | event="Trade executed" | unwrap duration_ms [5m])
  ```
- **Unit**: milliseconds
- **Threshold**: Warning at 500ms, Critical at 1000ms

#### Panel 4.2: Failed Trades
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Trade execution failed" [5m]))
  ```
- **Unit**: failures/minute
- **Color**: Red

#### Panel 4.3: Trade Failure Reasons
- **Type**: Table
- **Query**:
  ```logql
  topk(10, count_over_time({container="zebu-backend-prod"} | json | event="Trade execution failed" [24h]) by (error))
  ```
- **Columns**: Error reason, Count
- **Sort**: By count

### Row 5: User Activity

#### Panel 5.1: Active Users (Unique Sessions)
- **Type**: Time series
- **Query**:
  ```logql
  count(count by (correlation_id) (count_over_time({container="zebu-backend-prod"} | json [5m])))
  ```
- **Unit**: users
- **Display**: Estimate of concurrent users

#### Panel 5.2: Request Pattern by Hour
- **Type**: Heatmap
- **Query**:
  ```logql
  sum by (hour) (count_over_time({container="zebu-backend-prod"} | json [1h]))
  ```
- **Display**: Hour of day vs volume
- **Color**: Cool to hot gradient

#### Panel 5.3: Geographic Distribution (if available)
- **Type**: Stat or Table
- **Query**:
  ```logql
  # If client IP is logged
  count by (client_ip) (count_over_time({container="zebu-backend-prod"} | json [24h]))
  ```
- **Note**: Requires IP logging (privacy considerations)

### Row 6: Trading Patterns

#### Panel 6.1: Trade Size Distribution
- **Type**: Histogram
- **Query**:
  ```logql
  {container="zebu-backend-prod"} | json | event="Trade executed" | unwrap quantity
  ```
- **Buckets**: 1-10, 11-50, 51-100, 101-500, 500+
- **Display**: Bar chart showing distribution

#### Panel 6.2: Average Trade Value
- **Type**: Time series
- **Query**:
  ```logql
  avg_over_time({container="zebu-backend-prod"} | json | event="Trade executed" | unwrap price [1h])
  ```
- **Unit**: USD
- **Display**: Line with fill

#### Panel 6.3: Market Cap Preference
- **Type**: Pie chart
- **Query**: (Requires enrichment with ticker metadata)
  ```logql
  # If ticker market cap is logged
  sum by (market_cap_category) (count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h]))
  ```
- **Categories**: Large Cap, Mid Cap, Small Cap

## Variables

- **$time_bucket**: Aggregation interval (default: 5m)
- **$ticker**: Filter by specific ticker (default: all)
- **$action**: Filter by BUY or SELL (default: all)
- **$user_id**: Filter by user (default: all)

## Alerts

1. **Unusual Trading Volume**: Spike > 3x normal volume
2. **High Trade Failure Rate**: > 5% of trades failing
3. **No Trades**: No trades executed in 1 hour during trading hours (9:30 AM - 4:00 PM ET)

## Business Insights

This dashboard helps answer:
- Which stocks are most popular among users?
- When are peak trading hours?
- What is the typical trade size?
- Are users more likely to buy or sell?
- How fast are trades executing?
- What causes trade failures?

## Export/Import

Save to: `docs/monitoring/dashboards/trading-activity.json`

## Customization

- Add panels for **position sizing** (if logged)
- Track **round-trip trades** (buy → sell same ticker)
- Monitor **portfolio diversity** (number of positions per portfolio)
- Compare **paper trading performance** vs market benchmarks
