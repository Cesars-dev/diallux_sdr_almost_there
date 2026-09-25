# PLAN — v5 iter37 follow-up: Langfuse autopsy of the live micbridge disaster call

## Meta
- Date: 2026-09-09
- Project root: `/home/julio/projects/clean_diallux_SDR` (fork = main workspace). Engine tree lives on git branches `engine/iterNN-*`, checked out via worktrees under `/tmp/opencode/wt-iterNN`.
- Scope: READ-ONLY forensic analysis of the failed live browser-mic call(s) of 2026-09-09 — server log + Langfuse traces — producing a root-cause verdict report. NO code changes in this plan (fixes = follow-up plan).
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context
- Project: Dialux SDR voice engine ("Linda"), LangGraph 9-state pipeline (Intake → Discovery → Closer → Offer → contact_details → ConfirmSlots → VerifyLead → Booking → Closing), Deepgram Flux STT → graph → gates → Cartesia TTS. Repo doctrine: `/home/julio/projects/clean_diallux_SDR/AGENTS.md` (LAW 0: code = branch+test+report, owner-gated merge; docs = straight to main; never run services from the fork EXCEPT owner-ordered test runs).
- Branch `engine/iter37-browser-mic-tts` = iter33 phaseb engine chain (working MVP, parent commit `bfbd181`) + ported iter21 proven TTS session. Commits: `3499a1c` (port: /mic page, /mic/ws, transport plumbing, SSML jitter, speak-clock, warm_rag, rag_min_query_chars, .env.example → Linda), `a4af265` (fix#1: restore `deepgram_eager: bool = True` master switch — live test #1 crashed every session at start with AttributeError), `4e72200` (fix#2: init `query=""` in `graph/builder.py` before frozen-reuse branch — live test #2 crashed turn 2+ with UnboundLocalError inside the rag tracer span; + regression test). Suite: **154 passed**.
- Proven TTS config (tested live 2026-09-06 in ORIGINAL workspace, 116-turn call, e2e p50 1354ms): `CARTESIA_VOICE_ID=829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30` (Linda), `CARTESIA_SPEED=1.05`, `TTS_PROVIDER=cartesia`, `sonic-3.6`, `AUDIO_TRANSPORT=browser`, `DEEPGRAM_EAGER_EOT=true`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.6`. Verified via Cartesia `GET /voices/{id}`.
- Live test runs 2026-09-09 (owner Julio on the Mac via SSH tunnel, Chrome `http://localhost:<port>/mic`):
  - `:8004` (commit `3499a1c`, pid 2053946): every session crashed at start (fix#1 bug). Killed.
  - `:8005` (commit `a4af265`, pid 2080722): sessions started but turns ≥2 crashed with `UnboundLocalError: query` (fix#2 bug). Julio: "stuck on listening". Killed.
  - `:8005` restart (commit `4e72200`, pid 2099198, started ~06:5x): call RAN — log tail shows turns 89–97 between 06:58:59 and 07:00:41, call `baccf630adfd`, stopped `mic_stream_closed` 07:00:41. Julio verdict: **"total disaster"**. Observed in log: turn 91 `stt_eot_to_llm_first_ms=7151.7` (7s spike, eager speculative turn at 06:59:31 + TWO chat/completions 06:59:34 and 06:59:40), turns 96/97 with all-null metrics and ~6ms e2e right before close, `tts_first_to_audio_out_ms=0.0` on every turn, `barge_in: false` everywhere, ~97 turns total (healthy booking = 4–18 turns per iter31 battery). Root cause UNKNOWN — this plan finds it.
- Runtime facts: app = `/tmp/opencode/wt-iter37` (worktree of branch `engine/iter37-browser-mic-tts`), venv `/home/julio/projects/clean_diallux_SDR/engine/.venv` (python 3.12), log `/tmp/opencode/uvicorn_8005.log` (**overwritten on every restart — must be copied before any restart**), listen `127.0.0.1:8005`. Langfuse self-hosted `http://localhost:3001` (~25% ingest loss; server-log turn reports are the second source of truth). Secrets in `/tmp/opencode/wt-iter37/.env` (gitignored; has LANGFUSE_*, CARTESIA_API_KEY, DEEPGRAM_API_KEY, OPENAI_API_KEY, DATABASE_URL→`localhost:5434` docker `diallux-db`).
- Evidence zone: `/home/julio/projects/clean_diallux_SDR/research/` (gitignored). Reports of past batteries: `research/surgeon/…`.
- Tooling: engine `scripts/lf.py` (health/traces/costs/lat subcommands — exact syntax in `scripts/lf.md`), `scripts/lf_eval.py status`. opencode has a skill `langfuse-call-analysis` that wraps lf.py for v5 call autopsies — the executor MUST load it.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Autopsy is READ-ONLY: no code edits, no restarts, no kills during analysis | Fixing before evidence capture destroys the crime scene; log file is clobbered on restart |
| Analyze call `baccf630adfd` (07:00:41 close) as primary; any earlier `micbridge-*` traces from 06:5x as secondary | It is the "total disaster" call on the fixed build |
| Sources of truth = server log copy + Langfuse traces; log wins on conflict | Langfuse drops ~25% of ingests (known) |
| Report lands in `research/` (gitignored), ledger updates go on the iter37 branch, plan file to main | AGENTS.md zone rules |
| No re-test until the report names a root cause and Julio approves | Owner gate |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Julio's ear-witness account of the disaster call (what he heard/said, when audio died) | Ask Julio before writing the verdict |
| Exact session start time of call `baccf630adfd` | Full server log copy (log tail only showed turns 89+) |
| UNKNOWN — whether the mic picked up Linda's own TTS (echo self-talk loop) — suspected cause of ~97 turns | Langfuse transcript: check if user-role text mirrors agent text |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12; langgraph 1.2.11, langfuse 4.15.1, httpx, fastapi)
- Langfuse: `http://localhost:3001`, keys in `/tmp/opencode/wt-iter37/.env` (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`)
- App (DO NOT RESTART): pid `2099198`, `127.0.0.1:8005`, log `/tmp/opencode/uvicorn_8005.log`
- Live services that must NOT be touched: `:8001` cal_slots, `:8002` time, `:8003` validator, old `:8000` uvicorn pid 2659243 (ORIGINAL's, leave alone)
- docker `diallux-db` (:5434) — read-only needs only

## Architecture (one block diagram)
```
Mac Chrome /mic ──ws──▶ :8005 app (iter37 build)
   getUserMedia 16k PCM ─▶ Deepgram Flux STT ─▶ LangGraph graph ─▶ gates ─▶ Cartesia TTS (Linda)
                              │                                     │
                              └────────── Langfuse :3001 ◀──────────┘
                              trace micbridge-<call_sid>  +  turn reports ─▶ uvicorn_8005.log
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter37-langfuse-autopsy/log_uvicorn_8005_20260909.log` | copy of the live log | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter37-langfuse-autopsy/traces_micbridge.json` | lf.py trace dump | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter37-langfuse-autopsy/01_autopsy_baccf630adfd.md` | the verdict report | NEW |
| `/tmp/opencode/wt-iter37/notes.md` | append autopsy verdict line (on branch, committed) | EDIT |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter37_langfuse_call_autopsy.md` | this plan | NEW (main) |

## Deploy Rules
- NEVER restart/kill pid 2099198 or any uvicorn before the log copy exists.
- NEVER touch `:8001–:8003`, the `:8000` pid 2659243, production agents (`agent_16985b5d087e56c35141983396`, `agent_87e4d5f08475e5bc558b2f390f`), or Cal.com event 3801235 (real bookings — cancel any test booking created).
- No code changes on this plan; no pushes; no merges (LAW 0).

## Tasks (in order)

### T0 — Preserve evidence
Goal: immortalize the log before anything can clobber it.
Files: log copy (File Map row 1).
Commands (full):
```bash
mkdir -p /home/julio/projects/clean_diallux_SDR/research/surgeon/iter37-langfuse-autopsy
cp /tmp/opencode/uvicorn_8005.log /home/julio/projects/clean_diallux_SDR/research/surgeon/iter37-langfuse-autopsy/log_uvicorn_8005_20260909.log
wc -l /home/julio/projects/clean_diallux_SDR/research/surgeon/iter37-langfuse-autopsy/log_uvicorn_8005_20260909.log
df -i / | tail -1   # expect > 50000 free
```
Verification: copy exists, `grep -c "turn.*report" <copy>` > 90, first line timestamp noted (session start).
Dependencies: none.

### T1 — Langfuse pull
Goal: dump every micbridge trace from the test window.
Files: `traces_micbridge.json`.
Commands (full):
```bash
cd /tmp/opencode/wt-iter37 && set -a && . ./.env && set +a
.venv_placeholder  # use /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py health
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py traces --hours 3 --name micbridge > /home/julio/projects/clean_diallux_SDR/research/surgeon/iter37-langfuse-autopsy/traces_micbridge.json
```
(Exact lf.py flags per `scripts/lf.md`; the `langfuse-call-analysis` skill wraps this — load it.)
Verification: JSON contains trace id ending `baccf630adfd` (or the micbridge-<sid> session naming per `media/session.py`); if Langfuse dropped it, proceed with log-only and record the loss.
Dependencies: T0.

### T2 — Transcript + turn-by-turn dissection of `baccf630adfd`
Goal: reconstruct the whole call: every turn's user text, agent text, tool calls, gate rejections, state transitions.
Commands: parse the log copy (turn reports + `diallux.session` lines) and cross-ref Langfuse gens/spans for the trace. Extract: turn count, per-state turn histogram, user-vs-agent text table, all tool_calls with args, all EOT/eager events, silence rounds, end_call attempts.
Verification: a turn table exists in the report with ≥90 rows (turns 1–97) or the exact count with an explanation of gaps.
Dependencies: T1.

### T3 — Latency dissection
Goal: find where the 7–8s turn went and why `tts_first_to_audio_out_ms=0.0` everywhere.
Commands: aggregate `stt_eot_to_llm_first_ms`, `llm_first_to_tts_first_ms`, `e2e_response_ms` from all turn reports (awk/python over the log copy); compare against iter21 measured p50 1354ms / the log's 06:58–07:00 lines (turn 89: 1263ms, turn 91: 8021ms with TWO chat/completions, turn 93: 2742ms).
Verification: p50/p90/max per stage in the report; the turn-91 double-generation explained (eager speculative turn + real turn? cancel race?).
Dependencies: T0.

### T4 — Audio-path audit
Goal: answer "why couldn't Julio hear / why 97 turns" on the transport layer.
Check (log + code reading, no edits): (a) did `speak_chunk`/`_on_tts_audio` fire per turn and how many bytes went out the ws (`_send_raw` path); (b) `tts_first_to_audio_out_ms=0.0` semantics — is `t_audio_out` stamped before bytes actually flush (outbox writer)? (c) browser ducking/barge-in: `barge_in: false` on all turns — did the page ever duck its mic; (d) ECHO SELF-TALK test: do any "user" utterances in the transcript duplicate Linda's own spoken text (mic re-ingesting speaker output → loop). If echo confirmed → root cause candidate #1 for the 97-turn spiral.
Verification: each check has a yes/no + evidence line in the report.
Dependencies: T2.

### T5 — Verdict report
Goal: one md: timeline, turn table, latency table, audio findings, ranked root causes with evidence, and the recommended fix list (for the follow-up plan).
Files: `01_autopsy_baccf630adfd.md`.
Commands: write it; append one-line verdict to `/tmp/opencode/wt-iter37/notes.md`; commit on branch `engine/iter37-browser-mic-tts` (docs+ledger commit only, e.g. `iter37: autopsy verdict — <one line>`); present to Julio.
Verification: report exists; Julio has read the one-line verdict; follow-up fix plan drafted (separate file) ONLY after Julio confirms.
Dependencies: T2–T4 + Julio's ear-witness answers.

## Validation Plan (end-to-end)
1. T0: log copy immutable with >90 turn reports.
2. T1: micbridge trace JSON in research/.
3. T2–T4: every numbered check answered with evidence.
4. T5: verdict names ≥1 confirmed root cause (or explicitly states inconclusive + what extra capture is needed); notes.md updated on branch.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Any code fix for the root cause | Owner-gated follow-up plan; one variable per iteration |
| Live re-test on :8005/:8006 | Only after fixes + Julio present |
| Twilio deploy | Blocked on TWILIO keys (separate track, checklist in notes.md @ `4e72200`) |
| iter37 merge to main | LAW 0 — after live test passes |
