"""GetUser query - Retrieve user details."""

from dataclasses import dataclass
from uuid import UUID

from papertrade.application.ports.user_repository import UserRepository
from papertrade.domain.entities.user import User
from papertrade.domain.exceptions import UserNotFoundError


@dataclass(frozen=True)
class GetUserQuery:
    """Input data for retrieving a user.

    Attributes:
        user_id: User to retrieve
    """

    user_id: UUID


@dataclass(frozen=True)
class GetUserResult:
    """Result of retrieving a user.

    Attributes:
        user: User entity
    """

    user: User


class GetUserHandler:
    """Handler for GetUser query.

    Retrieves user details by ID.
    """

    def __init__(self, user_repository: UserRepository) -> None:
        """Initialize handler with repository dependency.

        Args:
            user_repository: Repository for user persistence
        """
        self._user_repository = user_repository

    async def execute(self, query: GetUserQuery) -> GetUserResult:
        """Execute the GetUser query.

        Args:
            query: Query with user_id

        Returns:
            Result containing user entity

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        user = await self._user_repository.get_by_id(query.user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {query.user_id}")

        return GetUserResult(user=user)
