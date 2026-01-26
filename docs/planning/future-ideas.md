# Future Ideas & Exploration

**Note**: For planned features in the roadmap (Phase 4-5), see [roadmap.md](./roadmap.md).

This document tracks experimental ideas and potential integrations that are not yet on the roadmap but may be worth exploring in the future.

## Integrations to Explore

| Idea | Link | Description | Priority |
|------|------|-------------|----------|
| Alpha Vantage MCP Server | https://mcp.alphavantage.co/ | Model Context Protocol server for AI-assisted market data access. Could enable agents to directly query market data during development. | Medium |
| Additional Market Data APIs | See [../reference/external-resources.md](../reference/external-resources.md) | Explore Finnhub, Yahoo Finance, or Polygon.io as alternatives/backups | Low |

## Feature Ideas (Exploratory)

Beyond Phase 4-5 features already in the [roadmap](./roadmap.md):

| Feature | Description | Exploration Priority |
|---------|-------------|---------------------|
| Social Trading | Follow other users' portfolios and strategies | Low - needs user base first |
| Paper Trading Competitions | Leaderboards, time-limited challenges | Medium - good for engagement |
| Portfolio Sharing | Share portfolio performance publicly | Low - privacy concerns |
| Custom Indicators | User-defined technical indicators for strategies | Medium - after Phase 5 |

## Technical Improvements (Exploratory)

Beyond roadmap items:

| Improvement | Description | When to Consider |
|-------------|-------------|------------------|
| GraphQL API | Alternative to REST for flexible queries | If REST becomes limiting |
| Event Sourcing | Full event sourcing for complete audit trail | Already have ledger pattern |
| Multi-currency Support | Support portfolios in different currencies | Low priority (USD sufficient) |

## Infrastructure Ideas

| Idea | Description |
|------|-------------|
| Kubernetes Deployment | Scale beyond single ECS deployment |
| Multi-region | Deploy to multiple AWS regions for latency |
| CDN for Frontend | CloudFront distribution for static assets |

---

*Add new ideas by editing this file. Move items to `project_plan.md` when they become concrete plans.*
