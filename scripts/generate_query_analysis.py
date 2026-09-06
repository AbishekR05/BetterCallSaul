# scripts/generate_query_analysis.py
import json
import pandas as pd
from pathlib import Path

audit_path = Path("d:/Abishek/benchmark/phase_2_3/audit_results.json")
with open(audit_path, "r", encoding="utf-8") as f:
    data = json.load(f)

queries_path = Path("d:/Abishek/benchmark/phase_2_1/eval_queries.jsonl")
queries = {}
with open(queries_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            item = json.loads(line)
            queries[item["query_id"]] = item

per_q_live = data["per_query_live_pipeline"]
per_q_iso = data["per_query_isolated"]

print("Loaded per-query data for", len(per_q_live), "queries.")

# Identify hits vs failures on live DB
hits_live = [q for q in per_q_live if q["recall_10"] > 0]
misses_live = [q for q in per_q_live if q["recall_10"] == 0]

print(f"Live DB Hits (Recall@10 > 0): {len(hits_live)}")
print(f"Live DB Misses (Recall@10 = 0): {len(misses_live)}")

# Check how many misses on live DB were hits on isolated pilot
recovered_in_pilot = [q for q in misses_live if any(i["recall_10"] > 0 for i in per_q_iso if i["query_id"] == q["query_id"])]
print(f"Misses in Live DB that were Hits in Isolated Pilot: {len(recovered_in_pilot)} / {len(misses_live)}")
