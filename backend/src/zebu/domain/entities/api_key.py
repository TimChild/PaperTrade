"""ApiKey entity - Machine-identity credential issued to a user.

API keys let agents (Claude Code subagents, scheduled tasks, MCP servers)
authenticate to the backend without going through Clerk. Each key is owned
by a Clerk user and carries one or more scopes. The raw key string is only
seen at creation; the persisted entity stores a hash.

The entity is pure: it has no I/O, no hashing primitives, no DB access.
Hashing is performed by the auth adapter, persistence by the repository.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from zebu.domain.exceptions import InvalidApiKeyError
from zebu.domain.value_objects.api_key_scope import ApiKeyScope


@dataclass(frozen=True)
class ApiKey:
    """A persisted API key — hash + metadata, not the raw secret.

    The raw key string is generated server-side at issuance time, returned
    once to the caller, and immediately discarded; only :attr:`key_hash`
    persists. ``ApiKey`` represents the *server-side record* of that key
    and is what the auth adapter loads to validate an inbound request.

    Attributes:
        id: Unique key identifier (UUID, surrogate of ``key_hash``).
        user_id: Clerk-derived owner UUID (matches the deterministic UUID
            used everywhere else for ownership checks). The auth adapter
            returns an :class:`AuthenticatedUser` whose ``id`` is the
            *original* Clerk user-id string stored on the record, so the
            existing ``get_current_user_id`` dependency keeps round-tripping
            it via :func:`uuid5(NAMESPACE_DNS, ...)` and produces the same
            UUID it would for a Clerk-authenticated request.
        clerk_user_id: The original Clerk user-id string (e.g.
            ``"user_2abc..."``) captured at mint time. The auth adapter
            returns this on :class:`AuthenticatedUser.id` so downstream
            ownership checks keep working unchanged.
        label: Human-readable label, set at creation (e.g.,
            "claude-desktop", "scheduled-snapshot-job"). 1-100 chars.
        key_hash: Deterministic, salt-free hash of the raw key (HMAC-SHA256
            with a server secret). The auth adapter is responsible for the
            hashing primitive — the entity just stores the result.
        scopes: Frozenset of :class:`ApiKeyScope` granted to this key.
            Must be non-empty.
        created_at: When the key was minted (UTC).
        last_used_at: When the key last authenticated a request (UTC, or
            ``None`` if never used). The auth adapter updates this each
            time the key successfully verifies.
        revoked_at: When the key was revoked (UTC, or ``None`` if active).
            A revoked key must not authenticate any request, even if
            ``expires_at`` is in the future.
        expires_at: Optional natural expiry (UTC). ``None`` means the key
            never expires (subject to revocation).

    Raises:
        InvalidApiKeyError: If invariants are violated.
    """

    id: UUID
    user_id: UUID
    clerk_user_id: str
    label: str
    key_hash: str
    scopes: frozenset[ApiKeyScope]
    created_at: datetime
    last_used_at: datetime | None = field(default=None)
    revoked_at: datetime | None = field(default=None)
    expires_at: datetime | None = field(default=None)

    def __post_init__(self) -> None:
        """Validate ApiKey invariants after initialization."""
        if not self.label or not self.label.strip():
            raise InvalidApiKeyError("ApiKey label cannot be empty or whitespace")
        if len(self.label) > 100:
            raise InvalidApiKeyError(
                f"ApiKey label must be at most 100 characters, got {len(self.label)}"
            )
        if not self.key_hash or not self.key_hash.strip():
            raise InvalidApiKeyError("ApiKey key_hash cannot be empty")
        if not self.clerk_user_id or not self.clerk_user_id.strip():
            raise InvalidApiKeyError("ApiKey clerk_user_id cannot be empty")
        if len(self.scopes) == 0:
            raise InvalidApiKeyError("ApiKey must have at least one scope")

        now = datetime.now(UTC)
        created_at_utc = (
            self.created_at
            if self.created_at.tzinfo is not None
            else self.created_at.replace(tzinfo=UTC)
        )
        if created_at_utc > now:
            raise InvalidApiKeyError("ApiKey created_at cannot be in the future")

        # last_used_at, if set, must not predate creation. Otherwise we'd
        # accept obviously-corrupt records — the entity is a defense-in-depth
        # check on what comes back from the DB.
        if self.last_used_at is not None:
            last_used_utc = (
                self.last_used_at
                if self.last_used_at.tzinfo is not None
                else self.last_used_at.replace(tzinfo=UTC)
            )
            if last_used_utc < created_at_utc:
                raise InvalidApiKeyError(
                    "ApiKey last_used_at cannot predate created_at"
                )

        # revoked_at, if set, must not predate creation.
        if self.revoked_at is not None:
            revoked_utc = (
                self.revoked_at
                if self.revoked_at.tzinfo is not None
                else self.revoked_at.replace(tzinfo=UTC)
            )
            if revoked_utc < created_at_utc:
                raise InvalidApiKeyError("ApiKey revoked_at cannot predate created_at")

        # expires_at, if set, must be after created_at — otherwise the key
        # is born expired and we should refuse to persist it.
        if self.expires_at is not None:
            expires_utc = (
                self.expires_at
                if self.expires_at.tzinfo is not None
                else self.expires_at.replace(tzinfo=UTC)
            )
            if expires_utc <= created_at_utc:
                raise InvalidApiKeyError("ApiKey expires_at must be after created_at")

    def is_revoked(self) -> bool:
        """Return True if the key has been explicitly revoked."""
        return self.revoked_at is not None

    def is_expired(self, *, at: datetime | None = None) -> bool:
        """Return True if the key has reached its natural expiry.

        Args:
            at: Reference timestamp (defaults to ``datetime.now(UTC)``).
                Tests pass an explicit value to avoid clock-dependent
                behaviour.
        """
        if self.expires_at is None:
            return False
        check = at if at is not None else datetime.now(UTC)
        check_utc = check if check.tzinfo is not None else check.replace(tzinfo=UTC)
        expires_utc = (
            self.expires_at
            if self.expires_at.tzinfo is not None
            else self.expires_at.replace(tzinfo=UTC)
        )
        return check_utc >= expires_utc

    def is_active(self, *, at: datetime | None = None) -> bool:
        """Return True if the key is neither revoked nor expired."""
        return not self.is_revoked() and not self.is_expired(at=at)

    def has_scope(self, scope: ApiKeyScope) -> bool:
        """Return True if the key carries the given scope."""
        return scope in self.scopes

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only — entity identity, not contents."""
        if not isinstance(other, ApiKey):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets."""
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging — never include the hash."""
        return (
            f"ApiKey(id={self.id}, user_id={self.user_id}, label={self.label!r}, "
            f"scopes={sorted(s.value for s in self.scopes)}, "
            f"revoked={self.is_revoked()})"
        )


@dataclass(frozen=True)
class ApiKeyCreationResult:
    """Returned at issuance — the only time the raw key is exposed.

    The caller is responsible for relaying ``raw_key`` to its true owner
    immediately. The server discards the raw key after computing the hash
    on the persisted ``api_key`` record. There is no way to retrieve a
    raw key from a persisted record — a lost key must be revoked and
    re-minted.

    Attributes:
        api_key: The persisted record (hash + metadata).
        raw_key: The plaintext key — present only on this object, only at
            issuance time.
    """

    api_key: ApiKey
    raw_key: str
