"""Tests for LoginUser command."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from papertrade.application.commands.login_user import LoginUserCommand, LoginUserHandler
from papertrade.application.ports.in_memory_user_repository import (
    InMemoryUserRepository,
)
from papertrade.application.services.jwt_service import JWTService
from papertrade.domain.entities.user import User
from papertrade.domain.exceptions import InactiveUserError, InvalidCredentialsError
from papertrade.domain.services.password_service import PasswordService


@pytest.fixture
def user_repo():
    """Provide clean in-memory user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def password_service():
    """Provide password service."""
    return PasswordService()


@pytest.fixture
def jwt_service():
    """Provide JWT service."""
    return JWTService(secret_key="test-secret-key-for-testing")


@pytest.fixture
def handler(user_repo, password_service, jwt_service):
    """Provide LoginUser handler with dependencies."""
    return LoginUserHandler(user_repo, password_service, jwt_service)


@pytest.fixture
async def active_user(user_repo, password_service):
    """Create and save an active user."""
    user = User(
        id=uuid4(),
        email="user@example.com",
        hashed_password=password_service.hash_password("Password123!"),
        created_at=datetime.now(UTC),
        is_active=True,
    )
    await user_repo.create(user)
    return user


@pytest.fixture
async def inactive_user(user_repo, password_service):
    """Create and save an inactive user."""
    user = User(
        id=uuid4(),
        email="inactive@example.com",
        hashed_password=password_service.hash_password("Password123!"),
        created_at=datetime.now(UTC),
        is_active=False,
    )
    await user_repo.create(user)
    return user


class TestLoginUser:
    """Tests for LoginUser command handler."""

    async def test_valid_login_succeeds(self, handler, active_user):
        """Test that valid login succeeds and returns tokens."""
        # Arrange
        command = LoginUserCommand(email="user@example.com", password="Password123!")

        # Act
        result = await handler.execute(command)

        # Assert
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.token_type == "Bearer"
        assert len(result.access_token) > 0
        assert len(result.refresh_token) > 0

    async def test_login_is_case_insensitive(self, handler, active_user):
        """Test that email lookup is case-insensitive."""
        # Arrange
        command = LoginUserCommand(
            email="USER@EXAMPLE.COM", password="Password123!"
        )

        # Act
        result = await handler.execute(command)

        # Assert
        assert result.access_token is not None

    async def test_incorrect_email_raises_error(self, handler, active_user):
        """Test that incorrect email raises InvalidCredentialsError."""
        # Arrange
        command = LoginUserCommand(
            email="wrong@example.com", password="Password123!"
        )

        # Assert
        with pytest.raises(InvalidCredentialsError, match="Incorrect email or password"):
            await handler.execute(command)

    async def test_incorrect_password_raises_error(self, handler, active_user):
        """Test that incorrect password raises InvalidCredentialsError."""
        # Arrange
        command = LoginUserCommand(email="user@example.com", password="WrongPassword!")

        # Assert
        with pytest.raises(InvalidCredentialsError, match="Incorrect email or password"):
            await handler.execute(command)

    async def test_inactive_user_cannot_login(self, handler, inactive_user):
        """Test that inactive user cannot login."""
        # Arrange
        command = LoginUserCommand(
            email="inactive@example.com", password="Password123!"
        )

        # Assert
        with pytest.raises(InactiveUserError, match="inactive"):
            await handler.execute(command)

    async def test_tokens_are_different(self, handler, active_user):
        """Test that access and refresh tokens are different."""
        # Arrange
        command = LoginUserCommand(email="user@example.com", password="Password123!")

        # Act
        result = await handler.execute(command)

        # Assert
        assert result.access_token != result.refresh_token

    async def test_tokens_contain_user_id(
        self, handler, active_user, jwt_service
    ):
        """Test that tokens contain the correct user ID."""
        # Arrange
        command = LoginUserCommand(email="user@example.com", password="Password123!")

        # Act
        result = await handler.execute(command)

        # Assert - decode tokens and check user ID
        access_payload = jwt_service.decode_token(result.access_token)
        refresh_payload = jwt_service.decode_token(result.refresh_token)

        assert access_payload["sub"] == str(active_user.id)
        assert refresh_payload["sub"] == str(active_user.id)
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
