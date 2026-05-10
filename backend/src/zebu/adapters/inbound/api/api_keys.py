"""API key management routes.

Phase C2: Clerk-gated endpoints that let a human user mint, list, and
revoke API keys for their machine identities (agents, scheduled tasks,
MCP servers).

Important security properties:

- These endpoints are *Clerk-gated only*. An API-key request that hits
  ``POST /api-keys`` is rejected with 403 — agents cannot mint other
  agents. The check uses :class:`AuthenticatedUser.id` shape: Clerk IDs
  are arbitrary strings (e.g. ``"user_2abc..."``) while the API-key
  adapter returns the same string round-tripped from the persisted
  record. We distinguish by re-checking the request headers — only a
  Bearer JWT (no API-key header) makes it through.
- The raw key is returned **once**, only on the create response. The
  server keeps just the HMAC hash; a lost key must be revoked and
  re-minted.
- Listing never returns the raw key.
"""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from zebu.adapters.auth.api_key_hasher import generate_raw_key, get_api_key_hasher
from zebu.adapters.inbound.api.dependencies import (
    ApiKeyRepositoryDep,
    extract_api_key_from_request,
    get_current_user,
)
from zebu.application.ports.auth_port import AuthenticatedUser
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.value_objects.api_key_scope import ApiKeyScope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


async def require_clerk_bearer(
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Reject API-key authenticated requests on this router.

    The whole point of these endpoints is that they're the human-only
    surface for minting/revoking machine credentials. An agent that's
    been granted an API key must not be able to create other API keys.

    Raises:
        HTTPException: 403 if the request was authenticated with an API key.
    """
    # The composite get_current_user routes Bearer-prefixed API keys to
    # the API-key adapter, but never the other direction. So if the
    # request is presenting any API-key-shaped header, we reject.
    if extract_api_key_from_request(request) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key management requires Clerk authentication",
        )
    # Also reject `Authorization: Bearer zk_...` — that gets routed to the
    # API-key adapter by get_current_user, but defence-in-depth.
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if auth_header:
        scheme, _, value = auth_header.partition(" ")
        if scheme.lower() == "bearer" and value.startswith("zk_"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key management requires Clerk authentication",
            )
    return current_user


ClerkBearerUser = Annotated[AuthenticatedUser, Depends(require_clerk_bearer)]


# Request / response models -------------------------------------------------


class CreateApiKeyRequest(BaseModel):
    """Request to mint a new API key."""

    label: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(
        ...,
        min_length=1,
        description="One or more of: read, trade, admin",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional ISO-8601 UTC expiry. Omit for no expiry.",
    )


class CreateApiKeyResponse(BaseModel):
    """Response after minting an API key.

    The ``raw_key`` field is included exactly once — on creation. After
    this response, the server has no way to recover it. Store it
    securely client-side.
    """

    id: UUID
    label: str
    scopes: list[str]
    raw_key: str = Field(
        ...,
        description=(
            "The raw API key. Returned only on creation; the server keeps "
            "only the hash. Store it securely — it cannot be retrieved later."
        ),
    )
    created_at: str
    expires_at: str | None


class ApiKeySummary(BaseModel):
    """API-key list-view summary. Never includes the raw key."""

    id: UUID
    label: str
    scopes: list[str]
    created_at: str
    last_used_at: str | None
    revoked_at: str | None
    expires_at: str | None
    is_active: bool


class ApiKeyListResponse(BaseModel):
    """Paginated-style list of an authenticated user's API keys."""

    items: list[ApiKeySummary]
    total: int


# Helpers -------------------------------------------------------------------


def _parse_scopes(scope_strings: list[str]) -> frozenset[ApiKeyScope]:
    """Parse a list of scope strings into the typed frozenset.

    Raises:
        HTTPException: 422 on any unknown scope value.
    """
    parsed: set[ApiKeyScope] = set()
    for raw in scope_strings:
        try:
            parsed.add(ApiKeyScope(raw))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid scope: {raw!r}. Valid scopes: "
                    f"{', '.join(s.value for s in ApiKeyScope)}"
                ),
            ) from exc
    return frozenset(parsed)


def _to_summary(api_key: ApiKey) -> ApiKeySummary:
    """Convert a domain :class:`ApiKey` to an :class:`ApiKeySummary`."""
    return ApiKeySummary(
        id=api_key.id,
        label=api_key.label,
        scopes=sorted(s.value for s in api_key.scopes),
        created_at=api_key.created_at.isoformat(),
        last_used_at=(
            api_key.last_used_at.isoformat()
            if api_key.last_used_at is not None
            else None
        ),
        revoked_at=(
            api_key.revoked_at.isoformat() if api_key.revoked_at is not None else None
        ),
        expires_at=(
            api_key.expires_at.isoformat() if api_key.expires_at is not None else None
        ),
        is_active=api_key.is_active(),
    )


# Routes --------------------------------------------------------------------


@router.post(
    "",
    response_model=CreateApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    request_body: CreateApiKeyRequest,
    repo: ApiKeyRepositoryDep,
    current_user: ClerkBearerUser,
) -> CreateApiKeyResponse:
    """Mint a new API key for the authenticated Clerk user.

    The raw key is included in the response **once** and never persisted
    in plaintext. Subsequent listings only return metadata.
    """
    scopes = _parse_scopes(request_body.scopes)

    raw_key = generate_raw_key()
    hasher = get_api_key_hasher()
    key_hash = hasher.hash(raw_key)

    # Convert Clerk user-id string → deterministic UUID owner using the
    # same uuid5 hashing get_current_user_id uses, so existing ownership
    # checks line up regardless of which auth path is used afterwards.
    from uuid import NAMESPACE_DNS, uuid5

    owner_uuid = uuid5(NAMESPACE_DNS, current_user.id)

    api_key = ApiKey(
        id=uuid4(),
        user_id=owner_uuid,
        clerk_user_id=current_user.id,
        label=request_body.label,
        key_hash=key_hash,
        scopes=scopes,
        created_at=datetime.now(UTC),
        last_used_at=None,
        revoked_at=None,
        expires_at=request_body.expires_at,
    )

    await repo.save(api_key)

    logger.info(
        "Minted API key",
        extra={
            "api_key_id": str(api_key.id),
            "label": api_key.label,
            "scopes": sorted(s.value for s in api_key.scopes),
        },
    )

    return CreateApiKeyResponse(
        id=api_key.id,
        label=api_key.label,
        scopes=sorted(s.value for s in api_key.scopes),
        raw_key=raw_key,
        created_at=api_key.created_at.isoformat(),
        expires_at=(
            api_key.expires_at.isoformat() if api_key.expires_at is not None else None
        ),
    )


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    repo: ApiKeyRepositoryDep,
    current_user: ClerkBearerUser,
) -> ApiKeyListResponse:
    """List API keys for the authenticated Clerk user.

    Includes revoked and expired keys so the user can audit history.
    Never returns the raw key.
    """
    from uuid import NAMESPACE_DNS, uuid5

    owner_uuid = uuid5(NAMESPACE_DNS, current_user.id)
    keys = await repo.get_by_user(owner_uuid)
    summaries = [_to_summary(k) for k in keys]
    return ApiKeyListResponse(items=summaries, total=len(summaries))


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: UUID,
    repo: ApiKeyRepositoryDep,
    current_user: ClerkBearerUser,
) -> None:
    """Revoke an API key.

    Sets ``revoked_at`` rather than hard-deleting, preserving audit
    history. A revoked key cannot authenticate any subsequent request.
    """
    record = await repo.get(api_key_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key not found: {api_key_id}",
        )

    if record.clerk_user_id != current_user.id:
        # Don't leak existence — same response as not found.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key not found: {api_key_id}",
        )

    if record.is_revoked():
        # Idempotent: revoking a revoked key is a no-op success.
        return

    revoked = ApiKey(
        id=record.id,
        user_id=record.user_id,
        clerk_user_id=record.clerk_user_id,
        label=record.label,
        key_hash=record.key_hash,
        scopes=record.scopes,
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        revoked_at=datetime.now(UTC),
        expires_at=record.expires_at,
    )
    await repo.save(revoked)

    logger.info(
        "Revoked API key",
        extra={"api_key_id": str(record.id)},
    )
