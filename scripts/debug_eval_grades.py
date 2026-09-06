import sys
sys.path.append("d:/Abishek")
import json
from pathlib import Path
from eval.schemas import RelevanceJudgment

AUDITED_GT_PATH = Path("d:/Abishek/benchmark/phase_2_4/ground_truth_v1_audited.jsonl")

grades = []
with open(AUDITED_GT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rj = RelevanceJudgment(**json.loads(line))
            grades.append(rj.relevance_grade)

print(f"Total judgments: {len(grades):,}")
print(f"Unique grades: {set(grades)}")
print(f"Grade >= 3 count: {sum(1 for g in grades if g >= 3.0):,}")
print(f"Grade >= 2 count: {sum(1 for g in grades if g >= 2.0):,}")
print(f"Grade == 1 count: {sum(1 for g in grades if g == 1.0):,}")
