# src/retrieval/preprocessing.py
"""
Lightweight, deterministic query preprocessing and normalization for Phase 2.3.
Cleans encoding artifacts and whitespace without destructive NLP transformations.
"""

import re
import unicodedata
from typing import Tuple, List


def preprocess_query(query: str, max_length: int = 1000) -> Tuple[str, List[str]]:
    """
    Normalizes raw layman query string.
    
    Operations:
      - Rejects empty or whitespace-only queries
      - Strips leading/trailing whitespace
      - Collapses repeated internal whitespace
      - Normalizes Unicode (NFKC)
      - Truncates to max_length with a logged warning if exceeded
      - Preserves case, punctuation, and natural language structure for transformer embedding
      
    Returns:
      (normalized_query_string, list_of_warning_messages)
    """
    warnings: List[str] = []
    
    if not query or not query.strip():
        raise ValueError("Query cannot be empty or whitespace-only.")
        
    # 1. Unicode normalization (NFKC)
    cleaned = unicodedata.normalize("NFKC", query)
    
    # 2. Strip leading/trailing whitespace & collapse internal spaces
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    
    # 3. Enforce maximum input length
    if len(cleaned) > max_length:
        warnings.append(
            f"Query character length ({len(cleaned)}) exceeded max_length ({max_length}). Truncated."
        )
        cleaned = cleaned[:max_length].strip()
        
    if not cleaned:
        raise ValueError("Query became empty after normalization.")
        
    return cleaned, warnings
