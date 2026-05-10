"""Strategy activation API routes.

Phase C1.3 — REST endpoints for live strategy execution:

* ``POST /strategies/{id}/activate`` — link a strategy to a paper-trading
  portfolio for daily live execution.
* ``POST /activations/{id}/deactivate`` — pause an active activation.
* ``GET  /strategies/{id}/activation`` — fetch the activation linked to
  a strategy (404 if none).
* ``GET  /activations`` — paginated list of the user's activations.
* ``POST /activations/{id}/run-now`` — trigger immediate execution
  outside the cadence. **Accepts both Clerk Bearer JWT and API-key
  auth** through ``CurrentUserDep`` (Phase C2 unified auth).

Ownership rule: every activation belongs to a single user, the same
user that owns both the strategy and the portfolio. Cross-user
references are caught at activation time (``activate``) and at every
read/mutation by comparing the activation's ``user_id`` against the
authenticated user.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from zebu.adapters.inbound.api.dependencies import (
    ActiveApiKeyIdDep,
    CurrentUserDep,
    MarketDataDep,
)
from zebu.adapters.inbound.api.schemas import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from zebu.adapters.inbound.api.schemas.pagination import build_paginated_response
from zebu.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from zebu.adapters.outbound.database.strategy_activation_repository import (
    SQLModelStrategyActivationRepository,
)
from zebu.adapters.outbound.database.strategy_repository import (
    SQLModelStrategyRepository,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from zebu.application.services.strategy_execution_service import (
    StrategyExecutionService,
)
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.infrastructure.database import SessionDep

# Two routers — one mounted under ``/strategies`` (existing prefix) and
# one under ``/activations`` — keep URL semantics consistent with the
# spec (`/strategies/{id}/activation` is "the" activation for a strategy
# while `/activations/{id}/...` operates on the activation directly).

strategies_router = APIRouter(prefix="/strategies", tags=["strategy-activations"])
activations_router = APIRouter(prefix="/activations", tags=["strategy-activations"])

# Module-level structlog logger. Picks up the actor identity bound by
# get_current_user (auth_method, clerk_user_id, api_key_id, api_key_label)
# automatically via structlog.contextvars — Phase H5.
logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ActivateStrategyRequest(BaseModel):
    """Request body for ``POST /strategies/{id}/activate``."""

    portfolio_id: UUID
    frequency: str = Field(
        default=ActivationFrequency.DAILY_MARKET_CLOSE.value,
        description=(
            "Execution cadence. Phase C1 ships only DAILY_MARKET_CLOSE; "
            "the field is forward-compatible for future cadences."
        ),
    )


class DeactivateRequest(BaseModel):
    """Request body for ``POST /activations/{id}/deactivate``.

    The ``reason`` is captured on the entity's ``last_error`` field for
    visibility in the user UI — it's not an error per se but it's the
    same auxiliary text channel.
    """

    reason: str | None = Field(default=None, max_length=500)


class StrategyActivationResponse(BaseModel):
    """Wire shape for a ``StrategyActivation``."""

    id: UUID
    user_id: UUID
    strategy_id: UUID
    portfolio_id: UUID
    status: str
    frequency: str
    last_executed_at: str | None
    last_error: str | None
    created_at: str
    updated_at: str


class RunNowResponse(BaseModel):
    """Wire shape for ``POST /activations/{id}/run-now``.

    Carries the immediate execution outcome so the API caller can show
    "ran X, executed Y trades" without polling. The full activation
    state lands in ``activation`` (which reflects post-run mutation —
    e.g. ``status=ERROR`` if the run failed).
    """

    activation: StrategyActivationResponse
    succeeded: bool
    trades: int
    error: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(activation: StrategyActivation) -> StrategyActivationResponse:
    """Convert a domain ``StrategyActivation`` to its wire response."""
    return StrategyActivationResponse(
        id=activation.id,
        user_id=activation.user_id,
        strategy_id=activation.strategy_id,
        portfolio_id=activation.portfolio_id,
        status=activation.status.value,
        frequency=activation.frequency.value,
        last_executed_at=(
            activation.last_executed_at.isoformat()
            if activation.last_executed_at is not None
            else None
        ),
        last_error=activation.last_error,
        created_at=activation.created_at.isoformat(),
        updated_at=activation.updated_at.isoformat(),
    )


def _parse_frequency(raw: str) -> ActivationFrequency:
    """Parse the ``frequency`` request field, returning a 422 on bad input."""
    try:
        return ActivationFrequency(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid frequency: '{raw}'. Must be one of: "
                f"{', '.join(f.value for f in ActivationFrequency)}"
            ),
        ) from exc


# ---------------------------------------------------------------------------
# Routes — under /strategies
# ---------------------------------------------------------------------------


@strategies_router.post(
    "/{strategy_id}/activate",
    response_model=StrategyActivationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def activate_strategy(
    strategy_id: UUID,
    request: ActivateStrategyRequest,
    current_user: CurrentUserDep,
    api_key_id: ActiveApiKeyIdDep,
    session: SessionDep,
) -> StrategyActivationResponse:
    """Activate a strategy for live execution against a portfolio.

    Validates that:

    * The caller owns the strategy.
    * The caller owns the portfolio.
    * The strategy doesn't already have an activation (one activation
      per strategy at a time — pause/restart cycles are an explicit
      future feature; for now a strategy is activated, then deactivated,
      then re-activated as a *new* activation if needed).

    The activation starts in ``ACTIVE`` status and is picked up by the
    next scheduler cycle.
    """
    frequency = _parse_frequency(request.frequency)

    strategy_repo = SQLModelStrategyRepository(session)
    portfolio_repo = SQLModelPortfolioRepository(session)
    activation_repo = SQLModelStrategyActivationRepository(session)

    strategy = await strategy_repo.get(strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy not found: {strategy_id}",
        )
    if strategy.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to activate this strategy",
        )

    portfolio = await portfolio_repo.get(request.portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio not found: {request.portfolio_id}",
        )
    if portfolio.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to use this portfolio",
        )

    existing = await activation_repo.get_by_strategy(strategy_id)
    if existing is not None and existing.status is ActivationStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Strategy {strategy_id} already has an active activation. "
                "Deactivate it first to re-activate against a different "
                "portfolio."
            ),
        )

    now = datetime.now(UTC)
    activation = StrategyActivation(
        id=uuid4(),
        user_id=current_user,
        strategy_id=strategy_id,
        portfolio_id=request.portfolio_id,
        status=ActivationStatus.ACTIVE,
        frequency=frequency,
        created_at=now,
        updated_at=now,
    )
    # Phase H2: stamp the originating credential so the activity feed can
    # surface the API-key label for activation_created rows.
    await activation_repo.save(activation, api_key_id=api_key_id)
    logger.info(
        "Strategy activated",
        activation_id=str(activation.id),
        strategy_id=str(strategy_id),
        portfolio_id=str(request.portfolio_id),
        frequency=frequency.value,
    )
    return _to_response(activation)


@strategies_router.get(
    "/{strategy_id}/activation",
    response_model=StrategyActivationResponse,
)
async def get_strategy_activation(
    strategy_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> StrategyActivationResponse:
    """Fetch the activation linked to a strategy.

    Returns 404 if no activation has ever been created. Returns 403 if
    an activation exists but belongs to a different user (defensive —
    the strategy ownership check should usually catch this first).
    """
    strategy_repo = SQLModelStrategyRepository(session)
    activation_repo = SQLModelStrategyActivationRepository(session)

    strategy = await strategy_repo.get(strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy not found: {strategy_id}",
        )
    if strategy.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this strategy",
        )

    activation = await activation_repo.get_by_strategy(strategy_id)
    if activation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No activation found for strategy: {strategy_id}",
        )
    if activation.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this activation",
        )
    return _to_response(activation)


# ---------------------------------------------------------------------------
# Routes — under /activations
# ---------------------------------------------------------------------------


@activations_router.get(
    "",
    response_model=PaginatedResponse[StrategyActivationResponse],
)
async def list_activations(
    current_user: CurrentUserDep,
    session: SessionDep,
    limit: int = Query(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Maximum number of activations to return (1-100, default 20).",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of activations to skip for pagination (default 0).",
    ),
) -> PaginatedResponse[StrategyActivationResponse]:
    """List the current user's activations, paginated.

    Returns activations in any status — clients can filter for ACTIVE
    on the wire if they only want the live-running set.
    """
    repo = SQLModelStrategyActivationRepository(session)
    # Repo returns owner-scoped activations in creation order. Page in
    # Python — activation volume per user is small (one per strategy);
    # SQL push-down is not worth the per-route complexity yet.
    activations = await repo.list_for_user(current_user)
    total = len(activations)
    page = activations[offset : offset + limit]
    items = [_to_response(a) for a in page]
    return build_paginated_response(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@activations_router.post(
    "/{activation_id}/deactivate",
    response_model=StrategyActivationResponse,
)
async def deactivate_activation(
    activation_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    body: DeactivateRequest | None = None,
) -> StrategyActivationResponse:
    """Pause an active activation.

    Sets ``status=PAUSED`` so the scheduler skips it on subsequent
    cycles. ``PAUSED`` is the user-driven "stop running this for now"
    semantic; ``STOPPED`` is reserved for terminal cases (e.g. linked
    portfolio deleted) and is not exposed via this endpoint.

    The optional ``reason`` is stored on ``last_error`` so the UI can
    surface "paused because: <reason>". This conflates "actual error"
    with "user-supplied note" but matches the existing entity shape;
    a dedicated field is a deferred refactor.
    """
    repo = SQLModelStrategyActivationRepository(session)
    activation = await repo.get(activation_id)
    if activation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activation not found: {activation_id}",
        )
    if activation.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to deactivate this activation",
        )

    reason = body.reason if body and body.reason is not None else None
    paused = StrategyActivation(
        id=activation.id,
        user_id=activation.user_id,
        strategy_id=activation.strategy_id,
        portfolio_id=activation.portfolio_id,
        status=ActivationStatus.PAUSED,
        frequency=activation.frequency,
        created_at=activation.created_at,
        updated_at=datetime.now(UTC),
        last_executed_at=activation.last_executed_at,
        last_error=reason,
    )
    await repo.save(paused)
    logger.info(
        "Strategy activation deactivated",
        activation_id=str(activation_id),
        reason=reason,
    )
    return _to_response(paused)


@activations_router.post(
    "/{activation_id}/run-now",
    response_model=RunNowResponse,
)
async def run_activation_now(
    activation_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    market_data: MarketDataDep,
) -> RunNowResponse:
    """Trigger immediate execution of an activation outside the cadence.

    Phase C3 entry point — accepts BOTH Clerk Bearer JWT (humans) and
    API-key auth (agents) through the unified ``CurrentUserDep`` from
    Phase C2. The endpoint is intentionally identical for both paths:
    an agent that owns the activation can run it the same way a human
    can.

    Behaviour:

    * Runs synchronously in the request handler. Live strategies do at
      most one ``generate_signals`` + a handful of trades, so a few
      hundred ms is acceptable. Backgrounding is a future-when-needed
      improvement.
    * Returns the post-run activation state (status may have flipped
      to ERROR if the run blew up).
    * Does *not* gate on the activation's status — a PAUSED activation
      can be ad-hoc run; the cron-driven scheduler is the only thing
      that respects status.
    """
    activation_repo = SQLModelStrategyActivationRepository(session)
    activation = await activation_repo.get(activation_id)
    if activation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activation not found: {activation_id}",
        )
    if activation.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to run this activation",
        )

    # Phase H5: log the run-now request with actor identity. The
    # api_key_label (when present) is auto-merged from contextvars
    # bound by get_current_user. This is the canonical "agent ran a
    # live strategy" signal for the activity feed (Phase H2).
    logger.info(
        "Strategy activation run-now requested",
        activation_id=str(activation_id),
        strategy_id=str(activation.strategy_id),
        portfolio_id=str(activation.portfolio_id),
    )

    strategy_repo = SQLModelStrategyRepository(session)
    portfolio_repo = SQLModelPortfolioRepository(session)
    transaction_repo = SQLModelTransactionRepository(session)

    service = StrategyExecutionService(
        activation_repo=activation_repo,
        strategy_repo=strategy_repo,
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        market_data=market_data,
    )
    result = await service.execute_one(activation_id)

    logger.info(
        "Strategy activation run-now completed",
        activation_id=str(activation_id),
        succeeded=result["succeeded"],
        trades=result["trades"],
        error=result["error"],
    )

    # Reload — the service mutated the activation (status / last_error /
    # last_executed_at). Returning the *fresh* state gives the client a
    # single source of truth.
    refreshed = await activation_repo.get(activation_id)
    # The service guarantees the row still exists post-run (it wrote to
    # it). A None here would indicate concurrent deletion, which is so
    # narrow we 500 explicitly via assert.
    assert refreshed is not None, (
        f"Activation {activation_id} was deleted mid-execution"
    )
    return RunNowResponse(
        activation=_to_response(refreshed),
        succeeded=result["succeeded"],
        trades=result["trades"],
        error=result["error"],
    )
