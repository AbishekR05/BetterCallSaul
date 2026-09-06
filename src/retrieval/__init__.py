# src/retrieval/__init__.py
"""
Phase 2.3 Read-Only Production Retrieval Pipeline for BetterCallSaul RAG.
"""

from src.retrieval.config import RetrievalConfig, RetrievalFilters
from src.retrieval.schema import RetrievalResult, RetrievalResultItem, ProvenanceFields, RetrievalTiming
from src.retrieval.retriever import LegalRetriever

__all__ = [
    "RetrievalConfig",
    "RetrievalFilters",
    "RetrievalResult",
    "RetrievalResultItem",
    "ProvenanceFields",
    "RetrievalTiming",
    "LegalRetriever",
]
