"""Unit tests for the ExplorationTask entity, constraints, and findings.

Phase C4 — covers the state machine (OPEN -> IN_PROGRESS -> DONE | ABANDONED),
the invariants enforced by ``__post_init__``, and the immutable-transition
helpers (``claim``, ``complete``, ``abandon``).

The tests intentionally avoid touching any persistence layer — these are
pure domain units. Repository round-tripping is covered separately under
``tests/integration/adapters``.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from zebu.domain.entities.exploration_task import (
    ExplorationConstraints,
    ExplorationFindings,
    ExplorationTask,
    ExplorationTaskStatus,
    InvalidExplorationTaskError,
)
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker


def _make_task(**overrides: object) -> ExplorationTask:
    """Factory for valid OPEN tasks; tests override what they care about."""
    now = datetime.now(UTC) - timedelta(minutes=1)
    defaults: dict[str, object] = {
        "id": uuid4(),
        "created_by": uuid4(),
        "prompt": "Explore mean-reversion strategies on AAPL",
        "status": ExplorationTaskStatus.OPEN,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return ExplorationTask(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ExplorationConstraints
# ---------------------------------------------------------------------------


class TestExplorationConstraints:
    def test_default_construction_is_valid(self) -> None:
        constraints = ExplorationConstraints()
        assert constraints.max_backtests is None
        assert constraints.allow_live_activation is True
        assert constraints.strategy_type_whitelist is None

    def test_with_all_fields(self) -> None:
        constraints = ExplorationConstraints(
            max_backtests=10,
            allow_live_activation=False,
            strategy_type_whitelist=[StrategyType.MOVING_AVERAGE_CROSSOVER],
        )
        assert constraints.max_backtests == 10
        assert constraints.allow_live_activation is False
        assert constraints.strategy_type_whitelist == [
            StrategyType.MOVING_AVERAGE_CROSSOVER
        ]

    def test_max_backtests_zero_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="positive integer"):
            ExplorationConstraints(max_backtests=0)

    def test_max_backtests_negative_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="positive integer"):
            ExplorationConstraints(max_backtests=-3)

    def test_empty_whitelist_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="non-empty list"):
            ExplorationConstraints(strategy_type_whitelist=[])

    def test_is_frozen(self) -> None:
        constraints = ExplorationConstraints()
        with pytest.raises(FrozenInstanceError):
            # Frozen dataclass — direct attribute assignment raises.
            constraints.max_backtests = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExplorationFindings
# ---------------------------------------------------------------------------


class TestExplorationFindings:
    def test_minimal_construction(self) -> None:
        findings = ExplorationFindings(summary="Tried MA-crossover; #2 won.")
        assert findings.summary == "Tried MA-crossover; #2 won."
        assert findings.backtest_run_ids == []
        assert findings.strategy_ids == []
        assert findings.notes is None

    def test_with_all_fields(self) -> None:
        run_id = uuid4()
        strategy_id = uuid4()
        findings = ExplorationFindings(
            summary="Investigated three variants",
            backtest_run_ids=[run_id],
            strategy_ids=[strategy_id],
            notes=["volatility was unusual on day 5"],
        )
        assert findings.backtest_run_ids == [run_id]
        assert findings.strategy_ids == [strategy_id]
        assert findings.notes == ["volatility was unusual on day 5"]

    def test_empty_summary_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="cannot be empty"):
            ExplorationFindings(summary="")

    def test_whitespace_summary_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="cannot be empty"):
            ExplorationFindings(summary="   ")

    def test_summary_over_4000_chars_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="at most 4000"):
            ExplorationFindings(summary="x" * 4001)

    def test_summary_exactly_4000_chars_valid(self) -> None:
        findings = ExplorationFindings(summary="x" * 4000)
        assert len(findings.summary) == 4000

    def test_is_frozen(self) -> None:
        findings = ExplorationFindings(summary="ok")
        with pytest.raises(FrozenInstanceError):
            findings.summary = "different"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExplorationTask construction
# ---------------------------------------------------------------------------


class TestExplorationTaskConstruction:
    def test_minimal_open_task(self) -> None:
        task = _make_task()
        assert task.status is ExplorationTaskStatus.OPEN
        assert task.target_portfolio_id is None
        assert task.tickers is None
        assert task.constraints is None
        assert task.claimed_by is None
        assert task.claimed_at is None
        assert task.findings is None

    def test_with_full_optional_payload(self) -> None:
        portfolio_id = uuid4()
        task = _make_task(
            target_portfolio_id=portfolio_id,
            tickers=[Ticker("AAPL"), Ticker("MSFT")],
            constraints=ExplorationConstraints(max_backtests=5),
        )
        assert task.target_portfolio_id == portfolio_id
        assert task.tickers is not None
        assert [t.symbol for t in task.tickers] == ["AAPL", "MSFT"]
        assert task.constraints is not None
        assert task.constraints.max_backtests == 5

    def test_empty_prompt_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="prompt cannot be empty"):
            _make_task(prompt="")

    def test_whitespace_prompt_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="prompt cannot be empty"):
            _make_task(prompt="   ")

    def test_prompt_over_4000_chars_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError, match="prompt must be at most 4000"
        ):
            _make_task(prompt="x" * 4001)

    def test_too_many_tickers_raises(self) -> None:
        with pytest.raises(InvalidExplorationTaskError, match="at most 50 entries"):
            _make_task(tickers=[Ticker("AAA") for _ in range(51)])

    def test_future_created_at_raises(self) -> None:
        future = datetime.now(UTC) + timedelta(minutes=10)
        with pytest.raises(
            InvalidExplorationTaskError, match="created_at cannot be in the future"
        ):
            _make_task(created_at=future, updated_at=future)

    def test_updated_before_created_raises(self) -> None:
        now = datetime.now(UTC) - timedelta(minutes=1)
        earlier = now - timedelta(minutes=5)
        with pytest.raises(
            InvalidExplorationTaskError, match="updated_at cannot be before"
        ):
            _make_task(created_at=now, updated_at=earlier)

    def test_claimed_before_created_raises(self) -> None:
        now = datetime.now(UTC) - timedelta(minutes=1)
        earlier = now - timedelta(minutes=5)
        with pytest.raises(
            InvalidExplorationTaskError, match="claimed_at cannot be before"
        ):
            _make_task(
                created_at=now,
                updated_at=now,
                status=ExplorationTaskStatus.IN_PROGRESS,
                claimed_by="agent-a",
                claimed_at=earlier,
            )


# ---------------------------------------------------------------------------
# Status invariants
# ---------------------------------------------------------------------------


class TestStatusInvariants:
    def test_open_with_claimed_by_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError, match="OPEN status must not have"
        ):
            _make_task(claimed_by="agent-a")

    def test_open_with_claimed_at_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError, match="OPEN status must not have"
        ):
            _make_task(claimed_at=datetime.now(UTC))

    def test_open_with_findings_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError, match="OPEN status must not have findings"
        ):
            _make_task(findings=ExplorationFindings(summary="x"))

    def test_in_progress_without_claimed_by_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError,
            match="IN_PROGRESS status must have both claimed_by",
        ):
            _make_task(
                status=ExplorationTaskStatus.IN_PROGRESS,
                claimed_at=datetime.now(UTC) - timedelta(seconds=30),
            )

    def test_in_progress_without_claimed_at_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError,
            match="IN_PROGRESS status must have both claimed_by",
        ):
            _make_task(
                status=ExplorationTaskStatus.IN_PROGRESS,
                claimed_by="agent-a",
            )

    def test_in_progress_with_findings_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError,
            match="IN_PROGRESS status must not have findings",
        ):
            _make_task(
                status=ExplorationTaskStatus.IN_PROGRESS,
                claimed_by="agent-a",
                claimed_at=datetime.now(UTC) - timedelta(seconds=30),
                findings=ExplorationFindings(summary="too early"),
            )

    def test_done_without_findings_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError, match="DONE status requires findings"
        ):
            _make_task(
                status=ExplorationTaskStatus.DONE,
                claimed_by="agent-a",
                claimed_at=datetime.now(UTC) - timedelta(seconds=30),
            )

    def test_done_without_claim_metadata_raises(self) -> None:
        with pytest.raises(
            InvalidExplorationTaskError, match="DONE status must retain claimed"
        ):
            _make_task(
                status=ExplorationTaskStatus.DONE,
                findings=ExplorationFindings(summary="ok"),
            )

    def test_abandoned_without_anything_is_valid(self) -> None:
        # Abandoning an OPEN-only task — claimed metadata never set.
        task = _make_task(status=ExplorationTaskStatus.ABANDONED)
        assert task.status is ExplorationTaskStatus.ABANDONED
        assert task.claimed_by is None
        assert task.findings is None

    def test_abandoned_keeps_claim_metadata(self) -> None:
        # Abandoning a previously-claimed task — metadata preserved.
        # claimed_at must be >= created_at (factory uses now-1min).
        task = _make_task(
            status=ExplorationTaskStatus.ABANDONED,
            claimed_by="agent-a",
            claimed_at=datetime.now(UTC) - timedelta(seconds=30),
        )
        assert task.claimed_by == "agent-a"


# ---------------------------------------------------------------------------
# Identity, hashing, repr
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_equality_by_id(self) -> None:
        same_id = uuid4()
        a = _make_task(id=same_id)
        b = _make_task(id=same_id, prompt="something different")
        assert a == b
        # Different IDs are not equal even with the same prompt.
        c = _make_task(prompt=a.prompt)
        assert a != c

    def test_equality_with_non_task(self) -> None:
        task = _make_task()
        assert task != "not a task"
        assert task != object()

    def test_hash_uses_id(self) -> None:
        task = _make_task()
        # Should be usable in a set / dict key.
        assert hash(task) == hash(task.id)
        assert {task, task} == {task}

    def test_repr_includes_id_and_status(self) -> None:
        task = _make_task()
        r = repr(task)
        assert str(task.id) in r
        assert "OPEN" in r

    def test_is_frozen(self) -> None:
        task = _make_task()
        with pytest.raises(FrozenInstanceError):
            task.status = ExplorationTaskStatus.IN_PROGRESS  # type: ignore[misc]


# ---------------------------------------------------------------------------
# State machine — claim / complete / abandon
# ---------------------------------------------------------------------------


class TestClaim:
    def test_claim_open_task(self) -> None:
        task = _make_task()
        when = datetime.now(UTC)
        claimed = task.claim(agent_id="agent-a", claimed_at=when)
        assert claimed.status is ExplorationTaskStatus.IN_PROGRESS
        assert claimed.claimed_by == "agent-a"
        assert claimed.claimed_at == when
        assert claimed.updated_at == when
        # Original instance is unchanged (immutable).
        assert task.status is ExplorationTaskStatus.OPEN
        assert task.claimed_by is None

    def test_claim_returns_new_instance(self) -> None:
        task = _make_task()
        claimed = task.claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
        assert claimed is not task

    def test_claim_non_open_raises(self) -> None:
        task = _make_task().claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
        with pytest.raises(
            InvalidExplorationTaskError,
            match="only OPEN tasks can be claimed",
        ):
            task.claim(agent_id="agent-b", claimed_at=datetime.now(UTC))

    def test_claim_empty_agent_id_raises(self) -> None:
        task = _make_task()
        with pytest.raises(InvalidExplorationTaskError, match="non-empty agent_id"):
            task.claim(agent_id="", claimed_at=datetime.now(UTC))

    def test_claim_whitespace_agent_id_raises(self) -> None:
        task = _make_task()
        with pytest.raises(InvalidExplorationTaskError, match="non-empty agent_id"):
            task.claim(agent_id="   ", claimed_at=datetime.now(UTC))


class TestComplete:
    def test_complete_in_progress_task(self) -> None:
        task = _make_task().claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
        findings = ExplorationFindings(summary="ran 3 backtests")
        completed = task.complete(findings=findings, completed_at=datetime.now(UTC))
        assert completed.status is ExplorationTaskStatus.DONE
        assert completed.findings == findings
        # Claim metadata is preserved.
        assert completed.claimed_by == "agent-a"
        assert completed.claimed_at == task.claimed_at

    def test_complete_open_raises(self) -> None:
        task = _make_task()
        with pytest.raises(
            InvalidExplorationTaskError,
            match="only IN_PROGRESS tasks can be completed",
        ):
            task.complete(
                findings=ExplorationFindings(summary="x"),
                completed_at=datetime.now(UTC),
            )

    def test_complete_already_done_raises(self) -> None:
        task = (
            _make_task()
            .claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
            .complete(
                findings=ExplorationFindings(summary="x"),
                completed_at=datetime.now(UTC),
            )
        )
        with pytest.raises(
            InvalidExplorationTaskError,
            match="only IN_PROGRESS tasks can be completed",
        ):
            task.complete(
                findings=ExplorationFindings(summary="y"),
                completed_at=datetime.now(UTC),
            )


class TestAbandon:
    def test_abandon_open_task(self) -> None:
        task = _make_task()
        abandoned = task.abandon(abandoned_at=datetime.now(UTC))
        assert abandoned.status is ExplorationTaskStatus.ABANDONED
        # Claim metadata stays None — was never claimed.
        assert abandoned.claimed_by is None
        assert abandoned.claimed_at is None

    def test_abandon_in_progress_keeps_claim_metadata(self) -> None:
        task = _make_task().claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
        abandoned = task.abandon(abandoned_at=datetime.now(UTC))
        assert abandoned.status is ExplorationTaskStatus.ABANDONED
        assert abandoned.claimed_by == "agent-a"
        assert abandoned.claimed_at == task.claimed_at

    def test_abandon_done_raises(self) -> None:
        task = (
            _make_task()
            .claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
            .complete(
                findings=ExplorationFindings(summary="x"),
                completed_at=datetime.now(UTC),
            )
        )
        with pytest.raises(
            InvalidExplorationTaskError, match="task is already terminal"
        ):
            task.abandon(abandoned_at=datetime.now(UTC))

    def test_abandon_already_abandoned_raises(self) -> None:
        task = _make_task().abandon(abandoned_at=datetime.now(UTC))
        with pytest.raises(
            InvalidExplorationTaskError, match="task is already terminal"
        ):
            task.abandon(abandoned_at=datetime.now(UTC))


class TestIsTerminal:
    def test_open_is_not_terminal(self) -> None:
        assert _make_task().is_terminal is False

    def test_in_progress_is_not_terminal(self) -> None:
        task = _make_task().claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
        assert task.is_terminal is False

    def test_done_is_terminal(self) -> None:
        task = (
            _make_task()
            .claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
            .complete(
                findings=ExplorationFindings(summary="x"),
                completed_at=datetime.now(UTC),
            )
        )
        assert task.is_terminal is True

    def test_abandoned_is_terminal(self) -> None:
        task = _make_task().abandon(abandoned_at=datetime.now(UTC))
        assert task.is_terminal is True


# ---------------------------------------------------------------------------
# replace() with invariants — make sure dataclass replace doesn't bypass them
# ---------------------------------------------------------------------------


class TestReplaceInvariants:
    def test_replace_to_invalid_state_raises(self) -> None:
        # ``replace`` calls ``__init__`` which calls ``__post_init__``, so
        # invariants are still enforced — this is a guarded bypass.
        task = _make_task()
        with pytest.raises(InvalidExplorationTaskError):
            replace(task, status=ExplorationTaskStatus.IN_PROGRESS)
