# Task 214 — Partial-pricing safe response for portfolio queries

**Status**: Scoped, not started
**Branch**: `fix/j-partial-pricing-503`
**Agent**: `backend-swe` + small `frontend-swe` touch (single PR)

## Origin

Surfaced 2026-05-13 immediately after Phase J L4 deployed. User opened `/dashboard` and observed portfolio totals jumping wildly across renders ($656.50 → $7,756.36 → $11,789.95 → $13,922.55 for the same portfolio across successive polls). Holdings table showed `Cash $656.50 / Holdings $1,733.80` despite four positions worth ~$9k. Day change displayed nonsense values like `-100%` and `-90.02%`.

Root cause: `backend/src/zebu/application/queries/get_portfolio_balances.py:117-135` catches `TickerNotFoundError` / `MarketDataUnavailableError` per-ticker, logs the warning, and silently drops the ticker from `current_prices_dict`. Then `PortfolioCalculator.calculate_portfolio_value` (`backend/src/zebu/domain/services/portfolio_calculator.py:142-168`) iterates holdings and skips any ticker whose price isn't in the dict. Net effect: `holdings_value`, `total_value`, and `daily_change` are silently computed against a partial set of positions. As the L3 lazy backfill + L2 prewarm complete in the background, successive polls return increasing partial totals.

This is a real bug independent of the data-warmth work — it's been latent since Phase 4. Phase J just made it visible by repeatedly hitting partial-fetch states.

## Decision (Tim 2026-05-13)

> "I'd prefer not to see any number than a wrong number, but we should still give the user some nice feedback that data is loading."

Adopt **Option (b) from the triage** — refuse to return a balance when any required price is missing; surface a structured "data is loading" response. Symmetric with L3's `IncompleteHistoricalDataError → 503 + Retry-After` pattern.

## Architecture

### New application exception

`PartialPricingError` in `backend/src/zebu/application/exceptions.py` alongside the existing `IncompleteHistoricalDataError`:

- `missing_tickers: list[Ticker]` — tickers whose current price could not be resolved
- `failed_reason: dict[Ticker, str]` — short reason per ticker (e.g. `"ticker_not_found"`, `"market_data_unavailable"`)
- `retry_after_seconds: int` — recommended client retry delay (default 5)

### Query handler change

`GetPortfolioBalancesQueryHandler` (`backend/src/zebu/application/queries/get_portfolio_balances.py`) — replace the silent-drop behavior:

1. After parallel `fetch_current_price_safe` calls, check whether `current_prices_dict` covers all `all_tickers`. If yes, current behavior unchanged.
2. If any tickers are missing AND the portfolio has a non-zero holding in that ticker, raise `PartialPricingError` with the missing list.
3. **Per-portfolio**: a missing ticker only blocks portfolios that actually hold it. A portfolio with only TSLA can still return a balance when MU/AAPL/MSFT failed for *other* portfolios. The handler should compute per-portfolio first, then decide which to fail.

Same treatment for `previous_prices_dict` — if a portfolio's daily change can't be computed against a complete previous-prices set, fail the response for that portfolio.

**Behavior**: the response is now `list[GetPortfolioBalanceResult | PartialPricingError]` conceptually. Cleanest wire shape: each result envelope carries `status: "ok" | "loading"` and the result OR the error metadata.

### API layer

`backend/src/zebu/adapters/inbound/api/portfolios.py` — three places this surfaces:

1. **`GET /api/v1/portfolios`** (list with embedded balances) — when ALL portfolios have partial pricing, return 503 + `Retry-After: 5` with `{ status: "fetching", missing_tickers: [...], retry_after_seconds: 5 }`. When SOME portfolios are OK and others aren't, return 200 with each portfolio carrying its own `pricing_status: "ok" | "loading"` + missing-tickers list.
2. **`GET /api/v1/portfolios/{id}`** (single detail) — analogous: if this portfolio's prices are partial, return 503 + Retry-After. If complete, return 200 normally.
3. **`GET /api/v1/portfolios/{id}/balance`** — same as (2).

The mixed-success case on the list endpoint is the only nuanced one. Default position: prefer returning a usable list with per-portfolio status over forcing the whole call into 503. The FE can render some cards fully and some in a "loading" state.

### Frontend

`frontend/src/hooks/usePortfolios.ts` + `usePortfolio.ts` (or the equivalent — confirm by reading):

- Recognize the 503-fetching response shape on the single-portfolio endpoints. Auto-retry with `retry_after_seconds` cadence, max 5 attempts (~25s total). Stop retrying after that; surface a hard "data unavailable" state with a link to `/admin/data-coverage` if user is admin, or "contact admin" copy otherwise.
- Recognize per-portfolio `pricing_status: "loading"` on the list endpoint. Render the card with: portfolio name + cash (which is unaffected) + a "Loading market data…" skeleton over the total-value and day-change rows. **Do NOT show stale or computed numbers in this state.**

Components to update:

- `frontend/src/components/features/portfolio/PortfolioCard.tsx` — render the loading skeleton when `pricing_status === "loading"`. The total-value and day-change rows become a shimmer; the portfolio name + cash row stay normal.
- `frontend/src/components/features/portfolio/PortfolioSummaryCard.tsx` — same treatment on the detail page hero. Total value → "Loading…" or a skeleton. Cash + holdings count still renders.
- `frontend/src/pages/PortfolioDetail.tsx` (or wherever the detail page orchestrates) — if 503 after retry budget exhausted, show a hard error block: "Market data temporarily unavailable for AAPL, MU, MSFT" + admin link / contact-admin copy.
- `HoldingsTable.tsx` — keep its existing `★` fallback row-by-row UI; the change here is the page-level total, not per-row.

### Timeout / bail-out copy

Per spec discussion: "data will load fairly quickly" is mostly true (cached: <1s; AV API: 1-3s) but the free-tier 25/day cap can stall things for hours. The UX must distinguish:

- **Short loading (<10s)**: skeleton, no message
- **Extended loading (10–30s)**: skeleton + small caption "Fetching market data…"
- **Stuck (>30s)**: error block, "Market data temporarily unavailable" + the specific missing tickers + a hint to use `/admin/data-coverage` (or contact admin)

## Implementation plan

Single PR. Order within branch:

1. **Domain exception** `PartialPricingError` + unit test.
2. **Query handler** — per-portfolio gating; raise/skip semantics; unit + integration tests covering all-fail, partial-fail, all-ok matrices.
3. **API layer** — 503 envelope + `Retry-After`; mixed-success per-portfolio status field on the list endpoint.
4. **Frontend hooks** — auto-retry on 503-fetching; expose `pricingStatus: "ok" | "loading" | "unavailable"` to consumers.
5. **Frontend components** — skeleton + bail-out copy in the four touch points.
6. **E2E happy path**: mock the in-memory adapter to return partial prices for a portfolio, hit the page, assert skeleton shows, advance the mock to return full prices, assert real values render.

## Quality requirements (non-negotiable)

- No `Any` / `any`; no Pyright / eslint suppressions
- Behavior-focused tests at port boundaries only
- Conventional commits
- `task quality:backend` + `task quality:frontend` + `task ci` green
- E2E for the loading + recovery flow

## Out of scope / future

- **Backfilling avg_cost / last_known_price as a graceful fallback** — explicitly rejected per Tim 2026-05-13. We prefer "no number" over "wrong number."
- **The day-change calculation for portfolios where previous-day prices are all present but current-day prices are partial** — covered by the same gating; no separate handling needed.
- **Activity feed / trade history rendering** — those queries don't recompute portfolio totals at request time; not affected by this bug.

## Success criteria

- After this PR lands, the original screenshots' failure mode (jumping totals, wrong holdings sum, -100% day change) is impossible.
- Cold-start visit to the dashboard shows a clean "Loading market data…" state for ~1-3 seconds, then resolves to correct totals.
- If the AV cap is exhausted (worst case), the user sees a clear "unavailable — backfill required" affordance with admin link, instead of misleading numbers.
- `task ci` green.

## References

- `docs/planning/agent-platform-next-steps.md` — Phase J context
- `backend/src/zebu/application/queries/get_portfolio_balances.py:117-135` — the silent-drop site
- `backend/src/zebu/domain/services/portfolio_calculator.py:142-168` — the silent-skip site
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py:654` — L3's `IncompleteHistoricalDataError → 503` is the canonical pattern this task mirrors
- `agent_docs/tasks/212_data_warmth_subsystem.md` — Layer 3's structured-error pattern (this task generalises it to current-price fetches)
