# Alert Configuration Guide

This guide documents the alert rules configured in Grafana Cloud for Zebu production monitoring.

## Alert Philosophy

Alerts should:
- **Actionable**: Each alert should require human intervention
- **Urgent**: Alerts indicate issues that need immediate attention
- **Specific**: Clear diagnosis and remediation path
- **Low noise**: Avoid false positives that cause alert fatigue

## Alert Severity Levels

| Severity | Response Time | Example |
|----------|---------------|---------|
| **Critical** | Immediate (< 5 min) | Service down, data loss |
| **High** | < 15 minutes | High error rate, API quota exceeded |
| **Medium** | < 1 hour | Degraded performance, high latency |
| **Low** | < 24 hours | Cache inefficiency, minor issues |

## Configured Alerts

### 1. High Error Rate (High Severity)

**Alert Name**: `Backend High Error Rate`

**Description**: Backend error rate exceeds acceptable threshold, indicating systemic issues.

**Query**:
```logql
sum(rate({container="zebu-backend-prod"} | json | level="error" [5m])) > 0.1
```

**Threshold**: > 0.1 errors/second (6 errors/minute)

**Duration**: 5 minutes

**Notification**:
- **Summary**: "Backend error rate is above 0.1 errors/second"
- **Description**: "Error rate: {{ $value }} errors/sec. Check logs for error patterns."
- **Severity**: High
- **Contact Point**: Email + Slack (if configured)

**Remediation**:
1. Check error logs in Grafana: `{container="zebu-backend-prod"} | json | level="error"`
2. Identify top error types: Use Application Overview dashboard → Top 10 Errors panel
3. Review recent deployments for code changes
4. Check external service health (database, Redis, Alpha Vantage)
5. If deployment-related: Consider rollback
6. If external service: Implement graceful degradation

**False Positive Scenarios**:
- Load testing or intentional error injection
- Brief spike during deployment rollover

**Tuning**: If persistent false positives, increase threshold to 0.15 or duration to 10 minutes.

---

### 2. Alpha Vantage Rate Limit Warning (High Severity)

**Alert Name**: `Alpha Vantage Rate Limit Exceeded`

**Description**: Alpha Vantage API rate limit has been hit, users may see stale data or errors.

**Query**:
```logql
count_over_time({container="zebu-backend-prod"} | json | event =~ ".*rate limit.*" [5m]) > 0
```

**Threshold**: > 0 rate limit warnings

**Duration**: 1 minute

**Notification**:
- **Summary**: "Alpha Vantage rate limit exceeded"
- **Description**: "Rate limit warnings detected. Users may receive stale cached data. Check API usage."
- **Severity**: High
- **Contact Point**: Email + Slack

**Remediation**:
1. **Immediate**: Verify stale cache is serving requests (degraded mode)
2. **Check usage**:
   ```logql
   count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [24h])
   ```
3. **Short-term**: Increase cache TTL to reduce API calls
4. **Long-term**: Consider upgrading to paid Alpha Vantage tier or adding alternative data source

**Prevention**:
- Monitor daily API usage proactively
- Implement cache warming for popular tickers
- Set up quota alerts at 80% and 90% thresholds

---

### 3. Backend Service Down (Critical Severity)

**Alert Name**: `Backend Service Health Check Failed`

**Description**: Backend container is not producing logs, likely down or unhealthy.

**Query**:
```logql
count_over_time({container="zebu-backend-prod"} [5m]) < 10
```

**Threshold**: < 10 log entries in 5 minutes

**Duration**: 5 minutes

**Notification**:
- **Summary**: "Backend service may be down - no logs detected"
- **Description**: "Backend container not producing logs. Service may be down or critically unhealthy."
- **Severity**: Critical
- **Contact Point**: Email + Slack + PagerDuty (if configured)

**Remediation**:
1. **Check container status**:
   ```bash
   ssh root@192.168.4.112
   docker ps -a | grep zebu-backend
   ```

2. **Check container logs**:
   ```bash
   docker logs zebu-backend-prod --tail 100
   ```

3. **Restart if crashed**:
   ```bash
   docker restart zebu-backend-prod
   ```

4. **If restart fails**: Check for disk space, memory, or configuration issues

5. **If persistent**: Full redeployment
   ```bash
   cd /opt/zebu
   docker-compose down
   docker-compose up -d
   ```

**Escalation**: If service doesn't recover within 15 minutes, notify senior engineer.

---

### 4. High API Response Time (Medium Severity)

**Alert Name**: `API Response Time Degraded`

**Description**: P95 response time exceeds acceptable threshold, users experiencing slow performance.

**Query**:
```logql
quantile_over_time(0.95, {container="zebu-backend-prod"} | json | unwrap duration_seconds [5m]) > 1.0
```

**Threshold**: P95 > 1 second

**Duration**: 5 minutes

**Notification**:
- **Summary**: "API response time degraded (P95 > 1s)"
- **Description**: "P95 latency: {{ $value }}s. Investigate slow queries or external services."
- **Severity**: Medium
- **Contact Point**: Email

**Remediation**:
1. **Check database performance**:
   ```logql
   {container="zebu-postgres-prod"} |~ "duration.*ms" | regexp "duration: (?P<duration>[0-9.]+) ms" | duration > 1000
   ```

2. **Check Alpha Vantage latency**:
   ```logql
   quantile_over_time(0.95, {container="zebu-backend-prod"} | json | event="Alpha Vantage API called" | unwrap duration_ms [5m])
   ```

3. **Check cache hit ratio** - low ratio = more slow API calls

4. **Review slow endpoints**:
   ```logql
   {container="zebu-backend-prod"} | json | duration_seconds > 1.0
   ```

**Tuning**: Adjust threshold based on baseline performance (e.g., 1.5s if typical P95 is 0.8s).

---

### 5. Database Connection Pool Exhaustion (High Severity)

**Alert Name**: `Database Connection Pool Exhausted`

**Description**: Database connection pool is exhausted, requests are failing or queueing.

**Query**:
```logql
count_over_time({container="zebu-backend-prod"} | json | error =~ ".*connection pool.*exhausted.*" [5m]) > 0
```

**Threshold**: > 0 pool exhaustion errors

**Duration**: 2 minutes

**Notification**:
- **Summary**: "Database connection pool exhausted"
- **Description**: "Connection pool errors detected. Increase pool size or investigate connection leaks."
- **Severity**: High
- **Contact Point**: Email + Slack

**Remediation**:
1. **Check active connections**:
   ```bash
   docker exec zebu-postgres-prod psql -U zebu -c "SELECT count(*) FROM pg_stat_activity;"
   ```

2. **Check for long-running queries**:
   ```bash
   docker exec zebu-postgres-prod psql -U zebu -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC;"
   ```

3. **Temporary fix**: Restart backend to reset connections
   ```bash
   docker restart zebu-backend-prod
   ```

4. **Long-term**: Increase connection pool size in backend configuration

---

### 6. Redis Cache Unavailable (High Severity)

**Alert Name**: `Redis Cache Service Down`

**Description**: Redis container is not producing logs, cache likely unavailable.

**Query**:
```logql
count_over_time({container="zebu-redis-prod"} [5m]) < 5
```

**Threshold**: < 5 log entries in 5 minutes

**Duration**: 3 minutes

**Notification**:
- **Summary**: "Redis cache service may be down"
- **Description**: "Redis not producing logs. Cache unavailable - expect high API usage."
- **Severity**: High
- **Contact Point**: Email + Slack

**Remediation**:
1. **Check Redis status**:
   ```bash
   docker exec zebu-redis-prod redis-cli ping
   ```

2. **Restart if unresponsive**:
   ```bash
   docker restart zebu-redis-prod
   ```

3. **Monitor impact**: Expect increased Alpha Vantage API calls and slower responses

4. **Verify recovery**: Check cache hit ratio returns to normal (>90%)

---

### 7. Excessive Alpha Vantage Usage (Medium Severity)

**Alert Name**: `Alpha Vantage Daily Quota Warning`

**Description**: Approaching daily API quota limit (80% threshold).

**Query**:
```logql
(count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [24h]) / 500) > 0.8
```

**Threshold**: > 80% of daily quota (400 calls)

**Duration**: 5 minutes

**Notification**:
- **Summary**: "Alpha Vantage API usage at 80% of daily quota"
- **Description**: "Current usage: {{ $value * 500 }} / 500 calls. Implement caching optimizations."
- **Severity**: Medium
- **Contact Point**: Email

**Remediation**:
1. **Monitor usage trend**: Check if spike or steady increase
2. **Review cache configuration**: Ensure proper TTLs
3. **Identify heavy tickers**:
   ```logql
   topk(10, count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [24h]) by (ticker))
   ```
4. **Consider**: Pre-warming cache for popular tickers, increasing TTL

**Prevention**: Set up proactive monitoring at 70%, 80%, and 90% thresholds.

---

## Alert Configuration in Grafana

### Creating an Alert Rule

1. Navigate to **Alerting** → **Alert Rules** → **New Alert Rule**

2. **Set Alert Name** (e.g., "Backend High Error Rate")

3. **Define Query**:
   - Data source: Loki
   - Query: Enter LogQL query from above
   - Set time range (e.g., last 5 minutes)

4. **Set Conditions**:
   - Threshold: Enter threshold value
   - Comparator: `>` or `<` based on alert type
   - For: Duration (e.g., 5 minutes)

5. **Add Labels**:
   - `severity`: critical / high / medium / low
   - `service`: backend / database / cache / api
   - `team`: platform / on-call

6. **Write Summary and Description** (use templating for dynamic values)

7. **Preview** the alert to verify it works

8. **Save** the alert rule

### Alert Annotations

Add annotations to alerts for better context:

```yaml
summary: Backend error rate is above threshold
description: |
  Current error rate: {{ $value }} errors/second

  Threshold: 0.1 errors/second

  Check logs: https://your-grafana-instance.grafana.net/explore?...

  Runbook: https://github.com/TimChild/PaperTrade/blob/main/docs/monitoring/monitoring-runbook.md#investigating-high-error-rates
```

### Alert Grouping

Group related alerts to reduce noise:

```yaml
group_by: ['service', 'severity']
group_wait: 30s
group_interval: 5m
repeat_interval: 4h
```

## Notification Channels

### Email Configuration

1. Go to **Alerting** → **Contact Points**
2. Create contact point:
   - Name: `Email - Production Alerts`
   - Type: Email
   - Addresses: `ops-team@example.com`

### Slack Configuration

1. Create Slack incoming webhook in your workspace
2. In Grafana:
   - Name: `Slack - #prod-alerts`
   - Type: Slack
   - Webhook URL: `https://hooks.slack.com/services/...`
   - Channel: `#prod-alerts`
   - Mention: `@channel` (for critical only)

### PagerDuty (Optional)

For critical alerts requiring 24/7 response:

1. Set up PagerDuty service and integration key
2. In Grafana:
   - Name: `PagerDuty - On-Call`
   - Type: PagerDuty
   - Integration Key: Your key
   - Severity: Map Grafana severity to PagerDuty

## Notification Policies

Route alerts based on severity:

```yaml
# Default policy
contact_point: Email - Production Alerts
group_by: ['service']

# Override for critical alerts
- match:
    severity: critical
  contact_point: PagerDuty - On-Call
  continue: true

# Override for high severity
- match:
    severity: high
  contact_point: Slack - #prod-alerts
  continue: true
```

## Testing Alerts

### Simulate High Error Rate

```bash
# SSH into production server
ssh root@192.168.4.112

# Generate errors
for i in {1..20}; do
  docker exec zebu-backend-prod python -c "
import logging
logging.basicConfig()
logger = logging.getLogger('test')
logger.error('Test alert error')
"
  sleep 1
done
```

### Simulate Rate Limit

```bash
# Trigger many API calls to hit rate limit
# (Requires access to test user account)
curl -X POST https://zebutrader.com/api/v1/portfolios/test-id/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "action": "BUY", "quantity": 1}'
```

### Verify Alert Delivery

1. **Check Grafana UI**: Alerting → Alert Rules → View state
2. **Check notification channel**: Email inbox, Slack channel
3. **Verify timing**: Alert should fire after threshold duration
4. **Test recovery**: Alert should clear when condition resolves

## Alert Maintenance

### Weekly Review

- Check alert firing frequency
- Identify false positives
- Tune thresholds as needed
- Verify all notifications are delivered

### Monthly Audit

- Review alert coverage (are we monitoring all critical services?)
- Update runbook links in alert descriptions
- Test notification channels
- Archive obsolete alerts

### After Incidents

- Review which alerts fired (or should have fired)
- Add new alerts for gaps discovered
- Update thresholds based on actual impact
- Document learnings in runbook

## Muting Alerts

### Scheduled Maintenance

When performing planned maintenance, silence alerts:

1. Go to **Alerting** → **Silences** → **New Silence**
2. Set duration (e.g., 2 hours)
3. Add matchers: `service=backend`, `severity!=critical`
4. Comment: "Scheduled deployment - backend upgrade"

### Load Testing

Silence alerts during load tests to avoid noise:

```yaml
matchers:
  - service=backend
  - severity=~medium|low
duration: 1h
comment: "Load testing in progress"
```

## Best Practices

1. **Start conservative**: Begin with higher thresholds, tune down based on observed patterns
2. **Include runbook links**: Every alert should link to remediation steps
3. **Use templating**: Include context (values, timestamps) in alert messages
4. **Test regularly**: Ensure alerts fire correctly and notifications are delivered
5. **Review and iterate**: Alert thresholds should evolve with system behavior
6. **Avoid alert fatigue**: Too many alerts = ignored alerts
7. **Document escalation**: Clear escalation path for different severity levels

## Related Documentation

- [Grafana Cloud Setup Guide](./grafana-cloud-setup.md)
- [Monitoring Runbook](./monitoring-runbook.md)
- [Dashboard Templates](./dashboards/)
