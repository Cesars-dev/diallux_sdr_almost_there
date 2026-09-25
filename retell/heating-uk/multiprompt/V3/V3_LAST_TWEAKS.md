# V3 Last Tweaks — Abrupt Hangup Bug Fixes

> Applied live via PATCH to `llm_ae461dfc248342f34b13d81108ec` (agent copy: `agent_47e4a4fbdfcbdb7bf2424f418a`).
> No new LLM/agent deployed — all fixes are live on the existing config.

---

## Bug 1: `speak_after_execution: true` on `book_calendar`

**Symptom:** After `book_calendar` succeeds, the tool result is auto-spoken ("Successfully booked an appointment...") as agent speech. This consumes the LLM's response slot for that turn. The LLM sees "turn done" and jumps straight to `end_call` — never generating the success message, "anything else?" check, or goodbye.

**Evidence:** Call `call_2dc22a80642019115d7e865fbd9`
```
264.9s → book_calendar called
268.7s → booking SUCCESS (booking_id: 23153018)
269.6s → end_call ← 0.9s later, no speech in between
```

**Fix:** `speak_after_execution: false` on `book_calendar` in booking state. PATCHED live.

**Same issue on** `check_availability` in `slot_selection` and `confirmation` states — both patched to `false`.

---

## Bug 2: `extract_booking_details` tool in booking state derails closing

**Symptom:** The pre-flight `extract_booking_details` tool exists in the booking state even though all variables are already set by the time the state is reached. The LLM calls it AFTER `book_calendar` already succeeded, which:
1. Triggers a filler phrase ("Let me note that down") — wasted speech
2. Consumes a turn
3. The LLM then calls `end_call` immediately after, never generating the closing

**Evidence:** Call `call_9d791ebdd28efb99ae2452dc851`
```
236s → book_calendar called → SUCCESS (booking_id: 23154469)
      user: "Okay."
247s → extract_booking_details called ← unnecessary, all vars set
      agent: "Let me note that down." ← filler triggered by tool
249s → end_call
```

**Fix:** Removed `extract_booking_details` from the booking state tools. The pre-flight check is still in the prompt as instructions (verify nulls, ask if missing) but no tool to derail the LLM post-booking. PATCHED live.

---

## Bug 3: Prompt Step 3 "Close" was an escape hatch to `end_call`

**Symptom:** The old Step 3 ("Follow `##v2-call-closing-kb##` for the proper closing structure. Then call `end_call`.") acted as an independent step. The LLM treated it as "Step 3 says call end_call" without generating speech first — especially after a tool result consumed the previous turn.

**Fix:** Merged Steps 2 and 3. The success handler now includes the full closing flow:
1. Say the success message
2. Ask "anything else?"
3. If yes → help, ask again
4. If no → goodbye → `end_call`

Added Critical Rule: *"Always speak to the user after the booking result. Never call `end_call` without speaking first."*
PATCHED live.

---

## State of the Live LLM (`llm_ae461dfc248342f34b13d81108ec`)

| State | Tools | `speak_after_execution` |
|-------|-------|------------------------|
| greeter | `extract_greeter_details`, `trigger_greeter_transition` | both `false` |
| triage | `extract_triage_details`, `trigger_triage_transition` | both `false` |
| address | `extract_address_details`, `trigger_address_transition` | both `false` |
| slot_selection | `check_availability`, `extract_slot_details`, `trigger_slot_transition` | all `false` |
| confirmation | `check_availability`, `extract_confirm_details`, `trigger_confirm_transition` | all `false` |
| booking | `book_calendar` (only!) | `false` |
| general | `end_call` | `true` (harmless — no speech to generate after) |

---

## Calls Referenced

| Call ID | Disconnect | Issue |
|---------|-----------|-------|
| `call_d3605c77c9e71aaf6f726db5a31` | `user_hangup` | User dropped mid-sentence — not a bug |
| `call_2dc22a80642019115d7e865fbd9` | `agent_hangup` | Bug 1: speak_after_execution on book_calendar |
| `call_9d791ebdd28efb99ae2452dc851` | `agent_hangup` | Bug 2: extract_booking_details tool derailed closing |
