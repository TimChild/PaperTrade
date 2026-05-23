"""In-memory :class:`AgentInvocationPort` for tests.

Provides a deterministic, programmable implementation so tests can
exercise the orchestrator without a real Anthropic call:

* :class:`StaticAgentInvocationPort` — always returns the same scripted
  result. Useful for "given decision X, the orchestrator does Y" tests.
* :class:`ScriptedAgentInvocationPort` — returns a queue of results in
  order; raises if the queue is exhausted. Useful for multi-trigger
  cycles where each trigger gets a different decision.
* :class:`FailingAgentInvocationPort` — always raises
  :class:`AgentInvocationError`, exercising the "agent call failed →
  INVOCATION_FAILED audit row" path.
* :class:`MockBacktestAgentInvocationPort` — Phase L-2 MOCK-mode port
  for the backtest pipeline. Always returns a deterministic, no-op
  :class:`AgentInvocationResult` (decision ``HOLD``) without touching
  the Anthropic SDK. The L-3 executor selects this port when the run's
  ``agent_invocation_mode`` is ``MOCK`` so audit rows are written
  end-to-end without paying for real API calls.

These are application-layer test fakes (matching
``in_memory_*_repository.py`` convention).
"""

from collections import deque
from collections.abc import Mapping

from zebu.application.ports.agent_invocation_port import (
    AgentInvocationResult,
    ToolDefinition,
    ToolDispatchCallback,
)
from zebu.domain.exceptions import AgentInvocationError
from zebu.domain.value_objects.agent_decision import AgentDecision


class StaticAgentInvocationPort:
    """Always returns the same scripted result.

    The orchestrator tests instantiate this with the decision they want
    to exercise (BUY, SELL, HOLD, MODIFY_STRATEGY, NEEDS_HUMAN) and
    inspect the resulting audit row + side effects.

    Records each invocation so tests can assert what was sent to the
    "agent" — :attr:`invocations` is a list of (system, user, tools,
    timeout_secs, agent_temperature) tuples in call order.

    Attributes:
        result: Scripted :class:`AgentInvocationResult` returned on
            every :meth:`invoke` call.
        invocations: Recorded calls (tuple of system_prompt, user_prompt,
            tools, timeout_secs, agent_temperature). Useful for
            assertions in tests.
    """

    def __init__(self, *, result: AgentInvocationResult) -> None:
        """Initialise with the scripted result."""
        self._result = result
        self.invocations: list[
            tuple[str, str, list[ToolDefinition] | None, float, float | None]
        ] = []

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
        agent_temperature: float | None = None,
        dispatch_tool_call: ToolDispatchCallback | None = None,
    ) -> AgentInvocationResult:
        """Record the call and return the scripted result.

        ``agent_temperature`` and ``dispatch_tool_call`` are recorded
        for assertion purposes (so L-2 tests can verify the wrapper
        plumbs them through) but are otherwise ignored — this fake is
        single-shot and sampling-free.
        """
        del dispatch_tool_call  # accepted for port parity; not used
        self.invocations.append(
            (system_prompt, user_prompt, tools, timeout_secs, agent_temperature)
        )
        return self._result


class ScriptedAgentInvocationPort:
    """Returns a queue of results in order.

    Used by integration tests that drive multiple trigger fires in one
    cycle and need each to receive a distinct decision.
    """

    def __init__(self, *, results: list[AgentInvocationResult]) -> None:
        """Initialise with the queue of results."""
        self._queue: deque[AgentInvocationResult] = deque(results)
        self.invocations: list[
            tuple[str, str, list[ToolDefinition] | None, float, float | None]
        ] = []

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
        agent_temperature: float | None = None,
        dispatch_tool_call: ToolDispatchCallback | None = None,
    ) -> AgentInvocationResult:
        """Pop and return the next scripted result, or raise if empty."""
        del dispatch_tool_call  # accepted for port parity; not used
        self.invocations.append(
            (system_prompt, user_prompt, tools, timeout_secs, agent_temperature)
        )
        if not self._queue:
            raise AgentInvocationError(
                "ScriptedAgentInvocationPort: result queue exhausted"
            )
        return self._queue.popleft()


class FailingAgentInvocationPort:
    """Always raises :class:`AgentInvocationError`.

    Used to exercise the "agent call failed → INVOCATION_FAILED audit
    row" path of the orchestrator.

    Attributes:
        message: Error message used in the raised exception. Defaults
            to a generic transport-failure message.
        invocations: Recorded calls (same shape as the other in-memory
            adapters) so tests can assert the orchestrator did try to
            invoke the agent.
    """

    def __init__(
        self,
        *,
        message: str = "Simulated Anthropic transport failure",
    ) -> None:
        """Initialise with the error message."""
        self._message = message
        self.invocations: list[
            tuple[str, str, list[ToolDefinition] | None, float, float | None]
        ] = []

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
        agent_temperature: float | None = None,
        dispatch_tool_call: ToolDispatchCallback | None = None,
    ) -> AgentInvocationResult:
        """Record the call and raise."""
        del dispatch_tool_call  # accepted for port parity; not used
        self.invocations.append(
            (system_prompt, user_prompt, tools, timeout_secs, agent_temperature)
        )
        raise AgentInvocationError(self._message)


class MockBacktestAgentInvocationPort:
    """Phase L-2 MOCK-mode port for the backtest pipeline.

    Always returns a deterministic, no-op
    :class:`AgentInvocationResult` (decision ``HOLD``) without touching
    the Anthropic SDK. Used by the L-3 executor when the run's
    ``agent_invocation_mode`` is :class:`BacktestAgentInvocationMode.MOCK`
    so the audit-write path is exercised end-to-end without paying for
    real API calls.

    The shape returned matches the MOCK-mode invariants on
    :class:`BacktestAgentInvocation` (per Task #217 §"Invariants"):

    * ``decision == AgentDecision.HOLD``
    * ``rationale == ""``
    * ``model == ""``
    * ``latency_ms == 0``
    * ``invocation_id is None``
    * ``payload == {"notes": "MOCK invocation — no action taken"}``

    The L-3 executor's audit-row writer is the boundary that bridges this
    result shape into the entity invariants — it sets
    ``invocation_mode=MOCK`` and ``decision_payload=None`` (per
    Task #217's MOCK invariants), while preserving the ``payload`` carried
    here for any structured-log emission.

    Attributes:
        invocations: Recorded calls (same shape as the other in-memory
            adapters) so tests can assert the executor wired MOCK mode
            into the port that bypassed the real adapter.
    """

    _MOCK_PAYLOAD: Mapping[str, object] = {"notes": "MOCK invocation — no action taken"}

    def __init__(self) -> None:
        """Initialise the MOCK port. No construction params required."""
        self.invocations: list[
            tuple[str, str, list[ToolDefinition] | None, float, float | None]
        ] = []

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
        agent_temperature: float | None = None,
        dispatch_tool_call: ToolDispatchCallback | None = None,
    ) -> AgentInvocationResult:
        """Return the deterministic MOCK result; never raises.

        ``dispatch_tool_call`` is accepted for port parity but never
        invoked — MOCK mode is no-op by definition and runs no
        tool-use loop.
        """
        del dispatch_tool_call  # accepted for port parity; not used
        self.invocations.append(
            (system_prompt, user_prompt, tools, timeout_secs, agent_temperature)
        )
        return AgentInvocationResult(
            decision=AgentDecision.HOLD,
            rationale="",
            payload=dict(self._MOCK_PAYLOAD),
            invocation_id=None,
            latency_ms=0,
            model="",
        )


def make_result(
    *,
    decision: AgentDecision,
    rationale: str = "Test rationale",
    payload: Mapping[str, object] | None = None,
    invocation_id: str = "msg_test_invocation",
    latency_ms: int = 250,
    model: str = "claude-haiku-4-5-20251001",
) -> AgentInvocationResult:
    """Convenience builder for scripted test results.

    The default payload is decision-appropriate so tests can pass a
    decision and not worry about constructing a valid payload manually.

    Args:
        decision: The agent decision to encode.
        rationale: Free-text rationale (persisted as ``agent_response_raw``).
        payload: Decision-specific payload. When ``None``, a default
            payload matching the decision shape is used.
        invocation_id: Anthropic message ID.
        latency_ms: Round-trip latency.
        model: Model identifier.

    Returns:
        :class:`AgentInvocationResult` ready to plug into a static port.
    """
    if payload is None:
        payload = _default_payload(decision)
    return AgentInvocationResult(
        decision=decision,
        rationale=rationale,
        payload=payload,
        invocation_id=invocation_id,
        latency_ms=latency_ms,
        model=model,
    )


def _default_payload(decision: AgentDecision) -> Mapping[str, object]:
    """Decision-appropriate default payload for test convenience."""
    match decision:
        case AgentDecision.BUY | AgentDecision.SELL:
            return {
                "ticker": "AAPL",
                "quantity": None,
                "notes": "Test trade",
            }
        case AgentDecision.HOLD:
            return {"notes": "Holding position"}
        case AgentDecision.MODIFY_STRATEGY:
            return {
                "parameter_overrides": {},
                "notes": "Modify strategy",
            }
        case AgentDecision.NEEDS_HUMAN:
            return {
                "summary": "Need human review",
                "urgency": "medium",
            }
        case AgentDecision.INVOCATION_FAILED:
            # The agent never returns INVOCATION_FAILED itself — it's
            # the executor's error sentinel — but the test fake
            # accepts it for parity.
            return {}


__all__ = [
    "FailingAgentInvocationPort",
    "MockBacktestAgentInvocationPort",
    "ScriptedAgentInvocationPort",
    "StaticAgentInvocationPort",
    "make_result",
]
