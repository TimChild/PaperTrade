# Zebu: Executive Summary

**Version**: v1.0.0 — Production Deployed
**Status**: Live at zebutrader.com (Phase 4 complete)

## What is Zebu?

Zebu is a stock market emulation platform that lets you practice trading strategies with virtual money and real market data. Think of it as a flight simulator for investors — all the experience, none of the financial risk.

## Current State

✅ **Production Deployed** — Live at zebutrader.com
✅ **Complete Trading Platform** — Buy, sell, analytics, backtesting
✅ **Trading Strategies** — Buy-and-hold, dollar-cost averaging, moving-average crossover with full backtest pipeline
✅ **Authenticated** — Clerk integration with private portfolios
✅ **Well Tested** — See PROGRESS.md for current test counts (reconciled there)
✅ **Monitored** — Grafana Cloud with alerts and dashboards
✅ **CD Pipeline** — Push to `main` auto-deploys to production

## Key Features Available Now

### 1. Portfolio Management

- Create unlimited portfolios with any starting cash balance (> $0)
- View all portfolios in a centralized dashboard
- Track portfolio value in real-time
- Automatic cash balance calculations from transaction ledger

### 2. Stock Trading

- **BUY orders** for any publicly traded stock (US & International)
- **SELL orders** with cost basis tracking and P&L calculation
- Real-time price fetching via Alpha Vantage
- Automatic portfolio balance updates
- Complete transaction history with immutable ledger
- Support for international exchanges (UK, Canada, Germany, China)
- Weekend/holiday-aware price handling

### 3. Market Data & Charts

- Real-time current prices from Alpha Vantage
- 3-tier intelligent caching (Redis → PostgreSQL → API)
- Rate limit protection (5 calls/min, 500/day)
- Historical price data storage for analytics
- Background price scheduler for automatic updates
- TradingView Lightweight Charts integration
- Candlestick and line charts with trade markers
- Graceful fallback when market data unavailable

### 4. Analytics & Backtesting

- Portfolio performance charts (value over time)
- Asset composition pie charts
- Performance metrics (daily change, total return)
- Daily snapshot calculations
- Complete P&L tracking with percentages
- **Full backtest pipeline** — three strategy types (Buy & Hold, DCA, Moving Average Crossover)
- **Strategy comparison UI** — side-by-side metrics across multiple backtest runs

### 5. Authentication & Security

- User authentication via Clerk
- Private portfolios (data privacy guaranteed)
- Protected API endpoints with JWT tokens
- HTTPS/SSL encryption (Let's Encrypt)
- Multi-factor authentication support

### 6. User Experience

- Clean, responsive React interface
- Mobile-responsive design (320px-2560px breakpoints)
- Real-time updates without page refreshes
- Form validation with helpful error messages
- Accessible design with proper ARIA labels
- Loading states for async operations
- Empty state messaging and contextual errors

## Known Limitations

### Trading Restrictions

- ⚠️ **Market orders only** — no limit/stop orders
- ⚠️ **Whole shares only** — no fractional shares
- ⚠️ **Long positions only** — no short selling

### Market Data Constraints

- **Rate Limits**: 5 API calls/minute, 500/day (Alpha Vantage free tier)
- **Market Hours**: Prices update during market hours with weekend/holiday awareness

### Future Improvements

- ⚠️ **No dark mode** — single theme currently
- ⚠️ **Single currency**: USD only (no multi-currency support)
- ⚠️ **Advanced analytics**: no Sharpe ratio, volatility metrics yet

## What's Coming Next

### Phase 5: Agent Platform (in progress)

The active forward plan is the **Agent Platform Proposal** (`docs/planning/agent-platform-proposal.md`) — evolving Zebu into an agent-driven trading platform with the app as human GUI and looped/scheduled agents executing strategies via API/MCP. Phase A (Claude infra migration) shipped 2026-05-09; Phase B (codebase health audit + foundation refactors) and Task #210 (live strategy execution) are the next active workstreams.

See the proposal for the full multi-phase plan (A–G).

## For Users: Getting Started

1. **Visit the application** at [zebutrader.com](https://zebutrader.com)
2. **Sign up** — Create an account with email or social login (Clerk)
3. **Create a portfolio** — Give it a name and starting cash (e.g., $10,000)
4. **Navigate to portfolio detail** — Click "Trade Stocks" on your portfolio card
5. **Execute a trade** — Enter a stock symbol (e.g., IBM) and quantity, click "Buy"
6. **Monitor holdings** — Watch your portfolio value update with real market prices
7. **View analytics** — Check performance charts and metrics
8. **Backtest strategies** — Configure a strategy, run it against historical data, compare results

See [USER_GUIDE.md](../USER_GUIDE.md) for detailed user guides.

## For Developers: Contributing

- **Architecture**: Clean Architecture with strict layer separation
- **Testing**: See PROGRESS.md for current test counts — 81%+ coverage on critical paths
- **Code Quality**: Ruff (Python) + ESLint (TypeScript), strict type checking
- **CI/CD**: GitHub Actions, push-to-main auto-deploys to production
- **Docker**: Full-stack containerization for local development
- **Monitoring**: Grafana Cloud for production observability

See [features.md](./features.md) for implementation details and [project_strategy.md](./project_strategy.md) for architecture principles.

## Performance Metrics

- **API**: <100ms median response time
- **E2E**: Complete user workflows validated with Playwright
- **Production**: Live at zebutrader.com with 99%+ uptime
- **Infrastructure**: Health checks on all services, Grafana monitoring

See PROGRESS.md for the current reconciled test count.

## Architecture Highlights

- **Backend**: Python 3.13+, FastAPI, SQLModel, PostgreSQL
- **Frontend**: TypeScript, React, Vite, TanStack Query, Tailwind CSS
- **Infrastructure**: Docker Compose + Proxmox VM (`scripts/proxmox-vm/`); push-to-main CD pipeline via self-hosted GitHub Actions runner
- **Caching**: Redis for market data (respects rate limits)
- **Testing**: Pytest, Vitest, Playwright

---

**Last Updated**: 2026-05-09
**Project Repository**: https://github.com/TimChild/PaperTrade
**Production URL**: https://zebutrader.com
**License**: MIT
