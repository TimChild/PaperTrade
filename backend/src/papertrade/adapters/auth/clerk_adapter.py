"""Clerk authentication adapter.

Implements AuthPort using Clerk's backend SDK for production authentication.
"""

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions

from papertrade.application.ports.auth_port import AuthenticatedUser, AuthPort
from papertrade.domain.exceptions import InvalidTokenError


class SimpleRequest:
    """Simple request object for Clerk authentication.

    Clerk's authenticate_request expects a request-like object with headers.
    This class provides a minimal implementation.
    """

    def __init__(self, token: str) -> None:
        """Initialize with Bearer token.

        Args:
            token: JWT token from Authorization header
        """
        # Try both lowercase and capitalized versions
        self.headers = {
            "authorization": f"Bearer {token}",
            "Authorization": f"Bearer {token}",
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
            # Create a simple request object with the token
            request = SimpleRequest(token)

            # Verify JWT with Clerk using authenticate_request
            # Note: This is synchronous, but we use async signature for port consistency
            request_state = self._clerk.authenticate_request(
                request=request, options=AuthenticateRequestOptions()
            )

            # Check various possible attributes for user identification
            user_id = None
            if hasattr(request_state, "payload") and request_state.payload:
                # The user ID is in the 'sub' (subject) claim of the JWT payload
                user_id = request_state.payload.get("sub")
            elif hasattr(request_state, "user_id") and request_state.user_id:
                user_id = request_state.user_id
            elif hasattr(request_state, "userId"):
                user_id = request_state.userId

            if not user_id:
                # Log all attributes to debug
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"Could not find user_id. RequestState: {repr(request_state)}"
                )
                raise InvalidTokenError("Invalid or expired token")

            # Get full user details
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
