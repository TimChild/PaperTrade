"""Integration tests for the parameterized auth-scheme fixture.

These tests pin down the contract of ``auth_headers_for_scheme`` and the
``auth_scheme`` parametrization in ``conftest.py``. The fixture is
intentionally Phase C-ready: today the only accepted scheme is ``bearer``,
but the fixture machinery is in place so when ``ApiKeyAuthAdapter`` lands
the parameter list expansion is the only change needed to exercise every
existing test against ``Authorization: ApiKey <key>`` and ``X-API-Key: <key>``.

See also:

- ``backend/tests/conftest.py`` — fixture definitions
- ``docs/planning/agent-platform-proposal.md`` §C2 — Phase C API-key spec
- ``agent_docs/audits/2026-05-09/test-quality.md`` finding test.P0-2 / test.P1-1
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Header construction (no API call — pure fixture contract)
# ---------------------------------------------------------------------------


class TestAuthSchemeFixture:
    """Pin down the auth_scheme / auth_headers_for_scheme fixtures."""

    def test_default_param_is_bearer(self, auth_scheme: str) -> None:
        """The default param list (``_AUTH_SCHEMES_CURRENT``) is ``("bearer",)``.
        Until Phase C lands, every test using ``auth_scheme`` runs once for
        bearer only. Locking this in surfaces an unintended scheme expansion
        as a focused failure rather than a CI-wide green-then-red surprise."""
        assert auth_scheme == "bearer"

    def test_bearer_headers_use_authorization(
        self, auth_headers_for_scheme: dict[str, str]
    ) -> None:
        assert auth_headers_for_scheme == {"Authorization": "Bearer test-token-default"}


# ---------------------------------------------------------------------------
# End-to-end: bearer scheme is currently accepted by the API
# ---------------------------------------------------------------------------


class TestBearerSchemeIsAccepted:
    """The Bearer path is the only one the backend recognises today.
    Verifies the fixture's bearer wiring lines up with ``InMemoryAuthAdapter``
    in conftest, so any future divergence (e.g. token format change) breaks
    here first rather than in every API integration test simultaneously."""

    def test_bearer_token_authenticates_default_user(
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
        # If it had failed, we'd get 401 here.
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Phase C readiness — placeholder shape for the future api-key tests
# ---------------------------------------------------------------------------


class TestPhaseCSchemeIsRejectedToday:
    """Documents that the Phase C schemes are NOT YET ACCEPTED.

    These tests are skipped today (no scheme is parametrized in) but the
    structure is in place so when Phase C lands, expanding the param list
    in conftest auto-enables them. A reviewer at Phase C time can flip the
    skip into a real assertion.

    This is the test.P1-1 mitigation: the auth fixture pattern won't need
    to be redesigned mid-Phase-C; it'll just need its parameter set extended.
    """

    @pytest.mark.parametrize(
        "scheme",
        ["api_key_authorization", "api_key_header"],
    )
    def test_api_key_schemes_currently_return_401(
        self,
        scheme: str,
        client: "TestClient",
    ) -> None:
        """Pre-Phase-C, neither api-key scheme should authenticate. Once Phase C
        lands the matching ``ApiKeyAuthAdapter`` and middleware update, change
        this assertion to 200 (with a seeded api-key fixture)."""
        from tests.conftest import _build_auth_headers  # type: ignore[import-not-found]

        headers = _build_auth_headers(scheme, token="ak_test_dummy_phase_c")

        response = client.get("/api/v1/portfolios", headers=headers)

        # Pre-Phase C: backend ignores api-key headers, so the request is
        # treated as unauthenticated -> 401.
        assert response.status_code == 401, (
            f"Phase C may have shipped — scheme {scheme!r} now authenticates. "
            "Update this test and expand _AUTH_SCHEMES_CURRENT in conftest."
        )
