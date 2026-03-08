# Phase 4.2: Backtest Execution Engine + Buy & Hold Strategy + API Endpoints

**Agent**: backend-swe
**Priority**: High — Core execution engine for the backtesting feature
**Depends on**: PR #201 (trade_factory) and PR #202 (domain entities, migrations, repos) — both merged to main

## Objective

Implement the complete backtest execution pipeline: historical data preparation, in-memory transaction building, strategy protocol + Buy & Hold strategy, the orchestrating executor service, DI wiring, and all backtest + strategy CRUD API endpoints. After this task, a user can create a strategy, run a backtest, and view the results through the API.

## Architecture Reference

Read `docs/architecture/phase4-trading-strategies.md` thoroughly — it contains the execution flow sequence diagram, API specs, and all design decisions. Everything here implements that spec.

## What Already Exists (from PRs #201 and #202)

- `domain/services/trade_factory.py` — `create_buy_transaction()` and `create_sell_transaction()` pure functions
- `domain/entities/strategy.py`, `backtest_run.py`, `portfolio.py` (with `portfolio_type`)
- `domain/value_objects/trade_signal.py`, `portfolio_type.py`, `strategy_type.py`, `backtest_status.py`
- `domain/exceptions.py` — `InvalidStrategyError`, `InvalidBacktestRunError`
- Repository ports + SQL + in-memory implementations for Strategy and BacktestRun
- Alembic migrations for all new tables

## What to Implement

### 1. HistoricalDataPreparer (Application Service)

**New file**: `backend/src/zebu/application/services/historical_data_preparer.py`

This service pre-fetches all price data needed for a backtest before the simulation loop.

```python
class HistoricalDataPreparer:
    """Pre-fetches and validates historical price data for backtesting."""

    def __init__(self, market_data: MarketDataPort) -> None: ...

    async def prepare(
        self,
        tickers: list[str],
        start_date: date,
        end_date: date,
        warm_up_days: int = 0,
    ) -> dict[str, dict[date, PricePoint]]:
        """Fetch price history for all tickers covering the full date range.

        Args:
            tickers: Stock symbols to fetch
            start_date: First day of simulation
            end_date: Last day of simulation
            warm_up_days: Extra calendar days before start_date needed for indicators

        Returns:
            PriceMap: dict mapping ticker -> date -> PricePoint

        Raises:
            InsufficientHistoricalDataError: If any ticker is missing data
        """
```

Implementation:
- Call `self._market_data.get_price_history(Ticker(t), start_datetime, end_datetime, interval="1day")` for each ticker
- `start_datetime` should be `start_date - timedelta(days=warm_up_days)` converted to UTC datetime
- Build the nested dict structure by iterating over results and indexing by `.timestamp.date()`
- If any ticker returns no data, raise a new exception (see below)

Add `InsufficientHistoricalDataError` to `domain/exceptions.py` (or `application/exceptions.py` — follow project convention) as a subclass of `DomainException` or `BusinessRuleViolationError`.

### 2. BacktestTransactionBuilder (Stateful Helper)

**New file**: `backend/src/zebu/application/services/backtest_transaction_builder.py`

This is NOT a service — it's a stateful helper used only by BacktestExecutor. It maintains in-memory portfolio state (cash + holdings) and uses the shared `trade_factory` functions to create Transaction objects.

```python
class BacktestTransactionBuilder:
    """In-memory portfolio state tracker that creates validated transactions."""

    def __init__(self, portfolio_id: UUID, initial_cash: Money) -> None:
        self._portfolio_id = portfolio_id
        self._cash_balance: Money = initial_cash
        self._holdings: dict[str, Quantity] = {}
        self._transactions: list[Transaction] = []

    @property
    def cash_balance(self) -> Money: ...

    @property
    def holdings(self) -> dict[str, Quantity]: ...

    @property
    def transactions(self) -> list[Transaction]: ...

    def apply_signal(
        self,
        signal: TradeSignal,
        price_per_share: Money,
        timestamp: datetime,
    ) -> Transaction | None:
        """Apply a trade signal, creating a transaction if valid.

        For amount-based signals, resolves to whole-share quantity via
        floor(amount / price). Returns None if the signal cannot be executed
        (insufficient funds/shares, zero quantity after floor, etc).
        """
```

Key behaviors:
- For BUY signals with `amount`: compute `quantity = floor(signal.amount / price_per_share.amount)`. If 0, return None.
- For BUY signals with `quantity`: use directly
- Call `create_buy_transaction()` from trade_factory, catch `InsufficientFundsError` → return None
- For SELL: similar pattern with `create_sell_transaction()`, catch `InsufficientSharesError` → return None
- On success: update `self._cash_balance` and `self._holdings`, append to `self._transactions`

### 3. Strategy Protocol + Buy & Hold Implementation

**New file**: `backend/src/zebu/domain/services/strategies/protocol.py`

```python
from typing import Protocol

class TradingStrategy(Protocol):
    """Protocol that all strategy implementations must satisfy."""

    def generate_signals(
        self,
        current_date: date,
        price_map: dict[str, dict[date, PricePoint]],
        cash_balance: Decimal,
        holdings: dict[str, Decimal],
    ) -> list[TradeSignal]:
        """Generate trade signals for a given date."""
        ...
```

**New file**: `backend/src/zebu/domain/services/strategies/__init__.py`

**New file**: `backend/src/zebu/domain/services/strategies/buy_and_hold.py`

```python
class BuyAndHoldStrategy:
    """Buy proportionally on day 1 of the backtest, hold forever."""

    def __init__(self, tickers: list[str], allocation: dict[str, float]) -> None:
        """
        Args:
            tickers: Symbols to trade
            allocation: Fraction of cash per ticker (must sum to ~1.0)
        """
        self._tickers = tickers
        self._allocation = allocation
        self._has_bought = False
```

Implementation of `generate_signals`:
- On the first call (when `self._has_bought` is False): generate one BUY signal per ticker with `amount = cash_balance * allocation[ticker]`
- Set `self._has_bought = True`
- On all subsequent calls: return empty list

### 4. BacktestExecutor (Application Service)

**New file**: `backend/src/zebu/application/services/backtest_executor.py`

This is the main orchestrator. It follows the execution pipeline from the architecture doc:

```python
class BacktestExecutor:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        transaction_repo: TransactionRepository,
        strategy_repo: StrategyRepository,
        backtest_run_repo: BacktestRunRepository,
        snapshot_service: SnapshotJobService,
        data_preparer: HistoricalDataPreparer,
    ) -> None: ...

    async def execute(self, command: RunBacktestCommand) -> BacktestRun:
        """Run a complete backtest synchronously.

        Pipeline:
        0. Setup: Create BACKTEST portfolio, deposit initial cash
        1. Pre-fetch: Call HistoricalDataPreparer
        2. Simulate: Loop over trading days, generate signals, apply via builder
        3. Persist: Bulk-save all transactions
        4. Snapshot: Call backfill_snapshots()
        5. Metrics: Compute return, drawdown, etc. from snapshots
        6. Save BacktestRun with COMPLETED status and metrics
        """
```

Key implementation details:
- Create a `Portfolio` with `portfolio_type=PortfolioType.BACKTEST`
- Create an initial DEPOSIT transaction at `start_date`
- Resolve strategy type to the correct `TradingStrategy` implementation (only Buy & Hold for now)
- The simulation loop iterates over each calendar day from `start_date` to `end_date`. For each day, check if there's price data for that date in the price_map. If not (weekend/holiday), skip the day.
- After simulation, save all transactions via the repo
- Call `snapshot_service.backfill_snapshots()` to generate historical snapshots
- Compute summary metrics from the snapshots:
  - `total_return_pct = (final_value - initial_cash) / initial_cash * 100`
  - `max_drawdown_pct` — iterate snapshots, track running peak, compute max trough
  - `annualized_return_pct` — `((1 + total_return/100) ^ (365/days) - 1) * 100`
  - `total_trades` — count of BUY + SELL transactions (excluding DEPOSIT)
- Wrap the whole thing in try/except: on failure, save BacktestRun with `status=FAILED` and `error_message`

### 5. RunBacktestCommand

**New file**: `backend/src/zebu/application/commands/run_backtest.py`

```python
@dataclass(frozen=True)
class RunBacktestCommand:
    user_id: UUID
    strategy_id: UUID
    backtest_name: str
    start_date: date
    end_date: date
    initial_cash: Decimal
```

### 6. API Endpoints

**New file**: `backend/src/zebu/adapters/inbound/api/strategies.py`

Implement the following endpoints (all require authentication):
- `POST /strategies` — Create a strategy template
- `GET /strategies` — List user's strategies
- `GET /strategies/{strategy_id}` — Get strategy details
- `DELETE /strategies/{strategy_id}` — Delete a strategy

**New file**: `backend/src/zebu/adapters/inbound/api/backtests.py`

- `POST /backtests` — Run a backtest (synchronous)
- `GET /backtests` — List user's backtest runs
- `GET /backtests/{backtest_id}` — Get backtest run details
- `DELETE /backtests/{backtest_id}` — Delete backtest + associated portfolio

See the architecture doc Section 4 (API Design) for request/response schemas and error codes.

Validation in POST /backtests:
- `start_date < end_date`
- `end_date <= date.today()`
- `initial_cash > 0`
- Date range max 3 years: `(end_date - start_date).days <= 3 * 365`

### 7. DI Wiring

**Modify**: `backend/src/zebu/adapters/inbound/api/dependencies.py`
- Add factory functions for `StrategyRepository`, `BacktestRunRepository`
- Add factory for `HistoricalDataPreparer`
- Add factory for `BacktestExecutor`

**Modify**: `backend/src/zebu/adapters/inbound/api/api.py` (or wherever routers are registered)
- Register the new strategies and backtests routers

### 8. Tests

Write comprehensive tests for:

**Unit tests** (in `backend/tests/unit/`):
- `application/services/test_historical_data_preparer.py` — mock MarketDataPort, test data fetching and error cases
- `application/services/test_backtest_transaction_builder.py` — test buy/sell signal application, insufficient funds/shares handling, amount-to-quantity resolution, state tracking
- `application/services/test_backtest_executor.py` — mock all dependencies, test the full pipeline end-to-end with Buy & Hold
- `domain/services/strategies/test_buy_and_hold.py` — test signal generation (first day buys, subsequent days empty)

**Integration tests** (optional but valuable — test API endpoints with in-memory repos):
- Create strategy → run backtest → verify backtest completed with metrics

## Constraints

- Run `task quality:backend` after all changes — all tests must pass, ruff + pyright clean
- Follow existing code patterns for API endpoints (see `portfolios.py`, `transactions.py` for patterns)
- Follow existing dependency injection patterns in `dependencies.py`
- Use the existing `get_current_user` auth dependency for all endpoints
- All trade creation MUST go through `trade_factory` functions (no duplicated logic)
- Catch and handle `InsufficientFundsError`/`InsufficientSharesError` gracefully in the builder (return None, don't abort)
- The simulation loop should skip dates with no price data (weekends/holidays) rather than failing

## Success Criteria

- Strategy CRUD endpoints work (POST, GET list, GET detail, DELETE)
- Backtest endpoints work (POST runs synchronously, GET list, GET detail, DELETE cascades)
- Buy & Hold strategy produces correct signals
- BacktestExecutor runs the full pipeline: setup → prefetch → simulate → persist → snapshot → metrics
- BacktestTransactionBuilder correctly tracks cash/holdings state
- Summary metrics (return %, drawdown %, annualized return, trade count) are computed and stored
- Failed backtests are handled gracefully (FAILED status + error_message)
- All existing tests continue to pass
- `task quality:backend` passes cleanly
