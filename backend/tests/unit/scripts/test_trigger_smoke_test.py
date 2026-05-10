"""Unit tests for ``scripts/trigger_smoke_test.py`` (Phase F-7).

The script is the operator-facing smoke harness for the trigger-fire
pipeline. These tests cover the parts that don't need a real Anthropic
key:

* Fixture builder produces self-consistent entities (idempotent state,
  correct invariants, drawdown is ~20%).
* The assertion helpers correctly classify pass / fail cases against
  hand-crafted ``TriggerFireRecord`` instances.
* End-to-end mock run through ``run_local_mode(mock_agent=True)``
  asserts the orchestration logic without burning API credits — this
  is the test that proves the script's main happy path works.

These tests do **not** exercise the real Anthropic adapter; that is
deferred to the operator-run smoke (per Phase F-7 design: "Don't run
it in this PR").
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from zebu.domain.entities.trigger_fire_record import TriggerFireRecord
from zebu.domain.value_objects.agent_decision import AgentDecision

# ---------------------------------------------------------------------------
# Script module loader
# ---------------------------------------------------------------------------

# The smoke-test script lives outside the standard ``backend/src`` import
# tree, so we load it directly by path. This keeps the script self-
# contained (it's not part of the installed ``zebu`` package) while
# letting the tests import its helpers.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "trigger_smoke_test.py"


def _load_script_module() -> object:
    """Load ``scripts/trigger_smoke_test.py`` as a module for inspection."""
    spec = importlib.util.spec_from_file_location("trigger_smoke_test", _SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["trigger_smoke_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def smoke_module() -> object:
    """Module-scoped fixture that loads the smoke-test script once."""
    return _load_script_module()


# ---------------------------------------------------------------------------
# Helpers — build TriggerFireRecord instances for assertion-helper tests
# ---------------------------------------------------------------------------


def _make_hold_record() -> TriggerFireRecord:
    """A HOLD audit row — no resulting_* pointers set."""
    return TriggerFireRecord(
        id=uuid4(),
        trigger_id=uuid4(),
        activation_id=uuid4(),
        fired_at=datetime.now(UTC) - timedelta(seconds=1),
        condition_evaluation_data={"schema_version": 1, "drawdown_pct": "20"},
        agent_response=AgentDecision.HOLD,
        agent_response_raw="Holding position",
        latency_ms=350,
        api_key_id_used=uuid4(),
    )


def _make_buy_record() -> TriggerFireRecord:
    """A BUY audit row — resulting_trade_id required."""
    return TriggerFireRecord(
        id=uuid4(),
        trigger_id=uuid4(),
        activation_id=uuid4(),
        fired_at=datetime.now(UTC) - timedelta(seconds=1),
        condition_evaluation_data={"schema_version": 1, "drawdown_pct": "20"},
        agent_response=AgentDecision.BUY,
        agent_response_raw="Buying the dip",
        latency_ms=420,
        api_key_id_used=uuid4(),
        resulting_trade_id=uuid4(),
    )


def _make_failed_record() -> TriggerFireRecord:
    """INVOCATION_FAILED audit row — all resulting_* must be None."""
    return TriggerFireRecord(
        id=uuid4(),
        trigger_id=uuid4(),
        activation_id=uuid4(),
        fired_at=datetime.now(UTC) - timedelta(seconds=1),
        condition_evaluation_data={"schema_version": 1, "drawdown_pct": "20"},
        agent_response=AgentDecision.INVOCATION_FAILED,
        agent_response_raw="Anthropic rate limit",
        latency_ms=120,
        api_key_id_used=uuid4(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFixtureBuilder:
    """`_build_local_fixture` produces a self-consistent fixture."""

    async def test_fixture_is_constructable(self, smoke_module: object) -> None:
        """The fixture builder runs without raising and returns all entities."""
        fixture = await smoke_module._build_local_fixture()  # type: ignore[attr-defined]

        # All seven slots present.
        assert fixture.api_key is not None
        assert fixture.portfolio is not None
        assert fixture.strategy is not None
        assert fixture.activation is not None
        assert fixture.trigger is not None
        assert len(fixture.transactions) == 2  # deposit + buy
        assert len(fixture.price_history) >= 6  # at least one ticker's history

    async def test_fixture_owner_id_consistent(self, smoke_module: object) -> None:
        """The same user_id flows through every owned entity."""
        fixture = await smoke_module._build_local_fixture()  # type: ignore[attr-defined]
        assert fixture.api_key.user_id == fixture.user_id
        assert fixture.portfolio.user_id == fixture.user_id
        assert fixture.strategy.user_id == fixture.user_id
        assert fixture.activation.user_id == fixture.user_id
        assert fixture.trigger.user_id == fixture.user_id

    async def test_fixture_activation_links_strategy_and_portfolio(
        self, smoke_module: object
    ) -> None:
        """The activation joins the strategy and portfolio."""
        fixture = await smoke_module._build_local_fixture()  # type: ignore[attr-defined]
        assert fixture.activation.strategy_id == fixture.strategy.id
        assert fixture.activation.portfolio_id == fixture.portfolio.id

    async def test_fixture_trigger_links_activation_and_api_key(
        self, smoke_module: object
    ) -> None:
        """Trigger points at the activation + default API key."""
        fixture = await smoke_module._build_local_fixture()  # type: ignore[attr-defined]
        assert fixture.trigger.activation_id == fixture.activation.id
        assert fixture.trigger.default_api_key_id == fixture.api_key.id

    async def test_fixture_is_idempotent_within_a_run(
        self, smoke_module: object
    ) -> None:
        """Two consecutive builds use independent UUIDs (no caching).

        The smoke is meant to be re-runnable; the in-memory fixture
        shouldn't hold persistent state across calls. Two builds in
        the same Python process should produce different IDs.
        """
        first = await smoke_module._build_local_fixture()  # type: ignore[attr-defined]
        second = await smoke_module._build_local_fixture()  # type: ignore[attr-defined]
        assert first.portfolio.id != second.portfolio.id
        # ... but the *user_id* (derived from uuid5 over a constant
        # namespace) IS stable, so a repeat smoke against the same DB
        # finds the same user.
        assert first.user_id == second.user_id

    async def test_fixture_drawdown_setup_will_fire_trigger(
        self, smoke_module: object
    ) -> None:
        """The seeded ledger + price history yield a drawdown above the 1% threshold.

        Crude check: the trigger is configured with
        ``threshold_pct=0.01`` and the seed has the primary ticker
        going from $100 -> $80 (20% drop) so the trigger MUST fire.
        """
        fixture = await smoke_module._build_local_fixture()  # type: ignore[attr-defined]
        # 1% threshold
        assert fixture.trigger.condition_params.threshold_pct == Decimal("0.01")
        # Last price for the primary ticker is $80, peak was $100 — drop = 20%
        primary_history = [
            p for p in fixture.price_history if p.ticker.symbol == "AAPL"
        ]
        prices = [p.price.amount for p in primary_history]
        assert max(prices) == Decimal("100")
        assert min(prices) == Decimal("80")


class TestAssertionHelpers:
    """The pass/fail helpers correctly classify hand-built audit rows."""

    def test_decision_valid_passes_for_known_decision(
        self, smoke_module: object
    ) -> None:
        """A HOLD decision is recognised as valid."""
        record = _make_hold_record()
        status = smoke_module._Status()  # type: ignore[attr-defined]
        smoke_module._assert_decision_valid(record=record, status=status)  # type: ignore[attr-defined]
        assert status.passed
        assert not status.failures

    def test_decision_warns_on_invocation_failed(self, smoke_module: object) -> None:
        """INVOCATION_FAILED is a soft warning, not a hard failure."""
        record = _make_failed_record()
        status = smoke_module._Status()  # type: ignore[attr-defined]
        smoke_module._assert_decision_valid(record=record, status=status)  # type: ignore[attr-defined]
        # Pipeline worked even if Anthropic failed — pass with warning.
        assert status.passed
        assert len(status.warnings) == 1

    def test_audit_invariants_pass_for_hold(self, smoke_module: object) -> None:
        """HOLD with no resulting_* pointers passes the invariant check."""
        record = _make_hold_record()
        status = smoke_module._Status()  # type: ignore[attr-defined]
        smoke_module._assert_audit_invariants(record=record, status=status)  # type: ignore[attr-defined]
        assert status.passed

    def test_audit_invariants_pass_for_buy(self, smoke_module: object) -> None:
        """BUY with resulting_trade_id set passes the invariant check."""
        record = _make_buy_record()
        status = smoke_module._Status()  # type: ignore[attr-defined]
        smoke_module._assert_audit_invariants(record=record, status=status)  # type: ignore[attr-defined]
        assert status.passed

    def test_latency_plausible_passes_for_real_call(self, smoke_module: object) -> None:
        """A real-call latency > 100ms passes the plausibility check."""
        record = _make_hold_record()  # latency_ms=350
        status = smoke_module._Status()  # type: ignore[attr-defined]
        smoke_module._assert_latency_plausible(  # type: ignore[attr-defined]
            record=record, mock_agent=False, status=status
        )
        assert status.passed
        assert not status.warnings

    def test_latency_plausible_warns_for_too_fast(self, smoke_module: object) -> None:
        """A real-call latency < 100ms warns that the call was suspicious."""
        # Build a record with low latency manually.
        record = TriggerFireRecord(
            id=uuid4(),
            trigger_id=uuid4(),
            activation_id=uuid4(),
            fired_at=datetime.now(UTC) - timedelta(seconds=1),
            condition_evaluation_data={"schema_version": 1},
            agent_response=AgentDecision.HOLD,
            agent_response_raw="Test",
            latency_ms=10,  # too fast — < 100ms floor
            api_key_id_used=uuid4(),
        )
        status = smoke_module._Status()  # type: ignore[attr-defined]
        smoke_module._assert_latency_plausible(  # type: ignore[attr-defined]
            record=record, mock_agent=False, status=status
        )
        assert status.passed  # warnings don't fail
        assert len(status.warnings) == 1

    def test_latency_plausible_silent_in_mock_mode(self, smoke_module: object) -> None:
        """When mock_agent=True, low latency is fine (no Anthropic call)."""
        record = TriggerFireRecord(
            id=uuid4(),
            trigger_id=uuid4(),
            activation_id=uuid4(),
            fired_at=datetime.now(UTC) - timedelta(seconds=1),
            condition_evaluation_data={"schema_version": 1},
            agent_response=AgentDecision.HOLD,
            agent_response_raw="Test",
            latency_ms=0,
            api_key_id_used=uuid4(),
        )
        status = smoke_module._Status()  # type: ignore[attr-defined]
        smoke_module._assert_latency_plausible(  # type: ignore[attr-defined]
            record=record, mock_agent=True, status=status
        )
        assert status.passed
        assert not status.warnings


class TestRunLocalModeMock:
    """End-to-end exercise of ``run_local_mode(mock_agent=True)``.

    The single test in this class is the script's happy-path
    integration: the orchestration runs to completion, the audit row
    is written, and the status object reports PASS. This is the test
    that proves the smoke script's main path works without burning
    API credits — exactly the assurance the F-7 PR documents.
    """

    async def test_mock_mode_completes_with_pass_status(
        self, smoke_module: object
    ) -> None:
        """Mocked end-to-end run produces PASS and writes one audit row."""
        status = smoke_module._Status()  # type: ignore[attr-defined]
        await smoke_module.run_local_mode(  # type: ignore[attr-defined]
            mock_agent=True, status=status
        )
        assert status.passed, (
            f"Mock smoke failed: failures={status.failures!r} "
            f"warnings={status.warnings!r}"
        )
        # No warnings expected in pure-mock mode either.
        assert not status.warnings, (
            f"Unexpected warnings in mock mode: {status.warnings!r}"
        )


class TestArgumentParsing:
    """``argparse`` accepts the documented flags."""

    def test_defaults(self, smoke_module: object) -> None:
        """Default mode is 'local'; --mock defaults to False."""
        args = smoke_module._parse_args([])  # type: ignore[attr-defined]
        assert args.mode == "local"
        assert args.mock is False
        assert args.base_url == "http://localhost:8000"

    def test_mock_flag(self, smoke_module: object) -> None:
        """--mock toggles the flag."""
        args = smoke_module._parse_args(["--mock"])  # type: ignore[attr-defined]
        assert args.mock is True

    def test_api_mode_flags(self, smoke_module: object) -> None:
        """API mode accepts base-url + api-key."""
        args = smoke_module._parse_args(  # type: ignore[attr-defined]
            [
                "--mode",
                "api",
                "--base-url",
                "https://zebutrader.com",
                "--api-key",
                "zk_test_xxx",
            ]
        )
        assert args.mode == "api"
        assert args.base_url == "https://zebutrader.com"
        assert args.api_key == "zk_test_xxx"

    def test_invalid_mode_rejected(self, smoke_module: object) -> None:
        """argparse rejects unknown modes with SystemExit."""
        with pytest.raises(SystemExit):
            smoke_module._parse_args(["--mode", "garbage"])  # type: ignore[attr-defined]
