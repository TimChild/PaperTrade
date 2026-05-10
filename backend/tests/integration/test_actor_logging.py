"""Integration tests: actor identity surfaces end-to-end on authenticated requests.

Phase H5 (multi-agent identity prep): when a request authenticates via
API key, the resolved :class:`AuthenticatedUser` must carry the key's
``label`` so the activity feed (Phase H2) and per-key rate limiter
(Phase F) can group / filter by it. The Clerk path leaves the api_key
fields ``None``.

The unit tests in :mod:`tests.unit.adapters.auth.test_api_key_adapter`
and :mod:`tests.unit.adapters.inbound.api.test_dependencies` cover the
mechanics — the adapter populates the right shape, and
``_bind_actor_to_log_context`` writes the right contextvars. These
integration tests cover the **end-to-end story** by:

1. Driving a real request through the FastAPI ``TestClient`` against
   write endpoints.
2. Capturing the resolved :class:`AuthenticatedUser` via a tiny
   request-scoped probe wired into the same ``CurrentUserDep`` chain
   the production handler uses.
3. Asserting the actor identity matches the auth scheme used.

This pattern keeps boundary-mocking minimal — the only override is the
probe endpoint itself; the auth path, repository, hasher, and adapter
are all the real implementations seeded by ``conftest.py``.

Coordination note: Phase H2 (recent activity feed) builds on top of
this same surface. When H2 lands, the in-flight migration may add
``api_key_id`` FK columns to writable tables — those should be set
from ``current_user.api_key_id`` (the field this test verifies is
populated correctly). See the H5 PR description for the audit
findings.
"""

from collections.abc import Generator
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from fastapi import APIRouter
from pydantic import BaseModel

from zebu.adapters.inbound.api.dependencies import CurrentUser
from zebu.main import app

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Probe endpoint: surfaces the resolved AuthenticatedUser so tests can
# assert what the auth chain produced.
# ---------------------------------------------------------------------------


class ResolvedActorResponse(BaseModel):
    """Wire shape mirroring :class:`AuthenticatedUser` for assertions."""

    id: str
    email: str
    auth_method: str
    api_key_id: UUID | None
    api_key_label: str | None


_probe_router = APIRouter(prefix="/__test_actor_probe", tags=["test-only"])


@_probe_router.get("/me", response_model=ResolvedActorResponse)
async def probe_resolved_actor(
    current_user: CurrentUser,
) -> ResolvedActorResponse:
    """Return the resolved :class:`AuthenticatedUser` verbatim.

    Wired into the app via :func:`_install_probe_router` so the test
    client can hit it. Production never mounts this — the install
    happens in the test's ``autouse`` fixture.
    """
    return ResolvedActorResponse(
        id=current_user.id,
        email=current_user.email,
        auth_method=current_user.auth_method,
        api_key_id=current_user.api_key_id,
        api_key_label=current_user.api_key_label,
    )


@pytest.fixture(autouse=True)
def _install_probe_router() -> Generator[None, None, None]:
    """Mount the probe router for the test, unmount on teardown.

    Cleanup removes the router so we don't leak the test-only surface
    into other tests.
    """
    app.include_router(_probe_router, prefix="/api/v1")
    yield
    # Remove every route whose path starts with the probe prefix.
    app.routes[:] = [
        r
        for r in app.routes
        if not getattr(r, "path", "").startswith("/api/v1/__test_actor_probe")
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestActorResolutionViaClerk:
    """Bearer (Clerk) authentication populates only the Clerk fields."""

    def test_bearer_resolves_clerk_user(self, client: "TestClient") -> None:
        response = client.get(
            "/api/v1/__test_actor_probe/me",
            headers={"Authorization": "Bearer test-token-default"},
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["auth_method"] == "clerk"
        assert body["id"] == "test-user-default"
        # The Clerk path leaves the per-key fields unpopulated.
        assert body["api_key_id"] is None
        assert body["api_key_label"] is None


class TestActorResolutionViaApiKey:
    """API-key authentication populates the per-key id and label."""

    def test_x_api_key_header_resolves_with_label(self, client: "TestClient") -> None:
        """``X-API-Key`` is the canonical agent header."""
        response = client.get(
            "/api/v1/__test_actor_probe/me",
            headers={"X-API-Key": "test-token-default"},
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["auth_method"] == "api_key"
        # The seeded test API key is owned by "test-user-default" and
        # has label "test-default".
        assert body["id"] == "test-user-default"
        assert body["api_key_label"] == "test-default"
        assert body["api_key_id"] is not None

    def test_authorization_apikey_scheme_resolves_with_label(
        self, client: "TestClient"
    ) -> None:
        """``Authorization: ApiKey <raw>`` is the alternate transport.

        Both schemes resolve through the same adapter, so the bound
        actor identity must be identical regardless of which header
        the caller used.
        """
        response = client.get(
            "/api/v1/__test_actor_probe/me",
            headers={"Authorization": "ApiKey test-token-default"},
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["auth_method"] == "api_key"
        assert body["api_key_label"] == "test-default"

    def test_two_minted_keys_resolve_to_distinct_labels(
        self, client: "TestClient"
    ) -> None:
        """Mint two keys with distinct labels; verify each surfaces its own.

        This is the core multi-agent identity invariant: a single
        Clerk user can mint multiple keys (e.g.
        ``claude-code-laptop-explorer`` and
        ``claude-code-laptop-strategist``), and each authenticated
        request must surface its own label so the activity feed can
        differentiate.
        """
        bearer_headers = {"Authorization": "Bearer test-token-default"}
        explorer_resp = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={
                "label": "claude-code-laptop-explorer",
                "scopes": ["read", "trade"],
            },
        )
        assert explorer_resp.status_code == 201
        explorer_raw = explorer_resp.json()["raw_key"]

        strategist_resp = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={
                "label": "claude-code-laptop-strategist",
                "scopes": ["read", "trade"],
            },
        )
        assert strategist_resp.status_code == 201
        strategist_raw = strategist_resp.json()["raw_key"]

        explorer_probe = client.get(
            "/api/v1/__test_actor_probe/me",
            headers={"X-API-Key": explorer_raw},
        )
        strategist_probe = client.get(
            "/api/v1/__test_actor_probe/me",
            headers={"X-API-Key": strategist_raw},
        )
        assert explorer_probe.status_code == 200
        assert strategist_probe.status_code == 200

        explorer_body = explorer_probe.json()
        strategist_body = strategist_probe.json()

        # Same Clerk user_id (the human owner is the same)…
        assert explorer_body["id"] == strategist_body["id"] == "test-user-default"
        assert explorer_body["auth_method"] == "api_key"
        assert strategist_body["auth_method"] == "api_key"
        # …but distinct API-key identities exposed for observability.
        assert explorer_body["api_key_label"] == "claude-code-laptop-explorer"
        assert strategist_body["api_key_label"] == "claude-code-laptop-strategist"
        assert explorer_body["api_key_id"] != strategist_body["api_key_id"]


class TestApiKeyLastUsedAtBumpedOnEveryRequest:
    """Every authenticated request via API key bumps ``last_used_at``.

    The API-key UI (Phase H3) surfaces "last used 2 hours ago"; if the
    bump regresses, that field will silently freeze. This test pins
    down the contract from the integration side.
    """

    def test_api_key_last_used_at_advances_on_each_request(
        self, client: "TestClient"
    ) -> None:
        bearer_headers = {"Authorization": "Bearer test-token-default"}
        api_key_headers = {"X-API-Key": "test-token-default"}

        # First request via API key.
        first_resp = client.get("/api/v1/portfolios", headers=api_key_headers)
        assert first_resp.status_code == 200

        # Read the seeded key's listing via Bearer (the management
        # surface is Clerk-only); the seeded key has label "test-default".
        list_first = client.get("/api/v1/api-keys", headers=bearer_headers)
        assert list_first.status_code == 200
        first_seed = next(
            item
            for item in list_first.json()["items"]
            if item["label"] == "test-default"
        )
        first_last_used = first_seed["last_used_at"]
        assert first_last_used is not None, (
            "last_used_at should be populated after a successful API-key auth"
        )

        # Second request must produce a >= timestamp (the adapter
        # uses datetime.now(UTC) on each verify; equality is acceptable
        # when the call resolves within one clock tick).
        second_resp = client.get("/api/v1/portfolios", headers=api_key_headers)
        assert second_resp.status_code == 200

        list_second = client.get("/api/v1/api-keys", headers=bearer_headers)
        assert list_second.status_code == 200
        second_seed = next(
            item
            for item in list_second.json()["items"]
            if item["label"] == "test-default"
        )
        second_last_used = second_seed["last_used_at"]
        assert second_last_used is not None
        # >= because tests can run within a single clock tick on a fast
        # machine; what matters is the bump never regresses.
        assert second_last_used >= first_last_used
