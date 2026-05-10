"""API key repository port (interface).

Defines the contract for API key persistence. Adapters implement this
interface to provide actual storage (SQLModel, in-memory for tests).
"""

from typing import Protocol
from uuid import UUID

from zebu.domain.entities.api_key import ApiKey


class ApiKeyRepository(Protocol):
    """Interface for API key persistence operations.

    The repository works with the persisted :class:`ApiKey` entity (hash +
    metadata). The raw key string never crosses this boundary — it lives
    only in the :class:`ApiKeyCreationResult` returned by the issuance
    handler, and only for the duration of the request that minted it.
    """

    async def save(self, api_key: ApiKey) -> None:
        """Persist an API key (insert if new, update if exists).

        Args:
            api_key: The persisted record to save.
        """
        ...

    async def get(self, api_key_id: UUID) -> ApiKey | None:
        """Retrieve a single API key by ID.

        Args:
            api_key_id: Unique key identifier.

        Returns:
            ApiKey if found, ``None`` otherwise.
        """
        ...

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Retrieve an API key by its hash.

        This is the primary lookup path used by the auth adapter when
        validating an inbound request. The adapter hashes the presented
        raw key and asks the repository for a matching record.

        Args:
            key_hash: The deterministic hash of the raw key.

        Returns:
            ApiKey if a record matches, ``None`` otherwise.
        """
        ...

    async def get_by_user(self, user_id: UUID) -> list[ApiKey]:
        """Retrieve all API keys owned by a user, oldest first.

        This includes revoked and expired keys — the issuance UI lists
        every key the user has ever minted so they can audit history.
        Filtering by status is the caller's responsibility.

        Args:
            user_id: Owner UUID.

        Returns:
            List of ApiKey records (may be empty).
        """
        ...

    async def delete(self, api_key_id: UUID) -> None:
        """Delete an API key record entirely.

        Note: revocation is the normal "no longer usable" path — this
        method is for hard-deleting test fixtures or cleaning up. Most
        callers should set ``revoked_at`` via :meth:`save` instead so
        audit history is preserved.

        Args:
            api_key_id: Unique key identifier.
        """
        ...
