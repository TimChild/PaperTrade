"""FastAPI exception handlers.

Maps domain exceptions to HTTP status codes with consistent error responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from papertrade.domain.exceptions import (
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidPortfolioError,
    InvalidTransactionError,
)


class ErrorResponse(BaseModel):
    """Standard error response format.

    Attributes:
        error: Error type/category
        message: Human-readable error message
        details: Optional additional error details
    """

    error: str
    message: str
    details: dict[str, str] | None = None


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(InvalidPortfolioError)
    async def handle_invalid_portfolio(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InvalidPortfolioError
    ) -> JSONResponse:
        """Handle InvalidPortfolioError -> 400 Bad Request."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="InvalidPortfolio",
                message=str(exc),
            ).model_dump(),
        )

    @app.exception_handler(InvalidTransactionError)
    async def handle_invalid_transaction(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InvalidTransactionError
    ) -> JSONResponse:
        """Handle InvalidTransactionError -> 400 Bad Request."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="InvalidTransaction",
                message=str(exc),
            ).model_dump(),
        )

    @app.exception_handler(InsufficientFundsError)
    async def handle_insufficient_funds(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InsufficientFundsError
    ) -> JSONResponse:
        """Handle InsufficientFundsError -> 400 Bad Request."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="InsufficientFunds",
                message=str(exc),
            ).model_dump(),
        )

    @app.exception_handler(InsufficientSharesError)
    async def handle_insufficient_shares(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InsufficientSharesError
    ) -> JSONResponse:
        """Handle InsufficientSharesError -> 400 Bad Request."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="InsufficientShares",
                message=str(exc),
            ).model_dump(),
        )
