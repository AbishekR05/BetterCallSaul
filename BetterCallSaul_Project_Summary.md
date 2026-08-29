# Project Summary: BetterCallSaul (Legal Awareness AI)

This document provides a comprehensive progress report and architectural summary for the **BetterCallSaul** project (a source-grounded Legal Awareness AI system for common citizens). This report can be shared with Claude to continue development.

---

## 1. Project Motivation & Goals
* **Preventive Legal Awareness:** Help ordinary citizens understand relevant legal constraints, regulations, and consumer/business liabilities *before* they take action (e.g. signing a contract, starting an online store, renting properties), rather than only answering post-dispute questions.
* **Orchestrated RAG:** A hybrid search pipeline (vector + lexical) grounded in authoritative legal sources, orchestrating LLM generation with strict inline citations to reduce hallucinations.

---

## 2. Phase 0: RAG V0 Baseline (Completed & Tagged)
We successfully built, tested, and pushed a modular local RAG baseline. The commit was tagged as `RAG_V0` on GitHub.

### Core Stack:
* **Database:** PostgreSQL 18 with the `pgvector` extension.
* **Embeddings:** Local SentenceTransformers using the `all-MiniLM-L6-v2` model (384 dimensions).
* **LLM Engine:** Remote Gemini API call utilizing `gemini-3.5-flash` with strict inline citation prompting.
* **API Wrapper:** FastAPI backend providing endpoints to query the grounded RAG database.

### Source Layout:
* [`src/config.py`](file:///d:/Full%20Stack/BetterCallSaul/src/config.py): Configuration parser.
* [`src/db.py`](file:///d:/Full%20Stack/BetterCallSaul/src/db.py): Bootstraps schema, tables (`documents`/`chunks`), and HNSW cosine indexes.
* [`src/ingestion.py`](file:///d:/Full%20Stack/BetterCallSaul/src/ingestion.py): Parses PDFs using PyMuPDF, chunks text, generates embeddings, and saves to database.
* [`src/retrieval.py`](file:///d:/Full%20Stack/BetterCallSaul/src/retrieval.py): Implements Reciprocal Rank Fusion (RRF) to merge vector similarity with full-text lexical search scores.
* [`src/generator.py`](file:///d:/Full%20Stack/BetterCallSaul/src/generator.py): Formats prompt contexts, queries Gemini, and manages citations.
* [`src/app.py`](file:///d:/Full%20Stack/BetterCallSaul/src/app.py): Exposes FastAPI endpoints.
* [`main.py`](file:///d:/Full%20Stack/BetterCallSaul/main.py): Unified CLI script providing commands: `init`, `ingest`, `query`, and `serve`.

---

## 3. Phase 1A: Legal Dataset Acquisition (Completed)
We designed and ran a scalable, resilient dataset acquisition script to filter and capture relevant legislation and case laws.

### Source Corpus:
* Gated HuggingFace dataset: `vaquill/open-india-law` (composed of 75 massive `.parquet` files covering Central, State/UT legislation, regulations, and High Court / Supreme Court judgments).

### Domain Mapping Config:
* [`config/domain_mapping.json`](file:///d:/Full%20Stack/BetterCallSaul/config/domain_mapping.json): Maps keyword rules to categorize scanned statutes and judgments into 15 layman-relevant legal domains (e.g. Consumer Protection, Employment & Labour, Workplace Rights, Contracts & Agreements, Property Law, Family Law, Cyber Law, Company Law, etc.).

### Ingestion Script Architectures & Optimizations:
We implemented the script at [`scripts/acquire_open_india_law.py`](file:///d:/Full%20Stack/BetterCallSaul/scripts/acquire_open_india_law.py). To handle the massive dataset (50GB+ compressed Parquet source) safely in a local consumer environment, we incorporated several key optimizations:

1. **Download-Process-Delete Pipeline:** Instead of keeping files permanently, the script downloads the source Parquet file to a temporary project directory, processes and filters it, uploads the result, and immediately deletes the temporary Parquet. **Permanent local disk footprint is 0 MB**.
2. **Memory-Optimized Row-Group Sequential Processing:** To avoid `ArrowMemoryError` on massive files (e.g., the 4.56 GB compressed Kerala judgments file which decompresses to 30GB+ in RAM), the script opens the Parquet locally and reads it sequentially row-group by row-group (~20k–50k rows at a time). This keeps system RAM usage **under 200MB**.
3. **On-the-Fly Gzip Compression (`.jsonl.gz`):** Outputs are written directly to Gzip files. This shrinks the text size by **90%** (e.g. compressing a 700MB JSONL text file to ~70MB), resolving slow upload bottlenecks caused by ISP upload speed limits.
4. **Google Drive Checkpointing & Manifest Resuming:** 
   * The script automatically downloads any existing `manifest.json` from the Google Drive target root (`BetterCallSaul Dataset`) at startup to learn which files have already completed.
   * If a file already exists on Google Drive (as `.jsonl` or `.jsonl.gz`), it outputs `[SKIP]` and moves on.
   * Checkpoint states (manifest and markdown reports) are updated and uploaded back to Google Drive after *every* file finishes processing, making the script safe to run overnight or restart after network crashes.
   * Google Drive API requests are wrapped with `num_retries=5` to survive transient network drops or SSL protocol resets.

### Phase 1A Run Results:
* **Total original records scanned:** **19,892,378**
* **Total domain-filtered records retained:** **15,745,223**
* **Total upload storage size on Google Drive:** **28,761.67 MB** (~28.7 GB compressed Gzip files).
* Target states processed: All states up to Puducherry, plus custom targeted runs for `in_state-gst_regulations`, `in_tamil-nadu_legislation`, `in_supreme-court_judgments`, and `in_trai_regulations`.

---

## 4. Current State & Next Steps (Phase 1B)
We are now ready to begin **Phase 1B: Database Ingestion Pipeline** to load these filtered cloud datasets into the local PostgreSQL database.

### Hardware Profile:
* CPU: Intel i5-14400F (10 Cores / 16 Threads)
* RAM: 32 GB DDR5
* GPU: NVIDIA GeForce RTX 5060 (8 GB VRAM)
* OS: Windows

### Phase 1B Objectives & Considerations:
* **GPU Embedding Acceleration:** Using the RTX 5060, PyTorch can process embeddings on VRAM utilizing CUDA instead of the CPU. This will speed up embeddings computation by **50x** (calculating 15.7M embeddings in roughly **2.5 to 3 hours**).
* **Storage Footprint in PostgreSQL:** Storing 15.7M chunks (raw text + 384-dimensional float vector embeddings + HNSW cosine index structures) will occupy about **35 GB to 40 GB** of space in PostgreSQL.
* **Batch Upsert Optimization:** We need to modify `src/db.py` to use bulk copy/batch transaction inserts instead of single row inserts to prevent the SQL database from bottlenecking.
* **Restartability:** The loader must check for existing `chunk_id` in the database before calculating embeddings to ensure it can resume safely if interrupted.
