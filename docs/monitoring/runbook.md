# Monitoring Runbook

Operational procedures for investigating and responding to Zebu production issues using Grafana Cloud.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Investigating High Error Rates](#investigating-high-error-rates)
3. [Checking Cache Performance](#checking-cache-performance)
4. [Monitoring API Rate Limits](#monitoring-api-rate-limits)
5. [Reviewing User Activity](#reviewing-user-activity)
6. [Emergency Response](#emergency-response)
7. [Common LogQL Queries](#common-logql-queries)

## Quick Reference

### Access Points

- **Grafana Cloud**: https://[your-stack].grafana.net
- **Production Server**: `ssh root@192.168.4.112`
- **Promtail Logs**: `sudo journalctl -u promtail -f`

### Key Dashboards

- **Application Overview**: System health, errors, performance
- **Trading Activity**: Trades, portfolios, user actions
- **External Services**: Alpha Vantage API, database, cache

### Critical Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error Rate | > 0.05/sec | > 0.1/sec |
| API Calls (Alpha Vantage) | > 400/day | > 480/day |
| Response Time (p95) | > 500ms | > 1000ms |
| Cache Hit Ratio | < 80% | < 70% |

## Investigating High Error Rates

### Step 1: Identify Error Patterns

```logql
# View all errors in last hour
{container="zebu-backend-prod"} | json | level="error"

# Top 10 error types
topk(10, count_over_time({container="zebu-backend-prod"} | json | level="error" [1h]) by (event))
```

**What to look for**:
- Repeated error messages (indicates systemic issue)
- New error types (indicates recent code change or external failure)
- Spike in errors (indicates sudden issue)

### Step 2: Get Error Context

```logql
# Get error details with stack traces
{container="zebu-backend-prod"} | json | level="error" | line_format "{{.timestamp}} [{{.logger}}] {{.event}} - {{.error}}"

# Errors for specific operation
{container="zebu-backend-prod"} | json | event="Trade executed" | level="error"
```

### Step 3: Check Related Logs

```logql
# All logs for a specific correlation ID
{container="zebu-backend-prod"} | json | correlation_id="abc-123-def"

# Request flow for failed requests
{container="zebu-backend-prod"} | json | status_code >= 500
```

### Step 4: Investigate Root Cause

Common error sources:

**Database Issues**:
```logql
{container="zebu-postgres-prod"} |~ "ERROR|FATAL"
```

**External API Failures**:
```logql
{container="zebu-backend-prod"} | json | logger="zebu.adapters.outbound.market_data.alpha_vantage_adapter" | level="error"
```

**Authentication Errors**:
```logql
{container="zebu-backend-prod"} | json | event =~ ".*auth.*" | level="error"
```

### Step 5: Determine Action

| Error Type | Action |
|------------|--------|
| Transient network issue | Monitor, likely self-resolving |
| Database connection pool exhausted | Restart backend container |
| Alpha Vantage API down | Enable extended cache TTL |
| Code bug | Rollback deployment or hotfix |
| Rate limit exceeded | Implement backoff, increase cache TTL |

## Checking Cache Performance

### Cache Hit Ratio

```logql
# Cache hits in last hour
sum(count_over_time({container="zebu-backend-prod"} | json | event="Price fetched from cache" [1h]))

# Total price fetches
sum(count_over_time({container="zebu-backend-prod"} | json | event =~ "Price fetched.*" [1h]))

# Calculate ratio manually or use Grafana panel
```

**Target**: > 90% cache hit ratio during trading hours

**If cache hit ratio is low (<80%)**:

1. **Check Redis is running**:
   ```logql
   {container="zebu-redis-prod"}
   ```
   
   If no logs: Redis container may be down.

2. **Check for cache evictions**:
   ```logql
   {container="zebu-redis-prod"} |~ "evict"
   ```
   
   High evictions = Redis out of memory.

3. **Review cache TTL settings**:
   ```bash
   # Check current TTL configuration
   ssh root@192.168.4.112
   docker logs zebu-backend-prod | grep -i "ttl"
   ```

### Cache Performance Optimization

**Increase TTL for stable data**:
- Historical prices (> 1 day old): 7 days TTL
- Recent prices: 1 hour TTL
- Current prices (intraday): 5 minutes TTL

**Warm cache proactively**:
- Pre-fetch popular tickers on application start
- Background job to refresh cache before expiry

## Monitoring API Rate Limits

### Alpha Vantage Usage

```logql
# API calls in last hour
count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [1h])

# API calls today (approximate - last 12 hours)
count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [12h])
```

**Free Tier Limits**:
- 5 calls/minute
- 500 calls/day

### Rate Limit Warnings

```logql
# Rate limit warnings
{container="zebu-backend-prod"} | json | event =~ ".*rate limit.*" | level="warning"

# Requests served from stale cache due to rate limiting
{container="zebu-backend-prod"} | json | event="Price fetched from cache" | source="cache" | level="warning"
```

### Mitigating Rate Limit Issues

**Immediate Actions**:

1. **Extend cache TTL** (temporary hotfix):
   ```bash
   # Update cache TTL in backend configuration
   # Requires code change + redeploy (not immediate)
   ```

2. **Reduce API calls**:
   - Batch price requests where possible
   - Increase cache duration during high-traffic periods

**Long-term Solutions**:

1. **Upgrade to paid tier** (Alpha Vantage):
   - $49/month for 500 calls/minute
   - $149/month for 1200 calls/minute

2. **Add alternative data source**:
   - Fallback to different provider
   - Hybrid approach (multiple providers)

3. **Optimize caching strategy**:
   - Intelligent cache warming
   - Predictive pre-fetching for popular tickers

## Reviewing User Activity

### Active Users

```logql
# Unique correlation IDs (proxy for active sessions) in last hour
count(count_over_time({container="zebu-backend-prod"} | json [1h]) by (correlation_id))
```

### Trading Activity

```logql
# Trades executed today
count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h])

# Top traded tickers
topk(10, count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h]) by (ticker))

# Trade volume by action
sum by (action) (count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h]))
```

### Portfolio Operations

```logql
# New portfolios created
count_over_time({container="zebu-backend-prod"} | json | event="Portfolio created" [24h])

# Portfolio value calculations
{container="zebu-backend-prod"} | json | event="Portfolio value calculated"
```

### Performance Metrics

```logql
# Average request duration
avg_over_time({container="zebu-backend-prod"} | json | unwrap duration_seconds [5m])

# P95 request duration
quantile_over_time(0.95, {container="zebu-backend-prod"} | json | unwrap duration_seconds [5m])

# Slow requests (> 1 second)
{container="zebu-backend-prod"} | json | duration_seconds > 1
```

## Emergency Response

### Backend Service Unresponsive

**Symptoms**:
- No logs appearing in Grafana
- Users reporting 502/504 errors
- Health check failing

**Diagnosis**:

```bash
ssh root@192.168.4.112

# Check container status
docker ps -a | grep zebu-backend

# Check container logs
docker logs zebu-backend-prod --tail 100

# Check container health
docker inspect zebu-backend-prod | grep Health -A 10
```

**Resolution**:

```bash
# Option 1: Restart container
docker restart zebu-backend-prod

# Option 2: Check and restart all services
cd /opt/zebu
docker-compose restart

# Option 3: Full redeployment (if restart doesn't work)
./scripts/proxmox-vm/deploy.sh
```

### Database Connection Issues

**Symptoms**:
- Errors like "connection pool exhausted"
- "unable to connect to database"

**Diagnosis**:

```logql
{container="zebu-postgres-prod"} |~ "connection|error"
```

```bash
# Check PostgreSQL status
docker exec zebu-postgres-prod pg_isready

# Check active connections
docker exec zebu-postgres-prod psql -U zebu -c "SELECT count(*) FROM pg_stat_activity;"
```

**Resolution**:

```bash
# Restart PostgreSQL (if safe)
docker restart zebu-postgres-prod

# Check connection pool settings in backend config
# Ensure max_connections in PostgreSQL >= connection pool size
```

### Redis Cache Unavailable

**Symptoms**:
- High Alpha Vantage API usage
- Slow response times
- Cache-related errors

**Diagnosis**:

```logql
{container="zebu-redis-prod"}
```

```bash
# Check Redis status
docker exec zebu-redis-prod redis-cli ping
# Should return: PONG
```

**Resolution**:

```bash
# Restart Redis
docker restart zebu-redis-prod

# Verify cache is working
docker exec zebu-redis-prod redis-cli INFO stats
```

### High Memory Usage

**Symptoms**:
- OOMKilled containers
- Slow performance

**Diagnosis**:

```bash
# Check memory usage
docker stats --no-stream

# Check system memory
free -h
```

**Resolution**:

```bash
# Identify memory-heavy container
docker stats --no-stream | sort -k 4 -hr

# Restart heavy containers
docker restart [container-name]

# If persistent, investigate memory leak
docker logs [container-name] | grep -i "memory\|oom"
```

## Common LogQL Queries

### Filtering

```logql
# Logs from specific container
{container="zebu-backend-prod"}

# Logs from multiple containers
{container=~"zebu-(backend|frontend)-prod"}

# Logs with specific level
{container="zebu-backend-prod"} | json | level="error"

# Logs matching text pattern
{container="zebu-backend-prod"} |= "Trade executed"

# Logs NOT matching pattern
{container="zebu-backend-prod"} != "health check"
```

### Aggregations

```logql
# Count logs over time
count_over_time({container="zebu-backend-prod"} [5m])

# Rate of log entries
rate({container="zebu-backend-prod"} [5m])

# Sum numeric field
sum(count_over_time({container="zebu-backend-prod"} | json | unwrap duration_ms [5m]))

# Average
avg_over_time({container="zebu-backend-prod"} | json | unwrap duration_ms [5m])

# Top N by label
topk(10, count_over_time({container="zebu-backend-prod"} [1h]) by (event))
```

### Time Ranges

```logql
# Last 5 minutes
{container="zebu-backend-prod"} [5m]

# Last hour
{container="zebu-backend-prod"} [1h]

# Last 24 hours
{container="zebu-backend-prod"} [24h]

# Specific time range (use Grafana UI time picker)
```

### Advanced Patterns

```logql
# Regex extraction
{container="zebu-backend-prod"} | regexp "ticker: (?P<ticker>[A-Z]+)"

# Line format
{container="zebu-backend-prod"} | json | line_format "{{.timestamp}}: {{.event}}"

# Label extraction
{container="zebu-backend-prod"} | json | label_format ticker=ticker

# Conditional filtering
{container="zebu-backend-prod"} | json | duration_ms > 1000 | event="Trade executed"
```

## Escalation Path

| Severity | Response Time | Action |
|----------|---------------|--------|
| **Critical** (service down) | Immediate | 1. Restart services<br>2. Notify on-call engineer<br>3. Investigate root cause |
| **High** (errors affecting users) | < 15 minutes | 1. Identify scope<br>2. Implement mitigation<br>3. Create incident report |
| **Medium** (degraded performance) | < 1 hour | 1. Monitor trends<br>2. Schedule fix in next sprint<br>3. Document findings |
| **Low** (minor issues) | < 24 hours | 1. Log in backlog<br>2. Address during maintenance window |

## Post-Incident Review

After resolving any P0/P1 incident:

1. **Document timeline**:
   - When issue first detected
   - Actions taken
   - When service restored

2. **Root cause analysis**:
   - What caused the issue?
   - Why did monitoring not catch it earlier?
   - What was the blast radius?

3. **Preventive measures**:
   - What can prevent recurrence?
   - What alerts should be added?
   - What documentation needs updating?

4. **Share learnings**:
   - Update this runbook
   - Team postmortem
   - Improve monitoring/alerting

## Useful Resources

- [Grafana Cloud Setup Guide](./grafana-cloud-setup.md)
- [LogQL Documentation](https://grafana.com/docs/loki/latest/logql/)
- [Zebu Architecture Docs](../architecture/)
- [Deployment Scripts](../../scripts/proxmox-vm/)
