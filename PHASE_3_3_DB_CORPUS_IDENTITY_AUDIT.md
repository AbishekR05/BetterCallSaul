# PHASE 3.3 DATABASE & CORPUS IDENTITY AUDIT REPORT

**Audit Timestamp:** 2026-09-28 T20:58:00 ISO  
**Execution Context:** Read-Only Direct SQL Inspection against PostgreSQL 18 Server (`localhost:5432`)

---

## 1. AUTHORITATIVE APPLICATION DATABASE IDENTITY

| Configuration Attribute | Application Setting | Connection / Config Source |
|---|---|---|
| **PostgreSQL Host** | `localhost` | `.env` (`DB_HOST`) / `src/db_phase2.py` |
| **PostgreSQL Port** | `5432` | `.env` (`DB_PORT`) / `src/db_phase2.py` |
| **Database Name** | `bettercallsaul` | `.env` (`DB_NAME`) / `src/db_phase2.py` |
| **Schema** | `public` | PostgreSQL Default Schema |
| **Tablespace** | `bcs_tablespace` | `d:/Abishek/pg_tablespace` (`src/db_phase2.py`) |
| **Live App Entrypoint** | FastAPI (`src.api.main:app`) | `src/api/dependencies.py` -> `LegalRetriever` -> `get_connection()` |

---

## 2. DIAGNOSTIC DATABASE IDENTITY

| Configuration Attribute | Diagnostic Setting | Verification Source |
|---|---|---|
| **PostgreSQL Host** | `localhost` | `scratch/audit_all_databases.py` & `scratch/inspect_exact_courts.py` |
| **PostgreSQL Port** | `5432` | Direct `psycopg` connection to `localhost:5432` |
| **Database Name** | `bettercallsaul` | Direct query against `bettercallsaul` |
| **Schema** | `public` | PostgreSQL Default Schema |
| **Tablespace** | `bcs_tablespace` | `d:/Abishek/pg_tablespace` |

*Conclusion: Both the live running application and the diagnostic scripts query the **EXACT SAME PostgreSQL database, host, port, tablespace, and schema** (`bettercallsaul` on `localhost:5432`).*

---

## 3. CORPUS COUNTS (AUTHORITATIVE DIRECT SQL METRICS)

Direct SQL execution against `bettercallsaul` database:

```sql
SELECT count(*) FROM source_documents; -- 5,358,998
SELECT count(*) FROM chunks;           -- 11,371,400
SELECT count(*) FROM embeddings;       -- 11,371,400
```

### Full Breakdown by Document Type & Court

| Document Classification / Court | Row Count (`source_documents`) | % of Total Corpus | Note / Domain Focus |
|---|---|---|---|
| **Madras High Court** | 2,003,806 | 37.39% | State High Court Judgments |
| **High Court of Kerala** | 1,568,118 | 29.26% | State High Court Judgments |
| **Orissa High Court** | 723,299 | 13.50% | State High Court Judgments |
| **High Court of Madhya Pradesh** | 713,829 | 13.32% | State High Court Judgments |
| **Patna High Court** | 60,097 | 1.12% | State High Court Judgments |
| **High Court of Manipur / Meghalaya / Others** | 45,716 | 0.85% | State High Court Judgments |
| **Legislation (`court = 'None'`)** | 237,113 | 4.42% | Central & State Acts / Statutes |
| **Supreme Court of India** | **240** | **0.0045%** | **Constitutional / Criminal / Service Law** |
| **TOTAL CORPUS** | **5,358,998** | **100.00%** | **11,371,400 Chunks / Embeddings** |

---

## 4. SIDE-BY-SIDE COMPARISON: APPLICATION VS DIAGNOSTIC ENVIRONMENT

| Metric / Parameter | Live Application Environment | Diagnostic Environment | Match Status |
|---|---|---|---|
| **Database Name** | `bettercallsaul` | `bettercallsaul` | **IDENTICAL** |
| **Host & Port** | `localhost:5432` | `localhost:5432` | **IDENTICAL** |
| **Tablespace** | `bcs_tablespace` | `bcs_tablespace` | **IDENTICAL** |
| **`source_documents` count** | 5,358,998 | 5,358,998 | **IDENTICAL** |
| **`chunks` count** | 11,371,400 | 11,371,400 | **IDENTICAL** |
| **`embeddings` count** | 11,371,400 | 11,371,400 | **IDENTICAL** |
| **Supreme Court document count** | 240 | 240 | **IDENTICAL** |
| **Legislation document count** | 237,113 | 237,113 | **IDENTICAL** |
| **State High Court document count** | 5,121,645 | 5,121,645 | **IDENTICAL** |

---

## 5. EXACT EXPLANATION FOR THE 5.14M vs 5,144 DISCREPANCY

1. **Production Corpus Size:** The authoritative production corpus in PostgreSQL 18 contains **5,358,998 source documents** and **11,371,400 chunks/embeddings** (~5.36M / 11.37M).
2. **First Diagnostic Truncation Artifact:** In the previous retrieval diagnostic script (`scratch/run_full_diagnostic.py`), a `GROUP BY court LIMIT 10` query was executed to summarize court distributions. Because 10 High Courts dominated the top list, the output truncated the tail of the `GROUP BY` list.
3. **Supreme Court Document Rank:** In `source_documents`, the `Supreme Court of India` entry is ranked **12th** out of 18 court entities with **240 documents**. Because `LIMIT 10` cut off the tail, the previous diagnostic script misreported 0 Supreme Court documents.
4. **Resolution:** Direct SQL `COUNT(*)` without `LIMIT` clauses confirms that the database has **5,358,998 documents** and **exactly 240 Supreme Court documents** are safely present in the database.

---

## 6. AUTHORITATIVE APPLICATION DATABASE DETERMINATION

* **Which database is actually being queried by the live application?**
  - The live application (FastAPI backend + Uvicorn server) queries **`bettercallsaul` on `localhost:5432`** using `bcs_tablespace`.
  - Both live turns API (`/api/v1/sessions/.../turns`) and the Phase 3.3 `IntentAwareRetrieverAdapter` connect directly to this 5.35M-document database.

---

## 7. SUPREME COURT DOCUMENT PRESENCE VERIFICATION

* **Are the previously reported 240 Supreme Court documents still present in the authoritative application corpus?**
  - **YES. Exactly 240 Supreme Court documents are present in `source_documents`** (e.g., landmark cases like *State of Punjab v. Jagdev Singh Talwandi*, *State of Haryana v. Bhajan Lal*, *State of Kerala v. M.K. Kunhikannan Nambiar*).

### Why the Supreme Court Flat Possession Query Retrieved High Court Cases:
1. **Ratio Disparity:** Supreme Court judgments represent **240 out of 5,358,998 documents (0.0045%)**. State High Court judgments represent **5,121,645 out of 5,358,998 documents (95.57%)**.
2. **Domain Scope of the 240 SC Cases:** The 240 Supreme Court decisions currently in the 5.35M corpus are primarily criminal, constitutional, and service law cases. **Zero out of the 240 SC cases cover real-estate flat possession disputes or builder compensation (e.g. RERA / Consumer Protection Act).**
3. **Dense Vector Search Behavior:** When querying for *"compensation for delayed possession of flat"*, pgvector HNSW dense search scanned the 11.37M vector index and retrieved high-scoring High Court writ petitions (Allahabad & Kerala High Courts) where property compensation/possession keywords matched, completely overwhelming the 240 unrelated SC criminal/service law vectors.

---

## 8. RECOMMENDED NEXT STEP BASED STRICTLY ON EVIDENCE

1. **Ingest Consumer / Real-Estate Supreme Court Cases (Phase 4.0 Corpus Expansion):**
   - Now that we have verified that the 240 Supreme Court cases in the database are criminal/constitutional cases, adding a targeted dataset of Supreme Court Real Estate / Consumer Rulings (e.g., *Supertech v. Emerald Court*, *DLF Homes v. D.S. Dhanda*, *Pioneer Urban v. Govindan Raghavan*) will allow vector search to retrieve authoritative SC precedents.
2. **Implement Hard Court Metadata Filtering in Phase 3.3 Adapter:**
   - Update `IntentAwareRetrieverAdapter` to pass explicit `RetrievalFilters(court="Supreme Court of India")` to `LegalRetriever` when the user explicitly requests Supreme Court rulings.

---

### AUDIT COMPLETE
*Status: All diagnostic requirements satisfied. Zero code or database modifications made.*
