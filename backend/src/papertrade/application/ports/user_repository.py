"""User repository port (interface).

Defines the contract for user persistence operations. Adapters implement
this interface to provide actual storage mechanisms (SQLModel, InMemory, etc.).
"""

from typing import Protocol
from uuid import UUID

from papertrade.domain.entities.user import User


class UserRepository(Protocol):
    """Interface for user persistence operations.

    This port follows the Repository pattern, abstracting persistence details
    from the application layer. Implementations can use any storage mechanism.
    """

    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User entity to create

        Returns:
            Created User entity

        Raises:
            DuplicateEmailError: If email already exists
            RepositoryError: If database connection or query fails
        """
        ...

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a single user by ID.

        Args:
            user_id: Unique identifier of the user

        Returns:
            User entity if found, None if not found

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a single user by email (case-insensitive).

        Args:
            email: Email address of the user

        Returns:
            User entity if found, None if not found

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: User entity with updated data

        Returns:
            Updated User entity

        Raises:
            UserNotFoundError: If user does not exist
            RepositoryError: If database connection or query fails
        """
        ...

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists (case-insensitive).

        Args:
            email: Email address to check

        Returns:
            True if user exists, False otherwise

        Raises:
            RepositoryError: If database connection fails
        """
        ...
