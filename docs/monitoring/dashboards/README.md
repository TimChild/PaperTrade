# Grafana Dashboard Import Guide

This directory contains production-ready Grafana dashboard JSON files for the Zebu application monitoring stack.

## Available Dashboards

### 1. Application Overview (`application-overview.json`)
**Purpose**: Comprehensive view of Zebu application health and performance  
**Panels**: 20 panels across 5 rows  
**Refresh**: 30 seconds  
**Default Time Range**: Last 1 hour

**Rows**:
- System Health (Request rate, error rate, service uptime)
- Performance Metrics (Response times P50/P95/P99, slow requests, heatmap)
- Cache Performance (Hit ratio, hits vs misses, Redis status)
- Error Analysis (Top errors, error logs, errors by endpoint)
- HTTP Status Codes (Distribution, 4xx/5xx errors over time)

### 2. Trading Activity (`trading-activity.json`)
**Purpose**: Monitor user trading behavior, portfolio operations, and trading patterns  
**Panels**: 23 panels across 6 rows  
**Refresh**: 1 minute  
**Default Time Range**: Last 24 hours

**Rows**:
- Trading Volume (Trades executed, volume over time, buy vs sell)
- Popular Tickers (Top 10, volume by ticker, unique tickers)
- Portfolio Operations (New portfolios, active portfolios, value calculations)
- Trade Performance (Execution time, failed trades, failure reasons)
- User Activity (Active users, request patterns)
- Trading Patterns (Trade size distribution, average value, market cap preference)

### 3. External Services (`external-services.json`)
**Purpose**: Monitor external dependencies (Alpha Vantage, PostgreSQL, Redis)  
**Panels**: 31 panels across 6 rows  
**Refresh**: 1 minute  
**Default Time Range**: Last 6 hours

**Rows**:
- Alpha Vantage API (Call count, rate, warnings, response times, errors)
- PostgreSQL Database (Connection status, logs, pool usage, slow queries, errors)
- Redis Cache (Status, operations, logs, memory usage, evictions)
- API Rate Limit Consumption (Quota usage, headroom, stale cache, reset timer)
- External API Health (Availability, error types, database fallback)
- Network & Connectivity (Network errors, DNS failures, SSL/TLS errors)

## Prerequisites

1. **Grafana Cloud Account**: Access to your Grafana Cloud instance (e.g., `logs-prod-042.grafana.net`)
2. **Loki Data Source**: Must be configured and accessible
3. **Promtail**: Should be shipping logs to Grafana Cloud (see `docs/monitoring/grafana-cloud-setup.md`)

## How to Import Dashboards

### Option 1: Via Grafana UI (Recommended)

1. **Login to Grafana Cloud**:
   ```
   https://your-instance.grafana.net
   ```

2. **Navigate to Dashboards**:
   - Click the **"+"** icon in the left sidebar
   - Select **"Import"**

3. **Upload JSON File**:
   - Click **"Upload JSON file"**
   - Select one of the dashboard files from this directory:
     - `application-overview.json`
     - `trading-activity.json`
     - `external-services.json`

4. **Configure Data Source**:
   - In the **"Loki"** dropdown, select your Loki data source
   - Usually named `grafanacloud-yourorg-logs` or similar

5. **Import**:
   - Click **"Import"**
   - Dashboard will be created and opened automatically

6. **Verify**:
   - Check that panels are rendering correctly
   - Confirm queries are returning data
   - Adjust time range if needed

### Option 2: Via Grafana API

```bash
# Set your Grafana Cloud details
GRAFANA_URL="https://your-instance.grafana.net"
GRAFANA_API_KEY="your-api-key"

# Import a dashboard
curl -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d @application-overview.json
```

**Note**: You'll need to create a Grafana API key with "Editor" permissions first.

### Option 3: Via Grafana CLI

```bash
# Install grafana-cli if not already installed
# Then import a dashboard
grafana-cli dashboards import application-overview.json
```

## Post-Import Configuration

### 1. Set Data Source Variable

If the data source UID doesn't match, update the `${DS_LOKI}` variable:

1. Open the dashboard
2. Click the **gear icon** (Dashboard settings) in the top right
3. Go to **"Variables"**
4. Edit the `DS_LOKI` variable to point to your Loki data source

### 2. Verify Container Names

The dashboards use `zebu-backend-prod`, `zebu-postgres-prod`, and `zebu-redis-prod` as container names. If your containers have different names:

1. Edit the dashboard variables (gear icon → Variables)
2. Update the `$container` variable default value
3. Or use the dropdown in the dashboard to select the correct container

### 3. Adjust Time Ranges

Default time ranges:
- **Application Overview**: 1 hour
- **Trading Activity**: 24 hours  
- **External Services**: 6 hours

To change:
- Click the **time picker** in the top right
- Select a new time range
- Click **"Save dashboard"** (disk icon) to persist

### 4. Configure Alerts (Optional)

The dashboards include threshold configurations but not alert rules. To set up alerts:

1. Click on a panel with thresholds (e.g., "Error Rate")
2. Click **"Edit"** (pencil icon)
3. Go to the **"Alert"** tab
4. Click **"Create alert rule from this panel"**
5. Configure notification channels

See `docs/monitoring/alert-configuration.md` for recommended alert rules.

## Troubleshooting

### No Data Appearing

**Problem**: Panels show "No data"

**Solutions**:
1. Verify Promtail is shipping logs:
   ```bash
   # Check Promtail status
   docker logs zebu-promtail-prod
   ```

2. Check Loki data source:
   - Go to **Configuration** → **Data Sources** → **Loki**
   - Click **"Save & Test"**
   - Should show "Data source is working"

3. Verify log labels:
   - Run a simple query in **Explore**:
     ```logql
     {container="zebu-backend-prod"}
     ```
   - If no results, check your Promtail configuration

### Query Errors

**Problem**: Panel shows "Query error" or "Bad request"

**Solutions**:
1. Check LogQL syntax in the query
2. Ensure all labels exist in your logs (e.g., `event`, `level`, `ticker`)
3. Some panels require specific log fields - see markdown specs for details

### Panels Overlapping

**Problem**: Dashboard layout looks broken

**Solutions**:
1. Try refreshing the page
2. Adjust browser zoom to 100%
3. Re-import the dashboard (it will update the existing one)

### Variable Not Working

**Problem**: Template variable not filtering correctly

**Solutions**:
1. Check the variable query syntax
2. Ensure the variable is used in panel queries (look for `${variable_name}`)
3. Try resetting the variable to its default value

## Customization

### Adding Panels

1. Click **"Add panel"** in the top right
2. Configure your query using LogQL
3. Select visualization type
4. Click **"Apply"**

### Modifying Queries

1. Click on a panel title → **"Edit"**
2. Modify the LogQL query in the query editor
3. Click **"Apply"** to save changes

### Changing Colors/Thresholds

1. Edit the panel
2. Go to **"Field"** or **"Overrides"** tab
3. Adjust color schemes or threshold values
4. Click **"Apply"**

### Exporting Modified Dashboards

After making changes, export the updated dashboard:

1. Click the **gear icon** (Dashboard settings)
2. Click **"JSON Model"** in the left sidebar
3. Click **"Copy to Clipboard"**
4. Save to a new file or update the existing one

## Validation

Before committing changes to dashboard JSON files, validate them:

```bash
# Validate JSON syntax
jq . < application-overview.json > /dev/null && echo "✓ Valid JSON"

# Pretty-print for easier reading
jq . < application-overview.json | less

# Count number of panels
jq '.dashboard.panels | length' < application-overview.json
```

## Related Documentation

- **Grafana Cloud Setup**: `docs/monitoring/grafana-cloud-setup.md`
- **Alert Configuration**: `docs/monitoring/alert-configuration.md`
- **Monitoring Runbook**: `docs/monitoring/monitoring-runbook.md`
- **Dashboard Specs** (Markdown reference):
  - `application-overview.md`
  - `trading-activity.md`
  - `external-services.md`

## Support

### Grafana Documentation
- **LogQL Query Language**: https://grafana.com/docs/loki/latest/query/
- **Dashboard JSON Schema**: https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/create-dashboard/
- **Panel Types**: https://grafana.com/docs/grafana/latest/panels-visualizations/

### Internal Resources
- Slack: `#zebu-monitoring`
- On-call: See PagerDuty rotation
- Runbook: `docs/monitoring/monitoring-runbook.md`

## Changelog

### 2026-01-18
- Initial creation of all three dashboard JSON files
- Converted from markdown specifications
- Tested basic JSON validation
- Added comprehensive import guide

## License

Internal use only - Zebu Platform
