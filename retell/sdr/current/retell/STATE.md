# V7.8_reach_details — STATE.md

> **UPDATED 2026-08-29 — LOCAL BUILD READY, NOT DEPLOYED.** V7.8_reach_details is the next
> iteration on top of V7.7_set_callback_number: `phone_confirmed` + `is_calling_best_number`
> become fully py-owned via the `record_reach_details` mirror (surgeon phase
> `tasks/surgeon/reach-details-mirror/`, 01-03 archived, 04_master_plan current).
> Retell is STILL LIVE on V7.7 (`agent_87e4d5f08475e5bc558b2f390f`) — nothing shipped.

---

## CURRENT BUILD — V7.8_reach_details (local, 2026-08-29)

| Item | Value |
|---|---|
| Chat agent | **not created yet** (deploy pending, owner gates) |
| LLM | **not created yet** (deploy pending) |
| Source of truth | `Dialux_SDR/V7.8_reach_details/` (built + parity verified, 9 states) |
| Status | **LOCAL. Unit ALL PASS (89), signed smoke ALL PASS, airtight battery ALL PASS, validator service restarted + active.** Deploy + ladder pending. |
| Baseline | `V7.7_set_callback_number/` clone — ALL prior manual iterations (1, 2, 3, 5, NOTE 7) carried over |

## Architecture delta vs V7.7 (the whole point of V7.8)

**`phone_confirmed` and `is_calling_best_number` are py-written ONLY.** The native
`extract_reach_details` tool (LLM-writable booleans — the split-brain flaw) is DELETED.
Replaced by one deterministic endpoint + the existing `set_callback_number`:

1. **`record_reach_details`** [custom webhook → :8003 `/validator-function/record-reach-details`]
   - IN (args): `is_calling_best_number` — `boolean` + **`enum: [true, false]`** (schema-locked;
     description: "Send true when the caller confirms… Send false when they give an alternate…
     Send exactly one — no other values.")
   - Python: `_coerce_bool` tolerant coercion (exact word → embedded word → junk), `record_reach_details`
   - OUT payloads (literal contract in tool description):
     - `{"status":"ok","is_calling_best_number":<bool>,"phone_confirmed":<bool>}` →
       **mirror**: yes → true/true; no → false/false (writes both dvs via `response_variables`)
     - `{"status":"invalid_answer","action":"ask_and_retry","instruction":"..."}` → **NO dv keys →
       no write** (fail-closed; instruction tells the model to ask again and re-call with exactly
       true or false — the arg-correcting retry loop)
   - `max_retry: 1` (HTTP-level retry on timeout/5xx — our endpoints always 200, so this fires
     only on infra failure; idempotent, safe)
   - `speak_after_execution: false` (booleans are never spoken)

2. **`set_callback_number`** [existing, unchanged logic] — mixed endpoint (string in, string+bool out):
   - IN: `callback_number` (spoken digits — no enum possible; enforced by py `normalize_phone` → E.164)
   - OUT: ok → `callback_number` E.164 + `phone_confirmed: true` (writes both); wrong_number →
     `review_and_recapture` instruction, no write. `phone_confirmed` is **always py-derived** here.
   - `max_retry: 1` added.

3. **Gate semantics (unchanged edge):** contact_details → ConfirmSlots requires
   `phone_confirmed` truthy. "No, another line" → py writes false → gate CLOSED; only
   `set_callback_number` ok reopens it. Unfilled "" → edge blocked → stuck call, never a wrong booking.

4. **Prompt `contact_details.md` §4** — rewritten to original-design style (tool + args only,
   no server narrative): YES → `record_reach_details` true, seeded number stands; NO →
   `record_reach_details` false → ask → read back digit-grouped with dashes (example
   `<So that's 2-5-6 7-8-9 0-1-2-3, correct?>` — vary grouping) → ONLY a clear confirmation
   (Yes/Correct/Right; mangled/hesitant/correction = re-ask) → `set_callback_number` → proceed.
   Extraction reference: call `record_reach_details` **ONCE** (re-call clobbers recorded state —
   the old deadlock vector, now forbidden in the prompt).

5. **Retry doctrine (corrected):** Retell has NO `tool_call_fail_behavior`. The real levers:
   per-tool `max_retry` (HTTP-level), in-body `instruction` (model-level arg-correcting retry —
   the dominant path), optional Structured Output (LLM-level, not enabled).

## Known accepted warnings (pre-existing, untouched)

- Closer state runs hot (~2458 tokens > 2300 ceiling) — pre-existing, not this iteration.
- Live V7.7 happy-path smoke 1/1 (Maria) + endpoint smokes — V7.8 needs its own.

## Manual iterations carried in this folder

1, 2, 3, 5, NOTE 7 (from V7.7 log) + **Iteration 8 — reach-details mirror** (DONE 2026-08-29).
Iter 6 (endpoint hardening) + Iter 4 (slot reservation): TO-DO for prod.
`V7.8_appt_confirmed/` parked — align its `appt_confirmed` with `phone_confirmed` when resumed.

---

## THE TWO THINGS TO DEPLOY AND TEST

### 1. Deploy to Retell (owner GO required)
```bash
export RETELL_API_KEY=<redacted - in host env>
cd Dialux_SDR/V7.8_reach_details
python3 tools/build_llm_json.py   # already done — parity verified
python3 deploy_v68.py             # creates NEW LLM + chat agent (never patches)
```
- Validator side is ALREADY live on the VPS (additive `/record-reach-details` route, restarted
  + smoke-tested 2026-08-29). No VPS action needed at deploy.
- After deploy: update `DEPLOYED_llm_snapshot.json`, `Dialux_SDR/STATE.md`, `AGENTS.md` lineage.

### 2. Test (acceptance ladder, after deploy)
- **Full 12+11 ladder** via `testing/test_llm_to_llm.py` + `runners/adversarial_suite.py`
  (personas already purged of fake 555 numbers). Key scenarios for THIS iteration:
  - Branch-a: caller says inbound number is best → `record_reach_details(true)` → both true → books.
  - Branch-b: alternate number → `record_reach_details(false)` → ask → read back → clear confirm →
    `set_callback_number` ok → gate opens → books on the alternate number.
  - Mangled confirm ("uh yeah I guess", correction, hesitation) → re-ask, never a wrong write.
  - Gate-block: falsy/missing `phone_confirmed` → edge must NOT fire (stuck contact_details, no booking).
  - `invalid_answer` retry loop: model sends junk once → instruction → re-call with true/false.
- **Cancel all test bookings after every batch** (Cal.com v2 cancel, `cancellationReason` required).
- **Latency test** on the live agent (tool turns ≤ ~2,000 ms; Intake/Discovery instant).
- Analyze per the three SOPs in `docs/Testing_guidelines/`.