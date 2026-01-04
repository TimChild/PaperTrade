"""Portfolio API routes.

Provides REST endpoints for portfolio operations:
- Create portfolio
- List user's portfolios
- Get portfolio details
- Deposit/withdraw cash
- Execute trades
- Query balance, holdings, value
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from papertrade.adapters.inbound.api.dependencies import (
    CurrentUserDep,
    MarketDataDep,
    PortfolioRepositoryDep,
    TransactionRepositoryDep,
)
from papertrade.application.commands.buy_stock import BuyStockCommand, BuyStockHandler
from papertrade.application.commands.create_portfolio import (
    CreatePortfolioCommand,
    CreatePortfolioHandler,
)
from papertrade.application.commands.deposit_cash import (
    DepositCashCommand,
    DepositCashHandler,
)
from papertrade.application.commands.sell_stock import (
    SellStockCommand,
    SellStockHandler,
)
from papertrade.application.commands.withdraw_cash import (
    WithdrawCashCommand,
    WithdrawCashHandler,
)
from papertrade.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from papertrade.application.queries.get_portfolio import (
    GetPortfolioHandler,
    GetPortfolioQuery,
)
from papertrade.application.queries.get_portfolio_balance import (
    GetPortfolioBalanceHandler,
    GetPortfolioBalanceQuery,
)
from papertrade.application.queries.get_portfolio_holdings import (
    GetPortfolioHoldingsHandler,
    GetPortfolioHoldingsQuery,
)
from papertrade.domain.exceptions import InvalidPortfolioError
from papertrade.domain.value_objects.ticker import Ticker

router = APIRouter(prefix="/portfolios", tags=["portfolios"])

# Default currency for Phase 1 (hardcoded until multi-currency support added)
DEFAULT_CURRENCY = "USD"


# Request/Response Models


class CreatePortfolioRequest(BaseModel):
    """Request to create a new portfolio."""

    name: str = Field(..., min_length=1, max_length=100)
    initial_deposit: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class CreatePortfolioResponse(BaseModel):
    """Response after creating a portfolio."""

    portfolio_id: UUID
    transaction_id: UUID


class PortfolioResponse(BaseModel):
    """Portfolio details response."""

    id: UUID
    user_id: UUID
    name: str
    created_at: str  # ISO 8601 format


class DepositRequest(BaseModel):
    """Request to deposit cash."""

    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class WithdrawRequest(BaseModel):
    """Request to withdraw cash."""

    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class TradeRequest(BaseModel):
    """Request to execute a trade."""

    action: str = Field(..., pattern="^(BUY|SELL)$")
    ticker: str = Field(..., min_length=1, max_length=5)
    quantity: Decimal = Field(..., gt=0, decimal_places=4)


class TransactionResponse(BaseModel):
    """Response after a transaction."""

    transaction_id: UUID


class BalanceResponse(BaseModel):
    """Cash balance response."""

    amount: str
    currency: str
    as_of: str  # ISO 8601 timestamp


class HoldingResponse(BaseModel):
    """Stock holding response."""

    ticker: str
    quantity: str
    cost_basis: str
    average_cost_per_share: str | None


class HoldingsResponse(BaseModel):
    """List of holdings response."""

    holdings: list[HoldingResponse]


# Routes


@router.post(
    "",
    response_model=CreatePortfolioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio(
    request: CreatePortfolioRequest,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
) -> CreatePortfolioResponse:
    """Create a new portfolio with initial deposit.

    Creates a portfolio and an initial DEPOSIT transaction.
    """
    command = CreatePortfolioCommand(
        user_id=current_user,
        name=request.name,
        initial_deposit_amount=request.initial_deposit,
        initial_deposit_currency=request.currency,
    )

    handler = CreatePortfolioHandler(portfolio_repo, transaction_repo)
    result = await handler.execute(command)

    return CreatePortfolioResponse(
        portfolio_id=result.portfolio_id,
        transaction_id=result.transaction_id,
    )


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
) -> list[PortfolioResponse]:
    """Get all portfolios for the current user."""
    portfolios = await portfolio_repo.get_by_user(current_user)

    return [
        PortfolioResponse(
            id=p.id,
            user_id=p.user_id,
            name=p.name,
            created_at=p.created_at.isoformat(),
        )
        for p in portfolios
    ]


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: UUID,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
) -> PortfolioResponse:
    """Get portfolio details by ID."""
    query = GetPortfolioQuery(portfolio_id=portfolio_id)
    handler = GetPortfolioHandler(portfolio_repo)

    try:
        result = await handler.execute(query)
        portfolio_dto = result.portfolio
    except InvalidPortfolioError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio not found: {portfolio_id}",
        ) from None

    # Verify user owns this portfolio
    if portfolio_dto.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this portfolio",
        )

    return PortfolioResponse(
        id=portfolio_dto.id,
        user_id=portfolio_dto.user_id,
        name=portfolio_dto.name,
        created_at=portfolio_dto.created_at.isoformat(),
    )


@router.post(
    "/{portfolio_id}/deposit",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def deposit_cash(
    portfolio_id: UUID,
    request: DepositRequest,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
) -> TransactionResponse:
    """Deposit cash into a portfolio."""
    # Verify user owns this portfolio
    await _verify_portfolio_ownership(portfolio_id, current_user, portfolio_repo)

    command = DepositCashCommand(
        portfolio_id=portfolio_id,
        amount=request.amount,
        currency=request.currency,
    )

    handler = DepositCashHandler(portfolio_repo, transaction_repo)
    result = await handler.execute(command)

    return TransactionResponse(transaction_id=result.transaction_id)


@router.post(
    "/{portfolio_id}/withdraw",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def withdraw_cash(
    portfolio_id: UUID,
    request: WithdrawRequest,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
) -> TransactionResponse:
    """Withdraw cash from a portfolio."""
    # Verify user owns this portfolio
    await _verify_portfolio_ownership(portfolio_id, current_user, portfolio_repo)

    command = WithdrawCashCommand(
        portfolio_id=portfolio_id,
        amount=request.amount,
        currency=request.currency,
    )

    handler = WithdrawCashHandler(portfolio_repo, transaction_repo)
    result = await handler.execute(command)

    return TransactionResponse(transaction_id=result.transaction_id)


@router.post(
    "/{portfolio_id}/trades",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_trade(
    portfolio_id: UUID,
    request: TradeRequest,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
    market_data: MarketDataDep,
) -> TransactionResponse:
    """Execute a buy or sell trade.

    Fetches the current market price automatically and executes the trade
    at that price. This prevents price manipulation and ensures trades
    execute at real market prices.

    Raises:
        HTTPException: 404 if ticker not found in market data
        HTTPException: 503 if market data service is unavailable
    """
    # Log the trade request for debugging (especially useful in CI)
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Trade request received: portfolio_id={portfolio_id}, "
        f"action={request.action}, ticker={request.ticker}, quantity={request.quantity}"
    )

    # Verify user owns this portfolio
    await _verify_portfolio_ownership(portfolio_id, current_user, portfolio_repo)

    # Fetch current market price
    ticker = Ticker(request.ticker)

    try:
        price_point = await market_data.get_current_price(ticker)
    except TickerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker not found: {request.ticker}",
        ) from None
    except MarketDataUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data unavailable: {str(e)}",
        ) from None

    if request.action == "BUY":
        command = BuyStockCommand(
            portfolio_id=portfolio_id,
            ticker_symbol=request.ticker,
            quantity_shares=request.quantity,
            price_per_share_amount=price_point.price.amount,
            price_per_share_currency=price_point.price.currency,
        )
        handler = BuyStockHandler(portfolio_repo, transaction_repo)
        result = await handler.execute(command)
    else:  # SELL
        command = SellStockCommand(
            portfolio_id=portfolio_id,
            ticker_symbol=request.ticker,
            quantity_shares=request.quantity,
            price_per_share_amount=price_point.price.amount,
            price_per_share_currency=price_point.price.currency,
        )
        handler = SellStockHandler(portfolio_repo, transaction_repo)
        result = await handler.execute(command)

    return TransactionResponse(transaction_id=result.transaction_id)


@router.get("/{portfolio_id}/balance", response_model=BalanceResponse)
async def get_balance(
    portfolio_id: UUID,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
    market_data: MarketDataDep,
) -> BalanceResponse:
    """Get current cash balance for a portfolio."""
    # Verify user owns this portfolio
    await _verify_portfolio_ownership(portfolio_id, current_user, portfolio_repo)

    query = GetPortfolioBalanceQuery(portfolio_id=portfolio_id)
    handler = GetPortfolioBalanceHandler(portfolio_repo, transaction_repo, market_data)
    result = await handler.execute(query)

    return BalanceResponse(
        amount=str(result.cash_balance.amount),
        currency=result.cash_balance.currency,
        as_of=result.as_of.isoformat(),
    )


@router.get("/{portfolio_id}/holdings", response_model=HoldingsResponse)
async def get_holdings(
    portfolio_id: UUID,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
    market_data: MarketDataDep,
) -> HoldingsResponse:
    """Get current stock holdings for a portfolio."""
    # Verify user owns this portfolio
    await _verify_portfolio_ownership(portfolio_id, current_user, portfolio_repo)

    query = GetPortfolioHoldingsQuery(portfolio_id=portfolio_id)
    handler = GetPortfolioHoldingsHandler(portfolio_repo, transaction_repo, market_data)
    result = await handler.execute(query)

    holdings = [
        HoldingResponse(
            ticker=h.ticker_symbol,
            quantity=f"{h.quantity_shares:.4f}",
            cost_basis=f"{h.cost_basis_amount:.2f}",
            average_cost_per_share=f"{h.average_cost_per_share_amount:.2f}"
            if h.average_cost_per_share_amount is not None
            else None,
        )
        for h in result.holdings
    ]

    return HoldingsResponse(holdings=holdings)


# Helper functions


async def _verify_portfolio_ownership(
    portfolio_id: UUID,
    user_id: UUID,
    portfolio_repo: PortfolioRepositoryDep,
) -> None:
    """Verify that a user owns a portfolio.

    Raises:
        HTTPException: 404 if portfolio not found, 403 if user doesn't own it
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Verifying portfolio ownership: portfolio_id={portfolio_id}, user_id={user_id}"
    )

    portfolio = await portfolio_repo.get(portfolio_id)

    if portfolio is None:
        logger.warning(f"Portfolio not found: {portfolio_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio not found: {portfolio_id}",
        )

    if portfolio.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this portfolio",
        )
