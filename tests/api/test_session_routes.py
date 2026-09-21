# tests/api/test_session_routes.py
"""
Unit tests for /api/v1/sessions CRUD endpoints (§5, §12).
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from src.api.main import create_app
from src.api.dependencies import init_app_dependencies
from src.conversation.persistent_session_store import PersistentSessionStore
from src.auth.auth_provider import PasswordAuthProvider
from src.auth.authorization_service import AuthorizationService
from src.conversation.orchestrator import ConversationalOrchestrator


@pytest.fixture
def api_context(tmp_path):
    db_path = str(tmp_path / "sessions_test.sqlite")
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

    # Register & login test user
    email = "session_user@example.com"
    passw = "Password123!"
    client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": passw})
    login_res = client.post("/api/v1/auth/login", json={"auth_identifier": email, "password": passw})
    token = login_res.json()["access_token"]

    return client, token


def test_session_crud_lifecycle(api_context):
    client, token = api_context
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Session
    create_res = client.post("/api/v1/sessions", json={}, headers=headers)
    assert create_res.status_code == 201
    session_data = create_res.json()
    session_id = session_data["session_id"]

    # 2. Get Session
    get_res = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == session_id

    # 3. List Sessions
    list_res = client.get("/api/v1/sessions", headers=headers)
    assert list_res.status_code == 200
    sessions_list = list_res.json()["sessions"]
    assert len(sessions_list) == 1
    assert sessions_list[0]["session_id"] == session_id

    # 4. Delete Session
    del_res = client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
    assert del_res.status_code == 204

    # 5. Get deleted session returns 404/403 generic error
    get_del = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert get_del.status_code in (404, 403)
    assert get_del.json()["error_code"] in ("session_not_found", "session_not_accessible")
