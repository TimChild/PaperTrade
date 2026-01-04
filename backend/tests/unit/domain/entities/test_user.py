"""Tests for User entity."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from papertrade.domain.entities.user import InvalidUserError, User


class TestUserConstruction:
    """Tests for User construction and validation."""

    def test_valid_construction(self) -> None:
        """Should create User with valid data."""
        user_id = uuid4()
        email = "user@example.com"
        hashed_password = "$2b$12$..."  # Mock bcrypt hash
        created_at = datetime.now(UTC)

        user = User(
            id=user_id,
            email=email,
            hashed_password=hashed_password,
            created_at=created_at,
            is_active=True,
        )

        assert user.id == user_id
        assert user.email == email
        assert user.hashed_password == hashed_password
        assert user.created_at == created_at
        assert user.is_active is True

    def test_valid_construction_with_inactive_user(self) -> None:
        """Should create User with is_active=False."""
        user = User(
            id=uuid4(),
            email="user@example.com",
            hashed_password="$2b$12$...",
            created_at=datetime.now(UTC),
            is_active=False,
        )
        assert user.is_active is False

    def test_valid_construction_defaults_to_active(self) -> None:
        """Should default is_active to True if not provided."""
        user = User(
            id=uuid4(),
            email="user@example.com",
            hashed_password="$2b$12$...",
            created_at=datetime.now(UTC),
        )
        assert user.is_active is True

    def test_invalid_construction_with_empty_email(self) -> None:
        """Should raise error for empty email."""
        with pytest.raises(InvalidUserError, match="email cannot be empty"):
            User(
                id=uuid4(),
                email="",
                hashed_password="$2b$12$...",
                created_at=datetime.now(UTC),
            )

    def test_invalid_construction_with_empty_password(self) -> None:
        """Should raise error for empty hashed_password."""
        with pytest.raises(InvalidUserError, match="hashed_password cannot be empty"):
            User(
                id=uuid4(),
                email="user@example.com",
                hashed_password="",
                created_at=datetime.now(UTC),
            )

    def test_invalid_construction_with_whitespace_password(self) -> None:
        """Should raise error for whitespace-only hashed_password."""
        with pytest.raises(InvalidUserError, match="hashed_password cannot be empty"):
            User(
                id=uuid4(),
                email="user@example.com",
                hashed_password="   ",
                created_at=datetime.now(UTC),
            )

    def test_invalid_construction_with_future_created_at(self) -> None:
        """Should raise error for created_at in the future."""
        future_time = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(InvalidUserError, match="cannot be in the future"):
            User(
                id=uuid4(),
                email="user@example.com",
                hashed_password="$2b$12$...",
                created_at=future_time,
            )


class TestUserEquality:
    """Tests for User equality and hashing."""

    def test_equality_based_on_id(self) -> None:
        """Should compare Users by ID only."""
        user_id = uuid4()
        user1 = User(
            id=user_id,
            email="user1@example.com",
            hashed_password="hash1",
            created_at=datetime.now(UTC),
        )
        user2 = User(
            id=user_id,
            email="user2@example.com",
            hashed_password="hash2",
            created_at=datetime.now(UTC),
        )

        assert user1 == user2

    def test_inequality_for_different_ids(self) -> None:
        """Should not equal Users with different IDs."""
        user1 = User(
            id=uuid4(),
            email="user@example.com",
            hashed_password="hash1",
            created_at=datetime.now(UTC),
        )
        user2 = User(
            id=uuid4(),
            email="user@example.com",
            hashed_password="hash1",
            created_at=datetime.now(UTC),
        )

        assert user1 != user2

    def test_inequality_with_non_user(self) -> None:
        """Should not equal non-User objects."""
        user = User(
            id=uuid4(),
            email="user@example.com",
            hashed_password="hash1",
            created_at=datetime.now(UTC),
        )

        assert user != "not a user"
        assert user != 123
        assert user != None

    def test_hash_based_on_id(self) -> None:
        """Should hash based on ID only."""
        user_id = uuid4()
        user1 = User(
            id=user_id,
            email="user1@example.com",
            hashed_password="hash1",
            created_at=datetime.now(UTC),
        )
        user2 = User(
            id=user_id,
            email="user2@example.com",
            hashed_password="hash2",
            created_at=datetime.now(UTC),
        )

        assert hash(user1) == hash(user2)

    def test_can_be_used_in_set(self) -> None:
        """Should be usable in sets based on ID."""
        user_id = uuid4()
        user1 = User(
            id=user_id,
            email="user1@example.com",
            hashed_password="hash1",
            created_at=datetime.now(UTC),
        )
        user2 = User(
            id=user_id,
            email="user2@example.com",
            hashed_password="hash2",
            created_at=datetime.now(UTC),
        )

        user_set = {user1, user2}
        assert len(user_set) == 1


class TestUserImmutability:
    """Tests for User immutability."""

    def test_user_is_frozen(self) -> None:
        """Should not allow modification of User attributes."""
        user = User(
            id=uuid4(),
            email="user@example.com",
            hashed_password="$2b$12$...",
            created_at=datetime.now(UTC),
        )

        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            user.email = "new@example.com"  # type: ignore[misc]

        with pytest.raises(Exception):
            user.is_active = False  # type: ignore[misc]


class TestUserRepr:
    """Tests for User string representation."""

    def test_repr_includes_key_info(self) -> None:
        """Should include ID, email, and is_active in repr."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email="user@example.com",
            hashed_password="$2b$12$...",
            created_at=datetime.now(UTC),
            is_active=True,
        )

        repr_str = repr(user)
        assert str(user_id) in repr_str
        assert "user@example.com" in repr_str
        assert "is_active=True" in repr_str
