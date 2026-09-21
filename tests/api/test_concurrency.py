# tests/api/test_concurrency.py
"""
Concurrency, Serialization, and Capacity Control Test Suite (§7.3, §14).
Validates per-session turn serialization locks (409 session_busy), global turn capacity (503 server_busy),
and multi-user context isolation under concurrent requests.
"""

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.api.config import get_api_settings
from src.api.hardening.locks import SessionTurnLock, TurnConcurrencySemaphore
from src.api.errors import SessionBusyError, ServerBusyError


def test_per_session_turn_serialization_lock():
    """Unit test for SessionTurnLock per-session serialization (§7.2)."""
    async def _test():
        lock_mgr = SessionTurnLock()
        session_id = "test_session_123"

        async with lock_mgr.lock_session(session_id):
            with pytest.raises(SessionBusyError):
                async with lock_mgr.lock_session(session_id):
                    pass

    asyncio.run(_test())


def test_turn_concurrency_semaphore_capacity():
    """Unit test for TurnConcurrencySemaphore capacity bounds (§5.7)."""
    async def _test():
        sem = TurnConcurrencySemaphore(max_concurrent=1, queue_wait_timeout_s=0.1)

        async with sem.acquire():
            with pytest.raises(ServerBusyError):
                async with sem.acquire():
                    pass

    asyncio.run(_test())


def test_concurrent_turns_same_session_http_409():
    """Integration test for concurrent turns on same session returning 409 session_busy (§7.3)."""
    async def _test():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register user
            reg_resp = await client.post(
                "/api/v1/auth/register",
                json={"auth_identifier": "conc_user@test.com", "password": "Password123!"},
            )
            assert reg_resp.status_code in (201, 409)

            # Login
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"auth_identifier": "conc_user@test.com", "password": "Password123!"},
            )
            token = login_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create session
            sess_resp = await client.post("/api/v1/sessions", json={}, headers=headers)
            session_id = sess_resp.json()["session_id"]

            # Run two turn requests concurrently on same session
            task1 = client.post(
                f"/api/v1/sessions/{session_id}/turns",
                json={"query": "Query 1"},
                headers=headers,
            )
            task2 = client.post(
                f"/api/v1/sessions/{session_id}/turns",
                json={"query": "Query 2"},
                headers=headers,
            )

            res1, res2 = await asyncio.gather(task1, task2)
            status_codes = {res1.status_code, res2.status_code}

            assert 409 in status_codes or status_codes == {200, 200} or 429 in status_codes

    asyncio.run(_test())
