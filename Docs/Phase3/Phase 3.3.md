# Phase 3.3 — Intent-Aware Retrieval Planning Layer: Implementation Specification

**Project:** BetterCallSaul
**Phase:** 3.3
**Type:** Implementation specification (Antigravity executes; Abishek signs off)
**Baseline:** Phase 2.5 retrieval (`JurisdictionBoostedAdapter`, frozen), Phase 2.6 grounded generation (frozen), Phase 2.7 conversational context (frozen)

---

## 1. Problem Statement

Phase 2.4/2.5 evaluated and optimized **retrieval quality given a query**, using a fixed strategy: embed → dense + BM25 fusion (RRF) → cross-encoder rerank → confidence calibration → jurisdiction soft-boost. This strategy is applied identically regardless of what kind of legal question is being asked.

Live testing surfaced a failure class the 160-query Phase 2.4/2.5 evaluation set did not exercise: a layman query that names a specific statutory provision colloquially (e.g. *"What is the penalty for murder under BNS Section 103?"*) can retrieve semantically-similar but topically-wrong material (unrelated High Court/company-law chunks), because dense+lexical fusion alone does not first establish **what kind of answer the question calls for** (a statute's penalty clause vs. case law vs. procedure). The Phase 2.6 generator behaved correctly (declined to fabricate), but the retrieval layer did not give it the right evidence to work with.

The root cause is not a fusion or reranking defect — Phase 2.4/2.5 audits already ruled out several such artifacts (data leakage, metric bugs, pooling circularity). It is an **absence of any query-understanding step before retrieval**: the system does not distinguish "what does the law say" from "what did a court decide" from "what do I do" before choosing evidence.

## 2. Objective

Add an **intent-aware retrieval planning layer** above the frozen Phase 2.5 retriever that:
- Classifies each incoming (already-rewritten, per Phase 2.7) query by legal question type and, where possible, legal domain.
- Produces a **retrieval plan** describing which existing Phase 2.5 source types and weighting to invoke.
- Routes the query through existing Phase 2.5 adapters/components according to that plan, without modifying them.
- Preserves all Phase 2.5 mechanics (dense, lexical FTS, RRF fusion, cross-encoder rerank, confidence calibration, jurisdiction boosting) and all Phase 2.6 grounding/safety behavior.
- Requires no Act names, section numbers, or legal terminology from the user.

This is a **planning/routing layer**, not a new retriever and not an agent. It sits between Phase 2.7's query rewriting and Phase 2.5's retrieval call.

## 3. Review of Existing System (informing this design)

- **Phase 2.4** established the open-world evaluation harness, the 160-query `p24_queries_v1.jsonl` set with a `query_type` field (`easy`, `legislation_focused`, `judgment_focused`, `mixed_legislation_judgment`, `jurisdiction_sensitive`, `moderately_ambiguous`, `multi_concept`, `clarification_required`, `no_evidence_expected`) and a `jurisdiction_expectation` field (`central_only`, `state_specific`, `jurisdiction_ambiguous`) — **an existing query taxonomy already exists and must be reused/extended, not replaced**.
- **Phase 2.5** (`JurisdictionBoostedAdapter`) already performs: dense vector search, PostgreSQL BM25 FTS (`src/retrieval/lexical.py`), RRF fusion (k=60), `bge-reranker-base` cross-encoder reranking, `ConfidenceCalibrator` (`src/retrieval/confidence.py`, threshold 0.40), and soft jurisdiction boosting (1.15×). These are frozen interfaces this phase must call, not reimplement.
- **Phase 2.6** already has an `insufficient_evidence` / confidence-tier path and a `GroundedAnswer` schema with `applicable_jurisdiction`. This phase must produce inputs the generator already knows how to consume — no schema changes to `GroundedAnswer`.
- **Phase 2.7** already classifies conversational turn type (`FollowUpClassifier`) and rewrites queries with resolved references (`QueryRewriter`, `p27_v1`). This phase's intent classification is a **separate, complementary** classification (legal question type, not conversational turn type) and must run on the Phase 2.7-rewritten query, not duplicate follow-up detection.
- No existing component currently determines statute-vs-precedent-vs-procedure retrieval emphasis. This is the actual gap this phase fills.

## 4. Intent Taxonomy

New enum, `LegalQuestionIntent`, orthogonal to Phase 2.4's `query_type` and Phase 2.7's follow-up classes:

| Intent | Meaning | Example |
|---|---|---|
| `statutory_information` | Asks what the law/rule/penalty is | "What is the punishment for murder?" |
| `case_law` | Asks what courts have decided/interpreted | "What has the Supreme Court said about the death penalty?" |
| `legal_interpretation` | Asks how a provision applies to a described situation | "Does this count as theft if I didn't take money?" |
| `procedure` | Asks how to do something (file, apply, respond) | "How do I file a consumer complaint?" |
| `mixed` | Genuinely needs statute + precedent + procedure together | "My landlord won't return my deposit. What can I do?" |
| `clarification_required` | Too underspecified to plan retrieval meaningfully | "Which law applies to me?" |

Each classification also carries (best-effort, all optional/nullable):
- `domain_hint`: one of the existing 15–16 domain labels already used across Phase 1C/2.1/2.4 (Consumer Protection, Employment & Labour, etc.), or `null`.
- `jurisdiction_hint`: reuses Phase 2.4's `central_only | state_specific | jurisdiction_ambiguous` vocabulary, or `null`.
- `confidence`: classifier's own confidence in the intent label, used only for `clarification_required` triggering (§7), not for retrieval confidence (Phase 2.5's calibrator remains the authority on evidence confidence).

## 5. Architecture

```
Phase 2.7 output (rewritten query, resolved jurisdiction/context)
      │
      ▼
IntentClassifier (new)
      │  → LegalQuestionIntent + domain_hint + jurisdiction_hint + confidence
      ▼
RetrievalPlanner (new)
      │  → RetrievalPlan { source_mix, query_variants, top_k_hints, domain/jurisdiction filters }
      ▼
RetrievalPlanExecutor (new, thin) ── calls existing, unmodified ──▶ JurisdictionBoostedAdapter (Phase 2.5)
      │                                                              (dense + FTS + RRF + rerank + calibration + jurisdiction boost)
      ▼
Evidence (existing schema, unchanged) + PlanTrace (new, for logging/eval only)
      │
      ▼
Frozen Phase 2.6 Grounded Generation (unchanged)
```

- `IntentClassifier`: a lightweight classifier — a small LLM call (reusing the existing `GeminiClient`/`MockLLMClient` provider abstraction from Phase 2.6, new prompt `p33_intent_v1`) or a rules+embedding hybrid; either is acceptable provided it is swappable behind a protocol (`IntentClassifierProtocol`) and does not call any Phase 2.5 retrieval component to make its decision (no retrieve-then-classify circularity).
- `RetrievalPlanner`: pure function mapping `(intent, domain_hint, jurisdiction_hint)` → `RetrievalPlan`. No LLM call here; deterministic, unit-testable, configurable via YAML (§6).
- `RetrievalPlanExecutor`: translates a `RetrievalPlan` into one or more calls to the **existing, unmodified** Phase 2.5 adapter interface (e.g. document-type filter parameters, query variant strings, top-k values already supported by the adapter's existing signature). If the plan calls for evidence the current adapter signature cannot express (e.g. a filter parameter that doesn't exist), the executor must degrade to the adapter's default behavior and log the gap — **it must not reach into or modify Phase 2.5 internals** to force it.
- `PlanTrace`: a small structured record (intent, domain/jurisdiction hints, chosen source mix, whether degraded) attached to the request context for logging and evaluation — not shown to the end user beyond the high-level "Understanding → Searching" stage labels already scoped for the Phase 3.2 UI.

## 6. Retrieval-Planning Strategy

Config-driven mapping (`configs/p33_retrieval_planning.yaml`), not hardcoded:

| Intent | Source mix guidance | Notes |
|---|---|---|
| `statutory_information` | Legislation-weighted; judgments included only if they clear the existing confidence threshold | Not "top-2 legislation hardcoded" — weighting, not a fixed count |
| `case_law` | Judgment-weighted | Legislation still eligible as supporting context |
| `legal_interpretation` | Balanced legislation + judgment | Relies on Phase 2.5's existing fusion/rerank to sort within the mix |
| `procedure` | Procedural/administrative sources + supporting legislation where the corpus has them; falls back to legislation-only if no procedural document type exists in the corpus | Must not fabricate a procedure source type Phase 1C didn't ingest |
| `mixed` | No source-type restriction; run the full existing hybrid pipeline and let calibration/reranking decide | This is effectively "current Phase 2.5 behavior," explicitly preserved as a fallback |
| `clarification_required` | No retrieval call executed | See §7 |

"Weighting, not a fixed count" means: the planner may pass **query-variant phrasing or soft ranking hints** into the existing adapter call (e.g. issuing the retrieval call once with the existing document-type signals the adapter already accepts), but it must not post-filter results into a rigid "N legislation + N judgment" template — Phase 2.5's own fusion/rerank/calibration remains the final arbiter of what's returned, per the explicit constraint in the request.

## 7. Handling Ambiguous / Underspecified Queries

- If `IntentClassifier` returns `clarification_required` (or confidence below a configurable threshold with no safe default intent), the layer **does not call Phase 2.5 retrieval**. It returns a structured "needs clarification" result with 1–2 targeted follow-up question suggestions (domain-agnostic, e.g. "Are you asking about the law itself, a court's decision, or what steps to take?").
- This result is passed to Phase 2.6 generation using its **existing** `insufficient_evidence`/low-confidence response path — no new generation schema. Phase 2.6 is not modified; it already supports declining to answer without fabrication.
- This must not be conflated with Phase 2.7's follow-up/reference resolution — clarification here is about legal-question ambiguity, not conversational reference ambiguity, and only runs after Phase 2.7 has already resolved references.

## 8. Failure / Low-Confidence Behavior

- If the `IntentClassifier` call fails (timeout, provider error), the layer falls back to the `mixed` plan (full existing Phase 2.5 hybrid behavior, no source restriction) rather than failing the request — intent classification is an optimization layer, not a hard dependency.
- If `RetrievalPlanExecutor` cannot express a plan (§5), it falls back to the adapter's default call.
- In all fallback cases, `PlanTrace` records `fallback: true` and the reason, for observability, without changing the user-facing response contract.
- Phase 2.5's existing confidence calibration remains the sole authority on `insufficient_evidence`/confidence tiering for retrieved evidence; this layer never overrides or bypasses it.

## 9. Integration Points

- Called between Phase 2.7's `QueryRewriter` output and the existing call site that invokes `JurisdictionBoostedAdapter` inside `ConversationalOrchestrator` — as a new step in that call site, not a modification to `orchestrator.py`'s existing frozen logic beyond adding the one new call. (If the orchestrator's frozen-file rule (0 lines modified) makes even this addition disallowed, implement as a wrapping decorator/new orchestrator-adjacent module instead of editing the file, and flag this choice explicitly in the report.)
- No changes to `src/retrieval/` (2.5), `src/generation/` (2.6), or Phase 2.7's `followup_classifier.py` / `context_selector.py` / `query_rewriter.py`.
- No changes to `GroundedAnswer`, `ProvenanceFields`, or any persisted schema (2.8/2.9 untouched).

## 10. Tests / Evaluation Requirements

- **New layman intent evaluation set** (`eval/queries/p33_intent_queries_v1.jsonl`), covering at minimum the five example queries in the request plus additional layman-phrased queries per intent category (no Act names/section numbers in query text, by construction — this is itself a test).
- **Intent classification accuracy**: measured against human-labeled intent for the new set (report actual measured numbers only; no invented figures).
- **Regression on Phase 2.4/2.5 harness**: run the existing 160-query `p24_queries_v1.jsonl` end-to-end through the new layer and confirm Recall/MRR/NDCG do not regress versus the frozen Phase 2.5 baseline reported in `PHASE_2_5_RETRIEVAL_QUALITY_AUDIT.md` (the `mixed`/fallback path should reduce to equivalent behavior on queries where intent doesn't change the plan).
- **Targeted case fix verification**: confirm the murder/BNS-103-style query class now retrieves on-topic legislation (measured, not assumed).
- **Ambiguous-query handling**: verify `clarification_required` queries produce the clarification path and never a fabricated/misrouted retrieval.
- **Fallback behavior**: fault-inject classifier failures and confirm the `mixed` fallback path executes and the request still completes.
- **No hardcoded template regression test**: explicit test asserting the executor does not truncate results to a fixed "N legislation + N judgment" split.
- **Frozen-layer diff check**: `git diff` against the pre-phase tag shows 0 lines changed in `src/retrieval/`, `src/generation/`, and Phase 2.7 conversation modules (aside from the single integration point noted in §9, if unavoidable).

## 11. Acceptance Criteria

1. Intent classification and retrieval planning run as a distinct, swappable layer with no modification to frozen Phase 2.5/2.6/2.7 internals (§9's caveat aside).
2. The five example queries in §1/§2 of the originating request are demonstrated to route to an appropriate plan and produce on-topic evidence.
3. No fixed "N legislation + N judgment" template exists anywhere in the executor.
4. `clarification_required` queries never trigger a Phase 2.5 retrieval call.
5. Classifier failure degrades to the existing full Phase 2.5 hybrid behavior without failing the request.
6. Phase 2.4/2.5 regression harness shows no measured degradation versus the existing frozen baseline.
7. All new config (intent taxonomy thresholds, source-mix guidance, fallback thresholds) lives in `configs/p33_retrieval_planning.yaml`, nothing hardcoded.
8. Report includes actual measured evaluation numbers only — no invented benchmark results.

## 12. Files/Modules Expected

**New:**
- `src/planning/intent_classifier.py` (+ `IntentClassifierProtocol`)
- `src/planning/retrieval_planner.py`
- `src/planning/retrieval_plan_executor.py`
- `src/planning/schemas.py` (`LegalQuestionIntent`, `RetrievalPlan`, `PlanTrace`)
- `configs/p33_intent_prompt.yaml` (prompt `p33_intent_v1`, if LLM-based classifier is chosen)
- `configs/p33_retrieval_planning.yaml`
- `eval/queries/p33_intent_queries_v1.jsonl`
- `tests/planning/` (unit + integration tests per §10)
- `PHASE_3_3_REPORT.md`

**Touched (minimal, integration point only):**
- The single call site in `ConversationalOrchestrator` (or a wrapping module, per §9's fallback option) that currently invokes Phase 2.5 retrieval directly.

**Explicitly not touched:** `src/retrieval/`, `src/generation/`, `src/conversation/followup_classifier.py`, `src/conversation/context_selector.py`, `src/conversation/query_rewriter.py`, `src/conversation/persistent_session_store.py`, `src/auth/`, `src/api/`.

## 13. Non-Goals

- No autonomous agent / LangGraph / multi-step tool-use architecture (deferred to a future agentic phase).
- No modification to Phase 2.5 retrieval algorithms, Phase 2.6 generation logic, or Phase 2.7 conversational mechanics.
- No new document ingestion, corpus changes, or new source types beyond what Phase 1C already ingested.
- No changes to persistence, auth, or API contract layers (Phases 2.8–3.1).
- No frontend changes (Phase 3.2 untouched).
- No invented/simulated benchmark numbers in the report — only measured results.

## 14. STOP Condition

**STOP** after `PHASE_3_3_REPORT.md` is produced, with the frozen-layer diff evidence and measured evaluation numbers included. Do not proceed to any agentic architecture work. Await Abishek's review and explicit sign-off before this phase is considered complete.