# Phase 2.7: Conversational Context & Session Memory — Implementation Specification

**Depends on:** Phase 2.5 (frozen retriever adapter), Phase 2.6 (frozen grounded-generation pipeline, signed off)
**Executing agent:** Antigravity
**Status:** SPECIFICATION ONLY — implementation not yet authorized

---

## 1. Phase Objective

Extend BetterCallSaul from single-turn grounded RAG into a multi-turn conversational legal-awareness system, by adding a session/context layer that sits **in front of** the existing Phase 2.5 retriever and Phase 2.6 generation pipeline, resolving and rewriting follow-up queries into standalone retrieval queries while leaving retrieval and grounding untouched as the sole source of legal truth.

---

## 2. Why Phase 2.7 Comes After 2.6

Phase 2.6 already produces a fully grounded, cited, safety-checked answer for one isolated query — that correctness guarantee must not be diluted by conversation history. Phase 2.7 only decides *what standalone query to ask* and *how much prior context is relevant*; it never adds a second path to legal claims. Building this after 2.6 (rather than folding conversation handling into generation) keeps the grounding guarantees from Phase 2.6 fully intact and testable in isolation, and keeps this phase reversible without touching frozen code.

---

## 3. Scope

- Session/conversation state model and storage (§7).
- Context-aware follow-up detection and resolution (§9).
- Query rewriting: context-dependent question → standalone retrieval query (§10).
- Bounded, relevance-based context selection for both the rewriter and (indirectly) the generation step.
- A conversational orchestration layer that calls the existing frozen Phase 2.5 retriever adapter and Phase 2.6 `generate_answer` pipeline unchanged, then records the turn into session state.
- Session isolation, expiration, and minimal-retention privacy behavior.
- Conversation-aware evaluation harness and metrics, built on Phase 2.4/2.6 principles.

---

## 4. Non-Scope

- No modification to `src/retrieval/retriever.py`, any Phase 2.3/2.4/2.5 module, or the Phase 2.6 generation/citation/grounding modules — all are called as-is, via their existing interfaces.
- No LangGraph, autonomous agents, or tool-selection logic.
- No long-term user profiling, personalization, or cross-session preference learning.
- No frontend/UI.
- No authentication system — session isolation is achieved via opaque, server-generated `session_id` tokens; a real auth layer is deferred unless a concrete leakage risk requires it (see §11).
- No autonomous resolution of genuinely ambiguous legal questions — ambiguity is surfaced via clarifying questions or `insufficient`/`unclear` states, never guessed.
- No treatment of prior `GroundedAnswer` text as evidence — it is conversational context only, never passed to the citation/grounding layer as a source.

---

## 5. Architecture / Data Flow

```
User query + session_id (optional; absent = new session)
      │
      ▼
┌────────────────────────────┐
│ Conversational Orchestrator  │  (src/conversation/orchestrator.py)
│                               │
│  1. Session Loader/Creator      │
│  2. Follow-up Classifier         │
│  3. Context Selector             │
│  4. Query Rewriter/Resolver       │
│  5. [standalone query] ──────────┼──► Phase 2.5 retriever (frozen, unchanged)
│                               │            │
│                               │◄───────────┘  ScoredChunk list
│  6. [query + evidence] ──────────┼──► Phase 2.6 generate_answer (frozen, unchanged)
│                               │            │
│                               │◄───────────┘  GroundedAnswer
│  7. Session Writer                │
└────────────────────────────┘
      │
      ▼
ConversationTurnResult (GroundedAnswer + turn metadata + session_id)
```

Steps 5 and 6 are pass-through calls to existing frozen interfaces — the orchestrator constructs their inputs and passes their outputs on unchanged; it does not re-implement or wrap their internal logic.

---

## 6. Components and Responsibilities

| Component | File | Responsibility |
|---|---|---|
| `SessionStore` | `src/conversation/session_store.py` | CRUD for `ConversationSession`, expiration, isolation guarantees. Pluggable backend (in-memory dict for dev/tests; Redis or a dedicated Postgres table — **not** the corpus tables — for production; interface-first, backend swappable). |
| `FollowUpClassifier` | `src/conversation/followup_classifier.py` | Determines whether the incoming query is standalone or context-dependent, and produces a coarse classification (`standalone`, `simple_followup`, `topic_change`, `ambiguous_followup`, `contradictory_followup`) used to drive §9/§10 behavior. |
| `ContextSelector` | `src/conversation/context_selector.py` | Selects a bounded, relevant subset of prior turns (§9) to feed the classifier/rewriter — never the full history. |
| `QueryRewriter` | `src/conversation/query_rewriter.py` | Produces a standalone retrieval query from the current query + selected context (§10), using an LLM call via the same `LLMClient` abstraction from Phase 2.6 (no new LLM integration layer). |
| `ConversationalOrchestrator` | `src/conversation/orchestrator.py` | Wires the above together and calls the frozen Phase 2.5/2.6 entry points; single external entry point `handle_turn(session_id | None, user_query) -> ConversationTurnResult`. |
| `SessionPrivacyGuard` | `src/conversation/privacy_guard.py` | Enforces minimal retention and redaction rules before a turn is written to the session store (§11). |

---

## 7. Data Models

```
ConversationTurn
  turn_id: str
  turn_index: int                     # ordinal within session
  user_query: str                     # as typed by user
  rewritten_query: str | None         # standalone query actually sent to retrieval, if rewritten
  followup_classification: str
  grounded_answer: GroundedAnswer      # unchanged Phase 2.6 object, embedded as-is
  jurisdiction_carried_forward: str | None
  domain_carried_forward: str | None
  timestamp_utc: str

ConversationSession
  session_id: str                     # opaque, server-generated (e.g. UUID4)
  created_at_utc: str
  last_active_utc: str
  expires_at_utc: str
  turns: list[ConversationTurn]        # ordered
  turn_count: int
  status: Literal["active", "expired", "closed"]

ConversationTurnResult                 # orchestrator's return type
  session_id: str
  turn: ConversationTurn
  context_selector_debug: ContextSelectionTrace   # what was selected and why, for eval/debugging
```

`ContextSelectionTrace` records which prior turn indices were selected, the selection reason (e.g. "same jurisdiction," "explicit pronoun reference," "most recent turn only"), and the estimated token cost — required for §12/§13 evaluation, not exposed to end users by default.

---

## 8. Interfaces / Data Contracts

- **Into Phase 2.5:** the orchestrator calls the existing frozen retriever adapter with a plain string query (the rewritten/standalone query) — identical contract to a Phase 2.6 single-turn call. No new parameters are added to the retriever interface.
- **Into Phase 2.6:** the orchestrator calls `generate_answer(query, scored_chunks)` exactly as Phase 2.6 defines it. The query passed is the standalone rewritten query, not the raw follow-up text, and `scored_chunks` come only from step 5 (§5) — never from prior turns.
- **Out of the orchestrator:** `ConversationTurnResult`, which embeds the untouched `GroundedAnswer` object so any caller already built against Phase 2.6's output shape keeps working — Phase 2.7 is additive, not a breaking change to the answer schema.

---

## 9. Context Selection Strategy

- **Default window:** consider at most the last `N` turns (config: `max_context_turns`, default 4) as candidates — never the full session history.
- **Relevance filtering within the window:** a turn is selected into the active context only if it plausibly relates to the current query, using cheap, explainable signals before falling back to an LLM judgment:
  1. Explicit reference cues in the current query (pronouns — "this," "that," "it"; comparative phrasing — "what about X"; elliptical questions with no independent subject — "what's the penalty?").
  2. Domain/jurisdiction continuity: prefer turns sharing the same `domain_carried_forward`/`jurisdiction_carried_forward` tags.
  3. Recency: most recent turn is always a candidate; older turns require an explicit reference cue or domain match to be included.
- **Topic-change detection:** if the `FollowUpClassifier` returns `topic_change`, the context window is cleared for that turn (treated as standalone) even if a session exists — stale context must not contaminate an unrelated new question.
- **Token budget:** the selected context is capped (config: `max_context_tokens_for_rewrite`, default small — this is a query-rewriting prompt, not the evidence-generation prompt from Phase 2.6, so its budget is independent and much smaller) — oldest/least-relevant selected turns are dropped first if over budget.
- **No blind concatenation:** the full transcript is never passed to any LLM call in this phase; only the `ContextSelector`'s bounded, filtered output is used.

---

## 10. Query Rewriting Strategy

- Applied only when `followup_classification` is `simple_followup` or (with extra caution) `ambiguous_followup`; `standalone` and `topic_change` queries bypass rewriting entirely and go to retrieval as-is.
- The rewriter is a single, versioned LLM prompt (`src/conversation/prompts.py`, `rewrite_prompt_version`) instructed to:
  1. Produce a fully standalone question that preserves the user's actual intent, substituting resolved references (e.g., "What about Karnataka?" + prior turn about Shops & Establishments Act → "Does the Shops and Establishments Act apply differently in Karnataka?").
  2. **Never invent facts** not present in the query or selected context — if a reference can't be confidently resolved from the selected context, the rewriter must return a `resolution_status: "unresolved"` signal rather than guessing (§15).
  3. Never resolve genuinely ambiguous references by picking one interpretation silently — ambiguity is passed through to the orchestrator as `resolution_status: "ambiguous"`, which triggers a clarifying-question response instead of a rewritten query.
- Output contract: `RewriteResult { rewritten_query: str | None, resolution_status: "resolved" | "unresolved" | "ambiguous", carried_jurisdiction: str | None, carried_domain: str | None }`.
- `contradictory_followup` (e.g., a fact in the new query conflicts with a fact assumed in a prior turn — "What if I already paid?" after a turn established the user hadn't) is treated as its own case: the rewriter includes the new fact plainly in the standalone query (facts stated by the user are never dropped) without asserting the prior turn was wrong; any apparent contradiction is left for the grounded-generation layer's evidence-based answer, not resolved by the rewriter.

---

## 11. Privacy / Security

- **Session isolation:** every `SessionStore` operation is keyed strictly by `session_id`; no read path exists that can return another session's turns. This is enforced at the store interface level (method signatures require `session_id`, no "list all sessions" or cross-session query capability is exposed).
- **No authentication added in this phase** — `session_id` is treated as a bearer capability (possession of the id is sufficient), which is acceptable for this phase's scope since no user accounts or persistent identity exist yet; this is explicitly flagged as a future hardening item if sessions are exposed beyond a trusted client.
- **Minimal retention:** `ConversationTurn` stores the query text, rewritten query, classification, and the `GroundedAnswer` (already minimal per Phase 2.6's own data-minimization discipline) — no additional free-text scratch/reasoning state is persisted.
- **Expiration:** sessions expire after a configurable TTL of inactivity (config: `session_ttl_minutes`, default 60); `SessionStore` must support explicit deletion (`delete_session(session_id)`) and a background/on-access expiration sweep that marks sessions `expired` and makes their turns unreadable/unrewritable.
- **Sensitive content:** the `SessionPrivacyGuard` scans outgoing turn content before storage for obvious sensitive-PII patterns (ID numbers, financial account numbers) using simple pattern rules (not an ML classifier) and redacts them before persistence — this is a best-effort guard, not a guarantee, and is documented as such.
- **No cross-session or cross-user aggregation** of any kind is performed by this phase (ties into "no long-term profiling" in §4).

---

## 12. Evaluation Methodology

Extends, rather than replaces, the Phase 2.4/2.6 evaluation principles:
- Reuses the Phase 2.6 human-grading approach (Abishek, small sample) for groundedness/relevance on conversational turns.
- Introduces a **new conversational test-case set** (§14) since Phase 2.4/2.6's query sets are single-turn by construction — this is a necessary new artifact, not a redesign of the prior sets, which remain frozen and reused for their own regression purposes.
- Every conversational evaluation run must confirm the underlying Phase 2.5/2.6 metrics (citation validity, jurisdiction correctness, insufficient-evidence honesty) are **unchanged in kind** — i.e., a multi-turn call to `generate_answer` must score identically to a single-turn call given the same rewritten query and evidence, proving the orchestrator adds no new grounding failure mode of its own.

---

## 13. Metrics

| Metric | Definition |
|---|---|
| **Follow-up classification accuracy** | % of test cases where `FollowUpClassifier` output matches the human-labeled expected class. |
| **Query rewrite correctness** | Human-graded 0–2: 0 = wrong/invented facts, 1 = partially preserves intent, 2 = fully correct standalone query. |
| **Reference resolution accuracy** | % of pronoun/elliptical test cases correctly resolved to the intended prior-turn subject. |
| **Context selection precision/recall** | Against a human-labeled "which prior turns are actually relevant" reference set — precision = selected turns that were truly relevant, recall = truly relevant turns that were selected. |
| **Groundedness preservation** | Same 0–2 scale as Phase 2.6, measured on conversational turns — must not degrade relative to Phase 2.6's single-turn baseline. |
| **Citation validity (conversational)** | Same as Phase 2.6's metric, re-measured on multi-turn output — expected ~100% by construction, since generation is unchanged. |
| **Jurisdiction preservation/consistency** | % of follow-ups where jurisdiction correctly carries forward (or correctly resets on topic change) versus a human-labeled expectation. |
| **Session isolation violation rate** | Automated test: must be exactly 0 — any leakage is a hard failure, not a graded score. |
| **Insufficient-evidence handling (conversational)** | Same honesty-rate concept as Phase 2.6, applied to follow-ups where evidence is genuinely absent. |
| **Context/token efficiency** | Mean tokens spent on context selection + rewriting per turn, and mean `max_context_turns` actually used vs. available. |
| **Latency overhead** | Added latency of classification + selection + rewriting, reported separately from the unchanged Phase 2.5/2.6 latency, plus total end-to-end. |
| **Failure/repair rate** | % of turns requiring rewrite retry, falling back to standalone treatment, or surfacing a clarifying question due to unresolved/ambiguous classification. |

---

## 14. Test Plan

**Automated test conversation set** (`eval/conversation/p27_conversations_v1.jsonl`), each a short scripted multi-turn session, covering at minimum one case per:
- Standalone questions embedded mid-session (should not be rewritten).
- Simple follow-ups ("What about Karnataka?", "Does this apply to tenants?", "What is the penalty?").
- Pronoun/reference resolution ("What if I already paid?" referring to a prior turn's subject).
- Jurisdiction changes across turns (central → state, state A → state B).
- Topic changes (should reset context, not be treated as a follow-up).
- Ambiguous follow-ups (reference could plausibly point to more than one prior turn/subject — expected behavior: clarifying question, not a guess).
- Contradictory follow-ups (new fact conflicts with an assumption from a prior turn).
- Insufficient-evidence follow-ups (the rewritten query still has no adequate corpus support).
- Long conversations (≥ `max_context_turns` + 3, to verify windowing/truncation behavior, not unbounded growth).
- Session isolation (two concurrent sessions interleaved; assert zero cross-contamination).
- Failure-path cases: missing/expired session id, malformed session state, forced query-rewrite failure, forced retrieval failure, forced LLM failure.

Each case specifies expected `followup_classification`, expected `resolution_status`, and (where applicable) the expected rewritten query's key preserved facts (not exact string match — graded per §13's rewrite-correctness scale).

**Human evaluation sample:** minimum 20–30 multi-turn sessions graded by Abishek for groundedness and rewrite correctness, drawn to cover every category above at least once.

---

## 15. Failure Handling

| Failure | Behavior |
|---|---|
| Empty/new session (no `session_id` provided) | Create a new session; treat query as standalone. |
| Missing/expired session id | Return a clear "session not found/expired" state; start a fresh session rather than erroring the whole request — do not silently attach the turn to an unrelated session. |
| Ambiguous follow-up | Return a clarifying-question response (no retrieval/generation call made) rather than guessing a resolution. |
| Failed query rewrite (LLM error, repeated `unresolved`) | Fall back to treating the raw user query as standalone (with a `safety_flags`-style note in `ContextSelectionTrace`) rather than blocking the turn entirely — evidence-grounding still applies normally to whatever query is actually sent. |
| Context overflow | Truncate per §9's token budget (oldest/least-relevant first); never silently include unbounded history. |
| Conflicting previous turns | Not resolved by the orchestrator; passed through as a contradictory_followup case per §10 — grounding layer answers from current evidence, prior claim is not treated as fact. |
| Topic switch | Context cleared for that turn; treated as standalone. |
| Retrieval failure (Phase 2.5 call errors) | Propagate the same failure behavior Phase 2.6 already defines for empty/failed retrieval — no new failure mode invented at this layer. |
| LLM failure (rewrite or generation) | Rewrite-LLM failure → fallback above; generation-LLM failure → Phase 2.6's existing `llm_call_failed` handling, unchanged. |
| Malformed session state | Treated as session-not-found; new session created; corrupt record flagged for cleanup, never trusted or partially used. |
| Session isolation violation (should never occur) | Treated as a critical bug — any detection in testing is a release blocker, not a gracefully-handled runtime case. |

General principle: prefer a clarifying question or an explicit insufficiency/standalone fallback over inventing resolved context.

---

## 16. Performance / Scalability Considerations

- Session store must support concurrent sessions without lock contention on unrelated sessions — per-session-keyed access only (§11).
- Context selection and query rewriting add at most one extra LLM call per conversational turn (the rewrite call); this is the primary added latency cost and is measured explicitly (§13) so it can be weighed against value.
- `max_context_turns` and token budgets are configurable specifically so they can be tuned for latency/cost without code changes as usage scales.
- Session storage backend is specified as an interface (§6) precisely so an in-memory dev backend can be swapped for Redis/Postgres-table storage under real concurrent load without touching orchestration logic.
- No change to Phase 2.5/2.6 latency characteristics is expected or permitted; any regression detected in evaluation (§12) is a defect in this phase, not an accepted cost of it.

---

## 17. Artifacts / Files to Implement

```
src/conversation/
  schemas.py             # ConversationTurn, ConversationSession, ConversationTurnResult, RewriteResult, ContextSelectionTrace
  session_store.py         # SessionStore interface + in-memory + (config-selectable) persistent backend
  followup_classifier.py
  context_selector.py
  query_rewriter.py
  prompts.py               # versioned rewrite prompt template(s)
  privacy_guard.py
  orchestrator.py           # handle_turn() entry point
configs/
  p27_conversation.yaml     # max_context_turns, token budgets, session_ttl_minutes, rewrite LLM config
eval/conversation/
  p27_conversations_v1.jsonl
  conversation_eval_harness.py   # implements §12/§13 metrics
tests/conversation/
  test_orchestrator.py, test_followup_classifier.py, test_context_selector.py,
  test_query_rewriter.py, test_session_store.py, test_privacy_guard.py   # covering §14 and §15
```

Implementation order: `schemas.py` → `session_store.py` (in-memory first) → `followup_classifier.py` → `context_selector.py` → `prompts.py` + `query_rewriter.py` → `privacy_guard.py` → `orchestrator.py` (wiring to frozen Phase 2.5/2.6 entry points) → test suite → `conversation_eval_harness.py`.

---

## 18. Acceptance Criteria

1. All §14 automated test cases pass, including the zero-tolerance session-isolation tests.
2. Phase 2.5 retriever and Phase 2.6 generation modules are unmodified (verified by diff/hash, per existing project discipline).
3. Conversational-mode citation validity and groundedness scores match Phase 2.6's single-turn baseline within noise (§12) — no new grounding failure mode introduced.
4. Follow-up classification accuracy, rewrite correctness, and context selection precision/recall are measured and reported — no numeric target fixed in advance; first results become the documented baseline, consistent with the project's process-over-threshold acceptance philosophy.
5. Session expiration and deletion behave as specified (§11), verified by automated test.
6. Latency overhead of the conversational layer is measured and reported separately from unchanged retrieval/generation latency.
7. Human evaluation sample (§14) completed and reviewed by Abishek.

---

## 19. Rollback / Isolation Requirements

- The entire Phase 2.7 layer is additive: it lives in a new `src/conversation/` package and a new orchestrator entry point. Any existing single-turn caller of Phase 2.6's `generate_answer` continues to work unchanged — Phase 2.7 does not require the single-turn path to be removed or rerouted.
- Because Phase 2.5/2.6 are called via their existing frozen interfaces only, disabling or removing the Phase 2.7 layer (e.g., reverting to direct single-turn calls) requires no changes to retrieval or generation code — rollback is a matter of routing callers back to the Phase 2.6 entry point directly.
- No schema or data migration is performed against the corpus database; session state lives in its own store, independent of `chunks`/`embeddings`, so rollback carries no corpus-data risk.

---

## 20. Relationship to Future Agentic Layer

Phase 2.7's `ConversationalOrchestrator` is deliberately a thin, linear coordinator — not a planner — so that a future LangGraph/agentic layer can be introduced as a **replacement for the orchestrator only**, without touching:
- The `SessionStore`/`ConversationSession` data model (an agent framework would consume/produce the same session state).
- The `FollowUpClassifier`/`ContextSelector`/`QueryRewriter` components, which can be reused as tools/nodes inside a future agent graph rather than rebuilt.
- The frozen Phase 2.5 retriever and Phase 2.6 generation interfaces, which any future agent would still call through the same contracts (§8).

In short: Phase 2.7 proves out and hardens the conversational primitives (session state, reference resolution, bounded context, query rewriting) as standalone, independently testable components with clean interfaces, so a later agentic phase is an orchestration swap, not a ground-up rebuild.

---

## 21. STOP Condition and Sign-off Requirements

**STOP** after the §17 implementation order completes, all §14 test cases pass (with zero session-isolation violations), and a first `conversation_eval_harness.py` run against `p27_conversations_v1.jsonl` produces a reviewable evaluation report following the §12/§13 methodology.

Do not begin LangGraph/agentic orchestration, personalization/profiling, authentication, or frontend work. Do not modify any Phase 2.3–2.6 file at any point in this phase. Await Abishek's review and explicit sign-off before scoping the next phase.