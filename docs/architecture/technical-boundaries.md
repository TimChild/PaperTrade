# Zebu: Technical Boundaries & Limitations

**Last Updated**: March 7, 2026
**Version**: Phase 3 Complete

## Overview

This document outlines known technical limitations, edge cases, and architectural boundaries in the Zebu application. Understanding these constraints helps set expectations and guides future development.

---

## Current Capabilities (Implemented)

### SELL Orders — ✅ Implemented

Market sell orders with real-time pricing, holdings validation, and cost basis tracking.

- `backend/src/zebu/application/commands/sell_stock.py`
- `frontend/src/components/features/portfolio/TradeForm.tsx` (BUY/SELL toggle)

### User Authentication — ✅ Implemented (Clerk)

Full authentication via Clerk with JWT validation on the backend.

- **Frontend**: `@clerk/clerk-react` — `ClerkProvider`, `SignIn` components
- **Backend**: `clerk-backend-api` — `AuthPort` adapter pattern
- **Auth files**: `backend/src/zebu/adapters/auth/clerk_adapter.py`, `backend/src/zebu/application/ports/auth_port.py`
- Portfolios are scoped to authenticated users

### Portfolio Analytics & Charts — ✅ Implemented

Price charts (TradingView lightweight-charts), composition pie charts, and performance charts.

- `frontend/src/components/features/PriceChart/LightweightPriceChart.tsx`
- `frontend/src/components/features/analytics/CompositionChart.tsx`
- `frontend/src/components/features/analytics/PerformanceChart.tsx`
- Uses `recharts` and `lightweight-charts` libraries

### Toast Notifications — ✅ Implemented

Non-blocking toast notifications replaced `window.alert()`.

- `frontend/src/utils/toast.ts`
- Used in `CreatePortfolioForm`, `PortfolioCard`, `PortfolioDetail`

---

## Active Limitations

### 1. API Rate Limiting (Alpha Vantage)

**Status**: ⚠️ Active Limitation
**Impact**: HIGH — Affects all market data operations
**Limits**: 5 API calls/minute, 500 calls/day (free tier)

**Mitigation**:
- Redis caches recent prices (configurable TTL)
- APScheduler background job fetches popular stocks
- Reduces real-time calls by ~70-80%

**Solutions**:
- Wait 60 seconds on limit hit
- Upgrade to paid tier ($49.99/month for 75 calls/min)
- Multi-provider fallback (future)

**Relevant code**:
- `backend/src/zebu/adapters/outbound/market_data/` — API adapter
- `backend/src/zebu/infrastructure/cache/price_cache.py` — Redis caching
- `backend/src/zebu/infrastructure/scheduler.py` — Background updates

### 2. Market Orders Only

**Status**: ❌ Not Available
**Impact**: MEDIUM

Trades execute immediately at current market price. No limit orders, stop orders, or stop-limit orders.

### 3. Whole Shares Only (No Fractional Shares)

**Status**: ❌ Not Supported
**Impact**: MEDIUM

Must buy/sell integer quantities. Domain model uses `int` for quantity.

### 4. No Short Selling

**Status**: ❌ Not Supported
**Impact**: LOW

Cannot sell stocks you don't own. No margin accounts.

### 5. USD Currency Only

**Status**: ⚠️ Single Currency
**Impact**: MEDIUM

All prices in USD. International stocks show USD-equivalent via Alpha Vantage conversion.

### 6. No Real-Time Updates (WebSockets)

**Status**: ❌ Polling-Based
**Impact**: MEDIUM

Prices don't auto-update. React Query refetches on window focus; background scheduler updates the cache.

### 7. Alpha Vantage Single Point of Failure

**Status**: ⚠️ No Fallback
**Impact**: HIGH

If Alpha Vantage is down, all trades fail and no price updates occur. The `MarketDataPort` abstraction exists to support future multi-provider fallback.

---

## Edge Cases & Known Issues

### Concurrent Trade Conflicts

Two simultaneous trades on the same portfolio could theoretically overdraw the balance. PostgreSQL transaction isolation provides some protection, but no explicit optimistic locking exists yet.

### Stale Price Display

Cached prices may differ from execution prices. The display price could be minutes old while the actual trade fetches a fresh price.

### Large Transaction History

No pagination on transaction history. Portfolios with 1000+ transactions will load slowly.

---

## Infrastructure Limitations

### Single Database (No Sharding)

Single PostgreSQL instance. Sufficient for current scale (~100K portfolios). No read replicas or connection pooling (PgBouncer) configured.

### No Centralized Monitoring in Production

Backend logs to stdout (Docker logs). Grafana Cloud setup is documented but not confirmed as active. No Sentry or APM integration.

### E2E Tests Cannot Execute Real Trades in CI

CI environments may block external DNS. E2E tests verify UI flows but trade submission may fail without Alpha Vantage access.

---

## Summary

### Remaining High-Impact Gaps

| Gap | Impact | Planned |
|-----|--------|---------|
| API rate limits | HIGH | Multi-provider fallback (Phase 4) |
| Single market data provider | HIGH | Phase 4 |
| No real-time updates | MEDIUM | WebSockets (Phase 4) |
| No limit/stop orders | MEDIUM | Phase 4 |

### Recently Resolved

| Item | When |
|------|------|
| User authentication (Clerk) | Phase 3b |
| Portfolio charts & analytics | Phase 3 |
| Toast notifications (replaced alerts) | Phase 3 |
| SELL order support | Phase 3a |
