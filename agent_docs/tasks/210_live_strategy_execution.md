# Task: Live Strategy Execution

## Overview

Add the ability for users to activate a saved strategy for live paper-trading execution. When active, the system automatically generates and executes trade signals on a schedule (daily at market close), using real market prices against a designated portfolio.

## Context

### What Exists
- **Strategy entity** with 3 types: BuyAndHold, DCA, MovingAverageCrossover
- **TradingStrategy protocol** — `generate_signals(current_date, price_map, cash_balance, holdings) -> list[TradeSignal]`
- **BacktestExecutor** — loops over historical days calling `generate_signals`, then creates transactions
- **TradeFactory** — pure domain functions `create_buy_transaction`, `create_sell_transaction` (shared between live and backtest)
- **APScheduler** — already runs daily jobs (`refresh_active_stocks`, `calculate_daily_snapshots`)
- **Portfolio types**: `PAPER_TRADING` and `BACKTEST`

### What's Needed
The backtest executor already proves the strategies work. Live execution needs to:
1. Run strategies against **today's prices** (not historical)
2. Execute resulting signals as **real transactions** in a linked portfolio
3. Track execution state (active/paused, last run, errors)

## Architecture

### New Domain Concepts

**StrategyActivation entity** (new):
- `id` — unique identifier
- `user_id` — owner
- `strategy_id` — which strategy to execute
- `portfolio_id` — which portfolio to trade in
- `status` — `ACTIVE | PAUSED | STOPPED | ERROR`
- `frequency` — execution schedule (e.g., `DAILY_MARKET_CLOSE`)
- `last_executed_at` — timestamp of last run
- `last_error` — error message if status is ERROR
- `created_at`, `updated_at`

**No new portfolio type needed** — live strategies trade into existing `PAPER_TRADING` portfolios.

### Execution Flow

1. Scheduler triggers daily (after market data refresh)
2. Query all `ACTIVE` strategy activations
3. For each activation:
   a. Load the strategy, portfolio, and current holdings
   b. Fetch current/latest prices for the strategy's tickers
   c. Call `strategy.generate_signals(today, price_map, cash, holdings)`
   d. Execute each signal as a transaction via existing command handlers
   e. Update `last_executed_at`
   f. On error: set status to `ERROR`, log the error

### New API Endpoints

- `POST /strategies/{id}/activate` — activate a strategy with a target portfolio
- `POST /strategies/{id}/deactivate` — pause/stop execution
- `GET /strategies/{id}/activation` — get activation status
- `GET /activations` — list all user's active strategies
- `POST /activations/{id}/run-now` — manual trigger for testing

## Implementation Plan

### Phase 1: Backend Domain & Infrastructure

1. **StrategyActivation entity** — new domain entity in `backend/src/zebu/domain/entities/`
2. **StrategyActivation repository port** — in `backend/src/zebu/application/ports/`
3. **SQLModel implementation** — in `backend/src/zebu/adapters/outbound/persistence/`
4. **Alembic migration** — new `strategy_activations` table
5. **Commands & Handlers**:
   - `ActivateStrategy` / `DeactivateStrategy` / `ExecuteActiveStrategies`
6. **StrategyExecutionService** — application service that:
   - Loads activation + strategy + portfolio
   - Calls `generate_signals` with current data
   - Executes signals via existing `BuyStockHandler` / `SellStockHandler`
   - Handles errors gracefully (don't crash on one failed strategy)

### Phase 2: Scheduler Integration

7. **New scheduler job**: `execute_active_strategies`
   - Runs after `refresh_active_stocks` (so prices are current)
   - Calls `StrategyExecutionService` for each active activation
   - Log results (trades executed, errors)
8. **SchedulerConfig extension** — add strategy execution timing config

### Phase 3: API Endpoints

9. **Strategy activation endpoints** — in `backend/src/zebu/adapters/inbound/api/`
10. **Request/Response schemas** — in `backend/src/zebu/adapters/inbound/api/schemas/`

### Phase 4: Frontend UI

11. **Activate button** on strategy detail/card
12. **Activation status display** — shows active/paused/error state
13. **Execution log/history** — recent runs with trade counts
14. **Manual trigger button** — "Run Now" for testing

## Testing Strategy

- **Unit tests**: StrategyActivation entity, StrategyExecutionService (mock prices)
- **Integration tests**: Full flow — activate → execute → verify transactions created
- **Domain tests**: Signal generation already tested in backtest tests; reuse patterns

## Key Decisions

1. **Reuse TradingStrategy protocol** — same `generate_signals` interface for both backtest and live
2. **Reuse TradeFactory** — same transaction creation logic
3. **No new portfolio type** — strategies trade into existing paper-trading portfolios
4. **Daily execution only** — start simple, can add intraday later
5. **Graceful error handling** — one failed strategy doesn't block others

## Success Criteria

- [ ] User can activate a strategy linked to a portfolio
- [ ] System automatically executes signals daily after market data refresh
- [ ] Transactions appear in the linked portfolio's history
- [ ] User can pause/stop execution
- [ ] Errors are logged and don't crash the scheduler
- [ ] Full test coverage for the execution pipeline

## Agent Assignment

**Phase 1-3**: Backend SWE agent
**Phase 4**: Frontend SWE agent (after backend is merged)

## References

- Strategy entity: `backend/src/zebu/domain/entities/strategy.py`
- TradingStrategy protocol: `backend/src/zebu/domain/services/strategies/protocol.py`
- BacktestExecutor (pattern to follow): `backend/src/zebu/application/services/backtest_executor.py`
- TradeFactory: `backend/src/zebu/domain/services/trade_factory.py`
- Scheduler: `backend/src/zebu/infrastructure/scheduler.py`
- Existing commands: `backend/src/zebu/application/commands/`
