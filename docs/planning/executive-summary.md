# Zebu: Executive Summary

**Version**: Phase 2 Complete (January 2026)
**Status**: Production-Ready with Real Market Data Integration

## What is Zebu?

Zebu is a stock market emulation platform that lets you practice trading strategies with virtual money and real market data. Think of it as a flight simulator for investors – all the experience, none of the financial risk.

## Current State

✅ **Fully Functional** - Core trading platform operational
✅ **Real Market Data** - Live prices via Alpha Vantage API
✅ **Production Ready** - Dockerized deployment with CI/CD
✅ **Well Tested** - 499 automated tests (418 backend + 81 frontend)

## Key Features Available Now

### 1. Portfolio Management
- Create unlimited portfolios with any starting cash balance (> $0)
- View all portfolios in a centralized dashboard
- Track portfolio value in real-time
- Automatic cash balance calculations from transaction ledger

### 2. Stock Trading
- **BUY orders** for any publicly traded stock (US & International)
- Real-time price fetching via Alpha Vantage
- Automatic portfolio balance updates
- Complete transaction history
- Support for international exchanges (UK, Canada, Germany, China)

### 3. Market Data Integration
- Real-time current prices from Alpha Vantage
- Price caching with Redis (respects API rate limits: 5 calls/min, 500/day)
- Historical price data storage for analytics
- Background price scheduler for automatic updates
- Graceful fallback when market data unavailable

### 4. User Experience
- Clean, responsive React interface
- Real-time updates without page refreshes
- Form validation with helpful error messages
- Accessible design with proper ARIA labels
- Loading states for async operations

## Known Limitations

### Trading Restrictions
- ⚠️ **No limit/stop orders** - Market orders only
- ⚠️ **No fractional shares** - Whole shares only
- ⚠️ **No short selling** - Long positions only

### Market Data Constraints
- **Rate Limits**: 5 API calls/minute, 500/day (Alpha Vantage free tier)
- **Demo API Key**: Used for development/testing (has additional limitations)
- **Market Hours**: Prices update during market hours; may show stale after-hours

### Portfolio Analytics
- ⚠️ **Limited visualizations** - No charts/graphs yet (Phase 3)
- ⚠️ **Basic P&L** - Shows gains/losses but no detailed analytics
- ⚠️ **No portfolio comparison** - Can't compare multiple portfolios

### Technical Boundaries
- **Single currency**: USD only (no multi-currency support)
- **No user authentication**: All portfolios visible to all users (development mode)
- **No backtesting**: Can't simulate trades at historical dates (Phase 3 feature)

## What's Coming Next

### Phase 3: Analytics & Backtesting (Planned)
- SELL order functionality
- Portfolio analytics dashboards with charts
- Historical backtesting (test strategies against past data)
- Performance metrics and benchmarking
- Portfolio comparison tools

### Phase 4: Advanced Features (Future)
- Automated trading algorithms
- WebSocket real-time updates
- User authentication & authorization
- Multi-currency support
- Advanced order types (limit, stop, stop-limit)

## For Users: Getting Started

1. **Visit the application** at `http://localhost:5173` (local) or your deployment URL
2. **Create a portfolio** - Give it a name and starting cash (e.g., $10,000)
3. **Navigate to portfolio detail** - Click "Trade Stocks" on your portfolio card
4. **Execute a trade** - Enter a stock symbol (e.g., IBM) and quantity, click "Buy"
5. **Monitor holdings** - Watch your portfolio value update with real market prices

See [USER_GUIDE.md](./USER_GUIDE.md) for detailed instructions.

## For Developers: Contributing

- **Architecture**: Clean Architecture with strict layer separation
- **Testing**: 82%+ coverage, all tests pass
- **Code Quality**: Ruff (Python) + ESLint (TypeScript), strict type checking
- **CI/CD**: GitHub Actions with automated testing and deployment
- **Docker**: Full-stack containerization for local development

See [FEATURE_STATUS.md](./FEATURE_STATUS.md) for implementation details and [TECHNICAL_BOUNDARIES.md](./TECHNICAL_BOUNDARIES.md) for known limitations.

## Performance Metrics

- **Backend**: 418 tests passing, <500ms API response time
- **Frontend**: 81 tests passing, accessible UI components
- **E2E**: 7 complete user workflows validated
- **Uptime**: Health checks on all services (PostgreSQL, Redis, Backend, Frontend)

## Architecture Highlights

- **Backend**: Python 3.12+, FastAPI, SQLModel, PostgreSQL
- **Frontend**: TypeScript, React, Vite, TanStack Query, Tailwind CSS
- **Infrastructure**: Docker Compose (dev), AWS CDK (production)
- **Caching**: Redis for market data (respects rate limits)
- **Testing**: Pytest, Vitest, Playwright

---

**Last Updated**: January 4, 2026
**Project Repository**: https://github.com/TimChild/Zebu
**License**: MIT
