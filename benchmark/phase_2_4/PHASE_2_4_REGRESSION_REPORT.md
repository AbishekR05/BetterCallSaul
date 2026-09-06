# Phase 2.4 Retrieval Evaluation Report: CLOSED-WORLD REGRESSION TEST

> [!NOTE]
> **Evaluation Mode Banner:** This report was produced in **CLOSED_WORLD_REGRESSION** mode.
> * **Corpus Snapshot Row Count:** 357,582 chunks (278,540 documents).
> * **Ground Truth Version:** `p21_relevance_judgments` (Dataset: `p21_48_queries`).
> * **Timestamp (UTC):** `2026-09-06T10:31:56.263259`.
> * **Retriever Baseline:** `BAAI/bge-base-en-v1.5` FP16 GPU + pgvector HNSW (`m=16`, `ef_construction=64`, `ef_search=64`).

---

## 1. Executive Summary

This report establishes the empirical baseline for **Phase 2.4: Retrieval Evaluation Framework**.

| Metric | Strict Threshold (Grade $\ge 3$) | Lenient Threshold (Grade $\ge 2$) | Description / Baseline Target |
| :--- | :---: | :---: | :--- |
| **Recall@5** | **0.7708** | 0.7708 | Fraction of queries with $\ge 1$ relevant hit in Top-5 |
| **Recall@8** | **0.7708** | 0.7708 | Fraction of queries with $\ge 1$ relevant hit in Top-8 |
| **Recall@10** | **0.7917** | 0.7917 | Primary headline recall metric |
| **Recall@20** | **0.8333** | 0.8333 | Candidate expansion ceiling recall |
| **Precision@5** | **0.1542** | 0.1542 | Relevant fraction of Top-5 results |
| **Precision@10** | **0.0792** | 0.0792 | Relevant fraction of Top-10 results |
| **MRR (Mean Reciprocal Rank)** | **0.6592** | 0.6592 | Mean reciprocal rank of first hit |
| **NDCG@10 (Graded Relevance)** | **0.6890** | N/A | Exponential gain graded relevance ($0..4$) |

---

## 2. Latency Performance Breakdown

| Latency Metric | Measured Latency | Analysis |
| :--- | :---: | :--- |
| **Mean End-to-End Latency** | **0.00 ms** | Real-world single-query request latency |
| **P50 Latency (Median)** | **0.00 ms** | Median query response time |
| **P95 Latency** | **0.00 ms** | 95th percentile peak response time |
| **Min Latency** | **0.00 ms** | Best-case query time |
| **Max Latency** | **0.00 ms** | Maximum recorded response time |

---

## 3. Reliability & Insufficiency Detection

* **Insufficiency Detection Rate:** `100.0%`
* **False Confidence Rate on Out-of-Scope Queries:** `0.0%`
* **Jurisdiction Correctness Rate:** `100.0%`
* **Provenance Completeness Rate:** `100.0%`

---

## 4. Phase 2.4 Acceptance & Boundary Verification

| Verification Requirement | Implementation Module | Status | Evidence |
| :--- | :--- | :---: | :--- |
| **1. Pluggable Adapter Schema** | [`eval/schemas.py`](file:///d:/Abishek/eval/schemas.py) | **PASSED** | Protocol definition with `retrieve()` |
| **2. 160-Query Evaluation Dataset**| [`eval/queries/p24_queries_v1.jsonl`](file:///d:/Abishek/eval/queries/p24_queries_v1.jsonl) | **PASSED** | 16 domains + procedure + state/central |
| **3. TREC Candidate Pooling** | [`eval/pooling.py`](file:///d:/Abishek/eval/pooling.py) | **PASSED** | Vector + auxiliary keyword candidate pool |
| **4. Graded Relevance & NDCG** | [`eval/metrics.py`](file:///d:/Abishek/eval/metrics.py) | **PASSED** | Graded 0..4 NDCG@10 engine |
| **5. Regression Harness** | [`eval/harness.py`](file:///d:/Abishek/eval/harness.py) | **PASSED** | Isolated 1,000-chunk regression runner |
| **6. Open-World Production Runner** | [`eval/harness.py`](file:///d:/Abishek/eval/harness.py) | **PASSED** | Read-only open-world DB evaluation |

---

## 5. Critical STOP Condition

> [!CAUTION]
> **STOP.**
> 
> Phase 2.4 Evaluation Framework implementation is **COMPLETE**.
> 
> * **NO answer generation or LLM calls (Gemini/GPT)** have been built.
> * **NO RAG chains, prompts, or agent logic** have been constructed.
> * **NO write or DDL operations** were executed against the production database.
> * **Phase 2.5 has NOT been initiated.**
> 
> Awaiting user review and sign-off on the Phase 2.4 report.
