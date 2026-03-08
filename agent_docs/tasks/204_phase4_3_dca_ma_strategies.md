# Task 204: Phase 4.3 — DCA & MA Crossover Strategies + Quality Fixes

## Context

Phase 4.2 (PR #203) delivered the backtest execution engine, Buy & Hold strategy, and CRUD API endpoints. This task completes Phase 4.3 by implementing the remaining two strategy types (Dollar-Cost Averaging and Moving Average Crossover) and addresses a code quality issue identified during PR #203 review.

**Architecture reference:** `docs/architecture/phase4-trading-strategies.md`

## Priority 1: Fix Encapsulation Issue in BacktestExecutor

**THIS MUST BE DONE FIRST** — do not proceed to strategy implementation until this is resolved.

### Problem
In `backend/src/zebu/application/services/backtest_executor.py`, the `_compute_metrics()` method accesses a private attribute of `SnapshotJobService`:

```python
snapshot_repo = self._snapshot_service._snapshot_repo  # type: ignore[attr-defined]
```

This breaks encapsulation and requires a `type: ignore` comment.

### Fix
Inject `SnapshotRepository` directly into `BacktestExecutor` as a separate dependency. The executor already receives `SnapshotJobService` for `backfill_snapshots()` — it should also receive `SnapshotRepository` directly for metric queries.

**Changes required:**
1. Add `snapshot_repo: SnapshotRepository` parameter to `BacktestExecutor.__init__()` (after `snapshot_service`)
2. Store as `self._snapshot_repo`
3. In `_compute_metrics()`, replace `self._snapshot_service._snapshot_repo` with `self._snapshot_repo` and remove the `# type: ignore`
4. Update DI wiring in `backend/src/zebu/adapters/inbound/api/backtests.py` `_build_executor()` to pass `snapshot_repo` to the executor
5. Update ALL existing tests that construct `BacktestExecutor` to pass the new parameter
6. Verify pyright passes with zero errors on the changed files

## Priority 2: Dollar-Cost Averaging Strategy

### Architecture (from `docs/architecture/phase4-trading-strategies.md`)

**Parameters:**
| Key | Type | Description | Constraints |
|-----|------|-------------|-------------|
| `frequency_days` | int | Days between purchases | 1–365 |
| `amount_per_period` | str (Decimal) | USD amount to invest per period | > 0 |
| `allocation` | dict[str, float] | Split per-period amount across tickers | Must sum to 1.0 ± 0.001 |

**Signal generation logic:**
- Track the last purchase date
- On each trading day, check if `frequency_days` have elapsed since last purchase (or if it's the first day)
- If yes, generate BUY signals for each ticker: `amount = amount_per_period * allocation[ticker]`
- Use amount-based `TradeSignal` (not quantity-based)
- DCA invests a fixed dollar amount at regular intervals regardless of price

### Implementation

**File:** `backend/src/zebu/domain/services/strategies/dollar_cost_averaging.py`

```python
class DollarCostAveragingStrategy:
    def __init__(self, tickers: list[str], frequency_days: int, amount_per_period: Decimal, allocation: dict[str, float]) -> None: ...
    def generate_signals(self, current_date, price_map, cash_balance, holdings) -> list[TradeSignal]: ...
```

- Must satisfy the `TradingStrategy` protocol
- Stateful: tracks `_last_purchase_date`
- On first call + every `frequency_days` thereafter, emit BUY signals
- Uses `TradeSignal(action=TradeAction.BUY, ticker=..., signal_date=..., amount=...)`

**Tests:** `backend/tests/unit/domain/services/strategies/test_dollar_cost_averaging.py`
- First day triggers purchase
- Subsequent days within frequency window: no signals
- Day at frequency boundary: triggers purchase
- Multiple tickers with allocation fractions
- Zero cash balance: still generates signal (builder will skip if insufficient)
- Edge case: frequency_days=1 (daily purchases)

### Wire into BacktestExecutor

In `BacktestExecutor._build_strategy()`, add a case for `StrategyType.DOLLAR_COST_AVERAGING`:
- Extract `frequency_days`, `amount_per_period`, `allocation` from `strategy.parameters`
- Validate parameters exist and have correct types
- Instantiate `DollarCostAveragingStrategy`

## Priority 3: Moving Average Crossover Strategy

### Architecture (from `docs/architecture/phase4-trading-strategies.md`)

**Parameters:**
| Key | Type | Description | Constraints |
|-----|------|-------------|-------------|
| `fast_window` | int | Short-term SMA window (days) | 2–200, must be < slow_window |
| `slow_window` | int | Long-term SMA window (days) | 2–200, must be > fast_window |
| `invest_fraction` | float | Fraction of cash to invest on BUY signal | 0 < value ≤ 1.0 |

**Signal generation logic:**
- For each ticker, compute fast SMA and slow SMA from `price_map` historical data
- **BUY signal:** When fast SMA crosses ABOVE slow SMA (golden cross) AND no current position
- **SELL signal:** When fast SMA crosses BELOW slow SMA (death cross) AND has current position
- Use amount-based signals for BUY: `amount = cash_balance * invest_fraction`
- Use quantity-based signals for SELL: sell entire position
- Requires warm-up data: `slow_window` calendar days before simulation start

### Implementation

**File:** `backend/src/zebu/domain/services/strategies/moving_average_crossover.py`

```python
class MovingAverageCrossoverStrategy:
    def __init__(self, tickers: list[str], fast_window: int, slow_window: int, invest_fraction: float) -> None: ...
    def generate_signals(self, current_date, price_map, cash_balance, holdings) -> list[TradeSignal]: ...
    def _compute_sma(self, price_map_for_ticker: dict[date, PricePoint], as_of_date: date, window: int) -> Decimal | None: ...
```

- Must satisfy the `TradingStrategy` protocol
- Stateful: tracks previous day's SMA values per ticker for crossover detection
- `_compute_sma()` should look backward from `as_of_date` by `window` trading days (not calendar days — use the actual dates available in price_map)
- If insufficient data to compute SMA, return no signals for that ticker

**Tests:** `backend/tests/unit/domain/services/strategies/test_moving_average_crossover.py`
- Golden cross triggers BUY signal
- Death cross triggers SELL signal
- No crossover: no signal
- Insufficient data for SMA: no signals
- Already holding position: no duplicate BUY on continued bullish trend
- Multiple tickers: independent signal generation
- Edge case: fast_window=2, slow_window=3 (minimum windows)

### Warm-up Window Support

The executor must pass `warm_up_days` to `HistoricalDataPreparer.prepare()` for MA Crossover strategies.

In `BacktestExecutor._run_pipeline()`:
- After building the strategy with `_build_strategy()`, determine `warm_up_days`:
  - For `MOVING_AVERAGE_CROSSOVER`: `slow_window * 2` calendar days (to account for weekends/holidays within the trading window)
  - For other strategies: 0
- Pass to `self._data_preparer.prepare(tickers=..., start_date=..., end_date=..., warm_up_days=warm_up_days)`

### Wire into BacktestExecutor

In `BacktestExecutor._build_strategy()`, add a case for `StrategyType.MOVING_AVERAGE_CROSSOVER`:
- Extract `fast_window`, `slow_window`, `invest_fraction` from `strategy.parameters`
- Validate: both are ints, fast < slow, both in 2–200 range, invest_fraction is float in (0, 1.0]
- Instantiate `MovingAverageCrossoverStrategy`

## Priority 4: Strategy Parameter Validation

In `backend/src/zebu/adapters/inbound/api/strategies.py`, the `create_strategy` endpoint should validate strategy-specific parameters BEFORE creating the domain entity.

Add validation logic after resolving `strategy_type`:
- **BUY_AND_HOLD:** Validate `allocation` dict present, sums to ~1.0
- **DOLLAR_COST_AVERAGING:** Validate `frequency_days` (1–365), `amount_per_period` (> 0), `allocation` sums to ~1.0
- **MOVING_AVERAGE_CROSSOVER:** Validate `fast_window` (2–200), `slow_window` (2–200, > fast_window), `invest_fraction` (0 < value ≤ 1.0)

Return 422 with clear error messages for invalid parameters.

## Priority 5: Filter Backtest Portfolios from Portfolio List

From Phase 4.3 architecture doc step 6: "Update portfolio list response to include `portfolio_type`"

Check the existing `GET /portfolios` endpoint:
- If it doesn't already filter by `portfolio_type`, add filtering so BACKTEST portfolios don't appear in the regular portfolio list by default
- Add `portfolio_type` to the portfolio response DTO

## Quality Requirements

- All new code must pass `ruff format`, `ruff check`, and `pyright` with zero errors
- Run `task quality:backend` before considering yourself done
- Follow the existing test patterns in `test_buy_and_hold.py` (class-based tests, helper fixtures)
- All strategy implementations must satisfy the `TradingStrategy` protocol (duck typing — don't inherit from it)
- Use `Decimal` for all monetary calculations
- Log at DEBUG level (strategy signal generation, SMA values)

## Files to Create
- `backend/src/zebu/domain/services/strategies/dollar_cost_averaging.py`
- `backend/src/zebu/domain/services/strategies/moving_average_crossover.py`
- `backend/tests/unit/domain/services/strategies/test_dollar_cost_averaging.py`
- `backend/tests/unit/domain/services/strategies/test_moving_average_crossover.py`

## Files to Modify
- `backend/src/zebu/application/services/backtest_executor.py` (fix encapsulation, wire strategies, warm-up)
- `backend/src/zebu/adapters/inbound/api/backtests.py` (pass snapshot_repo to executor)
- `backend/src/zebu/adapters/inbound/api/strategies.py` (parameter validation)
- `backend/tests/unit/application/services/test_backtest_executor.py` (update for new constructor param)
- Portfolio list endpoint (filter backtest portfolios, add portfolio_type to response)
