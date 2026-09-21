# benchmark/phase_3_1/benchmark_api_hardening.py
"""
Phase 3.1 API Hardening Performance Benchmark Suite (§15).
Measures P50/P95 latency deltas for lightweight routes, rate-limiting overhead,
concurrency scaling, and turn API boundary overhead.
"""

import time
import json
import statistics
import asyncio
from typing import List, Dict, Any
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.config import get_api_settings
from src.api.dependencies import init_app_dependencies, get_rate_limiter
from src.conversation.persistent_session_store import PersistentSessionStore
from src.auth.auth_provider import PasswordAuthProvider
from src.auth.authorization_service import AuthorizationService
from src.conversation.orchestrator import ConversationalOrchestrator
from tests.api.test_turn_routes import MockOrchestrator


def run_benchmark():
    print("=" * 60)
    print("PHASE 3.1 API HARDENING PERFORMANCE BENCHMARK SUITE")
    print("=" * 60)

    db_path = "benchmark/phase_3_1/benchmark_temp.sqlite"
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

    client = TestClient(app)
    settings = get_api_settings()

    # 1. Setup Benchmark Account & Session
    email = "bench_user@example.com"
    password = "BenchmarkPassword123!"
    client.post("/api/v1/auth/register", json={"auth_identifier": email, "password": password})
    login_res = client.post("/api/v1/auth/login", json={"auth_identifier": email, "password": password})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sess_res = client.post("/api/v1/sessions", json={}, headers=headers)
    session_id = sess_res.json()["session_id"]

    results: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "benchmarks": {},
    }

    # Helper for percentiles
    def get_stats(latencies: List[float]) -> Dict[str, float]:
        sorted_lat = sorted(latencies)
        p50 = statistics.median(sorted_lat)
        p95_idx = int(len(sorted_lat) * 0.95)
        p95 = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]
        return {
            "p50_ms": round(p50, 3),
            "p95_ms": round(p95, 3),
            "min_ms": round(min(sorted_lat), 3),
            "max_ms": round(max(sorted_lat), 3),
            "sample_count": len(sorted_lat),
        }

    # Benchmark 1: Authenticated GET /sessions/{id}
    print("\n1. Measuring GET /sessions/{id} (100 samples)...")
    get_latencies = []
    for _ in range(100):
        get_rate_limiter().reset()
        t0 = time.time()
        res = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
        t1 = time.time()
        assert res.status_code == 200
        get_latencies.append((t1 - t0) * 1000.0)

    results["benchmarks"]["get_session_lightweight"] = get_stats(get_latencies)

    # Benchmark 2: Session Lifecycle (create/list/delete)
    print("2. Measuring Session Lifecycle (50 cycles)...")
    lifecycle_latencies = []
    for _ in range(50):
        get_rate_limiter().reset()
        t0 = time.time()
        c_res = client.post("/api/v1/sessions", json={}, headers=headers)
        s_id = c_res.json()["session_id"]
        client.get("/api/v1/sessions", headers=headers)
        client.delete(f"/api/v1/sessions/{s_id}", headers=headers)
        t1 = time.time()
        lifecycle_latencies.append((t1 - t0) * 1000.0)

    results["benchmarks"]["session_crud_lifecycle"] = get_stats(lifecycle_latencies)

    # Benchmark 3: Rate Limiting Overhead (memory vs disabled)
    print("3. Measuring Rate-Limiter Overhead (Disabled vs In-Memory)...")
    settings.rate_limit_backend = "disabled"
    disabled_latencies = []
    for _ in range(100):
        t0 = time.time()
        client.get(f"/api/v1/sessions/{session_id}", headers=headers)
        t1 = time.time()
        disabled_latencies.append((t1 - t0) * 1000.0)

    settings.rate_limit_backend = "memory"
    memory_latencies = []
    for _ in range(100):
        get_rate_limiter().reset()
        t0 = time.time()
        client.get(f"/api/v1/sessions/{session_id}", headers=headers)
        t1 = time.time()
        memory_latencies.append((t1 - t0) * 1000.0)

    disabled_stats = get_stats(disabled_latencies)
    memory_stats = get_stats(memory_latencies)
    rl_overhead_p50 = round(memory_stats["p50_ms"] - disabled_stats["p50_ms"], 3)

    results["benchmarks"]["rate_limit_overhead"] = {
        "disabled": disabled_stats,
        "memory": memory_stats,
        "delta_p50_ms": rl_overhead_p50,
    }

    # Benchmark 4: Turn API Boundary Overhead
    print("4. Measuring Turn Endpoint API Boundary Overhead (50 samples)...")
    turn_latencies = []
    for _ in range(50):
        get_rate_limiter().reset()
        t0 = time.time()
        res = client.post(
            f"/api/v1/sessions/{session_id}/turns",
            json={"query": "What are the rules regarding contract termination?"},
            headers=headers,
        )
        t1 = time.time()
        assert res.status_code == 200
        turn_latencies.append((t1 - t0) * 1000.0)

    results["benchmarks"]["turn_boundary_overhead"] = get_stats(turn_latencies)

    print("\nBENCHMARK RESULTS SUMMARY:")
    print(json.dumps(results, indent=2))

    with open("benchmark/phase_3_1/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nBenchmark results saved to benchmark/phase_3_1/benchmark_results.json")


if __name__ == "__main__":
    run_benchmark()
