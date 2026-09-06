# Phase 2.4: Retrieval Evaluation Framework — Engineering Specification

**Project:** BetterCallSaul — Indian Legal Awareness RAG System
**Phase:** 2.4 (Retrieval-Quality Evaluation Framework)
**Depends on:** Phase 2.1 (Embedding Benchmark), Phase 2.2 (Production Vector Index — running), Phase 2.3 (Retrieval Pipeline — implemented, audited)
**Executing agent:** Antigravity
**Author:** Abishek (with Claude)
**Status:** SPECIFICATION ONLY — implementation not yet authorized

---

## 0. Preconditions and Non-Interference Guarantees

Before any implementation work begins, Antigravity must treat the following as hard constraints, not suggestions:

1. **No writes to the production database.** Every component built in this phase is read-only against PostgreSQL. No `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `CREATE INDEX`, `VACUUM`, or any DDL/DML statement may be issued against the `source_documents`, `chunks`, or `embeddings` tables. All evaluation-run artifacts (query sets, judgments, results) are stored as local files (JSONL/Parquet/JSON), never as new database tables, unless explicitly listed in §14 as a *local, evaluation-only* SQLite or DuckDB file.
2. **No interference with the running Phase 2.2 indexing job.** All evaluation queries against PostgreSQL must use short-lived, read-only connections with statement timeouts, and must not hold long transactions or locks. Do not run bulk scans of the `chunks`/`embeddings` tables; use targeted `SELECT`s only.
3. **The Phase 2.3 retriever (`src/retrieval/retriever.py`) is frozen.** Phase 2.4 evaluates it as-is. No tuning of `ef_search`, thresholds, dedup logic, or reranking is permitted inside this phase. If evaluation reveals a desired change, it is logged as a recommendation for a future phase, not implemented here.
4. **No generation layer.** Nothing in Phase 2.4 calls Gemini, GPT, or any LLM for answer synthesis. LangChain, where used, is restricted to data-loading/document utilities (e.g., `Document` objects, evaluators), never to an LLM chain that produces a legal answer.
5. **Corpus-state awareness.** Because Phase 2.2 is still loading, Phase 2.4 must be able to run in two distinct modes (§10) and must record the exact row count of `chunks` at the time of every open-world run, so results are always interpretable against a known corpus size.

---

## 1. Purpose and Evaluation Philosophy

### 1.1 Why this phase exists

Phase 2.3's audit proved that the Phase 2.1 benchmark (48 queries, 1,000-chunk closed candidate pool) is **not a valid quality signal** once the candidate pool grows past its ground-truth boundary. Recall@10 collapsing from 0.79 to 0.19 was not a retriever regression — it was a measurement artifact of judging an open-world system against closed-world labels. Phase 2.4 exists to replace "does the retriever return the one chunk we happened to label" with "does the retriever return material a legal-awareness system could actually use to answer a layman's question, out of everything currently in the corpus."

### 1.2 Closed-world regression testing vs. open-world production evaluation

These are two different instruments measuring two different things, and Phase 2.4 must never conflate them in a single report:

* **Closed-world regression testing** answers: *"Has the retriever's behavior changed on a fixed, small, fully-labeled slice of the corpus?"* The candidate pool and the ground truth are both frozen. This is a **regression test**, not a quality benchmark — it exists to catch code-level regressions (a broken embedding call, a changed distance metric, a bug in dedup) between commits, cheaply and quickly. A score change here is diagnostic of the *system*, not of retrieval quality against the real corpus.
* **Open-world production evaluation** answers: *"Given the full 15.7M+ chunk corpus as it exists today, how well does the retriever surface legally relevant material for realistic layman queries?"* Here the candidate pool is the entire indexed corpus, and ground truth must be built to tolerate the corpus containing many valid answers the annotator never saw at labeling time (§4 — pooling).

Every report produced by this phase must carry an explicit banner stating which of the two modes produced it, the exact corpus row count evaluated against, and the corpus/index configuration snapshot (§12).

### 1.3 What "successful legal retrieval" means for this system

BetterCallSaul is a source-grounded legal-awareness assistant, not a search engine and not an "AI lawyer." Given that framing, retrieval is successful for a query when it surfaces, within the top-K:

* At minimum, one chunk that is **legally sufficient** to ground a correct, non-misleading plain-English answer to the question as a layman would understand it (an "exact" or "sibling/neighbor" relevance grade — see §3.1) — this is the primary bar.
* Ideally, enough surrounding context (parent section, related provisions, and/or a supporting judgment) that the eventual generation layer (a future phase) can cite both the operative legal text and, where relevant, judicial interpretation of it.
* The **correct jurisdiction** for jurisdiction-sensitive queries (a Karnataka Shops & Establishments Act question must not be silently answered with a Kerala provision).
* Honest signaling of **insufficiency** when the corpus genuinely does not contain an answer, rather than confidently returning tangentially related material — a false "we found something" is worse than an honest "we don't have this."

Retrieval is *not* judged as successful merely because it returns text that is topically similar in embedding space; topical similarity without legal sufficiency is exactly the failure mode Phase 2.3's audit exposed (Case 1 and Case 2 — same names/document-title patterns, wrong case/act).

---

## 2. Evaluation Dataset

### 2.1 Scope and sizing

Design and construct a new evaluation query set, versioned independently from the Phase 2.1 48-query set, targeting **150–200 queries** (large enough to give stable per-domain and per-jurisdiction breakdowns across 16 domains, small enough to remain human-annotatable at legal-domain quality). Exact count is decided during annotation (§3.4), not fixed in advance.

### 2.2 Domain coverage

Every query is tagged with exactly one primary `domain` field drawn from the Phase 1B/1C domain taxonomy already in use:

Consumer Protection, Employment & Labour, Workplace Rights, Contracts & Agreements, Property Law (incl. Rental/Tenancy), Family Law, Criminal Law, Motor Vehicles / Traffic, Cyber Law / Digital Law, Banking & Finance, Taxation, Company / Corporate Law, Business & Entrepreneurship, Intellectual Property, Environmental Law, Constitutional Rights.

Add one new cross-cutting tag not present in Phase 1C's taxonomy but required by this spec: `Legal Procedure / Legal Aid` (e.g., "how do I file a consumer complaint," "what is Lok Adalat," "do I need a lawyer for a small claims dispute"). This tag may co-occur with a substantive domain tag as a secondary `procedure_related: true` flag rather than displacing the primary domain.

Target a minimum of **8 queries per domain** (16 domains × 8 = 128 minimum), with additional queries allocated to domains that carry more real-world query volume based on the fireworks-style "preventive legal awareness" use case (Consumer Protection, Employment & Labour, Property Law, Contracts & Agreements, Cyber Law) — these may receive up to 16 queries each.

### 2.3 Jurisdiction coverage

Each query carries a `jurisdiction_expectation` field with one of:
* `central_only` — only central legislation/judgments are correct.
* `state_specific: <state/UT name>` — a specific state or UT's law governs (e.g., Karnataka Shops and Establishments Act).
* `jurisdiction_ambiguous` — the layman question does not specify a state and a competent answer must either ask for clarification or present the central default plus a note that state rules vary (e.g., shop closing hours, rent control, excise-adjacent questions).

At minimum 25% of the query set must carry `state_specific` or `jurisdiction_ambiguous` tags, since jurisdiction handling is a differentiator called out in the project's core design documents and was directly implicated in the Phase 2.3 Case 1 failure (Madras vs. Kerala High Court).

### 2.4 Query-type taxonomy

Each query is tagged with one primary `query_type`:

| Type | Description |
|---|---|
| `easy` | Single clear legal concept, common wording, one obviously correct source. |
| `moderately_ambiguous` | Layman phrasing that maps to more than one plausible legal concept. |
| `multi_concept` | Genuinely requires evidence spanning 2+ legal concepts/domains (e.g., "I was fired while pregnant — what are my rights?" touches Employment & Labour and Constitutional Rights). |
| `jurisdiction_sensitive` | Correctness depends on identifying the right jurisdiction (see §2.3). |
| `legislation_focused` | Best answered primarily from an Act/Rule/notification. |
| `judgment_focused` | Best answered primarily from case law (statutory text alone is insufficient or silent). |
| `mixed_legislation_judgment` | Requires both a statutory provision and judicial interpretation of it. |
| `no_evidence_expected` | The corpus is expected to contain no adequate answer (e.g., a hyper-specific or out-of-scope/non-Indian question) — used to measure honest insufficiency signaling. |
| `clarification_required` | The question as posed is genuinely underspecified (missing state, missing which party, missing timeline) such that a well-designed system should ask a follow-up rather than guess. |

Target distribution (approximate, adjusted during annotation based on what the corpus can actually support): 30% easy, 20% moderately ambiguous, 15% multi-concept, 15% jurisdiction-sensitive (may overlap with other tags), 10% judgment-focused, 5% no-evidence-expected, 5% clarification-required. Overlap across tags (a query can be both `jurisdiction_sensitive` and `multi_concept`) is expected and modeled with a `secondary_tags: []` list rather than forcing single-tag exclusivity.

### 2.5 Difficult / adversarial subset (ties into §7)

A minimum of 20 queries are explicitly constructed as difficult cases, tagged `difficulty_category`, drawn from: vague layman wording, misspellings of legal/party/place names, colloquial phrasing ("my boss won't give me my last salary"), multi-concept mixing, jurisdiction omitted, an incorrect Act/section named by the user, multiple plausible jurisdictions, and no-supporting-evidence-in-corpus. These overlap with, but are annotated on top of, the §2.4 taxonomy.

### 2.6 Query authoring process

* Draft queries in the voice of an actual layman (no legal jargon in the query text itself, mirroring the project's "preventive legal awareness" framing from `legal_awareness_agent_project_context.md`), while the `domain`/`jurisdiction_expectation`/`query_type` metadata carries the precise classification.
* Do not reuse or lightly reword any of the original Phase 2.1 48 queries — the Phase 2.4 set is additive and independent; the 48-query set is preserved unmodified as the regression suite (§10).
* Each query gets a stable `query_id` of the form `p24-<domain_slug>-<sequential_number>` (e.g., `p24-consumer-protection-003`), never reused across versions.

---

## 3. Ground Truth Design

### 3.1 Relevance grade schema

Exact chunk-ID matching is explicitly rejected as the sole relevance criterion (per the Phase 2.3 audit's core finding). Instead, every judged (query, chunk) pair receives one of six ordinal relevance grades:

| Grade | Label | Meaning |
|---:|---|---|
| 4 | `exact_relevant` | This chunk, on its own, is sufficient to correctly and safely ground a plain-English answer to the query. |
| 3 | `sibling_relevant` | A neighboring/sibling chunk from the same section/provision that together with grade-4 (or alone) provides sufficient grounding — e.g., an adjacent sub-section or the immediately following chunk of a split provision. |
| 2 | `parent_relevant` | The parent section/document (a broader chunk than what was retrieved) contains the answer, but this specific chunk alone is too narrow/out of context to ground an answer safely. |
| 1 | `supporting_authority` | A judgment or secondary provision that supports or interprets the answer but is not, by itself, sufficient (e.g., a case interpreting the relevant section, cited alongside the statute). |
| 0.5 | `related_insufficient` | Topically related (same domain/nearby keywords) but does not actually answer the question — this is the grade that distinguishes true relevance from embedding-space topical similarity, directly targeting the Phase 2.3 failure mode. |
| 0 | `irrelevant` | Not related to the query in any way that would help ground an answer. |

Binary recall/precision metrics (§5) are computed using a configurable relevance threshold, with grades ≥3 (`exact_relevant` or `sibling_relevant`) counted as "relevant" for the primary metrics, and a secondary "lenient" metric variant additionally counting grade 2 (`parent_relevant`) as relevant, reported side-by-side. Grade 1 and 0.5 are never counted as relevant for recall/precision but are retained for qualitative failure analysis (§9) and for NDCG's graded-relevance calculation, where the full 0–4 scale is used directly.

### 3.2 Provenance preservation

Every ground-truth judgment record retains full provenance, not just a chunk ID:

```json
{
  "query_id": "p24-consumer-protection-003",
  "chunk_id": "c6e5565dc899110a9c56be97c4828671",
  "parent_document_id": "...",
  "document_title": "...",
  "document_type": "legislation | judgment",
  "jurisdiction": "central | <state/UT>",
  "court": "... (judgments only, else null)",
  "domain": "Consumer Protection",
  "relevance_grade": 4,
  "grade_label": "exact_relevant",
  "annotator_id": "ann_01",
  "annotation_round": 1,
  "notes": "free-text justification, required for grades 3-4 and for any 0.5 grade",
  "annotated_at": "ISO-8601 timestamp"
}
```

`notes` is mandatory (non-empty) for grade ≥3 and for grade 0.5, so that every "this is a real answer" and every "this looks related but isn't" judgment carries a human-readable justification usable in later audits — this is a direct lesson from how useful the Phase 2.3 audit's per-query diagnosis (Case 1, Case 2) turned out to be.

### 3.3 Human / legal-domain annotation process

1. **Annotator qualification.** Annotation is performed by Abishek directly (as the domain-knowledgeable human-in-the-loop, matching the Phase 2.1 process), optionally supplemented by a second annotator for a calibration subset if available. Annotators are not required to be licensed lawyers, but must consult the actual retrieved statutory/judgment text (not rely on memory) before grading, and must have access to search across the full corpus (not just retriever output) to find chunks the retriever missed (this feeds pooling, §4).
2. **Annotation unit.** For each query, the annotator is shown a *pooled* candidate set (§4.2) of chunks — not just what one retriever configuration returned — and grades each on the 0–4 scale of §3.1.
3. **Double-annotation and disagreement handling.** A minimum 15% random subset of (query, chunk) pairs is independently graded twice. Disagreement is defined as a grade difference ≥2 on the ordinal scale, or any disagreement crossing the relevance threshold (one annotator says ≥3, the other says <3). Disagreements are resolved by joint re-review and the resolved grade is marked `resolution: "adjudicated"` with both original grades preserved in `notes`. Compute and report **Cohen's weighted kappa** (linear weights, since the scale is ordinal) on the double-annotated subset as an annotation-quality metric; a kappa <0.4 on any domain triggers a mandatory re-annotation pass for that domain before it is included in a reported open-world run.
4. **Annotation batching.** Annotate in per-domain batches so that partial progress is usable (a domain can be marked "annotation-complete" and used in interim reports while others are still in progress) — consistent with the project's established checkpoint-everything philosophy.

### 3.4 Annotation versioning

The full ground-truth set is versioned (`ground_truth_v1`, `ground_truth_v2`, ...) and never mutated in place; corrections produce a new version with a changelog. Every evaluation report cites the exact ground-truth version used (§12).

---

## 4. Open-World Evaluation Methodology

### 4.1 Why naive labeling fails at 15.7M+ scale

It is infeasible, and was explicitly the Phase 2.3 audit's root-cause finding, to label "all relevant chunks in the corpus" for a query up front — the corpus is too large and growing. Phase 2.4 therefore uses **pooled evaluation**, standard practice in IR evaluation (TREC-style pooling), adapted for this system.

### 4.2 Pooling procedure

For each query in the open-world evaluation set:

1. Run the frozen Phase 2.3 retriever at a generous `top_k` (e.g., top-30, wider than any reported metric's K) against the **current full production corpus**.
2. Additionally run at least one alternate candidate-generation method to widen the pool beyond what the single frozen retriever configuration would find on its own — e.g., a plain keyword/full-text search (`ILIKE`/Postgres `tsvector`, whichever is cheapest and does not require new indexes) over `chunks.text` restricted to the query's named entities (Act names, section numbers, party names) — purely for pool construction, never as an alternate scored system in this phase.
3. Deduplicate and merge these into a single per-query candidate pool (typically 30–60 chunks).
4. Present the full pool to the annotator for grading per §3.
5. **Critically:** any chunk graded ≥3 becomes valid ground truth for that query going forward, regardless of which method surfaced it. A chunk that was not in the Phase 2.1 1,000-chunk sample, or was loaded into the corpus after the original benchmark, is fully eligible to become ground truth. This directly implements "do not assume anything outside the original Phase 2.1 sample is irrelevant."

### 4.3 Handling corpus growth between annotation and evaluation

Because Phase 2.2 is still loading at spec-writing time, pooling is performed against a corpus snapshot, and the snapshot's exact chunk-count and load timestamp is recorded alongside the ground-truth version (§12). If the corpus grows materially (e.g., >10% more chunks) between annotation and a later evaluation run, that run is flagged `pool_staleness_warning: true` in its report header, and a repooling pass is scheduled rather than silently treating old pooled judgments as complete for the new, larger corpus. Full re-pooling against the corpus is explicitly deferred until Phase 2.2 reports completion (per the STOP condition in §15).

### 4.4 Unlabeled-candidate convention

Any chunk returned by an evaluation run that is outside the pooled/graded set is treated as **not-yet-judged**, not as `irrelevant`, and is excluded from precision-affecting calculations by default, but logged and surfaced in reports as `unjudged_hits` so a human can spot-check whether pooling missed something (this prevents the framework itself from silently repeating the Phase 2.3 measurement mistake by treating "not labeled" as "wrong").

---

## 5. Metrics

All metrics are computed twice where applicable: once under the **strict** relevance threshold (grade ≥3) and once under the **lenient** threshold (grade ≥2), always reported side-by-side, never conflated into a single number.

| Metric | Definition | Status |
|---|---|---|
| **Recall@5 / @10 / @20** | Fraction of queries where at least one relevant (≥threshold) chunk appears in the top-K. | Primary |
| **Precision@5 / @10** | Fraction of top-K results that are relevant (≥threshold). | Secondary (expected structurally low given usually few relevant chunks per query — reported for completeness, not optimized against). |
| **MRR** | Mean reciprocal rank of the first relevant (≥threshold) result across all queries. | Primary |
| **NDCG@10** | Normalized Discounted Cumulative Gain using the full 0–4 graded relevance scale (not thresholded), rewarding grade-4 hits ranked higher than grade-1 hits. | Primary — this is the main metric that actually uses the ordinal grading system's information, and is the recommended headline metric for cross-run comparison since it does not collapse graded relevance into a binary. |
| **Success@K** (K=5,10) | Fraction of queries with ≥1 relevant hit in top-K — equivalent to Recall@K when each query has ≥1 relevant chunk, but reported separately and explicitly for `no_evidence_expected` queries, where "success" is inverted (§5.1). | Primary |
| **Coverage / insufficient-evidence rate** | Fraction of queries for which the retriever's own low-confidence signal (the existing `low_confidence_threshold = 0.40` two-tier mechanism in the live retriever) correctly flags insufficiency, cross-tabulated against whether ground truth agrees evidence is genuinely insufficient (see §5.1). | Primary — this is a legal-awareness-specific reliability metric, not a standard IR metric. |
| **Latency mean / P50 / P95** | End-to-end query latency (embedding + DB search + postprocessing), matching the breakdown methodology already established in the Phase 2.3 audit. | Primary |

### 5.1 Special handling for `no_evidence_expected` and `clarification_required` queries

Standard recall/precision are not meaningful for these query types. Instead:

* For `no_evidence_expected`: success = the retriever's low-confidence/insufficiency signal fires (i.e., it does *not* confidently present unrelated material as an answer). Report as a **false-confidence rate**: the fraction of `no_evidence_expected` queries where the system returned high-confidence (above `low_confidence_threshold`) results anyway.
* For `clarification_required`: since Phase 2.3 has no clarification-request logic (that belongs to a future agent/generation phase), Phase 2.4 only measures and reports what the retriever returns and whether it is jurisdiction-mixed (central + multiple states appearing high-ranked with similar scores, which is the retrieval-level signal a future clarification step would need) — no pass/fail judgment is applied to these queries in this phase; they are informational only.

These two query types are excluded from the primary Recall/MRR/NDCG aggregate calculations and reported in their own dedicated subsection (§9) so they don't distort the headline numbers.

---

## 6. Legal-Specific Evaluation

In addition to generic IR metrics, compute the following legal-domain-specific breakdowns for every open-world run:

* **Jurisdiction correctness rate:** for `state_specific` queries, the fraction where the top-K's highest-graded relevant hit matches the expected jurisdiction (not merely "a" relevant hit from any state).
* **Legal-domain correctness rate:** fraction of queries where the top-K's best hit's `domain` metadata matches (or is a reasonable adjacent domain to) the query's tagged domain — a proxy for whether the embedding space is domain-confusing (relevant given the Phase 2.1 domain-level table already showed uneven per-domain performance, e.g., Banking & Finance underperforming most models).
* **Source-type correctness:** for `legislation_focused` queries, fraction where the top hit is `document_type = legislation`; for `judgment_focused`, fraction where a judgment appears in top-K at all (since legislation may also legitimately co-occur).
* **Legislation vs. judgment retrieval balance:** overall ratio of legislation-type vs. judgment-type chunks in top-K results across the whole query set, compared against the corpus's actual legislation:judgment ratio, to detect systemic over/under-retrieval of one type.
* **Current vs. historical material:** where date metadata permits (amendment dates, repeal flags if present in metadata), flag any top-ranked chunk that is superseded/repealed material, reported as a `stale_law_hits` count — flagged for future work, not blocking Phase 2.4 acceptance, since date/repeal metadata completeness has not been verified as part of this corpus and may be a Phase 1B/1C metadata gap.
* **Provenance completeness:** fraction of top-K results across all queries that carry a complete provenance chain (document_id, title, jurisdiction, section/page where applicable, source reference) — any result missing required provenance fields is logged, since citation traceability is a stated system requirement (`legal_awareness_agent_project_context.md` §16).

---

## 7. Difficult Query Evaluation

The difficulty subset from §2.5 is evaluated using the same metrics as §5, but reported in its own isolated breakdown table (never averaged into the "easy" query numbers), specifically covering:

* Vague layman wording vs. precise legal wording — compare metrics for queries with a `precise_paraphrase` companion query (an optional paired precise version of the same underlying question) where available, to quantify the "layman phrasing penalty."
* Misspelled entity names (person names, Act names) — since Case 1 in the Phase 2.3 audit showed name-collision failures even without misspellings, this subset specifically stress-tests whether misspellings make entity confusion worse.
* Colloquial phrasing.
* Multi-concept mixing.
* Missing jurisdiction.
* User-cited wrong Act/section (the query names an incorrect provision — success here means retrieval isn't anchored to the wrong named entity and still finds the actually-correct provision).
* Multiple plausible jurisdictions.
* No supporting evidence in the corpus (overlaps with `no_evidence_expected`, evaluated per §5.1).

---

## 8. Baseline / Comparison Framework

### 8.1 Baseline definition

The **Baseline** configuration for all Phase 2.4 reports is fixed and explicitly recorded:

* Embedding model: `BAAI/bge-base-en-v1.5` (768-d), FP16 GPU inference.
* Vector index: PostgreSQL + pgvector, HNSW, `m=16`, `ef_construction=64`, `ef_search=64`.
* Retriever: `src/retrieval/retriever.py` as implemented in Phase 2.3, including current two-tier `low_confidence_threshold = 0.40`, deduplication, and parent-section context expansion — unmodified.

### 8.2 Extensibility, not implementation

Build the evaluation harness so that a "system under test" is a pluggable interface (e.g., a `RetrieverAdapter` protocol/abstract base with a single `retrieve(query, top_k) -> List[ScoredChunk]` method) so that **future** phases can register hybrid/BM25 retrieval, reranking, or alternative embedding models as additional adapters and reuse the same query set, ground truth, and metrics code without rewriting the harness. Phase 2.4 implements and registers exactly one adapter — the frozen Baseline — and explicitly does not implement, benchmark, or enable any second adapter. The harness's comparison-report code path may be built (so future phases don't have to redesign it), but it is only exercised with a single system in Phase 2.4's own runs.

---

## 9. Evaluation Reporting

Every run (closed-world or open-world) produces a versioned Markdown report plus a machine-readable JSON alongside it, containing:

1. **Run header/banner** — mode (closed-world/open-world), corpus row count, ground-truth version, code/config snapshot reference, timestamp (full detail in §12).
2. **Overall metrics** — the §5 metrics table, strict and lenient thresholds side by side.
3. **Per-domain metrics** — all §5 metrics broken out per the 16 domains of §2.2.
4. **Per-jurisdiction metrics** — central vs. each represented state/UT, plus the `jurisdiction_ambiguous` bucket reported separately.
5. **Legislation vs. judgment metrics** — per §6, split by `legislation_focused`/`judgment_focused`/`mixed` query types.
6. **Query difficulty breakdown** — per §2.4/§7, one row per `query_type` and one row per `difficulty_category`.
7. **Failure cases** — every query scoring 0 on the strict Recall@10, listed with query text, expected domain/jurisdiction, and the top-3 actually-retrieved chunks with their titles — modeled directly on the Phase 2.3 audit's "Case 1 / Case 2" deep-inspection format, since that format proved highly diagnostic.
8. **Top false positives** — chunks that repeatedly rank high across many unrelated queries (a signal of an over-attracting/generic chunk in the index).
9. **Top false negatives** — ground-truth-relevant chunks that are consistently outranked; include their rank position and the cosine score gap to the actual top-1.
10. **Latency distribution** — mean/P50/P95, plus a breakdown by pipeline stage matching the Phase 2.3 latency table format.
11. **Insufficient-evidence behavior** — the §5.1 false-confidence rate and any `clarification_required` jurisdiction-mixing signal.
12. **`no_evidence_expected` / `clarification_required` subsection** — reported separately per §5.1, never folded into headline numbers.
13. **Annotation quality** — Cohen's weighted kappa from §3.3, per domain.

---

## 10. Regression Testing

* The original Phase 2.1 48-query set and its `relevance_judgments.jsonl` (exact-chunk-ID ground truth over the 1,000-chunk sample) are copied byte-for-byte into this phase's evaluation harness as the **frozen regression suite**, stored under a clearly separate path/namespace from the new Phase 2.4 dataset, and never edited.
* A `run_regression()` entry point in the harness runs the frozen retriever against only the 1,000-chunk isolated pilot subset (reusing the Phase 2.3 audit's Experiment C methodology — restricting candidate search to the pilot 1,000 chunk IDs) and reproduces exact-chunk-ID Recall@5/@10, Precision@5/@10, MRR. This is a fast, cheap, CI-style check: expected result is a match (within floating-point/ANN-nondeterminism tolerance) to the Phase 2.1/Experiment-C numbers (Recall@10 ≈ 0.7917, MRR ≈ 0.66) every time it is run, since nothing about the pilot subset or the frozen retriever should have changed.
* A `run_open_world()` entry point runs the new Phase 2.4 query set with pooled ground truth against the live full corpus, per §4.
* The two entry points are kept in the same harness/CLI but never merged into one report — the regression report and the open-world report are always separate files (§9 header banner makes the mode explicit either way, as a second layer of protection against re-conflating them).

---

## 11. Acceptance Criteria

Because no open-world quality baseline currently exists for this system (the only prior open-world numbers, from the Phase 2.3 audit, were incidental byproducts of an audit rather than a designed evaluation), Phase 2.4 does **not** invent a pass/fail performance threshold such as "Recall@10 must exceed 0.6." Instead, acceptance criteria are process- and infrastructure-oriented:

Phase 2.4 is considered **complete and accepted** when:

1. The evaluation query set (§2) is authored, reviewed, and versioned, with domain/jurisdiction/query-type coverage targets from §2.2–§2.5 met or explicitly documented as unmet with reason.
2. Ground truth (§3) is annotated for at least the closed pool needed to run a first open-world evaluation, with double-annotation Cohen's kappa ≥0.4 achieved (or re-annotated until achieved) on every domain included in the first report.
3. The pooled open-world methodology (§4) is implemented and demonstrably produces pools materially different from (broader than) the original 1,000-chunk sample for at least a sample of queries, confirmed by a spot-check.
4. All metrics in §5 are implemented, unit-tested against hand-computed toy examples, and produce output matching the Phase 2.3 audit's own reproduced numbers when run in regression mode (§10) — this is the concrete, checkable proxy for "the harness is correct," replacing an arbitrary quality threshold.
5. The reporting format (§9) is implemented and produces both a first **regression** report and a first **open-world** report (the latter necessarily run against whatever partial corpus exists at the time — see §15 for the constraint that a *full-corpus* open-world run awaits Phase 2.2 completion).
6. The first open-world report's numbers (whatever they are) become the **documented empirical baseline** for future comparison — e.g., "Recall@10 (strict) = X, NDCG@10 = Y as of corpus snapshot Z chunks" — explicitly recorded as a baseline-to-improve-upon rather than a target that was hit or missed.
7. No production database writes or index modifications occurred during development or execution (verified via the same read-only audit method used in Phase 2.3, i.e., checking Postgres logs / `pg_stat_statements` for any non-`SELECT` activity attributable to the evaluation harness).

Future phases may set numeric thresholds (e.g., "Recall@10 strict ≥ baseline + 10%") once this baseline exists — that is explicitly out of scope here.

---

## 12. Reproducibility

Every evaluation run, closed-world or open-world, must emit a `run_manifest.json` capturing:

```json
{
  "run_id": "uuid",
  "run_mode": "closed_world_regression | open_world",
  "timestamp_utc": "ISO-8601",
  "eval_dataset_version": "p24_queries_v1",
  "ground_truth_version": "ground_truth_v1",
  "corpus_snapshot": {
    "chunks_row_count": 0,
    "embeddings_row_count": 0,
    "snapshot_taken_at": "ISO-8601"
  },
  "embedding_model": "BAAI/bge-base-en-v1.5",
  "embedding_model_revision": "<HF commit hash if resolvable>",
  "index_config": {
    "index_type": "HNSW",
    "m": 16,
    "ef_construction": 64,
    "ef_search": 64,
    "distance_metric": "cosine"
  },
  "retriever_code_version": "<git commit hash of src/retrieval/retriever.py>",
  "harness_code_version": "<git commit hash of Phase 2.4 harness>",
  "random_seed": 42,
  "python_env_lockfile_hash": "<hash of requirements/lockfile>",
  "reproducible_command": "python -m eval.run --mode open_world --config configs/p24_baseline.yaml"
}
```

* A fixed `random_seed` is used everywhere randomness appears (pooling tie-breaks, double-annotation subset sampling) so subset selection is reproducible.
* Configuration is never hardcoded inline in scripts; all run parameters live in a versioned YAML config file under `configs/`, and the manifest records which config file (and its content hash) produced the run.
* The evaluation dataset and ground truth files are stored with a version suffix in the filename and are treated as append-only/immutable once referenced by any published report.

---

## 13. Privacy and Safety

* All evaluation queries are **synthetic, author-written layman questions**, not real user conversations or real users' legal cases — consistent with the project's data-minimization principle already established in `legal_awareness_agent_project_context.md` §13.
* No real names, addresses, ID numbers, or case-specific personal details are used in query text; party names appearing in queries (e.g., in the "misspelled name" difficulty category) reference names that already appear in the public judgment corpus being retrieved from (i.e., referencing a public court record's named parties, not inventing or exposing private third-party data).
* Evaluation logs (latency logs, retrieved-chunk logs) are stored locally under the project's evaluation directory and are not uploaded anywhere requiring authentication beyond what's already used for the project's own Google Drive checkpointing, and contain no user-identifying data since there are no real users in this phase.

---

## 14. Implementation Plan

Build in this order, each step checkpointed and independently runnable before proceeding to the next:

1. **`eval/schemas.py`** — Pydantic models for `EvalQuery`, `RelevanceJudgment`, `RunManifest`, `ScoredChunk`, `RetrieverAdapter` protocol. No I/O.
2. **`eval/queries/p24_queries_v1.jsonl`** — the authored §2 query set (data, not code).
3. **`eval/pooling.py`** — pooled candidate-generation logic (§4.2): wraps the frozen retriever plus the auxiliary keyword-search candidate generator, merges and dedupes into per-query pools. Read-only DB access, short-lived connections, statement timeout enforced.
4. **`eval/annotation_tool.py`** — a minimal local CLI or notebook-driven tool that presents pooled candidates per query for grading, writes `RelevanceJudgment` records to `eval/ground_truth/ground_truth_v1.jsonl`, and computes running Cohen's kappa on the double-annotated subset as annotation proceeds.
5. **`eval/metrics.py`** — implementations of every metric in §5, each unit-tested against hand-computed toy fixtures before being run against real data.
6. **`eval/harness.py`** — orchestrates `run_regression()` and `run_open_world()` (§10), calling the frozen `RetrieverAdapter` (baseline, §8), computing metrics, and assembling the manifest (§12).
7. **`eval/report_builder.py`** — produces the Markdown + JSON report format of §9 from a harness run's raw output.
8. **`configs/p24_regression.yaml`**, **`configs/p24_open_world_baseline.yaml`** — run configurations.
9. **`eval/run.py`** — thin CLI entry point (`python -m eval.run --mode ...`) wiring the above together, matching the existing `main.py` CLI pattern already used in Phase 0.
10. First execution: `run_regression()` only, to validate the harness reproduces Phase 2.1/Experiment-C numbers (Acceptance Criterion 4).
11. Only after (10) passes: run `run_open_world()` against whatever corpus state currently exists, producing the first documented empirical baseline (Acceptance Criterion 6), clearly labeled with the partial corpus row count.

Do not begin implementing any Phase 2.5+ (generation/agent) code as part of this sequence, even opportunistically.

---

## 15. Phase Boundary — What Phase 2.4 Must NOT Implement

Phase 2.4 is retrieval evaluation only. Explicitly out of scope, and must not be built, even partially:

* No Gemini/GPT (or any LLM) answer generation of any kind.
* No final RAG chain assembling retrieved context into a prompt for generation.
* No agent or LangGraph orchestration logic.
* No frontend/UI of any kind.
* No automatic legal advice generation or "answer" surfaces — this phase produces metrics and reports about retrieval, not user-facing answers.
* No production retrieval algorithm changes — the Phase 2.3 retriever's thresholds, dedup logic, or reranking are not modified, tuned, or A/B tested against production traffic.
* No automatic reranking or hybrid-search implementation or optimization — the pluggable `RetrieverAdapter` interface (§8.2) is built for future extensibility but is not populated with a second adapter in this phase.
* No modification to the production PostgreSQL database or its indexes.
* No interference with the running Phase 2.2 indexing job.
* **No automatic full-corpus open-world evaluation run against an incomplete production corpus as a final/authoritative report** — interim open-world runs against the partial corpus are permitted and expected during development (and required for Acceptance Criterion 6), but must be clearly labeled as provisional/partial-corpus baselines. The comprehensive, citable open-world evaluation is explicitly deferred until Phase 2.2 reports full-corpus completion, at which point a repooling pass (§4.3) and a final full-corpus run should be scheduled as part of a subsequent phase (candidate: Phase 2.5 or a "Phase 2.4 final run" checkpoint), not automatically triggered by this spec.

---

## 16. Critical STOP Condition

**STOP.**

Once this specification is implemented per §14 through the first regression run and the first provisional open-world baseline run, Antigravity must halt.

* Do **not** proceed to Gemini/GPT answer generation, RAG chain construction, or agent/LangGraph work.
* Do **not** treat the provisional open-world baseline (run against the still-growing corpus) as a final acceptance number — it is a documented starting point only.
* Do **not** modify the production database, its indexes, or the running Phase 2.2 indexing job at any point during this phase.
* Do **not** modify the frozen Phase 2.3 retriever.
* Await user review and sign-off on the Phase 2.4 evaluation framework and its first baseline report before any Phase 2.5 work (answer generation) is scoped or specified.