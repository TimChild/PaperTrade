"""Unit tests for ConditionType and ConditionParams (Phase F-1).

Covers the discriminated-union pattern: per-type frozen dataclasses,
``params_from_dict`` factory, and the deliberate rejection of
``CUSTOM_RULE`` per the design doc Q1.

The tests focus on:

* Construction-time invariant checks (out-of-range values raise).
* JSON round-trip through ``to_dict`` / ``from_dict``.
* The factory's discriminator dispatch.
* ``params_match_type`` correctness for cross-type rejection by the
  trigger entity.

``EARNINGS_PROXIMITY`` and ``CUSTOM_RULE`` get smaller surface — earnings
is straightforward (the calendar port lands in F-4 so we only test the
parameter shape), CUSTOM_RULE is intentionally unimplemented.
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from zebu.domain.exceptions import InvalidTriggerError
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trigger_condition import (
    CONDITION_PARAMS_SCHEMA_VERSION,
    ConditionType,
    CustomRuleParams,
    DrawdownMetric,
    DrawdownParams,
    EarningsParams,
    VolatilityParams,
    params_from_dict,
    params_match_type,
)

# ---------------------------------------------------------------------------
# DrawdownParams
# ---------------------------------------------------------------------------


class TestDrawdownParams:
    """DRAWDOWN_THRESHOLD parameter validation + round-trip."""

    def test_minimal_valid_construction(self) -> None:
        """Default metric is PORTFOLIO_TOTAL; all values within range."""
        params = DrawdownParams(
            threshold_pct=Decimal("5"),
            lookback_days=30,
        )
        assert params.threshold_pct == Decimal("5")
        assert params.lookback_days == 30
        assert params.metric is DrawdownMetric.PORTFOLIO_TOTAL

    def test_with_per_ticker_metric(self) -> None:
        """Explicit PER_TICKER metric is accepted."""
        params = DrawdownParams(
            threshold_pct=Decimal("10"),
            lookback_days=14,
            metric=DrawdownMetric.PER_TICKER,
        )
        assert params.metric is DrawdownMetric.PER_TICKER

    @pytest.mark.parametrize(
        "threshold",
        [Decimal("0"), Decimal("-1"), Decimal("100.01"), Decimal("1000")],
    )
    def test_threshold_pct_out_of_range_raises(self, threshold: Decimal) -> None:
        """threshold_pct must be in (0, 100]."""
        with pytest.raises(InvalidTriggerError, match="threshold_pct must be in"):
            DrawdownParams(threshold_pct=threshold, lookback_days=10)

    @pytest.mark.parametrize("lookback_days", [0, -5, 366, 1000])
    def test_lookback_days_out_of_range_raises(self, lookback_days: int) -> None:
        """lookback_days must be in [1, 365]."""
        with pytest.raises(InvalidTriggerError, match="lookback_days must be in"):
            DrawdownParams(
                threshold_pct=Decimal("5"),
                lookback_days=lookback_days,
            )

    def test_lookback_days_bool_rejected(self) -> None:
        """``True`` is an int subclass — must be rejected explicitly."""
        with pytest.raises(InvalidTriggerError, match="must be an integer"):
            DrawdownParams(
                threshold_pct=Decimal("5"),
                lookback_days=True,  # type: ignore[arg-type]
            )

    def test_threshold_pct_non_finite_rejected(self) -> None:
        """NaN / Inf are not finite Decimals — rejected."""
        with pytest.raises(InvalidTriggerError, match="finite"):
            DrawdownParams(
                threshold_pct=Decimal("NaN"),
                lookback_days=10,
            )

    def test_to_dict_round_trip(self) -> None:
        """Serialise -> from_dict produces an equal instance."""
        params = DrawdownParams(
            threshold_pct=Decimal("7.5"),
            lookback_days=21,
            metric=DrawdownMetric.PER_TICKER,
        )
        as_dict = params.to_dict()
        assert as_dict["schema_version"] == CONDITION_PARAMS_SCHEMA_VERSION
        assert as_dict["threshold_pct"] == "7.5"
        assert as_dict["lookback_days"] == 21
        assert as_dict["metric"] == "PER_TICKER"
        rebuilt = DrawdownParams.from_dict(as_dict)
        assert rebuilt == params

    def test_from_dict_missing_threshold_raises(self) -> None:
        """Missing threshold_pct surfaces a clear error."""
        with pytest.raises(InvalidTriggerError, match="threshold_pct"):
            DrawdownParams.from_dict({"lookback_days": 10})

    def test_from_dict_missing_lookback_raises(self) -> None:
        """Missing lookback_days surfaces a clear error."""
        with pytest.raises(InvalidTriggerError, match="lookback_days"):
            DrawdownParams.from_dict({"threshold_pct": "5"})

    def test_from_dict_unknown_metric_raises(self) -> None:
        """Unknown metric value is rejected with a list of valid options."""
        with pytest.raises(InvalidTriggerError, match="metric must be one of"):
            DrawdownParams.from_dict(
                {
                    "threshold_pct": "5",
                    "lookback_days": 10,
                    "metric": "WHATEVER",
                }
            )

    def test_from_dict_accepts_string_threshold(self) -> None:
        """Decimal-as-string round-trip works (the JSON column writes strings)."""
        params = DrawdownParams.from_dict(
            {"threshold_pct": "5.25", "lookback_days": 14}
        )
        assert params.threshold_pct == Decimal("5.25")

    def test_is_frozen(self) -> None:
        """DrawdownParams is immutable."""
        params = DrawdownParams(
            threshold_pct=Decimal("5"),
            lookback_days=10,
        )
        with pytest.raises(FrozenInstanceError):
            params.lookback_days = 20  # type: ignore[misc]


# ---------------------------------------------------------------------------
# VolatilityParams
# ---------------------------------------------------------------------------


class TestVolatilityParams:
    """VOLATILITY_SPIKE parameter validation + round-trip."""

    def test_minimal_valid_construction(self) -> None:
        """Tickers default to None (= 'all of strategy's tickers')."""
        params = VolatilityParams(
            threshold_pct=Decimal("40"),
            over_days=20,
        )
        assert params.tickers is None

    def test_with_explicit_tickers(self) -> None:
        """Explicit subset is accepted."""
        params = VolatilityParams(
            threshold_pct=Decimal("60"),
            over_days=30,
            tickers=[Ticker("AAPL"), Ticker("NVDA")],
        )
        assert params.tickers is not None
        assert [t.symbol for t in params.tickers] == ["AAPL", "NVDA"]

    @pytest.mark.parametrize("over_days", [0, 4, 91, 1000])
    def test_over_days_out_of_range_raises(self, over_days: int) -> None:
        """over_days must be in [5, 90]."""
        with pytest.raises(InvalidTriggerError, match="over_days must be in"):
            VolatilityParams(
                threshold_pct=Decimal("30"),
                over_days=over_days,
            )

    def test_threshold_zero_rejected(self) -> None:
        """threshold_pct == 0 is out of (0, 100]."""
        with pytest.raises(InvalidTriggerError, match="threshold_pct"):
            VolatilityParams(
                threshold_pct=Decimal("0"),
                over_days=10,
            )

    def test_empty_tickers_list_rejected(self) -> None:
        """Empty list is ambiguous — callers must use None for 'all'."""
        with pytest.raises(InvalidTriggerError, match="non-empty list"):
            VolatilityParams(
                threshold_pct=Decimal("30"),
                over_days=10,
                tickers=[],
            )

    def test_to_dict_round_trip_with_tickers(self) -> None:
        """from_dict reconstructs the same instance, with tickers."""
        params = VolatilityParams(
            threshold_pct=Decimal("35"),
            over_days=20,
            tickers=[Ticker("MSFT"), Ticker("GOOG")],
        )
        as_dict = params.to_dict()
        assert as_dict["tickers"] == ["MSFT", "GOOG"]
        rebuilt = VolatilityParams.from_dict(as_dict)
        assert rebuilt == params

    def test_to_dict_round_trip_without_tickers(self) -> None:
        """Tickers=None round-trips as None in the JSON dict."""
        params = VolatilityParams(
            threshold_pct=Decimal("25"),
            over_days=10,
        )
        as_dict = params.to_dict()
        assert as_dict["tickers"] is None
        rebuilt = VolatilityParams.from_dict(as_dict)
        assert rebuilt == params

    def test_from_dict_invalid_ticker_propagates(self) -> None:
        """Invalid ticker string raises InvalidTickerError (caught by Ticker)."""
        from zebu.domain.exceptions import InvalidTickerError

        with pytest.raises(InvalidTickerError):
            VolatilityParams.from_dict(
                {
                    "threshold_pct": "30",
                    "over_days": 10,
                    "tickers": ["TOO_LONG_TICKER"],
                }
            )


# ---------------------------------------------------------------------------
# EarningsParams (lightweight — calendar port arrives in F-4)
# ---------------------------------------------------------------------------


class TestEarningsParams:
    """EARNINGS_PROXIMITY parameter shape only — full evaluation in F-4.

    The placeholder note here matches the dispatch from the F-1 task spec:
    "EarningsCalendarPort" ports / adapters land in F-4. F-1 only encodes
    the parameter VO and validates its bounds.
    """

    def test_minimal_valid_construction(self) -> None:
        """days_before in range, tickers default None."""
        params = EarningsParams(days_before=3)
        assert params.days_before == 3
        assert params.tickers is None

    @pytest.mark.parametrize("days_before", [0, -1, 15, 100])
    def test_days_before_out_of_range_raises(self, days_before: int) -> None:
        """days_before must be in [1, 14]."""
        with pytest.raises(InvalidTriggerError, match="days_before must be in"):
            EarningsParams(days_before=days_before)

    def test_round_trip_with_tickers(self) -> None:
        """JSON round-trip preserves tickers."""
        params = EarningsParams(
            days_before=5,
            tickers=[Ticker("AMZN")],
        )
        as_dict = params.to_dict()
        rebuilt = EarningsParams.from_dict(as_dict)
        assert rebuilt == params

    def test_validated_when_earnings_calendar_port_lands_in_f4(self) -> None:
        """Placeholder: full evaluation is validated in F-4 (EarningsCalendarPort).

        Constructing the parameter VO with valid bounds is enough for F-1
        — the evaluator function and the third-party calendar adapter
        ship in F-4.
        """
        # Marker test — exists so F-4 has a clear hook to extend.
        params = EarningsParams(days_before=7)
        assert params.days_before == 7


# ---------------------------------------------------------------------------
# CustomRuleParams (intentionally unimplemented)
# ---------------------------------------------------------------------------


class TestCustomRuleParams:
    """Intentionally unimplemented per Phase F design doc Q1.

    The dataclass exists so the discriminated-union ``ConditionParams``
    type alias has a placeholder, but construction always raises and
    ``params_from_dict`` rejects the discriminator.
    """

    def test_construction_intentionally_raises(self) -> None:
        """Direct construction raises with the design-doc reference."""
        with pytest.raises(InvalidTriggerError, match="not yet supported"):
            CustomRuleParams(raw={"some": "predicate"})

    def test_params_from_dict_custom_rule_rejected(self) -> None:
        """Factory dispatch on CUSTOM_RULE raises with the same message."""
        with pytest.raises(InvalidTriggerError, match="not yet supported"):
            params_from_dict(ConditionType.CUSTOM_RULE, {})


# ---------------------------------------------------------------------------
# params_from_dict factory + params_match_type
# ---------------------------------------------------------------------------


class TestParamsFromDictFactory:
    """Discriminator dispatch + cross-type validation."""

    def test_drawdown_dispatch(self) -> None:
        """Factory builds DrawdownParams from a DRAWDOWN_THRESHOLD payload."""
        params = params_from_dict(
            ConditionType.DRAWDOWN_THRESHOLD,
            {"threshold_pct": "5", "lookback_days": 10},
        )
        assert isinstance(params, DrawdownParams)

    def test_volatility_dispatch(self) -> None:
        """Factory builds VolatilityParams from a VOLATILITY_SPIKE payload."""
        params = params_from_dict(
            ConditionType.VOLATILITY_SPIKE,
            {"threshold_pct": "30", "over_days": 10},
        )
        assert isinstance(params, VolatilityParams)

    def test_earnings_dispatch(self) -> None:
        """Factory builds EarningsParams from an EARNINGS_PROXIMITY payload."""
        params = params_from_dict(
            ConditionType.EARNINGS_PROXIMITY,
            {"days_before": 5},
        )
        assert isinstance(params, EarningsParams)


class TestParamsMatchType:
    """Cross-type matching used by the entity invariant check."""

    def test_drawdown_matches_drawdown_type(self) -> None:
        """The expected pairing matches."""
        params = DrawdownParams(threshold_pct=Decimal("5"), lookback_days=10)
        assert params_match_type(ConditionType.DRAWDOWN_THRESHOLD, params) is True

    def test_drawdown_does_not_match_volatility_type(self) -> None:
        """Wrong pairing returns False — entity uses this to reject."""
        params = DrawdownParams(threshold_pct=Decimal("5"), lookback_days=10)
        assert params_match_type(ConditionType.VOLATILITY_SPIKE, params) is False

    def test_volatility_matches_volatility_type(self) -> None:
        """The expected pairing matches."""
        params = VolatilityParams(threshold_pct=Decimal("30"), over_days=10)
        assert params_match_type(ConditionType.VOLATILITY_SPIKE, params) is True

    def test_earnings_matches_earnings_type(self) -> None:
        """The expected pairing matches."""
        params = EarningsParams(days_before=5)
        assert params_match_type(ConditionType.EARNINGS_PROXIMITY, params) is True
