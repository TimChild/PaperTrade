"""FastAPI exception handlers.

Maps domain exceptions to HTTP status codes with consistent error responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from papertrade.domain.exceptions import (
    DuplicateEmailError,
    InactiveUserError,
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidCredentialsError,
    InvalidPortfolioError,
    InvalidTokenError,
    InvalidTransactionError,
    UserNotFoundError,
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

    # Authentication & Authorization Exception Handlers

    @app.exception_handler(InvalidCredentialsError)
    async def handle_invalid_credentials(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidCredentialsError
    ) -> JSONResponse:
        """Handle InvalidCredentialsError -> 401 Unauthorized."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                error="InvalidCredentials",
                message="Incorrect email or password",
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(InvalidTokenError)
    async def handle_invalid_token(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidTokenError
    ) -> JSONResponse:
        """Handle InvalidTokenError -> 401 Unauthorized."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                error="InvalidToken",
                message="Invalid or expired token",
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(InactiveUserError)
    async def handle_inactive_user(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InactiveUserError
    ) -> JSONResponse:
        """Handle InactiveUserError -> 403 Forbidden."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(
                error="InactiveUser",
                message="User account is inactive",
            ).model_dump(),
        )

    @app.exception_handler(UserNotFoundError)
    async def handle_user_not_found(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: UserNotFoundError
    ) -> JSONResponse:
        """Handle UserNotFoundError -> 404 Not Found."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error="UserNotFound",
                message="User not found",
            ).model_dump(),
        )

    @app.exception_handler(DuplicateEmailError)
    async def handle_duplicate_email(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: DuplicateEmailError
    ) -> JSONResponse:
        """Handle DuplicateEmailError -> 409 Conflict."""
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                error="DuplicateEmail",
                message="Email already registered",
            ).model_dump(),
        )
