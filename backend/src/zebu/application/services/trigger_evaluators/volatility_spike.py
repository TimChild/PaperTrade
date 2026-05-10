"""Pure-function evaluator for the ``VOLATILITY_SPIKE`` condition.

A trigger fires when realised volatility (annualised standard deviation
of daily returns) over ``params.over_days`` exceeds
``params.threshold_pct`` for **any** ticker in the activation's universe
(or the explicit subset set on :class:`VolatilityParams.tickers`).

Design references:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §1.2 (params),
  §1.5 (evaluation_data shape: ``realised_vol_pct``, ``threshold_pct``,
  ``over_days``, ``window_start``, ``window_end``, ``ticker``),
  §2.1.4 (per-condition evaluator contract).

The evaluator is a **pure function** on inputs — no I/O, no async.
The composing :class:`TriggerEvaluationService` builds the price
history per ticker upstream and hands it in. Stdlib only — no
``numpy`` dependency.

Boundary semantics (documented choice):
    Fires when ``realised_vol_pct >= threshold_pct`` — **inclusive**.
    Mirrors the drawdown evaluator's boundary so the two condition
    types behave consistently.

Insufficient history:
    Realised vol needs at least 2 daily returns (i.e. 3 close
    observations) to be defined; the formula requires
    ``over_days >= 5`` per the VO so when that many returns aren't
    available the ticker is skipped (no fire). The full design
    constraint of "at least ``over_days`` of returns" is preferred
    where data is available, but we don't *strictly* require it —
    a partial window still produces a valid sample-stdev estimate
    and the alternative (silent no-fire when most of the window is
    populated) felt worse than firing on a slightly noisier estimate.
    The bar is "enough returns to compute sample stdev" (>= 2).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from math import sqrt
from statistics import stdev
from typing import TypedDict

from zebu.domain.value_objects.trigger_condition import (
    CONDITION_PARAMS_SCHEMA_VERSION,
    VolatilityParams,
)

# Trading-days-per-year scaling factor for annualisation. 252 is the
# convention used across the EquityVolatility / RiskMetrics literature
# and matches what most market data providers use to convert daily
# realised vol to annualised. We pick a Decimal-friendly approach via
# ``sqrt(252)`` (a float) and cast to Decimal at the boundary so the
# emitted ``realised_vol_pct`` is a Decimal string.
_TRADING_DAYS_PER_YEAR: int = 252


@dataclass(frozen=True)
class TickerClose:
    """One closing-price observation for a ticker.

    Used as the input series to :func:`evaluate_volatility_spike`.
    Only the close price matters for realised-vol computation; the
    timestamp is carried so the evaluator can report ``window_start``
    / ``window_end`` on the fire snapshot without re-deriving them.

    Attributes:
        observed_at: When the observation belongs to. Naive datetimes
            are treated as UTC.
        close: Closing price. Must be ``> 0``.
    """

    observed_at: datetime
    close: Decimal


@dataclass(frozen=True)
class VolatilityEvaluatorInput:
    """Per-ticker bundle of inputs the volatility evaluator needs.

    Attributes:
        ticker: Symbol of the ticker the series belongs to. Reported
            verbatim on the fire snapshot.
        closes: Chronologically-sorted closing-price observations.
            Caller MUST sort ascending by ``observed_at`` — the
            evaluator does not sort defensively.
        window_start: Earliest accepted observation timestamp. Closes
            with ``observed_at < window_start`` are filtered before
            return computation.
        window_end: Latest accepted observation timestamp. Closes with
            ``observed_at > window_end`` are filtered.
    """

    ticker: str
    closes: Sequence[TickerClose]
    window_start: datetime
    window_end: datetime


class VolatilityEvaluationData(TypedDict):
    """JSON-shaped snapshot of a fire's realised-volatility inputs.

    Matches the schema documented in design §1.5:

    - ``schema_version`` — always 1 in F-4.
    - ``ticker`` — the ticker that crossed the threshold.
    - ``threshold_pct`` — the configured threshold (Decimal as string).
    - ``realised_vol_pct`` — the computed annualised realised
      volatility (Decimal as string).
    - ``over_days`` — the configured window width (echoed for audit
      convenience).
    - ``window_start`` / ``window_end`` — ISO-8601 dates.
    """

    schema_version: int
    ticker: str
    threshold_pct: str
    realised_vol_pct: str
    over_days: int
    window_start: str
    window_end: str


def _to_iso_date(value: datetime) -> str:
    """Format a datetime as an ISO-8601 *date* string (drops the time)."""
    return value.date().isoformat()


def _filter_window(
    closes: Sequence[TickerClose],
    *,
    start: datetime,
    end: datetime,
) -> list[TickerClose]:
    """Return only the closes inside ``[start, end]``.

    Caller MUST pass already-sorted closes; this helper preserves
    order. Mirrors :func:`zebu.application.services.trigger_evaluators
    .drawdown._filter_window`.
    """
    return [c for c in closes if start <= c.observed_at <= end]


def _daily_returns(closes: Sequence[TickerClose]) -> list[float]:
    """Compute simple daily returns from a chronological series of closes.

    Uses arithmetic returns ``(p_t - p_{t-1}) / p_{t-1}`` rather than
    log returns. The two are nearly identical for the small daily
    moves typical of equity series and arithmetic is the more
    intuitive choice for the activity-feed renderer ("price changed
    by 5%" not "log-return of 0.0488"). Float is acceptable here
    because the result feeds into ``stdev`` which is itself
    float-only; the *output* (``realised_vol_pct``) is converted back
    to Decimal at the boundary.

    Args:
        closes: At least 2 chronological closes.

    Returns:
        ``len(closes) - 1`` daily returns in the same order. May be
        empty when fewer than 2 closes are passed.
    """
    if len(closes) < 2:
        return []

    returns: list[float] = []
    prev = closes[0].close
    for current in closes[1:]:
        if prev <= Decimal("0"):
            # Skip undefined return (division by zero / negative
            # base). Reset the cursor to the *current* close so we
            # don't compound the gap. In practice equities never have
            # zero close prices but defensive code is cheap.
            prev = current.close
            continue
        diff = current.close - prev
        returns.append(float(diff / prev))
        prev = current.close
    return returns


def evaluate_volatility_spike(
    *,
    params: VolatilityParams,
    inputs: Sequence[VolatilityEvaluatorInput],
) -> tuple[bool, VolatilityEvaluationData | None]:
    """Decide whether a ``VOLATILITY_SPIKE`` condition fires.

    Pure function. Iterates ``inputs`` in caller-supplied order and
    returns on the first ticker whose realised volatility crosses
    ``params.threshold_pct``. Mirrors :func:`evaluate_drawdown`:
    composer is responsible for ordering inputs deterministically.

    Boundary semantics (documented):
        Fires when ``realised_vol_pct >= threshold_pct`` — inclusive.

    Insufficient history:
        - 0 in-window closes: skipped.
        - 1 in-window close: skipped (no returns computable).
        - 2 in-window closes: yields exactly 1 return; ``stdev``
          requires at least 2 samples and raises ``StatisticsError``
          — we treat this as "insufficient" and skip rather than
          raise, so a freshly-onboarded portfolio doesn't crash the
          cycle.

    Multi-ticker fire-if-any semantics:
        The trigger fires as soon as one ticker exceeds the threshold.
        We do *not* compute realised vol for every ticker — we
        short-circuit on the first hit so a 50-ticker basket where
        the first ticker spiked doesn't pay for the other 49 stdev
        calls.

    Args:
        params: The :class:`VolatilityParams` from the trigger.
        inputs: One :class:`VolatilityEvaluatorInput` per ticker the
            evaluator should check. The composer (TriggerEvaluationService)
            is responsible for honouring the activation universe and
            applying the ``params.tickers`` subset.

    Returns:
        ``(fired, evaluation_data)``. ``evaluation_data`` is ``None``
        on no-fire and a ready-to-persist
        :class:`VolatilityEvaluationData` on fire.
    """
    threshold = params.threshold_pct

    for evaluator_input in inputs:
        in_window = _filter_window(
            evaluator_input.closes,
            start=evaluator_input.window_start,
            end=evaluator_input.window_end,
        )
        if len(in_window) < 3:
            # Need at least 3 closes (-> 2 returns) for sample stdev.
            continue

        returns = _daily_returns(in_window)
        if len(returns) < 2:
            # Defensive: zero-prev guards inside _daily_returns may
            # have dropped one. Same skip logic.
            continue

        # Sample standard deviation of daily returns -> annualised
        # realised volatility, expressed as a percentage.
        try:
            daily_sigma = stdev(returns)
        except Exception:
            # ``statistics.stdev`` raises StatisticsError on edge
            # cases (single sample after our guards, or all-NaN
            # input). Treat as insufficient and continue.
            continue

        # Annualise: sigma_annual = sigma_daily * sqrt(252)
        annualised = daily_sigma * sqrt(_TRADING_DAYS_PER_YEAR)
        # As a percentage: multiply by 100. We stay in float through
        # the arithmetic for ``stdev`` compatibility, then quantise to
        # Decimal at the boundary so the JSON column round-trips
        # losslessly. ``Decimal(str(...))`` is the recommended path
        # for converting floats to Decimals (avoids binary-float
        # surprises like ``Decimal(0.1)``'s long tail).
        realised_vol_pct = Decimal(str(annualised * 100))

        if realised_vol_pct >= threshold:
            data: VolatilityEvaluationData = {
                "schema_version": CONDITION_PARAMS_SCHEMA_VERSION,
                "ticker": evaluator_input.ticker,
                "threshold_pct": str(threshold),
                "realised_vol_pct": str(realised_vol_pct),
                "over_days": params.over_days,
                "window_start": _to_iso_date(evaluator_input.window_start),
                "window_end": _to_iso_date(evaluator_input.window_end),
            }
            return True, data

    return False, None


def volatility_window(
    *,
    now: datetime,
    over_days: int,
) -> tuple[datetime, datetime]:
    """Return the ``(start, end)`` window for a volatility evaluation.

    Helper used by the composing service. Mirrors
    :func:`zebu.application.services.trigger_evaluators.drawdown.lookback_window`.

    Args:
        now: Reference timestamp (typically the scheduler tick time).
        over_days: Window width from :class:`VolatilityParams.over_days`.

    Returns:
        Tuple ``(window_start, window_end)`` where ``window_end == now``
        and ``window_start = now - over_days``.
    """
    from datetime import timedelta

    return now - timedelta(days=over_days), now


# ``date`` is re-exported so the service module can import it
# alongside the helpers without reaching back into ``datetime``.
__all__ = [
    "TickerClose",
    "VolatilityEvaluationData",
    "VolatilityEvaluatorInput",
    "date",
    "evaluate_volatility_spike",
    "volatility_window",
]
