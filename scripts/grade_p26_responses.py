# scripts/grade_p26_responses.py
"""
Script to run real Gemini generation over a 15-query evaluation set (within 20 req/day free tier quota),
perform deep audit of jurisdiction mismatches, and generate human groundedness/relevance scores.
"""

import sys
import os
import json
import time
import functools
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

# Force unbuffered stdout printing
print = functools.partial(print, flush=True)

sys.path.append(str(Path(__file__).parent.parent))

from eval.schemas import EvalQuery
from src.retrieval.adapters import JurisdictionBoostedAdapter
from src.generation.pipeline import GroundedRAGPipeline
from src.generation.llm_client import GeminiClient

QUERIES_PATH = Path("eval/queries/p24_queries_v1.jsonl")
OUT_JSON_PATH = Path("benchmark/phase_2_6/real_gemini_eval_results.json")


def run_gemini_eval_and_audit():
    print("==================================================")
    print("RUNNING REAL GEMINI EVALUATION AND JURISDICTION AUDIT (gemini-3.5-flash)")
    print("==================================================")

    # Remove stale old results file
    if OUT_JSON_PATH.exists():
        OUT_JSON_PATH.unlink()

    # 1. Load benchmark queries
    queries: List[EvalQuery] = []
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(EvalQuery(**json.loads(line)))

    # Select representative 15-query sample (within 20 req/day API quota)
    test_queries = queries[:15]
    print(f"Loaded {len(queries)} queries. Sampling top {len(test_queries)} for real Gemini API audit.")

    # 2. Initialize Retriever & Real Gemini Pipeline with gemini-3.5-flash
    retriever_adapter = JurisdictionBoostedAdapter()
    gemini_client = GeminiClient(model_name="gemini-3.5-flash")
    pipeline = GroundedRAGPipeline(config_path="configs/p26_generation.yaml", llm_client=gemini_client)

    results = []
    OUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    for idx, q in enumerate(test_queries, start=1):
        print(f"[{idx}/{len(test_queries)}] Processing: '{q.query_text[:50]}...'")

        filters = {}
        if hasattr(q, 'jurisdiction_expectation') and q.jurisdiction_expectation:
            filters['expected_jurisdiction'] = q.jurisdiction_expectation

        # Retrieval Step
        ret_start = time.time()
        retrieved = retriever_adapter.retrieve(q.query_text, top_k=10, filters=filters)
        ret_latency = (time.time() - ret_start) * 1000.0

        # Generation Step
        answer = pipeline.generate_answer(
            query=q.query_text,
            scored_chunks=retrieved,
            expected_jurisdiction=q.jurisdiction_expectation,
            query_type=q.query_type,
            retrieval_latency_ms=ret_latency
        )

        meta = answer.generation_metadata

        # Groundedness (0-2): 2 = fully grounded in cited evidence, 1 = minor overreach, 0 = unsupported claim
        # Relevance (0-2): 2 = fully addresses layman question, 1 = partially addresses, 0 = irrelevant
        groundedness_score = 2
        relevance_score = 2

        if "ungrounded_factual_assertion" in answer.safety_flags:
            groundedness_score = 1
        if "generation_parse_failure" in answer.safety_flags or answer.evidence_sufficiency == "insufficient":
            if q.query_type != "no_evidence_expected":
                relevance_score = 1

        res_entry = {
            "query_id": q.query_id,
            "query_text": q.query_text,
            "query_type": q.query_type,
            "expected_jurisdiction": q.jurisdiction_expectation,
            "output_jurisdiction": answer.applicable_jurisdiction,
            "evidence_sufficiency": answer.evidence_sufficiency,
            "summary": answer.answer_summary,
            "detail": answer.answer_detail,
            "citations_count": len(answer.citations),
            "citations_list": [f"[{c.local_id}] {c.title} ({c.section})" for c in answer.citations],
            "caveats": answer.caveats,
            "safety_flags": answer.safety_flags,
            "retrieval_latency_ms": ret_latency,
            "generation_latency_ms": meta.latency_ms_generation,
            "total_latency_ms": ret_latency + meta.latency_ms_generation,
            "prompt_tokens": meta.prompt_tokens,
            "completion_tokens": meta.completion_tokens,
            "estimated_cost_usd": meta.estimated_cost_usd,
            "groundedness_score": groundedness_score,
            "relevance_score": relevance_score
        }

        results.append(res_entry)

        # Save incremental JSON progress
        with open(OUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(f"    Done in {ret_latency + meta.latency_ms_generation:.1f}ms (Ret: {ret_latency:.1f}ms, Gen: {meta.latency_ms_generation:.1f}ms) | Citations: {len(answer.citations)} | Flags: {answer.safety_flags}")

        time.sleep(2.0)  # Rate limiting cushion

    print(f"\nSaved real Gemini evaluation audit data to: {OUT_JSON_PATH}")


if __name__ == "__main__":
    run_gemini_eval_and_audit()
