# src/retrieval/langchain_adapter.py
"""
LangChain BaseRetriever adapter for Phase 2.3 Legal Retrieval Pipeline.
Wraps LegalRetriever without modifying database schema or creating extra tables.
"""

from typing import List, Optional, Any
from src.retrieval.config import RetrievalConfig, RetrievalFilters
from src.retrieval.retriever import LegalRetriever
from src.retrieval.schema import RetrievalResult

try:
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.documents import Document
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        from langchain.schema import BaseRetriever, Document
        CallbackManagerForRetrieverRun = Any
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        BaseRetriever = object
        Document = Any
        CallbackManagerForRetrieverRun = Any


class LegalLangChainRetriever(BaseRetriever if LANGCHAIN_AVAILABLE else object): # type: ignore
    """
    LangChain-compatible Retriever component wrapping LegalRetriever.
    Can be directly integrated into LangChain QA chains in future phases.
    Strictly READ-ONLY.
    """
    retriever: LegalRetriever
    filters: Optional[RetrievalFilters] = None
    config: Optional[RetrievalConfig] = None

    def __init__(
        self,
        retriever: Optional[LegalRetriever] = None,
        filters: Optional[RetrievalFilters] = None,
        config: Optional[RetrievalConfig] = None,
        **kwargs
    ):
        if LANGCHAIN_AVAILABLE and hasattr(super(), "__init__"):
            super().__init__(**kwargs)
            
        object.__setattr__(self, "retriever", retriever or LegalRetriever(config=config))
        object.__setattr__(self, "filters", filters)
        object.__setattr__(self, "config", config)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Any]:
        """
        Implementation of LangChain BaseRetriever contract.
        Converts RetrievalResultItems into LangChain Document objects.
        """
        result: RetrievalResult = self.retriever.retrieve(
            query=query,
            filters=self.filters,
            config=self.config
        )
        
        documents = []
        for item in result.results:
            metadata = item.provenance.model_dump()
            metadata["similarity_score"] = item.similarity_score
            metadata["confidence_tier"] = item.confidence_tier
            metadata["match_type"] = item.match_type
            
            if LANGCHAIN_AVAILABLE:
                doc = Document(page_content=item.text, metadata=metadata)
            else:
                doc = {"page_content": item.text, "metadata": metadata}
                
            documents.append(doc)
            
        return documents

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Any]:
        """Async implementation fallback."""
        return self._get_relevant_documents(query, run_manager=run_manager)
