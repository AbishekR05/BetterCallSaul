# Phase 2.2 Pilot Indexing & Production Pipeline Report

This report details the execution and validation of the **Phase 2.2 Pilot Vector Indexing Pipeline** for the **BetterCallSaul** layman legal awareness RAG system.

---

## 1. Executive Summary

* **Target Embedding Model:** `BAAI/bge-base-en-v1.5` (768 dimensions).
* **Hardware Execution:** **NVIDIA GeForce RTX 5060 (8 GB VRAM)** with PyTorch CUDA 12.8 Nightly (`torch-2.12.0.dev+cu128`) in **FP16 mixed-precision**.
* **Storage Location:** Custom project tablespace `bcs_tablespace` located on the project D: drive ([`d:/Abishek/pg_tablespace`](file:///d:/Abishek/pg_tablespace)).
* **Pilot Corpus Size:** 1,000 stratified legal chunks (500 Legislation + 500 Judgments).
* **Validation Suite Status:** **7 / 7 CHECKS PASSED (100% SUCCESS)**.

---

## 2. Pilot Performance Metrics

| Metric | Measured Value | Notes |
| :--- | :---: | :--- |
| **GPU Embedding Throughput** | **203.26 chunks/sec** | Measured on RTX 5060 with FP16 batch size 256 |
| **Peak GPU VRAM Allocated** | **3.70 GB** | Out of 8.0 GB available VRAM |
| **PostgreSQL COPY Bulk Load Rate** | **1,506.21 rows/sec** | Atomic binary `COPY` into `bcs_tablespace` |
| **Vector Index Type** | **HNSW (Cosine)** | Parameters: `m = 16`, `ef_construction = 64` |
| **Index Construction Time** | **< 1.0s** | Built post-load in `bcs_tablespace` |

---

## 3. Validation Suite Results (Section 14 Compliance)

All 7 mandatory automated validation checks were executed by [`scratch/validate_phase2_2.py`](file:///d:/Abishek/scratch/validate_phase2_2.py):

| Validation Check | Description | Status | Details / Evidence |
| :--- | :--- | :---: | :--- |
| **1. Row-Count Reconciliation** | `chunks` == `embeddings` == input chunks | **PASSED** | 999 `source_documents`, 1,000 `chunks`, 1,000 `embeddings` |
| **2. Referential Integrity** | Zero orphaned rows in relational schema | **PASSED** | 0 orphaned chunks, 0 orphaned embeddings |
| **3. Vector Sanity** | 768 dimensions, no NaNs/Infs, unit norm | **PASSED** | All sampled vectors: 768 dims, L2 norm = 1.0000 |
| **4. Similarity Search Smoke Test** | `bge-base` query-prefix vector search | **PASSED** | Successfully retrieved Maharashtra Rent Control Act Section 43 for tenant deposit query |
| **5. Metadata Filtering** | Post/Pre-filtering on jurisdiction | **PASSED** | Filter `jurisdiction='central'` returned 100% matching central statutes |
| **6. Idempotency & Resumability** | Conflict handling & manifest retry | **PASSED** | `ON CONFLICT (chunk_id) DO NOTHING` executed safely without duplicate errors |
| **7. Truncation & Skip Audit** | Track max/avg chunk character lengths | **PASSED** | Max char length: 6,013, Avg char length: 1,906.18 |

---

## 4. Scalability Projections for Full Corpus (15.7M Chunks)

Based on the empirical measurements from this pilot run:

* **GPU Embedding Time (15.7M chunks):** **~21.5 hours** total (at 203 chunks/sec in continuous streaming mode).
* **Raw Vector Storage (15.7M x 768 dims x 4 bytes):** **~48.3 GB**.
* **Total PostgreSQL Tablespace Footprint (Text + Metadata + HNSW Index):** **~80.0 GB** inside [`d:/Abishek/pg_tablespace`](file:///d:/Abishek/pg_tablespace).
* **RAM Footprint:** In-flight batch memory stays under **2.5 GB RAM**, well within your 32 GB DDR5 budget.

---

## 5. Controlled 50,000-Chunk Pipeline Architecture Benchmark

Per project guidelines, a controlled empirical benchmark was executed on a **50,000-chunk sample** (`sample_50k.parquet`) comparing three streaming pipeline architectures before configuring the production pipeline:

### Empirical Benchmark Results

| Strategy / Architecture | Sustained Throughput | Peak GPU VRAM | Peak RAM | Est. 15.7M Total Time | Stability & Contention Notes | Recommendation Status |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **Strategy 1: Baseline Single Worker (Batch 256, FP16)** | **260.04 c/s** | **3.70 GB** | **14.90 GB** | **16.82 hours** | Zero IPC/GPU lock overhead; 100% stable; 0 OOM risk | **RECOMMENDED (OPTIMAL)** |
| **Strategy 2: DataLoader Prefetch (`num_workers=2`, `pin_memory=True`)** | **198.47 c/s** | **3.73 GB** | **14.99 GB** | **22.04 hours** | ~24% slower; PyTorch worker IPC string serialization overhead | Not Recommended |
| **Strategy 3: Dual-Worker Parallel Streams (`multiprocessing`)** | **148.47 c/s** | **7.40 GB** | **15.22 GB** | **29.46 hours** | ~43% slower; Windows WDDM CUDA context-switch lock contention & 2x VRAM duplicate model weights | Not Recommended |

### Architecture Benchmark Analysis & Key Findings

1. **Strategy 1 (Baseline Single Worker FP16) is the Winner:**
   - Achieves the highest sustained throughput at **260.04 chunks/sec**.
   - Reduces estimated 15.7M total execution time from ~21.5 hours down to **16.82 hours**.
   - Uses minimal VRAM (**3.70 GB**), leaving ample headroom on the 8 GB RTX 5060.
   - Eliminates process synchronization bugs, IPC bottlenecks, and GPU driver lock contention.

2. **Why Strategy 2 (DataLoader Prefetch) Performed Slower:**
   - Serializing Python string text objects across PyTorch DataLoader worker processes via IPC queues introduces CPU-to-main-thread marshaling overhead.

3. **Why Strategy 3 (Dual-Worker Multiprocessing) Failed to Scale:**
   - Under Windows WDDM GPU driver architecture, multiple Python processes competing for the same CUDA context incur heavy time-slicing and lock contention.
   - Each process duplicates model weights in VRAM (3.70 GB x 2 = **7.40 GB VRAM**), approaching the GPU memory limit without any speedup.

### Benchmark Recommendation

> [!IMPORTANT]
> Based on empirical benchmark evidence, **Strategy 1 (Single Worker, Batch 256, FP16 mixed precision)** is recommended for the production pipeline. Dual-Worker Parallel Streams are **rejected** due to Windows GPU context-switching overhead and double VRAM footprint.

---

## 6. Resumability & Interruption Safety

The pipeline uses [`scripts/manifest_manager.py`](file:///d:/Abishek/scripts/manifest_manager.py) to track status at batch-file granularity (`pending` ➔ `embedding` ➔ `embedded` ➔ `loading` ➔ `loaded`).
* If interrupted with **Ctrl+C, power loss, or reboot**, the pipeline auto-resets uncommitted transient states and resumes cleanly from the exact last incomplete batch file.
* Database primary key constraints (`chunk_id`, `document_id`) enforce idempotency, preventing duplicate rows even if re-run.

---

## 7. Critical STOP Condition

> [!CAUTION]
> **STOP.**
> 
> Per the project specification in `Phase 2 2 vector index construction.md`, the pilot run, validation suite, and 50,000-chunk benchmark have completed successfully, and **the full 15.7M dataset run must NOT begin automatically.**
> 
> This pilot report requires review and manual sign-off before initiating the full 15.7M corpus embedding and database indexing.

