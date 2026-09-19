# src/generation/response_parser.py
"""
Response Parsing and Validation Logic for Phase 2.6 (§8).
Parses intermediate LLM output JSON, handles repair retries, validates citation references, and checks jurisdiction claims.
"""

import json
import re
from typing import Tuple, List, Dict, Optional, Any
from eval.schemas import ScoredChunk
from src.generation.schemas import RawAnswerModel


class ResponseParser:
    """
    Parses and validates raw LLM text outputs into validated RawAnswerModels (§8).
    """

    @staticmethod
    def clean_json_text(raw_text: str) -> str:
        """Strips markdown code fences and extraneous whitespace from LLM text."""
        cleaned = raw_text.strip()
        # Remove ```json ... ``` or ``` ... ``` wrappers if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def parse_response(
        self,
        raw_text: str,
        local_id_map: Dict[str, ScoredChunk]
    ) -> Tuple[RawAnswerModel, List[str]]:
        """
        Parses raw text to RawAnswerModel and performs structural validation checks.
        Returns: (parsed_model, safety_flags)
        """
        safety_flags: List[str] = []
        cleaned_text = self.clean_json_text(raw_text)

        # 1. Parse JSON
        try:
            data = json.loads(cleaned_text)
            parsed_model = RawAnswerModel(**data)
        except Exception as e:
            # Parse failure — return fallback model with flag
            safety_flags.append("generation_parse_failure")
            fallback_model = RawAnswerModel(
                answer_summary="Unable to parse structured answer response.",
                answer_detail="Generation output could not be parsed into valid JSON structure.",
                applicable_jurisdiction="unclear",
                evidence_sufficiency="insufficient",
                citations_used=[],
                caveats=["Generation parse failure encountered. Consult raw logs."],
                clarifying_question=None
            )
            return fallback_model, safety_flags

        # 2. Validate citation IDs exist in local_id_map (§8.2)
        valid_citations = []
        invalid_citations = []
        for cite_id in parsed_model.citations_used:
            # Clean brackets if model included them e.g. "[E1]" -> "E1"
            clean_id = cite_id.replace("[", "").replace("]", "").strip()
            if clean_id in local_id_map:
                valid_citations.append(clean_id)
            else:
                invalid_citations.append(cite_id)

        if invalid_citations:
            safety_flags.append("invalid_citation_reference")
            parsed_model.citations_used = valid_citations

        # Also strip any [E99] tags from answer_detail if they reference non-existent IDs
        for bad_id in invalid_citations:
            bad_tag = f"[{bad_id}]"
            parsed_model.answer_detail = parsed_model.answer_detail.replace(bad_tag, "")

        # 3. Validate jurisdiction consistency (§8.3)
        if parsed_model.citations_used and parsed_model.applicable_jurisdiction not in ("central", "unclear", "multiple"):
            claimed_jur = parsed_model.applicable_jurisdiction.lower()
            cited_jurisdictions = []
            for cid in parsed_model.citations_used:
                chunk = local_id_map.get(cid)
                if chunk and isinstance(chunk.provenance, dict):
                    jur = (chunk.provenance.get("jurisdiction") or chunk.provenance.get("level") or "central").lower()
                    cited_jurisdictions.append(jur)

            # If claimed jurisdiction is specific state (e.g. Karnataka) but NO cited chunk contains it
            if cited_jurisdictions and not any(claimed_jur in j for j in cited_jurisdictions):
                safety_flags.append("jurisdiction_claim_mismatch")

        return parsed_model, safety_flags
