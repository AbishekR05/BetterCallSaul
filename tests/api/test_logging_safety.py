# tests/api/test_logging_safety.py
"""
Automated Logging Safety Audit Test for HTTP API Layer (§10, §12).
Scans application logs to ensure no Authorization bearer headers or plaintext passwords are logged.
"""

import logging
import pytest
from fastapi.testclient import TestClient
from src.api.main import create_app
from src.api.dependencies import init_app_dependencies
from src.conversation.persistent_session_store import PersistentSessionStore
from src.auth.auth_provider import PasswordAuthProvider
from src.auth.authorization_service import AuthorizationService
from src.conversation.orchestrator import ConversationalOrchestrator


def test_api_logging_safety_no_secret_leakage(tmp_path, caplog):
    db_path = str(tmp_path / "logging_safety_test.sqlite")
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

    raw_password = "SuperSecretHTTPPassword123!"
    email = "http_audit@example.com"

    with caplog.at_level(logging.DEBUG):
        # Register
        client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": raw_password})
        # Login
        login_res = client.post("/api/v1/auth/login", json={"auth_identifier": email, "password": raw_password})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session & Get session
        sess_res = client.post("/api/v1/sessions", json={}, headers=headers)
        sid = sess_res.json()["session_id"]
        client.get(f"/api/v1/sessions/{sid}", headers=headers)

    logged_text = caplog.text

    # Verify plaintext password is not in logs
    assert raw_password not in logged_text

    # Verify raw token is not in logs
    assert token not in logged_text
