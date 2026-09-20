# benchmark/phase_2_9/benchmark_auth_performance.py
"""
Performance Benchmark for Phase 2.9 Authentication & Authorization (§21).
Measures latency overhead for authentication, token validation, authorization checks, and end-to-end turns.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import numpy as np
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from src.auth.auth_provider import PasswordAuthProvider
from src.auth.authorization_service import AuthorizationService
from src.conversation.persistent_session_store import PersistentSessionStore


def run_auth_benchmark(iterations: int = 100):
    sqlite_path = "benchmark/phase_2_9/bench_auth.sqlite"
    store = PersistentSessionStore(backend="sqlite", sqlite_path=sqlite_path)
    auth_provider = PasswordAuthProvider(backend="sqlite", sqlite_path=sqlite_path)
    auth_service = AuthorizationService(session_store=store)

    email = "bench_user@example.com"
    raw_pass = "BenchPassword123!"

    user_obj = auth_provider.create_account(email, raw_pass)
    session = store.create_session(user_id=str(user_obj.user_id))

    # 1. Measure Authentication Latency
    auth_latencies = []
    tokens = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        auth_user, token = auth_provider.authenticate({"auth_identifier": email, "password": raw_pass})
        t1 = time.perf_counter()
        auth_latencies.append((t1 - t0) * 1000.0)  # ms
        tokens.append(token)

    # 2. Measure Token Validation Latency
    token_val_latencies = []
    test_token = tokens[0]
    for _ in range(iterations):
        t0 = time.perf_counter()
        val_user = auth_provider.validate_token(test_token)
        t1 = time.perf_counter()
        token_val_latencies.append((t1 - t0) * 1000.0)

    # 3. Measure Authorization Check Latency
    val_user = auth_provider.validate_token(test_token)
    authz_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        auth_service.authorize_session_access(val_user, session.session_id, action="read")
        t1 = time.perf_counter()
        authz_latencies.append((t1 - t0) * 1000.0)

    # 4. Measure End-to-End Auth Overhead (Token validation + Authz check)
    e2e_latencies = []
    for token in tokens:
        t0 = time.perf_counter()
        v_user = auth_provider.validate_token(token)
        auth_service.authorize_session_access(v_user, session.session_id, action="read")
        t1 = time.perf_counter()
        e2e_latencies.append((t1 - t0) * 1000.0)

    print("\n================ Phase 2.9 Performance Benchmark Results ================")
    print(f"Iterations: {iterations}")
    print(f"Authentication Latency:        P50 = {np.percentile(auth_latencies, 50):.3f} ms | P95 = {np.percentile(auth_latencies, 95):.3f} ms")
    print(f"Token Validation Latency:      P50 = {np.percentile(token_val_latencies, 50):.3f} ms | P95 = {np.percentile(token_val_latencies, 95):.3f} ms")
    print(f"Authorization Check Latency:    P50 = {np.percentile(authz_latencies, 50):.3f} ms | P95 = {np.percentile(authz_latencies, 95):.3f} ms")
    print(f"End-to-End Overhead:           P50 = {np.percentile(e2e_latencies, 50):.3f} ms | P95 = {np.percentile(e2e_latencies, 95):.3f} ms")
    print("=========================================================================\n")


if __name__ == "__main__":
    run_auth_benchmark()
