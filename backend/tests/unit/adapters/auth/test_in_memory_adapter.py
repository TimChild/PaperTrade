"""Unit tests for InMemoryAuthAdapter.

The in-memory adapter is the default in tests (see ``backend/tests/conftest.py``)
and the canonical "fake at the boundary" used to keep the test suite offline.
These tests exercise its contract directly so regressions in the boundary fake
can't masquerade as application bugs.
"""

import pytest

from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
from zebu.application.ports.auth_port import AuthenticatedUser
from zebu.domain.exceptions import InvalidTokenError


def _user(
    user_id: str = "user_test_1", email: str = "test@zebutrader.com"
) -> AuthenticatedUser:
    """Build a sample AuthenticatedUser for tests."""
    return AuthenticatedUser(id=user_id, email=email)


class TestVerifyToken:
    """Tests for InMemoryAuthAdapter.verify_token()."""

    @pytest.mark.asyncio
    async def test_add_user_then_verify_token_returns_user(self) -> None:
        """add_user() then verify_token() should round-trip the same user."""
        adapter = InMemoryAuthAdapter()
        user = _user()
        adapter.add_user(user, "tok-abc")

        result = await adapter.verify_token("tok-abc")

        assert result == user
        # AuthenticatedUser is frozen — equality covers id+email
        assert result.id == "user_test_1"
        assert result.email == "test@zebutrader.com"

    @pytest.mark.asyncio
    async def test_empty_adapter_rejects_all_tokens(self) -> None:
        """A freshly-constructed adapter has no tokens — every verify should fail."""
        adapter = InMemoryAuthAdapter()

        with pytest.raises(InvalidTokenError, match="Invalid token"):
            await adapter.verify_token("anything")

    @pytest.mark.asyncio
    async def test_unknown_token_raises_invalid_token_error(self) -> None:
        """A token not registered with add_user() should raise InvalidTokenError."""
        adapter = InMemoryAuthAdapter()
        adapter.add_user(_user(), "tok-known")

        with pytest.raises(InvalidTokenError):
            await adapter.verify_token("tok-not-known")

    @pytest.mark.asyncio
    async def test_empty_string_token_rejected(self) -> None:
        """The empty string is not a valid token even if no users are registered."""
        adapter = InMemoryAuthAdapter()
        adapter.add_user(_user(), "tok-known")

        with pytest.raises(InvalidTokenError):
            await adapter.verify_token("")

    @pytest.mark.asyncio
    async def test_multiple_users_routes_token_to_correct_user(self) -> None:
        """With several users registered, each token should resolve to its own user."""
        adapter = InMemoryAuthAdapter()
        alice = _user(user_id="user_alice", email="alice@example.com")
        bob = _user(user_id="user_bob", email="bob@example.com")
        adapter.add_user(alice, "tok-alice")
        adapter.add_user(bob, "tok-bob")

        assert (await adapter.verify_token("tok-alice")) == alice
        assert (await adapter.verify_token("tok-bob")) == bob

    @pytest.mark.asyncio
    async def test_re_adding_user_with_new_token_invalidates_old_token(self) -> None:
        """add_user re-registers a user under a *new* token; the old token should
        still resolve (we don't garbage-collect tokens). This test pins down the
        current contract so a future change is intentional."""
        adapter = InMemoryAuthAdapter()
        user = _user()
        adapter.add_user(user, "tok-1")
        adapter.add_user(user, "tok-2")

        # Both tokens map to the same user under current contract
        assert (await adapter.verify_token("tok-1")) == user
        assert (await adapter.verify_token("tok-2")) == user

    @pytest.mark.asyncio
    async def test_pre_populated_users_without_token_cannot_verify(self) -> None:
        """Constructing with users={...} populates _users but leaves _tokens empty;
        verify_token should still reject tokens until add_user is called."""
        user = _user()
        adapter = InMemoryAuthAdapter(users={user.id: user})

        with pytest.raises(InvalidTokenError):
            await adapter.verify_token(user.id)  # naive guess: the user_id


class TestGetUser:
    """Tests for InMemoryAuthAdapter.get_user()."""

    @pytest.mark.asyncio
    async def test_get_user_returns_user_when_present(self) -> None:
        """get_user() should return the AuthenticatedUser added via add_user()."""
        adapter = InMemoryAuthAdapter()
        user = _user()
        adapter.add_user(user, "tok-abc")

        assert (await adapter.get_user("user_test_1")) == user

    @pytest.mark.asyncio
    async def test_get_user_returns_none_when_missing(self) -> None:
        """get_user() should return None for an unknown user_id."""
        adapter = InMemoryAuthAdapter()

        assert (await adapter.get_user("user_does_not_exist")) is None

    @pytest.mark.asyncio
    async def test_get_user_finds_pre_populated_user(self) -> None:
        """The constructor's ``users`` arg should pre-populate get_user()."""
        user = _user(user_id="user_seeded", email="seeded@example.com")
        adapter = InMemoryAuthAdapter(users={user.id: user})

        assert (await adapter.get_user("user_seeded")) == user
