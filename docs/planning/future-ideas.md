# Future Ideas & Exploration

This document tracks ideas for future features, integrations, and improvements that we may want to explore.

## Integrations to Explore

| Idea | Link | Description | Priority |
|------|------|-------------|----------|
| Alpha Vantage MCP Server | https://mcp.alphavantage.co/ | Model Context Protocol server for AI-assisted market data access. Could enable agents to directly query market data during development. | Medium |
| Additional Market Data APIs | See [../reference/external-resources.md](../reference/external-resources.md) | Explore Finnhub, Yahoo Finance, or Polygon.io as alternatives/backups | Phase 4c (Planned) |

## Feature Ideas

| Feature | Description | Phase |
|---------|-------------|-------|
| Social Trading | Follow other users' portfolios and strategies | Future |
| Paper Trading Competitions | Leaderboards, time-limited challenges | Future |
| Portfolio Sharing | Share portfolio performance publicly | Future |
| Custom Indicators | User-defined technical indicators for strategies | Phase 5+ |
| Alerts & Notifications | Price alerts, portfolio value thresholds | Phase 4a (Planned) |
| Mobile App | React Native or PWA for mobile access | Future |

## Technical Improvements

| Improvement | Description | When |
|-------------|-------------|------|
| WebSocket Price Updates | Real-time price streaming instead of polling | Phase 4a (Planned) |
| GraphQL API | Alternative to REST for flexible queries | Future |
| Event Sourcing | Full event sourcing for complete audit trail | Future |
| Multi-currency Support | Support portfolios in different currencies | Phase 5 (Planned) |

## Infrastructure Ideas

| Idea | Description |
|------|-------------|
| Kubernetes Deployment | Scale beyond single ECS deployment |
| Multi-region | Deploy to multiple AWS regions for latency |
| CDN for Frontend | CloudFront distribution for static assets |

---

*Add new ideas by editing this file. Move concrete plans to `roadmap.md` when ready for implementation.*

**Note**: WebSocket updates and Alerts/Notifications are now planned for Phase 4a. Multi-currency support is targeted for Phase 5.
