"""BacktestAgentInvocationMode value object — agent invocation mode for backtests.

Phase L (Task #217) — Foundation entity for the agent-driven backtest
pipeline. The mode is set per :class:`RunBacktestCommand` and recorded
durably on the :class:`BacktestRun` row, plus per
:class:`BacktestAgentInvocation` audit row.

Values:

* ``NONE`` — Backtests run without agent invocation. No simulated triggers
  are evaluated and no :class:`BacktestAgentInvocation` rows are written.
  Default — preserves the pre-Phase-L executor behavior.
* ``MOCK`` — The executor evaluates simulated triggers but the agent
  invocation port returns a deterministic, no-op decision. Used for
  cheap integration testing of executor wiring without paying for real
  Anthropic calls. Audit rows are written.
* ``LIVE`` — Real Anthropic calls via the L-2 backtest-safe wrapper
  adapter. Audit rows are written. Costs real money and is bounded by
  the L-6 cost guardrails.

Mirrors :class:`TriggerInvocationMode` in shape and naming convention.
StrEnum so wire serialisation matches the lowercase token directly.
"""

from enum import StrEnum


class BacktestAgentInvocationMode(StrEnum):
    """How a backtest pipeline invokes the agent on simulated trigger fires.

    Values:
        NONE: Existing pre-Phase-L behavior — no agent invocation, no
            simulated triggers evaluated, no audit rows written. Default.
        MOCK: Evaluate simulated triggers but use a deterministic, no-op
            decision (no Anthropic calls). Audit rows are persisted so
            the wiring is exercised end-to-end.
        LIVE: Real Anthropic invocation via the L-2 backtest-safe
            adapter. Audit rows are persisted. Costs real API spend.
    """

    NONE = "none"
    MOCK = "mock"
    LIVE = "live"
