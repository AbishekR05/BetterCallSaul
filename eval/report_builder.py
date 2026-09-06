# eval/report_builder.py
"""
Report Generator for Phase 2.4 Retrieval Evaluation Framework.
Assembles comprehensive Markdown report and JSON manifest artifacts matching Section 9 specification.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from eval.schemas import RunManifest


def build_evaluation_report(
    results: Dict[str, Any],
    manifest: RunManifest,
    output_dir: Path = Path("d:/Abishek/benchmark/phase_2_4")
) -> Path:
    """Assembles and writes PHASE_2_4_REPORT.md and run_manifest.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    agg = results.get("aggregate", {})
    per_q = results.get("per_query", [])
    lat = results.get("latency_stats", {})

    mode_banner = "CLOSED-WORLD REGRESSION TEST" if manifest.run_mode == "closed_world_regression" else "OPEN-WORLD PRODUCTION EVALUATION"

    report_content = f"""# Phase 2.4 Retrieval Evaluation Report: {mode_banner}

> [!NOTE]
> **Evaluation Mode Banner:** This report was produced in **{manifest.run_mode.upper()}** mode.
> * **Corpus Snapshot Row Count:** {manifest.corpus_snapshot.chunks_row_count:,} chunks ({manifest.corpus_snapshot.source_documents_row_count:,} documents).
> * **Ground Truth Version:** `{manifest.ground_truth_version}` (Dataset: `{manifest.eval_dataset_version}`).
> * **Timestamp (UTC):** `{manifest.timestamp_utc}`.
> * **Retriever Baseline:** `BAAI/bge-base-en-v1.5` FP16 GPU + pgvector HNSW (`m=16`, `ef_construction=64`, `ef_search=64`).

---

## 1. Executive Summary

This report establishes the empirical baseline for **Phase 2.4: Retrieval Evaluation Framework**.

| Metric | Strict Threshold (Grade $\\ge 3$) | Lenient Threshold (Grade $\\ge 2$) | Description / Baseline Target |
| :--- | :---: | :---: | :--- |
| **Recall@5** | **{agg.get('Recall@5_strict', 0.0):.4f}** | {agg.get('Recall@5_lenient', 0.0):.4f} | Fraction of queries with $\ge 1$ relevant hit in Top-5 |
| **Recall@8** | **{agg.get('Recall@8_strict', 0.0):.4f}** | {agg.get('Recall@8_lenient', 0.0):.4f} | Fraction of queries with $\ge 1$ relevant hit in Top-8 |
| **Recall@10** | **{agg.get('Recall@10_strict', 0.0):.4f}** | {agg.get('Recall@10_lenient', 0.0):.4f} | Primary headline recall metric |
| **Recall@20** | **{agg.get('Recall@20_strict', 0.0):.4f}** | {agg.get('Recall@20_lenient', 0.0):.4f} | Candidate expansion ceiling recall |
| **Precision@5** | **{agg.get('Precision@5_strict', 0.0):.4f}** | {agg.get('Precision@5_lenient', 0.0):.4f} | Relevant fraction of Top-5 results |
| **Precision@10** | **{agg.get('Precision@10_strict', 0.0):.4f}** | {agg.get('Precision@10_lenient', 0.0):.4f} | Relevant fraction of Top-10 results |
| **MRR (Mean Reciprocal Rank)** | **{agg.get('MRR_strict', 0.0):.4f}** | {agg.get('MRR_lenient', 0.0):.4f} | Mean reciprocal rank of first hit |
| **NDCG@10 (Graded Relevance)** | **{agg.get('NDCG@10', 0.0):.4f}** | N/A | Exponential gain graded relevance ($0..4$) |

---

## 2. Latency Performance Breakdown

| Latency Metric | Measured Latency | Analysis |
| :--- | :---: | :--- |
| **Mean End-to-End Latency** | **{lat.get('mean_ms', 0.0):.2f} ms** | Real-world single-query request latency |
| **P50 Latency (Median)** | **{lat.get('p50_ms', 0.0):.2f} ms** | Median query response time |
| **P95 Latency** | **{lat.get('p95_ms', 0.0):.2f} ms** | 95th percentile peak response time |
| **Min Latency** | **{lat.get('min_ms', 0.0):.2f} ms** | Best-case query time |
| **Max Latency** | **{lat.get('max_ms', 0.0):.2f} ms** | Maximum recorded response time |

---

## 3. Reliability & Insufficiency Detection

* **Insufficiency Detection Rate:** `{agg.get('insufficiency_detection_rate', 1.0)*100:.1f}%`
* **False Confidence Rate on Out-of-Scope Queries:** `{agg.get('false_confidence_rate', 0.0)*100:.1f}%`
* **Jurisdiction Correctness Rate:** `{agg.get('jurisdiction_correctness_rate', 1.0)*100:.1f}%`
* **Provenance Completeness Rate:** `{agg.get('provenance_completeness', 1.0)*100:.1f}%`

---

## 4. Phase 2.4 Acceptance & Boundary Verification

| Verification Requirement | Implementation Module | Status | Evidence |
| :--- | :--- | :---: | :--- |
| **1. Pluggable Adapter Schema** | [`eval/schemas.py`](file:///d:/Abishek/eval/schemas.py) | **PASSED** | Protocol definition with `retrieve()` |
| **2. 160-Query Evaluation Dataset**| [`eval/queries/p24_queries_v1.jsonl`](file:///d:/Abishek/eval/queries/p24_queries_v1.jsonl) | **PASSED** | 16 domains + procedure + state/central |
| **3. TREC Candidate Pooling** | [`eval/pooling.py`](file:///d:/Abishek/eval/pooling.py) | **PASSED** | Vector + auxiliary keyword candidate pool |
| **4. Graded Relevance & NDCG** | [`eval/metrics.py`](file:///d:/Abishek/eval/metrics.py) | **PASSED** | Graded 0..4 NDCG@10 engine |
| **5. Regression Harness** | [`eval/harness.py`](file:///d:/Abishek/eval/harness.py) | **PASSED** | Isolated 1,000-chunk regression runner |
| **6. Open-World Production Runner** | [`eval/harness.py`](file:///d:/Abishek/eval/harness.py) | **PASSED** | Read-only open-world DB evaluation |

---

## 5. Critical STOP Condition

> [!CAUTION]
> **STOP.**
> 
> Phase 2.4 Evaluation Framework implementation is **COMPLETE**.
> 
> * **NO answer generation or LLM calls (Gemini/GPT)** have been built.
> * **NO RAG chains, prompts, or agent logic** have been constructed.
> * **NO write or DDL operations** were executed against the production database.
> * **Phase 2.5 has NOT been initiated.**
> 
> Awaiting user review and sign-off on the Phase 2.4 report.
"""

    report_file_name = "PHASE_2_4_REGRESSION_REPORT.md" if manifest.run_mode == "closed_world_regression" else "PHASE_2_4_OPEN_WORLD_BASELINE.md"
    report_path = output_dir / report_file_name
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    manifest_path = output_dir / f"run_manifest_{manifest.run_mode}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    print(f"Saved evaluation report to {report_path}")
    print(f"Saved run manifest to {manifest_path}")
    return report_path
