# src/generation/grounding_checker.py
"""
Post-Hoc Heuristic Grounding and Legal Safety Validation for Phase 2.6 (§9.3, §10).
Performs structural checks for ungrounded factual assertions and mandatory legal disclaimers.
"""

import re
from typing import List, Tuple
from src.generation.schemas import RawAnswerModel


class GroundingChecker:
    """
    Lightweight, non-LLM heuristic grounding and legal safety checker (§9.3).
    """

    # Regex patterns for specific factual assertions that require inline citations
    FACTUAL_PATTERNS = [
        r"\bSection\s+\d+\b",            # e.g., Section 302
        r"\bArticle\s+\d+\b",            # e.g., Article 21
        r"₹\s*\d+",                       # Currency amounts e.g. ₹5,000
        r"\b\d+\s+(?:years?|months?)\b",  # Imprisonment terms e.g. 3 years
        r"\b\d{4}\b"                     # Act years or dates e.g. 1960
    ]

    def verify_grounding(
        self,
        raw_answer: RawAnswerModel,
        existing_flags: List[str]
    ) -> Tuple[RawAnswerModel, List[str]]:
        """
        Scans answer_detail for uncited factual assertions and enforces mandatory legal disclaimers.
        Returns: (updated_raw_answer, combined_safety_flags)
        """
        flags = list(existing_flags)
        detail = raw_answer.answer_detail

        # 1. Check for ungrounded factual assertions (§9.3)
        # Split text into sentences
        sentences = re.split(r"(?<=[.!?])\s+", detail)
        has_ungrounded_fact = False

        for sentence in sentences:
            if not sentence.strip():
                continue

            # Check if sentence contains factual pattern (section, date, penalty)
            contains_fact = any(re.search(pat, sentence, re.IGNORECASE) for pat in self.FACTUAL_PATTERNS)
            # Check if sentence contains citation tag [E1], [E2]
            contains_citation = bool(re.search(r"\[E\d+\]", sentence))

            if contains_fact and not contains_citation:
                has_ungrounded_fact = True
                break

        if has_ungrounded_fact and "ungrounded_factual_assertion" not in flags:
            flags.append("ungrounded_factual_assertion")

        # 2. Enforce legal advice disclaimer in caveats (§10)
        disclaimer_text = "This response is provided for legal awareness and informational purposes only, not formal legal advice. Consult a qualified advocate for specific legal issues."
        
        # If evidence_sufficiency is partial or insufficient, ensure legal disclaimer is present
        if raw_answer.evidence_sufficiency in ("partial", "insufficient"):
            has_disclaimer = any("legal advice" in c.lower() or "consult" in c.lower() for c in raw_answer.caveats)
            if not has_disclaimer:
                raw_answer.caveats.append(disclaimer_text)

        return raw_answer, flags
