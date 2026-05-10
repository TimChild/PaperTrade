"""Tests for :class:`AnthropicAgentInvocationAdapter` (Phase F-3).

The Anthropic SDK's response shape (Message + ToolUseBlock) is what
the adapter parses. Rather than full VCR / cassette replay (deferred
to F-7 per the design), these tests mock the SDK at the
``AsyncAnthropic.messages.create`` boundary so adapter behavior is
exercised without a network call.

Why mock at the SDK rather than the HTTP transport (respx etc.)?
- The adapter is the boundary. Its contract is "given a prompt, call
  the SDK and return :class:`AgentInvocationResult`." Testing the
  adapter against the SDK's typed objects (Message, ToolUseBlock) is
  the most behavior-focused choice.
- HTTP-level cassettes are more brittle to SDK version bumps than
  object-shape mocks; the design doc explicitly accepts deferring real
  cassettes to F-7.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest
from anthropic.types import Message, TextBlock, ToolUseBlock

from zebu.adapters.outbound.anthropic.agent_invocation_adapter import (
    AnthropicAgentInvocationAdapter,
)
from zebu.application.ports.agent_invocation_port import ToolDefinition
from zebu.domain.exceptions import (
    AgentInvocationError,
    AgentResponseParseError,
)
from zebu.domain.value_objects.agent_decision import AgentDecision

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _build_message(
    *,
    decision: str | None = "HOLD",
    rationale: str = "All looks fine, holding.",
    payload_overrides: dict[str, object] | None = None,
    free_text: str | None = None,
    msg_id: str = "msg_test_id_12345",
    include_tool_use: bool = True,
) -> Message:
    """Build a fake :class:`Message` mimicking an Anthropic response.

    The adapter expects:
    - ``content`` is a list of ContentBlock objects.
    - One ``ToolUseBlock`` with ``name="record_decision"`` and ``input``
      containing the decision payload.
    - Optionally text blocks for the rationale fallback.
    """
    content: list[ToolUseBlock | TextBlock] = []
    if free_text:
        text_block = MagicMock(spec=TextBlock)
        text_block.type = "text"
        text_block.text = free_text
        content.append(text_block)

    if include_tool_use:
        tool_input: dict[str, object] = {}
        if decision is not None:
            tool_input["decision"] = decision
        tool_input["rationale"] = rationale
        if payload_overrides:
            tool_input.update(payload_overrides)

        tool_use = MagicMock(spec=ToolUseBlock)
        tool_use.name = "record_decision"
        tool_use.input = tool_input
        tool_use.id = "toolu_test_id"
        content.append(tool_use)

    message = MagicMock(spec=Message)
    message.id = msg_id
    message.content = content
    message.stop_reason = "tool_use"
    return cast("Message", message)


def _build_adapter_with_mock(
    *,
    message: Message | None = None,
    side_effect: Exception | None = None,
    model: str = "claude-haiku-4-5-20251001",
) -> tuple[AnthropicAgentInvocationAdapter, AsyncMock]:
    """Build an adapter with a mocked AsyncAnthropic client."""
    mock_client = MagicMock(spec=anthropic.AsyncAnthropic)
    mock_create = AsyncMock()
    if side_effect is not None:
        mock_create.side_effect = side_effect
    elif message is not None:
        mock_create.return_value = message
    mock_client.messages = MagicMock()
    mock_client.messages.create = mock_create

    adapter = AnthropicAgentInvocationAdapter(
        client=mock_client,
        model=model,
    )
    return adapter, mock_create


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_raises_when_no_api_key_and_no_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without an explicit api_key or client, ANTHROPIC_API_KEY required."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(AgentInvocationError) as exc_info:
            AnthropicAgentInvocationAdapter()
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_uses_explicit_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        adapter = AnthropicAgentInvocationAdapter(api_key="sk-test-explicit")
        assert adapter.model == "claude-haiku-4-5-20251001"

    def test_reads_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("ZEBU_AGENT_MODEL", "claude-sonnet-4-6")
        adapter = AnthropicAgentInvocationAdapter()
        assert adapter.model == "claude-sonnet-4-6"

    def test_explicit_client_bypasses_env_check(self) -> None:
        """A pre-built client argument means no env check needed."""
        mock_client = MagicMock(spec=anthropic.AsyncAnthropic)
        adapter = AnthropicAgentInvocationAdapter(client=mock_client)
        assert adapter.model == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Invoke — happy paths
# ---------------------------------------------------------------------------


class TestInvokeHappyPaths:
    async def test_hold_decision_parses_correctly(self) -> None:
        message = _build_message(decision="HOLD", rationale="No action needed")
        adapter, _mock_create = _build_adapter_with_mock(message=message)

        result = await adapter.invoke(
            system_prompt="Be a trigger agent.",
            user_prompt="Trigger fired, decide.",
        )

        assert result.decision is AgentDecision.HOLD
        assert result.rationale == "No action needed"
        assert result.invocation_id == "msg_test_id_12345"
        assert result.latency_ms >= 0
        assert result.payload == {"notes": ""}

    async def test_buy_decision_parses_payload(self) -> None:
        message = _build_message(
            decision="BUY",
            rationale="Buying on dip",
            payload_overrides={
                "ticker": "AAPL",
                "quantity": "10",
                "notes": "Accumulate on weakness",
            },
        )
        adapter, _ = _build_adapter_with_mock(message=message)

        result = await adapter.invoke(
            system_prompt="Be a trigger agent.",
            user_prompt="Trigger fired, decide.",
        )

        assert result.decision is AgentDecision.BUY
        assert result.payload["ticker"] == "AAPL"
        assert result.payload["quantity"] == "10"
        assert result.payload["notes"] == "Accumulate on weakness"

    async def test_modify_strategy_parses_overrides(self) -> None:
        message = _build_message(
            decision="MODIFY_STRATEGY",
            rationale="Reducing exposure",
            payload_overrides={
                "parameter_overrides": {"invest_fraction": "0.25"},
                "notes": "De-risk",
            },
        )
        adapter, _ = _build_adapter_with_mock(message=message)

        result = await adapter.invoke(
            system_prompt="Be a trigger agent.",
            user_prompt="Trigger fired, decide.",
        )

        assert result.decision is AgentDecision.MODIFY_STRATEGY
        assert result.payload["parameter_overrides"] == {"invest_fraction": "0.25"}
        assert result.payload["notes"] == "De-risk"

    async def test_needs_human_parses_summary_and_urgency(self) -> None:
        message = _build_message(
            decision="NEEDS_HUMAN",
            rationale="Earnings tomorrow",
            payload_overrides={
                "summary": "Pre-earnings drawdown — review",
                "urgency": "high",
            },
        )
        adapter, _ = _build_adapter_with_mock(message=message)

        result = await adapter.invoke(
            system_prompt="Be a trigger agent.",
            user_prompt="Trigger fired, decide.",
        )

        assert result.decision is AgentDecision.NEEDS_HUMAN
        assert result.payload["summary"] == "Pre-earnings drawdown — review"
        assert result.payload["urgency"] == "high"

    async def test_falls_back_to_free_text_for_rationale(self) -> None:
        """If rationale is empty, fall back to the free-text content."""
        message = _build_message(
            decision="HOLD",
            rationale="",
            free_text="My analysis: holding through the volatility.",
        )
        adapter, _ = _build_adapter_with_mock(message=message)

        result = await adapter.invoke(system_prompt="Sys", user_prompt="User")
        assert result.rationale == "My analysis: holding through the volatility."


# ---------------------------------------------------------------------------
# Invoke — error paths
# ---------------------------------------------------------------------------


class TestInvokeErrorPaths:
    async def test_raises_parse_error_when_no_record_decision_call(self) -> None:
        message = _build_message(include_tool_use=False, free_text="just text")
        adapter, _ = _build_adapter_with_mock(message=message)

        with pytest.raises(AgentResponseParseError) as exc_info:
            await adapter.invoke(system_prompt="s", user_prompt="u")
        assert "did not include a record_decision" in str(exc_info.value)

    async def test_raises_parse_error_when_decision_field_missing(self) -> None:
        message = _build_message(decision=None)  # tool_input lacks 'decision'
        adapter, _ = _build_adapter_with_mock(message=message)

        with pytest.raises(AgentResponseParseError) as exc_info:
            await adapter.invoke(system_prompt="s", user_prompt="u")
        assert "missing 'decision'" in str(exc_info.value)

    async def test_raises_parse_error_for_unknown_decision_value(self) -> None:
        message = _build_message(decision="UNKNOWN_DECISION_TYPE")
        adapter, _ = _build_adapter_with_mock(message=message)

        with pytest.raises(AgentResponseParseError) as exc_info:
            await adapter.invoke(system_prompt="s", user_prompt="u")
        assert "Unknown decision" in str(exc_info.value)

    async def test_rejects_invocation_failed_from_agent(self) -> None:
        """The agent must not return INVOCATION_FAILED — it's a system value."""
        message = _build_message(decision="INVOCATION_FAILED")
        adapter, _ = _build_adapter_with_mock(message=message)

        with pytest.raises(AgentResponseParseError) as exc_info:
            await adapter.invoke(system_prompt="s", user_prompt="u")
        assert "INVOCATION_FAILED" in str(exc_info.value)

    async def test_authentication_error_propagates_as_invocation_error(
        self,
    ) -> None:
        """Non-transient errors propagate immediately.

        Mock a 401 APIStatusError directly with a real status_code so
        the retry decision branch (status >= 500) evaluates correctly.
        """
        response = MagicMock()
        response.status_code = 401
        body = {"error": {"message": "Invalid API key"}}
        auth_error = anthropic.AuthenticationError(
            message="Invalid API key", response=response, body=body
        )
        # Override the SDK's `.status_code` to a real int (the SDK
        # populates it from response, but in the mocked path we set it
        # explicitly to avoid the MagicMock leakage).
        object.__setattr__(auth_error, "status_code", 401)
        adapter, _ = _build_adapter_with_mock(side_effect=auth_error)

        with pytest.raises(AgentInvocationError) as exc_info:
            await adapter.invoke(system_prompt="s", user_prompt="u")
        # Auth is non-transient — should NOT be wrapped in retry message.
        assert "Anthropic API call failed" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Tool / system block construction
# ---------------------------------------------------------------------------


class TestToolAndSystemBlocks:
    async def test_record_decision_tool_is_prepended(self) -> None:
        message = _build_message(decision="HOLD")
        adapter, mock_create = _build_adapter_with_mock(message=message)

        await adapter.invoke(system_prompt="s", user_prompt="u")

        call_kwargs = mock_create.call_args.kwargs
        tools = call_kwargs["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "record_decision"

    async def test_caller_supplied_tools_appear_after_record_decision(
        self,
    ) -> None:
        message = _build_message(decision="HOLD")
        adapter, mock_create = _build_adapter_with_mock(message=message)

        caller_tools = [
            ToolDefinition(
                name="get_portfolio_state",
                description="Read portfolio state",
                input_schema={
                    "type": "object",
                    "properties": {},
                },
            )
        ]
        await adapter.invoke(system_prompt="s", user_prompt="u", tools=caller_tools)

        tools = mock_create.call_args.kwargs["tools"]
        assert tools[0]["name"] == "record_decision"
        assert tools[1]["name"] == "get_portfolio_state"

    async def test_system_prompt_carries_cache_control(self) -> None:
        """Prompt caching must be enabled on the system block."""
        message = _build_message(decision="HOLD")
        adapter, mock_create = _build_adapter_with_mock(message=message)

        await adapter.invoke(
            system_prompt="A long system prompt that benefits from caching.",
            user_prompt="u",
        )

        call_kwargs = mock_create.call_args.kwargs
        system_blocks = call_kwargs["system"]
        assert isinstance(system_blocks, list)
        assert len(system_blocks) == 1
        assert system_blocks[0]["type"] == "text"
        assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
        assert (
            system_blocks[0]["text"]
            == "A long system prompt that benefits from caching."
        )

    async def test_forces_record_decision_via_tool_choice(self) -> None:
        message = _build_message(decision="HOLD")
        adapter, mock_create = _build_adapter_with_mock(message=message)

        await adapter.invoke(system_prompt="s", user_prompt="u")

        tool_choice = mock_create.call_args.kwargs["tool_choice"]
        assert tool_choice == {"type": "tool", "name": "record_decision"}

    async def test_passes_timeout_to_sdk(self) -> None:
        message = _build_message(decision="HOLD")
        adapter, mock_create = _build_adapter_with_mock(message=message)

        await adapter.invoke(system_prompt="s", user_prompt="u", timeout_secs=15.0)
        assert mock_create.call_args.kwargs["timeout"] == 15.0

    async def test_uses_configured_model(self) -> None:
        message = _build_message(decision="HOLD")
        adapter, mock_create = _build_adapter_with_mock(
            message=message, model="claude-opus-4-7"
        )
        result = await adapter.invoke(system_prompt="s", user_prompt="u")
        assert mock_create.call_args.kwargs["model"] == "claude-opus-4-7"
        assert result.model == "claude-opus-4-7"
