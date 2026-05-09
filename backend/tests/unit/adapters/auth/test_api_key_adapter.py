"""Unit tests for :class:`ApiKeyAuthAdapter`.

Covers the contract:

- A valid raw key (matching a non-revoked, non-expired record) returns the
  Clerk user-id on ``AuthenticatedUser.id`` and bumps ``last_used_at``.
- A wrong key, revoked key, or expired key all raise the same
  :class:`InvalidTokenError` — no information leakage.
- Empty / whitespace tokens are rejected without a repository lookup.

The repository layer is faked with :class:`InMemoryApiKeyRepository`. The
hasher uses a fixed test pepper.
"""

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_DNS, uuid4, uuid5

import pytest

from zebu.adapters.auth.api_key_adapter import ApiKeyAuthAdapter
from zebu.adapters.auth.api_key_hasher import ApiKeyHasher
from zebu.application.ports.in_memory_api_key_repository import (
    InMemoryApiKeyRepository,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.exceptions import InvalidTokenError
from zebu.domain.value_objects.api_key_scope import ApiKeyScope

TEST_PEPPER = "unit-test-pepper-not-secret"
TEST_USER = "user_under_test"


def _hasher() -> ApiKeyHasher:
    return ApiKeyHasher(secret=TEST_PEPPER)


def _build_record(
    *,
    raw_key: str,
    revoked_at: datetime | None = None,
    expires_at: datetime | None = None,
    created_at: datetime | None = None,
    last_used_at: datetime | None = None,
    clerk_user_id: str = TEST_USER,
) -> ApiKey:
    """Build a persisted :class:`ApiKey` whose hash matches ``raw_key``."""
    hasher = _hasher()
    return ApiKey(
        id=uuid4(),
        user_id=uuid5(NAMESPACE_DNS, clerk_user_id),
        clerk_user_id=clerk_user_id,
        label="unit-test",
        key_hash=hasher.hash(raw_key),
        scopes=frozenset({ApiKeyScope.READ}),
        created_at=created_at or datetime.now(UTC) - timedelta(hours=1),
        last_used_at=last_used_at,
        revoked_at=revoked_at,
        expires_at=expires_at,
    )


async def _seed(repo: InMemoryApiKeyRepository, record: ApiKey) -> None:
    """Seed the in-memory repo with a record."""
    await repo.save(record)


class TestVerifyTokenSuccess:
    """The happy path."""

    @pytest.mark.asyncio
    async def test_valid_key_returns_clerk_user_id(self) -> None:
        repo = InMemoryApiKeyRepository()
        record = _build_record(raw_key="zk_valid")
        await _seed(repo, record)
        adapter = ApiKeyAuthAdapter(repository=repo, hasher=_hasher())

        user = await adapter.verify_token("zk_valid")

        assert user.id == TEST_USER
        # The API-key path doesn't carry email — empty by contract.
        assert user.email == ""

    @pytest.mark.asyncio
    async def test_valid_key_bumps_last_used_at(self) -> None:
        repo = InMemoryApiKeyRepository()
        # Seed the record with a created_at well before the injected clock
        # so the bump is unambiguously after creation.
        created_at = datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)
        record = _build_record(
            raw_key="zk_valid", created_at=created_at, last_used_at=None
        )
        await _seed(repo, record)

        fixed_now = datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC)
        adapter = ApiKeyAuthAdapter(
            repository=repo, hasher=_hasher(), now=lambda: fixed_now
        )

        await adapter.verify_token("zk_valid")

        bumped = await repo.get(record.id)
        assert bumped is not None
        assert bumped.last_used_at == fixed_now

    @pytest.mark.asyncio
    async def test_repeated_use_keeps_bumping_last_used_at(self) -> None:
        repo = InMemoryApiKeyRepository()
        created_at = datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)
        record = _build_record(raw_key="zk_valid", created_at=created_at)
        await _seed(repo, record)
        ticks = iter(
            [
                datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
                datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC),
            ]
        )
        adapter = ApiKeyAuthAdapter(
            repository=repo, hasher=_hasher(), now=lambda: next(ticks)
        )

        await adapter.verify_token("zk_valid")
        await adapter.verify_token("zk_valid")

        bumped = await repo.get(record.id)
        assert bumped is not None
        assert bumped.last_used_at == datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC)


class TestVerifyTokenRejection:
    """Every failure mode raises the same :class:`InvalidTokenError`."""

    @pytest.mark.asyncio
    async def test_unknown_key_rejected(self) -> None:
        repo = InMemoryApiKeyRepository()
        adapter = ApiKeyAuthAdapter(repository=repo, hasher=_hasher())

        with pytest.raises(InvalidTokenError, match="Invalid API key"):
            await adapter.verify_token("zk_unknown")

    @pytest.mark.asyncio
    async def test_wrong_key_for_seeded_record_rejected(self) -> None:
        """A different raw key hashes differently → no record found."""
        repo = InMemoryApiKeyRepository()
        await _seed(repo, _build_record(raw_key="zk_valid"))
        adapter = ApiKeyAuthAdapter(repository=repo, hasher=_hasher())

        with pytest.raises(InvalidTokenError, match="Invalid API key"):
            await adapter.verify_token("zk_wrong")

    @pytest.mark.asyncio
    async def test_revoked_key_rejected(self) -> None:
        repo = InMemoryApiKeyRepository()
        now = datetime.now(UTC)
        record = _build_record(
            raw_key="zk_valid",
            created_at=now - timedelta(hours=2),
            revoked_at=now - timedelta(hours=1),
        )
        await _seed(repo, record)
        adapter = ApiKeyAuthAdapter(repository=repo, hasher=_hasher())

        with pytest.raises(InvalidTokenError, match="Invalid API key"):
            await adapter.verify_token("zk_valid")

    @pytest.mark.asyncio
    async def test_expired_key_rejected(self) -> None:
        repo = InMemoryApiKeyRepository()
        now = datetime.now(UTC)
        record = _build_record(
            raw_key="zk_valid",
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        await _seed(repo, record)
        adapter = ApiKeyAuthAdapter(repository=repo, hasher=_hasher())

        with pytest.raises(InvalidTokenError, match="Invalid API key"):
            await adapter.verify_token("zk_valid")

    @pytest.mark.asyncio
    async def test_empty_token_rejected_without_lookup(self) -> None:
        repo = InMemoryApiKeyRepository()
        # Seed a key whose hash matches the empty string under our pepper —
        # if the adapter forwarded "" to the repo it would be found.
        await _seed(repo, _build_record(raw_key=""))
        adapter = ApiKeyAuthAdapter(repository=repo, hasher=_hasher())

        with pytest.raises(InvalidTokenError, match="Invalid API key"):
            await adapter.verify_token("")

    @pytest.mark.asyncio
    async def test_whitespace_token_rejected(self) -> None:
        repo = InMemoryApiKeyRepository()
        adapter = ApiKeyAuthAdapter(repository=repo, hasher=_hasher())

        with pytest.raises(InvalidTokenError, match="Invalid API key"):
            await adapter.verify_token("   ")


class TestGetUser:
    """The compose-multi auth dependency uses verify_token, but get_user
    is part of the AuthPort contract."""

    @pytest.mark.asyncio
    async def test_get_user_returns_round_tripped_user(self) -> None:
        adapter = ApiKeyAuthAdapter(
            repository=InMemoryApiKeyRepository(), hasher=_hasher()
        )

        user = await adapter.get_user("user_2abc")

        assert user is not None
        assert user.id == "user_2abc"
        assert user.email == ""

    @pytest.mark.asyncio
    async def test_get_user_returns_none_for_blank(self) -> None:
        adapter = ApiKeyAuthAdapter(
            repository=InMemoryApiKeyRepository(), hasher=_hasher()
        )

        assert await adapter.get_user("") is None
        assert await adapter.get_user("   ") is None
