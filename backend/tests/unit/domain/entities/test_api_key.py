"""Unit tests for the :class:`ApiKey` domain entity.

These tests pin down the entity's invariants: scope non-emptiness, time
ordering, label/clerk-id validation, and the lifecycle helpers
(:meth:`is_revoked`, :meth:`is_expired`, :meth:`is_active`,
:meth:`has_scope`). The entity has no I/O — every test builds an
``ApiKey`` directly.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from zebu.domain.entities.api_key import ApiKey, ApiKeyCreationResult
from zebu.domain.exceptions import InvalidApiKeyError
from zebu.domain.value_objects.api_key_scope import ApiKeyScope


def _build(
    *,
    label: str = "test-key",
    scopes: frozenset[ApiKeyScope] | None = None,
    key_hash: str = "0" * 64,
    clerk_user_id: str = "user_test",
    created_at: datetime | None = None,
    last_used_at: datetime | None = None,
    revoked_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> ApiKey:
    """Build an ApiKey with sensible defaults — keeps every test focused."""
    return ApiKey(
        id=uuid4(),
        user_id=uuid4(),
        clerk_user_id=clerk_user_id,
        label=label,
        key_hash=key_hash,
        scopes=scopes if scopes is not None else frozenset({ApiKeyScope.READ}),
        created_at=created_at or datetime.now(UTC),
        last_used_at=last_used_at,
        revoked_at=revoked_at,
        expires_at=expires_at,
    )


class TestApiKeyConstruction:
    """Construction-time invariants — every assertion in __post_init__."""

    def test_minimum_valid_key_constructs(self) -> None:
        api_key = _build()
        assert api_key.label == "test-key"
        assert ApiKeyScope.READ in api_key.scopes

    def test_label_cannot_be_empty(self) -> None:
        with pytest.raises(InvalidApiKeyError, match="label"):
            _build(label="")

    def test_label_cannot_be_whitespace_only(self) -> None:
        with pytest.raises(InvalidApiKeyError, match="label"):
            _build(label="   ")

    def test_label_cannot_exceed_100_chars(self) -> None:
        with pytest.raises(InvalidApiKeyError, match="100"):
            _build(label="x" * 101)

    def test_label_at_100_chars_is_allowed(self) -> None:
        api_key = _build(label="x" * 100)
        assert len(api_key.label) == 100

    def test_clerk_user_id_cannot_be_empty(self) -> None:
        with pytest.raises(InvalidApiKeyError, match="clerk_user_id"):
            _build(clerk_user_id="")

    def test_key_hash_cannot_be_empty(self) -> None:
        with pytest.raises(InvalidApiKeyError, match="key_hash"):
            _build(key_hash="")

    def test_scopes_must_have_at_least_one_entry(self) -> None:
        with pytest.raises(InvalidApiKeyError, match="scope"):
            _build(scopes=frozenset())

    def test_multiple_scopes_are_allowed(self) -> None:
        api_key = _build(scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}))
        assert ApiKeyScope.READ in api_key.scopes
        assert ApiKeyScope.TRADE in api_key.scopes

    def test_created_at_in_future_rejected(self) -> None:
        future = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(InvalidApiKeyError, match="future"):
            _build(created_at=future)

    def test_last_used_at_before_created_at_rejected(self) -> None:
        created = datetime.now(UTC) - timedelta(hours=1)
        last_used = datetime.now(UTC) - timedelta(hours=2)
        with pytest.raises(InvalidApiKeyError, match="last_used_at"):
            _build(created_at=created, last_used_at=last_used)

    def test_revoked_at_before_created_at_rejected(self) -> None:
        created = datetime.now(UTC) - timedelta(hours=1)
        revoked = datetime.now(UTC) - timedelta(hours=2)
        with pytest.raises(InvalidApiKeyError, match="revoked_at"):
            _build(created_at=created, revoked_at=revoked)

    def test_expires_at_at_or_before_created_at_rejected(self) -> None:
        # Spec: born-expired keys must be refused at construction.
        created = datetime.now(UTC) - timedelta(hours=1)
        expires = datetime.now(UTC) - timedelta(hours=2)
        with pytest.raises(InvalidApiKeyError, match="expires_at"):
            _build(created_at=created, expires_at=expires)

    def test_expires_at_equal_to_created_at_rejected(self) -> None:
        moment = datetime.now(UTC) - timedelta(hours=1)
        with pytest.raises(InvalidApiKeyError, match="expires_at"):
            _build(created_at=moment, expires_at=moment)

    def test_naive_timestamps_are_treated_as_utc(self) -> None:
        # Construction must not reject naive datetimes — they're a real
        # database round-trip artefact and the entity should re-attach UTC.
        naive_now = datetime.now(UTC).replace(tzinfo=None)
        api_key = _build(created_at=naive_now)
        assert api_key.created_at == naive_now


class TestApiKeyLifecycleHelpers:
    """is_revoked / is_expired / is_active / has_scope behaviour."""

    def test_active_key_is_not_revoked(self) -> None:
        assert _build().is_revoked() is False

    def test_revoked_key_reports_revoked(self) -> None:
        now = datetime.now(UTC)
        api_key = _build(
            created_at=now - timedelta(minutes=10),
            revoked_at=now,
        )
        assert api_key.is_revoked() is True
        assert api_key.is_active() is False

    def test_expired_key_reports_expired(self) -> None:
        now = datetime.now(UTC)
        # expires_at must be after created_at to satisfy invariants.
        api_key = _build(
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        assert api_key.is_expired(at=now) is True
        assert api_key.is_active(at=now) is False

    def test_unexpired_key_reports_not_expired(self) -> None:
        now = datetime.now(UTC)
        api_key = _build(
            created_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=1),
        )
        assert api_key.is_expired(at=now) is False
        assert api_key.is_active(at=now) is True

    def test_no_expiry_means_never_expired(self) -> None:
        assert _build(expires_at=None).is_expired() is False

    def test_revoked_key_is_inactive_even_if_unexpired(self) -> None:
        now = datetime.now(UTC)
        api_key = _build(
            created_at=now - timedelta(hours=1),
            revoked_at=now,
            expires_at=now + timedelta(days=1),
        )
        assert api_key.is_active(at=now) is False

    def test_has_scope_returns_true_when_present(self) -> None:
        api_key = _build(scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}))
        assert api_key.has_scope(ApiKeyScope.READ) is True
        assert api_key.has_scope(ApiKeyScope.TRADE) is True

    def test_has_scope_returns_false_when_absent(self) -> None:
        api_key = _build(scopes=frozenset({ApiKeyScope.READ}))
        assert api_key.has_scope(ApiKeyScope.ADMIN) is False


class TestApiKeyEquality:
    """Equality and hashing behave like other entities — by ID."""

    def test_equal_when_id_matches(self) -> None:
        common_id = uuid4()
        a = ApiKey(
            id=common_id,
            user_id=uuid4(),
            clerk_user_id="u",
            label="a",
            key_hash="x" * 64,
            scopes=frozenset({ApiKeyScope.READ}),
            created_at=datetime.now(UTC),
        )
        b = ApiKey(
            id=common_id,
            user_id=uuid4(),
            clerk_user_id="u2",
            label="b",
            key_hash="y" * 64,
            scopes=frozenset({ApiKeyScope.TRADE}),
            created_at=datetime.now(UTC),
        )
        assert a == b
        assert hash(a) == hash(b)

    def test_not_equal_to_non_apikey(self) -> None:
        assert _build() != "not an apikey"

    def test_repr_does_not_leak_key_hash(self) -> None:
        api_key = _build(key_hash="deadbeefdeadbeef")
        assert "deadbeef" not in repr(api_key)


class TestApiKeyCreationResult:
    """The pair returned at issuance time."""

    def test_creation_result_holds_raw_key_and_record(self) -> None:
        record = _build()
        result = ApiKeyCreationResult(api_key=record, raw_key="zk_secret_token")
        assert result.api_key is record
        assert result.raw_key == "zk_secret_token"
