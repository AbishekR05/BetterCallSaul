# src/api/hardening/rate_limiter.py
"""
In-Memory Bounded Rate Limiter with Sliding Window Protocol (§5).
Supports per-IP, per-identifier, and per-user limits with LRU eviction of idle keys.
"""

import time
import threading
from typing import Dict, Tuple, Optional, Protocol
from dataclasses import dataclass
from collections import OrderedDict


@dataclass
class RateLimitDecision:
    allowed: bool
    retry_after_s: int = 0


class RateLimiter(Protocol):
    """Protocol interface for rate limiting providers (§5.1)."""

    def check(self, key: str, max_requests: int, window_s: int) -> RateLimitDecision:
        ...


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter with thread-safe operations
    and LRU cleanup of expired keys (§5.1, §5.6).
    """

    def __init__(self, max_keys: int = 10000):
        self.max_keys = max_keys
        # Map key -> OrderedDict of timestamp -> count
        self._store: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = threading.Lock()

    def check(self, key: str, max_requests: int, window_s: int) -> RateLimitDecision:
        if max_requests <= 0 or window_s <= 0:
            return RateLimitDecision(allowed=True, retry_after_s=0)

        now = time.time()
        window_start = now - window_s

        with self._lock:
            # LRU maintenance: move key to end
            if key in self._store:
                timestamps = self._store[key]
                self._store.move_to_end(key)
            else:
                if len(self._store) >= self.max_keys:
                    # Evict oldest key
                    self._store.popitem(last=False)
                timestamps = []
                self._store[key] = timestamps

            # Prune timestamps outside window
            valid_timestamps = [ts for ts in timestamps if ts > window_start]
            self._store[key] = valid_timestamps

            if len(valid_timestamps) < max_requests:
                valid_timestamps.append(now)
                return RateLimitDecision(allowed=True, retry_after_s=0)

            # Rate limit exceeded: calculate retry_after_s
            oldest_in_window = valid_timestamps[0]
            retry_after_s = max(1, int(oldest_in_window + window_s - now) + 1)
            return RateLimitDecision(allowed=False, retry_after_s=retry_after_s)

    def reset(self):
        """Clears all stored rate limit entries (for testing)."""
        with self._lock:
            self._store.clear()


class DisabledRateLimiter:
    """No-op rate limiter when backend is disabled."""

    def check(self, key: str, max_requests: int, window_s: int) -> RateLimitDecision:
        return RateLimitDecision(allowed=True, retry_after_s=0)

    def reset(self):
        pass



_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter(backend: str = "memory") -> RateLimiter:
    """Returns singleton rate limiter instance based on backend configuration (§5.1)."""
    global _global_limiter
    if _global_limiter is None:
        if backend == "disabled":
            _global_limiter = DisabledRateLimiter()
        else:
            _global_limiter = InMemoryRateLimiter()
    return _global_limiter
