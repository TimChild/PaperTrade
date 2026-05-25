"""Admin watchlist endpoints (Task #220).

Mounted under ``/admin/watchlist``. Two endpoints:

* ``POST /admin/watchlist`` — body ``{ticker: string}``. Pins the
  ticker by adding (or re-activating) its row in ``ticker_watchlist``.
  Idempotent — re-pinning an already-active ticker is a no-op and
  returns the same payload.
* ``DELETE /admin/watchlist/{ticker}`` — unpins by marking the row
  inactive. Returns 204 on success, 404 when the ticker isn't
  currently in the watchlist (so the operator can tell whether their
  action actually did anything).

Both endpoints are admin-gated via :data:`AdminUserDep`. Each action
logs a structured ``admin_watchlist_added`` / ``admin_watchlist_removed``
event for the audit trail.

Pin is *additive*: it does NOT change the scheduler's union semantic
(``watchlist_active ∪ recently_traded_30d``). Pinning ensures a ticker
stays in the refresh set after the 30-day trade window lapses;
unpinning does NOT remove a recently-traded ticker from the refresh
set. See ``agent_docs/tasks/220_watchlist_admin_surface.md`` for the
design notes.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from zebu.adapters.inbound.api.dependencies import AdminUserDep, TickerValidatorDep
from zebu.adapters.outbound.repositories.watchlist_manager import WatchlistManager
from zebu.application.exceptions import MarketDataUnavailableError
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/admin/watchlist", tags=["admin-watchlist"])

logger = structlog.get_logger(__name__)


# Single fixed priority for operator-pinned tickers. The watchlist's
# ``priority`` column exists in the schema but ``refresh_active_stocks``
# doesn't consult it yet — until it does, surfacing the knob would just
# be friction. See Task #220 design decision 2.
_PINNED_PRIORITY: int = 100


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class PinTickerRequest(BaseModel):
    """Request body for ``POST /admin/watchlist``.

    Only the ticker is configurable from the UI — priority is server-
    fixed (see :data:`_PINNED_PRIORITY`). ``extra="forbid"`` keeps the
    contract loud: a client that sends ``priority`` (or any other
    field) gets a 422 rather than a silently-ignored value.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(
        description="Stock ticker symbol to pin (uppercase recommended).",
    )


class PinTickerResponse(BaseModel):
    """Response body for ``POST /admin/watchlist``."""

    ticker: str = Field(description="Stock ticker symbol that was pinned.")
    is_watchlisted: bool = Field(
        description=(
            "Always ``True`` on a successful pin. Surfaced explicitly so "
            "the client can stamp the row without an extra GET."
        ),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PinTickerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_watchlist_pin(
    payload: PinTickerRequest,
    admin_user_id: AdminUserDep,
    session: SessionDep,
    validator: TickerValidatorDep,
) -> PinTickerResponse:
    """Pin a ticker to the watchlist.

    Adds (or re-activates) a row in ``ticker_watchlist``. The operation
    is idempotent — a second POST for the same ticker returns the same
    ``201`` payload without raising and without duplicating the row.
    ``WatchlistManager.add_ticker`` already handles the "row exists,
    flip ``is_active`` back on" path, so we just call it and trust the
    invariant.

    Before persisting, the ticker is validated against the market-data
    provider (``GLOBAL_QUOTE`` on Alpha Vantage).  Unrecognised symbols
    return 422; provider failures (rate-limit, network) return 500 so
    the operator gets a clear signal to retry rather than inferring
    their ticker was rejected.

    Auth: Clerk admin only.

    Returns:
        :class:`PinTickerResponse` with ``ticker`` and
        ``is_watchlisted=True``.

    Raises:
        HTTPException 400: On ticker validation errors (the domain
            raises :class:`InvalidTickerError`, mapped via the
            registered exception handler).
        HTTPException 422: When the ticker is not recognised by the
            market-data provider (empty ``Global Quote`` from AV).
        HTTPException 500: When the market-data provider is temporarily
            unreachable (rate-limit hit, network error) and we cannot
            confirm whether the ticker is valid.
    """
    # Normalise through the value object so invalid input surfaces as
    # the standard InvalidTickerError -> 400 via the registered handler.
    ticker = Ticker(payload.ticker)

    try:
        recognised = await validator.is_recognised(ticker)
    except MarketDataUnavailableError as exc:
        # Provider is temporarily unreachable — we cannot validate. Raise
        # 500 rather than 422 so the operator can distinguish "provider
        # down" from "ticker doesn't exist".
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Could not validate ticker {ticker.symbol!r}: "
                f"market-data provider is temporarily unavailable. "
                f"Details: {exc}"
            ),
        ) from exc

    if not recognised:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Ticker {ticker.symbol!r} is not recognised by the "
                "market-data provider."
            ),
        )

    manager = WatchlistManager(session)
    await manager.add_ticker(ticker, priority=_PINNED_PRIORITY)

    logger.info(
        "admin_watchlist_added",
        admin_user_id=str(admin_user_id),
        ticker=ticker.symbol,
    )

    return PinTickerResponse(ticker=ticker.symbol, is_watchlisted=True)


@router.delete(
    "/{ticker}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_watchlist_unpin(
    ticker: str,
    admin_user_id: AdminUserDep,
    session: SessionDep,
) -> None:
    """Unpin a ticker from the watchlist.

    Soft-deletes the row (sets ``is_active=False``) via
    :meth:`WatchlistManager.remove_ticker` so history is preserved.

    A ``DELETE`` on a ticker that isn't currently active in the
    watchlist returns 404 — chosen deliberately so the operator gets a
    visible signal that the action did nothing (vs. silent 204 on a
    no-op). The check is done by reading the watchlist set before the
    manager call; the manager's underlying UPDATE is itself idempotent
    so the read-then-write race is benign (a concurrent unpin doesn't
    leave the DB in a bad state, just returns 404 to the second caller).

    Auth: Clerk admin only.

    Raises:
        HTTPException 400: On ticker validation errors (the domain
            raises :class:`InvalidTickerError`, mapped via the
            registered exception handler).
        HTTPException 404: When the ticker is not currently in the
            watchlist (so the operator knows their action was a no-op).
    """
    # Normalise through the value object so invalid input surfaces as
    # the standard InvalidTickerError -> 400 via the registered handler.
    ticker_vo = Ticker(ticker)

    manager = WatchlistManager(session)
    active_tickers = await manager.get_all_active_tickers()
    if ticker_vo not in active_tickers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {ticker_vo.symbol} is not in the watchlist.",
        )

    await manager.remove_ticker(ticker_vo)

    logger.info(
        "admin_watchlist_removed",
        admin_user_id=str(admin_user_id),
        ticker=ticker_vo.symbol,
    )

    # FastAPI returns 204 No Content when the response model is None.
    return None
