# tests/api/test_error_model.py
"""
Unit tests for API Error Model uniformity (§11, §12).
Verifies that all error paths return the standard APIError schema { error_code, message, request_id }.
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
    db_path = str(tmp_path / "error_model_test.sqlite")
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


def assert_api_error_shape(response_json: dict, expected_codes: tuple):
    """Assertion helper verifying uniform APIError payload structure (§11)."""
    assert "error_code" in response_json
    assert "message" in response_json
    assert "request_id" in response_json
    assert response_json["error_code"] in expected_codes


def test_400_validation_error_shape(client):
    # Missing required field 'auth_identifier'
    res = client.post("/api/v1/auth/register", json={"password": "123"})
    assert res.status_code in (400, 422)
    assert_api_error_shape(res.json(), ("validation_error",))


def test_401_authentication_error_shape(client):
    res = client.get("/api/v1/sessions")
    assert res.status_code == 401
    assert_api_error_shape(res.json(), ("unauthenticated", "authentication_required"))


def test_403_authorization_error_shape(client):
    # Authenticate User A
    client.post("/api/v1/auth/register", json={"auth_identifier": "usera@example.com", "password": "Password123!"})
    login_res = client.post("/api/v1/auth/login", json={"auth_identifier": "usera@example.com", "password": "Password123!"})
    token = login_res.json()["access_token"]

    fake_session_id = "00000000-0000-0000-0000-000000000000"
    res = client.get(f"/api/v1/sessions/{fake_session_id}", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code in (403, 404)
    assert_api_error_shape(res.json(), ("session_not_found", "session_not_accessible"))


def test_409_identifier_exists_error_shape(client):
    client.post("/api/v1/auth/register", json={"auth_identifier": "dupe@example.com", "password": "Password123!"})
    res = client.post("/api/v1/auth/register", json={"auth_identifier": "dupe@example.com", "password": "Password123!"})

    assert res.status_code == 409
    assert_api_error_shape(res.json(), ("conflict", "identifier_exists"))
