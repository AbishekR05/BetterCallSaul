# src/conversation/orchestrator.py
"""
Conversational Orchestration Layer for Phase 2.7 (§5, §6).
Integrates SessionStore, FollowUpClassifier, ContextSelector, QueryRewriter, and SessionPrivacyGuard.
Passes standalone rewritten queries to frozen Phase 2.5 retriever and Phase 2.6 generate_answer pipeline.
"""

import time
import uuid
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.conversation.schemas import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnResult,
    ContextSelectionTrace,
    RewriteResult
)
from src.conversation.session_store import SessionStore, InMemorySessionStore
from src.conversation.privacy_guard import SessionPrivacyGuard
from src.conversation.followup_classifier import FollowUpClassifier
from src.conversation.context_selector import ContextSelector
from src.conversation.query_rewriter import QueryRewriter
from src.generation.llm_client import LLMClient, GeminiClient, MockLLMClient
from src.generation.pipeline import generate_answer
from src.generation.schemas import GroundedAnswer, GenerationMetadata
from src.retrieval.adapters import JurisdictionBoostedAdapter


class ConversationalOrchestrator:
    """
    Main Orchestrator for Phase 2.7 Conversational RAG.
    Public interface: handle_turn(session_id, user_query) -> ConversationTurnResult
    """

    def __init__(
        self,
        config_path: str = "configs/p27_conversation.yaml",
        session_store: Optional[SessionStore] = None,
        retriever_adapter: Optional[Any] = None,
        llm_client: Optional[LLMClient] = None
    ):
        self.config_path = Path(config_path)
        self.config = self._load_config()

        session_cfg = self.config.get("session", {})
        context_cfg = self.config.get("context", {})
        rewriter_cfg = self.config.get("rewriter", {})

        self.session_ttl_minutes = session_cfg.get("session_ttl_minutes", 60)
        self.max_turns_per_session = session_cfg.get("max_turns_per_session", 20)

        max_context_turns = context_cfg.get("max_context_turns", 4)
        max_context_tokens = context_cfg.get("max_context_tokens_for_rewrite", 512)

        # Wire dependencies
        self.session_store = session_store or InMemorySessionStore()
        self.privacy_guard = SessionPrivacyGuard()
        self.followup_classifier = FollowUpClassifier()
        self.context_selector = ContextSelector(
            max_context_turns=max_context_turns,
            max_context_tokens_for_rewrite=max_context_tokens
        )

        # Wire LLM client for rewriter
        if llm_client:
            self.llm_client = llm_client
        else:
            provider = rewriter_cfg.get("llm_provider", "gemini")
            if provider == "mock":
                self.llm_client = MockLLMClient()
            else:
                model_name = rewriter_cfg.get("model", "gemini-3.5-flash")
                self.llm_client = GeminiClient(model_name=model_name)

        prompt_version = rewriter_cfg.get("rewrite_prompt_version", "p27_v1")
        self.query_rewriter = QueryRewriter(llm_client=self.llm_client, prompt_version=prompt_version)

        # Wire frozen Phase 2.5 retriever adapter
        self.retriever_adapter = retriever_adapter or JurisdictionBoostedAdapter()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def handle_turn(
        self,
        session_id: Optional[str],
        user_query: str,
        *,
        retrieval_top_k: int = 8
    ) -> ConversationTurnResult:
        """
        Processes a conversational turn end-to-end (§5).
        """
        turn_start_time = time.time()

        # 1. Session Loader/Creator (§5 Step 1)
        session = None
        if session_id:
            session = self.session_store.get_session(session_id)

        if not session:
            session = self.session_store.create_session(ttl_minutes=self.session_ttl_minutes)

        # 2. Privacy Guard Redaction (§11)
        redacted_query = self.privacy_guard.redact_pii(user_query)

        # 3. Follow-up Classification (§9)
        classification = self.followup_classifier.classify(redacted_query, session.turns)

        # 4. Context Selection (§9)
        selected_context, context_trace = self.context_selector.select_context(
            session.turns, redacted_query, classification
        )

        # 5. Query Rewriting / Reference Resolution (§10)
        rewrite_res: Optional[RewriteResult] = None
        if classification in ("standalone", "topic_change"):
            query_to_retrieve = redacted_query
            rewrite_res = RewriteResult(
                rewritten_query=redacted_query,
                resolution_status="resolved",
                carried_jurisdiction=None,
                carried_domain=None
            )
        else:
            rewrite_res = self.query_rewriter.rewrite(redacted_query, selected_context)

        if classification == "ambiguous_followup" or (rewrite_res and rewrite_res.resolution_status == "ambiguous"):
            # Handle ambiguous follow-up by returning clarifying question (§15)
            ambiguous_answer = GroundedAnswer(
                query=redacted_query,
                answer_summary="The follow-up query is ambiguous relative to prior context.",
                answer_detail="Your request could refer to multiple prior legal topics. Please clarify which specific Act or topic you are referring to.",
                applicable_jurisdiction="unclear",
                evidence_sufficiency="insufficient",
                citations=[],
                caveats=["Ambiguous query reference."],
                clarifying_question="Which specific Act or issue from the prior discussion would you like information on?",
                unused_evidence_count=0,
                generation_metadata=GenerationMetadata(
                    llm_provider=getattr(self.llm_client, "model_name", "none"),
                    llm_model=getattr(self.llm_client, "model_name", "none"),
                    prompt_version="p27_v1",
                    latency_ms_total=(time.time() - turn_start_time) * 1000.0
                ),
                safety_flags=["ambiguous_followup_detected"]
            )
            turn = ConversationTurn(
                turn_id=str(uuid.uuid4()),
                turn_index=len(session.turns) + 1,
                user_query=redacted_query,
                rewritten_query=None,
                followup_classification=classification,
                grounded_answer=ambiguous_answer,
                jurisdiction_carried_forward=None,
                domain_carried_forward=None,
                timestamp_utc=datetime.utcnow().isoformat()
            )
            self.session_store.add_turn(session.session_id, turn, ttl_minutes=self.session_ttl_minutes)
            return ConversationTurnResult(
                session_id=session.session_id,
                turn=turn,
                context_selector_debug=context_trace
            )

        if rewrite_res.resolution_status == "unresolved" or not rewrite_res.rewritten_query:
            query_to_retrieve = redacted_query
        else:
            query_to_retrieve = rewrite_res.rewritten_query

        # 6. Call Frozen Phase 2.5 Retriever Adapter (§5 Step 5)
        retrieval_start = time.time()
        scored_chunks = []
        retrieval_latency_ms = 0.0
        try:
            scored_chunks = self.retriever_adapter.retrieve(query_to_retrieve, top_k=retrieval_top_k)
            retrieval_latency_ms = (time.time() - retrieval_start) * 1000.0
        except Exception as e:
            print(f"[Orchestrator Warning] Retrieval adapter error: {e}")
            retrieval_latency_ms = (time.time() - retrieval_start) * 1000.0

        # 7. Call Frozen Phase 2.6 generate_answer Pipeline (§5 Step 6)
        grounded_answer = generate_answer(
            query=query_to_retrieve,
            scored_chunks=scored_chunks,
            retrieval_latency_ms=retrieval_latency_ms,
            llm_client=self.llm_client
        )

        # 8. Record Turn & Update Session State (§5 Step 7)
        carried_jurisdiction = rewrite_res.carried_jurisdiction if rewrite_res else None
        if not carried_jurisdiction or carried_jurisdiction == "unclear":
            carried_jurisdiction = grounded_answer.applicable_jurisdiction

        carried_domain = rewrite_res.carried_domain if rewrite_res else None
        if not carried_domain and selected_context:
            carried_domain = selected_context[-1].domain_carried_forward

        turn = ConversationTurn(
            turn_id=str(uuid.uuid4()),
            turn_index=len(session.turns) + 1,
            user_query=redacted_query,
            rewritten_query=query_to_retrieve if query_to_retrieve != redacted_query else None,
            followup_classification=classification,
            grounded_answer=grounded_answer,
            jurisdiction_carried_forward=carried_jurisdiction,
            domain_carried_forward=carried_domain,
            timestamp_utc=datetime.utcnow().isoformat()
        )

        updated_session = self.session_store.add_turn(
            session.session_id, turn, ttl_minutes=self.session_ttl_minutes
        )

        return ConversationTurnResult(
            session_id=updated_session.session_id,
            turn=turn,
            context_selector_debug=context_trace
        )
