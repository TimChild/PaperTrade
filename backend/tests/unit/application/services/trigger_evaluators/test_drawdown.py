"""Tests for the pure :func:`evaluate_drawdown` evaluator (Phase F-2).

Boundary cases covered (all per the task spec):

* Drawdown below threshold ⇒ no fire.
* Drawdown exactly at threshold ⇒ fire (inclusive boundary, documented).
* Drawdown above threshold ⇒ fire.
* Insufficient ledger history (0 / 1 in-window points) ⇒ no fire.
* No holdings (empty input list) ⇒ no fire.
* Gain-then-loss vs straight-loss patterns ⇒ both fire when peak is
  reached then receded.
* Per-ticker mode picks the *first* eligible ticker and reports it.
* Non-positive peak (zero / negative value) ⇒ skipped (no fire).
* Pure ascending series (current > all prior) ⇒ no fire (drawdown 0).

The evaluator is a pure function on inputs — no mocks needed.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from zebu.application.services.trigger_evaluators.drawdown import (
    DrawdownEvaluatorInput,
    PortfolioValuePoint,
    evaluate_drawdown,
    lookback_window,
)
from zebu.domain.value_objects.trigger_condition import (
    DrawdownMetric,
    DrawdownParams,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 10, 14, 30, tzinfo=UTC)
_LOOKBACK_DAYS = 30
_WINDOW_START = _NOW - timedelta(days=_LOOKBACK_DAYS)
_WINDOW_END = _NOW


def _series(values: list[tuple[int, str]]) -> tuple[PortfolioValuePoint, ...]:
    """Build a chronological series of ``PortfolioValuePoint``.

    Args:
        values: List of ``(days_before_now, decimal_str)`` tuples. The
            *first* tuple is the *oldest* (largest ``days_before_now``).

    Returns:
        Tuple of points sorted ascending by ``observed_at``.
    """
    return tuple(
        PortfolioValuePoint(
            observed_at=_NOW - timedelta(days=days),
            value=Decimal(value),
        )
        for days, value in sorted(values, reverse=True)
    )


def _input(
    series_points: tuple[PortfolioValuePoint, ...],
    *,
    ticker: str | None = None,
) -> DrawdownEvaluatorInput:
    """Wrap a series in a DrawdownEvaluatorInput with the standard window."""
    return DrawdownEvaluatorInput(
        ticker=ticker,
        value_points=series_points,
        lookback_window_start=_WINDOW_START,
        lookback_window_end=_WINDOW_END,
    )


def _params(
    *,
    threshold_pct: str = "5",
    metric: DrawdownMetric = DrawdownMetric.PORTFOLIO_TOTAL,
    lookback_days: int = _LOOKBACK_DAYS,
) -> DrawdownParams:
    """Build DrawdownParams with sensible defaults."""
    return DrawdownParams(
        threshold_pct=Decimal(threshold_pct),
        lookback_days=lookback_days,
        metric=metric,
    )


# ---------------------------------------------------------------------------
# Threshold boundary
# ---------------------------------------------------------------------------


class TestThresholdBoundary:
    """Drawdown vs threshold comparison semantics."""

    def test_below_threshold_does_not_fire(self) -> None:
        """4% drawdown vs 5% threshold ⇒ skip."""
        # peak 100 -> current 96 ⇒ 4% drawdown.
        series = _series([(20, "100"), (1, "96")])
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is False
        assert data is None

    def test_exactly_at_threshold_fires_inclusive(self) -> None:
        """Boundary choice: drawdown == threshold ⇒ fire (documented)."""
        # peak 100 -> current 95 ⇒ exactly 5% drawdown.
        series = _series([(20, "100"), (1, "95")])
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is True
        assert data is not None
        # str(Decimal('5')) round-trips to '5'; comparing as Decimal makes
        # the test resilient to whether the evaluator normalises trailing
        # zeros.
        assert Decimal(data["drawdown_pct"]) == Decimal("5")
        # threshold is rendered exactly as supplied to make the fire row
        # round-trip cleanly through the JSON column.
        assert Decimal(data["threshold_pct"]) == Decimal("5")

    def test_above_threshold_fires(self) -> None:
        """10% drawdown vs 5% threshold ⇒ fire, snapshot includes peak/current."""
        series = _series([(20, "100"), (1, "90")])
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is True
        assert data is not None
        assert data["peak_value"] == "100"
        assert data["current_value"] == "90"
        # 10% drawdown rendered with at-least-one decimal of precision.
        assert Decimal(data["drawdown_pct"]) == Decimal("10")

    def test_drawdown_just_under_threshold(self) -> None:
        """4.99% drawdown vs 5% threshold ⇒ no fire (strict inequality fails)."""
        series = _series([(20, "10000"), (1, "9501")])
        params = _params(threshold_pct="5")

        fired, _ = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is False


# ---------------------------------------------------------------------------
# Drawdown patterns (gain-then-loss vs straight-loss)
# ---------------------------------------------------------------------------


class TestDrawdownPatterns:
    """Realistic price/value trajectories."""

    def test_gain_then_loss_uses_intra_window_peak(self) -> None:
        """Series rises from 100 to 120, then falls to 100 ⇒ 16.67% drawdown."""
        # 100 -> 120 -> 100 within the window.
        series = _series([(25, "100"), (10, "120"), (1, "100")])
        params = _params(threshold_pct="10")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is True
        assert data is not None
        assert data["peak_value"] == "120"
        assert data["current_value"] == "100"
        # (120 - 100) / 120 * 100 == 16.666... — assert at-or-above 16%
        # rather than chasing the rounding.
        assert Decimal(data["drawdown_pct"]) > Decimal("16")
        assert Decimal(data["drawdown_pct"]) < Decimal("17")

    def test_straight_loss_uses_first_observation_as_peak(self) -> None:
        """Monotonically declining series ⇒ peak is the oldest in-window point."""
        series = _series([(25, "100"), (10, "95"), (1, "85")])
        params = _params(threshold_pct="10")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is True
        assert data is not None
        assert data["peak_value"] == "100"
        assert data["current_value"] == "85"

    def test_monotonic_increase_does_not_fire(self) -> None:
        """Strictly ascending series ⇒ peak == current ⇒ 0% drawdown."""
        series = _series([(25, "100"), (10, "110"), (1, "120")])
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        # Either evaluator returns ``(False, None)`` (the current >= peak
        # short-circuit) or computes 0% which is below the 5% threshold.
        assert fired is False
        assert data is None


# ---------------------------------------------------------------------------
# Insufficient / pathological inputs
# ---------------------------------------------------------------------------


class TestInsufficientHistory:
    """Handle ledgers that don't have enough data to compute drawdown."""

    def test_empty_inputs_list_does_not_fire(self) -> None:
        """Caller passed no inputs (e.g. portfolio with no transactions)."""
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[])

        assert fired is False
        assert data is None

    def test_zero_observations_does_not_fire(self) -> None:
        """Input with empty value_points ⇒ skipped."""
        series: tuple[PortfolioValuePoint, ...] = ()
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is False
        assert data is None

    def test_single_observation_does_not_fire(self) -> None:
        """One in-window point can't establish peak vs current."""
        series = _series([(1, "100")])
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is False
        assert data is None

    def test_observations_outside_window_are_filtered(self) -> None:
        """A single in-window point + a pre-window point ⇒ no fire.

        The pre-window point is filtered before evaluation, so the
        evaluator sees only one point and returns no fire — even though
        the pre-window value would have established a peak.
        """
        # 100 days back is outside the 30-day window.
        series = _series([(100, "100"), (1, "90")])
        params = _params(threshold_pct="5", lookback_days=30)

        fired, _ = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is False

    def test_zero_peak_does_not_fire(self) -> None:
        """Peak == 0 ⇒ undefined drawdown ⇒ skip."""
        # Series starts at 0 and stays at 0. Peak is 0.
        series = _series([(20, "0"), (1, "0")])
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is False
        assert data is None


# ---------------------------------------------------------------------------
# Per-ticker mode
# ---------------------------------------------------------------------------


class TestPerTickerMode:
    """``DrawdownMetric.PER_TICKER`` — one input per ticker; first hit wins."""

    def test_per_ticker_picks_first_eligible_ticker(self) -> None:
        """Two tickers, both crash; the first in iteration order is reported."""
        # AAPL crashes 10%, MSFT crashes 20%. Caller orders MSFT first;
        # MSFT is the one we report (first hit short-circuits).
        msft_series = _series([(20, "100"), (1, "80")])
        aapl_series = _series([(20, "100"), (1, "90")])
        params = _params(threshold_pct="5", metric=DrawdownMetric.PER_TICKER)

        fired, data = evaluate_drawdown(
            params=params,
            inputs=[
                _input(msft_series, ticker="MSFT"),
                _input(aapl_series, ticker="AAPL"),
            ],
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] == "MSFT"
        assert data["metric"] == "PER_TICKER"
        # The non-firing ticker's data is not represented.

    def test_per_ticker_skips_tickers_without_drawdown(self) -> None:
        """First ticker is fine; second ticker fires ⇒ second is reported."""
        # AAPL is up 10% (no fire); MSFT is down 10% (fires).
        aapl_series = _series([(20, "100"), (1, "110")])
        msft_series = _series([(20, "100"), (1, "90")])
        params = _params(threshold_pct="5", metric=DrawdownMetric.PER_TICKER)

        fired, data = evaluate_drawdown(
            params=params,
            inputs=[
                _input(aapl_series, ticker="AAPL"),
                _input(msft_series, ticker="MSFT"),
            ],
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] == "MSFT"

    def test_per_ticker_no_fires_returns_none(self) -> None:
        """All tickers above threshold (i.e. no drawdown) ⇒ no fire."""
        aapl_series = _series([(20, "100"), (1, "98")])
        msft_series = _series([(20, "100"), (1, "97")])
        params = _params(threshold_pct="5", metric=DrawdownMetric.PER_TICKER)

        fired, data = evaluate_drawdown(
            params=params,
            inputs=[
                _input(aapl_series, ticker="AAPL"),
                _input(msft_series, ticker="MSFT"),
            ],
        )

        assert fired is False
        assert data is None


# ---------------------------------------------------------------------------
# Evaluation-data shape
# ---------------------------------------------------------------------------


class TestEvaluationDataShape:
    """Snapshot returned by the evaluator carries the design §1.5 fields."""

    def test_portfolio_total_metric_renders_ticker_as_null(self) -> None:
        """PORTFOLIO_TOTAL ⇒ ``ticker`` is None even if a ticker happened to
        be passed on the input (defensive — caller wouldn't usually).
        """
        series = _series([(20, "100"), (1, "85")])
        params = _params(threshold_pct="5", metric=DrawdownMetric.PORTFOLIO_TOTAL)

        fired, data = evaluate_drawdown(
            params=params,
            inputs=[_input(series, ticker="ignored-by-portfolio-total")],
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] is None
        assert data["metric"] == "PORTFOLIO_TOTAL"

    def test_evaluation_data_includes_required_design_fields(self) -> None:
        """Per §1.5, fire data should expose peak / current / window / metric."""
        series = _series([(25, "100"), (1, "85")])
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is True
        assert data is not None
        # Schema-version tag (per Q8) is on every fire's evaluation data.
        assert data["schema_version"] == 1
        # Core fields for the activity feed renderer.
        for required_field in (
            "metric",
            "ticker",
            "threshold_pct",
            "drawdown_pct",
            "peak_value",
            "current_value",
            "peak_at",
            "lookback_window_start",
            "lookback_window_end",
        ):
            assert required_field in data, f"Missing required field {required_field!r}"

    def test_window_dates_are_iso_dates_in_evaluation_data(self) -> None:
        """``lookback_window_start/end`` are ISO date strings (no time)."""
        series = _series([(25, "100"), (1, "85")])
        params = _params(threshold_pct="5")

        fired, data = evaluate_drawdown(params=params, inputs=[_input(series)])

        assert fired is True
        assert data is not None
        # ``YYYY-MM-DD`` is exactly 10 characters.
        assert len(data["lookback_window_start"]) == 10
        assert len(data["lookback_window_end"]) == 10
        # Round-trip parse confirms it's actually an ISO date.
        from datetime import date as _date

        _date.fromisoformat(data["lookback_window_start"])
        _date.fromisoformat(data["lookback_window_end"])


# ---------------------------------------------------------------------------
# lookback_window helper
# ---------------------------------------------------------------------------


class TestLookbackWindow:
    """Helper that constructs the ``(start, end)`` window for the service."""

    def test_default_window_anchors_end_at_now(self) -> None:
        """``end`` is exactly ``now``; ``start`` is ``now - lookback_days``."""
        now = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)

        start, end = lookback_window(now=now, lookback_days=30)

        assert end == now
        assert (now - start).days == 30

    def test_window_uses_timedelta_not_calendar_arithmetic(self) -> None:
        """365 days back from 2026-01-01 ⇒ 2025-01-01 (not 2025-01-02)."""
        now = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)

        start, _ = lookback_window(now=now, lookback_days=365)

        # 365 days exactly. (Note: calendar-aware "1 year" would land on
        # 2025-01-01 too in this case, but tested here to pin behaviour.)
        assert start == datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
