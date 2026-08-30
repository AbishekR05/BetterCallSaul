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

---

## 📁 Project Structure

```
BetterCallSaul/
├── benchmark/
│   └── phase_2_1/              # Embedding benchmark data, samples, and reports
│       ├── PHASE_2_1_BENCHMARK_REPORT.md
│       ├── eval_queries.jsonl
│       ├── relevance_judgments.jsonl
│       └── sampled_chunks.parquet
├── config/
│   └── domain_mapping.json     # Rule mapping for layman-relevant domains
├── Data/
│   └── Raw/
│       └── Consumer/           # Local PDF documents (acts/rules)
├── Docs/                       # Comprehensive specifications and reports
│   ├── PHASE_1B_REPORT.md
│   ├── PHASE_1C_REPORT.md
│   ├── Phase1/                 # Phase 1.x detailed analysis
│   └── Phase2/                 # Phase 2.x embedding & retrieval evaluations
├── scripts/                    # Ingestion, processing, and benchmarking scripts
│   ├── acquire_open_india_law.py # Resilient data scraping & GDrive backup
│   ├── normalize_corpus.py     # Cleansing & domain inspection
│   ├── chunk_corpus.py         # Structure-aware chunking pipeline
│   ├── draw_sample.py          # Stratified sampling for evaluation
│   └── benchmark_embeddings.py # GPU-based embedding benchmarking
├── src/                        # Core Application Source Code
│   ├── app.py                  # FastAPI server endpoints
│   ├── config.py               # Environment configuration settings
│   ├── db.py                   # DB connection, tables setup, pgvector schema
│   ├── generator.py            # LLM interface (Gemini/Ollama/HF) & citations
│   ├── ingestion.py            # Document parsing (PyMuPDF) and initial loading
│   └── retrieval.py            # Hybrid Search (FTS + Vector) via RRF
├── .env.example                # Env template file
├── .gitignore                  # Git ignore patterns
├── install_pgvector.ps1        # Helper to build/install pgvector on Windows
├── requirements.txt            # Python requirements
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
