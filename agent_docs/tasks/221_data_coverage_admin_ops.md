# Task 221 — Data-coverage admin ops: validation, delete, gap ranges, lookback config

## Overview

Three backend additions plus one config knob, all surfaced through the existing
admin data-coverage page:

1. **Ticker validation on pin** — `POST /admin/watchlist` currently accepts any
   symbol that passes the `Ticker` value-object regex. We've ended up with
   garbage like `T`, `TS`, `TES` in the DB. Reject symbols Alpha Vantage doesn't
   recognise before persisting.
2. **Hard delete** — `DELETE /admin/data-coverage/tickers/{ticker}` — admin
   only; removes the ticker from `ticker_watchlist` (hard delete, not the
   existing soft-delete unpin) **and** purges its `price_history` rows. This is
   the "this ticker was bogus, get rid of it entirely" escape hatch.
3. **Gap ranges in the coverage response** — add `gap_ranges` to each
   `TickerCoverageEntry` so the frontend can render an inline mini-viz.
4. **`ZEBU_HISTORY_MAX_LOOKBACK_DAYS` env knob** — when set, clamps the
   effective epoch to `max(ZEBU_HISTORY_EPOCH, today - lookback)`. Defaults to
   unset (no clamp). Set to `100` on prod to match AV free-tier reality.

## Context

### What exists

- `backend/src/zebu/adapters/inbound/api/admin_data_coverage.py` — `GET
  /admin/data-coverage`, `POST /admin/data-coverage/backfill`.
- `backend/src/zebu/adapters/inbound/api/admin_watchlist.py` — `POST
  /admin/watchlist` (pin) + `DELETE /admin/watchlist/{ticker}` (soft unpin).
- `backend/src/zebu/application/queries/data_coverage.py` — already computes
  `gap_days_count` per ticker by intersecting the trading-day calendar with
  covered dates. The intermediate `expected_trading_days - covered` set is
  exactly the data we need to surface as `gap_ranges`; we just need to expose
  it.
- `backend/src/zebu/adapters/inbound/api/dependencies.py:107` — `get_history_epoch`
  reads `ZEBU_HISTORY_EPOCH`; default `2015-01-01`.
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` —
  AV adapter; has a `_is_premium_refusal` helper that already detects the
  free-tier `outputsize=full` refusal.
- `backend/src/zebu/adapters/outbound/repositories/watchlist_manager.py` —
  `WatchlistManager.add_ticker / remove_ticker` (soft delete via
  `is_active=False`).
- `backend/src/zebu/adapters/outbound/repositories/price_repository.py` — the
  price-history repo. There is **no** existing "delete all rows for ticker"
  method; you'll need to add one.

### What's confirmed empirically (2026-05-25)

Real-key AV check against AAPL:

- `outputsize=compact` → exactly 100 trading days, oldest `2025-12-30`, newest
  `2026-05-22`.
- `outputsize=full` → premium-refusal "Information" payload, no data.

So the AV free-tier rolling window is genuinely ~100 days. The current
`ZEBU_HISTORY_EPOCH` default of `2015-01-01` produces a `gap_days_count` of
~2800 trading days for every ticker — useless as a signal. The lookback knob
lets us match the env to reality without lying about what data is reachable.

## Architecture

### Domain / Application changes

**`DataCoverageEntry`** (in `application/queries/data_coverage.py`) — add:

```python
@dataclass(frozen=True)
class GapRange:
    """Inclusive date range with no daily-bar coverage."""
    start: date
    end: date
```

Then add `gap_ranges: tuple[GapRange, ...]` to `DataCoverageEntry`. Computed
inside the same handler that already produces `gap_days_count`: collapse the
`expected_trading_days - covered` sorted-date set into contiguous runs.
**Use the trading-day calendar adjacency, not raw date adjacency** — Friday and
Monday are adjacent trading days even though they're 3 calendar days apart, so
a gap covering Fri+Mon should be one range, not two.

**Ticker validation port** — `application/ports/ticker_validator.py`:

```python
class TickerValidatorPort(Protocol):
    async def is_recognised(self, ticker: Ticker) -> bool: ...
```

Implementation in `adapters/outbound/market_data/`:

```python
class AlphaVantageTickerValidator:
    """Validates a ticker by calling AV's SYMBOL_SEARCH or GLOBAL_QUOTE.

    GLOBAL_QUOTE is cheaper (1 call, single JSON object). If the
    response has a non-empty ``Global Quote`` block with a non-zero
    price, the ticker is recognised. An empty ``Global Quote`` object
    means AV doesn't know the symbol.
    """
```

Wire this into a new dependency factory (`get_ticker_validator`) following the
same pattern as `get_market_data`.

### Endpoint changes

**`POST /admin/watchlist`** — add validation step before `manager.add_ticker`:

```python
validator: TickerValidatorPort = await get_ticker_validator(...)
if not await validator.is_recognised(ticker):
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Ticker {ticker.symbol} is not recognised by the "
               "market-data provider.",
    )
```

**`DELETE /admin/data-coverage/tickers/{ticker}`** — new endpoint, admin only.
Hard-deletes:

- All rows in `ticker_watchlist` for this symbol (not soft unpin — actually
  delete the row).
- All rows in `price_history` for this symbol (any interval, any source).
- Any non-terminal `BackfillTask` rows for this ticker → mark as `failed` with
  reason "ticker deleted by admin" so the scheduler stops touching them.

Returns 204 on success, 404 if the ticker is not present anywhere (no
watchlist row AND no price-history rows). Add an idempotency check: a second
DELETE on the same already-removed ticker returns 404, not 204 — same
pattern as the existing unpin endpoint.

### Config

**`ZEBU_HISTORY_MAX_LOOKBACK_DAYS`** — add to
`adapters/inbound/api/dependencies.py`:

```python
def get_effective_history_epoch() -> date:
    """Apply the lookback clamp on top of ZEBU_HISTORY_EPOCH.

    When ``ZEBU_HISTORY_MAX_LOOKBACK_DAYS`` is set to a positive int N,
    the effective epoch becomes ``max(ZEBU_HISTORY_EPOCH, today - N)``.
    Unset / empty / non-positive → no clamp, use the env epoch as-is.

    Set to 100 on AV free tier to match the rolling 100-day window; raise
    or unset when on AV premium.
    """
```

Replace the existing `HistoryEpochDep` wiring so handlers that compute the
coverage range use `get_effective_history_epoch`. Document the trade-off in the
docstring: when clamped, `gap_days_count` reflects only what's actually
reachable from the data provider, not the (aspirational) historical depth.

### Frontend contract (informational — Task 222 will consume this)

New `GET /admin/data-coverage` response per-entry shape adds:

```json
{
  "gap_ranges": [
    {"start": "2026-04-12", "end": "2026-04-12"},
    {"start": "2026-05-15", "end": "2026-05-17"}
  ]
}
```

Ordered chronologically. Empty array when `gap_days_count == 0`.

New endpoint:

```
DELETE /api/v1/admin/data-coverage/tickers/{ticker}  → 204 | 404
```

`POST /api/v1/admin/watchlist` now returns 422 on unrecognised tickers (in
addition to the existing 400 on `InvalidTickerError`).

## Implementation plan

1. **Add `GapRange` + `gap_ranges` to the query handler** with tests:
   `tests/unit/application/queries/test_data_coverage.py`. Cover: zero gaps;
   single-day gap; multi-day contiguous gap; multiple disjoint gaps; gap at the
   head of the window; gap at the tail.
2. **Add `TickerValidatorPort` + `AlphaVantageTickerValidator`** with unit
   tests (mock the AV HTTP call). Cover: recognised ticker → True; empty
   Global Quote → False; AV "Information" rate-limit → raise the existing
   `MarketDataError` (do **not** swallow as False — operator needs to know
   we couldn't validate).
3. **Wire validation into `POST /admin/watchlist`** with integration tests.
4. **Add hard-delete endpoint + `PriceRepository.delete_all_for_ticker`** with
   integration tests. Test the cascade: watchlist row gone, price_history rows
   gone, non-terminal backfill tasks marked failed.
5. **Add lookback env + `get_effective_history_epoch`** with unit tests.
   Default unset → behaves like existing dep; set to 100 with epoch=2015-01-01
   → effective epoch is today-100d.
6. **Add `ZEBU_HISTORY_MAX_LOOKBACK_DAYS=100` to the prod env** via a
   separate manual deploy step. Document in the progress doc — do NOT bundle
   this into the PR commit (env changes need a server-side action on prod).

## Testing strategy

- Unit tests for the gap-range collapse logic (trading-calendar adjacency, not
  calendar-day adjacency).
- Unit tests for the AV validator (mocked HTTP).
- Integration tests using the real DB (test DB) for the hard-delete cascade.
- Integration test confirming validation rejects an unrecognised symbol with
  422 (mock the validator port).

## Success criteria

- Pin endpoint rejects unrecognised symbols with 422 — verified with one
  integration test using a mocked validator.
- Delete endpoint cascades correctly — verified with an integration test
  using the real DB.
- `gap_ranges` is present in the coverage response, populated correctly for
  the test fixtures.
- `ZEBU_HISTORY_MAX_LOOKBACK_DAYS=100` produces an effective epoch of
  `today - 100` when `ZEBU_HISTORY_EPOCH=2015-01-01`.
- All existing tests still pass; lint + typecheck clean.

## Out of scope

- The actual UI work (delete button, mini-viz) — that's Task 222.
- Cleaning up the existing bogus tickers (T, TS, TES) — Tim will do that
  through the new delete endpoint once it's deployed. Don't pre-populate any
  migration to delete them.

## Agent assignment

`backend-swe` (Sonnet 4.6). One PR. Follow the standard PR-lifecycle: open PR,
run `/code-review <PR#>`, address findings, self-merge on green.

## References

- AV empirical depth check: confirmed 100 days on free tier (2026-05-25).
- `agent_docs/tasks/220_watchlist_admin_surface.md` — pin/unpin pattern.
- `agent_docs/tasks/215_backfill_ux_rework.md` — coverage range computation.
- `docs/architecture/principles.md` — Clean Architecture rules.
