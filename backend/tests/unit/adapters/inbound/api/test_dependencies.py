"""Unit tests for inbound API dependency injection.

Covers the env-driven admin allowlist helpers and the production
fail-fast guard added in Wave 1-A of the Phase B execution plan
(audits/2026-05-09 — sec.P1-2).
"""

import pytest
from fastapi import HTTPException

from zebu.adapters.auth.clerk_adapter import ClerkAuthAdapter
from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
from zebu.adapters.inbound.api.dependencies import (
    get_admin_user_ids,
    get_auth_port,
    is_admin_user,
    verify_admin,
)
from zebu.application.ports.auth_port import AuthenticatedUser


class TestGetAdminUserIds:
    """Tests for `get_admin_user_ids()` env parsing."""

    def test_unset_env_returns_empty_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
        assert get_admin_user_ids() == frozenset()

    def test_empty_string_returns_empty_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADMIN_USER_IDS", "")
        assert get_admin_user_ids() == frozenset()

    def test_single_user_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADMIN_USER_IDS", "user_2abc")
        assert get_admin_user_ids() == frozenset({"user_2abc"})

    def test_multiple_user_ids_with_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADMIN_USER_IDS", "user_a,  user_b , user_c ")
        assert get_admin_user_ids() == frozenset({"user_a", "user_b", "user_c"})

    def test_blank_segments_are_dropped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADMIN_USER_IDS", ",user_a,,user_b,")
        assert get_admin_user_ids() == frozenset({"user_a", "user_b"})


class TestIsAdminUser:
    """Tests for the `is_admin_user()` membership check."""

    def test_user_in_allowlist_returns_true(self) -> None:
        admin_ids = frozenset({"user_a", "user_b"})
        assert is_admin_user("user_a", admin_ids) is True

    def test_user_not_in_allowlist_returns_false(self) -> None:
        admin_ids = frozenset({"user_a", "user_b"})
        assert is_admin_user("user_c", admin_ids) is False

    def test_empty_allowlist_denies_everyone(self) -> None:
        admin_ids: frozenset[str] = frozenset()
        assert is_admin_user("user_a", admin_ids) is False


class TestVerifyAdmin:
    """Tests for the `verify_admin` FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_admin_user_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADMIN_USER_IDS", "user_admin")
        admin = AuthenticatedUser(id="user_admin", email="a@example.com")

        # verify_admin returns the deterministic UUID for the admin user.
        result = await verify_admin(admin)

        from uuid import NAMESPACE_DNS, uuid5

        assert result == uuid5(NAMESPACE_DNS, "user_admin")

    @pytest.mark.asyncio
    async def test_non_admin_raises_403(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADMIN_USER_IDS", "user_admin")
        non_admin = AuthenticatedUser(id="user_x", email="x@example.com")

        with pytest.raises(HTTPException) as excinfo:
            await verify_admin(non_admin)

        assert excinfo.value.status_code == 403
        assert "Admin privileges required" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_empty_allowlist_blocks_everyone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADMIN_USER_IDS", "")
        user = AuthenticatedUser(id="user_anyone", email="x@example.com")

        with pytest.raises(HTTPException) as excinfo:
            await verify_admin(user)

        assert excinfo.value.status_code == 403


class TestGetAuthPort:
    """Tests for `get_auth_port()` adapter selection + production fail-fast."""

    def test_returns_clerk_adapter_when_secret_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_abc")
        monkeypatch.delenv("APP_ENV", raising=False)

        adapter = get_auth_port()

        assert isinstance(adapter, ClerkAuthAdapter)

    def test_returns_in_memory_adapter_in_dev_when_secret_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "development")

        adapter = get_auth_port()

        assert isinstance(adapter, InMemoryAuthAdapter)

    def test_returns_in_memory_adapter_for_test_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLERK_SECRET_KEY", "test")
        monkeypatch.setenv("APP_ENV", "development")

        adapter = get_auth_port()

        assert isinstance(adapter, InMemoryAuthAdapter)

    def test_production_with_missing_secret_raises_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "production")

        with pytest.raises(RuntimeError, match="CLERK_SECRET_KEY"):
            get_auth_port()

    def test_production_with_empty_secret_raises_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLERK_SECRET_KEY", "")
        monkeypatch.setenv("APP_ENV", "production")

        with pytest.raises(RuntimeError, match="CLERK_SECRET_KEY"):
            get_auth_port()

    def test_production_with_test_placeholder_raises_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLERK_SECRET_KEY", "test")
        monkeypatch.setenv("APP_ENV", "production")

        with pytest.raises(RuntimeError, match="CLERK_SECRET_KEY"):
            get_auth_port()

    def test_production_with_real_secret_returns_clerk_adapter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLERK_SECRET_KEY", "sk_live_real_secret")
        monkeypatch.setenv("APP_ENV", "production")

        adapter = get_auth_port()

        assert isinstance(adapter, ClerkAuthAdapter)
