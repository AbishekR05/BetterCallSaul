# src/generation/llm_client.py
"""
LLM Client Protocol and Implementations for Phase 2.6 (§4).
Supports GeminiClient (API-based) and MockLLMClient (deterministic testing).
"""

import os
import time
import json
import requests
from typing import Protocol, Optional, Dict, Any
from src.generation.schemas import LLMResponse


class LLMClient(Protocol):
    """Protocol contract for swappable LLM clients (§4.1)."""
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.1
    ) -> LLMResponse:
        ...


class GeminiClient:
    """
    Gemini API implementation wrapping Google Generative Language API (§4.2).
    """

    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.1
    ) -> LLMResponse:
        start_time = time.time()

        if not self.api_key:
            raise ValueError("Gemini API key not found in environment (GEMINI_API_KEY / GOOGLE_API_KEY).")

        # Use REST Endpoint for maximum portability
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{system_prompt}\n\n{user_prompt}"
                }]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json"
            }
        }

        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res.raise_for_status()
        data = res.json()

        elapsed_ms = (time.time() - start_time) * 1000.0

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini API returned no candidates: {data}")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        raw_text = parts[0].get("text", "") if parts else ""

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", len(system_prompt + user_prompt) // 4)
        completion_tokens = usage.get("candidatesTokenCount", len(raw_text) // 4)

        return LLMResponse(
            raw_text=raw_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed_ms,
            model_name=self.model_name,
            model_version="1.0",
            finish_reason=candidate.get("finishReason", "STOP")
        )


class MockLLMClient:
    """
    Deterministic Mock LLM Client for cost-free unit testing and offline evaluation (§4.2).
    """

    def __init__(self, canned_response_mode: str = "sufficient"):
        self.canned_response_mode = canned_response_mode

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.1
    ) -> LLMResponse:
        start_time = time.time()

        if self.canned_response_mode == "sufficient":
            mock_json = {
                "answer_summary": "Under central legal provisions, the action is defined and governed by applicable statutory guidelines.",
                "answer_detail": "According to statutory authorities [E1], specific procedural compliance is required. Legal provisions [E2] outline the penalties for non-compliance.",
                "applicable_jurisdiction": "central",
                "evidence_sufficiency": "sufficient",
                "citations_used": ["E1", "E2"],
                "caveats": ["This output is for legal awareness purposes only and does not constitute formal legal advice."],
                "clarifying_question": None
            }
        elif self.canned_response_mode == "insufficient":
            mock_json = {
                "answer_summary": "Insufficient legal evidence retrieved to provide a definitive legal answer.",
                "answer_detail": "The retrieved passages do not contain explicit statutory provisions addressing this specific query.",
                "applicable_jurisdiction": "unclear",
                "evidence_sufficiency": "insufficient",
                "citations_used": [],
                "caveats": ["Insufficient evidence available in corpus. Consult a legal professional."],
                "clarifying_question": "What specific state jurisdiction applies to this matter?"
            }
        elif self.canned_response_mode == "malformed_json":
            raw_text = "This is not valid JSON content."
            elapsed_ms = (time.time() - start_time) * 1000.0
            return LLMResponse(
                raw_text=raw_text,
                prompt_tokens=100,
                completion_tokens=20,
                latency_ms=elapsed_ms,
                model_name="mock-model",
                model_version="1.0",
                finish_reason="STOP"
            )
        elif self.canned_response_mode == "invalid_citation":
            mock_json = {
                "answer_summary": "Sample response with invalid citation.",
                "answer_detail": "Sample claim referencing non-existent evidence [E99].",
                "applicable_jurisdiction": "central",
                "evidence_sufficiency": "sufficient",
                "citations_used": ["E99"],
                "caveats": ["Legal awareness disclaimer."],
                "clarifying_question": None
            }
        else:
            mock_json = {
                "answer_summary": "Default mock summary.",
                "answer_detail": "Default mock detail with citation [E1].",
                "applicable_jurisdiction": "central",
                "evidence_sufficiency": "sufficient",
                "citations_used": ["E1"],
                "caveats": ["Disclaimer."],
                "clarifying_question": None
            }

        raw_text = json.dumps(mock_json, indent=2)
        elapsed_ms = (time.time() - start_time) * 1000.0

        return LLMResponse(
            raw_text=raw_text,
            prompt_tokens=150,
            completion_tokens=80,
            latency_ms=elapsed_ms,
            model_name="mock-model",
            model_version="1.0",
            finish_reason="STOP"
        )
