"""Integration tests for the API-key management endpoints.

Covers:

- Mint: ``POST /api/v1/api-keys`` returns the raw key once and persists
  the hash. Listing afterwards never returns the raw key.
- List: ``GET /api/v1/api-keys`` shows only the authenticated user's keys.
- Revoke: ``DELETE /api/v1/api-keys/{id}`` revokes a key and prevents it
  from authenticating subsequent requests.
- Auth gating: API-key requests cannot mint other API keys (Clerk-only
  surface).
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def bearer_headers() -> dict[str, str]:
    """Headers for the seeded test user via Bearer (Clerk) auth."""
    return {"Authorization": "Bearer test-token-default"}


class TestCreateApiKey:
    def test_mint_returns_raw_key_once(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={
                "label": "claude-desktop",
                "scopes": ["read"],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["label"] == "claude-desktop"
        assert body["scopes"] == ["read"]
        assert body["raw_key"].startswith("zk_")
        assert "id" in body

    def test_mint_with_multiple_scopes(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={
                "label": "trade-agent",
                "scopes": ["read", "trade"],
            },
        )
        assert response.status_code == 201
        assert sorted(response.json()["scopes"]) == ["read", "trade"]

    def test_mint_with_unknown_scope_returns_422(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={
                "label": "bad",
                "scopes": ["super-admin"],
            },
        )
        assert response.status_code == 422

    def test_mint_with_empty_scopes_returns_422(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={"label": "bad", "scopes": []},
        )
        assert response.status_code == 422

    def test_mint_with_expiry_persists_expiry(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        expires = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        response = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={
                "label": "tmp",
                "scopes": ["read"],
                "expires_at": expires,
            },
        )
        assert response.status_code == 201
        # Expiry round-trips via the create response.
        assert response.json()["expires_at"] is not None

    def test_mint_requires_authentication(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/api-keys",
            json={"label": "x", "scopes": ["read"]},
        )
        assert response.status_code == 401

    def test_api_key_authenticated_request_cannot_mint(
        self, client: TestClient
    ) -> None:
        """Defence-in-depth: agents can't mint other API keys."""
        # The default seeded API key is "test-token-default" (raw value).
        response = client.post(
            "/api/v1/api-keys",
            headers={"X-API-Key": "test-token-default"},
            json={"label": "x", "scopes": ["read"]},
        )
        assert response.status_code == 403


class TestListApiKeys:
    def test_list_includes_minted_keys(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        # Mint two keys.
        client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={"label": "a", "scopes": ["read"]},
        )
        client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={"label": "b", "scopes": ["trade"]},
        )

        response = client.get("/api/v1/api-keys", headers=bearer_headers)
        assert response.status_code == 200
        body = response.json()
        # The seeded "test-default" + 2 newly minted = 3 keys for this user.
        assert body["total"] >= 2
        labels = {item["label"] for item in body["items"]}
        assert {"a", "b"}.issubset(labels)

    def test_list_does_not_return_raw_keys(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={"label": "a", "scopes": ["read"]},
        )
        response = client.get("/api/v1/api-keys", headers=bearer_headers)
        for item in response.json()["items"]:
            assert "raw_key" not in item
            assert "key_hash" not in item

    def test_list_requires_clerk_bearer(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/api-keys",
            headers={"X-API-Key": "test-token-default"},
        )
        assert response.status_code == 403


class TestRevokeApiKey:
    def test_revoke_succeeds_for_owned_key(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        mint_resp = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={"label": "to-revoke", "scopes": ["read"]},
        )
        api_key_id = mint_resp.json()["id"]

        del_resp = client.delete(
            f"/api/v1/api-keys/{api_key_id}", headers=bearer_headers
        )
        assert del_resp.status_code == 204

        # Verify it now shows as revoked in the list.
        list_resp = client.get("/api/v1/api-keys", headers=bearer_headers)
        revoked = next(i for i in list_resp.json()["items"] if i["id"] == api_key_id)
        assert revoked["revoked_at"] is not None
        assert revoked["is_active"] is False

    def test_revoke_is_idempotent(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        mint_resp = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={"label": "to-revoke", "scopes": ["read"]},
        )
        api_key_id = mint_resp.json()["id"]

        first = client.delete(f"/api/v1/api-keys/{api_key_id}", headers=bearer_headers)
        second = client.delete(f"/api/v1/api-keys/{api_key_id}", headers=bearer_headers)
        assert first.status_code == 204
        assert second.status_code == 204

    def test_revoked_key_cannot_authenticate(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        mint_resp = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={"label": "to-revoke", "scopes": ["read"]},
        )
        api_key_id = mint_resp.json()["id"]
        raw_key = mint_resp.json()["raw_key"]

        # Sanity: key works pre-revocation.
        ok = client.get("/api/v1/portfolios", headers={"X-API-Key": raw_key})
        assert ok.status_code == 200

        # Revoke.
        client.delete(f"/api/v1/api-keys/{api_key_id}", headers=bearer_headers)

        # Post-revocation: 401.
        rejected = client.get("/api/v1/portfolios", headers={"X-API-Key": raw_key})
        assert rejected.status_code == 401

    def test_revoke_unknown_id_returns_404(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        from uuid import uuid4

        response = client.delete(f"/api/v1/api-keys/{uuid4()}", headers=bearer_headers)
        assert response.status_code == 404


class TestRoundTripWithFreshKey:
    def test_minted_key_authenticates_subsequent_request(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        """End-to-end: mint a key, then use it to authenticate a separate call."""
        mint_resp = client.post(
            "/api/v1/api-keys",
            headers=bearer_headers,
            json={"label": "round-trip", "scopes": ["read"]},
        )
        raw_key = mint_resp.json()["raw_key"]

        # Use the new key on a different endpoint.
        portfolios_resp = client.get(
            "/api/v1/portfolios", headers={"X-API-Key": raw_key}
        )
        assert portfolios_resp.status_code == 200
