# Phase 2.9: Authentication, Authorization & User Identity Boundary — Implementation Specification

**Depends on:** Phase 2.5 (frozen retrieval), Phase 2.6 (frozen grounded generation), Phase 2.7 (frozen conversational orchestrator), Phase 2.8 (persistent `SessionStore`, storage abstraction, PII redaction, session isolation — implementation complete & verified)
**Executing agent:** Antigravity
**Status:** SPECIFICATION ONLY — implementation not yet authorized

---

## 1. Phase Objective

Give every persistent conversation session an explicit, stable owner, and enforce that a user can only read/write/delete their own sessions — via a thin identity/authorization boundary placed strictly in front of Phase 2.7's orchestrator. Authentication, authorization, and session persistence remain three separate components with three separate responsibilities; none is folded into another.

---

## 2. Why Phase 2.9 Comes After 2.8

Phase 2.8 already made session state durable and isolated at the `session_id` level, but explicitly deferred the question of *who* a `session_id` belongs to — possession of the id was sufficient, by design, with the auth boundary documented but unbuilt. That boundary is now the entire scope of this phase: attach a real owner to each session and enforce it, without touching the storage engine, schema philosophy, or conversational logic Phase 2.8 already proved correct.

---

## 3. Scope

1. A minimal `User` identity model and lifecycle (§7).
2. A swappable `AuthProvider` interface, with one initial implementation (password-based) (§8).
3. Secure credential handling: hashing, validation, no plaintext storage (§12).
4. An `AuthorizationService` enforcing session ownership on every session read/write/delete (§9).
5. Extension of Phase 2.8's session schema with an owning `user_id` foreign key (§10, §11).
6. Authentication lifecycle: login, logout, token/session expiry, revocation (§13).
7. Security-focused test plan with zero-tolerance cross-user isolation tests (§20).

---

## 4. Non-Scope

- No changes to `src/retrieval/`, Phase 2.5 behavior, `src/generation/`, Phase 2.6 logic, or Phase 2.7 conversational logic (`FollowUpClassifier`/`ContextSelector`/`QueryRewriter`) — all called unchanged, now simply invoked with an authenticated user's sessions instead of anonymous ones.
- No modification to Phase 2.8's `SessionStore` interface or storage engine choice — only an additive `user_id` field and ownership-checking wrapper (§9, §10).
- No LangGraph or autonomous agents.
- No frontend/UI.
- No complete public API layer — this phase defines the auth/authorization boundary and its interfaces, not route handlers, request/response DTOs for an external API, or API versioning.
- No user profiling or personalization beyond the minimal account metadata in §7.
- No OAuth/SSO/third-party identity provider integration — the initial `AuthProvider` implementation is password-based; the abstraction is designed to admit an OAuth provider later without being built now.
- No multi-factor authentication, email verification flows, or password-reset flows — noted as reasonable near-future additions but not required for this phase's core boundary to be correct and testable.

---

## 5. Authentication vs Authorization vs Session Persistence

These are three components with non-overlapping responsibilities, never merged:

| Concern | Question answered | Component | Depends on |
|---|---|---|---|
| **Authentication** | Who is this user? | `AuthProvider` (§8) | Credential store only. |
| **Authorization** | Is this authenticated user allowed to access this specific session? | `AuthorizationService` (§9) | An `AuthenticatedUser` (output of authentication) + the session's owner record. |
| **Session persistence** | What conversation state belongs to which session? | Phase 2.8's `SessionStore` (unchanged) | A `user_id` value it stores and returns, but never validates or interprets. |

`SessionStore` continues to trust whatever `user_id`/`session_id` it is given, exactly as Phase 2.8 documented — it is `AuthorizationService`'s job, not `SessionStore`'s, to ensure the caller is entitled to that `user_id` before the store is ever invoked.

---

## 6. Architecture / Data Flow

```
User request (credentials, or bearer token + session_id)
      │
      ▼
AuthProvider (src/auth/auth_provider.py)
      │  → AuthenticatedUser { user_id, ... } | AuthenticationError
      ▼
AuthorizationService (src/auth/authorization_service.py)
      │  checks: does session_id (if provided) belong to user_id?
      │  → authorized | AuthorizationError
      ▼
ConversationalOrchestrator.handle_turn(user_id, session_id | None, query)   (Phase 2.7, additive param only)
      │
      ▼
SessionStore (Phase 2.8, unchanged interface + user_id column)
      │
      ▼
Frozen Phase 2.5 Retrieval → Frozen Phase 2.6 Grounded Generation
```

The orchestrator receives an already-authenticated, already-authorized `user_id` as a plain parameter — it does not call `AuthProvider` or `AuthorizationService` itself, and has no knowledge of credentials, tokens, or password hashes. This keeps Phase 2.7 genuinely unmodified in logic, with the only change being one additive parameter threaded through to session-ownership calls.

---

## 7. User Identity Model

Minimal by design — this is an internal identity boundary, not an account/profile platform:

```
User
  user_id: UUID (PK, server-generated, stable, never reused)
  created_at_utc: timestamptz
  status: "active" | "disabled" | "deleted"
  auth_identifier: text (e.g. email or username — the credential lookup key; unique)
  password_hash: text (nullable if a future non-password AuthProvider is used)
  last_login_at_utc: timestamptz, nullable
```

**Explicitly NOT stored:** name, phone number, address, or any profile/demographic field; login history beyond `last_login_at_utc`; device/IP metadata (deferred to §16's audit-log discussion, and even there kept minimal). `auth_identifier` (e.g. email) is the only piece of "personal" data required to authenticate, and is treated as sensitive (§15).

**Account lifecycle:** `active` (can authenticate and own sessions) → `disabled` (authentication fails cleanly; existing sessions remain in storage but become inaccessible, matching a "soft lock" rather than data loss) → `deleted` (explicit, irreversible: `password_hash`/`auth_identifier` are purged; owned sessions are handled per the deletion policy in §10 — cascaded or orphaned-and-purged, decided at implementation time and documented, defaulting to cascade for privacy-by-design consistency with Phase 2.8's session-deletion philosophy).

---

## 8. Authentication Provider Abstraction

```
AuthProvider (protocol, src/auth/auth_provider.py)
  authenticate(credentials) -> AuthenticatedUser | AuthenticationError
  create_account(auth_identifier, raw_password) -> User | AccountCreationError
  logout(session_token) -> None
  validate_token(token) -> AuthenticatedUser | AuthenticationError
```

- `AuthenticatedUser` is a minimal value object: `{ user_id, auth_identifier, issued_at, expires_at }` — never carries the password hash or any credential material past the authentication boundary.
- **Initial implementation:** `PasswordAuthProvider`, using bcrypt/argon2 password hashing (§12) and a server-issued, short-lived session token (opaque random value, not a JWT with embedded claims, to avoid token-content leakage risk and keep revocation trivial via server-side lookup — see §12).
- **Replaceability:** the interface is the only contract `AuthorizationService` and any future API layer depend on; a future `OAuthProvider` or `SSOProvider` implements the same protocol and can be swapped via config (`configs/p29_auth.yaml: auth.provider`) with no change above this layer — mirroring the Phase 2.8 storage-backend swap pattern.

---

## 9. Authorization Model

`AuthorizationService` (`src/auth/authorization_service.py`) is the single place ownership is checked:

```
AuthorizationService
  authorize_session_access(authenticated_user, session_id, action: "read"|"write"|"delete") -> Authorized | AuthorizationError
```

- Before any `SessionStore` call for an existing session, the orchestrator's entry point calls `authorize_session_access` first. If the session's `user_id` does not match the authenticated user's `user_id`, the request fails with `AuthorizationError` — the `SessionStore` call is never made (no timing/existence side-channel from a downstream store error).
- **Session-ID guessing is not a bypass:** `session_id`s are server-generated UUIDv4 (already true since Phase 2.7/2.8) and are never sufficient on their own — every access additionally requires a valid `AuthenticatedUser` whose `user_id` matches the session's stored owner. Guessing a valid UUID without a matching authenticated identity still fails authorization.
- **New session creation:** always stamps the newly created session with the authenticated user's `user_id` at creation time — there is no path to create an unowned or differently-owned session.
- **Unauthenticated vs. unauthorized, defined distinctly:**
  - *Unauthenticated* — no valid `AuthenticatedUser` at all (missing/invalid/expired token, bad credentials). Response: a generic authentication-failure error, no information about whether a resource exists.
  - *Unauthorized* — a valid `AuthenticatedUser` exists, but does not own the requested `session_id`. Response: the same generic "not found or not accessible" error as a nonexistent session (§14) — never a distinct "this session exists but isn't yours" message, to avoid confirming session existence to a non-owner.

---

## 10. Session Ownership Model

- Phase 2.8's `sessions` table gains one additive column: `user_id UUID NOT NULL REFERENCES users(user_id)`. No other Phase 2.8 column changes.
- `SessionStore.create_session` now requires a `user_id` argument (the one additive, non-breaking interface change permitted by the hard constraints — see §18 for how this is threaded without altering Phase 2.8's read/update/delete method signatures, which already accept `session_id` and don't need to accept `user_id` since ownership is checked one layer above, in `AuthorizationService`, not inside the store).
- Ownership is immutable once set — no "transfer session to another user" operation exists in this phase.
- `InMemorySessionStore` (Phase 2.8's dev/test backend) is extended with the same `user_id` field for interface parity, so the full auth/authorization test suite can run against either backend.

---

## 11. Database Schema

**`users`** (new table, same `session_db` schema/database as Phase 2.8's session tables — still fully separate from the corpus database; no foreign key from `users` or `sessions` ever references `chunks`/`embeddings`)

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID, PK | Server-generated. |
| `auth_identifier` | text, UNIQUE NOT NULL | e.g. email; case-normalized before uniqueness check. |
| `password_hash` | text, nullable | Nullable to admit a future non-password `AuthProvider`. |
| `status` | text, CHECK (`active`/`disabled`/`deleted`) | |
| `created_at_utc` | timestamptz | |
| `last_login_at_utc` | timestamptz, nullable | |

**`auth_sessions`** (new table — distinct from `sessions`; this is the *authentication* token/session, not the *conversation* session, and the naming is kept deliberately distinct to avoid confusing the two concepts in code or schema)

| Column | Type | Notes |
|---|---|---|
| `token_id` | UUID, PK | The opaque bearer token value itself (or a hash of it — see §12). |
| `user_id` | UUID, FK → `users.user_id`, `ON DELETE CASCADE` | |
| `issued_at_utc` | timestamptz | |
| `expires_at_utc` | timestamptz | Indexed for expiry sweep, mirroring Phase 2.8's `sessions.expires_at_utc` pattern. |
| `revoked` | boolean, default false | Set true on logout; a revoked token fails `validate_token` immediately, no need to wait for natural expiry. |

**`sessions`** (Phase 2.8 table, modified)

| Column | Type | Notes |
|---|---|---|
| ...existing Phase 2.8 columns, unchanged... | | |
| `user_id` | UUID, FK → `users.user_id`, `ON DELETE CASCADE` | **New.** Cascading delete means deleting a user deletes their conversation sessions too — consistent, single-direction ownership cleanup. |

**Indexes:** `users(auth_identifier)` (unique, supports login lookup); `auth_sessions(user_id)`; `auth_sessions(expires_at_utc)`; `sessions(user_id)` (supports "list my sessions" without a table scan, if ever needed by a future API).

**Transaction boundaries:** account creation is a single insert (uniqueness constraint on `auth_identifier` is the race-safety mechanism for duplicate signups — a losing concurrent insert fails cleanly with a constraint violation, surfaced as `AccountCreationError`, not a crash). Login is read-then-insert (verify password, then insert a new `auth_sessions` row) — not required to be a single transaction since a failed insert after successful verification simply means the user retries login; no partial-auth state is exposed either way.

---

## 12. Credential & Secret Handling

- **Password hashing:** bcrypt or argon2id (config-selectable, argon2id preferred where available), with a per-password random salt (built into both algorithms) — no custom hashing, no unsalted/plain SHA-family hashing.
- **Never store or log plaintext passwords** — the raw password exists only transiently in memory during `create_account`/`authenticate` calls and is never persisted, cached, or written to any log line.
- **Token handling:** the bearer token issued at login is a cryptographically random value (not a predictable sequence, not a JWT with embedded claims for this phase's scope — keeping revocation a simple database lookup rather than requiring a token-blacklist system). The database stores either the token directly in a restricted-access table or a hash of it (config-decided; storing a hash is preferred, mirroring password-hash practice, so a database read alone can't be replayed as a valid token) — this decision is finalized at implementation time and documented in the code, not left ambiguous.
- **Secure random identifiers:** all of `user_id`, `token_id`, `session_id` continue to use a cryptographically secure UUID generator (already true from Phase 2.7/2.8 for `session_id`; extended consistently here).
- **Secret/configuration handling:** any pepper/signing secret used alongside password hashing (if the chosen library supports one) is read from environment/config, never hardcoded, and is explicitly out of version control — same discipline the project already applies to API keys (e.g., the Gemini key in Phase 2.6).
- **Least-privilege database access:** the application's database role for `users`/`auth_sessions` requires no more privilege than `SELECT`/`INSERT`/`UPDATE` on those specific tables — no superuser or cross-schema privilege is requested by this phase.
- **Brute-force/rate-limiting:** login attempts are rate-limited per `auth_identifier` (config: `max_login_attempts_per_window`, `window_minutes`) — implemented as a simple counter in this phase (in the `users` table or a lightweight counter table), not a full distributed rate-limiter, since that belongs to a future API/gateway layer; this phase provides the minimum protection appropriate to a backend-only boundary.
- **Account enumeration:** login failures return an identical generic error regardless of whether `auth_identifier` doesn't exist or the password was wrong — no "user not found" vs. "wrong password" distinction is exposed.

---

## 13. Authentication Lifecycle

| Event | Behavior |
|---|---|
| **Account creation** | `auth_identifier` + raw password → validated (basic format/strength check, config-defined minimum) → hashed → `User` row created with `status: active`. |
| **Login** | Credentials → `PasswordAuthProvider.authenticate` verifies hash → on success, issues a new `auth_sessions` token (TTL config: `auth_token_ttl_minutes`, independent of Phase 2.8's conversation-session TTL — these are two different expiring concepts, not shared config) → updates `last_login_at_utc`. |
| **Authenticated request context** | Every subsequent request presents the token; `validate_token` resolves it to an `AuthenticatedUser` (checking not expired, not revoked) before any conversation/session logic runs. |
| **Logout** | Sets `auth_sessions.revoked = true` for the presented token — immediate effect, no need to wait for TTL expiry. |
| **Expiration** | Same lazy-check + periodic-sweep pattern as Phase 2.8's conversation-session TTL (§12 of that spec), applied here to `auth_sessions.expires_at_utc` — reuses the pattern, not the same table/sweeper instance. |
| **Revoked/expired authentication state** | `validate_token` returns `AuthenticationError` for both revoked and expired tokens, with the same generic message for each (no signal to the caller about *why* it failed, beyond "authenticate again"). |
| **Invalid credentials** | Generic `AuthenticationError`, same message as any other authentication failure (§12's enumeration protection). |
| **Disabled/deleted user attempting login** | Generic `AuthenticationError` — does not reveal account status. |

---

## 14. Authorization Failure Handling

| Scenario | Response |
|---|---|
| No token presented | `AuthenticationError` — "authentication required." |
| Expired/revoked/invalid token | `AuthenticationError` — same generic message as above. |
| Valid user, `session_id` belongs to a different user | `AuthorizationError`, surfaced identically to "session not found" — never confirms the session's existence to a non-owner. |
| Valid user, `session_id` does not exist at all | Same generic "not found or not accessible" response as the above — authorization and existence failures are indistinguishable from the caller's point of view, by design. |
| Valid user, no `session_id` provided (new session) | Proceeds normally; a new session is created and owned by the authenticated user. |
| Downstream `SessionStore`/database failure during an already-authorized request | Follows Phase 2.8's existing failure behavior (§16 of that spec) unchanged — authorization succeeding doesn't change how storage failures are handled. |

---

## 15. Privacy & Data Minimization

- The only identity-linked personal datum stored is `auth_identifier` (e.g., email) — required to authenticate, minimized to that single field, consistent with §7.
- Password hashes are not "personal data" in the privacy-risk sense (they're not reversible to the password) but are still treated as sensitive secrets under the same never-log discipline as tokens (§16).
- Phase 2.8's PII-redaction behavior for conversation content is entirely preserved and unaffected — this phase adds an owner to a session, it does not change what's inside a session's turns or how `SessionPrivacyGuard` treats that content.
- Account deletion (`status: deleted`) purges `auth_identifier` and `password_hash` — an authenticated identifier is not retained after account deletion, only an anonymized `user_id` remains referenced by any conversation data that isn't itself cascaded/purged (matching whichever deletion behavior §7 finalizes).

---

## 16. Logging & Audit Safety

- **Never log:** raw passwords, password hashes, bearer tokens (or their hashes), or full `auth_identifier` values in ordinary operational logs — where an identifier must appear for debugging, it is truncated/masked (e.g., first character + domain for an email).
- **Safe audit metadata:** login success/failure events are logged with `user_id` (not `auth_identifier`), timestamp, and outcome (`success`/`failure`) — no credential material, no token value. Failure logs do not distinguish enumeration-sensitive reasons (§12) even internally beyond what's needed for rate-limiting.
- **Authorization failures** (cross-user access attempts) are logged with both the requesting `user_id` and the target `session_id` (not its content) — this is valuable security-audit signal and contains no conversation content, so it's exempt from the "never log content" rule that governs Phase 2.8's conversation logs.
- This phase's logging additions are entirely separate log lines from Phase 2.8's session-operation logs — no merging of auth events and conversation-content-adjacent events into one log stream, to keep any future log-review process able to reason about each independently.

---

## 17. Security Threat Model

| Threat | Mitigation |
|---|---|
| Password database compromise | Hashes only (bcrypt/argon2id, salted) — no plaintext recovery; §12. |
| Session/auth token theft | Short TTL, server-side revocation on logout, opaque random (or hashed-at-rest) tokens with no embedded claims to forge; §12/§13. |
| Session-ID guessing/enumeration | UUIDv4 unguessable ids + mandatory ownership check independent of id secrecy; §9. |
| Cross-user session access (IDOR-style) | `AuthorizationService` ownership check before every `SessionStore` call, zero-tolerance tested; §9/§20. |
| Account enumeration via login/signup responses | Generic error messages, no existence leakage; §12. |
| Brute-force credential guessing | Per-identifier rate limiting; §12. |
| Credential/token leakage via logs | Explicit never-log list, masked identifiers; §16. |
| Replay of a revoked/expired token | `validate_token` checks both `revoked` and `expires_at_utc` on every call, not cached past token issuance; §13. |
| Privilege escalation via database access | Least-privilege application DB role, no cross-schema access to the corpus DB; §12. |
| Concurrent duplicate signups (same identifier) | Unique constraint on `auth_identifier`, race-safe by database constraint, not application-level check-then-insert alone; §11. |

---

## 18. Migration Strategy from Phase 2.8

- **Schema migration:** additive only — `ALTER TABLE sessions ADD COLUMN user_id ...` plus two new tables (`users`, `auth_sessions`). No existing Phase 2.8 column is renamed or removed.
- **Existing Phase 2.8 sessions (if any exist from prior testing/dev use) have no owner.** This phase does not attempt to retroactively assign ownership to pre-existing anonymous sessions — they are treated as orphaned/test data, explicitly out of scope to migrate, and may be purged or left inert (decided operationally, not by this spec, since Phase 2.8 was itself pre-production).
- **`SessionStore` interface change:** `create_session` gains a required `user_id` parameter. This is the one interface change to Phase 2.8's contract, and it is additive-at-call-site (existing call sites are updated to pass the now-available authenticated `user_id`) rather than a behavior change to any other method — `get_session`/`save_turn`/`delete_session` keep their existing signatures, since ownership enforcement happens one layer above in `AuthorizationService`, not inside the store itself.
- **Backward compatibility:** Phase 2.8's own storage-correctness test suite (restart recovery, TTL, deletion, concurrency) is re-run unchanged against the now-`user_id`-bearing schema to confirm none of that behavior regressed.
- **Cutover:** enabling this phase means every session-creating request must now come with a valid `AuthenticatedUser` — there is no anonymous-session mode retained once this phase is enabled (unlike Phase 2.8's own in-memory/postgres backend toggle, this is not meant to be optional in a production configuration, though the auth-disabled dev/test path is retained for the test suite itself, clearly flagged as test-only).

---

## 19. Evaluation Methodology

- Reuse Phase 2.8's persistence-correctness suite, re-run against the modified schema, to confirm zero regression (§18).
- New security-focused evaluation is added on top (§20), with cross-user isolation treated as zero-tolerance pass/fail, not a graded metric — consistent with how Phase 2.7/2.8 already treated session isolation.
- Performance overhead (§21) is measured, not targeted against an invented threshold, consistent with the project's established process-over-arbitrary-threshold philosophy.

---

## 20. Security Test Plan

`tests/auth/` covering, at minimum one test per:

- **Valid authentication** — correct credentials succeed, return a usable `AuthenticatedUser`.
- **Invalid authentication** — wrong password, nonexistent identifier, malformed token — all fail with the same generic error.
- **Authorization boundaries** — owner can read/write/delete their own session; non-owner cannot, for every action type.
- **Cross-user session access** — user A's authenticated token used to request user B's `session_id` → `AuthorizationError`, zero-tolerance, every time.
- **Session-ID manipulation** — guessing/incrementing/fuzzing session ids under a valid-but-unrelated authenticated user → never succeeds.
- **Deleted users** — a deleted user's token (if somehow still held) fails authentication; their owned sessions are handled per §7/§18's finalized deletion behavior.
- **Revoked credentials** — a token explicitly revoked via logout fails `validate_token` immediately, not just at natural TTL expiry.
- **Expired authentication** — a token past `expires_at_utc` fails, even if never explicitly revoked.
- **Concurrent requests** — two simultaneous requests under the same authenticated user, different sessions, both succeed without cross-contamination; two simultaneous login attempts for the same identifier don't create duplicate `users` rows (constraint-enforced, §11).
- **Credential leakage in logs** — automated scan of emitted log lines during a full auth-flow test run confirms no plaintext password, hash, or token value appears (§16).
- **Database failures** — auth database unavailable → clean `AuthenticationError`-adjacent failure, not a crash or silent bypass (fail closed, never fail open into "treat as authenticated").
- **Replay/duplicate authentication attempts** — reusing an already-revoked token, or a duplicate signup with the same `auth_identifier`, both rejected cleanly per §11/§13.

---

## 21. Performance Metrics

| Metric | Definition |
|---|---|
| **Authentication latency** | Mean/P50/P95 time for `authenticate()` (dominated by password-hash verification cost — expected and acceptable to be slower than a plain lookup, by design). |
| **Token validation latency** | Mean/P50/P95 for `validate_token()` — this runs on every authenticated request, so its overhead relative to Phase 2.8's existing session-store latency is reported explicitly. |
| **Authorization check overhead** | Added latency of `authorize_session_access()` per conversation turn, reported alongside Phase 2.8's already-measured `save_turn`/`get_session` latency, not replacing it. |
| **End-to-end overhead** | Total added latency (auth + authorization) on top of a full Phase 2.7 conversational turn, reported as an observed baseline for future capacity planning — no invented pass/fail threshold. |

---

## 22. Acceptance Criteria

1. All §20 security tests pass, with zero cross-user access or session-ID-manipulation successes (zero-tolerance).
2. Phase 2.8's persistence-correctness suite passes unchanged against the migrated schema (§18).
3. No plaintext password or raw token ever appears in any log line, verified by automated scan (§16/§20).
4. `src/retrieval/`, Phase 2.5 behavior, `src/generation/`, Phase 2.6 logic, and Phase 2.7 conversational logic are unmodified beyond the single additive `user_id` parameter threading described in §18 (verified by diff/hash).
5. `AuthProvider` is demonstrated swappable: the security test suite passes against `PasswordAuthProvider`, and the interface is confirmed sufficient (by inspection/design review, not necessarily a second built implementation) to support a future OAuth/SSO provider without changing `AuthorizationService` or the orchestrator.
6. Performance overhead (§21) is measured and reported as a baseline.
7. The corpus database remains untouched and unreferenced by any table/query introduced in this phase.

---

## 23. Rollback / Isolation Requirements

- Schema changes are additive (§18); rolling back means dropping the two new tables and the `sessions.user_id` column, with no risk to corpus data (separate database/schema, as in Phase 2.8) and no risk to pre-existing session content (only ownership metadata is removed).
- Disabling this phase at the config level (a feature flag, `configs/p29_auth.yaml: auth.enabled: false`, used only in test/dev contexts per §18) reverts request handling to Phase 2.8's pre-auth behavior for local testing purposes; this flag is not intended for production use once the phase is accepted, but exists so the auth layer can be independently toggled during development and rollback drills.
- No changes to Phase 2.5/2.6/2.7 internals means reverting this phase entirely requires no changes to retrieval or generation code, matching the rollback discipline established in every prior phase.

---

## 24. Relationship to Future API / Frontend Layer

This phase produces exactly the boundary a future **Frontend → API → Authentication → Authorization → Conversation → RAG** architecture needs: `AuthProvider` and `AuthorizationService` are backend interfaces a future API layer calls directly (e.g., an API route wraps `authenticate()` for a `/login` endpoint and `validate_token()` as request middleware) — no route handlers, request/response schemas, or HTTP-layer concerns are built here, but nothing about this phase's design assumes a particular API framework, keeping that a clean, unblocked next step.

---

## 25. Relationship to Future Agentic / LangGraph Layer

A future agent/orchestration layer (replacing `ConversationalOrchestrator` per Phase 2.7 §20's stated plan) receives only an `AuthenticatedUser`'s `user_id` as context — the same minimal parameter the orchestrator itself receives in this phase (§6). It never receives credentials, password hashes, or raw tokens, and has no dependency on `AuthProvider` or `AuthorizationService` internals; ownership checks continue to happen in the same `AuthorizationService` layer regardless of what orchestrates the conversation above it. This keeps identity a stable, narrow input to any future orchestration layer rather than a capability that layer would need to reimplement or that could be abused if that layer were ever exposed to less-trusted logic (e.g., a tool call).

---

## 26. Expected Files / Artifacts

```
src/auth/
  schemas.py               # User, AuthenticatedUser, AuthenticationError, AuthorizationError
  auth_provider.py          # AuthProvider protocol + PasswordAuthProvider
  authorization_service.py
  password_hashing.py        # bcrypt/argon2id wrapper, isolated for easy algorithm swap
  rate_limiter.py             # simple per-identifier login attempt counter
db/
  session_db/
    migrations/
      p29_add_users_and_auth_sessions.sql   # additive schema migration (§11, §18)
configs/
  p29_auth.yaml               # auth provider selection, token TTL, rate-limit thresholds, auth.enabled test flag
tests/auth/
  test_auth_provider.py, test_authorization_service.py, test_password_hashing.py,
  test_cross_user_isolation.py, test_logging_safety.py, test_migration_compat.py   # covering §20
```

Implementation order: `schemas.py` → `password_hashing.py` → `auth_provider.py` (`PasswordAuthProvider`) → migration SQL → `authorization_service.py` → `rate_limiter.py` → orchestrator call-site update (additive `user_id` threading only, per §18) → test suite (§20) → `configs/p29_auth.yaml` finalized with defaults matched to test results.

---

## 27. STOP Condition and Sign-Off Requirements

**STOP** after all §20 security tests pass with zero cross-user/authorization violations, Phase 2.8's persistence suite passes unchanged against the migrated schema, and the §21 performance overhead baseline is measured and reported.

Do not build the public API layer, frontend, or any LangGraph/agentic orchestration. Do not modify `src/retrieval/`, `src/generation/`, or Phase 2.6/2.7 logic beyond the single additive `user_id` parameter documented in §18. Await Abishek's review and explicit sign-off before scoping the next phase.