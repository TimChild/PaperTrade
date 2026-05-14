"""Tests for StrategyActivation entity."""

import logging
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.exceptions import InvalidStrategyActivationError
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus


def _make_activation(**overrides: object) -> StrategyActivation:
    """Factory helper for building valid StrategyActivation instances."""
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": uuid4(),
        "user_id": uuid4(),
        "strategy_id": uuid4(),
        "portfolio_id": uuid4(),
        "status": ActivationStatus.ACTIVE,
        "frequency": ActivationFrequency.DAILY_MARKET_CLOSE,
        "created_at": now - timedelta(minutes=5),
        "updated_at": now - timedelta(minutes=4),
    }
    defaults.update(overrides)
    return StrategyActivation(**defaults)  # type: ignore[arg-type]


class TestStrategyActivationConstruction:
    """Tests for valid and invalid StrategyActivation construction."""

    def test_valid_construction(self) -> None:
        """Should create an activation with all required fields."""
        activation = _make_activation()
        assert activation.status is ActivationStatus.ACTIVE
        assert activation.frequency is ActivationFrequency.DAILY_MARKET_CLOSE
        assert activation.last_executed_at is None
        assert activation.last_error is None

    def test_optional_fields_default_to_none(self) -> None:
        """``last_executed_at`` and ``last_error`` default to None."""
        activation = _make_activation()
        assert activation.last_executed_at is None
        assert activation.last_error is None

    def test_with_last_executed_at(self) -> None:
        """Should accept a populated last_executed_at after creation."""
        now = datetime.now(UTC)
        created = now - timedelta(hours=1)
        activation = _make_activation(
            created_at=created,
            updated_at=now,
            last_executed_at=now - timedelta(minutes=10),
        )
        assert activation.last_executed_at is not None

    def test_updated_at_before_created_at_raises(self) -> None:
        """``updated_at`` cannot be before ``created_at``."""
        now = datetime.now(UTC)
        with pytest.raises(
            InvalidStrategyActivationError,
            match="updated_at .* cannot be before created_at",
        ):
            _make_activation(
                created_at=now - timedelta(minutes=1),
                updated_at=now - timedelta(minutes=5),
            )

    def test_updated_at_equal_to_created_at_is_valid(self) -> None:
        """``updated_at == created_at`` is allowed (e.g. on initial create)."""
        now = datetime.now(UTC) - timedelta(minutes=1)
        activation = _make_activation(created_at=now, updated_at=now)
        assert activation.created_at == activation.updated_at

    def test_future_created_at_raises(self) -> None:
        """``created_at`` cannot be in the future."""
        future = datetime.now(UTC) + timedelta(hours=1)
        with pytest.raises(
            InvalidStrategyActivationError,
            match="created_at cannot be in the future",
        ):
            _make_activation(
                created_at=future,
                updated_at=future + timedelta(minutes=1),
            )

    def test_last_executed_before_created_at_raises(self) -> None:
        """``last_executed_at`` cannot precede ``created_at``."""
        now = datetime.now(UTC)
        with pytest.raises(
            InvalidStrategyActivationError,
            match="last_executed_at cannot be before created_at",
        ):
            _make_activation(
                created_at=now - timedelta(minutes=2),
                updated_at=now - timedelta(minutes=1),
                last_executed_at=now - timedelta(hours=1),
            )

    def test_last_executed_in_future_raises(self) -> None:
        """``last_executed_at`` cannot be in the future."""
        now = datetime.now(UTC)
        with pytest.raises(
            InvalidStrategyActivationError,
            match="last_executed_at cannot be in the future",
        ):
            _make_activation(
                created_at=now - timedelta(minutes=5),
                updated_at=now - timedelta(minutes=4),
                last_executed_at=now + timedelta(minutes=10),
            )

    def test_naive_datetimes_treated_as_utc(self) -> None:
        """Naive datetimes should be accepted and treated as UTC."""
        now = datetime.now(UTC).replace(tzinfo=None)
        # All three timestamps naive — should not raise.
        activation = _make_activation(
            created_at=now - timedelta(minutes=2),
            updated_at=now - timedelta(minutes=1),
            last_executed_at=now,
        )
        assert activation.last_executed_at is not None

    def test_error_status_without_last_error_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """ERROR status without a ``last_error`` message should log a warning."""
        with caplog.at_level(
            logging.WARNING,
            logger="zebu.domain.entities.strategy_activation",
        ):
            _make_activation(status=ActivationStatus.ERROR, last_error=None)
        assert any(
            "status=ERROR but no last_error message" in record.message
            for record in caplog.records
        )

    def test_error_status_with_last_error_does_not_warn(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """ERROR status with a ``last_error`` should not log a warning."""
        with caplog.at_level(
            logging.WARNING,
            logger="zebu.domain.entities.strategy_activation",
        ):
            _make_activation(
                status=ActivationStatus.ERROR,
                last_error="Connection refused",
            )
        assert not any(
            "status=ERROR but no last_error message" in record.message
            for record in caplog.records
        )

    def test_active_status_without_last_error_does_not_warn(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Healthy ACTIVE status with no last_error should not log a warning."""
        with caplog.at_level(
            logging.WARNING,
            logger="zebu.domain.entities.strategy_activation",
        ):
            _make_activation(status=ActivationStatus.ACTIVE, last_error=None)
        assert not any(
            "status=ERROR but no last_error message" in record.message
            for record in caplog.records
        )


class TestStrategyActivationStatusValues:
    """Smoke checks on every status value."""

    @pytest.mark.parametrize(
        "status",
        [
            ActivationStatus.ACTIVE,
            ActivationStatus.PAUSED,
            ActivationStatus.STOPPED,
        ],
    )
    def test_non_error_statuses_construct_cleanly(
        self, status: ActivationStatus
    ) -> None:
        """ACTIVE / PAUSED / STOPPED should not require a last_error."""
        activation = _make_activation(status=status, last_error=None)
        assert activation.status is status
        assert activation.last_error is None

    def test_error_status_constructs_with_last_error(self) -> None:
        """ERROR with a meaningful last_error should construct cleanly."""
        activation = _make_activation(
            status=ActivationStatus.ERROR,
            last_error="No prices available",
        )
        assert activation.status is ActivationStatus.ERROR
        assert activation.last_error == "No prices available"

    def test_activation_status_rejects_unknown_value(self) -> None:
        """Constructing ActivationStatus with a bad string raises ValueError.

        This is the runtime guardrail relied on by the adapter layer:
        ``ActivationStatus(self.status)`` in ``StrategyActivationModel.to_domain``
        raises if a stored row's status drifts from the enum.
        """
        with pytest.raises(ValueError):
            ActivationStatus("NOT_A_REAL_STATUS")

    def test_activation_frequency_rejects_unknown_value(self) -> None:
        """Constructing ActivationFrequency with a bad string raises ValueError."""
        with pytest.raises(ValueError):
            ActivationFrequency("NOT_A_REAL_FREQUENCY")


class TestStrategyActivationEqualityAndHashing:
    """Identity-based equality and hashing tests."""

    def test_same_id_means_equal(self) -> None:
        """Activations with the same id should compare equal."""
        activation_id = uuid4()
        a = _make_activation(id=activation_id, status=ActivationStatus.ACTIVE)
        b = _make_activation(id=activation_id, status=ActivationStatus.PAUSED)
        # Different status, same id — still equal under identity semantics.
        assert a == b

    def test_different_id_means_not_equal(self) -> None:
        """Different ids should not be equal even if all other fields match."""
        a = _make_activation()
        b = _make_activation()
        assert a != b

    def test_not_equal_to_non_activation(self) -> None:
        """Comparing to a non-activation should return False, not error."""
        a = _make_activation()
        assert a != "not an activation"
        assert a is not None  # sanity

    def test_hash_uses_id(self) -> None:
        """Activations with the same id should hash the same."""
        activation_id = uuid4()
        a = _make_activation(id=activation_id)
        b = _make_activation(id=activation_id)
        assert hash(a) == hash(b)

    def test_usable_in_sets(self) -> None:
        """Activations should be usable in sets via id-based hashing."""
        a = _make_activation()
        b = _make_activation(id=a.id)  # same id => same activation
        c = _make_activation()  # different id
        s = {a, b, c}
        assert len(s) == 2


class TestStrategyActivationFrozenness:
    """Activation entity is immutable after construction."""

    def test_cannot_mutate_field(self) -> None:
        """Setting any attribute should raise FrozenInstanceError."""
        activation = _make_activation()
        with pytest.raises(FrozenInstanceError):
            activation.status = ActivationStatus.PAUSED  # type: ignore[misc]

    def test_cannot_mutate_last_error(self) -> None:
        """Cannot mutate optional fields either."""
        activation = _make_activation()
        with pytest.raises(FrozenInstanceError):
            activation.last_error = "broken"  # type: ignore[misc]


class TestStrategyActivationRepr:
    """The repr output should be informative for debugging."""

    def test_repr_contains_key_fields(self) -> None:
        """repr should include id, strategy_id, and status."""
        activation = _make_activation()
        text = repr(activation)
        assert str(activation.id) in text
        assert str(activation.strategy_id) in text
        assert "ACTIVE" in text


class TestDeactivationReason:
    """Issue #284 — ``deactivation_reason`` is the user-pause channel.

    Distinct from ``last_error`` (execution failures). Both can coexist
    — e.g. an activation that failed at runtime, was paused by a human
    with a note, and then re-activated, would carry both breadcrumbs.
    """

    def test_default_deactivation_reason_is_none(self) -> None:
        activation = _make_activation()
        assert activation.deactivation_reason is None

    def test_deactivation_reason_round_trips(self) -> None:
        activation = _make_activation(deactivation_reason="manual review needed")
        assert activation.deactivation_reason == "manual review needed"

    def test_deactivation_reason_and_last_error_can_coexist(self) -> None:
        """A row can carry both: an execution failure AND a pause note."""
        activation = _make_activation(
            status=ActivationStatus.PAUSED,
            last_error="market data timeout on AAPL",
            deactivation_reason="taking a break while we investigate",
        )
        assert activation.last_error == "market data timeout on AAPL"
        assert activation.deactivation_reason == "taking a break while we investigate"

    def test_deactivation_reason_is_frozen(self) -> None:
        activation = _make_activation(deactivation_reason="x")
        with pytest.raises(FrozenInstanceError):
            activation.deactivation_reason = "y"  # type: ignore[misc]
