"""Tests for :class:`InMemoryInboundRateLimiter` (Phase F-6).

Behavior-focused — the sliding-window contract is exercised against
``time.monotonic``-driven token consumption. Tests use a small monkey-
patched clock to fast-forward the window without sleeping.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from uuid import uuid4

import pytest

from zebu.infrastructure.inbound_rate_limiter import InMemoryInboundRateLimiter


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[float], None]]:
    """Replace ``time.monotonic`` with a controllable clock.

    Yields a ``set(seconds)`` callable that pins the clock at the given
    monotonic-second value. Each call to ``time.monotonic()`` returns
    whatever was last set.
    """
    current = {"value": 1000.0}

    def fake() -> float:
        return current["value"]

    def setter(seconds: float) -> None:
        current["value"] = seconds

    import time as time_module

    monkeypatch.setattr(time_module, "monotonic", fake)
    yield setter


class TestInitialisation:
    """Construction validates limits."""

    def test_invalid_minute_limit_rejected(self) -> None:
        with pytest.raises(ValueError, match="minute_limit must be >= 1"):
            InMemoryInboundRateLimiter(minute_limit=0, day_limit=100)

    def test_invalid_day_limit_rejected(self) -> None:
        with pytest.raises(ValueError, match="day_limit must be >= 1"):
            InMemoryInboundRateLimiter(minute_limit=5, day_limit=0)


class TestBypass:
    """Clerk-Bearer requests (api_key_id=None) bypass the limiter."""

    async def test_none_api_key_always_allowed(self) -> None:
        limiter = InMemoryInboundRateLimiter(minute_limit=1, day_limit=1)
        # First call exhausts a hypothetical 1/1 limit; bypass should
        # still permit subsequent calls.
        for _ in range(50):
            result = await limiter.check_and_consume(api_key_id=None)
            assert result.allowed is True
            assert result.minute_used == 0
            assert result.day_used == 0
            assert result.retry_after_seconds == 0.0


class TestTokenConsumption:
    """Per-key token accounting under the sliding window."""

    async def test_first_request_consumes_one_token(self) -> None:
        limiter = InMemoryInboundRateLimiter(minute_limit=5, day_limit=100)
        api_key_id = uuid4()
        result = await limiter.check_and_consume(api_key_id=api_key_id)
        assert result.allowed is True
        assert result.minute_used == 1
        assert result.day_used == 1

    async def test_exhausting_minute_bucket_denies_next_request(
        self, fake_clock: Callable[[float], None]
    ) -> None:
        fake_clock(1000.0)
        limiter = InMemoryInboundRateLimiter(minute_limit=3, day_limit=1000)
        api_key_id = uuid4()

        for _ in range(3):
            result = await limiter.check_and_consume(api_key_id=api_key_id)
            assert result.allowed is True

        denied = await limiter.check_and_consume(api_key_id=api_key_id)
        assert denied.allowed is False
        assert denied.minute_used == 3
        assert denied.minute_limit == 3
        assert denied.retry_after_seconds > 0

    async def test_minute_bucket_refills_after_window(
        self, fake_clock: Callable[[float], None]
    ) -> None:
        fake_clock(1000.0)
        limiter = InMemoryInboundRateLimiter(minute_limit=2, day_limit=1000)
        api_key_id = uuid4()

        # Burn the bucket at t=1000.
        await limiter.check_and_consume(api_key_id=api_key_id)
        await limiter.check_and_consume(api_key_id=api_key_id)
        denied = await limiter.check_and_consume(api_key_id=api_key_id)
        assert denied.allowed is False

        # Advance 61s — both prior timestamps fall out of the 60s window.
        fake_clock(1061.0)
        refilled = await limiter.check_and_consume(api_key_id=api_key_id)
        assert refilled.allowed is True
        assert refilled.minute_used == 1

    async def test_day_bucket_denies_independently(
        self, fake_clock: Callable[[float], None]
    ) -> None:
        """Exhaust day bucket while minute bucket has headroom — denied."""
        fake_clock(1000.0)
        # 5/min, 2/day — once the day bucket fills, requests are denied
        # even though the minute bucket has 3 slots free.
        limiter = InMemoryInboundRateLimiter(minute_limit=5, day_limit=2)
        api_key_id = uuid4()

        await limiter.check_and_consume(api_key_id=api_key_id)
        await limiter.check_and_consume(api_key_id=api_key_id)
        denied = await limiter.check_and_consume(api_key_id=api_key_id)

        assert denied.allowed is False
        assert denied.day_used == 2
        assert denied.day_limit == 2
        # Retry-after should be on the order of a day (the day bucket
        # binds) — assert it's >> 60s.
        assert denied.retry_after_seconds > 60.0

    async def test_per_key_isolation(self, fake_clock: Callable[[float], None]) -> None:
        """One noisy API key doesn't starve another."""
        fake_clock(1000.0)
        limiter = InMemoryInboundRateLimiter(minute_limit=2, day_limit=10)
        noisy = uuid4()
        quiet = uuid4()

        # Burn noisy's bucket.
        await limiter.check_and_consume(api_key_id=noisy)
        await limiter.check_and_consume(api_key_id=noisy)
        noisy_denied = await limiter.check_and_consume(api_key_id=noisy)
        assert noisy_denied.allowed is False

        # Quiet key still has its full allowance.
        quiet_result = await limiter.check_and_consume(api_key_id=quiet)
        assert quiet_result.allowed is True
        assert quiet_result.minute_used == 1


class TestRetryAfterAccuracy:
    """The retry_after value should reflect the binding bucket's age."""

    async def test_retry_after_reflects_minute_window(
        self, fake_clock: Callable[[float], None]
    ) -> None:
        fake_clock(1000.0)
        limiter = InMemoryInboundRateLimiter(minute_limit=1, day_limit=1000)
        api_key_id = uuid4()
        await limiter.check_and_consume(api_key_id=api_key_id)

        # 25 seconds elapsed — the original token expires 35s from now.
        fake_clock(1025.0)
        denied = await limiter.check_and_consume(api_key_id=api_key_id)
        assert denied.allowed is False
        # Allow a small fudge for floating-point.
        assert 34.9 <= denied.retry_after_seconds <= 35.1

    async def test_retry_after_uses_longer_of_two_buckets(
        self, fake_clock: Callable[[float], None]
    ) -> None:
        """When both buckets are blocking, the longer one wins."""
        fake_clock(1000.0)
        limiter = InMemoryInboundRateLimiter(minute_limit=1, day_limit=1)
        api_key_id = uuid4()
        await limiter.check_and_consume(api_key_id=api_key_id)
        denied = await limiter.check_and_consume(api_key_id=api_key_id)
        assert denied.allowed is False
        # Both buckets are blocking; day window is much longer.
        assert denied.retry_after_seconds > 60.0


class TestReset:
    """The reset() helper clears all per-key state."""

    async def test_reset_clears_all_state(self) -> None:
        limiter = InMemoryInboundRateLimiter(minute_limit=1, day_limit=10)
        api_key_id = uuid4()
        await limiter.check_and_consume(api_key_id=api_key_id)
        denied = await limiter.check_and_consume(api_key_id=api_key_id)
        assert denied.allowed is False

        limiter.reset()
        refreshed = await limiter.check_and_consume(api_key_id=api_key_id)
        assert refreshed.allowed is True


class TestRefund:
    """``refund`` pops the most-recently-consumed token from each bucket.

    Routes call this when the work the rate-limit token authorised fails
    before completing (e.g. ``TickerNotFoundError`` from the backtest
    engine). Without a refund, failed requests still count against the
    cap and an agent retrying after a transient error exhausts its
    quota on errors.
    """

    async def test_refund_restores_capacity(self) -> None:
        limiter = InMemoryInboundRateLimiter(minute_limit=2, day_limit=10)
        api_key_id = uuid4()

        # Burn the minute bucket.
        await limiter.check_and_consume(api_key_id=api_key_id)
        await limiter.check_and_consume(api_key_id=api_key_id)
        denied = await limiter.check_and_consume(api_key_id=api_key_id)
        assert denied.allowed is False

        # Refund one — capacity returns.
        await limiter.refund(api_key_id=api_key_id)
        allowed = await limiter.check_and_consume(api_key_id=api_key_id)
        assert allowed.allowed is True
        assert allowed.minute_used == 2

    async def test_refund_is_noop_for_clerk_bypass(self) -> None:
        limiter = InMemoryInboundRateLimiter(minute_limit=1, day_limit=1)
        # No state for None; refund is a silent no-op.
        await limiter.refund(api_key_id=None)
        # Bucket state for a real key remains usable.
        api_key_id = uuid4()
        result = await limiter.check_and_consume(api_key_id=api_key_id)
        assert result.allowed is True

    async def test_refund_is_idempotent_when_buckets_empty(self) -> None:
        limiter = InMemoryInboundRateLimiter(minute_limit=2, day_limit=10)
        api_key_id = uuid4()
        # No prior consume — refund should be a silent no-op.
        await limiter.refund(api_key_id=api_key_id)
        # Subsequent normal use still works.
        result = await limiter.check_and_consume(api_key_id=api_key_id)
        assert result.allowed is True
        assert result.minute_used == 1

    async def test_refund_per_key_isolation(self) -> None:
        limiter = InMemoryInboundRateLimiter(minute_limit=1, day_limit=10)
        a = uuid4()
        b = uuid4()
        await limiter.check_and_consume(api_key_id=a)
        await limiter.check_and_consume(api_key_id=b)
        # Refund a; b's bucket should be untouched.
        await limiter.refund(api_key_id=a)
        denied_b = await limiter.check_and_consume(api_key_id=b)
        assert denied_b.allowed is False
        allowed_a = await limiter.check_and_consume(api_key_id=a)
        assert allowed_a.allowed is True
