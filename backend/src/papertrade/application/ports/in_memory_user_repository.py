"""In-memory implementation of UserRepository for testing.

Provides fast, thread-safe in-memory storage suitable for unit testing.
No persistence between test runs.
"""

from threading import Lock
from uuid import UUID

from papertrade.domain.entities.user import User
from papertrade.domain.exceptions import DuplicateEmailError, UserNotFoundError


class InMemoryUserRepository:
    """In-memory implementation of UserRepository protocol.

    Uses Python dictionaries for O(1) access. Thread-safe with locks.
    Suitable for unit testing without database setup.
    """

    def __init__(self) -> None:
        """Initialize empty user storage."""
        self._users: dict[UUID, User] = {}
        self._emails: dict[str, UUID] = {}  # email -> user_id mapping
        self._lock = Lock()

    async def create(self, user: User) -> User:
        """Create a new user."""
        with self._lock:
            # Check for duplicate email (case-insensitive)
            email_lower = user.email.lower()
            if email_lower in self._emails:
                raise DuplicateEmailError(f"Email {user.email} is already registered")

            # Store user and email mapping
            self._users[user.id] = user
            self._emails[email_lower] = user.id
            return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a user by ID."""
        with self._lock:
            return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by email (case-insensitive)."""
        with self._lock:
            email_lower = email.lower()
            user_id = self._emails.get(email_lower)
            if user_id is None:
                return None
            return self._users.get(user_id)

    async def update(self, user: User) -> User:
        """Update an existing user."""
        with self._lock:
            if user.id not in self._users:
                raise UserNotFoundError(f"User {user.id} not found")

            # Get old user to check if email changed
            old_user = self._users[user.id]
            old_email_lower = old_user.email.lower()
            new_email_lower = user.email.lower()

            # If email changed, update email mapping
            if old_email_lower != new_email_lower:
                # Check if new email is already taken
                if new_email_lower in self._emails:
                    raise DuplicateEmailError(
                        f"Email {user.email} is already registered"
                    )
                # Remove old email mapping
                del self._emails[old_email_lower]
                # Add new email mapping
                self._emails[new_email_lower] = user.id

            # Update user
            self._users[user.id] = user
            return user

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists (case-insensitive)."""
        with self._lock:
            email_lower = email.lower()
            return email_lower in self._emails

    def clear(self) -> None:
        """Clear all users (for testing)."""
        with self._lock:
            self._users.clear()
            self._emails.clear()
