# plan_iter73_sop_full_metric_tables — full per-SOP metric tables + session context carry (2026-09-24 voice-lab session evidence)

## Meta
- Date: 2026-09-24
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: new session deliverable — ONE metric table per SOP (CALL / SALES / HUMANIZED, every category as a row) + a summary table, for the micbridge-96746e56d2fa call; then carry forward the voice-lab matrix + the two open engine problems (FIND-35 fake-booking recovery, cold-ack latency) as continuation work. HITL at every task.
- Status: PLAN ONLY (not started — awaits owner GO)
- Owner framing (verbatim intent): "I want to see all metrics of all SOPs on a table each, then a summary on a table" — the iter72 session closed before that full-table deliverable was rendered.

## Compaction Context (T0 resume point)
This session (2026-09-24, ~05:50–07:40 UTC) did the following — a fresh agent must continue from exactly here:

1. **Voice lab state (lane :8024):** Eryn matrix ran earlier (`kdnRe2koJdOK4Ovxn2DI` @ 0.4/1.2 → owner adjusted), then Sarah A&I `Nhs7eitvQWFTQBsf0yiT` (too slow), Vanessa "Beach Girl" `8DzKSPdgEQPaK5vKG0Rs`, then **Hannah "All-American" `ZSNL4hPqCnqoMPaI4jGX`** (added to account via `POST /v1/voices/add/{public_owner_id}/{voice_id}`; speed 1.5 is IMPOSSIBLE — EL API hard-rejects speed >1.2 on turbo_v2_5 with HTTP 400 `invalid_voice_settings`). Current `.env`: `TTS_PROVIDER=elevenlabs`, `ELEVENLABS_MODEL_ID=eleven_turbo_v2_5`, `ELEVENLABS_VOICE_ID=ZSNL4hPqCnqoMPaI4jGX`, `ELEVENLABS_STABILITY=0.7`, `ELEVENLABS_STYLE=1.0`, `ELEVENLABS_SPEED=1.0`. Cartesia prod pin untouched (`CARTESIA_MODEL_ID=sonic-3.6-2026-08-27`, Linda `829ccd10…`, speed 1.12). Rollback = flip `TTS_PROVIDER=cartesia` + restart.
2. **Per-state delivery table discovered (KEY finding):** `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/delivery.py:67-114` per-state EL profiles OVERRIDE the .env base in 8 of 9 states (`elevenlabs_tts.py:174` — "Profile fields win over the .env base"): begin/Intake 0.50/0.30/1.02, Discovery 0.60/0.15/1.0, VerifyLead 0.65/0.10/1.0, contact_details 0.70/0.05/0.95, ConfirmSlots 0.60/0.10/1.0, Booking 0.50/0.25/1.02, Offer 0.45/0.35/1.05. Owner's .env values only apply to unlisted states. Owner was told; flattening the table = staged code swap (LAW 0).
3. **ElevenLabs v3 research (PARKED, saved):** v3 has NO working speed slider (proved: speed 1.0/1.2/1.5 → identical audio duration via ffprobe; API accepts but ignores), expression = inline audio tags (`[speaking quickly]` verified ~10% faster ceiling vs turbo's real 1.2x), no SSML break, stability is the main knob. Drafted `general_prompt.md` `# Voice` swap saved but NOT applied. All in `/home/julio/projects/clean_diallux_SDR/research/11l_v3_prompting/01_v3_prompting_rules.md`.
4. **Git state:** repo on branch `engine/iter73-playback-rate` @ `1a8e04a` (T1 browser playback-rate knob committed: `?rate=` URL param clamped 0.80–1.15, `src.playbackRate.value` + `playhead = at + buf.duration / RATE`, zero comments per owner). **UNCOMMITTED: the scope fix** (RATE moved from inside `startCall` to top-level IIFE scope next to `SAMPLE_RATE` at line ~54 — the first version threw `ReferenceError: RATE is not defined` inside `playChunk` = TOTAL page silence; that was the 06:47 two-dead-calls outage). Merge points on main: MVP `4559a33` (09-16) → ladder `40b3b40` (iter52→64c, 09-22 19:11, the code the Caleb BOOKED call ran on) → EL cutover `84fd1ce` (iter66) → model-defaults `50a453f` (iter65 prewarm/sanitizer, 09-22 23:58). Main tip `078f06d` engine content == `50a453f` engine content byte-for-byte (only plan/docs after). Owner mental model confirmed: "iter52→64c ladder brain + EL adapter mouth + prewarm plumbing."
5. **Live calls today (all main-content lane):** morning ladder call (Caleb, BOOKED Friday 4pm = Cal.com UID `cAKRpgrmoBLTKxsHkb3c31`, created 04:17, event 3801235) → 05:1x Eryn call (Closing reached, NOT analyzed) → 05:48 aborted (5 turns) → **06:47 ×2 DEAD** (my RATE scope bug — page got audio, `playChunk` threw on every frame, total silence; fixed) → **06:54 `96746e56d2fa` FULL CALL ANALYZED** (see below).
6. **Call `micbridge-96746e56d2fa` (06:54:38–07:03:20, Hannah 0.7/1.0/1.0):** 37 turns, ended `end_call`. Langfuse trace `fe687befd6027609c62d11ff15b1ba7b` (53 gens, 37 tools). Latency: e2e p50 1715/p90 3341/max 5368ms; STT-EOT p50 1554 (e2e is caller-pause-dominated; 8 SLOW turns t10,t15,t17,t18,t25,t26,t33,t37 all Deepgram EOT patience); **LLM→TTS p50 175ms** (vs ~111ms morning ladder — EL style 1.0/stability 0.7 costs ~60ms first-byte); gen TTFT p50 ~931/p90 ~1192/max 4648 (1 outlier); cold-acks = 3 cache-0 spoken rounds (t20 contact_details transition, t41+t43 Closing); eager_final_match 100%; barge-in 1; zero drops/4401/poison.
7. **SOP verdicts (persisted, 14 rows, run `mic-20260924-96746e56`):** CALL FAIL (redundancy: contact number asked 4× t25→t34; re-ask after answer t16; flow PARTIAL: slot flip t32 — offered Friday 1PM then unavailable; bugs OBS: double-goodbye t43 after `end_call_blocked`), SALES 12/14 HIRE (D4 1/2), HUMANIZED PARTIAL/polish (R5.3 "You're right" stem ×3). Full transcript: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/06_transcript_96746e56d2fa.txt`; per-turn jsonl: `…/07_turn_reports_96746e56d2fa.jsonl`; report: `…/04_call_report_micbridge_96746e56d2fa.md`; matrix row 5 in `…/01_matrix.md`; SOP rows: `…/05_sop_rows.json`.
8. **FIND-35 (HIGH, open, ledger `findings`):** the booking was FAKE. `create_livecall_booking` 07:02:40 returned `{status:"booked", recovered:true, booking_verified:true, booked_human:"tomorrow, noon", booking_uid:"cAKRpgrmoBLTKxsHkb3c31"}` — but Cal.com truth: **0 upcoming bookings** on the account; UID lookup shows that booking is **Caleb Martin's from 04:17** (attendee Caleb Martin, +12134192928, start 2026-09-25T23:00Z). The endpoint's phone-match recovery path (`find_existing_booking` by phone — owner's test reused the same number) repackaged an EXISTING booking as a fresh one with a time that exists nowhere on Cal.com ("noon tomorrow"). The agent did NOT hallucinate; the endpoint response did. The first report wrongly said BOOKED — owner caught it ("if you have learned this, you would notice we never booked this one"). Agent-level rule going forward: `recovered=true` ⇒ NO-NEW-BOOKING until Cal.com confirms. Correct call verdict: NO-SALE (details captured, no booking created).
9. **Endpoint mechanics:** booking backend = Cal.com v2 (`api.cal.com/v2`), creds in `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/.env` `CAL_ACCOUNTS` (unquoted shell format `{diallux:{cal_api_key:cal_live_…,event_type_id:6522694,…},diallux_live:{cal_api_key:cal_live_…,event_type_id:3801235,timezone:America/Mexico_City,duration:45},dialux_live:{…same…}}` — NOT valid JSON, parse via `re.search(r"cal_live_[A-Za-z0-9]+")`). Event 3801235 = REAL bookings (cancel after tests). `slots.db` in that folder only has `counters`/`rl` tables — bookings live ONLY on Cal.com.
10. **SDK reality check (owner asked "where's my data / gitmess"):** all SOPs + SDKs ARE committed to main (root `scripts/live_sql.py|rag_pull.py|latency_pull.py|sop_mechanicals.py|call_ledger.py`; `engine/scripts/mic_events.py|lf.py|lf_eval.py|speech_replay.py|live_sql.py`). BUT **two diverged copies of live_sql.py on main**: root copy has the micbridge-*.name filter (537e53c — the ONLY copy that imports mic calls; engine copy lacks it, 22 lines differ). And the RATE scope fix in `engine/diallux/static/mic/index.html` is on the lane but UNCOMMITTED. Untracked: `tasks/surgeon/iter68-speech-flow/`, `tasks/surgeon/iter70-speech-fixes/`; modified docs: `GIT_TREE.md`, `docs/Testing_guidelines/MIC-CALL-ANALYSIS-SOP.md`.
11. **SDK operational notes (data-plane truths learned):** mic traces need the ROOT `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (engine copy fails `no traces in window`); `mic_events.py` defaults to stale `/tmp/opencode/voice_server_8022.log` — for lane :8024 the journal IS the log (`journalctl --user -u diallux-8024.service`); transcript pull = plain REST `GET {LANGFUSE_HOST}/api/public/observations?traceId=<full-id>&limit=200` (pagination `/api/public/traces/{tid}` shape failed; observations endpoint needs the FULL trace id from `GET /api/public/traces?name=micbridge-<sid>` — the short 12-char display id 400s); gen input = message LIST, output = `{"text":…,"tool_calls":[]}`; `sop-import` verdicts accept ONLY PASS/PARTIAL/FAIL/OBSERVATION (POLISH → PARTIAL before import); `live_sql.py import --window "HH:MM-HH:MM"` (no date prefix in window — ValueError otherwise).
12. **PENDING:** owner wanted per-SOP metric tables rendered IN CHAT (one table per SOP, then a summary table) — deferred to this new session (T1). iter71 T2 ack-latency fix + iter70 branch `engine/iter70-speech-fixes` @ `dc62fb9` remain unmerged/parked. iter68-lite STT watchdog `95f7ace` is the parked cure for adopted-socket silence (the 06:47 dead calls looked like it until the scope bug was proven; still worth porting — owner-gated).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Lane :8024 = the test surface; deploys = branch checkout + `systemctl --user restart diallux-8024.service` | Proven all session |
| Cartesia `sonic-3.6-2026-08-27` stays PRODUCTION; EL = test lane only | VOICE LAW |
| `ELEVENLABS_SPEED` stays 1.0 while testing the browser playback knob | Owner: "leave the speed at 1.0, do it browser side" |
| Playback-rate = browser-side `src.playbackRate` (NOT ffmpeg — measured +150–250ms buffer cost kills first-byte) | Owner ordered the playback trick |
| `?rate=` URL param, clamp 0.80–1.15, no restart needed between calls | Owner wants to flip speed live per call |
| v3 tag project PARKED (rules saved in `/home/julio/projects/clean_diallux_SDR/research/11l_v3_prompting/01_v3_prompting_rules.md`) | Owner: "let's put aside that project" |
| `recovered=true` in booking output ⇒ report NO-SALE, never BOOKED | FIND-35: recovery returns another call's booking |
| Agent-level BOOKED verdicts require Cal.com store confirmation | Owner: "I don't want you to review this on a hunch" |
| Verdict basis = AGENT latency only (TTFT/cache/LLM→TTS); caller STT wait shown separately | Mixing made tables "make no sense" (owner) |
| Code changes carry NO comments | Owner: "I don't want this to carry any comments" |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner ear verdict on Hannah 0.7/1.0/1.0 + which `?rate=` value | owner's ear (last call was before the rate knob was usable — audio was broken) |
| Whether to port iter68-lite STT watchdog (`engine/iter68-speech-lite` @ `95f7ace`) to kill adopted-socket dead-air permanently | owner GO |
| Whether the phone-match recovery in book-livecall gets a distinct status (`existing_booking`) | owner GO → new endpoint branch (NOT this fork's lane code — endpoint lives in `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/`, LIVE infra, handle with care) |
| Flatten per-state delivery table to .env recipe? | owner say-so (code swap on the lane branch) |
| Keep or revert playback-rate knob after ear test | owner |

## Environment & Dependencies
- Lane: systemd `diallux-8024.service`, port :8024, WorkingDirectory `/home/julio/projects/clean_diallux_SDR/engine`, logs `journalctl --user -u diallux-8024.service`
- Branch: `engine/iter73-playback-rate` @ `1a8e04a` (+1 uncommitted fix in `engine/diallux/static/mic/index.html` — COMMIT IT FIRST, T1)
- Mic URL: `https://flores.diallux-ai.site/voice24/mic?k=$VOICE_TEST_TOKEN` (+ `&rate=1.1` for the knob; no param = 1.0)
- `.env` knobs: `TTS_PROVIDER` (cartesia|elevenlabs) · `ELEVENLABS_*` · `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` NEVER TOUCH · `VOICE_TEST_TOKEN` NEVER TOUCH
- Langfuse REST (no SDK needed): `GET {LANGFUSE_HOST}/api/public/traces?name=micbridge-<sid>` → full id; `GET …/api/public/observations?traceId=<id>&limit=200`; auth Basic(`LANGFUSE_PUBLIC_KEY`:`LANGFUSE_SECRET_KEY`) from `/home/julio/projects/clean_diallux_SDR/engine/.env`
- Ledger import (mic): `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (root copy — has micbridge filter; stdlib python3) `--db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db import --window "HH:MM-HH:MM" --run <name> --commit <sha>`
- SOP rows: same SDK `sop-import --run <name> --sop ALL --file <rows.json>`; verdicts PASS/PARTIAL/FAIL/OBSERVATION only
- Cal.com check: creds from `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/.env` `CAL_ACCOUNTS` (regex-extract `cal_live_…`; account `diallux_live`, event 3801235); `GET https://api.cal.com/v2/bookings?pageSize=30&status=upcoming` + `GET https://api.cal.com/v2/bookings/<uid>` with headers `Authorization: <cal_live_key>`, `cal-api-version: 2024-08-13`
- Evidence dir: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/` (01_matrix.md, 04_call_report…, 05_sop_rows.json, 06_transcript…, 07_turn_reports…)

## Architecture (one block)
```
Owner mic (browser) → :8024 (ladder brain + EL adapter + prewarm)
    ├─ .env voice: Hannah 0.7/1.0/1.0 + per-state delivery override (delivery.py)
    ├─ browser playback ?rate= (index.html knob)
    ├─ booking → slots.diallux-ai.site/book-livecall → Cal.com v2 (event 3801235)
    ├─ measurement: journal round-usage + turn reports + Langfuse trace
    ├─ audit: 3 SOPs → ledger sops rows + findings
    └── THIS SESSION: render per-SOP metric tables + summary table from the ledger
```

## File Map
| File (absolute path) | What changes | New/Edit |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/static/mic/index.html` | T1: commit the RATE scope fix (working tree already has it) | Commit on branch |
| `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` vs `/home/julio/projects/clean_diallux_SDR/engine/scripts/live_sql.py` | T2: back-port micbridge filter to engine copy (22-line divergence) | Edit (branch) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/08_sop_metric_tables.md` | T3: per-SOP metric tables + summary table | New |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | T4: PT rows for FIND-35 + cold-ack carry | Append |
| ledger `findings`/`sops` | already has FIND-35 + 14 rows for 96746e56 | Read |

## Deploy Rules
- Restart: `systemctl --user restart diallux-8024.service && sleep 6 && curl -s http://127.0.0.1:8024/health` → expect `"tts":"elevenlabs/eleven_turbo_v2_5"`, `prewarm_pool stt/tts ready`
- NEVER touch: `CARTESIA_MODEL_ID` / `CARTESIA_VOICE_ID` / `CARTESIA_SPEED`, `VOICE_TEST_TOKEN`, other lanes (:8020–8023, :8026), :8000–8003, git history, Cal.com bookings without cancelling (event 3801235 REAL)
- Code on the branch only; docs straight to main; suite gate: `cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python -m pytest tests -q` (3 known pre-existing failures: `test_iter46_latency_floor::test_fast_first_flush_before_stream_end`, `test_iter59_dedupe_semantic::test_semantic_threshold_config_defaults`, `test_iter60_audit_fixes::test_turn_opening_reask_dropped_when_window_nonempty` — verified pre-existing with the change stashed)

## Tasks (in order) — HITL at every T
### T1 — Commit the RATE scope fix on the branch
Goal: working tree == branch tip for `engine/diallux/static/mic/index.html`.
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/static/mic/index.html`
Commands: `cd /home/julio/projects/clean_diallux_SDR && git add engine/diallux/static/mic/index.html && git commit -m "iter73 T1-fix: RATE moved to top-level IIFE scope (startCall-scoped const threw ReferenceError in playChunk — page received audio, never played it; the 06:47 outage)"`
Verification: `git status --short` shows no `M engine/diallux/static/mic/index.html`; `/mic` still serves (curl grep playbackRate).

### T2 — Sync the two live_sql.py copies
Goal: engine copy gets the micbridge name filter from root copy.
Files: `/home/julio/projects/clean_diallux_SDR/engine/scripts/live_sql.py`
Commands: copy the name-filter line block from `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (line ~153 `or name.startswith("micbridge-")`) into the engine copy's fetch_traces; run `cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python -m pytest tests -q` (no test covers this script; suite must stay 3-failures-known).
Verification: `engine/scripts/live_sql.py` grep micbridge = 1; re-run the import on window 06:54-07:04 idempotently (same call count, no dup rows).

### T3 — THE OWNER DELIVERABLE: per-SOP metric tables + summary table
Goal: render in chat AND save to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/03_sop_metric_tables.md`:
1. CALL table: all 8 categories (prompt_following · nonsense · redundancy · repetition · bugs · tool_calls · flow · metrics) × verdict × rule × evidence-quote, from the 14 ledger rows + a fresh read of the transcript `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter72-voice-lab/06_transcript_96746e56d2fa.txt` (never grade from memory).
2. SALES table: D1–D7 rows, each 0–2, total /14, band.
3. HUMANIZED table: R1–R5 (R5 sub-rows 5.1/5.3/5.4/5.5/5.7), PASS/POLISH/FAIL each.
4. SUMMARY table: one row per SOP — verdict + worst offender + one-line fix candidate.
5. Booking-truth row: Cal.com confirmation of ZERO new bookings + FIND-35 note (the call is NO-SALE; do not present SALES HIRE as a sale).
Dependencies: ledger SDK query `python3 /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db sops --run mic-20260924-96746e56 --json`.
Verification: every cell traces to a ledger row, transcript line, or Cal.com API response — nothing from memory.

### T4 — PENDING_TASKS + closeout rows
Append to `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md`: PT-74 (FIND-35 book-livecall recovery fabrication — endpoint-side fix candidate: distinct status for phone-match recovery; agent-side rule: recovered=true ⇒ NO-SALE), PT-75 (cold-ack carry: iter68 T4 chain-end ack flush `cc34343` — 3 cache-0 acks again on 96746e56d2fa), PT-76 (live_sql.py engine-copy back-port if not done in T2).
Verification: rows exist, referenced from `01_matrix.md`.

### T5 — Owner ear verdict on the playback knob (HITL)
Ask: which `?rate=` felt right (1.0/1.05/1.1/1.15)? Then: keep knob + set a default (owner pick) / remove knob. If keeping: owner decides whether the knob is mic-page-only (test surface) or ported to the Twilio path later (deferred).

### T6 — Next voice/recipe pick (HITL)
Options: more Hannah recipes (stability sweep 0.6/0.8), flatten delivery table (stage + swap), next shared voice, or rollback `TTS_PROVIDER=cartesia`. Owner dictates; every change = .env line + restart + `/health` verify + matrix row.

## Validation Plan (end-to-end)
1. T1 commit lands → branch clean except docs/evidence.
2. T3 tables rendered from ledger JSON + transcript — zero invented cells.
3. Any future BOOKED claim → Cal.com API store check FIRST (FIND-35 rule).
4. Suite: same 3 pre-existing failures, no new ones.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| book-livecall endpoint fix (distinct recovery status) | LIVE infra in the ORIGINAL workspace — needs its own plan + owner say-so |
| iter71 T2 ack-latency fix + Intake seeds | Separate plan exists (`plans/plan_v5_iter71_intake_samples_ack_latency.md`) |
| iter70 `engine/iter70-speech-fixes` @ `dc62fb9` merge | Owner-gated (LAW 0) |
| v3 audio-tag prompt swap | Parked in `/home/julio/projects/clean_diallux_SDR/research/11l_v3_prompting/01_v3_prompting_rules.md` |
| Morning 05:1x Eryn call analysis | Owner may finish later; 2-round 05:48 call aborted |
