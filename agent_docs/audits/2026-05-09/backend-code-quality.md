# Audit: Backend Code Quality

**Date**: 2026-05-09
**Auditor**: backend-swe (audit mode)
**Scope**: `backend/src/zebu/` (excluding tests)

## Findings

### P0 Critical

- **[P0-bcode-1] Swallowed exception masks real errors in price-fallback path**
  - Evidence: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py:217` — `except Exception:` in `get_current_price` catches *all* errors from `_fetch_from_api` and silently serves stale cached data. There's no log of what failed; only a `raise` if no cache exists. Same pattern at `:827` (history fetch) and `:361` (batch fetch).
  - Why: This is the canonical hot path the proposal builds on (Phase B's API-key auth + `ExplorationTask` queue both go through `MarketDataPort`). When agents start hammering this from looped strategies, a programming bug (e.g., `KeyError` on a parsing change) will be silently masked as "stale data served" with no telemetry trail. The single `except Exception` in `_fetch_from_api` already catches `httpx.TimeoutException`, `httpx.NetworkError`, and `httpx.HTTPError` explicitly above (lines 455–478), so this outer catch only catches the *unexpected* — exactly the things you want logged loudly. Plus `TickerNotFoundError` is being suppressed and replaced with stale data, which is wrong: the ticker genuinely doesn't exist.
  - Fix: Catch `MarketDataUnavailableError` (and only that) for the cache-fallback. Let `TickerNotFoundError`, `InvalidPriceDataError`, and unexpected exceptions propagate. At minimum, `logger.exception(...)` before the cache fallback so failures surface in production logs.

- **[P0-bcode-2] Silent `except Exception: continue` in portfolio composition skips holdings without logging**
  - Evidence: `backend/src/zebu/application/queries/get_portfolio_composition.py:130` — `except Exception: continue` (with the comment *"In production, might want to log this or use last known price"*). The handler silently drops holdings whose price fetch fails, returning a portfolio composition that omits real positions. The user sees a pie chart that doesn't sum to their total assets.
  - Why: This is exactly the kind of correctness bug that's invisible until someone notices the totals don't add up. Auth migration (Phase B) means agents will be querying composition programmatically and acting on it — a silently incorrect composition could drive bad trading decisions. The comment acknowledging the gap was never resolved.
  - Fix: Catch only `TickerNotFoundError` and `MarketDataUnavailableError`, log a `logger.warning`, and either include the holding with a `None` value or use last known price. Don't swallow `Exception`.

- **[P0-bcode-3] `Any` in domain entities for `Strategy.parameters` and `BacktestRun.strategy_snapshot` defeats type checking on the agent-platform critical path**
  - Evidence:
    - `backend/src/zebu/domain/entities/strategy.py:40` — `parameters: dict[str, Any]  # noqa: ANN401`
    - `backend/src/zebu/domain/entities/backtest_run.py:50` — `strategy_snapshot: dict[str, Any]  # noqa: ANN401`
    - Propagates through `BacktestExecutor._build_strategy` (`backtest_executor.py:328-396`), every strategy validator in `strategies.py:96-186`, and the persistence layer (`models.py:378`, `:460`).
  - Why: Strategy parameters are the primary contract between users / agents and the engine. The proposal explicitly calls out *"agent-driven trading"* — agents will programmatically construct strategy configs. Right now every parameter access has to do `isinstance` checks at runtime (see lines 342, 355, 363, 378 of `backtest_executor.py`) because the type system has no information. This is duplicated parsing logic that drifts from the API validator (`strategies.py:96+`) — the executor and the API both re-validate the same shape, and they will diverge.
  - Fix: Define a discriminated union of typed parameter dataclasses (one per `StrategyType`) — e.g., `BuyAndHoldParams`, `DCAParams`, `MovingAverageCrossoverParams` — store as JSON in the DB but parse to the typed model at the domain boundary. Strategy then carries `parameters: BuyAndHoldParams | DCAParams | MovingAverageCrossoverParams`. Eliminates `Any`, eliminates the duplicate validation, and unblocks agent-friendly schemas (Pydantic models export JSON Schema for free).

### P1 High

- **[P1-bcode-1] `BacktestExecutor._run_pipeline` is a 162-line god-method that the live executor (Task #210) needs to mirror**
  - Evidence: `backend/src/zebu/application/services/backtest_executor.py:166-326` covers six phases (setup, prefetch, simulate, persist, snapshot, metrics) inline. The CLAUDE.md explicitly says "Task #210's live executor will mirror its structure." Mirroring 162 lines of phase-mixed orchestration is the wrong substrate to copy from.
  - Why: Phase A → Phase B work (live strategy execution + agent platform) needs to share logic with the backtest path. The phases here are conceptually independent (e.g., the simulate loop has nothing to do with metrics computation), but they're glued together by shared local state (`builder`, `price_map`, `current_date`). A live executor that can't reuse `simulate` independently of `prefetch` will diverge.
  - Fix: Extract each `── Phase N ──` block into a private method (`_setup_portfolio`, `_simulate_trades`, `_persist_transactions`, `_finalize_with_metrics`). Each takes explicit inputs and returns explicit outputs; no shared mutable state. The 162-line method shrinks to a 30-line orchestrator, and Task #210 reuses `_simulate_trades` directly.

- **[P1-bcode-2] Module-level singletons (`_redis_client`, `_http_client`, `_scheduler`) are unsafe under multi-process and untestable**
  - Evidence:
    - `backend/src/zebu/adapters/inbound/api/dependencies.py:182-205` — `global _redis_client, _http_client` mutated lazily inside `get_market_data`. No locking, no shutdown.
    - `backend/src/zebu/infrastructure/scheduler.py:41,264,334` — `_scheduler: AsyncIOScheduler | None` mutated by `start_scheduler` / `stop_scheduler`.
  - Why: Phase B's API-key path means horizontally scaling FastAPI workers becomes plausible. Globals don't cross worker boundaries; each worker creates its own Redis/HTTP client without coordination. More immediately: tests have to do gymnastics (`monkeypatch` the module-level globals) to override these, and the redis client is never closed on shutdown — `lifespan()` has no `await _redis_client.aclose()`.
  - Fix: Move client lifecycle into FastAPI `lifespan()` and store on `app.state`. Inject via `Request.app.state.redis` / `app.state.http`. The scheduler is correctly tied to lifespan already; the pattern just needs to be consistent for redis + http.

- **[P1-bcode-3] Strategy parameter validation duplicated between API and executor with subtly different rules**
  - Evidence: `backend/src/zebu/adapters/inbound/api/strategies.py:96-186` (creation-time validation, returns 422) and `backend/src/zebu/application/services/backtest_executor.py:340-396` (execution-time validation, raises `InvalidStrategyError`). Both check `isinstance(allocation, dict)`, `isinstance(fast_window, int)`, etc., with *different* error messages and slightly different completeness (API checks `1 <= frequency_days <= 365`, executor doesn't; API checks `fast_window < slow_window`, executor doesn't).
  - Why: Two sources of truth for the same invariant. A user could create an invalid strategy through some bypass (CLI script, future API key path) and only see it fail at backtest time with a cryptic `InvalidStrategyError`. Phase B explicitly adds a non-Clerk auth path that may not go through the same router validation.
  - Fix: Move parameter validation into the typed parameter dataclasses (P0-bcode-3) and have both call-sites parse to those types. One set of rules, enforced at construction.

- **[P1-bcode-4] In-handler imports and mid-handler `getLogger` calls scattered across the API layer**
  - Evidence: `backend/src/zebu/adapters/inbound/api/portfolios.py:457`, `:611`, `:613` — `import logging` and `logging.getLogger(__name__)` called *inside* request handlers; `prices.py:307` — `from datetime import timedelta` mid-function; `analytics.py:370` — `from zebu.infrastructure.scheduler import ...` inside the handler.
  - Why: Mixed style obscures dependencies. The codebase otherwise consistently uses `structlog.get_logger(__name__)` at module level. The mid-function imports look like circular-import workarounds that were never cleaned up; if there's a real cycle, the audit can't tell because the workaround masks it. Rolling out structured logging consistently (Phase B telemetry) becomes harder with two logging styles coexisting.
  - Fix: Move all imports to module top. Move all logger creation to module top using `structlog.get_logger(__name__)` (the established pattern — see `prices.py:23`, `alpha_vantage_adapter.py:37`).

### P2 Medium

- **[P2-bcode-1] `# type: ignore[attr-defined]` repeated ~25× across repositories for SQLModel column ops**
  - Evidence: `backend/src/zebu/adapters/outbound/database/{transaction,backtest_run,snapshot,portfolio,strategy}_repository.py` and `repositories/{watchlist_manager,price_repository}.py` — every `.asc()`, `.desc()`, `.in_(...)`, `.is_not(None)` call has a `# type: ignore[attr-defined]` because Pyright doesn't see SQLModel field's SQLAlchemy column methods. ~25 occurrences in total.
  - Why: They're each individually justified, but the repetition is itself a smell — when the convention is "every SQLModel ordering needs a type-ignore," it desensitizes reviewers to type-ignore comments. A real one will slip through. Also, `noqa: E712` for `== True` SQLAlchemy comparisons is inflated by the same problem.
  - Fix: Either (a) use `column()` helper / `sqlalchemy.Column` directly to get typed accessors, or (b) define typed wrapper helpers (`order_by_timestamp_asc(stmt)`) so the suppressions live in one place. Even a project-level Pyright config to disable that specific check on adapter files is better than 25 inline comments.

- **[P2-bcode-2] `dict[str, Any]` return types on debug endpoints is fine, but `dict[str, Any]` inside `models.py` for JSON columns leaks into domain**
  - Evidence: `backend/src/zebu/adapters/outbound/database/models.py:378` (`StrategyModel.parameters`), `:460` (`BacktestRunModel.strategy_snapshot`). The column type is JSON, but `dict[str, Any]` propagates through `to_domain()` calls and is exactly what feeds the P0-bcode-3 chain.
  - Why: Same root issue as P0-bcode-3, surfacing at the persistence boundary. Once the domain types are tightened, the model layer can serialize via `model.parameters = params.model_dump()` and the `Any` disappears.
  - Fix: Tied to P0-bcode-3 — ship them together.

- **[P2-bcode-3] `database.py:25` engine-level `echo=True` always-on**
  - Evidence: `backend/src/zebu/infrastructure/database.py:25` — `engine_kwargs: dict[str, Any] = {"echo": True}`. SQL is logged on every query, in every environment.
  - Why: Production logs are flooded with raw SQL — privacy / log-cost concern, and `Any` is unnecessary here. A boolean from env (`os.getenv("DB_ECHO", "false") == "true"`) replaces both issues.
  - Fix: Drive `echo` from env, default `False`. Type the dict properly.

- **[P2-bcode-4] `CurrentUserDep` UUID synthesized from Clerk string is a foot-gun for the API-key auth migration**
  - Evidence: `backend/src/zebu/adapters/inbound/api/dependencies.py:151-177` — `get_current_user_id` does `uuid5(NAMESPACE_DNS, current_user.id)` to convert Clerk string IDs to UUIDs. Comment calls it "a compatibility layer ... during the migration."
  - Why: Phase B adds API-key auth. If those keys map to a different identity space, the deterministic-UUID trick breaks: two auth paths could collide on the same UUID, or the same identity could get two UUIDs. The migration was never finished; the band-aid is now load-bearing for Phase B work.
  - Fix: Either commit to UUID identities throughout (Clerk → store mapping in users table) or commit to string IDs. Don't keep deriving UUIDs from strings.

### P3 Nice-to-have

- **[P3-bcode-1] `pyright.reportUnknownMemberType/ArgumentType/VariableType = false` weakens strict mode**
  - Evidence: `backend/pyproject.toml:76-78` — three `reportUnknown*` rules disabled while `typeCheckingMode = "strict"`. This is the loophole that lets the JSON/SQLModel `Any` chain through unnoticed.
  - Why: Re-enabling them would surface dozens more issues (the SQLModel chain is the main victim). Worth tightening eventually, but doing so without first fixing P0-bcode-3 would be noisy.
  - Fix: Defer until the typed-strategy refactor. Then re-enable.

- **[P3-bcode-2] `models.py:51,131,259,368,449` — `__tablename__ = "..."  # type: ignore[assignment]` repeated for every model**
  - Evidence: 5 occurrences of the same comment pattern across `models.py`.
  - Why: Cosmetic but indicative — a per-package pyright override would silence these once.
  - Fix: Add `# pyright: reportAssignmentType=false` at the top of `models.py` (only that file).

## Summary

- **Total: 13** | **P0: 3** | **P1: 4** | **P2: 4** | **P3: 2**

**Notable strengths**:

- Domain layer is genuinely pure — no I/O, no `await`, frozen dataclasses for value objects (`money.py`, `ticker.py`).
- Domain exceptions are well-defined with rich attributes (`InsufficientFundsError` carries `available`/`required`/`shortfall`).
- Type-ignore comments are mostly *documented* with the reason, even where they're noisy — that's better than naked suppressions.
- Clean Architecture boundaries are respected — `application/ports/` are Protocols, adapters are properly outbound, no domain → infrastructure imports.
- FastAPI exception handler registration via decorators is a clean pattern, even if it requires `# pyright: ignore[reportUnusedFunction]`.

**Top concern**: The `dict[str, Any]` strategy-parameters chain (P0-bcode-3) is the structural blocker for Phase B's agent platform — it forces duplicate runtime validation across the API and executor and can't generate a JSON Schema for agents to consume.
