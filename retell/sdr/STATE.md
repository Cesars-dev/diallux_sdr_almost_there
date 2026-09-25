# Dialux_SDR — STATE.md

> **UPDATED 2026-08-27 — V7.7_set_callback_number is PROMOTED to production** (`agent_87e4d5f08475e5bc558b2f390f` /
> `llm_c5157c4e1795cda2dbdc88fda69b`), replacing V7.6_verify_state. Fixes the `callback_number`
> pollution bug via a deterministic `set_callback_number` webhook (clobber vector removed at the source).
> **Open:** full ladder (12+11, V7.7) + latency test, then retire `agent_edf1437704e976c53539c7effe`.
> Build blueprint: [`SKILL.md`](SKILL.md) · Folder map + version index: [`README.md`](README.md).
> Production voice agent `agent_4b577c7e169b069deae991b11d` remains READ-ONLY.

---

## CURRENT BUILD — V7.7_set_callback_number (2026-08-27)

| Item | Value |
|---|---|
| Chat agent | `agent_87e4d5f08475e5bc558b2f390f` |
| LLM | `llm_c5157c4e1795cda2dbdc88fda69b` (v0) — **gpt-5.2**, temp 0.1, `model_high_priority: false` |
| Source of truth | `Dialux_SDR/V7.7_set_callback_number/` (built + parity verified, 9 states) |
| Status | **LIVE, happy-path smoke 1/1 (Maria) + signed endpoint smoke 5/5 + unit 78/78.** Full ladder pending. |

### Architecture delta vs V7.6_verify_state (the whole point of V7.7)

**`extract_reach_details` no longer declares `callback_number`** — it sets `is_calling_best_number`
only. The alternate-number write now goes through a deterministic `set_callback_number` webhook:

1. `set_callback_number` [custom webhook → :8003 `/validator-function/set-callback-number`]
   - IN (args): `callback_number` (spoken digits, LLM never formats)
   - Python/pydantic: `normalize_phone` → E.164 `+1[2-9]\d{9}`; None/junk-tolerant input
   - OUT payloads (literal contract in tool description):
     - `{"status":"ok","callback_number":"+1XXXXXXXXXX"}` → **writes** callback_number via
       `response_variables` (only writer of callback_number besides the inbound seed)
     - `{"status":"wrong_number","action":"review_and_recapture","instruction":"..."}` →
       **NO callback_number key → no write** (self-healing meta-directive, NOT a `Say:` line — never spoken)
     - `{"status":"error",...}` → Telegram page to owner
2. `is_calling_best_number=true` path: the **seeded** inbound `callback_number` STANDS (never re-asked/re-written).
   `is_calling_best_number=false` path: caller gives an alternate → `set_callback_number` captures it.
3. Prompt `contact_details.md` §4 (phone) edited: YES → seeded number stands; NO → call `set_callback_number`
   + follow its `action`. Extraction reference re-wired to the 4 tools.
4. `tool_call_strict_mode`, top-level LLM settings, KB set, voice agent, deploy recipe — unchanged from V7.6.

### Architecture delta vs V7.5_lean (the whole point of V7.6)

**New state `VerifyLead` inserted between ConfirmSlots and Booking** — a DATA VALIDATION
CHECKPOINT (explicitly NOT a booking step; owner-iterated prompt v6 in
`prompts/states/VerifyLead.md`, locked rationale in `tasks/surgeon/v76-verify-state/`):

1. `verify_lead_data` [custom webhook → :8003 `/validator-function/verify-lead-data`]
   - IN (args the LLM passes from context): first_name, last_name, company_name,
     callback_number, prospect_timezone, selected_time
   - Python/pydantic: E.164 normalize (`normalize_phone`), tz resolve, name clean,
     time coercion; **None/junk-tolerant input, strict output**
   - OUT payloads (literal contract in tool description):
     - `{"status":"ok","data_verified":true,...}` + normalized injections via
       **response_variables**: data_verified, callback_number, first_name, last_name
     - `{"status":"incomplete","data_verified":false,"problems":[...],"actions":["Say: '...'"]}`
       — literal ask-strings written in Python (POLITE_ASKS/APOLOGETIC_VERIFIES style),
       LLM speaks verbatim; **CONTEXT FIRST, ASK SECOND** repair order
     - `{"status":"error",...}` → Telegram page to owner (real human callback loop —
       owner-approved doctrine exception valid ONLY in VerifyLead/Booking)
2. EDGE ConfirmSlots → VerifyLead: requires slot_verified==true, selected_time, prospect_timezone
3. EDGE VerifyLead → Booking (**THE GATE**): requires **data_verified==true** +
   selected_time + prospect_timezone — pollution physically cannot pass

**Booking state slimmed + determinized:**
- `validate_booking` [JS code] **DELETED** (its false-alarm on polluted "" drove the rebook cascade)
- `record_booking_uid`: extract_dynamic_variable **REPLACED by webhook** `/record-booking-uid`
  - pydantic `^[A-Za-z0-9]{22}$` (Cal v2 UIDs are uniformly 22-char alnum — verified across all logs)
  - THEN Cal GET verification: only `status:"accepted"` books write dv — hallucinated uids
    (`uid_not_found`) and cancelled ghosts (`uid_not_accepted:cancelled`) rejected, NO WRITE EVER
  - prompt: retry ≤3 on rejection, then calendar-trouble close
- `record_booking_outcome` unchanged; `create_livecall_booking` unchanged
- `extract_confirm_details`: corrective `callback_number` variable **DELETED** (landmine #1)

**Why (forensics, chat evidence archived):**
- *Sam triple-book*: `extract_confirm_details` wrote `""` over good `callback_number` →
  `validate_booking` false-alarm → model re-created (2nd booking) → second empty
  `record_booking_uid` clobbered good UID → cascade → **dv said booking_failed=true while 3 real
  bookings existed** (polarity inversion). Root: extract tools overwrite dv on EVERY call, even empty.
- *Maria false-close (V7.6 early)*: model skipped verify entirely and verbally claimed booked.
  Trigger: user-pressure language ("please book it" ×3) + old framing "everything collected… move on".
  Fixed by checkpoint-framing prompt v6 ("This is a DATA VALIDATION CHECKPOINT - not a booking step…
  KEEP CALLING until status ok"). 5/5 clean since.

### Prompt contracts (verbatim sources)
- `prompts/states/VerifyLead.md` — deployed v6 (checkpoint framing, Hard Constraints block,
  filler-line-WHILE-executing, context-first/ask-second, literal `"status"` payloads, keep-calling-until-ok)
- Tool descriptions carry the literal JSON payload contracts — do not paraphrase them
- Main general_prompt unchanged from V7.5_lean (owner sections + single CRITICAL CONSTRAINTS block)

### Context budget (o200k, main+state): VerifyLead 1549 · Booking 1619 · Closing 1399 ·
Offer 1855 · Intake 1826 · Discovery 2113 · contact_details 2014 · ConfirmSlots 1823 · Closer 2423 (warn)

---

## TODAY'S DEAD ITERATIONS (same folder, never patch — kept for lineage)

| Agent | Why dead |
|---|---|
| `agent_1b9e7dcac061b5b6d21823537a` | tool defs in wrong schema shape (`required_parameters` instead of `parameters.properties`) → model called with `{}` |
| `agent_152c677a6af8e0537dc83a57e9` | STALE BUILD SHIPPED — ran `build --check` (no write) then deployed |
| `agent_ea8e470787eba5c59b60e9fc8e` | same stale-payload mistake again |
| `agent_2f73c792df90184d9146860284` | correct payload; exposed Maria false-close (pre-prompt-fix) |
| `agent_bbe630119fcd34db454a13d604` | guard line added; skip still 1/3 → prompted v6 |

## PROCESS GOTCHAS (paid for today — do not repeat)

1. **`build_llm_json.py --check` does NOT write llm.json.** Always run FULL build before
   `deploy_v68.py`. Stale-payload deploys happened twice.
2. **Background env race**: `export X && jobA & jobB & wait` — only jobA inherits exports;
   jobB ran the harness DEFAULT agent (= stale V6.5 `agent_514a7af07acf4a407c76f486ce`).
   Put exports INSIDE each background command, or run sequentially.
3. **Custom tools need `parameters:{type:"object",properties:{…}}`** (house format).
   `required_parameters`+`value` templates are not read → `{}` args.
4. Shell cwd resets to `/home/julio` between commands — absolute paths or `workdir`.
5. Extract tools clobber dv with "" on repeat calls — that's WHY recorders are webhooks now.

## Self-hosted services (all on this VPS, Caddy `slots.diallux-ai.site`)

| Service | Port | Routes | Notes |
|---|---|---|---|
| time_endpoint | 8002 | `/time-function/*` | unchanged |
| cal_slots_endpoint | 8001 | `/check_availability` | unchanged, notify.py Telegram pattern |
| validator_endpoint | 8003 | `/validator-function/*` | **+3 new endpoints**: `/verify-lead-data`, `/record-booking-uid`, `/set-callback-number`; module `verify.py`; `_tg_notify()` helper; `CAL_COM_API_KEY` env used for UID verification |

- Fixtures: `test_validate.py` = **78/78 PASS** (incl. None-tolerance, 555-passes-format,
  21/23/24-char uid rejects, nested-args unwrap, 9 `set_callback_number` cases)
- Live-proven: `/set-callback-number` signed smoke 5/5 — valid → E.164 ok/write; bad → wrong_number/no-write
- Live-proven: real Cal booking → recorder ok; tampered → invalid_uid; fabricated ZZZ×22 →
  `uid_not_found`; cancelled ghost → `uid_not_accepted:cancelled`
- Caddy routes runtime-injected (admin API 127.0.0.1:2019) — re-inject if Caddy restarts.
  New subpaths needed NO route change.

## Lineage verdict (complete)

V7.0 prod-ref `agent_66df480ff8f240ee9e919d3b53` · V7.1 rejected `agent_ac47e5b9da4b407a02a52f3c62` ·
V7.2_production baseline `agent_c3bed9963cf528c85f58d1d521` · V7.3_craft_kb `agent_f724da044b38ca7e11098933ec` ·
V7.4_hard_gpt52 `agent_a9a7205fa6085e1b0c0246ae60` · V7.5_lean prev-prod `agent_edf1437704e976c53539c7effe`
(+ its 12+11 ladder receipts) · V7.6_verify_state `agent_bc0665fd64d4f94573d0520cf7` (prev-prod, 2026-08-26)
· **V7.7_set_callback_number `agent_87e4d5f08475e5bc558b2f390f` (CURRENT)**.
All old builds: `_archive/versions/`. Analysis SOPs: `docs/Testing_guidelines/`.
Runners: `testing/runners/{reg_one,adv_one}.py`; ALL transcripts `testing/json_logs/`.

## Accepted trade-offs (unchanged)
- Empty-arg `extract_*` ceremony calls = platform behavior (non-bug; cleanup idea shelved)
- gpt-5.2 ≈2× inference cost (discipline)
- Breakers may hit turn caps while qualifying politely
- 555-prefix numbers pass validator format-check — Cal.com is the judge there (owner decision:
  no hard guardrails where the calendar already rejects)

## NEXT ACTIONS (in order)

1. **Full acceptance ladder vs `agent_87e4d5f08475e5bc558b2f390f`**: first-12 regular async
   (`runners/reg_one.py 0..11`) → expect 8 designed-bookings landed (Sofia/Pedro may fail-closed
   on fictional numbers = environmental), zero bypasses, zero false greens → then 11 stress
   (`runners/adv_one.py`, idx set 0 1 2 3 4 6 7 8 9 10 11) → expect GKs 5/5 machinery,
   breakers contained, Jamie note: may run funnel on junk data but Cal rejects (accepted).
   Cancel ALL test bookings after.
2. If ladder holds → confirm promotion docs (already staged). Retire `agent_edf1437704e976c53539c7effe`
   + confirm `agent_bc0665fd64d4f94573d0520cf7` (V7.6) demoted to lineage.
3. **Latency test** (still open since V7.5): per-state round-trip timing; bar: tool turns
   ≤~2s filler-guarded; Intake/Discovery instant.
4. Backlog: duplicate-create retry quirk (now structurally mitigated by recorder — verify on
   ladder), Jamie early-refusal nicety.

## Deploy recipe (exact)
```bash
cd /home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/V7.7_set_callback_number
python3 tools/build_llm_json.py          # FULL build — --check does NOT write!
python3 deploy_v68.py                    # new llm+agent; KB registry reuse/upsert
# snapshot ids into DEPLOYED_llm_snapshot.json + PRODUCTION.md
# test: RETELL_API_KEY=$(grep ^RETELL_API_KEY= ../../..../.env | cut -d= -f2) \
#       CHAT_AGENT_ID=<new id> python3 ../testing/runners/reg_one.py 0
```

## Legacy history
6.x era: `_archive/versions/` + `_archive/agent_v6/` (V6.0-era 4-state, callback path, Booking
4,453 tok). 6.1 first-deploy failures root-caused into the edge-schema + validator-gate design.
KB policy (~$250 duplicates lesson): `AGENTS.md` ⛔ KB POLICY — registry reuse/upsert enforced
by deploy scripts; never hand-create KBs.
