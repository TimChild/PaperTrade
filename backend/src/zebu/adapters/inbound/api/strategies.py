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

from zebu.adapters.inbound.api.dependencies import CurrentUserDep
from zebu.adapters.outbound.database.strategy_repository import (
    SQLModelStrategyRepository,
)
from zebu.domain.entities.strategy import Strategy
from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/strategies", tags=["strategies"])


# Request/Response Models


class CreateStrategyRequest(BaseModel):
    """Request to create a new trading strategy."""

    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(
        ...,
        description="Algorithm type: BUY_AND_HOLD, DOLLAR_COST_AVERAGING, "
        "MOVING_AVERAGE_CROSSOVER",
    )
    tickers: list[str] = Field(..., min_length=1, max_length=10)
    parameters: dict[str, Any] = Field(default_factory=dict)


class StrategyResponse(BaseModel):
    """Strategy details response."""

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
        parameters=strategy.parameters,
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

    # Validate strategy-specific parameters
    params = request.parameters
    if strategy_type == StrategyType.BUY_AND_HOLD:
        allocation = params.get("allocation")
        if not isinstance(allocation, dict) or not allocation:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="BUY_AND_HOLD requires 'allocation' dict parameter",
            )
        total = sum(float(v) for v in allocation.values())
        if abs(total - 1.0) > 0.001:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"BUY_AND_HOLD allocation values must sum to 1.0 (got {total:.4f})"
                ),
            )

    elif strategy_type == StrategyType.DOLLAR_COST_AVERAGING:
        frequency_days = params.get("frequency_days")
        amount_per_period = params.get("amount_per_period")
        allocation = params.get("allocation")
        if not isinstance(frequency_days, int) or not (1 <= frequency_days <= 365):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "DOLLAR_COST_AVERAGING 'frequency_days' must be an integer"
                    " between 1 and 365"
                ),
            )
        try:
            apd = float(amount_per_period) if amount_per_period is not None else 0.0
        except (TypeError, ValueError):
            apd = 0.0
        if amount_per_period is None or apd <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="DOLLAR_COST_AVERAGING 'amount_per_period' must be > 0",
            )
        if not isinstance(allocation, dict) or not allocation:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="DOLLAR_COST_AVERAGING requires 'allocation' dict parameter",
            )
        total = sum(float(v) for v in allocation.values())
        if abs(total - 1.0) > 0.001:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"DOLLAR_COST_AVERAGING allocation values must sum to 1.0"
                    f" (got {total:.4f})"
                ),
            )

    elif strategy_type == StrategyType.MOVING_AVERAGE_CROSSOVER:
        fast_window = params.get("fast_window")
        slow_window = params.get("slow_window")
        invest_fraction = params.get("invest_fraction")
        if not isinstance(fast_window, int) or not (2 <= fast_window <= 200):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "MOVING_AVERAGE_CROSSOVER 'fast_window' must be an integer"
                    " between 2 and 200"
                ),
            )
        if not isinstance(slow_window, int) or not (2 <= slow_window <= 200):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "MOVING_AVERAGE_CROSSOVER 'slow_window' must be an integer"
                    " between 2 and 200"
                ),
            )
        if fast_window >= slow_window:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "MOVING_AVERAGE_CROSSOVER 'fast_window' must be less"
                    " than 'slow_window'"
                ),
            )
        try:
            inf = float(invest_fraction) if invest_fraction is not None else 0.0
        except (TypeError, ValueError):
            inf = 0.0
        if invest_fraction is None or not (0 < inf <= 1.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "MOVING_AVERAGE_CROSSOVER 'invest_fraction' must be > 0 and <= 1.0"
                ),
            )

    try:
        strategy = Strategy(
            id=uuid4(),
            user_id=current_user,
            name=request.name,
            strategy_type=strategy_type,
            tickers=request.tickers,
            parameters=request.parameters,
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
