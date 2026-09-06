# eval/annotation_tool.py
"""
Local Annotation CLI & Kappa Calculator for Phase 2.4 Ground Truth Creation.
Allows interactive or batch auto-labeling based on candidate grade definitions,
and calculates Cohen's weighted kappa on double-annotated subsets.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from eval.schemas import RelevanceJudgment


def cohen_weighted_kappa(y1: List[float], y2: List[float], min_grade: float = 0.0, max_grade: float = 4.0) -> float:
    """Computes linear weighted Cohen's Kappa for ordinal relevance grades (0 to 4)."""
    if len(y1) == 0 or len(y1) != len(y2):
        return 1.0

    grades = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0]
    n_grades = len(grades)
    grade_to_idx = {g: i for i, g in enumerate(grades)}

    # Build confusion matrix
    cm = np.zeros((n_grades, n_grades), dtype=float)
    for g1, g2 in zip(y1, y2):
        i1 = grade_to_idx.get(g1, 0)
        i2 = grade_to_idx.get(g2, 0)
        cm[i1, i2] += 1.0

    n = np.sum(cm)
    if n == 0:
        return 1.0

    # Linear weight matrix: w_ij = 1 - |i - j| / (n_grades - 1)
    w = np.zeros((n_grades, n_grades), dtype=float)
    for i in range(n_grades):
        for j in range(n_grades):
            w[i, j] = 1.0 - abs(i - j) / float(n_grades - 1)

    # Observed agreement
    po = np.sum(w * cm) / n

    # Expected agreement
    hist1 = np.sum(cm, axis=1)
    hist2 = np.sum(cm, axis=0)
    expected_cm = np.outer(hist1, hist2) / n
    pe = np.sum(w * expected_cm) / n

    if pe == 1.0:
        return 1.0

    kappa = (po - pe) / (1.0 - pe)
    return float(kappa)


def load_ground_truth(gt_path: Path) -> Dict[str, List[RelevanceJudgment]]:
    """Loads ground truth JSONL file grouped by query_id."""
    judgments_by_query: Dict[str, List[RelevanceJudgment]] = {}
    if not gt_path.exists():
        return judgments_by_query

    with open(gt_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                rj = RelevanceJudgment(**item)
                if rj.query_id not in judgments_by_query:
                    judgments_by_query[rj.query_id] = []
                judgments_by_query[rj.query_id].append(rj)
    return judgments_by_query


def append_ground_truth(gt_path: Path, judgments: List[RelevanceJudgment]):
    """Appends new relevance judgments to ground truth JSONL file."""
    gt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(gt_path, "a", encoding="utf-8") as f:
        for rj in judgments:
            f.write(rj.model_dump_json() + "\n")
