# PLAN — v5 iter57: iter56 voice leg (launcher fix + boot self-check) + battery closeout

## Meta
- Date: 2026-09-19
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: complete iter56's unfinished C3 voice leg — relaunch the :8020 voice server with the CORRECT interpreter (the `.venv/bin/uvicorn` shebang trap killed RAG all call), add a boot self-check so RAG is proven alive before any speech, run the voice call, then close the iter56 battery (bookings, PT flips, ITERATIONS.md, merge ASK).
- Status: **PLAN ONLY (not started — awaits owner go)**
- Branch: continues ON `engine/iter56-state-delta-payload` (worktree `/tmp/opencode/wt-iter56`, head `abde308`, working tree clean). The self-check tooling rides this branch as a scripts/ addition; NO new branch.

## Compaction Context (session 2026-09-18/19 — pin, do not re-derive)

- **iter56 LANDED (approved plan `plans/plan_v5_iter56_state_delta_payload.md`):** branch `engine/iter56-state-delta-payload` @ `abde308` = `55d9754` (surgeon package) → `6d22fab` (C1a+C1b: `state_in_delta=True` state-block→post-history delta, `head_strip_vars=True` {{var}}→"CURRENT CALL STATE" strip incl. `_lite_head`, `history_window` 16→0 full history, `_warm` tail gate, ingest freeze inert-gated) → `abde308` (C2: `state_in_delta` + `delta_tokens` on the round usage log + Langfuse gen metadata). Worktree `/tmp/opencode/wt-iter56` (`.venv` symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`, `.env` copied). Suite **361 passed** (346 + 14 pins in `tests/test_iter56_state_delta.py` + 1 F-05 warm pin). Working tree CLEAN (0 modified) — the auto-generated `engine/eval/llm2llm_report.json` was restored.
- **Chat battery PASSED** (ledger run `battery-iter56`, session `battery-iter56@abde308`, 3 calls/93 rounds): Rourke/Maria/Susan all PASS+booked; cache floor ladder 1664→2688→3712→4736→5760→6784→7808 (old flat-2688 disease GONE); TTFT p50 850 ms (all in band); 0 literal `{{` (exhaustive 18-head sweep); 0 re-asks (PT-53 dead — Susan adversarial adapted twice, no 7-variant loop). Gates G1-G6 = PASS (G2 peak-vs-first; literal last-vs-first caveat = Phase-B Closing cold round, pre-existing).
- **4-SOP audit PASSED (62 sops rows, `02_sop_audit.md`):** 0 critical. CALL 8/8+7/8, SALES 14/14 hire-band all three, HUMANIZED only cosmetic (R5.4 stacked acks ×3-7/call, 1 "I hear you") + PT-54 concat OBSERVATION. LATENCY: TTFT p50 851/p90 1,104; steady p50 849; LLM-dur p50 1,387.
- **Reports on disk:** `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter56-state-delta-payload/01_report.md` (battery+gates, ADDENDUM 1 turn-1/2 deep-dive, ADDENDUM 2 launcher bug) and `.../02_sop_audit.md`.
- **Turn-1/2 chat cold-start ROOT CAUSE (verified):** greeting prewarms fire unconditionally on VOICE (`diallux/media/session.py:204-215`) but the chat harness mirrors them only behind `--warm-greeting-ms` (harness.py:581, default 0) — battery ran without it. Proof run `warmtest-iter56` (Maria + `--warm-greeting-ms 1700`, trace `96d3b82d0c34`): warms fired (`warm:lite:Intake` 3,298 ms, `warm:Intake` 3,478 ms) → r02 ack **616 ms**, r03 **984 ms**, Discovery entry 646-712 ms. r01 stayed cold because the lite warm's REQUEST takes ~3.3 s > 1.7 s window → its cache write lands after turn 1. Voice iter55 call proved the window IS enough there (warm 2,336/2,446 ms < ~10 s greet window; r01 634 ms @ cache 1664).
- **VOICE CALL 2026-09-19 (sid 5e1d5c0eed0b) — RAG WAS DEAD ALL CALL (verified, ADDENDUM 2):** server #1 (pid 3565984) launched via `.venv/bin/uvicorn` whose shebang → `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/dialux-langgraph-production-v5/.venv/bin/python3` (OLD venv; `pyvenv.cfg` `include-system-site-packages = false`). That venv has NO usable fastembed: `import fastembed` succeeds as an EMPTY NAMESPACE STUB (`__file__ = None` — false positive!) and `from fastembed import TextEmbedding` → `ImportError (unknown location)`. Real fastembed 0.8.0 (installed 2026-09-15) is in the MAIN venv `/home/julio/projects/clean_diallux_SDR/engine/.venv` only. Result: every `retrieve_lanes` failed → zero KB, zero industry pin, agent knowledge-blind in Intake 7 turns. Call's good news: turn-1 cache 1664 (lite warm 2,346 ms landed), full warm 2,347 ms ok, eager-EOT adoption worked, e2e 861-1,503 ms/turn, cache floor 2688 held (expected at ~3.1k input — next floor 3712 not reached).
- **State left behind:** :8020 DOWN (test servers killed; live :8000-:8003 and production agents untouched all session). Worktree clean @ `abde308`. Proposals made but NOT implemented: health self-check, launcher wrapper, scripted-call runs, any .env/pip/merge changes.
- **Session KB findings (facts, not tasks):** Offer state retrieved 0 chunks on all 3 battery calls (1 heavy round + degraded first-round set; eager RAG prefire exists only on the VOICE EOT path, `media/session.py:369` — chat has no prefire). First heavy round of every state degrades in chat. Local embedder cold-load ~1.2-1.3 s per process (snowflake-arctic-embed-m), hidden behind speech in voice via eager fire; steady 87-242 ms. RAG steady behavior otherwise CORRECT: 2-3 lanes, 2-3 chunks, sales-psychology on Closer every call, industry pin sticky from Discovery, plumbing deep-dive auto-joined.
- **PT-53/PT-55:** fixes VERIFIED by battery (0 re-asks; cache ladder) — flips pending at closeout. PT-54/PT-56/PT-45/PT-46 remain OPEN (separate plans).
- **Cal.com anomaly (PT-56):** booking uid `qeTqHuZ1EDzH8bxEdhPQ6H` (mock fixture from `tests/mock_webhooks.py:14`) resolved to an old cancelled Sep-4 booking; chat battery bookings are MOCKED; the :8020 voice path books REAL slots on event 3801235 → any real booking created this session MUST be cancelled at closeout.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Voice server launches ONLY via `.venv/bin/python -m uvicorn diallux.app:app` — NEVER `.venv/bin/uvicorn` | shebang points at the old isolated Retell venv (no fastembed) — verified root cause of the RAG-dead call |
| Boot self-check is a small `scripts/` tool + `/health` field, committed on the SAME branch | keeps one-branch discipline; makes the embedder proof a gate, not a hope; `import fastembed` alone is a false positive (namespace stub) |
| Browser-mic round (owner on mic) is the primary voice test; `scripts/fake_twilio_call.py` is the fallback if the mic path misbehaves | manual round matches iter55's instrument baseline; scripted path exists as bigger gun |
| iter56 battery closeout happens in THIS plan's session after the voice leg | plan discipline: report → PT flips → ITERATIONS.md → ASK in one pass |
| No engine payload changes | iter56 is done and verified; voice leg is measurement + closeout; new fixes (cap=1 lite warm, Phase-B warm, eager RAG prefire in chat, Offer lanes) go to iter58 per ADDENDUM 1/2 + KB findings |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner on the mic for the voice call (or a caller WAV for the scripted path) | owner schedules ~5 min; server is restarted first |
| Which Cal.com credential scope owns the :8020 bookings (PT-56) | owner's Cal dashboard / `/book-livecall` webhook env — needed only if a booking must be cancelled |

## Environment & Dependencies
- Worktree: `/tmp/opencode/wt-iter56` (exists, clean @ `abde308`). `git -C /tmp/opencode/wt-iter56 log --oneline -1` must print `abde308`.
- Venv: `/tmp/opencode/wt-iter56/engine/.venv` (symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`; fastembed 0.8.0 verified; snowflake-arctic-embed-m via `RAG_EMBEDDING_MODEL` in `.env`).
- Env: `/tmp/opencode/wt-iter56/engine/.env` (has LANGFUSE_*, OPENAI_*, CARTESIA_*, DEEPGRAM_*, TELEGRAM creds via `hitl_ping` fallback to `/home/julio/projects/video_strategy/.env`).
- Suite command: `cd /tmp/opencode/wt-iter56/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → expect **361 passed**.
- Langfuse: `http://localhost:3001` (server-local); SDK `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/lf.py health`.
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` — import from the MAIN checkout only: `cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run <name> --commit abde308 --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`.
- NO sqlite3 CLI, NO `rg` on this box — `.venv/bin/python -c "import sqlite3…"` + the grep tool. NO relative paths in replies.
- Voice server port: **127.0.0.1:8020** (isolated; live :8000-:8003 NEVER touched).
- Telegram ping: `cd /tmp/opencode/wt-iter56/engine && export $(grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /home/julio/projects/video_strategy/.env | xargs) && .venv/bin/python scripts/hitl_ping.py "<text>"` (fires BEFORE every owner ask).

## Architecture (one block)
```
[greeting TTS ~7s window] ──fire──> warm_rag + warm:Intake(full) + warm:lite:Intake
        (voice: session.py:204-215 fires unconditionally)
caller speaks ──EOT──> eager turn + eager spawn_live_retrieve (session.py:369)
round payload: [tools][head({{var}}→anchor)][FULL history][DELTA: state dvs + pinned industry + RAG lanes + directive]
RAG lanes: local snowflake-arctic-embed-m embed + pgvector retrieve_lanes — REQUIRES fastembed IN THE SERVER'S INTERPRETER
```

## File Map
| File (absolute) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter56/engine/scripts/voice_preflight.py` | NEW boot self-check: prints sys.prefix, `fastembed.__file__`, `from fastembed import TextEmbedding` result, resolves KB store, runs ONE `retrieve_lanes` probe on Intake scope, prints chunk count; exit 1 on any failure | N |
| `/tmp/opencode/wt-iter56/engine/diallux/app.py` | +2 fields on `/health`: `python_venv` (sys.prefix tail) + `embedder` (fastembed import status via TextEmbedding name-check) — fail-safe, never raises | E |
| `/tmp/opencode/wt-iter56/engine/tests/test_units.py` (or a new tiny `tests/test_voice_preflight.py`) | pins: health carries embedder field; preflight script exit codes | N/E |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter56-state-delta-payload/03_voice_report.md` | voice-leg report (traces, warm spans, gates) | N |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | iter56 ledger line (on branch) | E |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-53/PT-55 flips; PT-45 note (harness greeting-warm default still 0 — chat-only); PT-57 (launcher trap → ops ticket) | E |

## Deploy Rules
- Code/commit discipline per LAW 0 v3: commits ONLY on `engine/iter56-state-delta-payload`; NO merges without owner say-so; `scripts/keyhound` before any push.
- Voice server: foreground/background uvicorn on **127.0.0.1:8020** ONLY (free port, owner-ordered test). NEVER bind/start :8000-:8003. NEVER touch production agents (`agent_16985b5d087e56c35141983396` voice, `agent_f305981ef7b5ce312c1c899bbf` chat, `agent_87e4d5f08475e5bc558b2f390f` legacy).
- Launcher (MANDATORY): `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8020 > /tmp/opencode/iter57_voice_server.log 2>&1 &` — NEVER `.venv/bin/uvicorn` (shebang trap, ADDENDUM 2).
- Cancel ALL Cal.com test bookings after the voice call (event 3801235 is REAL).
- Telegram ping BEFORE every owner ask (`scripts/hitl_ping.py`).

## Tasks (in order)
### T1 — Relaunch + boot self-check (the RAG gate)
Goal: :8020 serving the iter56 engine with PROVEN RAG before anyone speaks.
Files: `scripts/voice_preflight.py` (new), `diallux/app.py` health fields, test pin.
Commands (full):
1. Write `scripts/voice_preflight.py` per File Map; add health fields to `diallux/app.py`.
2. `cd /tmp/opencode/wt-iter56/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → 361+passed.
3. Launch: `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8020 > /tmp/opencode/iter57_voice_server.log 2>&1 & sleep 6 && curl -s http://127.0.0.1:8020/health`.
4. Preflight: `cd /tmp/opencode/wt-iter56/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/voice_preflight.py --url http://127.0.0.1:8020` .
Verification: health JSON contains `python_venv` ending `wt-iter56/engine/.venv` and `embedder` ok; preflight exits 0 and prints ≥1 chunk; server log has zero `No module named` lines.
Dependencies: fastembed 0.8.0 in main venv (verified), pgvector store reachable (env `RAG_*` in `.env`).
### T2 — Voice call (owner on mic)
Goal: the iter56 C3 voice leg.
Commands: owner opens `http://127.0.0.1:8020/mic` (SSH tunnel if remote: `ssh -N -L 8020:127.0.0.1:8020 julio@46.62.233.228`); full intake→booking call. Fallback if mic path fails: TTS a caller WAV + `cd /tmp/opencode/wt-iter56/engine && .venv/bin/python scripts/fake_twilio_call.py --url ws://127.0.0.1:8020/media --input /tmp/opencode/caller.wav --output /tmp/opencode/out.wav`.
Verification: server log shows RAG lanes with chunks > 0; `warm:lite:Intake` + `warm:Intake` spans ok; call trace in Langfuse (`micbridge-*`).
### T3 — Trace + gates + ledger
Goal: prove the voice leg against the iter55 baseline + the chat ladder.
Commands: pull newest `micbridge-*` trace via `scripts/lf.py traces`; extract per-turn TTFT/cache, warm spans, greeting anchors, RAG spans (industry pin + chunk counts); import: `cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run voice-iter56 --commit abde308 --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`.
Verification (gates): turn-1 cache ≥1664; cache_read climbs ≥ +1,000 from first to peak round; no `retrieve_lanes failed` lines; industry pin present in RAG spans; TTFT worst ≤ 1,600 ms (voice band from iter55 call: 634-782 steady).
### T4 — Closeout + ASK
Goal: end the iteration per LAW 0.
Commands: cancel test bookings (Cal.com API v2 `POST /v2/bookings/{uid}/cancel` with the Cal key from the relevant `.env`, or owner's dashboard — PT-56 caveat); commit `03_voice_report.md` evidence + ITERATIONS.md line + PENDING_TASKS flips (docs ride the branch per iter56 pattern); Telegram ping.
Verification: report written; bookings gone; ping sent; then **ASK JULIO (merge gate)** — hold for say-so.

## Validation Plan (end-to-end)
1. T1: health + preflight green (RAG ALIVE before speech — the ADDENDUM 2 trap closed).
2. T2: one full voice call, trace complete in Langfuse.
3. T3: ledger row `voice-iter56` + gates computed with SQL citations in `03_voice_report.md`.
4. T4: bookings cancelled; docs flipped; ASK.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Lite warm `max_completion_tokens=1` (3.3 s completion > greet window) | iter58 code ticket (ADDENDUM 1 fix list #2); one variable per iteration |
| Phase-B chain Closing warm | iter58 (G2 caveat, ADDENDUM 1 #3) |
| `--warm-greeting-ms` battery default (chat parity) | iter58 harness change (ADDENDUM 1 #1) |
| Chat eager RAG prefire / Offer 0-chunk state | iter58 RAG ticket (KB findings, this session's evidence) |
| Embedder warm-at-greeting (kills the 1.2 s cold load) | iter58, same ticket cluster |
| PT-54 concat echo, PT-56 booking uid anomaly, PT-45/PT-46 | separate plans/services-side |
| iter50 US-East migration | staged; awaits owner provisioning (`plans/plan_v5_iter50_us_region_migration.md`) |
