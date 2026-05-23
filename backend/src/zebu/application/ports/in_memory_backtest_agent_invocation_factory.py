"""In-memory :class:`BacktestAgentInvocationFactory` for tests.

Phase L-3 (Task #219). The backtest-executor unit / integration tests
construct this factory and configure the LIVE branch with whatever
:class:`AgentInvocationPort` test fake they need (typically a
:class:`StaticAgentInvocationPort` returning a scripted decision, or a
:class:`FailingAgentInvocationPort` to exercise the error path).

For ``MOCK`` mode, the factory returns the real
:class:`MockBacktestAgentInvocationPort` so the executor's MOCK path
runs exactly as it will in production.

``NONE`` raises, matching the protocol contract.
"""

from collections.abc import Callable
from datetime import date

from zebu.application.ports.agent_invocation_port import AgentInvocationPort
from zebu.application.ports.in_memory_agent_invocation_port import (
    MockBacktestAgentInvocationPort,
)
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)

# Zero-arg callable returning a fresh :class:`AgentInvocationPort`.
# Tests configure this via the in-memory factory's constructor when
# they exercise the LIVE branch.
type AgentInvocationPortFactory = Callable[[], AgentInvocationPort]


class InMemoryBacktestAgentInvocationFactory:
    """Test fake for :class:`BacktestAgentInvocationFactory`.

    Construction takes a ``live_port_factory`` — a zero-arg callable
    that returns a fresh :class:`AgentInvocationPort` per call — so
    tests can either reuse a single configured port
    (``lambda: my_static``) or spin a fresh one per simulated fire
    (e.g. when the port consumes a queue of results).

    The MOCK branch always uses the real
    :class:`MockBacktestAgentInvocationPort` so the executor's MOCK
    path runs exactly as it will in production.

    For tests driving multiple fires with different decisions, see
    :class:`ScriptedAgentInvocationPort` — pass a closure that returns
    the same scripted port instance on every call so its queue is
    drained across fires:

    ```python
    scripted = ScriptedAgentInvocationPort(results=[buy, sell, hold])
    factory = InMemoryBacktestAgentInvocationFactory(
        live_port_factory=lambda: scripted,
    )
    ```

    Attributes:
        live_calls: Recorded ``(simulated_date, agent_temperature)``
            tuples for each LIVE-mode ``for_simulated_date`` call.
            Tests assert these to verify the executor passed the
            right simulated date through.
        mock_calls: Same shape as :attr:`live_calls`, but for MOCK.
        last_live_port: The most recently returned LIVE-mode port, so
            tests can pull recorded invocations off the port directly.
    """

    def __init__(
        self,
        *,
        live_port_factory: AgentInvocationPortFactory | None = None,
    ) -> None:
        """Initialise the in-memory factory.

        Args:
            live_port_factory: Zero-arg callable returning a fresh
                :class:`AgentInvocationPort` per LIVE-mode call. When
                ``None``, LIVE-mode calls raise — tests that exercise
                only MOCK / NONE branches don't need to supply this.
        """
        self._live_port_factory = live_port_factory
        self._mock_port = MockBacktestAgentInvocationPort()
        self.live_calls: list[tuple[date, float | None]] = []
        self.mock_calls: list[tuple[date, float | None]] = []
        self.last_live_port: AgentInvocationPort | None = None

    def for_simulated_date(
        self,
        *,
        simulated_date: date,
        mode: BacktestAgentInvocationMode,
        agent_temperature: float | None,
    ) -> AgentInvocationPort:
        """Return the configured port for ``mode`` (raises on NONE).

        Args:
            simulated_date: Recorded into :attr:`live_calls` /
                :attr:`mock_calls` so tests can assert the executor
                advanced the simulated clock correctly.
            mode: ``LIVE`` calls :attr:`_live_port_factory`. ``MOCK``
                returns the shared mock port. ``NONE`` raises.
            agent_temperature: Recorded for assertion purposes.

        Returns:
            The :class:`AgentInvocationPort` for this fire.

        Raises:
            ValueError: If ``mode`` is
                :class:`BacktestAgentInvocationMode.NONE`, or if
                ``mode is LIVE`` and no ``live_port_factory`` was
                configured.
        """
        if mode is BacktestAgentInvocationMode.LIVE:
            if self._live_port_factory is None:
                raise ValueError(
                    "InMemoryBacktestAgentInvocationFactory was asked for a "
                    "LIVE port but no live_port_factory was configured. "
                    "Supply one via the constructor when the test exercises "
                    "the LIVE branch."
                )
            self.live_calls.append((simulated_date, agent_temperature))
            port = self._live_port_factory()
            self.last_live_port = port
            return port
        if mode is BacktestAgentInvocationMode.MOCK:
            self.mock_calls.append((simulated_date, agent_temperature))
            return self._mock_port
        raise ValueError(
            "InMemoryBacktestAgentInvocationFactory.for_simulated_date "
            f"called with mode={mode.value}; callers MUST short-circuit "
            "on NONE."
        )


__all__ = [
    "AgentInvocationPortFactory",
    "InMemoryBacktestAgentInvocationFactory",
]
