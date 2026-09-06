# Project Context

We are building a **Legal Awareness AI / Agentic RAG system for Indian law** ("Better Call Saul").

Prior phases:

* **Phase 1A (complete):** Acquired ~15.7 million filtered records (~28.8 GB) from the `vaquill/open-india-law` HuggingFace dataset, checkpointed to Google Drive.
* **Phase 1B (complete/near-complete):** Corpus inspection, normalization, schema/domain/jurisdiction classification, deduplication.
* **Phase 1C (complete/near-complete):** Legal-aware, structure-preserving chunking into a Parquet-based chunked corpus (`03_chunked/legislation/`, `03_chunked/judgments/`, `03_chunked/other/`), partitioned in batch files, with rich per-chunk metadata (chunk_id, document_id, parent_id, source_type, domain, jurisdiction, level, state, court, act/chapter/part/section/subsection/clause, case_name, citation, paragraph_number, date, effective_date, source_url, dataset_version, is_historical, etc.). Current corpus scale used for projections: **15,747,195 chunks**.
* **Phase 2.1 (complete):** Benchmarked 4 candidate embedding models on a stratified sample against a 48-query layman evaluation set. Result documented in `PHASE_2_1_BENCHMARK_REPORT.md`:

  | Model | Dim | Recall@10 | MRR | Throughput (c/s) | Peak VRAM | Est. Full Embed Time | Projected DB Size |
  |---|---|---|---|---|---|---|---|
  | `BAAI/bge-base-en-v1.5` | 768 | 0.7917 | 0.6615 | 79.3 | 2.00 GB | 55.17 hrs | 80.0 GB |

  **`BAAI/bge-base-en-v1.5` was selected** — highest MRR and Recall@10 among all candidates, with a feasible VRAM footprint and embedding time. This spec takes that decision as a settled input; it does not re-litigate model choice.

  Note for Antigravity: `bge-base-en-v1.5` requires the query-side instruction prefix `"Represent this sentence for searching relevant passages: "` at **query time only** (not for passages/chunks being indexed). This must be applied consistently at retrieval time in later phases; it does not affect this indexing phase directly but must be documented in the schema/config so it is not lost.

Hardware profile:

* CPU: Intel i5-14400F (10 Cores / 16 Threads)
* RAM: 32 GB DDR5
* GPU: NVIDIA GeForce RTX 5060 (**8 GB VRAM**)
* OS: Windows
* Local PostgreSQL with a configured tablespace on the project drive (`d:/Abishek/pg_tablespace`, per Phase 2.1 report)

---

# Phase 2.2 Objective

> **Build a production-style, resumable, incremental pipeline that embeds the full Phase 1C chunked corpus with `bge-base-en-v1.5` and loads the resulting vectors, chunk text, and legal metadata into PostgreSQL + pgvector — validated first on a small pilot subset, with the full 15M+ run executed only as an explicit, manual, separate step.**

This phase produces infrastructure and a validated pilot. It does **not** produce the final RAG retriever, reranker, agent, or answer-generation chain.

---

# High-Level Architecture

```text
                 Phase 1C
         Chunked Corpus (Parquet, batch files)
         legislation/ | judgments/ | other/
                     │
                     ▼
          ┌───────────────────────┐
          │  Phase 2.2 Indexer    │
          │  (incremental reader) │
          └──────────┬────────────┘
                     │
         read completed batch (manifest-gated)
                     │
                     ▼
          ┌───────────────────────┐
          │  Embedding Stage      │
          │  bge-base-en-v1.5     │
          │  RTX 5060, batched    │
          └──────────┬────────────┘
                     │
              (chunk_id, vector[768], metadata)
                     │
                     ▼
          ┌───────────────────────┐
          │  Bulk Load Stage      │
          │  COPY / batched INSERT│
          │  PostgreSQL + pgvector│
          └──────────┬────────────┘
                     │
                     ▼
          ┌───────────────────────┐
          │  Checkpoint/Manifest  │
          │  mark batch = indexed │
          └───────────────────────┘
```

Phase 1B/1C may still be running while this pipeline operates. The indexer is a **third stage** in the existing producer/consumer chain established in Phase 1C (Phase 1B → Phase 1C → Phase 2.2), and must follow the same completion-gating discipline: never read a Phase 1C batch file that is not marked complete in the Phase 1C manifest.

---

# 1. Incremental Reading of the Phase 1C Chunked Corpus

* The indexer reads the Phase 1C manifest/checkpoint system (established in Phase 1C) to discover chunk batch files (`legislation/batch_XXXX.parquet`, `judgments/batch_XXXX.parquet`, `other/batch_XXXX.parquet`) marked complete.
* Maintain a **separate Phase 2.2 manifest** (do not overload the Phase 1C manifest) tracking, per batch file: `phase_1c_status`, `phase_2_2_embedding_status` (`pending` / `embedding` / `embedded` / `failed`), `phase_2_2_load_status` (`pending` / `loading` / `loaded` / `failed`), row counts, timestamps, and error messages on failure.
* Never read a batch file mid-write. Rely on Phase 1C's atomic-write convention (`.tmp` → final `.parquet` → manifest `COMPLETE`) — the same discipline already specified in Phase 1C.
* Process batch files in a **stable, deterministic order** (e.g. sorted by filename) so restart behavior is predictable.
* Within a batch file, stream rows in row-group chunks (do not load an entire multi-hundred-MB batch file fully into a single in-memory structure larger than necessary — read via PyArrow row-group iteration or fixed-size pandas chunks, consistent with the memory-conscious approach already used in Phase 1A/1B).

---

# 2. Embedding Generation with `bge-base-en-v1.5` on the RTX 5060

* Use `sentence-transformers` (or the HuggingFace `transformers` + pooling equivalent) to load `BAAI/bge-base-en-v1.5` once per process and reuse across batches — do not reload the model per batch.
* Run inference on CUDA. Use **FP16 mixed precision** to reduce VRAM footprint and increase throughput, consistent with the approach validated in Phase 2.1.
* Passages (chunks) are embedded **without** the query instruction prefix — the BGE passage/document convention. Only queries (a later-phase concern) require the `"Represent this sentence for searching relevant passages: "` prefix. Document this explicitly in code comments/config so a future retrieval phase does not accidentally omit or duplicate it.
* Truncate/handle chunks exceeding the model's max sequence length (documented in Phase 2.1 model-card findings) consistently — log how many chunks were truncated and by how much, per batch, for later quality review.
* Embeddings must carry their originating `chunk_id` unambiguously through the pipeline (no positional-order assumptions that could desync if a chunk fails to embed).

---

# 3. GPU Batch Size Optimization

* Do not hardcode a single global batch size. Implement a **VRAM-aware batch sizing strategy**:
  * Start from the batch size validated during the Phase 2.1 benchmark for `bge-base-en-v1.5` as a baseline.
  * Optionally implement adaptive batching: on `CUDA out of memory`, catch the exception, halve the batch size, clear the CUDA cache, and retry, rather than crashing the whole run.
  * Log peak VRAM usage (`torch.cuda.max_memory_allocated()`) periodically so batch size can be tuned upward if headroom is consistently available.
* Batch by **token length bucketing** where practical (grouping similarly-sized chunks together) to avoid wasting VRAM padding short chunks up to the longest chunk in a batch.
* Document the final chosen batch size(s) and the reasoning in the pilot report (Section 15 below).

---

# 4. PostgreSQL + pgvector Storage of 768-Dimensional Embeddings

* Use the `vector(768)` column type from the `pgvector` extension (already used in the Phase 0 RAG_V0 baseline schema, extended here for legal metadata richness and 15M+ scale).
* Store raw embeddings as `vector(768)`; do not store them as JSON/text.
* Confirm the PostgreSQL version and `pgvector` extension version support the chosen index type (HNSW requires pgvector ≥ 0.5.0) — verify and document the installed version before proceeding.

---

# 5. Database Schema Design

Design **normalized relational tables**, not one giant flat table, so metadata is not duplicated per-chunk unnecessarily. Suggested schema (Antigravity should adapt field names/types to the actual Phase 1C Parquet schema — do not invent metadata not present in Phase 1C output):

```text
source_documents
  document_id (PK)
  source_type          -- legislation / judgment / other
  title
  act                  -- nullable, for legislation
  case_name            -- nullable, for judgments
  citation             -- nullable
  court                -- nullable
  jurisdiction
  level                -- central / state / UT
  state                -- nullable
  date
  effective_date       -- nullable
  is_historical
  source_url
  dataset_version
  original_source_id

domains
  domain_id (PK)
  domain_name           -- e.g. "Consumer Protection"

document_domains        -- many-to-many: a document/chunk may map to multiple domains
  document_id (FK)
  domain_id (FK)

chunks
  chunk_id (PK)
  document_id (FK -> source_documents)
  parent_id             -- nullable, self-referential (parent section/chunk)
  chunk_index
  source_type
  part / chapter / section / subsection / clause   -- nullable, legislation
  paragraph_number      -- nullable, judgments
  text                  -- full chunk text
  char_length
  cross_references      -- array/text of detected references (e.g. "Section 12", "Section 18")
  created_at

embeddings
  chunk_id (PK, FK -> chunks, one-to-one)
  model_name            -- 'bge-base-en-v1.5'
  model_version / dataset_version
  embedding vector(768)
  embedded_at
```

Design rationale to include in the spec/handoff:

* `embeddings` is a separate table from `chunks` (not a column on `chunks`) so that **a future model change or re-embedding does not require rewriting the chunks table**, and so multiple embedding models could coexist per chunk if ever needed (e.g. `embeddings_bge_base`, or a `model_name` discriminator column as shown above — Antigravity should pick one approach and document it, but must not silently assume only one embedding model will ever exist).
* `source_documents` deduplicates document-level metadata instead of repeating title/act/court/date on every chunk row — consistent with the Phase 1C principle of storing source-document references rather than copying full documents into every chunk.
* `document_domains` supports multi-domain tagging (a chunk's document can legitimately belong to more than one conceptual domain, as seen in the Phase 1B/1C domain distribution).

---

# 6. HNSW vs. IVFFlat — Index Type Decision

The spec must require Antigravity to **choose and justify**, not just pick a default. Guidance to include:

* **HNSW**: Better recall/query-latency trade-off, no training/clustering step required before use, index can be built incrementally as data is inserted (important since this is an incremental pipeline), but higher build-time memory/CPU cost and larger index size than IVFFlat at a given recall target.
* **IVFFlat**: Requires a representative sample to train cluster centroids **before** bulk-loading (a `lists` parameter tied to expected row count), which is awkward for an incrementally-growing 15M+ corpus being loaded in batches over multiple days — index quality can suffer if built on a small `lists` value derived from partial data. Smaller index size and typically faster to build, but generally lower recall than HNSW at comparable query speed for large corpora.
* **Recommendation to validate empirically**: given the incremental/multi-day nature of this pipeline and the corpus scale (15M+), **HNSW is expected to be the better fit** because it does not require a fixed centroid count decided upfront and supports incremental inserts more gracefully. Antigravity must confirm this is still true after the pilot (Section 15) — e.g. by comparing pilot-scale HNSW build time/query latency against an IVFFlat pilot run — and document the final decision with pilot evidence, not just this a-priori reasoning.
* Whichever is chosen, document the specific pgvector index parameters used (for HNSW: `m`, `ef_construction`, `ef_search`; for IVFFlat: `lists`, `probes`) and the reasoning for the chosen values given 15M+ rows and 768 dimensions.

---

# 7. Index & Query Parameter Design

* Create the vector index on the `embeddings.embedding` column using the chosen index type/parameters from Section 6.
* Create standard B-tree/composite indexes to support expected metadata filtering patterns (which will matter for a future hybrid-retrieval phase): at minimum on `chunks.document_id`, `chunks.source_type`, `source_documents.jurisdiction`, `source_documents.level`, `source_documents.state`, `document_domains.domain_id`.
* Document expected query patterns this schema/index design must support (even though the retriever itself is a later phase): vector similarity search alone; vector similarity search filtered by jurisdiction/domain/source_type; vector similarity search filtered by date range (for handling historical vs. current law).
* Note pgvector's interaction between HNSW/IVFFlat ANN search and additional `WHERE` filtering (post-filtering vs. pre-filtering trade-offs) as a known limitation to be aware of, without solving it in this phase — flag it as an input to the future retrieval-design phase.

---

# 8. Bulk Loading Strategy

* Row-by-row `INSERT` is explicitly disallowed for bulk loads at this scale.
* Use PostgreSQL's `COPY` command (via `psycopg`'s `copy_expert`/`copy_from`, or an equivalent bulk-COPY library) for loading `source_documents`, `chunks`, and `embeddings` rows.
* Batch size for `COPY` operations should be tuned separately from the GPU embedding batch size (these are independent concerns — embedding batch size is VRAM-bound, DB load batch size is I/O/transaction-bound). Document both values distinctly.
* Wrap each batch's DB load in a transaction so a failure partway through a batch does not leave that batch half-committed; on failure, the whole batch's DB writes must roll back cleanly so it can be safely retried.
* Defer non-critical index maintenance where beneficial: consider building the HNSW/IVFFlat vector index **after** an initial bulk load pass (or after the pilot, before the full run) rather than incrementally rebuilding it row-by-row during every batch insert, since large ANN index structures are often far more efficient to build in bulk than to maintain incrementally under constant insert load. Antigravity must decide and document whether the pilot builds the index before or after bulk-loading the pilot data, and carry that same decision into the full-run procedure.

---

# 9. Checkpointing & Resumability

* Extend the Phase 2.2 manifest (Section 1) to track state at the **batch-file granularity**: `pending → embedding → embedded → loading → loaded`, plus `failed` with an error message and retry count.
* On restart, the indexer must:
  1. Read the Phase 2.2 manifest.
  2. Skip any batch already `loaded`.
  3. Resume/retry any batch `failed` or stuck `embedding`/`loading` (treat an in-progress-but-not-completed state found at startup as needing re-verification/retry, since the previous run may have crashed mid-batch).
  4. Continue scanning for newly-`complete` Phase 1C batches not yet seen.
* This must survive: process crash, machine reboot, and manual interruption (Ctrl+C) without corrupting the manifest or leaving orphaned partial DB rows (see Section 10).
* A multi-hour/multi-day full run must be safely stoppable and restartable at any point without reprocessing already-`loaded` batches.

---

# 10. Preventing Duplicate Embeddings on Reprocessing

* `chunks.chunk_id` and `embeddings.chunk_id` must be primary keys / unique constraints, so a re-run that attempts to reinsert an already-loaded chunk fails fast on constraint violation rather than silently duplicating.
* Prefer an **idempotent upsert** pattern (`INSERT ... ON CONFLICT (chunk_id) DO NOTHING` or `DO UPDATE` as appropriate) over relying solely on the manifest to prevent reprocessing — the manifest prevents *unnecessary* recomputation (saving GPU time), while the DB constraint is the actual correctness backstop against duplication if the manifest and DB state ever disagree (e.g. after a crash between "embedded" and "loaded" states).
* Document which behavior is intended on conflict (skip vs. overwrite) and why — e.g. skip is likely correct for this phase since a given `chunk_id` from Phase 1C should be immutable once chunked, but state the assumption explicitly.

---

# 11. Storage Estimation

Produce concrete estimates, shown with the formula used (not just a final number), for:

* **Raw vector storage**: `num_chunks × 768 dims × 4 bytes (float32)` — state whether pgvector's on-disk representation adds overhead beyond raw bytes and account for it if known.
* **PostgreSQL row/table storage**: `chunks` table (text + metadata columns) and `source_documents`/`domains`/`document_domains` tables, estimated from the pilot's actual on-disk table sizes (via `pg_total_relation_size`) extrapolated to 15M+ rows, rather than a purely theoretical calculation.
* **pgvector index storage**: HNSW (or IVFFlat) index size, measured from the pilot via `pg_relation_size` on the index and extrapolated — cross-check against the Phase 2.1 report's projected ~80 GB figure for `bge-base-en-v1.5` at 15.7M chunks and reconcile any discrepancy.
* **Metadata storage**: separately called out from vector storage so the split is visible (the Phase 2.1 projected DB size figures did not necessarily separate these).
* **Total expected disk usage** at 15M+ scale, with a stated safety margin (e.g. +20%) for WAL, temp files during index builds, and vacuum overhead.
* Confirm the configured tablespace (`d:/Abishek/pg_tablespace` per Phase 2.1 report) has sufficient free space for the projected total before the full run is authorized.

---

# 12. Parallel Independence from Phase 1B/1C

* This pipeline must be runnable **while Phase 1B and/or Phase 1C are still producing new batches**. It is strictly a downstream consumer.
* It must never write to, modify, or delete any Phase 1A/1B/1C output directories or manifests — only read Phase 1C's manifest and batch files, and write to its own separate Phase 2.2 manifest and the PostgreSQL database.
* If no new completed Phase 1C batches are available, the indexer should idle/poll (with a sensible interval) rather than error out, so it can be left running as a long-lived background process alongside Phase 1B/1C.

---

# 13. Memory Discipline at Scale

* Never load the full chunked corpus, full embedding set, or full query-result set into RAM at once.
* Process strictly batch-by-batch: read one Phase 1C batch file (or row-group) → embed it → load it to Postgres → checkpoint → release memory → move to next batch.
* Bound in-flight memory usage: document the expected peak RAM usage per batch (chunk text + embeddings held simultaneously) given the chosen batch sizes, and confirm it stays well within the 32 GB system RAM budget alongside normal OS/Postgres/other-phase overhead.
* GPU VRAM and system RAM are separate constraints — do not assume headroom in one implies headroom in the other.

---

# 14. Validation Tests

Define concrete, automatable checks (not just informal spot-checks) to run after both the pilot and (later) the full run:

1. **Row-count reconciliation**: number of chunks read from Phase 1C batches == number of rows in `chunks` table == number of rows in `embeddings` table (per source_type and overall).
2. **Referential integrity**: every `chunks.document_id` has a matching `source_documents` row; every `embeddings.chunk_id` has a matching `chunks` row; no orphaned rows in either direction.
3. **Vector sanity**: spot-check a sample of stored vectors have the expected dimensionality (768), are not all-zero, and are not NaN/Inf.
4. **Similarity search smoke test**: run a handful of known queries (can reuse Phase 2.1's evaluation query set) against the pilot index and confirm the previously-established relevant chunks (from Phase 2.1's relevance judgments, where they fall within the pilot's loaded subset) are retrievable in the top-K results — this cross-checks that the stored vectors + index behave consistently with the Phase 2.1 benchmark's own embeddings.
5. **Metadata filtering correctness**: run filtered queries (e.g. jurisdiction = 'central' AND domain = 'Consumer Protection') and confirm returned rows actually match the filter, not just that the query executes.
6. **Checkpoint/resume correctness**: deliberately kill the pilot indexing process mid-batch and mid-load, restart it, and confirm (a) no duplicate rows appear, (b) processing resumes rather than restarting from scratch, (c) the manifest accurately reflects final state.
7. **Truncation/skip audit**: confirm the count of chunks truncated or skipped during embedding (Section 2) is logged and reconciles with the row-count check in (1) — i.e. skipped chunks are accounted for, not silently dropped from the totals.

---

# 15. Pilot Benchmark (Required Before Any Full Run)

Before the 15M+ run, execute a **pilot** using a subset of Phase 1C batches (a natural choice is to reuse or extend the same sampled/benchmark chunk set from Phase 2.1, or a fresh small set of full Phase 1C batch files — Antigravity should pick a pilot size on the order of tens of thousands of chunks, large enough to produce a meaningful, non-trivially-small vector index and realistic pgvector index-build timing, and document the exact size chosen).

The pilot must exercise, end-to-end, every stage of the pipeline and report on:

* Embedding generation: throughput (chunks/sec), peak VRAM, batch size(s) used, any OOM/retry events, truncation counts.
* GPU utilization: confirm the GPU is actually the bottleneck during embedding (vs. CPU/data-loading being the bottleneck), via basic utilization logging.
* PostgreSQL insertion speed: chunks/sec loaded via COPY, transaction batch size used.
* Vector storage: actual on-disk size of the pilot's `embeddings` table/index (measured, not estimated).
* Index creation: HNSW (or IVFFlat) build time at pilot scale, and the specific parameters used.
* Similarity search: query latency (ms) for top-K vector search at pilot scale, with and without metadata filters.
* Metadata filtering: confirm filtered queries return correct, plausible results (per Section 14.5).
* Checkpoint/resume behavior: results of the deliberate kill-and-restart test (Section 14.6).

Produce a **pilot report** (e.g. `PHASE_2_2_PILOT_REPORT.md`) summarizing the above, extrapolating pilot measurements to full-corpus scale for time and storage (reconciling with Section 11's estimates), and stating explicitly whether the pilot passed all validation checks in Section 14.

**The full 15M+ indexing run must not begin until:**
1. The pilot report is produced, and
2. Abishek has reviewed it and explicitly authorized the full run.

The full run is then a **separate, manually-invoked** execution of the same pipeline against the entire corpus — not something the pilot's completion triggers automatically.

---

# 16. LangChain Compatibility (Forward-Looking, Not Built Now)

* Design the schema and access patterns so that a future retrieval phase can wrap this store with LangChain's `PGVector` vector store integration (or an equivalent custom retriever) with minimal friction:
  * Keep chunk text, `chunk_id`, and metadata queryable together (e.g. via a view or join) so LangChain's `Document(page_content=..., metadata={...})` shape can be populated directly from a single query.
  * Avoid schema decisions that would force a lossy transform later (e.g. ensure metadata fields LangChain typically expects — source, jurisdiction, section — are present as plain columns, not buried in nested structures that are hard to flatten).
* Do **not** install/configure LangChain, write a retriever class, or build any chain in this phase. This is documentation/design guidance only, to avoid rework later.

---

# Explicit Non-Goals (Guardrails)

This phase must NOT:

* Run the full 15M+ embedding/indexing job automatically or by default — only the pilot runs automatically; the full run requires explicit manual invocation after sign-off.
* Build the final RAG retrieval chain, reranker, hybrid search, Gemini answer generation, agent, or frontend.
* Modify, delete, or write to any Phase 1A/1B/1C authoritative outputs or manifests.
* Assume Phase 1B or Phase 1C has fully finished — read only Phase 1C batches marked complete at the time this pipeline runs.
* Assume the entire corpus, embedding set, or query-result set fits in RAM or VRAM at once.
* Re-litigate the embedding model choice (`bge-base-en-v1.5` is a settled input from Phase 2.1).

---

# Phase 2.2 Completion Criteria

Phase 2.2 is complete when:

* [ ] Phase 2.2 manifest/checkpoint system is implemented and integrated with Phase 1C's manifest (read-only) 
* [ ] Incremental batch reading from Phase 1C's chunked corpus works without loading the full corpus into RAM
* [ ] `bge-base-en-v1.5` embedding generation runs on the RTX 5060 with VRAM-aware batch sizing and FP16
* [ ] Database schema (`source_documents`, `domains`, `document_domains`, `chunks`, `embeddings`) is created with appropriate types, keys, and indexes
* [ ] HNSW vs. IVFFlat decision is made and justified with pilot evidence, and the chosen index is built with documented parameters
* [ ] Bulk loading uses `COPY`/batched inserts, not row-by-row inserts, with per-batch transactional safety
* [ ] Checkpointing/resumability is implemented and verified via a deliberate kill-and-restart test
* [ ] Duplicate-prevention (unique constraints + idempotent upsert behavior) is implemented and verified
* [ ] Storage estimates (raw vectors, table storage, index storage, metadata storage, total) are produced from pilot measurements, reconciled against Phase 2.1's projections
* [ ] The pipeline runs correctly in parallel with an active/ongoing Phase 1B/1C process without interference
* [ ] All validation tests in Section 14 pass on the pilot
* [ ] `PHASE_2_2_PILOT_REPORT.md` is produced
* [ ] The full 15M+ run has NOT been started without explicit manual authorization following pilot review

---

# Critical STOP Condition

After the pilot succeeds and `PHASE_2_2_PILOT_REPORT.md` is produced:

**STOP.**

Do NOT automatically begin the full 15M+ embedding/indexing run. Do NOT build the retriever, reranker, hybrid search, Gemini generation chain, agent, or frontend.

The full indexing run is a distinct, manually-triggered operation requiring Abishek's review and sign-off on the pilot report. Once the full run is separately authorized and completes, the next phase will be **RAG Retriever & Hybrid Search Design**, where query-time embedding, metadata-filtered ANN search, lexical/BM25 fusion, and reranking are designed.

**Do not proceed beyond Phase 2.2 automatically.**