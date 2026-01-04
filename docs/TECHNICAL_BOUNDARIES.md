# PaperTrade: Technical Boundaries & Limitations

**Last Updated**: January 4, 2026
**Version**: Phase 2 Complete

## Overview

This document outlines known technical limitations, edge cases, and architectural boundaries in the PaperTrade application. Understanding these constraints helps set proper expectations and guides future development.

---

## Critical Limitations

### 1. SELL Orders ✅ IMPLEMENTED (Phase 3a Complete)

**Status**: ✅ Fully Available
**Impact**: Users can exit positions and rebalance portfolios
**Completed**: Phase 3a (discovered Jan 4, 2026)

**Features**:
- Market sell orders with real-time pricing
- Holdings validation (cannot sell more than owned)
- Cost basis tracking with proportional reduction
- Complete API and UI support
- Error handling for insufficient shares

**Implementation**:
- `backend/src/papertrade/domain/entities/transaction.py` - SELL transaction type
- `backend/src/papertrade/application/commands/sell_stock.py` - SellStockHandler
- `frontend/src/components/features/portfolio/TradeForm.tsx` - BUY/SELL toggle

---

### 2. No User Authentication

**Status**: ❌ Not Available
**Impact**: **CRITICAL** - Not production-ready
**Planned**: Phase 3 (Q1 2026)

**Details**:
- All portfolios visible to all users
- No user ownership model
- User ID stored in browser localStorage (easily spoofed)
- Anyone can access any portfolio by guessing ID

**Security Implications**:
- **Do NOT deploy to public internet without authentication**
- Suitable only for single-user/development environments
- No data privacy guarantees
- No audit trail of who created what

**Workarounds**:
- Deploy behind VPN or firewall
- Use only in local development
- Trust-based single-user deployment

**Technical Approach (Future)**:
- JWT or session-based authentication
- User entity in domain model
- Portfolio ownership via foreign key
- Login/logout endpoints
- Protected routes in frontend

**Code References**:
- `backend/src/papertrade/adapters/inbound/api/routes.py` - No auth middleware
- `frontend/src/lib/utils/userSession.ts` - LocalStorage user management

---

### 3. API Rate Limiting (Alpha Vantage)

**Status**: ⚠️ Active Limitation
**Impact**: **HIGH** - Affects all market data operations
**Limits**: 5 API calls/minute, 500 calls/day (free tier)

**Details**:
- Shared rate limit across all users
- Exceeding limit returns error
- Automatic retry with exponential backoff
- Cache reduces but doesn't eliminate calls

**Error Messages**:
```
"Market data unavailable: Rate limit exceeded"
"API rate limit reached, please try again later"
```

**Cache Mitigation**:
- Redis caches recent prices (default 5min TTL)
- Background scheduler fetches popular stocks
- Reduces real-time calls by ~70-80%

**When Limits Trigger**:
1. Multiple users trading simultaneously
2. Frequent page refreshes
3. High-volume testing/development
4. Background scheduler + manual trades

**Solutions**:
- **Short-term**: Wait 60 seconds, retry
- **Medium-term**: Upgrade to paid tier ($49.99/month for 75 calls/min)
- **Long-term**: Multi-provider fallback (Finnhub, IEX Cloud)

**Monitoring**:
- Check backend logs for `RateLimitExceeded` errors
- Redis cache hit/miss metrics (future)
- API call counter (not implemented)

**Code References**:
- `backend/src/papertrade/adapters/outbound/alpha_vantage.py` - Retry logic
- `backend/src/papertrade/infrastructure/cache.py` - Redis caching
- `backend/src/papertrade/infrastructure/scheduler.py` - Background updates

---

## Functional Limitations

### 4. Whole Shares Only (No Fractional Shares)

**Status**: ❌ Not Supported
**Impact**: MEDIUM - Limits trading flexibility

**Details**:
- Must buy integer quantities (1, 10, 100)
- Cannot buy 0.5 shares or 2.75 shares
- High-priced stocks require significant capital

**Examples**:
- ✅ Can buy: 1 share of GOOGL @ $175 = $175
- ❌ Cannot buy: 0.5 shares of GOOGL @ $175 = $87.50

**Workaround**:
- Start with larger portfolio balances
- Focus on lower-priced stocks
- Or wait for fractional share support (future)

**Technical Reason**:
- Domain model uses `int` for quantity
- Simpler ledger accounting
- Matches traditional brokerage behavior

**Future Consideration**:
- Change quantity to `Decimal` type
- Update validation logic
- Adjust holdings calculations

---

### 5. Market Orders Only

**Status**: ❌ Limit/Stop Orders Not Available
**Impact**: MEDIUM - No advanced order types

**Details**:
- Trades execute immediately at current market price
- No "buy at $X or lower" (limit order)
- No "sell if drops to $Y" (stop loss)
- No "buy when reaches $Z" (stop limit)

**Workarounds**:
- Manual monitoring and trading
- Accept current market prices
- Use price alerts (not implemented)

**Technical Reason**:
- Requires order management system
- Price monitoring for trigger conditions
- Queue for pending orders
- Background job to execute when conditions met

**Planned**: Phase 4 (Advanced Features)

---

### 6. No Short Selling

**Status**: ❌ Not Supported
**Impact**: LOW-MEDIUM - Can't bet against stocks

**Details**:
- Cannot sell stocks you don't own
- No margin accounts
- No borrowing shares

**Technical Reason**:
- Complex margin requirements
- Risk management needed
- Holdings can't go negative

**Planned**: Phase 4 or later (complex feature)

---

### 7. USD Currency Only

**Status**: ⚠️ Single Currency
**Impact**: MEDIUM - International stocks show USD-equivalent prices

**Details**:
- All prices displayed in USD
- International stocks converted to USD
- No native currency display (e.g., GBP for London stocks)
- Exchange rate handled by Alpha Vantage

**Examples**:
- TSCO.LON (UK) shown in USD, not GBP
- 0700.HK (Hong Kong) shown in USD, not HKD

**Workaround**:
- Accept USD-equivalent pricing
- Manual currency conversion if needed

**Future Enhancement**:
- Multi-currency support (Phase 4+)
- User selectable base currency
- Exchange rate tracking

---

## UI/UX Limitations

### 8. Browser Alert Dialogs

**Status**: ⚠️ Basic UI
**Impact**: LOW - Not elegant but functional

**Details**:
- Success/error messages use `window.alert()`
- Not dismissible until user clicks OK
- Blocks interaction
- Not styled/branded

**Examples**:
```javascript
alert("Trade executed successfully")
alert("Insufficient funds to execute trade")
```

**Future Improvement**:
- Toast notifications (React Toast, Sonner)
- Non-blocking messages
- Auto-dismiss after 3-5 seconds
- Styled to match application

**Code References**:
- `frontend/src/components/features/portfolio/TradeForm.tsx` - Alert usage

---

### 9. Limited Mobile Responsiveness

**Status**: ⚠️ Desktop-First Design
**Impact**: MEDIUM - Mobile users have suboptimal experience

**Details**:
- Works on mobile but not optimized
- Small touch targets
- Horizontal scrolling on tables
- Forms may be cramped

**Workaround**:
- Use desktop/laptop for best experience
- Landscape mode on tablets
- Pinch to zoom on mobile

**Future Enhancement**:
- Mobile-first redesign
- Touch-friendly UI components
- Responsive table designs
- Bottom sheet modals

---

### 10. No Real-Time Updates (WebSockets)

**Status**: ❌ Polling-Based
**Impact**: MEDIUM - Prices don't auto-update

**Details**:
- Must manually refresh page for new prices
- No live ticker updates
- Trade execution requires manual refresh to see results

**Current Behavior**:
- React Query refetches on focus
- Background cache updates (scheduler)
- User-initiated refreshes only

**Future Enhancement** (Phase 4):
- WebSocket connection to backend
- Server pushes price updates
- Real-time portfolio value changes
- Live trade notifications

**Technical Requirements**:
- WebSocket server (FastAPI supports)
- Client WebSocket connection (React)
- Message queue (Redis Pub/Sub)
- Connection management/reconnection

---

## Data & Analytics Limitations

### 11. No Portfolio Analytics/Charts

**Status**: ❌ Not Implemented
**Impact**: MEDIUM - Can't visualize performance
**Planned**: Phase 3

**Missing Features**:
- Performance line charts
- Gain/loss percentage calculations
- Portfolio value over time
- Holdings pie charts (asset allocation)
- Benchmark comparisons (S&P 500)

**Current State**:
- Historical price data stored in database
- Infrastructure ready for charts
- Just needs frontend visualization

**Future Libraries**:
- Recharts or Chart.js
- Lightweight Finance (LWFC)
- TradingView widgets

**Code References**:
- `backend/src/papertrade/domain/entities.py` - PriceHistory model exists
- `frontend/src/components/` - No chart components yet

---

### 12. No Backtesting

**Status**: ❌ Not Implemented
**Impact**: MEDIUM - Can't test strategies on historical data
**Planned**: Phase 3

**Missing Capability**:
- Select past start date
- Execute trades with historical prices
- Fast-forward through time
- See how strategy would have performed

**Technical Readiness**:
- Historical price data available
- Domain model supports time-aware operations
- Just needs use case implementation

**Planned Approach**:
- `BacktestPortfolio` use case
- `current_time` parameter in trade execution
- Query historical prices at specific dates
- Simulate time progression

---

## Technical & Architecture Limitations

### 13. Session Management (LocalStorage)

**Status**: ⚠️ Temporary Solution
**Impact**: MEDIUM - Fragile user tracking

**Current Implementation**:
- User ID stored in browser localStorage
- Persists across page reloads
- Sent in `X-User-Id` HTTP header
- No server-side validation

**Problems**:
1. Easily spoofed (change localStorage value)
2. Lost if localStorage cleared
3. Different browsers = different "users"
4. Incognito mode = new user each session

**Security Issues**:
- No authentication
- No authorization
- Trust-based system

**Future Solution**:
- JWT tokens
- Server-side session management
- Secure HTTP-only cookies
- Proper login/logout flow

**Code References**:
- `frontend/src/lib/utils/userSession.ts` - Current implementation
- `backend/src/papertrade/adapters/inbound/api/dependencies.py` - Header parsing

---

### 14. Single Database (No Sharding)

**Status**: ⚠️ Monolithic Database
**Impact**: LOW - Sufficient for current scale

**Current State**:
- Single PostgreSQL instance
- All data in one database
- No horizontal scaling

**Scale Limits**:
- ~100K portfolios before performance degrades
- ~1M transactions before indexing critical
- Single point of failure

**Future Requirements**:
- Read replicas for queries
- Write/read splitting
- Sharding by user_id (when auth added)
- Connection pooling (PgBouncer)

**Monitoring Needs**:
- Query performance tracking
- Slow query log
- Index usage statistics
- Connection pool metrics

---

### 15. No Backup/Disaster Recovery

**Status**: ❌ Not Implemented
**Impact**: CRITICAL - Data loss risk
**Planned**: Production deployment

**Missing**:
- Automated database backups
- Point-in-time recovery (PITR)
- Backup verification/testing
- Disaster recovery playbook

**Current Risk**:
- Docker volume deletion = data loss
- Container corruption = data loss
- Accidental `docker-compose down -v` = data loss

**Production Requirements**:
- Daily automated backups
- Off-site backup storage (S3)
- 7-day retention minimum
- Tested restore procedure
- Backup monitoring/alerting

**Solutions**:
- PostgreSQL `pg_dump` scheduled job
- AWS RDS automated backups
- Backup to S3 with lifecycle policies
- Document recovery SOP

---

### 16. No Monitoring/Observability

**Status**: ❌ Not Implemented
**Impact**: MEDIUM-HIGH - Blind to production issues
**Planned**: Production deployment

**Missing**:
- Application logs aggregation
- Error tracking (Sentry, Rollbar)
- Performance monitoring (APM)
- Uptime monitoring
- Database query analytics
- User analytics

**Current State**:
- Logs to stdout (Docker logs)
- No centralized logging
- No alerting
- Manual log review

**Production Needs**:
- ELK Stack or CloudWatch Logs
- Error tracking service
- Uptime monitor (Pingdom, StatusCake)
- Performance dashboard
- Alert on critical errors

---

## Edge Cases & Known Bugs

### 17. Concurrent Trade Conflicts

**Status**: ⚠️ Race Condition Risk
**Impact**: LOW - Rare but possible

**Scenario**:
Two trades execute simultaneously for same portfolio:
1. Trade A reads balance: $10,000
2. Trade B reads balance: $10,000
3. Trade A buys $8,000 of stock, commits
4. Trade B buys $8,000 of stock, commits
5. Balance should be -$6,000 (impossible)

**Current Protection**:
- Database transactions provide some isolation
- PostgreSQL serializable transactions
- Unlikely in single-user scenario

**Future Solution**:
- Optimistic locking with version field
- Portfolio balance lock during trades
- Idempotency keys for trade requests

**Code References**:
- `backend/src/papertrade/application/use_cases/execute_trade.py` - Transaction handling
- Database isolation level configuration

---

### 18. Negative Prices (Invalid Data)

**Status**: ⚠️ Possible from External API
**Impact**: LOW - Data validation needed

**Scenario**:
- Alpha Vantage returns corrupted price
- Negative or zero stock price
- Non-numeric price data

**Current Handling**:
- Pydantic validation catches some issues
- May propagate invalid data to database

**Needed Improvements**:
- Price sanity checks (> $0)
- Fallback to cached price if invalid
- Alert on suspicious data
- Manual override capability

**Code References**:
- `backend/src/papertrade/domain/value_objects.py` - Money validation
- `backend/src/papertrade/adapters/outbound/alpha_vantage.py` - API response parsing

---

### 19. Stale Price Display

**Status**: ⚠️ Cache Staleness
**Impact**: LOW-MEDIUM - Users see old prices

**Scenario**:
- Price cached 4 minutes ago
- Market moves significantly
- User sees stale price
- Trades at unexpected price (refreshed on execution)

**Current Behavior**:
- Cache TTL: 5 minutes (configurable)
- Actual execution fetches fresh price
- Display price may differ from trade price

**User Confusion**:
- "I bought at $100 but it says $105!"
- Actual: Display showed cached $100, executed at fresh $105

**Solutions**:
- Show cache timestamp: "Price as of 3:42 PM"
- Warning: "Final price confirmed at execution"
- Reduce cache TTL to 1 minute
- Implement WebSocket real-time updates

---

### 20. Docker Volume Permissions

**Status**: ⚠️ Platform-Specific Issue
**Impact**: LOW - Affects Docker development

**Scenario**:
- Linux hosts may have permission issues
- Node_modules volume owned by root
- Cannot install packages

**Symptoms**:
```
sh: vite: not found
EACCES: permission denied
```

**Solutions**:
- Run container as user 1000:1000
- Use named volumes instead of bind mounts
- `chmod` permissions in Dockerfile
- Run `npm install` as entrypoint

**Code References**:
- `docker-compose.yml` - Volume configuration
- `frontend/Dockerfile.dev` - User setup

---

## Performance Considerations

### 21. N+1 Query Problem (Holdings)

**Status**: ⚠️ Potential Performance Issue
**Impact**: MEDIUM - Slow portfolio page with many holdings

**Scenario**:
- Portfolio has 50 different holdings
- Each holding queries current price
- 50 separate API calls or database queries

**Current Mitigation**:
- Price caching reduces API calls
- Frontend batch requests (React Query)
- Acceptable for small portfolios (<20 holdings)

**Future Optimization**:
- Batch price fetching
- Single API call for multiple symbols
- Eager loading in SQL queries
- GraphQL DataLoader pattern

---

### 22. Large Transaction History

**Status**: ⚠️ Pagination Needed
**Impact**: MEDIUM - Slow page load for active portfolios

**Scenario**:
- Portfolio with 1,000+ transactions
- Loading all on page load
- Large payload, slow render

**Current State**:
- No pagination in transaction history
- Loads all transactions for portfolio
- Frontend renders all rows

**Future Enhancement**:
- Paginate transaction history (20-50 per page)
- Virtual scrolling for large lists
- Filter by date range
- Search transactions

**Code References**:
- `backend/src/papertrade/adapters/inbound/api/routes.py` - No pagination limits
- `frontend/src/components/features/portfolio/TransactionHistory.tsx` - Renders all

---

## API & Integration Limitations

### 23. Alpha Vantage Single Point of Failure

**Status**: ⚠️ No Fallback Provider
**Impact**: HIGH - Total market data failure if API down

**Scenario**:
- Alpha Vantage service outage
- API degradation
- Account suspended

**Result**:
- All trades fail
- No price updates
- Application unusable for trading

**Future Mitigation**:
- Multi-provider support (Finnhub, IEX Cloud, Polygon)
- Fallback chain: Primary → Secondary → Cached
- Circuit breaker pattern
- Provider health monitoring

**Code References**:
- `backend/src/papertrade/application/ports.py` - MarketDataPort abstraction ready
- Just need additional adapter implementations

---

### 24. No Cryptocurrency Support

**Status**: ❌ Not Planned
**Impact**: LOW - Different use case

**Reason**:
- Alpha Vantage has crypto data
- But crypto trading very different
- 24/7 markets (no close)
- Higher volatility
- Different terminology (coins vs shares)

**Future Possibility**:
- Separate crypto portfolio type
- Different validation rules
- 24/7 price updates
- Fractional coins standard

---

## Development & Testing Limitations

### 25. E2E Tests Cannot Execute Real Trades (CI)

**Status**: ⚠️ CI Environment Limitation
**Impact**: MEDIUM - Limited E2E coverage

**Issue**:
- CI environment blocks external DNS
- Cannot reach Alpha Vantage API
- E2E tests verify UI only, not full flow

**Current Coverage**:
- Portfolio creation: ✅ Full
- Trade form display: ✅ Full
- Trade submission: ⚠️ UI only (API call fails)
- Holdings update: ❌ Not verified in CI

**Workarounds**:
1. **Request domain whitelist**: `www.alphavantage.co`
2. **Mock server**: Wiremock/MSW to simulate API
3. **In-memory adapter**: Override MarketDataPort in tests
4. **Pre-populated cache**: Load Redis with fake prices

**Recommended**: Option #1 (whitelist) for true E2E testing

**Code References**:
- `docs/e2e-testing-alpha-vantage-investigation.md` - Full investigation
- `frontend/tests/e2e/trading.spec.ts` - Current E2E tests

---

### 26. Demo API Key Limitations

**Status**: ⚠️ Development Constraint
**Impact**: MEDIUM - More restrictive than free tier

**Demo Key**: `ALPHA_VANTAGE_API_KEY=demo`

**Limitations**:
- Only works for specific symbols (IBM, AAPL, MSFT)
- May have lower rate limits
- Could be throttled for excessive use
- Not suitable for production

**Solution**:
- Get free API key: https://www.alphavantage.co/support/#api-key
- Add to `.env`: `ALPHA_VANTAGE_API_KEY=YOUR_KEY_HERE`
- Production: Use environment variables or secrets manager

**Code References**:
- `.env.example` - API key configuration
- `backend/src/papertrade/config/settings.py` - Environment loading

---

## Summary

### High-Impact Limitations (Address First)

1. ❌ **No SELL orders** - Blocks portfolio rebalancing
2. ❌ **No authentication** - Blocks production deployment
3. ⚠️ **API rate limits** - Blocks multi-user scenarios
4. ❌ **No monitoring** - Blocks observability in production

### Medium-Impact Limitations (Address Soon)

5. ⚠️ **Browser alerts** - Poor UX
6. ⚠️ **No charts** - Limited analytics
7. ⚠️ **Mobile responsiveness** - Excludes mobile users
8. ⚠️ **No backups** - Risk of data loss

### Low-Impact Limitations (Can Wait)

9. ❌ **Fractional shares** - Nice to have
10. ❌ **Limit orders** - Advanced feature
11. ❌ **Multi-currency** - Niche use case
12. ⚠️ **LocalStorage sessions** - Works for now

---

**For detailed workarounds and solutions, see the individual sections above.**

**For feature roadmap, see** [FEATURE_STATUS.md](./FEATURE_STATUS.md).

**For usage guidance, see** [USER_GUIDE.md](./USER_GUIDE.md).

---

**Last Updated**: January 4, 2026
**Maintained By**: PaperTrade Development Team
