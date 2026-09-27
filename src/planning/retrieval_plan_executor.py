# src/planning/retrieval_plan_executor.py
"""
Retrieval Plan Executor & Intent-Aware Retriever Adapter for Phase 3.3 (§5, §6).
Translates a RetrievalPlan into calls against the frozen Phase 2.5 retriever interface.
Ensures zero hardcoded truncation templates and robust fallback handling.
"""

import time
from typing import List, Dict, Any, Optional
from eval.schemas import ScoredChunk
from src.retrieval.adapters import JurisdictionBoostedAdapter
from src.planning.schemas import (
    LegalQuestionIntent, IntentClassificationResult, RetrievalPlan, PlanTrace
)
from src.planning.intent_classifier import IntentClassifierProtocol, LLMIntentClassifier
from src.planning.retrieval_planner import RetrievalPlanner


class RetrievalPlanExecutor:
    """
    Executes a RetrievalPlan against an underlying Phase 2.5 retriever adapter.
    Preserves all Phase 2.5 dense/FTS/RRF/rerank/calibration mechanics.
    """
    def __init__(self, retriever_adapter: Optional[Any] = None):
        self.retriever_adapter = retriever_adapter or JurisdictionBoostedAdapter()

    def execute(
        self,
        plan: RetrievalPlan,
        query: str,
        top_k: int = 10,
        filters: Optional[Any] = None
    ) -> List[ScoredChunk]:
        """
        Executes retrieval according to RetrievalPlan.
        If plan.requires_clarification is True, short-circuits retrieval (§7).
        """
        if plan.requires_clarification:
            # Short-circuit retrieval for ambiguous queries (§7)
            return []

        # Merge plan filters with incoming filters
        execution_filters = {}
        if isinstance(filters, dict):
            execution_filters.update(filters)

        if plan.jurisdiction_filter:
            execution_filters["expected_jurisdiction"] = plan.jurisdiction_filter

        if plan.domain_filter:
            execution_filters["domain"] = plan.domain_filter

        # Pass source mix soft weighting hint into filters
        execution_filters["source_mix"] = plan.source_mix

        # Primary retrieval call through frozen Phase 2.5 adapter
        chunks = self.retriever_adapter.retrieve(query, top_k=top_k, filters=execution_filters)

        # Soft re-ranking boost by source type if specified in plan (weighting, NOT hard truncation)
        if plan.source_mix and chunks:
            leg_weight = plan.source_mix.get("legislation", 0.5)
            jud_weight = plan.source_mix.get("judgment", 0.5)

            # Apply soft preference multiplier without discarding low-weight candidates
            for chunk in chunks:
                match_type = getattr(chunk, "match_type", "")
                prov = getattr(chunk, "provenance", {}) or {}
                source_type = prov.get("source_type", "")

                if source_type == "legislation" or "statute" in match_type.lower():
                    chunk.similarity_score *= (0.8 + 0.4 * leg_weight)
                elif source_type == "judgment" or "judgment" in match_type.lower():
                    chunk.similarity_score *= (0.8 + 0.4 * jud_weight)

            # Re-sort by adjusted similarity score
            chunks = sorted(chunks, key=lambda c: c.similarity_score, reverse=True)

        return chunks[:top_k]


class IntentAwareRetrieverAdapter:
    """
    Full Phase 3.3 retriever adapter wrapping IntentClassifier, RetrievalPlanner, and RetrievalPlanExecutor.
    Implements standard RetrieverAdapter interface: retrieve(query, top_k, filters) -> List[ScoredChunk].
    """
    def __init__(
        self,
        classifier: Optional[IntentClassifierProtocol] = None,
        planner: Optional[RetrievalPlanner] = None,
        executor: Optional[RetrievalPlanExecutor] = None,
        base_retriever_adapter: Optional[Any] = None
    ):
        self.classifier = classifier or LLMIntentClassifier()
        self.planner = planner or RetrievalPlanner()
        self.executor = executor or RetrievalPlanExecutor(retriever_adapter=base_retriever_adapter)
        self.base_adapter = self.executor.retriever_adapter
        self.last_trace: Optional[PlanTrace] = None

    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Any] = None) -> List[ScoredChunk]:
        """
        Main entry point for intent-aware retrieval.
        """
        start_time = time.time()
        fallback_triggered = False
        fallback_reason = None

        # 1. Intent Classification
        try:
            classification = self.classifier.classify(query)
        except Exception as e:
            fallback_triggered = True
            fallback_reason = f"Classifier error: {e}"
            classification = IntentClassificationResult(
                intent=LegalQuestionIntent.MIXED,
                confidence=0.5,
                reasoning="Classifier exception fallback"
            )

        # 2. Retrieval Planning
        try:
            plan = self.planner.plan(classification, query)
        except Exception as e:
            fallback_triggered = True
            fallback_reason = f"Planner error: {e}"
            plan = RetrievalPlan(
                intent=LegalQuestionIntent.MIXED,
                source_mix={"legislation": 0.5, "judgment": 0.5},
                requires_clarification=False
            )

        # 3. Plan Execution
        chunks = []
        try:
            chunks = self.executor.execute(plan, query, top_k=top_k, filters=filters)
        except Exception as e:
            fallback_triggered = True
            fallback_reason = f"Executor error: {e}"
            # Degradation fallback (§8): execute unrouted base adapter retrieval
            chunks = self.base_adapter.retrieve(query, top_k=top_k, filters=filters)

        latency_ms = (time.time() - start_time) * 1000.0

        # 4. Record PlanTrace
        self.last_trace = PlanTrace(
            raw_query=query,
            rewritten_query=query,
            classified_intent=classification.intent,
            domain_hint=classification.domain_hint,
            jurisdiction_hint=classification.jurisdiction_hint,
            source_mix=plan.source_mix,
            fallback_triggered=fallback_triggered,
            fallback_reason=fallback_reason,
            requires_clarification=plan.requires_clarification,
            latency_ms=latency_ms
        )

        return chunks
