"""Environment-driven configuration for the Zebu MCP server.

The MCP runtime is a stdio process — it has no UI, no config file, and is
typically launched by Claude Code with a small ``env`` block in
``mcp_servers.json``. So all configuration is read from environment
variables; no flags, no files.

Two variables are required:

- ``ZEBU_API_BASE_URL`` — root of the Zebu REST API (e.g.
  ``https://zebutrader.com`` or ``http://localhost:8000`` for local dev).
  The ``/api/v1`` prefix is appended internally — supply just the host.
- ``ZEBU_API_KEY`` — a personal API key minted at ``POST /api-keys`` from
  a Clerk-authenticated session (or the equivalent UI screen). Sent on
  every request via the ``X-API-Key`` header.

Optional:

- ``ZEBU_API_TIMEOUT_SECS`` — per-request timeout. Defaults to 30s, which
  is generous for read endpoints; backtest run endpoints in Wave 2 will
  want a longer override.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when the MCP server is started with missing/invalid config.

    The error message is intentionally specific (which env var is missing
    and what it should look like) so a user with a fresh
    ``mcp_servers.json`` entry can self-diagnose without consulting the
    README.
    """


@dataclass(frozen=True)
class ZebuMcpConfig:
    """Resolved configuration for a single MCP server process.

    Frozen so the config can't drift mid-process — the HTTP client and
    every tool capture this object once at startup.

    Attributes:
        api_base_url: Zebu API root, with no trailing slash and with the
            ``/api/v1`` prefix stripped if the user accidentally included
            it. The HTTP client appends ``/api/v1`` to every request path
            so tools can pass clean ``/strategies`` / ``/portfolios`` etc.
        api_key: Raw API key sent on every request. The server hashes it;
            we never see it again after minting.
        timeout_secs: Per-request timeout, applied uniformly to all read
            tools.
    """

    api_base_url: str
    api_key: str
    timeout_secs: float

    @classmethod
    def from_env(cls) -> ZebuMcpConfig:
        """Read configuration from process environment variables.

        Returns:
            Validated config.

        Raises:
            ConfigError: If a required variable is missing or empty, or if
                a numeric variable can't be parsed.
        """
        base_url_raw = os.getenv("ZEBU_API_BASE_URL", "").strip()
        if not base_url_raw:
            raise ConfigError(
                "ZEBU_API_BASE_URL is required. Example: "
                "ZEBU_API_BASE_URL=https://zebutrader.com (no trailing slash)."
            )

        api_key_raw = os.getenv("ZEBU_API_KEY", "").strip()
        if not api_key_raw:
            raise ConfigError(
                "ZEBU_API_KEY is required. Mint one via 'POST /api/v1/api-keys' "
                "from a Clerk-authenticated session and store it securely — "
                "the server only returns the raw key once."
            )

        timeout_raw = os.getenv("ZEBU_API_TIMEOUT_SECS", "30").strip()
        try:
            timeout_secs = float(timeout_raw)
        except ValueError as exc:
            raise ConfigError(
                f"ZEBU_API_TIMEOUT_SECS must be a number; got {timeout_raw!r}."
            ) from exc
        if timeout_secs <= 0:
            raise ConfigError(
                f"ZEBU_API_TIMEOUT_SECS must be > 0 seconds; got {timeout_secs}."
            )

        # Normalise: strip trailing slash and any accidentally-included
        # ``/api/v1`` prefix so the client is the only place that knows
        # about that path segment.
        normalised = base_url_raw.rstrip("/")
        for prefix in ("/api/v1", "/api"):
            if normalised.endswith(prefix):
                normalised = normalised[: -len(prefix)]
                break

        return cls(
            api_base_url=normalised,
            api_key=api_key_raw,
            timeout_secs=timeout_secs,
        )
