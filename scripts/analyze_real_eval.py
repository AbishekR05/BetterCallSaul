# scripts/analyze_real_eval.py
import json
import numpy as np

with open("benchmark/phase_2_6/real_gemini_eval_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total entries in real evaluation audit: {len(data)}")

ret_latencies = [d['retrieval_latency_ms'] for d in data]
gen_latencies = [d['generation_latency_ms'] for d in data]
tot_latencies = [d['total_latency_ms'] for d in data]
prompt_tokens = [d['prompt_tokens'] for d in data]
comp_tokens = [d['completion_tokens'] for d in data]
costs = [d['estimated_cost_usd'] for d in data if d.get('estimated_cost_usd')]
groundedness_scores = [d['groundedness_score'] for d in data]
relevance_scores = [d['relevance_score'] for d in data]

print("\n--- LATENCY BREAKDOWN (ms) ---")
print(f"Retrieval Latency  : Mean = {np.mean(ret_latencies):.1f} ms | P50 = {np.median(ret_latencies):.1f} ms | P95 = {np.percentile(ret_latencies, 95):.1f} ms")
print(f"Generation Latency : Mean = {np.mean(gen_latencies):.1f} ms | P50 = {np.median(gen_latencies):.1f} ms | P95 = {np.percentile(gen_latencies, 95):.1f} ms")
print(f"Total RAG Latency  : Mean = {np.mean(tot_latencies):.1f} ms | P50 = {np.median(tot_latencies):.1f} ms | P95 = {np.percentile(tot_latencies, 95):.1f} ms")

print("\n--- HUMAN-GRADED METRICS (50-Query Sample, 0-2 scale) ---")
print(f"Groundedness / Faithfulness Score: Mean = {np.mean(groundedness_scores):.2f} / 2.0 (Dist: 2s={groundedness_scores.count(2)}, 1s={groundedness_scores.count(1)}, 0s={groundedness_scores.count(0)})")
print(f"Answer Relevance Score           : Mean = {np.mean(relevance_scores):.2f} / 2.0 (Dist: 2s={relevance_scores.count(2)}, 1s={relevance_scores.count(1)}, 0s={relevance_scores.count(0)})")

print("\n--- TOKEN & COST PROFILE ---")
print(f"Mean Prompt Tokens     : {np.mean(prompt_tokens):.1f}")
print(f"Mean Completion Tokens : {np.mean(comp_tokens):.1f}")
print(f"Total API Cost (USD)   : ${np.sum(costs):.6f}")

print("\n--- JURISDICTION ALIGNMENT AUDIT ---")
mismatches = []
for d in data:
    exp = (d['expected_jurisdiction'] or '').lower()
    out = (d['output_jurisdiction'] or '').lower()
    
    matched = True
    if 'central' in exp and out != 'central':
        matched = False
    elif 'state_specific' in exp:
        st = exp.replace('state_specific:', '').strip().lower()
        if st not in out:
            matched = False
            
    if not matched:
        mismatches.append(d)

print(f"Jurisdiction Alignment Rate: {(len(data) - len(mismatches)) / len(data) * 100:.1f}% ({len(data) - len(mismatches)}/{len(data)})")
print(f"Total Mismatches: {len(mismatches)}")

for m in mismatches:
    print(f"\n[Mismatch Query {m['query_id']}] '{m['query_text']}'")
    print(f"  Expected Jurisdiction : {m['expected_jurisdiction']}")
    print(f"  Output Jurisdiction   : {m['output_jurisdiction']}")
    print(f"  Citations             : {m['citations_list']}")
    print(f"  Flags                 : {m['safety_flags']}")
