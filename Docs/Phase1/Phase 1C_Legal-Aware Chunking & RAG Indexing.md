# Phase 1C: Legal-Aware Chunking & RAG Indexing Specification

**Project:** Legal Awareness AI / Agentic RAG
**Phase:** 1C — Chunking Strategy, Metadata Enrichment, Embedding Generation, Vector and Lexical Indexing
**Status:** Specification (implementation to be carried out separately by Antigravity)

---

## 1. Objective

The objective of Phase 1C is to take the normalized legal corpus produced in Phase 1B and design a **highly optimized, legal-aware chunking and indexing strategy** for the downstream RAG pipeline.

Specifically:
* Design specialized chunking algorithms for **legislation** (Acts, Rules, Regulations) and **judicial precedents** (Judgments).
* Enrich chunks with hierarchical parent metadata to prevent context loss.
* Generate dense vector embeddings using `all-MiniLM-L6-v2`.
* Populate the local PostgreSQL `bettercallsaul` database `chunks` table with `pgvector`.
* Build local sparse BM25 indices to enable hybrid search.

---

## 2. Legal-Aware Chunking Strategy

Standard character-count or token-count splitting (e.g., splitting every 500 characters blindly) destroys legal meaning by breaking apart section titles, definitions, and specific sub-clauses. We will use two distinct chunking strategies:

### A. Legislation/Statute Chunking
Legislation is highly structured. We must chunk by **logical sections**:
1. **Chunk Boundaries**: Identify sections using patterns like `Section X:`, `Sec. X.`, or equivalent paragraph transitions.
2. **Context Prepending**: Every chunk must prepend parent context to ensure the embedding captures the full scope:
   * Format: `[Act: {Act Title}] [Chapter: {Chapter Title}] [Section: {Section Number/Title}] \n {Section Content}`
3. **Overlapping**: Sections that are longer than the model limit (e.g., 512 tokens) should be subdivided using sentence-boundary splits with a 10% sentence overlap, retaining the prepended context in each sub-chunk.

### B. Judicial Precedents (Judgments) Chunking
Judgments are narrative and can be very long (hundreds of pages).
1. **Chunk Boundaries**: Chunk by paragraph boundaries (`\n\n`) rather than character counts.
2. **Context Prepending**: Prepend the case details:
   * Format: `[Case: {Case Name}] [Court: {Court Name}] [Date: {Judgment Date}] \n {Paragraph Content}`
3. **Size Constraints**: Target chunk size: **250 to 500 tokens**. Merge small consecutive paragraphs together until the target size is reached, ensuring paragraphs aren't split mid-sentence.

---

## 3. Metadata Enrichment

To support filtered retrieval (e.g., searching only within state-level laws of a specific state, or sorting by recent precedents), every chunk must retain the following metadata fields:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "document_type": "legislation | judgment",
  "title": "...",
  "page_number": 0,
  "jurisdiction": "central | state | union_territory",
  "state": "...",
  "court": "...",
  "domain": [],
  "date": "YYYY-MM-DD",
  "authority": "..."
}
```

This metadata will be written to the `metadata` JSONB column in the `chunks` table of the PostgreSQL database.

---

## 4. Dense Vector Indexing (pgvector)

1. **Embedding Model**: Use the configured local SentenceTransformer model `all-MiniLM-L6-v2` (384 dimensions).
2. **Hardware Acceleration**: Enable CUDA automatically (`device = "cuda" if torch.cuda.is_available() else "cpu"`) to accelerate embedding generation.
3. **Database Schema**:
   * Insert records into the `chunks` table:
     * `document_id`: link to parent document ID in the `documents` table.
     * `page_number`: page or paragraph sequence index.
     * `content`: full text chunk (with prepended context).
     * `embedding`: 384-dimensional vector.
     * `metadata`: JSONB metadata payload.
4. **Vector Search Index**: Build an HNSW index on the `embedding` column for fast cosine distance matching:
   ```sql
   CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx 
   ON chunks USING hnsw (embedding vector_cosine_ops);
   ```

---

## 5. Sparse Lexical Indexing (BM25)

Dense vectors are great at semantic matching but poor at retrieving specific keyword terms (like specific Act sections, numeric codes, or rare named entities). 
1. **Model**: Use `rank_bm25` (already installed in the environment).
2. **Indexing**: 
   * Tokenize and normalize the text chunks (lowercasing, stopword removal, stemming).
   * Fit the BM25 model on the entire corpus of chunk tokens.
   * Save the fitted BM25 model and the mapping of indices to local disk (e.g., as a pickle file `config/bm25_index.pkl`) for fast loading by the FastAPI server.

---

## 6. Pipeline Resumability & Memory Management

Because the normalized corpus contains millions of records, the chunking and indexing script must be:
* **Batch-Driven**: Read the normalized corpus files in chunks, generate embeddings in batches (e.g., batch size 64 or 128), and bulk-insert into PostgreSQL.
* **Checkpointed**: Track which files have been successfully chunked and indexed. If the process is killed, it must resume without duplicating entries.
* **Transaction Safe**: Use PostgreSQL bulk insert transactions to avoid database corruption or partial inserts.

---

## 7. Definition of Done

Phase 1C is complete when:
- [ ] Legal-aware chunking rules are implemented for legislation and judgments.
- [ ] Parents' context is prepended to chunks to preserve search relevance.
- [ ] A batch embedding script is developed using `all-MiniLM-L6-v2`.
- [ ] Database bulk-insertion is fully operational.
- [ ] HNSW index is created on the `chunks` table.
- [ ] BM25 index is generated and saved to disk.
- [ ] Verification script queries both vector search and BM25 and combines results (hybrid search baseline).
- [ ] Execution statistics are generated.
