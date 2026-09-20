# tests/api/test_auth_routes.py
"""
Unit tests for /api/v1/auth/ register, login, and logout endpoints (§5, §12).
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
def client(tmp_path):
    db_path = str(tmp_path / "auth_routes_test.sqlite")
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
    return TestClient(app)


def test_register_and_login_flow(client):
    email = "lawyer_api@example.com"
    password = "StrongPassword123!"

    # 1. Register
    reg_res = client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": password})
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["auth_identifier"] == email.lower()
    assert "user_id" in user_data

    # 2. Login
    login_res = client.post("/api/v1/auth/login", json={"auth_identifier": email, "password": password})
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    token = token_data["access_token"]

    # 3. Logout
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 204

    # 4. Subsequent use of revoked token fails with 401
    fail_logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert fail_logout.status_code == 401
    assert fail_logout.json()["error_code"] == "authentication_required"


def test_duplicate_registration_returns_409(client):
    email = "duplicate_api@example.com"
    password = "Password123!"

    client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": password})
    res2 = client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": password})

    assert res2.status_code == 409
    assert res2.json()["error_code"] == "identifier_exists"


def test_invalid_login_returns_401(client):
    email = "invalid_login@example.com"
    password = "ValidPassword123!"

    client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": password})

    # Wrong password -> 401 generic
    res = client.post("/api/v1/auth/login", json={"auth_identifier": email, "password": "WrongPassword"})
    assert res.status_code == 401
    assert res.json()["error_code"] == "authentication_required"
