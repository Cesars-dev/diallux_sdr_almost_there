# HVAC Agent V3 — Project Roadmap & Deployment Guide

> **Purpose:** This is the master onboarding document for an AI agent (via MCP) that will deploy the V3 HVAC voice agent on Retell. Read this FIRST before touching any other file. It explains what we're building, why each piece exists, where it lives, and the exact order to deploy.
>
> **Audience:** An AI agent (Claude Code, GLM, Cursor, etc.) connected to Retell via MCP. The agent has API access to create/update Retell agents, knowledge bases, tools, and states.

---

## 1. What We're Building

A 6-state multi-prompt voice agent for **British Heat Services**, a fictional UK HVAC (plumbing & heating) company in Newcastle upon Tyne. The agent answers calls 24/7, captures the customer's problem, address, and a slot, then books the appointment via Cal.com.

**The agent's name is Tom.** He's a virtual receptionist — warm, calm, British, efficient. He is NOT a diagnostician. He captures info and books. He never names parts, quotes repair prices, or recommends DIY.

**Target latency:** <1500ms p50 on GPT-5.1
**Target reliability:** 95%+ calls complete the booking flow without errors

---

## 2. Why This Architecture (the design philosophy)

### Why multi-prompt, not single-prompt

Single-prompt agents fail at this complexity. We tried. The prompt balloons to 6-9k tokens, the LLM loses track of rules, tool calls get dropped, and extraction returns empty strings. Multi-prompt gives us per-state isolation: each state has a small prompt (~300-700 tokens), a small set of tools, and one job.

### Why 6 states, not 3 or 8

- **3 states** (our V2.1): each state did too much. The booking prompt was 6KB and handled slot offering + readback + booking + closing. The LLM couldn't hold all the rules.
- **8 states**: too many transitions, each a failure point.
- **6 states**: each state has ONE job. Prompts stay under 700 tokens. Transitions are clean.

### Why the 2-tool pattern (extract strings + trigger boolean)

This is the key innovation that kills the `""` extraction bug from V2.1.

**The bug:** In V2.1, one extract tool held 8-12 variables including strings AND booleans. The LLM fired it early with empty args. Booleans got set to false, strings to `""`. Retell treats `""` as "has a value" — so the transition fired on empty data.

**The fix:** Split each state's tools:
1. `extract_[state]_strings` — strings only, called with actual values
2. `trigger_[state]_transition` — boolean only, called AFTER strings are verified

The boolean is in a separate tool. It can't fire accidentally during string extraction. The LLM must explicitly call the trigger tool after verifying the strings are non-null.

### Why no backward transitions

Retell multi-prompt is linear — you can't go back to a previous state. If the customer wants to change something mid-flow, we use the **upsert pattern**: call the same extract tool again with the new value. Retell overwrites the variable. The agent stays in the current state.

This is why `extract_slot_strings` exists in BOTH the slot_selection state AND the confirmation state — same tool name, same variable names. When the confirmation state calls it again with a new slot, Retell upserts.

### Why filler phrases before transitions

When the agent calls a tool, there's a 1-2 second latency spike. Without a filler phrase, the customer hears dead air and thinks the agent broke. With a filler ("Let me note that down."), the customer perceives a natural pause — like a receptionist checking a diary.

Filler phrases are mandatory before every tool call that triggers a state transition.

---

## 3. The 6-State Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  GREETER │────▶│  TRIAGE  │────▶│ ADDRESS  │────▶│  SLOTS   │────▶│ CONFIRM  │────▶│  BOOK    │
│          │     │          │     │          │     │          │     │          │     │          │
│ Greet    │     │ Symptoms │     │ Address  │     │ Find slot│     │ Confirm  │     │ Execute  │
│ Get name │     │ Brand    │     │ Confirm  │     │ Capture  │     │ Lock in  │     │ Close    │
│ Get intent│    │ Error    │     │          │     │          │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
   ~400 tok        ~500 tok         ~700 tok         ~400 tok         ~400 tok        ~300 tok
   2 tools          2 tools          2 tools          3 tools          4 tools         4 tools
```

### State 1: Greeter
- **Job:** Greet, capture name + intent, confirm
- **Tools:** `extract_greeter_strings` (name, intent) + `trigger_greeter_transition` (greeting_exchanged)
- **Edge schema requires:** `greeting_exchanged=true`, `customer_name`, `classified_intent`

### State 2: Triage
- **Job:** Capture problem category, symptom brief, boiler brand, error code
- **Tools:** `extract_triage_strings` (4 fields) + `trigger_triage_transition` (triage_complete)
- **Edge schema requires:** `triage_complete=true`, `problem_category`, `symptom_brief`
- **Special:** If intent is "quote", handle here → end_call (no transition to address)

### State 3: Address
- **Job:** Capture address (postcode, house number, street, city), confirm
- **Tools:** `extract_address_strings` (4 fields) + `trigger_address_transition` (address_confirmed)
- **Edge schema requires:** `address_confirmed=true`, `address_house_number`, `address_postcode`

### State 4: Slot Selection
- **Job:** Find a slot, offer 1-2 at a time, capture selection
- **Tools:** `check_availability` (Cal.com) + `extract_slot_strings` (2 fields) + `trigger_slot_transition` (slot_selected)
- **Edge schema requires:** `slot_selected=true`, `selected_slot_start`

### State 5: Confirmation
- **Job:** Read back the slot, get confirmation, lock in the booking string
- **Tools:** `check_availability` (safeguard) + `extract_slot_strings` (upsert) + `extract_confirm_strings` (booking_slot_string) + `trigger_confirm_transition` (booking_confirmed)
- **Edge schema requires:** `booking_confirmed=true`, `booking_slot_string`
- **Special:** Can upsert a new slot if customer changes mind — no going back to slot_selection

### State 6: Booking
- **Job:** Pre-flight check, execute booking, close
- **Tools:** `book_calendar` (Cal.com) + upsert tools for pre-flight (extract_greeter_strings, extract_address_strings, extract_confirm_strings)
- **No edge schema out** — terminal state, ends with `end_call`

---

## 4. File Map — What Lives Where

All files are in `/home/z/my-project/download/hvac_agent_prompts/`.

### State Prompts (load these into Retell as the multi-prompt states)
| File | Retell State | Tokens |
|---|---|---|
| `multiprompt_mvp_main_v3.md` | Main prompt (shared across all states) | ~1000 |
| `multiprompt_mvp_greeter_v3.md` | State 1: greeter | ~400 |
| `multiprompt_mvp_triage_v3.md` | State 2: triage | ~500 |
| `multiprompt_mvp_address_v3.md` | State 3: address | ~700 |
| `multiprompt_mvp_slot_selection_v3.md` | State 4: slot_selection | ~400 |
| `multiprompt_mvp_confirmation_v3.md` | State 5: confirmation | ~400 |
| `multiprompt_mvp_booking_v3.md` | State 6: booking | ~300 |

### Knowledge Bases (load these into Retell KBs, link to agent)

**Your existing 7 KBs (already on Retell — just link them):**
1. `##v2-company-kb##` — Company briefing (British Heat Services)
2. `##v2-diagnostic-restraint-kb##` — What Tom can/can't say about diagnoses
3. `##v2-gas-mention-kb##` — Gas/smell/leak handling protocol
4. `##v2-fees-kb##` — Call-out fees (£75 / £120 + VAT)
5. `##v2-interaction-kb##` — Smart interaction rules (mirroring, energy matching)
6. `##v2-knowledge-boundary-kb##` — Tom has no general trade knowledge
7. `##v2-sample-phrases-kb##` — Sample phrase variations

**New KBs to create on Retell (upload these files):**
8. `##uk-address-kb##` — UK address structure, postcode hyphenation for TTS, phonetic alphabet (file: `uk_address_kb.md`)
9. `##uk-hvac-trade-kb##` — HVAC symptom categories, approved phrases, questions, boiler brands, error code rule (file: `uk_hvac_symptom_kb.md`)
10. `##day-logic-kb##` — Day normalization rules (today/tomorrow/next Tuesday), slot offer format (file: `day_logic_kb.md`)
11. `##v2-call-closing-kb##` — 4-step closing structure, varied goodbyes (file: `call_closing_kb.md`)
12. `##uk-names-kb##` — Alphabetical list of common British + Indian names for 100% match (file: `uk_names_kb.md`)
13. `##name-spelling-kb##` — 3-path name confirmation flow, TTS hyphenation for names (file: `name_spelling_kb.md`)

### Tool Definitions
| File | Purpose |
|---|---|
| `tool_definitions_v3.json` | All extract tools, trigger tools, Cal.com tools, end_call — per state. Load via Retell API or dashboard. |

### Transition Schemas
| File | Purpose |
|---|---|
| `transition_schemas_v3.md` | 5 forward transition JSON schemas (greeter→triage, triage→address, address→slots, slots→confirm, confirm→booking). No backward transitions. |

---

## 5. Deployment Order (Step-by-Step)

Deploy in this exact order. Don't skip steps.

### Phase 1: Knowledge Bases (create first, link later)

1. **Create 6 new KBs on Retell** (the 7 existing ones are already there):
   - Upload `uk_address_kb.md` → name it `uk-address-kb`
   - Upload `uk_hvac_symptom_kb.md` → name it `uk-hvac-trade-kb`
   - Upload `day_logic_kb.md` → name it `day-logic-kb`
   - Upload `call_closing_kb.md` → name it `v2-call-closing-kb`
   - Upload `uk_names_kb.md` → name it `uk-names-kb`
   - Upload `name_spelling_kb.md` → name it `name-spelling-kb`

2. **Wait for KB processing to complete** (Retell shows status: in_progress → complete).

### Phase 2: Create the Agent

3. **Create a new multi-prompt agent** on Retell named "British Heat Services V3".
4. **Set the LLM** to GPT-5.1 (or GPT-5.4 fast if 5.1 isn't available — but 5.1 is preferred for this architecture).
5. **Set TTS** to ElevenLabs v2 with a British voice (match Newcastle region if possible).
6. **Set timezone** to Europe/London.
7. **Set temperature** to 0.1-0.3 (deterministic for data capture).
8. **Enable structured output** (required for reliable tool calls).
9. **Enable Fast Tier** (1.5x cost, but kills p90 latency spikes).

### Phase 3: Link Knowledge Bases

10. **Link all 13 KBs** to the agent (7 existing + 6 new).
11. **Set KB retrieval** to 3 chunks, 0.60 similarity threshold (Retell defaults — they work).

### Phase 4: Load the Main Prompt

12. **Paste `multiprompt_mvp_main_v3.md`** into the agent's Main Prompt field. This is shared across all states.

### Phase 5: Create the 6 States

13. **Create State 1: greeter**
    - Paste `multiprompt_mvp_greeter_v3.md` as the state prompt
    - Add tools from `tool_definitions_v3.json` → `states.greeter.tools`
    - Add the `end_call` general tool
    - Add transition schema: greeter → triage (from `transition_schemas_v3.md` section 1)

14. **Create State 2: triage**
    - Paste `multiprompt_mvp_triage_v3.md`
    - Add tools from `tool_definitions_v3.json` → `states.triage.tools`
    - Add `end_call`
    - Add transition: triage → address (section 2)

15. **Create State 3: address**
    - Paste `multiprompt_mvp_address_v3.md`
    - Add tools from `tool_definitions_v3.json` → `states.address.tools`
    - Add `end_call`
    - Add transition: address → slot_selection (section 3)

16. **Create State 4: slot_selection**
    - Paste `multiprompt_mvp_slot_selection_v3.md`
    - Add tools from `tool_definitions_v3.json` → `states.slot_selection.tools`
    - Add `end_call`
    - Add transition: slot_selection → confirmation (section 4)

17. **Create State 5: confirmation**
    - Paste `multiprompt_mvp_confirmation_v3.md`
    - Add tools from `tool_definitions_v3.json` → `states.confirmation.tools`
    - Add `end_call`
    - Add transition: confirmation → booking (section 5)

18. **Create State 6: booking**
    - Paste `multiprompt_mvp_booking_v3.md`
    - Add tools from `tool_definitions_v3.json` → `states.booking.tools`
    - Add `end_call`
    - No transition out (terminal state — ends with end_call)

### Phase 6: Configure Cal.com Integration

19. **Verify the Cal.com event_type_id** is `6389911` and the API key is `${CAL_KEY_1}` (already in the tool definitions).
20. **Test the Cal.com connection** by calling `check_availability` in the Retell playground.

### Phase 7: Test in Retell Playground

21. **Run the 3 core scenarios** from the test scenarios file:
    - Cold boiler breakdown, new customer
    - Returning customer, annual service
    - Customer asks about the fee mid-booking

22. **Check the latency** in the call dashboard. Target: <1500ms p50.

23. **Check the extraction** — verify no `""` values in the captured variables. If any appear, the 2-tool pattern failed and the agent skipped the verify step.

### Phase 8: Wire to a Phone Number

24. **Assign a Retell phone number** to the agent.
25. **Test with a real call** from your phone.

---

## 6. Critical Design Decisions to Preserve

When iterating or debugging, do NOT change these without explicit approval:

### Decision 1: 2-tool pattern (extract strings + trigger boolean)
Every state has separate tools for strings and booleans. The boolean tool is only called AFTER the string tool is verified. This is the structural defence against the `""` extraction bug.

### Decision 2: No backward transitions
Retell multi-prompt is linear. If the customer wants to change something, use the upsert pattern (call the same extract tool again with the new value). Never create a backward transition.

### Decision 3: Filler phrases before tool calls
Every state transition section starts with "Say a filler phrase." This is mandatory — it covers the latency spike.

### Decision 4: KBs for content, prompts for logic
Symptom questions, address rules, day logic, call closing, name matching — all in KBs. Prompts contain only state-specific logic and flow. This keeps prompts under 700 tokens.

### Decision 5: Verbatim variable names for upsert
`customer_name` is the same in greeter, triage (if used), and booking. `selected_slot_start` is the same in slot_selection and confirmation. `booking_slot_string` is the same in confirmation and booking. This is what makes upsert work — Retell overwrites when you extract again with the same name.

### Decision 6: Booleans can't be null
Booleans (`greeting_exchanged`, `triage_complete`, `address_confirmed`, `slot_selected`, `booking_confirmed`) default to false and can only be set to true via the trigger tool. They can't be `""`. This is the guardrail.

### Decision 7: Specific times, not windows
Slot offers always use "[DAY] at [TIME]" format (e.g., "Thursday at 2 PM"). Never "between 1 and 5" — that caused Bug #3 (day mismatch) in V2.1.

### Decision 8: Name capture with KB matching
The greeter uses `##uk-names-kb##` for 100% match and `##name-spelling-kb##` for confirmation. This prevents misspelled names from polluting the Cal.com booking.

---

## 7. What Each KB Does (and when it loads)

KBs are retrieved automatically based on the conversation context. Here's when each loads:

| KB | When it loads | What it provides |
|---|---|---|
| `##v2-company-kb##` | When customer asks about the company | Company name, Gas Safe reg, engineers, hours |
| `##v2-diagnostic-restraint-kb##` | When customer asks "what's wrong with my boiler" | Refusal phrase, what Tom can/can't say |
| `##v2-gas-mention-kb##` | When customer mentions gas, smell, or leak | Gas emergency script, 0800 111 999 |
| `##v2-fees-kb##` | When customer asks about cost | Call-out fees, repair cost refusal |
| `##v2-interaction-kb##` | Every turn (core interaction rules) | Mirroring, energy matching, off-script handling |
| `##v2-knowledge-boundary-kb##` | Every turn (core boundary) | Tom has no trade knowledge — use KBs only |
| `##v2-sample-phrases-kb##` | Every turn (sample phrase variations) | Alternative phrasings for common responses |
| `##uk-address-kb##` | When conversation hits address terms (postcode, street) | Postcode hyphenation, phonetic alphabet, field mapping |
| `##uk-hvac-trade-kb##` | When conversation hits heating terms (boiler, radiator) | Symptom categories, approved phrases, questions |
| `##day-logic-kb##` | When conversation hits time/day terms (today, tomorrow) | Day normalization, this week vs next week, slot format |
| `##v2-call-closing-kb##` | When agent is about to call end_call | 4-step closing structure, varied goodbyes |
| `##uk-names-kb##` | When agent captures a name | 100% match list |
| `##name-spelling-kb##` | When name doesn't match the names KB | 3-path confirmation flow, TTS hyphenation |

---

## 8. The 9 Bugs We're Solving (from V2.1 analysis)

This architecture was designed to fix these specific bugs. If you see them reappear in testing, the corresponding design decision was violated.

| Bug | V2.1 cause | V3 fix |
|---|---|---|
| 1. No-op extraction (empty args) | 10-12 fields per tool, LLM fired early with `""` | 2-tool pattern: 2-4 string fields, separate boolean trigger |
| 2. No dep guard before book_calendar | book_calendar in same state as check_availability | Separate booking state — can't reach it without confirmation |
| 3. Slot day mismatch (said tomorrow, booked today) | LLM stripped day labels from offer format | Hard rule in slot_selection: always "[DAY] at [TIME]" |
| 4. Readback skipped | Prompt rule, easily ignored by LLM | Dedicated confirmation state — readback is the entire purpose |
| 5. address_confirmed set without user confirmation | LLM bypassed the prompt rule | Separate trigger tool, only callable after explicit confirmation |
| 6. No terminal state for "quote" intent | Quote callers got stuck in the flow | Triage state handles quote → end_call |
| 7. Latency too high (2200ms+) | 8-variable extract tool, 6KB booking prompt | Small tools (2-4 fields), small prompts (300-700 tokens) |
| 8. Hallucinated booking (zero tool calls) | book_calendar accessible in wrong state | book_calendar only in booking state — can't say "booked" elsewhere |
| 9. Vague time window (1.5h range) | LLM offered "between 1 and 5" | Specific times only: "[DAY] at [TIME]" |

---

## 9. Testing Checklist

Before going live, verify:

- [ ] All 13 KBs are linked and status is "complete"
- [ ] All 6 states created with correct prompts
- [ ] All tools loaded per `tool_definitions_v3.json`
- [ ] All 5 transition schemas loaded
- [ ] Cal.com integration working (test check_availability in playground)
- [ ] GPT-5.1 model selected
- [ ] ElevenLabs v2 TTS with British voice
- [ ] Fast Tier enabled
- [ ] Temperature 0.1-0.3
- [ ] Structured output enabled

Run these test calls:
- [ ] Cold boiler breakdown, new customer (happy path)
- [ ] Returning customer, annual service
- [ ] Customer asks about the fee mid-booking
- [ ] Customer spells their postcode phonetically
- [ ] Customer changes mind mid-confirmation (test upsert)
- [ ] Customer has an unusual name (test name spelling KB)
- [ ] Customer says "quote" intent (test triage quote handling)
- [ ] Customer rejects 5 slot offers (test max 5 escalation)

For each call, check:
- [ ] No `""` values in extracted variables
- [ ] Latency p50 < 1500ms
- [ ] Booking lands in Cal.com with correct details
- [ ] Engineer handover notes are populated correctly

---

## 10. If Something Breaks

### Symptom: Agent stuck in a state, won't transition
- Check: did the extract_strings tool fire with non-empty values?
- Check: did the trigger_transition tool fire after?
- Fix: the agent may be skipping the verify step. Reinforce "verify non-null before triggering" in the state prompt.

### Symptom: `""` values in extracted variables
- Check: is the agent calling the extract tool with empty arguments?
- Fix: ensure the agent says the filler phrase first, THEN calls the tool with actual values from the conversation.

### Symptom: Latency above 1500ms
- Check: Get Call API latency breakdown — is it LLM, KB, or TTS?
- If LLM: prompt may be too large. Verify each state prompt is under 700 tokens.
- If KB: too many KBs loading per turn. Check if all 13 are necessary for the current state.
- If TTS: switch to a lower-latency voice.

### Symptom: Booking fails with Cal.com 400 error
- Check: is `customer_name` populated? (Pre-flight check should catch this.)
- Check: is `booking_slot_string` in ISO 8601 UTC with Z suffix?
- Check: is the email `jaydiallux@gmail.com`?

### Symptom: Agent says "booked" without calling book_calendar
- Check: this should be impossible in V3 — book_calendar only exists in the booking state.
- If it happens: the agent is hallucinating. Reinforce "don't say 'booked' before book_calendar returns success" in the booking prompt.

---

## 11. Sources & References

- **V2.1 bug analysis:** `BUG_ANALYSIS.md` (in upload folder)
- **Retell docs:** https://docs.retellai.com/
- **Retell Extract DV docs:** https://docs.retellai.com/build/single-multi-prompt/extract-dv
- **Retell LLM Options:** https://docs.retellai.com/build/llm-options
- **Retell Latency breakdown:** https://docs.retellai.com/reliability/check-actual-latency
- **Engineering reference:** `retell_engineering_reference.md` (in this folder)
- **Production architecture:** `production_voice_ai_architecture.md` (in this folder)

---

## Final Note for the Deploying Agent

This architecture is the result of 4 iterations (V1 single-prompt → V2.1 multi-prompt 3-state → V3 6-state with 2-tool pattern). Every design decision exists because a specific bug was observed in production testing. Don't "simplify" or "optimize" without understanding why each piece is here.

If you're unsure about a change, ask the human. Don't guess. The architecture is bulletproof as designed — the risk is in deviating from it.

**Deploy in order. Test each phase. Don't skip steps.**
