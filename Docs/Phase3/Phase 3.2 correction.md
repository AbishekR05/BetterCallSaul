# Phase 3.2 — Homepage Visual Redesign Directive (Correction Pass)

**Purpose:** The current build (screenshot reviewed) reads as a generic dark AI/SaaS product landing page, not the warm editorial legal-tech aesthetic specified. This document lists concrete deltas to fix. It supplements, not replaces, `PHASE_3_2_REACT_FRONTEND_SPEC.md` §4–5.

Do not treat this as permission to change scope, add sections, or touch the app/chat UI, auth, or API layer. **Homepage visual layer only.**

---

## 1. Root Cause Diagnosis

The build defaulted to "AI-generated dark SaaS" patterns instead of the reference's "premium editorial law firm" patterns:

| Symptom in current build | Reference does this instead |
|---|---|
| Near-black background on ~80% of the page | Reference is majority **warm white/ivory**, with only 1–2 dark sections used sparingly for contrast |
| Every feature/domain/value item is an icon-in-a-rounded-square (generic Lucide/Feather-style glyphs) | Reference uses **real photography** for hero/about, and plain numbered/text-led cards elsewhere — icons are rare, small, and never the focal element |
| Eyebrow labels on every section ("SYSTEM OVERVIEW", "CORE PRINCIPLES", "JURISPRUDENCE SCOPE", "ARCHITECTURE & WORKFLOW") | Reference uses eyebrow labels sparingly (e.g. "About us", "Our Value") — not on every section, and never in a techy all-caps voice |
| Stat pills/badges floating over the hero image (`<600ms`, `100%`, `BNS/BNSS`) reading like a SaaS dashboard | Reference overlays a single simple stat card (e.g. "152k+ Satisfied Clients") with a small supporting photo, not metric badges |
| Generic card grid for the 8 legal domains, all identical dark boxes with icon + tags | Reference alternates card sizes/colors (some orange-filled, some outline) in an asymmetric grid, mixed with one large photo tile |
| Numbered pipeline (01–05) as plain text steps in a row | Fine as a pattern, but needs warmer background, thinner rule lines, and serif numerals instead of a tech-style progress bar |
| Pricing cards look like SaaS pricing (₹0 / ₹4,999, checkmarks) — reads generic | Restyle to match the two-tone light/dark card treatment from the reference's stat/testimonial cards, keep content as-is |
| Overall type pairing leans sans-heavy with small serif accents | Reference is **serif-led**: large serif display headlines dominate every section, sans-serif is reserved for body/UI text only |
| Rounded pill badges everywhere ("Grounded Indian Penal Code Intelligence") | Reference uses at most one small eyebrow pill in the hero, understated, not neon-orange-on-black |

## 2. Visual System — Corrected Tokens

**Backgrounds:** default section background is warm off-white / ivory (`#F7F4EF`–`#FAF8F4` range), not black. Use near-black only for: the hero, and one deliberate "expertise/values" dark band later in the page (as in the reference) — not 6+ dark sections in a row.

**Text on light sections:** near-black (`#1A1714`-ish) for headings, warm gray for body.

**Accent:** warm orange (`#D9622B`–`#E2703A` range) used sparingly — one CTA button, one label, one card fill per section max. Not on every icon background.

**Typography:**
- Display/headline: elegant serif (e.g. a Playfair/Fraunces-class face), large scale (56–72px desktop hero), tight leading.
- Body/UI: clean sans-serif (e.g. Inter/Söhne-class), smaller scale, generous line-height.
- Eyebrow labels: small sans-serif, letterspaced, used on ≤3 sections total, not every section.
- Remove ALL-CAPS technical-sounding eyebrows ("SYSTEM OVERVIEW", "JURISPRUDENCE SCOPE"). Replace with plain, human labels ("About", "Our approach") or remove the eyebrow entirely.

**Icons/Imagery:**
- Do not use icon-in-rounded-square as the primary visual for Values, Domains, or How-It-Works cards. These read as generic AI/SaaS templates.
- Replace with: real/stock legal photography (courtroom, scales, documents, gavel — same family as the hero image) for at least the About and one other section; text-led cards (numeral + heading + short copy, no icon) for Values and the pipeline steps; a mixed-size card grid (not a uniform 4-up icon grid) for the 8 legal domains, echoing the reference's alternating filled/outline card layout.
- Where an icon is unavoidable (e.g. small inline marker), keep it under 20px and monochrome — never a colored icon inside a rounded gradient box.

**Cards/Surfaces:**
- Soft, warm cards on light background (subtle shadow, 1px hairline border), not dark cards with glow/border-gradient.
- Corner radius modest (8–12px), not the current heavy rounded-square icon tiles.

**Section rhythm:** alternate light → dark → light → light → dark → light, matching the reference's pacing, instead of stacking many dark sections consecutively.

## 3. Section-by-Section Fixes

1. **Hero:** Keep the serif headline and photography, but: reduce badge/stat clutter to one simple metric card overlapping the image (reference style), not three inline stat labels under the CTA row. Eyebrow pill: one only, muted, not glowing orange.
2. **About/System Overview:** Switch background to light/ivory. Use the two-photo stacked-collage treatment from the reference (large photo + offset smaller photo) instead of a single dark photo tile. Drop the "SYSTEM OVERVIEW" eyebrow; use plain "About" or none.
3. **Values ("Core Principles"):** Convert from 4 icon-boxes to text-led cards (large numeral or none, bold heading, 1-line description) on a light or single dark band — pick one, not the current isolated dark section floating between two other dark sections.
4. **Legal Domains grid:** Rebuild as an asymmetric grid mixing 1–2 filled-orange highlight cards with outline/plain cards, per the reference's practice-areas section, dropping the icon-in-box pattern and the small tag pills under each card.
5. **How It Works (5-step):** Keep the 5 stages, lighten the background, use serif numerals, thinner connecting rule, remove the neon progress-bar look.
6. **Pricing:** Keep the two-tier content, but restyle the cards to match the reference's warm card treatment (soft shadow, cream/dark contrast pairing) instead of the current flat dark SaaS-pricing-card look.
7. **Final CTA:** Keep, but confirm it's the *only* orange full-bleed band on the page — currently competing with too many other orange accents elsewhere.
8. **Footer:** Fine as-is structurally; just confirm it follows the same ivory/near-black alternation rather than pure black-on-black with low-contrast gray links.

## 4. What NOT to Change

- Copy/content, section order, and information architecture from `PHASE_3_2_REACT_FRONTEND_SPEC.md` stay the same.
- No new sections, no removed sections.
- No changes to the authenticated app shell, chat UI, or API integration — this pass is homepage visual design only.
- No literal copying of the reference's text, team photos, or law-firm-specific content (still excluded per original spec §5).

## 5. Acceptance Check

Before calling this done, compare the rebuilt homepage against the reference image side-by-side and confirm:
- [ ] Majority of the page is light/ivory, not dark
- [ ] No icon-in-rounded-square card pattern remains
- [ ] At most 2–3 sections use an eyebrow label; none read as "technical/SaaS"
- [ ] At least two sections use real photography as the primary visual, not icons
- [ ] Orange accent appears on ≤3 elements per section, not saturating every card
- [ ] Serif display type is the dominant visual voice on every section heading