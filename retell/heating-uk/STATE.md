# STATE — Heating UK Agent (current)

> **Single source of truth for current status.** Read this first.
> Supersedes `memory.md` and `BUG_ANALYSIS.md` (both V2.1-era, archived under `multiprompt/_archive/`).
> Full agent inventory: root [`AGENTS.md`](../../../AGENTS.md). Active work plan: root [`new_plan_sop.md`](../../../new_plan_sop.md) + [`NEXT_STEPS.md`](../../../NEXT_STEPS.md).

---

## TL;DR

- **Current iteration (near-prod):** `multiprompt/V3.1/` — 6-state, custom slot webhook **wired in**, confirmation guardrail **wired in**, Contract A booking, transition-language cleanup. **Built + chat-validated** (2026-08-02, on `merging_logic`).
- **Latest V3.1 build (chat, disposable, NOT on a phone):** LLM `llm_efbc69a19ddce46d1debf2b02cef` / chat agent `agent_c6932cfeebddf1d53bf1cabd8a` (gpt-5.1, 13 KBs). Replaces the prior leaky build (`llm_95d05a23…` / `agent_b361b172…`).
- **Deployed & receiving calls:** V3 "test9 copy" voice agent (`agent_47e4a4fb…`).
- **Production (frozen, do not touch):** Heating UK production (`agent_16985b5d…`).
- **Build:** per-version `build_v3_llm.py` (V3 + V3.1 each own one). **Never patch an LLM — always create new.**

---

## 2026-08-20 → 2026-08-21 — V2 booking contract (local `time` + `timezone`): DEPLOYED + TESTED PASS

- **LLM layer (on disk, done):** V3.1 prompts + `tool_definitions_v3.json` + `transition_*.json`
  slot vars are reworded to **LOCAL time, bare no Z, use `time` never `iso`**. Rebuild picks these up.
- **Endpoint (on disk, done):** `cal_slots_endpoint` `check_availability` takes an optional `timezone`
  arg (default = account tz) and omits `iso` for `diallux` (`include_iso:false`) so the agent can only
  pass local `time` + matching `timezone` (kills the 1h-shift bug, FINDINGS #2/#9).
- **DEPLOYED + TESTED PASS 2026-08-21:** restarted `cal-slots.service` (systemd **user** service for
  `2nd_workspace`, NOT `julio`). Fixed `config.py` (was dropping `include_iso` from the account dict)
  and stale `slots.db-wal/shm` ownership that made SQLite readonly. Built LLM `llm_b8cd0801af2d5386d7af8b59703b`
  + chat agent `agent_c7582c8ecda1f047f7a575c59b`; set `AGENT_ID` in `test_happy_path_today.py` and ran it →
  **RESULT: PASS**. Both bookings fired local `time` and landed at correct UTC (10:00 BST → `09:00:00Z`,
  09:00 BST → `08:00:00Z`) — **no 1h shift** — and were cancelled. Cancel = `POST /v2/bookings/{uid}/cancel`.
  See `PENDING_TASKS.md` PT-29.

### Quality finding (2026-08-21 happy-path test) — fix later
The V3.1 build is **functional** (bookings correct) but feels **robotic / low-quality in delivery**:
- **Repetition:** symptom/brand questions re-asked unnecessarily (worst in the Sarah test — symptom clarify looped 3×, brand re-asked 4×); partial `address_*` extract calls returning empty/`unknown` until all fields given.
- **Filler phrases:** heavy, canned "Taking notes, one moment please", "No problem John/Sarah", "Thanks, Sarah/John" — polite but machine-like and repeated.
- **Unauthorized diagnosis:** both runs volunteered *"Sounds like it could be a pressure or circulation issue."* — violates `v2-diagnostic-restraint-kb` (agent must not speculate).
- **Deferred:** NOT part of the V2 booking contract (that PASSED). Track as a polish/branch task — reduce question re-asks, vary/naturalize filler, and enforce diagnostic restraint. **Fix later.**

## Active resources (IDs)

> Authoritative table is in root `AGENTS.md`. Summary here for quick reference.

| Resource | ID | Notes |
|---|---|---|
| V3 test9 copy (voice, receiving calls) | `agent_47e4a4fbdfcbdb7bf2424f418a` | gpt-5.4, 6-state, inbound via +12137252463 |
| V3 LLM (live) | `llm_ae461dfc248342f34b13d81108ec` | |
| Production voice agent (FROZEN) | `agent_16985b5d087e56c35141983396` | v3 published, 11labs-Anthony |
| Production LLM | `llm_d1d49339820386f4a85ad8d641ea` | |
| Cal.com event type | `6522694` | Diallux Booking Demo, 60 min, Address location |
| Cal.com API key (webhook owner) | `${CAL_KEY_3}` | Akrit's, used by `cal_slots_endpoint` |
| Retell API key | `${RETELL_KEY_5}` | |
| **Calendar test agent v6 (disposable, VALIDATED)** | `agent_f604cbfc7107ea3e6c779d4d09` | LLM `llm_9f9549069b1ab37b284be23e540f`; proof source for the confirmation guardrail + webhook. Not wired to any phone. |
| Custom slot webhook (prod-ready) | `cal_slots_endpoint/` | `https://slots.diallux-ai.site/check_availability`; returns discrete `{day,time,iso}` slots. **Wired into V3.1** (`slot_selection` + `confirmation`). |
| **V3.1 build (chat, disposable, 2026-08-02)** | `agent_c6932cfeebddf1d53bf1cabd8a` | LLM `llm_efbc69a19ddce46d1debf2b02cef` (gpt-5.1, 13 KBs). Transition-language cleanup build. Chat-validated: 5 happy paths booked, `explicit_confirmation=true`, **no raw-JSON speech**. Not on any phone. |

> ⚠️ `V3/build_v3_llm.py` and `V3.1/build_v3_llm.py` set `model: gpt-5.1`, but the deployed V3 LLM is gpt-5.4. Reconcile on next build (follow-up).

---

## Architecture (6-state multi-prompt)

```
GREETER → TRIAGE → ADDRESS → SLOT_SELECTION → CONFIRMATION → BOOKING
```

Shared `general_prompt` + 2-tool pattern per state (extract strings + trigger boolean) — the structural defence against the V2.1 `""` extraction bug.
See `multiprompt/V3/PROJECT_ROADMAP_V3.md` for full design rationale.

**Knowledge bases:** 13 linked. V3.1 has its own copy at `multiprompt/V3.1/Knowledge bases/`. **Audit complete (2026-08-02): 13/13 live KBs verbatim (byte-exact)** vs local files — see `multiprompt/V3.1/KB_AUDIT.md`. No reconciliation needed. Obsolete `uk_hvac_symptom_kb.md` archived to `multiprompt/_archive/` (superseded by `uk-hvac-trade-kb.md`, which the live KB matches).

---

## Active flaws (V3 call analysis)

Source: `multiprompt/V3/call_analysis/ISSUES.md`. Two calls analysed (Maritza, Akrit UK).

| # | Sev | Flaw | Fix | Status |
|---|-----|------|-----|--------|
| F-1 | HIGH | Cal.com returns windows, not slots | custom webhook | **Webhook BUILT + DEPLOYED** (`cal_slots_endpoint/`); wiring into V3.1 pending |
| F-2 | HIGH | hallucinated time not in data | webhook | same as F-1 |
| F-3 | HIGH | re-offers rejected slot | webhook | same as F-1 |
| F-4 | MED | closing flow intermittent | prompt: remove `end_call` from booking tools | TODO |
| F-5 | MED | postcode collection chaotic | prompt: inline hyphenation rules | TODO |
| F-6 | LOW | city/postcode mismatch | UK Cities KB | BACKLOG |
| F-7 | LOW | KB phrase repeated | prompt: no-repeat rule | TODO |
| F-8 | LOW | intent confirm-back skipped | — | accepted (schema enforces) |
| F-9 | LOW | surname dropped | — | accepted |
| F-10 | **HIGH (BLOCKER for prod)** | books with `name: Unknown` when caller never states name | prompt: re-ask + enforce name before `book_calendar`; decouple from `booking` hardcode | TODO (chat-validated build) |
| F-11 | LOW (quality, functional) | robotic delivery: question re-asks (symptom/brand), heavy canned filler phrases, unauthorized "pressure/circulation" diagnosis | polish prompt: one-ask discipline, naturalize/vary filler, enforce diagnostic restraint | TODO (fix later — V2 contract already PASS) |

**F-1/2/3 status (2026-08-02):** the custom webhook + native booking + confirmation guardrail are **wired into V3.1 and validated end-to-end** on the V3.1 build (`agent_c6932cfe…`, 5 happy-path chats booked, `explicit_confirmation=true`, no raw-JSON speech). The disposable calendar test agent v6 remains the original proof source. The `WEBHOOK_TEST_PLAN.md` 2-tool spike is **superseded**.

---

## Confirmation Guardrail — VALIDATED & PROD-READY (2026-08-02)

**The problem we solved:** the agent booked *before* the customer explicitly confirmed — it read a bare `"Okay."`/`"mm-hmm"` as a yes and fired `book_calendar`. (Reproduced on calendar test agent v5.)

**The solve (proven on v6, 10-scenario suite):**
1. **Lean confirmation prompt** (73 lines): read the slot back as a question and STOP; require an affirmative *sentence* (`yes`, `that's right`, `book it`). Bare `okay`/`mm-hmm`/`uh-huh`/`right`/`yeah`/`sure` = backchannel, **NOT** confirmation.
2. **Dual-boolean edge** `confirmation → booking` requires **BOTH** `booking_confirmed` AND `explicit_confirmation` **plus** `booking_slot_string`. One boolean alone can never cross to `book_calendar`.
3. **`explicit_confirmation` tool** sets `true` ONLY on a clear verbal yes, else `false`; `trigger_confirm_transition` (sets `booking_confirmed`) only after confirm + `extract_confirm_details`.

**Evidence** (`agents/heating_uk/performance_tests/test_v3_10_scenarios.py`, results `data/ten_scenario_results.json`):
- **5 cooperative happy paths** → booked, but only after a read-back + explicit yes. Cal verified correct UTC + matching attendee.
- **5 tricky** (hesitant + dog, ambiguous "uhm... right", backtracks after agreeing, vague day, off-topic) → **ALL held**: `explicit_confirmation=false`, `booking_confirmed` unset, **zero** `book_calendar`.

**Webhook is PRODUCTION-READY:** `cal_slots_endpoint/main.py` (custom `check_availability`, discrete slots), public `https://slots.diallux-ai.site/check_availability`. Proven end-to-end. **Wired into V3.1 and validated.**

**DONE (2026-08-02, on `merging_logic`): guardrail + webhook + Contract A wired into V3.1 and built.**
1. `V3.1/JSON/tool_definitions_v3.json` → `slot_selection` + `confirmation` `check_availability` = **custom webhook** (`type: custom`, `url: https://slots.diallux-ai.site/check_availability`, `args_at_root: true`, `slot_target_date` param).
2. `V3.1/JSON/tool_definitions_v3.json` confirmation state → added the **`explicit_confirmation`** tool (verbatim from validated calendar agent).
3. `V3.1/JSON/transition_confirmation_to_booking.json` → required = `['confirmation_completed','explicit_confirmation','booking_slot_string']` (dual-boolean edge).
4. `V3.1/prompts/multiprompt_mvp_confirmation_v3.md` → lean backchannel guardrail ported.
5. Built fresh LLM `llm_efbc69a19ddce46d1debf2b02cef` + chat agent `agent_c6932cfeebddf1d53bf1cabd8a` (gpt-5.1); validated 5 happy-path chats — all booked, `explicit_confirmation=true`, **no raw-JSON speech** (transition-language cleanup confirmed).

**Known deferred items (do not re-litigate now, fix later):**
- **BLOCKER (fix later):** `customer_name` can end up `Unknown` if the caller never states their name, and the agent may still proceed to book with `name: Unknown`. Agent should re-ask for / enforce the name before `book_calendar`. Tied to the `booking` hardcode of `{{customer_name}}` + F-9. **Acceptable for this chat-validation only; fix before prod.**
- 5 tricky personas run to `max_turns` (25) rather than a graceful close; behavior is correct (holds politely), exit is just inelegant.

---

## Stale references (2026-08-02 audit + resolve)

- **`V3.1/JSON/check_availability_tool_v3.json`** — STALE: `type: check_availability_cal`, `event_type_id: 6389911` (legacy event), `cal_api_key: ${CAL_KEY_1}` (stale key). **Not read by the build** (build reads `tool_definitions_v3.json` + `transition_*.json`). Safe to delete (cosmetic cleanup only).
- **`V3.1/JSON/tool_definitions_v3.json`** — ✅ **RESOLVED**: now wires the **custom webhook** (`slot_selection` + `confirmation`), not `check_availability_cal`. Event `6522694`, key `${CAL_KEY_3}`.
- **`V3.1/JSON/transition_confirmation_to_booking.json`** — ✅ **RESOLVED**: required = `['confirmation_completed','explicit_confirmation','booking_slot_string']` (dual boolean).
- **`WEBHOOK_TEST_PLAN.md`** references `webhooks/slots/main.py` + `webhooks/slots/.env` — those paths do **not** exist; code lives in `cal_slots_endpoint/`. Also references `CAL_SLOTS_CUSTOM_FUNCTION.md` and `docs/MCP_Guidelines/...` — **both confirmed missing** (the webhook's real doc is `cal_slots_endpoint/production_grade_cal.md`).
- **STATE line ~32** (unchanged, still open): `V3.1/build_v3_llm.py` sets `model: gpt-5.1` vs deployed gpt-5.4. **Accepted for this build** (transition-cleanup used gpt-5.1 by decision). Follow-up if prod needs gpt-5.4.

---

## Where things live (post-reorg)

```
agents/heating_uk/
├── STATE.md                 ← you are here
├── README.md                ← agent overview
├── multiprompt/
│   ├── V3.1/                ← CURRENT iteration (prompts, JSON, Knowledge bases, build_v3_llm.py, WEBHOOK_TEST_PLAN.md)
│   ├── V3/                  ← prior/deployed iteration (prompts, JSON, Knowledge bases, call_analysis, PROJECT_ROADMAP_V3.md)
│   ├── WEBHOOK_TEST/        ← 2-tool validation spike (throwaway)
│   └── _archive/            ← V2.1, adapted, original + superseded builders/strays + memory_v2.1.md, BUG_ANALYSIS_v2.1.md
├── original_design/  single_prompt_test/  edits/
└── performance_tests/       ← scripts, scenarios, json_logs/, retrieved_chats/
```

---

## Deprecated / superseded (do not treat as current)

| Item | Location | Why deprecated |
|---|---|---|
| `memory.md` | `multiprompt/_archive/memory_v2.1.md` | V2.1-era state snapshot; superseded by this STATE.md + root AGENTS.md |
| `BUG_ANALYSIS.md` | `multiprompt/_archive/BUG_ANALYSIS_v2.1.md` | V2.1 bug list (no-op extraction, day mismatch, etc.); the V3 6-state redesign was built to fix those 9 bugs. Current flaw tracking = `V3/call_analysis/ISSUES.md` (F-1..F-9) |
| `V2.1/`, `adapted/`, `original/` | `multiprompt/_archive/` | earlier prompt lineages superseded by V3/V3.1 |
| `build_multiprompt_llm.py` | `multiprompt/_archive/` | V2-era 3-state builder (event `6389911`, stale key); replaced by per-version `build_v3_llm.py` |
| Cal.com event `6389911` | — | legacy HVAC_UK_appt (Google Meet, 30 min); superseded by `6522694` |
| Retell key `key_bffaf9b…` | (was in archived builder) | stale; current key is `key_a7b26c77…` |
| `retellai-mcp-server` (Node) | `/_archive/retellai-mcp-server` | deprecated local MCP bridge; now using hosted `https://mcp.retellai.com` via `.mcp.json` |
| `agents/_archive/*` (Dialux) | `/_archive/legacy-dialux` | old Dialux sales agents — unrelated to heating_uk |
