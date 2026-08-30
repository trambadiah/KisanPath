from __future__ import annotations

from kisanpath.api.rate_limit import InMemoryRateLimiter


async def test_fixed_window_rate_limit_is_deterministic() -> None:
    now = 120.0
    limiter = InMemoryRateLimiter(clock=lambda: now)

    first = await limiter.check("synthetic", limit=2, window_seconds=60)
    second = await limiter.check("synthetic", limit=2, window_seconds=60)
    blocked = await limiter.check("synthetic", limit=2, window_seconds=60)

    assert first.allowed and first.remaining == 1
    assert second.allowed and second.remaining == 0
    assert not blocked.allowed and blocked.retry_after_seconds == 60
