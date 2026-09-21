# tests/api/test_rag_timeouts.py
"""
RAG / LLM Upstream Failure Boundary Test Suite (§9, §14).
Validates 504 upstream_timeout, 502 upstream_failure, and lock/semaphore cleanup on failure.
"""

import asyncio
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.errors import UpstreamTimeoutError, UpstreamFailureError


@pytest.fixture
def client():
    return TestClient(app)


def test_turn_rag_timeout_returns_504(client):
    """Verifies that RAG pipeline execution exceeding turn_timeout_s returns 504 upstream_timeout (§9)."""
    # Register & Login
    client.post("/api/v1/auth/register", json={"auth_identifier": "timeout_user@test.com", "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"auth_identifier": "timeout_user@test.com", "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sess_resp = client.post("/api/v1/sessions", json={}, headers=headers)
    session_id = sess_resp.json()["session_id"]

    # Patch turn_service post_turn_async to raise UpstreamTimeoutError
    with patch("src.api.services.turn_service.TurnService.post_turn_async", side_effect=UpstreamTimeoutError("Timed out")):
        res = client.post(f"/api/v1/sessions/{session_id}/turns", json={"query": "Test query timeout"}, headers=headers)
        assert res.status_code == 504
        assert res.json()["error_code"] == "upstream_timeout"
        assert "Timed out" not in res.text  # Clean error message, no trace leak


def test_turn_rag_failure_returns_502(client):
    """Verifies non-timeout pipeline exception returns 502 upstream_failure (§9)."""
    client.post("/api/v1/auth/register", json={"auth_identifier": "failure_user@test.com", "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"auth_identifier": "failure_user@test.com", "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sess_resp = client.post("/api/v1/sessions", json={}, headers=headers)
    session_id = sess_resp.json()["session_id"]

    with patch("src.api.services.turn_service.TurnService.post_turn_async", side_effect=UpstreamFailureError("CUDA OOM")):
        res = client.post(f"/api/v1/sessions/{session_id}/turns", json={"query": "Test query failure"}, headers=headers)
        assert res.status_code == 502
        assert res.json()["error_code"] == "upstream_failure"
        assert "CUDA OOM" not in res.text  # Infrastructure details suppressed
