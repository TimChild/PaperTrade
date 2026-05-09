"""Tests for typed StrategyParameters value objects.

Covers per-type construction invariants and JSON round-trip behavior for the
discriminated union of ``BuyAndHoldParameters``, ``DcaParameters``, and
``MaCrossoverParameters``.
"""

from collections.abc import Mapping
from decimal import Decimal

import pytest

from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    DcaParameters,
    MaCrossoverParameters,
    parameters_for_type,
    parameters_from_dict,
)
from zebu.domain.value_objects.strategy_type import StrategyType


class TestBuyAndHoldParameters:
    """Construction and JSON round-trip for BuyAndHoldParameters."""

    def test_valid_construction(self) -> None:
        """Construction succeeds when allocation sums to 1.0."""
        params = BuyAndHoldParameters(
            allocation={"AAPL": Decimal("0.6"), "MSFT": Decimal("0.4")}
        )
        assert params.allocation == {
            "AAPL": Decimal("0.6"),
            "MSFT": Decimal("0.4"),
        }

    def test_allocation_must_sum_to_one(self) -> None:
        """Allocation that does not sum to 1.0 within tolerance is rejected."""
        with pytest.raises(InvalidStrategyError, match="must sum to 1.0"):
            BuyAndHoldParameters(allocation={"AAPL": Decimal("0.5")})

    def test_allocation_with_tolerance_accepted(self) -> None:
        """Allocation summing to 1.0 ± 0.001 is accepted."""
        params = BuyAndHoldParameters(allocation={"AAPL": Decimal("0.9995")})
        assert params.allocation == {"AAPL": Decimal("0.9995")}

    def test_negative_fraction_rejected(self) -> None:
        """Negative allocation fractions are rejected."""
        with pytest.raises(InvalidStrategyError, match="must be between 0 and 1"):
            BuyAndHoldParameters(
                allocation={"AAPL": Decimal("1.5"), "MSFT": Decimal("-0.5")}
            )

    def test_empty_allocation_rejected(self) -> None:
        """Empty allocation mapping is rejected."""
        with pytest.raises(InvalidStrategyError, match="non-empty mapping"):
            BuyAndHoldParameters(allocation={})

    def test_round_trip_via_to_dict_and_from_dict(self) -> None:
        """to_dict → from_dict yields an equivalent instance."""
        original = BuyAndHoldParameters(
            allocation={"AAPL": Decimal("0.7"), "MSFT": Decimal("0.3")}
        )
        as_dict = original.to_dict()
        reconstructed = BuyAndHoldParameters.from_dict(_as_mapping(as_dict))
        assert reconstructed == original

    def test_from_dict_accepts_legacy_float_values(self) -> None:
        """from_dict accepts legacy float-shaped JSON without losing precision."""
        legacy = {"allocation": {"AAPL": 0.5, "MSFT": 0.5}}
        params = BuyAndHoldParameters.from_dict(legacy)
        assert params.allocation == {
            "AAPL": Decimal("0.5"),
            "MSFT": Decimal("0.5"),
        }

    def test_from_dict_rejects_non_mapping_allocation(self) -> None:
        """from_dict rejects non-mapping allocation values."""
        with pytest.raises(InvalidStrategyError, match="non-empty mapping"):
            BuyAndHoldParameters.from_dict({"allocation": ["AAPL"]})


class TestDcaParameters:
    """Construction and JSON round-trip for DcaParameters."""

    def test_valid_construction(self) -> None:
        """All required fields produce a valid DcaParameters."""
        params = DcaParameters(
            frequency_days=30,
            amount_per_period=Decimal("100.50"),
            allocation={"VOO": Decimal("1")},
        )
        assert params.frequency_days == 30
        assert params.amount_per_period == Decimal("100.50")

    def test_frequency_days_below_one_rejected(self) -> None:
        """frequency_days must be at least 1."""
        with pytest.raises(InvalidStrategyError, match="between 1 and 365"):
            DcaParameters(
                frequency_days=0,
                amount_per_period=Decimal("100"),
                allocation={"VOO": Decimal("1")},
            )

    def test_frequency_days_above_365_rejected(self) -> None:
        """frequency_days must not exceed 365."""
        with pytest.raises(InvalidStrategyError, match="between 1 and 365"):
            DcaParameters(
                frequency_days=400,
                amount_per_period=Decimal("100"),
                allocation={"VOO": Decimal("1")},
            )

    def test_amount_per_period_must_be_positive(self) -> None:
        """amount_per_period must be > 0."""
        with pytest.raises(InvalidStrategyError, match="must be > 0"):
            DcaParameters(
                frequency_days=30,
                amount_per_period=Decimal("0"),
                allocation={"VOO": Decimal("1")},
            )

    def test_round_trip_via_to_dict_and_from_dict(self) -> None:
        """to_dict → from_dict yields an equivalent instance."""
        original = DcaParameters(
            frequency_days=14,
            amount_per_period=Decimal("250.25"),
            allocation={"VTI": Decimal("0.5"), "BND": Decimal("0.5")},
        )
        as_dict = original.to_dict()
        reconstructed = DcaParameters.from_dict(_as_mapping(as_dict))
        assert reconstructed == original

    def test_from_dict_rejects_missing_amount(self) -> None:
        """from_dict rejects payloads missing amount_per_period."""
        with pytest.raises(InvalidStrategyError, match="amount_per_period"):
            DcaParameters.from_dict({"frequency_days": 30, "allocation": {"VOO": "1"}})

    def test_from_dict_rejects_boolean_frequency(self) -> None:
        """from_dict treats bool as invalid for frequency_days."""
        with pytest.raises(InvalidStrategyError, match="frequency_days"):
            DcaParameters.from_dict(
                {
                    "frequency_days": True,
                    "amount_per_period": "100",
                    "allocation": {"VOO": "1"},
                }
            )


class TestMaCrossoverParameters:
    """Construction and JSON round-trip for MaCrossoverParameters."""

    def test_valid_construction(self) -> None:
        """fast_window < slow_window with valid invest_fraction works."""
        params = MaCrossoverParameters(
            fast_window=10,
            slow_window=20,
            invest_fraction=Decimal("0.5"),
        )
        assert params.fast_window == 10
        assert params.slow_window == 20

    def test_fast_window_must_be_less_than_slow_window(self) -> None:
        """fast_window must be strictly less than slow_window."""
        with pytest.raises(InvalidStrategyError, match="less than 'slow_window'"):
            MaCrossoverParameters(
                fast_window=50,
                slow_window=10,
                invest_fraction=Decimal("0.5"),
            )

    def test_window_below_two_rejected(self) -> None:
        """Window below 2 is rejected."""
        with pytest.raises(InvalidStrategyError, match="between 2 and 200"):
            MaCrossoverParameters(
                fast_window=1,
                slow_window=10,
                invest_fraction=Decimal("0.5"),
            )

    def test_window_above_200_rejected(self) -> None:
        """Window above 200 is rejected."""
        with pytest.raises(InvalidStrategyError, match="between 2 and 200"):
            MaCrossoverParameters(
                fast_window=10,
                slow_window=300,
                invest_fraction=Decimal("0.5"),
            )

    def test_invest_fraction_zero_rejected(self) -> None:
        """invest_fraction must be strictly > 0."""
        with pytest.raises(InvalidStrategyError, match="invest_fraction"):
            MaCrossoverParameters(
                fast_window=10,
                slow_window=20,
                invest_fraction=Decimal("0"),
            )

    def test_invest_fraction_above_one_rejected(self) -> None:
        """invest_fraction must not exceed 1.0."""
        with pytest.raises(InvalidStrategyError, match="invest_fraction"):
            MaCrossoverParameters(
                fast_window=10,
                slow_window=20,
                invest_fraction=Decimal("1.5"),
            )

    def test_round_trip_via_to_dict_and_from_dict(self) -> None:
        """to_dict → from_dict yields an equivalent instance."""
        original = MaCrossoverParameters(
            fast_window=12,
            slow_window=26,
            invest_fraction=Decimal("0.75"),
        )
        as_dict = original.to_dict()
        reconstructed = MaCrossoverParameters.from_dict(_as_mapping(as_dict))
        assert reconstructed == original


class TestParametersFromDict:
    """Discriminated dispatch via parameters_from_dict."""

    def test_buy_and_hold_dispatch(self) -> None:
        """BUY_AND_HOLD type produces BuyAndHoldParameters."""
        params = parameters_from_dict(
            StrategyType.BUY_AND_HOLD,
            {"allocation": {"AAPL": "1"}},
        )
        assert isinstance(params, BuyAndHoldParameters)

    def test_dca_dispatch(self) -> None:
        """DCA type produces DcaParameters."""
        params = parameters_from_dict(
            StrategyType.DOLLAR_COST_AVERAGING,
            {
                "frequency_days": 7,
                "amount_per_period": "200",
                "allocation": {"AAPL": "1"},
            },
        )
        assert isinstance(params, DcaParameters)

    def test_ma_crossover_dispatch(self) -> None:
        """MOVING_AVERAGE_CROSSOVER type produces MaCrossoverParameters."""
        params = parameters_from_dict(
            StrategyType.MOVING_AVERAGE_CROSSOVER,
            {
                "fast_window": 5,
                "slow_window": 20,
                "invest_fraction": "0.5",
            },
        )
        assert isinstance(params, MaCrossoverParameters)

    def test_parameters_for_type_matches_concrete_class(self) -> None:
        """parameters_for_type returns True for matching pairs."""
        bh = BuyAndHoldParameters(allocation={"AAPL": Decimal("1")})
        assert parameters_for_type(StrategyType.BUY_AND_HOLD, bh)
        assert not parameters_for_type(StrategyType.DOLLAR_COST_AVERAGING, bh)


def _as_mapping(value: dict[str, object]) -> Mapping[str, object]:
    """Coerce dict[str, object] into a Mapping for type-checker friendliness."""
    return value
