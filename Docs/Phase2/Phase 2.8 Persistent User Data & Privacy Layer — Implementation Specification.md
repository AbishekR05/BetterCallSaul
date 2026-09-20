# Phase 2.8: Persistent User Data & Privacy Layer — Implementation Specification

**Depends on:** Phase 2.5 (frozen retrieval), Phase 2.6 (frozen grounded generation, signed off), Phase 2.7 (conversational orchestration, `SessionStore` interface, `InMemorySessionStore`, `SessionPrivacyGuard` — signed off with a documented jurisdiction-consistency evaluation exception, unrelated to this phase)
**Executing agent:** Antigravity
**Status:** SPECIFICATION ONLY — implementation not yet authorized

---

## 1. Phase Objective

Replace Phase 2.7's `InMemorySessionStore` with a database-backed, production-oriented persistent session store — surviving process restarts, supporting concurrent access, and enforcing explicit retention/deletion — while keeping the existing `SessionStore` interface as the only thing the `ConversationalOrchestrator` depends on. This phase persists conversation/session state only; it does not touch the legal corpus, retrieval, or generation systems, and it does not introduce user accounts, authentication, or personalization.

---

## 2. Why Phase 2.8 Comes After 2.7

Phase 2.7 deliberately deferred persistence, using an in-memory store to prove out session isolation, TTL, context selection, and query rewriting as correct, testable primitives without the added variable of a database. Those primitives are now signed off. Phase 2.8's job is narrow and mechanical by design: give the same `SessionStore` contract a durable backend, so nothing above it (`ConversationalOrchestrator`, `FollowUpClassifier`, `ContextSelector`, `QueryRewriter`) needs to know or care that storage changed.

---

## 3. Scope

1. A `PersistentSessionStore` implementing Phase 2.7's `SessionStore` interface unchanged, backed by PostgreSQL (a **separate schema/database from the legal corpus** — see §5).
2. A minimal, explicitly-justified persisted data model (§7/§8).
3. Privacy-by-design controls: redaction-before-write, retention limits, expiration, explicit deletion (§6, §12, §13).
4. A storage abstraction that keeps PostgreSQL an implementation detail behind the interface, with `InMemorySessionStore` retained as a first-class dev/test backend (§9).
5. Formal session-isolation tests extended to the persistence layer (§10, §17, §20).
6. A migration path from Phase 2.7's in-memory behavior to persistent storage that changes no observable orchestrator behavior (§15).
7. Safe, redaction-aware logging/observability for the persistence layer (§14).
8. The authentication/authorization interface boundary this phase assumes but does not implement (§11).

---

## 4. Non-Scope

- No changes to `src/retrieval/`, Phase 2.5 retrieval behavior, `src/generation/`, or Phase 2.6 grounding/citation logic.
- No redesign of Phase 2.7 conversational logic (`FollowUpClassifier`, `ContextSelector`, `QueryRewriter`) — only the storage backend changes; any interface adjustment is limited to what §9 strictly requires and must be additive, not behavior-changing.
- No LangGraph or autonomous agents.
- No user profiling, personalization, or cross-session preference learning.
- No real authentication/authorization implementation — interface boundary only (§11).
- No frontend/UI.
- No deployment/cloud infrastructure beyond what's strictly required to run PostgreSQL for this data (i.e., no Docker/K8s/cloud provisioning work is authorized here beyond local schema setup).
- No storage of legal evidence, citations-as-documents, or corpus data — a `GroundedAnswer`'s citations are stored as lightweight references (chunk_id + minimal display fields already present in Phase 2.6's `Citation` object), never as a duplicate copy of corpus text.

---

## 5. Architecture / Data Flow

```
User request (query, session_id | None)
      │
      ▼
ConversationalOrchestrator (Phase 2.7, unchanged)
      │
      ▼
SessionStore interface (Phase 2.7, unchanged contract)
      │
      ├── InMemorySessionStore   (dev/test backend, retained)
      │
      └── PersistentSessionStore  (new, this phase)
                │
                ▼
          Session DB connection pool
                │
                ▼
          PostgreSQL — dedicated "session_db" schema/database,
          physically/logically separate from the corpus DB
          (chunks/embeddings tables are never touched by this phase)
```

Backend selection is config-driven (`configs/p28_persistence.yaml: session_store.backend: in_memory | postgres`), resolved once at orchestrator startup via a factory function — the orchestrator constructs a `SessionStore` from config and never imports or references a concrete backend class directly.

**Data-plane separation:** the session/user data store and the legal corpus vector store are two distinct databases (or at minimum two distinct schemas with no cross-schema foreign keys), enforced by using a separate connection pool/config block for each. This is a hard boundary, not just a convention — no query in this phase joins session tables against corpus tables.

---

## 6. Privacy-by-Design Principles

- **Data minimization first:** the default assumption for any candidate field is "do not persist it" unless §7 gives an explicit justification.
- **Redact before write, not after:** the existing Phase 2.7 `SessionPrivacyGuard` runs before any data reaches `PersistentSessionStore.save_turn(...)` — the persistence layer never receives, and therefore never accidentally stores, unredacted sensitive patterns. This ordering is enforced by construction: `PersistentSessionStore` only exposes append/update methods that take already-guarded `ConversationTurn` objects, never raw user text.
- **Expiration and deletion are first-class operations**, not administrative afterthoughts — both are part of the `SessionStore` interface and are exercised in every test suite (§20).
- **Conversation context is never conflated with legal evidence:** persisted `Citation` references point back to corpus `chunk_id`s; the corpus text itself is not duplicated into the session database. This preserves Phase 2.6/2.7's existing distinction between "what the user was told" and "what the system considers authoritative legal evidence."
- **No inference layer:** this phase does not analyze stored sessions to build behavioral or personalization profiles; persisted data exists solely to let a session's own conversation continue coherently across restarts.

---

## 7. Data Model

Persisted (all fields already exist in Phase 2.7's `ConversationSession`/`ConversationTurn` schemas — this phase does not introduce new conversational fields):

| Field | Justification |
|---|---|
| `session_id` | Required — the isolation key for every operation. |
| `created_at_utc`, `last_active_utc`, `expires_at_utc` | Required for TTL enforcement and expiration sweeps. |
| `status` (`active`/`expired`/`closed`) | Required lifecycle state. |
| `turn_index`, `user_query` (post-redaction), `rewritten_query`, `followup_classification` | Required to reconstruct conversational context across restarts — this is the functional purpose of persistence. |
| `grounded_answer` (Phase 2.6's `GroundedAnswer`, including resolved `Citation` references) | Required so a resumed session can display/reference its own prior answers; citations are references, not copied corpus text. |
| `jurisdiction_carried_forward`, `domain_carried_forward` | Required — consumed directly by Phase 2.7's `ContextSelector`. |
| `generation_metadata` (from `GroundedAnswer.generation_metadata`) | Retained since it's already part of the embedded `GroundedAnswer` object; not duplicated separately. |

**Explicitly NOT persisted:**
- Raw, pre-redaction user text (never reaches this layer — see §6).
- `ContextSelectionTrace` debug detail (token estimates, selection reasoning) — useful for evaluation runs, not for production session continuity; kept in logs/eval artifacts only (§14), never in the session DB.
- Any free-text field beyond what Phase 2.7's schemas already define — this phase adds no new "notes" or "metadata" catch-all columns.
- Any identity/account information — there is no `user_id` distinct from `session_id` in this phase (see §11).
- IP addresses, device identifiers, or any request-level metadata not already part of the conversational schema.

---

## 8. Database Schema

Two tables, normalized, in a dedicated `session_db` schema:

**`sessions`**
| Column | Type | Notes |
|---|---|---|
| `session_id` | UUID, PK | Server-generated, matches Phase 2.7's `session_id`. |
| `created_at_utc` | timestamptz | |
| `last_active_utc` | timestamptz | Updated on every turn write. |
| `expires_at_utc` | timestamptz | Recomputed on each turn write as `last_active_utc + TTL`. Indexed for the expiration sweep (§12). |
| `status` | text, check constraint (`active`/`expired`/`closed`) | |
| `turn_count` | integer | Denormalized counter, maintained transactionally with turn inserts, avoids a `COUNT(*)` on read. |

**`conversation_turns`**
| Column | Type | Notes |
|---|---|---|
| `turn_id` | UUID, PK | |
| `session_id` | UUID, FK → `sessions.session_id`, `ON DELETE CASCADE` | Cascading delete is the mechanism behind §12's "delete session" guarantee — no orphaned turns can outlive their session. |
| `turn_index` | integer | Unique together with `session_id`; ordering key. |
| `user_query` | text | Post-redaction only. |
| `rewritten_query` | text, nullable | |
| `followup_classification` | text | |
| `jurisdiction_carried_forward` | text, nullable | |
| `domain_carried_forward` | text, nullable | |
| `grounded_answer_json` | jsonb | Serialized `GroundedAnswer` (including citations, safety flags, generation metadata) — stored as a single JSONB document rather than further normalized, per the "avoid unnecessary database complexity" guidance; citations inside it are references (chunk_id + display fields), not corpus text copies. |
| `timestamp_utc` | timestamptz | |

Indexes: `sessions(expires_at_utc)` for the sweep; `sessions(status)`; `conversation_turns(session_id, turn_index)` (composite, supports both isolation-scoped lookups and ordered retrieval in one index).

**Design decision — individual rows vs. serialized session blob:** conversation turns are stored as **individual rows**, not one serialized JSON blob per session, because (a) it gives a per-turn index for the composite lookup above, (b) it supports appending a new turn as a single-row insert without rewriting the whole session, and (c) it keeps the door open for future per-turn analytics/evaluation queries without deserializing entire sessions. The `GroundedAnswer` *within* a turn remains a single JSONB document, since Phase 2.6 already treats it as an atomic, versioned output object with no need for its internals to be queried relationally.

**Transaction boundaries:** each `save_turn()` call is one transaction: insert the `conversation_turns` row, increment `sessions.turn_count`, and update `sessions.last_active_utc`/`expires_at_utc` — all three or none (standard `BEGIN`/`COMMIT`, no multi-statement partial-write path). Session creation is its own single-row-insert transaction. Deletion (§12) is a single-statement cascading delete, also transactional by default.

---

## 9. Storage Abstraction

- `SessionStore` (Phase 2.7's interface — `create_session`, `get_session`, `save_turn`, `expire_session`, `delete_session`, plus whatever minimal surface Phase 2.7 already defines) is **not modified**. If any method signature gap is found during implementation (e.g., a batch-read method useful for the migration compatibility test in §20), it is added as a new, additive method — never a changed signature on an existing method, to avoid silently breaking `InMemorySessionStore` or the orchestrator's existing call sites.
- `PersistentSessionStore` implements the interface using a connection pool (config-driven pool size), with all SQL confined to this one module (`src/conversation/persistent_session_store.py`) — no SQL string appears in the orchestrator, schemas, or any Phase 2.7 module.
- `InMemorySessionStore` remains available and is the default backend for unit tests and local dev (`configs/p28_persistence.yaml: session_store.backend: in_memory` as the test-suite default), per the hard constraint to keep it available.
- A backend factory (`src/conversation/session_store_factory.py`) is the single place that reads config and returns a concrete `SessionStore` — this is the one piece of new wiring the orchestrator's startup code needs to know about; the orchestrator's runtime logic is otherwise untouched.

---

## 10. Component Responsibilities

| Component | Responsibility (this phase) |
|---|---|
| `SessionPrivacyGuard` (Phase 2.7, reused) | Unchanged — still runs before any write reaches storage. No new redaction rules are added in this phase unless a persistence-specific leakage risk is found (none anticipated). |
| `PersistentSessionStore` | Implements `SessionStore` against PostgreSQL; owns all SQL, connection pooling, and transaction boundaries (§8). |
| `session_store_factory` | Backend selection at startup, config-driven. |
| `ConversationalOrchestrator` (Phase 2.7, unchanged) | Continues to depend only on the `SessionStore` interface; no awareness of the backend. |
| `ExpirationSweeper` (new, `src/conversation/expiration_sweeper.py`) | A small, independently-runnable job (invoked on-access — lazy check on `get_session` — and optionally via a periodic background task) that marks sessions `expired` once past `expires_at_utc`, per Phase 2.7's existing TTL semantics, now durable across restarts. |
| Future Authentication/Authorization layer (not built here) | Would sit strictly in front of the orchestrator, attaching a verified identity to a request before a `session_id` is created or accessed — see §11. |

---

## 11. Authentication / Authorization Boundary

Persistence is explicitly **not** authentication. This phase draws three separate, non-overlapping concerns:

- **Identity/Authentication** — verifying who is making a request. **Not implemented in this phase.** No login, no accounts, no credentials are introduced.
- **Session Persistence** — durably storing conversation state keyed by `session_id`. **This phase's actual scope.**
- **Authorization** — deciding whether a given caller may access a given `session_id`. **Not implemented in this phase**, but the interface boundary is defined: any future auth layer would sit in front of `ConversationalOrchestrator.handle_turn()`, verifying that the caller is entitled to the `session_id` they present, before the orchestrator (and therefore `SessionStore`) is ever invoked. `SessionStore` itself continues to trust that any `session_id` it receives has already been authorized upstream — it does not perform authorization checks itself, matching Phase 2.7's existing "possession of the id is sufficient" model, now explicitly documented as a boundary this phase does not change.

This phase's persistence layer is therefore forward-compatible with a future auth layer without modification: adding authentication later means adding a new layer above the orchestrator, not changing `PersistentSessionStore`, its schema, or its interface.

---

## 12. Retention & Deletion Policy

- **TTL:** unchanged from Phase 2.7 — `session_ttl_minutes` (default 60), now enforced durably via `expires_at_utc` in the database rather than only in-process memory.
- **Expiration sweep:** lazy (on-access, in `get_session`) is mandatory and always active; a periodic background sweep (config-toggleable, e.g., every 5 minutes) is provided so long-idle sessions are marked `expired` even without being accessed, keeping the `active` row count bounded.
- **Expired sessions are not immediately deleted** — they transition to `status: "expired"` and become unreadable/unwritable via the normal `SessionStore` interface (matching Phase 2.7 semantics), but remain in storage for a configurable grace period (`expired_retention_days`, default short, e.g. 7 days) before a separate, explicit hard-delete job purges them — this two-stage approach (expire, then later purge) avoids irreversible data loss from a transient TTL misconfiguration while still bounding total retention.
- **Explicit deletion:** `delete_session(session_id)` performs an immediate, irreversible cascading delete (§8's `ON DELETE CASCADE`) of the session and all its turns — available to be called directly, independent of the TTL/expiry path, satisfying the "explicit deletion" requirement as a first-class, always-available operation.
- **No indefinite retention path exists** — every session is on a bounded lifecycle (active → expired → purged, or explicitly deleted at any point).

---

## 13. PII Handling

- Unchanged mechanism from Phase 2.7: `SessionPrivacyGuard`'s pattern-based redaction (Aadhaar, PAN, credit card, bank account patterns) runs before any text is handed to `PersistentSessionStore`.
- This phase adds one guarantee Phase 2.7's in-memory store didn't need: **redaction-before-write is tested against the actual persistence path**, not just the in-memory path — i.e., a test asserts that a known PII pattern submitted through the full orchestrator → store flow is redacted in the row actually written to `conversation_turns`, not merely redacted in an intermediate in-process object (§20).
- Scope limitation carried forward unchanged from Phase 2.7 and restated here for clarity: pattern-based redaction covers the four listed categories only; free-text names, phone numbers, emails, and case numbers remain outside scope and are not claimed to be caught.

---

## 14. Logging & Observability

- **Never log raw conversation content by default** — log lines from `PersistentSessionStore` and `ExpirationSweeper` include `session_id`, `turn_index`, operation type (`create`/`save_turn`/`expire`/`delete`), row counts, and latency — never `user_query`, `rewritten_query`, or `grounded_answer_json` contents.
- A config flag (`log_full_turn_content: bool`, default `false`) mirrors Phase 2.6's existing `log_full_context` pattern for consistency, gated behind explicit opt-in for local debugging only, never enabled by default.
- Database-level logs (connection errors, pool exhaustion, transaction failures) are logged with query *shape* (which operation, which table) but never bound parameter values that could contain user text.
- Metrics emitted (not full logs): session create rate, average turns per session, expiration-sweep counts, deletion counts, query latency per operation type — all counts/timings, no content.

---

## 15. Migration Strategy

- **No live data migration is required or performed** — Phase 2.7's `InMemorySessionStore` holds no durable state (it is explicitly ephemeral, cleared on process restart), so there is nothing to migrate *from*; this phase is a backend addition, not a data transformation.
- **Compatibility guarantee:** `PersistentSessionStore` must pass the exact same interface-level test suite already exercised against `InMemorySessionStore` in Phase 2.7 (reused, not rewritten), proving behavioral equivalence at the `SessionStore` contract level (§20's migration-compatibility test).
- **Cutover:** switching `session_store.backend` from `in_memory` to `postgres` in config is the entire migration step for a fresh deployment — no code change in the orchestrator or any Phase 2.7 module is required.
- **Backward compatibility with Phase 2.7:** any existing caller code written against the `SessionStore` interface continues to work unmodified against `PersistentSessionStore`, verified by running Phase 2.7's own orchestrator test suite unchanged against the new backend.

---

## 16. Failure Handling

| Failure | Behavior |
|---|---|
| Database unavailable at session creation | Fail the request cleanly with a clear "session store unavailable" error — do not silently fall back to in-memory (which would create a data-durability illusion); fallback-to-memory is an explicit config choice for dev only, never automatic in a configured-for-postgres deployment. |
| Database unavailable mid-conversation (existing session) | Same — surfaced as a clear error to the orchestrator's caller; the in-flight turn's Phase 2.5/2.6 work (retrieval + generation) is not repeated or wasted silently — the orchestrator's existing error-handling for downstream failures (Phase 2.7 §15/§16 precedent) is followed: prefer a clear failure/insufficiency-style response over inventing state. |
| Malformed/corrupt row (e.g., invalid `grounded_answer_json`) | Treated as session-not-found for read purposes (matching Phase 2.7's malformed-state handling) — never partially deserialized and trusted; corrupt rows are flagged (logged with `session_id` and error type, no content) for manual cleanup. |
| Concurrent write conflict (two turns racing on the same session) | Prevented structurally via the transaction boundary in §8 (turn_index uniqueness constraint) — a losing concurrent writer gets a clean constraint-violation error, retried once by the caller with a recomputed `turn_index`, never silently overwritten. |
| Expiration sweep failure | Logged and retried on next scheduled run; a single failed sweep does not block on-access lazy expiration, which remains the authoritative enforcement path. |
| Deletion failure (partial cascade) | Not possible under a single transactional `DELETE ... CASCADE` statement; if the transaction fails, nothing is deleted (atomic all-or-nothing), and the caller is informed the deletion did not complete. |

---

## 17. Concurrency Considerations

- Connection pooling (size configurable, `configs/p28_persistence.yaml: session_store.pool_size`) bounds concurrent database connections; pool exhaustion surfaces as the "database unavailable" failure path (§16), not a silent queue-forever hang.
- Per-session writes are serialized at the database level via the `turn_index` uniqueness constraint (§8/§16) — two concurrent requests for the same `session_id` cannot both succeed in writing the same `turn_index`; this is the primary concurrency guarantee this phase provides (session-level, not sub-turn granularity).
- Cross-session concurrency is unconstrained and expected — different `session_id`s never contend with each other beyond ordinary connection-pool/database load, satisfying the isolation requirement under concurrent multi-session traffic.
- The expiration sweep's `UPDATE ... WHERE expires_at_utc < now() AND status = 'active'` is naturally idempotent and safe to run concurrently with itself or with on-access lazy checks (both converge on the same `expired` state; a race just means one of two equivalent updates wins).

---

## 18. Evaluation Methodology

- Reuse Phase 2.7's orchestrator-level test suite unchanged, run twice: once against `InMemorySessionStore` (regression check — must still pass, proving no behavior change), once against `PersistentSessionStore` (proving interface-level equivalence).
- Add a new persistence-specific test suite (§20) exercising restart recovery, isolation, deletion, expiration, concurrency, and failure paths that only exist once a real database is involved.
- No new conversational-quality metrics are introduced — Phase 2.7's follow-up/rewrite/grounding metrics are not re-measured here, since this phase does not touch that logic; only storage-correctness and latency-overhead are new measurement surfaces.

---

## 19. Metrics

| Metric | Definition |
|---|---|
| **Persistence correctness** | % of automated persistence test cases passing (target: 100%, since these are correctness tests, not quality benchmarks). |
| **Restart recovery correctness** | A session created, added to, then the process restarted (simulated by tearing down and reconstructing the `PersistentSessionStore` against the same DB) must return identical `ConversationSession` content — measured as exact-match pass/fail per test session. |
| **Session isolation violation rate** | Must be exactly 0 across all concurrent/isolation tests — same zero-tolerance standard as Phase 2.7. |
| **Deletion correctness** | A deleted session and all its turns are unreadable via any `SessionStore` method afterward, and confirmed absent from the underlying tables directly (not just via the interface) — pass/fail. |
| **TTL enforcement accuracy** | Sessions past `expires_at_utc` are correctly marked `expired` (both via lazy check and periodic sweep), measured against a set of sessions seeded with controlled `last_active_utc` values. |
| **PII-redaction-before-write verification** | 100% of seeded PII-pattern test inputs are absent from the raw stored row (§13) — pass/fail, zero tolerance. |
| **Logging privacy compliance** | Automated scan of emitted log lines during a test run asserting no raw query/answer content appears (§14) — pass/fail. |
| **Concurrent session safety** | No cross-contamination or lost writes across N simulated concurrent sessions (config N, e.g. 20) each with M turns (e.g. 5) — pass/fail plus measured throughput. |
| **Failure recovery** | Each §16 failure scenario produces the specified clean-failure behavior, not a crash or silent data loss — pass/fail per scenario. |
| **Backward compatibility with Phase 2.7** | Phase 2.7's existing orchestrator test suite passes unmodified against both backends — pass/fail. |
| **Storage/query latency overhead** | Mean/P50/P95 latency added by `save_turn`/`get_session` calls against `PersistentSessionStore`, measured locally against a local/dev PostgreSQL instance — reported as an observed baseline, not compared against an invented target (no arbitrary "<Xms" threshold is set in advance; the number is recorded for future capacity planning). |

---

## 20. Test Plan

`tests/conversation/test_persistent_session_store.py` (plus reused Phase 2.7 suites run against the new backend) covering:

- **Persistence/restart recovery** — create/populate a session, tear down and reconnect the store object against the same DB, confirm identical state.
- **Session isolation** — concurrent sessions, assert zero cross-read/cross-write; explicit attempt to read session B's data using session A's id fails cleanly (no ambient "list all" path exists, per §5's interface design).
- **Deletion** — explicit `delete_session`, confirm cascading removal at both the interface and raw-table level.
- **Expiration** — seeded `last_active_utc` in the past, confirm both lazy and swept expiration transitions.
- **Concurrent access** — N simulated concurrent sessions with M turns each, confirm correct `turn_index` sequencing per session and no cross-session interference.
- **PII redaction before persistence** — seeded PII-pattern inputs, confirm absence in the raw stored row.
- **Malformed/corrupt state** — manually corrupt a row's `grounded_answer_json`, confirm safe "not found"-style handling, not a crash.
- **Database failure** — simulate connection failure/pool exhaustion, confirm the clean-failure behavior of §16, not a hang or silent fallback.
- **Migration compatibility** — Phase 2.7's orchestrator test suite run unmodified against `PersistentSessionStore`, confirming pass.
- **Privacy/logging behavior** — automated log-content scan per §19.

---

## 21. Acceptance Criteria

1. All §20 test cases pass against a local PostgreSQL instance.
2. Phase 2.7's existing orchestrator test suite passes unmodified against both `InMemorySessionStore` and `PersistentSessionStore` (§15's compatibility guarantee).
3. Zero session-isolation violations across all isolation and concurrency tests.
4. PII-redaction-before-write and logging-privacy checks pass at 100%, zero tolerance (§19).
5. `src/retrieval/`, Phase 2.5 behavior, `src/generation/`, and Phase 2.6 logic are unmodified (verified by diff/hash, per existing project discipline).
6. Phase 2.7 conversational logic (`FollowUpClassifier`, `ContextSelector`, `QueryRewriter`) is unmodified except for additive `SessionStore` interface methods, if any were strictly necessary (documented explicitly if so).
7. Storage/query latency overhead is measured and reported as a baseline (§19) — no invented pass/fail threshold.
8. The corpus database (`chunks`/`embeddings`) is untouched by any operation in this phase, verified by confirming no query in the persistence layer references those tables.
9. Authentication/authorization boundary (§11) is documented, not implemented — confirmed by inspection that no login/credential code exists in this phase's deliverables.

---

## 22. Rollback / Isolation Requirements

- Rollback is a one-line config change: `session_store.backend: postgres → in_memory`. No code path depends on persistent storage existing; the orchestrator and all Phase 2.7 logic function identically against either backend.
- The session database is a separate schema/database from the corpus (§5); dropping or resetting it during development/testing carries zero risk to corpus data, and vice versa — this separation is itself a rollback/blast-radius safeguard, not just an architectural preference.
- No migration is destructive (§15 — there is no data to lose in a rollback, since `InMemorySessionStore` was always ephemeral).
- Reverting this phase entirely (removing `PersistentSessionStore`) requires no changes to Phase 2.5, 2.6, or 2.7 code, since all of it was written against the unchanged `SessionStore` interface.

---

## 23. Relationship to Future Frontend and Agentic Layers

- **Future authentication/frontend layer:** would sit in front of `ConversationalOrchestrator.handle_turn()`, attaching a verified identity and authorizing `session_id` access before invocation (§11). Nothing in this phase needs to change to support that — the orchestrator and `SessionStore` remain identity-agnostic.
- **Future frontend/API layer:** would call the same `handle_turn()` entry point Phase 2.7 already defines; persistent storage means a frontend can now reasonably offer "resume a previous conversation" functionality, since session state survives restarts — but building that UI/API surface is explicitly not part of this phase.
- **Future LangGraph/agentic orchestration:** as established in Phase 2.7 (§20 of that spec), a future agent layer would replace `ConversationalOrchestrator` while reusing the same `SessionStore` interface and data model — this phase strengthens that plan by making session state durable, which an agentic layer would need anyway for any non-trivial multi-step or long-running interaction, without requiring any schema change when that layer arrives.

---

## 24. Expected Files / Artifacts

```
src/conversation/
  persistent_session_store.py   # PersistentSessionStore implementing SessionStore
  session_store_factory.py       # config-driven backend selection
  expiration_sweeper.py
db/
  session_db/
    schema.sql                    # sessions, conversation_turns DDL (§8)
    migrations/                    # forward-only migration scripts if schema evolves later
configs/
  p28_persistence.yaml             # backend selection, pool size, TTL, expired_retention_days, log_full_turn_content
tests/conversation/
  test_persistent_session_store.py   # covering §20
  test_session_store_compat.py        # Phase 2.7 suite re-run against both backends
```

Implementation order: `db/session_db/schema.sql` → `persistent_session_store.py` (core CRUD) → `session_store_factory.py` → `expiration_sweeper.py` → `test_persistent_session_store.py` → `test_session_store_compat.py` (Phase 2.7 regression) → `configs/p28_persistence.yaml` finalized with defaults matched to test results.

---

## 25. STOP Condition and Sign-Off Requirements

**STOP** after all §20 tests pass, Phase 2.7's orchestrator suite passes unmodified against both backends, and the §19 latency-overhead baseline is measured and reported.

Do not implement authentication, a frontend/API layer, or LangGraph/agentic orchestration. Do not modify `src/retrieval/`, `src/generation/`, or Phase 2.6/2.7 logic beyond the strictly-necessary additive interface methods documented under Acceptance Criterion 6. Await Abishek's review and explicit sign-off before scoping the next phase.