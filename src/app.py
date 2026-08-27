# src/app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from src.db import init_db, get_db_connection
from src.ingestion import ingest_all_raw_documents
from src.retrieval import hybrid_retrieval
from src.generator import generate_rag_response
from src.config import DB_NAME, EMBEDDING_MODEL_NAME, LLM_PROVIDER

app = FastAPI(
    title="BetterCallSaul - Legal Awareness RAG API",
    description="A simple grounded RAG API using PyMuPDF, pgvector, and local/remote LLMs.",
    version="1.0.0"
)

# Startup event to ensure database tables are initialized
@app.on_event("startup")
def startup_event():
    print("Starting up Legal Awareness RAG API...")
    try:
        init_db()
    except Exception as e:
        print(f"Database initialization failed on startup: {e}")

class QueryRequest(BaseModel):
    query: str
    limit: int = 4

class Citation(BaseModel):
    citation_key: str
    source: str
    page_number: int

class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]

@app.get("/")
def read_root():
    # Check DB status
    db_connected = False
    try:
        conn = get_db_connection()
        conn.close()
        db_connected = True
    except Exception:
        pass
        
    return {
        "status": "online",
        "database": {
            "name": DB_NAME,
            "connected": db_connected
        },
        "embedding_model": EMBEDDING_MODEL_NAME,
        "llm_provider": LLM_PROVIDER
    }

@app.post("/ingest", status_code=200)
def trigger_ingestion():
    """Trigger ingestion of all PDFs inside Data/Raw/Consumer directory."""
    try:
        ingest_all_raw_documents()
        return {"status": "success", "message": "Raw PDF documents ingestion process triggered."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    """Retrieve relevant legal chunks and generate a grounded cited answer."""
    try:
        # 1. Retrieve top context chunks
        chunks = hybrid_retrieval(request.query, limit=request.limit)
        
        if not chunks:
            return {
                "query": request.query,
                "answer": "No relevant documents found. Please ensure files are ingested.",
                "citations": []
            }
            
        # 2. Generate answer
        result = generate_rag_response(request.query, chunks)
        
        return {
            "query": request.query,
            "answer": result["answer"],
            "citations": result["citations"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
