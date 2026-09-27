# src/planning/intent_classifier.py
"""
Intent Classifier Module for Phase 3.3.
Classifies rewritten legal queries into LegalQuestionIntent using LLM or rule-based fallback.
"""

import json
import yaml
import re
from pathlib import Path
from typing import Optional, Protocol, Dict, Any

from src.planning.schemas import LegalQuestionIntent, IntentClassificationResult
from src.generation.llm_client import LLMClient, GeminiClient, MockLLMClient
from src.generation.response_parser import ResponseParser


class IntentClassifierProtocol(Protocol):
    """Protocol for intent classification implementations."""
    def classify(self, query: str) -> IntentClassificationResult:
        ...


class LLMIntentClassifier:
    """
    LLM-backed legal intent classifier using p33_intent_v1 prompt.
    Fully swappable, robust against JSON formatting errors and provider failures.
    """
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config_path: str = "configs/p33_intent_prompt.yaml"
    ):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.system_prompt = self.config.get("system_prompt", "")
        self.min_confidence = self.config.get("min_confidence", 0.40)

        if llm_client:
            self.llm_client = llm_client
        else:
            provider = self.config.get("llm_provider", "gemini")
            if provider == "mock":
                self.llm_client = MockLLMClient()
            else:
                model_name = self.config.get("model", "gemini-3.6-flash")
                self.llm_client = GeminiClient(model_name=model_name)

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def classify(self, query: str) -> IntentClassificationResult:
        """
        Classifies query into LegalQuestionIntent.
        Returns IntentClassificationResult with intent, domain_hint, jurisdiction_hint, and confidence.
        Falls back safely to MIXED on error or low confidence.
        """
        if not query or not query.strip():
            return IntentClassificationResult(
                intent=LegalQuestionIntent.CLARIFICATION_REQUIRED,
                confidence=1.0,
                reasoning="Empty or blank query provided"
            )

        # Quick heuristic rule check for short underspecified queries (§7)
        words = query.strip().split()
        if len(words) <= 3 and not any(kw in query.lower() for kw in ["bns", "ipc", "crpc", "cpa", "act"]):
            return IntentClassificationResult(
                intent=LegalQuestionIntent.CLARIFICATION_REQUIRED,
                confidence=0.9,
                reasoning="Short underspecified query"
            )

        try:
            raw_response = self.llm_client.generate(
                system_prompt=self.system_prompt,
                user_prompt=f"User Question:\n\"{query}\""
            )

            cleaned_json = ResponseParser.clean_json_text(raw_response.raw_text)
            data = json.loads(cleaned_json)

            intent_str = str(data.get("intent", "mixed")).lower()
            try:
                intent_enum = LegalQuestionIntent(intent_str)
            except ValueError:
                intent_enum = LegalQuestionIntent.MIXED

            confidence = float(data.get("confidence", 0.8))
            domain_hint = data.get("domain_hint")
            if domain_hint == "null" or not domain_hint:
                domain_hint = None

            jurisdiction_hint = data.get("jurisdiction_hint")
            if jurisdiction_hint == "null" or not jurisdiction_hint:
                jurisdiction_hint = None

            reasoning = data.get("reasoning", "LLM classified intent")

            # Fallback to MIXED if confidence is below minimum threshold
            if confidence < self.min_confidence and intent_enum != LegalQuestionIntent.CLARIFICATION_REQUIRED:
                return IntentClassificationResult(
                    intent=LegalQuestionIntent.MIXED,
                    domain_hint=domain_hint,
                    jurisdiction_hint=jurisdiction_hint,
                    confidence=confidence,
                    reasoning=f"Confidence {confidence:.2f} below threshold {self.min_confidence:.2f}; falling back to MIXED"
                )

            return IntentClassificationResult(
                intent=intent_enum,
                domain_hint=domain_hint,
                jurisdiction_hint=jurisdiction_hint,
                confidence=confidence,
                reasoning=reasoning
            )

        except Exception as e:
            # Fallback behavior (§8): Classifier failure falls back to MIXED
            return IntentClassificationResult(
                intent=LegalQuestionIntent.MIXED,
                domain_hint=None,
                jurisdiction_hint=None,
                confidence=0.5,
                reasoning=f"LLM classifier exception ({type(e).__name__}); fallback to MIXED"
            )
