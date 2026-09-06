# src/retrieval/fusion.py
"""
Candidate List Fusion Algorithms for Phase 2.5 Retrieval Optimization.
Implements Reciprocal Rank Fusion (RRF) and Min-Max Weighted Score Fusion.
"""

from typing import List, Dict, Optional
from eval.schemas import ScoredChunk
from src.retrieval.candidate_pool import CandidatePool, Candidate


def reciprocal_rank_fusion(
    candidate_pool: CandidatePool,
    rrf_k: float = 60.0,
    top_k: int = 10
) -> List[ScoredChunk]:
    """
    Reciprocal Rank Fusion (RRF):
    RRF_Score(d) = sum_{m in sources} 1.0 / (k + rank_m(d))

    Args:
        candidate_pool: CandidatePool containing merged candidates
        rrf_k: Constant denominator offset (default 60.0)
        top_k: Number of fused results to return

    Returns:
        List of ScoredChunk objects ranked by RRF score.
    """
    candidates = candidate_pool.get_all_candidates()
    scored_candidates: List[tuple[Candidate, float]] = []

    for cand in candidates:
        rrf_score = 0.0
        for source_name, rank in cand.raw_ranks.items():
            rrf_score += 1.0 / (rrf_k + float(rank))
        scored_candidates.append((cand, rrf_score))

    # Sort descending by RRF score
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    result_chunks: List[ScoredChunk] = []
    for cand, score in scored_candidates[:top_k]:
        prov = dict(cand.provenance)
        prov["fusion_method"] = "rrf"
        prov["rrf_score"] = float(score)
        prov["raw_ranks"] = cand.raw_ranks

        result_chunks.append(
            ScoredChunk(
                chunk_id=cand.chunk_id,
                document_id=cand.document_id,
                text=cand.text,
                similarity_score=float(score),
                confidence_tier="high" if score > 0.015 else "low",
                match_type="hybrid_rrf",
                provenance=prov
            )
        )

    return result_chunks


def weighted_score_fusion(
    candidate_pool: CandidatePool,
    weights: Optional[Dict[str, float]] = None,
    top_k: int = 10
) -> List[ScoredChunk]:
    """
    Min-Max Normalized Weighted Score Fusion:
    Normalized_Score_m(d) = (Score_m(d) - min_m) / (max_m - min_m)
    Fused_Score(d) = sum_{m in sources} w_m * Normalized_Score_m(d)

    Args:
        candidate_pool: CandidatePool containing merged candidates
        weights: Dictionary of backend weights (e.g. {'dense': 0.7, 'lexical_fts': 0.3})
        top_k: Number of fused results to return

    Returns:
        List of ScoredChunk objects ranked by weighted score.
    """
    if weights is None:
        weights = {"dense": 0.7, "lexical_fts": 0.3}

    candidates = candidate_pool.get_all_candidates()
    if not candidates:
        return []

    # Compute min/max for each source for normalization
    source_min_max: Dict[str, tuple[float, float]] = {}
    for source in weights.keys():
        scores = [c.raw_scores[source] for c in candidates if source in c.raw_scores]
        if scores:
            min_val = min(scores)
            max_val = max(scores)
            source_min_max[source] = (min_val, max_val)
        else:
            source_min_max[source] = (0.0, 1.0)

    scored_candidates: List[tuple[Candidate, float]] = []

    for cand in candidates:
        fused_score = 0.0
        for source, w in weights.items():
            if source in cand.raw_scores:
                raw_score = cand.raw_scores[source]
                min_v, max_v = source_min_max[source]
                if max_v > min_v:
                    norm_score = (raw_score - min_v) / (max_v - min_v)
                else:
                    norm_score = 1.0 if raw_score > 0 else 0.0
                fused_score += w * norm_score

        scored_candidates.append((cand, fused_score))

    # Sort descending by fused score
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    result_chunks: List[ScoredChunk] = []
    for cand, score in scored_candidates[:top_k]:
        prov = dict(cand.provenance)
        prov["fusion_method"] = "weighted"
        prov["weighted_score"] = float(score)
        prov["raw_scores"] = cand.raw_scores

        result_chunks.append(
            ScoredChunk(
                chunk_id=cand.chunk_id,
                document_id=cand.document_id,
                text=cand.text,
                similarity_score=float(score),
                confidence_tier="high" if score > 0.40 else "low",
                match_type="hybrid_weighted",
                provenance=prov
            )
        )

    return result_chunks
