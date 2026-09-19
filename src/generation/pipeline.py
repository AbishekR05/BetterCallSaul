# src/generation/pipeline.py
"""
Single-Entry Orchestration Pipeline for Phase 2.6 Grounded RAG Answer Generation (§2, §15).
Coordinates Evidence Selector, Context Builder, LLM Client, Response Parser, Citation Mapper, and Grounding Checker.
"""

import time
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from eval.schemas import ScoredChunk
from src.generation.schemas import GroundedAnswer, GenerationMetadata
from src.generation.evidence_selector import EvidenceSelector
from src.generation.context_builder import ContextBuilder
from src.generation.prompts import PROMPT_VERSION, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, REPAIR_PROMPT
from src.generation.llm_client import LLMClient, GeminiClient, MockLLMClient
from src.generation.response_parser import ResponseParser
from src.generation.citation_mapper import CitationMapper
from src.generation.grounding_checker import GroundingChecker


class GroundedRAGPipeline:
    """
    End-to-end Phase 2.6 Answer Generation Pipeline.
    Consumes Phase 2.5 ScoredChunks and produces structured, cited GroundedAnswer objects.
    """

    def __init__(self, config_path: str = "configs/p26_generation.yaml", llm_client: Optional[LLMClient] = None):
        self.config_path = Path(config_path)
        self.config = self._load_config()

        llm_cfg = self.config.get("llm", {})
        ctx_cfg = self.config.get("context", {})

        self.max_context_chunks = ctx_cfg.get("max_context_chunks", 8)
        self.max_context_tokens = ctx_cfg.get("max_context_tokens", 2048)

        # Initialize sub-components
        self.evidence_selector = EvidenceSelector(
            max_context_chunks=self.max_context_chunks,
            max_context_tokens=self.max_context_tokens
        )
        self.context_builder = ContextBuilder()
        self.response_parser = ResponseParser()
        self.citation_mapper = CitationMapper()
        self.grounding_checker = GroundingChecker()

        # Wire LLM client
        if llm_client:
            self.llm_client = llm_client
        else:
            provider = llm_cfg.get("provider", "gemini")
            if provider == "mock":
                self.llm_client = MockLLMClient()
            else:
                model_name = llm_cfg.get("model", "gemini-1.5-flash")
                self.llm_client = GeminiClient(model_name=model_name)

    def _load_config(self) -> Dict[str, Any]:
        """Loads configuration from YAML file with default fallbacks."""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculates estimated USD cost based on token pricing table in config."""
        pricing = self.config.get("pricing", {})
        provider = self.config.get("llm", {}).get("provider", "gemini")
        provider_pricing = pricing.get(provider, {})

        prompt_cost = (prompt_tokens / 1000.0) * provider_pricing.get("prompt_token_cost_per_1k", 0.0)
        completion_cost = (completion_tokens / 1000.0) * provider_pricing.get("completion_token_cost_per_1k", 0.0)
        return round(prompt_cost + completion_cost, 6)

    def generate_answer(
        self,
        query: str,
        scored_chunks: List[ScoredChunk],
        *,
        expected_jurisdiction: Optional[str] = "central_only",
        query_type: Optional[str] = "easy",
        retrieval_latency_ms: float = 0.0,
        adapter_name: str = "Phase2.5_Hybrid_Reranked_Calibrated"
    ) -> GroundedAnswer:
        """
        Executes end-to-end generation for a single query (§2).
        """
        pipeline_start_time = time.time()
        safety_flags: List[str] = []

        # 1. Short-circuit on empty retrieval input (§14)
        if not scored_chunks:
            meta = GenerationMetadata(
                llm_provider=getattr(self.llm_client, "model_name", "none"),
                llm_model=getattr(self.llm_client, "model_name", "none"),
                prompt_version=PROMPT_VERSION,
                retrieval_adapter_used=adapter_name,
                latency_ms_retrieval=retrieval_latency_ms,
                latency_ms_generation=0.0,
                latency_ms_total=(time.time() - pipeline_start_time) * 1000.0
            )
            return GroundedAnswer(
                query=query,
                answer_summary="No legal evidence found in the corpus for this query.",
                answer_detail="Retrieval produced no candidate legal chunks. Unable to generate grounded response.",
                applicable_jurisdiction="unclear",
                evidence_sufficiency="insufficient",
                citations=[],
                caveats=["No matching legal documents retrieved. Consult a qualified legal professional."],
                clarifying_question=None,
                unused_evidence_count=0,
                generation_metadata=meta,
                safety_flags=["empty_retrieval_input"]
            )

        # 2. Evidence Selection (§3.1)
        selected_chunks, all_low_conf = self.evidence_selector.select_evidence(scored_chunks)
        if all_low_conf:
            safety_flags.append("all_evidence_low_confidence")

        # 3. Context Construction (§3.2)
        context_block, local_id_map = self.context_builder.build_context(
            selected_chunks,
            expected_jurisdiction=expected_jurisdiction
        )

        # 4. Prompt Construction (§5)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            query=query,
            context_block=context_block,
            expected_jurisdiction=expected_jurisdiction or "unspecified",
            query_type=query_type or "standard"
        )

        llm_cfg = self.config.get("llm", {})
        temp = llm_cfg.get("temperature", 0.1)
        max_tokens = llm_cfg.get("max_tokens", 1024)

        # 5. LLM Call & Retry Loop (§8.1, §14)
        parse_retry_count = 0
        gen_start_time = time.time()
        try:
            llm_response = self.llm_client.generate(
                SYSTEM_PROMPT,
                user_prompt,
                max_tokens=max_tokens,
                temperature=temp
            )
        except Exception as e:
            # LLM API Failure Fallback (§14)
            gen_latency = (time.time() - gen_start_time) * 1000.0
            safety_flags.append("llm_call_failed")
            meta = GenerationMetadata(
                llm_provider=getattr(self.llm_client, "model_name", "error"),
                llm_model=getattr(self.llm_client, "model_name", "error"),
                prompt_version=PROMPT_VERSION,
                retrieval_adapter_used=adapter_name,
                latency_ms_retrieval=retrieval_latency_ms,
                latency_ms_generation=gen_latency,
                latency_ms_total=(time.time() - pipeline_start_time) * 1000.0
            )
            return GroundedAnswer(
                query=query,
                answer_summary="Generation service currently unavailable.",
                answer_detail=f"LLM generation call failed: {str(e)}",
                applicable_jurisdiction="unclear",
                evidence_sufficiency="insufficient",
                citations=[],
                caveats=["Generation call failed. Consult system administrator."],
                clarifying_question=None,
                unused_evidence_count=len(selected_chunks),
                generation_metadata=meta,
                safety_flags=safety_flags
            )

        # 6. Response Parsing (§8)
        parsed_model, parse_flags = self.response_parser.parse_response(
            llm_response.raw_text,
            local_id_map
        )
        safety_flags.extend(parse_flags)

        # Handle 1-retry repair if JSON parse failed (§8.1)
        if "generation_parse_failure" in parse_flags:
            parse_retry_count = 1
            repair_user_prompt = REPAIR_PROMPT.format(query=query, context_block=context_block)
            try:
                llm_response_repair = self.llm_client.generate(
                    SYSTEM_PROMPT,
                    repair_user_prompt,
                    max_tokens=max_tokens,
                    temperature=0.0
                )
                parsed_model_repair, parse_flags_repair = self.response_parser.parse_response(
                    llm_response_repair.raw_text,
                    local_id_map
                )
                if "generation_parse_failure" not in parse_flags_repair:
                    parsed_model = parsed_model_repair
                    safety_flags.remove("generation_parse_failure")
                    safety_flags.extend(parse_flags_repair)
                    llm_response = llm_response_repair
            except Exception:
                pass

        # If evidence was low confidence, override evidence_sufficiency to insufficient (§9.1)
        if all_low_conf:
            parsed_model.evidence_sufficiency = "insufficient"

        # 7. Post-hoc Grounding and Legal Disclaimer Checks (§9.3, §10)
        parsed_model, grounding_flags = self.grounding_checker.verify_grounding(parsed_model, safety_flags)

        # 8. Citation Mapping (§7.1)
        resolved_citations, unused_count = self.citation_mapper.map_citations(
            parsed_model.citations_used,
            local_id_map
        )

        gen_latency = (time.time() - gen_start_time) * 1000.0
        total_latency = (time.time() - pipeline_start_time) * 1000.0
        est_cost = self._calculate_cost(llm_response.prompt_tokens, llm_response.completion_tokens)

        # 9. Assemble Generation Metadata (§11)
        metadata = GenerationMetadata(
            llm_provider=getattr(self.llm_client, "model_name", "gemini"),
            llm_model=getattr(self.llm_client, "model_name", "gemini-1.5-flash"),
            prompt_version=PROMPT_VERSION,
            retrieval_adapter_used=adapter_name,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.prompt_tokens + llm_response.completion_tokens,
            estimated_cost_usd=est_cost,
            latency_ms_retrieval=retrieval_latency_ms,
            latency_ms_generation=gen_latency,
            latency_ms_total=total_latency,
            parse_retry_count=parse_retry_count
        )

        # 10. Construct Final GroundedAnswer (§7.2)
        return GroundedAnswer(
            query=query,
            answer_summary=parsed_model.answer_summary,
            answer_detail=parsed_model.answer_detail,
            applicable_jurisdiction=parsed_model.applicable_jurisdiction,
            evidence_sufficiency=parsed_model.evidence_sufficiency,
            citations=resolved_citations,
            caveats=parsed_model.caveats,
            clarifying_question=parsed_model.clarifying_question,
            unused_evidence_count=unused_count,
            generation_metadata=metadata,
            safety_flags=list(set(grounding_flags))
        )


def generate_answer(
    query: str,
    scored_chunks: List[ScoredChunk],
    *,
    expected_jurisdiction: Optional[str] = "central_only",
    query_type: Optional[str] = "easy",
    retrieval_latency_ms: float = 0.0,
    adapter_name: str = "Phase2.5_Hybrid_Reranked_Calibrated",
    config_path: str = "configs/p26_generation.yaml",
    llm_client: Optional[LLMClient] = None
) -> GroundedAnswer:
    """
    Public entry point function for Phase 2.6 Answer Generation (§2, §15).
    """
    pipeline = GroundedRAGPipeline(config_path=config_path, llm_client=llm_client)
    return pipeline.generate_answer(
        query,
        scored_chunks,
        expected_jurisdiction=expected_jurisdiction,
        query_type=query_type,
        retrieval_latency_ms=retrieval_latency_ms,
        adapter_name=adapter_name
    )
