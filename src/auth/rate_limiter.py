# src/auth/rate_limiter.py
"""
Rate Limiter for Login Attempts (§12).
Tracks failed login attempts per auth_identifier within a rolling window.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List
import threading


class LoginRateLimiter:
    """
    Simple in-memory rate limiter tracking failed login attempts per auth_identifier.
    Thread-safe.
    """

    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window_seconds = window_minutes * 60
        self._lock = threading.Lock()
        # auth_identifier -> List of timestamp floats (seconds since epoch)
        self._failures: Dict[str, List[float]] = {}

    def record_failure(self, auth_identifier: str) -> None:
        """Records a failed login attempt for the given identifier."""
        identifier = auth_identifier.strip().lower()
        now = datetime.now(timezone.utc).timestamp()
        with self._lock:
            if identifier not in self._failures:
                self._failures[identifier] = []
            self._failures[identifier].append(now)

    def is_rate_limited(self, auth_identifier: str) -> bool:
        """Returns True if the identifier has exceeded max_attempts in the window."""
        identifier = auth_identifier.strip().lower()
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - self.window_seconds

        with self._lock:
            if identifier not in self._failures:
                return False

            # Prune old timestamps
            recent = [ts for ts in self._failures[identifier] if ts >= cutoff]
            self._failures[identifier] = recent

            return len(recent) >= self.max_attempts

    def reset(self, auth_identifier: str) -> None:
        """Resets failed attempt counters upon successful authentication."""
        identifier = auth_identifier.strip().lower()
        with self._lock:
            if identifier in self._failures:
                del self._failures[identifier]
