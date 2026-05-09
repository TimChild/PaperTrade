"""Hashing primitive for API keys.

Why HMAC-SHA256 (and not bcrypt/argon2):

- API keys are high-entropy server-issued tokens (256+ bits of randomness),
  not user-chosen passwords. The slow-hash work-factor that protects
  against rainbow tables and dictionary attacks on weak passwords is
  irrelevant here — a 256-bit random secret is already infeasible to
  brute-force at any work factor.
- Every authenticated request hits this primitive. With bcrypt at the
  recommended cost (~100ms), every API call would carry that latency
  before the route handler even runs. That's untenable for an MCP server
  doing read-heavy data lookups.
- HMAC with a server-side secret (the *pepper*) prevents an attacker who
  steals the DB from running a precomputed-table attack against the
  hashes — they'd also need the pepper, which is held in env config and
  never written to the DB.

The pepper is read from ``API_KEY_HMAC_SECRET``. In production the
``get_api_key_hasher`` factory raises if it's missing or set to the
default placeholder; in tests we fall back to a fixed test pepper so
the in-memory adapter can hash without env wiring.

Format of the raw key string:

- ``zk_`` prefix (so it's grep-able in logs and visually distinct from
  Bearer JWTs, which are base64url-encoded JSON triples)
- 32 bytes of randomness, base64url-encoded (43 chars, no padding)

Total length: 46 chars. Looks like ``zk_<43chars>``.
"""

import hmac
import os
import secrets
from dataclasses import dataclass

API_KEY_PREFIX = "zk_"
"""Visible prefix. Lets grep-the-logs surface accidental key leaks."""

_RAW_KEY_BYTES = 32
"""32 random bytes => 256 bits of entropy. Same order as a Clerk session
token, comfortably beyond brute-forceable."""


def generate_raw_key() -> str:
    """Generate a fresh raw API key.

    Returns:
        A new random key in the form ``zk_<43-char-base64url>``.
    """
    suffix = secrets.token_urlsafe(_RAW_KEY_BYTES)
    return f"{API_KEY_PREFIX}{suffix}"


@dataclass(frozen=True)
class ApiKeyHasher:
    """HMAC-SHA256 hasher with a server-side pepper.

    The pepper is the per-deployment secret. The hasher is stateless and
    cheap to construct — typically wired once at app startup via
    :func:`get_api_key_hasher`.

    Attributes:
        secret: The HMAC secret (pepper). Treat as sensitive — never log,
            never serialise.
    """

    secret: str

    def hash(self, raw_key: str) -> str:
        """Compute the deterministic hash of a raw key.

        Args:
            raw_key: The plaintext key string (with or without prefix —
                callers should pass the full string the user presents).

        Returns:
            Hex-encoded HMAC-SHA256 digest (64 chars).
        """
        digest = hmac.new(
            self.secret.encode("utf-8"),
            raw_key.encode("utf-8"),
            digestmod="sha256",
        )
        return digest.hexdigest()

    def verify(self, raw_key: str, expected_hash: str) -> bool:
        """Constant-time comparison of a raw key's hash against ``expected_hash``.

        Args:
            raw_key: The presented plaintext key.
            expected_hash: The hash stored on the persisted ApiKey record.

        Returns:
            True iff the hashes match (constant-time).
        """
        return hmac.compare_digest(self.hash(raw_key), expected_hash)


_TEST_PEPPER_PLACEHOLDER = "test"
"""Sentinel value treated like 'unset' in production — same convention
as the Clerk secret. Allows tests to set a fixed test pepper."""


def get_api_key_hasher() -> ApiKeyHasher:
    """Build the singleton :class:`ApiKeyHasher` from environment config.

    Reads ``API_KEY_HMAC_SECRET``. In production (``APP_ENV=production``),
    a missing or placeholder value is a hard configuration error — same
    posture as :func:`get_auth_port` for ``CLERK_SECRET_KEY``: surface the
    misconfiguration as a 500 on first request rather than silently
    accept any key.

    Returns:
        Configured :class:`ApiKeyHasher`.

    Raises:
        RuntimeError: If APP_ENV=production and ``API_KEY_HMAC_SECRET``
            is missing or set to the placeholder ``"test"``.
    """
    secret = os.getenv("API_KEY_HMAC_SECRET", "")
    app_env = os.getenv("APP_ENV", "development")

    if not secret or secret == _TEST_PEPPER_PLACEHOLDER:
        if app_env == "production":
            raise RuntimeError(
                "API_KEY_HMAC_SECRET must be configured when APP_ENV=production. "
                "Refusing to accept the placeholder pepper."
            )
        # Tests / dev: stable placeholder pepper. Tests that exercise the
        # hashing path explicitly should still set their own value to keep
        # them independent of the host env.
        secret = "test-api-key-pepper-do-not-use-in-production"

    return ApiKeyHasher(secret=secret)
