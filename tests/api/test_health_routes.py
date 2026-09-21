# tests/api/test_health_routes.py
"""
Unit tests for /health and /ready routes (§5, §11, §12).
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
    db_path = str(tmp_path / "health_test.sqlite")
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


def test_health_liveness_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_readiness_endpoint(client):
    response = client.get("/ready")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ready"
    assert "checks" in res_data
    assert res_data["checks"]["session_db"] == "ok"
