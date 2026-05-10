"""In-memory implementation of :class:`ApiKeyRepository` for tests.

This adapter lives in ``application/ports/`` alongside the other in-memory
test fakes (matching the existing convention). It has no persistence —
state is lost when the instance is dropped.
"""

from uuid import UUID

from zebu.domain.entities.api_key import ApiKey


class InMemoryApiKeyRepository:
    """Test-only in-memory implementation of :class:`ApiKeyRepository`."""

    def __init__(self) -> None:
        """Initialize an empty in-memory store."""
        self._by_id: dict[UUID, ApiKey] = {}

    async def save(self, api_key: ApiKey) -> None:
        """Insert or replace an API key in the in-memory store."""
        self._by_id[api_key.id] = api_key

    async def get(self, api_key_id: UUID) -> ApiKey | None:
        """Look up an API key by ID."""
        return self._by_id.get(api_key_id)

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Look up an API key by hash. O(n) — fine for tests."""
        for api_key in self._by_id.values():
            if api_key.key_hash == key_hash:
                return api_key
        return None

    async def get_by_user(self, user_id: UUID) -> list[ApiKey]:
        """Return all keys for a user, oldest first."""
        keys = [k for k in self._by_id.values() if k.user_id == user_id]
        keys.sort(key=lambda k: k.created_at)
        return keys

    async def delete(self, api_key_id: UUID) -> None:
        """Remove an API key from the in-memory store."""
        self._by_id.pop(api_key_id, None)
