# Dialux SDR — Project Documentation

> **PRODUCTION: `V7.7_set_callback_number/` — `agent_87e4d5f08475e5bc558b2f390f` / `llm_c5157c4e1795cda2dbdc88fda69b`**
> Current build per owner promotion 2026-08-27 (9-state; deterministic `/verify-lead-data` + `/record-booking-uid`
> + `/set-callback-number` webhooks; fixes the `callback_number` pollution clobber). Prior production:
> `V7.6_verify_state/` (`agent_bc0665fd64d4f94573d0520cf7`).
> Build blueprint: [`SKILL.md`](SKILL.md). Live status: [`STATE.md`](STATE.md). Everything else is archived.

---

## Folder map (organized 2026-08-25)

```
Dialux_SDR/
├── V7.7_set_callback_number/  ← THE BUILD (production source of truth)
│   ├── prompts/          general_prompt.md + states/*.md (editable sources)
│   ├── JSON/edges/       state machine definition
│   ├── tools/            build_llm_json.py (parity check) + deploy_v68.py
│   ├── Knowledge bases/  8 KBs (registry-managed)
│   ├── DEPLOYED_llm_snapshot.json + PRODUCTION.md
│   └── analysis/         this build's SOP reports
├── testing/              ← canonical test toolkit (moved from legacy V6.8/tools)
│   ├── test_llm_to_llm.py    LLM-to-LLM harness (PERSONAS 0–12; LOG_DIR = ./json_logs)
│   ├── json_logs/            ALL raw chat transcripts (JSON) — every run since V6.8
│   ├── *.tools.json / general_tools.json   tool schema sources
│   ├── runners/          reg_one.py (first-12 batch) · adv_one.py (11 stress) · analyze_v690.py
│   └── __pycache__/
├── SKILL.md              ← reverse-engineered architecture: how to build an SDR agent
├── STATE.md              ← current state, lineage verdict, next steps
├── SOURCES.md, config/, Knowledge bases/, tasks/
├── booking_cancellation_record.json
└── _archive/
    ├── versions/         ALL old builds (see index below) — archaeology only
    ├── 6.1 iterations/, legacy-dialux/, old-webhooks-runtime/, retellai-mcp-server/
    └── kb-dump backups etc.
```

Run tests today:
```bash
export $(grep ^RETELL_API_KEY= .env | head -1)
export CHAT_AGENT_ID=agent_87e4d5f08475e5bc558b2f390f
python3 Dialux_SDR/testing/runners/reg_one.py 0        # single persona
for i in $(seq 0 11); do python3 Dialux_SDR/testing/runners/reg_one.py $i > /tmp/r_$i.log 2>&1 & done; wait
```

---

## Self-hosted code functions (our server, NOT Retell-hosted)

All custom tools are FastAPI/webhook services on MainVps (user `julio`, systemd user units),
exposed through Caddy at `https://slots.diallux-ai.site`:

| Service | Port | Route | Used by |
|---|---|---|---|
| time_endpoint (`/today`) | 8002 | `/time-function/*` | ConfirmSlots date anchoring |
| cal_slots_endpoint (slot webhook) | — | via Caddy | `query_livecall_slots` |
| validator_endpoint (`/validate_lead`, `/verify-lead-data`, `/record-booking-uid`, `/set-callback-number`) | 8003 | `/validator-function/*` | **the gate** — `/validate_lead` writes `slot_verified`; `/verify-lead-data` writes `data_verified`; `/record-booking-uid` records only Cal-accepted 22-char UIDs; `/set-callback-number` deterministically writes `callback_number` |

Notes: Caddy routes were injected at runtime via admin API (`127.0.0.1:2019`) — re-inject if Caddy
restarts (root-owned Caddyfile). Validator unwraps Retell's nested `{args:{...}}` payload
(`args_at_root=false`). HMAC multi-key auth copied from time_endpoint.

## Booking chain & fallback

```
create_livecall_booking -> record_booking_uid (custom webhook, Cal-accepted 22-char UID only) -> record_booking_outcome -> end_call
```
Fallback doctrine: a failed calendar tool gets ONE honest line ("my calendar is having trouble
right now") + offer another slot. No callbacks, no emails, no SMS promises — there is no callback
team. UID validation (`record_booking_uid` webhook — pydantic `^[A-Za-z0-9]{22}$` + Cal GET
`status=="accepted"`) is mandatory after every create; outcome is recorded before wrap-up.

---

## Version index (all archived under `_archive/versions/`)

| Folder | Agent id | Verdict | Analysis reports inside folder |
|---|---|---|---|
| V6.6 … V6.90 | various | superseded iteration ladder | `analysis/dump_*.txt`, V6.88: `CALL_SOP_REPORT.md`+`SALES_ANALYSIS.md` |
| working_agent | `agent_514a7af07acf4a407c76f486ce` (V6.5) | retired reference | — |
| V7 | `agent_66df480ff8f240ee9e919d3b53` | previous production ref | `analysis/{CALL,HUMANIZED,SALES}-ANALYSIS-V7.md` |
| V7.1 | `agent_ac47e5b9da4b407a02a52f3c62` | rejected (sales rewrite broke funnel) | + `SALES-ANALYSIS-V71-HAPPY.md` |
| V7.2_production | `agent_c3bed9963cf528c85f58d1d521` | validated baseline | same trio |
| V7.3_craft_kb | `agent_f724da044b38ca7e11098933ec` | craft regression under stress | same trio |
| V7.4_hard_gpt52 | `agent_a9a7205fa6085e1b0c0246ae60` | constraints + gpt-5.2 proof | same trio |
| V7.5_lean | `agent_edf1437704e976c53539c7effe` | prior production (8-state, pre-VerifyLead) | same trio |
| V7.6_verify_state | `agent_bc0665fd64d4f94573d0520cf7` | previous production (9-state + deterministic verify/record webhooks) | see `tasks/surgeon/v76-verify-state/` |
| V7.7_set_callback_number | `agent_87e4d5f08475e5bc558b2f390f` | **CURRENT** — `callback_number` pollution fixed via `/set-callback-number` | see `tasks/surgeon/set-callback-number/` |
| V7_personal_iteration{,2,3} | see STATE.md | bisect experiments | same trio |

Raw chat JSONs for EVERY batch live in `testing/json_logs/` (naming: `<NAME>_chat_<id>.json`).
Persona transcript extracts for recent batches: `/tmp/opencode/v73_txt/` (ephemeral).

## Known issues / backlog

1. **Empty-string tool args on Retell** ("the '' bug"): all `extract_*` dynamic-variable tools fire
   with `""` args (~340 observed in V7.4 batches; data actually flows via transition edge args).
   Harmless but wasteful round-trips. Cleanup idea: strip ceremony extracts from early states or
   make them no-op acks explicit — one-variable-per-iteration change, untested.
2. Duplicate `create_livecall_booking` retry — mitigated: `record_booking_uid` webhook only records
   Cal-accepted UIDs, so dv cannot lie even if create fires twice. Full ladder still pending.
3. Caddy route injection is runtime-only.
4. V7.7 pending: full 12+11 acceptance ladder + latency test before retiring V7.5_lean.
