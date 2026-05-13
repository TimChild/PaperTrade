"""Tests for application layer exceptions."""

from datetime import date

import pytest

from zebu.application.exceptions import (
    IncompleteHistoricalDataError,
    InvalidPriceDataError,
    MarketDataError,
    MarketDataUnavailableError,
    PartialPricingError,
    TickerNotFoundError,
)
from zebu.domain.value_objects.ticker import Ticker


class TestMarketDataError:
    """Tests for MarketDataError base exception."""

    def test_construction(self) -> None:
        """Should create MarketDataError with message."""
        error = MarketDataError("Test error message")
        assert error.message == "Test error message"
        assert str(error) == "Test error message"

    def test_inheritance(self) -> None:
        """Should inherit from Exception."""
        error = MarketDataError("Test error")
        assert isinstance(error, Exception)


class TestTickerNotFoundError:
    """Tests for TickerNotFoundError exception."""

    def test_construction_with_default_message(self) -> None:
        """Should create TickerNotFoundError with default message."""
        error = TickerNotFoundError("XYZ")
        assert error.ticker == "XYZ"
        assert error.message == "Ticker not found: XYZ"
        assert str(error) == "Ticker not found: XYZ"

    def test_construction_with_custom_message(self) -> None:
        """Should create TickerNotFoundError with custom message."""
        custom_msg = "Custom error message"
        error = TickerNotFoundError("XYZ", custom_msg)
        assert error.ticker == "XYZ"
        assert error.message == custom_msg
        assert str(error) == custom_msg

    def test_inheritance(self) -> None:
        """Should inherit from MarketDataError."""
        error = TickerNotFoundError("XYZ")
        assert isinstance(error, MarketDataError)
        assert isinstance(error, Exception)

    def test_ticker_attribute_accessible(self) -> None:
        """Should allow access to ticker attribute for error handling."""
        error = TickerNotFoundError("INVALID")
        assert error.ticker == "INVALID"


class TestMarketDataUnavailableError:
    """Tests for MarketDataUnavailableError exception."""

    def test_construction_with_default_message(self) -> None:
        """Should create MarketDataUnavailableError with default message."""
        error = MarketDataUnavailableError("API rate limit exceeded")
        assert error.reason == "API rate limit exceeded"
        assert error.message == "Market data unavailable: API rate limit exceeded"
        assert str(error) == "Market data unavailable: API rate limit exceeded"

    def test_construction_with_custom_message(self) -> None:
        """Should create MarketDataUnavailableError with custom message."""
        custom_msg = "Custom error message"
        error = MarketDataUnavailableError("Network timeout", custom_msg)
        assert error.reason == "Network timeout"
        assert error.message == custom_msg
        assert str(error) == custom_msg

    def test_inheritance(self) -> None:
        """Should inherit from MarketDataError."""
        error = MarketDataUnavailableError("Test reason")
        assert isinstance(error, MarketDataError)
        assert isinstance(error, Exception)

    def test_reason_attribute_accessible(self) -> None:
        """Should allow access to reason attribute for error handling."""
        error = MarketDataUnavailableError("Network failure")
        assert error.reason == "Network failure"


class TestInvalidPriceDataError:
    """Tests for InvalidPriceDataError exception."""

    def test_construction_with_default_message(self) -> None:
        """Should create InvalidPriceDataError with default message."""
        error = InvalidPriceDataError("AAPL", "price must be positive")
        assert error.ticker == "AAPL"
        assert error.reason == "price must be positive"
        expected_msg = "Invalid price data for AAPL: price must be positive"
        assert error.message == expected_msg
        assert str(error) == expected_msg

    def test_construction_with_custom_message(self) -> None:
        """Should create InvalidPriceDataError with custom message."""
        custom_msg = "Custom error message"
        error = InvalidPriceDataError("AAPL", "negative price", custom_msg)
        assert error.ticker == "AAPL"
        assert error.reason == "negative price"
        assert error.message == custom_msg
        assert str(error) == custom_msg

    def test_inheritance(self) -> None:
        """Should inherit from MarketDataError."""
        error = InvalidPriceDataError("AAPL", "test reason")
        assert isinstance(error, MarketDataError)
        assert isinstance(error, Exception)

    def test_attributes_accessible(self) -> None:
        """Should allow access to ticker and reason attributes."""
        error = InvalidPriceDataError("TSLA", "impossible OHLCV values")
        assert error.ticker == "TSLA"
        assert error.reason == "impossible OHLCV values"


class TestIncompleteHistoricalDataError:
    """Tests for IncompleteHistoricalDataError (Phase J / Task #212 Layer 3)."""

    def test_construction_with_available_range(self) -> None:
        """Holds ticker, ranges, missing-day count and a default message."""
        ticker = Ticker("AAPL")
        requested = (date(2026, 1, 1), date(2026, 1, 31))
        available = (date(2026, 1, 15), date(2026, 1, 31))
        error = IncompleteHistoricalDataError(
            ticker=ticker,
            requested_range=requested,
            available_range=available,
            missing_days_count=14,
        )
        assert error.ticker == ticker
        assert error.requested_range == requested
        assert error.available_range == available
        assert error.missing_days_count == 14
        # Default message includes both the available range and the count.
        assert "AAPL" in str(error)
        assert "2026-01-15" in str(error)
        assert "14" in str(error)

    def test_construction_with_no_available_range(self) -> None:
        """``available_range=None`` is allowed for the no-data-yet case."""
        ticker = Ticker("AAPL")
        requested = (date(2026, 1, 1), date(2026, 1, 31))
        error = IncompleteHistoricalDataError(
            ticker=ticker,
            requested_range=requested,
            available_range=None,
            missing_days_count=30,
        )
        assert error.available_range is None
        assert "No historical data" in str(error)
        assert "AAPL" in str(error)

    def test_inheritance(self) -> None:
        """Should inherit from MarketDataError."""
        ticker = Ticker("AAPL")
        error = IncompleteHistoricalDataError(
            ticker=ticker,
            requested_range=(date(2026, 1, 1), date(2026, 1, 31)),
            available_range=None,
            missing_days_count=30,
        )
        assert isinstance(error, MarketDataError)
        assert isinstance(error, Exception)

    def test_custom_message_overrides_default(self) -> None:
        """Caller-supplied message wins."""
        ticker = Ticker("AAPL")
        error = IncompleteHistoricalDataError(
            ticker=ticker,
            requested_range=(date(2026, 1, 1), date(2026, 1, 31)),
            available_range=None,
            missing_days_count=30,
            message="custom!",
        )
        assert str(error) == "custom!"


class TestExceptionHierarchy:
    """Tests for exception hierarchy relationships."""

    def test_all_inherit_from_market_data_error(self) -> None:
        """Should be able to catch all market data errors."""
        errors = [
            TickerNotFoundError("XYZ"),
            MarketDataUnavailableError("test"),
            InvalidPriceDataError("AAPL", "test"),
            IncompleteHistoricalDataError(
                ticker=Ticker("AAPL"),
                requested_range=(date(2026, 1, 1), date(2026, 1, 31)),
                available_range=None,
                missing_days_count=30,
            ),
        ]

        for error in errors:
            assert isinstance(error, MarketDataError)

    def test_catch_specific_exceptions(self) -> None:
        """Should be able to catch specific exception types."""

        def raise_ticker_not_found() -> None:
            raise TickerNotFoundError("XYZ")

        def raise_unavailable() -> None:
            raise MarketDataUnavailableError("test")

        def raise_invalid_data() -> None:
            raise InvalidPriceDataError("AAPL", "test")

        with pytest.raises(TickerNotFoundError):
            raise_ticker_not_found()

        with pytest.raises(MarketDataUnavailableError):
            raise_unavailable()

        with pytest.raises(InvalidPriceDataError):
            raise_invalid_data()

    def test_catch_all_market_data_errors(self) -> None:
        """Should be able to catch all market data errors with base class."""

        def raise_any_market_data_error() -> None:
            raise TickerNotFoundError("XYZ")

        with pytest.raises(MarketDataError):
            raise_any_market_data_error()


class TestPartialPricingError:
    """Phase J / Task #214 — PartialPricingError construction + introspection."""

    def test_construction_with_defaults(self) -> None:
        """Default ``retry_after_seconds`` is 5; message includes symbols."""
        aapl, msft = Ticker("AAPL"), Ticker("MSFT")
        error = PartialPricingError(
            missing_tickers=[aapl, msft],
            failed_reason={
                aapl: "ticker_not_found",
                msft: "market_data_unavailable",
            },
        )
        assert error.missing_tickers == [aapl, msft]
        assert error.failed_reason[aapl] == "ticker_not_found"
        assert error.failed_reason[msft] == "market_data_unavailable"
        assert error.retry_after_seconds == 5
        assert "AAPL" in error.message
        assert "MSFT" in error.message

    def test_custom_retry_after(self) -> None:
        """``retry_after_seconds`` is configurable."""
        error = PartialPricingError(
            missing_tickers=[Ticker("AAPL")],
            failed_reason={Ticker("AAPL"): "market_data_unavailable"},
            retry_after_seconds=30,
        )
        assert error.retry_after_seconds == 30

    def test_inheritance(self) -> None:
        """Inherits from MarketDataError for broad-except blocks."""
        error = PartialPricingError(
            missing_tickers=[Ticker("AAPL")],
            failed_reason={Ticker("AAPL"): "ticker_not_found"},
        )
        assert isinstance(error, MarketDataError)
