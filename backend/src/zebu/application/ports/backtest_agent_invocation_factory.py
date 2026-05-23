"""BacktestAgentInvocationFactory port — per-simulated-day agent port builder.

Phase L-3 (Task #219). A tiny factory the :class:`BacktestExecutor`
calls to construct the :class:`AgentInvocationPort` for a single
simulated trigger fire. Keeps the executor (application-layer)
mode-agnostic: it asks the factory for "the port for this simulated
date" and the factory decides whether that's the L-2 backtest-safe
wrapper (LIVE), the deterministic mock (MOCK), or a hard error (NONE).

Implementations:

* :class:`AnthropicBacktestAgentInvocationFactory`
  (``adapters/outbound/anthropic/backtest_agent_invocation_factory.py``)
  — production wiring. Builds a fresh :class:`BacktestAgentInvocationAdapter`
  per simulated date on LIVE, returns a stateless
  :class:`MockBacktestAgentInvocationPort` on MOCK, raises on NONE.
* :class:`InMemoryBacktestAgentInvocationFactory`
  (``application/ports/in_memory_backtest_agent_invocation_factory.py``)
  — test fake. Returns a caller-supplied port for LIVE, the real mock
  port for MOCK, raises on NONE.

The factory boundary is what lets the executor stay agnostic of the
production Anthropic SDK construction details (env var reads, model
config, downstream balance-handler / exploration-task wiring).
"""

from datetime import date
from typing import Protocol

from zebu.application.ports.agent_invocation_port import AgentInvocationPort
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)


class BacktestAgentInvocationFactory(Protocol):
    """Per-simulated-day :class:`AgentInvocationPort` builder.

    Implementations construct (or return) the right port instance for
    one simulated trigger fire. The executor calls this once per fire,
    so production implementations MAY return a fresh instance each
    call (the L-2 wrapper binds ``simulated_date`` at construction
    time and is short-lived), while MOCK-mode implementations MAY
    return a singleton (the mock port is stateless).
    """

    def for_simulated_date(
        self,
        *,
        simulated_date: date,
        mode: BacktestAgentInvocationMode,
        agent_temperature: float | None,
    ) -> AgentInvocationPort:
        """Build (or return) the :class:`AgentInvocationPort` for one fire day.

        Args:
            simulated_date: The in-simulation calendar day for this
                fire. Bound at construction time on LIVE so the
                L-2 wrapper can enforce the simulated-date cap.
            mode: The agent invocation mode for the parent backtest
                run. ``LIVE`` / ``MOCK`` are accepted; ``NONE`` MUST
                raise (callers should skip the entire L-3 path when
                ``mode == NONE`` rather than asking the factory).
            agent_temperature: Optional sampling-temperature override.
                ``None`` defers to the implementation's default (L-2
                defaults to 0.0; the MOCK port ignores temperature).

        Returns:
            An :class:`AgentInvocationPort` ready to call ``invoke``
            on. Caller is responsible for the call and for handling
            any :class:`AgentInvocationError` (including its
            :class:`BacktestSafetyViolationError` subclass).

        Raises:
            ValueError: If ``mode`` is :class:`BacktestAgentInvocationMode.NONE`.
        """
        ...


__all__ = ["BacktestAgentInvocationFactory"]
