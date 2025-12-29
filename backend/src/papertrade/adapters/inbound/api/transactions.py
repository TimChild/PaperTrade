"""Transaction API routes.

Provides REST endpoints for transaction history queries.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from papertrade.adapters.inbound.api.dependencies import (
    CurrentUserDep,
    PortfolioRepositoryDep,
    TransactionRepositoryDep,
)
from papertrade.application.queries.list_transactions import (
    ListTransactionsHandler,
    ListTransactionsQuery,
)

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/transactions",
    tags=["transactions"],
)


# Response Models


class TransactionResponse(BaseModel):
    """Transaction details response."""

    id: str
    portfolio_id: str
    transaction_type: str
    timestamp: str  # ISO 8601 format
    cash_change: str
    ticker: str | None
    quantity: str | None
    price_per_share: str | None
    notes: str | None


class TransactionListResponse(BaseModel):
    """List of transactions with pagination."""

    transactions: list[TransactionResponse]
    total_count: int
    limit: int
    offset: int


# Routes


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    portfolio_id: UUID,
    current_user: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
    limit: int = 50,
    offset: int = 0,
    transaction_type: str | None = None,
) -> TransactionListResponse:
    """Get transaction history for a portfolio.

    Supports pagination and filtering by transaction type.
    """
    # Verify user owns this portfolio
    portfolio = await portfolio_repo.get(portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio not found: {portfolio_id}",
        )

    if portfolio.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this portfolio",
        )

    # Query transactions
    from papertrade.domain.entities.transaction import TransactionType

    tx_type_filter = None
    if transaction_type:
        tx_type_filter = TransactionType[transaction_type]

    query = ListTransactionsQuery(
        portfolio_id=portfolio_id,
        limit=limit,
        offset=offset,
        transaction_type=tx_type_filter,
    )

    handler = ListTransactionsHandler(portfolio_repo, transaction_repo)
    result = await handler.execute(query)

    # Convert DTOs to responses
    transactions = [
        TransactionResponse(
            id=str(tx.id),
            portfolio_id=str(tx.portfolio_id),
            transaction_type=tx.transaction_type,
            timestamp=tx.timestamp.isoformat(),
            cash_change=f"{tx.cash_change_amount:.2f}",
            ticker=tx.ticker_symbol,
            quantity=(
                f"{tx.quantity_shares:.4f}"
                if tx.quantity_shares is not None
                else None
            ),
            price_per_share=f"{tx.price_per_share_amount:.2f}"
            if tx.price_per_share_amount is not None
            else None,
            notes=tx.notes,
        )
        for tx in result.transactions
    ]

    return TransactionListResponse(
        transactions=transactions,
        total_count=result.total_count,
        limit=limit,
        offset=offset,
    )
