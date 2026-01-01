"""Tests for PricePoint DTO."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from papertrade.application.dtos.price_point import PricePoint
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.ticker import Ticker


class TestPricePointConstruction:
    """Tests for PricePoint construction and validation."""

    def test_valid_construction_with_required_fields(self) -> None:
        """Should create PricePoint with all required fields."""
        ticker = Ticker("AAPL")
        price = Money(Decimal("150.25"), "USD")
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)

        price_point = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        assert price_point.ticker.symbol == ticker.symbol
        assert price_point.price.amount == price.amount
        assert price_point.timestamp == timestamp
        assert price_point.source == "alpha_vantage"
        assert price_point.interval == "real-time"
        assert price_point.open is None
        assert price_point.high is None
        assert price_point.low is None
        assert price_point.close is None
        assert price_point.volume is None

    def test_valid_construction_with_ohlcv_data(self) -> None:
        """Should create PricePoint with OHLCV data."""
        ticker = Ticker("AAPL")
        price = Money(Decimal("150.25"), "USD")
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)
        open_price = Money(Decimal("149.00"), "USD")
        high_price = Money(Decimal("151.50"), "USD")
        low_price = Money(Decimal("148.50"), "USD")
        close_price = Money(Decimal("150.25"), "USD")
        volume = 1000000

        price_point = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="1day",
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )

        assert price_point.open == open_price
        assert price_point.high == high_price
        assert price_point.low == low_price
        assert price_point.close == close_price
        assert price_point.volume == volume

    def test_invalid_source(self) -> None:
        """Should raise ValueError for invalid source."""
        with pytest.raises(ValueError, match="Invalid source"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="invalid_source",
                interval="real-time",
            )

    def test_invalid_interval(self) -> None:
        """Should raise ValueError for invalid interval."""
        with pytest.raises(ValueError, match="Invalid interval"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="alpha_vantage",
                interval="invalid_interval",
            )

    def test_naive_timestamp(self) -> None:
        """Should raise ValueError for naive datetime (no timezone)."""
        with pytest.raises(ValueError, match="timezone-aware"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30),  # No timezone
                source="alpha_vantage",
                interval="real-time",
            )

    def test_non_utc_timestamp(self) -> None:
        """Should raise ValueError for non-UTC timezone."""
        from datetime import timezone as tz

        # Create a non-UTC timezone (UTC+5)
        non_utc = tz(timedelta(hours=5))
        with pytest.raises(ValueError, match="must be in UTC"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=non_utc),
                source="alpha_vantage",
                interval="real-time",
            )

    def test_non_positive_price(self) -> None:
        """Should raise ValueError for non-positive price."""
        with pytest.raises(ValueError, match="must be positive"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("0.00"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="alpha_vantage",
                interval="real-time",
            )

    def test_mismatched_currencies(self) -> None:
        """Should raise ValueError when Money values have different currencies."""
        with pytest.raises(ValueError, match="same currency"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("149.00"), "EUR"),  # Different currency
            )

    def test_invalid_ohlcv_low_greater_than_open(self) -> None:
        """Should raise ValueError when low > open."""
        with pytest.raises(ValueError, match="Low price.*cannot be greater than"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("149.00"), "USD"),
                high=Money(Decimal("151.50"), "USD"),
                low=Money(Decimal("150.00"), "USD"),  # low > open (149.00)
            )

    def test_invalid_ohlcv_open_greater_than_high(self) -> None:
        """Should raise ValueError when open > high."""
        with pytest.raises(ValueError, match="Open price.*cannot be greater than"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("152.00"), "USD"),  # open > high (151.50)
                high=Money(Decimal("151.50"), "USD"),
                low=Money(Decimal("148.50"), "USD"),
            )

    def test_invalid_ohlcv_low_greater_than_close(self) -> None:
        """Should raise ValueError when low > close."""
        with pytest.raises(ValueError, match="Low price.*cannot be greater than"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="alpha_vantage",
                interval="1day",
                high=Money(Decimal("151.50"), "USD"),
                low=Money(Decimal("151.00"), "USD"),  # low > close (150.25)
                close=Money(Decimal("150.25"), "USD"),
            )

    def test_invalid_ohlcv_close_greater_than_high(self) -> None:
        """Should raise ValueError when close > high."""
        with pytest.raises(ValueError, match="Close price.*cannot be greater than"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="alpha_vantage",
                interval="1day",
                high=Money(Decimal("151.50"), "USD"),
                low=Money(Decimal("148.50"), "USD"),
                close=Money(Decimal("152.00"), "USD"),  # close > high (151.50)
            )

    def test_negative_volume(self) -> None:
        """Should raise ValueError for negative volume."""
        with pytest.raises(ValueError, match="Volume must be non-negative"):
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="alpha_vantage",
                interval="1day",
                volume=-1000,
            )

    def test_zero_volume_allowed(self) -> None:
        """Should allow zero volume."""
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="alpha_vantage",
            interval="1day",
            volume=0,
        )
        assert price_point.volume == 0


class TestPricePointIsStale:
    """Tests for PricePoint.is_stale() method."""

    def test_fresh_price(self) -> None:
        """Should return False for fresh price."""
        # Create price 5 minutes ago
        timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        # Check if stale with 15 minute threshold
        assert not price_point.is_stale(timedelta(minutes=15))

    def test_stale_price(self) -> None:
        """Should return True for stale price."""
        # Create price 20 minutes ago
        timestamp = datetime.now(timezone.utc) - timedelta(minutes=20)
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        # Check if stale with 15 minute threshold
        assert price_point.is_stale(timedelta(minutes=15))

    def test_exactly_at_threshold(self) -> None:
        """Should return True when exactly at threshold (stale)."""
        # Create price exactly 15 minutes ago
        timestamp = datetime.now(timezone.utc) - timedelta(minutes=15)
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        # Should be stale (age >= max_age)
        assert price_point.is_stale(timedelta(minutes=15))


class TestPricePointWithSource:
    """Tests for PricePoint.with_source() method."""

    def test_change_source(self) -> None:
        """Should create new PricePoint with different source."""
        original = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="alpha_vantage",
            interval="real-time",
        )

        cached = original.with_source("cache")

        # Original should be unchanged (immutable)
        assert original.source == "alpha_vantage"
        # New instance should have new source
        assert cached.source == "cache"
        # Other fields should be identical
        assert cached.ticker == original.ticker
        assert cached.price == original.price
        assert cached.timestamp == original.timestamp
        assert cached.interval == original.interval

    def test_invalid_new_source(self) -> None:
        """Should raise ValueError for invalid new source."""
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="alpha_vantage",
            interval="real-time",
        )

        with pytest.raises(ValueError, match="Invalid source"):
            price_point.with_source("invalid_source")

    def test_preserves_ohlcv_data(self) -> None:
        """Should preserve OHLCV data when changing source."""
        original = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="alpha_vantage",
            interval="1day",
            open=Money(Decimal("149.00"), "USD"),
            high=Money(Decimal("151.50"), "USD"),
            low=Money(Decimal("148.50"), "USD"),
            close=Money(Decimal("150.25"), "USD"),
            volume=1000000,
        )

        cached = original.with_source("cache")

        assert cached.open == original.open
        assert cached.high == original.high
        assert cached.low == original.low
        assert cached.close == original.close
        assert cached.volume == original.volume


class TestPricePointEquality:
    """Tests for PricePoint equality semantics."""

    def test_equal_price_points(self) -> None:
        """Should be equal when all key fields match."""
        ticker = Ticker("AAPL")
        price = Money(Decimal("150.25"), "USD")
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)

        pp1 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        pp2 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        assert pp1 == pp2

    def test_different_ticker(self) -> None:
        """Should not be equal when ticker differs."""
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)
        price = Money(Decimal("150.25"), "USD")

        pp1 = PricePoint(
            ticker=Ticker("AAPL"),
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        pp2 = PricePoint(
            ticker=Ticker("GOOGL"),
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        assert pp1 != pp2

    def test_different_price(self) -> None:
        """Should not be equal when price differs."""
        ticker = Ticker("AAPL")
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)

        pp1 = PricePoint(
            ticker=ticker,
            price=Money(Decimal("150.25"), "USD"),
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        pp2 = PricePoint(
            ticker=ticker,
            price=Money(Decimal("150.50"), "USD"),
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        assert pp1 != pp2

    def test_different_timestamp(self) -> None:
        """Should not be equal when timestamp differs."""
        ticker = Ticker("AAPL")
        price = Money(Decimal("150.25"), "USD")

        pp1 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="alpha_vantage",
            interval="real-time",
        )

        pp2 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=datetime(2025, 12, 28, 14, 31, tzinfo=timezone.utc),
            source="alpha_vantage",
            interval="real-time",
        )

        assert pp1 != pp2

    def test_different_source(self) -> None:
        """Should not be equal when source differs."""
        ticker = Ticker("AAPL")
        price = Money(Decimal("150.25"), "USD")
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)

        pp1 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        pp2 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="cache",
            interval="real-time",
        )

        assert pp1 != pp2

    def test_different_interval(self) -> None:
        """Should not be equal when interval differs."""
        ticker = Ticker("AAPL")
        price = Money(Decimal("150.25"), "USD")
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)

        pp1 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )

        pp2 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="1day",
        )

        assert pp1 != pp2

    def test_ohlcv_not_in_equality(self) -> None:
        """Should be equal even when OHLCV data differs (not part of equality)."""
        ticker = Ticker("AAPL")
        price = Money(Decimal("150.25"), "USD")
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)

        pp1 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="1day",
            volume=1000000,
        )

        pp2 = PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="alpha_vantage",
            interval="1day",
            volume=2000000,
        )

        # OHLCV fields are not part of equality
        assert pp1 == pp2


class TestPricePointStringRepresentation:
    """Tests for PricePoint string representation."""

    def test_str_format(self) -> None:
        """Should format as specified."""
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="alpha_vantage",
            interval="real-time",
        )

        expected = "AAPL @ $150.25 as of 2025-12-28 14:30:00 UTC (source: alpha_vantage)"
        assert str(price_point) == expected

    def test_repr_format(self) -> None:
        """Should have proper repr."""
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="alpha_vantage",
            interval="real-time",
        )

        repr_str = repr(price_point)
        assert "PricePoint(" in repr_str
        assert "ticker=" in repr_str
        assert "price=" in repr_str
        assert "timestamp=" in repr_str
        assert "source='alpha_vantage'" in repr_str
        assert "interval='real-time'" in repr_str
