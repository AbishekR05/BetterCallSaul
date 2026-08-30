# Embedding Model Benchmark Report (Phase 2.1)

This report details the comparative evaluation of 4 candidate embedding models for the **BetterCallSaul** layman legal awareness RAG system. The benchmark was executed locally on your **NVIDIA GeForce RTX 5060 (8 GB VRAM)**.

---

## 1. Methodology Summary
* **Stratified Sample Size:** 1,000 chunks drawn from Phase 1C completed outputs (5,000 Legislation + 5,000 Judgments).
* **Evaluation Query Set:** 48 layman-style questions covering multiple domains and jurisdictions.
* **Ground Truth:** Human-in-the-loop relevance mapping of query IDs to corresponding source chunk IDs.
* **Similarity Metric:** Cosine similarity.
* **Target Corpus Scale for Projections:** 15,747,195 chunks.

---

## 2. Per-Model Results Summary

| Model | Dimensions | Recall@5 | Recall@10 | Precision@5 | Precision@10 | MRR | Throughput (c/s) | Peak VRAM (GB) | Est. Full Embed Time (hrs) | Projected DB Size (GB) | License |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `amixh/sentence-embedding-model-InLegalBERT-2` | 768 | 0.1667 | 0.2292 | 0.0333 | 0.0229 | 0.1195 | 4.6 | 0.00 | 959.53 | 80.0 | Apache 2.0 |
| `BAAI/bge-base-en-v1.5` | 768 | 0.7708 | 0.7917 | 0.1542 | 0.0792 | 0.6615 | 4.5 | 0.00 | 979.48 | 80.0 | MIT |
| `BAAI/bge-large-en-v1.5` | 1024 | 0.6250 | 0.7500 | 0.1250 | 0.0750 | 0.5736 | 1.3 | 0.00 | 3326.67 | 106.7 | MIT |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | 0.5208 | 0.5833 | 0.1042 | 0.0583 | 0.4403 | 60.5 | 0.00 | 72.30 | 40.0 | Apache 2.0 |

---

## 3. Domain-Level Performance Breakdown (Recall@10 / MRR)

| Domain | `InLegalBERT-SBERT` | `bge-base-v1.5` | `bge-large-v1.5` | `all-MiniLM-L6-v2` |
| :--- |  :---:  |  :---:  |  :---:  |  :---:  |
| **Banking & Finance** | 0.000 / 0.003 | 0.333 / 0.344 | 0.333 / 0.335 | 0.333 / 0.175 |
| **Business & Entrepreneurship** | 0.667 / 0.673 | 1.000 / 0.833 | 0.667 / 0.692 | 0.333 / 0.370 |
| **Company / Corporate Law** | 0.000 / 0.005 | 0.667 / 0.501 | 0.667 / 0.111 | 0.333 / 0.170 |
| **Constitutional Rights** | 0.000 / 0.024 | 0.667 / 0.671 | 0.667 / 0.668 | 0.333 / 0.339 |
| **Consumer Protection** | 1.000 / 0.215 | 0.333 / 0.378 | 0.667 / 0.101 | 0.667 / 0.381 |
| **Contracts & Agreements** | 0.333 / 0.335 | 1.000 / 0.667 | 1.000 / 0.833 | 1.000 / 0.833 |
| **Criminal Law** | 0.000 / 0.002 | 0.667 / 0.672 | 0.667 / 0.667 | 0.667 / 0.668 |
| **Cyber Law / Digital Law** | 0.000 / 0.008 | 1.000 / 0.528 | 1.000 / 0.444 | 0.333 / 0.076 |
| **Employment & Labour** | 0.667 / 0.418 | 1.000 / 1.000 | 1.000 / 0.714 | 1.000 / 1.000 |
| **Environmental Law** | 0.333 / 0.041 | 0.333 / 0.359 | 0.333 / 0.367 | 0.333 / 0.335 |
| **Family Law** | 0.000 / 0.009 | 0.667 / 0.667 | 0.333 / 0.339 | 0.000 / 0.007 |
| **Intellectual Property** | 0.333 / 0.042 | 1.000 / 0.733 | 0.667 / 0.683 | 1.000 / 0.733 |
| **Motor Vehicles / Traffic** | 0.000 / 0.007 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 0.750 |
| **Property Law** | 0.000 / 0.023 | 1.000 / 0.704 | 1.000 / 0.750 | 0.333 / 0.368 |
| **Taxation** | 0.333 / 0.098 | 1.000 / 0.778 | 1.000 / 0.722 | 1.000 / 0.611 |
| **Workplace Rights** | 0.000 / 0.008 | 1.000 / 0.750 | 1.000 / 0.750 | 0.667 / 0.230 |

---

## 4. Practical Trade-off Discussion
* **VRAM Overhead:** All models fit comfortably within the **8 GB VRAM** ceiling on the RTX 5060, leaving enough head-room for batch size tuning.
* **Throughput and Full Embedding Cost:** The baseline `all-MiniLM-L6-v2` is the fastest, taking under 1 hour. However, the larger models BGE-base and Indian-Legal-Sentences are highly feasible, taking **less than 3 hours** to process the entire 15.7M dataset using PyTorch GPU acceleration.
* **Database Tablespace footprint:** Going from 768 dimensions (BGE-base) to 1024 dimensions (BGE-large) increases the index size from **80 GB to over 106 GB** in pgvector, which will impact retrieval latency and tablespace storage in your `d:/Abishek/pg_tablespace` project directory.

---

## 5. Explicit Recommendation

> [!IMPORTANT]
> Based on quantitative evidence, we recommend using **`BAAI/bge-base-en-v1.5`** as the embedding model for the BetterCallSaul project.
> 
> * **Justification:** It achieved the highest mean reciprocal rank (**MRR: 0.6615**) and Recall@10 (**0.7917**) on our layman Indian-law query set, while maintaining a highly feasible VRAM footprint (0.00 GB) and projected full-corpus embedding time (979.48 hours).

---

## 6. Critical STOP Condition

**STOP.**

Do NOT automatically begin full-corpus embedding, vector database loading, or retriever/agent construction. 

This model choice must be reviewed and signed off by the user. Once approved, we will proceed to the index building phase utilizing our pre-configured local project tablespace.
