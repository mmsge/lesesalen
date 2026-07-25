"""Per-IP token bucket for the public API.

On working out the client IP: only central Caddy talks to this service, and
Caddy *appends* the immediate peer to `X-Forwarded-For`. So with exactly one
trusted proxy the real client is the **last** entry, and a client that forges
the header only pollutes the entries in front of it. Taking the first entry —
the usual reflex — would let anyone rotate their apparent identity per request
and walk straight through this limiter.
"""
from __future__ import annotations

import time

from . import config


class TokenBuckets:
    def __init__(self, rate: float, burst: int, max_tracked: int = 20000) -> None:
        self._rate = rate
        self._burst = float(burst)
        self._max_tracked = max_tracked
        self._buckets: dict[str, tuple[float, float]] = {}

    def allow(self, key: str, cost: float = 1.0) -> bool:
        now = time.monotonic()
        tokens, last = self._buckets.get(key, (self._burst, now))
        tokens = min(self._burst, tokens + (now - last) * self._rate)
        if tokens < cost:
            self._buckets[key] = (tokens, now)
            return False
        self._buckets[key] = (tokens - cost, now)
        if len(self._buckets) > self._max_tracked:
            self._evict(now)
        return True

    def _evict(self, now: float) -> None:
        """Drop buckets that have refilled — they carry no state worth keeping."""
        full_after = self._burst / self._rate if self._rate else 0
        stale = [k for k, (_t, last) in self._buckets.items() if now - last > full_after]
        for key in stale:
            self._buckets.pop(key, None)
        if len(self._buckets) > self._max_tracked:
            self._buckets.clear()


buckets = TokenBuckets(config.RATE_PER_SEC, config.RATE_BURST)


def client_ip(headers, fallback: str | None) -> str:
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[-1]  # see module docstring: last, not first
    return fallback or "unknown"
