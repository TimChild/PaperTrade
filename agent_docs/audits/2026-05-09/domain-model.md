# Audit: Domain model

- **Dimension**: Domain model quality
- **Auditor**: architect + refactorer
- **Slug**: domain
- **Date**: 2026-05-09
- **Scope**: `backend/src/zebu/domain/` — entities, value_objects, services, exceptions
- **Phase context**: Phase B1 of `docs/planning/agent-platform-proposal.md`. Findings are calibrated for Phase F (`StrategyConditionTrigger`) and Phase C (`ExplorationTask`) work landing on top of this layer.

## Summary

The domain layer has a strong skeleton: real entity/value-object split, frozen dataclasses, ID-based equality on aggregates, dedicated exception hierarchy, pure domain services. Calibration concerns are concentrated around (a) **`TradeSignal` as the primitive-obsession island** that every strategy and every Phase F/C feature will route through, (b) inconsistent layering between the rich `Holding` / `Transaction` core and the noticeably thinner `BacktestRun` / `PortfolioSnapshot` / `Strategy` periphery, and (c) value-object discipline that fades at the edges (raw `str` ticker, raw `Decimal` cash, raw `dict[str, Any]` strategy parameters).

**Top concern**: `TradeSignal` uses raw `str` ticker, raw `Decimal` for both `quantity` and `amount`, and a "exactly one of two optionals" invariant — and *every* strategy plus the Phase F `StrategyConditionTrigger` proposal will produce `TradeSignal`s. Fixing the value-object surface here before Phase F lands is the highest-leverage refactor in this dimension.

## P-counts

| Priority | Count |
|---|---|
| P0 | 0 |
| P1 | 5 |
| P2 | 5 |
| P3 | 2 |
| **Total** | **12** |

## Findings

### P1 — Phase-blocking primitive obsession

#### D-P1-1. `TradeSignal` uses raw `str` ticker and raw `Decimal` quantity/amount — and is the central abstraction for every strategy

**File**: `backend/src/zebu/domain/value_objects/trade_signal.py`

```python
ticker: str
quantity: Decimal | None = None
amount: Decimal | None = None
```

`Ticker`, `Quantity`, and `Money` value objects already exist with full validation. `TradeSignal` deliberately avoids them:

- `ticker: str` — no format check, no canonicalisation (case-sensitive `dict` lookups against ticker-keyed `price_map` are silently sensitive to mismatch).
- `quantity: Decimal | None` and `amount: Decimal | None` — no upper bound, no decimal-place validation, no currency on `amount`.
- The "exactly one of `quantity` / `amount` is set" invariant is enforced via two-optional fields rather than a tagged union (e.g., `SharesSignal | DollarSignal`), so every consumer has to defensively re-check.
- Validation raises bare `ValueError` (see D-P1-5).

**Why P1 (Phase F/C blocker)**: The agent-platform proposal §3.4 / §F3 introduces `StrategyConditionTrigger`, which fires an agent that ultimately produces `TradeSignal`s. Phase E1 parameter sweeps and Phase F2's first scheduled agent (`zebu-strategy-explorer`) will both emit `TradeSignal` programmatically. This is the highest-traffic value object on the agent path — fix the primitives before that path is paved.

**Suggested fix**: `ticker: Ticker`, replace the optional pair with `class SharesSignal(TradeSignal)` / `class DollarSignal(TradeSignal)` (or a `signal_qty: SignalQuantity = SharesQty(...) | DollarAmount(Money(...))` discriminated union). Currency stops being implicit on `amount`.

---

#### D-P1-2. Strategy `parameters: dict[str, Any]` and `BacktestRun.strategy_snapshot: dict[str, Any]` are the primary Phase E parameter-sweep surface

**Files**: `backend/src/zebu/domain/entities/strategy.py:40`, `backend/src/zebu/domain/entities/backtest_run.py:50`

```python
parameters: dict[str, Any]  # noqa: ANN401
strategy_snapshot: dict[str, Any]  # noqa: ANN401
```

The `noqa: ANN401` is honest about the smell. Each `StrategyType` already has implicit shape (BuyAndHold needs `allocation`; DCA needs `frequency_days`, `amount_per_period`, `allocation`; MAC needs `fast_window`, `slow_window`, `invest_fraction`) — but those constraints live in the *strategy implementation `__init__`* in `domain/services/strategies/`, *not* in the domain model. So `Strategy` can be constructed in the domain with `{}` parameters and only fail later when an executor tries to instantiate the strategy class.

Phase E1 ("parameter sweeps") is exactly the workflow that will programmatically generate variants of these dicts, and Phase E3 ("new strategy type via PR") will multiply the shapes. A typed `StrategyParameters` discriminated union (`BuyAndHoldParameters | DCAParameters | MACParameters`) attached to `StrategyType` would catch shape errors at strategy-creation time, document the parameter space for agents, and make it easier to teach `StrategyConditionTrigger` what's tweakable.

**Why P1 (Phase E/F blocker)**: this is the second most-touched surface on the agent path after `TradeSignal`. Fixing it at the domain model means the application/adapter layers can drop ad-hoc validation.

**Suggested fix**: introduce `StrategyParameters` (frozen dataclass per `StrategyType`), validate at `Strategy.__post_init__`, drop `dict[str, Any]`. Keep DB serialisation in the adapter layer where it belongs.

---

#### D-P1-3. Strategy and DCA strategy take raw `list[str]` / `dict[str, float]` allocation — primitive obsession in the strategy core

**Files**: `backend/src/zebu/domain/entities/strategy.py:39`, `backend/src/zebu/domain/services/strategies/{buy_and_hold,dollar_cost_averaging}.py`

`Strategy.tickers: list[str]` — not `list[Ticker]`, no per-ticker normalisation.
`allocation: dict[str, float]` — `float` for fractions of money is a long-running source of round-off bugs. The docstrings say "should sum to ~1.0" (∼ is doing a lot of work) and there is no enforcement that the keys are subsets of `tickers`, or that fractions are in `[0, 1]`, or that they sum to 1.0.

`MovingAverageCrossoverStrategy` similarly takes `invest_fraction: float`. `BuyAndHoldStrategy._allocation: dict[str, float]`. `DollarCostAveragingStrategy._amount_per_period: Decimal` is fine, but `_allocation: dict[str, float]` is not.

**Why P1**: Phase E will programmatically vary these — every parameter sweep is going to mint new allocations, and `float` arithmetic in money allocation is a known footgun. An `Allocation` value object (`dict[Ticker, Decimal]` with a `__post_init__` that asserts `sum == Decimal("1")` and each fraction in `[0, 1]`) would convert a class of runtime bugs into a class of construction-time errors.

**Suggested fix**: `class Allocation(frozen=True)` with `weights: Mapping[Ticker, Decimal]`; validate sums and ranges; use everywhere strategies talk about allocation. While here, change `tickers: list[str]` → `tickers: tuple[Ticker, ...]` on `Strategy`.

---

#### D-P1-4. `BacktestRun` uses raw `Decimal` for `initial_cash` and pct fields — Money/Percentage primitives leaking through aggregate root

**File**: `backend/src/zebu/domain/entities/backtest_run.py:54-62`

```python
initial_cash: Decimal
total_return_pct: Decimal | None = None
max_drawdown_pct: Decimal | None = None
annualized_return_pct: Decimal | None = None
```

`Money` is the established value object for cash; `initial_cash: Decimal` skips it (no currency, no 2-decimal validation, validation only checks `> 0`). Performance percentages have no `Percentage` value object at all — `total_return_pct=Decimal("9999")` is currently legal.

`PortfolioSnapshot` has the same issue: `total_value`, `cash_balance`, `holdings_value` are all raw `Decimal` rather than `Money`. The validation in `__post_init__` re-derives "no negative monetary values" by hand for each field — `Money` would supply this for free *except* that `Money` validates non-finite/2-decimal-place but allows negatives (which is correct for `Money` since BUY transactions need negative `cash_change`). This points at a missing distinction between **signed `Money`** (cash deltas) and **non-negative `MoneyAmount`** (balances).

**Why P1**: Phase F's agent harness will be reading these fields heavily for performance reporting; the DCA strategy's `amount_per_period: Decimal` and the SMA strategy's `cash_balance: Decimal` parameter all interact with these. The fix is a one-time refactor; the cost of *not* doing it grows with every new caller.

**Suggested fix**: `initial_cash: Money`, snapshot monetary fields → `Money`. Introduce `Percentage` value object for the four `*_pct` fields with finite + reasonable-range validation. Consider a `BalanceMoney` type for non-negative balances (or accept `Money` and validate `is_negative() is False` at the aggregate level).

---

#### D-P1-5. `TradeSignal` uses `ValueError` instead of domain exception — breaks the catch-all rationale of `DomainException`

**File**: `backend/src/zebu/domain/value_objects/trade_signal.py:43-47`

```python
raise ValueError("Exactly one of quantity or amount must be set")
raise ValueError("quantity must be positive")
raise ValueError("amount must be positive")
```

Every other value object (`Money`, `Ticker`, `Quantity`) and every entity (`Portfolio`, `Strategy`, `BacktestRun`, `Transaction`, `PortfolioSnapshot`) raise a typed `Invalid*Error` from `domain/exceptions.py`. `TradeSignal` is the lone exception. The docstring even says "Raises: ValueError" — codifying the inconsistency.

The exception module has `InvalidValueObjectError` and the `ValueError`/`TypeError` raised in `InsufficientFundsError.__init__` and `InsufficientSharesError.__init__` (lines 121, 123, 125, 169, 171) are similarly using stdlib exceptions where domain exceptions belong. These are inside *exception constructors* validating their own arguments — arguably reasonable, but they should at least be consistent with the rest of the layer and use `InvalidValueObjectError` or a new `InvalidExceptionArgumentError`.

**Why P1**: the whole point of `class DomainException(Exception)` is "catch all domain errors at the API boundary". `TradeSignal` failures slip past it. With strategies generating `TradeSignal`s in hot paths, this matters.

**Suggested fix**: add `InvalidTradeSignalError(InvalidValueObjectError)`, raise that. Convert the `ValueError`/`TypeError` in `exceptions.py` constructors to use domain exceptions.

---

### P2 — Structural / cohesion improvements

#### D-P2-1. `Holding` (entity) and `HoldingBreakdown` (value object) overlap conceptually — same domain noun, two different shapes

**Files**: `backend/src/zebu/domain/entities/holding.py`, `backend/src/zebu/domain/entities/portfolio_snapshot.py:11-25`

```python
@dataclass(frozen=True)
class Holding:                             # uses Ticker, Quantity, Money
    ticker: Ticker
    quantity: Quantity
    cost_basis: Money

@dataclass(frozen=True)
class HoldingBreakdown:                    # uses str, int, Decimal
    ticker: str
    quantity: int
    price_per_share: Decimal
    value: Decimal
```

Two near-identical concepts — "shares of a ticker held at a moment" — with different field types and different namespaces. The names don't disambiguate well: a `HoldingBreakdown` *is* a holding at snapshot time, not a "breakdown" of one. Worse, `HoldingBreakdown.quantity: int` rules out fractional shares (which `Quantity` explicitly supports) — so `Holding` ⊋ `HoldingBreakdown` semantically, but they don't share a type. `HoldingBreakdown` is filed inside `entities/portfolio_snapshot.py` despite being a structureless data carrier (no identity, no lifecycle) — it should live in `value_objects/`.

**Suggested fix**: Either (a) make `HoldingBreakdown` use the same value objects (`Ticker`, `Quantity`, `Money`) and rename to `SnapshotHolding`, or (b) drop `HoldingBreakdown` entirely and have `PortfolioSnapshot.holdings_breakdown: list[Holding]` plus a `prices_at_snapshot: Mapping[Ticker, Money]` so price isn't entangled with the holding identity.

---

#### D-P2-2. `BacktestStatus` is missing a `PENDING` state and has no encapsulated transitions

**File**: `backend/src/zebu/domain/value_objects/backtest_status.py`

```python
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
```

`BacktestRun` docstring (line 36) says "None while pending/running" — implying a `PENDING` state that doesn't exist as an enum value. There is no domain method for "is this run terminal?" / "can I transition to RUNNING?" — instead, `backtest_executor.py` does naked status assignment (`status=BacktestStatus.RUNNING`, `status=BacktestStatus.FAILED`, `status=BacktestStatus.COMPLETED`) with no protection against, e.g., transitioning a `COMPLETED` run back to `RUNNING`. Phase F's agent harness will create runs asynchronously — the `PENDING` → `RUNNING` distinction will matter then.

**Suggested fix**: Add `PENDING` to the enum. Add `BacktestStatus.is_terminal` and `BacktestRun.transition_to(new_status)` method that enforces the lifecycle (`PENDING → RUNNING → {COMPLETED, FAILED}`). The state machine belongs in the entity, not the executor.

---

#### D-P2-3. `Transaction` BUY/SELL invariants don't go through `trade_factory` — duplicated logic + risk of bypass

**Files**: `backend/src/zebu/domain/entities/transaction.py:111-165`, `backend/src/zebu/domain/services/trade_factory.py`

`Transaction.__post_init__` validates `cash_change == quantity × price` for BUY/SELL. `trade_factory.create_buy_transaction` *also* computes `total_cost = price.multiply(quantity.shares)` and constructs `Transaction(cash_change=total_cost.negate(), ...)`. Two separate places computing the same arithmetic.

This is currently OK but invites drift: if e.g. fee handling lands later (Phase E), one path will get fees and the other won't. The right shape is `Transaction.buy(...)` / `Transaction.sell(...)` factory classmethods on the entity, with `trade_factory` *only* doing the cross-state checks (sufficient cash, sufficient shares) before calling those classmethods. That eliminates the parallel arithmetic and centralises BUY/SELL construction.

**Suggested fix**: `Transaction.buy(portfolio_id, ticker, quantity, price, timestamp, notes)` classmethod handling the `cash_change = -(qty × price)` math; ditto `Transaction.sell`. `trade_factory` becomes "domain function that checks cross-entity invariants then delegates."

---

#### D-P2-4. `TradeAction` (BUY/SELL) and `TransactionType` (DEPOSIT/WITHDRAWAL/BUY/SELL) are two enums with overlapping members

**Files**: `backend/src/zebu/domain/value_objects/trade_signal.py:9-13`, `backend/src/zebu/domain/entities/transaction.py:14-20`

The same string `"BUY"` appears in both enums (`TradeAction.BUY` and `TransactionType.BUY`) but they're separate types — code that wants to map a `TradeSignal.action` to a `TransactionType` has to do an enum-to-enum hop manually. Fine for now, but Phase F's agent path will frequently need to translate signal → transaction; the redundancy will be felt.

**Suggested fix**: either (a) `TransactionType` ⊆ `TradeAction` via `TradeAction(TransactionType)` and let the trade enum extend the transaction enum, or (b) explicit mapping helper `TradeAction.to_transaction_type()` so the conversion has one home.

---

#### D-P2-5. `Strategy` and `Portfolio` validate `created_at` against `datetime.now(UTC)` in `__post_init__` — non-deterministic + breaks pure-domain rule

**Files**: `backend/src/zebu/domain/entities/portfolio.py:53`, `backend/src/zebu/domain/entities/strategy.py:54`

```python
now = datetime.now(UTC)
```

The principles doc says "Domain logic has no I/O operations". Reading the wall clock is a side effect — it makes entity construction non-deterministic (the same constructor args can succeed or fail across calls if the clock crosses `created_at`), it makes tests flaky around the boundary, and it couples domain construction to system time. `BacktestRun.__post_init__` does the same thing (`if self.end_date > date.today()`).

**Why P2 not P1**: in practice these checks all reject "future" timestamps and the bug would be obscure. But it's a clear principles violation that an audit should flag.

**Suggested fix**: drop the `now()` checks from `__post_init__`. Move "is this timestamp plausible?" to the application layer (commands) which already has access to a clock port (or should).

---

### P3 — Aesthetic / minor

#### D-P3-1. `Money.__str__` always uses 2 decimals even for `JPY` (which is whole-yen)

**File**: `backend/src/zebu/domain/value_objects/money.py:228`

`f"{self.amount:,.2f}"` produces `¥1,234.00` — wrong for JPY (no decimal places). Combined with `__post_init__` rejecting >2 decimals but allowing 2 decimals for currencies that should have 0, the currency-precision model is incomplete. Low-priority because the app is USD-only in practice.

#### D-P3-2. Inconsistent `__hash__` / `__eq__` — `Holding` hashes on (ticker, quantity, cost_basis) but most others hash on ID

**Files**: all entities under `backend/src/zebu/domain/entities/`

`Holding` is correctly value-object-hashed (no identity), but it's filed under `entities/`. Either `Holding` should be in `value_objects/` (it's a derived projection without identity) or its current location should be documented as "derived entity." The docstring already calls it "derived," which is the rare case where the file path lies about the concept.

---

## Calibration notes for B2 / B3 selection

- **Highest leverage to fix before Phase F**: D-P1-1 (`TradeSignal` primitives), D-P1-3 (`Allocation` VO), D-P1-2 (`StrategyParameters` typed). Together these eliminate roughly 80% of the primitive-obsession surface that `StrategyConditionTrigger`, `ExplorationTask`, and parameter-sweep agents will touch.
- **Cheap structural cleanups** (good Phase B3 candidates): D-P1-5 (TradeSignal exception), D-P2-2 (BacktestStatus PENDING + transitions), D-P2-3 (Transaction.buy/sell classmethods), D-P2-5 (drop `now()` from `__post_init__`).
- **Defer**: D-P2-4 (TradeAction/TransactionType merge — only worth it during a Phase F refactor anyway), D-P3-* (aesthetic).
- **No P0**: every entity *can* enforce its current set of invariants; there is no construction path that produces a domain object the layer claims to forbid. The gaps are all "more invariants would help" / "primitives where VOs would help" — design pressure, not broken contracts.

## References

- `docs/planning/agent-platform-proposal.md` §3.4, §C4, §F3
- `docs/architecture/principles.md` (Domain is Pure rule informs D-P2-5)
- `agent_docs/tasks/210_live_strategy_execution.md` (Phase C target)
