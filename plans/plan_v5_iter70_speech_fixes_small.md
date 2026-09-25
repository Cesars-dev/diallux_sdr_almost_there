# plan_v5_iter70_speech_fixes_small — small fixes on clean main (no machinery), owner-ear first

## Meta
- Date: 2026-09-23
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: re-fix the 3 speech-flow defects SMALL on clean main code (`8e06fe9` state) — silence re-prompt, merged-turn trim, transition-ack beat — plus the observability logging; NO dedupe machinery, NO branch cherry-picks, env knobs already carried.
- Status: PLAN ONLY (not started — T1 is the owner HITL ASK)
- Branch: `engine/iter70-speech-fixes` cut from main tip at T0 (docs commits `d74b63f`/`586add3` ride along; code base = `8e06fe9`)

## Compaction Context
Dialux SDR v5 engine (LangGraph voice pipeline) in `/home/julio/projects/clean_diallux_SDR`. 2026-09-23 the owner ear-tested iter68 ("speech flow") and iter68-lite on lane :8024; verdict = **total failure, branches PARKED** — the fixes were overengineered and caused more problems than they solved. The lane was rolled back to the proven config and is LIVE on it right now (verified 11:43):
- **:8024 serving CLEAN MAIN @ `8e06fe9` code** (the "out of this world" Cartesia voice). Main checkout clean (no uncommitted code). Verified in journal: `cartesia connected (model=sonic-3.6-2026-08-27)`, `/health` = gpt-5.4 + cartesia pin.
- **.env knobs (gitignored, NO code):** `TTS_PROVIDER=cartesia`, `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` (NEVER remove), `TTS_GATE_FAST_FIRST_FLUSH=false` (the char-cap cutter off — owner's winner), `TTS_DEDUPE_SEMANTIC=false` (kills cross-call muted re-asks — zero code, pydantic env override of main `config.py:309` `tts_dedupe_semantic=True`). Same-turn dup-sentence guard (`tts_dedupe_sentences=True` default) STAYS ON — owner confirmed it must live. Sanitizer (`tts_sanitize_tokens=True` default) STAYS — strips `{ } [ ]` code/bracket artifacts, 0 false drops ever logged.
- **WHAT WAS WORKING (the good state):** voice = Cartesia sonic-3.6-2026-08-27 ("out of this world"), battery 3/3 BOOK on every clean-main run, sanitizer catching real artifacts, fast-flush off, same-turn dup guard, and ONE iter68 win worth keeping: **transition acks carry the next question (no more silent acks)** — owner called it "a huge win".
- **POLLUTED BRANCHES (PARKED — total-failure owner verdict; do NOT merge, do NOT cherry-pick; reference for READING the diffs only):** `engine/iter68-speech-flow` @ `cc34343` (4 commits: T1 observability `c6159ce`, T2 transition beat `22e6f88`, T3 cos-gate machinery + silence re-ask `c3022c3`, T4 chain-link buffering `cc34343` — T4 created the Susan contact_details first-name loop) and `engine/iter68-speech-lite` @ `95f7ace` (cut from `22e6f88`; added semantic-off `24d6ffa`, silence re-ask port `651e567`, pin flips, STT zombie watchdog `95f7ace`). The overengineering that failed: scripted-question cos≥0.85 registry, semantic exempt-state tuples, 2-strike ladder code, chain-link TTS buffering, `_SILENT_ROUND_RE`. Root cause of the disaster: all the "cleaning/cutting" machinery muted or truncated real speech (semantic cut scripted re-asks at cos 0.99-1.0 live; fast-flush chopped sentences at 12 chars; chain-link swallowed questions).
- **REFERENCE PLANS (committed to main, good — read for context):** `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter68_speech_flow.md` (the good v1 plan with reproduced forensics), `plan_v5_iter68_speech_flow_v2.md`, `plan_v5_iter68_speech_flow_v3_battery_voice.md` (battery/deploy/ledger mechanics — reusable verbatim). Post-mortem rows PT-68..PT-73 in `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` (commit `d74b63f`) hold the owner verdict + law (PT-73: smallest change that fixes it; >~50 lines needs owner sign-off; prompt-first over code-first; env-knob-first over branch-first).
- **THE 3 SMALL FIXES this plan addresses (all diagnosed with live evidence):**
  1. **PT-68 silence re-prompt:** STT sometimes never fires EOT on a caller answer → agent waits silently (live: micbridge-adaa30aeb282 t13 = 26s dead air; micbridge-faeef9769187 = adopted Deepgram socket zombie, 39s audio sent, zero messages, owner heard NOTHING). Fix: one-shot pause timer that re-prompts the agent with a REPHRASED ask.
  2. **PT-70 silent acks (the huge win, keep):** transition acks must carry the next question in the same spoken turn (iter68 T2 `22e6f88` proved it; re-implement small, don't grab).
  3. **PT-69 merged turns:** a round that ends with "?" must yield to the caller; >2 questions in one turn → trim. Prompt-first; a ≤10-line builder trim hook only if prompts alone fail.
- **Tools that work on main already:** `scripts/speech_replay.py` SDK (replays a Langfuse trace through the filter chain, reads the SAME env knobs as the engine — stays truthful automatically), `scripts/lf.py` traces/show/gens, `scripts/live_sql.py` (MAIN repo copy — accepts micbridge-* since `537e53c`; the worktree copy is STALE for mic imports), `scripts/call.py` sop/turns/lat, `scripts/mic_events.py`.
- **Never touched:** `:8021` (pid 3834955), `:8022` (pid 884638), `:8000-8003` services, `engine/diallux/media/prewarm.py`, `elevenlabs_tts.py`, `tts_factory.py`, live agent IDs, Cal.com event 3801235 (REAL — cancel test bookings), `TTS_DEDUPE_SENTENCES` (stays default-on).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| ALL iter68/68-lite branches PARKED, not merged | Owner: "total failure… we don't grab spaghetti from polluted branches; we fix again but we fix problems we can handle" (PT-73 law) |
| Twilio branch `0394a3b` stays parked-but-merge-ready | Verified collision-free (git merge-tree exit 0 both orders) — merge is owner-gated, separate from this plan |
| Base = main @ `8e06fe9` code state + .env knobs | The "out of this world" voice config; docs commits on top are LAW 0-legal |
| `TTS_DEDUPE_SEMANTIC=false` env (already set) kills muted re-asks with zero code | pydantic env overrides main default True; verified live 11:43 restart |
| Same-turn dup-sentence guard (`tts_dedupe_sentences=True`) STAYS | Owner: "only the dup sentence on exact turn must live… that's already on main" |
| Sanitizer STAYS ON | 0 false drops in every audit; strips genuine `{ } [ ]` leaks (PT-61) |
| Silent-ack fix = re-implement SMALL (transition beat + turn_asked) | Owner: "the silent acks… that was a huge win, but we iterate again" — the ONE piece worth keeping (PT-70) |
| Redundancy = PROMPT-level, not code | Owner: "if agent is redundant we can just prompt it, we are overengineering" |
| Branch name: `engine/iter70-speech-fixes`, cut from main tip | LAW 0 v2.1 "branch" trigger; one variable per iteration |
| Battery = happy3 first; merge = owner only (LAW 0) | AGENTS.md iteration loop |
| HITL FIRST | Owner: "starting from, HITL" — T1 of this plan is the owner ASK |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner GO on this plan + scope pick (T2/T3/T4 order) | Telegram HITL ASK (T1 of this plan) |
| Ear-test verdicts (owner speaks on the mic) | `https://flores.diallux-ai.site/voice24/mic?k=$VOICE_TEST_TOKEN` (token in `/home/julio/projects/clean_diallux_SDR/engine/.env`) |
| Merge say-so | Telegram ASK at closeout |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv` (3.12.3; pytest 9.1.1; langchain_openai 1.6.0; openai 3.8.0; fastembed local arctic-embed-m at `/home/julio/fastembed/models`)
- Worktree: `git -C /home/julio/projects/clean_diallux_SDR worktree add /tmp/opencode/wt-iter70 engine/iter70-speech-fixes` then `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter70/engine/.venv` + `cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter70/engine/.env`
- Mic lane: systemd `diallux-8024.service` (`~/.config/systemd/user/diallux-8024.service`, `WorkingDirectory=/home/julio/projects/clean_diallux_SDR/engine`), mic page `https://flores.diallux-ai.site/voice24/mic?k=$VOICE_TEST_TOKEN`, logs `journalctl --user -u diallux-8024.service`
- Langfuse: self-hosted `http://localhost:3001` (keys in `.env` `LANGFUSE_*`); traces `chat-iter70-*` (harness) + `micbridge-<sid>` (mic lane)
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` — import via the MAIN-repo SDK `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (worktree copy misses micbridge-*); gates `--a chat-iter65-happy --b chat-iter70-happy`
- Report folder: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter70-speech-fixes/01_report.md` (gitignored)
- Suite expectation on clean main: 476 passed + 1 known env failure `tests/test_tts_providers.py::test_factory_switches_provider` (pre-existing cartesia-vs-EL env pin, owner-confirmed intended)

## Architecture (one block)
```
main @ 8e06fe9 (+ .env knobs)  ── branch engine/iter70-speech-fixes (worktree /tmp/opencode/wt-iter70)
   ├─ T2: pause re-prompt (one-shot timer in session.py, ~40 lines, knob silence_reask— RENAMED pause_reask to avoid parked-branch semantics; fires ≤1x/turn, cancelled on speech)
   ├─ T3: transition beat (builder.py transition ack one-trips when turn_asked + prompt directives — the PT-70 win, re-written small)
   ├─ T4: merged-turn trim (round ends on "?" → yield; >2 questions in a turn → keep first+last, trim middle; ≤10-line hook)
   ├─ T5: speech_filter observability (~10 log.info lines, forensics only)
   └─ deploy 6-8 files → :8024 → owner ear test → battery happy3 → ledger/gates → ASK → (owner) merge
```

## File Map
| File (absolute path) | What changes | New/Edit |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter70_speech_fixes_small.md` | THIS plan (docs → main) | New |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-68/69/70 statuses update as they land (docs → main) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py` | T2: one-shot pause re-prompt timer (arm after agent turn drained; fire ONE rephrased re-ask turn; cancel on speech; knob `pause_reask_ms=10000` default ON) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py` | T2 knobs: `pause_reask: bool = True`, `pause_reask_ms: int = 10000` | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` | T3 transition beat (one-trip ack+next-question when `turn_asked`) + T4 trim hook (>2 questions/turn → keep first + last) + T5 `_log_filter()` INFO lines | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/state.py` | T3: `turn_asked` flag (post-filter "? heard" truth) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/*.md` + `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json` | T3/T4 wording directives (re-ask vary; one question per turn) — llm.json lockstep byte-parity, refer-count 36 preserved | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter70_*.py` | Pins per task (NEW files, small) | New |
| `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py` | T5: speech_filter regex | Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter70-speech-fixes/01_report.md` | battery + ear-test report (gitignored) | New |

## Deploy Rules
- Lane deploy (copy + restart + verify):
  ```
  cd /tmp/opencode/wt-iter70 && git checkout-index --prefix=/tmp/opencode/iter70_stage/ -af && \
  cp /tmp/opencode/iter70_stage/engine/diallux/graph/builder.py /tmp/opencode/iter70_stage/engine/diallux/config.py /tmp/opencode/iter70_stage/engine/diallux/state.py /home/julio/projects/clean_diallux_SDR/engine/diallux/ 2>/dev/null; \
  cp /tmp/opencode/iter70_stage/engine/diallux/graph/builder.py /home/julio/projects/clean_diallux_SDR/engine/diallux/graph/ && \
  cp /tmp/opencode/iter70_stage/engine/diallux/config.py /tmp/opencode/iter70_stage/engine/diallux/state.py /home/julio/projects/clean_diallux_SDR/engine/diallux/ && \
  cp /tmp/opencode/iter70_stage/engine/diallux/media/session.py /home/julio/projects/clean_diallux_SDR/engine/diallux/media/ && \
  cp /tmp/opencode/iter70_stage/engine/agent/llm.json /home/julio/projects/clean_diallux_SDR/engine/agent/ && \
  cp /tmp/opencode/iter70_stage/engine/diallux/prompts/*.md /home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/ && \
  cp /tmp/opencode/iter70_stage/engine/scripts/mic_events.py /home/julio/projects/clean_diallux_SDR/engine/scripts/ && \
  systemctl --user restart diallux-8024.service && sleep 5 && \
  journalctl --user -u diallux-8024.service -n 10 --no-pager | grep "cartesia connected"
  ```
- Lane RESTORE after every ear test (merge hygiene): `git -C /home/julio/projects/clean_diallux_SDR checkout -- engine/diallux engine/agent/llm.json engine/scripts && systemctl --user restart diallux-8024.service`
- Battery (from the worktree, background-safe — `setsid nohup`, NOT bare nohup: two bare-nohup launches were killed by the shell process-group timeout today):
  ```
  cd /tmp/opencode/wt-iter70/engine && set -a && . ./.env && set +a && date +%H:%M && \
  setsid nohup .venv/bin/python tests/llm2llm/harness.py --personas happy3 --rag --langfuse --max-turns 48 > /tmp/opencode/iter70_battery.log 2>&1 < /dev/null &
  ```
- NEVER touch: `:8021`/`:8022`, `:8000-8003`, `engine/diallux/media/prewarm.py`, `elevenlabs_tts.py`, `tts_factory.py`, live agent IDs, Cal.com event 3801235 bookings (cancel test ones), `CARTESIA_MODEL_ID` in any .env, `TTS_DEDUPE_SENTENCES` (stays default-on)
- Push = owner terminal (agent shell has no creds)

## Tasks (in order)
### T0 — HITL ASK (owner GO) — FIRST ACTION OF THE NEW SESSION
Goal: owner approves scope (all of T2-T4, or a subset) + confirms the env-knob state carried from today.
Commands: `cd /home/julio/projects/clean_diallux_SDR/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "iter70 small-fixes plan ready: (1) 10s pause re-prompt (2) silent-ack transition beat (3) merged-turn trim. GO?"`
Verification: owner reply recorded in the report; no code before GO.
### T1 — Preflight
Goal: confirm the rollback state + branch cut.
Commands: `git -C /home/julio/projects/clean_diallux_SDR status --short -- engine/` (expect clean) · `git -C /home/julio/projects/clean_diallux_SDR worktree add /tmp/opencode/wt-iter70 -b engine/iter70-speech-fixes main` · venv symlink + .env copy · `grep -nE "TTS_DEDUPE_SEMANTIC|CARTESIA_MODEL_ID" /tmp/opencode/wt-iter70/engine/.env` (expect SEMANTIC=false, pin present)
Verification: `git -C /tmp/opencode/wt-iter70 log --oneline -1` = main tip; suite subset green (`cd /tmp/opencode/wt-iter70/engine && .venv/bin/python -m pytest tests/llm2llm/test_harness_units.py tests/test_iter31_c3_prefix.py tests/test_iter40_spike_readback.py tests/test_iter44_cache_floor.py tests/test_iter46_latency_floor.py -q -p no:warnings` — 0 fail)
### T2 — Pause re-prompt (PT-68) — ONE commit
Goal: caller silent ~10s after agent question → agent speaks a REPHRASED re-ask once; never loops; cancelled instantly on speech.
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py`, 1 pin file.
Mechanics: one-shot asyncio timer armed after each agent turn drains (NOT on start), fired into `_run_turn("", extra_payload={"pause_reask": True})`, `patch["pause_reask"]` rides the turn (no empty user message), directive rides the post-history delta: "the caller has gone quiet — re-ask ONCE, shorter, differently worded, then stop". Disarmed by `_on_start_of_turn` speech + never re-arms on its own turn. Knobs `pause_reask=True`, `pause_reask_ms=10000` (owner's "~10s" number).
Size law: ≤60 lines total; if the diff grows past that, STOP and ASK.
Verification: pins; live mic — answer a question, go silent ~11s, agent re-asks once rephrased; journal `pause re-ask firing (armed at turn N)`; NO loop (stays silent after the single re-ask until caller speaks).
### T3 — Transition beat / silent acks (PT-70) — ONE commit
Goal: every `transition_to_X` ack round ends with the destination's next question (no flat ack → dead air).
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/state.py` (`turn_asked` post-filter flag), prompt directives in Intake/Discovery/Closer/Offer `.md` + `agent/llm.json` (byte-parity mirror, refer=36).
Reference ONLY (read, don't cherry-pick): `git -C /home/julio/projects/clean_diallux_SDR show 22e6f88 -- engine/diallux/graph/builder.py engine/diallux/state.py`.
Verification: live mic — after each state transition the next question arrives in the SAME spoken turn; pins green.
### T4 — Merged-turn trim (PT-69) — ONE commit, prompt-first
Goal: one question per turn; >2 questions in one turn → keep first + last, trim the middle; a round ending in "?" always yields.
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` (≤10-line hook at the round boundary), prompts one-question directives.
Verification: pins; live mic — no back-to-back double questions; battery transcripts show ≤2 questions/turn.
### T5 — Observability lines (T1 reborn, tiny)
Goal: every filter drop logs `speech_filter stage=… sent=… state=… turn=…` at INFO (forensics only — zero behavior change).
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py`, 1 pin file.
Verification: a scripted FakeLLM round with an artifact logs the line; `scripts/speech_replay.py` output matches journal lines on a replay.
### T6 — Battery + lane deploy + ear test
Commands: the battery block in Deploy Rules (`--personas happy3`), then the lane-deploy block, then owner ear test (the 3 fixes audible: pause re-prompt at ~10s, transition acks carry next question, ≤2 questions/turn; voice UNCHANGED — cartesia pin).
Verification: 3/3 BOOK; `python3 /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db gates --a chat-iter65-happy --b chat-iter70-happy` green on G1/G2/G4; import via the MAIN SDK; report written to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter70-speech-fixes/01_report.md`; bookings cancelled (mock slots only today, but verify).
### T7 — Closeout: main checkout restored + HITL ASK
Commands: the lane-RESTORE block; `hitl_ping.py` the merge ASK (LAW 0 — merge = owner only).
Verification: main checkout clean; ASK sent.

## Validation Plan (end-to-end)
1. T1 scope ASK answered by owner before any code.
2. Each task = one small commit, suite subset green, ≤60-line diffs (PT-73 law).
3. Battery happy3 3/3 BOOK on branch code; ledger imported via MAIN SDK; gates by SQL.
4. Lane :8024 serves the branch for the ear test; cartesia pin verified in journal; restored after.
5. Owner ear verdict = the ONLY gate for merge; merge = owner only.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Twilio merge (iter67) + lane :8026 test | Owner-gated separately; collision-free verified |
| STT zombie-socket adoption health-check (prewarm validation) | Infra bug PT-72 — separate small ride after this one proves out |
| Mic WS 11-12s open on page load | PT-72 — browser-bridge audit, separate |
| Industry-vertical KB pin (52% zero-chunk coverage) | Owner-gated separate decision (iter52 metadata lane) |
| Turn-1 TTFT floor | Diagnosis only; separate branch if owner wants the ~1s floor attacked |
| Cherry-picking anything from `engine/iter68-*` | PT-73 law — parked branches are reference-only |
