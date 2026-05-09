"""Strategy API routes.

Provides REST endpoints for trading strategy management:
- Create strategy template
- List user's strategies
- Get strategy details
- Delete strategy
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from zebu.adapters.inbound.api.dependencies import CurrentUserDep, MarketDataDep
from zebu.adapters.outbound.database.strategy_repository import (
    SQLModelStrategyRepository,
)
from zebu.domain.entities.strategy import Strategy
from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.strategy_parameters import parameters_from_dict
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/strategies", tags=["strategies"])


# Request/Response Models


class CreateStrategyRequest(BaseModel):
    """Request to create a new trading strategy.

    The ``parameters`` shape varies by ``strategy_type`` and is validated
    after parsing — see
    :mod:`zebu.domain.value_objects.strategy_parameters` for the per-type
    contract.
    """

    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(
        ...,
        description="Algorithm type: BUY_AND_HOLD, DOLLAR_COST_AVERAGING, "
        "MOVING_AVERAGE_CROSSOVER",
    )
    tickers: list[str] = Field(..., min_length=1, max_length=10)
    parameters: dict[str, Any] = Field(default_factory=dict)


class StrategyResponse(BaseModel):
    """Strategy details response.

    Note: ``parameters`` is a JSON-serialized representation of the typed
    domain parameters. The wire shape is unchanged from the pre-typing
    refactor — clients see the same fields they always have.
    """

    id: UUID
    user_id: UUID
    name: str
    strategy_type: str
    tickers: list[str]
    parameters: dict[str, Any]
    created_at: str


def _to_strategy_response(strategy: Strategy) -> StrategyResponse:
    return StrategyResponse(
        id=strategy.id,
        user_id=strategy.user_id,
        name=strategy.name,
        strategy_type=strategy.strategy_type.value,
        tickers=strategy.tickers,
        parameters=dict(strategy.parameters.to_dict()),
        created_at=strategy.created_at.isoformat(),
    )


# Routes


@router.post(
    "",
    response_model=StrategyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_strategy(
    request: CreateStrategyRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
    market_data: MarketDataDep,
) -> StrategyResponse:
    """Create a new trading strategy template."""
    try:
        strategy_type = StrategyType(request.strategy_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid strategy_type: '{request.strategy_type}'. "
            f"Must be one of: "
            f"{', '.join(t.value for t in StrategyType)}",
        ) from None

    # Parse + validate strategy-specific parameters via the typed dataclass.
    # Single source of truth: domain rules raise InvalidStrategyError, mapped
    # to 422 below.
    try:
        parameters = parameters_from_dict(strategy_type, request.parameters)
    except InvalidStrategyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Validate tickers against supported tickers
    supported = {t.symbol for t in await market_data.get_supported_tickers()}
    unsupported = [t for t in request.tickers if t not in supported]
    if unsupported:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported tickers: {', '.join(unsupported)}",
        )

    try:
        strategy = Strategy(
            id=uuid4(),
            user_id=current_user,
            name=request.name,
            strategy_type=strategy_type,
            tickers=request.tickers,
            parameters=parameters,
            created_at=datetime.now(UTC),
        )
    except InvalidStrategyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    repo = SQLModelStrategyRepository(session)
    await repo.save(strategy)

    return _to_strategy_response(strategy)


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[StrategyResponse]:
    """List all strategies for the current user."""
    repo = SQLModelStrategyRepository(session)
    strategies = await repo.get_by_user(current_user)
    return [_to_strategy_response(s) for s in strategies]


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> StrategyResponse:
    """Get a strategy by ID."""
    repo = SQLModelStrategyRepository(session)
    strategy = await repo.get(strategy_id)

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

    return _to_strategy_response(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> None:
    """Delete a strategy template.

    Note: Deleting a strategy does not delete associated backtest runs.
    Backtest runs hold a snapshot of the strategy at the time of execution.
    """
    repo = SQLModelStrategyRepository(session)
    strategy = await repo.get(strategy_id)

    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy not found: {strategy_id}",
        )

    if strategy.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this strategy",
        )

    await repo.delete(strategy_id)
