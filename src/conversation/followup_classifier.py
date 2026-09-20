# src/conversation/followup_classifier.py
"""
Follow-up Classifier for Phase 2.7 Conversational Context & Session Memory.
Classifies incoming queries into standalone, simple_followup, topic_change, ambiguous_followup, or contradictory_followup.
"""

from typing import List, Optional
import re
from src.conversation.schemas import ConversationTurn


class FollowUpClassifier:
    """
    Classifies incoming user query relative to recent conversation turns.
    """

    PRONOUN_PATTERNS = [
        r"\b(this|that|it|these|those|its|their|them)\b",
        r"\b(same|above|aforesaid|aforementioned)\b",
        r"\b(what about|how about|and for|what of)\b",
        r"\b(what if|suppose|in case)\b",
    ]

    ELLIPTICAL_PATTERNS = [
        r"^(what|how|why|is|does|can|are) (about|for|is|the penalty|the fine|the procedure|in|under)\b",
        r"^\??(what about|how about|and|also|what of)\b",
    ]

    TOPIC_CHANGE_KEYWORDS = [
        "motor vehicle", "traffic", "driving licence", "accident claim",
        "divorce", "marriage", "custody", "alimony",
        "income tax", "gst", "customs",
        "cyber crime", "it act", "hacking",
        "consumer court", "defective product",
        "cheque bounce", "section 138",
        "bail", "anticipatory bail", "fir",
    ]

    CONTRADICTION_PATTERNS = [
        r"\b(actually|instead|contrary to|what if i already|suppose i did|even though|regardless)\b",
    ]

    AMBIGUOUS_PATTERNS = [
        r"\b(both|either|all of them|former|latter|which one|the second one|that law)\b",
    ]

    def classify(self, query: str, recent_turns: List[ConversationTurn]) -> str:
        """
        Classify incoming query relative to prior turns.
        Returns one of: 'standalone', 'simple_followup', 'topic_change', 'ambiguous_followup', 'contradictory_followup'.
        """
        if not recent_turns:
            return "standalone"

        query_lower = query.strip().lower()

        # Check for ambiguous references
        for pattern in self.AMBIGUOUS_PATTERNS:
            if re.search(pattern, query_lower):
                # If there are multiple prior turns with distinct concepts, mark ambiguous
                if len(recent_turns) >= 2:
                    return "ambiguous_followup"

        # Check for contradiction patterns
        for pattern in self.CONTRADICTION_PATTERNS:
            if re.search(pattern, query_lower):
                return "contradictory_followup"

        # Check for explicit pronoun references or elliptical phrasing
        has_pronoun = any(re.search(pat, query_lower) for pat in self.PRONOUN_PATTERNS)
        has_elliptical = any(re.search(pat, query_lower) for pat in self.ELLIPTICAL_PATTERNS)

        # Check if short query without verb/subject (e.g. "What about Karnataka?", "And in Tamil Nadu?")
        is_short_followup = len(query_lower.split()) <= 6 and ("about" in query_lower or query_lower.startswith("what if") or query_lower.startswith("and "))

        if has_pronoun or has_elliptical or is_short_followup:
            # Check if it also introduces a complete topic change
            if self._is_topic_change(query_lower, recent_turns):
                return "topic_change"
            return "simple_followup"

        # Check topic change for longer queries
        if self._is_topic_change(query_lower, recent_turns):
            return "topic_change"

        # If query has substantial self-contained legal subject and no pronouns/elliptical references, treat as standalone
        if len(query_lower.split()) >= 6 and not has_pronoun:
            return "standalone"

        # Default fallback for short context-dependent queries
        return "simple_followup"

    def _is_topic_change(self, query_lower: str, recent_turns: List[ConversationTurn]) -> bool:
        """Check if query represents a distinct topic change relative to recent turns."""
        if not recent_turns:
            return False

        last_turn = recent_turns[-1]
        last_query_lower = last_turn.user_query.lower()
        last_domain = (last_turn.domain_carried_forward or "").lower()
        last_text = f"{last_query_lower} {last_domain}"

        # Extract legal keywords present in query
        query_topics = [kw for kw in self.TOPIC_CHANGE_KEYWORDS if kw in query_lower]

        if query_topics:
            # If query contains topic change keyword not mentioned in last turn or domain
            if not any(kw in last_text for kw in query_topics):
                return True

        return False
