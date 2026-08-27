# BetterCallSaul: Preventive Legal Awareness Agent

BetterCallSaul is a source-grounded **Legal Awareness AI assistant** built to help ordinary people understand relevant legal constraints and options *before* they invest time, money, or effort into potentially regulated actions. 

Rather than focusing only on retroactive legal help (remedies after a dispute), this system prioritizes **preventive legal awareness** (e.g., verifying if online firework sales are regulated before building an e-commerce platform).

---

## 🌟 Key Features

1. **Grounded Legal QA:** RAG answers are generated strictly using authoritative sources (such as Consumer Protection Acts and Rules).
2. **Hybrid Search Retrieval:** Combines dense semantic vector search (`pgvector`) with sparse lexical matching (PostgreSQL Full-Text `tsvector`) fused together using **Reciprocal Rank Fusion (RRF)**.
3. **Traceable Citations:** The model cites precise source documents and page numbers for auditability.
4. **Local LLM & API Fallback Support:** Integrates with local Ollama instances, local HuggingFace `transformers` models running on GPU/CUDA, or cloud API endpoints (like Gemini 3.5 Flash).
5. **REST API Interface:** Built with FastAPI, containing endpoints to trigger document ingestion and run cited queries.

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

## 📁 Project Structure

```
BetterCallSaul/
├── Data/
│   └── Raw/
│       └── Consumer/       # Consumer Protection PDFs (2019, 2021, 2023)
├── Docs/
│   └── legal_awareness_agent_project_context.md
├── src/
│   ├── config.py         # Configs (Paths, DB connections, Models)
│   ├── db.py             # Postgres pgvector schema setup & table migrations
│   ├── ingestion.py      # PDF parsing via PyMuPDF, chunking, and embedding creation
│   ├── retrieval.py      # Lexical + Semantic search with RRF ranking
│   ├── generator.py      # Prompt construction and LLM interface (API & local HF)
│   └── app.py            # FastAPI endpoints
├── .env.example          # Environment variables template
├── .gitignore            # Git exclusions (protects local .env files)
├── install_pgvector.ps1  # Precompiled pgvector helper installation script for Windows
├── requirements.txt      # Python package requirements
├── main.py               # CLI entrypoint (init, ingest, query, serve)
└── README.md             # Project documentation
```

---

## ⚙️ Quick Start Setup

### Prerequisites
*   **Python:** Version 3.11+
*   **PostgreSQL:** Version 16+ running locally on port 5432.
*   **GPU Support:** CUDA-enabled GPU (e.g. GTX 1650 or higher) for fast local embeddings.

### 1. Clone & Set Up Directory
Ensure you are in the workspace root:
```bash
git clone https://github.com/AbishekR05/BetterCallSaul.git
cd BetterCallSaul
```

### 2. Install pgvector for local PostgreSQL 18 (Windows)
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
Initialize database tables and ingest the raw PDF documents:
```bash
# Set up pgvector extension, create tables, and construct HNSW indexes
python main.py init

# Parse, chunk, embed, and index Consumer Protection PDFs
python main.py ingest
```

### 5. Running Queries
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

## 🧠 Ingestion & Grounding Details

*   **PDF Extraction:** Extracted page-by-page using PyMuPDF.
*   **Text Chunking:** Cleaned and partitioned into overlapping chunks of 800 characters with 150 characters overlap.
*   **Embedding Model:** Chunks embedded locally with `all-MiniLM-L6-v2` (384 dimensions) and stored in the database.
*   **Verification:** Verified RAG performance on the Indian Consumer Protection Acts, producing highly grounded answers with precise source page number citations (e.g. `[a2019-35.pdf, Page 33]`).
