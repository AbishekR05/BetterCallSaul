# src/retrieval/candidate_pool.py
"""
Candidate pool merger and provenance tracker for Phase 2.5 Retrieval Optimization.
Merges candidate lists from multiple retrieval backends (e.g., dense, lexical FTS),
deduplicates by chunk_id, and preserves per-backend raw scores and source provenance.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from eval.schemas import ScoredChunk


class Candidate(BaseModel):
    """Internal candidate representation with multi-backend score tracking."""
    chunk_id: str
    document_id: str
    text: str
    raw_scores: Dict[str, float] = Field(default_factory=dict)
    raw_ranks: Dict[str, int] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidatePool:
    """
    Manages and merges candidate lists from multiple retrieval sources.
    Deduplicates candidates by chunk_id while preserving per-source raw scores and ranks.
    """

    def __init__(self):
        self._candidates: Dict[str, Candidate] = {}

    def add_candidates(self, source_name: str, chunks: List[ScoredChunk]) -> None:
        """
        Add a list of ScoredChunks from a specific retrieval backend.

        Args:
            source_name: Name of the backend source (e.g. 'dense', 'lexical_fts')
            chunks: List of ScoredChunk objects returned by the backend
        """
        for rank, chunk in enumerate(chunks, start=1):
            chunk_id = chunk.chunk_id
            if chunk_id not in self._candidates:
                self._candidates[chunk_id] = Candidate(
                    chunk_id=chunk_id,
                    document_id=chunk.document_id,
                    text=chunk.text,
                    raw_scores={source_name: chunk.similarity_score},
                    raw_ranks={source_name: rank},
                    provenance=dict(chunk.provenance) if chunk.provenance else {},
                    metadata={}
                )
            else:
                cand = self._candidates[chunk_id]
                cand.raw_scores[source_name] = chunk.similarity_score
                cand.raw_ranks[source_name] = rank
                if chunk.provenance:
                    cand.provenance.update(chunk.provenance)

    def get_all_candidates(self) -> List[Candidate]:
        """Returns all merged candidates as a list."""
        return list(self._candidates.values())

    def clear(self) -> None:
        """Clears all accumulated candidates."""
        self._candidates.clear()

    def __len__(self) -> int:
        return len(self._candidates)
