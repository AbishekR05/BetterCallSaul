# src/generation/evidence_selector.py
"""
Evidence Selection logic for Phase 2.6 (§3.1).
Filters, caps, and enforces token budgets over retrieved ScoredChunks.
"""

from typing import List, Tuple
from eval.schemas import ScoredChunk


def estimate_tokens(text: str) -> int:
    """Approximate token count for evidence text (approx 4 chars per token)."""
    return len(text) // 4 + 1


class EvidenceSelector:
    """
    Selects the optimal subset of ScoredChunks for LLM prompt context (§3.1).
    """

    def __init__(self, max_context_chunks: int = 8, max_context_tokens: int = 2048):
        self.max_context_chunks = max_context_chunks
        self.max_context_tokens = max_context_tokens

    def select_evidence(self, chunks: List[ScoredChunk]) -> Tuple[List[ScoredChunk], bool]:
        """
        Filters and truncates candidate ScoredChunks to satisfy context budget rules.
        Returns: (selected_chunks, all_evidence_low_confidence_flag)
        """
        if not chunks:
            return [], True

        # Rule 1: Separate high confidence vs low confidence chunks
        high_conf_chunks = [c for c in chunks if getattr(c, 'confidence_tier', 'high') != 'low']
        all_low_confidence = len(high_conf_chunks) == 0

        # Rule 2: If high confidence chunks exist, drop low confidence. Otherwise keep all as fallback.
        eligible_chunks = high_conf_chunks if high_conf_chunks else list(chunks)

        # Rule 3: Cap at max_context_chunks
        top_candidates = eligible_chunks[:self.max_context_chunks]

        # Rule 4: Enforce token budget without breaking mid-chunk
        selected_chunks = []
        current_tokens = 0

        for chunk in top_candidates:
            chunk_tokens = estimate_tokens(chunk.text)
            if current_tokens + chunk_tokens <= self.max_context_tokens:
                selected_chunks.append(chunk)
                current_tokens += chunk_tokens
            else:
                # Token limit reached — drop remaining lower-ranked chunks
                break

        # If even the top 1 chunk exceeds total budget alone, include it to avoid empty selection
        if not selected_chunks and top_candidates:
            selected_chunks = [top_candidates[0]]

        return selected_chunks, all_low_confidence
