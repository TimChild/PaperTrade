"""Tests for BacktestRun entity."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.domain.entities.backtest_run import BacktestRun
from zebu.domain.exceptions import InvalidBacktestRunError
from zebu.domain.value_objects.backtest_status import BacktestStatus


def _make_backtest_run(**overrides: object) -> BacktestRun:
    """Factory helper for building valid BacktestRun instances."""
    today = date.today()
    defaults: dict[str, object] = {
        "id": uuid4(),
        "user_id": uuid4(),
        "strategy_id": uuid4(),
        "portfolio_id": uuid4(),
        "strategy_snapshot": {"name": "Test", "type": "BUY_AND_HOLD"},
        "backtest_name": "My Backtest",
        "start_date": date(today.year - 2, 1, 1),
        "end_date": date(today.year - 1, 1, 1),
        "initial_cash": Decimal("10000.00"),
        "status": BacktestStatus.COMPLETED,
        "created_at": datetime.now(UTC) - timedelta(minutes=5),
    }
    defaults.update(overrides)
    return BacktestRun(**defaults)  # type: ignore[arg-type]


class TestBacktestRunConstruction:
    """Tests for valid and invalid BacktestRun construction."""

    def test_valid_construction(self) -> None:
        """Should create a BacktestRun with all required fields."""
        run = _make_backtest_run()
        assert run.backtest_name == "My Backtest"
        assert run.status == BacktestStatus.COMPLETED
        assert run.completed_at is None
        assert run.error_message is None

    def test_optional_fields_default_to_none(self) -> None:
        """All optional result fields should default to None."""
        run = _make_backtest_run()
        assert run.completed_at is None
        assert run.error_message is None
        assert run.total_return_pct is None
        assert run.max_drawdown_pct is None
        assert run.annualized_return_pct is None
        assert run.total_trades is None

    def test_strategy_id_can_be_none(self) -> None:
        """strategy_id should be optional (strategy may have been deleted)."""
        run = _make_backtest_run(strategy_id=None)
        assert run.strategy_id is None

    def test_backtest_name_empty_raises_error(self) -> None:
        """Should raise error for empty backtest_name."""
        with pytest.raises(
            InvalidBacktestRunError, match="cannot be empty or whitespace"
        ):
            _make_backtest_run(backtest_name="")

    def test_backtest_name_whitespace_raises_error(self) -> None:
        """Should raise error for whitespace-only backtest_name."""
        with pytest.raises(
            InvalidBacktestRunError, match="cannot be empty or whitespace"
        ):
            _make_backtest_run(backtest_name="   ")

    def test_backtest_name_too_long_raises_error(self) -> None:
        """Should raise error for backtest_name exceeding 100 characters."""
        with pytest.raises(InvalidBacktestRunError, match="maximum 100 characters"):
            _make_backtest_run(backtest_name="x" * 101)

    def test_backtest_name_exactly_100_chars_is_valid(self) -> None:
        """Should allow backtest_name exactly 100 characters long."""
        run = _make_backtest_run(backtest_name="x" * 100)
        assert len(run.backtest_name) == 100

    def test_start_date_equal_to_end_date_raises_error(self) -> None:
        """Should raise error when start_date equals end_date."""
        same_date = date.today() - timedelta(days=365)
        with pytest.raises(
            InvalidBacktestRunError, match="start_date must be before end_date"
        ):
            _make_backtest_run(start_date=same_date, end_date=same_date)

    def test_start_date_after_end_date_raises_error(self) -> None:
        """Should raise error when start_date is after end_date."""
        with pytest.raises(
            InvalidBacktestRunError, match="start_date must be before end_date"
        ):
            _make_backtest_run(
                start_date=date.today() - timedelta(days=100),
                end_date=date.today() - timedelta(days=200),
            )

    def test_end_date_in_future_raises_error(self) -> None:
        """Should raise error when end_date is in the future."""
        with pytest.raises(
            InvalidBacktestRunError, match="end_date cannot be in the future"
        ):
            _make_backtest_run(
                start_date=date.today() - timedelta(days=10),
                end_date=date.today() + timedelta(days=1),
            )

    def test_initial_cash_zero_raises_error(self) -> None:
        """Should raise error when initial_cash is zero."""
        with pytest.raises(
            InvalidBacktestRunError, match="initial_cash must be positive"
        ):
            _make_backtest_run(initial_cash=Decimal("0"))

    def test_initial_cash_negative_raises_error(self) -> None:
        """Should raise error when initial_cash is negative."""
        with pytest.raises(
            InvalidBacktestRunError, match="initial_cash must be positive"
        ):
            _make_backtest_run(initial_cash=Decimal("-100"))


class TestBacktestRunEquality:
    """Tests for BacktestRun equality semantics."""

    def test_equal_runs_have_same_id(self) -> None:
        """Two BacktestRun objects with the same ID should be equal."""
        run_id = uuid4()
        a = _make_backtest_run(id=run_id)
        b = _make_backtest_run(id=run_id, backtest_name="Different")
        assert a == b

    def test_different_ids_are_not_equal(self) -> None:
        """BacktestRuns with different IDs should not be equal."""
        assert _make_backtest_run() != _make_backtest_run()

    def test_not_equal_to_non_backtest_run(self) -> None:
        """BacktestRun should not be equal to a non-BacktestRun object."""
        assert _make_backtest_run() != "not a run"

    def test_hashable(self) -> None:
        """BacktestRun should be usable in sets and as dict keys."""
        run = _make_backtest_run()
        assert hash(run) == hash(run)
        s = {run}
        assert run in s

    def test_equal_runs_have_same_hash(self) -> None:
        """Equal runs (same ID) must have the same hash."""
        run_id = uuid4()
        a = _make_backtest_run(id=run_id)
        b = _make_backtest_run(id=run_id, backtest_name="Other")
        assert hash(a) == hash(b)
