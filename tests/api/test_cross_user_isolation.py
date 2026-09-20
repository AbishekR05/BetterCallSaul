# tests/api/test_cross_user_isolation.py
"""
Zero-Tolerance HTTP Cross-User Session Isolation Test Suite (§6, §12).
Verifies that User A's token cannot read, write turns, or delete User B's session over HTTP.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import create_app
from src.api.dependencies import init_app_dependencies
from src.conversation.persistent_session_store import PersistentSessionStore
from src.auth.auth_provider import PasswordAuthProvider
from src.auth.authorization_service import AuthorizationService
from src.conversation.orchestrator import ConversationalOrchestrator


@pytest.fixture
def http_isolation_context(tmp_path):
    db_path = str(tmp_path / "http_isolation_test.sqlite")
    store = PersistentSessionStore(backend="sqlite", sqlite_path=db_path)
    provider = PasswordAuthProvider(backend="sqlite", sqlite_path=db_path)
    authz = AuthorizationService(session_store=store)
    orchestrator = ConversationalOrchestrator(session_store=store)

    init_app_dependencies(
        session_store=store,
        auth_provider=provider,
        authorization_service=authz,
        orchestrator=orchestrator,
    )

    app = create_app()
    client = TestClient(app)

    # Register User A
    client.post("/api/v1/auth/register", json={"auth_identifier": "usera@example.com", "password": "Password123!"})
    token_a = client.post("/api/v1/auth/login", json={"auth_identifier": "usera@example.com", "password": "Password123!"}).json()["access_token"]

    # Register User B
    client.post("/api/v1/auth/register", json={"auth_identifier": "userb@example.com", "password": "Password123!"})
    token_b = client.post("/api/v1/auth/login", json={"auth_identifier": "userb@example.com", "password": "Password123!"}).json()["access_token"]

    return client, token_a, token_b


def test_zero_tolerance_http_cross_user_access(http_isolation_context):
    client, token_a, token_b = http_isolation_context

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a session
    sess_a_res = client.post("/api/v1/sessions", json={}, headers=headers_a)
    session_a_id = sess_a_res.json()["session_id"]

    # User B creates a session
    sess_b_res = client.post("/api/v1/sessions", json={}, headers=headers_b)
    session_b_id = sess_b_res.json()["session_id"]

    # 1. User B attempts GET /sessions/{session_a_id} -> 403 Forbidden
    get_cross = client.get(f"/api/v1/sessions/{session_a_id}", headers=headers_b)
    assert get_cross.status_code == 403
    assert get_cross.json()["error_code"] == "session_not_accessible"

    # 2. User B attempts POST /sessions/{session_a_id}/turns -> 403 Forbidden
    turn_cross = client.post(
        f"/api/v1/sessions/{session_a_id}/turns",
        json={"query": "Cross user query attempt"},
        headers=headers_b,
    )
    assert turn_cross.status_code == 403
    assert turn_cross.json()["error_code"] == "session_not_accessible"

    # 3. User B attempts DELETE /sessions/{session_a_id} -> 403 Forbidden
    del_cross = client.delete(f"/api/v1/sessions/{session_a_id}", headers=headers_b)
    assert del_cross.status_code == 403
    assert del_cross.json()["error_code"] == "session_not_accessible"

    # 4. User A's session is still intact and accessible by User A
    get_owner = client.get(f"/api/v1/sessions/{session_a_id}", headers=headers_a)
    assert get_owner.status_code == 200
    assert get_owner.json()["session_id"] == session_a_id
