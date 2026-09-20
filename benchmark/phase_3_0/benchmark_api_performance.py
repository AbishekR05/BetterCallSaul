# benchmark/phase_3_0/benchmark_api_performance.py
"""
Performance Baseline & Added Latency Overhead Benchmark for Phase 3.0 API (§13).
Isolates API HTTP boundary overhead from downstream RAG execution.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import numpy as np
from fastapi.testclient import TestClient
from src.api.main import create_app
from src.api.dependencies import init_app_dependencies
from src.conversation.persistent_session_store import PersistentSessionStore
from src.auth.auth_provider import PasswordAuthProvider
from src.auth.authorization_service import AuthorizationService
from src.conversation.orchestrator import ConversationalOrchestrator
from tests.conversation.test_persistent_session_store import create_dummy_turn


class BenchmarkMockOrchestrator(ConversationalOrchestrator):
    """Fast, deterministic orchestrator double with dynamic turn indexing for API benchmarking."""

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


def run_api_benchmark(iterations: int = 100):
    db_path = "benchmark/phase_3_0/bench_api.sqlite"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    store = PersistentSessionStore(backend="sqlite", sqlite_path=db_path)
    provider = PasswordAuthProvider(backend="sqlite", sqlite_path=db_path)
    authz = AuthorizationService(session_store=store)
    orchestrator = BenchmarkMockOrchestrator(session_store=store)

    init_app_dependencies(
        session_store=store,
        auth_provider=provider,
        authorization_service=authz,
        orchestrator=orchestrator,
    )

    app = create_app()
    client = TestClient(app)

    email = "bench_api@example.com"
    passw = "BenchPassword123!"

    client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": passw})

    # 1. Benchmark POST /auth/login Latency
    login_latencies = []
    tokens = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = client.post("/api/v1/auth/login", json={"auth_identifier": email, "password": passw})
        t1 = time.perf_counter()
        login_latencies.append((t1 - t0) * 1000.0)
        tokens.append(res.json()["access_token"])

    headers = {"Authorization": f"Bearer {tokens[0]}"}

    # 2. Benchmark POST /sessions Creation Latency
    create_latencies = []
    session_ids = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = client.post("/api/v1/sessions", json={}, headers=headers)
        t1 = time.perf_counter()
        create_latencies.append((t1 - t0) * 1000.0)
        session_ids.append(res.json()["session_id"])

    # 3. Benchmark GET /sessions/{id} Retrieval Latency
    test_sid = session_ids[0]
    get_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = client.get(f"/api/v1/sessions/{test_sid}", headers=headers)
        t1 = time.perf_counter()
        get_latencies.append((t1 - t0) * 1000.0)

    # 4. Benchmark GET /sessions Listing Latency
    list_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = client.get("/api/v1/sessions", headers=headers)
        t1 = time.perf_counter()
        list_latencies.append((t1 - t0) * 1000.0)

    # 5. Benchmark POST /sessions/{id}/turns Added API Layer Latency Overhead
    turn_latencies = []
    for i in range(iterations):
        t0 = time.perf_counter()
        res = client.post(
            f"/api/v1/sessions/{test_sid}/turns",
            json={"query": f"Benchmark legal query turn #{i}?"},
            headers=headers,
        )
        t1 = time.perf_counter()
        turn_latencies.append((t1 - t0) * 1000.0)

    print("\n================ Phase 3.0 API Performance Benchmark Results ================")
    print(f"Iterations: {iterations}")
    print(f"POST /auth/login Latency:          P50 = {np.percentile(login_latencies, 50):.3f} ms | P95 = {np.percentile(login_latencies, 95):.3f} ms")
    print(f"POST /sessions Creation:           P50 = {np.percentile(create_latencies, 50):.3f} ms | P95 = {np.percentile(create_latencies, 95):.3f} ms")
    print(f"GET /sessions/{{id}} Retrieval:      P50 = {np.percentile(get_latencies, 50):.3f} ms | P95 = {np.percentile(get_latencies, 95):.3f} ms")
    print(f"GET /sessions Listing (100 items): P50 = {np.percentile(list_latencies, 50):.3f} ms | P95 = {np.percentile(list_latencies, 95):.3f} ms")
    print(f"POST /turns API Layer Overhead:   P50 = {np.percentile(turn_latencies, 50):.3f} ms | P95 = {np.percentile(turn_latencies, 95):.3f} ms")
    print("=============================================================================\n")


if __name__ == "__main__":
    run_api_benchmark()
