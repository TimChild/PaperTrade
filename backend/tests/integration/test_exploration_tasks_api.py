"""Integration tests for the ExplorationTask API.

Phase C4 — covers:

* Create / list / get / delete happy paths.
* Validation errors flow through the global handlers (422 + ErrorResponse
  envelope).
* List endpoint exposes the standard ``PaginatedResponse`` envelope with
  ``items / total / limit / offset / has_more``.
* Atomic claim — second claimer gets 409.
* Findings submission transitions task to DONE.
* Auth gating — every route returns 401 without Bearer.
* Owner-only delete — non-owners get 403.

Tests use the repo-pattern dependency overrides established by the project
(in-memory market data, in-memory auth, SQLite in-memory DB).
"""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_task(
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    prompt: str = "Investigate AAPL mean-reversion",
    target_portfolio_id: str | None = None,
    tickers: list[str] | None = None,
    constraints: dict[str, object] | None = None,
) -> dict[str, object]:
    """Create an exploration task and return its body."""
    payload: dict[str, object] = {"prompt": prompt}
    if target_portfolio_id is not None:
        payload["target_portfolio_id"] = target_portfolio_id
    if tickers is not None:
        payload["tickers"] = tickers
    if constraints is not None:
        payload["constraints"] = constraints

    response = client.post(
        "/api/v1/exploration-tasks",
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_minimal_task(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers, prompt="Explore mean-reversion")
        assert body["prompt"] == "Explore mean-reversion"
        assert body["status"] == "OPEN"
        assert body["target_portfolio_id"] is None
        assert body["tickers"] is None
        assert body["constraints"] is None
        assert body["claimed_by"] is None
        assert body["claimed_at"] is None
        assert body["findings"] is None
        # Sanity: id is a uuid
        UUID(str(body["id"]))

    def test_create_with_full_payload(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = str(uuid4())
        body = _create_task(
            client,
            auth_headers,
            prompt="Explore",
            target_portfolio_id=portfolio_id,
            tickers=["AAPL", "MSFT"],
            constraints={
                "max_backtests": 10,
                "allow_live_activation": False,
                "strategy_type_whitelist": ["MOVING_AVERAGE_CROSSOVER"],
            },
        )
        assert body["target_portfolio_id"] == portfolio_id
        assert body["tickers"] == ["AAPL", "MSFT"]
        assert body["constraints"]["max_backtests"] == 10
        assert body["constraints"]["allow_live_activation"] is False
        assert body["constraints"]["strategy_type_whitelist"] == [
            "MOVING_AVERAGE_CROSSOVER"
        ]

    def test_create_empty_prompt_returns_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/exploration-tasks",
            headers=auth_headers,
            json={"prompt": ""},
        )
        assert response.status_code == 422
        body = response.json()
        # Standard ErrorResponse envelope.
        assert "detail" in body
        assert isinstance(body["detail"], str)

    def test_create_oversize_prompt_returns_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/exploration-tasks",
            headers=auth_headers,
            json={"prompt": "x" * 4001},
        )
        assert response.status_code == 422

    def test_create_invalid_strategy_type_in_whitelist_returns_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/exploration-tasks",
            headers=auth_headers,
            json={
                "prompt": "Explore",
                "constraints": {"strategy_type_whitelist": ["NOT_A_TYPE"]},
            },
        )
        assert response.status_code == 422

    def test_create_invalid_ticker_returns_400(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/exploration-tasks",
            headers=auth_headers,
            json={"prompt": "Explore", "tickers": ["lowercase"]},
        )
        # InvalidTickerError -> 400.
        assert response.status_code == 400

    def test_create_max_backtests_zero_returns_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/exploration-tasks",
            headers=auth_headers,
            json={
                "prompt": "Explore",
                "constraints": {"max_backtests": 0},
            },
        )
        assert response.status_code == 422

    def test_create_unauthenticated_returns_auth_error(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/api/v1/exploration-tasks",
            json={"prompt": "Explore"},
        )
        # FastAPI's HTTPBearer returns 403 on missing header, 401 on
        # invalid token. Both are auth-failure semantics.
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# List + paginate
# ---------------------------------------------------------------------------


class TestList:
    def test_list_empty(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get("/api/v1/exploration-tasks", headers=auth_headers)
        assert response.status_code == 200
        page = response.json()
        assert page["items"] == []
        assert page["total"] == 0
        assert page["limit"] == 20
        assert page["offset"] == 0
        assert page["has_more"] is False

    def test_list_returns_paginated_envelope(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        for i in range(3):
            _create_task(client, auth_headers, prompt=f"task {i}")

        page = client.get(
            "/api/v1/exploration-tasks?limit=2&offset=0",
            headers=auth_headers,
        ).json()
        assert page["total"] == 3
        assert page["limit"] == 2
        assert page["offset"] == 0
        assert len(page["items"]) == 2
        assert page["has_more"] is True

        page2 = client.get(
            "/api/v1/exploration-tasks?limit=2&offset=2",
            headers=auth_headers,
        ).json()
        assert page2["total"] == 3
        assert len(page2["items"]) == 1
        assert page2["has_more"] is False

    def test_list_filters_by_status(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        a = _create_task(client, auth_headers)
        # Claim one of them
        client.post(
            f"/api/v1/exploration-tasks/{a['id']}/claim",
            headers=auth_headers,
        )

        opens = client.get(
            "/api/v1/exploration-tasks?status=OPEN",
            headers=auth_headers,
        ).json()
        in_progress = client.get(
            "/api/v1/exploration-tasks?status=IN_PROGRESS",
            headers=auth_headers,
        ).json()
        assert opens["total"] == 0
        assert in_progress["total"] == 1

    def test_list_invalid_status_returns_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get(
            "/api/v1/exploration-tasks?status=NOPE",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_list_scope_mine(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        # All tasks here were created by the default test user so they
        # should all show up under scope=mine too.
        _create_task(client, auth_headers, prompt="t1")
        _create_task(client, auth_headers, prompt="t2")
        page = client.get(
            "/api/v1/exploration-tasks?scope=mine",
            headers=auth_headers,
        ).json()
        assert page["total"] == 2

    def test_list_rejects_limit_above_max(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get(
            "/api/v1/exploration-tasks?limit=101",
            headers=auth_headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_one(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers, prompt="zone")
        response = client.get(
            f"/api/v1/exploration-tasks/{body['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == body["id"]

    def test_get_missing_returns_404(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get(
            f"/api/v1/exploration-tasks/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], str)

    def test_get_unauthenticated_returns_auth_error(
        self,
        client: TestClient,
    ) -> None:
        response = client.get(f"/api/v1/exploration-tasks/{uuid4()}")
        # 401 / 403 — both are auth-failure semantics for HTTPBearer.
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_owner_succeeds(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers)
        response = client.delete(
            f"/api/v1/exploration-tasks/{body['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        # Verify it's gone.
        followup = client.get(
            f"/api/v1/exploration-tasks/{body['id']}",
            headers=auth_headers,
        )
        assert followup.status_code == 404

    def test_delete_missing_returns_404(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.delete(
            f"/api/v1/exploration-tasks/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_delete_non_owner_returns_403(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        # Create as default user.
        body = _create_task(client, auth_headers)
        # Add a second user to the in-memory auth adapter and call DELETE
        # with that user's token.
        from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
        from zebu.adapters.inbound.api.dependencies import get_auth_port
        from zebu.application.ports.auth_port import AuthenticatedUser

        # Get the existing test adapter and add another user/token.
        # The fixture caches the adapter on the override fn.
        override = client.app.dependency_overrides[get_auth_port]
        adapter = override()
        assert isinstance(adapter, InMemoryAuthAdapter)
        adapter.add_user(
            AuthenticatedUser(id="other-user", email="other@example.com"),
            "other-token",
        )

        response = client.delete(
            f"/api/v1/exploration-tasks/{body['id']}",
            headers={"Authorization": "Bearer other-token"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------


class TestClaim:
    def test_claim_open_task_succeeds(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers)
        response = client.post(
            f"/api/v1/exploration-tasks/{body['id']}/claim",
            headers=auth_headers,
            json={"agent_id": "agent-a"},
        )
        assert response.status_code == 200
        claimed = response.json()
        assert claimed["status"] == "IN_PROGRESS"
        assert claimed["claimed_by"] == "agent-a"
        assert claimed["claimed_at"] is not None

    def test_claim_without_agent_id_uses_user(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers)
        response = client.post(
            f"/api/v1/exploration-tasks/{body['id']}/claim",
            headers=auth_headers,
        )
        assert response.status_code == 200
        claimed = response.json()
        # The fallback agent_id is the user's UUID — same UUID that
        # appears as created_by.
        assert claimed["claimed_by"] == body["created_by"]

    def test_claim_already_claimed_returns_409(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers)
        first = client.post(
            f"/api/v1/exploration-tasks/{body['id']}/claim",
            headers=auth_headers,
            json={"agent_id": "agent-a"},
        )
        assert first.status_code == 200

        second = client.post(
            f"/api/v1/exploration-tasks/{body['id']}/claim",
            headers=auth_headers,
            json={"agent_id": "agent-b"},
        )
        assert second.status_code == 409
        # Verify the original claim sticks.
        loaded = client.get(
            f"/api/v1/exploration-tasks/{body['id']}",
            headers=auth_headers,
        ).json()
        assert loaded["claimed_by"] == "agent-a"

    def test_claim_missing_returns_404(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            f"/api/v1/exploration-tasks/{uuid4()}/claim",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Submit findings
# ---------------------------------------------------------------------------


class TestSubmitFindings:
    def test_submit_findings_transitions_to_done(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers)
        client.post(
            f"/api/v1/exploration-tasks/{body['id']}/claim",
            headers=auth_headers,
            json={"agent_id": "agent-a"},
        )

        run_id = str(uuid4())
        response = client.post(
            f"/api/v1/exploration-tasks/{body['id']}/findings",
            headers=auth_headers,
            json={
                "summary": "ran 3 backtests",
                "backtest_run_ids": [run_id],
                "notes": ["volatility was unusual"],
            },
        )
        assert response.status_code == 200
        completed = response.json()
        assert completed["status"] == "DONE"
        assert completed["findings"]["summary"] == "ran 3 backtests"
        assert completed["findings"]["backtest_run_ids"] == [run_id]
        assert completed["findings"]["notes"] == ["volatility was unusual"]

    def test_submit_findings_on_open_returns_409(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers)
        response = client.post(
            f"/api/v1/exploration-tasks/{body['id']}/findings",
            headers=auth_headers,
            json={"summary": "premature"},
        )
        assert response.status_code == 409

    def test_submit_findings_empty_summary_returns_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _create_task(client, auth_headers)
        client.post(
            f"/api/v1/exploration-tasks/{body['id']}/claim",
            headers=auth_headers,
        )
        response = client.post(
            f"/api/v1/exploration-tasks/{body['id']}/findings",
            headers=auth_headers,
            json={"summary": ""},
        )
        assert response.status_code == 422

    def test_submit_findings_missing_task_returns_404(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            f"/api/v1/exploration-tasks/{uuid4()}/findings",
            headers=auth_headers,
            json={"summary": "x"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Auth coverage — all routes require auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_all_routes_require_auth(
        self,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        # Each tuple: (method, path, optional json body).
        cases: list[tuple[str, str, dict[str, object] | None]] = [
            ("POST", "/api/v1/exploration-tasks", {"prompt": "x"}),
            ("GET", "/api/v1/exploration-tasks", None),
            ("GET", f"/api/v1/exploration-tasks/{task_id}", None),
            ("DELETE", f"/api/v1/exploration-tasks/{task_id}", None),
            ("POST", f"/api/v1/exploration-tasks/{task_id}/claim", None),
            (
                "POST",
                f"/api/v1/exploration-tasks/{task_id}/findings",
                {"summary": "x"},
            ),
        ]
        for method, path, payload in cases:
            response = client.request(method, path, json=payload)
            # FastAPI's HTTPBearer security raises 403 when the header is
            # missing entirely (Bearer scheme not present), 401 when the
            # token fails verification. Both are auth-failure semantics.
            assert response.status_code in (401, 403), (
                f"{method} {path} returned {response.status_code} unexpectedly"
            )
