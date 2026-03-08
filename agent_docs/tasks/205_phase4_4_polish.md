# Task 205: Phase 4.4 — Polish & Integration Tests

## Context

Phase 4.1–4.3 are complete. All three strategy types (Buy & Hold, DCA, MA Crossover), the execution engine, CRUD endpoints, and portfolio filtering are implemented and merged. This task covers the final polish items from the architecture doc (`docs/architecture/phase4-trading-strategies.md`).

## Priority 1: Validate Strategy Tickers Against Supported Tickers

In `backend/src/zebu/adapters/inbound/api/strategies.py`, the `create_strategy` endpoint should validate that all tickers in the request are supported.

### Implementation

The `MarketDataPort` has a `get_supported_tickers()` method. Add validation in the `create_strategy` endpoint:

1. Add `MarketDataDep` to the endpoint's dependencies (import from `dependencies.py`)
2. After validating strategy-specific parameters, call `await market_data.get_supported_tickers()`
3. Check that every ticker in `request.tickers` is in the supported set
4. Return 422 with a clear message listing unsupported tickers if any are invalid

Example:
```python
supported = {t.symbol for t in await market_data.get_supported_tickers()}
unsupported = [t for t in request.tickers if t not in supported]
if unsupported:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported tickers: {', '.join(unsupported)}",
    )
```

## Priority 2: Handle HistoricalDataPreparer Failures with 503

In `backend/src/zebu/adapters/inbound/api/backtests.py`, the `run_backtest` endpoint should catch `InsufficientHistoricalDataError` and return a 503 response.

### Implementation

1. Import `InsufficientHistoricalDataError` from `zebu.domain.exceptions`
2. In the `run_backtest` endpoint, add a catch for this exception:
```python
except InsufficientHistoricalDataError as exc:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    ) from exc
```

This goes alongside the existing `InvalidStrategyError` catch block.

## Priority 3: Integration Tests for All Three Strategies

Create integration-style tests that exercise the full `BacktestExecutor` pipeline for each strategy type. These should test the complete flow: setup → prefetch → simulate → persist → snapshot → metrics.

### File: `backend/tests/integration/test_backtest_strategies.py`

Use the existing in-memory repository implementations and a mock market data adapter to avoid external dependencies while still testing the full pipeline.

**Test structure:**
```python
class TestBuyAndHoldIntegration:
    async def test_full_pipeline_completes_with_metrics(self): ...

class TestDCAIntegration:
    async def test_full_pipeline_with_periodic_purchases(self): ...

class TestMovingAverageCrossoverIntegration:
    async def test_full_pipeline_with_crossover_signals(self): ...
```

**Each test should:**
1. Create a strategy entity with appropriate parameters
2. Set up in-memory repos (portfolio, transaction, strategy, backtest_run, snapshot)
3. Create a mock market data adapter with realistic price data covering the date range
4. Instantiate `BacktestExecutor` with all dependencies
5. Run `execute()` with a `RunBacktestCommand`
6. Assert:
   - BacktestRun status is COMPLETED
   - Metrics are computed (total_return_pct, max_drawdown_pct, etc.)
   - Transactions were created
   - Portfolio exists with type BACKTEST

**For MA Crossover specifically:**
- Use price data that creates a clear golden cross followed by a death cross
- Verify both BUY and SELL transactions are generated

**Look at existing test patterns:**
- `backend/tests/unit/application/services/test_backtest_executor.py` for executor setup
- `backend/tests/unit/domain/services/strategies/test_buy_and_hold.py` for in-memory market data mock patterns
- In-memory repos: `backend/src/zebu/application/ports/in_memory_*.py`

## Priority 4: Documentation Updates

Update `docs/architecture/phase4-trading-strategies.md` to reflect implementation status:
- Add a "Status" section at the top noting all phases are complete
- Note any deviations from the original plan (if any)

Update `PROGRESS.md`:
- Mark Phase 4 as complete
- Add summary of what was delivered
- Update "Next Steps" section

## Quality Requirements

- All new code must pass `ruff format`, `ruff check`, and `pyright` with zero errors
- Run `task quality:backend` before considering yourself done
- Integration tests should use `pytest.mark.asyncio` decorator
- No external API calls in tests — use in-memory adapters/mocks only
- All existing tests must continue to pass (828+ tests)

## Files to Create
- `backend/tests/integration/test_backtest_strategies.py`

## Files to Modify
- `backend/src/zebu/adapters/inbound/api/strategies.py` (ticker validation)
- `backend/src/zebu/adapters/inbound/api/backtests.py` (503 error handling)
- `docs/architecture/phase4-trading-strategies.md` (status update)
- `PROGRESS.md` (completion update)
