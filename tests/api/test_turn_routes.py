# tests/api/test_turn_routes.py
"""
Unit tests for POST /api/v1/sessions/{session_id}/turns endpoint (§5, §8, §12).
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
from tests.conversation.test_persistent_session_store import create_dummy_turn


class MockOrchestrator(ConversationalOrchestrator):
    """Fast, deterministic orchestrator double for API route testing."""

    def __init__(self, session_store):
        super().__init__(session_store=session_store)

    def handle_turn(self, user_id: str, session_id: str, user_query: str):
        from src.conversation.schemas import ConversationTurnResult, ContextSelectionTrace
        sess = self.session_store.get_session(session_id)
        next_idx = (sess.turn_count if sess else 0) + 1
        dummy_turn = create_dummy_turn(next_idx, user_query)
        self.session_store.add_turn(session_id, dummy_turn)

        return ConversationTurnResult(
            session_id=session_id,
            turn=dummy_turn,
            context_selector_debug=ContextSelectionTrace(),
        )


@pytest.fixture
def turn_context(tmp_path):
    db_path = str(tmp_path / "turn_routes_test.sqlite")
    store = PersistentSessionStore(backend="sqlite", sqlite_path=db_path)
    provider = PasswordAuthProvider(backend="sqlite", sqlite_path=db_path)
    authz = AuthorizationService(session_store=store)
    orchestrator = MockOrchestrator(session_store=store)

    init_app_dependencies(
        session_store=store,
        auth_provider=provider,
        authorization_service=authz,
        orchestrator=orchestrator,
    )

    app = create_app()
    client = TestClient(app)

    email = "turn_user@example.com"
    passw = "Password123!"
    client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": passw})
    login_res = client.post("/api/v1/auth/login", json={"auth_identifier": email, "password": passw})
    token = login_res.json()["access_token"]

    return client, token, store


def test_post_turn_success(turn_context):
    client, token, store = turn_context
    headers = {"Authorization": f"Bearer {token}"}

    # Create session
    create_res = client.post("/api/v1/sessions", json={}, headers=headers)
    session_id = create_res.json()["session_id"]

    # Submit conversation turn
    turn_res = client.post(
        f"/api/v1/sessions/{session_id}/turns",
        json={"query": "What is minimum wage?"},
        headers=headers,
    )

    assert turn_res.status_code == 200
    data = turn_res.json()
    assert data["session_id"] == session_id
    assert data["turn_index"] == 1
    assert "answer_summary" in data
    assert "answer_detail" in data
    assert "applicable_jurisdiction" in data
    # Public response omits generation_metadata and safety_flags per §7
    assert "generation_metadata" not in data
    assert "safety_flags" not in data
