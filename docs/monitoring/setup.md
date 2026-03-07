# Grafana Cloud Setup Guide

This guide walks through setting up Grafana Cloud monitoring for Zebu production deployment.

## Overview

Zebu uses **Grafana Cloud Free Tier** for:
- **Loki**: Log aggregation from Docker containers
- **Grafana**: Dashboards and visualization
- **Alerts**: Critical issue notifications

**Free Tier Limits**:
- 50GB logs/month
- 10,000 metric series
- 14-day retention

**Estimated Usage**: ~100MB/day (well within limits)

## 1. Create Grafana Cloud Account

1. Go to https://grafana.com/auth/sign-up/create-user
2. Fill in registration details
3. Verify email address
4. Create a new stack:
   - Stack name: `zebu-prod`
   - Region: `us-central-1` (or closest to your deployment)
   - Plan: Free

5. Note your stack details:
   - Stack URL: `https://<your-stack>.grafana.net`
   - Stack ID: Used for API access

## 2. Generate Loki API Credentials

1. In Grafana Cloud, navigate to **Connections** → **Data Sources**
2. Find **Loki** data source (should be pre-configured)
3. Click on Loki to view details
4. Note the **URL** (e.g., `https://logs-prod-us-central1.grafana.net`)

5. Generate API token:
   - Go to **Administration** → **API Keys** (or **Cloud Access Policies**)
   - Click **Create API Key**
   - Name: `promtail-zebu-prod`
   - Role: **MetricsPublisher** (allows writing logs)
   - Click **Create**
   - **IMPORTANT**: Copy the API key immediately (shown only once)

6. Find your instance/user ID:
   - In the Loki data source settings, look for the basic auth username
   - Usually a numeric ID (e.g., `123456`)

## 3. Install Promtail on Production Server

SSH into your Proxmox VM:

```bash
ssh root@192.168.4.112
```

Download the installation script:

```bash
cd /tmp
curl -o install-promtail.sh https://raw.githubusercontent.com/TimChild/PaperTrade/main/scripts/monitoring/install-promtail.sh
chmod +x install-promtail.sh
```

Set environment variables with your Grafana Cloud credentials:

```bash
export LOKI_URL='https://logs-prod-042.grafana.net'  # Your Grafana Cloud Loki URL
export LOKI_USERNAME='1456248'  # Your instance ID
export LOKI_API_KEY='glc_...'  # Your API token
```

Run the installation script:

```bash
sudo -E bash install-promtail.sh
```

**Note**: The script uses `curl` instead of `wget` and static file paths instead of Docker API for better compatibility.

The script will:
- Download Promtail v2.9.3
- Install to `/usr/local/bin/promtail`
- Create configuration in `/etc/promtail/config.yml`
- Set up systemd service
- Start Promtail automatically

## 4. Verify Log Ingestion

### Check Promtail Status

```bash
# Check if Promtail is running
sudo systemctl status promtail

# View Promtail logs
sudo journalctl -u promtail -f
```

Look for messages like:
```
level=info msg="Starting Promtail" version=...
level=info msg="Clients configured" clients=1
```

### Check Grafana Cloud

1. Log into your Grafana Cloud instance
2. Go to **Explore**
3. Select **Loki** data source
4. Run a test query:

```logql
{container="zebu-backend-prod"}
```

You should see logs appearing within 30-60 seconds.

### Test Log Labels

Verify structured logging is working:

```logql
{container="zebu-backend-prod"} | json | level="info"
```

Should show parsed JSON fields in the log viewer.

## 5. Import Dashboards

### Dashboard: Application Overview

1. In Grafana, click **Dashboards** → **New** → **Import**
2. Upload `/docs/monitoring/dashboards/application-overview.json`
3. Select **Loki** as the data source
4. Click **Import**

Repeat for:
- `trading-activity.json`
- `external-services.json`

### Create Custom Dashboard (Alternative)

If you prefer to build manually:

1. Click **Dashboards** → **New Dashboard**
2. Add panels using the queries documented in each dashboard JSON file
3. Save dashboard with appropriate name

## 6. Configure Alerts

### Alert Rule: High Error Rate

1. Go to **Alerting** → **Alert Rules** → **New Alert Rule**
2. Configure:
   - **Name**: High Error Rate - Backend
   - **Query**:
     ```logql
     rate({container="zebu-backend-prod"} | json | level="error" [5m])
     ```
   - **Condition**: `> 0.1` (more than 0.1 errors/second)
   - **For**: 5 minutes
   - **Summary**: Backend error rate is above threshold
3. Click **Save**

### Alert Rule: Alpha Vantage Rate Limit

1. Create new alert rule
2. Configure:
   - **Name**: Alpha Vantage Rate Limit Warning
   - **Query**:
     ```logql
     count_over_time({container="zebu-backend-prod"} |= "rate limit" [5m])
     ```
   - **Condition**: `> 0`
   - **For**: 1 minute
   - **Summary**: Alpha Vantage rate limit exceeded
3. Click **Save**

### Alert Rule: Backend Service Down

1. Create new alert rule
2. Configure:
   - **Name**: Backend Service Health Check
   - **Query**:
     ```logql
     count_over_time({container="zebu-backend-prod"} [5m])
     ```
   - **Condition**: `< 10` (fewer than 10 log entries in 5 minutes)
   - **For**: 5 minutes
   - **Summary**: Backend service may be down
3. Click **Save**

## 7. Set Up Notification Channels

### Email Notifications

1. Go to **Alerting** → **Contact Points**
2. Click **New Contact Point**
3. Configure:
   - **Name**: Email - Production Alerts
   - **Integration**: Email
   - **Addresses**: Your email address
4. Click **Save**

### Slack Notifications (Optional)

1. Create Slack incoming webhook in your workspace
2. In Grafana, create new contact point:
   - **Name**: Slack - Production Alerts
   - **Integration**: Slack
   - **Webhook URL**: Your Slack webhook URL
3. Click **Save**

### Assign Contact Points to Alerts

1. Go to **Alerting** → **Notification Policies**
2. Edit the default policy or create a new one
3. Set contact point to your configured channel
4. Save policy

## 8. Test Alerts

Simulate an error to test alerting:

```bash
# SSH into production server
ssh root@192.168.4.112

# Generate some errors (adjust based on your setup)
docker exec zebu-backend-prod python -c "import logging; logging.error('Test alert')"
```

You should receive an alert notification within 5-6 minutes (5 min for condition + 1 min evaluation).

## Troubleshooting

### No Logs Appearing in Grafana

1. **Check Promtail is running**:
   ```bash
   sudo systemctl status promtail
   ```

2. **Check Promtail logs for errors**:
   ```bash
   sudo journalctl -u promtail -n 100
   ```

   Look for authentication errors, network issues, or permission problems.

3. **Verify Docker socket access**:
   ```bash
   ls -l /var/run/docker.sock
   ```

   Promtail needs read access to the Docker socket.

4. **Check container names match**:
   ```bash
   docker ps --format "{{.Names}}"
   ```

   Ensure container names match the regex patterns in `/etc/promtail/config.yml`.

### Logs Appearing But Not Parsed

1. **Check JSON format**:
   ```bash
   docker logs zebu-backend-prod --tail 10
   ```

   Logs should be valid JSON like:
   ```json
   {"event": "Request started", "level": "info", "timestamp": "2026-01-17T..."}
   ```

2. **Update pipeline stages** in `/etc/promtail/config.yml` if log format changed

3. **Restart Promtail** after config changes:
   ```bash
   sudo systemctl restart promtail
   ```

### Rate Limit Errors from Grafana Cloud

If you see errors like `429 Too Many Requests`:

1. **Check ingestion rate**: Free tier limit is 50GB/month
2. **Reduce log verbosity**: Filter out DEBUG logs
3. **Increase scrape interval** in Promtail config from 5s to 10s or 15s

## Security Considerations

### Credentials Storage

- **Never commit** Loki credentials to version control
- Store credentials securely (password manager, secrets vault)
- Rotate API keys periodically (every 90 days recommended)

### Network Security

- Promtail connects to Grafana Cloud over HTTPS (TLS encrypted)
- API key transmitted via HTTP Basic Auth over TLS
- No inbound connections required

### Access Control

- Limit Grafana Cloud user access (only authorized team members)
- Use role-based access control in Grafana
- Enable 2FA for Grafana Cloud account

## Cost Management

### Current Usage (Estimated)

- **Logs**: ~3GB/month (backend + frontend + DB + Redis)
- **Metrics**: 0 (not using Prometheus yet)
- **Cost**: $0 (within free tier)

### If Approaching Limits

1. **Reduce retention**: 14 days → 7 days
2. **Filter logs**: Only ship WARNING and above
3. **Sample high-frequency logs**: Ship 1 in every N requests
4. **Upgrade plan**: Paid tier if needed for production scale

### Monitoring Usage

1. Go to **Administration** → **Usage Insights**
2. Check:
   - Logs ingested (GB/month)
   - Metrics series count
   - Days until limit reset

## Next Steps

1. ✅ Promtail installed and running
2. ✅ Logs flowing to Grafana Cloud
3. ✅ Dashboards created
4. ✅ Alerts configured
5. 📖 Read [Monitoring Runbook](./monitoring-runbook.md) for operational procedures
6. 📊 Customize dashboards for your specific needs
7. 🔔 Test alert notifications with real scenarios

## Additional Resources

- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Promtail Configuration](https://grafana.com/docs/loki/latest/clients/promtail/configuration/)
- [LogQL Query Language](https://grafana.com/docs/loki/latest/logql/)
- [Grafana Cloud Free Tier Details](https://grafana.com/pricing/)
