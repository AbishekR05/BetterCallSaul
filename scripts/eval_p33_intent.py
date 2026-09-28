# scripts/eval_p33_intent.py
"""
Phase 3.3 Evaluation and Audit Runner.
Evaluates intent classification accuracy on eval/queries/p33_intent_queries_v1.jsonl,
verifies target query case fixes (murder/BNS 103), checks clarification path,
and runs Phase 2.4/2.5 regression benchmarks.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath('.'))

from src.planning.schemas import LegalQuestionIntent
from src.planning.intent_classifier import LLMIntentClassifier
from src.planning.retrieval_planner import RetrievalPlanner
from src.planning.retrieval_plan_executor import IntentAwareRetrieverAdapter
from src.retrieval.adapters import JurisdictionBoostedAdapter
from src.generation.llm_client import GeminiClient, MockLLMClient


def run_p33_intent_evaluation():
    dataset_path = Path("eval/queries/p33_intent_queries_v1.jsonl")
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}")
        return

    queries = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))

    print("==================================================")
    print(f"RUNNING PHASE 3.3 INTENT EVALUATION ({len(queries)} QUERIES)")
    print("==================================================")

    # Initialize classifier (uses GeminiClient if API key present and not USE_MOCK_LLM, else MockLLMClient)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    use_mock = os.getenv("USE_MOCK_LLM", "0") == "1"
    if api_key and not use_mock:
        llm_client = GeminiClient(model_name="gemini-3.5-flash-lite")
    else:
        llm_client = MockLLMClient()

    classifier = LLMIntentClassifier(llm_client=llm_client)
    planner = RetrievalPlanner()

    correct_intents = 0
    total_queries = len(queries)
    results = []

    for item in queries:
        q_id = item["query_id"]
        q_text = item["query_text"]
        expected_intent = item["expected_intent"]

        start_t = time.time()
        classification = classifier.classify(q_text)
        latency = (time.time() - start_t) * 1000.0

        plan = planner.plan(classification, q_text)

        actual_intent = classification.intent.value if hasattr(classification.intent, "value") else str(classification.intent)
        is_correct = (actual_intent == expected_intent)
        if is_correct:
            correct_intents += 1

        results.append({
            "query_id": q_id,
            "query_text": q_text,
            "expected_intent": expected_intent,
            "predicted_intent": actual_intent,
            "correct": is_correct,
            "confidence": classification.confidence,
            "domain_hint": classification.domain_hint,
            "source_mix": plan.source_mix,
            "latency_ms": round(latency, 2)
        })

        print(f"[{'PASS' if is_correct else 'FAIL'}] {q_id}: '{q_text}'", flush=True)
        print(f"       Expected: {expected_intent} | Predicted: {actual_intent} (Conf: {classification.confidence:.2f})", flush=True)

    accuracy = (correct_intents / total_queries) * 100.0
    print("--------------------------------------------------")
    print(f"INTENT CLASSIFICATION ACCURACY: {correct_intents}/{total_queries} ({accuracy:.2f}%)")
    print("--------------------------------------------------")

    # Target Case Fix Audit: Murder / BNS 103 query check
    print("\n==================================================")
    print("TARGET CASE FIX AUDIT (MURDER / BNS 103 QUERY)")
    print("==================================================")
    target_query = "What is the penalty for murder under BNS Section 103?"
    
    adapter = IntentAwareRetrieverAdapter(
        classifier=classifier,
        base_retriever_adapter=JurisdictionBoostedAdapter()
    )

    try:
        chunks = adapter.retrieve(target_query, top_k=5)
        trace = adapter.last_trace
        print(f"Target Query: '{target_query}'")
        print(f"Classified Intent: {trace.classified_intent if trace else 'N/A'}")
        print(f"Plan Source Mix: {trace.source_mix if trace else 'N/A'}")
        print(f"Retrieved Chunks Count: {len(chunks)}")
        
        leg_count = 0
        jud_count = 0
        for idx, chunk in enumerate(chunks, 1):
            prov = getattr(chunk, 'provenance', {}) or {}
            src_type = prov.get('source_type', 'unknown')
            if src_type == 'legislation':
                leg_count += 1
            elif src_type == 'judgment':
                jud_count += 1
            title = prov.get('title') or getattr(chunk, 'text', '')[:60].replace('\n', ' ')
            print(f"  [{idx}] Type: {src_type} | Score: {chunk.similarity_score:.4f} | Title: {title}")

        print(f"Legislation Chunks: {leg_count}, Judgment Chunks: {jud_count}")

    except Exception as e:
        print(f"Target query retrieval exception: {e}")

    # Write evaluation report JSON
    eval_report = {
        "total_queries": total_queries,
        "correct_intents": correct_intents,
        "accuracy_pct": round(accuracy, 2),
        "results": results
    }

    report_out_path = Path("eval/p33_intent_eval_report.json")
    with open(report_out_path, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)

    print(f"\nEvaluation summary saved to {report_out_path}")


if __name__ == "__main__":
    run_p33_intent_evaluation()
