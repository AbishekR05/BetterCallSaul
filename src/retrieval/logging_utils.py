# src/retrieval/logging_utils.py
"""
Structured JSON Lines logger for Phase 2.3 Legal Retrieval Pipeline.
Captures query telemetry, timing breakdown, filters, scores, and warnings.
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Optional
from src.retrieval.schema import RetrievalResult


def hash_query_text(query: str) -> str:
    """Hash query string for data-minimization privacy compliant logging."""
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def log_retrieval_event(result: RetrievalResult, log_dir: Optional[Path] = None) -> str:
    """
    Logs structured JSON line telemetry record of retrieval invocation.
    Returns JSON string record.
    """
    if log_dir is None:
        log_dir = Path("d:/Abishek/benchmark/phase_2_3")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "retrieval_events.jsonl"
    
    top_scores = [item.similarity_score for item in result.results]
    
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "query_hash": hash_query_text(result.query),
        "normalized_length": len(result.normalized_query),
        "filters_requested": result.filters_requested.model_dump() if result.filters_requested else None,
        "filters_applied": result.filters_applied.model_dump() if result.filters_applied else None,
        "insufficient_evidence": result.insufficient_evidence,
        "candidate_count": result.candidate_count,
        "returned_count": result.returned_count,
        "top_similarity_score": top_scores[0] if top_scores else 0.0,
        "similarity_scores": top_scores,
        "timing_ms": result.timing.model_dump(),
        "warnings": result.warnings,
        "error": result.error
    }
    
    json_str = json.dumps(record)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json_str + "\n")
    except Exception as e:
        print(f"Warning: Failed to write retrieval log event ({e})")
        
    return json_str
