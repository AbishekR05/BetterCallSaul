# Phase 3.1 — API Hardening & Production Readiness: Implementation Specification

**Project:** BetterCallSaul
**Phase:** 3.1
**Type:** Implementation specification (Antigravity executes; Abishek signs off)
**Baseline:** Phase 3.0 (FastAPI API boundary), Phases 2.5–2.9 frozen

---

## 1. Objective

Harden the Phase 3.0 FastAPI backend so it fails safely, resists abuse, behaves correctly under concurrency, and is observable, **without changing** the RAG, conversation, persistence, or authentication architecture.

Guiding rules:
- Every failure produces a deterministic, safe, uniform `APIError` response (`{ error_code, message, request_id }`). No stack traces, SQL, file paths, hostnames, library names, or model/provider details reach clients.
- Hardening lives in `src/api/` (and a new `src/api/hardening/` subpackage). Nothing below the API boundary is modified.
- Every new limit, timeout, and toggle is centralized in `configs/p31_hardening.yaml`. Nothing hardcoded.

## 2. Phase 3.0 Baseline

Treated as established and frozen unless a documented security/reliability defect requires change:

- Package `src/api/` with routers `auth`, `sessions`, `turns`, `health`; services `AuthService`, `SessionService`, `TurnService`; DTOs in `src/api/schemas/`.
- Pipeline: `API → get_authenticated_user → get_authorized_session → Service → ConversationalOrchestrator → SessionStore → Retrieval (2.5) → Generation (2.6)`.
- Endpoints under `/api/v1` (auth register/login/logout, sessions CRUD, `POST /sessions/{id}/turns`) plus `/health`, `/ready`.
- Existing middleware: CORS, request ID, 100 KB body cap, security headers.
- 3.0 baseline: 59 tests passing; API turn overhead P50 12.6 ms (RAG excluded). Known upstream latency: retrieval P50 ~3–11 s, P95 up to ~13 s (Phases 2.6/2.7 reports). **Timeout defaults in this phase must respect this.**

**Before any change:** tag the repo `phase_3_0_baseline` and record the current OpenAPI JSON as `benchmark/phase_3_1/openapi_baseline.json`.

## 3. Scope

In scope: items 4–15 below. All work is additive middleware, dependencies, exception mapping, config, tests, and benchmarks at or above the API layer.

Permitted contract changes (must be listed in `PHASE_3_1_CHANGELOG.md`): new status codes `429`, `503`, `504`, `409 session_busy`; new response headers `Retry-After`, `X-Request-ID`, `WWW-Authenticate`. No existing field, path, or success schema is removed or renamed.

## 4. Reliability Hardening

**4.1 Global exception boundary.** Register handlers so every exception maps to `APIError`. Unknown exceptions → `500 internal_error` with generic message; full detail logged server-side with `request_id` only.

**4.2 Domain exception taxonomy** (new, in `src/api/errors.py`), mapped centrally:

| Condition | HTTP | `error_code` |
|---|---|---|
| Malformed body / validation | 422 | `validation_error` |
| Malformed path UUID | 422 | `invalid_identifier` |
| Missing/malformed/invalid/expired/revoked token | 401 | `unauthenticated` |
| Session not found **or** not owned | 404 | `session_not_found` (identical for both) |
| Duplicate registration | 409 | `conflict` |
| Concurrent turn on same session | 409 | `session_busy` |
| Body too large | 413 | `payload_too_large` |
| Rate limit exceeded | 429 | `rate_limited` (+ `Retry-After`) |
| Turn concurrency capacity exceeded | 503 | `server_busy` (+ `Retry-After`) |
| Database/auth-store unavailable | 503 | `dependency_unavailable` |
| RAG/LLM timeout | 504 | `upstream_timeout` |
| RAG/LLM failure (non-timeout) | 502 | `upstream_failure` |
| Anything else | 500 | `internal_error` |

**4.3 Graceful degradation.** If the pipeline returns the existing `llm_call_failed` fallback or a low-evidence answer, it is passed through as a normal `200` `GroundedAnswerResponse` (existing 2.6 behavior). Only exceptions that escape the orchestrator are mapped to 5xx.

**4.4 No silent retries of writes.** Reads may retry once on transient connection error (configurable); writes never auto-retry.

## 5. Rate Limiting

**5.1 Design.** Define a `RateLimiter` protocol (`check(key, rule) -> Decision(allowed, retry_after_s)`). Ship one implementation: in-process sliding-window/token-bucket with bounded memory (LRU eviction of idle keys). Selectable via config (`rate_limit.backend: memory | disabled`). No Redis/distributed store in this phase.

**5.2 Keys.** Unauthenticated endpoints: client IP (honor `X-Forwarded-For` only if `trusted_proxies` configured; otherwise socket peer). Login additionally keyed by normalized `auth_identifier`. Authenticated endpoints: `user_id` derived from token.

**5.3 Default rules (all configurable; starting values, tune from benchmark):**

| Endpoint | Key | Default rule |
|---|---|---|
| `POST /auth/register` | IP | 5 / hour |
| `POST /auth/login` | IP | 10 / minute |
| `POST /auth/login` | identifier | 5 failed / 15 min (complements Phase 2.9's limiter; must not conflict) |
| `POST /sessions` | user | 20 / minute |
| `POST /sessions/{id}/turns` | user | 10 / minute, plus concurrency cap |
| `GET`/`DELETE` session endpoints | user | 120 / minute |

**5.5 Behavior.** Rate-limit check runs **before** password hashing and before any RAG work. `429` response includes `Retry-After`. Login failures return the same `401` message regardless of whether the identifier exists.

**5.6 Documented limitation.** In-memory limits are per-process; multi-worker deployments multiply effective limits. Record this in the README/changelog. Replacement path is the `RateLimiter` protocol.

**5.7 Turn concurrency cap.** A global semaphore (`max_concurrent_turns`, default small, e.g. 2) protects the shared 8 GB GPU and Gemini quota. Requests beyond capacity wait up to `queue_wait_timeout_s`, then return `503 server_busy`.

## 6. Request Validation

- All request DTOs: `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)`; no `user_id` field anywhere (existing rule, add regression test).
- Field limits (configurable): `auth_identifier` ≤ 254 chars; password 8–128 chars; turn `query` 1–2,000 chars; session title/metadata ≤ 200 chars; reject control characters and NUL bytes.
- Body limit enforced on **actual bytes read** (streaming counter), not only `Content-Length`; chunked requests without `Content-Length` must be capped. Content-Type must be `application/json` for JSON endpoints (`415` otherwise, mapped to `APIError`).
- Path `session_id` typed as `UUID`; malformed → `422 invalid_identifier`, never `500`.
- `Authorization` header: strict parse of `Bearer <token>` (case-insensitive scheme, exactly one token, length-bounded). Any deviation → `401` with `WWW-Authenticate: Bearer`, identical body to invalid-token case.
- Duplicate requests: duplicate registration → `409`; repeated `DELETE` → `404` (uniform, not `500`); double-submitted turns handled by §7.2 (`session_busy`). No idempotency-key mechanism in this phase.
- Timeout boundaries: `request_timeout_s` for lightweight endpoints; `turn_timeout_s` for turns (default must exceed observed P95 retrieval+generation with headroom). Both configurable.
- `request_id`: honor inbound `X-Request-ID` only if it matches `^[A-Za-z0-9_-]{8,64}$`; otherwise generate. Always echo in response header and error body.

## 7. Concurrency & Resource Safety

**7.1 Audit checklist** (findings recorded in the report, fixes applied only at API/service layer):
- No module-level mutable state in `src/api/` other than explicitly documented, lock-protected structures (rate limiter, turn semaphore, session locks).
- Orchestrator, `AuthProvider`, `SessionStore` instantiated once via lifespan; verify thread/async safety of each as used. If any is not safe for concurrent use, serialize access at the service layer and document.
- Blocking calls (sync DB, GPU embedding, Gemini) must not run on the event loop; execute in a bounded threadpool.
- DB connections: acquired per request via pool/context manager and always released (test with induced exceptions and client disconnects).

**7.2 Per-session turn serialization.** At most one in-flight turn per `session_id` (in-process lock map with cleanup). A second concurrent turn returns `409 session_busy`. Prevents interleaved turn ordering and context corruption.

**7.3 Concurrency test matrix** (threads or `httpx.AsyncClient` gather):
- N concurrent logins (same user, different users)
- N concurrent session creations (same user)
- Concurrent read/delete of the same session
- Concurrent turns: same session (expect one success + `session_busy`), different sessions of one user, different users (verify no cross-session context leakage via unique sentinel strings)
- Connection pool count before/after (no leak)

Any cross-user or cross-session leakage is a **blocking failure**.

## 8. Database Failure Handling

Wrap store/auth-store calls at the service layer, translating driver exceptions (connection, timeout, operational, integrity) into `DependencyUnavailableError` (→ `503`) or domain errors. Never expose driver messages.

Fault-injection tests (mock/patch store or point at closed port; SQLite and Postgres where available):
1. DB unreachable at request time → `503 dependency_unavailable`.
2. Connection drops mid-request → `503`, connection released.
3. Transaction failure on write (turn save, session create) → `503`/`500` generic, no partial state visible (verify turn count consistency).
4. Session deleted between authorization and turn execution → `404 session_not_found`, no `500`.
5. Auth DB failure during login/token validation → `503`; **fail closed** (never treat as authenticated).
6. Recovery: after DB returns, next request succeeds without process restart.

## 9. RAG/LLM Failure Boundary

- `TurnService` runs `handle_turn` under `asyncio.wait_for` (via threadpool) with `turn_timeout_s`. On timeout: `504 upstream_timeout`; log with `request_id`; release semaphore and session lock in `finally`.
- Note (document, don't fix): Python threads cannot be force-cancelled; the timed-out work may finish in the background. The semaphore is released only when the worker actually finishes, to prevent unbounded GPU/LLM pile-up.
- Exception mapping: retrieval/DB-corpus errors, reranker/embedding errors (incl. CUDA OOM) → `502 upstream_failure`; LLM provider quota/timeouts already handled by 2.6 fallback (passed through as 200); anything unmapped → `500`.
- Session state on failure: a failed turn must not leave a half-written turn (rely on 2.8 atomic `add_turn`; verify by test).
- Correlation: `request_id` propagated into orchestrator/log context (contextvar); no changes to frozen module signatures.
- Tests use `MockLLMClient` and injected failing orchestrator doubles at the service boundary. No edits to `src/retrieval/`, `src/generation/`, `src/conversation/`.

## 10. Observability / Logging

- One structured (JSON) access log line per request: `timestamp, request_id, method, route_template, status_code, latency_ms, user_id (opaque UUID, authenticated only), error_code (if any)`. Use the **route template** (`/sessions/{id}/turns`), not the raw path.
- Turn logs may add: `query_length_chars`, `evidence_sufficiency`, `stage_latency_ms` if already exposed by the pipeline. **Never** the query text or answer text.
- Response timing header `X-Process-Time-Ms` (configurable on/off).
- Never log: passwords, hashes, bearer tokens, `Authorization` header, request/response bodies, session content, raw exception messages from drivers. Use an allowlist-based log formatter plus a redaction filter as defense in depth.
- Log level and format from config; unhandled exceptions logged with stack trace **server-side only**.

## 11. Health / Readiness

- `GET /health` — liveness only: process is up. No dependency calls. `200 {"status":"ok"}`.
- `GET /ready` — readiness: `200` only if all **required** checks pass, else `503`. Checks (each with per-check timeout, run concurrently):
  - session/auth database reachable (`SELECT 1`, read-only)
  - corpus database reachable (read-only ping)
  - orchestrator/pipeline initialized (retriever, embedding model, reranker loaded)
  - required configuration/secrets present (boolean only)
- Optional dependencies (e.g., LLM provider) are **not** probed live (cost/quota); readiness reports configuration presence only.
- Response body: `{"status": "ready"|"not_ready", "checks": {"session_db": "ok"|"fail", ...}}`. Check names are generic; no hostnames, versions, connection strings, exception text.
- Both endpoints unauthenticated, not rate-limited by user, and excluded from access-log noise (configurable).

## 12. Configuration / Secrets

- `configs/p31_hardening.yaml` (defaults) + environment variable overrides; `APP_ENV = development | production` (default `production`-safe).
- Secrets (Gemini API key, DB credentials, any signing/HMAC values) only from environment/secret file; never in YAML, code, logs, or `.env` committed to git. Verify `.gitignore` and scan the repo for hardcoded credentials (report result).
- **Startup validation (fail fast, non-zero exit, clear generic message):** required secrets present; DB URLs parseable; limits/timeouts positive; in production: CORS origins explicit (no `*`), debug/reload off, interactive docs (`/docs`, `/redoc`, `/openapi.json`) controlled by config flag (default off in production), rate limiter not `disabled`.
- Development profile may relax the above but must log a clear "development mode" warning.
- Startup validation error messages name the missing **setting**, never its value.

## 13. OpenAPI Verification

Automated contract test (`tests/api/test_openapi_contract.py`) against generated schema:
- All paths under `/api/v1` (plus `/health`, `/ready`).
- `bearerAuth` security scheme declared; applied to every protected endpoint, absent on register/login/health/ready.
- Request/response models match Phase 3.0 contract table; `extra="forbid"` reflected.
- Every endpoint declares its possible error responses (`401/404/409/413/422/429/503/504` as applicable) referencing the `APIError` model.
- Diff against `openapi_baseline.json`: only changes permitted in §3 are allowed; any other difference fails the test.
- 422 validation errors are normalized to `APIError` (not FastAPI's default `detail` shape); schema and runtime must agree.

## 14. Security Regression Tests

Extend `tests/api/` (all must pass; zero tolerance on isolation):
- Auth: missing/malformed/wrong-scheme/oversized header; invalid, expired, revoked (post-logout) tokens.
- Cross-user: A→B session GET/DELETE/turn returns identical response to nonexistent session; UUID manipulation/enumeration.
- Rate limiting: each rule triggers `429` with `Retry-After`; window recovery; per-user isolation of limits; login brute-force with valid/invalid identifiers indistinguishable.
- Oversized body (declared and chunked); wrong Content-Type; unknown fields; over-length fields; control characters.
- Information leakage: forced internal exceptions (patched) produce no stack trace, path, SQL, or library names in body or headers; same for 404/403/401 parity.
- Concurrency (§7.3), DB failure (§8), RAG/LLM failure (§9).
- Logging safety: captured logs during all above tests scanned for passwords, tokens, hashes, `Authorization`, query text, sentinel secrets.
- Health/readiness: no secret/infrastructure leakage; correct 503 on injected dependency failure.
- Regression: all 59 Phase 3.0 tests and Phase 2.5–2.9 suites still pass unchanged.

## 15. Performance Benchmarks

Script: `benchmark/phase_3_1/benchmark_api_hardening.py`. Report **P50/P95**, n and environment stated. Use the mock LLM for controlled runs; optionally one real-Gemini run, labeled separately.

| Benchmark | Notes |
|---|---|
| Authenticated lightweight endpoint (`GET /sessions/{id}`) | vs Phase 3.0 baseline |
| Session create / list / delete | vs Phase 3.0 baseline |
| Rate-limit overhead | same endpoint with limiter `disabled` vs `memory` |
| Concurrent lightweight requests | e.g., 1, 10, 50 concurrent |
| Turn endpoint under controlled concurrency | e.g., 1, 2, 4 concurrent turns; report queueing, `503 server_busy` counts, timeouts |
| API boundary overhead for turns | isolated from RAG time, comparable to 3.0's 12.6 ms |

Report deltas against 3.0; no numeric pass thresholds (informational baseline). Do not optimize RAG.

## 16. Non-Scope

Modifying 2.5 retrieval, 2.6 generation, 2.7 conversation, 2.8 persistence, or 2.9 auth internals; frontend/React; OAuth/social login; LangGraph/agents; payments; distributed rate limiting/Redis; deployment platform/Docker/cloud; API gateway/WAF; RAG performance optimization; idempotency-key framework; new corpus/data work.

## 17. Acceptance Criteria

Process/infrastructure correctness (not numeric performance thresholds):

1. All new and existing tests pass (Phase 3.0's 59 + Phase 3.1 additions); zero failures.
2. Zero cross-user or cross-session leakage in sequential and concurrent tests.
3. No test path exposes a stack trace, internal path, SQL, driver, or provider detail to the client.
4. Every error response conforms to `APIError` and carries `request_id`.
5. DB-unavailable, DB mid-request failure, session-vanishes, auth-store failure, RAG failure, and RAG timeout each yield the specified deterministic status/code; auth store failure fails closed.
6. Rate limits demonstrably enforced on all listed endpoints; limiter is swappable via protocol and can be disabled by config.
7. No connection or lock/semaphore leaks after failure and timeout tests.
8. Logging audit finds no prohibited data across the full test run.
9. `/health` and `/ready` behave per §11 with no infrastructure disclosure.
10. Startup validation rejects invalid production configuration; no hardcoded secrets found.
11. OpenAPI contract test passes; only §3-permitted differences from baseline.
12. Frozen-layer integrity: **0 lines modified** in `src/retrieval/`, `src/generation/`, `src/conversation/`, `src/auth/`, and Phase 2.8 persistence files (verified by `git diff` against `phase_3_0_baseline`).
13. Benchmarks produced with P50/P95 and documented methodology.
14. Any discovered defect requiring a change to a frozen layer is **reported, not fixed**, and listed for sign-off.

## 18. Rollback Strategy

- Baseline tag `phase_3_0_baseline` created before work starts; Phase 3.1 committed on a dedicated branch, merged only after sign-off.
- Each hardening component (rate limiter, turn cap, session lock, timeout, extra-field strictness, docs toggle) has a config flag so it can be disabled without code revert.
- New modules are additive (`src/api/hardening/`); reverting the branch restores 3.0 behavior. No schema migrations are introduced in this phase (if one proves necessary, stop and report).
- `PHASE_3_1_CHANGELOG.md` lists every contract change so clients can be checked against it.

## 19. Artifacts

- `configs/p31_hardening.yaml`
- `src/api/hardening/` (rate limiter, limits, session lock, timeout/concurrency guard, log redaction)
- Updated `src/api/errors.py`, `main.py`, `dependencies.py`, `config.py`, services
- `tests/api/` additions (security, concurrency, DB failure, RAG failure, health, OpenAPI, logging)
- `benchmark/phase_3_1/benchmark_api_hardening.py`, `openapi_baseline.json`, results JSON
- `PHASE_3_1_CHANGELOG.md`
- `PHASE_3_1_REPORT.md`: results per acceptance criterion, concurrency/DB/RAG failure findings, benchmark tables, documented limitations (per-process rate limits, uncancellable worker threads), and frozen-layer diff evidence

## 20. STOP / Sign-Off Criteria

**STOP** after `PHASE_3_1_REPORT.md` is produced. Do NOT begin frontend, deployment, containerization, distributed rate limiting, or any Phase 3.2 work, and do not modify frozen layers.

Sign-off requires Abishek's review of: acceptance-criteria results, any reported frozen-layer defects, documented contract changes, and the known-limitations list. Phase 3.1 is complete only on explicit clearance.