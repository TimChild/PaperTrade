"""Clerk authentication adapter.

Implements AuthPort using Clerk's backend SDK for production authentication.
"""

import logging

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions, AuthStatus

from papertrade.application.ports.auth_port import AuthenticatedUser, AuthPort
from papertrade.domain.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)


class SimpleRequest:
    """Simple request object for Clerk's authenticate_request method.

    Clerk's SDK expects a request object with a headers dictionary.
    Both lowercase and capitalized Authorization headers are needed because
    Clerk's backend SDK checks both header casings for compatibility with
    different frameworks and environments.
    """

    def __init__(self, token: str) -> None:
        """Initialize request with Authorization header.

        Args:
            token: JWT token from the Authorization header
        """
        self.headers = {
            "authorization": f"Bearer {token}",
            "Authorization": f"Bearer {token}",  # Clerk checks both casings
        }


class ClerkAuthAdapter(AuthPort):
    """Clerk implementation of AuthPort.

    Integrates with Clerk's authentication service to verify JWT tokens
    and retrieve user information. This adapter handles the translation
    between Clerk's API and our application's authentication port.

    Attributes:
        _clerk: Clerk SDK client instance
    """

    def __init__(self, secret_key: str) -> None:
        """Initialize Clerk adapter with API credentials.

        Args:
            secret_key: Clerk secret key for backend API authentication
        """
        self._clerk = Clerk(bearer_auth=secret_key)

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify JWT token and return authenticated user.

        Uses Clerk's SDK to verify the JWT token and extract user information.
        The token should be a valid Clerk session token.

        Args:
            token: JWT token from the Authorization header

        Returns:
            AuthenticatedUser: Verified user identity

        Raises:
            InvalidTokenError: If token is invalid, expired, or verification fails
        """
        try:
            # Create a request object with the token
            request = SimpleRequest(token)

            # Authenticate the request using Clerk's SDK
            # Note: This is synchronous but we use async signature for port consistency
            request_state = self._clerk.authenticate_request(
                request=request, options=AuthenticateRequestOptions()
            )

            logger.info(f"Clerk auth status: {request_state.status}")

            # Check if authentication was successful
            if request_state.status != AuthStatus.SIGNED_IN:
                logger.warning(
                    f"Auth failed: status={request_state.status}, "
                    f"reason={request_state.reason}"
                )
                raise InvalidTokenError(
                    f"Authentication failed: {request_state.reason}"
                )

            # Extract user ID from JWT payload (not from request_state.user_id)
            if not request_state.payload:
                raise InvalidTokenError("Token payload is missing")

            user_id = request_state.payload.get("sub")
            if not user_id:
                raise InvalidTokenError(
                    "User ID (sub claim) not found in token payload"
                )

            logger.info(f"Authenticated user ID: {user_id}")

            # Get full user details from Clerk
            user = self._clerk.users.get(user_id=user_id)

            # Extract email (take first email address)
            email = ""
            if user.email_addresses and len(user.email_addresses) > 0:
                email = user.email_addresses[0].email_address

            return AuthenticatedUser(
                id=user.id,
                email=email,
            )
        except InvalidTokenError:
            # Re-raise our domain exception
            raise
        except Exception as e:
            # Convert any Clerk SDK exceptions to our domain exception
            logger.error(f"Token verification failed: {str(e)}", exc_info=True)
            raise InvalidTokenError(f"Token verification failed: {str(e)}") from e

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        """Get user by ID.

        Retrieves user information from Clerk by user ID.

        Args:
            user_id: Clerk user ID

        Returns:
            AuthenticatedUser if found, None otherwise
        """
        try:
            user = self._clerk.users.get(user_id=user_id)

            # Extract email (take first email address)
            email = ""
            if user.email_addresses and len(user.email_addresses) > 0:
                email = user.email_addresses[0].email_address

            return AuthenticatedUser(
                id=user.id,
                email=email,
            )
        except Exception:
            # User not found or other error
            return None
