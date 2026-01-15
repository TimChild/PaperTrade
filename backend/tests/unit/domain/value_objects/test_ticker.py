"""Tests for Ticker value object."""

import pytest

from zebu.domain.exceptions import InvalidTickerError
from zebu.domain.value_objects.ticker import Ticker


class TestTickerConstruction:
    """Tests for Ticker construction and validation."""

    def test_valid_single_letter_ticker(self) -> None:
        """Should create Ticker with single letter symbol."""
        ticker = Ticker("F")
        assert ticker.symbol == "F"

    def test_valid_four_letter_ticker(self) -> None:
        """Should create Ticker with four letter symbol."""
        ticker = Ticker("AAPL")
        assert ticker.symbol == "AAPL"

    def test_valid_five_letter_ticker(self) -> None:
        """Should create Ticker with five letter symbol (max length)."""
        ticker = Ticker("GOOGL")
        assert ticker.symbol == "GOOGL"

    def test_lowercase_converted_to_uppercase(self) -> None:
        """Should convert lowercase to uppercase."""
        ticker = Ticker("aapl")
        assert ticker.symbol == "AAPL"

    def test_mixed_case_converted_to_uppercase(self) -> None:
        """Should convert mixed case to uppercase."""
        ticker = Ticker("AaPl")
        assert ticker.symbol == "AAPL"

    def test_invalid_empty_string(self) -> None:
        """Should raise error for empty string."""
        with pytest.raises(InvalidTickerError, match="1 to 5 characters"):
            Ticker("")

    def test_invalid_whitespace_only(self) -> None:
        """Should raise error for whitespace only."""
        with pytest.raises(InvalidTickerError, match="1 to 5 characters"):
            Ticker("   ")

    def test_invalid_too_long(self) -> None:
        """Should raise error for symbol longer than 5 characters."""
        with pytest.raises(InvalidTickerError, match="1 to 5 characters"):
            Ticker("GOOGLE")

    def test_invalid_contains_numbers(self) -> None:
        """Should raise error for symbols with numbers."""
        with pytest.raises(InvalidTickerError, match="only uppercase letters"):
            Ticker("APL12")

    def test_invalid_contains_special_characters(self) -> None:
        """Should raise error for symbols with special characters."""
        with pytest.raises(InvalidTickerError, match="only uppercase letters"):
            Ticker("APL-B")

    def test_invalid_contains_spaces(self) -> None:
        """Should raise error for symbols with spaces."""
        with pytest.raises(InvalidTickerError, match="only uppercase letters"):
            Ticker("A PL")


class TestTickerEquality:
    """Tests for Ticker equality semantics."""

    def test_equality_same_symbol(self) -> None:
        """Two tickers with same symbol should be equal."""
        t1 = Ticker("AAPL")
        t2 = Ticker("AAPL")
        assert t1 == t2

    def test_equality_case_insensitive(self) -> None:
        """Equality should be case-insensitive."""
        t1 = Ticker("AAPL")
        t2 = Ticker("aapl")
        assert t1 == t2

    def test_inequality_different_symbols(self) -> None:
        """Tickers with different symbols should not be equal."""
        t1 = Ticker("AAPL")
        t2 = Ticker("MSFT")
        assert t1 != t2

    def test_hashable(self) -> None:
        """Ticker should be usable as dict key."""
        t1 = Ticker("AAPL")
        t2 = Ticker("MSFT")
        ticker_dict = {t1: "Apple", t2: "Microsoft"}
        assert ticker_dict[Ticker("AAPL")] == "Apple"
        assert ticker_dict[Ticker("MSFT")] == "Microsoft"

    def test_hash_consistency(self) -> None:
        """Equal tickers should have same hash."""
        t1 = Ticker("AAPL")
        t2 = Ticker("aapl")
        assert hash(t1) == hash(t2)


class TestTickerImmutability:
    """Tests that Ticker is immutable."""

    def test_cannot_modify_symbol(self) -> None:
        """Should not be able to modify symbol after construction."""
        ticker = Ticker("AAPL")
        with pytest.raises(AttributeError):
            ticker.symbol = "MSFT"  # type: ignore


class TestTickerStringRepresentation:
    """Tests for Ticker string representation."""

    def test_str_representation(self) -> None:
        """Should return symbol as string."""
        ticker = Ticker("AAPL")
        assert str(ticker) == "AAPL"

    def test_repr_representation(self) -> None:
        """Should have useful repr."""
        ticker = Ticker("AAPL")
        assert "Ticker" in repr(ticker)
        assert "AAPL" in repr(ticker)
