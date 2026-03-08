# Task 200: Phase 4 Architecture Design — Automated Trading Strategies & Backtesting

**Agent**: architect
**Priority**: High

## Project Context

Zebu is a paper trading platform where users practice trading strategies without real money. It follows Clean Architecture (Ports & Adapters) with a Python/FastAPI backend and React/TypeScript frontend.

**What exists today (Phases 1–3):**
- Users create portfolios, deposit cash, buy/sell stocks at current or historical prices
- Daily portfolio snapshots track value over time (now with per-holding breakdown)
- Performance analytics: line charts, composition pie charts, composition-over-time stacked area charts
- Market data from Alpha Vantage with 3-tier caching (Redis → PostgreSQL → API)
- All domain entities are pure and immutable; holdings are derived from transactions via pure functions
- An `as_of` parameter already exists on trade commands for executing trades at historical dates/prices

## Objective

Design the architecture for Phase 4: users define trading strategies and execute them over historical periods (e.g., 3 months of 2025), rapidly generating all the trades that strategy would have produced. This lets users test ideas before committing to them in their paper portfolio.

The design should answer: what new domain concepts are needed, how does execution work, how do results integrate with the existing analytics system, and what's the implementation plan?

## What To Investigate

Thoroughly explore the current codebase before designing. Key areas:

- **Trade execution flow**: Commands in `backend/src/zebu/application/commands/` — how `as_of` works, what validation happens, whether existing handlers can be reused or need wrapping
- **Domain model**: Entities in `backend/src/zebu/domain/entities/` — how Portfolio, Transaction, and Holding relate, what would need to change
- **Market data**: `backend/src/zebu/application/ports/market_data_port.py` and adapters — what historical data methods exist, rate limits, caching behavior
- **Portfolio calculator**: `backend/src/zebu/domain/services/portfolio_calculator.py` — pure computation over transactions, potential for reuse
- **Snapshot system**: `backend/src/zebu/application/services/snapshot_job.py` — daily snapshots, backfill capability, known gap where backfill uses current prices instead of historical
- **Architecture patterns**: How dependency injection works, how ports/adapters compose, what in-memory implementations exist for testing

## Known Context From Prior Audit

These facts were confirmed by investigation — use them as starting points, not constraints:

- The `as_of` mechanism means existing trade handlers could potentially be reused for backtesting
- `PortfolioCalculator` is pure static (no I/O) — holdings derived from transactions
- `MarketDataPort` has `get_price_at(ticker, timestamp)` and `get_price_history(ticker, start, end, interval)` already
- All ports use Python `Protocol` with in-memory implementations available
- Alpha Vantage free tier: 5 calls/min, 500/day — but each call returns ~20 years of daily data, persisted permanently in PostgreSQL
- `backfill_snapshots()` has a known bug: uses current prices instead of historical — acknowledged in a code comment
- No way to distinguish backtest portfolios from regular paper-trading portfolios currently

## Design Areas To Address

1. **Strategy Definition** — How users define what a strategy does. Consider the full spectrum from simple predefined templates to flexible user-defined rules. What's the right starting point for a v1?

2. **Backtest Execution** — How a strategy gets evaluated against historical data to produce trades. Think about performance, data access patterns, and whether to reuse or wrap existing trade infrastructure.

3. **Results & Portfolio Model** — How backtest results relate to the existing portfolio/transaction/snapshot model. Should backtests produce real portfolio records? Something separate? A hybrid?

4. **Analytics Integration** — How users view and compare backtest results. Can the existing performance/composition analytics system be reused?

5. **Data Readiness** — How to handle the case where historical price data hasn't been fetched yet for tickers in a strategy.

6. **API Design** — What new endpoints are needed and how they fit alongside existing ones.

7. **Implementation Phases** — What to build first (MVP) vs later. Consider what delivers value fastest.

## Deliverable

A design document placed in `docs/architecture/phase4-trading-strategies.md` containing:

1. **Domain model** — New entities/value objects, relationships to existing model (diagrams welcome)
2. **Execution flow** — How a backtest runs from request to results (sequence diagram)
3. **API design** — New endpoints with request/response shapes
4. **Data model** — New tables/columns needed, migration strategy
5. **Performance analysis** — Expected scale, optimization approach
6. **Implementation plan** — Phased breakdown, what to build first
7. **Trade-offs** — Key decisions with rationale, alternatives considered

## Constraints

- Preserve Clean Architecture (dependency rule, pure domain layer)
- Don't break existing paper-trading functionality
- Reuse existing infrastructure where it makes sense — but don't force it if a different approach is better
- Design doc only — no implementation code
- Backend architecture only (frontend will be designed separately)
