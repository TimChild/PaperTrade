"""Typed schemas for Zebu API responses surfaced through MCP.

Mirrors the wire shapes from
``backend/src/zebu/adapters/inbound/api/`` but is intentionally a *copy*
rather than an import — the MCP package is supposed to be liftable into
its own repo. If the backend tightens a wire shape, this file gets
updated alongside.

Design notes:

* Every list-returning tool maps the Zebu ``PaginatedResponse[T]`` (see
  ``backend/.../schemas/pagination.py``) onto a ``Page[T]`` here that
  preserves the pagination metadata. We *don't* flatten to a bare list —
  agents need to know there's a next page, otherwise they'll silently miss
  results once the user has more than 20 portfolios / strategies / etc.
* Money-and-decimal-shaped fields stay as strings (e.g. ``"123.45"``)
  matching the wire format. Coercing to ``Decimal`` here would force a
  parse that the caller may not want; tools can pass them through as-is.
* Datetime fields stay as ISO-8601 strings for the same reason — the MCP
  protocol serialises tool results to JSON, so re-parsing to ``datetime``
  on this side and serialising back is wasted work.
* For *write* tools added in Wave 2 we also have request-body schemas
  (e.g. :class:`CreateStrategyRequest`, :class:`RunBacktestRequest`).
  These mirror the backend's request models but are intentionally
  permissive — the backend is the source of truth for parameter
  invariants. For example, ``parameters`` on
  :class:`CreateStrategyRequest` is a free-form ``dict[str, object]``
  matching the wire shape; the typed-dataclass per-type shape is checked
  server-side and the typed 422 ``ZebuApiError`` carries the field-level
  detail back to the agent.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    """MCP-side mirror of the backend's ``PaginatedResponse[T]``.

    Wave 1 design decision: we expose pagination metadata to the agent
    rather than flattening to a bare list. Without ``has_more``, an agent
    asking for "all portfolios" with the default ``limit=20`` would
    silently miss anything past row 20 once the user has more than that
    many — the kind of bug that's invisible in dev and shows up in
    production after a year of accumulated data.
    """

    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------


class SupportedTickers(BaseModel):
    """Response shape for ``GET /api/v1/prices/``."""

    tickers: list[str]
    count: int


class CurrentPrice(BaseModel):
    """Response shape for ``GET /api/v1/prices/{ticker}``."""

    ticker: str
    price: str = Field(description="Decimal-formatted price, e.g. '184.32'.")
    currency: str
    timestamp: str = Field(description="ISO-8601 UTC observation time.")
    source: str
    is_stale: bool


class PricePoint(BaseModel):
    """Single point in a historical price series."""

    ticker: str
    price: str
    currency: str
    timestamp: str
    source: str
    interval: str


class PriceHistory(BaseModel):
    """Response shape for ``GET /api/v1/prices/{ticker}/history``."""

    ticker: str
    prices: list[PricePoint]
    start: str
    end: str
    interval: str
    count: int


# ---------------------------------------------------------------------------
# Portfolios
# ---------------------------------------------------------------------------


class Portfolio(BaseModel):
    """Response shape for ``GET /api/v1/portfolios/{id}``."""

    id: UUID
    user_id: UUID
    name: str
    created_at: str
    portfolio_type: str


class PortfolioBalance(BaseModel):
    """Response shape for ``GET /api/v1/portfolios/{id}/balance``."""

    cash_balance: str
    holdings_value: str
    total_value: str
    currency: str
    as_of: str
    daily_change: str
    daily_change_percent: str


class Holding(BaseModel):
    """Single stock holding inside a portfolio."""

    ticker: str
    quantity: str
    cost_basis: str
    average_cost_per_share: str | None = None
    current_price: str | None = None
    market_value: str | None = None
    unrealized_gain_loss: str | None = None
    unrealized_gain_loss_percent: str | None = None
    price_timestamp: str | None = None
    price_source: str | None = None


class PortfolioState(BaseModel):
    """Composite response — what an agent typically wants when it asks
    "give me the state of portfolio X".

    Aggregates the three GET endpoints into a single MCP tool result so
    agents don't have to chain three calls just to know "what's in there
    right now."
    """

    portfolio: Portfolio
    balance: PortfolioBalance
    holdings: list[Holding]


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


class Strategy(BaseModel):
    """Response shape for ``GET /api/v1/strategies/{id}``."""

    id: UUID
    user_id: UUID
    name: str
    strategy_type: str
    tickers: list[str]
    parameters: dict[str, Any]
    created_at: str


# ---------------------------------------------------------------------------
# Backtests
# ---------------------------------------------------------------------------


class BacktestRun(BaseModel):
    """Response shape for ``GET /api/v1/backtests/{id}``."""

    id: UUID
    user_id: UUID
    strategy_id: UUID | None
    portfolio_id: UUID
    backtest_name: str
    start_date: str
    end_date: str
    initial_cash: str
    status: str
    created_at: str
    completed_at: str | None = None
    error_message: str | None = None
    total_return_pct: str | None = None
    max_drawdown_pct: str | None = None
    annualized_return_pct: str | None = None
    total_trades: int | None = None


# ---------------------------------------------------------------------------
# Strategy activations
# ---------------------------------------------------------------------------


class StrategyActivation(BaseModel):
    """Response shape for ``GET /api/v1/activations`` items.

    Same shape as the activation singleton at
    ``GET /api/v1/strategies/{id}/activation``.
    """

    id: UUID
    user_id: UUID
    strategy_id: UUID
    portfolio_id: UUID
    status: str
    frequency: str
    last_executed_at: str | None = None
    last_error: str | None = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Exploration tasks
# ---------------------------------------------------------------------------


class ExplorationConstraints(BaseModel):
    """Optional constraints attached to an exploration task."""

    max_backtests: int | None = None
    allow_live_activation: bool = True
    strategy_type_whitelist: list[str] | None = None


class ExplorationFindingsMetrics(BaseModel):
    """Primary backtest metrics for the chosen candidate (Phase E2).

    Decimal fields are wire strings (e.g. ``"24.4"``) — same convention as
    ``BacktestRun`` metric fields. ``total_return_pct`` is required;
    everything else is optional because not every backtest yields all
    metrics (e.g. a single-trade buy-and-hold has no Sharpe).
    """

    total_return_pct: str
    sharpe_ratio: str | None = None
    max_drawdown_pct: str | None = None
    n_trades: int | None = None
    annualized_return_pct: str | None = None


class ExplorationFindingsComparison(BaseModel):
    """Comparison of the chosen candidate to a baseline backtest (Phase E2).

    Deltas are signed: positive means the candidate outperformed.
    """

    baseline_strategy_id: UUID
    baseline_total_return_pct: str
    delta_total_return_pct: str
    delta_sharpe: str | None = None


class ExplorationFindings(BaseModel):
    """Findings submitted by an agent that completed an exploration task.

    Phase E2 added structured fields for parameter-sweep results. Every E2
    field is optional; agents may submit only ``summary`` for narrative
    findings.
    """

    summary: str
    backtest_run_ids: list[UUID]
    strategy_ids: list[UUID]
    notes: list[str] | None = None
    recommended_strategy_id: UUID | None = None
    # `recommended_parameters` is opaque per-strategy-type JSON. The shape
    # varies by strategy_type — see the schema for ``CreateStrategyRequest``
    # for the per-type contract.
    recommended_parameters: dict[str, Any] | None = None
    metrics: ExplorationFindingsMetrics | None = None
    comparison_to_baseline: ExplorationFindingsComparison | None = None
    confidence: float | None = None


class ExplorationTask(BaseModel):
    """Response shape for ``GET /api/v1/exploration-tasks/{id}``."""

    id: UUID
    created_by: UUID
    prompt: str
    status: str
    target_portfolio_id: UUID | None = None
    tickers: list[str] | None = None
    constraints: ExplorationConstraints | None = None
    claimed_by: str | None = None
    claimed_at: str | None = None
    findings: ExplorationFindings | None = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Write-tool request bodies (Wave 2)
#
# These mirror the backend's request models. We keep them in this single
# schemas module so the MCP package has one place to look up "what shape
# do I send to /strategies vs /backtests vs /strategies/{id}/activate?".
# ---------------------------------------------------------------------------


class CreateStrategyRequest(BaseModel):
    """Request body for ``POST /api/v1/strategies``.

    The ``parameters`` field is intentionally a free-form mapping — the
    backend's ``CreateStrategyRequest`` accepts ``dict[str, Any]`` and
    parses it into one of three typed dataclasses (``BuyAndHoldParameters``
    / ``DcaParameters`` / ``MaCrossoverParameters``) using ``strategy_type``
    as the discriminator. Encoding the discriminated union in this schema
    would force the MCP tool's JSON Schema to be a sprawling ``oneOf``,
    which most agents can drive but few render usefully.

    Per-type expected shape (see
    ``backend/.../value_objects/strategy_parameters.py`` for the canonical
    contract):

    * ``BUY_AND_HOLD``: ``{"allocation": {"<TICKER>": "<fraction>", ...}}``
      — fractions are decimal strings summing to 1.0 (±0.001).
    * ``DOLLAR_COST_AVERAGING``: ``{"frequency_days": <int 1-365>,
      "amount_per_period": "<decimal-str>", "allocation": {...}}``.
    * ``MOVING_AVERAGE_CROSSOVER``: ``{"fast_window": <int 2-200>,
      "slow_window": <int 2-200, > fast_window>,
      "invest_fraction": "<decimal-str in (0, 1]>"}``.

    Invalid shapes come back as a typed 422 ``ZebuApiError`` with the
    backend's per-field detail map.
    """

    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(
        ...,
        description=(
            "Algorithm type: BUY_AND_HOLD, DOLLAR_COST_AVERAGING, "
            "MOVING_AVERAGE_CROSSOVER."
        ),
    )
    tickers: list[str] = Field(..., min_length=1, max_length=10)
    parameters: dict[str, Any] = Field(default_factory=dict)


class RunBacktestRequest(BaseModel):
    """Request body for ``POST /api/v1/backtests``.

    Dates are accepted as ISO-8601 ``YYYY-MM-DD`` strings (the backend
    parses them with Pydantic's date parser). ``initial_cash`` is a
    decimal-string with at most 2 decimal places — encoded as a string
    so the wire-side decimal representation is exact.
    """

    strategy_id: UUID
    backtest_name: str = Field(..., min_length=1, max_length=100)
    start_date: str = Field(
        ..., description="YYYY-MM-DD ISO-8601 date for the backtest start."
    )
    end_date: str = Field(
        ...,
        description=(
            "YYYY-MM-DD ISO-8601 date for the backtest end (must be after "
            "start_date and not in the future; range <= 3 years)."
        ),
    )
    initial_cash: str = Field(
        ...,
        description="Starting cash as a decimal string, e.g. '10000.00'. > 0.",
    )


class ActivateStrategyRequest(BaseModel):
    """Request body for ``POST /api/v1/strategies/{id}/activate``."""

    portfolio_id: UUID
    frequency: str = Field(
        default="DAILY_MARKET_CLOSE",
        description=(
            "Execution cadence. Phase C1 ships only DAILY_MARKET_CLOSE; "
            "the field is forward-compatible for future cadences."
        ),
    )


class DeactivateActivationRequest(BaseModel):
    """Request body for ``POST /api/v1/activations/{id}/deactivate``."""

    reason: str | None = Field(
        default=None,
        max_length=500,
        description=(
            "Optional human-readable reason; surfaced on the activation's "
            "``last_error`` field for UI display."
        ),
    )


class RunNowResponse(BaseModel):
    """Response shape for ``POST /api/v1/activations/{id}/run-now``.

    Carries the immediate execution outcome along with the post-run
    activation state, so a caller can see "ran X, executed Y trades"
    without polling.
    """

    activation: StrategyActivation
    succeeded: bool
    trades: int
    error: str | None = None


class CreateExplorationTaskRequest(BaseModel):
    """Request body for ``POST /api/v1/exploration-tasks``.

    Mirrors the backend's ``CreateExplorationTaskRequest``. Optional
    fields are forwarded as-is when supplied; ``constraints`` is a
    nested object reusing :class:`ExplorationConstraints`.
    """

    prompt: str = Field(..., min_length=1, max_length=4000)
    target_portfolio_id: UUID | None = None
    tickers: list[str] | None = Field(default=None, max_length=50)
    constraints: ExplorationConstraints | None = None


class ClaimExplorationTaskRequest(BaseModel):
    """Request body for ``POST /api/v1/exploration-tasks/{id}/claim``.

    The backend accepts an empty body; supplying ``agent_id`` lets the
    caller stamp a free-form label (typically the API-key label or the
    agent's chosen identifier) for audit visibility.
    """

    agent_id: str | None = Field(default=None, min_length=1, max_length=200)


class SubmitExplorationFindingsRequest(BaseModel):
    """Request body for ``POST /api/v1/exploration-tasks/{id}/findings``.

    Submitting findings transitions the task from IN_PROGRESS -> DONE.
    The backend rejects (409) if the task is in any other status.

    Phase E2 — extended with structured recommendation fields. The
    narrative ``summary`` remains the required wrapper; every E2 field is
    optional so agents can submit just ``summary`` for narrative findings.
    """

    summary: str = Field(..., min_length=1, max_length=4000)
    backtest_run_ids: list[UUID] = Field(default_factory=list)
    strategy_ids: list[UUID] = Field(default_factory=list)
    notes: list[str] | None = None
    recommended_strategy_id: UUID | None = None
    recommended_parameters: dict[str, Any] | None = None
    metrics: ExplorationFindingsMetrics | None = None
    comparison_to_baseline: ExplorationFindingsComparison | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class NoteResult(BaseModel):
    """Result of the ``note`` tool.

    The note tool is intentionally local-only in Wave 2 — the backend
    has no free-floating note endpoint, and the only way to attach text
    to an ``ExplorationTask`` is via ``submit_exploration_finding``,
    which transitions the task to DONE (so it can't be used as an
    "append a thought" channel without ending the task). Rather than
    add a new backend endpoint, the tool echoes the note back to the
    agent with guidance on the persistent paths.
    """

    text: str
    exploration_task_id: UUID | None = None
    strategy_id: UUID | None = None
    persisted: bool = Field(
        default=False,
        description=(
            "Always false in Wave 2 — the note is local-only. To persist a "
            "note, call ``submit_exploration_finding`` (which DONE-transitions "
            "an IN_PROGRESS task and accepts a ``notes`` list) or include "
            "the text in a future ``create_exploration_task`` ``prompt``."
        ),
    )
    advice: str = Field(
        description=(
            "Suggested follow-up — typically points the agent at the right "
            "persistent tool (submit_exploration_finding / "
            "create_exploration_task)."
        ),
    )
