"""Tests for Ticker value object."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from papertrade.domain.value_objects import Ticker


class TestTickerCreation:
    """Test Ticker value object creation and validation."""

    def test_create_ticker_uppercase(self) -> None:
        """Test creating ticker with uppercase symbol."""
        ticker = Ticker("AAPL")
        assert ticker.symbol == "AAPL"

    def test_create_ticker_lowercase_normalizes(self) -> None:
        """Test creating ticker with lowercase normalizes to uppercase."""
        ticker = Ticker("aapl")
        assert ticker.symbol == "AAPL"

    def test_create_ticker_mixed_case_normalizes(self) -> None:
        """Test creating ticker with mixed case normalizes to uppercase."""
        ticker = Ticker("AaPl")
        assert ticker.symbol == "AAPL"

    def test_create_single_letter_ticker(self) -> None:
        """Test creating single letter ticker."""
        ticker = Ticker("X")
        assert ticker.symbol == "X"

    def test_create_five_letter_ticker(self) -> None:
        """Test creating five letter ticker."""
        ticker = Ticker("GOOGL")
        assert ticker.symbol == "GOOGL"

    def test_create_ticker_too_short(self) -> None:
        """Test that empty ticker raises error."""
        with pytest.raises(ValueError, match="1-5 characters"):
            Ticker("")

    def test_create_ticker_too_long(self) -> None:
        """Test that ticker longer than 5 characters raises error."""
        with pytest.raises(ValueError, match="1-5 characters"):
            Ticker("TOOLONG")

    def test_create_ticker_with_numbers(self) -> None:
        """Test that ticker with numbers raises error."""
        with pytest.raises(ValueError, match="only letters"):
            Ticker("AAP1")

    def test_create_ticker_with_special_chars(self) -> None:
        """Test that ticker with special characters raises error."""
        with pytest.raises(ValueError, match="only letters"):
            Ticker("AA-PL")

    def test_ticker_is_immutable(self) -> None:
        """Test that Ticker is immutable."""
        ticker = Ticker("AAPL")
        with pytest.raises(Exception):  # FrozenInstanceError
            ticker.symbol = "GOOGL"  # type: ignore


class TestTickerComparison:
    """Test Ticker comparison operations."""

    def test_ticker_equality(self) -> None:
        """Test ticker equality."""
        t1 = Ticker("AAPL")
        t2 = Ticker("aapl")  # Should normalize to AAPL
        t3 = Ticker("GOOGL")
        assert t1 == t2
        assert t1 != t3

    def test_ticker_hash(self) -> None:
        """Test that equal tickers have the same hash."""
        t1 = Ticker("AAPL")
        t2 = Ticker("aapl")
        assert hash(t1) == hash(t2)

    def test_ticker_in_set(self) -> None:
        """Test that tickers can be used in sets."""
        tickers = {Ticker("AAPL"), Ticker("aapl"), Ticker("GOOGL")}
        # Should only have 2 items (AAPL appears twice)
        assert len(tickers) == 2

    def test_ticker_as_dict_key(self) -> None:
        """Test that tickers can be used as dict keys."""
        prices = {Ticker("AAPL"): 150.0, Ticker("GOOGL"): 2800.0}
        assert prices[Ticker("aapl")] == 150.0


class TestTickerStringRepresentation:
    """Test Ticker string representations."""

    def test_str(self) -> None:
        """Test string representation."""
        ticker = Ticker("AAPL")
        assert str(ticker) == "AAPL"

    def test_repr(self) -> None:
        """Test developer-friendly representation."""
        ticker = Ticker("AAPL")
        assert "Ticker" in repr(ticker)
        assert "AAPL" in repr(ticker)


class TestTickerPropertyBased:
    """Property-based tests for Ticker using Hypothesis."""

    @given(
        symbol=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=5)
    )
    def test_valid_uppercase_symbols_accepted(self, symbol: str) -> None:
        """Test that any 1-5 uppercase letter string is accepted."""
        ticker = Ticker(symbol)
        assert ticker.symbol == symbol

    @given(
        symbol=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)
    )
    def test_lowercase_symbols_normalized(self, symbol: str) -> None:
        """Test that lowercase symbols are normalized to uppercase."""
        ticker = Ticker(symbol)
        assert ticker.symbol == symbol.upper()

    @given(
        symbol=st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            min_size=1,
            max_size=5,
        )
    )
    def test_normalization_is_idempotent(self, symbol: str) -> None:
        """Test that normalizing twice gives same result as normalizing once."""
        t1 = Ticker(symbol)
        t2 = Ticker(t1.symbol)
        assert t1 == t2
