"""Evaluator for the ``EARNINGS_PROXIMITY`` condition.

A trigger fires when **any** ticker in the activation's universe (or
the explicit subset on :class:`EarningsParams.tickers`) has scheduled
earnings within ``params.days_before`` days of ``now``.

Design references:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §1.2 (params),
  §1.5 (evaluation_data shape: ``ticker``, ``next_earnings_date``,
  ``days_until``, ``source``), §2.1.4 (evaluator contract — takes the
  earnings calendar port directly), §10 Q5 (port-deferred adapter).

Unlike :func:`evaluate_drawdown` and :func:`evaluate_volatility_spike`,
this evaluator takes the :class:`EarningsCalendarPort` directly per
the design's §2.1.4 table. It's still architecturally clean — the
evaluator is the only consumer of the port and the dependency is
explicit on the call. The composing :class:`TriggerEvaluationService`
just resolves the ticker list and forwards.

Boundary semantics (documented choice):
    Fires when ``days_until <= days_before`` — **inclusive**. An
    earnings event scheduled exactly ``days_before`` days from now
    fires on this tick. This matches the drawdown evaluator's
    inclusive boundary.

Multi-ticker fire-if-any semantics:
    Mirrors :func:`evaluate_volatility_spike`: the trigger fires on
    the first ticker with an in-window earnings event. The composer
    sorts the ticker list deterministically so the choice is
    reproducible.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TypedDict

from zebu.application.ports.earnings_calendar_port import (
    EarningsCalendarPort,
    EarningsEvent,
)
from zebu.domain.value_objects.trigger_condition import (
    CONDITION_PARAMS_SCHEMA_VERSION,
    EarningsParams,
)


@dataclass(frozen=True)
class EarningsEvaluatorInput:
    """Bundle of inputs the earnings evaluator needs.

    Attributes:
        tickers: Ticker symbols to query the calendar for. Caller
            (the composing service) is responsible for resolving
            ``params.tickers`` and the activation's universe into
            this list — the evaluator just forwards it to the port.
        now: Reference timestamp. ``now`` is *not* bound to
            :func:`datetime.now()` inside the evaluator so unit tests
            can pin the clock without monkeypatching.
    """

    tickers: list[str]
    now: datetime


class EarningsEvaluationData(TypedDict):
    """JSON-shaped snapshot of a fire's earnings inputs.

    Matches the schema documented in design §1.5 with the standard
    ``schema_version`` tag (Q8).

    - ``schema_version`` — always 1 in F-4.
    - ``ticker`` — the ticker that has the in-window event.
    - ``next_earnings_date`` — ISO-8601 date.
    - ``days_until`` — calendar days from ``now`` to the event,
      inclusive lower bound (0 means "today").
    - ``before_market_open`` — echoed from the source event so the
      activity feed can render "BMO" / "AMC" without re-fetching.
    - ``confirmed`` — echoed from the source event.
    - ``source`` — string identifier of the calendar adapter (e.g.
      ``"stub"``, ``"brave_mcp"``). Caller passes this so the audit
      row records *which* feed told us about the event.
    """

    schema_version: int
    ticker: str
    next_earnings_date: str
    days_until: int
    before_market_open: bool
    confirmed: bool
    source: str


def _days_until(*, event: EarningsEvent, now: datetime) -> int:
    """Calendar days from ``now`` to ``event.report_date``.

    ``now`` is treated as UTC. The result can be negative when the
    event is in the past — caller should filter those out before
    deciding to fire (and the port contract says it returns *upcoming*
    events anyway).
    """
    now_date = now.astimezone(UTC).date() if now.tzinfo is not None else now.date()
    delta = event.report_date - now_date
    return delta.days


async def evaluate_earnings_proximity(
    *,
    params: EarningsParams,
    inputs: EarningsEvaluatorInput,
    earnings_calendar: EarningsCalendarPort,
    source_label: str = "stub",
) -> tuple[bool, EarningsEvaluationData | None]:
    """Decide whether an ``EARNINGS_PROXIMITY`` condition fires.

    Args:
        params: The :class:`EarningsParams` from the trigger.
        inputs: The resolved ticker list + reference timestamp.
        earnings_calendar: The port the evaluator queries. With the
            F-4 default :class:`StubEarningsCalendarAdapter`, the
            response is always empty so the evaluator never fires —
            this is intentional per design Q5 (real source attaches
            via a third-party MCP later).
        source_label: Identifier of the calendar feed used. Echoed
            into the fire snapshot so the activity feed can render
            "earnings reported by <source>". Defaults to ``"stub"``;
            production wiring should pass a more specific label.

    Returns:
        ``(fired, evaluation_data)``. ``evaluation_data`` is ``None``
        on no-fire and a ready-to-persist
        :class:`EarningsEvaluationData` on fire.
    """
    if not inputs.tickers:
        return False, None

    # Fetch all upcoming events for the universe in a single call.
    # The port is responsible for honouring ``within_days`` so we
    # don't have to re-filter, but we still defensively cap the
    # response to events with ``days_until in [0, params.days_before]``
    # — guards against an adapter that returns more than asked.
    events = await earnings_calendar.upcoming_earnings(
        inputs.tickers, within_days=params.days_before
    )
    if not events:
        return False, None

    # Build a ticker-symbol set for fast membership checking — guards
    # against an adapter that returns events for tickers we didn't
    # ask about (some calendar feeds do this if they normalise
    # symbols differently).
    requested_tickers = set(inputs.tickers)

    # Iterate the requested tickers in caller order so the choice of
    # "first hit" is deterministic. Within a ticker, pick the
    # earliest-by-date event that lands in the window.
    events_by_ticker = _index_events_by_ticker(events)
    for ticker in inputs.tickers:
        if ticker not in requested_tickers:  # pragma: no cover  # defensive
            continue
        ticker_events = events_by_ticker.get(ticker, [])
        chosen = _pick_in_window_event(
            events=ticker_events,
            params=params,
            now=inputs.now,
        )
        if chosen is None:
            continue

        days_until = _days_until(event=chosen, now=inputs.now)
        data: EarningsEvaluationData = {
            "schema_version": CONDITION_PARAMS_SCHEMA_VERSION,
            "ticker": chosen.ticker,
            "next_earnings_date": chosen.report_date.isoformat(),
            "days_until": days_until,
            "before_market_open": chosen.before_market_open,
            "confirmed": chosen.confirmed,
            "source": source_label,
        }
        return True, data

    return False, None


def _index_events_by_ticker(
    events: Sequence[EarningsEvent],
) -> dict[str, list[EarningsEvent]]:
    """Group earnings events by ticker, preserving original order."""
    by_ticker: dict[str, list[EarningsEvent]] = {}
    for event in events:
        by_ticker.setdefault(event.ticker, []).append(event)
    return by_ticker


def _pick_in_window_event(
    *,
    events: list[EarningsEvent],
    params: EarningsParams,
    now: datetime,
) -> EarningsEvent | None:
    """Pick the closest in-window event, or ``None``.

    "In window" = ``0 <= days_until <= params.days_before``.

    Among multiple in-window events for the same ticker, pick the
    earliest (most imminent) so the snapshot reports the event the
    agent should reason about *first*. Ties are broken by
    ``confirmed=True`` over ``confirmed=False`` (a confirmed date
    beats a still-estimated one).
    """
    candidates: list[tuple[int, int, EarningsEvent]] = []
    for event in events:
        days = _days_until(event=event, now=now)
        if days < 0:
            continue
        if days > params.days_before:
            continue
        # Sort key: ``(days_until, confirmed_flag_inverted)`` so
        # smaller days_until wins, with confirmed=True (0) preferred
        # over confirmed=False (1) at ties.
        candidates.append((days, 0 if event.confirmed else 1, event))

    if not candidates:
        return None

    candidates.sort(key=lambda triple: (triple[0], triple[1]))
    return candidates[0][2]


def earnings_window(
    *,
    now: datetime,
    days_before: int,
) -> tuple[date, date]:
    """Return the ``(start, end)`` calendar-date window for an evaluation.

    Helper for the composing service / activity feed renderer; not
    used by the evaluator itself but kept here so consumers can
    reconstruct the window without re-deriving from ``now`` + params.

    Args:
        now: Reference timestamp.
        days_before: Window width from :class:`EarningsParams.days_before`.

    Returns:
        Tuple ``(window_start, window_end)`` where ``window_start``
        is the date of ``now`` and ``window_end = window_start +
        days_before``.
    """
    from datetime import timedelta

    base = now.astimezone(UTC).date() if now.tzinfo is not None else now.date()
    return base, base + timedelta(days=days_before)


__all__ = [
    "EarningsEvaluationData",
    "EarningsEvaluatorInput",
    "earnings_window",
    "evaluate_earnings_proximity",
]
