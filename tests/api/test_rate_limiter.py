# tests/api/test_rate_limiter.py
"""
Rate Limiter & Abuse Prevention Test Suite (§5, §14).
Validates sliding-window mechanics, LRU eviction, HTTP 429 enforcement, and Retry-After headers.
"""

import time
import pytest
from fastapi.testclient import TestClient

from src.api.hardening.rate_limiter import InMemoryRateLimiter, RateLimitDecision
from src.api.main import app
from src.api.config import get_api_settings


def test_in_memory_rate_limiter_sliding_window():
    """Unit test for sliding window rate limiter logic (§5.1)."""
    limiter = InMemoryRateLimiter(max_keys=10)

    # 3 requests allowed in 5 seconds
    res1 = limiter.check("test_key", max_requests=3, window_s=5)
    assert res1.allowed is True
    assert res1.retry_after_s == 0

    res2 = limiter.check("test_key", max_requests=3, window_s=5)
    assert res2.allowed is True

    res3 = limiter.check("test_key", max_requests=3, window_s=5)
    assert res3.allowed is True

    # 4th request exceeds limit
    res4 = limiter.check("test_key", max_requests=3, window_s=5)
    assert res4.allowed is False
    assert res4.retry_after_s >= 1


def test_rate_limiter_lru_eviction():
    """Verifies LRU eviction when key count exceeds max_keys (§5.1)."""
    limiter = InMemoryRateLimiter(max_keys=2)

    limiter.check("key1", max_requests=1, window_s=10)
    limiter.check("key2", max_requests=1, window_s=10)
    # Exceed capacity with key3 -> evicts oldest key1
    limiter.check("key3", max_requests=1, window_s=10)

    # key1 should be evicted, so a new check gets fresh count
    res = limiter.check("key1", max_requests=1, window_s=10)
    assert res.allowed is True


def test_register_rate_limit_http_429():
    """Integration test verifying 429 rate_limited on register endpoint (§5.3)."""
    client = TestClient(app)
    settings = get_api_settings()

    # Temporarily set low register limit for testing
    settings.rate_limit_rules["register_ip"] = {"requests": 2, "window_s": 60}

    res1 = client.post("/api/v1/auth/register", json={"auth_identifier": "user_rl1@test.com", "password": "Password123!"})
    res2 = client.post("/api/v1/auth/register", json={"auth_identifier": "user_rl2@test.com", "password": "Password123!"})
    res3 = client.post("/api/v1/auth/register", json={"auth_identifier": "user_rl3@test.com", "password": "Password123!"})

    assert res3.status_code == 429
    assert res3.json()["error_code"] == "rate_limited"
    assert "Retry-After" in res3.headers
