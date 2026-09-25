# Natural Speech — H5 (Tom) main-prompt iteration

> Working iteration of the **Heating UK V3.1** agent main prompt (`multiprompt_mvp_main_v3.md`),
> focused on making Tom's voice sound as natural as the Dialux SDR agent ("Linda"), **within the
> same token budget**, while keeping the role an appointment centre (receptionist, not sales).
> This is a local iteration — nothing here is deployed. See the project root `AGENTS.md` / `README.md`.

## What this folder is

A saved session / iteration under `V3.1/Iterations/Natural Speech/` for the **H5 (Heating UK / Tom)**
agent only. It contains the rewritten main prompt plus this readme. It is not wired to the live agent.

## Why this iteration

The Dialux SDR ("Linda") sounds far more natural than Tom, despite a similar token footprint.
Analysis showed the gap is **prompt craft, not token volume**:

- Linda's main prompt is **speech coaching** (contractions, pauses, energy mirroring, varied
  openings, no repetition) — it tells the model *how to talk*.
- Tom's main prompt was mostly **constraint-listing** ("never speak JSON", "don't diagnose",
  "don't quote") — it spends tokens on *what to avoid*, and its KBs are mostly restraint rules.

Goal: give Tom Linda's natural-speech voice while staying an appointment centre, moving boundaries
into KBs as **"what to say"** phrasing instead of "what not to say" lists.

## What changed in the rewritten main prompt

1. **Voice first.** Added a "How you sound (highest priority)" section modelled on Linda's coaching:
   contractions, one-question-per-turn + wait, acknowledgments ("Right", "Got it"), varied
   openings, short turns, no repetition, thinking pauses, natural address/postcode pace,
   light AI-disclosure handling.
2. **Removed all state-machine / schema / transition / graph language.** No mention of states,
   transitions, schemas, or graphs. Flow is plain: *"understand why they called → take the
   address → pick a time → confirm → book."* The platform tracks variables and transitions
   automatically; the prompt no longer tries to explain it.
3. **KB access is trigger-based**, one section per KB ("When the caller asks X → refer to KB"):
   - `##v2-sample-phrases-kb##` — phrasing & acknowledgments, mirroring
   - `##v2-interaction-kb##` — off-script handling
   - `##v2-fees-kb##` — fee / call-out charge (only if asked)
   - `##v2-gas-mention-kb##` — gas / smell / leak mentions
   - `##v2-company-kb##` — company details, opening hours
   - `##v2-call-closing-kb##` — ending the call
4. **Removed "emergency" from the vocabulary** (too alarming for the LLM) — gas section is now
   just "mentions gas, smell, or a leak."
5. **end_call kept verbatim** from the original: only used when *"you are absolutely certain every
   single user query, intent, or inquiry has been fulfilled"* — then refer to the closing KB, say
   goodbye politely, end the call.
6. **Boundaries kept but minimal** (only company-protecting): no diagnosis/fixing, no promising an
   outcome, no repair quotes, no booking a slot the calendar didn't return, no taking payment.
7. **Removed** the invented address-capture KB line.

## Token counts (o200k_base)

| Asset | Old | New |
|-------|-----|-----|
| main prompt | 1,173 | **639** |

New main + single active state:

| state | tokens |
|-------|--------|
| main + greeter | 1,451 |
| main + triage | 1,301 |
| main + address | 1,661 |
| main + slot_selection | 1,611 |
| main + confirmation | 1,707 |
| main + booking | 1,468 |

Old main + state ran 1,835–2,241; new runs **1,301–1,707** (lighter). The freed budget (~530 tokens)
can optionally be folded back into richer voice examples if a closer-to-1,100 main is preferred.

## ✅ WIN — locked in (2026-08-06)

Final main prompt with UK HVAC slang rules added inline (positive "use these terms"
only, no US "never say" list): **765 tokens**. Every state is **under 2,000 tokens**
main+state, the threshold for likely production grade:

| state | main + state |
|-------|--------------|
| greeter | 1,577 |
| triage | 1,427 |
| address | 1,787 |
| slot_selection | 1,737 |
| confirmation | 1,833 |
| booking | 1,594 |

**Status: ALL states under 2k → production-grade-ready.** The saved
`multiprompt_mvp_main_v3_natural_speech.md` includes: natural-speech voice coaching,
the absolute JSON/tool-jargon guardrail, trigger-based KB references, and the UK
HVAC slang block — at 765 tokens, leaving headroom before the 1,000-token soft cap.

## Next steps (not done here)

- Review each KB (`kb_v2_*`) and rewrite restraint rules as positive "what to say" phrasing.
- Optionally enrich the main prompt's voice section with the freed token budget.
- Deploy as a **new** LLM (never patch) and happy-path test per the project build policy.
