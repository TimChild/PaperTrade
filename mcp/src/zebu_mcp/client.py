"""HTTP client wrapping the Zebu REST API for MCP tools.

Owns auth-header injection, error mapping, and pagination plumbing.
Tools call typed methods like ``client.list_portfolios(limit=20)`` rather
than constructing httpx requests themselves — that keeps every tool free
of plumbing and makes it easy to swap transport (stdio HTTP, in-process,
mocked) in tests.

Error mapping
-------------

The Zebu API standardised on the ``ErrorResponse`` envelope (see
``backend/.../schemas/errors.py``):

    {
        "detail": "<human-readable>",
        "code": "<optional machine code>",
        "fields": {...} | null
    }

Every non-2xx response is parsed into a typed :class:`ZebuApiError`
exception so MCP tools can re-raise it cleanly. The exception preserves
the HTTP status, the machine code, and the per-field map — that's enough
for an agent to decide whether to retry, ask the user, or escalate.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import Any, Self
from uuid import UUID

import httpx

from zebu_mcp._version import __version__
from zebu_mcp.config import ZebuMcpConfig
from zebu_mcp.schemas import (
    ActivateStrategyRequest,
    BacktestRun,
    ClaimExplorationTaskRequest,
    CreateExplorationTaskRequest,
    CreateStrategyRequest,
    CurrentPrice,
    DeactivateActivationRequest,
    ExplorationTask,
    Holding,
    Page,
    Portfolio,
    PortfolioBalance,
    PortfolioState,
    PriceHistory,
    RunBacktestRequest,
    RunNowResponse,
    Strategy,
    StrategyActivation,
    SubmitExplorationFindingsRequest,
    SupportedTickers,
)

_API_PREFIX = "/api/v1"


class ZebuApiError(Exception):
    """Raised when the Zebu API returns a non-2xx response.

    Attributes:
        status_code: HTTP status code from the upstream response (e.g.
            404, 422, 503).
        detail: Human-readable message from the ``ErrorResponse`` envelope,
            or the raw body if the response wasn't JSON.
        code: Machine-readable error code from the envelope, if present.
            Stable strings like ``ticker_not_found``,
            ``insufficient_funds`` — match on these for retry logic.
        fields: Per-field detail map. For 422 errors this is
            ``{field_name: error_message}``; for domain errors it carries
            auxiliary data (e.g. ``available`` / ``required`` /
            ``shortfall`` / ``ticker``).
        method: HTTP method of the failing request, for log context.
        url: Full URL that was called.
    """

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        code: str | None,
        fields: dict[str, str] | None,
        method: str,
        url: str,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.fields = fields
        self.method = method
        self.url = url
        super().__init__(
            f"{method} {url} -> {status_code}{f' [{code}]' if code else ''}: {detail}"
        )


class ZebuClient(AbstractAsyncContextManager["ZebuClient"]):
    """Async HTTP client for the Zebu API.

    Lifecycle is async-context-managed so the underlying ``httpx``
    connection pool is closed cleanly when the MCP server stops. The
    config is captured at construction; reconfiguration mid-process is
    not supported (and not desirable — env reload is a process restart).

    Auth strategy
    -------------

    The API key is sent in the ``X-API-Key`` header on every request.
    Phase C2 wired the backend to accept *both* ``X-API-Key`` and
    ``Authorization: ApiKey ...``; we picked ``X-API-Key`` because it's
    the simplest header for users to inspect / curl-replay (no scheme
    word) and there's no Bearer JWT contention to worry about for
    machine-to-machine traffic.
    """

    def __init__(self, config: ZebuMcpConfig) -> None:
        """Construct the client. Does NOT open the HTTP transport.

        Use ``async with ZebuClient(cfg)`` or call ``__aenter__`` to
        actually open the connection pool. This split is what lets tests
        construct a client + inject a mock transport without making a
        real HTTPS handshake.

        Args:
            config: Resolved configuration.
        """
        self._config = config
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle ---------------------------------------------------------

    async def __aenter__(self) -> Self:
        """Open the underlying httpx client.

        Returns:
            ``self``, ready for use.
        """
        self._client = httpx.AsyncClient(
            base_url=self._config.api_base_url + _API_PREFIX,
            timeout=self._config.timeout_secs,
            headers={
                "X-API-Key": self._config.api_key,
                "Accept": "application/json",
                "User-Agent": f"zebu-mcp/{__version__}",
            },
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close the underlying httpx client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # -- internals ---------------------------------------------------------

    @property
    def _http(self) -> httpx.AsyncClient:
        """Return the underlying client or raise if not entered.

        Routes through this property so every method gets the same
        helpful error message instead of a bare ``AttributeError`` if
        someone forgets the ``async with``.
        """
        if self._client is None:
            raise RuntimeError(
                "ZebuClient used before entering its async context. "
                "Wrap it in 'async with' or call __aenter__()."
            )
        return self._client

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Send a request and parse the JSON body, mapping errors.

        Args:
            method: HTTP method (uppercase).
            path: Path under ``/api/v1`` — e.g. ``/portfolios``.
            params: Query parameters (None values dropped before send).
            json: JSON body to send (typically for POST/PUT). Forwarded
                directly to httpx — pass a serialised ``dict`` rather
                than a Pydantic model. ``None`` means no body.

        Returns:
            Parsed JSON body, or ``None`` for 204 responses.

        Raises:
            ZebuApiError: On any non-2xx response.
            httpx.HTTPError: On transport-level failure (connection
                refused, timeout, etc.) — left as-is so the caller can
                tell network problems apart from API-shape problems.
        """
        # Drop None-valued params so callers can pass optional filters
        # without manually filtering — httpx would serialise None to
        # the literal string "None" which is wrong.
        cleaned_params: dict[str, Any] | None
        if params is None:
            cleaned_params = None
        else:
            cleaned_params = {k: v for k, v in params.items() if v is not None}

        response = await self._http.request(
            method=method,
            url=path,
            params=cleaned_params,
            json=json,
        )

        if response.is_success:
            # 204 No Content has no body.
            if response.status_code == 204:
                return None
            return response.json()

        # Map error responses. Try the standard envelope first; if the
        # body isn't JSON or doesn't fit the shape, fall back to the raw
        # text so we never lose information.
        detail: str
        code: str | None = None
        fields: dict[str, str] | None = None
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            raw_detail = payload.get("detail")
            detail = raw_detail if isinstance(raw_detail, str) else response.text
            raw_code = payload.get("code")
            if isinstance(raw_code, str):
                code = raw_code
            raw_fields = payload.get("fields")
            if isinstance(raw_fields, dict):
                # Pyright keeps this as dict[str, Any] without coercion;
                # cast each value through str() so the typed exception
                # field is consistent.
                fields = {str(k): str(v) for k, v in raw_fields.items()}
        else:
            detail = response.text or response.reason_phrase

        raise ZebuApiError(
            status_code=response.status_code,
            detail=detail,
            code=code,
            fields=fields,
            method=method,
            url=str(response.request.url),
        )

    # -- prices ------------------------------------------------------------

    async def list_supported_tickers(self) -> SupportedTickers:
        """``GET /prices/`` — list every ticker the platform has data for."""
        # Note the trailing slash: the FastAPI route is registered as
        # ``/prices/`` so we must keep it here to avoid a 307.
        body = await self._request_json("GET", "/prices/")
        return SupportedTickers.model_validate(body)

    async def get_current_price(self, ticker: str) -> CurrentPrice:
        """``GET /prices/{ticker}`` — last observed price."""
        body = await self._request_json("GET", f"/prices/{ticker}")
        return CurrentPrice.model_validate(body)

    async def get_price_history(
        self,
        ticker: str,
        *,
        start: str,
        end: str,
        interval: str = "1day",
    ) -> PriceHistory:
        """``GET /prices/{ticker}/history`` — historical price series.

        Args:
            ticker: Stock ticker symbol.
            start: ISO-8601 datetime or ``YYYY-MM-DD`` date.
            end: ISO-8601 datetime or ``YYYY-MM-DD`` date.
            interval: Currently only ``1day`` is supported. Sub-daily
                intervals (``1min``, ``5min``, ``15min``, ``30min``,
                ``1hour``) will be rejected by the API with HTTP 422
                until intraday data is wired in (GitHub issue #285).
        """
        body = await self._request_json(
            "GET",
            f"/prices/{ticker}/history",
            params={"start": start, "end": end, "interval": interval},
        )
        return PriceHistory.model_validate(body)

    # -- portfolios --------------------------------------------------------

    async def list_portfolios(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        include_backtest: bool = False,
    ) -> Page[Portfolio]:
        """``GET /portfolios`` — paginated list of portfolios for the auth user."""
        body = await self._request_json(
            "GET",
            "/portfolios",
            params={
                "limit": limit,
                "offset": offset,
                "include_backtest": include_backtest,
            },
        )
        return Page[Portfolio].model_validate(body)

    async def get_portfolio(self, portfolio_id: UUID) -> Portfolio:
        """``GET /portfolios/{id}`` — single portfolio."""
        body = await self._request_json("GET", f"/portfolios/{portfolio_id}")
        return Portfolio.model_validate(body)

    async def get_portfolio_balance(
        self,
        portfolio_id: UUID,
    ) -> PortfolioBalance:
        """``GET /portfolios/{id}/balance``."""
        body = await self._request_json("GET", f"/portfolios/{portfolio_id}/balance")
        return PortfolioBalance.model_validate(body)

    async def get_portfolio_holdings(
        self,
        portfolio_id: UUID,
    ) -> list[Holding]:
        """``GET /portfolios/{id}/holdings`` — list of stock holdings."""
        body = await self._request_json("GET", f"/portfolios/{portfolio_id}/holdings")
        # The route returns ``{"holdings": [...]}`` — unwrap.
        if not isinstance(body, dict) or "holdings" not in body:
            raise ZebuApiError(
                status_code=500,
                detail="Unexpected holdings response shape",
                code=None,
                fields=None,
                method="GET",
                url=f"/portfolios/{portfolio_id}/holdings",
            )
        raw_holdings = body["holdings"]
        if not isinstance(raw_holdings, list):
            raise ZebuApiError(
                status_code=500,
                detail="Unexpected holdings response shape",
                code=None,
                fields=None,
                method="GET",
                url=f"/portfolios/{portfolio_id}/holdings",
            )
        return [Holding.model_validate(h) for h in raw_holdings]

    async def get_portfolio_state(self, portfolio_id: UUID) -> PortfolioState:
        """Composite — fetch portfolio + balance + holdings in parallel.

        Mirrors the typical agent question "what's the state of this
        portfolio right now?". Three round trips because the backend
        exposes them as separate endpoints; we hide the fan-out behind
        the convenience method so MCP tools call a single thing.

        Note: not parallelised yet — three sequential awaits. Phase D
        Wave 2 can introduce ``asyncio.gather`` if latency matters in
        practice; the API serves these in the low tens of ms each.
        """
        portfolio = await self.get_portfolio(portfolio_id)
        balance = await self.get_portfolio_balance(portfolio_id)
        holdings = await self.get_portfolio_holdings(portfolio_id)
        return PortfolioState(
            portfolio=portfolio,
            balance=balance,
            holdings=holdings,
        )

    # -- strategies --------------------------------------------------------

    async def list_strategies(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Strategy]:
        """``GET /strategies`` — paginated list of strategies."""
        body = await self._request_json(
            "GET",
            "/strategies",
            params={"limit": limit, "offset": offset},
        )
        return Page[Strategy].model_validate(body)

    async def get_strategy(self, strategy_id: UUID) -> Strategy:
        """``GET /strategies/{id}``."""
        body = await self._request_json("GET", f"/strategies/{strategy_id}")
        return Strategy.model_validate(body)

    async def create_strategy(self, request: CreateStrategyRequest) -> Strategy:
        """``POST /strategies`` — create a strategy template.

        The request body matches the backend's ``CreateStrategyRequest``;
        ``parameters`` is a free-form mapping that the backend parses
        into the typed strategy-parameters dataclass via
        ``parameters_from_dict``. Invalid parameters surface as a typed
        422 ``ZebuApiError`` with per-field detail.
        """
        body = await self._request_json(
            "POST",
            "/strategies",
            json=request.model_dump(mode="json"),
        )
        return Strategy.model_validate(body)

    # -- backtests ---------------------------------------------------------

    async def list_backtests(
        self,
        *,
        strategy_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[BacktestRun]:
        """``GET /backtests`` — paginated list of backtest runs.

        The backend's list endpoint doesn't currently filter by strategy
        ID server-side (it returns all owner-scoped runs). When
        ``strategy_id`` is supplied we filter client-side so the tool
        contract is honoured today; if backend filtering is added later
        the param can be passed through transparently.
        """
        body = await self._request_json(
            "GET",
            "/backtests",
            params={"limit": limit, "offset": offset},
        )
        page = Page[BacktestRun].model_validate(body)
        if strategy_id is None:
            return page
        # Client-side filter — keep pagination metadata aligned by
        # recomputing on the filtered subset. Documents the gap clearly:
        # ``total`` is now "matching this strategy in this page", which
        # is a known imperfection we'll fix once the backend supports
        # ``?strategy_id=``.
        filtered_items = [r for r in page.items if r.strategy_id == strategy_id]
        return Page[BacktestRun](
            items=filtered_items,
            total=len(filtered_items),
            limit=page.limit,
            offset=page.offset,
            has_more=False,
        )

    async def get_backtest(self, backtest_id: UUID) -> BacktestRun:
        """``GET /backtests/{id}``."""
        body = await self._request_json("GET", f"/backtests/{backtest_id}")
        return BacktestRun.model_validate(body)

    async def run_backtest(self, request: RunBacktestRequest) -> BacktestRun:
        """``POST /backtests`` — run a backtest synchronously.

        The backend currently runs to completion in the request handler
        (see ``backtest_executor.execute``), so the returned ``status`` is
        almost always ``COMPLETED`` (or ``FAILED``) rather than ``RUNNING``.
        Tools layer on top can still poll defensively in case the backend
        switches to a background-job model.
        """
        body = await self._request_json(
            "POST",
            "/backtests",
            json=request.model_dump(mode="json"),
        )
        return BacktestRun.model_validate(body)

    # -- activations -------------------------------------------------------

    async def list_activations(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[StrategyActivation]:
        """``GET /activations`` — paginated list of activations."""
        body = await self._request_json(
            "GET",
            "/activations",
            params={"limit": limit, "offset": offset},
        )
        return Page[StrategyActivation].model_validate(body)

    async def list_active_activations(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[StrategyActivation]:
        """``GET /activations`` filtered to ACTIVE status (client-side).

        The backend doesn't expose a status filter on this list endpoint;
        we pull a page and filter. Same caveat as ``list_backtests`` —
        the ``total`` reflects matching items in the current page only.
        """
        page = await self.list_activations(limit=limit, offset=offset)
        active = [a for a in page.items if a.status == "ACTIVE"]
        return Page[StrategyActivation](
            items=active,
            total=len(active),
            limit=page.limit,
            offset=page.offset,
            has_more=False,
        )

    async def get_strategy_activation(
        self,
        strategy_id: UUID,
    ) -> StrategyActivation:
        """``GET /strategies/{id}/activation`` — the activation for a strategy.

        Returns 404 (mapped to :class:`ZebuApiError`) if no activation has
        ever been created for the strategy.
        """
        body = await self._request_json("GET", f"/strategies/{strategy_id}/activation")
        return StrategyActivation.model_validate(body)

    async def activate_strategy(
        self,
        strategy_id: UUID,
        request: ActivateStrategyRequest,
    ) -> StrategyActivation:
        """``POST /strategies/{id}/activate`` — link strategy to a portfolio."""
        body = await self._request_json(
            "POST",
            f"/strategies/{strategy_id}/activate",
            json=request.model_dump(mode="json"),
        )
        return StrategyActivation.model_validate(body)

    async def deactivate_activation(
        self,
        activation_id: UUID,
        request: DeactivateActivationRequest,
    ) -> StrategyActivation:
        """``POST /activations/{id}/deactivate`` — pause an active activation."""
        body = await self._request_json(
            "POST",
            f"/activations/{activation_id}/deactivate",
            json=request.model_dump(mode="json"),
        )
        return StrategyActivation.model_validate(body)

    async def run_activation_now(self, activation_id: UUID) -> RunNowResponse:
        """``POST /activations/{id}/run-now`` — trigger immediate execution.

        Returns the post-run activation state along with the immediate
        outcome (``succeeded``, ``trades``, ``error``). Runs synchronously
        in the backend handler, so the response carries the final state.
        """
        body = await self._request_json(
            "POST",
            f"/activations/{activation_id}/run-now",
        )
        return RunNowResponse.model_validate(body)

    # -- exploration tasks -------------------------------------------------

    async def list_exploration_tasks(
        self,
        *,
        status: str | None = None,
        scope: str = "all",
        limit: int = 20,
        offset: int = 0,
    ) -> Page[ExplorationTask]:
        """``GET /exploration-tasks`` — paginated list of tasks.

        Args:
            status: ``OPEN`` / ``IN_PROGRESS`` / ``DONE`` / ``ABANDONED``,
                or None to use the default queue view (open tasks under
                ``scope=all``).
            scope: ``all`` for the global queue, ``mine`` for tasks the
                current user created.
            limit: Page size.
            offset: Page offset.
        """
        body = await self._request_json(
            "GET",
            "/exploration-tasks",
            params={
                "status": status,
                "scope": scope,
                "limit": limit,
                "offset": offset,
            },
        )
        return Page[ExplorationTask].model_validate(body)

    async def get_exploration_task(self, task_id: UUID) -> ExplorationTask:
        """``GET /exploration-tasks/{id}``."""
        body = await self._request_json("GET", f"/exploration-tasks/{task_id}")
        return ExplorationTask.model_validate(body)

    async def create_exploration_task(
        self,
        request: CreateExplorationTaskRequest,
    ) -> ExplorationTask:
        """``POST /exploration-tasks`` — file a new task on the queue."""
        body = await self._request_json(
            "POST",
            "/exploration-tasks",
            json=request.model_dump(mode="json"),
        )
        return ExplorationTask.model_validate(body)

    async def claim_exploration_task(
        self,
        task_id: UUID,
        request: ClaimExplorationTaskRequest,
    ) -> ExplorationTask:
        """``POST /exploration-tasks/{id}/claim`` — atomically claim work.

        The backend's ``claim_atomic`` issues a single status-conditional
        UPDATE so two callers fighting for the same task can't both win.
        Returns 409 (mapped to :class:`ZebuApiError`) if the task is no
        longer OPEN; 404 if it never existed.
        """
        body = await self._request_json(
            "POST",
            f"/exploration-tasks/{task_id}/claim",
            json=request.model_dump(mode="json"),
        )
        return ExplorationTask.model_validate(body)

    async def submit_exploration_findings(
        self,
        task_id: UUID,
        request: SubmitExplorationFindingsRequest,
    ) -> ExplorationTask:
        """``POST /exploration-tasks/{id}/findings`` — submit + DONE-transition.

        Backend rejects (409) if the task is not currently IN_PROGRESS.
        """
        body = await self._request_json(
            "POST",
            f"/exploration-tasks/{task_id}/findings",
            json=request.model_dump(mode="json"),
        )
        return ExplorationTask.model_validate(body)

    async def delete_exploration_task(self, task_id: UUID) -> None:
        """``DELETE /exploration-tasks/{id}`` — owner-only abandon-and-delete.

        Note: only the *creator* can delete. A claiming agent that gives
        up cannot use this endpoint (see Wave 3 / future endpoint).
        """
        await self._request_json(
            "DELETE",
            f"/exploration-tasks/{task_id}",
        )
