"""Shared API schemas (cross-router envelopes, errors, pagination)."""

from zebu.adapters.inbound.api.schemas.errors import ErrorCode, ErrorResponse
from zebu.adapters.inbound.api.schemas.pagination import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
    PaginationParams,
)
from zebu.adapters.inbound.api.schemas.triggers import (
    CreateTriggerRequest,
    DisableAllResponse,
    TriggerFireResponse,
    TriggerResponse,
    UpdateTriggerRequest,
)

__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "CreateTriggerRequest",
    "DisableAllResponse",
    "ErrorCode",
    "ErrorResponse",
    "MAX_PAGE_LIMIT",
    "PaginatedResponse",
    "PaginationParams",
    "TriggerFireResponse",
    "TriggerResponse",
    "UpdateTriggerRequest",
]
