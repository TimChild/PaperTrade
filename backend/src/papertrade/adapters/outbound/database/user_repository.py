"""SQLModel implementation of UserRepository.

Provides user persistence using SQLModel ORM with SQLite/PostgreSQL.
"""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from papertrade.adapters.outbound.database.models import UserModel
from papertrade.domain.entities.user import User
from papertrade.domain.exceptions import DuplicateEmailError, UserNotFoundError


class SQLModelUserRepository:
    """SQLModel implementation of UserRepository protocol.

    Uses SQLModel ORM for database operations with unique constraint support.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session for this unit of work
        """
        self._session = session

    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User entity to create

        Returns:
            Created User entity

        Raises:
            DuplicateEmailError: If email already exists
        """
        model = UserModel.from_domain(user)
        self._session.add(model)

        try:
            await self._session.flush()
        except IntegrityError as e:
            # Unique constraint violation on email
            raise DuplicateEmailError(
                f"Email {user.email} is already registered"
            ) from e

        return model.to_domain()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a single user by ID.

        Args:
            user_id: Unique identifier of the user

        Returns:
            User entity if found, None if not found
        """
        result = await self._session.get(UserModel, user_id)
        if result is None:
            return None
        return result.to_domain()

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a single user by email (case-insensitive).

        Args:
            email: Email address of the user

        Returns:
            User entity if found, None if not found
        """
        statement = select(UserModel).where(
            UserModel.email.ilike(email)  # type: ignore[attr-defined]  # SQLModel field has SQLAlchemy column methods
        )
        result = await self._session.exec(statement)
        model = result.first()
        if model is None:
            return None
        return model.to_domain()

    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: User entity with updated data

        Returns:
            Updated User entity

        Raises:
            UserNotFoundError: If user does not exist
            DuplicateEmailError: If email change conflicts with existing email
        """
        # Check if user exists
        existing = await self._session.get(UserModel, user.id)
        if existing is None:
            raise UserNotFoundError(f"User {user.id} not found")

        # Update fields
        existing.email = user.email
        existing.hashed_password = user.hashed_password
        existing.is_active = user.is_active

        try:
            await self._session.flush()
        except IntegrityError as e:
            # Unique constraint violation on email
            raise DuplicateEmailError(
                f"Email {user.email} is already registered"
            ) from e

        return existing.to_domain()

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists (case-insensitive).

        Args:
            email: Email address to check

        Returns:
            True if user exists, False otherwise
        """
        statement = select(UserModel).where(
            UserModel.email.ilike(email)  # type: ignore[attr-defined]
        )
        result = await self._session.exec(statement)
        return result.first() is not None
