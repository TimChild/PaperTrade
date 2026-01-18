# Task 157: Create Grafana Dashboard JSON Files

**Agent**: quality-infra
**Priority**: MEDIUM
**Date**: 2026-01-18
**Related**: PR #145 (Grafana Cloud monitoring setup), Grafana Cloud instance (logs-prod-042.grafana.net)

## Problem Statement

We have comprehensive markdown documentation for 3 Grafana dashboards, but no importable JSON files. Users must manually recreate 60+ panels by hand, which is error-prone and time-consuming.

**Current State**:
- ✅ Promtail shipping logs to Grafana Cloud
- ✅ Dashboard specifications documented in markdown
- ❌ No ready-to-import JSON dashboard files

**Impact**: Setting up monitoring dashboards takes 30-45 minutes of manual work instead of 30 seconds of import.

## Objective

Create 3 production-ready Grafana dashboard JSON files that can be imported directly into Grafana Cloud.

**Deliverables**:
1. `docs/monitoring/dashboards/application-overview.json` (20+ panels)
2. `docs/monitoring/dashboards/trading-activity.json` (18+ panels)
3. `docs/monitoring/dashboards/external-services.json` (25+ panels)

## Requirements

### 1. Dashboard JSON Structure

Each JSON file must be a valid Grafana dashboard definition:

```json
{
  "dashboard": {
    "title": "Zebu - Application Overview",
    "tags": ["zebu", "production", "overview"],
    "timezone": "browser",
    "editable": true,
    "refresh": "30s",
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "panels": [
      {
        "id": 1,
        "type": "timeseries",
        "title": "Request Rate",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
        "targets": [{
          "expr": "sum(rate({container=\"zebu-backend-prod\"} | json | event=\"Request started\" [1m]))",
          "refId": "A"
        }],
        "options": { /* ... */ }
      }
      // ... more panels
    ]
  }
}
```

### 2. Convert All Markdown Specs

**Source Files**:
- [docs/monitoring/dashboards/application-overview.md](../docs/monitoring/dashboards/application-overview.md)
- [docs/monitoring/dashboards/trading-activity.md](../docs/monitoring/dashboards/trading-activity.md)
- [docs/monitoring/dashboards/external-services.md](../docs/monitoring/dashboards/external-services.md)

**For Each Panel**:
- ✅ Correct panel type (timeseries, stat, gauge, table, pie)
- ✅ Exact LogQL queries from markdown
- ✅ Proper grid positioning (rows, columns)
- ✅ Thresholds and alerts configured
- ✅ Units, legends, colors as specified
- ✅ Tooltips and descriptions

### 3. Dashboard-Specific Requirements

#### Application Overview Dashboard
- **Rows**: System Health, Performance Metrics, API Endpoints, Cache Performance
- **Key Panels**: Request rate, error rate, P50/P95/P99 latency, cache hit ratio
- **Time Range**: Last 1 hour (default)
- **Refresh**: 30s

#### Trading Activity Dashboard
- **Rows**: Trading Volume, Order Types, Portfolio Operations, User Activity
- **Key Panels**: Trades/day, buy vs sell ratio, portfolio creation rate
- **Time Range**: Last 24 hours (default)
- **Refresh**: 1m

#### External Services Dashboard
- **Rows**: Alpha Vantage, PostgreSQL, Redis, Rate Limiting
- **Key Panels**: API quota usage, rate limit warnings, DB connection pool, cache memory
- **Time Range**: Last 6 hours (default)
- **Refresh**: 1m

### 4. Grafana Cloud Compatibility

**Data Source**:
- All queries use Loki data source (provisioned)
- Use `${DS_LOKI}` variable for data source reference
- Compatible with Grafana v10.x (Grafana Cloud current version)

**Panel Features**:
- Use modern panel types (not deprecated ones)
- Include proper field overrides for units/colors
- Add helpful panel descriptions
- Configure tooltips for better UX

### 5. Testing & Validation

**Before Submitting**:
1. Validate JSON syntax (`jq . < dashboard.json`)
2. Verify all LogQL queries are valid
3. Check grid positions don't overlap
4. Confirm all markdown specs are converted

**After Import** (manual testing by user):
1. Import JSON into Grafana Cloud
2. Verify all panels render correctly
3. Confirm queries return data
4. Check thresholds and colors

## File Structure

```
docs/monitoring/dashboards/
├── application-overview.md       # Existing: Keep as reference docs
├── application-overview.json     # NEW: Importable dashboard
├── trading-activity.md           # Existing: Keep as reference docs
├── trading-activity.json         # NEW: Importable dashboard
├── external-services.md          # Existing: Keep as reference docs
└── external-services.json        # NEW: Importable dashboard
```

## Implementation Notes

### LogQL Query Examples

**Time Series (Request Rate)**:
```json
{
  "expr": "sum(rate({container=\"zebu-backend-prod\"} | json | event=\"Request started\" [1m]))",
  "refId": "A",
  "datasource": {"type": "loki", "uid": "${DS_LOKI}"}
}
```

**Stat Panel (Error Count)**:
```json
{
  "expr": "sum(count_over_time({container=\"zebu-backend-prod\"} | json | level=\"error\" [5m]))",
  "refId": "A",
  "instant": true
}
```

**Table (Recent Errors)**:
```json
{
  "expr": "{container=\"zebu-backend-prod\"} | json | level=\"error\"",
  "refId": "A",
  "maxLines": 100
}
```

### Grid Layout Tips

- Each row starts at `y` coordinate (0, 8, 16, 24, etc.)
- Full width = 24 units
- Standard panel height = 8 units
- Two panels side-by-side: `w: 12` each
- Three panels: `w: 8` each

### Thresholds Configuration

```json
"fieldConfig": {
  "defaults": {
    "thresholds": {
      "mode": "absolute",
      "steps": [
        {"color": "green", "value": null},
        {"color": "yellow", "value": 0.05},
        {"color": "red", "value": 0.1}
      ]
    }
  }
}
```

## Success Criteria

- ✅ All 3 JSON files created and validate with `jq`
- ✅ Every panel from markdown specs is represented
- ✅ Grid layout is clean (no overlaps, aligned rows)
- ✅ All LogQL queries are syntactically correct
- ✅ Documentation updated with import instructions
- ✅ README added: `docs/monitoring/dashboards/README.md` explaining how to import

## References

- **Grafana Dashboard JSON Schema**: https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/create-dashboard/
- **LogQL Documentation**: https://grafana.com/docs/loki/latest/query/
- **Panel Types**: https://grafana.com/docs/grafana/latest/panels-visualizations/
- **Existing Markdown Specs**: `docs/monitoring/dashboards/*.md`

## Out of Scope

- ❌ Prometheus/Metrics dashboards (Loki only for now)
- ❌ Custom Grafana plugins
- ❌ Alerting rules (separate task, covered in alert-configuration.md)
- ❌ User authentication/permissions

## Quality Standards

- Follow Clean Architecture (JSON files are infrastructure artifacts)
- No hardcoded data source UIDs (use variables)
- Include panel descriptions for maintainability
- Validate JSON before committing (`task lint` should pass)
- Test coverage: N/A (configuration files)
