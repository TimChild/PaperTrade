"""Tests for the pure :func:`evaluate_volatility_spike` evaluator (Phase F-4).

Boundary cases covered (per the task spec):

* Realised vol below threshold ⇒ no fire.
* Realised vol exactly at threshold ⇒ fire (inclusive boundary, documented).
* Realised vol above threshold ⇒ fire.
* Just-below threshold ⇒ no fire (strict-less-than confirmed).
* Insufficient history (0 / 1 / 2 in-window closes) ⇒ no fire.
* Single-ticker activation with crossed threshold ⇒ fire (basic case).
* Multi-ticker activation, only one ticker breaches ⇒ fire on that ticker.
* Multi-ticker activation, none breach ⇒ no fire.
* Empty inputs list ⇒ no fire.
* Snapshot data shape (schema_version, ticker, threshold/realised, dates).

The evaluator is a pure function on inputs — no mocks, no async.
Stdlib-only (statistics.stdev + math.sqrt) — no numpy.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import sqrt
from statistics import stdev

from zebu.application.services.trigger_evaluators.volatility_spike import (
    TickerClose,
    VolatilityEvaluatorInput,
    evaluate_volatility_spike,
    volatility_window,
)
from zebu.domain.value_objects.trigger_condition import VolatilityParams

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 10, 14, 30, tzinfo=UTC)
_OVER_DAYS = 20
_WINDOW_START = _NOW - timedelta(days=_OVER_DAYS)
_WINDOW_END = _NOW

_TRADING_DAYS_PER_YEAR = 252


def _closes(values: list[tuple[int, str]]) -> tuple[TickerClose, ...]:
    """Build a chronological series of closes.

    Args:
        values: ``(days_before_now, decimal_str)`` tuples. The *first*
            tuple is the *oldest* (largest ``days_before_now``).

    Returns:
        Tuple sorted ascending by ``observed_at``.
    """
    return tuple(
        TickerClose(
            observed_at=_NOW - timedelta(days=days),
            close=Decimal(price),
        )
        for days, price in sorted(values, reverse=True)
    )


def _input(
    closes: tuple[TickerClose, ...],
    *,
    ticker: str = "AAPL",
) -> VolatilityEvaluatorInput:
    """Wrap closes in a VolatilityEvaluatorInput with the standard window."""
    return VolatilityEvaluatorInput(
        ticker=ticker,
        closes=closes,
        window_start=_WINDOW_START,
        window_end=_WINDOW_END,
    )


def _params(
    *,
    threshold_pct: str = "30",
    over_days: int = _OVER_DAYS,
) -> VolatilityParams:
    """Build VolatilityParams with sensible defaults.

    The default threshold (30%) is roughly the historical SPY long-run
    annualised vol; tests pick higher / lower depending on whether they
    want a fire.
    """
    return VolatilityParams(
        threshold_pct=Decimal(threshold_pct),
        over_days=over_days,
    )


def _expected_realised_vol_pct(closes: tuple[TickerClose, ...]) -> Decimal:
    """Reference-implementation realised vol % for assertions.

    Mirrors the production formula so the test pins behaviour rather
    than reimplementing it from first principles.
    """
    if len(closes) < 2:
        raise AssertionError("Need >= 2 closes")
    rets: list[float] = []
    prev = closes[0].close
    for current in closes[1:]:
        rets.append(float((current.close - prev) / prev))
        prev = current.close
    if len(rets) < 2:
        raise AssertionError("Need >= 2 returns for stdev")
    daily_sigma = stdev(rets)
    annualised = daily_sigma * sqrt(_TRADING_DAYS_PER_YEAR)
    return Decimal(str(annualised * 100))


# ---------------------------------------------------------------------------
# Threshold boundary
# ---------------------------------------------------------------------------


class TestThresholdBoundary:
    """Realised-vol vs threshold comparison semantics."""

    def test_below_threshold_does_not_fire(self) -> None:
        """Stable price series ⇒ low realised vol ⇒ no fire."""
        # 10 closes that drift +0.1% / -0.1% — daily vol is tiny.
        closes_data: list[tuple[int, str]] = [
            (15, "100"),
            (14, "100.10"),
            (13, "100.00"),
            (12, "100.10"),
            (11, "100.00"),
            (10, "100.10"),
            (9, "100.00"),
            (8, "100.10"),
            (7, "100.00"),
            (6, "100.10"),
            (5, "100.00"),
        ]
        closes = _closes(closes_data)
        params = _params(threshold_pct="50")  # 50% annualised vol — far above

        fired, data = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is False
        assert data is None

    def test_above_threshold_fires(self) -> None:
        """Wild swings ⇒ high realised vol ⇒ fire above threshold."""
        # Daily ~5% swings annualise to a very high vol (~80%+).
        closes_data: list[tuple[int, str]] = [
            (10, "100"),
            (9, "105"),
            (8, "100"),
            (7, "105"),
            (6, "100"),
            (5, "105"),
            (4, "100"),
            (3, "105"),
            (2, "100"),
            (1, "105"),
        ]
        closes = _closes(closes_data)
        params = _params(threshold_pct="30")

        fired, data = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is True
        assert data is not None
        # Sanity: realised vol matches our reference computation.
        expected = _expected_realised_vol_pct(closes)
        assert Decimal(data["realised_vol_pct"]) == expected
        assert Decimal(data["realised_vol_pct"]) >= Decimal("30")

    def test_exactly_at_threshold_fires_inclusive(self) -> None:
        """Boundary choice: realised >= threshold ⇒ fire (documented).

        Picks the threshold to *equal* the computed realised vol.
        """
        closes_data: list[tuple[int, str]] = [
            (10, "100"),
            (9, "102"),
            (8, "100"),
            (7, "102"),
            (6, "100"),
            (5, "102"),
            (4, "100"),
            (3, "102"),
            (2, "100"),
            (1, "102"),
        ]
        closes = _closes(closes_data)
        # Compute the exact realised vol and use it as threshold.
        realised = _expected_realised_vol_pct(closes)
        params = _params(threshold_pct=str(realised))

        fired, data = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is True
        assert data is not None
        # Realised exactly matches threshold.
        assert Decimal(data["realised_vol_pct"]) == Decimal(data["threshold_pct"])

    def test_just_below_threshold_does_not_fire(self) -> None:
        """Strict less-than: realised < threshold ⇒ no fire even very close."""
        closes_data: list[tuple[int, str]] = [
            (10, "100"),
            (9, "102"),
            (8, "100"),
            (7, "102"),
            (6, "100"),
            (5, "102"),
            (4, "100"),
            (3, "102"),
            (2, "100"),
            (1, "102"),
        ]
        closes = _closes(closes_data)
        # Pin threshold a tiny amount above realised to assert
        # strict-less-than. ``realised + 0.000001`` keeps the gap
        # below any rounding noise.
        realised = _expected_realised_vol_pct(closes)
        threshold = realised + Decimal("0.000001")
        params = _params(threshold_pct=str(threshold))

        fired, _ = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is False


# ---------------------------------------------------------------------------
# Insufficient / pathological inputs
# ---------------------------------------------------------------------------


class TestInsufficientHistory:
    """Handle ledgers / market-data feeds that don't have enough data."""

    def test_empty_inputs_does_not_fire(self) -> None:
        """Caller passed no inputs ⇒ no fire."""
        params = _params()
        fired, data = evaluate_volatility_spike(params=params, inputs=[])

        assert fired is False
        assert data is None

    def test_zero_closes_does_not_fire(self) -> None:
        """Input with empty closes ⇒ skipped."""
        closes: tuple[TickerClose, ...] = ()
        params = _params()
        fired, data = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is False
        assert data is None

    def test_single_close_does_not_fire(self) -> None:
        """One close ⇒ zero returns ⇒ skipped."""
        closes = _closes([(1, "100")])
        params = _params()
        fired, data = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is False
        assert data is None

    def test_two_closes_does_not_fire(self) -> None:
        """Two closes ⇒ one return ⇒ stdev needs >=2 samples ⇒ skip."""
        closes = _closes([(2, "100"), (1, "110")])
        params = _params(threshold_pct="1")  # tiny threshold — would fire if computed
        fired, data = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is False
        assert data is None

    def test_observations_outside_window_are_filtered(self) -> None:
        """Closes outside ``[window_start, window_end]`` are dropped first."""
        # Three closes pre-window + one in-window → after filter, only
        # 1 close remains → not enough for a return.
        closes = (
            TickerClose(
                observed_at=_NOW - timedelta(days=100),
                close=Decimal("100"),
            ),
            TickerClose(
                observed_at=_NOW - timedelta(days=99),
                close=Decimal("110"),
            ),
            TickerClose(
                observed_at=_NOW - timedelta(days=98),
                close=Decimal("100"),
            ),
            TickerClose(
                observed_at=_NOW - timedelta(days=1),
                close=Decimal("105"),
            ),
        )
        params = _params(
            threshold_pct="1"
        )  # would fire if pre-window data wasn't dropped

        fired, _ = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is False


# ---------------------------------------------------------------------------
# Multi-ticker / first-hit semantics
# ---------------------------------------------------------------------------


class TestMultiTickerFireSemantics:
    """Fire-if-any: short-circuits on the first ticker over the threshold."""

    def test_single_ticker_breach_fires_with_correct_ticker(self) -> None:
        """One ticker, breach ⇒ fire and snapshot identifies the ticker."""
        closes = _closes(
            [
                (10, "100"),
                (9, "108"),
                (8, "92"),
                (7, "105"),
                (6, "95"),
                (5, "108"),
                (4, "92"),
                (3, "105"),
                (2, "95"),
                (1, "108"),
            ]
        )
        params = _params(threshold_pct="30")

        fired, data = evaluate_volatility_spike(
            params=params, inputs=[_input(closes, ticker="TSLA")]
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] == "TSLA"

    def test_multi_ticker_first_breaching_wins(self) -> None:
        """Two tickers, both breach — the first in iteration order is reported."""
        spike = _closes(
            [
                (10, "100"),
                (9, "110"),
                (8, "90"),
                (7, "110"),
                (6, "90"),
                (5, "110"),
                (4, "90"),
                (3, "110"),
                (2, "90"),
                (1, "110"),
            ]
        )
        # Caller orders TSLA first; TSLA short-circuits as the first hit.
        params = _params(threshold_pct="30")

        fired, data = evaluate_volatility_spike(
            params=params,
            inputs=[
                _input(spike, ticker="TSLA"),
                _input(spike, ticker="NVDA"),
            ],
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] == "TSLA"

    def test_multi_ticker_skips_calm_then_fires_on_volatile(self) -> None:
        """First ticker calm; second volatile ⇒ fire on second ticker."""
        calm = _closes(
            [
                (10, "100"),
                (9, "100.10"),
                (8, "100.20"),
                (7, "100.10"),
                (6, "100.05"),
                (5, "100.10"),
                (4, "100.00"),
                (3, "100.10"),
                (2, "100.05"),
                (1, "100.10"),
            ]
        )
        spike = _closes(
            [
                (10, "100"),
                (9, "110"),
                (8, "90"),
                (7, "110"),
                (6, "90"),
                (5, "110"),
                (4, "90"),
                (3, "110"),
                (2, "90"),
                (1, "110"),
            ]
        )
        params = _params(threshold_pct="30")

        fired, data = evaluate_volatility_spike(
            params=params,
            inputs=[
                _input(calm, ticker="JNJ"),
                _input(spike, ticker="GME"),
            ],
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] == "GME"

    def test_multi_ticker_none_breach_does_not_fire(self) -> None:
        """All tickers calm ⇒ no fire."""
        calm = _closes(
            [
                (10, "100"),
                (9, "100.10"),
                (8, "100.20"),
                (7, "100.10"),
                (6, "100.05"),
                (5, "100.10"),
                (4, "100.00"),
                (3, "100.10"),
                (2, "100.05"),
                (1, "100.10"),
            ]
        )
        params = _params(threshold_pct="30")

        fired, data = evaluate_volatility_spike(
            params=params,
            inputs=[
                _input(calm, ticker="JNJ"),
                _input(calm, ticker="WMT"),
            ],
        )

        assert fired is False
        assert data is None


# ---------------------------------------------------------------------------
# Evaluation-data shape
# ---------------------------------------------------------------------------


class TestEvaluationDataShape:
    """Snapshot returned by the evaluator carries the design §1.5 fields."""

    def test_includes_required_design_fields(self) -> None:
        """All §1.5 fields present on a fire."""
        closes = _closes(
            [
                (10, "100"),
                (9, "110"),
                (8, "90"),
                (7, "110"),
                (6, "90"),
                (5, "110"),
                (4, "90"),
                (3, "110"),
                (2, "90"),
                (1, "110"),
            ]
        )
        params = _params(threshold_pct="30", over_days=_OVER_DAYS)

        fired, data = evaluate_volatility_spike(
            params=params, inputs=[_input(closes, ticker="GME")]
        )

        assert fired is True
        assert data is not None
        assert data["schema_version"] == 1
        for required_field in (
            "ticker",
            "threshold_pct",
            "realised_vol_pct",
            "over_days",
            "window_start",
            "window_end",
        ):
            assert required_field in data, f"Missing required field {required_field!r}"
        assert data["over_days"] == _OVER_DAYS

    def test_window_dates_are_iso_dates(self) -> None:
        """``window_start`` / ``window_end`` are 10-char ISO date strings."""
        closes = _closes(
            [
                (10, "100"),
                (9, "110"),
                (8, "90"),
                (7, "110"),
                (6, "90"),
                (5, "110"),
                (4, "90"),
                (3, "110"),
                (2, "90"),
                (1, "110"),
            ]
        )
        params = _params(threshold_pct="30")

        fired, data = evaluate_volatility_spike(params=params, inputs=[_input(closes)])

        assert fired is True
        assert data is not None
        assert len(data["window_start"]) == 10
        assert len(data["window_end"]) == 10

        # Parses as ISO date.
        from datetime import date as _date

        _date.fromisoformat(data["window_start"])
        _date.fromisoformat(data["window_end"])


# ---------------------------------------------------------------------------
# volatility_window helper
# ---------------------------------------------------------------------------


class TestVolatilityWindow:
    """Helper that constructs the ``(start, end)`` window for the service."""

    def test_default_window_anchors_end_at_now(self) -> None:
        """``end`` is exactly ``now``; ``start`` is ``now - over_days``."""
        now = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)

        start, end = volatility_window(now=now, over_days=20)

        assert end == now
        assert (now - start).days == 20
