"""API key authentication adapter.

Implements :class:`AuthPort` by validating a raw API key against a hashed
record in the database. Used by Phase C2 to give agents a way to
authenticate without going through Clerk.

Flow:

1. Client sends ``Authorization: ApiKey <raw>`` or ``X-API-Key: <raw>``.
2. The auth dependency in ``dependencies.py`` strips the scheme/header
   and calls :meth:`verify_token` with the raw key.
3. This adapter hashes the raw key, looks it up in the repository, and
   verifies the record is active (not revoked, not expired).
4. On success, ``last_used_at`` is bumped and an :class:`AuthenticatedUser`
   is returned — same shape as the Clerk path, so downstream code is
   identical regardless of how the request authenticated.

The adapter returns ``AuthenticatedUser.id`` as the *original Clerk
user-id string* captured on the persisted record. The existing
``get_current_user_id`` dependency hashes it via
:func:`uuid5(NAMESPACE_DNS, ...)` to produce the same deterministic
UUID a Clerk request would, so every ownership check in the codebase
keeps working unchanged regardless of which auth path was used.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from zebu.adapters.auth.api_key_hasher import ApiKeyHasher
from zebu.application.ports.api_key_repository import ApiKeyRepository
from zebu.application.ports.auth_port import AuthenticatedUser
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)


class ApiKeyAuthAdapter:
    """Auth adapter that validates raw API keys against persisted hashes.

    Conforms to :class:`AuthPort`. ``get_user`` reconstructs a minimal
    :class:`AuthenticatedUser` from the user_id string — there's no
    Clerk-style metadata fetch on this path.

    Attributes:
        repository: Where to look up persisted keys.
        hasher: Hashing primitive (HMAC-SHA256 with a server pepper).
    """

    def __init__(
        self,
        repository: ApiKeyRepository,
        hasher: ApiKeyHasher,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            repository: API key repository.
            hasher: HMAC hashing primitive.
            now: Optional clock for deterministic tests. Defaults to
                ``datetime.now(UTC)``.
        """
        self._repository = repository
        self._hasher = hasher
        self._now = now or (lambda: datetime.now(UTC))

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify a raw API key and return the owning user identity.

        Every failure mode raises the same :class:`InvalidTokenError` —
        differentiated error messages would let an attacker probe whether
        a guessed key was once valid. Logs at INFO record the failure
        category for ops; the response is uniform.

        Args:
            token: The raw API key string presented by the client.

        Returns:
            AuthenticatedUser whose ``id`` is the owner UUID serialised
            as a string and whose ``email`` is empty.

        Raises:
            InvalidTokenError: For every authentication failure.
        """
        if not token or not token.strip():
            raise InvalidTokenError("Invalid API key")

        key_hash = self._hasher.hash(token)
        record = await self._repository.get_by_hash(key_hash)

        if record is None:
            logger.info("API key auth failed: no matching record")
            raise InvalidTokenError("Invalid API key")
        if record.is_revoked():
            logger.info(
                "API key auth failed: revoked",
                extra={"api_key_id": str(record.id)},
            )
            raise InvalidTokenError("Invalid API key")
        if record.is_expired():
            logger.info(
                "API key auth failed: expired",
                extra={"api_key_id": str(record.id)},
            )
            raise InvalidTokenError("Invalid API key")

        # Successful auth: bump last_used_at. Only this field changes.
        bumped = ApiKey(
            id=record.id,
            user_id=record.user_id,
            clerk_user_id=record.clerk_user_id,
            label=record.label,
            key_hash=record.key_hash,
            scopes=record.scopes,
            created_at=record.created_at,
            last_used_at=self._now(),
            revoked_at=record.revoked_at,
            expires_at=record.expires_at,
        )
        await self._repository.save(bumped)

        return AuthenticatedUser(
            id=record.clerk_user_id,
            email="",
        )

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        """Reconstruct a minimal :class:`AuthenticatedUser` from a Clerk user-id.

        The API-key path doesn't carry user metadata. Callers walking both
        the Clerk and API-key paths uniformly get a non-None response that
        round-trips ``user_id`` unchanged.

        Args:
            user_id: The Clerk user-id string returned by :meth:`verify_token`.

        Returns:
            ``AuthenticatedUser`` reconstructed from ``user_id`` (email
            is empty), or ``None`` for a falsy input.
        """
        if not user_id or not user_id.strip():
            return None
        return AuthenticatedUser(id=user_id, email="")
