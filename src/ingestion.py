# src/ingestion.py
import fitz  # PyMuPDF
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
from src.config import RAW_DATA_DIR, EMBEDDING_MODEL_NAME
from src.db import get_db_connection

# Load local embedding model (cached automatically in ~/.cache/huggingface/sentence_transformers)
print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}'...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
print("Embedding model loaded.")

def chunk_text(text, chunk_size=800, chunk_overlap=150):
    """Splits text into chunks of chunk_size characters with overlap, breaking on spaces."""
    if not text or not text.strip():
        return []
        
    chunks = []
    text = text.replace('\r', ' ').replace('\n', ' ')
    # Clean multiple spaces
    text = ' '.join(text.split())
    
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
            
        # Try to find a space near the end to split nicely
        space_idx = text.rfind(' ', start + chunk_size - 100, end)
        if space_idx != -1 and space_idx > start:
            end = space_idx
            
        chunks.append(text[start:end].strip())
        start = end - chunk_overlap
        
    return [c for c in chunks if len(c) > 20] # Filter very small chunks

def ingest_pdf(pdf_path):
    """Extracts text from a PDF, chunks it, computes embeddings, and stores in the database."""
    pdf_path = Path(pdf_path)
    filename = pdf_path.name
    print(f"\nProcessing: {filename}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if already ingested
        cur.execute("SELECT id FROM documents WHERE filename = %s", (filename,))
        row = cur.fetchone()
        if row:
            print(f"Document {filename} is already ingested (ID: {row[0]}). Skipping.")
            conn.close()
            return row[0]
            
        # Extract title or default to filename
        doc = fitz.open(pdf_path)
        title = doc.metadata.get('title') or filename
        
        # Insert document record
        cur.execute(
            "INSERT INTO documents (filename, title) VALUES (%s, %s) RETURNING id",
            (filename, title)
        )
        document_id = cur.fetchone()[0]
        
        all_chunks_to_insert = []
        
        # Process page by page
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Chunk the page text
            page_chunks = chunk_text(text)
            
            if not page_chunks:
                continue
                
            # Create embeddings for this page's chunks
            embeddings = embedding_model.encode(page_chunks, show_progress_bar=False)
            
            for chunk_idx, (content, embedding) in enumerate(zip(page_chunks, embeddings)):
                metadata = {
                    "source": filename,
                    "page": page_num + 1,
                    "chunk_index": chunk_idx
                }
                import json
                all_chunks_to_insert.append((
                    document_id,
                    page_num + 1,
                    content,
                    embedding.tolist(), # Convert numpy array to list for pgvector
                    json.dumps(metadata)
                ))
                
        # Batch insert chunks
        if all_chunks_to_insert:
            cur.executemany(
                "INSERT INTO chunks (document_id, page_number, content, embedding, metadata) VALUES (%s, %s, %s, %s, %s)",
                all_chunks_to_insert
            )
            conn.commit()
            print(f"Successfully ingested {len(all_chunks_to_insert)} chunks from {len(doc)} pages.")
        else:
            print("No text chunks found to ingest.")
            
        conn.close()
        return document_id
        
    except Exception as e:
        print(f"Error during ingestion of {filename}: {e}")
        return None

def ingest_all_raw_documents():
    """Scan RAW_DATA_DIR and ingest all PDFs."""
    if not RAW_DATA_DIR.exists():
        print(f"Directory {RAW_DATA_DIR} does not exist.")
        return
        
    pdf_files = list(RAW_DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF documents found in {RAW_DATA_DIR}")
        return
        
    print(f"Found {len(pdf_files)} PDF(s) to process.")
    for pdf_file in pdf_files:
        ingest_pdf(pdf_file)
    print("Ingestion task complete.")
