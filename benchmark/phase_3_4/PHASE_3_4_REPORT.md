# PHASE 3.4 HARD METADATA-AWARE RETRIEVAL CONSTRAINTS REPORT

**Report Timestamp:** 2026-09-28 T23:59:00 ISO  
**Status:** **PHASE 3.4 IMPLEMENTATION COMPLETE & VERIFIED** (Option A Approved)  
**Baseline:** Phase 3.3 Intent-Aware Planning (`650d1f2`), Phase 2.5 Retrieval (Frozen), Phase 2.6 Generation (Frozen)

---

## 1. Executive Summary & Objective Realization

Phase 3.4 extends the Phase 3.3 Intent-Aware Retrieval Planning Layer with **Hard Metadata-Aware Retrieval Constraints**.

When a user explicitly mentions a target court (e.g., `"Supreme Court"`, `"Kerala High Court"`), source type (`"statute"`, `"judgment"`), or jurisdiction in their query, Phase 3.4 deterministically extracts and structures these requirements into `RetrievalPlan.hard_constraints`.

Under Option A (approved by sign-off):
1. **Zero High Court Substitution:** The retriever strictly enforces explicit hard constraints. High Court judgments are **never** returned as silent substitutes when Supreme Court rulings are explicitly requested.
2. **Deterministic SQL Pre-Check:** Before attempting constrained retrieval, a cheap SQL `EXISTS` query verifies whether matching documents exist in the PostgreSQL database. If 0 matching documents exist, retrieval immediately returns a structured `ConstraintInsufficiency` object with `reason="no_documents_match_constraint"`.
3. **Multi-Leg Filter Alignment:** Both dense HNSW vector search and BM25 lexical FTS search receive and enforce metadata filters. Lexical candidates can no longer bypass filters or bleed into RRF fusion.
4. **Auto-Relaxation Overridden:** `RetrievalPlanExecutor` forces `RetrievalConfig(auto_relax_filters=False)` for hard-constrained calls, preventing `LegalRetriever` from silently dropping filters.

---

## 2. Pre-Flight Audit Summary (§3)

### Critical Defects Discovered & Resolved (Option A):
1. **Lexical FTS Filter Bypassing:** Updated `LexicalSearcher.search(query, top_k, filters)` in `src/retrieval/lexical.py` to accept `filters` and apply parameterized `WHERE` clauses. Updated `HybridAdapter.retrieve()` in `src/retrieval/adapters.py` to pass `filters` to the lexical leg.
2. **Silent Filter Relaxation:** `RetrievalPlanExecutor.execute()` now forces `auto_relax_filters=False` for hard-constrained queries so filters are never dropped.
3. **Pre-Check False-Zero Protection:** SQL `EXISTS` pre-checks prevent ANN graph traversal under-recall from masking document existence.

---

## 3. Files Created & Modified

### Created Files:
* **`configs/p34_metadata_constraints.yaml`**: Canonical court alias mappings (`"Supreme Court of India"`, `"High Court of Kerala"`, `"Madras High Court"`, `"Orissa High Court"`, `"High Court of Madhya Pradesh"`, `"Patna High Court"`), source type aliases, and jurisdiction mappings.
* **`src/planning/constraint_extractor.py`**: Deterministic rule-based extractor mapping raw/rewritten query text spans to canonical `HardConstraints`. Never invents constraints without explicit text evidence.
* **`tests/planning/test_p34_metadata_constraints.py`**: Unit and integration test suite (9 test cases covering Supreme Court, High Court, legislation, unconstrained, and insufficiency paths).
* **`benchmark/phase_3_4/PHASE_3_4_REPORT.md`**: Implementation report.

### Modified Files (Additive Only):
* **`src/planning/schemas.py`**: Added `HardConstraints` and `ConstraintInsufficiency` schemas; extended `RetrievalPlan` (`hard_constraints`) and `PlanTrace` (`hard_constraints_applied`, `constraint_provenance`, `constraint_outcome`).
* **`src/planning/retrieval_planner.py`**: Integrated `ConstraintExtractor` into `RetrievalPlanner.plan()`.
* **`src/planning/retrieval_plan_executor.py`**: Integrated `_check_constraint_exists()` SQL pre-check, `RetrievalFilters` construction, `auto_relax_filters=False` enforcement, and structured `ConstraintInsufficiency` trace recording.
* **`src/retrieval/lexical.py`**: Added `filters` support to `LexicalSearcher.search()`.
* **`src/retrieval/adapters.py`**: Forwarded `filters` to `lexical_searcher.search()` in `HybridAdapter.retrieve()`.

---

## 4. Empirical Test Results & Verification

### A. Phase 3.4 Unit & Integration Test Suite (`pytest`)

```bash
venv\Scripts\pytest -o pythonpath=. tests/planning/test_p34_metadata_constraints.py
```

**Results:** `9 passed in 15.71s (100% success)`

1. `test_constraint_extractor_supreme_court` — **PASS**
2. `test_constraint_extractor_kerala_high_court` — **PASS**
3. `test_constraint_extractor_source_type_legislation` — **PASS**
4. `test_constraint_extractor_no_constraints` — **PASS**
5. `test_constraint_extractor_weak_semantic_no_hard_filter` — **PASS**
6. `test_retrieval_planner_attaches_hard_constraints` — **PASS**
7. `test_failing_query_enforces_supreme_court_without_high_court_substitutes` — **PASS**
8. `test_explicit_legislation_constraint_no_judgments` — **PASS**
9. `test_unconstrained_query_preserves_phase33_behavior` — **PASS**

---

### B. Specific Target Query Verification

**Query:** `"Supreme Court precedent on compensation for delayed possession of flat by real estate developer."`

#### Execution Trace:
* **Classified Intent:** `case_law`
* **Hard Constraints Extracted:** `{'court': ['Supreme Court of India']}`
* **Evidence Span:** `{'court': 'Supreme Court'}`
* **SQL Pre-Check Result:** 240 Supreme Court documents exist in DB; 0 SC flat possession chunks exist.
* **Returned Chunks Count:** `0` (Zero High Court substitutes returned)
* **Constraint Outcome:** `insufficiency`
* **Insufficiency Reason:** `no_relevant_candidates_under_constraint`

**Verification Status:** **SUCCESS.** High Court writ petitions are strictly prohibited from appearing as substitutes when Supreme Court rulings are requested.

---

### C. Phase 3.3 Regression Suite Verification (`eval_p33_intent.py`)

**Results:** `20 / 20 passed (100.00% Intent Classification Accuracy)`  
**Clarification Path:** 100% preserved.  
**Unconstrained Queries:** 100% byte-identical behavior preserved.

---

## 5. Architectural Boundaries & Non-Goals

1. **Frozen Components Integrity:** Zero changes made to Phase 2.6 generation (`src/generator.py`), Phase 2.7 conversation orchestrator (`src/conversation/`), API dependencies, or PostgreSQL schema.
2. **Corpus Scope:** Zero database writes or external dataset ingestions performed during this phase.

---

### PHASE 3.4 COMPLETE
*Status: All implementation and acceptance criteria satisfied.*
