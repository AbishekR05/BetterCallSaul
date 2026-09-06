# src/retrieval/reranker.py
"""
Cross-Encoder Reranker Interface and Implementation for Phase 2.5 Retrieval Optimization.
Implements BAAI/bge-reranker-base cross-encoder reranking over candidate pools.
"""

from typing import List, Protocol, Optional
import torch
from sentence_transformers import CrossEncoder
from eval.schemas import ScoredChunk


class Reranker(Protocol):
    """Thin swappable protocol for cross-encoder reranking engines."""
    def rerank(self, query: str, candidates: List[ScoredChunk], top_k: int = 10) -> List[ScoredChunk]:
        ...


class BGEReranker:
    """
    Reranker implementation using BAAI/bge-reranker-base.
    Computes cross-attention logit scores between query and passage texts.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", device: str = "cuda"):
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self._model: Optional[CrossEncoder] = None

    def _load_model(self) -> None:
        if self._model is None:
            print(f"Loading cross-encoder reranker '{self.model_name}' on device '{self.device}'...")
            self._model = CrossEncoder(self.model_name, device=self.device, max_length=512)

    def rerank(self, query: str, candidates: List[ScoredChunk], top_k: int = 10) -> List[ScoredChunk]:
        """
        Rerank a list of candidate ScoredChunk objects using BGE cross-encoder.

        Args:
            query: Plain text query string
            candidates: List of ScoredChunk candidates from previous retrieval/fusion step
            top_k: Number of reranked results to return

        Returns:
            Re-ranked List of ScoredChunk objects sorted by cross-encoder score.
        """
        if not candidates:
            return []

        self._load_model()

        pairs = [[query, cand.text] for cand in candidates]
        
        # Predict cross-encoder relevance scores
        scores = self._model.predict(pairs, show_progress_bar=False)

        scored_candidates = list(zip(candidates, scores))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        reranked_chunks: List[ScoredChunk] = []
        for cand, score in scored_candidates[:top_k]:
            prov = dict(cand.provenance)
            prov["reranker"] = self.model_name
            prov["reranker_score"] = float(score)

            reranked_chunks.append(
                ScoredChunk(
                    chunk_id=cand.chunk_id,
                    document_id=cand.document_id,
                    text=cand.text,
                    similarity_score=float(score),
                    confidence_tier="high" if score > 0.0 else "low",
                    match_type="reranked_bge",
                    provenance=prov
                )
            )

        return reranked_chunks
