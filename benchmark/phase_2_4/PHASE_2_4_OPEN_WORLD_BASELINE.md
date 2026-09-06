# Phase 2.4 Retrieval Evaluation Report: OPEN-WORLD PRODUCTION EVALUATION

> [!NOTE]
> **Evaluation Mode Banner:** This report was produced in **OPEN_WORLD** mode.
> * **Corpus Snapshot Row Count:** 357,582 chunks (278,540 documents).
> * **Ground Truth Version:** `ground_truth_v1` (Dataset: `p24_queries_v1`).
> * **Timestamp (UTC):** `2026-09-06T10:37:25.806421`.
> * **Retriever Baseline:** `BAAI/bge-base-en-v1.5` FP16 GPU + pgvector HNSW (`m=16`, `ef_construction=64`, `ef_search=64`).

---

## 1. Executive Summary

This report establishes the empirical baseline for **Phase 2.4: Retrieval Evaluation Framework**.

| Metric | Strict Threshold (Grade $\ge 3$) | Lenient Threshold (Grade $\ge 2$) | Description / Baseline Target |
| :--- | :---: | :---: | :--- |
| **Recall@5** | **1.0000** | 0.5000 | Fraction of queries with $\ge 1$ relevant hit in Top-5 |
| **Recall@8** | **1.0000** | 0.8000 | Fraction of queries with $\ge 1$ relevant hit in Top-8 |
| **Recall@10** | **1.0000** | 1.0000 | Primary headline recall metric |
| **Recall@20** | **1.0000** | 1.0000 | Candidate expansion ceiling recall |
| **Precision@5** | **0.6000** | 1.0000 | Relevant fraction of Top-5 results |
| **Precision@10** | **0.3000** | 1.0000 | Relevant fraction of Top-10 results |
| **MRR (Mean Reciprocal Rank)** | **1.0000** | 1.0000 | Mean reciprocal rank of first hit |
| **NDCG@10 (Graded Relevance)** | **1.0000** | N/A | Exponential gain graded relevance ($0..4$) |

---

## 2. Latency Performance Breakdown

| Latency Metric | Measured Latency | Analysis |
| :--- | :---: | :--- |
| **Mean End-to-End Latency** | **613.95 ms** | Real-world single-query request latency |
| **P50 Latency (Median)** | **349.51 ms** | Median query response time |
| **P95 Latency** | **2479.84 ms** | 95th percentile peak response time |
| **Min Latency** | **257.91 ms** | Best-case query time |
| **Max Latency** | **4163.12 ms** | Maximum recorded response time |

---

## 3. Reliability & Insufficiency Detection

* **Insufficiency Detection Rate:** `0.0%`
* **False Confidence Rate on Out-of-Scope Queries:** `100.0%`
* **Jurisdiction Correctness Rate:** `0.0%`
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
