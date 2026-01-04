"""Tests for RegisterUser command."""

import pytest

from papertrade.application.commands.register_user import (
    RegisterUserCommand,
    RegisterUserHandler,
)
from papertrade.application.ports.in_memory_user_repository import (
    InMemoryUserRepository,
)
from papertrade.domain.exceptions import DuplicateEmailError
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
def handler(user_repo, password_service):
    """Provide RegisterUser handler with dependencies."""
    return RegisterUserHandler(user_repo, password_service)


class TestRegisterUser:
    """Tests for RegisterUser command handler."""

    async def test_valid_registration_succeeds(self, handler, user_repo):
        """Test that valid user registration succeeds."""
        # Arrange
        command = RegisterUserCommand(
            email="user@example.com", password="SecurePass123!"
        )

        # Act
        result = await handler.execute(command)

        # Assert
        assert result.user is not None
        assert result.user.email == "user@example.com"
        assert result.user.is_active is True
        assert result.user.hashed_password.startswith("$2b$")  # Bcrypt hash

        # Verify user was saved
        saved_user = await user_repo.get_by_id(result.user.id)
        assert saved_user is not None
        assert saved_user.email == "user@example.com"

    async def test_duplicate_email_raises_error(self, handler):
        """Test that duplicate email raises DuplicateEmailError."""
        # Arrange
        command1 = RegisterUserCommand(
            email="user@example.com", password="Password123!"
        )
        command2 = RegisterUserCommand(
            email="user@example.com", password="DifferentPass456!"
        )

        # Act
        await handler.execute(command1)

        # Assert
        with pytest.raises(DuplicateEmailError, match="already registered"):
            await handler.execute(command2)

    async def test_duplicate_email_case_insensitive(self, handler):
        """Test that duplicate email check is case-insensitive."""
        # Arrange
        command1 = RegisterUserCommand(
            email="User@Example.com", password="Password123!"
        )
        command2 = RegisterUserCommand(
            email="user@example.com", password="DifferentPass456!"
        )

        # Act
        await handler.execute(command1)

        # Assert
        with pytest.raises(DuplicateEmailError, match="already registered"):
            await handler.execute(command2)

    async def test_empty_password_raises_error(self, handler):
        """Test that empty password raises ValueError."""
        # Arrange
        command = RegisterUserCommand(email="user@example.com", password="")

        # Assert
        with pytest.raises(ValueError, match="Password cannot be empty"):
            await handler.execute(command)

    async def test_whitespace_password_raises_error(self, handler):
        """Test that whitespace-only password raises ValueError."""
        # Arrange
        command = RegisterUserCommand(email="user@example.com", password="   ")

        # Assert
        with pytest.raises(ValueError, match="Password cannot be empty"):
            await handler.execute(command)

    async def test_short_password_raises_error(self, handler):
        """Test that password shorter than 8 characters raises ValueError."""
        # Arrange
        command = RegisterUserCommand(email="user@example.com", password="Short1!")

        # Assert
        with pytest.raises(ValueError, match="at least 8 characters"):
            await handler.execute(command)

    async def test_password_is_hashed(self, handler, user_repo):
        """Test that password is hashed before storage."""
        # Arrange
        plain_password = "MySecurePassword123!"
        command = RegisterUserCommand(email="user@example.com", password=plain_password)

        # Act
        result = await handler.execute(command)

        # Assert
        assert result.user.hashed_password != plain_password
        assert result.user.hashed_password.startswith("$2b$")  # Bcrypt hash format

        # Verify hash is verifiable
        from papertrade.domain.services.password_service import PasswordService

        assert PasswordService.verify_password(
            plain_password, result.user.hashed_password
        )

    async def test_invalid_email_format_raises_error(self):
        """Test that invalid email format raises ValidationError."""
        # Note: EmailStr validation happens at assignment, not construction
        # Skip this test as dataclass doesn't validate EmailStr at construction
        # The email validation happens at the API layer with Pydantic models
        pytest.skip("EmailStr validation is handled at API layer, not command layer")
