# Application Overview Dashboard

This dashboard provides a comprehensive view of Zebu application health and performance.

## Dashboard Structure

**Refresh**: Auto (30s)  
**Time Range**: Last 1 hour (configurable)

## Panels

### Row 1: System Health

#### Panel 1.1: Request Rate
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Request started" [1m]))
  ```
- **Unit**: requests/second
- **Legend**: Request Rate
- **Threshold**: Warning at 10 req/s, Critical at 50 req/s

#### Panel 1.2: Error Rate
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | level="error" [1m]))
  ```
- **Unit**: errors/second
- **Legend**: Error Rate
- **Threshold**: Warning at 0.05 err/s, Alert at 0.1 err/s
- **Color**: Red fill for errors

#### Panel 1.3: Service Uptime
- **Type**: Stat
- **Query**:
  ```logql
  count_over_time({container="zebu-backend-prod"} [5m]) > 0
  ```
- **Display**: 
  - "UP" (green) if logs present
  - "DOWN" (red) if no logs
- **Threshold**: 0 = down, >0 = up

### Row 2: Performance Metrics

#### Panel 2.1: Response Time (P50, P95, P99)
- **Type**: Time series
- **Queries**:
  ```logql
  # P50
  quantile_over_time(0.50, {container="zebu-backend-prod"} | json | unwrap duration_seconds [1m])
  
  # P95
  quantile_over_time(0.95, {container="zebu-backend-prod"} | json | unwrap duration_seconds [1m])
  
  # P99
  quantile_over_time(0.99, {container="zebu-backend-prod"} | json | unwrap duration_seconds [1m])
  ```
- **Unit**: seconds
- **Legend**: P50, P95, P99
- **Threshold**: Warning at 0.5s (p95), Critical at 1.0s (p95)

#### Panel 2.2: Slow Requests (>1s)
- **Type**: Time series
- **Query**:
  ```logql
  count_over_time({container="zebu-backend-prod"} | json | duration_seconds > 1.0 [1m])
  ```
- **Unit**: count
- **Legend**: Slow Requests

#### Panel 2.3: Request Duration Heatmap
- **Type**: Heatmap
- **Query**:
  ```logql
  {container="zebu-backend-prod"} | json | unwrap duration_seconds
  ```
- **Bucket**: Logarithmic scale (0.01s to 10s)
- **Color**: Blue (fast) to Red (slow)

### Row 3: Cache Performance

#### Panel 3.1: Cache Hit Ratio
- **Type**: Gauge
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Price fetched from cache" | source="redis" [5m])) 
  / 
  sum(rate({container="zebu-backend-prod"} | json | event =~ "Price fetched.*" [5m])) * 100
  ```
- **Unit**: percent (0-100)
- **Threshold**: 
  - Green > 90%
  - Yellow 70-90%
  - Red < 70%

#### Panel 3.2: Cache Hits vs Misses
- **Type**: Time series (stacked)
- **Queries**:
  ```logql
  # Cache hits
  sum(rate({container="zebu-backend-prod"} | json | event="Price fetched from cache" [1m]))
  
  # Cache misses (API calls)
  sum(rate({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [1m]))
  ```
- **Display**: Stacked area chart
- **Legend**: Cache Hits (green), API Calls (orange)

#### Panel 3.3: Redis Status
- **Type**: Logs panel
- **Query**:
  ```logql
  {container="zebu-redis-prod"}
  ```
- **Display**: Last 50 log lines
- **Limit**: 50 lines

### Row 4: Error Analysis

#### Panel 4.1: Top 10 Errors
- **Type**: Table
- **Query**:
  ```logql
  topk(10, count_over_time({container="zebu-backend-prod"} | json | level="error" [1h]) by (event, logger))
  ```
- **Columns**: 
  - Event
  - Logger
  - Count
  - Trend (sparkline)
- **Sort**: By count (descending)

#### Panel 4.2: Error Logs
- **Type**: Logs panel
- **Query**:
  ```logql
  {container="zebu-backend-prod"} | json | level="error"
  ```
- **Display**: Last 100 errors with full context
- **Limit**: 100 lines
- **Time columns**: Show timestamp, level, event, error message

#### Panel 4.3: Error Rate by Endpoint
- **Type**: Bar chart
- **Query**:
  ```logql
  sum by (request_path) (count_over_time({container="zebu-backend-prod"} | json | level="error" [1h]))
  ```
- **Display**: Horizontal bars
- **Sort**: By count

### Row 5: HTTP Status Codes

#### Panel 5.1: Status Code Distribution
- **Type**: Pie chart
- **Query**:
  ```logql
  sum by (status_code) (count_over_time({container="zebu-backend-prod"} | json | status_code > 0 [1h]))
  ```
- **Legend**: 
  - 2xx (green)
  - 3xx (blue)
  - 4xx (yellow)
  - 5xx (red)

#### Panel 5.2: 4xx Errors Over Time
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | status_code >= 400 | status_code < 500 [1m]))
  ```
- **Unit**: requests/second
- **Color**: Yellow

#### Panel 5.3: 5xx Errors Over Time
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | status_code >= 500 [1m]))
  ```
- **Unit**: requests/second
- **Color**: Red

## Variables

Define the following dashboard variables for easy filtering:

- **$container**: Container name (default: `zebu-backend-prod`)
- **$interval**: Time bucket (default: `1m`, options: 30s, 1m, 5m, 15m)
- **$log_level**: Log level filter (default: all, options: debug, info, warning, error)

## Alerts

Configure alerts on this dashboard:

1. **High Error Rate**: Error rate > 0.1/sec for 5 minutes
2. **Service Down**: No logs for 5 minutes
3. **High Response Time**: P95 > 1 second for 5 minutes
4. **Low Cache Hit Rate**: < 70% for 15 minutes

## Export/Import

To export this dashboard:
1. Click **Dashboard Settings** (gear icon)
2. Click **JSON Model**
3. Copy JSON
4. Save to `docs/monitoring/dashboards/application-overview.json`

To import:
1. Go to **Dashboards** → **Import**
2. Upload JSON file
3. Select Loki data source
4. Click **Import**

## Customization Tips

- **Add panels** for specific features (e.g., authentication events, portfolio operations)
- **Adjust time ranges** based on traffic patterns
- **Create alert rules** for business-critical metrics
- **Use annotations** to mark deployments or incidents
- **Add links** to related dashboards or runbooks
