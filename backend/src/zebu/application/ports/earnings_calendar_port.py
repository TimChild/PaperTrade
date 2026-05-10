"""Port for fetching upcoming earnings events for tickers.

Used by the :func:`evaluate_earnings_proximity` evaluator to decide
whether a trigger should fire because at least one covered ticker is
within ``days_before`` of its next earnings report.

The port is deliberately narrow — :meth:`upcoming_earnings` is the only
read the evaluator needs. The Phase-F design (§10 Q5) defers picking
the *real* earnings source: it could be a third-party MCP (Brave /
Tavily / a dedicated earnings feed), a public REST API, or a paid feed.
The port lets the evaluator stay agnostic until that decision lands.

Implementations:

- ``StubEarningsCalendarAdapter`` (in
  ``zebu.adapters.outbound.earnings.stub_calendar_adapter``) — F-4
  default. Returns an empty list (no fires) so triggers don't
  spuriously wake the agent before a real source is configured.

References:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §1.2 (EarningsParams),
  §1.5 (evaluation_data shape), §2.1.4 (evaluator contract), §10 Q5
  (deferred adapter decision).
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class EarningsEvent:
    """One scheduled earnings report for a single ticker.

    Attributes:
        ticker: Symbol the report belongs to. Carried as a plain string
            (not :class:`Ticker`) because some external sources return
            tickers we don't know about; coercion to :class:`Ticker`
            happens at the evaluator boundary if at all.
        report_date: Calendar date the report is scheduled for. ``date``
            (not ``datetime``) because earnings calendars publish at
            day-granularity — the time-of-day comes from
            ``before_market_open``.
        before_market_open: ``True`` when the report is filed before
            the market opens (BMO); ``False`` when after the close
            (AMC). Some sources also surface "during market hours" — we
            collapse that to ``False`` (treat as AMC) per the design
            spec; the evaluator only uses this for tie-breaking when
            multiple events share a date.
        confirmed: ``True`` when the calendar source has confirmed the
            date (i.e. the company has formally announced it). ``False``
            for "estimated" / "projected" dates that may slip. The
            evaluator may surface this on the activity feed but does
            not currently filter on it — better to fire a few extra
            times than miss a real earnings window.
    """

    ticker: str
    report_date: date
    before_market_open: bool
    confirmed: bool


class EarningsCalendarPort(Protocol):
    """Protocol for fetching upcoming earnings events.

    Implementations live in ``adapters/outbound/earnings/``. The port
    is intentionally read-only — Zebu doesn't *publish* earnings data,
    only consumes it.
    """

    async def upcoming_earnings(
        self,
        tickers: list[str],
        within_days: int,
    ) -> list[EarningsEvent]:
        """Return upcoming earnings events for ``tickers``.

        The implementation is responsible for filtering by both the
        ticker list and the time window. The evaluator does *not*
        re-filter — it trusts the port to honour the contract so a
        future "fan-out to a remote MCP" adapter doesn't have to fetch
        the world to satisfy a small request.

        Args:
            tickers: Ticker symbols to look up. Empty list is permitted
                — implementations should return ``[]`` rather than
                error in that case (it's a no-op fetch, not an
                input-validation error).
            within_days: Inclusive upper bound on how far in the
                future to look, measured in *calendar* days from the
                current date (UTC). Must be ``>= 1`` — implementations
                may treat ``< 1`` as a contract violation.

        Returns:
            List of :class:`EarningsEvent`. The order is not specified;
            callers that care about ordering must sort. May contain
            multiple events per ticker (e.g. an estimate plus a
            confirmation), in which case the evaluator picks the
            closest in time.

        Note:
            Implementations should fail open — when the upstream
            source is unavailable, return ``[]`` and log rather than
            raising. The evaluator treats "no events" as "no fire",
            which is the safer default for an unreliable signal. This
            mirrors how :class:`MarketDataPort` adapters handle
            missing tickers (skip and log).
        """
        ...


__all__ = ["EarningsCalendarPort", "EarningsEvent"]
