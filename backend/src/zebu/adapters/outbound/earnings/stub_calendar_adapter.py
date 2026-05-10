"""Stub adapter for :class:`EarningsCalendarPort` — F-4 default.

Per Phase-F design Q5 (`docs/architecture/phase-f-agent-in-the-loop.md`),
the *real* earnings calendar source is deferred — it will be attached at
runtime via a third-party MCP (Brave / Tavily / a dedicated earnings
feed) once the wider plumbing is in place. F-4 ships an explicit stub so
the dispatch path is wired end-to-end while the upstream-source
discussion is still open.

The stub returns an empty list for every call. Semantically this means
"no upcoming earnings within the requested window" — i.e. the
:class:`EarningsProximityEvaluator` never fires on this adapter. That
is the safer default: trigger fires woke the agent (which costs an LLM
call), so the failure mode here favours under-firing over noise.

When the real adapter lands:

- Replace this in the DI wiring (``adapters/inbound/api/dependencies.py``)
  with the production adapter.
- The port contract stays the same — no evaluator changes required.
- This stub stays in the codebase as a deterministic fixture for
  unit and integration tests that don't want to hit a real source.

TODO(Phase F follow-up): pick the real source (Q5) and write the
adapter alongside this one.
"""

from zebu.application.ports.earnings_calendar_port import EarningsEvent


class StubEarningsCalendarAdapter:
    """No-op implementation of :class:`EarningsCalendarPort`.

    Returns an empty list of :class:`EarningsEvent` for every call.
    Suitable for:

    - Default DI wiring in F-4 (until a real source is configured).
    - Tests that want a deterministic "no earnings" baseline without
      needing to construct a more elaborate fake.

    Not suitable for:

    - Tests of the *firing* path of :class:`EarningsProximityEvaluator`
      — those should construct a small in-test fake (or use the
      ``InMemoryEarningsCalendarAdapter`` if/when one is added)
      because the stub by definition can never fire.
    """

    async def upcoming_earnings(
        self,
        tickers: list[str],
        within_days: int,
    ) -> list[EarningsEvent]:
        """Return ``[]`` for any input.

        Args:
            tickers: Ignored — the stub never returns events for any
                ticker.
            within_days: Ignored — see above.

        Returns:
            Empty list.
        """
        # Ignore both inputs intentionally — the contract is "no
        # events known". Using ``del`` keeps Pyright happy without
        # adding a type-ignore.
        del tickers, within_days
        return []


__all__ = ["StubEarningsCalendarAdapter"]
