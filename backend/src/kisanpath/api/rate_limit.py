"""Rate-limit port with development memory and multi-replica Redis adapters."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimiter(Protocol):
    async def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision: ...
    async def close(self) -> None: ...


class InMemoryRateLimiter:
    """Bounded fixed-window limiter for one-process local/judge mode."""

    def __init__(self, *, clock: Callable[[], float] = time.time, max_keys: int = 10_000) -> None:
        self._clock = clock
        self._max_keys = max_keys
        self._windows: dict[str, tuple[int, int]] = {}

    async def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = int(self._clock())
        window = now // window_seconds
        stored_window, count = self._windows.get(key, (window, 0))
        if stored_window != window:
            count = 0
        count += 1
        if len(self._windows) >= self._max_keys and key not in self._windows:
            expired = [item for item, (bucket, _) in self._windows.items() if bucket != window]
            for item in expired:
                self._windows.pop(item, None)
            if len(self._windows) >= self._max_keys:
                self._windows.pop(next(iter(self._windows)))
        self._windows[key] = (window, count)
        retry_after = window_seconds - (now % window_seconds)
        return RateLimitDecision(count <= limit, max(0, limit - count), retry_after)

    async def close(self) -> None:
        return None


class RedisRateLimiter:
    """Atomic fixed-window adapter using a Redis-compatible async client."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        bucket = int(time.time()) // window_seconds
        redis_key = f"kisanpath:rate:{bucket}:{key}"
        count = int(
            await self._client.eval(
                "local n=redis.call('INCR',KEYS[1]); "
                "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
                1,
                redis_key,
                window_seconds + 1,
            )
        )
        retry_after = window_seconds - (int(time.time()) % window_seconds)
        return RateLimitDecision(count <= limit, max(0, limit - count), retry_after)

    async def close(self) -> None:
        await self._client.aclose()
