# DEPRECATED — Dialux SDR 6.4 (edge-schema null-fix, superseded by 6.5)

> **Status: DEPRECATED.** Do not deploy or edit anything in this folder.
> Superseded by the **6.5** build one level up (`../`), which is the current working agent.

## Why deprecated

This 6.4 build was the **edge-schema null-fix**: each `*.edges.json` was reduced to only its
`required` params so the `transition_to_*` calls would stop dumping not-yet-known vars
(`first_name: null`, `callback_number: null`, `industry: null`) into `collected_dynamic_variables`.

It was deployed 2026-08-22 as a NEW chat agent (`agent_74b34a77089cfbc325f02613c9` / LLM
`llm_043beb4a94649eb959bf31c1e01c`), but the happy-path test could **not** be run because the
Retell account was **blocked with HTTP 402 (payment overdue)** — no chat session could be created.

The transition schema still carried fields we didn't need at each step. The **6.5** build (parent
folder) is the canonical working version that this folder is archived under.

## Contents (archived V6.3 → 6.4 lineage)

- `llm.json` — full deployable LLM payload
- `prompts/` — `general_prompt.md`, `begin_message.txt`, `states/*.md`
- `tools/` — `general_tools.json` + per-state `*.tools.json`
- `edges/` — per-state `*.edges.json` (transition schemas)
- `Knowledge bases/` — the 9 KBs (all reused, no new KBs)
- `knowledge_bases.json` — KB reference list
- `RETEST_REPORT_2026-08-21.md` — V6.3 pass report (context)
- `tini.md` — scratch file

## Transition graph (this archived build)

```
Intake ──[inbound_channel, interest_topic, pain_frame, intake_completed]───────────▶ Discovery
Discovery ──[industry, pain_points, interest_signal, pattern_matched, discovery_completed]─▶ Closer
Closer ──[industry, pain_points, interest_level, closer_completed]───────────────────▶ Offer
Offer ──[livecall_agreed, offer_completed]─────────────────────────────────────────▶ contact_details
contact_details ──[first_name, last_name, company_name, prospect_timezone, callback_number, is_calling_best_number, contact_details_completed]─▶ Booking
Booking ──[booking_confirmed, booking_completed]───────────────────────────────────▶ Closing
Closing ──(terminal)
```