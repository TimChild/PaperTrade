# Zebu: Executive Summary

**Version**: v1.2.0 - Production Deployed
**Status**: Live at zebutrader.com

## What is Zebu?

Zebu is a stock market emulation platform that lets you practice trading strategies with virtual money and real market data. Think of it as a flight simulator for investors – all the experience, none of the financial risk.

## Current State

✅ **Production Deployed** - Live at zebutrader.com
✅ **Complete Trading Platform** - Buy, sell, analytics, backtesting
✅ **Authenticated** - Clerk integration with private portfolios
✅ **Well Tested** - 796 automated tests (571 backend + 225 frontend)
✅ **Monitored** - Grafana Cloud with alerts and dashboards

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
- Backtesting support (trade at historical dates with `as_of` parameter)
- Daily snapshot calculations
- Complete P&L tracking with percentages

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
- ⚠️ **No limit/stop orders** - Market orders only (planned Phase 4)
- ⚠️ **No fractional shares** - Whole shares only
- ⚠️ **No short selling** - Long positions only

### Market Data Constraints
- **Rate Limits**: 5 API calls/minute, 500/day (Alpha Vantage free tier)
- **Market Hours**: Prices update during market hours with weekend/holiday awareness

### Future Improvements
- ⚠️ **No dark mode** - Single theme currently
- ⚠️ **Single currency**: USD only (no multi-currency support)
- ⚠️ **Advanced analytics**: No Sharpe ratio, volatility metrics yet

## What's Coming Next

### Phase 4: Professional Features (2026)
- Advanced order types (limit, stop orders)
- Real-time WebSocket price updates
- Multi-provider market data (resilience)
- Enhanced observability and monitoring

### Phase 5: Automation (2027+)
- Automated trading algorithms
- Strategy builder interface
- Advanced analytics (Sharpe ratio, volatility)
- Portfolio comparison tools

## For Users: Getting Started

1. **Visit the application** at [zebutrader.com](https://zebutrader.com)
2. **Sign up** - Create an account with email or social login (Clerk)
3. **Create a portfolio** - Give it a name and starting cash (e.g., $10,000)
4. **Navigate to portfolio detail** - Click "Trade Stocks" on your portfolio card
5. **Execute a trade** - Enter a stock symbol (e.g., IBM) and quantity, click "Buy"
6. **Monitor holdings** - Watch your portfolio value update with real market prices
7. **View analytics** - Check performance charts and metrics
8. **Backtest strategies** - Try trading at historical dates to test ideas

See [docs/user/](../user/) for detailed user guides.

## For Developers: Contributing

- **Architecture**: Clean Architecture with strict layer separation
- **Testing**: 81%+ coverage, 796 tests passing
- **Code Quality**: Ruff (Python) + ESLint (TypeScript), strict type checking
- **CI/CD**: GitHub Actions with automated testing and deployment
- **Docker**: Full-stack containerization for local development
- **Monitoring**: Grafana Cloud for production observability

See [features.md](./features.md) for implementation details and [project_strategy.md](./project_strategy.md) for architecture principles.

## Performance Metrics

- **Backend**: 571 tests passing, <100ms median API response time
- **Frontend**: 225 tests passing, 0 ESLint suppressions
- **E2E**: Complete user workflows validated with Playwright
- **Production**: Live at zebutrader.com with 99%+ uptime
- **Infrastructure**: Health checks on all services, Grafana monitoring

## Architecture Highlights

- **Backend**: Python 3.12+, FastAPI, SQLModel, PostgreSQL
- **Frontend**: TypeScript, React, Vite, TanStack Query, Tailwind CSS
- **Infrastructure**: Docker Compose (dev), AWS CDK (production)
- **Caching**: Redis for market data (respects rate limits)
- **Testing**: Pytest, Vitest, Playwright

---

**Last Updated**: January 26, 2026
**Project Repository**: https://github.com/TimChild/PaperTrade
**Production URL**: https://zebutrader.com
**License**: MIT
