# src/planning/retrieval_planner.py
"""
Retrieval Planner Module for Phase 3.3.
Pure, deterministic function mapping IntentClassificationResult to RetrievalPlan.
Configurable via configs/p33_retrieval_planning.yaml (§5, §6).
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from src.planning.schemas import (
    LegalQuestionIntent, IntentClassificationResult, RetrievalPlan
)
from src.planning.constraint_extractor import ConstraintExtractor


class RetrievalPlanner:
    """
    Pure deterministic planner mapping (intent, domain_hint, jurisdiction_hint) -> RetrievalPlan.
    No LLM call; relies on YAML intent mappings and deterministic constraint extraction (§4, §5).
    """
    def __init__(
        self,
        config_path: str = "configs/p33_retrieval_planning.yaml",
        constraint_extractor: Optional[ConstraintExtractor] = None
    ):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.intent_mappings = self.config.get("intent_mappings", {})
        self.fallback_intent = self.config.get("fallback_intent", "mixed")
        self.constraint_extractor = constraint_extractor or ConstraintExtractor()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def plan(self, classification: IntentClassificationResult, query: str) -> RetrievalPlan:
        """
        Generates a RetrievalPlan given intent classification and raw/rewritten query.
        """
        intent_value = classification.intent.value if isinstance(classification.intent, LegalQuestionIntent) else str(classification.intent)
        
        mapping = self.intent_mappings.get(intent_value)
        if not mapping:
            # Fallback to mixed mapping
            mapping = self.intent_mappings.get(self.fallback_intent, {
                "source_mix": {"legislation": 0.5, "judgment": 0.5},
                "top_k_hints": {"candidate_k": 50, "rerank_k": 15},
                "requires_clarification": False
            })

        source_mix = mapping.get("source_mix", {"legislation": 0.5, "judgment": 0.5})
        top_k_hints = mapping.get("top_k_hints", {"candidate_k": 50, "rerank_k": 15})
        requires_clarification = mapping.get("requires_clarification", False)
        clarification_prompt = mapping.get("clarification_prompt")

        # Deterministically extract explicit hard constraints from query
        hard_constraints = self.constraint_extractor.extract(query)

        # Query expansion / variants
        query_variants = [query]
        
        # Build RetrievalPlan
        return RetrievalPlan(
            intent=classification.intent,
            source_mix=source_mix,
            query_variants=query_variants,
            top_k_hints=top_k_hints,
            domain_filter=classification.domain_hint,
            jurisdiction_filter=classification.jurisdiction_hint,
            hard_constraints=hard_constraints,
            requires_clarification=requires_clarification,
            clarification_prompt=clarification_prompt
        )

