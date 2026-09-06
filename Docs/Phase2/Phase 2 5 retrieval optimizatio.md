# Phase 2.5: Retrieval Optimization — Implementation Specification

**Depends on:** Phase 2.3 (frozen baseline retriever), Phase 2.4 (evaluation framework, query set `p24_queries_v1`, ground truth, harness)
**Executing agent:** Antigravity
**Status:** SPECIFICATION ONLY — implementation not yet authorized

---

## 0. Non-Negotiable Constraints

* The Phase 2.3 retriever (`src/retrieval/retriever.py`) is never modified. All new work lives in new modules, wired in as additional `RetrieverAdapter` implementations (interface already defined in Phase 2.4).
* No writes to production PostgreSQL; no DDL/index changes against the live tables. Any lexical index needed for BM25/full-text (e.g., a `tsvector` column + GIN index) is proposed as a **pilot-scoped, reversible** addition and requires explicit sign-off before being applied to the production table — default development target is the existing 1,000-chunk pilot sample and the current partial live corpus, read-only.
* No interference with the running Phase 2.2 indexing job.
* Every experiment uses the Phase 2.4 harness, query set, and ground truth unchanged. No new query set, no new grading scale.
* No Gemini/GPT, no RAG chain, no agent/LangGraph, no frontend, no BGE-base replacement.
* No parameter is tuned to chase a benchmark number without a corresponding experiment showing the change helps; every shipped default must trace to an experiment result in §5.

---

## 1. Goal

Determine, empirically, which of the following changes measurably improve open-world retrieval quality over the frozen Phase 2.3 baseline, using Phase 2.4's metrics — and ship only the changes that do, as configurable, independently toggleable options.

---

## 2. Proposed Modules

| Module | Purpose |
|---|---|
| `src/retrieval/lexical.py` | PostgreSQL full-text/BM25-style lexical search over `chunks.text` (via `ts_rank_cd` on a `tsvector`, or a pilot-scoped extension such as `pg_search`/`ParadeDB` if evaluated — decision logged in §5). Read-only queries; index addition (if any) proposed separately, not auto-applied. |
| `src/retrieval/fusion.py` | Configurable fusion of dense + lexical candidate lists: implement Reciprocal Rank Fusion (RRF) as the default, plus weighted-score fusion as an alternative, both behind a config flag (`fusion_method: rrf | weighted`, `weights: {dense: x, lexical: y}`). |
| `src/retrieval/candidate_pool.py` | Merges dense + lexical candidates, dedupes by `chunk_id`, preserves per-candidate provenance/metadata and per-source raw scores (needed for fusion and later analysis). |
| `src/retrieval/reranker.py` | Thin, swappable interface (`Reranker` protocol, single `rerank(query, candidates) -> ranked candidates` method) with one initial implementation (a cross-encoder, e.g. `BAAI/bge-reranker-base`, chosen for VRAM fit and licensing consistency with the existing BGE family — confirm VRAM/throughput in a small pilot before committing). |
| `src/retrieval/confidence.py` | Threshold calibration: replaces the current fixed `low_confidence_threshold = 0.40` with an empirically-derived threshold (or small decision rule) fit on labeled in-scope vs. out-of-scope queries from the Phase 2.4 set. |
| `src/retrieval/jurisdiction_filter.py` | Optional jurisdiction-aware boosting/filtering: detects when a query's jurisdiction is unambiguous (using the Phase 2.4 `jurisdiction_expectation` labeling logic as a reference, not by re-deriving new NLP) and applies a soft boost (never a hard filter) toward matching-jurisdiction chunks; leaves `jurisdiction_ambiguous` queries untouched. |
| `src/retrieval/adapters.py` | Registers each combination (dense-only [existing baseline], dense+lexical fusion, +reranking, +confidence calibration, +jurisdiction boost) as a distinct `RetrieverAdapter` for the Phase 2.4 harness, so experiments run as harness comparisons, not ad hoc scripts. |
| `configs/p25_experiments/*.yaml` | One config per adapter combination tested (see §5). |

---

## 3. Implementation Order

1. `candidate_pool.py` (dedup/provenance-preserving merge) — needed by everything downstream; testable with synthetic inputs before any real search is wired in.
2. `lexical.py` — get standalone lexical search working and sanity-checked against the pilot 1,000-chunk sample first (cheap, no risk to production).
3. `fusion.py` (RRF first, weighted second) — combine dense (frozen Phase 2.3 retriever output) + lexical via `candidate_pool.py`.
4. `adapters.py` registration for baseline vs. hybrid — run Experiment 1 (§5) before building anything further. **Do not proceed to reranking if hybrid shows no signal without first understanding why.**
5. `reranker.py` — only after hybrid fusion is working end-to-end; run Experiment 2.
6. `confidence.py` — independent of fusion/reranking; can be developed in parallel with steps 2–5 since it only needs the existing dense baseline's scores plus Phase 2.4's in-scope/out-of-scope labels. Run Experiment 3.
7. `jurisdiction_filter.py` — last, since it's the narrowest-scope change; run Experiment 4.
8. Combined best-configuration run (Experiment 5) once individual effects are understood.

---

## 4. Experiments

All experiments run via the Phase 2.4 harness (`run_open_world`, and `run_regression` for the frozen baseline sanity check), against the same corpus snapshot and query set, with the exact snapshot row-count and query/ground-truth version recorded in each run's manifest so results are comparable.

| # | Experiment | Adapter(s) compared | Hypothesis being tested |
|---|---|---|---|
| 1 | Hybrid vs. dense-only | Baseline (dense) vs. dense+lexical (RRF) vs. dense+lexical (weighted) | Does adding lexical candidates recover cases where dense search fails on exact names/section numbers (per Phase 2.3's Case 1/Case 2 failures)? |
| 2 | Reranking | Best config from Exp. 1 vs. same + reranker | Does reranking the merged pool improve ranking quality (NDCG@10, MRR) enough to justify its latency cost? |
| 3 | Confidence calibration | Baseline fixed threshold (0.40) vs. empirically-fit threshold | Does a calibrated threshold reduce the false-confidence rate on `no_evidence_expected` queries without materially hurting Recall@K on in-scope queries? |
| 4 | Jurisdiction-aware boosting | Best config so far vs. same + jurisdiction boost | Does jurisdiction boosting improve jurisdiction correctness rate on `state_specific` queries without degrading `jurisdiction_ambiguous` query metrics? |
| 5 | Combined | Frozen Phase 2.3 baseline vs. best individually-validated combination | Net effect of shipping all validated improvements together vs. the original baseline. |

Each experiment must report a result even if negative — "no measurable improvement" or "regression" is a valid, expected, and useful outcome, and does not block moving to the next experiment unless the module itself is broken.

---

## 5. Metrics (per Phase 2.4, unchanged)

For every experiment: Recall@5/@10/@20 (strict + lenient), Precision@5/@10, MRR, NDCG@10, Success@K, insufficient-evidence / false-confidence rate, jurisdiction correctness rate (Exp. 4 only), latency mean/P50/P95. Report all experiments in one comparison table per §4, plus per-domain/per-jurisdiction breakdowns only for the metrics that moved.

---

## 6. Acceptance Criteria

Phase 2.5 is complete when:

1. Experiments 1–4 are each run independently against the frozen baseline and reported with a clear verdict (improved / no change / regressed), including latency cost.
2. Every shipped default (fusion method, weights, reranker on/off, confidence threshold, jurisdiction boost on/off) is traceable to a specific experiment result — no undocumented tuning.
3. Experiment 5 (combined) is run and reported against the untouched Phase 2.3 baseline using the same Phase 2.4 harness/query set/ground truth.
4. All new components scale to the full 15.7M+ chunk target in principle — lexical search and reranking latency/throughput are measured on the current partial corpus and extrapolated, with any full-corpus-scale index changes explicitly flagged as requiring separate sign-off before production application.
5. No production database or index was modified; Phase 2.2 indexing was not interrupted; the Phase 2.3 baseline file is unchanged (verified by diff/hash).

No numeric performance threshold (e.g., "Recall@10 must reach X") is set in advance — acceptance is about having a rigorous, documented, honest experimental comparison, not hitting a target.

---

## 7. STOP Condition

**STOP** after Experiment 5's report is delivered and reviewed.

Do not: enable any change in a production path, apply any new index to the production database, begin Gemini/GPT or RAG-chain work, or start a new phase — without explicit user sign-off on the Phase 2.5 experimental results.