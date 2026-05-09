# Phase C2 — API-key authentication path

**Date**: 2026-05-09
**Author**: backend-swe
**Spec**: `docs/planning/agent-platform-proposal.md` §C2; `agent_docs/audits/2026-05-09/security.md` P1-4

## Summary

Lands the API-key authentication path so machine identities (agents,
scheduled tasks, MCP servers) can authenticate without going through
Clerk. Both schemes coexist at the dependency layer — the Clerk path
is unchanged.

## Domain / persistence

- New entity `ApiKey` (`backend/src/zebu/domain/entities/api_key.py`)
  with fields: `id`, `user_id`, `clerk_user_id` (so the original Clerk
  ID round-trips), `label`, `key_hash`, `scopes`, `created_at`,
  `last_used_at`, `revoked_at`, `expires_at`. Lifecycle helpers:
  `is_revoked`, `is_expired`, `is_active`, `has_scope`.
- New value object `ApiKeyScope` (StrEnum: `READ`, `TRADE`, `ADMIN`).
- New domain exception `InvalidApiKeyError`.
- New repository port `ApiKeyRepository`
  (`backend/src/zebu/application/ports/api_key_repository.py`) with
  in-memory and SQLModel implementations.
- Alembic migration `c001_add_api_keys` creates `api_keys` table with
  unique index on `key_hash` and lookup index on `user_id`. No FK on
  `user_id` — Clerk owns the user record.

## Hashing primitive

HMAC-SHA256 with a server-side pepper (`API_KEY_HMAC_SECRET`).

- Why not bcrypt: API keys are 256-bit random tokens. The slow-hash
  work factor that protects weak passwords against rainbow tables is
  irrelevant; bcrypt would add ~100ms latency to every authenticated
  call.
- Why not plain SHA256: a DB leak would let an attacker run a
  precomputed-table attack. The pepper makes that infeasible.
- Constant-time comparison via `hmac.compare_digest`.
- Production fails fast if pepper is missing or set to the placeholder
  value (same posture as `CLERK_SECRET_KEY`).

Raw key shape: `zk_<43-char-base64url>` — 256 bits of entropy. The
`zk_` prefix is grep-able in logs to surface accidental leaks.

## Auth flow

`get_current_user` in `dependencies.py` is now composite:

1. `Authorization: Bearer <jwt>` → `ClerkAuthAdapter`.
2. `Authorization: ApiKey <key>` or `X-API-Key: <key>` →
   `ApiKeyAuthAdapter`.
3. Quality-of-life: `Authorization: Bearer zk_<key>` is also routed to
   the API-key adapter so agents using HTTP libraries that hardcode the
   `Bearer` scheme can present an API key without remembering the
   `ApiKey` scheme name.

Both paths return the same `AuthenticatedUser` shape; downstream code
is unchanged. The API-key path returns `clerk_user_id` on
`AuthenticatedUser.id`, so `get_current_user_id` continues to produce
the same deterministic UUID via `uuid5(NAMESPACE_DNS, …)`.

Failures are unified — every API-key auth failure (unknown, revoked,
expired, malformed) raises `InvalidTokenError("Invalid API key")` with
no information leakage.

## Endpoints (Clerk-gated only)

- `POST /api/v1/api-keys` — mints a new key. Returns the raw key once;
  the server keeps only the hash.
- `GET /api/v1/api-keys` — lists the user's keys (no raw values).
- `DELETE /api/v1/api-keys/{id}` — revokes (sets `revoked_at`).

API-key authenticated requests are explicitly rejected with 403 on this
router — agents cannot mint other agents.

## Scope helper

`require_scope(ApiKeyScope.TRADE)` builds a FastAPI dependency that:

- Passes Clerk Bearer requests through (humans are full-trust).
- Requires API-key requests to carry the named scope or `ADMIN`.

Wired but not applied broadly — Phase D follow-up will sweep through
and apply read/trade granularity per route.

## Test parameterization flip

`backend/tests/conftest.py::_AUTH_SCHEMES_CURRENT` now expands to
`("bearer", "api_key_authorization", "api_key_header")`. The
`auth_headers_for_scheme` fixture auto-runs every test that depends on
it across all three transports. Today only
`test_auth_scheme_parameterization.py` opts in (its tests now run 3×
instead of 1×). Existing integration tests use the Bearer-only
`auth_headers` fixture and are unaffected.

A seeded test API key (`test-token-default`, owned by
`test-user-default` with all three scopes) makes the parameterization
work end-to-end against the same default test user the Bearer path
authenticates as.

## Tests

- `backend/tests/unit/domain/entities/test_api_key.py` — 27 tests, 100%
  entity coverage.
- `backend/tests/unit/adapters/auth/test_api_key_adapter.py` — 11
  tests, 100% adapter coverage (success path, every rejection mode,
  empty / whitespace tokens).
- `backend/tests/unit/adapters/auth/test_api_key_hasher.py` — 14 tests
  pinning down hash determinism, constant-time verify, and the
  production-pepper-required check.
- `backend/tests/integration/test_api_keys_api.py` — 15 tests covering
  mint / list / revoke, raw-key-once, scope validation, agent-can't-
  mint-agent, and end-to-end round-trip with a freshly-minted key.
- `backend/tests/integration/test_auth_scheme_parameterization.py` —
  rewritten to assert all three transports authenticate; negative
  cases for unknown/missing/empty keys.

Full suite: 1090 passed, no regressions. `task quality:backend` clean
(format, ruff, pyright strict, coverage).

## Deferred to Phase D / E

- Per-key rate limiting.
- Audit log of API-key writes (who/when/what).
- Frontend UI for listing/minting/revoking keys.
- Applying `require_scope` broadly across routes.

## Files added / changed

Added:
- `backend/src/zebu/domain/entities/api_key.py`
- `backend/src/zebu/domain/value_objects/api_key_scope.py`
- `backend/src/zebu/adapters/auth/api_key_adapter.py`
- `backend/src/zebu/adapters/auth/api_key_hasher.py`
- `backend/src/zebu/adapters/outbound/database/api_key_model.py`
- `backend/src/zebu/adapters/outbound/database/api_key_repository.py`
- `backend/src/zebu/adapters/inbound/api/api_keys.py`
- `backend/src/zebu/application/ports/api_key_repository.py`
- `backend/src/zebu/application/ports/in_memory_api_key_repository.py`
- `backend/migrations/versions/c001_add_api_keys_table.py`
- Tests: see Tests section.

Changed:
- `backend/src/zebu/domain/entities/__init__.py`
- `backend/src/zebu/domain/value_objects/__init__.py`
- `backend/src/zebu/domain/exceptions.py`
- `backend/src/zebu/adapters/inbound/api/dependencies.py`
- `backend/src/zebu/main.py`
- `backend/migrations/env.py`
- `backend/tests/conftest.py`
- `backend/tests/integration/test_auth_scheme_parameterization.py`
- `docs/architecture/authentication.md`
- `CLAUDE.md`
- `.env.example`, `.env.production.example`
- Pre-existing `UP042` lint errors fixed in
  `schemas/errors.py` and `queries/get_portfolio_performance.py`
  (StrEnum migration) so the suite goes green.
