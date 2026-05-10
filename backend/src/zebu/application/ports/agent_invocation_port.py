"""AgentInvocationPort — abstract Anthropic Messages API call.

Phase F-3 of the agent platform. The port abstracts "send a prompt to an
agent, get back a structured decision" so the application layer doesn't
import the Anthropic SDK and tests can swap deterministic stubs.

The implementation lives in
``adapters/outbound/anthropic/agent_invocation_adapter.py`` and uses the
Anthropic Messages API's tool-use mechanism to coerce a typed
:class:`AgentInvocationResult` rather than parsing free-text.

References:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §2.1.5 (port spec),
  §3.3 (tool-use protocol — the agent terminates the conversation by
  calling a virtual ``record_decision`` tool).
- :class:`AgentDecision` for the discriminated decision values.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from zebu.domain.value_objects.agent_decision import AgentDecision


@dataclass(frozen=True)
class ToolDefinition:
    """A tool the agent may call during its reasoning.

    The shape mirrors the Anthropic Messages API's ``tools`` block — the
    adapter passes the list straight through, with one synthetic
    ``record_decision`` tool prepended so the agent has a guaranteed
    terminator.

    Attributes:
        name: Tool name as the model sees it (e.g.
            ``"mcp__zebu__get_portfolio_state"``).
        description: Natural-language description shown to the model.
        input_schema: JSON-Schema-shaped mapping describing the input
            parameters. The adapter forwards this verbatim; F-3 ships
            with a minimal schema (no MCP read-tools wired into the
            prompt yet — that's F-4 / F-5).
    """

    name: str
    description: str
    input_schema: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentInvocationResult:
    """The structured result of one agent invocation.

    Returned by :meth:`AgentInvocationPort.invoke`. Carries the parsed
    decision, the agent's free-text rationale, the per-decision payload,
    and observability metadata for the audit row.

    Attributes:
        decision: The decision the agent recorded by calling
            ``record_decision``. One of :class:`AgentDecision`'s values
            except ``INVOCATION_FAILED`` (which is reserved for the
            executor to write when the call itself errors — the agent
            never returns this).
        rationale: The agent's free-text reasoning. Persisted on the
            audit row as ``agent_response_raw``. Truncated to 8000 chars
            at write time by the audit entity.
        payload: Decision-specific payload. Shape depends on
            ``decision`` (see :class:`AgentDecision` docstring for the
            per-decision contracts):

            * ``BUY`` / ``SELL``: ``{"ticker": str, "quantity": str | None,
              "notes": str}`` (quantity as string for Decimal round-trip;
              None means "default sizing").
            * ``HOLD``: ``{"notes": str}``.
            * ``MODIFY_STRATEGY``: ``{"parameter_overrides": dict[str, object],
              "notes": str}``.
            * ``NEEDS_HUMAN``: ``{"summary": str, "urgency": str}``
              where urgency is one of ``low`` / ``medium`` / ``high``.

            The orchestrator validates the payload shape before acting.
        invocation_id: Anthropic message ID. ``None`` if the SDK didn't
            return one (older SDK versions, mocked transports).
        latency_ms: Round-trip latency from "send the request" to "receive
            the final response" in milliseconds. ``>= 0``.
        model: The Anthropic model identifier used for this invocation
            (e.g. ``"claude-haiku-4-5-20251001"``). Persisted in
            structured logs for cost-attribution analysis.
    """

    decision: AgentDecision
    rationale: str
    payload: Mapping[str, object]
    invocation_id: str | None
    latency_ms: int
    model: str


class AgentInvocationPort(Protocol):
    """Port abstraction over the Anthropic Messages API.

    Implementations:

    * :class:`AnthropicAgentInvocationAdapter`
      (``adapters.outbound.anthropic.agent_invocation_adapter``) —
      production adapter, calls Anthropic with tool-use coercion.
    * :class:`StaticAgentInvocationPort` (and friends) in
      ``application.ports.in_memory_agent_invocation_port`` — test
      fakes used by the orchestrator's unit + integration tests.

    The port returns :class:`AgentInvocationResult` on success and raises
    :class:`AgentInvocationError` (or its
    :class:`AgentResponseParseError` subclass) on failure. The
    orchestrator translates failures into ``INVOCATION_FAILED``
    :class:`TriggerFireRecord` rows so the audit chain captures every
    fire attempt.
    """

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
    ) -> AgentInvocationResult:
        """Send a prompt to the agent and return its structured decision.

        Args:
            system_prompt: System-level message bounding the agent (paper
                trading only, operating-manual guardrails, etc.). Cached
                across invocations by the production adapter — see
                Anthropic's prompt-caching docs.
            user_prompt: Per-invocation user message — the trigger fire
                context (strategy state, portfolio state, condition
                snapshot, the trigger's ``agent_prompt``).
            tools: Optional list of tool definitions the agent may call.
                The adapter prepends a synthetic ``record_decision`` tool
                that the agent must call to terminate the conversation.
                ``None`` is equivalent to ``[]``.
            timeout_secs: Per-call timeout. The adapter passes this into
                the SDK's ``timeout`` parameter. Default 60s.

        Returns:
            :class:`AgentInvocationResult` with the parsed decision and
            audit metadata.

        Raises:
            AgentInvocationError: Transport failure (network error, API
                authentication failure, rate limit exhausted after retries).
            AgentResponseParseError: The model returned a response that
                couldn't be coerced into a structured decision (e.g. it
                terminated without calling ``record_decision``, or the
                payload didn't match the expected shape for the chosen
                decision).
        """
        ...


__all__ = [
    "AgentInvocationPort",
    "AgentInvocationResult",
    "ToolDefinition",
]
