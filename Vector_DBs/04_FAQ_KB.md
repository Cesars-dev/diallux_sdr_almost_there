# 04 — FAQ KB status & integration note

**File created (owner-approved content):** `engine/agent/knowledge_bases/faq-kb.md`
(copy in this folder: `faq-kb.md`). Full text with all 17 sections = `faq-kb.md` alongside.

**Status: WRITTEN, NOT INGESTED.** pgvector does not know about it yet.

## What it contains (17 sections)

1. Proof, results & reviews (dashboard + recordings + CRM real-time data)
2. Trust & is this a scam
3. Getting set up (72h receptionist / 1–3 weeks full system)
4. What if the AI doesn't know an answer (warm transfer, never invents)
5. AI vs a real person
6. Cost compared to hiring ($2,500/mo human service anchor, 30–50% cut)
7. Speed to lead (first-to-respond-wins, missed-call costs)
8. Time & money savings (recovered bookings, no-show reduction)
9. Sounds human, not robotic
10. Cheaper options online ($697/month sanctioned string — owner to confirm FAQ-exposure)
11. Identifying the agent ("This is Linda…", wrong-number recovery)
12. Not the decision-maker / hold handling
13. Contract & cancellation (month-to-month, cancel anytime)
14. Text / SMS capability (confirmations + reminders)
15. Works with my phone system (keep number, forward, any carrier)
16. The voice — is it a recording? (top-of-the-line Voice AI, true receptionist)
17. Results guarantee (keep working free until money back)

## Facts provenance

- Sections 1,3–8,10–12: facts sourced verbatim from the 10 existing KBs (mapping table in lab repo `diallux_kb_lab`, commit for build_faq.py).
- Sections 3,13,14,15,16,17 + proof transparency: owner-supplied 2026-09-13 (see 02_DECISIONS.md owner-answers table).
- No invented facts. The two inline `[TODO owner]` markers from the draft were replaced by owner facts.

## Measured impact (real-caller 50, arctic + rerank + 0.24)

| metric | without FAQ | with FAQ |
|---|---|---|
| mean | 0.479 | **1.031** |
| served | 26/50 | 41/50 |
| refusals | 24 | **9** |
| junk served | 1 | 2 |
| mean@served | 0.922 | **1.257** |

15 previously-refused questions now answered (10 at judge 2.00). Full per-question
recovery list in lab `results.db` eval ids 44 → 46.

## Ingest checklist (NEXT SESSION, owner say-so)

1. `cd engine && python scripts/rag_ingest.py --dry-run` → verify chunk counts (10 KBs + faq-kb).
2. Owner "go" → `python scripts/rag_ingest.py` (rebuilds `public.kb_chunks` with CURRENT OpenAI embedder — live behavior unchanged except new KB present).
3. Add `##faq-kb##` marker to the prompts that should see it (general_prompt.md suggested; NOT mechanical states).
4. Threshold decision is separate (see 05_CUTOVER_STEPS.md) — under current OpenAI embedder, leaving 0.40 is the known-harmful status quo; changing it is a one-line .env/config change requiring owner approval per LAW 0.
