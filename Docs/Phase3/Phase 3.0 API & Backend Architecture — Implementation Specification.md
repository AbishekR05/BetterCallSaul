# Phase 3.0: API & Backend Architecture — Implementation Specification

**Depends on:** Phase 2.5 (frozen retrieval), Phase 2.6 (frozen grounded generation), Phase 2.7 (frozen conversational orchestrator), Phase 2.8 (persistent `SessionStore`), Phase 2.9 (`AuthProvider`, `AuthorizationService`, user identity)
**Executing agent:** Antigravity
**Status:** SPECIFICATION ONLY — implementation not yet authorized

---

## 1. Objective

Expose the completed Phase 2 system through a clean, minimal FastAPI HTTP boundary: `API → Authentication → Authorization → Conversation → Retrieval → Grounded Generation`. The API layer is thin — it authenticates, authorizes, translates HTTP to/from existing service calls, and returns structured responses. It contains no retrieval, generation, or conversational logic of its own.

---

## 2. Why Phase 3.0 Follows Phase 2.9

Every component this API exposes already exists and is frozen: `AuthProvider`/`AuthorizationService` (2.9) sit in front of `SessionStore` (2.8), which the `ConversationalOrchestrator` (2.7) calls, which calls frozen retrieval (2.5) and generation (2.6). Phase 3.0 adds nothing to that chain conceptually — it only makes it reachable over HTTP, with the same security boundary Phase 2.9 already defined now enforced at the request layer instead of by direct Python calls.

---

## 3. Architecture

```
HTTP Request
      │
      ▼
FastAPI app (middleware: CORS, request-id, logging, rate limit, size limit)
      │
      ▼
Router (auth | sessions | turns | health)
      │
      ▼
Dependency: get_authenticated_user  ── calls AuthProvider.validate_token (Phase 2.9)
      │
      ▼
Dependency: get_authorization_service / session ownership check (Phase 2.9)
      │
      ▼
Application service layer (thin adapters, §4)
      │
      ▼
ConversationalOrchestrator.handle_turn(user_id, session_id, query)   (Phase 2.7, unchanged)
      │
      ▼
SessionStore (2.8) → Frozen Retrieval (2.5) → Frozen Generation (2.6)
```

No router function calls `SessionStore`, retrieval, or generation directly — every router depends only on the application service layer (§4), which itself depends only on the existing Phase 2.7–2.9 entry points.

---

## 4. FastAPI Structure

```
src/api/
  main.py                # app factory, middleware registration, router mounting, lifespan
  dependencies.py         # get_authenticated_user, get_authorization_service, get_orchestrator, get_session_store
  routers/
    auth.py                # /auth/register, /auth/login, /auth/logout
    sessions.py             # /sessions, /sessions/{id}
    turns.py                 # /sessions/{id}/turns
    health.py                 # /health, /ready
  schemas/                # §7 Pydantic models, one module per resource
  services/
    auth_service.py         # thin wrapper: request DTO ↔ AuthProvider (2.9)
    session_service.py        # thin wrapper: request DTO ↔ SessionStore + AuthorizationService
    turn_service.py             # thin wrapper: request DTO ↔ ConversationalOrchestrator.handle_turn
  errors.py                # exception types + FastAPI exception handlers → §11 error model
  config.py                 # settings (pydantic-settings), reads configs/p30_api.yaml + env
```

- **Dependency injection:** FastAPI `Depends()` chains resolve `AuthenticatedUser` and, where a `session_id` is in the path, a verified ownership check — both as reusable dependencies, never re-implemented per-route.
- **Service boundaries:** each `services/*.py` module is a thin translation layer only — DTO in, call an existing Phase 2.7–2.9 function, DTO out. No business logic (retry policy, retrieval tuning, prompt handling) lives here; that all remains inside the components it already lives in.
- **Configuration:** `configs/p30_api.yaml` — CORS origins, rate-limit thresholds, request size limits, log level — loaded once at startup via `pydantic-settings`; no config values hardcoded in route handlers.
- **Startup/shutdown lifecycle:** FastAPI `lifespan` context manager initializes the database connection pool (Phase 2.8's `PersistentSessionStore`) once at startup and closes it cleanly at shutdown; the embedding model / LLM clients used by retrieval and generation are initialized by those existing modules exactly as they already are (this phase does not change their init pattern, only ensures the API process triggers it once, not per-request).
- **Database/session-store access:** the API process holds one `SessionStore` instance (backend selected via Phase 2.8's existing factory) and one `AuthProvider`/`AuthorizationService` pair, constructed at startup and handed out via dependencies — no per-request store construction.
- **Error handling:** centralized FastAPI exception handlers (§11) translate internal exception types (`AuthenticationError`, `AuthorizationError`, `SessionNotFoundError`, `RetrievalFailureError`, `GenerationFailureError`) into the safe error schema — route handlers raise domain exceptions, never construct HTTP error bodies inline.

---

## 5. API Contract

All endpoints under `/api/v1` except health checks. `Auth: none/required` states whether a valid bearer token is required; `Authz: none/ownership` states whether session-ownership verification additionally applies.

| Endpoint | Auth | Authz | Request | Success | Failure codes |
|---|---|---|---|---|---|
| `POST /auth/register` | none | none | `RegisterRequest` | `201` `AuthUserResponse` | `400` validation, `409` identifier already exists |
| `POST /auth/login` | none | none | `LoginRequest` | `200` `AuthTokenResponse` | `400` validation, `401` invalid credentials (generic), `429` rate-limited |
| `POST /auth/logout` | required | none | — (token from header) | `204` | `401` invalid/expired token |
| `GET /sessions` | required | none (scoped to caller) | — | `200` `SessionListResponse` (only caller's sessions) | `401` |
| `POST /sessions` | required | none | `CreateSessionRequest` (empty/optional body) | `201` `SessionResponse` | `401` |
| `GET /sessions/{session_id}` | required | ownership | — | `200` `SessionResponse` | `401`, `403`/`404` (see §6 — identical response) |
| `DELETE /sessions/{session_id}` | required | ownership | — | `204` | `401`, `403`/`404` (identical) |
| `POST /sessions/{session_id}/turns` | required | ownership | `TurnRequest` | `200` `GroundedAnswerResponse` | `400` validation, `401`, `403`/`404` (identical), `422` retrieval/generation failure (see §11) |
| `GET /health` | none | none | — | `200` `{"status": "ok"}` | — (liveness only, no dependency checks) |
| `GET /ready` | none | none | — | `200` `{"status": "ready"}` | `503` if DB/session-store connection check fails |

`GET /sessions` returns only sessions owned by the caller — no `user_id` filter parameter is accepted, closing off any path to request another user's list.

---

## 6. Authentication / Authorization Boundary

```
HTTP Request (Authorization: Bearer <token>, or credentials for /auth/*)
      │
      ▼
get_authenticated_user dependency
      │  calls AuthProvider.validate_token(token)  →  AuthenticatedUser | raise AuthenticationError
      ▼
[for routes with a session_id path param]
get_authorized_session dependency
      │  calls AuthorizationService.authorize_session_access(authenticated_user, session_id, action)
      │  →  Authorized | raise AuthorizationError
      ▼
Route handler receives AuthenticatedUser.user_id and a pre-authorized session_id — never a client-supplied user_id
```

- **The API never trusts a client-supplied `user_id`.** No request schema in §7 includes a `user_id` field anywhere, including `TurnRequest`/`CreateSessionRequest` — `user_id` is derived exclusively from the validated token via `get_authenticated_user`. This is enforced structurally (the field doesn't exist on the input schema), not by a runtime check that could be bypassed.
- **Session ownership always derives from authenticated identity:** every `session_id`-scoped route depends on `get_authorized_session`, which calls Phase 2.9's `AuthorizationService` unchanged — the API adds no separate/parallel ownership logic.
- **Preserved Phase 2.9 properties, unchanged at this layer:**
  - Cross-user access → `AuthorizationError` → mapped to the same generic `403`/`404`-equivalent response regardless of whether the session exists (§11), never distinguishing the two.
  - Token validation/revocation → delegated entirely to `AuthProvider.validate_token`; the API adds no token parsing/caching logic of its own.
  - Secure errors → §11.
  - No credential/token logging → §10's structured-logging requirement excludes the `Authorization` header and any request body field named `password`.
  - Rate limiting → applied at the `/auth/login` and `/auth/register` routes specifically (§10), matching Phase 2.9's existing per-identifier rate-limit concept, now also enforced at the HTTP entry point as a first line of defense.

---

## 7. Pydantic Schemas

`src/api/schemas/` — request and response models, minimal fields only:

```
RegisterRequest        { auth_identifier: str, password: str }
LoginRequest            { auth_identifier: str, password: str }
AuthUserResponse         { user_id: UUID, auth_identifier: str, created_at_utc: datetime }
AuthTokenResponse         { access_token: str, expires_at_utc: datetime, token_type: "bearer" }

SessionResponse           { session_id: UUID, created_at_utc: datetime, last_active_utc: datetime,
                             expires_at_utc: datetime, status: str, turn_count: int }
SessionListResponse        { sessions: list[SessionResponse] }
CreateSessionRequest        {}   # no fields; user_id comes from auth, everything else server-assigned

TurnRequest                  { query: str }
GroundedAnswerResponse        { session_id: UUID, turn_index: int,
                                 answer_summary: str, answer_detail: str,
                                 applicable_jurisdiction: str, evidence_sufficiency: str,
                                 citations: list[CitationResponse], caveats: list[str],
                                 clarifying_question: str | None }
CitationResponse                { document_title: str, document_type: str, jurisdiction: str,
                                   section: str | None, source_reference: str | None }

APIError                          { error_code: str, message: str, request_id: str }
```

- `GroundedAnswerResponse` intentionally omits Phase 2.6's `generation_metadata` (token counts, cost, model name) and `safety_flags` from the public response — those remain internal-only (logged per §10), since the API response should stay privacy-conscious and minimal, not leak operational/cost detail to the client.
- `AuthTokenResponse` never includes `user_id`-to-password mapping detail or the token hash — only the opaque token itself, as issued.
- No schema anywhere accepts `user_id` as client input (§6).

---

## 8. Conversation Integration

`POST /sessions/{session_id}/turns`:

1. `get_authenticated_user` resolves `AuthenticatedUser.user_id` from the bearer token.
2. `get_authorized_session` confirms `session_id` (path param) is owned by that `user_id`, via Phase 2.9's `AuthorizationService` unchanged.
3. `turn_service.py` calls `ConversationalOrchestrator.handle_turn(user_id, session_id, query=body.query)` — the exact Phase 2.7 entry point, with the one additive `user_id` parameter Phase 2.9 already introduced. No retry, fallback, or retrieval/generation logic is added at this layer; whatever `handle_turn` returns (including its own internal failure-handling per Phase 2.6/2.7's existing specs) is what the API translates into a response.
4. The returned `GroundedAnswer` (embedded in `ConversationTurnResult`) is mapped field-by-field into `GroundedAnswerResponse` (§7) — a pure serialization step, not a transformation of content.
5. If `handle_turn` itself raises (retrieval failure, LLM failure — per Phase 2.6/2.7's existing failure modes), the API's centralized exception handling (§11) maps it to a `422` with a safe, generic message — it does not invent new failure semantics beyond what Phase 2.6/2.7 already define.

No conversation, retrieval, or generation logic is duplicated inside `turns.py` or `turn_service.py` — both are pass-through/translation only.

---

## 9. Database Boundaries

- The API process uses exactly the database connections Phase 2.8/2.9 already establish (session/user database) — it opens no new connection to, and issues no query against, the corpus/vector database (`chunks`/`embeddings`). Retrieval's own database access remains entirely inside `src/retrieval/`, invoked only indirectly via the orchestrator.
- All session/user data access from the API goes through existing abstractions — `SessionStore` (2.8) and `AuthProvider`/`AuthorizationService` (2.9) — never raw SQL in `src/api/`.
- **Transaction/error boundaries:** each API request that mutates state (register, login, create session, post a turn) maps to exactly one call into the existing service layer, which owns its own transaction boundary internally (per Phase 2.8 §8 / Phase 2.9 §11) — the API layer does not open, span, or manage database transactions itself; a failure partway through an existing service call surfaces as a clean exception, not a partially-committed state the API needs to reason about.

---

## 10. Middleware / Security

| Concern | Requirement |
|---|---|
| **CORS** | Explicit allow-list of origins from config (`configs/p30_api.yaml: cors.allowed_origins`) — no wildcard `*` once a real frontend origin is known; wildcard permitted only in local-dev config profile. |
| **Request IDs** | Middleware generates a UUID per request (or honors an inbound `X-Request-ID`), attached to all log lines and included in every `APIError` response for support/debugging traceability. |
| **Structured logging** | JSON log lines per request: method, path, status code, latency, request_id, `user_id` (once authenticated) — never the `Authorization` header value, `password` fields, or response body content containing conversation text (mirrors Phase 2.6/2.7/2.9's existing never-log-content discipline, now applied at the HTTP layer too). |
| **Secret/config management** | DB credentials, LLM API keys, and any auth signing secret are read from environment variables, never committed to `configs/p30_api.yaml` in plaintext — the YAML holds non-secret settings only (timeouts, CORS origins, rate limits), consistent with the project's existing secret-handling discipline (Phase 2.9 §12). |
| **Rate limiting** | Applied at minimum to `/auth/login` and `/auth/register` (reusing/extending Phase 2.9's per-identifier limiter, now also keyed by request IP as a coarse additional layer at the HTTP boundary); `/sessions/{id}/turns` gets a lightweight per-user rate limit too, since it triggers the most expensive downstream work (retrieval + LLM call). |
| **Security headers** | Standard defensive headers on every response (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`) — minimal, not a full CSP policy, appropriate for a JSON API with no HTML rendering. |
| **Request size limits** | Body size cap (config, e.g. small KB-scale limit) — primarily protects the `turns` endpoint from oversized query payloads; enforced via ASGI middleware before the request reaches route logic. |
| **Graceful error handling** | Every uncaught exception is caught by a top-level handler and converted to a generic `500 APIError` with no stack trace or internal detail leaked to the client — full detail goes to the server-side log only, keyed by `request_id`. |
| **Health/readiness** | `/health` is a pure liveness check (process is running, no dependency calls). `/ready` additionally verifies the session-store database connection is reachable (a lightweight query), returning `503` if not — used for deployment readiness gating, not for general traffic decisions. |

---

## 11. Error Model

Every error response uses the same `APIError` schema (§7): `{ error_code, message, request_id }`. `message` is always a safe, generic, non-leaking string; internal exception detail (stack traces, SQL errors, provider error bodies) is logged server-side only, keyed by `request_id`.

| Internal exception | HTTP status | `error_code` | `message` |
|---|---|---|---|
| Request schema validation failure | `400` | `validation_error` | "The request could not be validated." |
| `AuthenticationError` (missing/invalid/expired/revoked token, bad credentials) | `401` | `authentication_required` | "Authentication failed." (identical for every cause, per Phase 2.9 §12) |
| Duplicate `auth_identifier` at registration | `409` | `identifier_exists` | "An account with this identifier already exists." |
| `AuthorizationError` **or** session not found | `403` (or uniformly `404` — one is chosen at implementation time and applied consistently; both are indistinguishable to the caller per Phase 2.9 §14) | `session_not_accessible` | "Session not found or not accessible." |
| Rate limit exceeded | `429` | `rate_limited` | "Too many requests. Please try again later." |
| Retrieval or generation failure surfaced from `handle_turn` | `422` | `processing_failed` | "Unable to process this request right now." |
| Session-store/database unavailable | `503` | `service_unavailable` | "Service temporarily unavailable." |
| Any uncaught exception | `500` | `internal_error` | "An unexpected error occurred." |

This table is the single source of truth for error mapping — implemented once in `src/api/errors.py`'s exception handlers, not scattered across route handlers.

---

## 12. Testing Strategy

`tests/api/`, covering:

- **Endpoint validation** — malformed/missing fields on every request schema → `400` with the standard error shape.
- **Registration/login/logout** — happy path for each; duplicate registration → `409`; logout invalidates the token for subsequent requests.
- **Authentication failures** — missing token, malformed token, expired token, revoked token → all `401` with identical generic message (reusing Phase 2.9's own test fixtures where possible rather than re-deriving them).
- **Expired/revoked tokens** — explicit test that a token still passes structural parsing but fails `validate_token` after logout/expiry.
- **Cross-user session access** — user A's token against user B's `session_id`, every route (`GET`/`DELETE`/`POST turns`) → uniform not-accessible response, zero-tolerance (mirrors Phase 2.9 §20, exercised now via HTTP).
- **Session CRUD** — create, list (scoped to caller only), get, delete; deleted session subsequently returns not-accessible, not a different "already deleted" state that would leak existence.
- **Conversation turn flow** — a full `POST /turns` call against a test double for `ConversationalOrchestrator` (not the real LLM/retrieval, to keep API tests fast/deterministic) confirms correct request→service→response mapping.
- **Malformed requests** — oversized body, wrong content-type, invalid JSON → clean `400`/`413`, never a crash.
- **Consistent error responses** — every error path returns the exact `APIError` shape from §7/§11, verified with a shared assertion helper across all failure tests.
- **API → existing pipeline integration** — one narrow integration test exercising the real (or a realistic mock) Phase 2.7 orchestrator end-to-end through the HTTP layer, confirming the API doesn't alter behavior versus calling the orchestrator directly.
- **Health/readiness** — `/health` always `200` when the process is up; `/ready` returns `503` when the DB connection is deliberately broken in a test.
- **Secret/token logging safety** — automated scan of captured log output during the full test run confirms no `Authorization` header value, password, or token appears (extends Phase 2.9 §16/§20 to the HTTP layer).

---

## 13. Performance Baseline

Lightweight, locally-measured, no invented targets — consistent with the project's established process-over-threshold philosophy:

| Benchmark | Measured |
|---|---|
| `POST /auth/login` | Mean/P50/P95 latency (dominated by password-hash verification, per Phase 2.9 §21 — expected, not a regression). |
| `GET /sessions` (listing) | Mean/P50/P95 latency at a small (e.g. 20-session) and moderate (e.g. 200-session) scale. |
| `POST /sessions` (creation) | Mean/P50/P95 latency. |
| `GET /sessions/{id}` (retrieval) | Mean/P50/P95 latency. |
| `POST /sessions/{id}/turns` | Mean/P50/P95 **added** latency of the API layer itself, reported separately from the already-measured Phase 2.5/2.6/2.7 pipeline latency — isolates HTTP/auth/authorization overhead from unchanged downstream cost. |
| Concurrent requests | A modest concurrency test (e.g. N simulated concurrent users, mixed read/write) confirming no cross-request contamination and reporting throughput/latency under load — informational baseline, not a load-test/capacity-planning exercise. |

---

## 14. Non-Scope

- No React/frontend implementation.
- No OAuth/social login (Phase 2.9's `AuthProvider` interface admits it later; not built here).
- No payments/subscriptions.
- No admin dashboard.
- No user profiling or personalization.
- No agentic/LangGraph implementation.
- No retrieval redesign (Phase 2.5 untouched).
- No generation redesign (Phase 2.6 untouched).
- No changes to Phase 2.5–2.9 internals beyond calling their existing, already-defined entry points.
- No production deployment infrastructure (Docker/K8s/cloud) beyond what's needed to run the API process locally for testing — explicitly deferred, matching the "do not over-engineer production infrastructure yet" instruction.

---

## 15. Future Frontend Integration

This API is designed to be the direct backend for `React → FastAPI → Auth → Authorization → Conversation → RAG` with no anticipated contract changes: schemas are already minimal JSON, CORS is config-driven for exactly this purpose (§10), and the bearer-token model (§6) is standard and framework-agnostic on the client side. Building the frontend itself remains fully out of scope for this phase.

---

## 16. Future Agentic Integration

When `ConversationalOrchestrator` is eventually replaced by a LangGraph/agentic layer (per Phase 2.7 §20 and Phase 2.9 §25's stated plans), `turn_service.py` is the only place that changes — it would call the new orchestration entry point instead of `handle_turn`, passing the same minimal `(user_id, session_id, query)` context it already passes today. The agentic layer receives authorized user/session context exactly as the current orchestrator does; it never receives credentials, tokens, or `AuthProvider`/`AuthorizationService` internals, since those remain fully upstream of the service layer in both architectures.

---

## 17. Acceptance Criteria

1. All §12 tests pass, including zero-tolerance cross-user access tests exercised via HTTP.
2. No route or schema accepts a client-supplied `user_id` (verified by code review/inspection of every request schema in §7).
3. Every error path returns the uniform `APIError` shape (§11), verified by the shared test helper.
4. `/health` and `/ready` behave as specified, including the `503` degraded-dependency case.
5. No credential, token, or conversation content appears in captured logs during the full test run (§12).
6. `src/retrieval/`, `src/generation/`, and Phase 2.6–2.9 internals are unmodified beyond being called through their existing entry points (verified by diff/hash).
7. The API layer issues no query against the corpus/vector database (verified by inspection — no corpus table name appears anywhere under `src/api/`).
8. Performance baseline (§13) is measured and reported, with turn-endpoint API-layer overhead isolated from downstream pipeline latency.

---

## 18. Rollback Strategy

- The entire API layer lives under `src/api/` as a new, additive package — no existing module under `src/retrieval/`, `src/generation/`, `src/conversation/`, or `src/auth/` is modified to support it, since all integration happens through their already-existing public entry points.
- Removing `src/api/` entirely requires no change anywhere else in the codebase — the orchestrator, retrieval, generation, session store, and auth components all remain fully usable via direct Python calls (as they already are today, e.g. from test harnesses and evaluation scripts) with or without the API layer present.
- No schema or data migration is introduced by this phase — the API reads/writes only through existing Phase 2.8/2.9 storage abstractions, so there is nothing database-side to roll back.

---

## 19. Artifacts

```
src/api/
  main.py
  dependencies.py
  config.py
  errors.py
  routers/
    auth.py
    sessions.py
    turns.py
    health.py
  schemas/
    auth.py
    session.py
    turn.py
    error.py
  services/
    auth_service.py
    session_service.py
    turn_service.py
configs/
  p30_api.yaml
tests/api/
  test_auth_routes.py
  test_session_routes.py
  test_turn_routes.py
  test_health_routes.py
  test_error_model.py
  test_cross_user_isolation.py
  test_logging_safety.py
```

Implementation order: `schemas/` → `errors.py` (error model first, so every route can use it from day one) → `dependencies.py` (auth/authz wiring against existing Phase 2.9 components) → `services/` (thin wrappers) → `routers/` (`health.py` first as the simplest, then `auth.py`, `sessions.py`, `turns.py`) → `main.py` (app assembly, middleware, lifespan) → `config.py` → test suite (§12) → performance baseline (§13).

---

## 20. STOP / Sign-off Criteria

**STOP** after all §12 tests pass (zero cross-user violations), the §17 acceptance criteria are verified, and the §13 performance baseline is measured and reported.

Do not build the frontend, OAuth/social login, admin dashboard, or any agentic/LangGraph orchestration. Do not modify Phase 2.5–2.9 internals beyond calling their existing entry points. Await Abishek's review and explicit sign-off before scoping the next phase.