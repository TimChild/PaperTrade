"""Logging middleware for FastAPI applications.

This module provides middleware that adds request correlation IDs and
context binding for structured logging with structlog.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Add request correlation ID and context to all logs.

    This middleware:
    1. Generates or extracts a correlation ID for each request
    2. Binds request context (path, method, client IP) to structlog
    3. Logs request start and completion with timing information
    4. Adds correlation ID to response headers for client-side tracing

    The correlation ID and request context are automatically included in all
    log statements made during request processing via structlog's context vars.

    Example:
        >>> app = FastAPI()
        >>> app.add_middleware(LoggingContextMiddleware)
        >>>
        >>> # In a route handler:
        >>> logger = structlog.get_logger(__name__)
        >>> logger.info("Processing request")  # Includes correlation_id automatically
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request with logging context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler in chain

        Returns:
            HTTP response with X-Correlation-ID header
        """
        # Generate correlation ID (or use client-provided one)
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Clear any existing context and bind new request context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_path=request.url.path,
            request_method=request.method,
            client_ip=request.client.host if request.client else None,
        )

        logger = structlog.get_logger(__name__)
        logger.info(
            "Request started",
            path=request.url.path,
            method=request.method,
        )

        # Track request timing
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate request duration
        duration = time.time() - start_time

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_seconds=round(duration, 3),
        )

        return response


__all__ = ["LoggingContextMiddleware"]
