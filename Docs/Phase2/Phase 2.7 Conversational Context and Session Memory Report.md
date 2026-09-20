# Phase 2.7: Conversational Context & Session Memory — Formal Implementation & Evaluation Report

**Date:** Sunday, September 20, 2026  
**Executing Agent:** Antigravity  
**Repository:** `BetterCallSaul`  
**Phase Status:** COMPLETE WITH EVALUATION RECONCILIATION  

---

## 1. Executive Summary

Phase 2.7 extends BetterCallSaul from single-turn grounded legal RAG (Phase 2.6) into a multi-turn conversational legal-awareness system. It adds a session state, query rewriting, and context orchestration layer strictly **in front of** the existing Phase 2.5 retriever (`JurisdictionBoostedAdapter`) and Phase 2.6 answer generation pipeline (`GroundedRAGPipeline`), preserving all prior grounding and citation guarantees unchanged.

All core components—session isolation, TTL expiration sweeps, PII redaction, follow-up query classification, bounded context windowing, and reference-resolving query rewriting—were implemented, unit tested, and evaluated against an initial 17-turn scripted validation benchmark.

---

## 2. Key Metrics Summary (Authoritative Evaluation Run)

> [!NOTE]  
> **Evaluation Scope Notice:** This evaluation was conducted over a **17-turn scripted validation set** (across 5 multi-turn sessions). In a 17-turn dataset, a single turn represents **5.88 percentage points**. These results serve as an initial implementation smoke test and baseline rather than a proof of production-scale statistical reliability.

| Metric | Target / Specification | Authoritative Measured Result | Status |
|---|---|---|---|
| **Follow-up Classification Accuracy** | Baseline | **94.1%** (16/17 turns) | PASS |
| **Reference Resolution Accuracy** | Baseline | **100.0%** (17/17 turns) | PASS (Automated) |
| **Jurisdiction Consistency Rate** | **≥ 90.0%** | **76.5%** (13/17 turns) | **BELOW TARGET ❌** |
| **Citation Validity Rate** | 100.0% | **100.0%** (17/17 turns) | PASS (100% Provenance) |
| **Groundedness Structural Pass** | 100.0% | **100.0%** (17/17 turns) | PASS (Automated Check) |
| **Session Isolation Violation Rate** | **0.00%** | **0.00%** (0 cross-session leaks) | **VERIFIED** |
| **Mean Rewrite Context Token Cost** | ≤ 512 tokens | **45.7 tokens** | PASS |
| **P50 Retrieval Latency (Phase 2.5)** | Benchmark | **11471.9 ms** | Candidate Pool + BGE Reranker |
| **P50 Generation Latency (Phase 2.6)** | Benchmark | **0.1 ms** (Mock) / ~1,350 ms (Gemini) | Generation Pipeline |
| **P50 Rewrite Overhead (Phase 2.7)** | Benchmark | **1.7 ms** | Session + Rewrite Layer |
| **P50 Total Pipeline Latency** | Benchmark | **11473.9 ms** | End-to-End RAG |
| **P95 Total Pipeline Latency** | Benchmark | **13776.9 ms** | End-to-End RAG |

---

## 3. Jurisdiction & Classification Root-Cause Analysis

The authoritative evaluation identified **5 total mismatches** (4 jurisdiction mismatches and 1 classification mismatch) out of 17 turns:

### 1. Retrieval & Grounding Evidence Mismatch (3 Turns: #1, #10, #11)
- **Turn #1 (`eval_sess_001 T1`):** User asked about Shops and Establishments Act in *Maharashtra*. Standalone retrieval returned central Act sections; Phase 2.6 `GroundedAnswer` returned `applicable_jurisdiction: "central"`.
- **Turns #10 & #11 (`eval_sess_004 T1 & T2`):** User asked about resignation notice period in *Delhi*. Candidate retrieval returned general central provisions, leading to `central` classification.
- **Impact:** `jurisdiction_carried_forward` defaults to the grounded answer's jurisdiction.

### 2. State Jurisdiction Carry-Forward Tracking (1 Turn: #3)
- **Turn #3 (`eval_sess_001 T3`):** User asked `"What is the penalty for violating this requirement?"` following Turn #2 (`"What about Karnataka?"`).
- **Impact:** Heuristic rewrite fallback resolved the query text but did not explicitly attach `carried_jurisdiction: "karnataka"` to the turn, defaulting to central.

### 3. Coarse Classifier Pattern Overlap (1 Turn: #6)
- **Turn #6 (`eval_sess_002 T3`):** User asked `"What is the procedure for maternity benefit leave under labor laws?"` following a Minimum Wages query.
- **Impact:** `FollowUpClassifier` matched `"What is the procedure..."` under `ELLIPTICAL_PATTERNS`, classifying a topic change as `simple_followup`.

---

## 4. Evaluation Methodology & Scope Clarifications

1. **Reference Resolution Accuracy (100.0%):** Measured via **automated string and status matching** against human-labeled expected resolution targets (`expected_resolution: "resolved" | "ambiguous"`) in `p27_conversations_v1.jsonl`.
2. **Groundedness Structural Pass (100.0%):** This is an **automated structural validation check** verifying that `evidence_sufficiency` is valid and no `ungrounded_claims` or `hallucination` safety flags were raised by Phase 2.6 `GroundingChecker`. It is **not** equivalent to the human 50-query semantic groundedness evaluation conducted in Phase 2.6.
3. **Pattern-Based PII Redaction Scope:** Scans and redacts 4 specific pattern categories (**Aadhaar 12-digit numbers, PAN cards, credit card numbers, and bank account numbers**). Free-text personal names, phone numbers, email addresses, and court case numbers are outside pattern scope.

---

## 5. Architectural Integrity & Frozen Code Compliance

- `src/retrieval/`: **0 lines modified** (100% frozen Phase 2.3/2.5 code).
- `src/generation/`: **0 lines modified** (100% frozen Phase 2.6 code).
- Phase 2.7 functions strictly as an additive wrapper residing entirely within `src/conversation/`.

---

## 6. Conclusion & Reconciled Sign-Off Status

Phase 2.7 successfully demonstrates multi-turn conversational session memory, context selection, PII redaction, and reference resolution without compromising frozen retrieval or generation pipelines. Jurisdiction consistency scored **76.5%** on the 17-turn benchmark (**BELOW TARGET** relative to the 90.0% goal due to state-specific corpus retrieval coverage and carry-forward tagging), which is documented above for future prompt and adapter tuning.
