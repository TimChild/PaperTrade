"""Tests for JWTService."""

from datetime import timedelta
from uuid import uuid4

import pytest

from papertrade.application.services.jwt_service import JWTService
from papertrade.domain.exceptions import InvalidTokenError


@pytest.fixture
def jwt_service():
    """Provide JWT service with test secret key."""
    return JWTService(secret_key="test-secret-key-for-testing-only")


class TestJWTService:
    """Tests for JWT service token operations."""

    def test_create_access_token(self, jwt_service):
        """Test creating an access token."""
        user_id = uuid4()
        token = jwt_service.create_access_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, jwt_service):
        """Test creating a refresh token."""
        user_id = uuid4()
        token = jwt_service.create_refresh_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self, jwt_service):
        """Test decoding a valid token."""
        user_id = uuid4()
        token = jwt_service.create_access_token(user_id)

        payload = jwt_service.decode_token(token)

        assert payload is not None
        assert "sub" in payload
        assert "exp" in payload
        assert payload["sub"] == str(user_id)

    def test_decode_invalid_token_raises_error(self, jwt_service):
        """Test that decoding invalid token raises InvalidTokenError."""
        invalid_token = "invalid.token.here"

        with pytest.raises(InvalidTokenError):
            jwt_service.decode_token(invalid_token)

    def test_decode_expired_token_raises_error(self, jwt_service):
        """Test that decoding expired token raises InvalidTokenError."""
        user_id = uuid4()
        # Create token that expires immediately
        token = jwt_service.create_access_token(
            user_id, expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(InvalidTokenError, match="expired"):
            jwt_service.decode_token(token)

    def test_get_user_id_from_token(self, jwt_service):
        """Test extracting user ID from token."""
        user_id = uuid4()
        token = jwt_service.create_access_token(user_id)

        extracted_id = jwt_service.get_user_id_from_token(token)

        assert extracted_id == user_id

    def test_get_user_id_from_invalid_token_raises_error(self, jwt_service):
        """Test that extracting user ID from invalid token raises error."""
        with pytest.raises(InvalidTokenError):
            jwt_service.get_user_id_from_token("invalid.token")

    def test_access_and_refresh_tokens_have_different_types(self, jwt_service):
        """Test that access and refresh tokens have different type claims."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id)
        refresh_token = jwt_service.create_refresh_token(user_id)

        access_payload = jwt_service.decode_token(access_token)
        refresh_payload = jwt_service.decode_token(refresh_token)

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_tokens_from_different_users_are_different(self, jwt_service):
        """Test that tokens for different users are different."""
        user1_id = uuid4()
        user2_id = uuid4()

        token1 = jwt_service.create_access_token(user1_id)
        token2 = jwt_service.create_access_token(user2_id)

        assert token1 != token2

        payload1 = jwt_service.decode_token(token1)
        payload2 = jwt_service.decode_token(token2)

        assert payload1["sub"] == str(user1_id)
        assert payload2["sub"] == str(user2_id)

    def test_empty_secret_key_raises_error(self):
        """Test that empty secret key raises ValueError."""
        with pytest.raises(ValueError, match="secret_key cannot be empty"):
            JWTService(secret_key="")

    def test_custom_expiration_times(self):
        """Test creating service with custom expiration times."""
        service = JWTService(
            secret_key="test-key",
            access_token_expire_minutes=30,
            refresh_token_expire_days=14,
        )

        assert service.access_token_expire_minutes == 30
        assert service.refresh_token_expire_days == 14
