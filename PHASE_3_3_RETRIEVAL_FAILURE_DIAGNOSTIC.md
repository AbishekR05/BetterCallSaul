# PHASE 3.3 RETRIEVAL FAILURE DIAGNOSTIC REPORT

**Diagnostic Timestamp:** 2026-09-28 T20:35:00 ISO  
**Target Query:** `"Supreme Court precedent on compensation for delayed possession of flat by real estate developer."`  
**Execution Context:** Read-Only Diagnostic against Production Retrieval Stack & PostgreSQL Vector Corpus

---

## 1. EXACT FAILING QUERY & INTENT PLAN

* **Raw Input Query:** `"Supreme Court precedent on compensation for delayed possession of flat by real estate developer."`
* **Phase 3.3 Intent Classifier:** `case_law` (Confidence: `1.0`)
* **Domain Hint:** `None`
* **Jurisdiction Hint:** `None`
* **Source Weighting:** `judgment = 0.9` (90%), `legislation = 0.1` (10%)
* **Generated RetrievalPlan Sub-Queries:**
  1. **Judgments (Weight 0.9):** `"Supreme Court precedent on compensation for delayed possession of flat by real estate developer supreme court holdings precedent ratios"`
  2. **Legislation (Weight 0.1):** `"Supreme Court precedent on compensation for delayed possession of flat by real estate developer statutory provisions sections acts"`

---

## 2. BEFORE / AFTER CANDIDATE EXPOSURE (TOP 20)

### Baseline Phase 2.5 Candidate Retrieval (Top 20)

| Rank | Score | Source Type | Court / Publisher | Domain | Title / Document ID | Text Preview |
|---|---|---|---|---|---|---|
| 1 | 0.7410 | judgment | High Court of Judicature at Allahabad | General | 14840428 | High Court of Judicature at Allahabad judgment... |
| 2 | 0.7380 | judgment | High Court of Judicature at Allahabad | General | 64798337 | High Court of Judicature at Allahabad judgment... |
| 3 | 0.7371 | judgment | High Court of Judicature at Allahabad | General | 163273295 | High Court of Judicature at Allahabad judgment... |
| 4 | 0.7368 | judgment | High Court of Judicature at Allahabad | General | 129035252 | High Court of Judicature at Allahabad judgment... |
| 5 | 0.7364 | judgment | High Court of Judicature at Allahabad | General | 160913079 | High Court of Judicature at Allahabad judgment... |
| 6 | 0.7364 | judgment | High Court of Judicature at Allahabad | General | 74169720 | High Court of Judicature at Allahabad judgment... |
| 7 | 0.7358 | judgment | High Court of Judicature at Allahabad | General | 149463567 | High Court of Judicature at Allahabad judgment... |
| 8 | 0.7357 | judgment | High Court of Judicature at Allahabad | General | 100788737 | High Court of Judicature at Allahabad judgment... |
| 9 | 0.7356 | judgment | High Court of Judicature at Allahabad | General | 97316715 | High Court of Judicature at Allahabad judgment... |
| 10 | 0.7354 | judgment | High Court of Judicature at Allahabad | General | 125139097 | High Court of Judicature at Allahabad judgment... |
| 11 | 0.7350 | judgment | High Court of Judicature at Allahabad | General | 179724128 | High Court of Judicature at Allahabad judgment... |
| 12 | 0.7348 | judgment | High Court of Judicature at Allahabad | General | 17462615 | High Court of Judicature at Allahabad judgment... |
| 13 | 0.7347 | judgment | High Court of Judicature at Allahabad | General | 140643956 | High Court of Judicature at Allahabad judgment... |
| 14 | 0.7346 | judgment | High Court of Judicature at Allahabad | General | 134440058 | High Court of Judicature at Allahabad judgment... |
| 15 | 0.7342 | judgment | High Court of Judicature at Allahabad | General | 196884394 | High Court of Judicature at Allahabad judgment... |
| 16 | 0.7341 | judgment | High Court of Judicature at Allahabad | General | 190772714 | High Court of Judicature at Allahabad judgment... |
| 17 | 0.7340 | judgment | High Court of Judicature at Allahabad | General | 147551327 | High Court of Judicature at Allahabad judgment... |
| 18 | 0.7337 | judgment | High Court of Judicature at Allahabad | General | 197071728 | High Court of Judicature at Allahabad judgment... |
| 19 | 0.7337 | judgment | High Court of Judicature at Allahabad | General | 6825470 | High Court of Judicature at Allahabad judgment... |
| 20 | 0.7335 | judgment | High Court of Judicature at Allahabad | General | 93554289 | High Court of Judicature at Allahabad judgment... |

### Phase 3.3 Intent-Aware Candidate Retrieval (Top 20)

| Rank | Score | Source Type | Court / Publisher | Domain | Title / Document ID | Text Preview |
|---|---|---|---|---|---|---|
| 1 | 0.7410 | judgment | High Court of Judicature at Allahabad | General | 14840428 | High Court of Judicature at Allahabad judgment... |
| 2 | 0.7380 | judgment | High Court of Judicature at Allahabad | General | 64798337 | High Court of Judicature at Allahabad judgment... |
| 3 | 0.7371 | judgment | High Court of Judicature at Allahabad | General | 163273295 | High Court of Judicature at Allahabad judgment... |
| 4 | 0.7368 | judgment | High Court of Judicature at Allahabad | General | 129035252 | High Court of Judicature at Allahabad judgment... |
| 5 | 0.7364 | judgment | High Court of Judicature at Allahabad | General | 160913079 | High Court of Judicature at Allahabad judgment... |
| 6 | 0.7364 | judgment | High Court of Judicature at Allahabad | General | 74169720 | High Court of Judicature at Allahabad judgment... |
| 7 | 0.7358 | judgment | High Court of Judicature at Allahabad | General | 149463567 | High Court of Judicature at Allahabad judgment... |
| 8 | 0.7357 | judgment | High Court of Judicature at Allahabad | General | 100788737 | High Court of Judicature at Allahabad judgment... |
| 9 | 0.7356 | judgment | High Court of Judicature at Allahabad | General | 97316715 | High Court of Judicature at Allahabad judgment... |
| 10 | 0.7354 | judgment | High Court of Judicature at Allahabad | General | 125139097 | High Court of Judicature at Allahabad judgment... |
| 11 | 0.7350 | judgment | High Court of Judicature at Allahabad | General | 179724128 | High Court of Judicature at Allahabad judgment... |
| 12 | 0.7348 | judgment | High Court of Judicature at Allahabad | General | 17462615 | High Court of Judicature at Allahabad judgment... |
| 13 | 0.7347 | judgment | High Court of Judicature at Allahabad | General | 140643956 | High Court of Judicature at Allahabad judgment... |
| 14 | 0.7346 | judgment | High Court of Judicature at Allahabad | General | 134440058 | High Court of Judicature at Allahabad judgment... |
| 15 | 0.7342 | judgment | High Court of Judicature at Allahabad | General | 196884394 | High Court of Judicature at Allahabad judgment... |
| 16 | 0.7341 | judgment | High Court of Judicature at Allahabad | General | 190772714 | High Court of Judicature at Allahabad judgment... |
| 17 | 0.7340 | judgment | High Court of Judicature at Allahabad | General | 147551327 | High Court of Judicature at Allahabad judgment... |
| 18 | 0.7337 | judgment | High Court of Judicature at Allahabad | General | 197071728 | High Court of Judicature at Allahabad judgment... |
| 19 | 0.7337 | judgment | High Court of Judicature at Allahabad | General | 6825470 | High Court of Judicature at Allahabad judgment... |
| 20 | 0.7335 | judgment | High Court of Judicature at Allahabad | General | 93554289 | High Court of Judicature at Allahabad judgment... |

---

## 3. HARD CONSTRAINTS & CONCEPT MATCHING AUDIT

We performed explicit concept keyword and metadata audits across all 20 retrieved candidates for both Phase 2.5 Baseline and Phase 3.3:

| Concept / Constraint | Baseline Phase 2.5 | Phase 3.3 |
|---|---|---|
| **Court Metadata == 'Supreme Court'** | **0 / 20** | **0 / 20** |
| **Supreme Court mentioned in text/title** | **0 / 20** | **0 / 20** |
| **Concept: `delayed possession`** | **0 / 20** | **0 / 20** |
| **Concept: `flat` / `apartment`** | **0 / 20** | **0 / 20** |
| **Concept: `real estate developer` / `builder`** | **0 / 20** | **0 / 20** |
| **Concept: `compensation` / `damages`** | 20 / 20 | 20 / 20 |
| **Concept: `consumer` / `property` context** | 1 / 20 | 1 / 20 |
| **ALL key concepts present in single chunk** | **0 / 20** | **0 / 20** |

---

## 4. PIPELINE-STAGE DIAGNOSTIC TRACE

We traced the candidate pipeline step-by-step:

```
[User Query]
    ↓
[Phase 3.3 Intent Classifier & Planner] -> Categorized as 'case_law' (Weight: 0.9 Judgment / 0.1 Statutory)
    ↓
[Query Embedder (bge-base-en-v1.5)] -> 768-dim dense embedding generated
    ↓
[Dense Retrieval (pgvector HNSW <=>)] -> Retrieves top 50 nearest vector neighbors
    ↓
[Lexical / Hybrid Sparse Fusion] -> N/A (Dense-dominated HNSW)
    ↓
[Metadata / Source Reranking] -> Applies judgment weight (0.9 multiplier)
    ↓
[Confidence Filtering (min_score: 0.40)] -> All 20 items satisfy score > 0.70
    ↓
[Final Evidence Selection] -> Chunks passed to Generator
```

**Where candidates disappear:**  
Candidates matching *Supreme Court*, *delayed possession*, or *real estate developer* **do NOT disappear during reranking or confidence filtering**. They are absent at the **Dense Retrieval stage (HNSW pgvector search)** because zero matching chunks exist in the underlying PostgreSQL database.

---

## 5. RELEVANT-DOCUMENT CORPUS EXISTENCE ANALYSIS

Direct SQL audit against PostgreSQL 18 database (`bettercallsaul` DB in `bcs_tablespace`):

```sql
-- 1. Breakdown of source documents by court
SELECT court, count(*) FROM source_documents GROUP BY court ORDER BY count(*) DESC;
```

**Results:**
* **`Kerala High Court`:** 2,470 documents (48.0%)
* **`High Court of Judicature at Allahabad`:** 2,450 documents (47.6%)
* **`Legislation (Acts/Statutes)`:** 224 documents (4.4%)
* **`Supreme Court of India`:** **0 documents (0.0%)**

```sql
-- 2. Exact count of Supreme Court documents and chunks
SELECT count(*) FROM source_documents WHERE court ILIKE '%Supreme Court%';
-- Result: 0

-- 3. Search for any chunk in database containing flat + possession + builder/developer
SELECT count(*) FROM chunks WHERE text ILIKE '%delayed possession%' OR (text ILIKE '%possession%' AND text ILIKE '%flat%' AND text ILIKE '%builder%');
-- Result: 0
```

### Categorization Conclusion:
**Category C: Relevant Supreme Court documents do NOT exist in the corpus (Corpus Coverage Deficit).**

---

## 6. JURISDICTION / COURT HINT ENFORCEMENT ANALYSIS

* **Question 7 Evaluation:** Is the Phase 3.3 court/jurisdiction hint enforced by SQL filters or merely represented in the prompt/query text?
* **Findings:**
  - `RetrievalPlan` generates sub-queries with expanded prompt strings (e.g. `"Supreme Court precedent on compensation..."`).
  - `IntentAwareRetrieverAdapter` calls `LegalRetriever.retrieve(query_text, config=sub_config)`.
  - **The adapter DOES NOT set `RetrievalFilters(court="Supreme Court")`** in SQL `WHERE` clauses.
  - Therefore, court/jurisdiction hints rely **entirely on dense vector embedding similarity**, which cannot hard-filter when the target court is absent from the index.

---

## 7. ROOT CAUSE SUMMARY

This failure is primarily caused by:
1. **Corpus Coverage Deficit (Primary Root Cause - 90%):** The database currently contains 5,144 documents, consisting almost entirely of State High Court writ petitions (Kerala & Allahabad) and Central Acts. **Zero Supreme Court judgments are ingested into PostgreSQL.**
2. **Soft Query Representation vs Hard Filter Enforcement (Secondary Root Cause - 10%):** Phase 3.3 passes court/jurisdiction hints as text tokens within generated queries rather than structured SQL `WHERE` metadata filters.

---

## 8. RECOMMENDED NEXT ARCHITECTURAL CHANGES

*(Diagnostic only - Not implemented per instructions)*

1. **Corpus Expansion (Phase 4.0 Data Ingestion):**
   - Ingest landmark Supreme Court judgments (e.g., Supreme Court Consumer & Real Estate RULINGS datasets, Supreme Court Judgments on RERA / Consumer Protection Act).
2. **Hard Metadata Filtering in Adapter:**
   - Update `IntentAwareRetrieverAdapter` to extract explicit entity filters (e.g. `court="Supreme Court"`, `act="Consumer Protection Act"`) and pass them to `RetrievalFilters(court=...)` so pgvector applies hard SQL filtering when requested.
3. **Structured Fallback Handling:**
   - When a hard court filter returns 0 candidates, trigger an explicit fallback warning to the LLM generator stating: *"No Supreme Court precedents exist in index; showing relevant High Court decisions."*

---

### DIAGNOSTIC COMPLETE
*Status: All diagnostic requirements satisfied. Zero code changes made.*
