# eval/schemas.py
"""
Data Schemas and Protocol Definitions for Phase 2.4 Retrieval Evaluation Framework.
"""

from typing import List, Dict, Any, Optional, Protocol, Union
from pydantic import BaseModel, Field
from datetime import datetime


class EvalQuery(BaseModel):
    """Evaluation query schema."""
    query_id: str
    query_text: str
    domain: str
    procedure_related: bool = False
    jurisdiction_expectation: str = "central_only"  # central_only | state_specific: <State> | jurisdiction_ambiguous
    query_type: str = "easy"  # easy, moderately_ambiguous, multi_concept, jurisdiction_sensitive, legislation_focused, judgment_focused, mixed_legislation_judgment, no_evidence_expected, clarification_required
    secondary_tags: List[str] = Field(default_factory=list)
    difficulty_category: Optional[str] = None
    precise_paraphrase: Optional[str] = None


class RelevanceJudgment(BaseModel):
    """Ground truth relevance judgment schema."""
    query_id: str
    chunk_id: str
    parent_document_id: Optional[str] = None
    document_title: Optional[str] = None
    document_type: Optional[str] = None  # legislation | judgment
    jurisdiction: Optional[str] = None
    court: Optional[str] = None
    domain: Optional[str] = None
    relevance_grade: float  # 0, 0.5, 1, 2, 3, 4
    grade_label: str  # exact_relevant (4), sibling_relevant (3), parent_relevant (2), supporting_authority (1), related_insufficient (0.5), irrelevant (0)
    annotator_id: str = "ann_01"
    annotation_round: int = 1
    notes: Optional[str] = None
    annotated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    resolution: Optional[str] = None  # direct | adjudicated


class ScoredChunk(BaseModel):
    """Unified chunk retrieval result item."""
    chunk_id: str
    document_id: str
    text: str
    similarity_score: float
    confidence_tier: str = "high"  # high | low
    match_type: str = "direct"
    provenance: Dict[str, Any] = Field(default_factory=dict)


class RetrieverAdapter(Protocol):
    """Pluggable adapter interface for retrieval systems under test."""
    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Any] = None) -> List[ScoredChunk]:
        ...


class CorpusSnapshot(BaseModel):
    """Corpus state snapshot."""
    chunks_row_count: int
    embeddings_row_count: int
    source_documents_row_count: int
    snapshot_taken_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class IndexConfig(BaseModel):
    """Index configuration metadata."""
    index_type: str = "HNSW"
    m: int = 16
    ef_construction: int = 64
    ef_search: int = 64
    distance_metric: str = "cosine"


class RunManifest(BaseModel):
    """Evaluation run manifest for full reproducibility."""
    run_id: str
    run_mode: str  # closed_world_regression | open_world
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    eval_dataset_version: str = "p24_queries_v1"
    ground_truth_version: str = "ground_truth_v1"
    corpus_snapshot: CorpusSnapshot
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    index_config: IndexConfig = Field(default_factory=IndexConfig)
    retriever_code_version: str = "main"
    harness_code_version: str = "p24_v1"
    random_seed: int = 42
    reproducible_command: str = "python -m eval.run --mode regression"
