# Phase 3.2 — React Frontend & Application UI: Implementation Specification

**Project:** BetterCallSaul
**Phase:** 3.2
**Type:** Implementation specification (specification only — no code, no frontend build)
**Baseline:** Phase 3.0/3.1 FastAPI `/api/v1` contract (frozen, consumed as-is)

---

## 1. Objective

Design a React + TypeScript SPA that presents BetterCallSaul as a premium legal-intelligence product — a marketing homepage plus an authenticated conversation application — built strictly on the existing `/api/v1` REST contract, and structured so a future agentic layer can surface step-level status without a UI redesign.

## 2. Baseline & Constraints

- Consumes `/api/v1` (auth, sessions, turns, health) exactly as specified in Phase 3.0/3.1. No backend changes.
- No direct DB/RAG access from the client; no client-supplied `user_id`; identity always comes from the bearer token.
- Reference image is visual inspiration only (typography, palette, spacing, imagery, card/section rhythm) — not content, copy, or literal layout. Remove anything law-firm-specific (see §11).

## 3. Stack

- React + TypeScript + Vite, component-based CSS (CSS Modules or a lightweight utility approach — implementer's choice, documented in the report).
- REST client via `fetch`/`axios` wrapped in a typed service layer.
- No Next.js. No state-management framework beyond React context/hooks unless the report justifies one.

## 4. Visual Direction (from reference, adapted)

- Elegant serif display type for headings; clean sans-serif for UI text.
- Palette: near-black, warm white, muted gray, warm orange accent.
- Alternating light/dark sections, generous whitespace, large display type, editorial composition.
- Lady Justice / scales imagery used as abstract/editorial motif, not stock law-firm photography of specific "attorneys."
- Subtle motion (fades/slides on scroll), respecting `prefers-reduced-motion`.
- No literal copying of the reference's text, team photos, or stats.

## 5. Homepage (Public, Unauthenticated)

Single long-scroll landing page, sections in order:

1. **Hero** — headline, one-paragraph product explanation, primary CTA "Start Chatting" (→ login/register), secondary CTA "How It Works" (→ in-page anchor). Strongest visual section; Lady Justice/scales imagery.
2. **About BetterCallSaul** — plain-language explanation: makes Indian law easier to understand, evidence-grounded answers, explicit information-vs-advice distinction.
3. **Our Values** — 4 concise cards: Evidence First, Clarity Over Complexity, Privacy by Design, Responsible AI.
4. **Find Answers to Your Legal Questions** — grid/accordion of domain categories (Consumer Rights, Property, Employment, Family, Business, Cyber Law, Contracts, Criminal Law). Each card links into the chat app pre-seeding a starting topic (no backend change required — passed as initial client-side prompt text).
5. **How BetterCallSaul Works** — 5-step visual: Understand Situation → Find Relevant Legal Sources → Check Evidence/Jurisdiction → Generate Grounded Explanation → (implicit) Cited Answer. High-level only, no chain-of-thought language.
6. **Plans** — visually consistent placeholder tiers (e.g., Free / Pro, illustrative feature bullets only). No real prices, no payment UI, no subscription logic. Clearly a UI shell for future billing integration.
7. **Final CTA** — closing section driving to "Start Chatting."
8. **Footer** — product/resource/account links, Privacy, Terms, and a persistent legal-information disclaimer line.

Explicitly excluded from the reference: Our Team, named lawyers/professionals, client testimonials, client counts/stats, "Book a Consultation," law-firm claims, invented credentials.

## 6. Authenticated Application

### 6.1 Login / Register
- Two forms (email/identifier + password), client-side validation mirroring backend field limits (Phase 3.1 §6). Surfaces backend error codes (`unauthenticated`, `conflict`, `rate_limited`, `validation_error`) as plain-language messages — never raw API error bodies.
- Token stored in memory + short-lived persistence (e.g., sessionStorage) — never logged, never placed in URL params.

### 6.2 Application Shell
- Persistent left/side rail: new conversation, session list, account/logout.
- Main panel: active conversation workspace.
- Route protection: authenticated routes redirect to login when unauthenticated or on 401; token cleared on logout/expiry.

### 6.3 Session List
- Fetched via `GET /sessions`; shows title/last-activity; create via `POST /sessions`; delete via `DELETE /sessions/{id}` with confirmation.
- Only the current user's sessions are ever requested or rendered (no client-side merging across users).

### 6.4 Conversation Workspace
- Empty state: friendly prompt + disclaimer + suggested domain starters (from homepage categories).
- User messages and BetterCallSaul responses in a standard chat layout.
- Responses render: plain-English answer, **inline citation markers** linking to a evidence panel (document title, section, jurisdiction — from `GroundedAnswerResponse` fields), and a persistent disclaimer ("Legal information, not legal advice").
- Loading state: distinct "thinking" indicator using the agent-ready status pattern (§7), not a bare spinner.
- Error states, mapped from Phase 3.1 error codes:
  - `429 rate_limited` → "You're sending messages too fast" + retry timing from `Retry-After`.
  - `503 server_busy` / `dependency_unavailable` → "BetterCallSaul is temporarily unavailable, please retry."
  - `504 upstream_timeout` → "This is taking longer than expected" + retry action.
  - `409 session_busy` → disable input until the in-flight turn resolves.
  - Generic 4xx/5xx → uniform fallback message; never render raw `error_code`/stack content to the user (a small "details" affordance may show `request_id` only, for support).
- Request cancellation: leaving a conversation or navigating away aborts the in-flight turn request (`AbortController`); UI reflects cancellation distinctly from failure.

## 7. Agent-Ready Design (UI only, no agent logic)

- Loading/status indicator is a **step-list component** driven by a small enum (`understanding | searching | checking_evidence | preparing_response`), not free text.
- In Phase 3.2, the backend does not emit step events, so the component runs a deterministic client-side simulated sequence during the wait (documented as a placeholder). It must be architected so a future real status stream (e.g., SSE/WebSocket) can replace the simulated timer without changing the component's public interface.
- No chain-of-thought, intermediate model output, or retrieved-document dumps are ever rendered — only the high-level stage labels and, on completion, the final grounded answer with citations.

## 8. API Integration Layer

- Typed client module per resource (`authApi`, `sessionsApi`, `turnsApi`, `healthApi`), all requests/responses typed from the Phase 3.0 DTOs.
- Central auth interceptor: attaches bearer token, redirects to login on 401, never attaches or exposes `user_id` client-side.
- Central error normalizer: maps every non-2xx response to a typed `ApiError { errorCode, message, requestId }` used uniformly by UI error states (§6.4).
- No direct database or RAG/vector-store access from the client under any code path.

## 9. Security & Privacy

- No password, token, or `Authorization` header ever logged to console or sent to analytics.
- Model-generated content rendered as sanitized text/markdown (no `dangerouslySetInnerHTML` without sanitization) to prevent injected HTML/script from a generated answer.
- No storage of unnecessary personal/legal information client-side beyond what's needed for the active session view; conversation content not persisted outside the backend's own session store.
- Disclaimer ("legal information, not legal advice") visible on homepage About section, chat empty state, and every generated answer.

## 10. Responsive Design

- Breakpoints: desktop (≥1024px), tablet (768–1023px), mobile (<768px).
- Homepage: multi-column sections collapse to single-column stacks on tablet/mobile; hero imagery scales, not crops awkwardly.
- App shell: session rail collapses to a slide-over/drawer on tablet and mobile; conversation workspace remains full-width and usable one-handed on mobile.

## 11. Accessibility

- Semantic HTML landmarks (`header`, `nav`, `main`, `footer`); heading hierarchy preserved.
- Full keyboard navigation for nav, forms, session list, and chat input/send; visible focus states throughout.
- Contrast meeting WCAG AA on both light and dark sections (verify orange accent against dark backgrounds).
- Form fields and buttons carry accessible labels/`aria-*` where icon-only.
- `prefers-reduced-motion` disables/reduces scroll and loading animations.

## 12. Testing Requirements (high level)

- Component tests: hero/section rendering, chat message rendering (incl. citations), error-state components, step-status component.
- API client tests: request shaping, auth header attachment, error normalization for each mapped status code (§6.4).
- Auth flow tests: login/register success and failure, token expiry redirect, logout clears state.
- Session isolation: UI never requests/displays another user's session data (mocked API boundary tests).
- Chat interaction tests: send/receive, loading state, cancellation, disabled input during `session_busy`.
- Error-state tests: one test per mapped error code in §6.4.
- Responsive/accessibility checks: breakpoint snapshot or viewport tests; automated a11y lint (e.g., axe) on key screens.
- Safe rendering: test that generated content containing HTML/script is rendered inert.

## 13. Non-Goals

Agent implementation or LangGraph; new RAG/retrieval or LLM architecture; database redesign; OAuth redesign; real payment/billing implementation; admin dashboard; legal-professional marketplace; fake statistics, testimonials, or team bios; Next.js migration.

## 14. Acceptance Criteria

1. Homepage renders all 8 sections per §5, responsive across breakpoints, with no excluded content (§5 exclusion list).
2. Authenticated app supports login/register, session list, new conversation, conversation workspace, and logout end-to-end against the real `/api/v1` contract (or a mocked equivalent for tests).
3. Every Phase 3.1 error code in scope (§6.4) has a distinct, user-safe UI state; no raw backend error detail is ever rendered.
4. No client code path reads/writes `user_id`, tokens, or another user's session data outside the sanctioned auth flow.
5. Step-status component is implemented against a documented enum interface, decoupled from its current simulated data source.
6. Accessibility and responsive requirements (§10–11) verified by the test suite in §12.
7. Generated content rendering is XSS-safe (tested).
8. No modification to backend code, contracts, or infrastructure.

## 15. Artifacts

- This specification document, committed to the repository.
- (Future implementation phase) `frontend/` React+TS+Vite app, typed API client, component/test suites, and a `PHASE_3_2_REPORT.md` on completion.

## 16. STOP Condition

**STOP.** This document is specification only. Do not scaffold the Vite project, write components, or install frontend dependencies until this spec is reviewed and signed off.