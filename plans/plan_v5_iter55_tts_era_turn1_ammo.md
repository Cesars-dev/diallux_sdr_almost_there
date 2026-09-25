# PLAN — v5 iter55: production-era truth + turn-1 "ammo locked" landing (live-first, not lab-first)

## Meta
- Date: 2026-09-17 (authored from the iter54 assessment session)
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: prove which latency era is actually serving production, instrument the warm path (the number nobody has ever measured), then land the turn-1 "ammo locked" design (full preloaded first round + "one moment, taking notes" filler on transitions) under the owner gates: **first 3-4 interactions ≤900 ms TTFT; worst case TTFT ≤1,100 ms / user-hears ≤1,400 ms**.
- Status: **PLAN ONLY (not started — awaits owner go)**
- Branch: NEW `engine/iter55-tts-era-turn1-ammo` cut from `engine/iter52-industry-pin` @ HEAD `054af7b` (amended iter52; ledger runs pinned `a36bdd7` = same engine code, personas.py +33 only). Zero changes to main. No merges without owner say-so (LAW 0 v3).
- This plan **SUPERSEDES** `plans/plan_v5_iter54_turn1_cache_landing.md` (absorbs the riddle + its T0/T1, replaces the O1-O5 menu with the owner's converged design and new gates). The iter54 "owner picks ONE" ASK is retired.

### Post-plan-session addendum (same day — what happened after this plan was written)
- `plans/NEXT_STEPS.md` rewritten: iter55 = NOW #1; stale items struck (merge iter29-31 stack → already in main via MVP merge `4559a33`; "cut iter32" → superseded); **HITL section added** (real-path test level, filler copy, EOT wait ceiling, warm_rag keep-drop-reorder, cutover authorization); **Services cutover promoted to top NEXT item**; NAMING CONVENTION note added (`iter<N>` = code iteration; a plan owns no iter number; iter43 = real branch ABANDONED `iter43-failed`, iter44 = real branch `engine/iter44-cache-floor`, `mvp-finally` deliberately not iterNN-numbered; formal note rides `engine/ITERATIONS.md` at next branch closeout).
- `plans/PENDING_TASKS.md` PT-51 flipped to SUPERSEDED (menu collapsed: O3/O4 dead, O1 gated on T0, O2 → "taking notes" fallback default OFF, O5 free win).
- iter55 plan amended: owner directive **NO KB loads at/before call start** pinned as Resolved Decision; `warm_rag`/KB-resolve = REMOVAL/REORDER candidates behind a HITL row (physics: warm_rag is async but feeds the turn-2 first heavy round's lane-B embed — dropping it degrades that round's RAG to zero fresh chunks; decide AFTER the T1 greeting-span numbers).

## SESSION START PROTOCOL (fresh agent — execute in order, no memory assumed)
1. Read this plan fully. Read `AGENTS.md` (repo law) + `engine/ITERATIONS.md` §26 tail (the last ledger line) for context.
2. Cut the worktree:
   ```bash
   git -C /tmp/opencode worktree add /tmp/opencode/wt-iter55 -b engine/iter55-tts-era-turn1-ammo engine/iter52-industry-pin
   ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter55/engine/.venv
   cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter55/engine/.env
   ```
   Sanity: `git -C /tmp/opencode/wt-iter55 log --oneline -1` must print `054af7b` (amended iter52; engine code identical to ledger-pinned `a36bdd7`).
3. Suite check (expect **333 passed**):
   ```bash
   cd /tmp/opencode/wt-iter55/engine && .venv/bin/python -m pytest tests -o addopts="" -q
   ```
4. Langfuse health: `cd /tmp/opencode/wt-iter55/engine && .venv/bin/python scripts/lf.py health`.
5. Read-only first: T0 (spans) → T1 (measurement) — NO behavior flag before T0+T1 land in the report.

### Probe mechanics (pinned facts)
- `Settings` = pydantic BaseSettings, `env_file=".env"`, NO env prefix → knob env names are the field names UPPER_SNAKE: `FIRST_TURN_LITE`, `PREWARM_MAX_COMPLETION_TOKENS`, `STATE_ENTRY_LITE`, `RAG_PIN_INDUSTRY`, `PREWARM_ENTRY_WAIT_EOT_MS`. Shell-export BEATS the `.env` file (pydantic precedence) → probes use `VAR=value` prefixes on the command line; revert = unset (defaults live in `config.py`: first_turn_lite=True, prewarm_max_completion_tokens=64, state_entry_lite=True, rag_pin_industry=True, prewarm_entry_wait_eot_ms=500).
- The repo `.env` carries NONE of these knobs today (verified) — every probe is env-prefix + unset = exact rollback.
- **Cold-probe discipline**: a "true cold" probe requires ≥3.5 h provider idle (residue TTL proven ≥43 min, dead by 3.5 h — battery-iter52 call-1). Run letters: first probe `cold-probe-a`, the ≥3.5 h-later rerun `cold-probe-b`. Do NOT batch cold probes back-to-back.
- Ledger import TRAP: run `scripts/live_sql.py` from `/home/julio/projects/clean_diallux_SDR/engine` (MAIN checkout), never from the worktree (ROOT resolves wrong — hit twice in iter52).
- NO sqlite3 CLI on this box; NO `rg` in bash — `.venv/bin/python -c "import sqlite3…"` and the grep tool.

## Compaction Context (session forensics — pin, do not re-derive)

### The five findings that changed the picture this session
1. **The live :8000 engine runs iter40-era code.** Verified: process cwd `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5`, `git log` = iter40-era commits; `diallux/config.py` has ZERO occurrences of `prompt_prewarm`/`first_turn_lite`/`state_entry_lite`; `builder.py`/`llm.py` have no `warm_prompt_cache`/`warm()`. **The entire warm→register→ride cache machine (iter43-52) has never served a real call.** Every latency iteration since iter43 was lab-tested only (harness). The live product takes every turn cold, always.
2. **Warm completion time is measured nowhere.** `diallux/graph/llm.py` `warm()` has zero tracing (no span, no log). Langfuse shows only hot-path rounds. Today warm-landing is only *bounded* by round alternation ("missed at N, hit at N+1"). Every wait value (100/500 ms) was a guess. T0 spans are the prerequisite for ANY wait sizing.
3. **The riddle verdict is CONFIRMED at code level** ("working as designed, failing as intended"): provider registers cache on request COMPLETION (~2.5-4 s cold, incl. 64 dead completion tokens), engine windows budgeted at TTFT scale, ack rounds wait **0 ms** by design (`builder.py:1381-1387` — `entry_lite` branch is literal `pass`, "the state-entry ack NEVER awaits"). Alternation signature verified in ledger round sequences.
4. **Owner gates are now HARD:** first 3-4 interactions ≤900 ms TTFT ("first impressions are everything"); worst-case TTFT ≤1,100 ms / user-hears ≤1,400 ms. Turn-3 (2nd substantive answer) ≤900 ms is the design band. Multi-second waits (O3/O4 as menu items) are DEAD under these gates — the option space collapsed to: observability → O5 → O1-style full turn-1 → fallback filler.
5. **Evidence corrections found in the ledger** (`research/surgeon/iter48-rag-truth/ledger.db`): happy-f's "2,688×4/4 @792-810" is residue-confounded (started 27 min after happy-e, same commit + same 4 personas → same-persona full-tree residue; TTL ≥43 min proven by mvp-a→chat-a lite read); happy-f call-1 was 1,143 ms (omitted from the range); happy-f "7/144" counts only real-TTFT zeros (15 NULL-ttft Closing zeros excluded). Cold turn-1 truth: 998/1,047/790/1,221 ms (plumber-a/b, battery-maria, happy-d). Cold turn-2 ack already rides cache: 709-1,067 ms @2,688.

### The measured physics (numbers are the plan's ground truth)
| Quantity | Value | Source |
|---|---|---|
| Cached TTFT (floor) | 679-840 ms (lite 1,664 tok), 700-950 ms (full 2,688 tok) | ledger rounds |
| Cold TTFT | turn-1 lite ~998-1,221 ms; ack cold ~686-846 ms; Discovery cold ~981-1,212 ms | ledger |
| TTFT anatomy | ~650 ms fixed (network+queue+first token) + ~150 ms/1k tok prefill | derived from cached-vs-cold deltas |
| Warm registration cost | ~2.5-4 s cold (TTFT 1.3-2.2 s + 64 dead tokens) | llm.py:234 + plan estimate — **UNMEASURED, T0 fixes this** |
| Lite-head cross-call residue TTL | ≥43 min (mvp-a→chat-a 1,664 hit), gone by 3.5 h | ledger run spacing |
| Greeting audio length | ~4.5-5 s (15 words, "begin" profile speed 1.12 "happy", delivery.py:69-73) + user reply 2-5 s → turn-1 runway ~6-10 s typical; barge-in shrinks to ~3-4.5 s | code + estimate — **uninstrumented, T0 adds the greeting span** |
| Live :8000 e2e (user stopped → caller hears) | mean 2.20 s (47 turns since Sep 9); stt_eot→llm_first: 0/47 ≤800 ms, 19/47 ≤1,200 ms; llm_first→tts_first ≤500 ms on 43/47 (TTS NOT the bottleneck) | Prometheus `diallux_turn_e2e_response_ms` @ :8000/metrics |
| :8005 (iter52 engine, 127.0.0.1 — Twilio can't reach it) | 38 turns, mean 2.75 s (browser-mic tests, small sample) | :8005/metrics |
| KB-resolve block in front of the greeting | bounded 2.0 s, measured 26 ms warm (process singleton `rag.py:528 _SINGLETON`) | session.py:186-190, bridge log Sep 6 |
| warm_rag cost | local arctic-m ~20-35 ms/query after one-time ~833 ms ONNX session load (async during greeting, off the critical path) | rag.py:148-166, config.py:205-206 |

### What the owner wants (direct quotes, standing directives)
- "No matter what run 1 and <800 ms is a problem, we will sound stupid... I am creating a production agent, not a toy, so this whole intro sequence and full ammo locked agent might be the answer."
- "The 1,100 ms is WORST CASE SCENARIO... first 5 turns should be 600-800."
- "We have 2 laggy times: 1. call starts, 2. turn-1 (post-greeting). Those 2 turns buy time to pre-warm."
- "Ship it to TTS without this RAG load nonsense." (Resolved: the greeting is TTS-only; the only RAG-adjacent start cost is the 26 ms singleton resolve — the nonsense fear is unfounded on iter52 code.)
- "Test the TTS engine again to see which era we are testing from." (Answer: TTS/STT layers are identical across eras — Cartesia sonic-3.6 + Deepgram flux, verified in live logs; the ERA GAP is the LLM/cache layer. The test that matters is the era A/B + real-path measurement.)

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| **T0 observability FIRST — warm spans + greeting span — before any behavior change** | warm completion is the load-bearing unknown (registration cost, silent failures, barge-in shrinkage); everything else is guessing without it |
| **Turn-1 direction = full "ammo locked" round (O1 recipe, `FIRST_TURN_LITE=false`), gated on T0** | owner directive; happy-f 4/4 is residue-confounded so T0's cold-probe warm-completion distribution decides; O1 is 1 env var, instantly revertible |
| **O5 (shrink lite warm completion tail) executes regardless — single pure-win variable** | fewer dead ms on the registration path helps turn-1 AND transitions; zero UX cost; the 64-token cap was for FULL-warm rejection safety, the LITE warm carries one noop tool |
| **Fallback = "one moment, taking notes" filler round (O2 shape), ONLY if T0/T5 show residual misses; flag `prefill_fallback` default OFF; never chains** | owner-phrased sales-voice filler beats silence; no-tools ⇒ speech-only by construction; fallback buys wall-clock via speech + caller reply (3-8 s ≫ warm needs) |
| **O3/O4 (multi-second honest waits / serialize) are DEAD as options** | owner ceiling TTFT ≤1,100 ms / hear ≤1,400 ms; and the ack path has no wait knob by design (`builder.py:1381` `pass`) — they'd reopen the iter49 "ack speaks instantly" MUST-HAVE |
| **Lite warm may fire BEFORE the 2s-bounded KB resolve at session start (reorder, hygiene-grade)** | lite warm needs no KB ([lite head][history], noop tool only); warm resolve measured 26 ms so this is a worst-case guard, not a big win; zero behavior change |
| **NO KB loads at/before the call start is the OWNER DIRECTIVE — the lite turn needs zero KB (verified: turn-1 lite = [lite head][history], no tools beyond noop, NO retrieval lanes — `builder.py:1412-1414`), and the KB-resolve (2s-capped, measured 26 ms warm) + `warm_rag` (~833 ms one-time ONNX load, async) at session start are REMOVAL/REORDER candidates, not givens** | owner: "the state ack is loading kb, dv, tools etc — we don't need to load KBs at the lite turn or even before call starts." Physics check: warm_rag is async (off the critical path) BUT its only benefit is the first HEAVY round's lane-B embed (turn-2+); dropping it means that round's retrieval pays the 833 ms load inside the RAG-await cap (60 ms) → first heavy round degrades to zero fresh chunks. That trade (start-clean vs turn-2-has-chunks) is an owner HITL decision measured by the T1 greeting span, not a default |
| **Gates for this plan:** first 3-4 turns TTFT ≤900 ms; worst-case TTFT ≤1,100; hear ≤1,400; steady p50 ≤950 | owner session directives 2026-09-17 |
| **Era truth is a measurement task, not a belief** — compare live :8000 Prometheus histograms vs iter52 engine on the SAME access path (browser mic bridge first; real Twilio = separate owner ASK) | live has never run the new stack; lab never ran the old stack; the comparison is the "TTS engine era test" |
| **Live production agents and services are NEVER touched** (LAW 0 + plan scope) | production voice agent `agent_16985b5d087e56c35141983396`, chat `agent_87e4d5f08475e5bc558b2f390f`, live :8000-:8006 |
| iter54 plan is superseded; PT-51 decision item collapses into this plan's T5 | owner converged on the design instead of the menu |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| **Owner GO for the real-path test level**: (a) browser mic-bridge battery only, or (b) + real Twilio test call (needs a test number + owner-gated Twilio webhook change; production agent untouched) | owner |
| **HITL — warm_rag / KB-resolve keep-drop-reorder** (Resolved Decisions row: no-KB-before-call-start directive vs the turn-2-first-heavy-round trade) | owner, after T1 greeting-span numbers |
| "One moment, taking notes" filler copy + voice profile (author draft, owner approves text) | owner (T6) |
| iter52 merge decision (standing ASK, separate) | owner |
| Turn-1 wait ceiling decision AFTER T0 numbers (if EOT await needs raising above 500 ms) | owner |
| Confirm :8005's 38-turn population (what called it since Sep 6) — check before using its histogram | T1 log check |

## Environment & Dependencies
- Engine worktree (source of truth, iter52 HEAD): `/tmp/opencode/wt-iter52` (branch `engine/iter52-industry-pin` @ `054af7b`; amended commit, engine code identical to ledger-pinned `a36bdd7`).
- New worktree: `git -C /tmp/opencode worktree add /tmp/opencode/wt-iter55 -b engine/iter55-tts-era-turn1-ammo engine/iter52-industry-pin` + `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter55/engine/.venv` + copy `.env`.
- venv: python 3.12.3 — ALWAYS `<venv>/bin/python -m pip` (pip-script shebang trap).
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (runs/calls/rounds/rag/findings). Import TRAP: run `scripts/live_sql.py` from the MAIN checkout's `engine/` dir, not worktrees (ROOT resolves wrong — hit twice in iter52).
- Langfuse: `scripts/lf.py` (health/traces/show/gens), keys in `engine/.env`; ingest lag ~5-10 s; SDK list calls need `datetime` objects not strings.
- Harness: `engine/tests/llm2llm/harness.py` — `--personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini`. Personas: 26 @ `054af7b`.
- Browser mic bridge (the "UI button" real STT+TTS path, no carrier): GET `/mic`, WS `/mic/ws` on the iter52 engine instance (127.0.0.1:8005 currently; run foreground on a free port for tests — owner-ordered exception per plan SOP).
- Prometheus live metrics: `curl http://localhost:8000/metrics` (deployed-era engine; DO NOT RESTART IT) and `http://localhost:8005/metrics` (iter52 instance).
- Provider: gpt-5.4 agent (`engine/.env`), prompt-caches tool-bearing requests only (FIND-5), registers on completion.
- NO sqlite3 CLI — `.venv/bin/python -c "import sqlite3, ..."`; NO `rg` in bash — use the grep tool.
- Suite: `.venv/bin/python -m pytest tests -o addopts="" -q` from the worktree engine dir — expect **333** green.
- NEVER touch: live services :8000-:8006 (no restarts from the fork), production agent IDs, `kb_chunks` (SELECT-count only), Cal.com event `3801235` (REAL — harness uses `--slots mock`, still cancel all test bookings after batteries). `scripts/keyhound` before any push; no push in normal flow.

## Architecture (what T0 makes visible, and what each change does)
```
CALL START (iter52 code, session.py:176-226):
  ws start → stt.connect → tts.connect → [KB resolve ≤2s BLOCKS] → fire warm_rag (async)
  → fire FULL Intake warm + LITE warm (fire-and-forget) → greeting TTS (speed 1.12, ~4.5-5s)
  → caller replies → turn-1 round (lite shape, awaits lite-warm 500ms) → ...

T0 ADDS (no behavior change):
  span warm:<shape> {fired_at, completed_at, ms, ok|failed}   ← lite + full + transition detection
  span greeting {stream_start → first_audio_out}               ← the runway measurement
  log _await_warm outcome per entry {waited_ms, landed|timeout|already_done}

AFTER T0 (owner-gated, one variable per probe):
  O5: prewarm_max_completion_tokens 64→32→16 (lite warm only)  → registration tail shrinks 0.5-1.5s
  O1: FIRST_TURN_LITE=false → turn-1 = FULL round riding the greeting full-warm
      (the "ammo locked" opener; gate: turn-1 ≤900ms cold probe ×4, cache ≥2,688)
  O2-lite (only if T0 shows residual ack misses): "one moment, taking notes"
      ~700-900 tok no-tools filler at warm-pending entries, flag default OFF
```

## File Map
| File (absolute, on the new branch) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter55/engine/diallux/graph/llm.py` | T0: record warm fired/ok-failed timestamps on the LLM instance. NOTE: the `LLM` class has NO tracer access (verified — `__init__(self, settings)` only); the SPAN itself is emitted by builder.py's task done-callback (see builder.py row) | Edit |
| `/tmp/opencode/wt-iter55/engine/diallux/graph/builder.py` | T0: warm span emission + `_await_warm` outcome logging; T6-only: fallback trigger at entry + warm-pending (behind `prefill_fallback`, default OFF) | Edit |
| `/tmp/opencode/wt-iter55/engine/diallux/observability/tracer.py` | T0: `warm` + `greeting` span helpers | Edit |
| `/tmp/opencode/wt-iter55/engine/diallux/media/session.py` | T0: greeting span (stream-start → first-audio-out); optional reorder: lite `warm_prompt_cache` call moved ABOVE the 2s-bounded KB resolve (guarded by flag, default current order) | Edit |
| `/tmp/opencode/wt-iter55/engine/diallux/config.py` | T0: logging flag; O5: `prewarm_max_completion_tokens`; T6: `prefill_fallback` + fallback wait/wait cap (all default = current behavior) | Edit |
| `/tmp/opencode/wt-iter55/engine/agent/prompts/prefill_fallback_head.md` | T6-only: filler head (~400-600 tok identity+voice) + the "one moment, taking notes" hint (~120 tok) — text owner-approved BEFORE commit | New |
| `/tmp/opencode/wt-iter55/engine/tests/test_iter55_observability.py` | pins: warm span fields present, greeting span present, zero behavior delta (suite 333 + new pins green) | New |
| `/tmp/opencode/wt-iter55/engine/tests/test_iter55_fallback.py` | T6-only pins: fires only on warm-pending; no-tools shape; no chaining; next-round-cache assertion | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter55-era-truth/01_era_and_warm_p90.md` | measured truth: era comparison + warm completion distribution + greeting runway + option probe results | New (gitignored) |

## Deploy Rules
- All engine work on `engine/iter55-tts-era-turn1-ammo` (worktree `/tmp/opencode/wt-iter55`); suite green before any probe; one variable per probe.
- Live :8000-:8006 processes: NEVER restarted/stopped from the fork. Era test reads their `/metrics` read-only. Any real-Twilio test needs owner GO (plan SOP exception: foreground uvicorn, 127.0.0.1, free port).
- Batteries: cancel ALL test bookings (Cal.com `3801235` REAL); harness uses `--slots mock`.
- Docs (this plan, NEXT_STEPS.md) = straight to main per LAW 0 v3; plan amends, never stacks.
- Before any push: `scripts/keyhound`. No push without owner say-so.

## Tasks (in order)
### T0 — Warm + greeting observability (no behavior change)
Goal: make the invisible visible: warm fired/completed/failed per shape (lite, full, detection) + greeting stream-start→first-audio + `_await_warm` outcomes.
Files: llm.py, builder.py, tracer.py, session.py, config.py (flag), new test.
Verification: one mic-bridge session + one harness call; Langfuse shows `warm` and `greeting` spans with completed-at; `git diff 054af7b` shows only observability; suite green (333+).

### T1 — The measured truth: warm completion + ack p90 + era histograms (read-only, no flags)
Goal: produce THE table nobody has: warm-completion p50/p90 per shape × cold/warm provider; ack-round p50/p90; greeting duration distribution; live :8000 histogram snapshot.
Commands (full):
```bash
cd /tmp/opencode/wt-iter55/engine && set -a && . ./.env && set +a
.venv/bin/python tests/llm2llm/harness.py --personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini
# true-cold repeat ≥4h later (second letter: cold-probe-b)
cd /home/julio/projects/clean_diallux_SDR/engine && set -a && . ./.env && set +a
.venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run warm-span-a --commit <sha> --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db
curl -s http://localhost:8000/metrics | grep -E "e2e_response|stt_eot|llm_first_to_tts" > /home/julio/projects/clean_diallux_SDR/research/surgeon/iter55-era-truth/live_8000_snapshot_$(date +%m%d).prom
```
Verification: warm spans yield ≥10 lite-warm + ≥10 full-warm completion samples; the 01_era_and_warm_p90.md table has lite/full × cold/warm p50/p90; ack p50/p90 computed from ledger SQL.

### T2 — Era A/B truth (lab vs deployed)
Goal: answer "which era are we testing from" with numbers: run the SAME mic-bridge probe (real STT+TTS path) on the iter52 engine and compare e2e_response_ms p50/p90 vs the :8000 live histograms (2.20 s mean era).
Commands: browser mic-bridge sessions (the `/mic` page) ×2 personas ×3 calls each on the iter52 instance; export `turn:final` reports from Langfuse. **OWNER-ASSISTED (HITL): the mic page needs a human at a browser with a mic — the agent starts the engine, Julio makes the test calls, the agent pulls the reports.** Agent-side alternative if owner is unavailable: reuse the existing micbridge Langfuse traces (Sep 6/11/12, `e2aacc99471a`, `43d83d0815c9`) as the era-52 sample and note the n.
Verification: table "era-0 (deployed iter40) vs era-52 (this branch)" in the report; the delta decomposes into LLM-cache work vs TTS/STT/carrier.

### T3 — O5 sweep (one variable): lite warm completion tail
Sweep lite warm completion tail 64→32→16 via env prefix (FULL warm keeps 64 — the 16-tok 400-rejection history belongs to the full shape; verify the sweep only touches the lite warm by reading `_warm`'s lite branch before running):
```bash
cd /tmp/opencode/wt-iter55/engine && set -a && . ./.env && set +a
PREWARM_MAX_COMPLETION_TOKENS=32 .venv/bin/python tests/llm2llm/harness.py --personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini
# then repeat with =16; unset = exact rollback
```
Gate: zero `prewarm failed` warnings ×20 lite warms; registration-time delta reported from T0 spans (compare warm span ms across the three settings).

### T4 — Turn-1 "ammo locked" probe (one variable): `FIRST_TURN_LITE=false`
The owner's converged design: turn-1 = FULL round riding the greeting full-warm.
```bash
cd /tmp/opencode/wt-iter55/engine && set -a && . ./.env && set +a
FIRST_TURN_LITE=false .venv/bin/python tests/llm2llm/harness.py --personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini
```
Run on a TRUE-COLD provider (≥3.5 h idle — cold-probe discipline) ×4 calls, letter-suffixed (`ammo-a`…`ammo-d`). Sanity-check FIRST: the T0 warm spans must show the greeting FULL warm completing BEFORE the turn-1 round fires — that is the mechanism under test.
Gate (cold probe ×4): turn-1 cache ≥2,688 AND TTFT ≤900 ms ×4/4; first-3-turns TTFT ≤900 steady; suite green. If turn-1 still misses on true cold → T0 data names the failure (silent fail vs cold queue vs lag) → fallback (T6) or wait-ceiling decision.

### T5 — Cold probe + warm battery (post-change verification)
Commands: same as T1 (`cold-probe-b`, `warm-battery-iter55` — 4 personas staggered 15 s, Maria/Danny/Susan/Marcus).
Gates: turn-1 cache ≥2,688 ×4/4 cold; battery cache-0 ≤3/call; steady TTFT p50 ≤950; first-3-turns ≤900; hear-band p50 ≤1,400.

### T6 — Fallback filler ("one moment, taking notes") — ONLY IF T4 shows residual misses
Author `prefill_fallback_head.md` (owner-approved copy), wire behind `prefill_fallback=True` default OFF, zero behavior until probe. Gate: fallback TTFT ≤700 ms cold; fires only on warm-pending (rate ≈ ack cache-0 rate); no chaining; next round cache>0; transcripts clean; turn caps respected.

### T7 — Verdict + closeout + ASK
Gates green → ITERATIONS.md line + PENDING_TASKS PT-51/PT-52 flips + report to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter55-era-truth/01_era_and_warm_p90.md`. ASK list: merge iter52? merge iter55? keep `FIRST_TURN_LITE=false` default? **cutover authorization** (the deployed :8000 has never run the cache machine — that is the final step that makes the product match the lab).

## Validation Plan (end-to-end)
1. T0: warm + greeting spans visible; zero behavior delta; suite green.
2. T1: warm-completion distribution table exists (the previously-unmeasurable number); ack p50/p90 from SQL.
3. T2: era table — deployed vs iter52 on the same access path.
4. T3: O5 zero-rejection ×20 + measured registration delta.
5. T4: turn-1 ≤900 ms cold ×4/4, cache ≥2,688.
6. T5: battery no-regression (cache-0 ≤3/call, p50 ≤950).
7. T6: only if needed; all fallback gates green or feature stays OFF.
8. T7: report + ASK (merges + cutover).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merging `engine/iter52-industry-pin` → main | standing owner ASK, separate (though T0/T4 build on it — cut iter55 from the branch HEAD regardless) |
| iter53 hygiene (git label `fec12dd-plan53`, T1-T7) | docs-only today; independent |
| Real-Twilio cutover execution | the ASK this plan's evidence feeds; never done agent-side |
| Time-to-first-AUDIO gate redefinition as the primary SOP gate | surfaced this session (e2e ≠ TTFT); needs its own owner decision after T0/T2 data |
| Provider-side cache mechanics (TTL guarantees, registration lag) | black box; T0 measures empirically |
| Trimming the 1.7k lite head | content-design decision; floor math says prefill savings are ~150 ms/1k tok — secondary |
| O3/O4 as written (multi-second waits, serialize) | DEAD under the 1,100/1,400 gates; the wait knob that survives is the existing 500 ms EOT await (raise = owner ceiling decision post-T0) |
