# src/retrieval/jurisdiction_filter.py
"""
Jurisdiction-Aware Soft Boosting Engine for Phase 2.5 Retrieval Optimization.
Applies soft multiplicative/additive relevance score boosts for matching jurisdiction chunks.
"""

from typing import List, Optional
from eval.schemas import ScoredChunk


class JurisdictionBooster:
    """
    Applies soft score boosting to candidates whose jurisdiction matches the query's
    expected jurisdiction, preserving out-of-jurisdiction chunks with unboosted scores.
    """

    def __init__(self, boost_factor: float = 1.15):
        self.boost_factor = boost_factor

    def apply_boost(
        self,
        chunks: List[ScoredChunk],
        expected_jurisdiction: Optional[str] = None
    ) -> List[ScoredChunk]:
        """
        Apply soft boost to matching jurisdiction chunks.

        Args:
            chunks: List of ScoredChunk candidates
            expected_jurisdiction: Target jurisdiction ('central', 'kerala', 'karnataka', etc.)

        Returns:
            Re-sorted list of ScoredChunk objects with boosted similarity scores.
        """
        if not expected_jurisdiction or expected_jurisdiction in ("jurisdiction_ambiguous", "all", "any"):
            return chunks

        boosted: List[tuple[ScoredChunk, float]] = []
        expected_clean = expected_jurisdiction.strip().lower()

        for chunk in chunks:
            prov = dict(chunk.provenance)
            chunk_jurisdiction = str(prov.get("jurisdiction", prov.get("source_type", ""))).strip().lower()
            
            score = chunk.similarity_score
            if expected_clean in chunk_jurisdiction or chunk_jurisdiction in expected_clean:
                score *= self.boost_factor
                prov["jurisdiction_boosted"] = True
                prov["boost_factor"] = self.boost_factor

            updated_chunk = ScoredChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                similarity_score=float(score),
                confidence_tier=chunk.confidence_tier,
                match_type=chunk.match_type,
                provenance=prov
            )
            boosted.append((updated_chunk, score))

        boosted.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in boosted]
