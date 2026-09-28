# Phase 3.4 — Hard Metadata-Aware Retrieval Constraints: Implementation Specification

**Project:** BetterCallSaul
**Phase:** 3.4
**Type:** Implementation specification (Antigravity executes; Abishek signs off)
**Baseline:** Phase 3.3 intent-aware planning; Phase 2.5 retrieval (frozen); Phase 2.6 generation (frozen)

---

## 1. Problem Statement

Phase 3.3 correctly classifies *"Supreme Court precedent on compensation for delayed possession of flat by real estate developer"* as `case_law`, but the resulting `RetrievalPlan` expresses "Supreme Court" only through query text. The plan does not pass a structured `RetrievalFilters(court=...)` constraint to the retriever, so dense retrieval returns semantically similar High Court material.

Diagnostic facts (as reported, not re-verified by this spec): the live DB holds 240 Supreme Court documents, none relevant to real-estate/flat-possession/builder-compensation. The relevant precedent is **absent from the corpus**. Two distinct problems therefore exist:

1. **Constraint loss (fixable now):** an explicit user requirement is downgraded to a soft embedding hint and silently violated.
2. **Corpus gap (out of scope):** even a correct filter will yield nothing for this query. The correct outcome is an honest "no matching evidence under the requested constraint," not a substitute.

## 2. Objective

Represent explicit user-stated metadata constraints (court, jurisdiction, source type) structurally in `RetrievalPlan`, carry them through the Phase 3.3 executor/adapter boundary into the **existing** retrieval filter interface, and enforce them during candidate retrieval. Zero results under a hard constraint produce a structured insufficiency state, never a silent fallback to other courts.

## 3. Pre-Flight Audit (mandatory, before any code)

Antigravity must first document, from the existing code, without modifying it:

1. What `RetrievalFilters` fields exist, and their exact accepted value formats (e.g., court string values, jurisdiction/state, document type).
2. Whether the Phase 2.5 adapter (`JurisdictionBoostedAdapter`) forwards filters to **every candidate leg**: dense vector search, lexical FTS, and any reranker candidate pool. A filter honored on only one leg is a defect for this phase's purposes.
3. **How the dense filter is applied.** With HNSW and `ef_search=64` over ~11.4M chunks, a filter applied *after* ANN candidate selection can return zero or few rows even when matching chunks exist (Supreme Court is ~240 documents in a very large corpus). If filtering is post-ANN, a "zero results" outcome cannot be trusted as evidence of absence.
4. The distinct stored `court` / jurisdiction / document-type values in the database (read-only query), to build the canonical alias map in §5.

**If item 2 or 3 shows the frozen retriever cannot enforce filters reliably, STOP and report** with options (e.g., a minimal, separately-signed-off change, or a read-only pre-check strategy in the executor). Do not modify `retriever.py` or work around it silently.

## 4. Architecture & Data Flow

```
Phase 2.7 rewritten query
      │
      ▼
Phase 3.3 IntentClassifier / RetrievalPlanner  (unchanged logic)
      │
      ▼
ConstraintExtractor (new, deterministic)  ── scans query for EXPLICIT court/jurisdiction/source-type mentions
      │  → ExtractedConstraints { court_set, jurisdiction, source_type, evidence_spans }
      ▼
RetrievalPlan (extended)  ── adds hard_constraints, soft_preferences
      │
      ▼
RetrievalPlanExecutor (extended)
      │  1. map hard_constraints → existing RetrievalFilters (canonical values)
      │  2. existence check (§7) if hard constraint present
      │  3. call frozen Phase 2.5 adapter with filters
      ▼
Evidence  |  ConstraintInsufficiency (structured state)
      │
      ▼
Phase 2.6 generation (existing insufficient-evidence path)
```

The extractor runs on the Phase 2.7-rewritten query. It does not call the LLM and does not depend on the intent classifier's output to *create* a hard constraint (the classifier may only *corroborate*).

## 5. Schema / Interface Changes (additive only)

- `RetrievalPlan`: add `hard_constraints: HardConstraints | None` and keep existing soft fields as `soft_preferences`. Default `None` preserves Phase 3.3 behavior exactly.
- `HardConstraints`: `court: list[CanonicalCourt] | None` (list supports multi-court), `jurisdiction: str | None`, `source_type: {legislation, judgment} | None`, plus `provenance` (the query text span that triggered each field).
- `CanonicalCourt`: values must match stored DB values exactly, resolved through a config alias map (`configs/p34_metadata_constraints.yaml`), e.g. "Supreme Court", "SC" → the stored Supreme Court value; "Kerala High Court", "High Court of Kerala" → the stored Kerala HC value. Aliases only map to values that the §3 audit confirmed exist.
- `ConstraintInsufficiency`: `{ constraint_summary, matched_candidate_count, reason }` where `reason ∈ {no_documents_match_constraint, no_relevant_candidates_under_constraint}`. It travels in `PlanTrace` and to the upper layer.
- `PlanTrace`: add `hard_constraints_applied`, `constraint_provenance`, `constraint_outcome`.
- No changes to `GroundedAnswer`, `ProvenanceFields`, `RetrievalFilters` definition, or any persisted schema.

## 6. Hard vs Soft Constraint Semantics

| Signal | Treatment |
|---|---|
| User explicitly names a court ("Supreme Court", "Kerala High Court") | **Hard** `court` filter |
| User explicitly names both ("Supreme Court and High Court cases") | **Hard**, multi-court set. Bare "High Court" with no state → hard only if the schema supports a High Court group; otherwise treat as source preference (soft) and note it in `PlanTrace` |
| User names a state jurisdiction explicitly ("under Karnataka law") | Hard `jurisdiction` only if the §3 audit shows a reliable jurisdiction field; otherwise remains Phase 2.5's existing soft boost |
| User explicitly asks for "judgments/cases" or "Act/section" | Hard `source_type` only when phrasing is unambiguous; intent `case_law` alone is **soft** weighting, not a hard filter |
| Domain inferred from topic | **Soft only** in this phase |
| Intent classifier inference without explicit text support | **Never hard** |
| No constraint stated ("Indian law on consumer complaints") | No filter |

Rules: a hard constraint requires an `evidence_span` in the query text. Weak semantic guesses never create a filter. Soft preferences continue to flow through Phase 3.3/2.5 weighting unchanged. Conflicting or unresolvable mentions (e.g., unknown court name) do not become hard filters; the plan records `constraint_unresolved` and proceeds unconstrained with a flag, so the upper layer can say the constraint could not be applied.

## 7. Zero-Result Behavior

When a hard constraint is present:

1. **Existence check (read-only, cheap):** confirm whether any chunks/documents satisfy the constraint at all. Zero → `ConstraintInsufficiency(no_documents_match_constraint)`, retrieval skipped.
2. Otherwise call the retriever with filters. If results are empty or all fall below the existing calibrator threshold → `ConstraintInsufficiency(no_relevant_candidates_under_constraint)`.
3. **Never** widen to other courts, drop the filter, or re-run unconstrained. No silent substitution.
4. The structured state is delivered to Phase 2.6 through its existing insufficient-evidence path so the answer can state that evidence under the requested constraint (e.g., Supreme Court decisions on this topic) is not available in the current corpus, without fabricating. If that path cannot carry the constraint description without a `GroundedAnswer` schema change, report it and use the smallest additive mechanism approved at sign-off.
5. The false-zero risk from §3.3 must be closed: the report states how the executor guarantees "zero" means absence, not ANN under-recall.

## 8. Failure Fallback

- Classifier/planner failure: fall back to Phase 3.3's existing `mixed` behavior. The `ConstraintExtractor` is deterministic and independent, so an **explicit** constraint still applies even when the classifier fails.
- Extractor failure: log, proceed with no hard constraints (Phase 3.3 behavior), flag in `PlanTrace`.
- Filter-mapping failure (alias not in DB): treated as unresolved constraint per §6, never guessed.

## 9. Tests

All tests run against an isolated test database or fixture set. **No writes to the production corpus.**

- Explicit Supreme Court request → `court` hard filter present; alias resolves to stored value.
- Explicit High Court request (Kerala) → correct canonical court.
- Multi-court request → multi-court set, if §3 confirms support.
- Explicit source-type request → hard `source_type`.
- No court specified → no hard filter, output identical to Phase 3.3.
- Ambiguous / unknown jurisdiction → no hard filter, `constraint_unresolved` flagged.
- Weak semantic guess (topic implies court) → no hard filter.
- **Case A (fixture with no matching Supreme Court chunks):** the flat-possession query returns `ConstraintInsufficiency`, zero High Court evidence in output.
- **Case B (fixture with matching Supreme Court chunks plus High Court distractors):** every returned chunk is Supreme Court; distractors never appear in final results.
- False-zero test: a fixture where matching chunks exist but rank outside the unfiltered top ANN candidates must still be found (or the limitation must be reported per §3).
- Classifier/planner failure with explicit court text → constraint still enforced.
- Backward compatibility: plans without `hard_constraints` produce byte-identical retriever calls to Phase 3.3.
- Phase 2.4/2.5 regression suite unchanged; report measured results only.
- Frozen-layer `git diff` check.

## 10. Acceptance Criteria

1. §3 pre-flight audit completed and documented before implementation.
2. Explicit court/source-type/jurisdiction requirements reach the retriever as structured filters, verified by call-level assertions, not just output inspection.
3. No hard filter is created without an evidence span in the query text.
4. Under a hard constraint, no out-of-constraint chunk appears in final evidence in any tested case.
5. Zero-result outcomes return `ConstraintInsufficiency`, never substituted evidence; "zero" is demonstrated reliable (no ANN false-zero) or the limitation is reported.
6. Cases A and B in §9 both pass.
7. Queries without explicit constraints behave identically to Phase 3.3.
8. Explicit constraints survive classifier failure.
9. All aliases, thresholds and mappings live in `configs/p34_metadata_constraints.yaml`.
10. 0 lines modified in frozen components; only measured numbers appear in the report.

## 11. Files

**New:** `src/planning/constraint_extractor.py`, `configs/p34_metadata_constraints.yaml`, `tests/planning/test_p34_*`, `PHASE_3_4_REPORT.md` (including the §3 audit findings).
**Modified (additive):** `src/planning/schemas.py`, `src/planning/retrieval_planner.py`, `src/planning/retrieval_plan_executor.py`.

## 12. Frozen Components

`src/retrieval/` (including `retriever.py` and the Phase 2.5 adapter), `src/generation/`, Phase 2.7 conversation modules, `src/auth/`, `src/api/`, persistence, and the corpus/DB contents.

## 13. Non-Goals

Corpus ingestion or acquiring a Supreme Court dataset; any change to dense/lexical/fusion/reranking; changing Phase 3.3 intent taxonomy; LangGraph/agents; hard-coded legislation/judgment allocations; inferring courts or domains from topic; UI changes; new benchmark claims.

## 14. STOP Condition

**STOP** after `PHASE_3_4_REPORT.md`. If the §3 audit shows the frozen retriever cannot enforce filters reliably, STOP at that point and report before implementing. Await Abishek's explicit sign-off.