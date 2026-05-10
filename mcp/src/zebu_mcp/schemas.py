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


class ExplorationFindings(BaseModel):
    """Findings submitted by an agent that completed an exploration task."""

    summary: str
    backtest_run_ids: list[UUID]
    strategy_ids: list[UUID]
    notes: list[str] | None = None


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
