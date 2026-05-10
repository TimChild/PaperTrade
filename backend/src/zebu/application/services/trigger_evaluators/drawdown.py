"""Pure-function evaluator for the ``DRAWDOWN_THRESHOLD`` condition.

A trigger fires when the activation's portfolio (or any single ticker,
depending on :class:`DrawdownMetric`) is down ``>= threshold_pct`` from
its peak inside the ``lookback_days`` window.

Design references:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §1.2 (params),
  §1.5 (evaluation_data shape), §2.1.4 (per-condition evaluator
  contract), §10 Q6 (ledger-recompute over snapshot reuse — drawdown
  needs intraday-fresh state).

F-2 scope: this is a **pure function on inputs**. The service composes
the I/O around it (ledger walk → portfolio-value-by-day series, batch
price fetch for ``PER_TICKER`` mode). Keeping the evaluator pure means
unit tests don't need any market-data adapters.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TypedDict

from zebu.domain.value_objects.trigger_condition import (
    CONDITION_PARAMS_SCHEMA_VERSION,
    DrawdownMetric,
    DrawdownParams,
)


@dataclass(frozen=True)
class PortfolioValuePoint:
    """One observation of an aggregate value at a moment in time.

    Used both for portfolio-total drawdown (one series across the whole
    portfolio) and for per-ticker drawdown (one series per ticker). The
    value can be any monetary unit — the evaluator only ever computes
    ratios so the unit cancels.

    Attributes:
        observed_at: When the value was observed. Naive datetimes are
            treated as UTC.
        value: The value at that timestamp. Must be ``>= 0``.
    """

    observed_at: datetime
    value: Decimal


@dataclass(frozen=True)
class DrawdownEvaluatorInput:
    """Bundle of inputs the drawdown evaluator needs.

    The shape is designed so the same dataclass works for both
    :class:`DrawdownMetric.PORTFOLIO_TOTAL` (the ``ticker`` slot is left
    ``None`` and ``value_points`` is the portfolio-total series) and
    :class:`DrawdownMetric.PER_TICKER` (one input per ticker, each with
    its own price-history series).

    Attributes:
        ticker: Ticker symbol when the input is per-ticker. ``None`` for
            portfolio-total mode. The ``DRAWDOWN_THRESHOLD`` evaluator
            renders this into the ``evaluation_data`` JSON when the
            condition fires.
        value_points: Chronological observations of the underlying
            value. Must be sorted ascending by ``observed_at`` — the
            evaluator does not sort defensively (avoids hidden cost).
            All values must be ``>= 0``.
        lookback_window_start: Earliest observation considered. Anything
            with ``observed_at < lookback_window_start`` is ignored.
        lookback_window_end: Latest observation considered. The "current"
            value used for the drawdown comparison is the most recent
            point with ``observed_at <= lookback_window_end``.
    """

    ticker: str | None
    value_points: Sequence[PortfolioValuePoint]
    lookback_window_start: datetime
    lookback_window_end: datetime


class DrawdownEvaluationData(TypedDict):
    """JSON-shaped snapshot of a fire's drawdown inputs.

    Matches the schema documented in design §1.5 with a couple of
    extensions to keep the data self-describing:

    - ``schema_version`` — always 1 in F-2; bump if the shape changes.
    - ``metric`` — string value of :class:`DrawdownMetric`.
    - ``ticker`` — ticker symbol when ``metric == PER_TICKER``; ``None``
      otherwise. Null is valid JSON; the field is always present so
      consumers don't have to special-case its absence.
    - Decimals are serialised as strings (matches the strategy-parameters
      pattern) so the JSON column round-trips losslessly.
    """

    schema_version: int
    metric: str
    ticker: str | None
    threshold_pct: str
    drawdown_pct: str
    peak_value: str
    current_value: str
    peak_at: str
    lookback_window_start: str
    lookback_window_end: str


def _to_iso_date(value: datetime) -> str:
    """Format a datetime as an ISO-8601 *date* string (drops the time)."""
    return value.date().isoformat()


def _to_iso_datetime(value: datetime) -> str:
    """Format a datetime as an ISO-8601 datetime string."""
    return value.isoformat()


def _filter_window(
    points: Iterable[PortfolioValuePoint],
    *,
    start: datetime,
    end: datetime,
) -> list[PortfolioValuePoint]:
    """Return only the points inside ``[start, end]``.

    Caller MUST pass already-sorted points; this helper preserves order.

    Args:
        points: Chronologically-sorted observations.
        start: Earliest accepted ``observed_at``.
        end: Latest accepted ``observed_at``.

    Returns:
        New list with only the in-window observations.
    """
    return [p for p in points if start <= p.observed_at <= end]


def evaluate_drawdown(
    *,
    params: DrawdownParams,
    inputs: Sequence[DrawdownEvaluatorInput],
) -> tuple[bool, DrawdownEvaluationData | None]:
    """Decide whether a ``DRAWDOWN_THRESHOLD`` condition fires.

    Pure function. Picks the first eligible series in ``inputs`` whose
    drawdown crosses ``params.threshold_pct``. The choice of "first"
    rather than "worst-of" is deliberate: per-ticker drawdown is
    short-circuited at the first hit so the evaluator returns quickly
    when the basket has many tickers but only one has cracked. The
    composer (`TriggerEvaluationService`) is responsible for ordering
    inputs deterministically so the choice is repeatable.

    Boundary semantics (documented choice):
        Fires when ``drawdown_pct >= threshold_pct`` — **inclusive**.
        Exactly hitting the threshold counts as a fire. This matches
        the intuitive reading of "5% drawdown threshold" and keeps the
        condition consistent under the "infinite-precision drawdown
        becomes a fire" ideal: an inclusive boundary triggers
        immediately on the first observation that touches it, rather
        than the next-larger one.

    Insufficient history:
        If after window-filtering an input has zero or one observation,
        no drawdown can be computed — the input is skipped. If every
        input is skipped, the result is ``(False, None)``.

    Zero / non-positive peak:
        If the in-window peak is ``<= 0``, the drawdown is undefined
        (division by zero or sign-flipping). The input is skipped. This
        happens for tickers with no holdings yet or for portfolios with
        no observations.

    Args:
        params: The :class:`DrawdownParams` from the trigger.
        inputs: One or more pre-computed value series. For
            ``PORTFOLIO_TOTAL`` mode, pass exactly one input with
            ``ticker=None``; for ``PER_TICKER`` mode, pass one input per
            ticker.

    Returns:
        ``(fired, evaluation_data)`` where ``fired`` is ``True`` when
        any input crosses the threshold. ``evaluation_data`` is ``None``
        when no fire occurred and a ready-to-persist
        :class:`DrawdownEvaluationData` mapping when one did.
    """
    # The threshold check is `drawdown_pct >= threshold_pct`. We compute
    # `drawdown_pct = (peak - current) / peak * 100` so it's always >= 0
    # (peak is the in-window max; current is <= peak by definition). A
    # negative drawdown can only happen if `current > peak`, which we
    # guard against by always taking the running max.
    threshold = params.threshold_pct

    for evaluator_input in inputs:
        in_window = _filter_window(
            evaluator_input.value_points,
            start=evaluator_input.lookback_window_start,
            end=evaluator_input.lookback_window_end,
        )
        if len(in_window) < 2:
            # Need at least one prior point to establish a peak and one
            # later point to compare against.
            continue

        # Peak must be a *prior* observation — taking the global max of
        # the window is equivalent (the current point can't drawdown
        # from itself, by definition the most-recent point's "current" is
        # always self).
        peak_point = max(in_window, key=lambda p: p.value)
        if peak_point.value <= Decimal("0"):
            # Undefined drawdown — skip.
            continue

        # The "current" value is the latest observation in the window.
        current_point = in_window[-1]

        if current_point.value > peak_point.value:
            # Defensive: a series that strictly increases in the
            # window has a drawdown of 0% (peak == current). Skip the
            # arithmetic so we don't emit a negative drawdown.
            continue

        diff = peak_point.value - current_point.value
        drawdown_pct = (diff / peak_point.value) * Decimal("100")

        if drawdown_pct >= threshold:
            data: DrawdownEvaluationData = {
                "schema_version": CONDITION_PARAMS_SCHEMA_VERSION,
                "metric": params.metric.value,
                "ticker": (
                    evaluator_input.ticker
                    if params.metric is DrawdownMetric.PER_TICKER
                    else None
                ),
                "threshold_pct": str(threshold),
                "drawdown_pct": str(drawdown_pct),
                "peak_value": str(peak_point.value),
                "current_value": str(current_point.value),
                "peak_at": _to_iso_datetime(peak_point.observed_at),
                "lookback_window_start": _to_iso_date(
                    evaluator_input.lookback_window_start
                ),
                "lookback_window_end": _to_iso_date(
                    evaluator_input.lookback_window_end
                ),
            }
            return True, data

    return False, None


def lookback_window(
    *,
    now: datetime,
    lookback_days: int,
) -> tuple[datetime, datetime]:
    """Return the ``(start, end)`` window for a drawdown evaluation.

    Helper used by the composing service when it builds the
    :class:`DrawdownEvaluatorInput` instances. Defined here (next to
    its consumer) rather than in the service so unit tests can exercise
    it without importing the service module.

    Args:
        now: Reference timestamp (typically the scheduler tick time).
        lookback_days: Window width from the entity's
            :class:`DrawdownParams`.

    Returns:
        Tuple ``(window_start, window_end)`` where ``window_end == now``
        and ``window_start = now - lookback_days``.
    """
    from datetime import timedelta

    return now - timedelta(days=lookback_days), now


# ``date`` is re-exported so the service module can import it
# alongside the helpers without reaching back into `datetime`.
__all__ = [
    "DrawdownEvaluationData",
    "DrawdownEvaluatorInput",
    "PortfolioValuePoint",
    "date",
    "evaluate_drawdown",
    "lookback_window",
]
