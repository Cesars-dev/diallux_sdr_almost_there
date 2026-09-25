# PLAN — iter48b: Commit B payload coverage (fix 5) — master-plan-follow session

## Meta
- Date: 2026-09-12
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Worktree: `/tmp/opencode/wt-iter44`, branch `engine/iter48-rag-truth` @ `308253e`
  (Commit A `d9a3396` + live_sql `47cfb38` + lf_quick `308253e` all committed)
- Scope: Commit B **fix 5 ONLY** (payload coverage: await split 500/100 + lite-warm
  await + warm WARNING/retry + 16-token-cap verify). Fix 4 (improvisation rule)
  DEFERRED by owner 2026-09-12. Fix 6 (cross-turn dedupe) deferred per iter48 plan.
- Coding source of truth: `research/surgeon/iter48-rag-truth/04_master_plan.md`
  — steps **M9–M15** (this plan pinpoints them below). M8 is the deferred fix 4.
- Status: PLAN ONLY (not started — awaits owner approval; execute in a NEW session)

## Compaction Context

**Where things stand:** iter48 Commit A shipped on `engine/iter48-rag-truth`
(@ `d9a3396`, suite 265 green): fix 1 = `refer_query` R1 recipe (whats + dv
values + caller text, `[state:` scaffold gone), fix 2 = clean drift vectors,
fix 3 = forced-drift rescue (async + sync parity) + filler-freeze stale-base
reset. Evidence @ `47cfb38`: `scripts/live_sql.py` (Langfuse→SQLite importer,
runs/calls/rounds/rag + gates G1-G5) — smoke-a + happy-a imported, **G1 PASS
(16/16 entries chunked), G2 PASS (no are-you-ai redirect)**.

**happy-b (2026-09-12 12:00-12:15, commit `47cfb38`→`308253e`):** Maria/Danny/
Marcus PASS; Susan FAIL = turn-budget exhaustion from the first-name loop —
NOT a Commit A regression. Both known bugs recorded in ledger.db `findings`
(FIND-1 first-name loop, FIND-2 time-extraction loop) + `plans/PENDING_TASKS.md`
PT-43/PT-44 + `07_call_analysis_sop_happy_b.md` Appendix 2. Fix 4 (improvisation
rule) deferred by owner. `scripts/lf_quick.py` SDK + `SQL_ANALYSIS_SOP.md` +
AGENTS.md eval-SOP section (revision logging + autopsy reports) landed @ main
`52e3af0`/`eb27b44`.

**Forensics the remaining fix addresses (from the iter48 plan, code-pinned):**
- #4 turn-1 lite (`first_turn_lite=True`, config.py:76): lite warm exists
  (`diallux/media/session.py`:202-205) but the lite task is never registered in
  `_latest_warm` (builder.py:272-273 `if not lite:`) and the lite round skips the
  entry-await (`builder.py:838` `if not lite`) → live turn-1 cache_read=0.
- #5 warm coverage holes: entry await single cap 100 ms (config.py:165) → 1-6
  cache-0 rounds per call; warm failures swallowed at info level (llm.py:225
  `log.info("prewarm skipped")`; builder.py:323-324 second swallow); 16-token cap
  (config.py:83) possibly rejected by gpt-5.x — unverified.

**Latency data (ledger, happy-b):** steady TTFT p50 903 / p90 1129 ms (floor
holds); turn-1 858-929 ms on 3/4 calls (Maria 2417 = day's first call, cold pool);
cache-0 rounds 12/83 with TTFT; LLM p50 1263 / p90 1792 ms.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Commit B scope = fix 5 ONLY (M9-M15); M8 improvisation rule DEFERRED | owner 2026-09-12: "lets leave the improve rule for later" — no prompt/head-byte change in this session |
| Await split: `prewarm_entry_wait_ms` stays 100 (mid-turn) + NEW `prewarm_entry_wait_eot_ms` 500 (EOT-boundary) | master plan R5/M9; EOT entries have the user's reply window as warm head start |
| EOT-boundary distinguisher = `rounds_left == max_tool_rounds` | master plan R5; sole writers verified: ingest sets (builder.py:1458), deterministic decrements (1303) |
| Lite warm MUST be awaitable: register under key `lite:<state>` + lite round awaits it with EOT cap | master plan R4/M12 — WITHOUT this, gate G3 (turn-1 cache_read>0 ≥3/4) is unreachable (audit A5) |
| Warm failure → `log.warning` + ONE lite-shape retry | plan fix 5; makes the 16-token-cap rejection observable (BLOCKED item) |
| Cap 16→64 ONLY if rejection observed in T-log | plan BLOCKED item; decision logged in evidence |
| Gates: G3 (turn-1 cache>0 ≥3/4, cache-0 ≤1/call) + G4 (steady ≤950, turn-1 ≤1000, A's G1-G2 hold) | iter48 plan T4, verified vs `happy-a` snapshot |
| Verification ladder: smoke → happy-4 → SQL gate → battery-13 (G5) only after B passes | owner-mandated staging |
| Eval SOP: every run imported with its commit sha; `lf_quick.py bugs` re-run after every revision; autopsy report on any failure | AGENTS.md eval-SOP section @ main `eb27b44` |
| LAW 0: no merge/push without owner say-so | git crystal ball v2 |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner go-ahead for this plan (fresh session) | owner |
| 16-token-cap rejection behavior | observe in warm WARNING logs during T2 smoke; if rejected → config.py:83 16→64, log decision in evidence |

## Environment & Dependencies
- Worktree: `/tmp/opencode/wt-iter44` (branch `engine/iter48-rag-truth`, clean tree).
- Python: `/tmp/opencode/wt-iter44/.venv/bin/python` (3.12). NO new deps.
- Suite baseline: **265 passed** (verify first: `.venv/bin/python -m pytest tests -q --tb=no -p no:warnings`).
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`
  (runs smoke-a / happy-a / happy-b already imported; happy-a = the compare snapshot).
- Langfuse: self-hosted `:3001`; keys via worktree `.env` (`LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`).
- Ports: :8007 is OWNER's live-test server — NEVER start/stop it from the agent session.
  Harness is in-process (graph transport) and needs NO HTTP server.
- :8000-:8006 live services, live agent IDs, slots.db, Cal.com event 3801235: NEVER touched.
- Surgeon folder: `research/surgeon/iter48-rag-truth/` (evidence, gitignored).

## Architecture (one block)
```
engine/iter48-rag-truth @ 308253e
   └─ COMMIT B (fix 5, master plan M9-M15)
        ├─ config.py: + prewarm_entry_wait_eot_ms=500 (mid-turn flag unchanged 100)
        ├─ builder.py: _await_warm(wait_ms param) + entry split (EOT vs mid-turn)
        │            + lite warm registered (lite:<state>) + lite round awaits it
        │            + _warm non-lite: WARNING + ONE lite-shape retry
        ├─ llm.py: warm() failure log.info → log.warning
        ├─ tests: +5 pins in tests/test_iter48_rag_truth.py (M14)
        ├─ [suite green → commit → smoke → happy-4 → import happy-c → G3-G4 vs happy-a]
        └─ battery-13 (G5) → ASK → live :8007 owner-driven (G6) → ASK
M8 (improvisation rule) = DEFERRED — separate later session, owner-approved wording.
```

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter44/diallux/config.py` | + `prewarm_entry_wait_eot_ms: int = 500` beside `prewarm_entry_wait_ms: int = 100` (165); comment per master plan M9 | Edit |
| `/tmp/opencode/wt-iter44/diallux/graph/builder.py` | `_await_warm` optional `wait_ms` param (326-341); entry split at 838-839; lite-round await (~819-824); `warm_prompt_cache` lite registration (272-273); `_warm` lite-retry (322-324) | Edit |
| `/tmp/opencode/wt-iter44/diallux/graph/llm.py` | `warm()` failure log level info→warning (223-225) | Edit |
| `/tmp/opencode/wt-iter44/tests/test_iter48_rag_truth.py` | +5 pins (M14): await split, lite-round await, back-compat, (no head tests — M8 deferred), parity untouched | Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` | + runs smoke-c / happy-c (+ findings rows if any failure) | New (evidence) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/05_battery_report.md` | battery report (T5, only after G3-G4 pass) | New |

## Deploy Rules
- Commits on `engine/iter48-rag-truth` ONLY. NO merge/push without owner (LAW 0).
- :8007 belongs to the OWNER (live tests). Agent NEVER restarts it. After any
  owner live session: cancel ALL test bookings (Cal.com 3801235 is REAL).
- Langfuse server: never restart.

## MASTER-PLAN PINPOINT (what M9-M15 actually edit — imported verbatim essence)

| Master plan step | Exact change | Pinned code anchor (verified 2026-09-12) |
|---|---|---|
| **M9** (config) | add `prewarm_entry_wait_eot_ms: int = 500`; keep `prewarm_entry_wait_ms: int = 100` as mid-turn cap | `config.py:165`; readers: builder.py:332, 838 ONLY (grep-verified) |
| **M10** | `_await_warm(..., wait_ms: int | None = None)` — None → mid-turn flag | builder.py:326-341 (single call site today) |
| **M11** | entry split at 838: `eot = state.get("rounds_left", 0) == runtime.settings.max_tool_rounds` → EOT cap else mid-turn cap | builder.py:838-839; ingest 1458 / decrement 1303 sole writers |
| **M12** (lite warm — audit A5, REQUIRED for G3) | `warm_prompt_cache`: register lite task under `key` (`lite:<state>`, collides with nothing — 272-273 `if not lite:` guard replaced); lite round (~819-824) awaits `_latest_warm["lite:<state>"]` with EOT cap; turn 1 IS an EOT boundary | builder.py:261-273 + 819-824 |
| **M13** | llm.py `warm()`: `log.info`→`log.warning("prewarm failed: %s", exc)` (223-225); builder `_warm` non-lite path (322): on exception ONE lite-shape retry (`[lite head][history]`, no tools/tail), then silent pass | llm.py:217-225; builder.py:288-296 lite messages pattern |
| **M14** | tests: EOT 500 vs mid-turn 100 caps; lite-round awaits `lite:<state>`; `_await_warm(None)` back-compat; parity check | append to `tests/test_iter48_rag_truth.py` |
| **M15** | suite green (265+5) → commit | `git add -A && git commit -m "iter48 Commit B: payload coverage …"` |
| M8 — **DEFERRED** | improvisation rule into `general_prompt.md` + llm.json parity | owner 2026-09-12: later |

## Tasks (in order)

### T1 — Fresh-session context check
Goal: confirm the tree is exactly what this plan assumes.
Files: none changed.
Commands: `cd /tmp/opencode/wt-iter44 && git log --oneline -1 && git status --porcelain`
(expect `308253e` or later iter48 commit, clean tree) + suite run (expect 265 green).
Verification: outputs match.

### T2 — Commit B code (M9–M13 + M14 tests)
Goal: fix 5, exactly per the master-plan table above. NO prompt/.md/llm.json changes.
Files: config.py, builder.py, llm.py, tests/test_iter48_rag_truth.py.
Commands: edits per File Map; then
`cd /tmp/opencode/wt-iter44 && .venv/bin/python -m pytest tests -q --tb=no -p no:warnings`
(265+5 green) → `git add -A && git commit -m "iter48 Commit B: payload coverage (await split 500/100, lite-warm await, warm WARNING+one lite retry) — fix 4 deferred by owner"`.
Verification: suite count printed; commit sha recorded; grep `prewarm_entry_wait_eot_ms`
config.py:165 region; grep `_latest_warm` registration has NO `if not lite:` guard.

### T3 — Smoke + happy-4 + import + gates G3-G4 (compare vs happy-a)
Goal: prove fix 5 on real runs; revision-logged per AGENTS.md.
Commands:
1. `cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && date +"%H:%M"`
2. Smoke: `.venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 28` (expect PASS)
3. Happy-4: `--personas Maria`, then Danny, Susan, Marcus (sequential or parallel with env inline per happy-b lesson: `nohup bash -c 'set -a && . ./.env && set +a && .venv/bin/python tests/llm2llm/harness.py --personas <P> --rag --langfuse --max-turns 28'`)
4. Import: `.venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run happy-c --commit <new-sha>`
5. Re-verify fixes: `.venv/bin/python scripts/lf_quick.py bugs --run happy-c` (ALL COVERED — no regression from B)
6. Gates: `.venv/bin/python scripts/live_sql.py gates --a happy-a --b happy-c`
   - G3: turn-1 cache_read>0 ≥3/4 happy calls; cache-0 rounds ≤1 per call.
   - G4: steady TTFT p50 ≤950/call, turn-1 ≤1000; happy-a's G1-G2 still hold.
Verification: gates print PASS/FAIL (pinned queries); NOTE Maria turn-1 2417 ms in
happy-b was day-first-cold — if Maria turn-1 misses ≤1000 again while being the
session's first call, document cold-pool cause, judge on the other 3 + a second run.

### T4 — Failure handling (autopsy protocol)
If ANY run fails or a gate FAILs: `lf_quick.py rounds --run happy-c --persona <P>`
+ autopsy report `research/surgeon/iter48-rag-truth/08_autopsy_<name>.md`
(per-call turns, ledger rows, root cause line-pinned, NEW vs known FIND-1/FIND-2),
ledger `findings` row + PENDING_TASKS PT entry. THEN STOP and ASK the owner.

### T5 — Battery first-13 (only after G3-G4 PASS)
Goal: full battery per iter48 plan T5; import as `battery-iter48`; gates G5
(≥11/13, Pedro expected fail, Sofia loops expected; NO NEW failure vs baseline;
Offer 0-chunk freeze = 0). Cancel all mock bookings. Report
`05_battery_report.md` + ASK (merge? live reference?).
Verification: `lf_quick.py bugs --run battery-iter48` + `live_sql.py gates --a battery-iter48`.

### T6 — Live reference (owner drives :8007)
Owner relaunches :8007 on branch HEAD (deploy command in the iter48 plan). Owner
asks "what do you guys do" early in Intake. Gate G6: answer = pitch; turn-1
cache_read>0; turn-1 TTFT ≤1000; rag span shows state-anchored Intake chunks.
Final report `06_live_report.md` + ASK (merge decision).

## Validation Plan (end-to-end)
1. Suite green (265→270) before any run.
2. Every run imported + `lf_quick.py bugs` re-verified (revision logging).
3. Gates G3-G4 SQL-pinned, compared vs happy-a; G1-G2 re-run (no regression).
4. Any crash/loop/regression → autopsy + findings row + STOP.
5. Battery only after B's gates pass; live only after battery; no merge without owner.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| M8 improvisation rule (fix 4) | owner 2026-09-12: "leave the improve rule for later" |
| Cross-turn dedupe (fix 6) | owner deferred in iter48 plan (eager-cancel grace A/B partial mitigation) |
| FIND-1 one-liner (accept any first name) | owner: fix later; PT-43 |
| FIND-2 battery-scale retest | owner: fix later; PT-44 |
| Sofia slot-loop | separate plan, SPEC'd in iter47 |
| Cache growth 2,688→~5k (D1/D2) | separate iteration, compatible |
