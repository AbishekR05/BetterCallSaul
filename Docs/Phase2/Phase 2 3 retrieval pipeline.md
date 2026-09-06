# Project Context

We are building a **Legal Awareness AI / Agentic RAG system for Indian law** ("Better Call Saul") for **layman users with little or no legal background**.

Prior phases:

* **Phase 1A–1C (complete):** Acquired, normalized, and legally-aware-chunked ~15.7M+ Indian legal records (legislation + judgments) into a Parquet-based chunked corpus with rich metadata (domain, jurisdiction, level, state, court, act/section/subsection, case citation, date/effective_date, provenance, parent/child relationships, etc.).
* **Phase 2.1 (complete):** Benchmarked embedding models on a stratified sample against a 48-query layman evaluation set. Selected **`BAAI/bge-base-en-v1.5`** (768 dimensions) — highest Recall@10 (0.7917) and MRR (0.6615) among candidates. Confirmed this model requires the query-side instruction prefix `"Represent this sentence for searching relevant passages: "` at **query time only**; passages/chunks are embedded without any prefix.
* **Phase 2.2 (pilot complete and validated):** Built the production indexing pipeline — normalized PostgreSQL schema (`source_documents`, `domains`, `document_domains`, `chunks`, `embeddings`), COPY-based bulk loading, checkpointed/resumable incremental embedding of Phase 1C batches, and an **HNSW cosine index** on `embeddings.embedding` with `m=16`, `ef_construction=64`. The pilot subset (~1,000 chunks) passed all validation tests (row-count reconciliation, referential integrity, vector sanity, similarity search smoke test, metadata filtering correctness, checkpoint/resume correctness).

**Current state at the start of Phase 2.3:**

* The **full 15.7M+ production indexing run is currently executing in the background**, incrementally embedding and loading Phase 1C batches into the same PostgreSQL database, using the same schema and manifest system established in Phase 2.2.
* Phase 2.3 must be developed and tested **only against the existing pilot-scale data already loaded**, and must be **strictly read-only** with respect to the `chunks`, `embeddings`, `source_documents`, `domains`, and `document_domains` tables and the Phase 2.2 manifest.
* Phase 2.3 must not compete for GPU VRAM with the production indexing job in a way that could destabilize it, and must not issue schema-modifying DDL, bulk writes, or index-rebuild operations against the production database while indexing is in progress.

Hardware/software environment (unchanged from Phase 2.2):

* GPU: NVIDIA RTX 5060, 8 GB VRAM (shared with the background indexing job — see Section 14 constraints)
* PostgreSQL + pgvector, HNSW cosine index (`m=16`, `ef_construction=64`) on `embeddings.embedding`
* LangChain will be used for RAG orchestration in a later phase; Phase 2.3 must produce a retriever compatible with LangChain, but does not build the generation chain.

---

# Phase 2.3 Objective

> **Build a production-ready, read-only retrieval pipeline that takes a layman legal question, embeds it correctly with `bge-base-en-v1.5`, performs cosine-similarity search (optionally metadata-filtered) against the existing pgvector index, and returns a clean, deduplicated, provenance-complete, score-safeguarded set of relevant legal chunks — without generating any answer text.**

This phase is retrieval only. It stops at "here are the relevant, trustworthy legal chunks, with their sources." Answer generation, reranking (unless explicitly scoped in), and agentic orchestration are later phases.

---

# 1. Retrieval Architecture & Data Flow

```text
                     User Query (raw text)
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Query Preprocessing      │
                 │ (normalize, clean)       │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Optional: Filter         │
                 │ Extraction               │
                 │ (jurisdiction/domain/    │
                 │  source_type hints, if   │
                 │  explicitly provided by  │
                 │  caller — NOT NLU/intent │
                 │  classification)         │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Query Embedding          │
                 │ bge-base-en-v1.5          │
                 │ + query instruction       │
                 │   prefix applied          │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ pgvector Cosine Search   │
                 │ (HNSW, top-N candidates) │
                 │ + optional metadata      │
                 │   WHERE filters          │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Post-Processing          │
                 │ - score threshold        │
                 │ - dedup                  │
                 │ - parent/child expansion │
                 │ - provenance join        │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Retrieval Result Object  │
                 │ (schema in Section 14)   │
                 └─────────────────────────┘
```

The retrieval pipeline is exposed as a single callable/class (`LegalRetriever` — see Section 15) with one primary method, e.g. `retrieve(query: str, filters: RetrievalFilters | None, config: RetrievalConfig | None) -> RetrievalResult`, so it can be invoked directly, wrapped by LangChain, or later wrapped by an agent — without those callers needing to know about embeddings or SQL.

This is a **library/service component**, not a standalone script. Antigravity should design it as an importable Python module with a thin CLI/test harness on top for the pilot test plan (Section 20).

---

# 2. Query Preprocessing & Normalization

Before embedding, apply lightweight, deterministic normalization (do NOT apply heavy NLP/intent classification — that belongs to a future query-understanding phase):

* Strip leading/trailing whitespace; collapse internal repeated whitespace.
* Normalize Unicode (e.g. NFKC) to avoid embedding differences from visually-identical but differently-encoded characters (common with text copy-pasted from PDFs/WhatsApp).
* Enforce a maximum input length (character or token count, configurable — see Section 16) and truncate with a logged warning if exceeded, rather than silently failing or passing an oversized string to the tokenizer.
* Reject empty/whitespace-only queries early with a clear error result (not an exception that crashes the caller — see Section 18).
* Do NOT lowercase, stem, or remove stopwords — BGE-base is a transformer embedding model and destructive normalization can hurt embedding quality; preserve natural language as typed, only cleaning encoding/whitespace artifacts.

---

# 3. BGE-Base Query Instruction Prefix Handling

This is a **correctness-critical detail** carried over from Phase 2.1/2.2 notes:

* Every query embedded for retrieval MUST be prefixed with exactly:
  `"Represent this sentence for searching relevant passages: "`
  followed by the normalized query text, before being passed to the model.
* This prefix must be applied in **exactly one place** in the codebase (a single shared constant/function), not duplicated across call sites, to avoid future drift (e.g. someone adding the prefix twice, or a new call site forgetting it).
* Passage-side chunk embeddings already stored in `embeddings` (from Phase 2.2) were embedded **without** this prefix — Phase 2.3 must not re-embed or alter any stored chunk embeddings; it only applies the prefix to incoming queries.
* Add an automated check (unit test) that fails loudly if the prefix constant is ever changed or omitted, since a silent regression here would degrade retrieval quality without any obvious error.

---

# 4. Query Embedding Generation

* Load `BAAI/bge-base-en-v1.5` once per process/service lifetime (not per request) — model loading is expensive and must not happen on every query.
* Run query embedding on GPU (CUDA) using the same FP16 approach validated in Phase 2.2, but be mindful this shares the GPU with the background production indexing job (see Section 14 on VRAM sharing/contention). Provide a configuration flag to fall back to CPU inference for queries if GPU contention becomes an issue during development — single-query embedding is cheap enough that CPU fallback is a reasonable safety valve, unlike bulk corpus embedding.
* Normalize the resulting query embedding vector (L2 normalization) to match the normalization convention already used for stored chunk embeddings (per the context notes: "Embeddings use normalized BGE-base vectors"), so cosine similarity via pgvector's `<=>` operator (or inner product on pre-normalized vectors, whichever pgvector operator class matches the HNSW index's configured distance metric) is computed correctly and consistently with the index.
* Confirm and document which pgvector distance operator/index configuration (`vector_cosine_ops` vs. `vector_ip_ops`, etc.) matches "HNSW cosine index" as stated in the context, and ensure the query path uses the identical operator the index was built with — a mismatch here would silently fall back to a sequential scan or return incorrect rankings.

---

# 5. pgvector Cosine Similarity Search

* Query the `embeddings` table via the HNSW index using the same distance operator it was built with, joined to `chunks` (and `source_documents`, `domains`/`document_domains` as needed for metadata) to retrieve chunk text and metadata alongside similarity scores in a single query where practical, to avoid N+1 query patterns.
* Retrieve a **candidate set larger than the final top-K** (see Section 6) before post-processing (score thresholding, dedup, parent/child expansion), since those steps can only reduce the candidate set — over-fetch modestly (e.g. fetch `top_n_candidates = K * multiplier`, configurable) so the final returned set still has K good results after filtering.
* Set the HNSW query-time parameter `ef_search` explicitly per query (do not rely on a server-wide default) since this directly trades off recall vs. latency — expose it as a configurable parameter (Section 16) with a sensible default informed by the pilot benchmark (Section 20).

---

# 6. Top-K Retrieval Configuration & Selection

* `K` (final number of chunks returned to the caller) must be a configurable parameter, not hardcoded, with a documented sensible default (e.g. `K=8`, to be validated against Phase 2.1's evaluation query set — note that benchmark) — Antigravity should tune the default based on pilot testing (Section 20), not assume a number without evidence.
* Distinguish three related-but-different "K" values in code/config, clearly named, to avoid confusion:
  * `candidate_k` — how many nearest neighbors are pulled from pgvector before post-processing (larger).
  * `final_k` — how many chunks are ultimately returned after thresholding/dedup/expansion (smaller, caller-facing).
  * `ef_search` — the HNSW-specific search-quality parameter (Section 5), distinct from both K values above.
* Support **per-request override** of `final_k` (e.g. a caller wanting only the single best match vs. a broader evidence set for a complex question) without requiring a code change — this anticipates the future agentic layer needing variable evidence breadth per sub-question.

---

# 7. Metadata Filtering

Support optional, composable filters passed alongside the query, applied as SQL `WHERE` clauses joined against `chunks`/`source_documents`/`document_domains`:

* **Jurisdiction** (e.g. `jurisdiction = 'central'` or a specific state name)
* **Level** — Central vs. State/UT (distinct from the specific state, per the Phase 1B/1C schema's `level` field)
* **Legal domain** — one or more values from the Phase 1B/1C domain taxonomy (via `document_domains`), supporting OR-across-selected-domains semantics
* **Source type** — legislation vs. judgment vs. other
* **Court** — for judgments only (nullable/ignored for legislation rows)
* **Date / effective_date range** — to support future "what is the current law" vs. "what was the law at time X" distinctions; filter should support open-ended ranges (before/after/between)

Design requirements:

* All filters are **optional and composable** (any combination, including none).
* Filters that don't apply to a given `source_type` (e.g. `court` on legislation rows) must not silently exclude those rows — only apply the filter to rows where the field is semantically meaningful, or make this behavior explicit and documented, whichever Antigravity determines is more correct; either way it must be a deliberate, documented decision, not an accidental artifact of `NULL` comparison semantics in SQL.
* Filters are applied via a structured object (e.g. a `RetrievalFilters` dataclass/Pydantic model), not a raw dict or SQL string, to keep the API type-safe and to prevent SQL injection — filter values must be parameterized, never string-interpolated into the query.

---

# 8. Semantic Retrieval vs. Metadata-Filtered Retrieval — When Each Applies

Document explicit guidance (this phase does not build the caller-side logic that decides this automatically — that is a future query-understanding/agent concern — but the retriever's API must make both modes trivially usable by a future caller):

* **Pure semantic retrieval** (no filters): appropriate when the query itself doesn't specify jurisdiction/domain, or when the caller wants the broadest possible evidence sweep (e.g. an initial exploratory search).
* **Metadata-filtered retrieval**: appropriate when the caller (a future query-understanding step, or the user explicitly, e.g. via a UI jurisdiction selector) has already established jurisdiction/domain/source_type context — e.g. a user who has stated they are asking about Karnataka tenancy law should have state/domain filters applied to avoid diluting results with irrelevant-jurisdiction matches that happen to be textually similar.
* Filtering should generally be treated as a **precision-improving narrowing step**, applied on top of semantic search (i.e. still rank by cosine similarity within the filtered subset), not as a replacement for semantic ranking.
* Document the known risk of over-filtering: if filters are too narrow (e.g. wrong state guessed) the retriever may return zero or poor results even though relevant material exists elsewhere in the corpus — Section 9 covers how the retriever should surface this rather than fail silently.

---

# 9. Handling Ambiguous Queries & Insufficient Evidence

* If, after semantic search (and any applied filters) and score thresholding (Section 10), **fewer than a configurable minimum number of results** remain (e.g. `min_acceptable_results`, default informed by pilot testing), the retriever must return a result object with an explicit `insufficient_evidence: true` flag (see schema, Section 14) — not an empty list with no explanation, and not a fabricated/low-confidence result presented as if it were reliable.
* If filters were applied and zero/few results were returned, but a **filter-relaxed retry** (same query, filters removed or loosened) would surface higher-scoring results, the retriever should optionally perform this retry (configurable — `auto_relax_filters: bool`) and clearly mark in the result which filters were actually honored vs. dropped, so a caller/future agent can decide whether to trust the relaxed results or ask the user to confirm jurisdiction.
* The retriever does **not** attempt to rephrase, decompose, or disambiguate the query itself (no query rewriting, no LLM call) — that is out of scope for this phase (see Section 24). It only reports clearly when it could not find confident evidence, so a later phase (agent or generation layer) can decide what to do about it (e.g. ask a clarifying question, or state the limitation to the user).

---

# 10. Retrieval Score Thresholds & Safeguards

This is a **legal-correctness safeguard**, not a nice-to-have:

* Define a configurable **minimum similarity score threshold** below which a candidate is discarded entirely, regardless of its rank — a top-1 result with a low absolute similarity score is still a poor match and must not be presented as reliable evidence just because it was the best of a bad set.
* The threshold should be derived empirically from the pilot's retrieval-quality evaluation (Section 21/22), not guessed — document the chosen value and the reasoning (e.g. observed score distribution for known-relevant vs. known-irrelevant pairs from Phase 2.1's relevance judgments).
* Support **two tiers** if useful: a "high confidence" threshold (results safe to present as strong evidence) and a lower "weak/related" threshold (results that might be background-relevant but should be flagged as lower-confidence) — mirrors the graded-relevance concept introduced in Phase 2.1. This is optional but recommended; if implemented, both tier thresholds must be configurable and their meaning clearly reflected in the result schema.
* When all candidates fall below even the lower threshold, this is exactly the `insufficient_evidence` case from Section 9 — the two mechanisms (thresholding and insufficient-evidence flagging) are directly linked and must be implemented consistently, not as separate/conflicting logic paths.

---

# 11. Parent/Child Chunk Relationships & Neighbor Retrieval

* The Phase 1C schema preserves `parent_id` (chunk's parent section/chunk) and `chunk_index` (position within its parent/document). Phase 2.3 must use this to optionally **expand context** around a strong match:
* Support a configurable option (e.g. `include_parent_context: bool`, `include_sibling_context: bool`) that, when enabled, additionally fetches:
  * The matched chunk's **parent** chunk/section (if one exists), to give surrounding legal context (e.g. a subsection match should be able to surface its parent section for the "which Act, which section" framing described in Phase 1C).
  * Optionally, **immediately adjacent sibling chunks** (`chunk_index - 1`, `chunk_index + 1` within the same `parent_id`/`document_id`) where a legal provision naturally continues across chunk boundaries.
* These context-expansion chunks must be clearly distinguished in the result schema from directly-matched chunks (e.g. a `match_type: "direct" | "parent_context" | "sibling_context"` field) — they should never be silently merged with genuine similarity-ranked matches, since they were not retrieved on the basis of similarity to the query.
* Context expansion must not itself count against `final_k` in a way that silently reduces the number of genuine top-K matches returned — treat it as supplementary, additive information.

---

# 12. Deduplication of Retrieved Chunks

* Deduplicate at two levels:
  1. **Exact duplicate `chunk_id`** appearing more than once in the raw candidate set (can happen if context-expansion, Section 11, pulls in a chunk that was already a direct match).
  2. **Near-duplicate text** — chunks with a very high text-similarity/hash match (reusing the duplicate-detection approach already established in Phase 1C for chunk-level deduplication) but different `chunk_id`s, which can occur if the corpus itself contains legally-duplicate material (e.g. a provision reproduced in two places). Do not silently drop these without a documented policy — Phase 1C's guidance was to **not** aggressively deduplicate legally-distinct material (different jurisdictions/versions/acts), so retrieval-time dedup must be more conservative than corpus-level dedup, and should generally only collapse true exact-text duplicates from the *same* document/version, keeping the higher-scoring occurrence.
* Document the exact dedup key and policy used, since this is a place where being too aggressive could hide legally meaningful distinctions (e.g. state amendments to central law).

---

# 13. Source/Provenance Preservation

Every returned chunk must carry enough information to be traced back to its authoritative source, reusing fields already established in Phase 1B/1C/2.2 — do not invent new provenance fields:

* `document_id`, `chunk_id`, `source_type`
* `title`, `act` / `case_name`, `citation`
* `jurisdiction`, `level`, `state`, `court`
* `section` / `subsection` / `clause` or `paragraph_number` as applicable
* `date`, `effective_date`, `is_historical`
* `source_url`, `original_source_id`, `dataset_version`

This provenance must be included in **every** result item, including context-expansion items (Section 11), so a downstream citation-generation phase never has to re-query the database to know where a chunk came from.

---

# 14. Retrieval Result Schema / API Design

Define a structured result object (Pydantic model recommended, for validation and easy LangChain/JSON interop). Conceptual shape:

```text
RetrievalResult
  query: str                      # original, pre-normalization
  normalized_query: str
  filters_requested: RetrievalFilters | None
  filters_applied: RetrievalFilters | None   # may differ if auto-relaxed (Section 9)
  insufficient_evidence: bool
  candidate_count: int             # raw candidates before post-processing
  returned_count: int               # len(results)
  results: list[RetrievalResultItem]
  timing: RetrievalTiming           # see Section 17
  warnings: list[str]               # e.g. "query truncated", "filters relaxed"

RetrievalResultItem
  chunk_id: str
  document_id: str
  text: str
  similarity_score: float
  confidence_tier: "high" | "low"   # if two-tier thresholding (Section 10) is implemented
  match_type: "direct" | "parent_context" | "sibling_context"
  provenance: ProvenanceFields       # Section 13 fields
```

* This schema is the **stable public contract** of the retriever — LangChain integration (Section 15) and any future agent/generation code depends on it, so field names/types should be settled deliberately, not left implicit in code.
* Provide serialization to plain dict/JSON for API/logging use, in addition to the Python object.

---

# 15. LangChain Integration

* Use LangChain's existing PostgreSQL/pgvector integration (`langchain-postgres` / the pgvector vector store class appropriate to the LangChain version in use) configured against the **existing** schema/table, rather than having LangChain create its own separate table/schema — Antigravity must confirm whether the chosen LangChain pgvector integration can operate against a pre-existing custom schema (with our richer metadata tables) or whether a thin custom LangChain-compatible retriever wrapper is more appropriate given our normalized (non-LangChain-default) schema; document which approach was chosen and why.
* Regardless of which integration path is chosen, LangChain must **not** be allowed to run its own schema-creation/migration against the production database — this phase is read-only against the corpus tables (per the context constraints). If the chosen LangChain integration wants to manage its own tables, isolate that to a separate, clearly-named schema/table (e.g. for LangChain's internal bookkeeping only) and never point it at `chunks`/`embeddings` for writes.
* The end deliverable is a LangChain-compatible retriever object (implementing LangChain's `BaseRetriever` interface or equivalent) that internally calls the `LegalRetriever` built in this phase, so it can be dropped into a LangChain chain in a future phase without modification to this phase's core logic.
* Do not build the chain itself (no `RetrievalQA`, no prompt templates, no LLM call) — only the retriever component.

---

# 16. Configurable Parameters (No Hardcoding)

All of the following must live in a single configuration source (e.g. a `RetrievalConfig` Pydantic model / YAML+env-driven config, consistent with how prior phases centralized config), not scattered as magic numbers across the codebase:

* `candidate_k`, `final_k` defaults
* `ef_search`
* similarity score thresholds (high/low tiers)
* `min_acceptable_results` (insufficient-evidence trigger)
* `auto_relax_filters` (bool) and relaxation strategy
* `include_parent_context`, `include_sibling_context` (bools) and sibling window size
* max query input length
* GPU vs. CPU device selection for query embedding
* database connection parameters (reusing Phase 2.2's connection/config approach, not a new one)
* dedup policy toggles (Section 12)

Document defaults and the reasoning/evidence behind each (tied back to pilot testing, Section 20/21, where applicable).

---

# 17. Logging & Observability

Every retrieval call must log (structured logging, not just print statements) at minimum:

* Total end-to-end query latency
* Query embedding latency (separate from DB latency)
* Database search latency (the pgvector query itself, separate from post-processing time)
* Post-processing latency (dedup, context expansion, provenance join), if non-trivial
* Number of raw candidates returned from pgvector
* Final returned count after post-processing
* Top-K similarity scores (at least the top result's score, ideally the full returned set's scores)
* Filters applied (and whether they were relaxed per Section 9)
* `insufficient_evidence` flag value
* Any warnings (truncation, relaxation, etc.)
* Failures/exceptions, with enough context to debug (query text hash or truncated preview — avoid logging full raw user query text at a verbose/persistent log level if it might contain sensitive personal details, per the project's data-minimization principle established in the project context doc)

Logs should be structured (e.g. JSON lines) so they can later feed an evaluation dashboard, consistent with the project's stated Version 4 goal of "observability" and "evaluation dashboard."

---

# 18. Error Handling & Safe Failure Behavior

* Database connection failures, embedding-model load failures, and CUDA errors must be caught and surfaced as a clear, typed error result/exception — never allowed to crash the calling process ungracefully in a way that could, for instance, interfere with anything else running on the machine (including the background Phase 2.2 indexing job).
* On any internal failure, the retriever must fail **closed**: return a result indicating failure/no-evidence rather than partial, potentially-misleading results (e.g. do not return zero-filtered results and mark them as if scoring/thresholding had been correctly applied when it actually errored out partway through).
* Timeouts: define a configurable max wall-clock time for the DB search step; if exceeded, fail safely with a clear "search timed out" result rather than hanging indefinitely (relevant given the corpus will keep growing to 15.7M+ concurrently).
* Never let a retrieval-side error propagate as an unhandled exception into whatever future agent/chain calls this component — always return the structured result/error type.

---

# 19. Performance Considerations for 15.7M+ Scale

* The pilot is tested at ~1,000 chunks; document explicitly which performance characteristics are expected to hold vs. change at 15.7M+ scale (informed by, but not limited to, Phase 2.2's storage/index projections):
  * HNSW query latency is expected to scale sub-linearly but not stay constant as the index grows from ~1K to ~15.7M vectors — the pilot's measured latency (Section 20) is a lower bound, not a final performance guarantee, and this must be stated plainly in the pilot report rather than implied to be representative of production scale.
  * `ef_search` may need re-tuning at full scale (higher `ef_search` generally needed to maintain recall as the index grows) — flag this as a known follow-up once the full index finishes, not something resolved in this phase.
  * Metadata filter selectivity changes at scale — a filter that barely narrows a 1,000-row pilot may narrow a 15.7M-row corpus dramatically, changing the pre-filter-vs-post-filter cost trade-off noted in Phase 2.2's index design section.
* Design the retriever to be easily re-benchmarked once the full index finishes (i.e., the same test harness from Section 20 should be rerunnable later against the full corpus with no code changes, only config/data changes) — this is a design requirement now, even though the actual full-scale rebenchmark is out of scope for this phase.

---

# 20. Pilot Test Plan (Against Existing ~1,000-Chunk Index)

Using the existing pilot data from Phase 2.2 (do not trigger any new embedding/indexing job):

1. Verify the retriever connects to the existing database read-only and can execute a basic vector search against the pilot's `embeddings` table without error.
2. Confirm the query-embedding path applies the BGE instruction prefix correctly (Section 3) via a unit test that inspects the exact string passed to the model.
3. Run a batch of representative queries (can reuse/extend Phase 2.1's 48-query evaluation set, since it was validated against this same pilot embedding space) and record: latency breakdown (Section 17), returned scores, and whether previously-known-relevant chunks (from Phase 2.1's relevance judgments) are retrieved.
4. Measure baseline `ef_search` vs. latency/recall trade-off at pilot scale by sweeping a small set of `ef_search` values, to inform the default chosen in Section 16 (with the caveat from Section 19 that this default may need revisiting at full scale).
5. Empirically derive the score-threshold values (Section 10) from the distribution of similarity scores for known-relevant vs. known-irrelevant Phase 2.1 query/chunk pairs.
6. Confirm the pipeline does not issue any write/DDL statements against the production database during any part of this test plan (verifiable via a read-only DB role/credentials if practical, or via query-log inspection).

---

# 21. Retrieval Quality Evaluation Methodology

* Reuse Phase 2.1's query set and relevance judgments as the primary evaluation basis (they were built against this same embedding space and are the most defensible ground truth available at pilot scale).
* Compute the same class of metrics as Phase 2.1 (Recall@K, Precision@K, MRR) but now through the **actual retrieval pipeline** (query preprocessing → prefixed embedding → pgvector HNSW search → thresholding → dedup) rather than Phase 2.1's offline brute-force cosine comparison — this validates that the live pipeline reproduces (or explains any divergence from) the benchmark's offline numbers. Any material gap between Phase 2.1's offline metrics and Phase 2.3's live-pipeline metrics on the same queries/chunks must be investigated and explained (e.g. HNSW's approximate nature vs. Phase 2.1's presumably exact brute-force comparison, `ef_search` setting, thresholding cutting off true positives, etc.) rather than left as an unexplained discrepancy.
* Additionally evaluate the specific behaviors unique to the live pipeline that Phase 2.1 did not test: metadata filtering correctness, insufficient-evidence detection, parent/sibling context expansion, deduplication behavior.
* Where the ~1,000-chunk pilot lacks sufficient coverage for a given domain/jurisdiction to evaluate meaningfully, document this gap explicitly rather than reporting a misleadingly small/zero sample as a real result — this mirrors the Phase 2.1 guidance on excluding/flagging queries without ground truth in the sample.

---

# 22. Required Test Cases

Implement and document explicit test cases (automated where feasible, manual/documented where not) for each of the following:

1. **Successful retrieval** — a clear, well-formed layman query with known relevant chunks in the pilot set returns them above the high-confidence threshold.
2. **Metadata filtering** — the same query, filtered by a correct domain/jurisdiction, returns a subset consistent with the filter; filtered by an incorrect/mismatched domain, returns few/no results (and is handled per Section 9, not silently).
3. **Cross-jurisdiction queries** — a query where relevant material could plausibly exist in multiple jurisdictions (central + at least one state, if pilot data allows) is tested both unfiltered and filtered per-jurisdiction, confirming the filter actually narrows correctly.
4. **Legislation retrieval** — a query whose only relevant ground truth is legislation-type chunks retrieves them correctly and `source_type` metadata reflects this.
5. **Judgment retrieval** — analogous test for judgment-type chunks, including confirming `court`/`case_name`/`citation`/`paragraph_number` provenance fields are populated correctly.
6. **Mixed legislation + judgment retrieval** — a query with relevant ground truth spanning both source types returns a mixed result set, correctly ranked by similarity rather than grouped/biased by source type.
7. **Ambiguous questions** — a deliberately vague/multi-interpretable layman question (constructed for this test, or drawn from Phase 2.1's query set if a suitable one exists) is confirmed to either return a broad/lower-confidence result set correctly flagged, or trigger `insufficient_evidence` if scores are too low — not silently return a single confidently-flagged answer as if unambiguous.
8. **No-evidence/low-similarity questions** — a query about a topic known to be absent from the pilot sample (e.g. a domain with zero pilot coverage) correctly triggers `insufficient_evidence: true` rather than returning irrelevant chunks as if they were relevant.

Each test case must assert on the structured `RetrievalResult` schema fields (Section 14), not just eyeball raw output.

---

# 23. Phase 2.3 Acceptance Criteria

Phase 2.3 is complete when:

* [ ] `LegalRetriever` component implemented as an importable module with a single primary `retrieve(...)` entrypoint
* [ ] Query preprocessing/normalization implemented per Section 2
* [ ] BGE query instruction prefix applied correctly and exclusively at query time, verified by a dedicated unit test
* [ ] Query embedding runs via GPU (with CPU fallback option) without disrupting the background Phase 2.2 production indexing job
* [ ] pgvector cosine search implemented using the correct operator matching the existing HNSW cosine index, with configurable `ef_search`
* [ ] `candidate_k` / `final_k` distinction implemented and both configurable, with a pilot-informed default
* [ ] All specified metadata filters (jurisdiction, level, domain, source_type, court, date/effective_date range) implemented, composable, parameterized (no SQL injection risk)
* [ ] Insufficient-evidence detection and optional filter-relaxation implemented per Section 9
* [ ] Score thresholding (single or two-tier) implemented with pilot-derived, documented threshold values
* [ ] Parent/sibling context expansion implemented and clearly distinguished from direct matches in the result schema
* [ ] Deduplication implemented per the documented policy (Section 12)
* [ ] Full provenance fields present on every result item, including context-expansion items
* [ ] `RetrievalResult` / `RetrievalResultItem` schema implemented as documented (Section 14), with JSON serialization
* [ ] A LangChain-compatible retriever wrapper implemented against the existing schema, without LangChain writing to or migrating the production corpus tables
* [ ] All listed parameters centralized in a single `RetrievalConfig`, no hardcoded magic numbers
* [ ] Structured logging implemented covering all items in Section 17
* [ ] Error handling implemented per Section 18 (fail-closed, typed errors, timeouts, no unhandled exceptions)
* [ ] Pilot test plan (Section 20) executed and documented
* [ ] Retrieval-quality evaluation (Section 21) executed, with any divergence from Phase 2.1's offline metrics explained
* [ ] All required test cases (Section 22) implemented and passing (or, for genuinely inapplicable cases due to pilot data gaps, explicitly documented as such)
* [ ] Confirmed, throughout development and testing, that no writes/DDL were issued against the production corpus tables and that the background Phase 2.2 indexing job was not disrupted
* [ ] A `PHASE_2_3_RETRIEVAL_REPORT.md` produced summarizing pilot results, chosen configuration defaults and their justification, evaluation metrics, and known limitations/caveats for full-scale performance (per Section 19)

---

# 24. Explicit Non-Goals (Guardrails)

This phase must NOT:

* Generate any answer text or call Gemini or any other LLM for generation.
* Build the final RAG chain, prompt templates, or citation-formatting/answer-composition logic.
* Build any agent, LangGraph workflow, tool-selection, or query decomposition logic.
* Implement reranking (e.g. a cross-encoder reranking stage) — this specification does not identify reranking as in-scope for Phase 2.3; it remains a candidate for a future phase.
* Perform NLU/intent classification or automatic filter inference from free-text queries (filters are only applied when explicitly supplied by the caller).
* Issue any write, DDL, index-rebuild, or bulk-load operation against the production database, or otherwise interfere with the background Phase 2.2 full-corpus indexing run.
* Start any new full-corpus (or even pilot-scale) embedding/indexing job — Phase 2.3 consumes the existing pilot index as-is.
* Modify the embedding model, the HNSW index configuration (`m`, `ef_construction`), or the database schema established in Phase 2.2.
* Build a frontend, API server exposing this over HTTP, authentication, or user-facing UI (a thin internal test harness/CLI for the pilot test plan is in scope; a public-facing API is not).

---

# Recommended Project File/Folder Structure

```text
src/
├── retrieval/
│   ├── __init__.py
│   ├── config.py            # RetrievalConfig (Section 16)
│   ├── preprocessing.py     # query normalization (Section 2)
│   ├── embedding.py         # query embedding + prefix handling (Sections 3-4)
│   ├── search.py            # pgvector cosine search + ef_search handling (Section 5)
│   ├── filters.py           # RetrievalFilters model + SQL filter construction (Section 7)
│   ├── postprocessing.py    # thresholding, dedup, context expansion (Sections 10-12)
│   ├── provenance.py        # provenance field assembly (Section 13)
│   ├── schema.py            # RetrievalResult / RetrievalResultItem (Section 14)
│   ├── retriever.py         # LegalRetriever main class, orchestrates the above
│   ├── langchain_adapter.py # LangChain BaseRetriever-compatible wrapper (Section 15)
│   ├── logging_utils.py     # structured logging setup (Section 17)
│   └── errors.py            # typed error/result types (Section 18)
│
├── db/
│   └── connection.py        # reuse/import Phase 2.2's DB connection/config approach
│
tests/
├── retrieval/
│   ├── test_preprocessing.py
│   ├── test_prefix_handling.py     # Section 3 dedicated unit test
│   ├── test_filters.py
│   ├── test_thresholds_dedup.py
│   ├── test_context_expansion.py
│   ├── test_result_schema.py
│   ├── test_error_handling.py
│   └── test_cases_functional.py    # Section 22 required test cases
│
scripts/
└── pilot_retrieval_benchmark.py    # Section 20 pilot test plan runner, produces the report

benchmark/
└── phase_2_3/
    ├── ef_search_sweep_results.*
    ├── threshold_derivation_results.*
    └── PHASE_2_3_RETRIEVAL_REPORT.md
```

---

# Recommended Implementation Sequence

1. `config.py` (`RetrievalConfig`, `RetrievalFilters`) — settle the config/schema contracts first since everything else depends on them.
2. `schema.py` (`RetrievalResult`, `RetrievalResultItem`) — settle the output contract next.
3. `db/connection.py` — reuse Phase 2.2's connection approach, confirmed read-only credentials/role if available.
4. `preprocessing.py` — query normalization.
5. `embedding.py` — query embedding + prefix handling, with the dedicated prefix unit test (Section 3) written alongside it.
6. `search.py` — pgvector cosine search against the existing HNSW index, confirming operator-class match (Section 4/5) before anything else proceeds.
7. `filters.py` — metadata filter construction, parameterized.
8. `postprocessing.py` — thresholding, dedup, parent/sibling context expansion (Sections 10-12).
9. `provenance.py` — provenance assembly (Section 13).
10. `retriever.py` — wire steps 4-9 together into `LegalRetriever.retrieve(...)`.
11. `errors.py`, `logging_utils.py` — fail-closed error handling and structured logging, integrated into `retriever.py`.
12. `langchain_adapter.py` — LangChain-compatible wrapper around the completed `LegalRetriever`.
13. `scripts/pilot_retrieval_benchmark.py` — run the Section 20 pilot test plan, derive score thresholds (Section 10) and `ef_search` default (Section 6/16) empirically from real measurements.
14. Required test cases (Section 22) and retrieval-quality evaluation (Section 21), using the now-empirically-derived defaults.
15. `PHASE_2_3_RETRIEVAL_REPORT.md` — final report, acceptance criteria checklist (Section 23) verification.

---

# Critical STOP Condition

After the retrieval pipeline is implemented, pilot-tested, and `PHASE_2_3_RETRIEVAL_REPORT.md` is produced:

**STOP.**

Do NOT build the answer-generation chain, add Gemini/LLM calls, add reranking, add agent/LangGraph logic, or expose this over an HTTP API/frontend.

Do NOT start a new full-corpus or pilot-scale embedding/indexing job — this phase only ever reads the index Phase 2.2 already built/is building.

Report to Abishek:

1. Pilot retrieval-quality metrics (Recall@K, Precision@K, MRR) and any divergence from Phase 2.1's offline benchmark, explained.
2. Chosen configuration defaults (`final_k`, `ef_search`, score thresholds, etc.) and the pilot evidence behind each.
3. Confirmation that no writes/DDL were issued against the production database and the background Phase 2.2 indexing job was undisturbed throughout development/testing.
4. Known limitations expected at full 15.7M+ scale (Section 19) that will need revisiting once the production index finishes.
5. Recommended next phase and what it should cover.

**Do not proceed beyond Phase 2.3 automatically.**