"""Unit tests for ClerkAuthAdapter.

Mocks the Clerk SDK at the boundary — i.e. the ``Clerk`` client instance and
its two methods we actually call:

- ``Clerk.authenticate_request(request, options)`` -> ``RequestState``
- ``Clerk.users.get(user_id=...)`` -> Clerk ``User`` model (duck-typed in tests)

We do **not** stub internal logic of the adapter; we drive the adapter the way
production does (``await adapter.verify_token(token)``) and assert behavioural
outcomes (return value or raised ``InvalidTokenError``).
"""

from collections.abc import Iterable
from typing import cast
from unittest.mock import MagicMock

import pytest
from clerk_backend_api.security.types import (
    AuthErrorReason,
    AuthStatus,
    RequestState,
    TokenVerificationErrorReason,
)

from zebu.adapters.auth.clerk_adapter import ClerkAuthAdapter, SimpleRequest
from zebu.application.ports.auth_port import AuthenticatedUser
from zebu.domain.exceptions import InvalidTokenError

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeEmail:
    """Duck-typed stand-in for the Clerk SDK ``EmailAddress`` model.

    The adapter only reads ``.email_address``.
    """

    def __init__(self, email_address: str) -> None:
        self.email_address = email_address


class _FakeClerkUser:
    """Duck-typed stand-in for the Clerk SDK ``User`` model.

    The adapter only reads ``.id`` and iterates ``.email_addresses``.
    """

    def __init__(self, *, id: str, emails: Iterable[str]) -> None:  # noqa: A002
        self.id = id
        self.email_addresses = [_FakeEmail(e) for e in emails]


def _make_adapter() -> tuple[ClerkAuthAdapter, MagicMock]:
    """Construct a ClerkAuthAdapter and replace its SDK client with a MagicMock.

    Returns the adapter and the mock client so the test can configure
    ``client.authenticate_request.return_value`` and
    ``client.users.get.return_value``.
    """
    adapter = ClerkAuthAdapter(secret_key="sk_test_dummy")
    mock_client = MagicMock()
    # Inject the mock as the SDK boundary
    adapter._clerk = mock_client  # type: ignore[assignment]  # mocking SDK at boundary
    return adapter, mock_client


def _signed_in_state(sub: str = "user_test_123") -> RequestState:
    """Build a ``RequestState`` representing a successful Clerk verification."""
    return RequestState(
        status=AuthStatus.SIGNED_IN,
        token="signed-token",
        payload={"sub": sub, "iat": 1700000000, "exp": 1700003600},
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestVerifyTokenHappyPath:
    """verify_token() returns the authenticated user when Clerk approves."""

    @pytest.mark.asyncio
    async def test_returns_authenticated_user_with_id_and_email(self) -> None:
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = _signed_in_state(sub="user_abc")
        mock.users.get.return_value = _FakeClerkUser(
            id="user_abc", emails=["alice@example.com"]
        )

        result = await adapter.verify_token("a-real-jwt")

        assert isinstance(result, AuthenticatedUser)
        assert result.id == "user_abc"
        assert result.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_uses_first_email_when_user_has_multiple(self) -> None:
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = _signed_in_state(sub="user_multi")
        mock.users.get.return_value = _FakeClerkUser(
            id="user_multi",
            emails=["primary@example.com", "secondary@example.com"],
        )

        result = await adapter.verify_token("token")

        assert result.email == "primary@example.com"

    @pytest.mark.asyncio
    async def test_returns_empty_email_when_user_has_no_email_addresses(self) -> None:
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = _signed_in_state(sub="user_no_email")
        mock.users.get.return_value = _FakeClerkUser(id="user_no_email", emails=[])

        result = await adapter.verify_token("token")

        assert result.id == "user_no_email"
        assert result.email == ""

    @pytest.mark.asyncio
    async def test_passes_token_to_clerk_via_authorization_header(self) -> None:
        """The adapter must wrap the token in a ``Bearer ...`` Authorization header
        before handing it to Clerk's SDK — this is the contract Clerk relies on."""
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = _signed_in_state(sub="user_x")
        mock.users.get.return_value = _FakeClerkUser(id="user_x", emails=["x@y.com"])

        await adapter.verify_token("the-token-value")

        assert mock.authenticate_request.call_count == 1
        request_arg = cast(
            SimpleRequest, mock.authenticate_request.call_args.kwargs["request"]
        )
        assert request_arg.headers["Authorization"] == "Bearer the-token-value"


# ---------------------------------------------------------------------------
# Sad paths
# ---------------------------------------------------------------------------


class TestVerifyTokenInvalidToken:
    """verify_token() raises InvalidTokenError on Clerk-side rejection."""

    @pytest.mark.asyncio
    async def test_signed_out_status_raises_invalid_token_error(self) -> None:
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = RequestState(
            status=AuthStatus.SIGNED_OUT,
            reason=AuthErrorReason.SESSION_TOKEN_MISSING,
        )

        with pytest.raises(InvalidTokenError, match="Authentication failed"):
            await adapter.verify_token("missing-token")

        # users.get should NEVER be called when the request isn't signed in
        mock.users.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_expired_token_raises_invalid_token_error(self) -> None:
        """Clerk reports ``token-expired`` as the reason on a signed-out state."""
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = RequestState(
            status=AuthStatus.SIGNED_OUT,
            reason=TokenVerificationErrorReason.TOKEN_EXPIRED,
        )

        with pytest.raises(InvalidTokenError, match="Authentication failed"):
            await adapter.verify_token("expired-token")

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_invalid_token_error(self) -> None:
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = RequestState(
            status=AuthStatus.SIGNED_OUT,
            reason=TokenVerificationErrorReason.TOKEN_INVALID_SIGNATURE,
        )

        with pytest.raises(InvalidTokenError):
            await adapter.verify_token("malformed-token")

    @pytest.mark.asyncio
    async def test_missing_payload_raises_with_helpful_message(self) -> None:
        """If Clerk reports SIGNED_IN but somehow gives us no payload, we should
        raise — never proceed to call ``users.get`` with garbage."""
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = RequestState(
            status=AuthStatus.SIGNED_IN,
            payload=None,
        )

        with pytest.raises(InvalidTokenError, match="payload is missing"):
            await adapter.verify_token("token")

        mock.users.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_sub_claim_raises_with_helpful_message(self) -> None:
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = RequestState(
            status=AuthStatus.SIGNED_IN,
            payload={"iat": 1700000000, "exp": 1700003600},  # no "sub"
        )

        with pytest.raises(InvalidTokenError, match="sub claim"):
            await adapter.verify_token("token")

        mock.users.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_sub_claim_raises_with_helpful_message(self) -> None:
        """An empty-string sub is just as broken as a missing sub."""
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = RequestState(
            status=AuthStatus.SIGNED_IN,
            payload={"sub": ""},
        )

        with pytest.raises(InvalidTokenError, match="sub claim"):
            await adapter.verify_token("token")


class TestVerifyTokenSDKErrors:
    """verify_token() converts SDK-level failures into InvalidTokenError."""

    @pytest.mark.asyncio
    async def test_authenticate_request_raises_is_wrapped_in_invalid_token_error(
        self,
    ) -> None:
        """A network error (or any other SDK-internal exception) during
        authenticate_request should surface as InvalidTokenError, not bleed up
        as a raw Exception that the API layer doesn't know how to handle."""
        adapter, mock = _make_adapter()
        mock.authenticate_request.side_effect = ConnectionError("JWKS fetch failed")

        with pytest.raises(InvalidTokenError, match="Token verification failed"):
            await adapter.verify_token("token")

    @pytest.mark.asyncio
    async def test_users_get_failure_raises_invalid_token_error(self) -> None:
        """If Clerk verifies the token but ``users.get`` fails (user deleted,
        network error mid-call), the adapter should raise InvalidTokenError so
        the API layer returns 401 rather than 500."""
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = _signed_in_state(sub="user_gone")
        mock.users.get.side_effect = RuntimeError("404 user not found")

        with pytest.raises(InvalidTokenError, match="Token verification failed"):
            await adapter.verify_token("token")

    @pytest.mark.asyncio
    async def test_invalid_token_error_re_raised_unwrapped(self) -> None:
        """If our own InvalidTokenError is raised inside the try block (e.g.
        because of a missing sub claim), it should not be wrapped in a *second*
        InvalidTokenError with the message ``Token verification failed: ...``.
        This pins down the re-raise in lines 114-116 of clerk_adapter.py."""
        adapter, mock = _make_adapter()
        mock.authenticate_request.return_value = RequestState(
            status=AuthStatus.SIGNED_IN,
            payload={"sub": ""},
        )

        with pytest.raises(InvalidTokenError) as exc_info:
            await adapter.verify_token("token")

        assert "Token verification failed" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# get_user()
# ---------------------------------------------------------------------------


class TestGetUser:
    """get_user() returns AuthenticatedUser or None."""

    @pytest.mark.asyncio
    async def test_returns_user_when_clerk_returns_user(self) -> None:
        adapter, mock = _make_adapter()
        mock.users.get.return_value = _FakeClerkUser(
            id="user_known", emails=["known@example.com"]
        )

        result = await adapter.get_user("user_known")

        assert result is not None
        assert result.id == "user_known"
        assert result.email == "known@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_clerk_raises(self) -> None:
        """get_user swallows SDK exceptions and returns None — different shape
        from verify_token, which raises. This is the documented contract on
        AuthPort and we want to lock it in."""
        adapter, mock = _make_adapter()
        mock.users.get.side_effect = RuntimeError("404 user_not_found")

        result = await adapter.get_user("user_unknown")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_with_empty_email_when_user_has_no_emails(self) -> None:
        adapter, mock = _make_adapter()
        mock.users.get.return_value = _FakeClerkUser(id="user_silent", emails=[])

        result = await adapter.get_user("user_silent")

        assert result is not None
        assert result.id == "user_silent"
        assert result.email == ""


# ---------------------------------------------------------------------------
# SimpleRequest helper
# ---------------------------------------------------------------------------


class TestSimpleRequest:
    """SimpleRequest wraps the bearer token for Clerk's authenticate_request."""

    def test_constructs_authorization_header(self) -> None:
        request = SimpleRequest("the-jwt")

        assert request.headers == {"Authorization": "Bearer the-jwt"}

    def test_handles_empty_token(self) -> None:
        """SimpleRequest doesn't validate — Clerk does. It must still construct
        cleanly so the empty-token error surfaces from Clerk, not from us."""
        request = SimpleRequest("")

        assert request.headers["Authorization"] == "Bearer "
