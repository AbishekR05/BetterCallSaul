# BetterCallSaul: Preventive Legal Awareness Agent

BetterCallSaul is a source-grounded **Preventive Legal Awareness AI assistant** built to help ordinary citizens understand relevant legal constraints, regulations, and liabilities *before* they invest time, money, or effort into potentially regulated actions. 

Rather than focusing solely on retroactive legal help (remedies after a dispute), this system prioritizes **preventive legal awareness** (e.g., verifying if online firework sales are regulated before building an e-commerce platform, or understanding employee rights and contract liabilities prior to signing agreements).

---

## 🌟 Key Features

1. **Grounded Legal QA:** RAG answers are generated strictly using authoritative sources (such as Consumer Protection Acts, central/state legislation, and judgments).
2. **Hybrid Search Retrieval:** Combines dense semantic vector search (`pgvector`) with sparse lexical matching (PostgreSQL Full-Text Search `tsvector`) fused together using **Reciprocal Rank Fusion (RRF)**.
3. **Traceable Citations:** The model cites precise source documents, sections, or page numbers for auditability.
4. **Multi-LLM Engine:** Integrates with local Ollama instances, local HuggingFace `transformers` models running on GPU/CUDA, or cloud API endpoints (like Gemini 3.5 Flash).
5. **FastAPI Web Server:** Backend containing REST endpoints to trigger document ingestion and run cited queries.
6. **Resilient Data Processing:** Highly optimized ingestion pipelines designed to handle massive datasets (50GB+) on consumer-grade hardware.

---

## 🏗️ System Architecture

```
                       [ User Query ]
                             │
                             ▼
                    [ Hybrid Retriever ]
                   /                    \
                  ▼                      ▼
          [ Vector Search ]      [ Keyword Search ]
             (pgvector)             (Postgres FTS)
                  \                      /
                   ▼                    ▼
                 [ Reciprocal Rank Fusion ] (RRF)
                             │
                             ▼
                  [ Top K Context Chunks ]
                             │
                             ▼
                     [ LLM Generator ]
               (Gemini / Ollama / Local HF)
                             │
                             ▼
              [ Grounded Answer + Citations ]
```

---

## 📅 Roadmap & Implementation Phases

The project is structured into progressive phases to move from a small-scale prototype to a production-grade, nation-scale legal database.

### 🔹 Phase 0: RAG V0 Baseline (Completed)
- Built a modular local RAG prototype.
- **Database:** PostgreSQL with `pgvector`.
- **Embeddings:** Local SentenceTransformers `all-MiniLM-L6-v2` (384 dimensions).
- **LLM Engine:** Remote Gemini API (`gemini-3.5-flash`) with strict inline citation prompting.
- Exposed backend endpoints via FastAPI and a unified CLI.

### 🔹 Phase 1A: Legal Dataset Acquisition (Completed)
- Built a resilient pipeline to filter and download records from the gated HuggingFace dataset `vaquill/open-india-law` (50GB+ raw Parquet data).
- Categorized legislation and judgments into **15 layman-relevant legal domains** using rule-based keywords (e.g., Consumer Protection, Property Law, Cyber Law, Contracts).
- Implemented optimizations for running on consumer hardware:
  - *Download-Process-Delete pipeline* to maintain a 0 MB permanent disk footprint.
  - *Row-Group Sequential Processing* to keep system RAM under 200MB.
  - *On-the-fly Gzip compression* (`.jsonl.gz`) to reduce network transit sizes by 90%.
  - *Checkpointing & resumption* via Google Drive API to resist network drops.
- **Acquired:** **15,745,223 filtered records** (~28.7 GB compressed Gzip files).

### 🔹 Phase 1B: Corpus Inspection & Normalization (Completed)
- Audited text quality across all downloaded files:
  - Removed 92 duplicate records, leaving **15,747,195 clean records**.
  - Audited short/empty documents.
- Mapped full domain distributions (e.g., Constitutional Rights, Criminal Law, Environmental Law, Taxation, and Consumer Protection).

### 🔹 Phase 1C: Legal-Aware Chunking & Indexing (Completed)
- Designed a structure-aware legal chunking pipeline to partition documents based on their layout types:
  - **Legislation:** Partitioned cleanly by sections/sub-sections.
  - **Judgments:** Split based on semantic paragraphs and court arguments.
- Prevented memory bloat and upload timeouts using a **partition-based streaming Parquet writer** (`chunk_corpus.py`).

### 🔹 Phase 2.1: Embedding Selection Benchmark (Completed)
Evaluated 4 candidate embedding models on a stratified sample of 1,000 chunks (500 Legislation + 500 Judgments) using local GPU acceleration (**NVIDIA RTX 5060, 8 GB VRAM**).

| Model | Dimensions | Recall@5 | Recall@10 | Precision@5 | Precision@10 | MRR | Throughput (c/s) | Peak VRAM | Est. Ingestion Time (15.7M) | Projected DB Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `InLegalBERT-2` | 768 | 0.1667 | 0.2292 | 0.0333 | 0.0229 | 0.1195 | 80.9 c/s | 1.59 GB | ~54.09 hours | 80.0 GB |
| **`bge-base-en-v1.5`** | **768** | **0.7708** | **0.7917** | **0.1542** | **0.0792** | **0.6615** | **79.3 c/s** | **2.00 GB** | **~55.17 hours** | **80.0 GB** |
| `bge-large-en-v1.5` | 1024 | 0.6250 | 0.7500 | 0.1250 | 0.0750 | 0.5736 | 25.6 c/s | 2.86 GB | ~170.97 hours | 106.7 GB |
| `all-MiniLM-L6-v2` | 384 | 0.5208 | 0.5833 | 0.1042 | 0.0583 | 0.4403 | 760.4 c/s | 2.76 GB | ~5.75 hours | 40.0 GB |

* **Final Recommendation:** **`BAAI/bge-base-en-v1.5`** is recommended for production. It achieves the highest **MRR (0.6615)** and **Recall@10 (0.7917)** on legal queries with a highly viable indexing footprint.

### 🔹 Phase 2.2: Vector Index Construction & Production Ingestion (Completed)
- Designed a production-grade, resumable, manifest-gated batch embedding and ingestion pipeline (`src/db_phase2.py`, `scripts/build_vector_index.py`, `scripts/run_production_indexing.py`).
- Utilized PostgreSQL `COPY`-based bulk insertion with deferred HNSW index construction (`m=16`, `ef_construction=64`) on `bge-base-en-v1.5` (768-dim) vectors.
- Achieved **~510 chunks/sec COPY throughput** on local GPU (`NVIDIA RTX 5060`).

### 🔹 Phase 2.3: Read-Only Modular Hybrid Retrieval Pipeline (Completed)
- Implemented a clean, read-only retrieval engine (`src/retrieval/retriever.py`) separating vector search, filtering, and candidate deduplication.
- Enforced query-side BGE instruction prefixing (`"Represent this sentence for searching relevant passages: "`) and structured legal provenance tracking.

### 🔹 Phase 2.4: Open-World Retrieval Evaluation Framework (Completed)
- Constructed a 160-query open-world legal evaluation dataset (`eval/queries/p24_queries_v1.jsonl`) and non-circular human-audited ground truth judgments (`ground_truth_v1_audited.jsonl`).
- Built dual evaluation modes: closed-world regression harness and open-world production evaluation (`eval/harness.py`, `eval/metrics.py`, `scripts/audit_phase2_4_framework.py`).

### 🔹 Phase 2.5: Modular Retrieval Optimization Suite (Completed)
Implemented and benchmarked 5 experimental retrieval optimizations using pluggable `RetrieverAdapter` modules (`src/retrieval/`):
1. **Full-Text BM25 Lexical Search (`lexical.py`):** High-performance 2-stage PostgreSQL cover-density search (<20ms query latency).
2. **Hybrid Candidate Fusion (`fusion.py`):** Reciprocal Rank Fusion (RRF $k=60$) & Min-Max Weighted Score Fusion.
3. **Cross-Encoder Reranking (`reranker.py`):** Deep logit re-ranking via `BAAI/bge-reranker-base` on CUDA GPU (~1.5s per query).
4. **Confidence Calibration (`confidence.py`):** Empirical score thresholding suppressing false confidence on out-of-scope queries (0.0% false confidence rate).
5. **Jurisdiction Boosting (`jurisdiction_filter.py`):** Soft multiplicative score boosting (1.15x) for central vs. state statutory alignment.

---

## 📁 Project Structure

```
BetterCallSaul/
├── benchmark/                  # Benchmark datasets, reports, and run logs
│   ├── phase_2_1/              # Phase 2.1 embedding selection benchmark
│   ├── phase_2_2/              # Phase 2.2 vector ingestion & 50k benchmark reports
│   ├── phase_2_3/              # Phase 2.3 retrieval pipeline audit reports
│   ├── phase_2_4/              # Phase 2.4 evaluation framework & open-world baseline
│   └── phase_2_5/              # Phase 2.5 retrieval optimization suite report & results
├── config/                     # Domain mappings & environment configs
│   └── domain_mapping.json     # Rule mapping for layman-relevant domains
├── configs/                    # Experiment configuration files
│   ├── p24_open_world_baseline.yaml
│   └── p24_regression.yaml
├── Data/                       # Local data directories
├── Docs/                       # Comprehensive specifications and phase reports
│   ├── Phase1/                 # Phase 1.x detailed analysis
│   └── Phase2/                 # Phase 2.1 - 2.5 technical specifications & specs
├── eval/                       # Phase 2.4 & 2.5 Evaluation Framework
│   ├── annotation_tool.py      # Ground-truth annotation assistant
│   ├── harness.py              # Evaluation runner & adapter executor
│   ├── metrics.py              # Precision, Recall, MRR, nDCG, hit rate metrics
│   ├── pooling.py              # Candidate pooling & depth sampling
│   ├── report_builder.py       # Evaluation markdown report generator
│   ├── run.py                  # Evaluation CLI entrypoint
│   └── schemas.py              # Evaluation schemas & data classes
├── scripts/                    # Ingestion, processing, evaluation, and pipeline scripts
│   ├── build_vector_index.py   # Vector table initialization & HNSW creation
│   ├── run_production_indexing.py # Background batch embedding & COPY ingestion
│   ├── audit_phase2_4_framework.py # Framework audit script
│   ├── run_audited_open_world_eval.py # Open-world evaluation runner
│   └── run_p25_experiments.py  # Phase 2.5 optimization experiment runner
├── src/                        # Core Application Source Code
│   ├── db_phase2.py            # Normalized Phase 2 PostgreSQL schema & COPY helpers
│   ├── retrieval/              # Modular Retrieval Engine (Phase 2.3 - 2.5)
│   │   ├── adapters.py         # Pluggable RetrieverAdapter registry
│   │   ├── candidate_pool.py   # Candidate merging & provenance tracking
│   │   ├── confidence.py       # Empirical confidence calibrator
│   │   ├── config.py           # Retrieval configuration settings
│   │   ├── embedding.py        # BGE embedding provider & query prefixing
│   │   ├── filters.py          # Metadata & structured filtering
│   │   ├── fusion.py           # RRF & Min-Max Weighted fusion
│   │   ├── jurisdiction_filter.py # Soft jurisdiction score booster
│   │   ├── lexical.py          # PostgreSQL BM25 Cover-Density FTS engine
│   │   ├── reranker.py         # BAAI/bge-reranker-base Cross-Encoder
│   │   ├── retriever.py        # Frozen Baseline Retriever
│   │   └── search.py           # Low-level pgvector similarity search
│   ├── app.py                  # FastAPI server endpoints
│   ├── config.py               # Application configuration
│   └── generator.py            # LLM interface (Gemini/Ollama/HF) & citations
├── tests/                      # Unit & Functional Test Suite
│   ├── eval/                   # Metrics & harness unit tests
│   ├── retrieval/              # Retrieval module unit tests
│   └── run_all_tests.py        # Unified test suite runner
├── .env.example                # Env template file
├── .gitignore                  # Git ignore patterns
├── requirements.txt            # Python dependencies
├── main.py                     # Entrypoint CLI
└── README.md                   # Project Documentation
```

---

## ⚙️ Quick Start Setup

### Prerequisites
* **Python:** Version 3.11+
* **PostgreSQL:** Version 16+ running locally on port 5432.
* **GPU Support:** CUDA-enabled GPU for fast local embeddings (highly recommended).

### 1. Clone & Set Up Directory
```bash
git clone https://github.com/AbishekR05/BetterCallSaul.git
cd BetterCallSaul
```

### 2. Install pgvector for local PostgreSQL (Windows)
Open a **PowerShell terminal as Administrator** and execute:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; .\install_pgvector.ps1
```

### 3. Environment Configurations
Rename `.env.example` to `.env` and configure your credentials:
```ini
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bettercallsaul
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here

GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Initialize Database & Run Ingestion
Initialize database tables and ingest the raw local PDF documents:
```bash
# Set up pgvector extension, create tables, and construct HNSW indexes
python main.py init

# Parse, chunk, embed, and index Consumer Protection PDFs
python main.py ingest
```

### 5. Running Queries (CLI & Server)
Query the RAG pipeline directly via CLI:
```bash
python main.py query "What is the penalty for false or misleading advertisements?"
```

Start the FastAPI backend server:
```bash
python main.py serve
```
Visit `http://127.0.0.1:8000/docs` to test endpoints via Swagger UI.

---

## 🧪 Running Phase 2.1 Embedding Benchmark

To execute or verify the embedding model selection benchmark:
1. **Draw a Stratified Sample:**
   ```bash
   python scripts/draw_sample.py
   ```
2. **Execute Benchmark Harness:**
   ```bash
   python scripts/benchmark_embeddings.py
   ```
   *Note: This script will download/load the 4 candidate models onto your CUDA GPU sequentially, calculate embedding representations, and compute Recall, Precision, MRR, Throughput, and VRAM consumption.*
