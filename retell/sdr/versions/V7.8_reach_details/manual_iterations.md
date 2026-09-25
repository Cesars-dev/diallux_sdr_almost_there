# Manual Iterations — V7.8_reach_details

> Log of MANUAL (direct-edit) iterations applied to the current production agent, bypassing the normal
> clone→build→deploy flow. Each entry: what, why, where, status. Manually tracked so future rebuilds
> (`tools/build_llm_json.py`) and the next version don't silently lose these.

## Current version
- **CURRENT production (live on Retell):** `V7.7_set_callback_number` → `agent_87e4d5f08475e5bc558b2f390f` / `llm_c5157c4e1795cda2dbdc88fda69b` (gpt-5.2, promoted 2026-08-27).
- **NEXT local build (this folder):** `V7.8_reach_details` — clone of V7.7 + Iter 8 (reach-details mirror) + all prior manual iterations. Built locally 2026-08-29, parity verified, **NOT deployed**.
- `V7.8_appt_confirmed/` exists as an **undeployed** clone (V7.8 plan: `tasks/v7.8_appt_confirmed/plan.md`). Do NOT build/deploy it yet — see STATUS below.

---

## Iteration 1 — Confirm phone number (digit-level) + deterministic `phone_confirmed` gate
- **Why:** First-12 batch showed the phone number reaches Booking with a single (or zero) read-back. A caller who misstates a digit, or says "oh wait that's not my number," can't get a clean overwrite once past `contact_details` — `set_callback_number` is only available there, and `verify_lead_data` writes `callback_number` from raw LLM args (verify.py:134), so a bad value persists into `create_livecall_booking` and Cal rejects (or books wrong-SMS).
- **Where:** `prompts/states/contact_details.md` (number confirm step) + `tools/contact_details.tools.json` + `edges/contact_details.edges.json` + `validator_endpoint/verify.py` + `llm.json`.
- **Design (reworked 2026-08-28, NOT a standalone extract tool):**
  - Added `phone_confirmed` boolean as a required edge gate (`edges/contact_details.edges.json`), registered in `llm.json` `default_dynamic_variables`.
  - **Best-number path (caller says inbound # is best):** `extract_reach_details` (native) sets `is_calling_best_number=true` AND `phone_confirmed=true` together — no extra confirm question. This is the common real-number case.
  - **Alternate path (caller gives new #):** `extract_reach_details` sets `is_calling_best_number=false`, `phone_confirmed` stays flat; caller gives alternate → `set_callback_number` (code tool) records it → server returns `phone_confirmed:true` on ok (verified in `verify.py` + tests). On `wrong_number` it omits both keys → no write.
  - Edge won't fire until one of those two paths confirms → blocks transition on any falsy `phone_confirmed`. Safe failure (stuck call, never a wrong booking).
- **Notes:** the first approach (separate `extract_phone_confirmed` native tool forcing a manual confirm every call) was REVERTED — wrong for the common real-number case. `set_callback_number` server change needs a VPS validator-service restart at deploy.
- **Status:** DONE — surgical patch landed 2026-08-28. Rebuilt + parity verified; server test PASS; awaiting local deploy + acceptance re-run.

## Iteration 2 — Vary filler phrases, never verbatim
- **Why:** Batch humanization failed R2/R4. The closed acknowledgment list in `general_prompt.md:8` ("Got it / Makes sense / I hear you") makes the model open ~50% of turns with "Got it" (Pedro 17/32, Gene 8/15, Daniel 10/20, Brenda 11/24). Verbatim `< >`/KB sample lines leak across calls ("One moment while I confirm that.", the "Really glad you called…" close, "5 to 10 extra booked jobs").
- **Where:** `prompts/general_prompt.md` (acknowledgment rule → prohibit canned openers / respond to content) + `prompts/states/Booking.md`, `Closing.md` (turn verbatim lines into descriptions to vary).
- **Status:** DONE — surgical patch landed 2026-08-28 (additive sample/vary notes in general_prompt.md, Booking.md, Closing.md).

## Iteration 3 — Strip markdown `**` + code jargon from KBs
- **Why:** Markdown `**` leaks into spoken output as literal asterisks (`**$6,500/week**`) on leak-math calls (Susan 9, Sofia 10, Pedro 7, Brenda 5). Source is BOTH the main prompt (general_prompt.md: 6 `**`; e.g. "**Stop losing revenue**", "**NEVER**") AND heavily the KBs, which bold the exact stats the agent speaks aloud:
  - `Knowledge bases/industry-kb.md` — **287** occurrences
  - `Knowledge bases/pain-points-kb.md` — **37**
  - `Knowledge bases/sales-psychology-kb.md` — **35**
  - `Knowledge bases/voice-ai-capabilities-kb.md` — **15**
  - Main prompt is NOT enforced against it (only forbids JSON/function names/variables/`{}`/`[]`, not `**`).
- **Where:** strip `**` from all KBs + `prompts/**`; remove any spoken code jargon / bracket syntax.
- **Status:** DONE — surgical patch landed 2026-08-28 (all `**` stripped from KBs + prompts; zero residual).

---

## Iteration 5 — Fix phantom-close: ConfirmSlots → VerifyLead transition wording + "never announce a booking before it's real"
- **Why:** Sam (GK stress idx 0, expected book) ended up NO-BOOK because the agent **narrated** "I've got you down for today at 6:15 PM Central… bye" and fired `end_call` WITHOUT ever calling `verify_lead_data` or `create_livecall_booking`. Pure hallucinated close (bad prompting), NOT a server issue — his `query_livecall_slots` succeeded and `validate_lead` returned `slot_verified:true`. Root causes:
  1. `ConfirmSlots.md` step 4 literally says *"`slot_verified: true` → `transition_to_Booking`"* — but the real edge is **ConfirmSlots → VerifyLead** (a data checkpoint, not a booking). Telling the model "→ Booking" primes it to think the appointment is already locked the instant `slot_verified:true` returns.
  2. `slot_verified:true` read as "done" instead of "data OK, keep going through VerifyLead → Booking".
  3. `VerifyLead.md` already forbids announcing a booking, but the model ignored it on a smooth, cooperative caller.
- **Where:** `prompts/states/ConfirmSlots.md` (change the "→ transition_to_Booking" wording to reflect the true VerifyLead checkpoint destination) + add a hard rule (in VerifyLead and/or ConfirmSlots): **NEVER say "booked / set / got you down" until `create_livecall_booking` actually returns success; and `transition_to_VerifyLead` must be followed by `verify_lead_data`, never by `end_call` / a goodbye announcing a booking.**
- **Scope:** prompt-only. Distinct from the V7.8 `appt_confirmed` gate (that fixes Nick/Wendy non-yes forcing; this fixes Sam's yes-but-dropped-at-the-gate). V7.8 does NOT fix this — it doesn't touch VerifyLead/Booking prompts.
- **Status:** DONE — surgical patch landed 2026-08-28 (ConfirmSlots `transition_to_Booking`→`transition_to_VerifyLead` + new CRITICAL CONSTRAINT; contact_details `transition_to_Booking`→`transition_to_ConfirmSlots`).

## Iteration 6 — (DEFERRED to tomorrow) Harden the Cal slots endpoint against concurrent-load timeouts
- **Why:** During the 11-worker async stress run the endpoint started returning ECONNABORTED "timeout of 15000ms exceeded" to `query_livecall_slots` once ≥4 agents hit it concurrently (DAVE ×4, NICK ×2; early calls succeeded, later ones timed out). This **was the root cause of DAVE's no-book** (slot timeout → agent guessed a slot → `validate_lead` still passed slot_verified:true because it only checks data presence → `verify_lead_data` looped on `selected_time: unfixable_format` → max turns, no booking). SAM and NICK were NOT caused by this (separate prompt bugs).
- **Architecture to review tomorrow** (`cal_slots_endpoint/main.py`): sync `def check_availability` runs in FastAPI's threadpool; each call does a **blocking** `requests.get` to Cal.com with `timeout=REQUEST_TIMEOUT` (10s) + up to 2 retries (`fetch_cal_slots`) → can exceed Retell's 15s tool timeout under queueing. Metrics showed `slot_queries:300`, `sig_rejected:13`, `unknown_account:10` (some 401s may be Retell not sending `X-Retell-Signature` — verify). No per-client/Cal rate limit, no connection pool, no caching of the 7-day slot window.
- **Candidate fixes (decide tomorrow):** cache `GET /v2/slots` window (short TTL) to cut Cal.com round-trips; bound/queue concurrent Cal.com calls; raise `REQUEST_TIMEOUT`/make `fetch_cal_slots` retry only on 5xx not timeout; reuse an HTTP session/connection pool; verify the `sig_rejected` (401) path isn't dropping legit Retell slot calls.
- **Status:** TO-DO for prod — not in this batch. Revisit when concurrent load is real.

---

## Iteration 4 — (OPTIONAL / low priority) Cal slot reservation — 2-caller collision freeze
- **Why:** Two callers racing for the same slot can 409. Root of the Sofia 409 loop was actually calendar contention (leftover test bookings), NOT the phone — the 400 was the phone; the 409s were taken slots with a VALID number. At current volume (~10 calls/day) collisions are very unlikely; this is a guard, not a fix for a real problem.
- **Capability (verified, Cal.com v2):** `POST /v2/slots/reservations` (cal-api-version `2024-09-04`), body `{eventTypeId: 3801235, slotStart: "<ISO>", reservationDuration: 300}` — key is `slotStart` (NOT slotStartTime). Returns `reservationUid`; release via `DELETE /v2/slots/reservations/{uid}`. Auto-releases after `reservationDuration` (300s) — self-healing if DELETE is skipped. A reserved slot is hidden from subsequent `GET /v2/slots` availability → a concurrent caller won't see it. Ref: `docs/api/CAL_COM_API_NOTES.md:176`.
- **Design (if ever built):** confirm slot → `reserve_livecall_slot` webhook (HMAC, like the others) → `create_livecall_booking` → DELETE/release. This prevents the "guessed next slot" recovery path from ever firing.
- **Status:** TO-DO for prod — nice-to-have, not in this batch. Revisit only if slot collisions appear.

---

## NOTE — Testing-suite: purge fake 555 numbers from personas (no agent code change)
- **Why:** Some personas hand the agent junk/fake `555` numbers (`+15555551234`, `+15551234567`, and the seeded `+13125551234`-style dynvars are fine, but several BRK personas feed raw 555/`212-555-1234` values). These produce Cal `400 invalid_number` rejects that are **not a production scenario** — a real caller never fakes a number. All they do is pollute the signal and burn calls on a branch that can't happen live.
- **Policy:**
  1. If a persona's *agenda* is to test something OTHER than the fake number (e.g. pressure, objection-handling, waffle), then **upsert at least the phone value** — give it a real, Cal-acceptable number so the test targets its actual intent instead of dying on a fake-phone reject.
  2. If a persona exists *only* to feed a fake number (its whole point is junk phone), then it's useless — **delete it and write a proper persona** instead.
  - No persona should exist purely to throw fake numbers at the agent; that's noise, not a test.
- **Where:** `testing/test_llm_to_llm.py` PERSONAS + `runners/adversarial_suite.py` personas (e.g. Nick `212-555-1234`, Sofia correction, BRK 555s). Keep the dynvar-seeded real numbers (`+15123120001` etc.); replace only the fake-555 inputs.
- **Status:** DONE — surgical patch landed 2026-08-28 (all fake 555 numbers replaced with real non-555 values in test_llm_to_llm.py + adversarial_suite.py + mirror).

---

## Iteration 8 — reach-details mirror: `phone_confirmed` fully py-owned (surgeon phase `reach-details-mirror`)
- **Why:** Iter 1's hybrid left `phone_confirmed` LLM-writable via native `extract_reach_details` (LLM roulette on a gate flag, split-brain with `set_callback_number`), and no py path could write `false` when the caller says "no, call me elsewhere". Rework per owner design: both booleans py-written by ONE deterministic endpoint; prompt carries only tool+args (no server narrative); tolerant arg parsing (LLM sends `true`/`"Yes"`/`1`/`"yes this is fine"`/`"another number"` → coerced).
- **Where:** `validator_endpoint/verify.py` (`_coerce_bool` + `record_reach_details`), `main.py` (`/record-reach-details` route), `test_validate.py` (+11 tests), `tools/contact_details.tools.json` (native `extract_reach_details` DELETED, custom `record_reach_details` added), `prompts/states/contact_details.md` (§4 YES/NO branch rewritten to original-design style: ask → read back digit-grouped dashes → clear-confirmation rule → `set_callback_number`; reference line: call `record_reach_details` ONCE — re-call clobbers recorded state).
- **Semantics:** yes → py writes `is_calling_best_number=true, phone_confirmed=true`; no → both false (gate closed); only `set_callback_number` ok reopens. Junk/mangled → `invalid_answer`, NO dv keys, no write (fail-closed, LLM re-asks).
- **Plan:** `tasks/surgeon/reach-details-mirror/` (01-03 archived, 04_master_plan current). Executed 2026-08-29 per 04: unit ALL PASS (12 new), signed smoke ALL PASS (10 payload shapes), airtight battery ALL PASS (signature tamper/forge/missing → 401, invalid json → 400, unwrap shapes, branch-b full chain incl. re-call-after-confirm), service restarted + active.
- **Status:** DONE — built `llm.json` (9 states, parity verified, only pre-existing Closer-hot warning). NOT deployed to Retell. Deploy needs: validator restart already live (additive route) → deploy_v68.py → acceptance re-run.

---

## STATUS
- Iterations 1, 2, 3, 5, 8 and NOTE 7 are DONE (6 of 8 — surgical patches landed 2026-08-28/29). Iter 8 (`V7.8_reach_details`) rebuilt locally, parity verified, NOT deployed to Retell.
- Iter 6 (endpoint hardening) and Iter 4 (slot reservation) are TO-DO for prod — not in this batch.
- Iter 8 supersedes Iter 1's hybrid: `phone_confirmed` + `is_calling_best_number` are py-written only (`record_reach_details` mirror + `set_callback_number` ok path). Native `extract_reach_details` deleted.
- V7.8_appt_confirmed (explicit-confirm boolean + edge gate) is parked. Note: Iter 8 added `phone_confirmed` (boolean + edge gate) — align V7.8's `appt_confirmed` with it when resumed.
- After these land: rebuild (`tools/build_llm_json.py`) → deploy → re-run acceptance ladder → update `STATE.md`/`AGENTS.md` lineage.