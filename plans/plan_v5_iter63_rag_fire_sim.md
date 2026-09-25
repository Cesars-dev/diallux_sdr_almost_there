# PLAN — iter63: `--rag-fire-sim` — chat-surface lane-fire simulation (harness-only)

## Meta
- Date: 2026-09-21
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — add a `--rag-fire-sim` flag to the chat harness that fires the two RAG lanes (lane A / lane B) the same way the mic session layer does, so chat batteries can test that retrieval fires at the proper time, on the proper state, with the proper query, and that the agent USES the retrieved knowledge. Engine code is NOT touched. Mic/voice behavior is NOT touched.
- Status: **PLAN ONLY (not started — awaits approval)**

## ⛔ ABSOLUTE NO-TOUCH — MIC/VOICE (read this twice)

**This iteration changes ZERO mic/voice anything.** The mic path must be byte-identical before and after iter63:

| NEVER touch in iter63 | Why |
|---|---|
| `/tmp/opencode/wt-iter62/engine/diallux/media/session.py` | the live session layer — lane firing lives here already; the sim MIRRORS it, never edits it |
| `/tmp/opencode/wt-iter62/engine/diallux/media/deepgram_stt.py` | STT/EagerEOT timing is owner-calibrated |
| `/tmp/opencode/wt-iter62/engine/diallux/media/prewarm.py` | iter61 territory |
| `/tmp/opencode/wt-iter62/engine/diallux/graph/builder.py` + `tools.py` | the iter62 brain — the sim DRIVES it via existing public methods (`spawn_live_retrieve`, the graph), zero edits |
| prompts (incl. `contact_details.md`), `.env`, RAG settings (`rag_filter_score=0.24`, `rag_min_query_chars=12`, `rag_live_await_ms=60`) | owner-calibrated |
| `:8021` server (pid in `/tmp/opencode/voice_8021.pid`, REAL pid 3834955, serving wt-iter62) | iter62 MIC GATE surface — no restart for iter63; the server never imports `tests/` so iter63 cannot affect it even in principle |
| `:8020` (wt-iter58 production test surface), ports 8000-8003 | live infra, forever off-limits from this repo |
| `engine/iter62-lane-restore` branch content | iter63 only READS it as its base |

The ONLY files iter63 may create/modify are listed in the File Map below — all under `tests/`.

## Compaction Context (session 2026-09-21 — pin, do not re-derive)

- **Where we are:** iter62 (lane restore) is executed on branch `engine/iter62-lane-restore` (worktree `/tmp/opencode/wt-iter62`, base `6c986e8`): E1-E11 applied, R1/R2 rewritten, 9-pin file written, suite **422 passed 0 failed**, `:8021` restarted from wt-iter62 (REAL pid 3834955, health + preflight GREEN), Telegram sent — the owner's mic re-test call is PENDING (blocks iter62 T7/T8: ledger flips, fix report, commit, ASK). iter62 is NOT yet committed or merged.
- **Why iter63 exists:** the owner asked to test the RAG fix's LOGIC via chat ("test that the rag fires at the proper time with the proper semantic response on the proper state — that the agent is working as designed and smart enough"), explicitly not caring about real-voice timing right now. On chat, `tests/llm2llm/harness.py` drives `graph.astream()` directly with NO media session → no flux Update / EagerEOT events → lanes never fire → rag spans show the fail-clean shape (`degraded=true, zero_hit=true`) by design. The owner previously deferred chat firing; he has NOW authorized it as iter63, harness-only.
- **Why the sim is honest (the key insight):** before iter62, a chat sim would have been fiction — the consume re-extracted the query from history, not from what was fired. iter62's E1/E2 made `state["user_text"]` the single source of truth (ingest keeps the turn transcript; `state_node` consumes it). So a sim that fires lane B with the caller utterance tests the EXACT consume logic the mic runs. No parallel code path: the sim calls the SAME `runtime.spawn_live_retrieve(state, dvs, transcript, lane=...)` that `CallSession._fire_live_retrieve` (`diallux/media/session.py:410-425`) calls.
- **Session fire mechanics (what the sim mirrors, never edits):** lane A fires ONCE per turn at the first flux Update with an EMPTY utterance (refer-tags + dv values; utterance-independent); lane B fires at EagerEOT/EOT with the turn transcript as a single query. Tasks keyed `<state>|laneA` / `<state>|laneB`; every fire bumps `_live_task_seq`. Proven by test_iter59/test_iter60 pins.
- **The one honest fake:** a configurable "speech tail" sleep (`--fire-sim-tail-ms`, default 500) between the lane-B fire and the graph turn — the stand-in for the caller still speaking when EagerEOT fires. It lets the arctic embed (~90-190 ms) land inside the window, which is the mechanism under test. With tail=0 (or `rag_live_await_ms=5` in pins) the consume misses → `degraded=true, zero_hit=true` — the fail-clean semantics visible on chat, documented as expected, NOT a regression.
- **What the sim will NOT prove:** barge-in/eager-transcript divergence timing and real e2e latency (p50). Mic-only. The iter62 MIC GATE remains the live verification.
- **Stacking:** iter63 branches from the head of `engine/iter62-lane-restore` AFTER iter62's commit (T8). If the owner later rejects iter62 content, iter63 inherits and re-bases. Merge of either branch = owner STOP POINT (LAW 0).
- **Persona naming trap:** the "(BOOK) Mike Rourke — plumber, wife-runs-office + price push" and "(GK) Priya — price-obsessed shopper" personas are the price-objection batteries for the "smart enough" check. `--personas` matches by name substring (proven: `--personas Maria` in AGENTS.md).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| iter63 modifies ONLY `tests/llm2llm/harness.py` + new test files; ZERO engine/mic/voice changes | owner: "if we do iter63 we only modify the chat?" — YES, confirmed; mic/voice settings untouchable (see NO-TOUCH table) |
| The sim fires via the EXISTING `runtime.spawn_live_retrieve(...)` with the SAME args/keys/seq as `CallSession._fire_live_retrieve` — no new fire code path | a parallel path would test a fiction; the session method is the contract |
| Branch `engine/iter63-rag-fire-sim` cut from the head of `engine/iter62-lane-restore` (stacked, after iter62's commit) | the sim depends on iter62 E1/E2 (transcript single-source); branching from `6c986e8` would test the OLD broken consume |
| Fire-then-sleep(tail)-then-astream, with the tail BEFORE the latency clock starts (`agent_ms` excludes the tail) | mirrors mic semantics: retrieval runs during the caller's remaining speech; mic latency excludes caller speech time |
| The tail default 500 ms, flag-settable (`--fire-sim-tail-ms`); NOT a settings change | honest speech-window stand-in without touching owner-calibrated config |
| Fail-clean spans on short windows are EXPECTED on chat (`degraded=true, zero_hit=true`) — documented, not a regression | same owner-accepted semantics as iter62 chat `--rag` |
| NO restart of `:8021` for iter63; it keeps serving wt-iter62 for the iter62 MIC GATE | server never imports `tests/`; zero behavioral coupling |
| Suite: baseline = iter62 head (**422 passed**) + 3 new pins = **425 passed, 0 failed** gate | per-iteration pin convention; count stated up front |
| No merges, no tags, commits only on `engine/iter63-rag-fire-sim` after suite green; ASK owner at the end (LAW 0) | standing law |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Base commit sha for the branch cut = iter62's T8 commit | the iter62 session (T8 commits on `engine/iter62-lane-restore`; read `git -C /tmp/opencode/wt-iter62 log --oneline -1` after that commit lands) |
| Owner go for the chat battery run (spends OPENAI_API_KEY tokens) | the ASK at the end of the pin work |
| GATE 0 — owner approval of THIS plan | owner says "go" |

## Environment & Dependencies
- Project root: `/home/julio/projects/clean_diallux_SDR` (docs/plans/research on `main`; engine on `engine/iterNN-*` worktrees).
- Stacked base: head of `engine/iter62-lane-restore` (iter62 commit sha — see BLOCKED). Worktree: `/tmp/opencode/wt-iter63`, branch `engine/iter63-rag-fire-sim`.
- Venv: symlink `/home/julio/projects/clean_diallux_SDR/engine/.venv` into `/tmp/opencode/wt-iter63/engine/.venv` (copy-mirror venv — pip via `<venv>/bin/python -m pip` ONLY).
- `.env`: copy from `/tmp/opencode/wt-iter62/engine/.env` (`OPENAI_API_KEY`, `DATABASE_URL` → localhost:5434/diallux, `RAG_TABLE_NAME=kb_chunks_v2`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.7`, `VOICE_TEST_TOKEN`, `LANGFUSE_*`). Never committed.
- Suite command: `cd /tmp/opencode/wt-iter63/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3` → baseline gate **422 passed** (iter62 head) BEFORE iter63 edits; final gate **425 passed, 0 failed** AFTER the 3 new pins.
- Chat battery commands (from `/tmp/opencode/wt-iter63/engine`, `.env` sourced): `.venv/bin/python tests/llm2llm/harness.py --personas happy --rag --rag-fire-sim --langfuse --max-turns 48` (smoke), then `--personas "Mike Rourke"` and `--personas "Priya"` (price-objection batteries).
- Test server `:8021` (pid 3834955, serving wt-iter62) is NOT iter63's surface — read-only. Health: `curl -sf http://127.0.0.1:8021/health`.
- Call ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; import chat runs via `scripts/live_sql.py import --window "HH:MM-HH:MM" --run chat-iter63-sim --branch engine/iter63-rag-fire-sim --commit <sha>` from the wt-iter63 worktree with `.env` sourced. NO `sqlite3` CLI — `<venv>/bin/python -c "import sqlite3; ..."`.
- Langfuse UI `http://localhost:3001`; `scripts/lf.py`; harness traces with `--langfuse`.
- Telegram HITL: `cd /tmp/opencode/wt-iter63/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<message>"`.
- Prior-iteration references (read-only): iter62 plan `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter62_lane_restore_exec.md`; master plan `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/04_master_plan.md`; iter61 deep dive `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter61-prewarm-staleness/03_kb_retrieval_deep_dive.md` §7.

## Architecture (one block diagram)
```
iter63 EXEC (branch engine/iter63-rag-fire-sim, stacked on engine/iter62-lane-restore)
  GATE 0 owner approves THIS plan            ← CURRENT
  T1 worktree wt-iter63 + baseline suite 422 (iter62 head)
  T2 harness: --rag-fire-sim + --fire-sim-tail-ms in GraphAgent.send (ONLY code change)
  T3 3 hermetic pins (tests/test_iter63_rag_fire_sim.py)
  T4 suite gate 425 passed, 0 failed
  T5 chat battery: happy smoke → Mike Rourke + Priya (price objections), --rag --langfuse
  T6 ledger import (run chat-iter63-sim) + span analysis (state/query/zero_hit/pinned)
  T7 fix/iteration report + branch commit + Telegram ASK
  STOP — merge = owner decision (LAW 0)
  (NO :8021 restart anywhere in this plan — mic/voice untouched)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter63/engine/tests/llm2llm/harness.py` | T2: additive `--rag-fire-sim` + `--fire-sim-tail-ms` flags; in `GraphAgent.send()` (line ~180), when the flag is on: BEFORE `t0 = time.perf_counter()`, snapshot state (state_name, dvs) via `await self.rt.graph.aget_state(self.config)`, fire `self.rt.spawn_live_retrieve(state_name, dvs, "", lane="laneA")` + `self.rt.spawn_live_retrieve(state_name, dvs, text, lane="laneB")` (the exact `CallSession._fire_live_retrieve` contract), `await asyncio.sleep(tail_ms / 1000.0)`, then astream as today. Flag-off path = byte-identical to today. | E |
| `/tmp/opencode/wt-iter63/engine/tests/test_iter63_rag_fire_sim.py` | 3 hermetic pins (spec in §Tasks T3) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter63-rag-fire-sim/01_iteration_report.md` | the deliverable: per-pin evidence + battery span table + "smart enough" read | N |
| UNTOUCHED FOREVER (mic/voice): `diallux/media/session.py`, `diallux/media/deepgram_stt.py`, `diallux/media/prewarm.py`, `diallux/graph/builder.py`, `diallux/graph/tools.py`, all prompts, `.env`, `:8021`, `:8020`, `:8000-8003` | — | — |

## Deploy Rules
- NOTHING deploys. `:8021` keeps serving wt-iter62 (pid 3834955) — the iter62 MIC GATE surface. NO restart for iter63 (harness is test-only; the server never imports `tests/`). `:8020` and ports 8000-8003 NEVER touched. `.env` never committed; run `scripts/keyhound` before any push. Commits only on `engine/iter63-rag-fire-sim` after the suite gate is green. Merge = owner decision at the STOP POINT.
- Cancel any Cal.com test bookings (event 3801235 is REAL) if the battery creates one (mock slots default — it should not).

## Tasks (in order)

### T1 — Worktree + baseline (BLOCKED until iter62 T8 commit lands)
Goal: the exact stacked tree to build on; suite green before touching anything.
Files: none.
Commands:
```bash
cd /home/julio/projects/clean_diallux_SDR && git worktree add -b engine/iter63-rag-fire-sim /tmp/opencode/wt-iter63 <iter62-commit-sha>
ln -sfn /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter63/engine/.venv
cp -p /tmp/opencode/wt-iter62/engine/.env /tmp/opencode/wt-iter63/engine/.env
cd /tmp/opencode/wt-iter63/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
Dependencies: iter62 T8 (commit on `engine/iter62-lane-restore`).
Verification: `git -C /tmp/opencode/wt-iter63 log --oneline -1` = the iter62 commit sha; suite = **422 passed** (any other count → STOP and reconcile).

### T2 — Harness flag (THE one code change)
Goal: `--rag-fire-sim` fires both lanes exactly like the session, before each graph turn; flag-off path byte-identical.
Files: `/tmp/opencode/wt-iter63/engine/tests/llm2llm/harness.py`.
Commands: edit `GraphAgent.send()` per the File Map spec (fire laneA `""` + laneB `<caller text>`, sleep tail, then astream; all inside `if self.rag_fire_sim:`). Add the two argparse flags in `main()` (line ~564) and thread them into the GraphAgent ctor (new kwarg `rag_fire_sim: bool = False, fire_sim_tail_ms: int = 500`). `py_compile` after.
Dependencies: T1.
Verification: `py_compile` clean; `--offline` smoke passes; `git diff` shows ONLY additive lines in harness.py; with the flag OFF, a `--personas happy --max-turns 3` run behaves byte-identically to the iter62-branch harness (same turns, same tools).

### T3 — 3 hermetic pins
Goal: prove the sim fires correctly and the consume semantics are visible on chat.
Files: `/tmp/opencode/wt-iter63/engine/tests/test_iter63_rag_fire_sim.py` (new; crib `_t4_settings`/`LanesStore`/`_chunk`/`mock_client` from `tests/test_iter49_rag_parity.py`, `_run` from test_iter59; `GraphAgent` accepts `tracer=`, `kb_store=`, `llm=` directly).
Pins:
1. **`test_fire_sim_spawns_both_lanes_once_per_turn`** — GraphAgent(rag_fire_sim=True, kb_store=LanesStore) driven one turn against a FakeLLM speech round → `store.lane_calls` has exactly 2 retrieve_lanes calls: first the laneA plan (refer-tag query, utterance-independent), second the laneB plan whose query IS the caller utterance. NO third fire (no respawn — iter62 E4).
2. **`test_fire_sim_landed_span_semantics`** — spy tracer + LanesStore with chunks, tail ≥ embed → the turn's `rag` span output has `state` == the turn's state, `query` containing the caller utterance, `zero_hit is False`, `degraded is False`.
3. **`test_fire_sim_short_window_fails_clean`** — LanesStore(delay=2.0), `rag_live_await_ms=5`, tail=0 → the turn's `rag` span has `degraded is True` and `zero_hit is True` (fail-clean visible on chat; NOT a regression).
Dependencies: T2.
Verification: the new file has exactly the 3 named test functions; zero other test files touched.

### T4 — Suite gate
Goal: 425 passed, 0 failed.
Files: none.
Commands: `cd /tmp/opencode/wt-iter63/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3`.
Dependencies: T3.
Verification: **425 passed, 0 failed**. If an existing test fails: STOP, diagnose, fix forward or amend THIS plan — never weaken a pin.

### T5 — Chat battery (owner go required — spends tokens)
Goal: the owner's two questions answered: (1) agent working as designed — lanes fire on the right state at the right time; (2) smart enough — the agent USES the retrieved knowledge against price objections.
Files: none.
Commands (from `/tmp/opencode/wt-iter63/engine`, `.env` sourced):
```bash
.venv/bin/python tests/llm2llm/harness.py --personas happy --rag --rag-fire-sim --langfuse --max-turns 48
.venv/bin/python tests/llm2llm/harness.py --personas "Mike Rourke" --rag --rag-fire-sim --langfuse --max-turns 48
.venv/bin/python tests/llm2llm/harness.py --personas "Priya" --rag --rag-fire-sim --langfuse --max-turns 48
```
Dependencies: T4.
Verification: all three runs complete without crash; per-persona JSON/verbose output captured for the report (harness prints per-turn caller/agent/tools/state).

### T6 — Ledger + span analysis
Goal: evidence survives the session; the RAG-logic verdict is queryable.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`.
Commands: `scripts/live_sql.py import --window "HH:MM-HH:MM" --run chat-iter63-sim --branch engine/iter63-rag-fire-sim --commit <sha>` from the wt-iter63 worktree with `.env` sourced; read back via venv python + sqlite3 module.
Dependencies: T5.
Verification: the run + calls + rag rows read back by SQL; span checks: objection-turn `query` NON-EMPTY (contains the utterance), `zero_hit=False` where the KB has content, `pinned` non-empty once industry known, short-window turns `degraded=true` as expected.

### T7 — Report + commit + ASK
Goal: close the loop; owner decision point.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter63-rag-fire-sim/01_iteration_report.md` (new).
Commands:
```bash
cd /tmp/opencode/wt-iter63 && git add engine/tests && git commit -m "iter63: --rag-fire-sim chat lane-fire sim (harness-only; mic/voice untouched)"
```
Then Telegram ASK (hitl command in Environment): suite count, battery span verdict (state/query/zero_hit/pinned table), ledger run imported, report path — merge decision = owner (STOP POINT).
Dependencies: T6.
Verification: suite green; `git -C /tmp/opencode/wt-iter63 status` clean after commit; report on disk; ping sent. **STOP — merge = owner.**

## Validation Plan (end-to-end)
1. THIS plan approved before any code; all work on `/tmp/opencode/wt-iter63` @ branch `engine/iter63-rag-fire-sim` stacked on the iter62 commit.
2. `tests/test_iter63_rag_fire_sim.py` exists with exactly the 3 named pins; suite = **425 passed, 0 failed**.
3. ZERO diff outside `tests/` (`git -C /tmp/opencode/wt-iter63 diff --stat` vs the iter62 commit shows only `tests/llm2llm/harness.py` + the new test file). Mic/voice: `:8021` pid unchanged (3834955), health green, ZERO restarts performed.
4. Battery evidence imported (`chat-iter63-sim`); objection-turn span query non-empty; landed turns `zero_hit=False`; fail-clean turns visible as `degraded=true, zero_hit=true`.
5. Report on disk; owner ASK sent.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| iter62 T7/T8 (ledger flips, fix report, commit, ASK) | pending the owner's MIC CALL — separate session flow, iter62 plan governs |
| Making the mic path consume the sim (or vice versa) | pointless — the sim DRIVES the existing session-shaped fire; nothing to share |
| Barge-in / eager-divergence / real-latency verification | mic-only, owner knows; iter62 MIC GATE covers it |
| Chat lane firing becoming DEFAULT (flag off) | owner decision after seeing the battery evidence |
| RAG settings tuning (0.24 / 12 / 60 ms) | owner-calibrated, no evidence to change |
| Merges/tags/`git-tree.sh` for iter62 or iter63 | LAW 0 — owner STOP POINT |
