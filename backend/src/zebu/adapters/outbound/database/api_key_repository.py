"""SQLModel implementation of ApiKeyRepository."""

from uuid import UUID

from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.domain.entities.api_key import ApiKey


class SQLModelApiKeyRepository:
    """SQLModel implementation of :class:`ApiKeyRepository`.

    Persists :class:`ApiKey` records via the SQLModel ORM. The hot path
    (``get_by_hash``) goes through the ``idx_api_key_hash`` unique index.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session for this unit of work.
        """
        self._session = session

    async def save(self, api_key: ApiKey) -> None:
        """Persist (upsert) an API key.

        On update, every mutable field is overwritten — the entity is
        small and this avoids surprising partial updates.

        Args:
            api_key: The persisted record to save.
        """
        existing = await self._session.get(ApiKeyModel, api_key.id)

        new_model = ApiKeyModel.from_domain(api_key)
        if existing is None:
            self._session.add(new_model)
            return

        existing.user_id = new_model.user_id
        existing.clerk_user_id = new_model.clerk_user_id
        existing.label = new_model.label
        existing.key_hash = new_model.key_hash
        existing.scopes = new_model.scopes
        existing.created_at = new_model.created_at
        existing.last_used_at = new_model.last_used_at
        existing.revoked_at = new_model.revoked_at
        existing.expires_at = new_model.expires_at
        self._session.add(existing)

    async def get(self, api_key_id: UUID) -> ApiKey | None:
        """Retrieve a single API key by ID.

        Args:
            api_key_id: Unique key identifier.

        Returns:
            ApiKey if found, ``None`` otherwise.
        """
        model = await self._session.get(ApiKeyModel, api_key_id)
        if model is None:
            return None
        return model.to_domain()

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Retrieve an API key by its hash (auth-path hot lookup).

        Args:
            key_hash: Deterministic hash of the raw key.

        Returns:
            ApiKey if a record matches, ``None`` otherwise.
        """
        statement = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        result = await self._session.exec(statement)
        model = result.first()
        if model is None:
            return None
        return model.to_domain()

    async def get_by_user(self, user_id: UUID) -> list[ApiKey]:
        """Retrieve all API keys owned by a user, oldest first.

        Args:
            user_id: Owner UUID.

        Returns:
            List of ApiKey records (may be empty).
        """
        statement = (
            select(ApiKeyModel)
            .where(ApiKeyModel.user_id == user_id)
            .order_by(ApiKeyModel.created_at.asc())  # type: ignore[attr-defined]  # SQLModel field has SQLAlchemy column methods
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def delete(self, api_key_id: UUID) -> None:
        """Hard-delete an API key record.

        Args:
            api_key_id: Unique key identifier.
        """
        statement = delete(ApiKeyModel).where(
            ApiKeyModel.id == api_key_id  # type: ignore[arg-type]  # SQLModel field comparison returns column expression
        )
        await self._session.exec(statement)
