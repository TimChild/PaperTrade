"""SQLModel persistence model for ApiKey.

The model lives alongside the other DB models but in its own file so the
auth domain doesn't pollute :mod:`zebu.adapters.outbound.database.models`.
There is intentionally no FK from ``api_keys.user_id`` to a users table:
``user_id`` is a Clerk-derived deterministic UUID and Clerk owns the
authoritative user record, so the local DB has nothing to FK against.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import JSON, Column, Field, Index, SQLModel

from zebu.domain.entities.api_key import ApiKey
from zebu.domain.value_objects.api_key_scope import ApiKeyScope


class ApiKeyModel(SQLModel, table=True):
    """Database model for the :class:`ApiKey` domain entity.

    Fields mirror the entity. Scopes are stored as a JSON array of strings
    so adding a new :class:`ApiKeyScope` value doesn't require a migration.
    The ``key_hash`` column has a unique constraint and an index — every
    auth request goes through ``get_by_hash``, so this is the hot path.

    Attributes:
        id: Primary key (UUID).
        user_id: Owner UUID (deterministic from Clerk user ID, not FK'd).
        clerk_user_id: The original Clerk user-id string captured at
            issuance. Returned on ``AuthenticatedUser.id`` so existing
            ownership checks keep working.
        label: Human-readable label.
        key_hash: HMAC-SHA256 hash of the raw key (hex). Unique-indexed.
        scopes: JSON array of :class:`ApiKeyScope` values.
        created_at: When the key was minted.
        last_used_at: Last successful auth timestamp (nullable).
        revoked_at: Revocation timestamp (nullable).
        expires_at: Natural expiry (nullable).
    """

    __tablename__ = "api_keys"  # type: ignore[assignment]
    __table_args__ = (
        Index("idx_api_key_user_id", "user_id"),
        Index("idx_api_key_hash", "key_hash", unique=True),
    )

    id: UUID = Field(primary_key=True)
    user_id: UUID = Field(index=True)
    clerk_user_id: str = Field(max_length=255)
    label: str = Field(max_length=100)
    key_hash: str = Field(max_length=128)
    scopes: list[str] = Field(  # type: ignore[assignment]  # SQLModel + JSON column needs sa_column override
        sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime
    last_used_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)

    def to_domain(self) -> ApiKey:
        """Convert database model to domain entity.

        Returns:
            ApiKey domain entity with timezone-aware UTC timestamps.

        Raises:
            ValueError: If a stored scope string is not a known
                :class:`ApiKeyScope` value (suggests rolling back a scope
                addition without migrating data).
        """
        scopes = frozenset(ApiKeyScope(scope) for scope in self.scopes)

        # Database stores naive UTC datetimes — re-attach UTC tzinfo.
        created_at_utc = self.created_at.replace(tzinfo=UTC)
        last_used_at_utc = (
            self.last_used_at.replace(tzinfo=UTC)
            if self.last_used_at is not None
            else None
        )
        revoked_at_utc = (
            self.revoked_at.replace(tzinfo=UTC) if self.revoked_at is not None else None
        )
        expires_at_utc = (
            self.expires_at.replace(tzinfo=UTC) if self.expires_at is not None else None
        )

        return ApiKey(
            id=self.id,
            user_id=self.user_id,
            clerk_user_id=self.clerk_user_id,
            label=self.label,
            key_hash=self.key_hash,
            scopes=scopes,
            created_at=created_at_utc,
            last_used_at=last_used_at_utc,
            revoked_at=revoked_at_utc,
            expires_at=expires_at_utc,
        )

    @classmethod
    def from_domain(cls, api_key: ApiKey) -> "ApiKeyModel":
        """Convert domain entity to database model.

        Args:
            api_key: Domain entity to persist.

        Returns:
            ApiKeyModel ready for insert/update.
        """

        def _strip_tz(value: datetime | None) -> datetime | None:
            if value is None:
                return None
            if value.tzinfo is None:
                return value
            return value.astimezone(UTC).replace(tzinfo=None)

        return cls(
            id=api_key.id,
            user_id=api_key.user_id,
            clerk_user_id=api_key.clerk_user_id,
            label=api_key.label,
            key_hash=api_key.key_hash,
            scopes=sorted(scope.value for scope in api_key.scopes),
            created_at=_strip_tz(api_key.created_at) or api_key.created_at,
            last_used_at=_strip_tz(api_key.last_used_at),
            revoked_at=_strip_tz(api_key.revoked_at),
            expires_at=_strip_tz(api_key.expires_at),
        )
