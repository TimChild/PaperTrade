# API Design Audit — Phase B1

**Date**: 2026-05-09
**Auditor**: backend-swe + architect
**Slug**: `api`
**Scope**: `backend/src/zebu/adapters/inbound/api/` — all routers and their schemas

## Summary

The API surface is **largely consistent** for the portfolios/transactions/strategies/backtests resources — REST verbs and status codes are correct (`201` on create, `204` on delete, `404`/`403`/`422` used appropriately), Pydantic request/response models are explicit, every owner-scoped endpoint validates ownership, and routes sit behind `/api/v1/`. The error shape from the global handlers (`{detail: str | dict}`) is good.

However, **whole categories of endpoints are unauthenticated** (the entire `prices` router, the entire `debug` router, and the `analytics` admin router), which is a P0. There are also several inconsistency issues that Phase D MCP tooling and Phase C ExplorationTask endpoints will need to match if not fixed first: the error envelope mixing `str` and `dict` `detail` shapes, list endpoints without pagination (`strategies`, `backtests`, `balances`), and admin endpoints returning loose `dict[str, ...]` instead of typed responses.

## Findings

### P0-API-1: Entire `prices` router is unauthenticated

**File**: `/Users/timchild/github/PaperTrade/backend/src/zebu/adapters/inbound/api/prices.py`

Every route on the `/prices` router (`GET /prices/batch`, `GET /prices/{ticker}`, `GET /prices/{ticker}/history`, `GET /prices/`, `GET /prices/{ticker}/check`, `POST /prices/fetch-historical`, `GET /prices/debug/cache/{ticker}`) lacks `CurrentUserDep`. Any unauthenticated client can hit them — including `POST /prices/fetch-historical`, which triggers paid Alpha Vantage calls and writes to the DB. The `inspect_price_cache` debug route also exposes internal cache state.

This is the sole router in the whole codebase without auth on the data endpoints (`portfolios`, `transactions`, `strategies`, `backtests`, `analytics` non-admin all use `CurrentUserDep`). Phase D MCP will be calling these via API key auth — once that lands, this gap becomes externally exploitable.

**Fix**: Add `CurrentUserDep` to all `/prices` routes. Move `/prices/debug/cache/{ticker}` and `/prices/fetch-historical` behind admin guard (or delete fetch-historical — see P3 dead-code finding).

---

### P0-API-2: `analytics` admin router is unauthenticated and unrestricted

**File**: `/Users/timchild/github/PaperTrade/backend/src/zebu/adapters/inbound/api/analytics.py:347–423`

`admin_router` mounts `POST /analytics/prices/refresh` and `POST /analytics/snapshots/daily` with **no auth dep at all**. Each handler has a `# TODO: Add admin authentication check when auth is implemented` comment but no implementation.

`POST /analytics/prices/refresh` triggers a full Alpha Vantage refresh on demand (cost + rate-limit consumption), and `POST /analytics/snapshots/daily` runs against every portfolio in the system. These are reachable by any unauthenticated caller in production right now.

**Fix**: Wrap both endpoints with `CurrentUserDep` plus an admin-claim check (or — minimally — `CurrentUserDep` so unauthenticated calls fail), and replace the TODOs with the actual gate. Phase B1 should land this with the API-key auth work since the same admin role check will apply.

---

### P0-API-3: `debug` router is unauthenticated and exposes infrastructure metadata

**File**: `/Users/timchild/github/PaperTrade/backend/src/zebu/adapters/inbound/api/debug.py:190, 249, 308`

`GET /debug` returns DB URL (with redacted password but full host/user/db), Redis URL, presence and prefixes of API keys, scheduler job listing, and price-cache contents. No auth. This is reachable in production at `https://zebutrader.com/api/v1/debug`.

The redactions help, but the exposure of host names, key prefixes, and pool/scheduler internals is still a recon vector. The `/debug/price-cache/{ticker}` endpoint also runs an unbounded query that could be abused for amplification.

**Fix**: Either gate the entire `debug` router behind admin auth, or drop it from the production OpenAPI schema (`include_in_schema=False`) and constrain it to `APP_ENV=development`.

---

### P1-API-4: Inconsistent error envelope (`detail` is sometimes `str`, sometimes `dict`)

**Files**: `error_handlers.py`, `portfolios.py:312, 320, 363, 368, 480, 488, 622, 628`, `transactions.py:94, 106`, `backtests.py:198, 232, 238, 261, 267`, `strategies.py:88, 99, 117, 130, 134, 141, 154, 161, 169, 181, 192, 209, 242, 246, 271, 276`

`ErrorResponse` is declared as `detail: str | dict[str, str | float]`. In practice:

- Domain-exception handlers (`error_handlers.py`) return rich dicts: `{"type": "insufficient_funds", "message": ..., "available": ..., "shortfall": ...}`.
- `HTTPException`s raised from routes mostly return strings: `f"Portfolio not found: {portfolio_id}"`.
- `portfolios.py` route handlers re-raise `TickerNotFoundError`/`MarketDataUnavailableError` with **dict** detail, while the global handler for the same exceptions also returns dict detail — but only one path runs.

A frontend (or Phase D MCP client) cannot reliably parse `error.detail.type` because `detail` may be either shape. This forces every consumer to write `typeof detail === 'string' ? detail : detail.message` everywhere.

**Fix**: Standardize on the structured shape: `{type: str, message: str, ...extras}`. Convert all `HTTPException(detail=f"...")` calls to `HTTPException(detail={"type": "<machine-code>", "message": "<human>"})`. Either keep the `ErrorResponse` Pydantic model (so OpenAPI documents it) or extend FastAPI's default `{"detail": ...}` consistently.

---

### P1-API-5: List endpoints without pagination

**Files**:
- `strategies.py:219` — `GET /strategies` returns all of a user's strategies.
- `backtests.py:210` — `GET /backtests` returns all of a user's backtest runs.
- `portfolios.py:262` — `GET /portfolios/balances` returns balances for **all** of a user's portfolios.
- `portfolios.py:551` — `GET /portfolios/{id}/holdings` returns all positions for one portfolio (acceptable, bounded by the portfolio).

`GET /portfolios` and `GET /portfolios/{id}/transactions` correctly paginate via `limit`/`offset`. The other list endpoints will grow unbounded — backtest runs in particular will accumulate quickly once Phase C/D agents start scheduling them.

Note that `portfolios.py:248` paginates *after* fetching with `await portfolio_repo.get_by_user(...)` — the repo loads everything and the route slices in Python. The pagination shape is right, but the repo call needs to push `limit`/`offset` to SQL too (cross-cutting; flag for the perf audit).

**Fix**: Add `limit: int = Query(50, ge=1, le=200)` + `offset: int = Query(0, ge=0)` to `list_strategies`, `list_backtests`, and ideally `get_all_balances` (or replace it with explicit `?portfolio_ids=` filtering). Make the pagination response shape consistent — `transactions` returns `{transactions, total_count, limit, offset}` while `portfolios` returns a bare list.

---

### P1-API-6: Inconsistent list response envelope (bare list vs paginated object)

**Files**: `portfolios.py:225` (bare `list[PortfolioResponse]`), `strategies.py:219` (bare list), `backtests.py:210` (bare list) versus `transactions.py:60` (paginated `TransactionListResponse`).

Bare list responses cannot embed pagination metadata or future fields like `has_more` / `next_cursor` without breaking change. Phase D MCP will want a uniform pattern so the LLM can reliably read counts.

**Fix**: Choose one envelope (`{items: [...], total_count: int, limit: int, offset: int}` or cursor-based) and apply to **all** list endpoints. Pick before Phase D MCP starts wrapping these.

---

### P1-API-7: Filtering query-param patterns are inconsistent

**Files**:
- `portfolios.py:233` — `include_backtest: bool` (boolean toggle).
- `transactions.py:68` — `transaction_type: str | None` (raw enum string, no validation).
- `prices.py:256` — `interval: str = "1day"` (raw string, no validation against allowed set).
- `analytics.py:190` — `range: TimeRange` (proper Pydantic enum). Good pattern.

`transaction_type` accepts arbitrary strings and would `KeyError` on `TransactionType[...]` if invalid. `interval` accepts anything; the adapter presumably rejects unknown values but the API surface doesn't validate.

**Fix**: Adopt the `analytics.py` pattern — declare these as `Enum` query params so FastAPI auto-validates and the OpenAPI schema enumerates the allowed values.

---

### P1-API-8: Loose `dict[str, ...]` response models on admin and debug endpoints

**Files**:
- `analytics.py:287` — `dict[str, str | dict[str, int]]`
- `analytics.py:351, 392` — `dict[str, str]`, `dict[str, str | dict[str, int]]`
- `debug.py:191, 250, 309` — `dict[str, Any]`
- `prices.py:539` — `dict[str, object]`

These violate the project's "no `Any`, explicit Pydantic schemas" standard (see `CLAUDE.md`). They produce no OpenAPI body schema, so consumers can't generate types. The frontend `Debug.tsx` already uses one of them — frontend types those as `any` by necessity.

**Fix**: Define explicit Pydantic response models for each (e.g. `BackfillJobResult`, `SchedulerStatusResponse`, `DebugInfoResponse`). At minimum, add `response_model=` declarations.

---

### P2-API-9: OpenAPI metadata gaps — only `prices.py` has `summary`/`description` on routes

**Files**: All routers except `prices.py`.

`prices.py` consistently passes `summary=`, `description=` to its decorators. Every other router relies on the docstring (which FastAPI does pick up, but inconsistently — only the first line becomes the summary). Tags are correctly grouped (`portfolios`, `transactions`, `strategies`, `backtests`, `analytics`, `analytics-admin`, `prices`, `debug`).

The `analytics` router uses `tags=["analytics"]` but its prefix is `/portfolios` (overlap with the `portfolios` router) — that's fine for OpenAPI but worth flagging: `/portfolios/{id}/performance` lives in the analytics file. Consider unifying or making the seam explicit in docs.

**Fix**: Add `summary` and `description` keyword args on all `@router.*` decorators. Useful for the soon-to-arrive MCP server, which often surfaces tool descriptions from the `summary`.

---

### P2-API-10: `transactions.py` mixes `str` and `UUID` types in response

**File**: `transactions.py:34–46`

`TransactionResponse` declares `id: str`, `portfolio_id: str` (and the route casts via `str(tx.id)`), but elsewhere in the codebase (`portfolios.py`, `strategies.py`, `backtests.py`) UUIDs are typed as `UUID` and Pydantic serializes them. This breaks consistency for clients — sometimes they get `"550e8400-..."` from one endpoint and the same shape from another but the OpenAPI schema differs (`type: string` vs `type: string, format: uuid`).

**Fix**: Use `UUID` typing in `TransactionResponse` to match the rest of the codebase; FastAPI already serializes to canonical string.

---

### P2-API-11: Money/quantity values returned as pre-formatted strings

**Files**: `portfolios.py` (e.g. `BalanceResponse`, `HoldingResponse`), `transactions.py`, `backtests.py`.

Cash, quantities, prices, and gain/loss values are `f"{value:.2f}"`-formatted strings on the wire. `analytics.py` chose the better pattern: `JsonFloat = Annotated[Decimal, PlainSerializer(float)]` — Decimal in, JSON number out. The string-formatting pattern forces clients to parse; loses precision metadata; means localization/formatting decisions live on the server.

**Fix**: Adopt the `JsonFloat`/Decimal pattern across responses. Or, at minimum, have one consistent rule. (If kept as strings, decide on `2` vs `4` decimal places consistently — currently `cash_balance` uses 2 and `quantity` uses 4 silently.)

---

### P2-API-12: Inline strategy-parameter validation belongs in the domain

**File**: `strategies.py:85–195`

`create_strategy` runs ~110 lines of strategy-type-specific parameter validation inline, raising `HTTPException(422)`. This logic is business rules for `BUY_AND_HOLD`/`DOLLAR_COST_AVERAGING`/`MOVING_AVERAGE_CROSSOVER` — it should live in the domain (e.g. `Strategy` constructor or a `StrategyParameters` value object) and the route should catch a single domain exception. The current shape will diverge from any executor-side validation.

**Fix**: Move parameter validation into the `Strategy` entity / per-type value objects. Have `Strategy(...)` raise `InvalidStrategyError` with structured details. Route just catches and maps to 422.

---

### P3-API-13: Dead-code / unused endpoints

**Files**:
- `prices.py:468` — `POST /prices/fetch-historical` not referenced from frontend.
- `prices.py:533` — `GET /prices/debug/cache/{ticker}` not referenced from frontend.
- `analytics.py:280` — `POST /portfolios/{id}/snapshots/backfill` not referenced from frontend.
- `analytics.py:350` — `POST /analytics/prices/refresh` not referenced from frontend.
- `analytics.py:391` — `POST /analytics/snapshots/daily` not referenced from frontend.
- `debug.py:249` — `GET /debug/scheduler` not referenced from frontend.
- `debug.py:308` — `GET /debug/price-cache/{ticker}` not referenced from frontend.

`grep` of the frontend turns up no usage. Some may be admin/operator tools (kept), but they currently have no auth, no admin UI, and no documented invocation path — so they're either delete candidates or "needs-an-admin-tool" candidates.

**Fix**: For each, either (a) move behind admin auth and document the admin invocation, or (b) delete. Defer the call until P0-API-2/3 is decided — the right answer might be "fold into a single admin router with admin guard."

---

### P3-API-14: Unbounded date adjustment in `get_price_history`

**File**: `prices.py:303–309`

When `end` is exactly midnight the route silently adjusts to `end + 1 day - 1 microsecond`. This is a quiet behavior the OpenAPI schema doesn't document. A Phase D MCP tool spec calling this for a precise time window will get more data than asked.

**Fix**: Document the behavior in the route's `description`, or add an explicit `inclusive_end: bool = True` query param.

---

## Endpoint inventory (for reference)

| Method | Path | Auth | Pagination | response_model |
|---|---|---|---|---|
| POST | `/api/v1/portfolios` | Yes | n/a | Yes (201) |
| GET | `/api/v1/portfolios` | Yes | limit/offset | Yes |
| GET | `/api/v1/portfolios/balances` | Yes | **No** | Yes |
| GET | `/api/v1/portfolios/{id}` | Yes | n/a | Yes |
| DELETE | `/api/v1/portfolios/{id}` | Yes | n/a | n/a (204) |
| POST | `/api/v1/portfolios/{id}/deposit` | Yes | n/a | Yes (201) |
| POST | `/api/v1/portfolios/{id}/withdraw` | Yes | n/a | Yes (201) |
| POST | `/api/v1/portfolios/{id}/trades` | Yes | n/a | Yes (201) |
| GET | `/api/v1/portfolios/{id}/balance` | Yes | n/a | Yes |
| GET | `/api/v1/portfolios/{id}/holdings` | Yes | n/a | Yes |
| GET | `/api/v1/portfolios/{id}/transactions` | Yes | limit/offset | Yes |
| GET | `/api/v1/portfolios/{id}/performance` | Yes | n/a | Yes |
| GET | `/api/v1/portfolios/{id}/composition` | Yes | n/a | Yes |
| POST | `/api/v1/portfolios/{id}/snapshots/backfill` | Yes (no admin) | n/a | **Loose dict** |
| POST | `/api/v1/strategies` | Yes | n/a | Yes (201) |
| GET | `/api/v1/strategies` | Yes | **No** | Yes |
| GET | `/api/v1/strategies/{id}` | Yes | n/a | Yes |
| DELETE | `/api/v1/strategies/{id}` | Yes | n/a | n/a (204) |
| POST | `/api/v1/backtests` | Yes | n/a | Yes (201) |
| GET | `/api/v1/backtests` | Yes | **No** | Yes |
| GET | `/api/v1/backtests/{id}` | Yes | n/a | Yes |
| DELETE | `/api/v1/backtests/{id}` | Yes | n/a | n/a (204) |
| GET | `/api/v1/prices/batch` | **No** | n/a | Yes |
| GET | `/api/v1/prices/{ticker}` | **No** | n/a | Yes |
| GET | `/api/v1/prices/{ticker}/history` | **No** | n/a | Yes |
| GET | `/api/v1/prices/` | **No** | n/a | Yes |
| GET | `/api/v1/prices/{ticker}/check` | **No** | n/a | Yes |
| POST | `/api/v1/prices/fetch-historical` | **No** | n/a | Yes |
| GET | `/api/v1/prices/debug/cache/{ticker}` | **No** | n/a | **Loose dict** |
| POST | `/api/v1/analytics/prices/refresh` | **No** | n/a | **Loose dict** |
| POST | `/api/v1/analytics/snapshots/daily` | **No** | n/a | **Loose dict** |
| GET | `/api/v1/debug` | **No** | n/a | **Loose dict** |
| GET | `/api/v1/debug/scheduler` | **No** | n/a | **Loose dict** |
| GET | `/api/v1/debug/price-cache/{ticker}` | **No** | n/a | **Loose dict** |
| GET | `/health` | n/a | n/a | inline dict |
| GET | `/` | n/a | n/a | inline dict |
| GET | `/api/v1/` | n/a | n/a | inline dict |

## Priority counts

- **P0**: 3 (unauthenticated `prices`, `analytics-admin`, `debug` routers)
- **P1**: 5 (error envelope, missing pagination, list response shape, filter-param consistency, loose dict responses)
- **P2**: 4 (OpenAPI metadata, UUID typing, money formatting, domain validation)
- **P3**: 2 (dead code, end-date inclusivity)

**Total**: 14 findings.

## Recommendations for Phase B/C/D

- Fix all P0s before Phase B1 lands API-key auth (otherwise the MCP layer inherits an open back door).
- Pick the standard error shape and list-envelope shape **before** Phase C ExplorationTask endpoints are designed — those will land 4–6 new endpoints that should match.
- Address P1-API-7 (enum query params) and P2-API-9 (summary/description on routes) before Phase D MCP tool generation — the MCP server reads these.
