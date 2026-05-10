"""Tests for the :func:`evaluate_earnings_proximity` evaluator (Phase F-4).

Boundary cases covered:

* Calendar returns no events ⇒ no fire (the F-4 stub default).
* One ticker, one event in window ⇒ fire.
* One ticker, one event outside window ⇒ no fire.
* Multi-ticker, one ticker has an in-window event ⇒ fire on that ticker.
* Multi-ticker, none have in-window events ⇒ no fire.
* Empty ticker list ⇒ no fire (defensive).
* Boundary: event exactly ``days_before`` days away ⇒ fire (inclusive).
* Past-dated events from the calendar ⇒ ignored.
* Multiple events for one ticker ⇒ closest-by-date wins.
* Confirmed beats estimated when ties on date.
* Calendar returns a ticker we didn't ask for ⇒ ignored.

The evaluator takes the calendar port directly (per design §2.1.4); we
use a small in-memory fake calendar — not a mock, an actual class
implementing the port — to exercise the firing path without depending
on an external service.
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from zebu.application.ports.earnings_calendar_port import (
    EarningsCalendarPort,
    EarningsEvent,
)
from zebu.application.services.trigger_evaluators.earnings_proximity import (
    EarningsEvaluatorInput,
    earnings_window,
    evaluate_earnings_proximity,
)
from zebu.domain.value_objects.trigger_condition import EarningsParams

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeEarningsCalendar:
    """In-memory implementation of :class:`EarningsCalendarPort`.

    Not a mock — a deterministic fake. Lets the firing-path tests
    exercise the evaluator without needing a real upstream source.
    The F-4 default :class:`StubEarningsCalendarAdapter` is exercised
    in a separate suite (``test_stub_earnings_adapter`` at the
    integration level).
    """

    def __init__(self, events: list[EarningsEvent]) -> None:
        self._events = events
        # Capture call args so tests can assert the evaluator passes
        # the right ticker list / window through.
        self.calls: list[tuple[list[str], int]] = []

    async def upcoming_earnings(
        self,
        tickers: list[str],
        within_days: int,
    ) -> list[EarningsEvent]:
        """Return events filtered by ticker only.

        We can't filter by ``within_days`` here because we don't have
        ``now``; a production adapter has access to its own clock and
        would. The evaluator does its own window check defensively, so
        this fake exercises that path correctly.
        """
        self.calls.append((list(tickers), within_days))
        ticker_set = set(tickers)
        return [event for event in self._events if event.ticker in ticker_set]


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 10, 14, 30, tzinfo=UTC)
_NOW_DATE = _NOW.date()


def _params(*, days_before: int = 5) -> EarningsParams:
    """EarningsParams with sensible defaults."""
    return EarningsParams(days_before=days_before)


def _event(
    *,
    ticker: str,
    days_from_now: int,
    before_market_open: bool = True,
    confirmed: bool = True,
) -> EarningsEvent:
    """Build an :class:`EarningsEvent` ``days_from_now`` from ``_NOW``."""
    return EarningsEvent(
        ticker=ticker,
        report_date=_NOW_DATE + timedelta(days=days_from_now),
        before_market_open=before_market_open,
        confirmed=confirmed,
    )


def _inputs(*tickers: str, now: datetime = _NOW) -> EarningsEvaluatorInput:
    """Build EarningsEvaluatorInput for one or more tickers."""
    return EarningsEvaluatorInput(tickers=list(tickers), now=now)


# ---------------------------------------------------------------------------
# No-fire scenarios
# ---------------------------------------------------------------------------


class TestNoFireScenarios:
    """Calendar empty / no in-window events."""

    @pytest.mark.asyncio
    async def test_empty_calendar_does_not_fire(self) -> None:
        """No events from the port ⇒ no fire (F-4 stub default)."""
        calendar: EarningsCalendarPort = _FakeEarningsCalendar(events=[])
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is False
        assert data is None

    @pytest.mark.asyncio
    async def test_event_outside_window_does_not_fire(self) -> None:
        """Earnings 30 days out vs window=7 ⇒ no fire."""
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=30)]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is False
        assert data is None

    @pytest.mark.asyncio
    async def test_past_event_does_not_fire(self) -> None:
        """An event with ``days_until < 0`` is skipped (already happened)."""
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=-1)]
        )
        fired, _ = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is False

    @pytest.mark.asyncio
    async def test_empty_ticker_list_does_not_fire(self) -> None:
        """No tickers to query ⇒ no fire (defensive — service should
        also short-circuit before this, but the contract is documented).
        """
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=2)]
        )
        fired, _ = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs(),  # empty
            earnings_calendar=calendar,
        )

        assert fired is False

    @pytest.mark.asyncio
    async def test_multi_ticker_none_in_window_does_not_fire(self) -> None:
        """Two tickers, both with events 30 days out ⇒ no fire."""
        calendar = _FakeEarningsCalendar(
            events=[
                _event(ticker="AAPL", days_from_now=30),
                _event(ticker="MSFT", days_from_now=30),
            ]
        )
        fired, _ = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL", "MSFT"),
            earnings_calendar=calendar,
        )

        assert fired is False


# ---------------------------------------------------------------------------
# Fire scenarios
# ---------------------------------------------------------------------------


class TestFireScenarios:
    """Events inside the window ⇒ fire on the right ticker."""

    @pytest.mark.asyncio
    async def test_single_ticker_in_window_fires(self) -> None:
        """One ticker, event in window ⇒ fire and data identifies the ticker."""
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=2)]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] == "AAPL"
        assert data["days_until"] == 2
        assert data["next_earnings_date"] == (_NOW_DATE + timedelta(days=2)).isoformat()
        assert data["before_market_open"] is True
        assert data["confirmed"] is True

    @pytest.mark.asyncio
    async def test_event_at_exact_boundary_fires(self) -> None:
        """Event exactly ``days_before`` days out ⇒ fire (inclusive boundary)."""
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=7)]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert data["days_until"] == 7

    @pytest.mark.asyncio
    async def test_event_today_fires(self) -> None:
        """Event with ``days_until == 0`` (today) ⇒ fire (boundary)."""
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=0)]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert data["days_until"] == 0

    @pytest.mark.asyncio
    async def test_multi_ticker_only_one_in_window_fires_correctly(self) -> None:
        """Two tickers; only one has an in-window event ⇒ fire on it."""
        calendar = _FakeEarningsCalendar(
            events=[
                _event(ticker="AAPL", days_from_now=30),  # outside
                _event(ticker="MSFT", days_from_now=2),  # inside
            ]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL", "MSFT"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] == "MSFT"

    @pytest.mark.asyncio
    async def test_multi_ticker_first_in_iter_order_wins(self) -> None:
        """Two tickers both in window ⇒ first by caller iteration wins."""
        # AAPL first in caller list and has an in-window event ⇒ AAPL.
        calendar = _FakeEarningsCalendar(
            events=[
                _event(ticker="AAPL", days_from_now=4),
                _event(ticker="MSFT", days_from_now=2),
            ]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL", "MSFT"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert data["ticker"] == "AAPL"
        assert data["days_until"] == 4

    @pytest.mark.asyncio
    async def test_multiple_events_for_ticker_picks_closest(self) -> None:
        """Two events for one ticker ⇒ pick the closest-by-date."""
        # Hypothetical: confirmed Q3 vs estimated Q4 — pick Q3.
        calendar = _FakeEarningsCalendar(
            events=[
                _event(ticker="AAPL", days_from_now=5),
                _event(ticker="AAPL", days_from_now=2),
            ]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert data["days_until"] == 2

    @pytest.mark.asyncio
    async def test_confirmed_event_beats_estimated_at_same_date(self) -> None:
        """Two events on the same date ⇒ confirmed wins on tie-break."""
        calendar = _FakeEarningsCalendar(
            events=[
                _event(ticker="AAPL", days_from_now=3, confirmed=False),
                _event(ticker="AAPL", days_from_now=3, confirmed=True),
            ]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert data["confirmed"] is True

    @pytest.mark.asyncio
    async def test_calendar_returns_unrequested_ticker_is_ignored(self) -> None:
        """Adapter returns extra ticker we didn't ask about ⇒ ignored."""
        # Calendar returns NVDA but we asked about AAPL only.
        calendar = _FakeEarningsCalendar(
            events=[
                _event(ticker="NVDA", days_from_now=2),
            ]
        )

        # Force the fake to return NVDA even when we ask for AAPL —
        # bypass the fake's own filter so the evaluator's defence is
        # what's exercised.
        class _NoisyCalendar:
            async def upcoming_earnings(
                self,
                tickers: list[str],
                within_days: int,
            ) -> list[EarningsEvent]:
                del tickers, within_days
                return [_event(ticker="NVDA", days_from_now=2)]

        fired, _ = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=_NoisyCalendar(),
        )

        del calendar  # use the noisier one in the assertion
        assert fired is False


# ---------------------------------------------------------------------------
# Snapshot data shape
# ---------------------------------------------------------------------------


class TestEvaluationDataShape:
    """Snapshot returned by the evaluator carries the design §1.5 fields."""

    @pytest.mark.asyncio
    async def test_includes_required_design_fields(self) -> None:
        """All §1.5 fields present on a fire."""
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=3)]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
            source_label="brave_mcp",
        )

        assert fired is True
        assert data is not None
        assert data["schema_version"] == 1
        for required_field in (
            "ticker",
            "next_earnings_date",
            "days_until",
            "before_market_open",
            "confirmed",
            "source",
        ):
            assert required_field in data, f"Missing required field {required_field!r}"
        # Source label propagates from the caller for audit-row attribution.
        assert data["source"] == "brave_mcp"

    @pytest.mark.asyncio
    async def test_default_source_label_is_stub(self) -> None:
        """When the caller doesn't pass a source label, default is ``"stub"``."""
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=3)]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert data["source"] == "stub"

    @pytest.mark.asyncio
    async def test_next_earnings_date_is_iso_date(self) -> None:
        """``next_earnings_date`` is a 10-char ISO date string."""
        calendar = _FakeEarningsCalendar(
            events=[_event(ticker="AAPL", days_from_now=3)]
        )
        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=7),
            inputs=_inputs("AAPL"),
            earnings_calendar=calendar,
        )

        assert fired is True
        assert data is not None
        assert len(data["next_earnings_date"]) == 10
        date.fromisoformat(data["next_earnings_date"])


# ---------------------------------------------------------------------------
# Stub adapter behaviour
# ---------------------------------------------------------------------------


class TestStubEarningsCalendarAdapter:
    """The F-4 default adapter returns ``[]`` for all calls."""

    @pytest.mark.asyncio
    async def test_stub_returns_empty_list(self) -> None:
        """Per design Q5: stub never reports earnings (until real source attached)."""
        from zebu.adapters.outbound.earnings.stub_calendar_adapter import (
            StubEarningsCalendarAdapter,
        )

        adapter = StubEarningsCalendarAdapter()
        result = await adapter.upcoming_earnings(["AAPL", "MSFT"], within_days=7)

        assert result == []

    @pytest.mark.asyncio
    async def test_stub_returns_empty_for_empty_input(self) -> None:
        """Empty input is also empty output (no error)."""
        from zebu.adapters.outbound.earnings.stub_calendar_adapter import (
            StubEarningsCalendarAdapter,
        )

        adapter = StubEarningsCalendarAdapter()
        result = await adapter.upcoming_earnings([], within_days=14)

        assert result == []

    @pytest.mark.asyncio
    async def test_evaluator_with_stub_never_fires(self) -> None:
        """End-to-end: evaluator + stub ⇒ no fire (the F-4 default state)."""
        from zebu.adapters.outbound.earnings.stub_calendar_adapter import (
            StubEarningsCalendarAdapter,
        )

        fired, data = await evaluate_earnings_proximity(
            params=_params(days_before=14),
            inputs=_inputs("AAPL", "MSFT"),
            earnings_calendar=StubEarningsCalendarAdapter(),
        )

        assert fired is False
        assert data is None


# ---------------------------------------------------------------------------
# earnings_window helper
# ---------------------------------------------------------------------------


class TestEarningsWindow:
    """Helper that constructs the calendar-date window."""

    def test_window_anchors_at_now_date(self) -> None:
        """``window_start`` is today; ``window_end = today + days_before``."""
        now = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
        start, end = earnings_window(now=now, days_before=7)

        assert start == date(2026, 1, 15)
        assert end == date(2026, 1, 22)

    def test_window_with_naive_datetime_treats_as_utc(self) -> None:
        """Naive ``now`` is treated as UTC (no exception)."""
        now = datetime(2026, 1, 15, 9, 0)
        start, _ = earnings_window(now=now, days_before=7)

        assert start == date(2026, 1, 15)
