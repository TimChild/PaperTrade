"""Unit tests for :class:`MockBacktestAgentInvocationPort` (Phase L-2 / Task #218).

The MOCK-mode port is the deterministic no-op used by the L-3 backtest
executor when the run's ``agent_invocation_mode`` is ``MOCK``. The shape
of the returned :class:`AgentInvocationResult` is contractually frozen
(per Task #218 §"New port implementation"): always HOLD, empty
rationale, empty model, zero latency, no invocation id, payload of
``{"notes": "MOCK invocation — no action taken"}``.

The test enforces every one of those invariants so a future change to
the port can't silently drift the audit row's MOCK shape.
"""

from __future__ import annotations

from zebu.application.ports.in_memory_agent_invocation_port import (
    MockBacktestAgentInvocationPort,
)
from zebu.domain.value_objects.agent_decision import AgentDecision


class TestMockBacktestAgentInvocationPort:
    """Shape of the deterministic MOCK result, plus call recording."""

    async def test_returns_hold_decision(self) -> None:
        port = MockBacktestAgentInvocationPort()
        result = await port.invoke(system_prompt="s", user_prompt="u")
        assert result.decision is AgentDecision.HOLD

    async def test_returns_documented_payload(self) -> None:
        port = MockBacktestAgentInvocationPort()
        result = await port.invoke(system_prompt="s", user_prompt="u")
        assert result.payload == {"notes": "MOCK invocation — no action taken"}

    async def test_returns_empty_rationale(self) -> None:
        port = MockBacktestAgentInvocationPort()
        result = await port.invoke(system_prompt="s", user_prompt="u")
        assert result.rationale == ""

    async def test_returns_empty_model(self) -> None:
        port = MockBacktestAgentInvocationPort()
        result = await port.invoke(system_prompt="s", user_prompt="u")
        assert result.model == ""

    async def test_returns_zero_latency(self) -> None:
        port = MockBacktestAgentInvocationPort()
        result = await port.invoke(system_prompt="s", user_prompt="u")
        assert result.latency_ms == 0

    async def test_returns_no_invocation_id(self) -> None:
        port = MockBacktestAgentInvocationPort()
        result = await port.invoke(system_prompt="s", user_prompt="u")
        assert result.invocation_id is None

    async def test_records_invocations_for_test_assertions(self) -> None:
        """The MOCK port records its calls so L-3 tests can assert wiring."""
        port = MockBacktestAgentInvocationPort()
        await port.invoke(
            system_prompt="sys-1",
            user_prompt="usr-1",
        )
        await port.invoke(
            system_prompt="sys-2",
            user_prompt="usr-2",
            timeout_secs=30.0,
            agent_temperature=0.0,
        )
        assert len(port.invocations) == 2
        sys1, usr1, _tools1, _timeout1, _temp1 = port.invocations[0]
        sys2, usr2, _tools2, timeout2, temp2 = port.invocations[1]
        assert sys1 == "sys-1"
        assert usr1 == "usr-1"
        assert sys2 == "sys-2"
        assert usr2 == "usr-2"
        assert timeout2 == 30.0
        assert temp2 == 0.0

    async def test_multiple_invocations_return_identical_results(self) -> None:
        """Determinism: every call returns the same payload shape."""
        port = MockBacktestAgentInvocationPort()
        first = await port.invoke(system_prompt="s1", user_prompt="u1")
        second = await port.invoke(system_prompt="s2", user_prompt="u2")
        assert first.decision == second.decision
        assert first.payload == second.payload
        assert first.rationale == second.rationale
        assert first.model == second.model
        assert first.latency_ms == second.latency_ms
        assert first.invocation_id == second.invocation_id

    async def test_payload_not_shared_between_calls(self) -> None:
        """Mutating one call's payload must not affect the next call."""
        port = MockBacktestAgentInvocationPort()
        first = await port.invoke(system_prompt="s", user_prompt="u")
        # Defensive copy — mutating ``first.payload`` should not leak
        # into the next invocation.
        first_payload_dict = dict(first.payload)
        first_payload_dict["notes"] = "tampered"
        second = await port.invoke(system_prompt="s", user_prompt="u")
        assert second.payload == {"notes": "MOCK invocation — no action taken"}
