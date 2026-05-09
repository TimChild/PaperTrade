# Audit — Test quality & flakiness

- **Auditor**: `quality-infra`
- **Slug**: `tests`
- **Date**: 2026-05-09
- **Phase**: B1
- **Scope**: `backend/tests/`, `frontend/tests/`, `frontend/playwright.config.ts`, `frontend/tests/setup.ts`, conftest files, plus auth-related code paths exercised in tests

## Executive summary

The test suite is in a healthier shape than the brief implied: **zero `pytest.mark.flaky` annotations, zero `@retry`, zero `pytest.skip`** in the backend, and only two skipped frontend tests (one per-environment skip, one explicitly skipped pending fix). Mock placement is *largely* clean — application-layer tests use real in-memory adapters rather than mocks, which is exactly the boundary discipline `CLAUDE.md` and `quality-infra.md` call for. The remaining issues, however, cluster into three deeply consequential failure modes that line up with Tim's "past flakiness was largely auth-related" observation:

1. **The Alpha Vantage `demo` API key is a live external dependency in CI E2E** — only IBM is supported by that key, with a 5/min, 25/day rate limit. With 21 E2E tests and `workers: 1`, a single CI run can exhaust the daily quota and produce non-deterministic failures unrelated to code under test. This is the single biggest flakiness root cause and is a **P0** because Phase C (live strategy execution + scheduler-driven trading) will multiply API calls and amplify the problem.
2. **Every E2E test signs in fresh against Clerk** — the per-test `clerk.signIn({ emailAddress })` strategy was the most recent fix (PR #171, #147) for an iterating series of auth-flakiness firefights. It's better than the prior storage-state approach but still creates a real network dependency on Clerk testing infra during 21 sign-ins per CI run, with `retries: 2` further amplifying load. Importantly, **this whole pattern will need to change for Phase C** when API-key auth is added — the current CI tests will not exercise the new path at all, and there are zero unit tests for either auth adapter today.
3. **Critical-path under-coverage** — `BacktestExecutor` (474 LOC, the canonical "iterate over days, generate signals, execute trades" loop that Phase C's live executor will mirror) has only 4 unit tests; `infrastructure/scheduler.py` (361 LOC) has 3 lifecycle tests with zero job-execution coverage; both Clerk and InMemory auth adapters have **zero** dedicated tests.

The good news: the foundation is solid. The application layer's mock-free style is a model the new Phase C/D code should follow. The fixes below are mostly *additive* (more coverage where it matters, swap the live external dependency for an injectable test double) rather than rip-and-replace.

## Findings

### P0 — Live Alpha Vantage `demo` key in E2E CI causes rate-limit flakiness

- **What**: `docker-compose.yml:66` defaults `ALPHA_VANTAGE_API_KEY` to `demo`, and CI's E2E job (`.github/workflows/ci.yml:165-185`) starts the full Docker stack without overriding it. The backend's `get_market_data` dependency (`backend/src/zebu/adapters/inbound/api/dependencies.py:186-256`) then constructs a real `AlphaVantageAdapter` that hits `https://www.alphavantage.co/query?...` over the network. The `demo` key only resolves `IBM`, which is why `frontend/tests/e2e/trading.spec.ts` hardcodes IBM 22 times across 6 tests with comments like `Note: Using IBM because the Alpha Vantage demo API key only supports IBM ticker`. Free tier limits are 5 requests/minute and 25 requests/day.
- **Why it matters**: With 21 E2E tests, `retries: 2` on CI, a price fetch on portfolio render *and* on every trade, and `workers: 1`, one CI run on a busy day can blow the 25/day cap mid-run — failures appear as "trade didn't complete in 5s" or "holding-symbol-IBM not visible" with no actionable signal. This is the highest-probability source of historical CI flakiness once Clerk session expiry was solved (PR #171).
- **Evidence**:

  - `frontend/tests/e2e/trading.spec.ts:31, 49, 81, 124, 174, 198, 287` — IBM hardcoded
  - `backend/src/zebu/adapters/inbound/api/dependencies.py:209-213` — defaults to `demo` key when env var unset
  - `.github/workflows/ci.yml:165-185` — passes Clerk vars but not a real Alpha Vantage key

- **Fix sketch**: Add a `MARKET_DATA_PROVIDER` env switch (`alpha_vantage` | `in_memory`) read in `get_market_data`. In CI E2E and docker-compose dev, set it to `in_memory` and seed prices via the existing `InMemoryMarketDataAdapter` (already used in `backend/tests/conftest.py:80-134` for backend integration tests). Remove the IBM hardcode from `trading.spec.ts` once the seeded adapter supports a richer set. **Phase C requires this change anyway** — agents can't run unattended overnight backtests against a live API with a 25/day cap.

### P0 — Zero unit tests for either auth adapter; auth-test pattern won't survive API-key auth (Phase C)

- **What**: `backend/src/zebu/adapters/auth/clerk_adapter.py` and `backend/src/zebu/adapters/auth/in_memory_adapter.py` have no dedicated tests. Auth is exercised end-to-end through API integration tests with hardcoded `Bearer test-token-default` headers (`backend/tests/conftest.py:189-196`), which means: (a) the only test of `verify_token` is implicit, and (b) when Phase C adds an `ApiKeyAuthAdapter` reading `Authorization: ApiKey <key>` or `X-API-Key: <key>`, none of the existing fixtures will route correctly — `auth_headers` only emits `Bearer ...`.
- **Why it matters**: Tim flagged auth-flakiness as the #1 historical pain. Without dedicated unit tests for the adapter contract (token expiry, malformed JWT, network failure on JWKS fetch, user-not-found), regressions land silently. More importantly, Phase C's plan (`docs/planning/agent-platform-proposal.md` §C2) adds a *second* auth path tried *after* Bearer — without a clear test boundary on `AuthPort.verify_token`, that middleware logic is going to be retro-tested at the integration layer where Clerk's behaviour is already a known flake source.
- **Evidence**:

  - `find backend/tests -name "test_*auth*"` returns nothing
  - `grep -rln "ClerkAuthAdapter\|InMemoryAuthAdapter" backend/tests/` only matches conftest setup, never test subjects
  - `backend/tests/conftest.py:136-159` constructs a singleton `InMemoryAuthAdapter` with one user; tests cannot easily test multi-user / token-expiry edge cases without breaking the singleton

- **Fix sketch**: Add `backend/tests/unit/adapters/auth/test_in_memory_adapter.py` covering `verify_token` happy/sad paths, multi-user, token rotation, and the empty-string token edge case. For `ClerkAuthAdapter`, add a unit test using `respx` or `httpx` mocking at the JWKS endpoint to cover signature validation, expired-token, missing-claim. Both belong **before** Phase C extends the port.

### P1 — `BacktestExecutor` (Phase C's blueprint) has only 4 unit tests over 474 LOC

- **What**: `backend/tests/unit/application/services/test_backtest_executor.py` contains 4 tests: `test_completed_backtest_has_completed_status`, `test_missing_strategy_raises_error`, `test_backtest_creates_portfolio`, `test_buy_and_hold_executes_trade_on_day1`. The executor itself is 474 lines covering day iteration, signal generation across 3 strategy types, transaction creation, snapshot writing, error/cancel paths, and metric calculation.
- **Why it matters**: `CLAUDE.md` lines 102-104 and the agent-platform proposal §C1 explicitly identify this file as the structural template the live executor will mirror. Any silent regression here propagates to live trading. The MA-crossover and DCA strategy-specific behaviour, the `cancel`/`fail` paths, the snapshot-on-each-day logic, and the `total_trades` / `final_value` reporting are all unverified by direct unit tests.
- **Evidence**:

  - `wc -l backend/src/zebu/application/services/backtest_executor.py` → 474
  - `grep -c "async def test" backend/tests/unit/application/services/test_backtest_executor.py` → 4

- **Fix sketch**: Add tests covering: MA-crossover strategy executes signals at crossover, DCA strategy executes on cadence, error mid-execution leaves run in `FAILED` not `RUNNING`, cancel mid-execution leaves `CANCELLED`, snapshot is written per simulated day, total-trades and final-value match expected when prices known. All achievable with the existing in-memory adapters — no new infra.

### P1 — `infrastructure/scheduler.py` job-execution paths untested

- **What**: `backend/tests/unit/infrastructure/test_scheduler.py` has 3 tests (config defaults, custom values, start/stop lifecycle). The 361-line scheduler module wires real cron triggers to `refresh_active_tickers_job` (and is the surface Phase C/F will extend with strategy-execution and trigger-evaluation jobs). The actual job functions, batch handling, the misfire grace, and the `max_age_hours` filter are not exercised.
- **Why it matters**: Phase C (`agent_docs/tasks/210_live_strategy_execution.md`) adds a scheduler-driven daily live-execution job. Phase F adds trigger evaluation on every tick. Both will be wired into this same scheduler. Building those on a thinly-tested base means the first regression surfaces in production at 09:30 ET on a Monday.
- **Evidence**: `grep -c "def test_" backend/tests/unit/infrastructure/test_scheduler.py` → 3 (excluding 4 config tests)
- **Fix sketch**: Add tests that invoke the registered job functions directly with a controlled clock (e.g. `freezegun`), verify `batch_size` / `batch_delay_seconds` are honoured, and assert the `max_age_hours` filter excludes stale tickers. Keep the schedule wiring (cron strings) tested at the integration layer — but cover the *function* behaviour at unit level.

### P1 — Every E2E test forces a real Clerk sign-in even when auth isn't load-bearing

- **What**: `frontend/tests/e2e/fixtures.ts:16-43` extends Playwright's `page` fixture so that *every* test, even `dark-mode.spec.ts` and `not-found.spec.ts` which are entirely UI-local, runs `setupClerkTestingToken` + `clerk.signIn` + waitForURL `/dashboard`. With 21 tests and `retries: 2`, that's 21–63 real Clerk roundtrips per CI run. Clerk testing tokens are fast and rate limits are higher than production, but the cost compounds with the price-API rate limits above and increases CI duration.
- **Why it matters**: Past commits show a *long* history of fighting Clerk-rate-limits in CI: PR #80, PR #83, PR #147 (shared storage state), PR #156 (E2E test mode reverted), PR #171 (per-test `clerk.signIn`). Each iteration moved closer to "real Clerk every test," which works when the rest of the system is healthy but breaks when stress accumulates. A test that doesn't need an authenticated session shouldn't pay this cost.
- **Evidence**:

  - `frontend/tests/e2e/fixtures.ts:16-43` — base `test` fixture always authenticates
  - `frontend/tests/e2e/dark-mode.spec.ts:1` — uses `import { test } from './fixtures'` despite never reading auth state
  - `frontend/tests/e2e/not-found.spec.ts:1` — same

- **Fix sketch**: Provide two fixtures: `test` (auth-required, current behaviour) and `unauthenticatedTest` (raw Playwright `test`, used by dark-mode, not-found, and any future "marketing route" tests). Sub-second saving per test, several minutes per CI run.

### P1 — Mock-on-`datetime` pattern across Alpha Vantage tests is brittle

- **What**: 11 separate tests in `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_*.py` use `with patch("zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime") as mock_datetime:` and reassign `mock_datetime.now.return_value`. Some also patch `zebu.application.dtos.price_point.datetime` (`backend/tests/integration/adapters/test_alpha_vantage_adapter.py:236`). This works but is fragile — any refactor that imports `datetime` differently (e.g. `from datetime import datetime as dt`) silently breaks the patch.
- **Why it matters**: This is the single most common mock pattern in the codebase. The fact that it's *adapter-level* mocking is fine (correct boundary). The brittleness is what hurts: when `dt.now()` returns wall-clock instead of mocked, the test passes locally on a Tuesday, fails on a holiday, and no one knows why.
- **Evidence**: `grep -rn "patch.*datetime" backend/tests/ | wc -l` → 14
- **Fix sketch**: Inject a `Clock` protocol (or `Callable[[], datetime]`) into `AlphaVantageAdapter.__init__` instead of importing `datetime` at module level. Tests pass a stubbed clock; production passes `datetime.now`. This is a `quality-infra` + `architect` fix and should land alongside any other AlphaVantageAdapter refactor in Phase B3.

### P2 — `time.sleep(0.01)` in two integration tests to force timestamp ordering

- **What**: `backend/tests/integration/adapters/test_sqlmodel_portfolio_repository.py:193` and `backend/tests/integration/adapters/test_sqlmodel_transaction_repository.py:113` use `time.sleep(0.01)` to ensure two consecutive `datetime.now()` calls produce different values. On a fast machine SQLite truncation could still produce a tie; on a slow CI runner this slows the suite by ~20ms × N tests.
- **Why it matters**: It works today but is non-deterministic in principle. Sleep-based ordering is a known anti-pattern.
- **Fix sketch**: Pass explicit `created_at=datetime.now() + timedelta(milliseconds=10)` to the second entity instead of relying on wall-clock advance.

### P2 — `it.skip` in `frontend/src/hooks/__tests__/usePriceQuery.test.tsx:46` with no follow-up

- **What**: `it.skip('handles ticker not found error', async () => { ... })`. No comment, no JIRA / GitHub issue link, no `// TODO:` explaining why it's skipped. The test exists but never runs.
- **Why it matters**: `quality-infra.md` says "no flaky tests, no quarantined tests." A silent `.skip` is exactly that — invisible debt.
- **Fix sketch**: Either fix the underlying issue (likely an MSW handler that doesn't return the 404 the test expects — see `frontend/src/mocks/handlers.ts`) and re-enable, or delete the test and add a behaviour-equivalent integration test elsewhere. Don't leave it skipped without a tracking issue.

### P2 — `test.skip()` for "empty state" test based on environment state, not deterministic

- **What**: `frontend/tests/e2e/multi-portfolio.spec.ts:144` skips when portfolios already exist. This means whether the test runs depends on prior test state — the global cleanup in `global-setup.ts` (`cleanupTestPortfolios`) only runs in dev with Docker access; in CI fresh DB the test runs, in CI re-runs against a persisted DB it might not, and locally with accumulated data it definitely won't.
- **Why it matters**: A test that doesn't always exercise its assertion is a test that doesn't exist for the failure case. CI signal is reduced silently.
- **Fix sketch**: Use Playwright's database-reset hook (or call `cleanupTestPortfolios` in a `beforeEach` for *just this test*) to guarantee an empty state, then run unconditionally.

### P2 — Several E2E tests use `page.waitForTimeout(2000-3000)` after trade actions

- **What**: `frontend/tests/e2e/trading.spec.ts` lines 44, 92, 136, 186, 214, 297. Six raw timeouts of 2–3 seconds. The comment "Wait for trade to process and page to update" implies the test author wasn't sure how to detect "trade complete."
- **Why it matters**: Sleep-based waits are the textbook flaky-test pattern. They pass when the system is fast, fail when CI is slow, mask actual regressions, and cost ~18 seconds across the trading suite alone.
- **Fix sketch**: Replace each with a deterministic wait — `expect(page.getByTestId('holding-symbol-IBM')).toBeVisible()` or wait on the success toast (`expect(page.getByText(/bought/i)).toBeVisible({ timeout: 5000 })`). The test already does the latter immediately above the timeout in most cases, so the timeout is doing nothing useful but adding wall-clock cost.

### P3 — `console.log` debug noise in `analytics.spec.ts`

- **What**: `frontend/tests/e2e/analytics.spec.ts:23-43` has 7 `console.log` / `console.error` calls in the beforeEach. Useful when debugging the test once; pure noise in CI logs ever after.
- **Fix sketch**: Remove or guard behind `process.env.DEBUG_E2E`.

## Root-cause hypothesis on past flakiness

Two compounding sources, both auth-and-network-shaped, with the second masking the first:

1. **Clerk testing infrastructure** had several real failure modes: 60-second token expiry (fixed PR #171), session-storage races between parallel workers (fixed PR #147), bot detection in test mode (fixed by `setupClerkTestingToken`). Each generation of the fix was sound but moved the chips around — solving one mode exposed the next. The current per-test `clerk.signIn` is the most stable shape so far.
2. **Live Alpha Vantage `demo` key** has been an *invisible* second-order flakiness source the whole time, attributed to "Clerk being flaky" because the symptoms (timeouts on portfolio/trade actions) look the same. Once Clerk is finally stable (post-#171), this becomes the dominant source — and Phase C will make it dramatically worse if not addressed first.

The hypothesis: **fix the Alpha Vantage dependency before Phase C, and Tim will see flakiness drop further than expected, because part of what he's been attributing to Clerk has been Alpha Vantage all along.** The Clerk fixes were real; they were just sharing the stage.

## Quick sanity stats

- Backend tests files: 80
- Backend tests LOC: ~20,000
- E2E tests: 21 across 7 spec files
- Skipped: 2 frontend (one `it.skip`, one conditional `test.skip()`); 0 backend
- `pytest.mark.flaky` / `@retry`: 0
- `time.sleep` in tests: 2 (both `0.01s` for ordering)
- `waitForTimeout` in E2E: 6 (all in `trading.spec.ts`)
- Application-layer tests with mocks: 0 (all use in-memory adapters — model citizen)
- Auth adapter tests: 0
- BacktestExecutor tests: 4 vs 474 LOC

## Recommendation summary

| # | Pri | Title | Fix locus |
|---|---|---|---|
| 1 | P0 | Replace live Alpha Vantage `demo` key in CI E2E with in-memory adapter | `backend/src/zebu/adapters/inbound/api/dependencies.py`, `docker-compose.yml`, `.github/workflows/ci.yml`, `frontend/tests/e2e/trading.spec.ts` |
| 2 | P0 | Add unit tests for `ClerkAuthAdapter` and `InMemoryAuthAdapter`; lay testing groundwork for Phase C API-key auth | `backend/tests/unit/adapters/auth/` (new) |
| 3 | P1 | Expand `BacktestExecutor` test coverage to match its critical-path status | `backend/tests/unit/application/services/test_backtest_executor.py` |
| 4 | P1 | Add scheduler job-execution unit tests | `backend/tests/unit/infrastructure/test_scheduler.py` |
| 5 | P1 | Split E2E fixtures into `test` (authed) and `unauthenticatedTest` | `frontend/tests/e2e/fixtures.ts`, `dark-mode.spec.ts`, `not-found.spec.ts` |
| 6 | P1 | Inject a clock instead of patching `datetime` module-level | `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` + tests |
| 7 | P2 | Replace `time.sleep(0.01)` with explicit timestamps | two repository integration tests |
| 8 | P2 | Resolve or delete `it.skip('handles ticker not found error')` | `frontend/src/hooks/__tests__/usePriceQuery.test.tsx` |
| 9 | P2 | Make multi-portfolio empty-state test deterministic | `frontend/tests/e2e/multi-portfolio.spec.ts` |
| 10 | P2 | Replace `page.waitForTimeout(2000-3000)` with deterministic waits | `frontend/tests/e2e/trading.spec.ts` |
| 11 | P3 | Remove debug `console.log` from `analytics.spec.ts` beforeEach | `frontend/tests/e2e/analytics.spec.ts` |
