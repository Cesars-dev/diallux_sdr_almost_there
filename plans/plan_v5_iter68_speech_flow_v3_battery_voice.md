# plan_v5_iter68_speech_flow_v3_battery_voice — T6 battery (async) + :8024 lane deploy + owner ear test + closeout

## Meta
- Date: 2026-09-23
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: run the iter68 happy3 battery in the background, deploy the iter68 code to the :8024 mic lane (web endpoint), run the owner ear test, close out (ledger import, bookings cancelled, checkout restored, report, HITL ASK, docs to main).
- Status: IN PROGRESS — **T1 DONE (preflight clean: no stray bookings from the aborted 08:16 battery — 0 chat-* traces in 2h; worktree clean @ cc34343; plan committed to main @ `2ffa596`) · T2 NOT DONE (two launch attempts died — nohup was killed by the shell-timeout process-group kill, then the foreground run was aborted at 08:37; ZERO battery calls made, no bookings) · T3 DONE (lane deployed 08:36: 12 runtime files copied worktree→main checkout, `diallux-8024.service` restarted, journal confirms `cartesia connected (model=sonic-3.6-2026-08-27)`, `/health` = gpt-5.4 + cartesia/sonic-3.6-2026-08-27 + prewarm ready; main checkout now holds TEMPORARY uncommitted iter68 copies — restore per T6) · T4-T7 PENDING. EXECUTE FROM T2 IN A NEW SESSION.**
- Branch: `engine/iter68-speech-flow` @ `cc34343` (4 commits: T1 `c6159ce`, T2 `22e6f88`, T3 `c3022c3`, T4 `cc34343`), worktree `/tmp/opencode/wt-iter68`
- Base: main @ `8e06fe9` · Suite: **476 passed + 1 known env failure** (`tests/test_tts_providers.py::test_factory_switches_provider` — pre-existing cartesia-vs-EL-default env pin, NOT iter68's; owner-confirmed intended `.env`)

## Compaction Context
Dialux SDR v5 engine (LangGraph voice pipeline) in `/home/julio/projects/clean_diallux_SDR`. iter68 "speech flow" fixes four reproduced mic-call defects. **T1-T4 are committed on branch `engine/iter68-speech-flow` @ `cc34343`** (worktree `/tmp/opencode/wt-iter68`, venv symlinked to the main checkout's `engine/.venv`, `.env` copied in — gitignored): T1 speech-filter observability (`speech_filter stage=… sent=… state=… turn=…` INFO logs at all 4 drop stages, both flush sites) + cancel-safe Langfuse gen spans + `mic_events.py` CUT/REASK tags + `speech_replay.py --knobs`; T2 deterministic transition beat (ok `transition_to_*` one-trips ONLY when `turn_asked` — post-filter spoken-`?` GraphState flag; flat ack routes into the destination's EXISTING entry_lite ack = exactly ONE continuation round) + `tts_gate_fast_first_flush` code default False + `tts_gate_fast_first_flush_min_chars: int = 12` knob + turn-end/transition-ack/letter-spelling prompt directives in Intake/Discovery/Closer/Offer.md mirrored into `agent/llm.json` (byte-locked for Offer + contact_details via `tests/test_iter43_prompts.py`; `refer` count = 36 preserved); T3 scripted-question full pass (exact normalized dict + flex cos ≥ `scripted_pass_cos_threshold`=0.85 vs pre-embedded `<...>` spans of the CURRENT state; batch pre-embed once per call via new `rag.py::embed_many`) + per-state semantic gate (`tts_dedupe_semantic_exempt_states=("Intake",)`) + re-ask-round exemption + 2-strike re-ask ladder + letter-spelling in `contact_details.md` + silence re-ask (`silence_reask=True`, `silence_reask_ms=2000`: session timer one-shot armed in `_late_turn_report`, cancelled on `_on_start_of_turn`, fires `_run_turn("", extra_payload={"silence_reask": True})`, ingest guard = no empty user message appended, re-ask rounds always heavy + semantic-exempt) + scripted-pass simulation in `speech_replay.py`; T4 one spoken reply per turn (chain-link rounds — prev round's tools all matched by NEW `_SILENT_ROUND_RE` which adds `calculate_`/`record_` prefixes to `_MECHANICAL_RE` — buffer their TTS; chain-end ack flushes at transition `tool_call_start`; text-only final rounds flush; `round_spoke` stays content-based so the iter32 force_speech rule never fires mid-chain; the `?`-yield backstop was DROPPED — it killed calculate→reveal chains and is redundant for text-only stacks).
Suite: 476 passed, 1 failed = the known env pin `test_factory_switches_provider` (asserts EL code default; `.env` runs cartesia per VOICE LAW — owner-confirmed intended, pre-existing, not iter68's).
Offline calibration PASSED: `speech_replay.py` on `micbridge-ccacb090cc54` shows the 8 previously-muted scripted re-asks SPOKEN (scripted-flex cos 0.9055-1.0), 0 cuts; `micbridge-14d42eafa601` + `micbridge-cc750d181c6f` 0 cuts (Intake exempt per owner rule).
T5 read-only done: turn-1 TTFT (1,071ms on `cc750d181c6f`) ≈ steady-state p50 (1,018ms) — the ~1s floor is gpt-5.4 uncached prefill, prewarm/await path clean (`await_warm already_done waited_ms=0`); live mic KB coverage 52% zero-chunks (26/50 rag rows) → recommend pinning the industry vertical (iter52 metadata lane) — SEPARATE owner decision, not this iteration.
T6 battery was started 08:16 and ABORTED seconds in — almost certainly no bookings made; T1 of this plan verifies via Langfuse.
**What remains:** the T6 battery + report + ASK (this plan), the :8024 lane deploy of the iter68 code, the owner ear test, Cal.com booking cleanup, main-checkout restore, docs to main.
Twilio coexistence (owner directive, verified in `tasks/surgeon/iter68-speech-flow/archive/`): branch `engine/iter67-twilio-live-lane` @ `0394a3b` overlaps iter68 ONLY in `engine/diallux/config.py` (Twilio adds `twilio_signature_check` @ ~:389; iter68 edits :165-:344) — ≥45 lines apart, `git merge-tree` exit 0, BOTH merge orders clean. Rule: keep the MAIN checkout clean of iter68 lane-deploy copies whenever the owner merges (restore after every ear test).
**Never touched:** `:8021` (pid 3834955), `:8022` (pid 884638), `:8000-8003` services, `engine/diallux/media/prewarm.py`, `engine/diallux/media/elevenlabs_tts.py`, `engine/diallux/media/tts_factory.py`, branches `engine/iter66-*`/`iter64-ela`, live agent IDs, Cal.com event 3801235 (REAL — cancel test bookings).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Battery = `happy3` only this session (3 personas, no Rourke) | Owner directive "3 happy battery first"; Rourke deferred |
| Battery runs from the WORKTREE `/tmp/opencode/wt-iter68/engine` (not the lane) | chat harness ≠ mic lane; the worktree runs branch code @ cc34343 |
| Lane deploy = copy 12 runtime files into the MAIN checkout + restart `diallux-8024.service`; RESTORE after testing | Master plan §8 + §0.4 hygiene: uncommitted copies in the main checkout would block the owner's Twilio merge |
| Battery async (background, nohup), lane deploy in parallel | Owner: "3 happy battery first, async, then voice" |
| Ear test verdicts = owner only; merge = owner only | LAW 0 |
| `TTS_PROVIDER=cartesia`, `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27`, `TTS_GATE_FAST_FIRST_FLUSH=false`, `OPENAI_MODEL=gpt-5.4` | VOICE LAW (AGENTS.md, commit `6724be3`) + owner 2026-09-23 "fast flush off, provider cartesia for now" |
| Scripted-pass threshold 0.85 stays; A/B offline via `speech_replay.py --knobs scripted_pass_cos_threshold=…` | Owner's "room to breathe" band 0.85-0.90; live tuning needs no redeploy |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Ear-test verdicts (owner speaks on the mic) | `https://flores.diallux-ai.site/voice24/mic` after T3 |
| Merge say-so (iter68 AND Twilio) | Telegram ASK at closeout |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv` (symlinked into `/tmp/opencode/wt-iter68/engine/.venv`; 3.12.3; pytest 9.1.1; langchain_openai 1.6.0; openai 3.8.0; fastembed local arctic-embed-m at `/home/julio/fastembed/models`)
- Secrets: `/tmp/opencode/wt-iter68/engine/.env` (copy of the main checkout's — `OPENAI_API_KEY`, `LANGFUSE_*`, `DATABASE_URL`, `CARTESIA_*`, `DEEPGRAM_API_KEY`; NEVER print values, NEVER commit)
- Battery lane: chat llm2llm harness — NO mic-lane interaction
- Mic lane: systemd `diallux-8024.service` (`~/.config/systemd/user/diallux-8024.service`, `WorkingDirectory=/home/julio/projects/clean_diallux_SDR/engine`, `CALL_PREWARM=true`), mic page `https://flores.diallux-ai.site/voice24/mic`, logs `journalctl --user -u diallux-8024.service`
- Langfuse: self-hosted `http://localhost:3001` (keys in `.env` `LANGFUSE_*`); traces named `chat-iter68-happy`/`chat-iter68-rourke` by the harness + `micbridge-<sid>` on the mic lane; SDK `/home/julio/projects/clean_diallux_SDR/engine/scripts/lf.py`
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (NO sqlite3 CLI — `.venv/bin/python -c "import sqlite3; …"`); import via `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (accepts `chat-*` and `micbridge-*`)
- Branch registry: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` — refresh via `scripts/call_ledger.py` extracted from `git show engine/iter47-call-ledger:scripts/call_ledger.py`, run from the MAIN checkout's `engine/` dir (TRAP per AGENTS.md)
- Report folder: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter68-speech-flow/01_report.md` (gitignored evidence zone)

## Architecture (one block)
```
[worktree /tmp/opencode/wt-iter68 @ cc34343]
   ├── (T2) nohup harness --personas happy3 → Langfuse chat-iter68-* traces → ledger import → gates
   └── (T3) 12 runtime files ──copy──► MAIN checkout engine/ ──► systemctl restart diallux-8024
                                                                 └── (T5) owner mic call → speech_filter journal lines + turn reports → ear verdict
(T6) cancel test bookings · restore main checkout · registry refresh · report · hitl_ping ASK
```

## File Map
| File (absolute path) | What changes | New/Edit |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter68_speech_flow_v3_battery_voice.md` | THIS plan (docs → main) | New |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-65/66/67 rows (docs → main) | Edit |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter68_speech_flow_v2.md` | Status line → EXECUTED (T1-T4) / battery phase v3 (docs → main) | Edit |
| `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter68-speech-flow/**` (4 md + archive/) | commit to main as docs | Add |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter68-speech-flow/01_report.md` | battery + ear-test report (gitignored) | New |
| MAIN checkout copies (TEMPORARY, restored in T6): `engine/diallux/graph/builder.py`, `engine/diallux/config.py`, `engine/diallux/media/session.py`, `engine/diallux/rag.py`, `engine/diallux/state.py`, `engine/agent/llm.json`, `engine/diallux/prompts/{Intake,Discovery,Closer,Offer,contact_details}.md`, `engine/scripts/mic_events.py`, `engine/scripts/speech_replay.py` | lane deploy of iter68 | Copy |

## Deploy Rules
- Battery (from the worktree — full command):
  ```
  cd /tmp/opencode/wt-iter68/engine && set -a && . ./.env && set +a && date +%H:%M && \
  nohup .venv/bin/python tests/llm2llm/harness.py --personas happy3 --rag --rag-fire-sim --langfuse --max-turns 48 > /tmp/opencode/iter68_battery.log 2>&1 &
  ```
- Lane deploy (copy + restart + verify):
  ```
  cd /tmp/opencode/wt-iter68 && git checkout-index --prefix=/tmp/opencode/iter68_stage/ -af && \
  cp /tmp/opencode/iter68_stage/engine/{diallux/graph/builder.py,diallux/config.py,diallux/media/session.py,diallux/rag.py,diallux/state.py,agent/llm.json} /home/julio/projects/clean_diallux_SDR/engine/ && \
  cp /tmp/opencode/iter68_stage/engine/diallux/prompts/{Intake,Discovery,Closer,Offer,contact_details}.md /home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/ && \
  cp /tmp/opencode/iter68_stage/engine/scripts/{mic_events,speech_replay}.py /home/julio/projects/clean_diallux_SDR/engine/scripts/ && \
  systemctl --user restart diallux-8024.service && sleep 4 && \
  journalctl --user -u diallux-8024.service -n 30 --no-pager
  ```
  (verify boot + `cartesia connected (model=sonic-3.6-2026-08-27)`)
- Lane RESTORE after the ear test (Twilio-merge hygiene, master plan §0.4):
  ```
  git -C /home/julio/projects/clean_diallux_SDR checkout -- engine/diallux engine/agent/llm.json engine/scripts && \
  systemctl --user restart diallux-8024.service
  ```
- NEVER touch: `:8021`/`:8022`, `:8000-8003`, `engine/diallux/media/prewarm.py`, `elevenlabs_tts.py`, `tts_factory.py`, live agent IDs, Cal.com event 3801235 bookings (cancel test ones)
- Push = owner terminal (agent shell has no creds)

## Tasks (in order)
### T1 — Preflight: stray-booking check + state verify
Goal: confirm the aborted 08:16 battery left no test bookings; confirm branch/worktree/env state.
Commands:
- `cd /tmp/opencode/wt-iter68/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/lf.py traces --name chat- --hours 2 | head -20` (any `chat-` trace after 08:10 = the aborted battery started a call — if found, cancel its booking)
- `git -C /tmp/opencode/wt-iter68 status --short` (expect clean) · `git -C /tmp/opencode/wt-iter68 log --oneline -1` (expect `cc34343`)
Verification: no chat-* traces after 08:10 (or bookings cancelled); tree clean @ cc34343.

### T2 — Launch happy3 battery (background)
Goal: 3/3 happy-path personas BOOK on iter68 code @ cc34343.
Commands: the nohup battery command in Deploy Rules (log `/tmp/opencode/iter68_battery.log`).
Dependencies: `.env` in the worktree (present), Langfuse up.
Verification: `tail /tmp/opencode/iter68_battery.log` shows per-persona progress; completion line with 3/3 BOOK.

### T3 — Lane deploy of iter68 to :8024 (parallel with the battery)
Goal: the web endpoint (`https://flores.diallux-ai.site/voice24/mic`) serves iter68 code.
Commands: the lane-deploy block in Deploy Rules.
Verification: journal shows the app up; the NEXT live call logs `speech_filter stage=…` lines (T1 machinery live) and turn reports; `cartesia connected (model=sonic-3.6-2026-08-27)`.

### T4 — Battery completion: import + gates
Goal: ledger evidence + named SQL gates.
Commands:
- `cd /tmp/opencode/wt-iter68/engine && set -a && . ./.env && set +a && /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py import --window "<HH:MM-HH:MM from the battery log>" --run chat-iter68-happy --branch engine/iter68-speech-flow --commit cc34343 --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`
- Gates: `.venv/bin/python /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py gates --a chat-iter65-happy --b chat-iter68-happy` (per SQL_ANALYSIS_SOP)
Verification: 3/3 BOOK rows; no 4-round leaks (rounds table per call ≤ realistic rounds); replay one battery trace with `speech_replay.py` showing 0 muted-scripted cuts.

### T5 — Owner ear test on :8024 (HITL — owner speaks)
Goal: owner judges the fixed flow live: scripted re-asks audible, transition acks never flat, one reply per turn, silence re-ask at ~2s, ≤2 asks per missing field, letter-spelled company name.
Commands: owner calls `https://flores.diallux-ai.site/voice24/mic` (say it is iter68: verify via `journalctl --user -u diallux-8024.service | grep speech_filter | head`).
Verification: journal shows `speech_filter` lines + `silence_reask` at most once per silent window; no `stage=sanitize` floods; owner verdict recorded in the report.

### T6 — Closeout: bookings cancelled + checkout restored + registry + report + ASK
Commands:
- Cancel ALL test bookings made today (Cal.com event 3801235 is REAL)
- Restore: the lane-RESTORE block in Deploy Rules (main checkout clean again)
- Registry refresh: `git show engine/iter47-call-ledger:scripts/call_ledger.py > /tmp/opencode/call_ledger.py && cp /tmp/opencode/call_ledger.py /home/julio/projects/clean_diallux_SDR/engine/scripts/ && cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python scripts/call_ledger.py` (backup the registry DB first: `.venv/bin/python -c "import shutil; shutil.copy('/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db','/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db.iter68.bak')"`)
- Report: write `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter68-speech-flow/01_report.md` (battery gates, ear-test verdicts, T5 findings, Twilio-coexistence status)
- ASK: `cd /tmp/opencode/wt-iter68/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py` — **STOP AT HITL; merge = owner only (iter68 AND Twilio).**
Verification: registry rows for iter68 present; report exists; ASK sent.

### T7 — Docs to main (straight commit, LAW 0 docs lane)
Commands:
```
git -C /home/julio/projects/clean_diallux_SDR add plans/plan_v5_iter68_speech_flow_v3_battery_voice.md plans/PENDING_TASKS.md plans/plan_v5_iter68_speech_flow_v2.md tasks/surgeon/iter68-speech-flow && \
git -C /home/julio/projects/clean_diallux_SDR commit -m "docs: iter68 battery/voice phase plan + PT-65/66/67 + surgeon dossier (audit->master plan)"
```
PENDING_TASKS rows: PT-65 speech-filter observability (DONE iter68 branch), PT-66 re-ask escalation + 2s silence rule (DONE iter68 branch), PT-67 one-reply-per-turn + scripted full-pass + transition beat (DONE iter68 branch) — statuses "DONE (iter68 branch @ cc34343, awaiting merge — owner)".
Verification: `git -C /home/julio/projects/clean_diallux_SDR log --oneline -1` shows the docs commit; main checkout still has NO code changes (only docs).

## Validation Plan (end-to-end)
1. Battery: happy3 3/3 BOOK on branch code; ledger imported; gates queried by SQL not by feel.
2. Lane: :8024 serving iter68 (`speech_filter` logs live), Cartesia pin confirmed in the journal.
3. Owner ear test: the four fixed behaviors audible (scripted re-asks, transition beat, one-reply-per-turn, silence re-ask).
4. Bookings cancelled; main checkout restored; registry refreshed; report written; ASK sent; docs on main.
5. Merge = owner only (iter68 AND the Twilio branch — verified collision-free, both orders).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Rourke battery persona | Owner asked for the 3-happy battery; Rourke can run after the ear verdict |
| Industry-vertical pin (T5 KB recommendation) | Owner-gated separate decision (iter52 metadata lane) |
| Turn-1 TTFT floor fix | Diagnosis only — no structural defect found; separate branch if the owner wants the ~1s floor attacked |
| Merge + push + tag + ITERATIONS.md ledger line | Owner-gated (LAW 0) |
| Twilio lane :8026 test | Blocked on owner Twilio creds/session (separate) |
