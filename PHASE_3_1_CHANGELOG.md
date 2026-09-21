# PHASE 3.1 CHANGELOG — API Hardening & Production Readiness

**Baseline:** Phase 3.0 FastAPI API Boundary (`phase_3_0_baseline`)  
**Phase:** 3.1  
**Status:** Completed & Verified  

---

## 1. Permitted API Contract Additions

The following response status codes, headers, and error shapes have been added to the API contract. All existing success schemas, endpoint paths, and success status codes remain strictly unchanged.

### New Status Codes
- `429 Too Many Requests`: Returned when request rate limits are exceeded (§5).
- `503 Service Unavailable`: Returned when global turn concurrency capacity is exceeded (`server_busy`), database/auth stores are unreachable (`dependency_unavailable`), or readiness probe fails.
- `504 Gateway Timeout`: Returned when RAG retrieval or LLM execution exceeds the configured `turn_timeout_s` boundary (§9).
- `409 Conflict`: Returned when duplicate registration is attempted (`conflict`), or when a concurrent turn is submitted on an active session (`session_busy`) (§7.2).
- `413 Payload Too Large`: Returned when request body exceeds `max_request_size_bytes` (100 KB default).
- `415 Unsupported Media Type`: Returned when mutation request methods (POST/PUT/PATCH) specify a non-JSON Content-Type.
- `404 Not Found`: Uniformly returned for non-existent, deleted, or cross-user session requests to prevent session enumeration (§4.2, §4.8).

### New Response Headers
- `Retry-After`: Returned in seconds on `429 rate_limited` and `503 server_busy` capacity responses.
- `X-Request-ID`: Echoed on all API responses (validated inbound `^[A-Za-z0-9_-]{8,64}$` or generated UUID v4).
- `WWW-Authenticate: Bearer`: Returned on `401 unauthenticated` responses.
- `X-Process-Time-Ms`: Optional server-side processing latency header.

### Uniform Error Payload
All error responses now strictly return the deterministic `APIError` shape:
```json
{
  "error_code": "unauthenticated | rate_limited | server_busy | dependency_unavailable | upstream_timeout | upstream_failure | session_busy | payload_too_large | validation_error | invalid_identifier | session_not_found | conflict | internal_error",
  "message": "Human readable sanitized error description",
  "request_id": "8eb9f057-9043-4bce-b85b-dc43af9bb050"
}
```

---

## 2. Hardening Additions & Subpackages

- **Configuration (`configs/p31_hardening.yaml`)**: Centralized timeouts (`request_timeout_s`, `turn_timeout_s`), field limits, rate limiting rules, CORS origins, and trusted proxy settings.
- **Hardening Subpackage (`src/api/hardening/`)**:
  - `rate_limiter.py`: In-memory sliding-window rate limiter with LRU eviction of idle keys.
  - `locks.py`: Per-session turn serialization lock (`SessionTurnLock`) and global turn capacity semaphore (`TurnConcurrencySemaphore`).
  - `redaction.py`: Structured JSON access log formatter and sensitive data redaction filter.
  - `middleware.py`: Content-Type filtering and request ID tracing middleware.
- **Health & Readiness (`src/api/routers/health.py`)**: Subsystem probing for session DB, corpus DB, orchestrator initialization, and secret presence.

---

## 3. Known Limitations & Operating Directives

- **In-Memory Rate Limiter**: Rate limit counters are in-process. In multi-worker deployments, effective rates scale with the number of worker processes. A pluggable `RateLimiter` protocol is provided for future Redis backends.
- **Worker Thread Cancellation**: Python worker threads running timed-out LLM queries cannot be forcibly killed; the timed-out thread finishes in the background, and the turn capacity semaphore is held until worker exit to protect GPU quota.
