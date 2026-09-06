# src/retrieval/adapters.py
"""
Pluggable RetrieverAdapters for Phase 2.5 Experiments.
Wires together candidate_pool, lexical, fusion, reranker, confidence, and jurisdiction_filter.
"""

from typing import List, Dict, Any, Optional
from eval.schemas import ScoredChunk, RetrieverAdapter
from eval.harness import BaselineRetrieverAdapter
from src.retrieval.lexical import LexicalSearcher
from src.retrieval.candidate_pool import CandidatePool
from src.retrieval.fusion import reciprocal_rank_fusion, weighted_score_fusion
from src.retrieval.reranker import BGEReranker
from src.retrieval.confidence import ConfidenceCalibrator
from src.retrieval.jurisdiction_filter import JurisdictionBooster


class BaselineAdapter(BaselineRetrieverAdapter):
    """Alias for Phase 2.3 frozen dense baseline retriever adapter."""
    pass


class HybridAdapter:
    """
    Adapter combining Dense (Phase 2.3) + Lexical FTS search using RRF or Weighted Score Fusion.
    """
    def __init__(
        self,
        fusion_method: str = "rrf",
        rrf_k: float = 60.0,
        weights: Optional[Dict[str, float]] = None,
        candidate_k: int = 50
    ):
        self.dense_adapter = BaselineAdapter()
        self.lexical_searcher = LexicalSearcher()
        self.fusion_method = fusion_method
        self.rrf_k = rrf_k
        self.weights = weights or {"dense": 0.7, "lexical_fts": 0.3}
        self.candidate_k = candidate_k

    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Any] = None) -> List[ScoredChunk]:
        # 1. Retrieve candidates from Dense & Lexical backends
        dense_chunks = self.dense_adapter.retrieve(query, top_k=self.candidate_k, filters=filters)
        lexical_chunks = self.lexical_searcher.search(query, top_k=self.candidate_k)

        # 2. Merge into candidate pool
        pool = CandidatePool()
        pool.add_candidates("dense", dense_chunks)
        pool.add_candidates("lexical_fts", lexical_chunks)

        # 3. Apply selected fusion method
        if self.fusion_method == "weighted":
            return weighted_score_fusion(pool, weights=self.weights, top_k=top_k)
        else:
            return reciprocal_rank_fusion(pool, rrf_k=self.rrf_k, top_k=top_k)


class RerankedAdapter:
    """
    Adapter wrapping HybridAdapter with BAAI/bge-reranker-base cross-encoder reranking.
    """
    def __init__(
        self,
        hybrid_adapter: Optional[HybridAdapter] = None,
        reranker: Optional[BGEReranker] = None,
        rerank_candidate_k: int = 30
    ):
        self.hybrid_adapter = hybrid_adapter or HybridAdapter(fusion_method="rrf", candidate_k=50)
        self.reranker = reranker or BGEReranker()
        self.rerank_candidate_k = rerank_candidate_k

    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Any] = None) -> List[ScoredChunk]:
        # Get hybrid candidates
        candidates = self.hybrid_adapter.retrieve(query, top_k=self.rerank_candidate_k, filters=filters)
        # Apply cross-encoder reranking
        return self.reranker.rerank(query, candidates, top_k=top_k)


class CalibratedAdapter:
    """
    Adapter adding empirical confidence threshold calibration over base adapters.
    """
    def __init__(
        self,
        base_adapter: Optional[Any] = None,
        calibrator: Optional[ConfidenceCalibrator] = None
    ):
        self.base_adapter = base_adapter or RerankedAdapter()
        self.calibrator = calibrator or ConfidenceCalibrator(high_confidence_threshold=0.40)

    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Any] = None) -> List[ScoredChunk]:
        chunks = self.base_adapter.retrieve(query, top_k=top_k, filters=filters)
        return self.calibrator.calibrate(chunks)


class JurisdictionBoostedAdapter:
    """
    Full pipeline adapter adding soft jurisdiction boosting.
    """
    def __init__(
        self,
        base_adapter: Optional[Any] = None,
        booster: Optional[JurisdictionBooster] = None
    ):
        self.base_adapter = base_adapter or CalibratedAdapter()
        self.booster = booster or JurisdictionBooster(boost_factor=1.15)

    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Any] = None) -> List[ScoredChunk]:
        chunks = self.base_adapter.retrieve(query, top_k=top_k, filters=filters)
        # Extract expected jurisdiction if passed in filters/context
        expected_jur = None
        if isinstance(filters, dict):
            expected_jur = filters.get("expected_jurisdiction") or filters.get("jurisdiction")
        return self.booster.apply_boost(chunks, expected_jurisdiction=expected_jur)
