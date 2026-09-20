# src/conversation/query_rewriter.py
"""
Query Rewriter for Phase 2.7 Conversational Context & Session Memory.
Transforms context-dependent user follow-ups into standalone legal retrieval queries (§10).
"""

import json
import re
from typing import List, Optional
from src.generation.llm_client import LLMClient
from src.conversation.schemas import ConversationTurn, RewriteResult
from src.conversation.prompts import REWRITE_PROMPT_P27_V1


class QueryRewriter:
    """
    Executes query rewriting using LLMClient protocol or deterministic heuristic fallbacks.
    """

    def __init__(self, llm_client: LLMClient, prompt_version: str = "p27_v1"):
        self.llm_client = llm_client
        self.prompt_version = prompt_version

    def rewrite(self, user_query: str, selected_context: List[ConversationTurn]) -> RewriteResult:
        """
        Rewrite user follow-up query into a standalone retrieval query using selected context turns.
        """
        if not selected_context:
            return RewriteResult(
                rewritten_query=user_query,
                resolution_status="resolved",
                carried_jurisdiction=None,
                carried_domain=None
            )

        # Format context for prompt
        formatted_turns = []
        for turn in selected_context:
            formatted_turns.append(
                f"Turn #{turn.turn_index}:\n"
                f"  User Query: {turn.user_query}\n"
                f"  Answer Summary: {turn.grounded_answer.answer_summary}\n"
                f"  Jurisdiction: {turn.grounded_answer.applicable_jurisdiction}\n"
                f"  Domain: {turn.domain_carried_forward or 'N/A'}"
            )
        context_str = "\n\n".join(formatted_turns)

        user_prompt = f"Selected Prior Context:\n{context_str}\n\nCurrent Follow-up Query: {user_query}"
        system_prompt = REWRITE_PROMPT_P27_V1

        try:
            llm_res = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=256,
                temperature=0.0
            )

            res_text = llm_res.raw_text.strip()
            # Clean markdown JSON block if present
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            if res_text.startswith("```"):
                res_text = res_text[3:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]
            res_text = res_text.strip()

            parsed = json.loads(res_text)
            if "rewritten_query" not in parsed and "resolution_status" not in parsed:
                return self._heuristic_rewrite(user_query, selected_context)

            return RewriteResult(
                rewritten_query=parsed.get("rewritten_query"),
                resolution_status=parsed.get("resolution_status", "resolved"),
                carried_jurisdiction=parsed.get("carried_jurisdiction"),
                carried_domain=parsed.get("carried_domain"),
                raw_response=res_text
            )
        except Exception:
            # Fallback to heuristic rewrite if LLM call fails or returns non-JSON (e.g. MockLLM default response)
            return self._heuristic_rewrite(user_query, selected_context)

    def _heuristic_rewrite(self, user_query: str, selected_context: List[ConversationTurn]) -> RewriteResult:
        """
        Deterministic heuristic rewrite fallback for offline testing or LLM output parse failures.
        """
        last_turn = selected_context[-1]
        last_query = last_turn.user_query
        last_domain = last_turn.domain_carried_forward or ""
        last_jurisdiction = last_turn.grounded_answer.applicable_jurisdiction

        query_lower = user_query.lower()

        # Check for state location shift (e.g., "What about Karnataka?", "And in Tamil Nadu?")
        states = ["karnataka", "maharashtra", "delhi", "tamil nadu", "kerala", "gujarat", "west bengal"]
        target_state = None
        for state in states:
            if state in query_lower:
                target_state = state
                break

        if target_state:
            # Reframe around target state and subject of last query
            subject = last_domain or last_query
            rewritten = f"What are the legal provisions and applicability of {subject} in {target_state.title()}?"
            return RewriteResult(
                rewritten_query=rewritten,
                resolution_status="resolved",
                carried_jurisdiction=target_state,
                carried_domain=last_domain or "labor_law"
            )

        # Check for pronoun replacement ("this", "that", "it", "its")
        rewritten = user_query
        subject_term = last_domain or "the aforementioned legal provisions"
        for pronoun in [r"\bthis\b", r"\bthat\b", r"\bit\b", r"\bthese\b", r"\bthose\b"]:
            if re.search(pronoun, rewritten, re.IGNORECASE):
                rewritten = re.sub(pronoun, subject_term, rewritten, flags=re.IGNORECASE)

        if rewritten == user_query and ("penalty" in query_lower or "fine" in query_lower or "procedure" in query_lower):
            rewritten = f"{user_query} for {subject_term}"

        return RewriteResult(
            rewritten_query=rewritten,
            resolution_status="resolved",
            carried_jurisdiction=last_jurisdiction if last_jurisdiction != "unclear" else "central",
            carried_domain=last_domain
        )
