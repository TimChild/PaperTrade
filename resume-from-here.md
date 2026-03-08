# Resume From Here

> **Written**: March 8, 2026
> **Purpose**: Temporary file for the next agent/session to quickly understand current state. Delete after reading.

## Current State

**Production is deployed and healthy** at `192.168.4.112` (Proxmox VM). All services running.

**No open PRs.** All PRs have been merged or closed. The repository is clean.

### What Was Done This Session (March 7–8, 2026)

1. **Bug fixes** (pushed directly to main):
   - `snapshot_job.py` — was silently dropping holdings when price lookups failed. Now raises `MarketDataUnavailableError`. Cleaned 75 bad snapshots from production DB.
   - Analytics API — Pydantic serialized `Decimal` as JSON strings, breaking charts/tooltips/stats. Fixed with `JsonFloat = Annotated[Decimal, PlainSerializer(float)]` pattern. Added Y-axis auto-scaling.

2. **Merged PRs**:
   - **#192** — Backend: deterministic weekend cache tests + batch portfolio balances endpoint
   - **#193** — Frontend: click-to-trade from price charts, holdings price polish, 5-min auto-refetch
   - **#194** — Docs reorg: `agent_tasks/` → `agent_docs/tasks/`, MkDocs config, GitHub Pages workflow
   - **#195** — Backend: `HoldingBreakdown` domain entity, JSON column on snapshots, API extension
   - **#196** — Frontend: `CompositionOverTimeChart.tsx` stacked area chart using snapshot breakdown data
   - **#200** — Architecture: Phase 4 design document for trading strategies & backtesting (reviewed, revised)

3. **Closed PRs** (superseded):
   - **#197** — Empty duplicate of #196
   - **#198, #199** — Earlier architect runs superseded by #200
   - **#174** — Stale price data granularity design from January

## What's Next: Phase 4 — Trading Strategies & Backtesting

The architecture design is finalized in `docs/architecture/phase4-trading-strategies.md`. Read that document before starting implementation.

### Implementation Order (from the design doc)

**Prerequisite**: Fix `backfill_snapshots()` bug — must use `get_price_at()` for historical dates instead of `get_current_price()`. Located in `backend/src/zebu/application/services/snapshot_job.py`.

**Phase 4.1 — Foundation**:
1. Extract `trade_factory.py` — shared pure domain functions (`create_buy_transaction()`, `create_sell_transaction()`) used by both existing handlers and new backtest builder
2. Refactor `BuyStockHandler` and `SellStockHandler` to call trade_factory (no behavior change)
3. Add `PortfolioType` enum + field to `Portfolio` entity
4. Create `Strategy` and `BacktestRun` domain entities
5. Create `TradeSignal` value object
6. Alembic migrations (portfolio_type column, new tables)
7. Repository ports + implementations (SQL + in-memory)

**Phase 4.2 — Execution Engine**: `HistoricalDataPreparer`, `BacktestTransactionBuilder`, `BacktestExecutor`, Buy & Hold strategy, API endpoints

**Phase 4.3 — More Strategies**: Strategy CRUD endpoints, DCA strategy, MA Crossover strategy

**Phase 4.4 — Polish**: Ticker validation, date range guards, error handling, integration tests

### Key Architecture Decisions (settled)

- Backtest portfolios are real `Portfolio` records with `portfolio_type = BACKTEST`
- All existing analytics endpoints work for backtest portfolios with zero changes
- Execution uses in-memory `BacktestTransactionBuilder` with **shared domain functions** (not duplicated logic)
- Three strategy types: Buy & Hold, Dollar-Cost Averaging, Moving Average Crossover
- Synchronous execution for v1 (3-year max date range)
- Pre-fetch all price data before simulation loop
- Summary metrics stored on `BacktestRun` entity (not a separate table for v1)

### Open Questions (see design doc Section 10)

Fractional shares, MA warm-up period, strategy deletion behavior, failure cleanup, concurrent backtests, backtest portfolio immutability, rate limit handling.

## Useful Commands

- `task docs:serve` — Serve MkDocs locally (uses `uvx`, no install needed)
- `task quality:backend` — Format + lint + type check + test backend
- `task quality:frontend` — Format + lint + type check + test frontend
- `task proxmox-vm:deploy` — Deploy to production
- `task proxmox-vm:status` — Check production health

## Test Counts (as of this session)

- Backend: ~717 tests passing
- Frontend: ~263 tests passing
