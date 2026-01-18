# External Services Dashboard

Monitor external dependencies: Alpha Vantage API, PostgreSQL, Redis, and other third-party services.

## Dashboard Structure

**Refresh**: Auto (1m)  
**Time Range**: Last 6 hours (configurable)

## Panels

### Row 1: Alpha Vantage API

#### Panel 1.1: API Calls Today
- **Type**: Stat (big number)
- **Query**:
  ```logql
  count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [24h])
  ```
- **Display**: Current count / 500 (daily limit)
- **Threshold**:
  - Green: < 400 calls
  - Yellow: 400-480 calls
  - Red: > 480 calls

#### Panel 1.2: API Call Rate
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [1m]))
  ```
- **Unit**: calls/minute
- **Threshold**: Warning at 4 calls/min (approaching 5 calls/min limit)
- **Display**: Line with threshold marker

#### Panel 1.3: Rate Limit Warnings
- **Type**: Logs panel
- **Query**:
  ```logql
  {container="zebu-backend-prod"} | json | event =~ ".*rate limit.*" | level="warning"
  ```
- **Display**: Last 50 warnings
- **Highlight**: Rate limit messages in red

#### Panel 1.4: API Response Times
- **Type**: Time series
- **Queries**:
  ```logql
  # P50
  quantile_over_time(0.50, {container="zebu-backend-prod"} | json | event="Alpha Vantage API called" | unwrap duration_ms [5m])
  
  # P95
  quantile_over_time(0.95, {container="zebu-backend-prod"} | json | event="Alpha Vantage API called" | unwrap duration_ms [5m])
  ```
- **Unit**: milliseconds
- **Legend**: P50, P95
- **Threshold**: Warning at 2000ms (2 seconds)

#### Panel 1.5: API Errors
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | logger="zebu.adapters.outbound.market_data.alpha_vantage_adapter" | level="error" [5m]))
  ```
- **Unit**: errors/minute
- **Color**: Red

### Row 2: PostgreSQL Database

#### Panel 2.1: Database Connection Status
- **Type**: Stat
- **Query**:
  ```logql
  count_over_time({container="zebu-postgres-prod"} [1m]) > 0
  ```
- **Display**: "Connected" (green) or "Disconnected" (red)

#### Panel 2.2: Database Logs
- **Type**: Logs panel
- **Query**:
  ```logql
  {container="zebu-postgres-prod"}
  ```
- **Display**: Last 100 log lines
- **Filter**: Show errors and warnings prominently

#### Panel 2.3: Connection Pool Usage
- **Type**: Time series
- **Query**:
  ```logql
  # If connection pool metrics are logged
  {container="zebu-backend-prod"} | json | event =~ ".*connection pool.*" | unwrap active_connections
  ```
- **Unit**: connections
- **Threshold**: Warning at 80% of pool size

#### Panel 2.4: Slow Queries
- **Type**: Logs panel
- **Query**:
  ```logql
  {container="zebu-postgres-prod"} |~ "duration.*ms" | regexp "duration: (?P<duration>[0-9.]+) ms" | duration > 1000
  ```
- **Display**: Queries taking > 1 second
- **Limit**: 50 queries

#### Panel 2.5: Database Errors
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-postgres-prod"} |~ "ERROR|FATAL" [5m]))
  ```
- **Unit**: errors/minute
- **Color**: Red

### Row 3: Redis Cache

#### Panel 3.1: Redis Status
- **Type**: Stat
- **Query**:
  ```logql
  count_over_time({container="zebu-redis-prod"} [1m]) > 0
  ```
- **Display**: "Online" (green) or "Offline" (red)

#### Panel 3.2: Cache Operations
- **Type**: Time series (stacked)
- **Queries**:
  ```logql
  # Cache reads (hits)
  sum(rate({container="zebu-backend-prod"} | json | event="Price fetched from cache" | source="redis" [1m]))
  
  # Cache writes
  sum(rate({container="zebu-backend-prod"} | json | event =~ ".*cache.*set.*" [1m]))
  ```
- **Display**: Stacked area
- **Legend**: Reads, Writes

#### Panel 3.3: Redis Logs
- **Type**: Logs panel
- **Query**:
  ```logql
  {container="zebu-redis-prod"}
  ```
- **Display**: Last 50 log lines
- **Filter**: Highlight warnings and errors

#### Panel 3.4: Cache Memory Usage (if logged)
- **Type**: Time series
- **Query**:
  ```logql
  {container="zebu-redis-prod"} |~ "memory" | regexp "used_memory:(?P<memory>[0-9]+)"
  ```
- **Unit**: bytes
- **Threshold**: Warning at 80% of available memory

#### Panel 3.5: Evictions
- **Type**: Time series
- **Query**:
  ```logql
  {container="zebu-redis-prod"} |~ "evict"
  ```
- **Unit**: evictions/minute
- **Note**: High evictions indicate memory pressure

### Row 4: API Rate Limit Consumption

#### Panel 4.1: Daily Quota Usage
- **Type**: Gauge (0-100%)
- **Query**:
  ```logql
  (count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [24h]) / 500) * 100
  ```
- **Unit**: percent
- **Threshold**:
  - Green: 0-70%
  - Yellow: 70-90%
  - Red: 90-100%

#### Panel 4.2: Hourly Rate Limit Headroom
- **Type**: Time series
- **Query**:
  ```logql
  5 - sum(rate({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [1m]))
  ```
- **Unit**: calls/minute available
- **Display**: Line showing remaining capacity
- **Threshold**: Warning when < 1 call/min headroom

#### Panel 4.3: Requests Served from Stale Cache
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Price fetched from cache" | level="warning" [5m]))
  ```
- **Unit**: requests/minute
- **Note**: Indicates rate limiting is impacting users

#### Panel 4.4: Time Until Rate Limit Reset
- **Type**: Stat
- **Query**: (Calculated in backend if logged)
  ```logql
  {container="zebu-backend-prod"} | json | event="Rate limiter status" | line_format "{{.reset_in_seconds}}s"
  ```
- **Display**: Countdown timer

### Row 5: External API Health

#### Panel 5.1: API Availability
- **Type**: Stat (percentage)
- **Query**:
  ```logql
  # Successful API calls / Total API calls
  (count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [1h]) 
  - count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" | level="error" [1h]))
  / count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [1h]) * 100
  ```
- **Unit**: percent
- **Target**: > 99.9% availability

#### Panel 5.2: API Error Types
- **Type**: Table
- **Query**:
  ```logql
  topk(10, count_over_time({container="zebu-backend-prod"} | json | logger="zebu.adapters.outbound.market_data.alpha_vantage_adapter" | level="error" [6h]) by (error))
  ```
- **Columns**: Error type, Count
- **Sort**: By count

#### Panel 5.3: Fallback to Database
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | event="Price fetched from cache" | source="database" [5m]))
  ```
- **Unit**: requests/minute
- **Note**: Shows degraded mode (using Tier 2 cache)

### Row 6: Network & Connectivity

#### Panel 6.1: Network Errors
- **Type**: Time series
- **Query**:
  ```logql
  sum(rate({container="zebu-backend-prod"} | json | error =~ ".*network.*|.*timeout.*|.*connection.*" | level="error" [5m]))
  ```
- **Unit**: errors/minute
- **Color**: Red

#### Panel 6.2: DNS Resolution Failures (if logged)
- **Type**: Stat
- **Query**:
  ```logql
  count_over_time({container="zebu-backend-prod"} | json | error =~ ".*DNS.*|.*name resolution.*" [1h])
  ```
- **Display**: Count in last hour

#### Panel 6.3: SSL/TLS Errors (if logged)
- **Type**: Logs panel
- **Query**:
  ```logql
  {container="zebu-backend-prod"} | json | error =~ ".*SSL.*|.*TLS.*|.*certificate.*"
  ```
- **Display**: Certificate-related errors

## Variables

- **$service**: Filter by service (Alpha Vantage, PostgreSQL, Redis)
- **$time_range**: Custom time range for analysis

## Alerts

1. **Alpha Vantage Rate Limit**: > 480 calls in 24h
2. **API Errors**: > 5% error rate over 10 minutes
3. **Database Down**: No PostgreSQL logs for 2 minutes
4. **Redis Down**: No Redis logs for 2 minutes
5. **High API Latency**: P95 > 3 seconds for 5 minutes

## Remediation Actions

### Alpha Vantage Rate Limit Hit

**Immediate**:
1. Increase cache TTL temporarily
2. Serve stale cached data
3. Notify users of potential delays

**Short-term**:
1. Optimize cache warming strategy
2. Batch requests more efficiently
3. Consider upgrading to paid tier

### Database Connection Issues

**Immediate**:
1. Check PostgreSQL container health
2. Restart database if necessary
3. Verify connection pool configuration

**Short-term**:
1. Review slow queries
2. Add connection pool monitoring
3. Optimize frequently-run queries

### Redis Cache Failure

**Immediate**:
1. Restart Redis container
2. Verify Redis is accepting connections
3. Check memory usage

**Short-term**:
1. Increase Redis memory allocation
2. Review cache eviction policy
3. Consider Redis persistence (RDB/AOF)

## Export/Import

Save to: `docs/monitoring/dashboards/external-services.json`

## Optimization Opportunities

This dashboard helps identify:
- When to upgrade Alpha Vantage tier
- Database query performance issues
- Cache configuration improvements
- Network reliability problems
- Peak usage patterns for capacity planning
