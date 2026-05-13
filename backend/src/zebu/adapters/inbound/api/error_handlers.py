"""FastAPI exception handlers.

Maps domain exceptions to HTTP status codes with consistent error responses.

Wave 3-G: All handlers now emit the unified ``ErrorResponse`` envelope
``{detail, code, fields}`` defined in ``schemas.errors``. ``detail`` is always
a string; auxiliary numeric / identifier data (``available``, ``required``,
``shortfall``, ``ticker``, ``reason``, ...) ride in ``fields`` as strings.
"""

from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from zebu.adapters.inbound.api.schemas.errors import ErrorCode, ErrorResponse
from zebu.application.exceptions import (
    IncompleteHistoricalDataError,
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.domain.entities.exploration_task import InvalidExplorationTaskError
from zebu.domain.exceptions import (
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidMoneyError,
    InvalidPortfolioError,
    InvalidQuantityError,
    InvalidStrategyError,
    InvalidTickerError,
    InvalidTransactionError,
)


def _error_json(
    *,
    status_code: int,
    detail: str,
    code: ErrorCode | None = None,
    fields: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a ``JSONResponse`` carrying an ``ErrorResponse`` envelope.

    Centralised so every handler in this module emits the same shape.
    """
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            detail=detail,
            code=code.value if code is not None else None,
            fields=fields,
        ).model_dump(),
    )


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
        return _error_json(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            code=ErrorCode.INVALID_PORTFOLIO,
        )

    @app.exception_handler(InvalidTransactionError)
    async def handle_invalid_transaction(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InvalidTransactionError
    ) -> JSONResponse:
        """Handle InvalidTransactionError -> 400 Bad Request."""
        return _error_json(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            code=ErrorCode.INVALID_TRANSACTION,
        )

    @app.exception_handler(InsufficientFundsError)
    async def handle_insufficient_funds(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InsufficientFundsError
    ) -> JSONResponse:
        """Handle InsufficientFundsError -> 400 Bad Request with structured details."""
        shortfall = exc.required.subtract(exc.available)
        return _error_json(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
            code=ErrorCode.INSUFFICIENT_FUNDS,
            fields={
                "available": f"{float(exc.available.amount)}",
                "required": f"{float(exc.required.amount)}",
                "shortfall": f"{float(shortfall.amount)}",
            },
        )

    @app.exception_handler(InsufficientSharesError)
    async def handle_insufficient_shares(  # pyright: ignore[reportUnusedFunction]  # Used as FastAPI exception handler decorator
        request: Request, exc: InsufficientSharesError
    ) -> JSONResponse:
        """Handle InsufficientSharesError -> 400 Bad Request with structured details."""
        shortfall = exc.required.shares - exc.available.shares
        return _error_json(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
            code=ErrorCode.INSUFFICIENT_SHARES,
            fields={
                "ticker": exc.ticker,
                "available": f"{float(exc.available.shares)}",
                "required": f"{float(exc.required.shares)}",
                "shortfall": f"{float(shortfall)}",
            },
        )

    @app.exception_handler(InvalidTickerError)
    async def handle_invalid_ticker(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidTickerError
    ) -> JSONResponse:
        """Handle InvalidTickerError -> 400 Bad Request."""
        return _error_json(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            code=ErrorCode.INVALID_TICKER,
        )

    @app.exception_handler(InvalidQuantityError)
    async def handle_invalid_quantity(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidQuantityError
    ) -> JSONResponse:
        """Handle InvalidQuantityError -> 400 Bad Request."""
        return _error_json(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            code=ErrorCode.INVALID_QUANTITY,
        )

    @app.exception_handler(InvalidMoneyError)
    async def handle_invalid_money(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidMoneyError
    ) -> JSONResponse:
        """Handle InvalidMoneyError -> 400 Bad Request."""
        return _error_json(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            code=ErrorCode.INVALID_MONEY,
        )

    @app.exception_handler(InvalidStrategyError)
    async def handle_invalid_strategy(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidStrategyError
    ) -> JSONResponse:
        """Handle InvalidStrategyError -> 422 Unprocessable Entity."""
        return _error_json(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            code=ErrorCode.INVALID_STRATEGY,
        )

    @app.exception_handler(InvalidExplorationTaskError)
    async def handle_invalid_exploration_task(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: InvalidExplorationTaskError
    ) -> JSONResponse:
        """Handle InvalidExplorationTaskError -> 422 Unprocessable Entity."""
        return _error_json(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            code=ErrorCode.INVALID_EXPLORATION_TASK,
        )

    @app.exception_handler(TickerNotFoundError)
    async def handle_ticker_not_found(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: TickerNotFoundError
    ) -> JSONResponse:
        """Handle TickerNotFoundError -> 404 Not Found."""
        return _error_json(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid ticker symbol: {exc.ticker}",
            code=ErrorCode.TICKER_NOT_FOUND,
            fields={"ticker": exc.ticker},
        )

    @app.exception_handler(MarketDataUnavailableError)
    async def handle_market_data_unavailable(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: MarketDataUnavailableError
    ) -> JSONResponse:
        """Handle MarketDataUnavailableError -> 503 Service Unavailable."""
        return _error_json(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch market data. Please try again later.",
            code=ErrorCode.MARKET_DATA_UNAVAILABLE,
            fields={"reason": exc.reason},
        )

    @app.exception_handler(IncompleteHistoricalDataError)
    async def handle_incomplete_historical_data(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: IncompleteHistoricalDataError
    ) -> JSONResponse:
        """Handle IncompleteHistoricalDataError -> 503 with structured body.

        Phase J / Task #212 Layer 3. Returns a *bespoke* body shape that
        differs from the standard ``{detail, code, fields}`` envelope —
        the spec calls for ``{status, ticker, missing_range, eta_seconds,
        retry_after_seconds}`` so the frontend can distinguish a
        "fetching" 503 from any other 503 by inspecting ``status`` at
        the top level. ``Retry-After`` HTTP header mirrors the body's
        ``retry_after_seconds``.
        """
        retry_after_seconds = 60
        req_start, req_end = exc.requested_range
        if exc.available_range is None:
            missing_start, missing_end = req_start, req_end
        else:
            avail_start, avail_end = exc.available_range
            head_missing = avail_start > req_start
            tail_missing = avail_end < req_end
            if head_missing and tail_missing:
                missing_start, missing_end = req_start, req_end
            elif head_missing:
                missing_start = req_start
                missing_end = avail_start - timedelta(days=1)
            else:
                missing_start = avail_end + timedelta(days=1)
                missing_end = req_end
        body: dict[str, Any] = {
            "status": "fetching",
            "ticker": exc.ticker.symbol,
            "missing_range": {
                "start": missing_start.isoformat(),
                "end": missing_end.isoformat(),
            },
            "eta_seconds": retry_after_seconds,
            "retry_after_seconds": retry_after_seconds,
        }
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body,
            headers={"Retry-After": str(retry_after_seconds)},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Normalise every ``HTTPException`` into the standard envelope.

        FastAPI's default handler emits ``{"detail": <whatever was passed>}``
        which leaks dict-shaped detail through routes that have not been
        migrated yet. This handler:

        * If the route raised ``HTTPException(detail=str)``, passes the string
          through as ``detail`` with no code or fields.
        * If the route raised ``HTTPException(detail={"type": ..., "message":
            ..., **extras})`` (legacy shape), splits it into
            ``detail`` / ``code`` / ``fields``. Routes are being migrated to
            the new shape; this keeps backwards compatibility while the
            migration is in flight.
        * If the route raised ``HTTPException(detail=ErrorResponse(...).model_dump())``
          it is passed through unchanged.

        Auth headers (e.g. ``WWW-Authenticate: Bearer``) on the original
        exception are preserved.
        """
        detail_obj: object = exc.detail

        # Pass-through if the route already produced the new envelope.
        if isinstance(detail_obj, dict) and "detail" in detail_obj:
            payload: dict[str, Any] = dict(detail_obj)
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(**payload).model_dump(),
                headers=exc.headers,
            )

        # Legacy {"type": "...", "message": "...", ...extras} dict detail.
        if isinstance(detail_obj, dict):
            type_value = detail_obj.get("type")
            message_value = detail_obj.get("message")
            code_str = str(type_value) if type_value is not None else None
            message_str = (
                str(message_value) if message_value is not None else "An error occurred"
            )
            fields = {
                k: str(v)
                for k, v in detail_obj.items()
                if k not in {"type", "message"} and v is not None
            }
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    detail=message_str,
                    code=code_str,
                    fields=fields or None,
                ).model_dump(),
                headers=exc.headers,
            )

        # Plain-string detail (the common case for non-domain errors).
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(detail=str(detail_obj)).model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Map FastAPI's request validation errors into the standard envelope.

        The default 422 response is ``{"detail": [{loc, msg, type, ...}, ...]}``
        which violates the Wave 3-G envelope. This handler flattens it into
        ``{detail, code, fields}`` where ``fields`` maps each invalid field
        path (e.g. ``"body.initial_deposit"``) to the validator message.
        """
        return _error_json(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request validation failed",
            code=ErrorCode.VALIDATION_ERROR,
            fields=_validation_errors_to_fields(exc.errors()),
        )

    @app.exception_handler(ValidationError)
    async def handle_pydantic_validation_error(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Pydantic ``ValidationError`` (raised from response validation or
        manual model construction). Treated the same way as a request
        validation error so the envelope shape stays uniform."""
        return _error_json(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validation failed",
            code=ErrorCode.VALIDATION_ERROR,
            fields=_validation_errors_to_fields(exc.errors()),
        )


def _validation_errors_to_fields(
    errors: Sequence[Any],
) -> dict[str, str]:
    """Flatten a Pydantic-style errors list into the ``fields`` map.

    Each error has a ``loc`` tuple (e.g. ``("body", "initial_deposit")``) and
    a ``msg`` string. We join the ``loc`` parts with dots and use the message
    as the value. If two errors share the same path (rare), the later one
    wins — Pydantic already aggregates them into a single ``msg`` per field.

    The ``Sequence[Any]`` type is intentionally loose: Pydantic v2's
    ``ValidationError.errors()`` returns ``list[ErrorDetails]`` (a TypedDict)
    while FastAPI's ``RequestValidationError.errors()`` returns
    ``Sequence[Any]``. The structural access below works for both.
    """
    fields: dict[str, str] = {}
    for err in errors:
        loc = err.get("loc", ()) if isinstance(err, dict) else getattr(err, "loc", ())
        msg = (
            err.get("msg", "Invalid value")
            if isinstance(err, dict)
            else getattr(err, "msg", "Invalid value")
        )
        if isinstance(loc, (list, tuple)):
            key = ".".join(str(part) for part in loc) or "__root__"
        else:
            key = str(loc)
        fields[key] = str(msg)
    return fields
