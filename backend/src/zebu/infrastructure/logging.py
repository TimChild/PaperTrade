"""Structured logging configuration using structlog.

This module provides centralized logging configuration for the application
using structlog for structured logging with JSON output in production and
human-readable colored output in development.

Features:
    - JSON-formatted logs for machine parsing (Loki/Grafana integration)
    - Human-readable colored output for development
    - Automatic request correlation IDs (via middleware)
    - Incremental context binding (attach context once, use everywhere)
    - Lazy evaluation for better performance
"""

import logging
import sys

import structlog
from structlog.processors import (
    CallsiteParameter,
    CallsiteParameterAdder,
    StackInfoRenderer,
    TimeStamper,
    UnicodeDecoder,
    add_log_level,
    format_exc_info,
)
from structlog.stdlib import (
    add_logger_name,
)


def setup_structlog(
    log_level: str = "INFO",
    json_output: bool = True,
) -> None:
    """Configure structlog for the application.

    This function sets up structlog with appropriate processors and formatters
    for either production (JSON output) or development (colored console output).

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        json_output: If True, output JSON lines. If False, human-readable colored output

    Example:
        >>> # Production mode (JSON output)
        >>> setup_structlog(log_level="INFO", json_output=True)
        >>>
        >>> # Development mode (colored console)
        >>> setup_structlog(log_level="DEBUG", json_output=False)
        >>>
        >>> logger = structlog.get_logger(__name__)
        >>> logger.info("Application started", version="0.1.0")
    """
    # Shared processors for all loggers
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,  # Merge context variables
        add_log_level,  # Add log level to event dict
        add_logger_name,  # Add logger name to event dict
        TimeStamper(fmt="iso", utc=True),  # Add timestamp in ISO format
        StackInfoRenderer(),  # Render stack info if available
        format_exc_info,  # Format exceptions
        UnicodeDecoder(),  # Decode unicode
        CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.FILENAME,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ]
        ),  # Add call site info
    ]

    if json_output:
        # Production: JSON output for machine parsing
        from pythonjsonlogger.json import JsonFormatter

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())

        structlog.configure(
            processors=shared_processors
            + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure stdlib logging
        logging.basicConfig(
            format="%(message)s",
            level=getattr(logging, log_level.upper()),
            handlers=[handler],
        )
    else:
        # Development: Human-readable colored output
        structlog.configure(
            processors=shared_processors
            + [
                structlog.dev.ConsoleRenderer(colors=True),  # Colored console output
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure stdlib logging
        logging.basicConfig(
            format="%(message)s",
            level=getattr(logging, log_level.upper()),
            stream=sys.stdout,
        )


__all__ = ["setup_structlog"]
