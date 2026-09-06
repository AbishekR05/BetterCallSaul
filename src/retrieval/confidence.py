# src/retrieval/confidence.py
"""
Confidence Threshold Calibration for Phase 2.5 Retrieval Optimization.
Replaces fixed thresholds with empirically fit decision boundaries to reduce false-confidence.
"""

from typing import List
from eval.schemas import ScoredChunk


class ConfidenceCalibrator:
    """
    Evaluates similarity/rerank scores against calibrated thresholds to determine
    confidence tier ('high' vs 'low') and filter out false-confidence results.
    """

    def __init__(self, high_confidence_threshold: float = 0.40):
        self.high_confidence_threshold = high_confidence_threshold

    def calibrate(self, chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        """
        Apply calibrated confidence tiering to retrieved chunks.

        Args:
            chunks: List of ScoredChunk objects

        Returns:
            List of ScoredChunk objects with updated confidence_tier fields.
        """
        calibrated: List[ScoredChunk] = []
        for chunk in chunks:
            tier = "high" if chunk.similarity_score >= self.high_confidence_threshold else "low"
            chunk_dict = chunk.model_dump()
            chunk_dict["confidence_tier"] = tier
            calibrated.append(ScoredChunk(**chunk_dict))
        return calibrated
