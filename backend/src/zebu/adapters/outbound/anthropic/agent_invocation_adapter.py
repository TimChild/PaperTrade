"""Anthropic Messages API adapter for :class:`AgentInvocationPort`.

Phase F-3 of the agent platform. Implements the trigger-fire agent
invocation by calling the Anthropic Messages API with the tool-use
mechanism: the adapter prepends a synthetic ``record_decision`` tool,
forces the agent to terminate by calling it, and parses the typed
response into :class:`AgentInvocationResult`.

Design references:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §2.1.5
  (port spec), §3.3 (record_decision protocol), §3.4 (prompt
  assembly).
- :class:`AgentInvocationPort` for the contract.

Key decisions (per skill guidance):
- **Prompt caching** on the system prompt — the system prompt is
  identical across invocations and a perfect cache candidate. The
  adapter sets ``cache_control: ephemeral`` on the system block.
- **Model:** ``claude-haiku-4-5-20251001`` by default (the trigger-fire
  context is small; Haiku 4.5 is the right cost tier). Override via
  ``ZEBU_AGENT_MODEL`` env.
- **API key:** read from ``ANTHROPIC_API_KEY`` env at construction;
  raises if missing in production.
- **Timeout:** caller-supplied (default 60s in the port). Passed to the
  SDK's ``timeout`` parameter.
- **Retries:** bounded retry (max 2) with exponential backoff for
  transient errors (network, rate limit). Non-transient errors (auth,
  invalid input) propagate immediately.

The adapter does **not** implement an agent reasoning loop in F-3 — the
agent reads the user prompt, then calls ``record_decision`` once. F-4
will introduce MCP read-tool calls inside this loop so the agent can
gather additional context before deciding.
"""

import asyncio
import json
import logging
import os
import time
from collections.abc import Mapping
from typing import cast

import anthropic
from anthropic.types import Message, MessageParam, ToolParam, ToolUseBlock

from zebu.application.ports.agent_invocation_port import (
    AgentInvocationResult,
    ToolDefinition,
    ToolDispatchCallback,
)
from zebu.domain.exceptions import (
    AgentInvocationError,
    AgentResponseParseError,
)
from zebu.domain.value_objects.agent_decision import AgentDecision

logger = logging.getLogger(__name__)


# Default model — Haiku 4.5 is the right cost tier for the trigger-fire
# context (small prompt, single decision call). Configurable via env.
_DEFAULT_MODEL: str = "claude-haiku-4-5-20251001"

# Token cap for the structured decision call. The agent only ever needs
# to write a brief rationale + a small JSON payload, so this is generous
# without wasting tokens.
_MAX_TOKENS: int = 4096

# Retry settings for transient errors. The Anthropic SDK has built-in
# retries for connection errors / 429 / 5xx; we layer additional retries
# at the adapter level so a temporary failure doesn't immediately become
# an INVOCATION_FAILED audit row.
_MAX_RETRIES: int = 2
_RETRY_INITIAL_BACKOFF_SECS: float = 1.0

# Maximum number of tool-use loop turns before the adapter gives up.
# Each turn = one ``messages.create`` round-trip + one batch of tool
# dispatches. 20 turns is generous for the L-2 backtest path (the agent
# rarely needs more than a few read-tool calls before deciding) but
# guards against an unbounded loop on a malformed callback.
_MAX_TOOL_USE_TURNS: int = 20


# --------------------------------------------------------------------------- #
# record_decision tool schema                                                 #
# --------------------------------------------------------------------------- #


def _build_record_decision_tool() -> ToolParam:
    """Construct the JSON-schema for the synthetic ``record_decision`` tool.

    The agent **must** call this tool to terminate the conversation.
    The schema uses ``oneOf`` over the discriminator-style payloads so
    the model is steered to a per-decision payload shape. The adapter
    validates the actually-emitted shape after the call.

    Returns:
        :class:`ToolParam` ready to pass into the Anthropic SDK.
    """
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": [
                    AgentDecision.BUY.value,
                    AgentDecision.SELL.value,
                    AgentDecision.HOLD.value,
                    AgentDecision.MODIFY_STRATEGY.value,
                    AgentDecision.NEEDS_HUMAN.value,
                ],
                "description": (
                    "The structured decision. BUY/SELL execute a paper "
                    "trade on the activation's portfolio. HOLD records "
                    "the fire but takes no action. MODIFY_STRATEGY "
                    "updates the strategy parameters (asset universe is "
                    "not modifiable). NEEDS_HUMAN escalates via an "
                    "ExplorationTask flagged for human review."
                ),
            },
            "rationale": {
                "type": "string",
                "description": (
                    "Free-text rationale for the decision (1-1000 chars). "
                    "Persisted on the audit row for review."
                ),
            },
            "ticker": {
                "type": "string",
                "description": (
                    "Required for BUY/SELL. The ticker symbol to trade "
                    "(must be in the strategy's ticker list)."
                ),
            },
            "quantity": {
                "type": "string",
                "description": (
                    "Optional for BUY/SELL. Number of shares as a "
                    "decimal string. Omit (or use null) for default "
                    "sizing — the strategy decides."
                ),
            },
            "notes": {
                "type": "string",
                "description": (
                    "Required for BUY/SELL/HOLD/MODIFY_STRATEGY. Brief "
                    "operational note for the audit trail."
                ),
            },
            "parameter_overrides": {
                "type": "object",
                "description": (
                    "Required for MODIFY_STRATEGY. Map of strategy "
                    "parameter name to new value. The 'tickers' field "
                    "is forbidden — that would change the asset universe."
                ),
                "additionalProperties": True,
            },
            "summary": {
                "type": "string",
                "description": (
                    "Required for NEEDS_HUMAN. Short summary of why "
                    "human review is needed."
                ),
            },
            "urgency": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": (
                    "Required for NEEDS_HUMAN. Urgency tier for the escalation."
                ),
            },
        },
        "required": ["decision", "rationale"],
    }
    return cast(
        "ToolParam",
        {
            "name": "record_decision",
            "description": (
                "Final-step tool. Call exactly once to record your "
                "decision. The conversation ends when this is called."
            ),
            "input_schema": schema,
        },
    )


# --------------------------------------------------------------------------- #
# Adapter                                                                     #
# --------------------------------------------------------------------------- #


class AnthropicAgentInvocationAdapter:
    """Production :class:`AgentInvocationPort` backed by the Anthropic API.

    Construction reads ``ANTHROPIC_API_KEY`` from env (or accepts an
    explicit ``api_key`` argument for tests). Reads the model from
    ``ZEBU_AGENT_MODEL`` if set, defaulting to Haiku 4.5.

    The adapter is async; the underlying client is :class:`anthropic.AsyncAnthropic`.
    Concurrency: a single instance is safe to share across coroutines —
    the SDK's async client is connection-pooled.

    Attributes:
        model: The Anthropic model identifier used for invocations.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        """Initialise the adapter.

        Args:
            api_key: Anthropic API key. When ``None``, reads
                ``ANTHROPIC_API_KEY`` from env. Raises if neither is set.
            model: Model identifier. When ``None``, reads
                ``ZEBU_AGENT_MODEL`` from env, defaulting to Haiku 4.5.
            client: Pre-built :class:`anthropic.AsyncAnthropic` client.
                Tests use this to inject a mocked transport.

        Raises:
            AgentInvocationError: If ``api_key`` is not provided and
                ``ANTHROPIC_API_KEY`` is not in the environment.
        """
        resolved_key = (
            api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        )
        if client is None and not resolved_key:
            raise AgentInvocationError(
                "ANTHROPIC_API_KEY is not set. The Anthropic adapter "
                "requires an API key to invoke the trigger-fire agent. "
                "Set ANTHROPIC_API_KEY in the environment or pass an "
                "explicit api_key argument."
            )

        self._client = client or anthropic.AsyncAnthropic(api_key=resolved_key)
        self.model = model or os.environ.get("ZEBU_AGENT_MODEL", _DEFAULT_MODEL)

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
        """Send the prompt to Anthropic and return the parsed decision.

        See :meth:`AgentInvocationPort.invoke` for the base contract.
        This implementation has two modes:

        **Single-shot (``dispatch_tool_call`` is ``None``)** — Phase F-3
        behaviour, preserved unchanged. The model is forced to call
        ``record_decision`` via ``tool_choice``, the response is parsed
        immediately, and the call returns. No tool-use loop runs.

        **Multi-turn tool-use loop (``dispatch_tool_call`` provided)** —
        Phase L-2 behaviour. The model is allowed to call
        ``record_decision`` OR any caller-supplied read tool. When it
        calls a read tool, the adapter invokes ``dispatch_tool_call`` to
        execute it, appends a ``tool_result`` to the conversation, and
        re-issues ``messages.create`` until the model calls
        ``record_decision`` (or :attr:`_MAX_TOOL_USE_TURNS` is exceeded).
        The dispatch callback is the only place safety enforcement
        lives — the wrapper supplies a closure that validates each call
        against ``simulated_date`` and raises
        :class:`BacktestSafetyViolationError` on violation.

        Args:
            system_prompt: System-level message bounding the agent.
            user_prompt: Per-invocation user message.
            tools: Optional list of tool definitions the agent may call
                (in addition to the synthetic ``record_decision``).
            timeout_secs: Per-call timeout passed to the SDK.
            agent_temperature: Optional override for the model's
                ``temperature`` parameter. When not ``None``, passed
                through to ``messages.create``; when ``None``, the SDK's
                default applies. Added in Phase L-2 for the backtest
                wrapper's ``temperature=0`` default.
            dispatch_tool_call: Optional callback that executes
                non-``record_decision`` tool calls. When ``None`` the
                adapter uses the F-3 single-shot path; when supplied the
                adapter runs the multi-turn tool-use loop and routes each
                tool call through the callback.

        Raises:
            AgentInvocationError: Transport / authentication failure
                (after retries), or invalid input rejected by the API,
                or the tool-use loop exceeded :attr:`_MAX_TOOL_USE_TURNS`
                without the model calling ``record_decision``.
                :class:`BacktestSafetyViolationError` raised by the
                dispatch callback propagates as a subclass.
            AgentResponseParseError: The model's response did not call
                ``record_decision`` or the payload didn't match the
                expected shape for the chosen decision.
        """
        tool_blocks = self._build_tool_blocks(tools or [])
        system_blocks = self._build_system_blocks(system_prompt)
        messages: list[MessageParam] = [
            {"role": "user", "content": user_prompt},
        ]

        start = time.perf_counter()
        try:
            if dispatch_tool_call is None:
                (
                    message,
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    cache_creation_tokens,
                ) = await self._invoke_single_shot(
                    system_blocks=system_blocks,
                    messages=messages,
                    tools=tool_blocks,
                    timeout_secs=timeout_secs,
                    agent_temperature=agent_temperature,
                )
            else:
                (
                    message,
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    cache_creation_tokens,
                ) = await self._invoke_tool_use_loop(
                    system_blocks=system_blocks,
                    messages=messages,
                    tools=tool_blocks,
                    timeout_secs=timeout_secs,
                    agent_temperature=agent_temperature,
                    dispatch_tool_call=dispatch_tool_call,
                )
        except anthropic.APIError as exc:
            # Non-transient API error after retries (auth, malformed
            # input, etc.). Surface as AgentInvocationError so the
            # orchestrator records INVOCATION_FAILED.
            raise AgentInvocationError(
                f"Anthropic API call failed: {exc}",
                cause=exc,
            ) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        return self._parse_response(
            message=message,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read_tokens,
            cache_creation_input_tokens=cache_creation_tokens,
        )

    async def _invoke_single_shot(
        self,
        *,
        system_blocks: list[dict[str, object]],
        messages: list[MessageParam],
        tools: list[ToolParam],
        timeout_secs: float,
        agent_temperature: float | None,
    ) -> tuple[Message, int, int, int, int]:
        """F-3 single-shot path: force ``record_decision`` via ``tool_choice``.

        The model has no opportunity to call read tools — it must
        terminate immediately by calling ``record_decision``. Identical
        in behaviour to the pre-L-2 implementation; preserved when no
        :data:`ToolDispatchCallback` is provided to :meth:`invoke`.

        Returns the final :class:`Message` along with the input/output
        token counts from the single round-trip. Token counts are read
        from :attr:`Message.usage`; when the SDK / a test fake omits the
        attribute we fall back to ``0`` rather than crashing — L-6's
        cost accumulator treats 0 as "free", which is the right
        behaviour for non-billable invocations.
        """
        message = await self._invoke_with_retry(
            system_blocks=system_blocks,
            messages=messages,
            tools=tools,
            timeout_secs=timeout_secs,
            agent_temperature=agent_temperature,
            tool_choice={"type": "tool", "name": "record_decision"},
        )
        (
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_creation_tokens,
        ) = _extract_usage(message)
        return (
            message,
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_creation_tokens,
        )

    async def _invoke_tool_use_loop(
        self,
        *,
        system_blocks: list[dict[str, object]],
        messages: list[MessageParam],
        tools: list[ToolParam],
        timeout_secs: float,
        agent_temperature: float | None,
        dispatch_tool_call: ToolDispatchCallback,
    ) -> tuple[Message, int, int, int, int]:
        """Phase L-2 multi-turn tool-use loop.

        Iterates the Messages API conversation until the model calls
        ``record_decision`` or :attr:`_MAX_TOOL_USE_TURNS` is exceeded.
        Each turn:

        1. Call ``messages.create`` with ``tool_choice="auto"`` (so the
           model may emit either a read-tool call or
           ``record_decision``).
        2. Inspect the response. If it contains a ``record_decision``
           tool-use block, return immediately — the outer
           :meth:`_parse_response` builds the result.
        3. Otherwise, for each non-``record_decision`` tool-use block,
           call the dispatch callback with the tool name + input;
           collect the string result.
        4. Append the assistant message + a follow-up user message
           containing the ``tool_result`` blocks. Re-enter the loop.

        :class:`BacktestSafetyViolationError` raised by the dispatch
        callback propagates immediately — the wrapper's safety contract
        is "violation aborts the invocation".

        Returns the terminator :class:`Message` along with the
        cross-turn-accumulated input / output token totals (Phase L-6 —
        the budget accumulator needs every turn's tokens, not just the
        final turn's).

        Raises:
            AgentInvocationError: Loop exceeded
                :attr:`_MAX_TOOL_USE_TURNS` without
                ``record_decision``; or the model returned with
                ``stop_reason != "tool_use"`` and no terminator.
        """
        # Mutable copy: each turn appends an assistant + a user(tool_result).
        conversation: list[MessageParam] = list(messages)
        input_tokens_total: int = 0
        output_tokens_total: int = 0
        cache_read_tokens_total: int = 0
        cache_creation_tokens_total: int = 0

        for turn in range(_MAX_TOOL_USE_TURNS):
            message = await self._invoke_with_retry(
                system_blocks=system_blocks,
                messages=conversation,
                tools=tools,
                timeout_secs=timeout_secs,
                agent_temperature=agent_temperature,
                tool_choice={"type": "auto"},
            )
            turn_in, turn_out, turn_cache_read, turn_cache_creation = _extract_usage(
                message
            )
            input_tokens_total += turn_in
            output_tokens_total += turn_out
            cache_read_tokens_total += turn_cache_read
            cache_creation_tokens_total += turn_cache_creation

            tool_uses: list[ToolUseBlock] = [
                block for block in message.content if isinstance(block, ToolUseBlock)
            ]

            # Terminator: the model called ``record_decision``. Return
            # immediately so :meth:`_parse_response` extracts it.
            if any(block.name == "record_decision" for block in tool_uses):
                return (
                    message,
                    input_tokens_total,
                    output_tokens_total,
                    cache_read_tokens_total,
                    cache_creation_tokens_total,
                )

            # No terminator AND no read-tool calls: the model returned
            # plain text. Surface as an invocation error — the parse
            # path would also fail, but distinguishing "ran out of
            # tools to call" from "couldn't parse the response" makes
            # the audit row more diagnostic.
            if not tool_uses:
                raise AgentInvocationError(
                    "Tool-use loop ended without a record_decision call "
                    f"(turn {turn + 1}/{_MAX_TOOL_USE_TURNS}, "
                    f"stop_reason={message.stop_reason!r})"
                )

            # Dispatch each read-tool call. The callback may raise
            # :class:`BacktestSafetyViolationError`; we let it propagate
            # untouched so the L-3 executor sees the original cause.
            tool_results: list[Mapping[str, object]] = []
            for block in tool_uses:
                tool_input = dict(cast("Mapping[str, object]", block.input))
                content = await dispatch_tool_call(block.name, tool_input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content,
                    }
                )

            # Echo the assistant message back, then append a user
            # message with the tool_result blocks. The SDK reconstructs
            # the assistant turn from ``message.content`` blocks as
            # ``ContentBlockParam`` dicts.
            conversation.append(
                {
                    "role": "assistant",
                    "content": cast(
                        "list[object]",  # type: ignore[arg-type]
                        message.content,
                    ),
                }
            )
            conversation.append(
                {
                    "role": "user",
                    "content": cast(
                        "list[object]",  # type: ignore[arg-type]
                        tool_results,
                    ),
                }
            )

        # Exhausted turn budget — the model kept calling read tools
        # without ever terminating with ``record_decision``.
        raise AgentInvocationError(
            "Tool-use loop exceeded "
            f"max turns ({_MAX_TOOL_USE_TURNS}) without a record_decision call"
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _build_tool_blocks(self, caller_tools: list[ToolDefinition]) -> list[ToolParam]:
        """Build the SDK tools list with ``record_decision`` prepended.

        The synthetic ``record_decision`` tool is always present and
        serves as the conversation terminator. Any caller-supplied tools
        (typically MCP read tools in F-4+) follow.
        """
        record_tool = _build_record_decision_tool()
        result: list[ToolParam] = [record_tool]
        for tool in caller_tools:
            result.append(
                cast(
                    "ToolParam",
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": dict(tool.input_schema),
                    },
                )
            )
        return result

    @staticmethod
    def _build_system_blocks(system_prompt: str) -> list[dict[str, object]]:
        """Build the system message with prompt caching enabled.

        The system prompt is the largest static element of the trigger
        invocation; caching it gives ~10x cost reduction on repeated
        fires. The ``cache_control: ephemeral`` annotation tells the
        Anthropic API to cache the prefix up to and including this
        block (5-minute default TTL).
        """
        return [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    async def _invoke_with_retry(
        self,
        *,
        system_blocks: list[dict[str, object]],
        messages: list[MessageParam],
        tools: list[ToolParam],
        timeout_secs: float,
        agent_temperature: float | None = None,
        tool_choice: Mapping[str, object] | None = None,
    ) -> Message:
        """Call the Messages API with bounded retry on transient errors.

        Transient = network hiccup, rate-limit, 5xx. Non-transient
        (auth, 4xx other than 429) propagates immediately so we don't
        burn retries on a request that will never succeed.

        The Anthropic SDK already does some retries; this layers on a
        small additional cushion specifically for the trigger-fire path
        where one transient bump shouldn't fail the audit.

        Args:
            system_blocks: System message blocks (with cache_control).
            messages: Conversation history. May include prior
                assistant + tool_result turns when called from inside
                the tool-use loop.
            tools: SDK ``ToolParam`` list — ``record_decision`` plus any
                caller tools.
            timeout_secs: Per-call timeout.
            agent_temperature: Optional override for the model's
                ``temperature`` sampling parameter. When ``None`` the
                SDK's default applies; when set, passed through verbatim.
            tool_choice: Tool-choice directive. When ``None``, defaults
                to forcing ``record_decision`` (preserves F-3
                single-shot behaviour). The L-2 loop passes
                ``{"type": "auto"}`` so the model may call read tools
                before terminating.
        """
        resolved_tool_choice: Mapping[str, object] = (
            tool_choice
            if tool_choice is not None
            else {"type": "tool", "name": "record_decision"}
        )
        backoff = _RETRY_INITIAL_BACKOFF_SECS
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                create_kwargs: dict[str, object] = {
                    "model": self.model,
                    "max_tokens": _MAX_TOKENS,
                    "system": cast("object", system_blocks),
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": resolved_tool_choice,
                    "timeout": timeout_secs,
                }
                if agent_temperature is not None:
                    create_kwargs["temperature"] = agent_temperature
                return await self._client.messages.create(**create_kwargs)  # type: ignore[arg-type]
            except (
                anthropic.APIConnectionError,
                anthropic.RateLimitError,
                anthropic.APITimeoutError,
            ) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "Transient Anthropic error — retrying",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": _MAX_RETRIES,
                            "backoff_secs": backoff,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                # Out of retries — fall through.
                break
            except anthropic.APIStatusError as exc:
                # 5xx errors are transient; everything else (4xx auth /
                # validation) is not.
                if exc.status_code >= 500 and attempt < _MAX_RETRIES:
                    last_exc = exc
                    logger.warning(
                        "Anthropic 5xx — retrying",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": _MAX_RETRIES,
                            "backoff_secs": backoff,
                            "status": exc.status_code,
                        },
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise

        # Exhausted retries.
        assert last_exc is not None  # noqa: S101  - invariant from loop
        raise AgentInvocationError(
            f"Anthropic call failed after {_MAX_RETRIES + 1} attempts: {last_exc}",
            cause=last_exc,
        ) from last_exc

    def _parse_response(
        self,
        *,
        message: Message,
        latency_ms: int,
        input_tokens: int,
        output_tokens: int,
        cache_read_input_tokens: int = 0,
        cache_creation_input_tokens: int = 0,
    ) -> AgentInvocationResult:
        """Coerce the Messages API response into :class:`AgentInvocationResult`.

        The model is forced to call ``record_decision`` via
        ``tool_choice``, so the expected shape is one
        :class:`ToolUseBlock` with ``name=record_decision``. We also
        capture any free-text the model emitted before the tool call
        as the rationale fallback.

        Args:
            message: Final SDK :class:`Message` (the terminator turn).
            latency_ms: Total wall-clock latency of the invocation.
            input_tokens: Cross-turn-accumulated input-token total
                (Phase L-6). Surfaced verbatim on the result for the
                L-6 budget accumulator.
            output_tokens: Cross-turn-accumulated output-token total
                (Phase L-6).
            cache_read_input_tokens: Cross-turn-accumulated cache-read
                input-token total. Billed at 0.1× the standard input rate.
            cache_creation_input_tokens: Cross-turn-accumulated
                cache-creation input-token total. Billed at 1.25× the
                standard input rate.

        Raises:
            AgentResponseParseError: If no ``record_decision`` tool-use
                block is found, or the payload doesn't match the
                expected shape for the chosen decision.
        """
        free_text_parts: list[str] = []
        tool_use: ToolUseBlock | None = None

        for block in message.content:
            if isinstance(block, ToolUseBlock) and block.name == "record_decision":
                tool_use = block
            elif hasattr(block, "type") and block.type == "text":  # type: ignore[union-attr]
                # `text` is the SDK's TextBlock — extract via attribute.
                free_text_parts.append(getattr(block, "text", ""))

        if tool_use is None:
            raise AgentResponseParseError(
                "Anthropic response did not include a record_decision tool "
                "call. Stop reason: "
                f"{message.stop_reason}; content blocks: "
                f"{[type(b).__name__ for b in message.content]}"
            )

        # The SDK types tool_use.input as ``Dict[str, object]`` so
        # pyright considers a runtime dict-check redundant. We trust the
        # SDK's typing here — the Anthropic API is contractually
        # required to return a JSON object on tool_use blocks.
        payload = dict(cast("Mapping[str, object]", tool_use.input))

        decision_str = payload.get("decision")
        if not isinstance(decision_str, str):
            raise AgentResponseParseError(
                "record_decision payload missing 'decision' field"
            )
        try:
            decision = AgentDecision(decision_str)
        except ValueError as exc:
            raise AgentResponseParseError(
                f"Unknown decision value: {decision_str!r}"
            ) from exc

        if decision is AgentDecision.INVOCATION_FAILED:
            # The agent should never select INVOCATION_FAILED itself —
            # that's a system-generated sentinel. Treat as parse error.
            raise AgentResponseParseError(
                "Agent attempted to record decision=INVOCATION_FAILED; "
                "this value is system-generated only"
            )

        rationale_obj = payload.get("rationale")
        rationale_text: str
        if isinstance(rationale_obj, str) and rationale_obj.strip():
            rationale_text = rationale_obj
        elif free_text_parts:
            # Fallback: model wrote prose then forgot rationale.
            rationale_text = "\n".join(free_text_parts).strip()
        else:
            rationale_text = ""

        # Build per-decision payload. The orchestrator will validate
        # required fields before acting; the adapter only enforces the
        # decision-discriminator + rationale here.
        decision_payload = self._build_decision_payload(decision=decision, raw=payload)

        invocation_id: str | None = message.id if message.id else None

        return AgentInvocationResult(
            decision=decision,
            rationale=rationale_text,
            payload=decision_payload,
            invocation_id=invocation_id,
            latency_ms=latency_ms,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
        )

    @staticmethod
    def _build_decision_payload(
        *,
        decision: AgentDecision,
        raw: Mapping[str, object],
    ) -> Mapping[str, object]:
        """Extract the per-decision payload from the raw tool input.

        Different decisions take different fields; this normalises the
        payload shape so the orchestrator can match on
        :attr:`AgentInvocationResult.decision` and reach for known keys.
        Optional fields are coerced to ``None`` rather than dropped to
        keep the JSON shape predictable on the audit row.
        """
        notes_obj = raw.get("notes")
        notes = notes_obj if isinstance(notes_obj, str) else ""

        match decision:
            case AgentDecision.BUY | AgentDecision.SELL:
                ticker_obj = raw.get("ticker")
                quantity_obj = raw.get("quantity")
                ticker = ticker_obj if isinstance(ticker_obj, str) else ""
                if isinstance(quantity_obj, str) and quantity_obj.strip():
                    quantity: str | None = quantity_obj
                elif quantity_obj is None:
                    quantity = None
                else:
                    # Coerce numeric to string for round-trip integrity.
                    quantity = str(quantity_obj)
                return {
                    "ticker": ticker,
                    "quantity": quantity,
                    "notes": notes,
                }
            case AgentDecision.HOLD:
                return {"notes": notes}
            case AgentDecision.MODIFY_STRATEGY:
                overrides_obj = raw.get("parameter_overrides")
                overrides: Mapping[str, object]
                if isinstance(overrides_obj, Mapping):
                    overrides = dict(cast("Mapping[str, object]", overrides_obj))
                else:
                    overrides = {}
                return {
                    "parameter_overrides": overrides,
                    "notes": notes,
                }
            case AgentDecision.NEEDS_HUMAN:
                summary_obj = raw.get("summary")
                urgency_obj = raw.get("urgency")
                summary = summary_obj if isinstance(summary_obj, str) else ""
                urgency = (
                    urgency_obj
                    if isinstance(urgency_obj, str)
                    and urgency_obj in ("low", "medium", "high")
                    else "medium"
                )
                return {"summary": summary, "urgency": urgency}
            case AgentDecision.INVOCATION_FAILED:
                # Defensive — the parse step rejects this earlier.
                return {}


def _stable_dumps(obj: object) -> str:
    """JSON-dump with sorted keys for deterministic representations.

    Used in tests and structured logs where byte-stable output matters.
    """
    return json.dumps(obj, sort_keys=True, default=str)


def _extract_usage(message: Message) -> tuple[int, int, int, int]:
    """Extract per-message token counts from one SDK :class:`Message`.

    Returns ``(input_tokens, output_tokens, cache_read_input_tokens,
    cache_creation_input_tokens)``. The Anthropic SDK's
    :class:`Message.usage` reports these as **separate fields** —
    ``input_tokens`` covers fresh (non-cached) input only; cache reads
    and cache writes are billed at different rates (0.1× and 1.25× of
    the standard input rate). The L-6 cost estimator multiplies each
    by its own rate, so we surface all four.

    Falls back to ``(0, 0, 0, 0)`` on any attribute miss / TypeError so
    a misbehaving test transport doesn't crash the invocation. The
    accumulator treats 0 as "free", which is the right behaviour for
    non-billable fakes.
    """
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0, 0, 0, 0

    def _read(name: str) -> int:
        try:
            return int(getattr(usage, name, 0) or 0)
        except (TypeError, ValueError):
            return 0

    return (
        _read("input_tokens"),
        _read("output_tokens"),
        _read("cache_read_input_tokens"),
        _read("cache_creation_input_tokens"),
    )


__all__ = [
    "AnthropicAgentInvocationAdapter",
    "_stable_dumps",
]
