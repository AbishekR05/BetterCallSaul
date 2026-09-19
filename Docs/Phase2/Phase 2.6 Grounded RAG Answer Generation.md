# Phase 2.6: Grounded RAG Answer Generation — Implementation Specification

**Depends on:** Phase 2.3 (frozen retriever), Phase 2.4 (evaluation framework/harness), Phase 2.5 (retrieval optimization — hybrid/rerank/calibration, experimentally validated)
**Executing agent:** Antigravity
**Status:** SPECIFICATION ONLY — implementation not yet authorized

---

## 1. Phase Objective and Scope

Build the layer that turns Phase 2.5's retrieved, scored, provenance-tagged evidence into a plain-English, source-grounded legal-awareness answer for a single query — with no conversation state, no agentic tool selection, and no multi-turn memory. This is the last purely-request/response layer before any conversational or agentic capability is added.

**In scope:** evidence → prompt → LLM call → structured, cited, safety-checked answer, for one query at a time.
**Out of scope:** everything listed in §16.

---

## 2. Inputs / Outputs and Architecture

```
User query (text)
      │
      ▼
Phase 2.5 retriever (frozen; hybrid + rerank + calibration + jurisdiction boost)
      │  → List[ScoredChunk] with provenance, confidence_tier, relevance scores
      ▼
┌─────────────────────────────┐
│  Phase 2.6 (this phase)      │
│                               │
│  1. Evidence Selector          │
│  2. Context Builder            │
│  3. Prompt Builder             │
│  4. LLM Client (swappable)     │
│  5. Response Parser/Validator  │
│  6. Citation Mapper            │
│  7. Safety/Grounding Checker   │
└─────────────────────────────┘
      │
      ▼
GroundedAnswer (structured object, §7)
```

**Input contract:** the exact `List[ScoredChunk]` object already produced by the Phase 2.5 retriever adapter (no new retrieval call is made inside this phase; Phase 2.6 consumes retrieval output, it does not invoke or re-implement retrieval).

**Output contract:** a single `GroundedAnswer` Pydantic object (§7), returned synchronously from a Python function/FastAPI endpoint — no streaming, no session state, in this phase.

---

## 3. Evidence / Context Construction

### 3.1 Evidence Selector (`src/generation/evidence_selector.py`)
- Takes the retriever's ranked `ScoredChunk` list (already deduped/reranked/calibrated per Phase 2.5) and selects the subset to pass to the LLM.
- Selection rule: take top-N by final rank (config: `max_context_chunks`, default 8), **and** drop anything below `confidence_tier == "low"` unless it's the only evidence available (in which case it's still passed through, flagged, and handled by §9).
- Enforce a token budget (config: `max_context_tokens`, default model-dependent) — if the top-N chunks exceed budget, truncate lowest-ranked first, never truncate mid-chunk.
- Preserve each chunk's full metadata (jurisdiction, document_type, title, section, court, date) alongside its text — nothing is stripped before prompt construction.

### 3.2 Context Builder (`src/generation/context_builder.py`)
- Formats selected chunks into a structured, labeled evidence block, each chunk tagged with a short local reference id (`[E1]`, `[E2]`, ...) used later for citation mapping (§8).
- Each evidence entry in the block includes: local id, document title, document type (legislation/judgment), jurisdiction, section/citation if available, and chunk text.
- Chunks are grouped/ordered: legislation before judgments, higher-confidence before lower-confidence, matching-jurisdiction before other-jurisdiction (when the query has a clear jurisdiction expectation) — ordering only, no chunk is ever silently dropped by this step (dropping happens only in §3.1).

---

## 4. LLM Integration and Model Abstraction

### 4.1 `LLMClient` protocol (`src/generation/llm_client.py`)
```python
class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int, temperature: float) -> LLMResponse: ...
```
- `LLMResponse` carries: raw text, prompt tokens, completion tokens, latency_ms, model_name, model_version/revision, finish_reason.
- No agent/tool-calling capability is used or exposed here — pure text-in/text-out.

### 4.2 Implementations
- `GeminiClient` — wraps the existing Gemini API integration already used in Phase 0 (`gemini-3.5-flash` or current default), config-driven model name.
- `MockLLMClient` — deterministic canned-response client for unit tests, so the pipeline is fully testable without API calls/cost.
- Model selection is entirely config-driven (`configs/p26_generation.yaml: llm.provider`, `llm.model`); no provider-specific logic leaks outside the `llm_client.py` module. Adding a second real provider later means adding one more class implementing `LLMClient` — no changes elsewhere.

### 4.3 Determinism and safety settings
- `temperature` defaults low (0.0–0.2, configurable) since this is a grounded-fact task, not creative generation.
- Any provider-level safety filters are left enabled at their default; Phase 2.6 does not disable or relax provider safety settings.

---

## 5. Grounding Prompt Design

### 5.1 System prompt (fixed, versioned in `src/generation/prompts.py`, not inline in code that calls the LLM)
Must explicitly instruct the model to:
1. Answer **only** from the numbered evidence block provided — never from general/parametric legal knowledge.
2. Cite every substantive claim with its local evidence id (`[E1]`, etc.); a claim with no citation is not permitted.
3. If the evidence is insufficient, contradictory, or jurisdiction-mismatched, say so explicitly rather than filling gaps — the model must prefer an honest "insufficient evidence" response over a confident guess.
4. Never state or imply it is providing legal advice; frame output as legal information/awareness, and include language recommending professional consultation for the user's specific situation, consistent with the project's stated positioning (legal-awareness assistant, not "AI lawyer").
5. Preserve jurisdiction distinctions explicitly in the answer text when evidence spans multiple jurisdictions (e.g., "Under central law... however, in Karnataka specifically...").
6. Output **only** the structured format defined in §6 — no free-form preamble/postamble outside that structure.

### 5.2 User prompt template
Contains: the user's original query, the formatted evidence block from §3.2, and the query's known metadata if available from retrieval (e.g., detected/expected jurisdiction, domain) so the model doesn't have to re-infer it.

### 5.3 Prompt versioning
Every prompt template (system + user template) carries a version string (`prompt_version: "p26_v1"`) recorded in every generation's output/log, so future prompt changes are diffable and A/B-comparable rather than silently drifting.

---

## 6. Structured Response Format

The LLM is instructed (§5.1 point 6) to return JSON matching this schema (validated by §8's parser, not trusted blindly):

```json
{
  "answer_summary": "1-2 sentence plain-English direct answer",
  "answer_detail": "fuller plain-English explanation, citations inline as [E1], [E2]",
  "applicable_jurisdiction": "central | <state/UT> | multiple | unclear",
  "evidence_sufficiency": "sufficient | partial | insufficient",
  "citations_used": ["E1", "E3"],
  "caveats": ["free-text notes, e.g. jurisdiction ambiguity, conflicting evidence, recommend professional consultation"],
  "clarifying_question": "optional — only populated when evidence_sufficiency is 'partial' and a specific missing fact would resolve it"
}
```

This raw model JSON is an intermediate artifact; the pipeline's actual output is the richer `GroundedAnswer` (§7) which wraps this plus resolved citation objects and metadata.

---

## 7. Citation / Provenance Generation and Preservation

### 7.1 `CitationMapper` (`src/generation/citation_mapper.py`)
- Maps each local id (`E1`, `E2`, ...) referenced in `citations_used` back to the original `ScoredChunk`'s full provenance (document_id, title, document_type, jurisdiction, section, court, source URL/reference, relevance grade/score from retrieval).
- Produces a `Citation` object per used reference; citations that appear in the model's text but were **not** in `citations_used`, or reference an id that doesn't exist in the evidence block, are treated as a validation failure (§9.3), not silently accepted.
- Any evidence chunk that was included in the context but never cited is retained in the output as `unused_evidence` (not shown to the end user by default, but logged) — useful for later prompt/quality debugging.

### 7.2 `GroundedAnswer` object (final output, `src/generation/schemas.py`)
```python
class GroundedAnswer(BaseModel):
    query: str
    answer_summary: str
    answer_detail: str
    applicable_jurisdiction: str
    evidence_sufficiency: Literal["sufficient", "partial", "insufficient"]
    citations: list[Citation]          # resolved, full provenance
    caveats: list[str]
    clarifying_question: str | None
    unused_evidence_count: int
    generation_metadata: GenerationMetadata   # §11
    safety_flags: list[str]            # §10
```

Provenance is never summarized away or dropped between retrieval and final output — every `Citation` traces back to a real `chunk_id` retrievable from the database.

---

## 8. Response Parsing and Validation

`src/generation/response_parser.py`:
1. Parse the LLM's raw text as JSON against the §6 schema. On parse failure, retry once with a stricter "return valid JSON only" repair prompt; on second failure, return a `GroundedAnswer` with `evidence_sufficiency="insufficient"` and a `safety_flags` entry `"generation_parse_failure"` — never surface raw/malformed model output to the caller.
2. Validate every id in `citations_used` exists in the evidence block passed to the model (§7.1). Any citation to a non-existent id is stripped and logged as `safety_flags: ["invalid_citation_reference"]`.
3. Validate `applicable_jurisdiction` is consistent with the jurisdictions actually present in the cited evidence (a mismatch — e.g., claims "Karnataka" but all citations are central legislation — is logged as `safety_flags: ["jurisdiction_claim_mismatch"]`, answer still returned but flagged).

---

## 9. Handling Insufficient or Conflicting Evidence

### 9.1 Insufficient evidence
- Signal comes from two places: Phase 2.5's calibrated `confidence_tier` on the retrieved chunks, and the model's own `evidence_sufficiency` field.
- If **retrieval** confidence is low for all candidates (matching Phase 2.5's insufficient-evidence detection), the evidence block passed to the model explicitly states this ("all evidence below confidence threshold") so the model is primed to answer honestly rather than overreach — this directly closes the false-confidence gap Phase 2.5 measured.
- If the model itself reports `evidence_sufficiency = "insufficient"`, the `GroundedAnswer.answer_detail` must not contain confident factual claims beyond what's cited; this is checked structurally (§9.3), not just trusted.

### 9.2 Conflicting evidence
- When cited chunks disagree (e.g., a superseded provision vs. a current one, or differing state rules), the model is instructed (§5.1) to surface the conflict explicitly in `caveats` rather than silently picking one side. Phase 2.6 does not attempt automated conflict resolution (e.g., recency-based override) — that is flagged as a future enhancement, not built here.

### 9.3 Post-hoc grounding check (`src/generation/grounding_checker.py`)
A lightweight, non-LLM heuristic check run on every response before it's returned:
- Every sentence in `answer_detail` containing a citation marker must have that marker resolve to a real, in-context evidence id (already partially covered by §8.2; this step additionally flags sentences that assert something citation-worthy — dates, section numbers, penalty amounts — with **no** citation marker at all, using simple pattern heuristics, not a second LLM call).
- Flags (does not silently rewrite) via `safety_flags`; a human/QA reviewer or a future auto-guard can act on repeated flags. This is a safety-net, not a full factuality verifier — full semantic entailment checking is explicitly out of scope for this phase (see §16).

---

## 10. Hallucination Prevention and Legal-Safety Constraints

- **Evidence-closed generation:** the system prompt (§5.1) plus the structural checks (§8, §9.3) are the two-layer defense — prompt-level instruction and post-hoc structural validation. No claim of "hallucination-free" is made; the goal is measurable reduction and flagging, evaluated in §12.
- **No legal advice framing:** every `GroundedAnswer` with `evidence_sufficiency` of `partial` or `insufficient` must include a caveat recommending professional consultation; this is enforced in code (appended if the model omits it), not left to the model's discretion alone.
- **No fabricated citations:** any citation id not traceable to a real chunk_id is a hard validation failure (§8.2), never passed through.
- **No jurisdiction overreach:** the jurisdiction-consistency check (§8.3) is mandatory on every response.
- **Temperature and prompt fixed/versioned** (§4.3, §5.3) so behavior is reproducible for a given evidence set — critical for both debugging and later evaluation.

---

## 11. Logging, Latency, Token/Cost Tracking

`GenerationMetadata` (embedded in every `GroundedAnswer`):
```python
class GenerationMetadata(BaseModel):
    llm_provider: str
    llm_model: str
    prompt_version: str
    retrieval_adapter_used: str        # which Phase 2.5 config produced the input evidence
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    latency_ms_retrieval: float        # passed through from Phase 2.5, not recomputed
    latency_ms_generation: float
    latency_ms_total: float
    parse_retry_count: int
    timestamp_utc: str
```
- Every generation call is logged (structured JSON log line, local file) with the full `GenerationMetadata` plus `query` and `safety_flags`, for later cost/latency/failure analysis — no raw evidence text needs to be logged by default (config flag `log_full_context: bool`, default `false`, to control log volume/PII exposure).
- Cost tracking uses a per-provider price table in config (`configs/p26_generation.yaml: llm.pricing`), not hardcoded numbers, since prices change.

---

## 12. Evaluation Methodology and Metrics

Phase 2.6 requires a **new** evaluation layer (answer-level, not retrieval-level) — the Phase 2.4 harness evaluates retrieval only and is reused unchanged as the evidence source, not extended in place.

### 12.1 New evaluation dataset
Reuse the Phase 2.4 `p24_queries_v1` query set (same queries, same ground truth documents) as the base, since it already has domain/jurisdiction/difficulty tagging and pooled relevant-evidence judgments — do not author a third independent query set.

### 12.2 Metrics
| Metric | Method |
|---|---|
| **Citation validity rate** | % of citations in output that resolve to real, in-context evidence (should be ~100% by construction per §8; measures whether validation is actually catching failures). |
| **Groundedness / faithfulness** | Human-graded (Abishek, small sample, e.g. 40–60 queries) 0–2 scale: 0 = contains unsupported claim, 1 = mostly grounded with minor overreach, 2 = fully grounded. LLM-as-judge is **not** used as the primary signal in this phase (avoids compounding one model's errors with another's) — it may be piloted informationally but is not authoritative. |
| **Answer relevance** | Human-graded 0–2: does the answer actually address the layman question asked. |
| **Insufficient-evidence honesty rate** | Of queries where Phase 2.5 ground truth says evidence is genuinely absent (`no_evidence_expected` tag), % where the generated answer correctly reports insufficiency rather than fabricating an answer. |
| **Jurisdiction correctness in generated answer** | % where `applicable_jurisdiction` in the output matches the query's `jurisdiction_expectation` tag from Phase 2.4. |
| **Latency** | mean/P50/P95 generation latency, separate from retrieval latency. |
| **Token usage / cost** | mean tokens and estimated cost per query, by query type. |
| **Parse failure rate** | % of generations requiring the JSON-repair retry (§8.1) or failing entirely. |

### 12.3 Report
A `PHASE_2_6_EVALUATION_REPORT.md` (generated after implementation, not part of this spec) follows the same reporting discipline as Phase 2.4: overall metrics, per-domain, per-jurisdiction, per-difficulty-category, failure case listing.

---

## 13. Test Cases and Acceptance Criteria

### 13.1 Required test cases (unit + integration, `tests/generation/`)
- Well-supported query → answer with correct citations, `evidence_sufficiency: sufficient`.
- Query with only low-confidence evidence → `evidence_sufficiency: insufficient`, professional-consultation caveat present.
- Query with conflicting evidence (synthetic fixture) → conflict surfaced in `caveats`, no silent pick.
- Jurisdiction-mismatched evidence (synthetic fixture: query expects Karnataka, evidence is Kerala) → `jurisdiction_claim_mismatch` flag raised.
- Malformed LLM JSON output (via `MockLLMClient`) → repair retry triggers, and second failure path returns safe fallback, never raw text.
- Citation to a non-existent local id (via `MockLLMClient`) → stripped and flagged, does not crash pipeline.
- Empty evidence list (retrieval returned nothing) → clean `insufficient` response, no LLM call wasted (short-circuit before calling `LLMClient`).

### 13.2 Acceptance criteria
1. All §13.1 test cases pass.
2. Citation validity rate = 100% on the evaluation set (structural guarantee, not aspirational).
3. Insufficient-evidence honesty rate reported and reviewed — no numeric target set in advance (consistent with the project's process-over-threshold acceptance philosophy); the first measured rate becomes the documented baseline.
4. Groundedness and answer-relevance human-graded scores reported for the sampled subset (§12.2) — reviewed by Abishek, not gated on a pass/fail number.
5. `LLMClient` swap verified: running the same evaluation subset through `MockLLMClient` and (if available) a second real provider produces valid, schema-conformant output from both, proving the abstraction isn't leaking provider-specific assumptions.
6. No modification to any Phase 2.3/2.5 retrieval file (verified by diff/hash, per existing project discipline).
7. Logging/cost tracking (§11) verified present on every generation in a test run.

---

## 14. Failure Handling

| Failure | Behavior |
|---|---|
| LLM API error/timeout | One retry with backoff (config: `max_retries`, `backoff_seconds`); on final failure, return `GroundedAnswer` with `evidence_sufficiency: insufficient`, `safety_flags: ["llm_call_failed"]`, no partial/garbled answer text. |
| Malformed JSON from model | Repair retry (§8.1); safe fallback on second failure. |
| Empty retrieval input | Short-circuit, no LLM call, immediate `insufficient` response (§13.1). |
| Context exceeds token budget even after truncation | Log `safety_flags: ["context_truncated"]`, proceed with truncated context rather than failing outright. |
| Citation/jurisdiction validation failure | Flag and strip/annotate, never block returning a response (fail open on structure, fail closed on unsupported claims). |

---

## 15. Files / Modules to Implement

```
src/generation/
  schemas.py            # GroundedAnswer, Citation, GenerationMetadata, LLMResponse
  evidence_selector.py
  context_builder.py
  prompts.py             # versioned system/user prompt templates
  llm_client.py           # LLMClient protocol + GeminiClient + MockLLMClient
  response_parser.py
  citation_mapper.py
  grounding_checker.py
  pipeline.py             # orchestrates 1-7 from §2 end to end, single entry point: generate_answer(query, scored_chunks) -> GroundedAnswer
configs/
  p26_generation.yaml      # llm provider/model, temperature, max_context_chunks/tokens, pricing table, retry config
eval/
  generation_eval_harness.py   # reuses p24 queries/ground truth, adds human-grading capture + §12 metrics
tests/generation/
  test_pipeline.py, test_response_parser.py, test_citation_mapper.py, test_grounding_checker.py (covering §13.1)
```

Implementation order: `schemas.py` → `evidence_selector.py`/`context_builder.py` → `prompts.py` → `llm_client.py` (Mock first, Gemini second) → `response_parser.py` → `citation_mapper.py` → `grounding_checker.py` → `pipeline.py` (wiring) → test suite → `generation_eval_harness.py`.

---

## 16. Explicit Boundaries — What Phase 2.6 Must NOT Include

- No modification to Phase 2.3 or Phase 2.5 retrieval code — retrieval is called, never altered.
- No conversational memory, multi-turn context, or session state — one query in, one `GroundedAnswer` out.
- No LangGraph or agent/tool-orchestration logic — this is a fixed, linear pipeline (§2), not an agent that decides what to retrieve.
- No frontend/UI.
- No authentication/user accounts.
- No deployment/Docker/hosting work.
- No commitment to a single paid LLM provider — the abstraction (§4) is mandatory precisely so this isn't locked in.
- No automated factual/entailment verification model (a second LLM-as-judge or NLI model for hallucination detection) — the grounding checker (§9.3) is heuristic/structural only; a stronger verifier is a candidate for a future phase, not built here.
- No automatic conflict resolution between contradictory evidence (§9.2) — conflicts are surfaced, not resolved, by this phase.
- No production database writes beyond the phase's own log files — this phase reads retrieval output and calls an external LLM API; it does not write to `chunks`/`embeddings`.

---

## 17. STOP Condition

**STOP** after the implementation order in §15 completes, the §13.1 test suite passes, and a first `generation_eval_harness.py` run against the Phase 2.4 query set produces a reviewable `PHASE_2_6_EVALUATION_REPORT.md`.

Do not begin conversational memory, agent/LangGraph orchestration, or frontend work. Await Abishek's review and explicit sign-off before scoping the next phase.