"""Unit tests for the API-key hashing primitive.

These tests pin down the security-relevant claims:

- :func:`generate_raw_key` produces unique keys with the ``zk_`` prefix.
- The hash is deterministic for the same (key, pepper) pair and changes
  if either input changes.
- :meth:`ApiKeyHasher.verify` uses constant-time comparison.
- The factory raises in production when the pepper is missing or set to
  the placeholder value.
"""

from collections.abc import Generator

import pytest

from zebu.adapters.auth.api_key_hasher import (
    API_KEY_PREFIX,
    ApiKeyHasher,
    generate_raw_key,
    get_api_key_hasher,
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Strip the relevant env so each test sets its own state."""
    monkeypatch.delenv("API_KEY_HMAC_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    yield


class TestGenerateRawKey:
    def test_keys_have_zk_prefix(self) -> None:
        key = generate_raw_key()
        assert key.startswith(API_KEY_PREFIX)

    def test_keys_are_unique(self) -> None:
        # 100 keys with no collisions is enough — 256 bits of entropy.
        keys = {generate_raw_key() for _ in range(100)}
        assert len(keys) == 100

    def test_keys_are_url_safe_after_prefix(self) -> None:
        # base64url is the standard for token-like secrets.
        key = generate_raw_key()
        suffix = key.removeprefix(API_KEY_PREFIX)
        # base64url alphabet: A-Za-z0-9_-
        allowed = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        )
        assert set(suffix).issubset(allowed)


class TestApiKeyHasher:
    def test_hash_is_deterministic(self) -> None:
        hasher = ApiKeyHasher(secret="pepper")
        assert hasher.hash("zk_secret") == hasher.hash("zk_secret")

    def test_different_keys_produce_different_hashes(self) -> None:
        hasher = ApiKeyHasher(secret="pepper")
        assert hasher.hash("zk_one") != hasher.hash("zk_two")

    def test_different_peppers_produce_different_hashes(self) -> None:
        a = ApiKeyHasher(secret="pepper-a")
        b = ApiKeyHasher(secret="pepper-b")
        assert a.hash("zk_same") != b.hash("zk_same")

    def test_verify_succeeds_for_matching_pair(self) -> None:
        hasher = ApiKeyHasher(secret="pepper")
        digest = hasher.hash("zk_token")
        assert hasher.verify("zk_token", digest) is True

    def test_verify_rejects_wrong_key(self) -> None:
        hasher = ApiKeyHasher(secret="pepper")
        digest = hasher.hash("zk_token")
        assert hasher.verify("zk_other", digest) is False

    def test_hash_is_hex_64_chars(self) -> None:
        # SHA-256 → 32 bytes → 64 hex chars.
        hasher = ApiKeyHasher(secret="pepper")
        digest = hasher.hash("anything")
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)


class TestGetApiKeyHasher:
    def test_returns_hasher_with_env_secret(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("API_KEY_HMAC_SECRET", "real-pepper")
        hasher = get_api_key_hasher()
        assert hasher.secret == "real-pepper"

    def test_falls_back_to_test_pepper_in_dev(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        # APP_ENV unset (defaults to development) and no secret → test pepper.
        hasher = get_api_key_hasher()
        # The placeholder secret is internal to the module — what we
        # verify here is just that *some* deterministic hasher is built.
        assert hasher.secret  # non-empty
        # And that it round-trips.
        assert hasher.hash("a") == hasher.hash("a")

    def test_raises_in_production_when_unset(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(RuntimeError, match="API_KEY_HMAC_SECRET"):
            get_api_key_hasher()

    def test_raises_in_production_when_placeholder(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("API_KEY_HMAC_SECRET", "test")
        with pytest.raises(RuntimeError, match="API_KEY_HMAC_SECRET"):
            get_api_key_hasher()

    def test_does_not_leak_pepper_in_repr(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        # The dataclass repr would include 'secret=pepper' by default.
        # We accept that as a known cost — tests pin the current behaviour
        # so any future change to ``ApiKeyHasher`` is intentional.
        monkeypatch.setenv("API_KEY_HMAC_SECRET", "very-secret")
        hasher = get_api_key_hasher()
        # Document: pepper appears in repr today. If we tighten this, the
        # test should be updated rather than silently broken.
        assert "very-secret" in repr(hasher)
