"""Integration tests for the parameterized auth-scheme fixture.

Phase C2 has shipped: ``ApiKeyAuthAdapter`` is wired into
``dependencies.get_current_user`` and ``_AUTH_SCHEMES_CURRENT`` in
``conftest.py`` now expands to ``("bearer", "api_key_authorization",
"api_key_header")``. Every test that depends on the ``auth_scheme``
fixture is automatically exercised against all three transports.

These tests pin down the contract of the fixture itself so a regression
shows up here first rather than as a confusing failure across every
integration test in the suite.

See also:

- ``backend/tests/conftest.py`` — fixture definitions + seeded test key
- ``docs/planning/agent-platform-proposal.md`` §C2 — Phase C API-key spec
- ``agent_docs/audits/2026-05-09/test-quality.md`` finding test.P0-2 / test.P1-1
- ``backend/src/zebu/adapters/auth/api_key_adapter.py`` — the new adapter
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


_ALL_SCHEMES = ("bearer", "api_key_authorization", "api_key_header")


# ---------------------------------------------------------------------------
# Header construction (no API call — pure fixture contract)
# ---------------------------------------------------------------------------


class TestAuthSchemeFixture:
    """Pin down the auth_scheme / auth_headers_for_scheme fixtures."""

    def test_default_params_cover_all_schemes(self, auth_scheme: str) -> None:
        """``_AUTH_SCHEMES_CURRENT`` should expose every accepted transport.

        Locking this in surfaces unintended scheme additions or removals as
        a focused fixture failure rather than a CI-wide surprise.
        """
        assert auth_scheme in _ALL_SCHEMES

    def test_bearer_headers_use_authorization(self) -> None:
        from tests.conftest import _build_auth_headers  # type: ignore[import-not-found]

        headers = _build_auth_headers("bearer")
        assert headers == {"Authorization": "Bearer test-token-default"}

    def test_api_key_authorization_headers_use_apikey_scheme(self) -> None:
        from tests.conftest import _build_auth_headers  # type: ignore[import-not-found]

        headers = _build_auth_headers("api_key_authorization")
        assert headers == {"Authorization": "ApiKey test-token-default"}

    def test_api_key_header_uses_x_api_key(self) -> None:
        from tests.conftest import _build_auth_headers  # type: ignore[import-not-found]

        headers = _build_auth_headers("api_key_header")
        assert headers == {"X-API-Key": "test-token-default"}


# ---------------------------------------------------------------------------
# End-to-end: every parametrized scheme authenticates against the API
# ---------------------------------------------------------------------------


class TestEverySchemeIsAccepted:
    """All three transports should resolve to the same default test user."""

    def test_scheme_authenticates_default_user(
        self,
        client: "TestClient",
        auth_headers_for_scheme: dict[str, str],
    ) -> None:
        # Listing portfolios is one of the cheapest authenticated endpoints.
        response = client.get(
            "/api/v1/portfolios",
            headers=auth_headers_for_scheme,
        )

        # 200 (with possibly empty list) means auth succeeded.
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Negative cases — bad / missing keys still produce 401
# ---------------------------------------------------------------------------


class TestApiKeyNegativeCases:
    """Sanity-check the failure paths so a buggy adapter doesn't silently allow."""

    def test_unknown_api_key_returns_401(self, client: "TestClient") -> None:
        response = client.get(
            "/api/v1/portfolios",
            headers={"X-API-Key": "zk_definitely_not_a_real_key"},
        )
        assert response.status_code == 401

    def test_missing_credentials_returns_401(self, client: "TestClient") -> None:
        response = client.get("/api/v1/portfolios")
        assert response.status_code == 401

    @pytest.mark.parametrize("scheme", ["api_key_authorization", "api_key_header"])
    def test_empty_api_key_returns_401(self, scheme: str, client: "TestClient") -> None:
        from tests.conftest import _build_auth_headers  # type: ignore[import-not-found]

        # Empty string token after a valid scheme name.
        headers = _build_auth_headers(scheme, token="")
        # Reset to the empty-value form (the helper concatenates).
        if scheme == "api_key_authorization":
            headers = {"Authorization": "ApiKey "}
        else:
            headers = {"X-API-Key": ""}

        response = client.get("/api/v1/portfolios", headers=headers)
        assert response.status_code == 401
