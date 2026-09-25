# Heating UK Agent

A Retell AI voice agent for UK HVAC (plumbing & heating) companies. Acts as **"Tom"**, a virtual receptionist that handles inbound calls: symptom triage, UK address capture, appointment booking via Cal.com, and call close.

> **Current status, active flaws, and IDs:** see [`STATE.md`](STATE.md).
> **Design rationale:** [`multiprompt/V3/PROJECT_ROADMAP_V3.md`](multiprompt/V3/PROJECT_ROADMAP_V3.md).

---

## Architecture

```
Retell Voice Agent (voice config)
  └── Retell LLM — 6-state multi-prompt state machine
        ├── general_prompt: identity, voice rules, KBs, company briefing
        ├── starting_state: "greeter"
        │
        ├── GREETER → TRIAGE → ADDRESS → SLOT_SELECTION → CONFIRMATION → BOOKING
        │
        ├── 2-tool pattern per state:  extract_<state>_strings  +  trigger_<state>_transition
        ├── Knowledge Bases: 13 linked
        └── Tools:  check_availability (CUSTOM webhook), book_calendar (Cal.com), end_call (global)
```

The 2-tool pattern (strings separate from the boolean transition trigger) is the structural defence against the V2.1 `""` extraction bug. See `STATE.md` → "Deprecated / superseded".

---

## Versions

| Version | Role | Location |
|---|---|---|
| **V3.1** | **CURRENT iteration** (near-prod; custom slot-webhook integration) | `multiprompt/V3.1/` |
| V3 | prior / deployed iteration (receiving live calls) | `multiprompt/V3/` |
| WEBHOOK_TEST | 2-tool validation spike (throwaway) | `multiprompt/WEBHOOK_TEST/` |
| V2.1 / adapted / original | earlier lineages (history) | `multiprompt/_archive/` |

Each version is self-contained: own `prompts/`, `JSON/` (tool defs + transition edges), `build_v3_llm.py`, and (V3 + V3.1) `Knowledge bases/`. **V3.1 is the canon — don't collapse versions.**

---

## Deploy

Build via the per-version script (creates a **new** LLM — never patch):

```bash
export RETELL_API_KEY=${RETELL_KEY_5}
python3 multiprompt/V3.1/build_v3_llm.py          # creates LLM + a chat test agent
python3 performance_tests/test_v3_llm_to_llm.py   # LLM-to-LLM regression
```

**Build policy:** fork a new builder only for substantial architectural changes; reuse the same `build_v3_llm.py` for LLM-param iterations. After building → audit → wire to the voice agent → publish.

---

## Current deployed resources

> Full table in root [`AGENTS.md`](../../AGENTS.md). Summary:

| Resource | ID |
|---|---|
| V3 test9 copy (voice, receiving calls) | `agent_47e4a4fbdfcbdb7bf2424f418a` |
| V3 LLM (live) | `llm_ae461dfc248342f34b13d81108ec` |
| Production voice agent (FROZEN) | `agent_16985b5d087e56c35141983396` |

### Config

- **Model:** gpt-5.4 (deployed). *Note: `build_v3_llm.py` currently sets `gpt-5.1` — reconcile on next build.*
- **Voice:** `11labs-Anthony` (ElevenLabs `eleven_flash_v2_5`)
- **Language:** en-GB · **Timezone:** Europe/London · **STT:** Deepgram nova-2
- **Calendar:** Cal.com event type **`6522694`** (Diallux Booking Demo, 60 min, Address location). Booking API version `2026-05-01`; cancel `2026-02-25`. Attendee email `jaydiallux@gmail.com`.
- **Slot availability:** our custom webhook → [`../../../cal_slots_endpoint/`](../../../cal_slots_endpoint/) (replaces Retell's native window-returning tool). Fixes F-1/F-2/F-3 once wired into V3.1 tool definitions.

---

## Company variables (Phase 1 — hardcoded literals)

These 7 values are literal strings in the prompt (not `{{placeholders}}`): company `British Heat Services`, region `Newcastle upon Tyne`, Gas Safe `GB-123456`, engineers `Dave, Steve, Mark`, hours `Mon-Fri 8am-6pm, Sat 9am-1pm`, `over 5` years, owner `Mike`.

**Phase 2 (future):** webhook injection for multi-company via `retell_update_live_call` + `retell_llm_dynamic_variables`.

---

## Testing

```bash
python3 performance_tests/test_v3_llm_to_llm.py     # LLM-to-LLM (preferred first pass)
```

Scenarios: `performance_tests/hvac_test_scenarios.md` (18). Results + logs under `performance_tests/`.
Methodology & SOPs: root `docs/Testing_guidelines/`.

---

## Folders

```
heating_uk/
├── STATE.md                 current status + active flaws + deprecation notes
├── README.md                this file
├── multiprompt/             versions container (V3.1, V3, WEBHOOK_TEST, _archive/)
├── original_design/         original single-prompt design
├── single_prompt_test/      archived single-prompt agent + KBs
├── edits/                   dated prompt-edit changelog
└── performance_tests/       scripts, scenarios, json_logs/, retrieved_chats/
```

## Environment

Required in `.env` at project root: `RETELL_API_KEY`, `CAL_COM_API_KEY`.
