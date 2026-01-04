"""Tests for PasswordService."""

import pytest

from papertrade.domain.services.password_service import PasswordService


class TestPasswordService:
    """Tests for PasswordService hashing and verification."""

    def test_hash_password(self) -> None:
        """Should hash a password successfully."""
        password = "SecurePass123!"
        hashed = PasswordService.hash_password(password)

        assert hashed is not None
        assert hashed != password  # Should not be plaintext
        assert hashed.startswith("$2b$")  # Bcrypt hash format

    def test_hash_password_returns_different_hashes(self) -> None:
        """Should generate different hashes for same password (salted)."""
        password = "SecurePass123!"
        hash1 = PasswordService.hash_password(password)
        hash2 = PasswordService.hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_hash_password_with_empty_string_raises_error(self) -> None:
        """Should raise ValueError for empty password."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordService.hash_password("")

    def test_verify_password_with_correct_password(self) -> None:
        """Should return True for correct password."""
        password = "SecurePass123!"
        hashed = PasswordService.hash_password(password)

        assert PasswordService.verify_password(password, hashed) is True

    def test_verify_password_with_incorrect_password(self) -> None:
        """Should return False for incorrect password."""
        password = "SecurePass123!"
        hashed = PasswordService.hash_password(password)

        assert PasswordService.verify_password("WrongPassword", hashed) is False

    def test_verify_password_with_empty_plain_password(self) -> None:
        """Should return False for empty plain password."""
        hashed = PasswordService.hash_password("SecurePass123!")

        assert PasswordService.verify_password("", hashed) is False

    def test_verify_password_with_empty_hashed_password(self) -> None:
        """Should return False for empty hashed password."""
        assert PasswordService.verify_password("SecurePass123!", "") is False

    def test_verify_password_with_both_empty(self) -> None:
        """Should return False when both passwords are empty."""
        assert PasswordService.verify_password("", "") is False

    def test_hash_and_verify_roundtrip(self) -> None:
        """Should hash and verify correctly in roundtrip."""
        passwords = [
            "SimplePassword",
            "Complex!P@ssw0rd#",
            "12345678",
            "a" * 72,  # Maximum password length for bcrypt
        ]

        for password in passwords:
            hashed = PasswordService.hash_password(password)
            assert PasswordService.verify_password(password, hashed) is True
            assert PasswordService.verify_password("wrong", hashed) is False
