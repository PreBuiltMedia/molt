"""
Redis-backed sliding-window-ish rate limiter, safe across multiple API
server processes (unlike InMemoryRateLimiter in rate_limit.py, which is
dev-only).

Uses a simple fixed-window counter (INCR + EXPIRE) rather than a true
sliding window -- slightly bursty at window boundaries, but far cheaper than
a sorted-set sliding window and plenty accurate for a 5-hour window. Swap in
a sorted-set implementation later if you need exactness at the edges.
"""
from __future__ import annotations

from dataclasses import dataclass

import redis

from app.core.config import settings

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_in_seconds: float


def check_and_record(account_id: str, bucket: str, limit: int | None, window_seconds: int | None) -> RateLimitResult:
    if limit is None:
        return RateLimitResult(allowed=True, remaining=-1, reset_in_seconds=0)

    r = get_redis()
    key = f"ratelimit:{account_id}:{bucket}"

    # Atomic increment; set expiry only on first increment in the window so
    # we don't keep sliding the window forward on every request.
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    count, ttl = pipe.execute()

    if ttl == -1 and window_seconds is not None:
        r.expire(key, window_seconds)
        ttl = window_seconds

    if count > limit:
        return RateLimitResult(allowed=False, remaining=0, reset_in_seconds=max(ttl, 0))

    return RateLimitResult(allowed=True, remaining=max(limit - count, 0), reset_in_seconds=0)
