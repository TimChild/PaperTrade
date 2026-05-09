"""Unit tests for the standard ErrorResponse envelope.

Wave 3-G — exercises the schema directly so the contract is locked in even
if no route currently emits a particular shape (e.g. `fields` carrying
validation errors).
"""

import pytest
from pydantic import ValidationError

from zebu.adapters.inbound.api.schemas.errors import ErrorCode, ErrorResponse


class TestErrorResponse:
    """ErrorResponse must accept the documented shapes and reject the rest."""

    def test_minimal_response_only_requires_detail(self) -> None:
        """A bare ``{detail}`` payload is valid — code and fields are optional."""
        resp = ErrorResponse(detail="Something went wrong")
        assert resp.detail == "Something went wrong"
        assert resp.code is None
        assert resp.fields is None

    def test_full_response_round_trips_through_model_dump(self) -> None:
        """Detail / code / fields all survive a ``model_dump`` cycle unchanged."""
        resp = ErrorResponse(
            detail="Insufficient funds",
            code=ErrorCode.INSUFFICIENT_FUNDS.value,
            fields={"available": "100.00", "required": "200.00"},
        )
        dumped = resp.model_dump()
        assert dumped == {
            "detail": "Insufficient funds",
            "code": "insufficient_funds",
            "fields": {"available": "100.00", "required": "200.00"},
        }

    def test_detail_must_be_string(self) -> None:
        """The Wave 3-G contract is that ``detail`` is *always* a string —
        passing a dict (the legacy shape) must raise ``ValidationError``."""
        with pytest.raises(ValidationError):
            ErrorResponse(detail={"type": "x", "message": "y"})  # pyright: ignore[reportArgumentType]

    def test_fields_must_be_str_to_str(self) -> None:
        """``fields`` is a string-to-string map. Numeric values must be
        stringified before construction so the wire shape stays uniform."""
        with pytest.raises(ValidationError):
            ErrorResponse(detail="x", fields={"available": 100.0})  # pyright: ignore[reportArgumentType]

    def test_serialised_payload_matches_documented_envelope(self) -> None:
        """The dumped JSON shape must match the documented envelope exactly:
        ``{detail, code, fields}`` with no extra keys."""
        resp = ErrorResponse(detail="hello")
        dumped = resp.model_dump()
        assert set(dumped.keys()) == {"detail", "code", "fields"}


class TestErrorCode:
    """ErrorCode enum values must be stable strings — frontend / MCP clients
    match on them, so renaming would be a breaking change."""

    def test_known_codes_have_expected_string_values(self) -> None:
        assert ErrorCode.INSUFFICIENT_FUNDS.value == "insufficient_funds"
        assert ErrorCode.INSUFFICIENT_SHARES.value == "insufficient_shares"
        assert ErrorCode.TICKER_NOT_FOUND.value == "ticker_not_found"
        assert ErrorCode.MARKET_DATA_UNAVAILABLE.value == "market_data_unavailable"
        assert ErrorCode.VALIDATION_ERROR.value == "validation_error"

    def test_codes_are_str_enum(self) -> None:
        """Each member doubles as a plain string so it can be passed to
        ``ErrorResponse(code=...)`` without explicit ``.value`` access."""
        assert ErrorCode.INSUFFICIENT_FUNDS == "insufficient_funds"
