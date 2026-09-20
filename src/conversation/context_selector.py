# src/conversation/context_selector.py
"""
Context Selector for Phase 2.7 Conversational Context & Session Memory.
Selects bounded, relevant subset of prior turns for query rewriting (§9).
"""

from typing import List, Tuple, Optional
from src.conversation.schemas import ConversationTurn, ContextSelectionTrace


class ContextSelector:
    """
    Selects bounded, relevant prior turns from a session for query rewriting.
    """

    def __init__(self, max_context_turns: int = 4, max_context_tokens_for_rewrite: int = 512):
        self.max_context_turns = max_context_turns
        self.max_context_tokens = max_context_tokens_for_rewrite

    def select_context(
        self,
        turns: List[ConversationTurn],
        current_query: str,
        classification: str
    ) -> Tuple[List[ConversationTurn], ContextSelectionTrace]:
        """
        Select bounded relevant turns from conversation history.
        Returns tuple of (selected_turns, debug_trace).
        """
        # If topic_change or standalone or no turns, clear context window
        if classification in ("topic_change", "standalone") or not turns:
            trace = ContextSelectionTrace(
                selected_turn_indices=[],
                selection_reasons=["Context cleared due to classification: " + classification],
                estimated_token_cost=0,
                window_size=0,
                cleared_on_topic_change=(classification == "topic_change"),
            )
            return [], trace

        # Consider at most last max_context_turns
        candidate_turns = turns[-self.max_context_turns:]
        selected_turns: List[ConversationTurn] = []
        reasons: List[str] = []

        query_lower = current_query.lower()
        has_pronouns = any(word in query_lower for word in ["this", "that", "it", "these", "those", "same", "above", "penalties", "fine", "penalty"])
        has_location_shift = any(word in query_lower for word in ["karnataka", "maharashtra", "delhi", "tamil nadu", "kerala", "gujarat"])

        for i, turn in enumerate(candidate_turns):
            reason = None
            is_most_recent = (i == len(candidate_turns) - 1)

            if is_most_recent:
                reason = "Most recent prior turn included by default"
            elif has_pronouns:
                reason = "Turn included due to explicit pronoun/reference cues in query"
            elif has_location_shift and turn.domain_carried_forward:
                reason = f"Turn included due to domain continuity ({turn.domain_carried_forward})"
            elif turn.jurisdiction_carried_forward:
                reason = f"Turn included due to jurisdiction match ({turn.jurisdiction_carried_forward})"

            if reason:
                selected_turns.append(turn)
                reasons.append(f"Turn #{turn.turn_index}: {reason}")

        # Enforce token budget (estimate 1.3 tokens per word)
        total_tokens = sum(self._estimate_tokens(t) for t in selected_turns)
        while total_tokens > self.max_context_tokens and len(selected_turns) > 1:
            dropped_turn = selected_turns.pop(0)  # drop oldest first
            reasons.append(f"Turn #{dropped_turn.turn_index} dropped to fit token budget ({self.max_context_tokens} max)")
            total_tokens = sum(self._estimate_tokens(t) for t in selected_turns)

        trace = ContextSelectionTrace(
            selected_turn_indices=[t.turn_index for t in selected_turns],
            selection_reasons=reasons,
            estimated_token_cost=total_tokens,
            window_size=len(selected_turns),
            cleared_on_topic_change=False,
        )

        return selected_turns, trace

    def _estimate_tokens(self, turn: ConversationTurn) -> int:
        """Estimate token count for a turn in rewrite context."""
        text = f"User: {turn.user_query}\nAnswer: {turn.grounded_answer.answer_summary}"
        return int(len(text.split()) * 1.3)
