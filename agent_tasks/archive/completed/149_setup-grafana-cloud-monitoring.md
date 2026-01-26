# Task 149: Setup Grafana Cloud Monitoring & Observability

**Agent**: quality-infra
**Priority**: HIGH
**Date**: 2026-01-17
**Related**: Production deployment (zebutrader.com), PR #152 (structlog migration)

## Problem Statement

Zebu is now live in production at zebutrader.com, but we have **zero visibility** into:
- Application errors and exceptions
- API request rates and latency
- Cache hit/miss ratios
- Rate limit warnings from Alpha Vantage
- User activity patterns
- System resource usage

Without monitoring, we're flying blind and can't:
1. Detect issues before users report them
2. Understand usage patterns for optimization
3. Debug production-only problems
4. Make data-driven decisions about caching/scaling

## Objective

Set up **Grafana Cloud Free Tier** monitoring with:
- Log aggregation (Loki) for structured logs
- Basic dashboards for key metrics
- Alerts for critical issues

**Budget**: $0/month (free tier: 50GB logs, 10k series, 14-day retention)

## Background: Current Logging

Backend already has **structlog** with JSON logging configured (PR #152):

```python
# backend/src/zebu/infrastructure/logging.py
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

Logs include structured data:
```json
{
  "event": "Price fetched from cache",
  "timestamp": "2026-01-17T10:30:45Z",
  "level": "info",
  "ticker": "AAPL",
  "source": "redis",
  "ttl_seconds": 3600
}
```

## Requirements

### 1. Grafana Cloud Setup

**Account Creation**:
1. Sign up at https://grafana.com/auth/sign-up/create-user
2. Create free cloud stack (select region closest to deployment)
3. Note credentials:
   - Stack URL (e.g., `https://yourstack.grafana.net`)
   - Instance ID
   - API key

**Services to Enable**:
- ✅ Grafana (dashboards and visualization)
- ✅ Loki (log aggregation)
- ✅ Prometheus (metrics - optional for Phase 1)

### 2. Install Promtail on Proxmox VM

Promtail ships logs from the VM to Grafana Cloud Loki.

**Installation Script**: `scripts/monitoring/install-promtail.sh`

```bash
#!/bin/bash
set -e

# Configuration
LOKI_URL="https://logs-prod-us-central1.grafana.net"
LOKI_USERNAME="your-instance-id"  # From Grafana Cloud
LOKI_API_KEY="your-api-key"       # From Grafana Cloud

# Download Promtail
PROMTAIL_VERSION="2.9.3"
wget https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-linux-amd64.zip
unzip promtail-linux-amd64.zip
sudo mv promtail-linux-amd64 /usr/local/bin/promtail
sudo chmod +x /usr/local/bin/promtail

# Create config directory
sudo mkdir -p /etc/promtail

# Create Promtail config
cat <<EOF | sudo tee /etc/promtail/config.yml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: ${LOKI_URL}/loki/api/v1/push
    basic_auth:
      username: ${LOKI_USERNAME}
      password: ${LOKI_API_KEY}

scrape_configs:
  # Zebu Backend Logs (JSON format)
  - job_name: zebu-backend
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(zebu-backend-prod)'
        action: keep
      - source_labels: ['__meta_docker_container_name']
        target_label: container
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: stream
    pipeline_stages:
      - json:
          expressions:
            level: level
            timestamp: timestamp
            event: event
            logger: logger
      - labels:
          level:
          logger:
      - timestamp:
          source: timestamp
          format: RFC3339

  # Zebu Frontend Logs (nginx access logs)
  - job_name: zebu-frontend
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(zebu-frontend-prod)'
        action: keep
      - source_labels: ['__meta_docker_container_name']
        target_label: container
    pipeline_stages:
      - regex:
          expression: '^(?P<remote_addr>[\w\.]+) - (?P<remote_user>[^ ]*) \[(?P<time_local>.*)\] "(?P<method>[^ ]*) (?P<path>[^ ]*) (?P<protocol>[^ ]*)" (?P<status>[\d]+) (?P<bytes_sent>[\d]+)'
      - labels:
          method:
          status:

  # PostgreSQL Logs
  - job_name: zebu-postgres
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(zebu-postgres-prod)'
        action: keep
      - source_labels: ['__meta_docker_container_name']
        target_label: container

  # Redis Logs
  - job_name: zebu-redis
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(zebu-redis-prod)'
        action: keep
      - source_labels: ['__meta_docker_container_name']
        target_label: container
EOF

# Create systemd service
cat <<EOF | sudo tee /etc/systemd/system/promtail.service
[Unit]
Description=Promtail log shipper
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start Promtail
sudo systemctl daemon-reload
sudo systemctl enable promtail
sudo systemctl start promtail

echo "✓ Promtail installed and started"
echo "Check status: sudo systemctl status promtail"
echo "View logs: sudo journalctl -u promtail -f"
```

**Deployment**:
```bash
# Run from local machine
scp scripts/monitoring/install-promtail.sh root@192.168.4.112:/tmp/
ssh root@192.168.4.112 'bash /tmp/install-promtail.sh'
```

### 3. Create Grafana Dashboards

**Dashboard 1: Application Overview**

Panels:
1. **Request Rate** (logs-based)
   - Query: `rate({container="zebu-backend-prod"} |= "Request received" [5m])`
   - Visualization: Time series

2. **Error Rate** (logs-based)
   - Query: `rate({container="zebu-backend-prod"} | json | level="error" [5m])`
   - Visualization: Time series with alert threshold

3. **Cache Hit Ratio** (logs-based)
   - Query: `sum(rate({container="zebu-backend-prod"} |= "Price fetched from cache" | json | source="redis" [5m])) / sum(rate({container="zebu-backend-prod"} |= "Price fetched" [5m]))`
   - Visualization: Gauge (0-100%)

4. **API Response Times** (logs-based)
   - Query: `{container="zebu-backend-prod"} | json | __error__="" | line_format "{{.duration_ms}}"`
   - Visualization: Heatmap

5. **Top Errors** (logs-based)
   - Query: `topk(10, count_over_time({container="zebu-backend-prod"} | json | level="error" [1h]) by (event))`
   - Visualization: Table

**Dashboard 2: Trading Activity**

Panels:
1. **Trades Executed** (logs-based)
   - Query: `count_over_time({container="zebu-backend-prod"} |= "Trade executed" [1h])`
   - Visualization: Time series

2. **Trade Volume by Ticker** (logs-based)
   - Query: `sum by (ticker) (count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [24h]))`
   - Visualization: Bar chart

3. **Portfolio Creations** (logs-based)
   - Query: `count_over_time({container="zebu-backend-prod"} |= "Portfolio created" [24h])`
   - Visualization: Stat panel

**Dashboard 3: External Services**

Panels:
1. **Alpha Vantage API Calls** (logs-based)
   - Query: `count_over_time({container="zebu-backend-prod"} | json | event="Alpha Vantage API called" [1h])`
   - Visualization: Time series with rate limit line

2. **Alpha Vantage Rate Limit Warnings** (logs-based)
   - Query: `{container="zebu-backend-prod"} | json | level="warning" |= "rate limit"`
   - Visualization: Logs panel

3. **Database Query Performance** (logs-based)
   - Query: `{container="zebu-postgres-prod"} |= "duration" | regexp "duration: (?P<duration>[0-9.]+)"`
   - Visualization: Heatmap

### 4. Configure Alerts

**Alert 1: High Error Rate**
```yaml
name: High Error Rate
condition: rate({container="zebu-backend-prod"} | json | level="error" [5m]) > 0.1
for: 5m
message: "Backend error rate is above 0.1 errors/second"
```

**Alert 2: Alpha Vantage Rate Limit**
```yaml
name: Alpha Vantage Rate Limit Warning
condition: count_over_time({container="zebu-backend-prod"} |= "rate limit exceeded" [5m]) > 0
for: 1m
message: "Alpha Vantage rate limit exceeded - users may see errors"
```

**Alert 3: Service Down**
```yaml
name: Backend Service Down
condition: absent_over_time({container="zebu-backend-prod"} [5m])
for: 5m
message: "Backend container not producing logs - may be down"
```

**Notification Channel**: Email or Slack (configure in Grafana Cloud)

### 5. Add Logging to Key Operations

Enhance existing logs to support dashboards:

**File**: `backend/src/zebu/adapters/inbound/api/routes/trades.py`

```python
@router.post("", response_model=TradeResponse, status_code=201)
async def execute_trade(
    request: TradeRequest,
    use_case: ExecuteTradeUseCase = Depends(get_execute_trade_use_case),
) -> TradeResponse:
    start_time = time.time()

    logger.info(
        "Trade request received",
        ticker=request.ticker,
        action=request.action,
        quantity=float(request.quantity),
    )

    try:
        result = await use_case.execute(request)
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Trade executed",
            ticker=request.ticker,
            action=request.action,
            quantity=float(request.quantity),
            price=float(result.execution_price.amount),
            duration_ms=duration_ms,
        )

        return result
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Trade execution failed",
            ticker=request.ticker,
            action=request.action,
            error=str(e),
            duration_ms=duration_ms,
        )
        raise
```

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

```python
async def get_current_price(self, ticker: Ticker) -> PricePoint:
    # ... existing code ...

    logger.info(
        "Alpha Vantage API called",
        ticker=ticker.symbol,
        endpoint="quote",
        tokens_remaining=self._rate_limiter.tokens,
    )
```

### 6. Documentation

**File**: `docs/monitoring/grafana-cloud-setup.md`

Document:
- Grafana Cloud login URL and credentials (store securely)
- Dashboard URLs
- How to query logs (LogQL basics)
- Common queries for debugging
- Alert notification setup
- Troubleshooting Promtail

**File**: `docs/monitoring/monitoring-runbook.md`

Operational procedures:
- How to investigate high error rates
- How to check cache performance
- How to monitor API rate limits
- How to review user activity
- Emergency response for alerts

## Success Criteria

1. ✅ Promtail running on Proxmox VM and shipping logs to Grafana Cloud
2. ✅ At least 3 dashboards created (Application, Trading, External Services)
3. ✅ Logs visible in Grafana Loki with proper labels
4. ✅ 3 critical alerts configured (errors, rate limits, service health)
5. ✅ Documentation complete and tested
6. ✅ Key operations logging duration and outcomes
7. ✅ Cache hit/miss ratios visible in dashboards

## Testing Strategy

1. **Promtail Installation**:
   ```bash
   ssh root@192.168.4.112
   sudo systemctl status promtail  # Should be active (running)
   sudo journalctl -u promtail -n 50  # Check for errors
   ```

2. **Log Ingestion**:
   - Generate some traffic on zebutrader.com
   - Check Grafana Cloud Explore for logs appearing within 30 seconds
   - Verify JSON parsing works (structured fields visible)

3. **Dashboards**:
   - Execute a few trades
   - Verify "Trades Executed" panel shows activity
   - Check cache hit ratio is >90% after warmup

4. **Alerts**:
   - Simulate an error condition (e.g., invalid API key)
   - Verify alert fires within 5 minutes
   - Check notification received

## Implementation Notes

### LogQL Query Language

Basic examples:
```logql
# All backend logs
{container="zebu-backend-prod"}

# Only errors
{container="zebu-backend-prod"} | json | level="error"

# Specific event
{container="zebu-backend-prod"} | json | event="Trade executed"

# Rate of events
rate({container="zebu-backend-prod"} |= "Trade executed" [5m])

# Aggregate by field
sum by (ticker) (count_over_time({container="zebu-backend-prod"} | json | event="Trade executed" [1h]))
```

### Dashboard JSON Export

Export dashboards to `docs/monitoring/dashboards/` for version control:
- `application-overview.json`
- `trading-activity.json`
- `external-services.json`

This allows easy recreation if dashboards are accidentally deleted.

### Cost Management

Free tier limits:
- **Logs**: 50GB/month ingestion
- **Metrics**: 10,000 series
- **Retention**: 14 days

Estimated usage for Zebu:
- ~100MB/day logs (well under limit)
- ~500 metric series (if we add Prometheus later)

**If approaching limits**:
1. Reduce log verbosity (filter DEBUG logs)
2. Sample high-frequency logs
3. Decrease retention to 7 days

## Related Files

- `scripts/monitoring/install-promtail.sh` (NEW)
- `docs/monitoring/grafana-cloud-setup.md` (NEW)
- `docs/monitoring/monitoring-runbook.md` (NEW)
- `docs/monitoring/dashboards/*.json` (NEW)
- `backend/src/zebu/adapters/inbound/api/routes/trades.py` (MODIFY - add timing logs)
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` (MODIFY - add API call logs)

## Future Enhancements (Out of Scope)

- Prometheus metrics for more granular performance data
- Distributed tracing with Tempo
- Custom metrics instrumentation (StatsD/OpenTelemetry)
- SLO/SLI tracking (99% uptime, p95 latency targets)

## Definition of Done

- [ ] Grafana Cloud account created and configured
- [ ] Promtail installed on Proxmox VM and shipping logs
- [ ] 3+ dashboards created with meaningful panels
- [ ] 3 critical alerts configured with notifications
- [ ] Enhanced logging in trade execution and market data adapters
- [ ] Documentation complete (setup guide + runbook)
- [ ] Logs visible in Grafana Cloud within 30 seconds
- [ ] All dashboards tested with real traffic
