"""Anthropic outbound adapter package — Phase F-3 + Phase L-2.

Provides:

* :class:`AnthropicAgentInvocationAdapter` — the production
  implementation of :class:`AgentInvocationPort` that calls the
  Anthropic Messages API with tool-use coercion, prompt caching, and
  bounded retries. Now supports a multi-turn tool-use loop when a
  :data:`ToolDispatchCallback` is provided (L-2 cross-cutting change).
* :class:`BacktestAgentInvocationAdapter` — the L-2 backtest-safe
  wrapper that exposes only the :class:`BacktestSafeTool` whitelist
  and enforces the ``simulated_date`` cap on every tool call.
"""

from zebu.adapters.outbound.anthropic.agent_invocation_adapter import (
    AnthropicAgentInvocationAdapter,
)
from zebu.adapters.outbound.anthropic.backtest_agent_invocation_adapter import (
    BacktestAgentInvocationAdapter,
)

__all__ = [
    "AnthropicAgentInvocationAdapter",
    "BacktestAgentInvocationAdapter",
]
