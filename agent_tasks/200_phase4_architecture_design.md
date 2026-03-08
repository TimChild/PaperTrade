# Task 200: Phase 4 Architecture Design — Automated Trading Strategies & Backtesting

**Agent**: architect
**Priority**: High
**Estimated Effort**: 4-6 hours
**Status**: DRAFT — Do not launch yet

## Objective

Design the architecture for Phase 4: Automated Trading Strategies with Historical Backtesting. Users should be able to define trading strategies (rule-based) and run them over historical periods (e.g., 3 months), rapidly generating all buy/sell trades throughout that period based on the strategy rules.

## Context & Architecture Audit Findings

An audit of the current codebase found the architecture is **very well positioned** for this feature. The key findings:

### Strengths Already In Place

1. **`as_of` trade execution**: The `BuyStockHandler` and `SellStockHandler` command handlers already accept an `as_of: datetime | None` field. When provided, trades are recorded with the historical timestamp and priced via `market_data.get_price_at(ticker, as_of)`. A backtest engine can reuse these handlers directly.

2. **Pure domain model**: `Portfolio`, `Transaction`, and `Holding` entities are immutable and pure. `PortfolioCalculator` derives holdings from transactions via static methods — no I/O, no real-time coupling. Perfect for replay-based backtesting.

3. **Historical market data infrastructure**: `MarketDataPort` already defines `get_price_at(ticker, timestamp)` and `get_price_history(ticker, start, end, interval)`. The Alpha Vantage adapter implements 3-tier caching (Redis → PostgreSQL → API). Once fetched, ~20 years of daily data per ticker is stored permanently in PostgreSQL.

4. **Clean Architecture / Ports & Adapters**: All ports are Protocol-based with in-memory implementations available. A `BacktestEngine` can compose existing handlers with a specialized adapter.

5. **Date validations are compatible**: All constraints (`as_of` can't be future, `snapshot_date` can't be future, etc.) work correctly for historical backtesting.

### Known Gaps To Address

1. **Portfolio differentiation** — No way to distinguish "paper-trading" portfolios from "backtest result" portfolios. Needs either a `portfolio_type` field or a new linking entity.

2. **Snapshot backfill uses current prices** — `snapshot_job.py`'s `backfill_snapshots()` calls `get_current_price()` instead of `get_price_at(ticker, date)`. There's a comment in the code acknowledging this. Easy fix.

3. **Rate limits on first-time data import** — Alpha Vantage free tier: 5 calls/min, 500/day. Each ticker is 1 API call for full history, but 10 new tickers = 2 min wait. Need a data pre-warming/readiness check step.

4. **No strategy domain concept** — Need new entities for `Strategy` (rules, parameters) and `BacktestRun` (strategy + date range + result portfolio).

## Design Questions To Answer

The architecture doc should address:

### 1. Strategy Definition Model
- How do users define a strategy? (e.g., "Buy AAPL when 50-day MA crosses above 200-day MA, sell when it crosses below")
- What is the domain entity structure? Consider: `Strategy`, `StrategyRule`, `StrategyParameter`
- Should strategies be stored as structured data (JSON rules) or as code (Python expressions)?
- What built-in strategy types should we support initially? (e.g., Moving Average Crossover, RSI threshold, periodic rebalancing)

### 2. Backtest Execution Engine
- How does the engine iterate through trading days?
- How does it evaluate strategy rules against price data for each day?
- Should it create a real `Portfolio` + `Transaction` records, or use a separate in-memory model?
- Performance considerations: 3 months × 5 tickers = ~65 trading days × 5 evaluations. How fast can this be?
- Should execution be synchronous (API request → wait → result) or async (start job → poll for completion)?

### 3. Market Data Pre-Warming
- How do we ensure all required price history exists before a backtest starts?
- Should we have an explicit "prepare data" step, or do it lazily during execution?
- How do we handle tickers with incomplete history?

### 4. Portfolio Type Differentiation
- How to distinguish backtest portfolios from regular paper-trading portfolios?
- Options: (a) `portfolio_type` enum on Portfolio, (b) separate `BacktestRun` entity linking to portfolio, (c) both
- How should the UI handle this? Separate views? Filter toggle?

### 5. Results & Analytics
- What metrics should a backtest produce? (total return, Sharpe ratio, max drawdown, win rate, etc.)
- Can we reuse the existing snapshot/analytics system for backtest results?
- How do backtest results compare against a benchmark (e.g., S&P 500)?

### 6. API Design
- What new endpoints are needed?
- RESTful resource design for strategies and backtest runs
- Consider: `POST /strategies`, `POST /strategies/{id}/backtest`, `GET /backtest-runs/{id}/results`

## Key Files To Investigate

- `backend/src/zebu/application/commands/buy_stock.py` — `as_of` mechanism
- `backend/src/zebu/application/commands/sell_stock.py` — `as_of` mechanism
- `backend/src/zebu/application/ports/market_data_port.py` — historical data interface
- `backend/src/zebu/domain/entities/portfolio.py` — current portfolio model
- `backend/src/zebu/domain/entities/transaction.py` — transaction model
- `backend/src/zebu/domain/services/portfolio_calculator.py` — pure holdings calculation
- `backend/src/zebu/application/services/snapshot_job.py` — backfill_snapshots gap
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` — rate limits, caching
- `backend/src/zebu/adapters/outbound/repositories/price_repository.py` — historical price queries

## Deliverable

A design document (placed in `docs/architecture/phase4-trading-strategies.md`) that covers:
1. Domain model diagram (new entities + relationships to existing ones)
2. Sequence diagram for a backtest execution flow
3. API endpoint design
4. Data model changes (new tables, migrations needed)
5. Performance analysis and optimization strategy
6. Phased implementation plan (what to build first)
7. Trade-offs and decisions with rationale

## Constraints
- Must preserve Clean Architecture principles (dependency rule, pure domain)
- Must not break existing paper-trading functionality
- Should reuse existing infrastructure (command handlers, market data port, repositories) wherever possible
- Backend only — no frontend work in this task
- Design doc only — no implementation code

<!--
TODO: Before launching this task:
- Review with findings from PRs #194, #195, #196
- Add any additional context from those implementations
- Finalize the design questions based on user preferences
-->
