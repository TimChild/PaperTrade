"""Shared API schemas (cross-router envelopes, errors, pagination)."""

from zebu.adapters.inbound.api.schemas.errors import ErrorCode, ErrorResponse
from zebu.adapters.inbound.api.schemas.pagination import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
    PaginationParams,
)

__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "ErrorCode",
    "ErrorResponse",
    "MAX_PAGE_LIMIT",
    "PaginatedResponse",
    "PaginationParams",
]
