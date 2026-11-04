"""
Sliding-window rate limiter.

In-memory for local dev. In production, back this with Redis
(INCR + EXPIRE, or a sorted set for a true sliding window) so it works
across multiple API server instances.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.config import PLANS, PlanLimits, PlanName


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_in_seconds: float


class InMemoryRateLimiter:
    """Keyed by (account_id, bucket). Not safe across multiple processes —
    replace with Redis before running more than one worker."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check_and_record(
        self, account_id: str, bucket: str, limit: int | None, window_seconds: int | None
    ) -> RateLimitResult:
        if limit is None:
            return RateLimitResult(allowed=True, remaining=-1, reset_in_seconds=0)

        now = time.monotonic()
        key = (account_id, bucket)
        hits = self._hits[key]

        if window_seconds is not None:
            cutoff = now - window_seconds
            while hits and hits[0] < cutoff:
                hits.popleft()

        if len(hits) >= limit:
            reset_in = window_seconds - (now - hits[0]) if window_seconds else 0
            return RateLimitResult(allowed=False, remaining=0, reset_in_seconds=max(reset_in, 0))

        hits.append(now)
        remaining = limit - len(hits)
        return RateLimitResult(allowed=True, remaining=remaining, reset_in_seconds=0)


rate_limiter = InMemoryRateLimiter()


def enforce_rate_limit(account_id: str, plan: PlanName, bucket: str) -> None:
    """
    Dev/test path: in-memory, single-process only.

    Production path: app/core/redis_rate_limit.py's check_and_record, which
    is safe across multiple API server processes. Swap the import below
    (or branch on settings.env) once Redis is actually deployed -- shipping
    this in-memory version behind multiple uvicorn workers will silently
    under-enforce limits, since each worker has its own counters.
    """
    limits: PlanLimits = PLANS[plan]

    if bucket == "search":
        limit = limits.search_records_per_window
    elif bucket == "enrich":
        limit = limits.enrichment_calls_per_window
    else:
        limit = None

    result = rate_limiter.check_and_record(
        account_id=account_id,
        bucket=bucket,
        limit=limit,
        window_seconds=limits.window_seconds,
    )

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded for '{bucket}' on plan '{plan.value}'. "
                f"Resets in ~{result.reset_in_seconds:.0f}s. Upgrade your plan "
                f"for a higher ceiling."
            ),
        )
