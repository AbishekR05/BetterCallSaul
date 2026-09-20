# scripts/audit_p27_eval.py
"""
Detailed per-turn evaluation auditor for Phase 2.7.
Runs MockLLM and GeminiClient evaluations, prints exact per-turn outputs and latency breakdowns,
and categorizes any jurisdiction or classification mismatches.
"""

import json
import time
import numpy as np
from src.conversation.orchestrator import ConversationalOrchestrator
from src.conversation.session_store import InMemorySessionStore
from src.generation.llm_client import MockLLMClient, GeminiClient
from src.retrieval.adapters import JurisdictionBoostedAdapter


def audit_run(use_mock: bool = True):
    dataset_path = "eval/conversation/p27_conversations_v1.jsonl"
    config_path = "configs/p27_conversation.yaml"

    turns_data = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                turns_data.append(json.loads(line.strip()))

    store = InMemorySessionStore()
    retriever = JurisdictionBoostedAdapter()
    llm_client = MockLLMClient(canned_response_mode="sufficient") if use_mock else GeminiClient(model_name="gemini-3.5-flash")

    orchestrator = ConversationalOrchestrator(
        config_path=config_path,
        session_store=store,
        retriever_adapter=retriever,
        llm_client=llm_client
    )

    session_id_map = {}
    total_latencies = []
    retrieval_latencies = []
    generation_latencies = []
    rewrite_latencies = []

    mismatches = []

    print(f"\n========================================================")
    print(f" AUDIT RUN ({'MockLLMClient' if use_mock else 'GeminiClient'})")
    print(f"========================================================")

    for idx, turn_info in enumerate(turns_data, 1):
        ext_sess_id = turn_info["session_id"]
        query = turn_info["query"]
        expected_class = turn_info["expected_classification"]
        expected_resolution = turn_info["expected_resolution"]
        expected_jur = turn_info["expected_jurisdiction"]

        internal_sess_id = session_id_map.get(ext_sess_id)

        t_start = time.time()
        res = orchestrator.handle_turn(session_id=internal_sess_id, user_query=query)
        t_total = (time.time() - t_start) * 1000.0

        if not internal_sess_id:
            session_id_map[ext_sess_id] = res.session_id

        turn = res.turn
        answer = turn.grounded_answer
        meta = answer.generation_metadata

        total_latencies.append(t_total)
        retrieval_latencies.append(meta.latency_ms_retrieval)
        generation_latencies.append(meta.latency_ms_generation)
        rewrite_latencies.append(max(0.0, t_total - meta.latency_ms_retrieval - meta.latency_ms_generation))

        actual_class = turn.followup_classification
        actual_jur = (turn.jurisdiction_carried_forward or answer.applicable_jurisdiction).lower()
        class_match = (actual_class == expected_class)

        jur_match = (expected_jur == "unclear" or actual_jur == expected_jur or expected_jur in actual_jur)

        print(f"Turn #{idx:02d} [{ext_sess_id} T{turn.turn_index}]")
        print(f"  User Query: '{query}'")
        print(f"  Class: {actual_class} (Expected: {expected_class}) -> {'MATCH' if class_match else 'MISMATCH'}")
        print(f"  Rewritten: '{turn.rewritten_query or 'N/A'}'")
        print(f"  Jurisdiction: {actual_jur} (Expected: {expected_jur}) -> {'MATCH' if jur_match else 'MISMATCH'}")
        print(f"  Sufficiency: {answer.evidence_sufficiency} | Citations: {len(answer.citations)} | Flags: {answer.safety_flags}")
        print(f"  Latency: Total={t_total:.1f}ms (Retrieval={meta.latency_ms_retrieval:.1f}ms, Gen={meta.latency_ms_generation:.1f}ms, Rewrite/Overhead={t_total - meta.latency_ms_retrieval - meta.latency_ms_generation:.1f}ms)")
        print(f"--------------------------------------------------------")

        if not jur_match or not class_match:
            mismatches.append({
                "turn_index": idx,
                "query": query,
                "expected_class": expected_class,
                "actual_class": actual_class,
                "expected_jur": expected_jur,
                "actual_jur": actual_jur,
                "rewritten_query": turn.rewritten_query,
                "answer_summary": answer.answer_summary,
                "reason": "class_mismatch" if not class_match else "jurisdiction_mismatch"
            })

    print(f"\nSUMMARY STATISTICS:")
    print(f"Total Turns: {len(turns_data)}")
    print(f"Class Accuracy: {sum(1 for t in turns_data if t['expected_classification'] == t['expected_classification'])} / {len(turns_data)}")
    print(f"P50 Total Latency: {np.percentile(total_latencies, 50):.1f} ms")
    print(f"P95 Total Latency: {np.percentile(total_latencies, 95):.1f} ms")
    print(f"P50 Retrieval Latency: {np.percentile(retrieval_latencies, 50):.1f} ms")
    print(f"P50 Generation Latency: {np.percentile(generation_latencies, 50):.1f} ms")
    print(f"P50 Rewrite Overhead Latency: {np.percentile(rewrite_latencies, 50):.1f} ms")
    print(f"Mismatches Count: {len(mismatches)}")
    for m in mismatches:
        print(f"  - Turn #{m['turn_index']}: {m['reason']} (Exp Jur: {m['expected_jur']}, Act Jur: {m['actual_jur']})")


if __name__ == "__main__":
    audit_run(use_mock=True)
