"""Unit tests for :class:`AlphaVantageTickerValidator`.

Task #221 — ticker validation on ``POST /admin/watchlist``.

Mocks the ``httpx.AsyncClient`` HTTP call so no real network traffic is
needed. Covers the three decision branches:

1. Non-empty ``Global Quote`` block → ``is_recognised`` returns ``True``.
2. Empty ``Global Quote`` block → ``is_recognised`` returns ``False``
   (AV doesn't know this symbol).
3. ``Information`` / ``Note`` body (rate-limit or premium gate) →
   ``MarketDataUnavailableError`` raised. The caller must surface this
   as a 500, not a 422.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from zebu.adapters.outbound.market_data.av_ticker_validator import (
    AlphaVantageTickerValidator,
)
from zebu.application.exceptions import MarketDataUnavailableError
from zebu.domain.value_objects.ticker import Ticker


def _make_response(body: dict[str, object], status_code: int = 200) -> httpx.Response:
    """Build a fake ``httpx.Response`` with the given JSON body."""
    content = json.dumps(body).encode()
    return httpx.Response(
        status_code=status_code,
        headers={"content-type": "application/json"},
        content=content,
        request=httpx.Request("GET", "https://www.alphavantage.co/query"),
    )


def _make_validator(
    http_client: httpx.AsyncClient,
) -> AlphaVantageTickerValidator:
    return AlphaVantageTickerValidator(
        http_client=http_client,
        api_key="test-key",
        base_url="https://www.alphavantage.co/query",
        timeout=5.0,
    )


class TestIsRecognised:
    """``is_recognised`` decision table."""

    async def test_non_empty_global_quote_returns_true(self) -> None:
        """A full ``Global Quote`` block → ticker is recognised."""
        aapl_response = _make_response(
            {
                "Global Quote": {
                    "01. symbol": "AAPL",
                    "05. price": "192.53",
                    "07. latest trading day": "2026-05-22",
                }
            }
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = aapl_response

        validator = _make_validator(mock_client)
        result = await validator.is_recognised(Ticker("AAPL"))

        assert result is True
        mock_client.get.assert_awaited_once()

    async def test_empty_global_quote_returns_false(self) -> None:
        """An empty ``Global Quote`` dict → symbol not known to AV."""
        empty_response = _make_response({"Global Quote": {}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = empty_response

        validator = _make_validator(mock_client)
        result = await validator.is_recognised(Ticker("BOGUS"))

        assert result is False

    async def test_missing_global_quote_key_returns_false(self) -> None:
        """Completely absent ``Global Quote`` key → also not recognised."""
        bad_response = _make_response({})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = bad_response

        validator = _make_validator(mock_client)
        result = await validator.is_recognised(Ticker("NOPE"))

        assert result is False

    async def test_information_body_raises_market_data_unavailable(self) -> None:
        """AV ``Information`` rate-limit body → raise, not return False.

        The caller needs to distinguish "provider down / rate-limited"
        from "ticker doesn't exist". Swallowing this as ``False`` would
        block the operator from pinning a valid ticker during an AV
        rate-limit window.
        """
        rate_limit_response = _make_response(
            {
                "Information": (
                    "Thank you for using Alpha Vantage! Our standard API rate "
                    "limit is 25 requests per day."
                )
            }
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = rate_limit_response

        validator = _make_validator(mock_client)
        with pytest.raises(MarketDataUnavailableError):
            await validator.is_recognised(Ticker("AAPL"))

    async def test_note_body_raises_market_data_unavailable(self) -> None:
        """AV ``Note`` body (older rate-limit format) → also raises."""
        note_response = _make_response(
            {
                "Note": (
                    "Thank you for using Alpha Vantage! Our standard API call "
                    "frequency is 5 calls per minute and 100 calls per day."
                )
            }
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = note_response

        validator = _make_validator(mock_client)
        with pytest.raises(MarketDataUnavailableError):
            await validator.is_recognised(Ticker("AAPL"))

    async def test_premium_refusal_body_raises_market_data_unavailable(self) -> None:
        """AV premium-gate ``Information`` body → raises, not False.

        The ``outputsize=full`` premium-gate body uses the same
        ``Information`` key. Although our GLOBAL_QUOTE call doesn't use
        ``outputsize``, the heuristic for detection is the same — any
        ``Information``/``Note`` body should raise.
        """
        premium_response = _make_response(
            {
                "Information": (
                    "The outputsize=full parameter value is a premium feature "
                    "for the TIME_SERIES_DAILY endpoint."
                )
            }
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = premium_response

        validator = _make_validator(mock_client)
        with pytest.raises(MarketDataUnavailableError):
            await validator.is_recognised(Ticker("AAPL"))

    async def test_timeout_raises_market_data_unavailable(self) -> None:
        """Network timeout → ``MarketDataUnavailableError``."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")

        validator = _make_validator(mock_client)
        with pytest.raises(MarketDataUnavailableError, match="Timeout"):
            await validator.is_recognised(Ticker("AAPL"))

    async def test_network_error_raises_market_data_unavailable(self) -> None:
        """Network error → ``MarketDataUnavailableError``."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.NetworkError("connection refused")

        validator = _make_validator(mock_client)
        with pytest.raises(MarketDataUnavailableError, match="Network error"):
            await validator.is_recognised(Ticker("AAPL"))

    async def test_http_error_status_raises_market_data_unavailable(self) -> None:
        """HTTP 4xx/5xx from AV → ``MarketDataUnavailableError``."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        # raise_for_status() is called after response — simulate a 500.
        error_response = httpx.Response(
            status_code=500,
            content=b"internal server error",
            request=httpx.Request("GET", "https://www.alphavantage.co/query"),
        )
        mock_client.get.return_value = error_response

        validator = _make_validator(mock_client)
        with pytest.raises(MarketDataUnavailableError):
            await validator.is_recognised(Ticker("AAPL"))
