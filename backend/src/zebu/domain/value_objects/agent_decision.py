"""AgentDecision value object — the structured response a woken agent emits.

When a trigger fires and the evaluator invokes the Anthropic Messages API
with the strategy + condition snapshot, the agent must terminate the
conversation by calling the ``record_decision`` virtual tool. The
:class:`AgentDecision` enum is the discriminator for the decision the tool
records.

See ``docs/architecture/phase-f-agent-in-the-loop.md`` §1.6 for the
per-decision payload contract and §3.3 for how the adapter forces the
``record_decision`` call.

The ``INVOCATION_FAILED`` value is system-generated, not chosen by the
agent: when the Anthropic call errors (transport, parse failure, missing
``record_decision`` call), the executor still writes an audit row with
this value so the activity feed shows the failed attempt instead of
silently dropping it.

This entity ships in F-1 as scaffolding. The decision-execution logic
that maps each value to a side effect lands in F-3.
"""

from enum import StrEnum


class AgentDecision(StrEnum):
    """The structured decision a woken trigger-fire agent emits.

    Values:
        BUY: Agent decided to buy a position. Payload includes
            ``ticker``, optional ``quantity`` (None = "default sizing — let
            the strategy decide"), and ``notes``.
        SELL: Agent decided to sell. Same payload shape as BUY with
            direction reversed.
        HOLD: Agent decided to do nothing. Payload includes ``notes``.
            Still recorded as a fire row so audit chronology is intact.
        MODIFY_STRATEGY: Agent proposed a change to the strategy's
            parameters. Payload includes ``parameter_overrides`` and
            ``notes``. The executor validates each override against the
            strategy's parameter VO and rejects forbidden fields (notably
            ``tickers`` — that would change the asset universe and is a
            security boundary).
        NEEDS_HUMAN: Agent escalated to the human via a new
            ``ExplorationTask``. Payload includes ``summary`` and
            ``urgency`` (low / medium / high).
        INVOCATION_FAILED: System-generated when the Anthropic call
            errored (transport, parse, missing ``record_decision``). Not a
            value the agent picks itself.
    """

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    MODIFY_STRATEGY = "MODIFY_STRATEGY"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    INVOCATION_FAILED = "INVOCATION_FAILED"
