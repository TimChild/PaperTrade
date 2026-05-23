"""Backtest-safe wrapper around :class:`AgentInvocationPort`.

Phase L-2 (Task #218). Wraps the production
:class:`AnthropicAgentInvocationAdapter` (or any other live
:class:`AgentInvocationPort`) to enforce the two safety invariants of
agent-driven backtests:

1. **Tool surface restriction.** Only the
   :class:`BacktestSafeTool` whitelist is exposed to the model. Banned
   tools (``web_search``, ``fetch_news``, ``get_current_price``,
   third-party MCP tools) are not registered as callable surface, and
   any name not in the whitelist that somehow reaches the dispatch
   callback raises :class:`BacktestSafetyViolationError`.
2. **Simulated-date filter.** Every whitelisted tool that takes a date
   parameter is capped at ``simulated_date`` end-of-UTC-day. Any caller
   argument exceeding this cap raises
   :class:`BacktestSafetyViolationError` — the wrapper never silently
   coerces a future date down, since silently swallowing the violation
   would hide a future-data leak.

The wrapper implements :class:`AgentInvocationPort`, so the L-3
executor injects it via DI with no awareness of the wrapping.
``simulated_date`` is bound at construction time (per-fire-day
instance), keeping the port contract clean.

References:
- ``agent_docs/tasks/218_backtest_agent_invocation_adapter.md`` — full spec.
- ``docs/planning/agent-platform-next-steps.md`` §3.2 (future-data leakage),
  §3.5 (BACKTEST_SAFE_TOOLS).
- :class:`AnthropicAgentInvocationAdapter` — inner adapter extended with
  the optional :data:`ToolDispatchCallback` parameter to support the
  multi-turn tool-use loop.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from zebu.application.ports.agent_invocation_port import (
    AgentInvocationPort,
    AgentInvocationResult,
    ToolDefinition,
)
from zebu.application.ports.exploration_task_repository import (
    ExplorationTaskRepository,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.queries.get_portfolio_balance import (
    GetPortfolioBalanceHandler,
    GetPortfolioBalanceQuery,
)
from zebu.domain.entities.exploration_task import ExplorationTaskStatus
from zebu.domain.exceptions import BacktestSafetyViolationError
from zebu.domain.value_objects.backtest_safe_tool import (
    BACKTEST_SAFE_TOOL_NAMES,
    BacktestSafeTool,
)
from zebu.domain.value_objects.ticker import Ticker

logger = logging.getLogger(__name__)


# Default temperature for backtest invocations. Proposal §5 Q4: deterministic
# intent and lower thinking-token cost on each fire. The "ish" caveat — the
# Anthropic API at temp=0 is not bit-stable across re-runs — is documented in
# the spec (§"Non-determinism") and surfaced to the user via the L-4 UI.
_DEFAULT_BACKTEST_TEMPERATURE: float = 0.0


def _end_of_utc_day(simulated_date: date) -> datetime:
    """Convert a calendar date to its end-of-UTC-day datetime.

    The simulated-date boundary is end-of-day so the agent can see the
    simulated trading day's close (the freshest information available
    for the in-simulation "today") but cannot peek at the next day's open.

    This mirrors :class:`HistoricalDataPreparer.prepare`'s convention.
    """
    return datetime(
        simulated_date.year,
        simulated_date.month,
        simulated_date.day,
        hour=23,
        minute=59,
        second=59,
        tzinfo=UTC,
    )


def _parse_datetime_arg(
    raw: object, *, field_name: str, date_to_end_of_day: bool = False
) -> datetime | None:
    """Coerce a tool-argument value to a UTC datetime.

    Accepts ISO-8601 strings, :class:`date`, or pre-parsed
    :class:`datetime`. Returns ``None`` if the argument was not
    supplied; raises :class:`ValueError` for other types so the caller
    can wrap into a :class:`BacktestSafetyViolationError`.

    Args:
        raw: The caller-supplied value (typed loosely because it comes
            from the model's tool input).
        field_name: Field name used in error messages.
        date_to_end_of_day: When the input is a date-only value
            (``date`` instance or ``"YYYY-MM-DD"`` string), interpret it
            as end-of-UTC-day instead of midnight. Useful for upper-
            bound arguments like ``end`` / ``as_of`` / ``claimed_before``
            where the caller's "Mar 14" typically means "all of Mar 14".
            For lower-bound arguments like ``start``, leave as midnight.
    """
    if raw is None:
        return None
    if isinstance(raw, datetime):
        # Normalise to UTC; reject naive datetimes.
        if raw.tzinfo is None:
            raise ValueError(
                f"{field_name} must be timezone-aware (UTC); got naive datetime"
            )
        return raw.astimezone(UTC)
    if isinstance(raw, date):
        # ``isinstance(d, date)`` is True for both date and datetime; we
        # already handled datetime above so this is a calendar-only date.
        if date_to_end_of_day:
            return datetime(raw.year, raw.month, raw.day, 23, 59, 59, tzinfo=UTC)
        return datetime(raw.year, raw.month, raw.day, tzinfo=UTC)
    if isinstance(raw, str):
        # Accept both "YYYY-MM-DD" and full ISO-8601 datetimes.
        try:
            if len(raw) == 10:
                if date_to_end_of_day:
                    parsed = datetime.fromisoformat(raw).replace(
                        hour=23, minute=59, second=59, tzinfo=UTC
                    )
                else:
                    parsed = datetime.fromisoformat(raw).replace(tzinfo=UTC)
            else:
                parsed = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} is not a valid ISO-8601 date/datetime: {raw!r}"
            ) from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    raise ValueError(
        f"{field_name} must be a datetime, date, or ISO-8601 string; "
        f"got {type(raw).__name__}"
    )


def _build_safety_preamble(simulated_date: date) -> str:
    """Build the system-prompt safety preamble.

    Tells the agent it's running in backtest mode, what the simulated
    date is, and which tools are available — defence in depth so the
    agent's reasoning is constrained at the prompt layer in addition to
    the runtime dispatch enforcement.

    Tests assert structural properties (sections present, simulated_date
    inlined) rather than exact string equality, so the wording can drift
    without breaking the suite.
    """
    iso = simulated_date.isoformat()
    tool_list = ", ".join(BACKTEST_SAFE_TOOL_NAMES)
    return (
        "BACKTEST MODE — SAFETY PREAMBLE\n"
        f"\nThe current simulated date is {iso}. You are executing inside "
        "a deterministic backtest replay; the world outside this date "
        "does not exist from your perspective.\n"
        "\nYou MAY NOT call tools that return data after this date. Every "
        "tool call you issue is filtered server-side against this date "
        "boundary — out-of-bounds calls are rejected and cause the "
        "invocation to fail with no decision recorded.\n"
        "\nAvailable tools (whitelist — anything else is blocked): "
        f"{tool_list}. Use them sparingly and decide quickly; cost and "
        "loop turns are bounded.\n"
        "\nAt the end of your reasoning, call record_decision exactly "
        "once with your structured decision.\n"
    )


def _build_safe_tool_definitions(simulated_date: date) -> list[ToolDefinition]:
    """Build the :class:`ToolDefinition` list for the whitelist.

    Schemas mention the ``simulated_date`` boundary in their description
    so the agent is informed at the schema layer; the runtime dispatch
    still enforces it.
    """
    iso = simulated_date.isoformat()
    return [
        ToolDefinition(
            name=BacktestSafeTool.GET_PRICE_HISTORY.value,
            description=(
                "Fetch historical price points for a ticker. "
                f"Backtest constraint: ``end`` must be <= {iso} "
                "(end-of-UTC-day). Out-of-bounds values are rejected. "
                "Both ``start`` and ``end`` accept ISO-8601 date "
                "(YYYY-MM-DD) or datetime."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol (e.g. 'AAPL').",
                    },
                    "start": {
                        "type": "string",
                        "description": "Start of range (ISO-8601). Inclusive.",
                    },
                    "end": {
                        "type": "string",
                        "description": (
                            f"End of range (ISO-8601). Inclusive. Must be "
                            f"<= {iso}. Omit to default to {iso}."
                        ),
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["1min", "5min", "1hour", "1day"],
                        "description": "Price interval. Default '1day'.",
                    },
                },
                "required": ["ticker", "start"],
            },
        ),
        ToolDefinition(
            name=BacktestSafeTool.GET_PORTFOLIO_STATE.value,
            description=(
                "Read the simulated backtest portfolio's cash, holdings, "
                f"and total value. Backtest constraint: ``as_of`` must be "
                f"<= {iso} (end-of-UTC-day). Omit to default to {iso}."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "string",
                        "description": "Portfolio UUID (the backtest portfolio).",
                    },
                    "as_of": {
                        "type": "string",
                        "description": (
                            f"Reference time (ISO-8601). Must be <= {iso}. "
                            f"Omit to default to {iso}."
                        ),
                    },
                },
                "required": ["portfolio_id"],
            },
        ),
        ToolDefinition(
            name=BacktestSafeTool.LIST_EXPLORATION_TASKS.value,
            description=(
                "List completed exploration tasks (status=DONE). Use this "
                "to read prior agent research findings that may inform "
                f"today's decision. Backtest constraint: ``claimed_before`` "
                f"must be <= {iso} (end-of-UTC-day). Omit to default to "
                f"{iso}. Status filter is hard-coded to DONE for backtest "
                "replays."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "claimed_before": {
                        "type": "string",
                        "description": (
                            f"Upper bound on claim timestamp (ISO-8601). "
                            f"Must be <= {iso}. Omit to default to {iso}."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 20).",
                    },
                },
                "required": [],
            },
        ),
    ]


class BacktestAgentInvocationAdapter:
    """Backtest-safe wrapper around an inner :class:`AgentInvocationPort`.

    Conforms to :class:`AgentInvocationPort` so the L-3 executor can
    inject it via DI without knowing it's wrapped. Construction binds
    one ``simulated_date`` — L-3 builds a fresh instance per simulated
    fire day.

    Constructor parameters per Task #218 §"Constructor":

    Attributes:
        _inner: The production :class:`AgentInvocationPort` (typically
            :class:`AnthropicAgentInvocationAdapter`). Tests may inject
            a fake to assert the wrapper's behaviour without an SDK call.
        _simulated_date: The in-simulation calendar day this wrapper
            enforces.
        _market_data: Adapter for ``GET_PRICE_HISTORY`` dispatch.
        _portfolio_balance_handler: Handler for ``GET_PORTFOLIO_STATE``
            dispatch. Reuses the existing balance query so historical
            ``as_of`` semantics match the rest of the platform.
        _exploration_task_repo: Repository for ``LIST_EXPLORATION_TASKS``
            dispatch.
        _agent_temperature: Sampling temperature passed through to the
            inner port. ``None`` means "use the inner adapter's default"
            (which, for the production Anthropic adapter, is the SDK's
            default). Default is ``0.0`` for deterministic-ish replays.
    """

    def __init__(
        self,
        *,
        inner: AgentInvocationPort,
        simulated_date: date,
        market_data: MarketDataPort,
        portfolio_balance_handler: GetPortfolioBalanceHandler,
        exploration_task_repo: ExplorationTaskRepository,
        agent_temperature: float | None = _DEFAULT_BACKTEST_TEMPERATURE,
    ) -> None:
        """Initialise the wrapper for one simulated-day invocation.

        Args:
            inner: The :class:`AgentInvocationPort` to delegate to. The
                wrapper does NOT touch the Anthropic SDK directly; this
                keeps the dependency localised and tests cheap.
            simulated_date: The in-simulation "today". All tool calls
                are capped at this date end-of-UTC-day.
            market_data: For ``GET_PRICE_HISTORY``.
            portfolio_balance_handler: For ``GET_PORTFOLIO_STATE``.
            exploration_task_repo: For ``LIST_EXPLORATION_TASKS``.
            agent_temperature: Sampling temperature override. Defaults
                to :data:`_DEFAULT_BACKTEST_TEMPERATURE` (0.0). Pass
                ``None`` to let the inner adapter's default apply.
        """
        self._inner = inner
        self._simulated_date = simulated_date
        self._market_data = market_data
        self._portfolio_balance_handler = portfolio_balance_handler
        self._exploration_task_repo = exploration_task_repo
        self._agent_temperature = agent_temperature
        # Pre-computed end-of-day cap for tool argument validation.
        self._simulated_eod: datetime = _end_of_utc_day(simulated_date)

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
        agent_temperature: float | None = None,
    ) -> AgentInvocationResult:
        """Run the simulated agent invocation with safety enforcement.

        Per the spec §"Behaviour":

        - **Caller-supplied ``tools`` is IGNORED.** The wrapper supplies
          its own :attr:`BACKTEST_SAFE_TOOLS_DEFINITIONS` list to the
          inner port so the agent's tool surface is exactly the
          whitelist — belt-and-braces against a future L-3 mistake.
        - **Safety preamble** is prepended to the caller's
          ``system_prompt`` so the agent reads the boundary up front.
        - **Dispatch callback** validates every tool call against
          ``simulated_date`` and routes to the underlying adapter /
          handler / repo.

        Args:
            system_prompt: Caller's system prompt. Prepended with the
                safety preamble.
            user_prompt: Caller's user prompt — forwarded verbatim.
            tools: Ignored. The wrapper supplies its own whitelist.
            timeout_secs: Per-call timeout, forwarded to the inner.
            agent_temperature: Per-call temperature override. When
                ``None`` (default), the constructor-supplied
                :attr:`_agent_temperature` is used. When set, overrides
                for this call only — useful for tests that need to
                assert plumbing without re-constructing the wrapper.

        Returns:
            The :class:`AgentInvocationResult` from the inner port,
            returned unmodified.

        Raises:
            BacktestSafetyViolationError: Agent called a non-whitelisted
                tool, or passed a date/datetime argument exceeding
                ``simulated_date`` end-of-UTC-day.
            AgentInvocationError: Transport / parse failure from the
                inner port (propagates).
        """
        # Belt-and-braces: ignore any caller-supplied tools list.
        del tools

        safety_preamble = _build_safety_preamble(self._simulated_date)
        if system_prompt:
            wrapped_system_prompt = f"{safety_preamble}\n\n{system_prompt}"
        else:
            wrapped_system_prompt = safety_preamble
        tool_definitions = _build_safe_tool_definitions(self._simulated_date)

        # ``dispatch_tool_call`` is the closure-with-state pattern; it
        # captures ``self`` so each tool call can route to the right
        # private helper after argument validation.
        async def dispatch(name: str, tool_input: Mapping[str, object]) -> str:
            return await self._dispatch_tool_call(name=name, tool_input=tool_input)

        if agent_temperature is not None:
            effective_temperature = agent_temperature
        else:
            effective_temperature = self._agent_temperature

        return await self._inner.invoke(
            system_prompt=wrapped_system_prompt,
            user_prompt=user_prompt,
            tools=tool_definitions,
            timeout_secs=timeout_secs,
            agent_temperature=effective_temperature,
            dispatch_tool_call=dispatch,
        )

    # ------------------------------------------------------------------ #
    # Tool dispatch                                                       #
    # ------------------------------------------------------------------ #

    async def _dispatch_tool_call(
        self, *, name: str, tool_input: Mapping[str, object]
    ) -> str:
        """Route one tool call to the right handler after safety validation.

        :class:`BacktestSafetyViolationError` is raised — and propagated
        — when:

        * ``name`` is not in :class:`BacktestSafeTool`.
        * Any date argument exceeds ``simulated_date`` end-of-UTC-day.
        """
        try:
            tool = BacktestSafeTool(name)
        except ValueError as exc:
            raise BacktestSafetyViolationError(
                tool_name=name,
                simulated_date=self._simulated_date,
                reason=f"tool {name!r} is not in BACKTEST_SAFE_TOOLS",
            ) from exc

        if tool is BacktestSafeTool.GET_PRICE_HISTORY:
            return await self._dispatch_get_price_history(tool_input)
        if tool is BacktestSafeTool.GET_PORTFOLIO_STATE:
            return await self._dispatch_get_portfolio_state(tool_input)
        if tool is BacktestSafeTool.LIST_EXPLORATION_TASKS:
            return await self._dispatch_list_exploration_tasks(tool_input)
        # Unreachable — every enum value is handled above. Defensive
        # ``raise`` so a future enum addition surfaces loudly.
        raise BacktestSafetyViolationError(  # pragma: no cover - unreachable
            tool_name=name,
            simulated_date=self._simulated_date,
            reason=f"unhandled safe tool {tool.value!r}",
        )

    async def _dispatch_get_price_history(
        self, tool_input: Mapping[str, object]
    ) -> str:
        """Dispatch ``get_price_history`` with simulated-date cap on ``end``."""
        ticker_raw = tool_input.get("ticker")
        if not isinstance(ticker_raw, str) or not ticker_raw.strip():
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PRICE_HISTORY.value,
                simulated_date=self._simulated_date,
                reason="'ticker' argument is required and must be a non-empty string",
            )
        try:
            start = _parse_datetime_arg(tool_input.get("start"), field_name="start")
        except ValueError as exc:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PRICE_HISTORY.value,
                simulated_date=self._simulated_date,
                reason=str(exc),
            ) from exc
        if start is None:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PRICE_HISTORY.value,
                simulated_date=self._simulated_date,
                reason="'start' argument is required",
            )

        try:
            end_arg = _parse_datetime_arg(
                tool_input.get("end"),
                field_name="end",
                date_to_end_of_day=True,
            )
        except ValueError as exc:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PRICE_HISTORY.value,
                simulated_date=self._simulated_date,
                reason=str(exc),
            ) from exc

        if end_arg is None:
            end = self._simulated_eod
        elif end_arg > self._simulated_eod:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PRICE_HISTORY.value,
                simulated_date=self._simulated_date,
                reason=(
                    f"end {end_arg.isoformat()} exceeds simulated_date "
                    f"end-of-UTC-day {self._simulated_eod.isoformat()}"
                ),
            )
        else:
            end = end_arg

        interval_raw = tool_input.get("interval", "1day")
        interval = interval_raw if isinstance(interval_raw, str) else "1day"

        ticker = Ticker(ticker_raw.upper())
        price_points = await self._market_data.get_price_history(
            ticker=ticker,
            start=start,
            end=end,
            interval=interval,
        )
        # Serialise to a small JSON-compatible shape. The model only
        # needs the list of (timestamp, price) tuples — not the full
        # PricePoint metadata.
        serialised = [
            {
                "timestamp": pp.timestamp.isoformat(),
                "price": str(pp.price.amount),
                "currency": pp.price.currency,
                "source": pp.source,
            }
            for pp in price_points
        ]
        return json.dumps(
            {
                "ticker": ticker.symbol,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "interval": interval,
                "price_points": serialised,
            }
        )

    async def _dispatch_get_portfolio_state(
        self, tool_input: Mapping[str, object]
    ) -> str:
        """Dispatch ``get_portfolio_state`` with simulated-date cap on ``as_of``."""
        portfolio_id_raw = tool_input.get("portfolio_id")
        if not isinstance(portfolio_id_raw, str) or not portfolio_id_raw.strip():
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PORTFOLIO_STATE.value,
                simulated_date=self._simulated_date,
                reason=(
                    "'portfolio_id' argument is required and must be a "
                    "non-empty UUID string"
                ),
            )
        try:
            portfolio_id = UUID(portfolio_id_raw)
        except ValueError as exc:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PORTFOLIO_STATE.value,
                simulated_date=self._simulated_date,
                reason=(f"'portfolio_id' is not a valid UUID: {portfolio_id_raw!r}"),
            ) from exc

        try:
            as_of_arg = _parse_datetime_arg(
                tool_input.get("as_of"),
                field_name="as_of",
                date_to_end_of_day=True,
            )
        except ValueError as exc:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PORTFOLIO_STATE.value,
                simulated_date=self._simulated_date,
                reason=str(exc),
            ) from exc

        if as_of_arg is None:
            as_of = self._simulated_eod
        elif as_of_arg > self._simulated_eod:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.GET_PORTFOLIO_STATE.value,
                simulated_date=self._simulated_date,
                reason=(
                    f"as_of {as_of_arg.isoformat()} exceeds simulated_date "
                    f"end-of-UTC-day {self._simulated_eod.isoformat()}"
                ),
            )
        else:
            as_of = as_of_arg

        result = await self._portfolio_balance_handler.execute(
            GetPortfolioBalanceQuery(portfolio_id=portfolio_id, as_of=as_of)
        )
        return json.dumps(
            {
                "portfolio_id": str(result.portfolio_id),
                "cash_balance": str(result.cash_balance.amount),
                "holdings_value": str(result.holdings_value.amount),
                "total_value": str(result.total_value.amount),
                "currency": result.currency,
                "as_of": result.as_of.isoformat(),
                "daily_change": str(result.daily_change.amount),
                "daily_change_percent": str(result.daily_change_percent),
            }
        )

    async def _dispatch_list_exploration_tasks(
        self, tool_input: Mapping[str, object]
    ) -> str:
        """Dispatch ``list_exploration_tasks`` with simulated-date cap.

        ``claimed_before`` is capped at ``simulated_date`` end-of-UTC-day.
        Status is hard-locked to ``DONE`` for backtest replays — the
        agent reads historical research artefacts only, not the live
        in-progress backlog.
        """
        try:
            claimed_before_arg = _parse_datetime_arg(
                tool_input.get("claimed_before"),
                field_name="claimed_before",
                date_to_end_of_day=True,
            )
        except ValueError as exc:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.LIST_EXPLORATION_TASKS.value,
                simulated_date=self._simulated_date,
                reason=str(exc),
            ) from exc

        if claimed_before_arg is None:
            claimed_before = self._simulated_eod
        elif claimed_before_arg > self._simulated_eod:
            raise BacktestSafetyViolationError(
                tool_name=BacktestSafeTool.LIST_EXPLORATION_TASKS.value,
                simulated_date=self._simulated_date,
                reason=(
                    f"claimed_before {claimed_before_arg.isoformat()} exceeds "
                    f"simulated_date end-of-UTC-day {self._simulated_eod.isoformat()}"
                ),
            )
        else:
            claimed_before = claimed_before_arg

        limit_raw = tool_input.get("limit", 20)
        limit = (
            limit_raw
            if isinstance(limit_raw, int) and not isinstance(limit_raw, bool)
            else 20
        )
        # Fetch DONE-status tasks; the repo doesn't expose a
        # ``claimed_before`` filter so we post-filter here. The repo
        # caps via ``limit``; over-fetch and filter is acceptable for
        # the small backtest set sizes.
        tasks = await self._exploration_task_repo.list_by_status(
            ExplorationTaskStatus.DONE,
            limit=limit,
        )
        filtered = [
            t
            for t in tasks
            if t.claimed_at is not None and t.claimed_at <= claimed_before
        ]
        return json.dumps(
            {
                "claimed_before": claimed_before.isoformat(),
                "status": ExplorationTaskStatus.DONE.value,
                "tasks": [
                    {
                        "id": str(t.id),
                        "prompt": t.prompt,
                        "claimed_at": (
                            t.claimed_at.isoformat() if t.claimed_at else None
                        ),
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in filtered
                ],
            },
            default=_json_default,
        )


def _json_default(obj: object) -> object:
    """Fallback serialiser for tool-result JSON.

    The dispatched tools occasionally surface :class:`Decimal` values
    (price / balance amounts) and :class:`UUID` instances; json.dumps
    doesn't handle those natively. Stringify everything else so a
    surprise type doesn't crash the dispatch.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return cast("object", str(obj))


__all__ = [
    "BacktestAgentInvocationAdapter",
    "_build_safe_tool_definitions",
    "_build_safety_preamble",
]
