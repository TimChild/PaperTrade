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

These are application-layer test fakes (matching
``in_memory_*_repository.py`` convention).
"""

from collections import deque
from collections.abc import Mapping

from zebu.application.ports.agent_invocation_port import (
    AgentInvocationResult,
    ToolDefinition,
)
from zebu.domain.exceptions import AgentInvocationError
from zebu.domain.value_objects.agent_decision import AgentDecision


class StaticAgentInvocationPort:
    """Always returns the same scripted result.

    The orchestrator tests instantiate this with the decision they want
    to exercise (BUY, SELL, HOLD, MODIFY_STRATEGY, NEEDS_HUMAN) and
    inspect the resulting audit row + side effects.

    Records each invocation so tests can assert what was sent to the
    "agent" — :attr:`invocations` is a list of (system, user, tools)
    tuples in call order.

    Attributes:
        result: Scripted :class:`AgentInvocationResult` returned on
            every :meth:`invoke` call.
        invocations: Recorded calls (tuple of system_prompt, user_prompt,
            tools). Useful for assertions in tests.
    """

    def __init__(self, *, result: AgentInvocationResult) -> None:
        """Initialise with the scripted result."""
        self._result = result
        self.invocations: list[tuple[str, str, list[ToolDefinition] | None, float]] = []

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
    ) -> AgentInvocationResult:
        """Record the call and return the scripted result."""
        self.invocations.append((system_prompt, user_prompt, tools, timeout_secs))
        return self._result


class ScriptedAgentInvocationPort:
    """Returns a queue of results in order.

    Used by integration tests that drive multiple trigger fires in one
    cycle and need each to receive a distinct decision.
    """

    def __init__(self, *, results: list[AgentInvocationResult]) -> None:
        """Initialise with the queue of results."""
        self._queue: deque[AgentInvocationResult] = deque(results)
        self.invocations: list[tuple[str, str, list[ToolDefinition] | None, float]] = []

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
    ) -> AgentInvocationResult:
        """Pop and return the next scripted result, or raise if empty."""
        self.invocations.append((system_prompt, user_prompt, tools, timeout_secs))
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
        self.invocations: list[tuple[str, str, list[ToolDefinition] | None, float]] = []

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
    ) -> AgentInvocationResult:
        """Record the call and raise."""
        self.invocations.append((system_prompt, user_prompt, tools, timeout_secs))
        raise AgentInvocationError(self._message)


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
    "ScriptedAgentInvocationPort",
    "StaticAgentInvocationPort",
    "make_result",
]
