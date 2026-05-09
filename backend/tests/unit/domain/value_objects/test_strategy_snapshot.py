"""Tests for the StrategySnapshot value object."""

from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    DcaParameters,
    MaCrossoverParameters,
)
from zebu.domain.value_objects.strategy_snapshot import StrategySnapshot
from zebu.domain.value_objects.strategy_type import StrategyType


class TestStrategySnapshotRoundTrip:
    """JSON round-trip behaviour for each strategy type."""

    def test_buy_and_hold_round_trip(self) -> None:
        """BUY_AND_HOLD snapshot survives to_dict / from_dict."""
        snapshot = StrategySnapshot(
            strategy_id=uuid4(),
            name="Hold AAPL",
            strategy_type=StrategyType.BUY_AND_HOLD,
            tickers=("AAPL",),
            parameters=BuyAndHoldParameters(allocation={"AAPL": Decimal("1")}),
        )
        reconstructed = StrategySnapshot.from_dict(snapshot.to_dict())
        assert reconstructed == snapshot

    def test_dca_round_trip(self) -> None:
        """DCA snapshot survives to_dict / from_dict."""
        snapshot = StrategySnapshot(
            strategy_id=uuid4(),
            name="Weekly VTI",
            strategy_type=StrategyType.DOLLAR_COST_AVERAGING,
            tickers=("VTI",),
            parameters=DcaParameters(
                frequency_days=7,
                amount_per_period=Decimal("250.00"),
                allocation={"VTI": Decimal("1")},
            ),
        )
        reconstructed = StrategySnapshot.from_dict(snapshot.to_dict())
        assert reconstructed == snapshot

    def test_ma_crossover_round_trip(self) -> None:
        """MA crossover snapshot survives to_dict / from_dict."""
        snapshot = StrategySnapshot(
            strategy_id=uuid4(),
            name="Golden Cross",
            strategy_type=StrategyType.MOVING_AVERAGE_CROSSOVER,
            tickers=("SPY",),
            parameters=MaCrossoverParameters(
                fast_window=20,
                slow_window=50,
                invest_fraction=Decimal("0.5"),
            ),
        )
        reconstructed = StrategySnapshot.from_dict(snapshot.to_dict())
        assert reconstructed == snapshot


class TestStrategySnapshotLegacyShape:
    """Backward-compatible reads of pre-refactor snapshot rows.

    Pre-refactor BacktestRun.strategy_snapshot was a free-form dict whose
    ``parameters`` carried raw floats / ints / strings. ``from_dict`` must
    still parse those rows so existing backtest history stays accessible.
    """

    def test_legacy_buy_and_hold_with_float_allocation(self) -> None:
        """Legacy BUY_AND_HOLD snapshot with float allocation parses cleanly."""
        legacy = {
            "id": str(uuid4()),
            "name": "Old Strategy",
            "strategy_type": "BUY_AND_HOLD",
            "tickers": ["AAPL"],
            "parameters": {"allocation": {"AAPL": 1.0}},
        }
        snapshot = StrategySnapshot.from_dict(legacy)
        assert snapshot.strategy_type == StrategyType.BUY_AND_HOLD
        assert isinstance(snapshot.parameters, BuyAndHoldParameters)

    def test_legacy_dca_with_decimal_amount(self) -> None:
        """Legacy DCA snapshot with raw Decimal amount parses cleanly."""
        legacy = {
            "id": str(uuid4()),
            "name": "Old DCA",
            "strategy_type": "DOLLAR_COST_AVERAGING",
            "tickers": ["VTI"],
            "parameters": {
                "frequency_days": 30,
                "amount_per_period": Decimal("250"),
                "allocation": {"VTI": 1.0},
            },
        }
        snapshot = StrategySnapshot.from_dict(legacy)
        assert isinstance(snapshot.parameters, DcaParameters)


class TestStrategySnapshotFromDictErrors:
    """Validation errors raised by StrategySnapshot.from_dict."""

    def test_unknown_strategy_type_raises(self) -> None:
        """An unknown strategy_type string raises InvalidStrategyError."""
        with pytest.raises(InvalidStrategyError, match="unknown strategy_type"):
            StrategySnapshot.from_dict(
                {
                    "id": str(uuid4()),
                    "name": "test",
                    "strategy_type": "WAT",
                    "tickers": ["AAPL"],
                    "parameters": {"allocation": {"AAPL": "1"}},
                }
            )

    def test_missing_parameters_raises(self) -> None:
        """A snapshot missing 'parameters' raises InvalidStrategyError."""
        with pytest.raises(InvalidStrategyError, match="missing 'parameters'"):
            StrategySnapshot.from_dict(
                {
                    "id": str(uuid4()),
                    "name": "test",
                    "strategy_type": "BUY_AND_HOLD",
                    "tickers": ["AAPL"],
                }
            )

    def test_missing_strategy_type_raises(self) -> None:
        """A snapshot missing 'strategy_type' raises InvalidStrategyError."""
        with pytest.raises(InvalidStrategyError, match="missing 'strategy_type'"):
            StrategySnapshot.from_dict(
                {
                    "id": str(uuid4()),
                    "parameters": {"allocation": {"AAPL": "1"}},
                }
            )
