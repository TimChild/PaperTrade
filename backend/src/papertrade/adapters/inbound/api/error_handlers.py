"""FastAPI exception handlers.

Maps domain exceptions to HTTP status codes with consistent error responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from papertrade.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from papertrade.domain.exceptions import (
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidMoneyError,
    InvalidPortfolioError,
    InvalidQuantityError,
    InvalidTickerError,
    InvalidTransactionError,
)


class ErrorResponse(BaseModel):
    """Standard error response format.

    Attributes:
        detail: Error details (can be string or structured dict)
    """

    detail: str | dict[str, str | float]


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
                detail=str(exc),
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
                detail=str(exc),
            ).model_dump(),
        )

    @app.exception_handler(InsufficientFundsError)
    async def handle_insufficient_funds(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InsufficientFundsError
    ) -> JSONResponse:
        """Handle InsufficientFundsError -> 400 Bad Request with structured details."""
        shortfall = exc.required.subtract(exc.available)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                detail={
                    "type": "insufficient_funds",
                    "message": exc.message,
                    "available": float(exc.available.amount),
                    "required": float(exc.required.amount),
                    "shortfall": float(shortfall.amount),
                }
            ).model_dump(),
        )

    @app.exception_handler(InsufficientSharesError)
    async def handle_insufficient_shares(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InsufficientSharesError
    ) -> JSONResponse:
        """Handle InsufficientSharesError -> 400 Bad Request with structured details."""
        shortfall = exc.required.shares - exc.available.shares
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                detail={
                    "type": "insufficient_shares",
                    "message": exc.message,
                    "ticker": exc.ticker,
                    "available": float(exc.available.shares),
                    "required": float(exc.required.shares),
                    "shortfall": float(shortfall),
                }
            ).model_dump(),
        )

    @app.exception_handler(InvalidTickerError)
    async def handle_invalid_ticker(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidTickerError
    ) -> JSONResponse:
        """Handle InvalidTickerError -> 400 Bad Request."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                detail={
                    "type": "invalid_ticker",
                    "message": str(exc),
                }
            ).model_dump(),
        )

    @app.exception_handler(InvalidQuantityError)
    async def handle_invalid_quantity(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidQuantityError
    ) -> JSONResponse:
        """Handle InvalidQuantityError -> 400 Bad Request."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                detail={
                    "type": "invalid_quantity",
                    "message": str(exc),
                }
            ).model_dump(),
        )

    @app.exception_handler(InvalidMoneyError)
    async def handle_invalid_money(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidMoneyError
    ) -> JSONResponse:
        """Handle InvalidMoneyError -> 400 Bad Request."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                detail={
                    "type": "invalid_money",
                    "message": str(exc),
                }
            ).model_dump(),
        )

    @app.exception_handler(TickerNotFoundError)
    async def handle_ticker_not_found(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: TickerNotFoundError
    ) -> JSONResponse:
        """Handle TickerNotFoundError -> 404 Not Found."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                detail={
                    "type": "ticker_not_found",
                    "message": f"Invalid ticker symbol: {exc.ticker}",
                    "ticker": exc.ticker,
                }
            ).model_dump(),
        )

    @app.exception_handler(MarketDataUnavailableError)
    async def handle_market_data_unavailable(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: MarketDataUnavailableError
    ) -> JSONResponse:
        """Handle MarketDataUnavailableError -> 503 Service Unavailable."""
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                detail={
                    "type": "market_data_unavailable",
                    "message": "Unable to fetch market data. Please try again later.",
                    "reason": exc.reason,
                }
            ).model_dump(),
        )
