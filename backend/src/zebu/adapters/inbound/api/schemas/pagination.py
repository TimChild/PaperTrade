"""Standard pagination envelope and query helpers for list endpoints.

Wave 3-G: This module defines the single shape every list endpoint must
return. The audit (`agent_docs/audits/2026-05-09/api-design.md` findings
P1-API-3 and P1-API-5) found that some list routes returned bare ``list[T]``
while others returned an ad-hoc ``{transactions, total_count, limit, offset}``
shape, and that several lists had no pagination at all.

Convention:

* Query params: ``?limit=N&offset=N`` with ``limit`` defaulting to 20 and
  capped at 100, ``offset`` non-negative.
* Response: ``{items, total, limit, offset, has_more}``. ``has_more`` is
  computed once on the server so clients do not have to recompute it.

Use ``PaginatedResponse[T]`` as the route's ``response_model``. ``T`` may be
any Pydantic model — FastAPI will inline the generic into the OpenAPI schema.
"""

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field

DEFAULT_PAGE_LIMIT = 20
"""Default value for the ``limit`` query parameter when omitted by the client."""

MAX_PAGE_LIMIT = 100
"""Maximum value the ``limit`` query parameter may take. Requests with a
larger ``limit`` are rejected by FastAPI as 422 before reaching the handler."""


class PaginatedResponse[T](BaseModel):
    """Standard list response envelope.

    Attributes:
        items: Page of items returned by this request. May be shorter than
            ``limit`` if fewer rows remain.
        total: Total count of matching rows across all pages. Lets clients
            render "showing 1-20 of 134" UIs without an extra round trip.
        limit: The ``limit`` query value the server actually applied (after
            clamping). Echoed so the client can confirm what it asked for.
        offset: The ``offset`` query value the server actually applied.
        has_more: ``True`` when ``offset + len(items) < total``. Pre-computed
            on the server so clients do not duplicate the arithmetic.
    """

    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=MAX_PAGE_LIMIT)
    offset: int = Field(ge=0)
    has_more: bool


# Reusable Annotated query parameters. Routes import these so every list
# endpoint advertises identical parameter names, descriptions, and bounds in
# the OpenAPI schema.

PaginationLimit = Annotated[
    int,
    Query(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Maximum number of items to return (1-100, default 20).",
    ),
]
PaginationOffset = Annotated[
    int,
    Query(
        default=0,
        ge=0,
        description="Number of items to skip for pagination (default 0).",
    ),
]


class PaginationParams(BaseModel):
    """Validated pagination parameters extracted from a request.

    Routes can either accept ``limit`` and ``offset`` as separate ``Query``
    parameters and construct this manually, or use the ``PaginationLimit`` /
    ``PaginationOffset`` annotated aliases. The latter is simpler for routes
    that only paginate; the model is convenient when a route also has other
    filter params and wants to forward them as a single object to a handler.
    """

    limit: int = Field(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT)
    offset: int = Field(default=0, ge=0)


def build_paginated_response[T](
    *,
    items: list[T],
    total: int,
    limit: int,
    offset: int,
) -> PaginatedResponse[T]:
    """Construct a ``PaginatedResponse`` with ``has_more`` filled in.

    Centralised so every router computes ``has_more`` the same way.

    Args:
        items: Page of items returned to the client.
        total: Total matching rows across all pages.
        limit: Applied limit (after clamping by FastAPI's Query validation).
        offset: Applied offset.

    Returns:
        Populated ``PaginatedResponse[T]``.
    """
    return PaginatedResponse[T](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )
