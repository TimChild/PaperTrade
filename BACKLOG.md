# Project Backlog

Incomplete items only. Completed work is tracked in PROGRESS.md.

**Last Updated**: March 8, 2026

---

## Features

### Live Strategy Execution
- Execute saved strategies as live paper-trading rules (not just backtesting)
- Scheduling/execution engine with risk management / position limits
- Notification on signal triggers
- **Priority**: HIGH (natural next major feature after Phase 4)

### S&P 500 Benchmark Comparison
- Add S&P 500 (SPY) as a benchmark overlay in backtest result charts
- Allow users to compare strategy performance against market index
- **Priority**: MEDIUM

### Multiple Currencies
- Support non-USD portfolios and multi-currency holdings
- **Priority**: LOW (future phase)

### WebSocket Integration
- Real-time price updates via WebSocket instead of polling
- **Priority**: LOW (future phase)

### Social / Sharing Features
- Share portfolio or backtest results with other users
- **Priority**: LOW (future phase)

---

## Technical Debt

### Admin Authentication TODOs — ~2-4 hours
- 6 TODO comments in `analytics.py` endpoints: analytics endpoints marked "Admin only" but no auth check implemented
- Affected endpoints: `/analytics/backtest`, `/analytics/recalculate/{portfolio_id}`, `/analytics/recalculate-all`
- Solution: Add admin role check (requires extending Clerk integration or adding admin flag)
- **Note**: Also add user ownership verification for portfolio-specific endpoints
- **Priority**: LOW — production app is currently single-user

### Add Database Indexes — ~1 hour
- Tables: `Transaction.portfolio_id` and `Transaction.timestamp`
- Implementation: Add to SQLModel models with a proper Alembic migration
- Benefit: Faster queries as transaction history grows

---

## Infrastructure

### Alembic in CD Pipeline
- Automate `alembic upgrade head` in the CD workflow (currently not run on deploy)
- **Priority**: MEDIUM — needed when next migration is added

### Error Monitoring
- Add Sentry (or equivalent) for frontend error tracking — 5K errors/month on free tier
- Backend structured logging (structlog) is already in place

### Bundle Size Analysis — ~30 minutes
- Command: `npm run build && npx vite-bundle-visualizer`
- Goal: Document baseline, optimize if needed
- **Priority**: LOW — app is fast, but useful to have a baseline
