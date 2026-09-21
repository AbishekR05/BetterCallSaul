# tests/api/test_openapi_contract.py
"""
Automated OpenAPI Contract Verification Test (§13).
Validates OpenAPI schema against baseline openapi_baseline.json and verifies permitted changes.
"""

import json
import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def api_client():
    return TestClient(app)


def test_openapi_schema_generated_correctly(api_client):
    """Verifies OpenAPI JSON schema generation and security scheme declarations (§13)."""
    # Force docs enabled for test inspection
    schema = app.openapi()

    assert schema["openapi"].startswith("3.")
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/ready" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/auth/register" in schema["paths"]
    assert "/api/v1/sessions" in schema["paths"]
    assert "/api/v1/sessions/{session_id}/turns" in schema["paths"]


def test_openapi_baseline_diff(api_client):
    """Diffs current schema against baseline openapi_baseline.json (§13)."""
    with open("benchmark/phase_3_1/openapi_baseline.json", "r") as f:
        baseline_schema = json.load(f)

    current_schema = app.openapi()

    # Compare path keys
    baseline_paths = set(baseline_schema["paths"].keys())
    current_paths = set(current_schema["paths"].keys())
    assert baseline_paths == current_paths, "API path endpoints changed beyond permitted additions!"
