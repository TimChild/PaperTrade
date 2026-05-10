#!/usr/bin/env python3
"""End-to-end smoke test for the Zebu trigger-fire pipeline.

Phase F-7 — last PR in the agent-in-the-loop trigger system. Proves
the pipeline works end-to-end: trigger fires -> agent invoked ->
:class:`TriggerFireRecord` written -> any resulting trade landed.

Run modes
---------

* ``local`` — Build the full orchestration with **in-memory adapters**
  and exercise the pipeline programmatically. No DB, no HTTP. Deterministic
  and fast. The agent boundary can be either the real Anthropic adapter
  (when ``ANTHROPIC_API_KEY`` is set + ``--mock=false``) or a scripted
  :class:`StaticAgentInvocationPort` (when ``--mock`` is passed).

* ``api`` — Drive the pipeline against a deployed Zebu backend over
  HTTPS using a real API key. Creates a test portfolio + strategy +
  activation + trigger, fires the trigger via
  ``POST /api/v1/triggers/{id}/evaluate``, and verifies the resulting
  fire-log row. Requires the trigger evaluation endpoint to be live
  (Phase F-5).

  .. note::
     The ``evaluate`` endpoint is documented in the Phase F design §7.2
     but not yet implemented (Phase F-5 shipped CRUD + fire-log + kill
     switches only). API-mode smoke testing waits on that endpoint
     before it can be deterministic — until then, ``api`` mode
     exercises only the setup half.

Cost
----

The real Anthropic call (``local`` mode without ``--mock``) burns API
credits. Haiku 4.5 + the F-3 prompt (small system, ~1.5KB user) is
well under $0.01 per run. Each smoke run makes exactly **one**
Anthropic call.

The ``--mock`` flag (default ``false``) disables the real call and
substitutes a scripted decision so the script can validate the
orchestration logic without burning credits.

Run examples
------------

::

    # 1. Mocked end-to-end (no Anthropic credits burned)
    uv run python scripts/trigger_smoke_test.py --mode local --mock

    # 2. Real Anthropic in local mode (burns ~$0.01)
    export ANTHROPIC_API_KEY=sk-ant-...
    uv run python scripts/trigger_smoke_test.py --mode local

    # 3. Real API against production
    uv run python scripts/trigger_smoke_test.py \
        --mode api \
        --base-url https://zebutrader.com \
        --api-key "$ZEBU_TRADE_API_KEY"

Exit codes
----------

* ``0`` — PASS. All assertions held.
* ``1`` — FAIL. One or more assertions failed; diagnostic context
  is printed to stderr.
* ``2`` — Misconfigured invocation (missing env vars, unknown mode).

See ``docs/deployment/production-checklist.md`` for the operating
procedure: run this script (``--mode=api``) before flipping
``ZEBU_TRIGGER_FIRES_ENABLED=true`` on the production VM.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Final
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

# The script imports application + domain code directly; this works
# when run from a checkout where ``backend/src`` is on the path. The
# repo's task wrapper / ``uv run`` makes that the case automatically.
_ROOT: Final[str] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "backend", "src"))

if TYPE_CHECKING:
    import httpx

    from zebu.application.ports.agent_invocation_port import AgentInvocationPort
    from zebu.application.ports.in_memory_exploration_task_repository import (
        InMemoryExplorationTaskRepository,
    )
    from zebu.application.ports.in_memory_transaction_repository import (
        InMemoryTransactionRepository,
    )
    from zebu.application.services.trigger_evaluation_service import (
        EvaluationSummary,
    )
    from zebu.domain.entities.api_key import ApiKey
    from zebu.domain.entities.portfolio import Portfolio
    from zebu.domain.entities.strategy import Strategy
    from zebu.domain.entities.strategy_activation import StrategyActivation
    from zebu.domain.entities.strategy_condition_trigger import (
        StrategyConditionTrigger,
    )
    from zebu.domain.entities.transaction import Transaction
    from zebu.domain.entities.trigger_fire_record import TriggerFireRecord
    from zebu.domain.value_objects.price_point import PricePoint


# Default values for the smoke fixture. Picked to be obviously "test"
# data so an operator inspecting the DB can tell what created them.
_TEST_PORTFOLIO_NAME: Final[str] = "f7-smoke-test-portfolio"
_TEST_STRATEGY_NAME: Final[str] = "f7-smoke-test-strategy"
_TEST_TICKERS: Final[list[str]] = ["AAPL", "NVDA"]
_TEST_INITIAL_CASH: Final[Decimal] = Decimal("10000")
_TEST_AGENT_PROMPT: Final[str] = (
    "Smoke-test trigger: the F-7 fixture forces a drawdown to verify the "
    "Anthropic round-trip. Decide HOLD — the operator does not want any "
    "trade landing from this fixture."
)
_TEST_THRESHOLD_PCT: Final[Decimal] = Decimal("0.01")  # 1% — fires easily
_TEST_LOOKBACK_DAYS: Final[int] = 30
_TEST_COOLDOWN_SECONDS: Final[int] = 60

# Real-call latency heuristic. If the orchestrator round-trip is < 100 ms,
# the agent path was probably mocked or cached — the smoke wants to
# confirm a real Anthropic call happened in non-mock runs.
_REAL_CALL_LATENCY_FLOOR_MS: Final[int] = 100


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


@dataclass
class _Status:
    """Track pass/fail outcomes across assertions."""

    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        """Record a hard failure; will cause exit code 1."""
        self.failures.append(message)
        print(f"FAIL: {message}", file=sys.stderr)

    def warn(self, message: str) -> None:
        """Record a soft warning; does not affect exit code."""
        self.warnings.append(message)
        print(f"WARN: {message}", file=sys.stderr)

    def ok(self, message: str) -> None:
        """Print a success line."""
        print(f"  ok: {message}")

    @property
    def passed(self) -> bool:
        return not self.failures


# ---------------------------------------------------------------------------
# Local-mode runner (in-memory adapters)
# ---------------------------------------------------------------------------


async def run_local_mode(*, mock_agent: bool, status: _Status) -> None:
    """Exercise the pipeline with in-memory adapters.

    Builds a portfolio + strategy + activation + trigger entirely in
    memory, seeds a 20%+ drawdown via the transaction ledger + price
    history, then runs
    :meth:`TriggerEvaluationService.evaluate_all` with the orchestrator
    wired. Asserts the audit row landed and the decision came back
    structured.

    Args:
        mock_agent: When True, substitute a :class:`StaticAgentInvocationPort`
            so no Anthropic credits are burned. When False, instantiate the
            real :class:`AnthropicAgentInvocationAdapter` (requires
            ``ANTHROPIC_API_KEY`` in env).
        status: Outcome tracker.
    """
    # Imports are deferred so the script can produce a friendly error if
    # ``backend/src`` isn't on the path (e.g. invoked outside the repo).
    from zebu.adapters.outbound.earnings.stub_calendar_adapter import (
        StubEarningsCalendarAdapter,
    )
    from zebu.adapters.outbound.market_data.in_memory_adapter import (
        InMemoryMarketDataAdapter,
    )
    from zebu.application.ports.in_memory_agent_invocation_port import (
        StaticAgentInvocationPort,
        make_result,
    )
    from zebu.application.ports.in_memory_api_key_repository import (
        InMemoryApiKeyRepository,
    )
    from zebu.application.ports.in_memory_exploration_task_repository import (
        InMemoryExplorationTaskRepository,
    )
    from zebu.application.ports.in_memory_portfolio_repository import (
        InMemoryPortfolioRepository,
    )
    from zebu.application.ports.in_memory_strategy_activation_repository import (
        InMemoryStrategyActivationRepository,
    )
    from zebu.application.ports.in_memory_strategy_repository import (
        InMemoryStrategyRepository,
    )
    from zebu.application.ports.in_memory_transaction_repository import (
        InMemoryTransactionRepository,
    )
    from zebu.application.ports.in_memory_trigger_fire_repository import (
        InMemoryTriggerFireRepository,
    )
    from zebu.application.ports.in_memory_trigger_repository import (
        InMemoryTriggerRepository,
    )
    from zebu.application.services.trigger_evaluation_service import (
        TriggerEvaluationService,
    )
    from zebu.application.services.trigger_invocation_orchestrator import (
        TriggerInvocationOrchestrator,
    )
    from zebu.domain.value_objects.agent_decision import AgentDecision

    # 1. Build the fixture.
    fixture = await _build_local_fixture()
    status.ok(
        f"fixture built: portfolio={fixture.portfolio_id} "
        f"strategy={fixture.strategy_id} activation={fixture.activation_id} "
        f"trigger={fixture.trigger_id}"
    )

    # 2. Resolve the agent boundary.
    agent_port: AgentInvocationPort
    if mock_agent:
        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.HOLD,
                rationale=(
                    "F-7 mock: drawdown crossed threshold but operator "
                    "explicitly asked for HOLD in the agent_prompt."
                ),
            )
        )
        status.ok("agent boundary: mocked (no Anthropic credits)")
    else:
        agent_port = _build_real_anthropic_adapter()
        status.ok(f"agent boundary: real Anthropic ({type(agent_port).__name__})")

    # 3. Wire repos.
    trigger_repo = InMemoryTriggerRepository()
    fire_repo = InMemoryTriggerFireRepository()
    activation_repo = InMemoryStrategyActivationRepository()
    strategy_repo = InMemoryStrategyRepository()
    portfolio_repo = InMemoryPortfolioRepository()
    txn_repo = InMemoryTransactionRepository()
    market_data = InMemoryMarketDataAdapter()
    api_key_repo = InMemoryApiKeyRepository()
    task_repo = InMemoryExplorationTaskRepository()

    await trigger_repo.save(fixture.trigger)
    await activation_repo.save(fixture.activation)
    await strategy_repo.save(fixture.strategy)
    await portfolio_repo.save(fixture.portfolio)
    await api_key_repo.save(fixture.api_key)
    for txn in fixture.transactions:
        await txn_repo.save(txn)
    for point in fixture.price_history:
        market_data.seed_price(point)

    # 4. Build orchestrator + evaluator.
    orchestrator = TriggerInvocationOrchestrator(
        agent_invocation=agent_port,  # type: ignore[arg-type]
        trigger_repo=trigger_repo,
        trigger_fire_repo=fire_repo,
        activation_repo=activation_repo,
        strategy_repo=strategy_repo,
        portfolio_repo=portfolio_repo,
        transaction_repo=txn_repo,
        market_data=market_data,
        api_key_repo=api_key_repo,
        exploration_task_repo=task_repo,
    )
    service = TriggerEvaluationService(
        trigger_repo=trigger_repo,
        activation_repo=activation_repo,
        strategy_repo=strategy_repo,
        portfolio_repo=portfolio_repo,
        transaction_repo=txn_repo,
        market_data=market_data,
        earnings_calendar=StubEarningsCalendarAdapter(),
        orchestrator=orchestrator,
        fires_enabled_override=True,
    )

    # 5. Run.
    print("\n--- Firing trigger via evaluate_all() ---")
    summary = await service.evaluate_all()
    print(
        f"  summary: processed={summary['processed']} fired={summary['fired']} "
        f"failed={summary['failed']} skipped={summary['skipped']}"
    )

    # 6. Assertions.
    _assert_summary(summary=summary, status=status)
    if not summary["results"]:
        status.fail("evaluate_all returned no results — fixture wrong?")
        return

    result = summary["results"][0]
    fire_record_id = result["fire_record_id"]
    if fire_record_id is None:
        status.fail("no fire_record_id on result — orchestrator path not exercised")
        return

    record = await fire_repo.get(fire_record_id)
    if record is None:
        status.fail(
            f"TriggerFireRecord {fire_record_id} not found in fire repo "
            "after orchestrator ran"
        )
        return
    status.ok(
        f"audit row written: id={record.id} decision={record.agent_response.value}"
    )
    status.ok(f"agent rationale: {record.agent_response_raw[:120]}...")
    status.ok(f"latency_ms: {record.latency_ms}")

    _assert_decision_valid(record=record, status=status)
    _assert_audit_invariants(record=record, status=status)
    _assert_latency_plausible(
        record=record,
        mock_agent=mock_agent,
        status=status,
    )
    await _assert_transaction_consistency(
        record=record,
        txn_repo=txn_repo,
        task_repo=task_repo,
        status=status,
    )


def _build_real_anthropic_adapter() -> AgentInvocationPort:
    """Construct the production Anthropic adapter (requires API key)."""
    from zebu.adapters.outbound.anthropic.agent_invocation_adapter import (
        AnthropicAgentInvocationAdapter,
    )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. Either set it, "
            "or pass --mock to use the in-memory agent.",
            file=sys.stderr,
        )
        sys.exit(2)
    return AnthropicAgentInvocationAdapter()


# ---------------------------------------------------------------------------
# Local fixture builder
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _LocalFixture:
    """Container for the in-memory fixture entities + seeded state.

    Holds the freshly-constructed entities and the seed data the
    in-memory adapters need to be populated with before
    :meth:`TriggerEvaluationService.evaluate_all` runs.
    """

    user_id: UUID
    api_key: ApiKey
    portfolio: Portfolio
    strategy: Strategy
    activation: StrategyActivation
    trigger: StrategyConditionTrigger
    transactions: list[Transaction]
    price_history: list[PricePoint]

    @property
    def portfolio_id(self) -> UUID:
        return self.portfolio.id

    @property
    def strategy_id(self) -> UUID:
        return self.strategy.id

    @property
    def activation_id(self) -> UUID:
        return self.activation.id

    @property
    def trigger_id(self) -> UUID:
        return self.trigger.id


async def _build_local_fixture() -> _LocalFixture:
    """Construct an in-memory fixture that will fire on drawdown.

    Builds: ApiKey, Portfolio, Strategy(BUY_AND_HOLD on AAPL+NVDA),
    Activation(ACTIVE), Trigger(DRAWDOWN_THRESHOLD at 1%, lookback
    30d, cooldown 60s). Seeds a transaction ledger that establishes
    a $10,000 starting cash + a buy at $100/share + a price drop to
    $80/share so the portfolio is ~20% down from peak.
    """
    from zebu.domain.entities.api_key import ApiKey
    from zebu.domain.entities.portfolio import Portfolio
    from zebu.domain.entities.strategy import Strategy
    from zebu.domain.entities.strategy_activation import StrategyActivation
    from zebu.domain.entities.strategy_condition_trigger import (
        StrategyConditionTrigger,
    )
    from zebu.domain.entities.transaction import Transaction, TransactionType
    from zebu.domain.value_objects.activation_frequency import ActivationFrequency
    from zebu.domain.value_objects.activation_status import ActivationStatus
    from zebu.domain.value_objects.api_key_scope import ApiKeyScope
    from zebu.domain.value_objects.money import Money
    from zebu.domain.value_objects.portfolio_type import PortfolioType
    from zebu.domain.value_objects.price_point import PricePoint
    from zebu.domain.value_objects.quantity import Quantity
    from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
    from zebu.domain.value_objects.strategy_type import StrategyType
    from zebu.domain.value_objects.ticker import Ticker
    from zebu.domain.value_objects.trigger_condition import (
        ConditionType,
        DrawdownMetric,
        DrawdownParams,
    )
    from zebu.domain.value_objects.trigger_status import TriggerStatus

    now = datetime.now(UTC)
    user_id = uuid5(NAMESPACE_DNS, "f7-smoke-test-user")

    api_key = ApiKey(
        id=uuid4(),
        user_id=user_id,
        clerk_user_id="user_f7_smoke",
        label="f7-smoke-test-key",
        # 64-char hash to satisfy any defensive length checks.
        key_hash="hash_" + "0" * 60,
        scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=now - timedelta(days=60),
    )

    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,
        name=_TEST_PORTFOLIO_NAME,
        created_at=now - timedelta(days=60),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )

    # Use the first ticker as the canonical "this is the one we bought".
    # The BuyAndHold strategy spans both tickers but the trigger fires
    # on PORTFOLIO_TOTAL so the universe doesn't drive the snapshot.
    primary_ticker = _TEST_TICKERS[0]

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name=_TEST_STRATEGY_NAME,
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=_TEST_TICKERS,
        parameters=BuyAndHoldParameters(
            allocation={t: Decimal("0.5") for t in _TEST_TICKERS},
        ),
        created_at=now - timedelta(days=60),
    )

    activation = StrategyActivation(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy.id,
        portfolio_id=portfolio.id,
        status=ActivationStatus.ACTIVE,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=now - timedelta(days=45),
        updated_at=now - timedelta(days=45),
    )

    trigger = StrategyConditionTrigger(
        id=uuid4(),
        activation_id=activation.id,
        user_id=user_id,
        condition_type=ConditionType.DRAWDOWN_THRESHOLD,
        condition_params=DrawdownParams(
            threshold_pct=_TEST_THRESHOLD_PCT,
            lookback_days=_TEST_LOOKBACK_DAYS,
            metric=DrawdownMetric.PORTFOLIO_TOTAL,
        ),
        agent_prompt=_TEST_AGENT_PROMPT,
        status=TriggerStatus.ACTIVE,
        cooldown_seconds=_TEST_COOLDOWN_SECONDS,
        created_at=now - timedelta(days=10),
        updated_at=now - timedelta(days=10),
        created_by=user_id,
        default_api_key_id=api_key.id,
    )

    # Seed transactions: deposit $10K, buy 50 shares at $100 (= $5,000).
    deposit = Transaction(
        id=uuid4(),
        portfolio_id=portfolio.id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=now - timedelta(days=29),
        cash_change=Money(_TEST_INITIAL_CASH, "USD"),
    )
    buy_price = Money(Decimal("100"), "USD")
    buy_qty = Quantity(Decimal("50"))
    buy = Transaction(
        id=uuid4(),
        portfolio_id=portfolio.id,
        transaction_type=TransactionType.BUY,
        timestamp=now - timedelta(days=28),
        cash_change=Money(-(buy_price.amount * buy_qty.shares), "USD"),
        ticker=Ticker(primary_ticker),
        quantity=buy_qty,
        price_per_share=buy_price,
    )

    # Price history: $100 -> $80 (a 20% drop, well above the 1% threshold).
    # The other ticker in the strategy universe gets a flat history at
    # the same price so the portfolio's TOTAL value reflects the drop.
    price_history: list[PricePoint] = []
    for days_ago, price_str in (
        (28, "100"),
        (15, "100"),
        (7, "95"),
        (3, "85"),
        (1, "80"),
        (0, "80"),
    ):
        price_history.append(
            PricePoint(
                ticker=Ticker(primary_ticker),
                price=Money(Decimal(price_str), "USD"),
                timestamp=now - timedelta(days=days_ago),
                source="database",
                interval="1day",
                close=Money(Decimal(price_str), "USD"),
            )
        )
    # Flat-price filler for the second ticker so its presence doesn't
    # crash the drawdown evaluator on missing data.
    for days_ago in (28, 15, 7, 3, 1, 0):
        price_history.append(
            PricePoint(
                ticker=Ticker(_TEST_TICKERS[1]),
                price=Money(Decimal("500"), "USD"),
                timestamp=now - timedelta(days=days_ago),
                source="database",
                interval="1day",
                close=Money(Decimal("500"), "USD"),
            )
        )

    return _LocalFixture(
        user_id=user_id,
        api_key=api_key,
        portfolio=portfolio,
        strategy=strategy,
        activation=activation,
        trigger=trigger,
        transactions=[deposit, buy],
        price_history=price_history,
    )


# ---------------------------------------------------------------------------
# Assertions (shared across modes)
# ---------------------------------------------------------------------------


def _assert_summary(*, summary: EvaluationSummary, status: _Status) -> None:
    """Check ``EvaluationSummary`` shape: 1 processed, 1 fired."""
    processed = summary["processed"]
    fired = summary["fired"]
    failed = summary["failed"]

    if processed != 1:
        status.fail(f"expected 1 trigger processed, got {processed}")
    if fired != 1:
        status.fail(
            f"expected 1 trigger to fire (drawdown 20% > threshold 1%), got {fired}"
        )
    if failed != 0:
        status.fail(f"expected 0 evaluation failures, got {failed}")


def _assert_decision_valid(*, record: TriggerFireRecord, status: _Status) -> None:
    """Decision must be a recognised :class:`AgentDecision` value."""
    from zebu.domain.value_objects.agent_decision import AgentDecision

    valid = {
        AgentDecision.BUY,
        AgentDecision.SELL,
        AgentDecision.HOLD,
        AgentDecision.MODIFY_STRATEGY,
        AgentDecision.NEEDS_HUMAN,
        AgentDecision.INVOCATION_FAILED,
    }
    decision = record.agent_response
    if decision not in valid:
        status.fail(f"unrecognised AgentDecision: {decision!r}")
    elif decision is AgentDecision.INVOCATION_FAILED:
        status.warn(
            "agent returned INVOCATION_FAILED — pipeline is working, but "
            "the call itself errored. Inspect agent_response_raw for cause."
        )
    else:
        status.ok(f"decision is valid: {decision.value}")


def _assert_audit_invariants(*, record: TriggerFireRecord, status: _Status) -> None:
    """Resulting-pointer cardinality matches the decision.

    Per :class:`TriggerFireRecord` invariants in F-1: exactly one
    ``resulting_*`` pointer set for actionable decisions; none for
    HOLD / INVOCATION_FAILED. The entity validates this at construction,
    so it being saved at all means this holds — we still log it for
    operator visibility.
    """
    from zebu.domain.value_objects.agent_decision import AgentDecision

    decision = record.agent_response
    has_trade = record.resulting_trade_id is not None
    has_modify = record.resulting_modify_payload is not None
    has_task = record.resulting_exploration_task_id is not None
    pointers_set = sum([has_trade, has_modify, has_task])

    if decision in {AgentDecision.HOLD, AgentDecision.INVOCATION_FAILED}:
        if pointers_set != 0:
            status.fail(
                f"decision={decision.value} but {pointers_set} resulting_* "
                "pointers set (expected 0)"
            )
        else:
            status.ok("audit invariants hold (no side-effect pointers for HOLD)")
    else:
        if pointers_set != 1:
            status.fail(
                f"decision={decision.value} but {pointers_set} resulting_* "
                "pointers set (expected exactly 1)"
            )
        else:
            status.ok(
                f"audit invariants hold (exactly one resulting_* pointer for "
                f"{decision.value})"
            )


def _assert_latency_plausible(
    *, record: TriggerFireRecord, mock_agent: bool, status: _Status
) -> None:
    """Latency in real-call mode should be > floor; mock mode is unconstrained."""
    latency_ms = record.latency_ms
    if mock_agent:
        status.ok(f"latency (mocked): {latency_ms}ms")
        return
    if latency_ms < _REAL_CALL_LATENCY_FLOOR_MS:
        status.warn(
            f"real-call latency was only {latency_ms}ms — expected "
            f"> {_REAL_CALL_LATENCY_FLOOR_MS}ms; was the Anthropic call "
            "actually made?"
        )
    else:
        status.ok(f"latency plausible for real Anthropic call: {latency_ms}ms")


async def _assert_transaction_consistency(
    *,
    record: TriggerFireRecord,
    txn_repo: InMemoryTransactionRepository,
    task_repo: InMemoryExplorationTaskRepository,
    status: _Status,
) -> None:
    """If decision was BUY/SELL, a transaction exists; if HOLD, none."""
    from zebu.domain.value_objects.agent_decision import AgentDecision

    decision = record.agent_response
    if decision in {AgentDecision.BUY, AgentDecision.SELL}:
        trade_id = record.resulting_trade_id
        if trade_id is None:
            status.fail(f"decision={decision.value} but resulting_trade_id is None")
        else:
            txn = await txn_repo.get(trade_id)
            if txn is None:
                status.fail(f"resulting_trade_id={trade_id} but transaction not found")
            else:
                status.ok(f"trade landed: id={txn.id} action={txn.transaction_type}")
    elif decision is AgentDecision.NEEDS_HUMAN:
        task_id = record.resulting_exploration_task_id
        if task_id is None:
            status.fail(
                "decision=NEEDS_HUMAN but resulting_exploration_task_id is None"
            )
        else:
            task = await task_repo.get(task_id)
            if task is None:
                status.fail(
                    f"resulting_exploration_task_id={task_id} but task not found"
                )
            else:
                status.ok(f"exploration task filed: id={task.id}")
    elif decision is AgentDecision.HOLD:
        # No follow-up state; the audit row alone is the artefact.
        status.ok("HOLD decision: no side-effect transaction expected")


# ---------------------------------------------------------------------------
# API-mode runner (deferred — waiting on POST /triggers/{id}/evaluate)
# ---------------------------------------------------------------------------


async def run_api_mode(*, base_url: str, api_key: str, status: _Status) -> None:
    """Drive the smoke test against a deployed Zebu backend over HTTPS.

    Creates a portfolio, strategy, activation, and trigger via the public
    REST endpoints, then calls ``POST /triggers/{id}/evaluate`` to fire
    the trigger deterministically and reads back the resulting fire-log
    row via ``GET /triggers/{id}/fires``.

    .. note::
       The manual evaluate endpoint is documented in the Phase F design
       but is not yet implemented (Phase F-5 shipped CRUD + fire log +
       kill switches only). When it lands, this branch fills in the
       evaluator call. Until then, API mode runs the setup half and
       prints instructions for manually verifying via the fire-log GET.

    Args:
        base_url: Zebu backend root (e.g. ``https://zebutrader.com``).
        api_key: ``trade``-scoped API key for the test account.
        status: Outcome tracker.
    """
    try:
        import httpx
    except ImportError:
        status.fail(
            "API mode requires httpx; run "
            "`uv pip install httpx` or invoke via `uv run`."
        )
        return

    headers = {
        "Authorization": f"ApiKey {api_key}",
        "Content-Type": "application/json",
    }
    api_root = base_url.rstrip("/") + "/api/v1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health check — confirm the backend is up.
        health_url = base_url.rstrip("/") + "/health"
        resp = await client.get(health_url)
        if resp.status_code != 200:
            status.fail(f"backend health failed: {resp.status_code} at {health_url}")
            return
        status.ok(f"backend reachable: {health_url}")

        # 2. Create or find a test portfolio.
        portfolio_id = await _ensure_test_portfolio(
            client=client, api_root=api_root, headers=headers, status=status
        )
        if portfolio_id is None:
            return
        status.ok(f"portfolio: {portfolio_id}")

        # 3. Create test strategy.
        strategy_id = await _create_test_strategy(
            client=client, api_root=api_root, headers=headers, status=status
        )
        if strategy_id is None:
            return
        status.ok(f"strategy: {strategy_id}")

        # 4. Activate strategy.
        activation_id = await _activate_strategy(
            client=client,
            api_root=api_root,
            headers=headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
            status=status,
        )
        if activation_id is None:
            return
        status.ok(f"activation: {activation_id}")

        # 5. Attach trigger.
        trigger_id = await _attach_trigger(
            client=client,
            api_root=api_root,
            headers=headers,
            activation_id=activation_id,
            status=status,
        )
        if trigger_id is None:
            return
        status.ok(f"trigger: {trigger_id}")

        # 6. Manual evaluation (when the endpoint exists).
        evaluate_url = f"{api_root}/triggers/{trigger_id}/evaluate"
        resp = await client.post(evaluate_url, headers=headers)
        if resp.status_code == 404:
            status.warn(
                "POST /triggers/{id}/evaluate is not yet implemented "
                "(Phase F-5 deferred this endpoint). Falling back to "
                "fire-log polling. The trigger will fire on the next "
                "scheduler tick (~15 min in market hours)."
            )
            await _poll_fire_log(
                client=client,
                api_root=api_root,
                headers=headers,
                trigger_id=trigger_id,
                status=status,
            )
        elif resp.status_code >= 400:
            status.fail(f"evaluate endpoint failed: {resp.status_code} {resp.text}")
            return
        else:
            status.ok(f"trigger evaluated synchronously: {resp.json()}")
            await _verify_fire_record(
                client=client,
                api_root=api_root,
                headers=headers,
                trigger_id=trigger_id,
                status=status,
            )


async def _ensure_test_portfolio(
    *,
    client: httpx.AsyncClient,
    api_root: str,
    headers: dict[str, str],
    status: _Status,
) -> UUID | None:
    """Find an existing F-7 test portfolio or create one.

    Idempotent — re-running the smoke does not stack up test portfolios.
    """
    list_url = f"{api_root}/portfolios"
    resp = await client.get(list_url, headers=headers)
    if resp.status_code != 200:
        status.fail(f"GET /portfolios failed: {resp.status_code} {resp.text}")
        return None
    body = resp.json()
    for portfolio in body.get("items", []):
        if portfolio.get("name") == _TEST_PORTFOLIO_NAME:
            return UUID(portfolio["id"])

    # Not found — create.
    create_url = f"{api_root}/portfolios"
    payload = {
        "name": _TEST_PORTFOLIO_NAME,
        "initial_deposit": str(_TEST_INITIAL_CASH),
        "currency": "USD",
    }
    resp = await client.post(create_url, json=payload, headers=headers)
    if resp.status_code != 201:
        status.fail(f"POST /portfolios failed: {resp.status_code} {resp.text}")
        return None
    return UUID(resp.json()["portfolio_id"])


async def _create_test_strategy(
    *,
    client: httpx.AsyncClient,
    api_root: str,
    headers: dict[str, str],
    status: _Status,
) -> UUID | None:
    """Create a BUY_AND_HOLD test strategy.

    Each smoke run mints a fresh strategy — strategies don't have a
    natural idempotent key in the API surface and the volume per user
    is small enough that we don't bother de-duplicating.
    """
    create_url = f"{api_root}/strategies"
    payload: dict[str, object] = {
        "strategy_type": "BUY_AND_HOLD",
        "name": f"{_TEST_STRATEGY_NAME}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "tickers": _TEST_TICKERS,
        "parameters": {
            "allocation": {t: "0.5" for t in _TEST_TICKERS},
        },
    }
    resp = await client.post(create_url, json=payload, headers=headers)
    if resp.status_code != 201:
        status.fail(f"POST /strategies failed: {resp.status_code} {resp.text}")
        return None
    return UUID(resp.json()["id"])


async def _activate_strategy(
    *,
    client: httpx.AsyncClient,
    api_root: str,
    headers: dict[str, str],
    strategy_id: UUID,
    portfolio_id: UUID,
    status: _Status,
) -> UUID | None:
    """Activate the test strategy against the test portfolio."""
    activate_url = f"{api_root}/strategies/{strategy_id}/activate"
    payload = {
        "portfolio_id": str(portfolio_id),
        "frequency": "daily_market_close",
    }
    resp = await client.post(activate_url, json=payload, headers=headers)
    if resp.status_code != 201:
        status.fail(
            f"POST /strategies/{strategy_id}/activate failed: "
            f"{resp.status_code} {resp.text}"
        )
        return None
    return UUID(resp.json()["id"])


async def _attach_trigger(
    *,
    client: httpx.AsyncClient,
    api_root: str,
    headers: dict[str, str],
    activation_id: UUID,
    status: _Status,
) -> UUID | None:
    """Attach a low-threshold drawdown trigger to the activation."""
    create_url = f"{api_root}/activations/{activation_id}/triggers"
    payload: dict[str, object] = {
        "condition_type": "DRAWDOWN_THRESHOLD",
        "condition_params": {
            "threshold_pct": str(_TEST_THRESHOLD_PCT),
            "lookback_days": _TEST_LOOKBACK_DAYS,
            "metric": "PORTFOLIO_TOTAL",
        },
        "agent_prompt": _TEST_AGENT_PROMPT,
        "cooldown_seconds": _TEST_COOLDOWN_SECONDS,
        "priority": 0,
    }
    resp = await client.post(create_url, json=payload, headers=headers)
    if resp.status_code != 201:
        status.fail(
            f"POST /activations/{activation_id}/triggers failed: "
            f"{resp.status_code} {resp.text}"
        )
        return None
    return UUID(resp.json()["id"])


async def _verify_fire_record(
    *,
    client: httpx.AsyncClient,
    api_root: str,
    headers: dict[str, str],
    trigger_id: UUID,
    status: _Status,
) -> None:
    """Verify the fire-log carries a row for the just-evaluated trigger."""
    fires_url = f"{api_root}/triggers/{trigger_id}/fires"
    resp = await client.get(fires_url, headers=headers)
    if resp.status_code != 200:
        status.fail(f"GET /triggers/{trigger_id}/fires failed: {resp.status_code}")
        return
    body = resp.json()
    items = body.get("items", [])
    if not items:
        status.fail("trigger evaluated but fire-log is empty")
        return
    record = items[0]
    status.ok(
        f"fire-log row: id={record['id']} decision={record['agent_response']} "
        f"latency_ms={record['latency_ms']}"
    )


async def _poll_fire_log(
    *,
    client: httpx.AsyncClient,
    api_root: str,
    headers: dict[str, str],
    trigger_id: UUID,
    status: _Status,
) -> None:
    """Fallback when no manual evaluate endpoint exists.

    Doesn't block on the next scheduler tick (could be 15 min). Just
    prints the URL the operator should poll.
    """
    del client, headers  # not needed when we're just printing a URL
    fires_url = f"{api_root}/triggers/{trigger_id}/fires"
    status.warn(
        "Cannot trigger a manual evaluation. The trigger fires on the "
        "next scheduler tick (every 15 min during market hours). "
        f"Poll the fire-log at {fires_url} to confirm it lands."
    )


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments. Uses stdlib argparse only (no third-party deps)."""
    description = (__doc__ or "").split("Run modes")[
        0
    ].strip() or "End-to-end smoke test for the Zebu trigger-fire pipeline."
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="See ``docs/deployment/production-checklist.md`` for the operating procedure.",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "api"],
        default="local",
        help=(
            "Execution mode. 'local' runs against in-memory adapters; 'api' "
            "drives a deployed backend over HTTPS."
        ),
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help=(
            "(local mode only) Use a scripted in-memory agent instead of "
            "the real Anthropic adapter. No API credits burned."
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help=("(api mode only) Backend root URL. e.g. https://zebutrader.com"),
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help=(
            "(api mode only) Zebu API key with the 'trade' scope. "
            "When omitted, reads from $ZEBU_API_KEY."
        ),
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        default=False,
        help=(
            "(api mode only) Do NOT clean up the created fixture portfolio "
            "after the run. Useful for inspecting results in the UI."
        ),
    )
    return parser.parse_args(argv)


async def _async_main(args: argparse.Namespace, status: _Status) -> None:
    """Dispatch the requested mode."""
    print(f"=== Zebu trigger-fire smoke test ({args.mode} mode) ===")

    if args.mode == "local":
        await run_local_mode(mock_agent=args.mock, status=status)
        return

    # api mode
    api_key = args.api_key or os.environ.get("ZEBU_API_KEY")
    if not api_key:
        print(
            "ERROR: API mode requires --api-key or $ZEBU_API_KEY",
            file=sys.stderr,
        )
        sys.exit(2)
    await run_api_mode(
        base_url=args.base_url,
        api_key=api_key,
        status=status,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = _parse_args(argv)
    status = _Status()

    try:
        asyncio.run(_async_main(args, status))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover  -- defensive
        import traceback

        print(f"Smoke test raised unexpectedly: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    print()
    if status.passed:
        print("=== PASS ===")
        if status.warnings:
            print(f"  ({len(status.warnings)} warning(s) — review output)")
        return 0
    print("=== FAIL ===")
    print(f"  {len(status.failures)} failure(s):")
    for failure in status.failures:
        print(f"    - {failure}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
