"""Inbound rate limiter port — Phase F-6.

Abstracts the per-API-key rate-limit check on inbound HTTP routes (notably
``POST /backtests/run``). Distinct from
:class:`zebu.infrastructure.rate_limiter.RateLimiter`, which gates the
OUTBOUND Alpha Vantage path — that limiter is keyed by a fixed Redis
prefix, while this one is keyed per ``api_key_id`` so a single noisy
machine identity can't starve the rest of the platform.

References:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §6.2 — defaults,
  bypass-for-Clerk semantics, 429 response envelope.
- ``docs/agents/operating-manual.md`` §4.2 — the agent-side soft caps
  that interplay with the platform-layer limits this port enforces.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class RateLimitCheckResult:
    """Snapshot of a rate-limit check.

    Returned by :meth:`InboundRateLimiterPort.check_and_consume`. The
    audit-trail fields (``minute_used``, ``day_used``) describe the
    bucket state *after* the check — useful for the 429 error envelope so
    a caller can self-report "5/5 in last 60s; retry in 12s" without a
    second round-trip.

    Attributes:
        allowed: True when the request was permitted (and a token
            consumed); False when at least one bucket was exhausted.
        minute_limit: Maximum tokens per 60-second window (the
            configured cap).
        day_limit: Maximum tokens per 24-hour window (the configured
            cap).
        minute_used: Tokens consumed in the current 60-second window,
            including this request when ``allowed`` is True.
        day_used: Tokens consumed in the current 24-hour window,
            including this request when ``allowed`` is True.
        retry_after_seconds: Seconds until the *earliest* bucket has at
            least one token again. ``0.0`` when ``allowed`` is True. The
            value is rounded up to the next whole second by the API
            handler before populating the ``Retry-After`` header (per
            RFC 9110).
    """

    allowed: bool
    minute_limit: int
    day_limit: int
    minute_used: int
    day_used: int
    retry_after_seconds: float


class InboundRateLimiterPort(Protocol):
    """Per-API-key inbound rate limiter.

    The limiter applies BOTH a per-minute and a per-day cap; whichever
    fires first denies the request. Per design §6.2 + the operating
    manual §4.2:

    - Defaults: 5/min, 100/day. Configurable via
      ``ZEBU_BACKTEST_RATE_LIMIT_MIN`` / ``ZEBU_BACKTEST_RATE_LIMIT_DAY``.
    - Clerk Bearer requests (``api_key_id is None``) bypass the limiter
      entirely — human users are full-trust.
    - State is per-process in v1 (single-process backend). Horizontal
      scaling requires a shared store (Redis bucket); a deferred
      enhancement.

    Implementations live in :mod:`zebu.infrastructure.inbound_rate_limiter`.
    """

    async def check_and_consume(
        self,
        *,
        api_key_id: UUID | None,
    ) -> RateLimitCheckResult:
        """Atomically check both buckets and consume one token if available.

        When ``api_key_id`` is ``None`` (Clerk Bearer auth), the limiter
        returns :class:`RateLimitCheckResult` with ``allowed=True``,
        ``minute_used=0``, ``day_used=0``, ``retry_after_seconds=0.0`` —
        the limits don't apply to humans.

        Args:
            api_key_id: The API-key identity making the request, or
                ``None`` for Clerk Bearer auth (bypass).

        Returns:
            :class:`RateLimitCheckResult` describing the bucket state
            after the check. The caller is responsible for translating
            ``allowed=False`` into a 429 response with the standard
            error envelope + ``Retry-After`` header.
        """
        ...


__all__ = [
    "InboundRateLimiterPort",
    "RateLimitCheckResult",
]
