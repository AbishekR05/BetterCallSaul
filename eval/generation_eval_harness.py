# eval/generation_eval_harness.py
"""
Evaluation Harness for Phase 2.6 Grounded RAG Answer Generation (§12).
Reuses Phase 2.4 benchmark queries (p24_queries_v1.jsonl) and evaluates answer-level metrics:
  - Citation Validity Rate
  - Insufficient-Evidence Honesty Rate
  - Jurisdiction Correctness
  - Generation Latency (Mean, P50, P95)
  - Token Usage & Estimated USD Cost
  - Parse Failure Rate
Generates PHASE_2_6_EVALUATION_REPORT.md.
"""

import sys
import os
import time
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

# Workspace root
sys.path.append(str(Path(__file__).parent.parent))

from eval.schemas import EvalQuery, RelevanceJudgment
from src.retrieval.adapters import JurisdictionBoostedAdapter
from src.generation.pipeline import GroundedRAGPipeline
from src.generation.llm_client import MockLLMClient, GeminiClient


QUERIES_PATH = Path("eval/queries/p24_queries_v1.jsonl")
AUDITED_GT_PATH = Path("benchmark/phase_2_4/ground_truth_v1_audited.jsonl")
REPORT_PATH = Path("benchmark/phase_2_6/PHASE_2_6_EVALUATION_REPORT.md")
LOG_PATH = Path("benchmark/phase_2_6/generation_events.jsonl")


def run_generation_evaluation(
    max_queries: int = None,
    use_gemini: bool = False,
    config_path: str = "configs/p26_generation.yaml"
):
    print("==================================================")
    print("STARTING PHASE 2.6 GROUNDED RAG ANSWER GENERATION EVALUATION")
    print("==================================================")

    # Ensure output directory exists
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load benchmark queries
    queries: List[EvalQuery] = []
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(EvalQuery(**json.loads(line)))

    if max_queries:
        queries = queries[:max_queries]

    print(f"Loaded {len(queries)} evaluation queries.")

    # 2. Initialize Retriever & Generation Pipeline
    print("Initializing Phase 2.5 Retriever Adapter (JurisdictionBoostedAdapter)...")
    retriever_adapter = JurisdictionBoostedAdapter()

    if use_gemini:
        print("Using real Gemini API client (GeminiClient with gemini-3.5-flash)...")
        llm_client = GeminiClient(model_name="gemini-3.5-flash")
    else:
        print("Using Mock LLM client (MockLLMClient)...")
        llm_client = MockLLMClient(canned_response_mode="sufficient")

    pipeline = GroundedRAGPipeline(config_path=config_path, llm_client=llm_client)

    # Telemetry metrics containers
    total_queries = len(queries)
    valid_citation_count = 0
    total_citation_count = 0

    no_evidence_query_count = 0
    honest_insufficient_count = 0

    jurisdiction_matched_count = 0
    jurisdiction_evaluable_count = 0

    generation_latencies = []
    total_latencies = []
    prompt_tokens_list = []
    completion_tokens_list = []
    costs_list = []

    parse_failure_count = 0
    parse_retry_count = 0

    event_logs = []

    print(f"Running evaluation over {total_queries} queries...")

    for idx, q in enumerate(queries, start=1):
        if idx % 10 == 0 or idx == total_queries:
            print(f"[{idx}/{total_queries}] Evaluating query: '{q.query_text[:40]}...'")

        # Step A: Retrieval
        filters = {}
        if hasattr(q, 'jurisdiction_expectation') and q.jurisdiction_expectation:
            filters['expected_jurisdiction'] = q.jurisdiction_expectation

        ret_start = time.time()
        retrieved_chunks = retriever_adapter.retrieve(q.query_text, top_k=10, filters=filters)
        ret_latency = (time.time() - ret_start) * 1000.0

        # Step B: Generation
        answer = pipeline.generate_answer(
            query=q.query_text,
            scored_chunks=retrieved_chunks,
            expected_jurisdiction=q.jurisdiction_expectation,
            query_type=q.query_type,
            retrieval_latency_ms=ret_latency
        )

        # Telemetry updates
        meta = answer.generation_metadata
        generation_latencies.append(meta.latency_ms_generation)
        total_latencies.append(meta.latency_ms_total)
        prompt_tokens_list.append(meta.prompt_tokens)
        completion_tokens_list.append(meta.completion_tokens)
        costs_list.append(meta.estimated_cost_usd or 0.0)

        if "generation_parse_failure" in answer.safety_flags:
            parse_failure_count += 1
        if meta.parse_retry_count > 0:
            parse_retry_count += 1

        # Metric 1: Citation Validity
        for cite in answer.citations:
            total_citation_count += 1
            if cite.chunk_id in [c.chunk_id for c in retrieved_chunks]:
                valid_citation_count += 1

        # Metric 2: Insufficient-Evidence Honesty
        if q.query_type == "no_evidence_expected":
            no_evidence_query_count += 1
            if answer.evidence_sufficiency == "insufficient":
                honest_insufficient_count += 1

        # Metric 3: Jurisdiction Correctness
        exp_jur = (q.jurisdiction_expectation or "").lower()
        ans_jur = (answer.applicable_jurisdiction or "").lower()

        if "central" in exp_jur:
            jurisdiction_evaluable_count += 1
            if ans_jur == "central":
                jurisdiction_matched_count += 1
        elif "state_specific" in exp_jur:
            jurisdiction_evaluable_count += 1
            state_name = exp_jur.replace("state_specific:", "").strip().lower()
            if state_name in ans_jur:
                jurisdiction_matched_count += 1

        # Log event line
        log_entry = {
            "query_id": q.query_id,
            "query": q.query_text,
            "evidence_sufficiency": answer.evidence_sufficiency,
            "applicable_jurisdiction": answer.applicable_jurisdiction,
            "citations_count": len(answer.citations),
            "safety_flags": answer.safety_flags,
            "generation_latency_ms": meta.latency_ms_generation,
            "total_tokens": meta.total_tokens,
            "estimated_cost_usd": meta.estimated_cost_usd
        }
        event_logs.append(log_entry)

    # Save events log JSONL
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        for entry in event_logs:
            f.write(json.dumps(entry) + "\n")

    # Compute aggregates
    citation_validity_rate = (valid_citation_count / total_citation_count * 100.0) if total_citation_count > 0 else 100.0
    insufficient_honesty_rate = (honest_insufficient_count / no_evidence_query_count * 100.0) if no_evidence_query_count > 0 else 100.0
    jurisdiction_accuracy_rate = (jurisdiction_matched_count / jurisdiction_evaluable_count * 100.0) if jurisdiction_evaluable_count > 0 else 100.0
    parse_failure_rate = (parse_failure_count / total_queries * 100.0)

    mean_gen_latency = float(np.mean(generation_latencies))
    p50_gen_latency = float(np.median(generation_latencies))
    p95_gen_latency = float(np.percentile(generation_latencies, 95))

    mean_total_latency = float(np.mean(total_latencies))
    p95_total_latency = float(np.percentile(total_latencies, 95))

    mean_prompt_tokens = float(np.mean(prompt_tokens_list))
    mean_completion_tokens = float(np.mean(completion_tokens_list))
    total_cost_usd = float(np.sum(costs_list))

    print(f"\n==================================================")
    print(f"EVALUATION COMPLETE ({total_queries} queries)")
    print(f"  - Citation Validity: {citation_validity_rate:.1f}% ({valid_citation_count}/{total_citation_count})")
    print(f"  - Jurisdiction Correctness: {jurisdiction_accuracy_rate:.1f}% ({jurisdiction_matched_count}/{jurisdiction_evaluable_count})")
    print(f"  - Insufficient Honesty: {insufficient_honesty_rate:.1f}% ({honest_insufficient_count}/{no_evidence_query_count})")
    print(f"  - Mean Gen Latency: {mean_gen_latency:.1f}ms | P95 Gen Latency: {p95_gen_latency:.1f}ms")
    print(f"  - Mean Total RAG Latency: {mean_total_latency:.1f}ms | P95 Total RAG Latency: {p95_total_latency:.1f}ms")
    print(f"  - Total Cost: ${total_cost_usd:.6f}")
    print(f"==================================================")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-queries", type=int, default=None, help="Limit number of queries for fast evaluation")
    parser.add_argument("--use-gemini", action="store_true", help="Use real Gemini API instead of Mock client")
    parser.add_argument("--config", type=str, default="configs/p26_generation.yaml", help="Path to config file")
    args = parser.parse_args()

    run_generation_evaluation(
        max_queries=args.max_queries,
        use_gemini=args.use_gemini,
        config_path=args.config
    )
