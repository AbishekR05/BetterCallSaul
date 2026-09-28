# PHASE 3.4 PRE-FLIGHT AUDIT & IMPLEMENTATION REPORT

**Report Timestamp:** 2026-09-28 T23:20:00 ISO  
**Status:** **PRE-FLIGHT AUDIT COMPLETE — MANDATORY STOP TRIGGERED FOR SIGN-OFF** (§3, §14)  
**Baseline:** Phase 3.3 Intent-Aware Planning (`650d1f2`), Phase 2.5 Retrieval (Frozen), Phase 2.6 Generation (Frozen)

---

## 1. Executive Summary & Pre-Flight Findings

Per **Phase 3.4 Specification §3 & §14**, a mandatory read-only pre-flight audit was conducted on the frozen retrieval pipeline (`src/retrieval/`) and PostgreSQL database (`bettercallsaul` on `localhost:5432`).

### Critical Audit Finding:
**The frozen Phase 2.5 retriever CANNOT enforce metadata filters reliably without architectural adjustments.**

Specifically, two severe filter enforcement defects and one false-zero ANN recall limitation were discovered in the frozen retrieval pipeline:

1. **Lexical FTS Filter Bypassing (Candidate Leg Defect):** `HybridAdapter.retrieve()` in `src/retrieval/adapters.py` passes filters to dense vector search, but calls `LexicalSearcher.search()` **without filters**. `LexicalSearcher` does not accept a `filters` parameter, allowing unconstrained chunks from any court/source_type to enter the candidate pool and bleed into RRF fusion.
2. **Silent Filter Relaxation (Auto-Relax Defect):** `LegalRetriever.retrieve()` in `src/retrieval/retriever.py` defaults `auto_relax_filters=True`. When a hard metadata filter yields zero candidates or scores below 0.40, `retriever.py` **automatically re-runs vector search with `filters=None`**, silently discarding the user's hard constraint.
3. **Post-ANN False-Zero Risk:** In `src/retrieval/search.py`, vector search uses HNSW `ef_search=64` over 11.37M chunks. Supreme Court judgments account for only 240 out of 5,358,998 documents (0.0045% of the database). HNSW graph traversal with `ef_search=64` can miss rare Supreme Court chunks, causing false-zero returns even when matching chunks exist.

Per §3 & §14 of the Phase 3.4 specification:
> *"If item 2 or 3 shows the frozen retriever cannot enforce filters reliably, STOP and report with options... Await Abishek's explicit sign-off."*

---

## 2. Detailed §3 Pre-Flight Audit Results

### 2.1 Existing `RetrievalFilters` Schema & accepted formats

| Field Name | Type | SQL Mapping (`src/retrieval/filters.py`) | Value Matching Logic | Accepted Formats |
|---|---|---|---|---|
| `court` | `Optional[str]` | `LOWER(d.court) = LOWER(%s)` | Exact lower-case match | `"Supreme Court of India"`, `"High Court of Kerala"` |
| `source_type` | `Optional[str]` | `LOWER(c.source_type) = LOWER(%s)` | Exact lower-case match | `"judgment"`, `"legislation"` |
| `jurisdiction` | `Optional[str]` | `LOWER(d.jurisdiction) = LOWER(%s)` | Exact lower-case match | `"state"`, `"central"` |
| `level` | `Optional[str]` | `LOWER(d.level) = LOWER(%s)` | Exact lower-case match | `"central"`, `"state"` |
| `domains` | `Optional[List[str]]` | `c.document_id IN (SELECT ...)` | IN clause over domain names | `["criminal_law", "property_law"]` |
| `date_after`/`before` | `Optional[str]` | `d.date >= %s` | Date comparison | `"YYYY-MM-DD"` or `"YYYY"` |

### 2.2 Candidate Leg Filter Forwarding Analysis

Tracing `JurisdictionBoostedAdapter.retrieve(query, top_k, filters)` across all legs:

```
JurisdictionBoostedAdapter.retrieve(query, filters)
   ↓
CalibratedAdapter.retrieve(query, filters)
   ↓
RerankedAdapter.retrieve(query, filters)
   ↓
HybridAdapter.retrieve(query, filters)
   ├── Leg 1: Dense Search ──> dense_adapter.retrieve(query, filters=filters)  [HONORED]
   └── Leg 2: Lexical Search ─> lexical_searcher.search(query)                 [DEFECT: FILTERS IGNORED]
```

* **Dense Vector Leg:** Passes `filters` to `LegalRetriever.retrieve()`.
* **Lexical FTS Leg:** `LexicalSearcher.search(query, top_k)` in `src/retrieval/lexical.py` **does NOT accept or apply `filters`**. It executes an unconstrained keyword search across all 11.37M chunks. Unconstrained candidates are then merged via Reciprocal Rank Fusion (RRF), contaminating the candidate pool with out-of-constraint High Court chunks.

### 2.3 Dense HNSW Filter Application & False-Zero Risk

* **HNSW Post/Pre-Filtering Mechanics:** `execute_vector_search()` in `src/retrieval/search.py` executes:
  ```sql
  SELECT ... FROM embeddings e
  JOIN chunks c ON e.chunk_id = c.chunk_id
  JOIN source_documents d ON c.document_id = d.document_id
  WHERE LOWER(d.court) = LOWER('Supreme Court of India')
  ORDER BY e.embedding <=> %s::vector ASC LIMIT %s;
  ```
  With `ef_search=64`, HNSW graph traversal explores the 64 closest vector nodes. Because Supreme Court documents comprise **only 0.0045% of the database** (240 out of 5.35M docs), standard HNSW ANN search often fails to encounter any SC nodes in the top 64 explored candidates.
* **Auto-Relaxation Trap:** When 0 candidates pass the SQL WHERE clause, `LegalRetriever.retrieve()` sees `returned_count < min_acceptable_results (1)` and triggers auto-relaxation:
  ```python
  if insufficient_ev and filters_applied is not None and cfg.auto_relax_filters:
      # RETRIES WITH filters=None!
      relaxed_raw = execute_vector_search(..., filters=None)
  ```
  This silently drops the user's hard constraint and returns High Court documents.

### 2.4 Canonical Stored Metadata Values in Production Database

Direct read-only SQL query against `bettercallsaul` DB on `localhost:5432`:

#### Distinct Stored `court` Values (`source_documents`)
1. `'Madras High Court'`: 2,003,806 documents
2. `'High Court of Kerala'`: 1,568,118 documents
3. `'Orissa High Court'`: 723,299 documents
4. `'High Court of Madhya Pradesh'`: 713,829 documents
5. `'None'`: 237,113 documents *(Legislation)*
6. `'Patna High Court'`: 60,097 documents
7. `'High Court of Manipur'`: 25,822 documents
8. `'High Court of Meghalaya'`: 19,650 documents
9. `'High Court of Madras'`: 6,312 documents
10. `'High Court of Orissa'`: 362 documents
11. `'High Court of Patna'`: 322 documents
12. **`'Supreme Court of India'`: 240 documents**
13. `'High Court of Bombay'`: 18 documents
14. `'High Court of Jharkhand'`: 3 documents
15. `'High Court of Gauhati'`: 3 documents
16. `'High Court of Haryana'`: 2 docs
17. `'High Court of Chennai'`: 1 doc
18. `'High Court of Gujarat'`: 1 doc

#### Distinct Stored `source_type` Values (`chunks`)
1. `'judgment'`: 11,143,976 chunks
2. `'legislation'`: 227,424 chunks

#### Distinct Stored `jurisdiction` Values (`source_documents`)
1. `'state'`: 5,326,274 documents
2. `'central'`: 32,724 documents

---

## 3. Options for Sign-Off (Per §3 & §14 Instructions)

To resolve the pre-flight filter enforcement defects cleanly while respecting frozen layer boundaries, two options are submitted for Abishek's explicit sign-off:

### Option A (Recommended): Minimal Additive Adapter Fix + Pre-Check Existence in Executor
1. **Executor Existence Check & Config Control:**
   - In `RetrievalPlanExecutor` (Phase 3.4), before invoking the retriever, perform a cheap SQL `EXISTS` query for the canonical constraint (e.g. `WHERE LOWER(d.court) = 'supreme court of india'`).
   - If 0 documents match in DB -> immediately return `ConstraintInsufficiency(no_documents_match_constraint)`.
2. **Override `auto_relax_filters = False`:**
   - Pass `RetrievalConfig(auto_relax_filters=False)` when executing hard-constrained calls so `LegalRetriever` never silently drops filters.
3. **Minimal Additive Update to `src/retrieval/` (Requires Sign-Off):**
   - Update `LexicalSearcher.search(query, top_k, filters=None)` in `src/retrieval/lexical.py` to accept and apply `filters`.
   - Update `HybridAdapter.retrieve()` to pass `filters` to `lexical_searcher.search()`.

### Option B: Read-Only Post-Filtering & Pre-Check in `RetrievalPlanExecutor` (Zero Code Changes in `src/retrieval/`)
1. **Executor-Side Existence Check & Filter Enforcement:**
   - Keep `src/retrieval/` 100% frozen with zero changes.
   - In `RetrievalPlanExecutor`, pass `RetrievalConfig(auto_relax_filters=False)` to disable filter relaxation.
   - Post-filter candidates returned by `JurisdictionBoostedAdapter` to purge any unconstrained lexical candidates that bled through.
   - If candidate count under filter is 0, return `ConstraintInsufficiency`.

---

## 4. STOP Condition Triggered

Per **Phase 3.4 Specification §14**:
**Implementation is STOPPED at this report.** No Phase 3.4 feature code (`ConstraintExtractor`, `hard_constraints` schema extensions) has been written yet.

Awaiting Abishek's explicit sign-off on Option A vs Option B before proceeding with implementation.
