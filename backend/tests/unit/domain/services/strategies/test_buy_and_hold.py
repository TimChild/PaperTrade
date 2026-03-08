"""Tests for BuyAndHoldStrategy."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.domain.services.strategies.buy_and_hold import BuyAndHoldStrategy
from zebu.domain.value_objects.trade_signal import TradeAction


class TestBuyAndHoldStrategy:
    """Tests for BuyAndHoldStrategy signal generation."""

    def _make_price_map(self) -> dict:  # type: ignore[type-arg]
        """Return an empty price map (not used by BuyAndHold)."""
        return {}

    def test_first_call_generates_buy_signals(self) -> None:
        """On the first call, one BUY signal per ticker is generated."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL", "GOOGL"],
            allocation={"AAPL": 0.6, "GOOGL": 0.4},
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 2
        tickers = {s.ticker for s in signals}
        assert tickers == {"AAPL", "GOOGL"}
        actions = {s.action for s in signals}
        assert actions == {TradeAction.BUY}

    def test_buy_signal_amounts_match_allocation(self) -> None:
        """Each BUY signal amount = cash_balance × allocation fraction."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL", "GOOGL"],
            allocation={"AAPL": 0.6, "GOOGL": 0.4},
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        signal_map = {s.ticker: s for s in signals}
        assert signal_map["AAPL"].amount == Decimal("6000")
        assert signal_map["GOOGL"].amount == Decimal("4000")

    def test_subsequent_calls_return_empty(self) -> None:
        """After the first buy, all subsequent calls return no signals."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL"],
            allocation={"AAPL": 1.0},
        )

        # First call
        first = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("1000"),
            holdings={},
        )
        assert len(first) == 1

        # All subsequent calls
        for _ in range(5):
            subsequent = strategy.generate_signals(
                current_date=date(2024, 1, 3),
                price_map=self._make_price_map(),
                cash_balance=Decimal("1000"),
                holdings={"AAPL": Decimal("10")},
            )
            assert subsequent == []

    def test_zero_cash_generates_no_signals(self) -> None:
        """If cash_balance is zero, no signals are generated."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL"],
            allocation={"AAPL": 1.0},
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("0"),
            holdings={},
        )
        # amount = 0, so it should be skipped
        assert signals == []

    def test_zero_allocation_skips_ticker(self) -> None:
        """Tickers with 0% allocation produce no signals."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL", "GOOGL"],
            allocation={"AAPL": 1.0, "GOOGL": 0.0},
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 1
        assert signals[0].ticker == "AAPL"

    def test_missing_allocation_ticker_is_skipped(self) -> None:
        """Tickers not in the allocation dict are skipped."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL", "GOOGL"],
            allocation={"AAPL": 0.6},  # GOOGL not included
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 1
        assert signals[0].ticker == "AAPL"

    def test_signal_date_matches_current_date(self) -> None:
        """Signal date matches the current_date argument."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL"],
            allocation={"AAPL": 1.0},
        )
        today = date(2024, 6, 15)

        signals = strategy.generate_signals(
            current_date=today,
            price_map=self._make_price_map(),
            cash_balance=Decimal("1000"),
            holdings={},
        )

        assert signals[0].signal_date == today

    def test_not_bought_initially(self) -> None:
        """Strategy starts with _has_bought = False."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL"],
            allocation={"AAPL": 1.0},
        )
        assert strategy._has_bought is False

    def test_has_bought_set_after_first_call(self) -> None:
        """After first successful call, _has_bought is True."""
        strategy = BuyAndHoldStrategy(
            tickers=["AAPL"],
            allocation={"AAPL": 1.0},
        )
        strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("1000"),
            holdings={},
        )
        assert strategy._has_bought is True
