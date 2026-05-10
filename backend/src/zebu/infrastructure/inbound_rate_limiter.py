"""In-memory inbound rate limiter — Phase F-6.

Implements :class:`InboundRateLimiterPort` with a token-bucket per
``api_key_id``. State is held in-process; v1 deliberately ships without
a Redis backing store so a single backend deploy can ship the guardrail
without infra changes. Horizontal-scaling deployments need a shared
store (Redis sorted-set bucket); a deferred enhancement.

The implementation tracks two sliding-window buckets (minute + day) per
key as a :class:`collections.deque` of consumption timestamps. On every
check, expired timestamps fall off the front of each deque, the current
deque length is the "used" count, and a request is allowed when both
counts are below their respective caps.

Stdlib only — no Redis, no async lock library — matching the F-6 brief.
A :class:`threading.Lock` per key serialises check + consume so two
concurrent requests for the same key can't both pass when only one
token remains.

Defaults match the design doc (§6.2):

- 5 requests per 60 seconds.
- 100 requests per 86400 seconds (24 hours).

Both limits are enforced; whichever bucket is empty first denies.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Final
from uuid import UUID

from zebu.application.ports.inbound_rate_limiter_port import RateLimitCheckResult

_MINUTE_WINDOW_SECONDS: Final[float] = 60.0
_DAY_WINDOW_SECONDS: Final[float] = 86400.0


class InMemoryInboundRateLimiter:
    """In-process token-bucket rate limiter keyed by API-key UUID.

    Uses sliding-window buckets (a deque of recent consume timestamps
    per key) so the "5 per minute" rule is enforced over any
    60-second sliding window, not a fixed-edge minute (which would let
    a noisy caller burst 10 requests across the boundary between two
    minutes).

    Locking: one :class:`Lock` per key. The check-and-consume operation
    is fully serialised per key. Across keys, requests proceed in
    parallel — typical contention is one in-flight request per
    machine identity, so per-key locking is cheap.

    Attributes:
        minute_limit: Tokens per 60-second window.
        day_limit: Tokens per 86400-second window.
    """

    def __init__(
        self,
        *,
        minute_limit: int = 5,
        day_limit: int = 100,
    ) -> None:
        """Initialise the limiter.

        Args:
            minute_limit: Tokens per 60-second window. Must be ``>= 1``.
            day_limit: Tokens per 24-hour window. Must be ``>= 1``.

        Raises:
            ValueError: If either limit is non-positive.
        """
        if minute_limit < 1:
            raise ValueError(f"minute_limit must be >= 1; got {minute_limit}")
        if day_limit < 1:
            raise ValueError(f"day_limit must be >= 1; got {day_limit}")
        self.minute_limit = minute_limit
        self.day_limit = day_limit
        # Per-key sliding-window buckets. Both deques hold monotonic
        # ``time.monotonic()`` timestamps; the minute bucket is a strict
        # subset of the day bucket in flow order, but we keep them
        # separate so eviction stays O(1) on each.
        self._minute_bucket: dict[UUID, deque[float]] = defaultdict(deque)
        self._day_bucket: dict[UUID, deque[float]] = defaultdict(deque)
        # Per-key lock factory. ``defaultdict`` is not thread-safe for
        # creation; we serialise creation with a top-level lock.
        self._key_locks: dict[UUID, Lock] = {}
        self._key_locks_creation = Lock()

    def _get_lock(self, api_key_id: UUID) -> Lock:
        """Look up (or create) the per-key lock atomically."""
        with self._key_locks_creation:
            lock = self._key_locks.get(api_key_id)
            if lock is None:
                lock = Lock()
                self._key_locks[api_key_id] = lock
            return lock

    async def check_and_consume(
        self,
        *,
        api_key_id: UUID | None,
    ) -> RateLimitCheckResult:
        """Check both windows and consume a token when both have headroom.

        See :meth:`InboundRateLimiterPort.check_and_consume` for the
        contract. The Clerk-Bearer bypass (``api_key_id is None``)
        returns a zero-state result immediately without touching the
        buckets.
        """
        if api_key_id is None:
            return RateLimitCheckResult(
                allowed=True,
                minute_limit=self.minute_limit,
                day_limit=self.day_limit,
                minute_used=0,
                day_used=0,
                retry_after_seconds=0.0,
            )

        now = time.monotonic()
        minute_cutoff = now - _MINUTE_WINDOW_SECONDS
        day_cutoff = now - _DAY_WINDOW_SECONDS

        lock = self._get_lock(api_key_id)
        with lock:
            minute_q = self._minute_bucket[api_key_id]
            day_q = self._day_bucket[api_key_id]

            # Evict expired timestamps from the front of both deques.
            while minute_q and minute_q[0] <= minute_cutoff:
                minute_q.popleft()
            while day_q and day_q[0] <= day_cutoff:
                day_q.popleft()

            minute_used = len(minute_q)
            day_used = len(day_q)

            if minute_used < self.minute_limit and day_used < self.day_limit:
                minute_q.append(now)
                day_q.append(now)
                return RateLimitCheckResult(
                    allowed=True,
                    minute_limit=self.minute_limit,
                    day_limit=self.day_limit,
                    minute_used=minute_used + 1,
                    day_used=day_used + 1,
                    retry_after_seconds=0.0,
                )

            # Denied — compute retry-after as "time until the FRONT
            # entry in the binding bucket expires". The binding bucket
            # is whichever one is currently at-or-over its cap.
            retry_after = 0.0
            if minute_used >= self.minute_limit and minute_q:
                retry_after = max(
                    retry_after,
                    minute_q[0] + _MINUTE_WINDOW_SECONDS - now,
                )
            if day_used >= self.day_limit and day_q:
                retry_after = max(
                    retry_after,
                    day_q[0] + _DAY_WINDOW_SECONDS - now,
                )
            return RateLimitCheckResult(
                allowed=False,
                minute_limit=self.minute_limit,
                day_limit=self.day_limit,
                minute_used=minute_used,
                day_used=day_used,
                retry_after_seconds=max(retry_after, 0.0),
            )

    async def refund(
        self,
        *,
        api_key_id: UUID | None,
    ) -> None:
        """Refund the most recently consumed token in each bucket.

        Implementation notes: pops the **most recent** (right-end) entry
        from each bucket. We don't try to identify the exact consumed
        token (we don't track per-request ids) — the LIFO discipline is
        correct in the typical case where refund is called immediately
        after the consume that's being undone.
        """
        if api_key_id is None:
            return

        lock = self._get_lock(api_key_id)
        with lock:
            minute_q = self._minute_bucket[api_key_id]
            day_q = self._day_bucket[api_key_id]
            if minute_q:
                minute_q.pop()
            if day_q:
                day_q.pop()

    def reset(self) -> None:
        """Clear all bucket state.

        Used by tests to isolate cases. Not part of the port.
        """
        with self._key_locks_creation:
            self._minute_bucket.clear()
            self._day_bucket.clear()
            self._key_locks.clear()


__all__ = ["InMemoryInboundRateLimiter"]
