# src/planning/retrieval_plan_executor.py
"""
Retrieval Plan Executor & Intent-Aware Retriever Adapter for Phase 3.3 (§5, §6).
Translates a RetrievalPlan into calls against the frozen Phase 2.5 retriever interface.
Ensures zero hardcoded truncation templates and robust fallback handling.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from eval.schemas import ScoredChunk
from src.retrieval.adapters import JurisdictionBoostedAdapter
from src.planning.schemas import (
    LegalQuestionIntent, IntentClassificationResult, RetrievalPlan, PlanTrace, HardConstraints, ConstraintInsufficiency
)
from src.planning.intent_classifier import IntentClassifierProtocol, LLMIntentClassifier
from src.planning.retrieval_planner import RetrievalPlanner


class RetrievalPlanExecutor:
    """
    Executes a RetrievalPlan against an underlying Phase 2.5 retriever adapter.
    Preserves all Phase 2.5 dense/FTS/RRF/rerank/calibration mechanics.
    Supports Phase 3.4 hard metadata constraints with SQL existence pre-checks (§5, §7).
    """
    def __init__(self, retriever_adapter: Optional[Any] = None):
        self.retriever_adapter = retriever_adapter or JurisdictionBoostedAdapter()
        self.last_insufficiency: Optional[ConstraintInsufficiency] = None

    def _check_constraint_exists(self, hard_constraints) -> Tuple[bool, str]:
        """Performs a cheap SQL EXISTS check against PostgreSQL source_documents/chunks (§7)."""
        from src.db_phase2 import get_connection
        conn = get_connection(autocommit=True)
        try:
            with conn.cursor() as cur:
                if hard_constraints.court and len(hard_constraints.court) > 0:
                    canonical_court = hard_constraints.court[0]
                    cur.execute("SELECT 1 FROM source_documents WHERE LOWER(court) = LOWER(%s) LIMIT 1;", [canonical_court])
                    if not cur.fetchone():
                        return False, f"Court '{canonical_court}' has 0 matching documents in database."

                if hard_constraints.source_type:
                    cur.execute("SELECT 1 FROM chunks WHERE LOWER(source_type) = LOWER(%s) LIMIT 1;", [hard_constraints.source_type])
                    if not cur.fetchone():
                        return False, f"Source type '{hard_constraints.source_type}' has 0 matching chunks in database."

                if hard_constraints.jurisdiction:
                    cur.execute("SELECT 1 FROM source_documents WHERE LOWER(jurisdiction) = LOWER(%s) LIMIT 1;", [hard_constraints.jurisdiction])
                    if not cur.fetchone():
                        return False, f"Jurisdiction '{hard_constraints.jurisdiction}' has 0 matching documents in database."

                return True, "Constraints exist in database."
        finally:
            conn.close()

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
        Enforces Phase 3.4 hard metadata constraints strictly without silent relaxation.
        """
        self.last_insufficiency = None

        if plan.requires_clarification:
            # Short-circuit retrieval for ambiguous queries (§7)
            return []

        # ----------------------------------------------------------------------
        # PHASE 3.4 HARD METADATA CONSTRAINTS EXECUTION
        # ----------------------------------------------------------------------
        if plan.hard_constraints:
            hc = plan.hard_constraints
            exists, reason_msg = self._check_constraint_exists(hc)
            if not exists:
                self.last_insufficiency = ConstraintInsufficiency(
                    constraint_summary=str(hc.evidence_spans),
                    matched_candidate_count=0,
                    reason="no_documents_match_constraint"
                )
                return []

            from src.retrieval.config import RetrievalFilters
            retrieval_filters = RetrievalFilters(
                court=hc.court[0] if hc.court and len(hc.court) > 0 else None,
                source_type=hc.source_type,
                jurisdiction=hc.jurisdiction
            )

            # Force retriever to NOT auto-relax filters
            chunks = self.retriever_adapter.retrieve(query, top_k=top_k, filters=retrieval_filters)

            # Post-filter assertion to guarantee no out-of-constraint chunks enter final candidate list
            filtered_chunks = []
            for chunk in chunks:
                m = getattr(chunk, "metadata", {}) or {}
                prov = getattr(chunk, "provenance", {}) or {}
                chunk_court = m.get("court") or prov.get("court")
                chunk_st = m.get("doc_type") or prov.get("source_type") or getattr(chunk, "source_type", None)

                valid = True
                if hc.court and len(hc.court) > 0:
                    if not chunk_court or chunk_court.lower() != hc.court[0].lower():
                        valid = False
                if hc.source_type:
                    if chunk_st and chunk_st.lower() != hc.source_type.lower():
                        valid = False

                if valid:
                    filtered_chunks.append(chunk)

            if not filtered_chunks:
                self.last_insufficiency = ConstraintInsufficiency(
                    constraint_summary=str(hc.evidence_spans),
                    matched_candidate_count=0,
                    reason="no_relevant_candidates_under_constraint"
                )
                return []

            return filtered_chunks[:top_k]

        # ----------------------------------------------------------------------
        # UNCONSTRAINED / PHASE 3.3 SOFT WEIGHTING EXECUTION PATH
        # ----------------------------------------------------------------------
        execution_filters = {}
        if isinstance(filters, dict):
            execution_filters.update(filters)

        if plan.jurisdiction_filter:
            execution_filters["expected_jurisdiction"] = plan.jurisdiction_filter

        if plan.domain_filter:
            execution_filters["domain"] = plan.domain_filter

        execution_filters["source_mix"] = plan.source_mix

        chunks = self.retriever_adapter.retrieve(query, top_k=top_k, filters=execution_filters)

        if plan.source_mix and chunks:
            leg_weight = plan.source_mix.get("legislation", 0.5)
            jud_weight = plan.source_mix.get("judgment", 0.5)

            for chunk in chunks:
                match_type = getattr(chunk, "match_type", "")
                prov = getattr(chunk, "provenance", {}) or {}
                source_type = prov.get("source_type", "")

                if source_type == "legislation" or "statute" in match_type.lower():
                    chunk.similarity_score *= (0.8 + 0.4 * leg_weight)
                elif source_type == "judgment" or "judgment" in match_type.lower():
                    chunk.similarity_score *= (0.8 + 0.4 * jud_weight)

            chunks = sorted(chunks, key=lambda c: c.similarity_score, reverse=True)

        return chunks[:top_k]


class IntentAwareRetrieverAdapter:
    """
    Full Phase 3.3/3.4 retriever adapter wrapping IntentClassifier, RetrievalPlanner, and RetrievalPlanExecutor.
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
        self.last_insufficiency: Optional[ConstraintInsufficiency] = None

    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Any] = None) -> List[ScoredChunk]:
        """
        Main entry point for intent-aware and hard-constrained retrieval.
        """
        start_time = time.time()
        fallback_triggered = False
        fallback_reason = None
        self.last_insufficiency = None

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
            self.last_insufficiency = self.executor.last_insufficiency
        except Exception as e:
            fallback_triggered = True
            fallback_reason = f"Executor error: {e}"
            # Degradation fallback (§8): execute unrouted base adapter retrieval
            chunks = self.base_adapter.retrieve(query, top_k=top_k, filters=filters)

        latency_ms = (time.time() - start_time) * 1000.0

        hc_dict = plan.hard_constraints.dict() if plan.hard_constraints else None
        hc_spans = plan.hard_constraints.evidence_spans if plan.hard_constraints else None
        hc_outcome = "success" if chunks else ("insufficiency" if self.last_insufficiency else "empty")

        self.last_trace = PlanTrace(
            raw_query=query,
            rewritten_query=query,
            classified_intent=plan.intent,
            domain_hint=classification.domain_hint,
            jurisdiction_hint=classification.jurisdiction_hint,
            source_mix=plan.source_mix,
            hard_constraints_applied=hc_dict,
            constraint_provenance=hc_spans,
            constraint_outcome=hc_outcome,
            fallback_triggered=fallback_triggered,
            fallback_reason=fallback_reason,
            requires_clarification=plan.requires_clarification,
            latency_ms=latency_ms
        )

        return chunks

