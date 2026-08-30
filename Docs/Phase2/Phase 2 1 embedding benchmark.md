# Project Context

We are building a **Legal Awareness AI / Agentic RAG system for Indian law** ("Better Call Saul").

The target users are **laymen users who have little or no knowledge of the law relevant to the domain or situation they are asking about**.

Prior phases:

* **Phase 1A (complete):** Acquired ~15.7 million filtered records (~28.8 GB) from the `vaquill/open-india-law` HuggingFace dataset, checkpointed to Google Drive.
* **Phase 1B (complete/near-complete):** Corpus inspection, normalization, schema/domain/jurisdiction classification, deduplication. Final corpus expected to be **10M+ normalized records**.
* **Phase 1C (complete/near-complete):** Legal-aware, structure-preserving chunking of normalized records into a Parquet-based chunked corpus (`03_chunked/legislation/`, `03_chunked/judgments/`, `03_chunked/other/`), with rich per-chunk metadata (domain, jurisdiction, act/section/subsection, court, case citation, provenance, etc.).

Phase 1B and Phase 1C outputs may still be growing/finalizing. This phase must not assume they are 100% complete.

Hardware profile:

* CPU: Intel i5-14400F (10 Cores / 16 Threads)
* RAM: 32 GB DDR5
* GPU: NVIDIA GeForce RTX 5060 (**8 GB VRAM**)
* OS: Windows

The eventual architecture remains:

```text
User → React Frontend → FastAPI Backend → Query Understanding
  → RAG (simple) / Agent (complex) → Evidence Layer → LLM (Gemini, model-agnostic)
  → Plain-English Answer + Citations
```

This phase — **Phase 2.1: Embedding Model Benchmarking** — sits between the chunked corpus (Phase 1C) and full-scale embedding/vector-index construction (a future phase). Its sole purpose is to select an embedding model with evidence, before committing GPU-hours and storage to embedding 10M+ chunks.

---

# Phase 2.1 Objective

> **Determine, with reproducible quantitative evidence on our actual legal corpus, which embedding model should be used to embed the full Better Call Saul chunk corpus — and document why.**

This is a **benchmarking/decision phase**, not a production-build phase. It produces:

1. A small, representative, reusable evaluation dataset (chunks + queries + relevance judgments).
2. Local embeddings of that sample for each candidate model.
3. Retrieval-quality metrics (Recall@K, Precision@K, MRR) per model.
4. Practical performance metrics per model (speed, VRAM, dimensionality, projected storage).
5. A written comparison and a single recommended model with justification.

---

# Candidate Models

Benchmark, at minimum, these models:

| Model | Type | Notes |
|---|---|---|
| `l3cube-pune/indian-legal-sentences` | Domain-specific (Indian legal) | Candidate for legal-domain specialization |
| `BAAI/bge-base-en-v1.5` | General-purpose, mid-size | Strong general baseline |
| `BAAI/bge-large-en-v1.5` | General-purpose, large | Higher quality ceiling, higher cost |

Optionally include:

| Model | Type | Notes |
|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | Lightweight general-purpose | Already used in the Phase 0 RAG_V0 baseline; useful as a cheap/fast reference point |

Design the benchmark harness so that **additional candidate models can be added later via configuration**, without rewriting the pipeline (model-agnostic embedding loader).

For each model, record from its model card/documentation (do not guess):

* Native embedding dimensionality
* Max input sequence length / token limit
* Whether it requires special query/passage prefixes (e.g. BGE's `"Represent this sentence for searching relevant passages: "` query instruction) — if so, this MUST be applied correctly and consistently, since omitting it materially degrades BGE retrieval quality
* License terms (must confirm each model is usable for this project)

---

# Step 1 — Representative Sample of Phase 1C Chunks

Do NOT use the full chunked corpus.

Build a **sampling script** that:

1. Reads the Phase 1C manifest/checkpoint to find chunk batch files currently marked complete (respecting the Phase 1B/1C producer-consumer parallelism already established — never read a batch file that is still being written).
2. Draws a **stratified sample** across:
   * Source type (legislation vs. judgment vs. other)
   * Domain (cover as many of the ~15+ Phase 1B/1C domain categories as have sufficient volume — e.g. Consumer Protection, Employment & Labour, Family Law, Criminal Law, Property Law, Cyber Law, Company Law, Constitutional Rights, Taxation, Environmental Law, etc.)
   * Jurisdiction (central and, where available, state/UT)
3. Targets a sample size that is **large enough to be statistically meaningful but small enough to embed quickly on an 8GB GPU** — target on the order of **5,000–20,000 chunks** total (exact number left to Antigravity's judgment based on domain coverage needs; must be documented and configurable).
4. Persists the sampled chunk set to a dedicated benchmark directory (e.g. `benchmark/phase_2_1/sampled_chunks.parquet`) with full original metadata intact, so the sample is reusable across model runs and reproducible on rerun (fixed random seed).

This sampling step must be clearly separated from, and must never mutate, the Phase 1B/1C authoritative outputs.

---

# Step 2 — Evaluation Query Set

Construct a small, hand-curated (or carefully LLM-assisted-then-human-reviewed) set of **realistic layman Indian-law questions**.

Requirements:

* Target **at least 40–60 queries** (exact count documented; more is better if time allows).
* Questions must be phrased the way an actual layman would ask them — conversational, not legal-jargon search queries. Example style: *"My landlord won't return my rental deposit, what can I do?"* rather than *"Section 108 Transfer of Property Act tenancy deposit remedy."*
* Cover **multiple legal domains** (spread across the Phase 1B/1C domain taxonomy — consumer, employment, family, property/tenancy, criminal, cyber/online fraud, company/corporate, constitutional rights, taxation, environmental, etc.).
* Cover **multiple jurisdictions** where the sample allows (central law questions and at least some state/UT-specific questions).
* Include a mix of:
  * Simple factual questions (should map to 1 clearly relevant chunk/section)
  * Slightly broader questions (should map to 2–4 relevant chunks)
* Store as a structured file (e.g. `benchmark/phase_2_1/eval_queries.jsonl` or `.csv`) with fields such as: `query_id`, `query_text`, `domain`, `jurisdiction`, `difficulty` (simple/moderate).

---

# Step 3 — Relevance Judgments (Ground Truth)

For each query, establish the expected relevant chunk(s)/document(s) from the sampled set.

Requirements:

* Produce a mapping of `query_id → [chunk_id, ...]` marking which sampled chunks are genuinely relevant evidence for that query.
* This is a **manual/human-reviewed step** (Antigravity may assist by proposing candidates via keyword/metadata search over the sample, but a human — Abishek — must confirm relevance before it is treated as ground truth). The spec must make clear that unreviewed auto-generated relevance labels are not acceptable as final ground truth.
* Allow **graded relevance** if practical (e.g. `2 = directly answers`, `1 = related/background`, `0 = not relevant`), but binary relevance is acceptable as a minimum.
* Store as `benchmark/phase_2_1/relevance_judgments.jsonl` (or `.csv`), separate from the query file, keyed by `query_id`.
* Document any query for which **no relevant chunk exists in the sample** (this can happen since only a subset of the corpus is sampled) — such queries should be excluded from metric computation or flagged, not silently scored as failures of the embedding model.

---

# Step 4 — Local Embedding Generation

For each candidate model:

1. Load the model locally (Sentence-Transformers / HuggingFace `transformers`, whichever is appropriate per model) and run inference on the **RTX 5060 (8GB VRAM)** via CUDA.
2. Embed:
   * All sampled chunks (Step 1)
   * All evaluation queries (Step 2), applying the model's correct query-side instruction/prefix if required
3. Respect the 8GB VRAM ceiling:
   * Use appropriately small batch sizes per model (larger models like `bge-large-en-v1.5` will need smaller batches than `MiniLM`)
   * Use FP16/mixed precision where supported to reduce VRAM footprint and increase throughput
   * If a model's max batch will not fit in 8GB even at batch size 1 for the longest chunks, document this as a finding rather than crashing — truncate or chunk-split only for the benchmark measurement, and note the implication for full-corpus embedding
4. Persist embeddings per model to disk (e.g. `benchmark/phase_2_1/embeddings/{model_name}/chunks.npy` + an id-alignment file, and `.../queries.npy`) so metric computation can be rerun without re-embedding.
5. Record for each model, during this step:
   * Total wall-clock time to embed the sample
   * Chunks/sec throughput
   * Peak VRAM usage (via `torch.cuda.max_memory_allocated()` or equivalent)
   * Actual output embedding dimensionality
   * Any OOM errors or batch-size adjustments made

---

# Step 5 — Retrieval Evaluation

For each candidate model, using its own embeddings from Step 4:

1. For each evaluation query, compute cosine similarity (or the model-recommended similarity metric) between the query embedding and all sampled chunk embeddings.
2. Rank chunks by similarity and take the top-K for K values including at least **K = 5** and **K = 10** (document exact K values used).
3. Compare the top-K results against the relevance judgments (Step 3) to compute, per query and then averaged across the query set:
   * **Recall@K**
   * **Precision@K**
   * **MRR (Mean Reciprocal Rank)** — rank of the first relevant result
4. Break down results by **domain** and by **query difficulty** (simple vs. moderate) in addition to overall averages, so domain-specific strengths/weaknesses (e.g. does the legal-specific model outperform general models specifically on legal-terminology-heavy queries?) are visible.
5. Exclude/flag queries with no ground-truth relevant chunk in the sample (per Step 3) from metric averages, and report how many queries were excluded.

---

# Step 6 — Practical Performance & Storage Projection

For each model, using the measurements from Step 4, project **full-corpus** implications (10M+ chunks — use the actual current Phase 1C chunk count if available at benchmark time, otherwise a clearly labeled estimate):

* Estimated total embedding time at full corpus scale (based on measured chunks/sec, single RTX 5060)
* Estimated VRAM feasibility at full scale (this is about batch/runtime feasibility, not cumulative VRAM — clarify that VRAM usage is per-batch, not per-corpus)
* Estimated on-disk storage for the full corpus's embeddings, computed as:
  `num_chunks × dimensionality × bytes_per_value` (state the precision assumed, e.g. float32 vs float16)
* Estimated PostgreSQL/pgvector storage impact at full scale, consistent with the storage-footprint reasoning already used in Phase 1B planning (~35–40 GB was estimated there for a 384-dim model at 15.7M chunks — recompute proportionally for each candidate's actual dimensionality)

---

# Step 7 — Domain-Specific vs. General-Purpose Comparison

Produce an explicit comparative analysis answering:

* Does `l3cube-pune/indian-legal-sentences` outperform the general-purpose BGE models on legal-domain queries, and by how much (in Recall@K/Precision@K/MRR terms)?
* Is any quality advantage large enough to justify its dimensionality/speed/storage trade-offs versus `bge-base-en-v1.5` and `bge-large-en-v1.5`?
* How does the lightweight `all-MiniLM-L6-v2` baseline (if included) compare — is it a viable low-cost option, or does it lose too much retrieval quality for legal text?
* Are there specific domains or query types where one model clearly wins and another clearly loses (rather than one model being uniformly better)?

---

# Step 8 — Benchmark Report

Produce a final Markdown report: `benchmark/phase_2_1/PHASE_2_1_BENCHMARK_REPORT.md`.

Required contents:

1. **Methodology summary** — sample size/strategy, query set size/composition, ground-truth process.
2. **Per-model results table** — Recall@5, Recall@10, Precision@5, Precision@10, MRR, embedding dimensionality, throughput (chunks/sec), peak VRAM (GB), projected full-corpus embedding time, projected full-corpus storage (GB).
3. **Domain-level breakdown** — retrieval quality per model per domain.
4. **Practical trade-off discussion** — quality vs. speed vs. storage vs. VRAM feasibility.
5. **Explicit recommendation** answering, in plain terms:
   > **Which embedding model should Better Call Saul use, and why?**
   The recommendation must weigh retrieval quality against practical constraints (VRAM, projected embedding time for 10M+ chunks, storage), not quality alone.
6. **Caveats/limitations** — sample size limitations, ground-truth subjectivity, any queries excluded, any models that couldn't be run at full precision/batch size due to VRAM.
7. **Recommended next steps** (pointing to, but not starting, the next phase).

---

# Reproducibility Requirements

* All random sampling (Step 1) must use a fixed, documented random seed.
* All scripts (sampling, embedding, evaluation) must be runnable independently and idempotently — rerunning the embedding step for one model should not require re-sampling or re-embedding other models.
* All intermediate artifacts (sample, queries, relevance judgments, per-model embeddings, computed metrics) must be persisted to disk, not just printed, so the benchmark can be audited or extended later (e.g. adding a new candidate model without redoing everything).
* Configuration (model list, K values, batch sizes, sample size) should live in a single config file, not hardcoded across scripts.

---

# Explicit Non-Goals (Guardrails)

This phase must NOT:

* Embed the full 10M+ chunk corpus.
* Build or write to the production vector database (pgvector/PostgreSQL).
* Build a retriever, reranker, or agent.
* Modify or delete any Phase 1A/1B/1C authoritative outputs.
* Assume Phase 1B or Phase 1C has fully finished — read only batches/files marked complete at the time this phase runs.
* Automatically proceed to full-corpus embedding or vector index construction after the report is generated.

---

# Phase 2.1 Completion Criteria

Phase 2.1 is complete when:

* [ ] A reproducible, stratified sample of Phase 1C chunks has been drawn and persisted
* [ ] A realistic, domain- and jurisdiction-diverse layman query set (≥40–60 queries) has been created
* [ ] Human-reviewed relevance judgments exist for each query
* [ ] Embeddings have been generated locally on the RTX 5060 for every candidate model (`l3cube-pune/indian-legal-sentences`, `bge-base-en-v1.5`, `bge-large-en-v1.5`, and optionally `all-MiniLM-L6-v2`)
* [ ] Recall@K, Precision@K, and MRR have been computed per model, overall and per-domain
* [ ] Throughput, peak VRAM, dimensionality, and projected full-corpus time/storage have been recorded per model
* [ ] Domain-specific vs. general-purpose models have been explicitly compared
* [ ] `PHASE_2_1_BENCHMARK_REPORT.md` has been produced with a clear, justified recommendation
* [ ] No full-corpus embedding or vector database work has been started

---

# Critical STOP Condition

After Phase 2.1's report is produced:

**STOP.**

Do NOT automatically begin full-corpus embedding, vector database construction, or retriever/agent work.

The recommended embedding model, its dimensionality, and its projected time/storage costs become inputs to a future phase (**RAG Index Design & Full-Corpus Embedding**), where index type, hybrid retrieval, metadata filtering, and reranking will be designed. That phase requires separate human sign-off on the model choice before proceeding.

**Do not proceed beyond Phase 2.1 automatically.**