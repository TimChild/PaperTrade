"""JWT service for token generation and validation.

This is an application service that handles JWT token operations.
It uses python-jose for JWT encoding/decoding with HS256 algorithm.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt

from papertrade.domain.exceptions import InvalidTokenError


class JWTService:
    """Application service for JWT token generation and validation.

    This service provides secure JWT operations for authentication.
    Access tokens are short-lived (15 minutes), refresh tokens are longer-lived (7 days).

    Attributes:
        secret_key: Secret key for JWT signing (from environment)
        algorithm: JWT algorithm (default: HS256)
        access_token_expire_minutes: Access token expiry time
        refresh_token_expire_days: Refresh token expiry time
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """Initialize JWT service.

        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiry in minutes
            refresh_token_expire_days: Refresh token expiry in days

        Raises:
            ValueError: If secret_key is empty
        """
        if not secret_key:
            raise ValueError("JWT secret_key cannot be empty")
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self, user_id: UUID, expires_delta: timedelta | None = None
    ) -> str:
        """Generate an access token for a user.

        Args:
            user_id: User's unique identifier
            expires_delta: Optional custom expiration time

        Returns:
            JWT access token string

        Raises:
            ValueError: If user_id is invalid
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        expire = datetime.now(UTC) + expires_delta
        to_encode = {
            "sub": str(user_id),  # Subject: user ID
            "exp": expire,  # Expiration time
            "type": "access",  # Token type
        }
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self, user_id: UUID, expires_delta: timedelta | None = None
    ) -> str:
        """Generate a refresh token for a user.

        Args:
            user_id: User's unique identifier
            expires_delta: Optional custom expiration time

        Returns:
            JWT refresh token string

        Raises:
            ValueError: If user_id is invalid
        """
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_expire_days)

        expire = datetime.now(UTC) + expires_delta
        to_encode = {
            "sub": str(user_id),  # Subject: user ID
            "exp": expire,  # Expiration time
            "type": "refresh",  # Token type
        }
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, str]:
        """Decode and validate a JWT token.

        Args:
            token: JWT token string to decode

        Returns:
            Decoded token payload as dictionary

        Raises:
            InvalidTokenError: If token is invalid, expired, or malformed
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise InvalidTokenError(f"Invalid or expired token: {e}") from e

    def get_user_id_from_token(self, token: str) -> UUID:
        """Extract user ID from a JWT token.

        Args:
            token: JWT token string

        Returns:
            User UUID from token's 'sub' claim

        Raises:
            InvalidTokenError: If token is invalid or missing user ID
        """
        payload = self.decode_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise InvalidTokenError("Token missing user ID (sub claim)")

        try:
            return UUID(user_id_str)
        except ValueError as e:
            raise InvalidTokenError(f"Invalid user ID in token: {user_id_str}") from e
