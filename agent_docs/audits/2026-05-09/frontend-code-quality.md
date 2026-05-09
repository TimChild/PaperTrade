# Frontend code quality audit

- **Auditor**: `frontend-swe (audit mode)`
- **Date**: 2026-05-09
- **Scope**: `frontend/src/` (excluding tests)
- **Slug prefix**: `fcode`
- **Phase**: B1 of agent-platform proposal

## Headline

The frontend is in unusually good shape against the project's hard rules. **Zero `any`, zero ESLint suppressions, zero `@ts-ignore` / `@ts-expect-error`, no setState-in-`useEffect` props-sync anti-pattern.** The `key` prop pattern is correctly applied where needed (e.g. `PortfolioDetail.tsx:256`). All bigger components use explicit `React.JSX.Element` return types.

The findings below are mostly P2 cleanups around hook ergonomics, an a11y gap on a clickable table row, dead mock code, and a small handful of consistency cleanups that will compound if Phase G frontend work lands on top of them.

## Findings

### P1 — Phase G hot spots

#### fcode-001 — Custom hooks consistently lack explicit return types

- **Evidence**: `frontend/src/hooks/usePortfolio.ts:13,24,36,48,62,82,110,181`; `frontend/src/hooks/useBacktests.ts:8,16,25,35`; `frontend/src/hooks/useStrategies.ts:8,16,25,35`; `frontend/src/hooks/useAnalytics.ts:10,22`; `frontend/src/hooks/useHoldings.ts:7`; `frontend/src/hooks/usePriceHistory.ts:48`; `frontend/src/hooks/useHistoricalPriceQuery.ts:13`; `frontend/src/hooks/usePriceQuery.ts:13,41`; `frontend/src/hooks/useHealthCheck.ts:4`. None have `:` annotation between params and `{`.
- **Why**: `frontend-swe.md` calls "explicit return types on all functions" a hard rule. With TanStack Query 5's heavy generics, an inferred `UseQueryResult` / `UseMutationResult` is brittle: changing the queryFn return shape silently changes every call site. Phase G adds `useExplorationTask`, `useAgentRun`, `useLiveStrategy` hooks — codifying the pattern now (e.g. a `usePortfolios(): UseQueryResult<PortfolioDTO[], AxiosError>` type) prevents the new hooks from shipping without it.
- **Fix**: Add explicit return types to all custom hooks. Two acceptable shapes: (a) re-export `UseQueryResult<TData, TError>` / `UseMutationResult<TData, TError, TVariables>` from TanStack Query and annotate, or (b) extract a small `QueryResult<T>` alias if the signatures cluster. Bundle in one PR — it's mechanical.

#### fcode-002 — Clickable `<tr>` row has no keyboard affordance

- **Evidence**: `frontend/src/pages/Backtests.tsx:205-210` — `<tr ... onClick={() => void navigate(...)}>` with no `role`, `tabIndex`, or `onKeyDown`.
- **Why**: Whole row is a click target visually (`cursor-pointer`) but invisible to keyboard users — unreachable via Tab, can't be activated by Enter. `frontend-swe.md` lists "keyboard-navigable" as a hard a11y rule. The pattern will likely be copied into Phase G's exploration-task list / agent-run list, so fixing it once and pinning the convention matters more than the single-row fix.
- **Fix**: Either (a) wrap the visible name cell in a real `<Link>` (cleanest — tests already navigate by clicking `data-testid="backtest-row-…"` so adapt those), or (b) add `tabIndex={0}`, `role="button"`, `onKeyDown` Enter/Space handler, `aria-label={`View backtest ${bt.backtest_name}`}`. Option (a) is preferred — `PortfolioCard.tsx:76` already uses the wrapping-`<Link>` idiom.

#### fcode-003 — Dead mock service alongside live API service

- **Evidence**: `frontend/src/services/portfolio.ts` (88 lines, mock-only `portfolioService` with `setTimeout` simulated delays). Zero importers (`grep -rn "portfolioService\|services/portfolio'"` returns nothing in `frontend/src/`).
- **Why**: Phase G work will scaffold new services under `services/api/`. A second top-level `services/portfolio.ts` that nobody uses is exactly the kind of file a new contributor (or Claude) imports into a new feature thinking it's the canonical shape — it isn't. The DTO names also disagree with the real ones (`request.portfolioId` here vs. `TradeRequest` shape in `services/api/types.ts`). Drift trap.
- **Fix**: Delete `frontend/src/services/portfolio.ts` and `frontend/src/mocks/portfolio.ts` if no longer used (verify imports first). MSW handlers in `frontend/src/mocks/handlers.ts` already cover mock data for tests.

### P2 — Cleanups

#### fcode-004 — `console.error` chatter from API client interceptor

- **Evidence**: `frontend/src/services/api/client.ts:114-140` — every 401/403/404/500/network error logs 2-3 `console.error` lines unconditionally; `frontend/src/pages/PortfolioDetail.tsx:60,76` log every trade submit.
- **Why**: Tests of error paths produce noisy output and prod browsers report `console.error` to telemetry as "errors." For Phase G, agent-driven flows will probably 404/timeout often as part of normal operation (polling exploration-task results); the current interceptor would treat each as an error.
- **Fix**: Either (a) gate logs on `import.meta.env.DEV`, or (b) introduce a `logger` utility (`utils/logger.ts`) wrapping levels so prod can be tuned. Keep the `console.error` in `ErrorBoundary.tsx:24` — that's correct.

#### fcode-005 — `useEffect` with `setState` for system theme tracking is correct, but the dependency boundary is fragile

- **Evidence**: `frontend/src/contexts/ThemeContext.tsx:33-54`. `setSystemTheme` lives in a `useState` and is updated from a `matchMedia` listener inside `useEffect` — this *is* external-system sync (legitimate `useEffect`), but the listener is only attached when `theme === 'system'`, so toggling theme to/from `system` removes / re-adds the listener. If user is on `'system'`, switches to `'dark'`, then back to `'system'` after the OS has changed, `systemTheme` is stale until the next OS-level change.
- **Why**: Edge case, not active bug. Phase G shouldn't touch this, but the pattern is the kind of thing a contributor will copy when adding (e.g.) "follow agent's currently-selected portfolio" cross-tab sync, getting it wrong.
- **Fix**: Always attach the listener; gate the `effectiveTheme` derivation on `theme === 'system' ? systemTheme : theme` (already done at line 38). Then `theme` doesn't need to be in the effect deps. Or: re-read `getSystemTheme()` on the listener-attach path, not just on mount.

#### fcode-006 — `_axiosError` cast to `as AxiosError` and `error as AxiosError<ErrorResponse>` repeated across hooks/utils

- **Evidence**: `frontend/src/hooks/usePriceQuery.ts:21,51`; `frontend/src/hooks/useHistoricalPriceQuery.ts:21`; `frontend/src/utils/errorFormatters.ts:24,29`. Type narrowing via `as` rather than `axios.isAxiosError`.
- **Why**: All four are unsafe-by-construction (`as` is the polite cousin of `any`). `axios.isAxiosError(error)` is a real type guard and will keep `errorFormatters.ts` honest as the error shape evolves. Project pride is "no type-checker suppressions"; these `as` casts are functionally the same suppression on `unknown`.
- **Fix**: Replace `const x = error as AxiosError` with `if (!axios.isAxiosError(error)) return ...; const x = error;`.

#### fcode-007 — `'usingRealTimePrice' in holding` runtime check after `useMemo` already typed it

- **Evidence**: `frontend/src/components/features/portfolio/HoldingsTable.tsx:152-155`. The `useMemo` at line 36 returns a typed object that *always* has `usingRealTimePrice: boolean`. The narrow `'usingRealTimePrice' in holding && holding.usingRealTimePrice` is dead defense — TS knows the key exists.
- **Why**: Minor. Suggests defensive-after-the-fact thinking that hides real type info from readers. Phase G should not be a place where new components add similar dead narrowings.
- **Fix**: Replace with `const usingFallback = !holding.usingRealTimePrice`.

### P3 — Defer

#### fcode-008 — `services/api/types.ts` uses `Record<string, unknown>` for strategy parameters

- **Evidence**: `frontend/src/services/api/types.ts:122,130` — `parameters: Record<string, unknown>` in `StrategyResponse` / `CreateStrategyRequest`; mirrored in `CreateStrategyForm.tsx:109`.
- **Why**: Strategy parameters are strongly typed on the backend (per-strategy schema) but are an opaque map on the wire. The form already discriminates manually on `strategyType` to build the right shape — a discriminated union (`type StrategyParameters = BuyAndHoldParams | DCAParams | MAParams`) would let the compiler enforce that `MOVING_AVERAGE_CROSSOVER` always carries `fast_window`.
- **Fix**: Phase G is adding new strategy types and a programmatic `ExplorationTask` parameter shape — re-do this once instead of twice. Defer to that task.

#### fcode-009 — Two `Card`-like components live in `components/ui/` (`card.tsx` lowercase shadcn-style and `Card.tsx` casing inconsistency)

- **Evidence**: shadcn-style lowercase filenames (`button.tsx`, `card.tsx`, `input.tsx`, `label.tsx`, `badge.tsx`, `separator.tsx`) coexist with `Dialog.tsx`, `ConfirmDialog.tsx`, `EmptyState.tsx`, `ErrorDisplay.tsx`, `ErrorState.tsx`, `LoadingSpinner.tsx`. Mixed casing convention.
- **Why**: Cosmetic. Won't cause bugs.
- **Fix**: Pick one casing and rename. Or document the split (e.g. "shadcn primitives lowercase, our own components PascalCase") in `frontend-swe.md`. Not worth doing on its own.

## Quick stats

- Total `tsx` files in `src` (excl. tests/prototypes): ~50
- `any` occurrences: 0
- `eslint-disable` occurrences: 0
- `@ts-ignore` / `@ts-expect-error` occurrences: 0
- `as`-casts on non-builtin types (excl. `as const`, `import * as React`): 8
- Custom hooks without explicit return types: 24 / 24
- Inline `() => fn(arg)` event handlers: ~30 (all in the canonical "small closure capturing local state" form — not a finding on its own)
- `useEffect` occurrences: 11 — all legitimate (DOM/external sync); none are props-to-state syncs

## Why no P0

The criteria for P0 (`any` in shared types / API client / state; setState-in-useEffect on critical paths; broken accessibility) all came up empty — every thing I'd normally flag P0 in a React codebase isn't here. The team has been disciplined about the `frontend-swe.md` rules. The closest thing to a P0 was fcode-002 (keyboard a11y on backtest row), but it's a single component on a non-critical path and the pattern's correctly handled in `PortfolioCard.tsx`, so P1 is the right call.
