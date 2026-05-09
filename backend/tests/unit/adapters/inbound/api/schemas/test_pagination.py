"""Unit tests for the standard PaginatedResponse envelope and helpers.

Wave 3-G — locks in the wire shape and the ``has_more`` arithmetic so every
list endpoint computes pagination metadata identically.
"""

import pytest
from pydantic import BaseModel, ValidationError

from zebu.adapters.inbound.api.schemas.pagination import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
    PaginationParams,
    build_paginated_response,
)


class _Item(BaseModel):
    """Tiny stand-in for a real domain DTO — pagination is generic."""

    name: str


class TestPaginatedResponse:
    """PaginatedResponse[T] must serialise to the documented envelope."""

    def test_envelope_keys_match_documented_shape(self) -> None:
        page = PaginatedResponse[_Item](
            items=[_Item(name="a")],
            total=1,
            limit=10,
            offset=0,
            has_more=False,
        )
        assert set(page.model_dump().keys()) == {
            "items",
            "total",
            "limit",
            "offset",
            "has_more",
        }

    def test_total_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            PaginatedResponse[_Item](
                items=[],
                total=-1,
                limit=10,
                offset=0,
                has_more=False,
            )

    def test_limit_caps_at_max_page_limit(self) -> None:
        with pytest.raises(ValidationError):
            PaginatedResponse[_Item](
                items=[],
                total=0,
                limit=MAX_PAGE_LIMIT + 1,
                offset=0,
                has_more=False,
            )

    def test_offset_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            PaginatedResponse[_Item](
                items=[],
                total=0,
                limit=10,
                offset=-1,
                has_more=False,
            )


class TestBuildPaginatedResponse:
    """``build_paginated_response`` is the single source of ``has_more``."""

    def test_has_more_true_when_more_rows_remain(self) -> None:
        page = build_paginated_response(
            items=[_Item(name=str(i)) for i in range(20)],
            total=100,
            limit=20,
            offset=0,
        )
        assert page.has_more is True

    def test_has_more_false_when_returning_last_page(self) -> None:
        page = build_paginated_response(
            items=[_Item(name="a")],
            total=21,
            limit=20,
            offset=20,
        )
        assert page.has_more is False

    def test_has_more_false_for_empty_result(self) -> None:
        page = build_paginated_response(
            items=[],
            total=0,
            limit=20,
            offset=0,
        )
        assert page.has_more is False

    def test_has_more_handles_offset_past_end(self) -> None:
        """Asking for offset beyond ``total`` yields an empty page with
        ``has_more=False`` — there is nothing more to fetch."""
        page = build_paginated_response(
            items=[],
            total=5,
            limit=10,
            offset=100,
        )
        assert page.has_more is False
        assert page.items == []


class TestPaginationParams:
    """The optional helper model used when a route forwards params to a handler."""

    def test_defaults_match_documented_constants(self) -> None:
        params = PaginationParams()
        assert params.limit == DEFAULT_PAGE_LIMIT
        assert params.offset == 0

    def test_rejects_zero_limit(self) -> None:
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)

    def test_rejects_limit_above_max(self) -> None:
        with pytest.raises(ValidationError):
            PaginationParams(limit=MAX_PAGE_LIMIT + 1)
