"""Password service for hashing and verifying passwords.

This is a domain service that encapsulates password security logic.
It uses bcrypt for secure password hashing with a cost factor of 12.
"""

import bcrypt


class PasswordService:
    """Domain service for password hashing and verification.

    This service provides secure password operations using bcrypt.
    Passwords are never stored in plaintext.

    Methods:
        hash_password: Hash a plaintext password
        verify_password: Verify a plaintext password against a hash
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plaintext password to hash

        Returns:
            Bcrypt hash string

        Raises:
            ValueError: If password is empty
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Hash password with bcrypt (rounds=12 for strong security)
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            plain_password: Plaintext password to verify
            hashed_password: Bcrypt hash to verify against

        Returns:
            True if password matches hash, False otherwise
        """
        if not plain_password or not hashed_password:
            return False

        try:
            password_bytes = plain_password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            # Invalid hash format or other error
            return False
