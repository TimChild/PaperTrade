# Test-quality work deferred from Wave 4-C

> NOTE for future cleanup: Wave 4-C ("convert critical-path tests to behavior-focused")
> closed the highest-impact implementation-focused offenders on the
> BacktestExecutor / SnapshotJob / trade-execution / strategy-generation paths.
> The items below were intentionally left for follow-up because each requires
> production-code changes that were out of scope for a pure test refactor PR
> (per the wave's "don't refactor production code" guardrail).

## Deferred items

### D1 — Datetime patch pattern in Alpha Vantage adapter tests (audit P1-4)

- **Files**:

  - `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py` (2 patches at lines 706, 748)
  - `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_holidays.py` (8 patches)
  - `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_cache.py` (8 patches)
  - `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_current_price.py` (8 patches; assertions converted to behavior-focused in Wave 4-C, but the patches themselves remain)
  - `backend/tests/integration/adapters/test_alpha_vantage_adapter.py` (7 patches)

- **Why deferred**: the audit's recommended fix is to inject a `Clock` protocol
  (or `Callable[[], datetime]`) into `AlphaVantageAdapter.__init__` so tests can
  pass a stub clock instead of patching the `datetime` module. That is a
  production-code refactor and was explicitly out of scope for Wave 4-C.

- **Recommended next step**: bundle with the next AlphaVantageAdapter touch in
  Phase B3 / C0 (Tim's note in the audit: "should land alongside any other
  AlphaVantageAdapter refactor in Phase B3").

### D2 — Implementation-focused asserts on cache-tier ordering in `test_alpha_vantage_adapter.py`

- **File / lines**: `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py:835-880, 936-940`
- **Pattern**:

  ```python
  mock_price_cache.get_history.assert_called_once()
  mock_price_repository.get_price_history.assert_not_called()
  mock_price_cache.set_history.assert_called_once()
  ```

- **Why deferred**: these three tests in `TestRedisCachingIntegration` assert
  on which tier (Redis vs DB vs API) was checked and in what order. The
  observable side effect ("API was not called", measured via the rate limiter)
  is already asserted; the remaining `assert_called_once` calls are checking
  internal call ordering. Converting them to a real `PriceCache` + fakeredis
  would change the assertion shape (verify cache state instead of call count),
  but doing it cleanly requires also changing the `mock_price_repository`
  fixture into a fake (or making the test a sociable `Adapter + real cache +
  fake repo` test). Held back to keep this PR scoped to ~10-15 tests.

- **Recommended next step**: wrap into a "convert all Alpha Vantage adapter
  tests to behavior-focused" follow-up PR alongside D1 (the `Clock` injection)
  so the whole adapter-test surface is rewritten in one consistent style.

### D3 — `test.P1-3` (Every E2E test forces a real Clerk sign-in)

- **File**: `frontend/tests/e2e/fixtures.ts`, `dark-mode.spec.ts`, `not-found.spec.ts`
- **Why deferred**: this is a frontend E2E concern, not a backend behavior-focused
  conversion. Already tracked under audit `test.P1-3`; the SUMMARY's wave plan
  pairs it with the E2E hardening work, not with backend test refactors.

### D4 — `MagicMock` price_repository in alpha_vantage_weekend_current_price.py

- **File**: `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_current_price.py`
- **Why deferred**: Wave 4-C replaced `mock_price_cache` with a real
  `PriceCache` + fakeredis. The remaining `mock_price_repository` is still a
  `MagicMock` because `PriceRepository` is a SQL-backed adapter and lacks an
  in-memory port adapter today. Adding one would be a small but separate
  feature (an `InMemoryPriceRepository` class implementing the port) and is
  appropriate to ship with the same Phase B3 / C0 Alpha Vantage touch.

- **Recommended next step**: when D1 lands, also add an `InMemoryPriceRepository`
  to `application/ports/` and migrate these tests off `MagicMock` entirely.

## What Wave 4-C *did* close

For traceability, here are the conversions that landed in this PR:

- `backend/tests/unit/application/services/test_snapshot_job.py` — replaced
  inline duplicate `InMemorySnapshotRepository` (87 LOC) with the canonical
  `application.ports.in_memory_snapshot_repository.InMemorySnapshotRepository`;
  converted 7 assertions that poked at `snapshot_repo._snapshots` (internal
  state) to use the public protocol methods (`get_latest`, `get_range`,
  `get_by_portfolio_and_date`).

- `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_current_price.py` —
  replaced `mock_price_cache: MagicMock` (used in 8 tests) with a real
  `PriceCache` backed by `fakeredis`. The implementation-focused assertion
  pattern `mock_price_cache.set.assert_called_once(); call_args[1]["ttl"] == 7200`
  was replaced with behavior-focused queries: `await cache.get(ticker)` for the
  cached value and `await cache.get_ttl(ticker)` for the TTL.

Total: 20 tests touched, 8 implementation-focused assertions removed, 1
duplicate fake removed.
