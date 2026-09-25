# PLAN — v5 iter49h: T7 residual + close-out (T7 → T8 report+ASK → T9 registry)

## Meta
- Date: 2026-09-16
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Parent plan (READ FIRST — its Compaction Context is the full iter49 history): `plans/plan_v5_iter49g_closeout_report_registry.md` (committed to main @ `3fc0972`).
- Scope: ONE session — execute T7 (residual pin), then T8 (report + ledger findings + owner ASK), then T9 (registry repair). T7/T8/T9 are copied VERBATIM from iter49g below. NO live battery (owner-gated, separate session).
- Status: PLAN ONLY (not started — awaits approval).
- **Work branch: `engine/iter49c-engine-finish` @ `ffe30d`** (lineage `fc42a3e` → `94d0082` → `c8dd05a` → `a4b53b3` → `ffe30d`). Worktree: `/tmp/opencode/wt-iter49`. ALL code edits happen there. NO merge without owner (LAW 0).
- 49-b checkpoint: `engine/iter49-rag-parity` @ `fc42a3e` — frozen, do not advance.

## Compaction Context (what changed since iter49g was written — pin, do not re-derive)

Nothing was executed after `ffe30d`. This section only pins the owner-aligned mental model of the cache mechanics (confirmed in-session 2026-09-16) and the standing open question:

- **The round chain, owner's letter model:**
  - **a = lite ack** (first round in a new state): request = `[full tools][head kb=False][state-block][history]` + a post-history SPEECH-ONLY directive. Reads b's cached prefix, speaks instantly, NO RAG lanes, NO await.
  - **b = async/silent**, two separate bg things: the **heavy warm** (fired at transition, throwaway request with the EXACT next-round prefix `[tools][head][state-block][history]`, 64-token cap, output discarded) and the **async RAG spawn** (fired at eager EOT, fresh chunks retrieved off the hot path).
  - **c = next response (heavy)**: `[tools][head][state-block][history]` — same prefix; because a's own request extended the cache, c reads through the ack exchange too — plus the fresh RAG delta post-history.
  - **NO merge** — b is not merged into a; b seeds the cache, a reads it, a's own request re-seeds it, c reads through. ONE byte-identical prefix hands cache forward round by round; each call pays only its fresh tail (new user msg + directive/delta).
- **Why the ack carries FULL tools (not the dummy):** the dummy (`LITE_NOOP_TOOL`) is correct for TURN-1 lite only (that shape is tiny and unique — its own lite warm seeds it). The ack already renders the state head + state-block = the heavy bytes, so full tools make its prefix byte-identical to the heavy round's → it rides the warm that ALREADY fires at every transition. A dummy would create a third shape nothing seeds (a new `entry:<state>` warm would be needed per transition — the iter49f recipe). **The dummy-vs-real-tools decision is still OPEN — owner ASK at T8** (iter49f plan records the owner verbatim "Lite turns must have a dummy tool"; `ffe30d` supersedes it mechanically).
- **Suite/gates at `ffe30d` (verified):** 304 passed hermetic; smoke 7/7; gold replay GATE PASS (right-vertical 0.788 pooled AND mean, zero-chunk 1/47, chunks/turn 2.17).

## BUG LOG (T7 execution rule — NOTE ONLY, NO FIXES)

**Standing instruction from the owner (2026-09-16):** while executing T7, if ANY bug surfaces — pin failure, assertion mismatch, suite regression, gate drift — the executor must **NOT fix it**. Instead:
1. Record it in THIS section (append a numbered row: id, what, where — file:line, repro command, exact failure output, suspected root cause, affected commit).
2. If the bug BLOCKS T7's completion (suite not green), STOP the session there and deliver the log to the owner (HITL). If it does not block, continue to T8/T9 and carry the log into the T8 report's bug section.
3. Bugs are noted as NEW rows here; they are NOT merged into iter49g's 5-bug list (that list is frozen history). The T8 report cites both lists.
4. Exception to "no fix": if the suite cannot run AT ALL (import error, collection error), fix the minimum to unblock the suite and record what was touched — nothing else.

| id | bug | where | repro | status |
|---|---|---|---|---|
| 1 | Flaky assert, units mismatch — `aw3 < 0.005` is a seconds-units threshold but `_consume_live_retrieve` returns await_ms in MILLISECONDS (builder.py:1034, rounded to 0.1); the cap=0 "never await" leg demanded <5µs while its real sync overhead (~40–60µs) rounds to 0.1ms under load → intermittent FAIL (`assert (True is True and 0.1 < 0.005)`). Suspected root cause: test bug only — production code is CORRECT (the `cap_ms > 0` guard at builder.py:1022–23 means cap=0 never awaits; the 0.1ms is measurement overhead of the sync path). Executor note: the mid-session "10/10 fail" reading was a measurement artifact (pytest.ini `addopts = -q` + an explicit `-q` = `-qq` swallows the summary line, so grepping "1 passed" always missed); the true pre-fix signature is a load-dependent flake (1 observed failure at load avg ~1.5+, passes on a quiet box). | `tests/test_iter49_rag_parity.py:503` (introduced @ `c8dd05a3`, found during iter49h T7) | `.venv/bin/python -m pytest tests/test_iter49_rag_parity.py::test_async_bounded_await_degrades_then_lands_then_prev` under load avg ≥ ~1.5 (pre-fix) | FIXED @ `1f15e8b` (owner-approved: threshold → `aw3 < 5` ms; 10/10 stable under load ~2.0; suite 305 green re-confirmed) |

## Environment & Dependencies (the critical subset — full list in iter49g)
- Working dir for ALL commands: `/tmp/opencode/wt-iter49` (the worktree). Branch `engine/iter49c-engine-finish` @ `ffe30d`.
- Python: `/tmp/opencode/wt-iter49/.venv/bin/python` (3.12.3; symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`).
- TRAPS (paid for — violating = repeat mistakes): (1) pip ONLY as `<venv>/bin/python -m pip …` (the `bin/pip` shebang points at the ORIGINAL live venv); (2) NEVER run python with cwd=`/home/julio` (`/home/julio/fastembed/` shadows the package); (3) NO `sqlite3` CLI on this box — use `.venv/bin/python -c "import sqlite3; …"`; (4) a suite green-count can be RACY-green — always re-run the FULL suite from the worktree after any change; (5) model id has the org slash `snowflake/snowflake-arctic-embed-m`.
- Postgres `localhost:5434/diallux` (DSN from worktree `.env`). `kb_chunks` 233/1536-d NEVER touched; `kb_chunks_v2` 193/768-d owned by `scripts/kb_reembed.py` only.
- iter48 ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (findings columns: id, severity, found_at, status, bug, evidence, branch_commit, fix_commit, fix_note; max(id) = FIND-6).
- Registry: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` (tables branches/commits/runs/calls) + generator ref `engine/iter47-call-ledger:scripts/call_ledger.py`.
- Ports: :8007 owner live-test — never start/stop. :8000–:8006 live services — never touch.

## Deploy Rules (verbatim from iter49g)
- Commits ONLY on `engine/iter49c-engine-finish` (worktree `/tmp/opencode/wt-iter49`). NO merge/push without owner (LAW 0). Docs (plans/AGENTS.md/PENDING_TASKS) straight to main.
- NEVER start/stop :8007 (owner), live services :8000–:8006, or the original workspace.
- Never modify an existing Retell LLM — read the snapshot only. Before any push: `scripts/keyhound`. After any owner live/battery session: cancel ALL test bookings (Cal.com event 3801235 REAL).
- DEPLOY NOTE (goes in the T8 report): the live host `.env` must gain the cutover triple at deploy — `RAG_EMBEDDING_MODEL=snowflake/snowflake-arctic-embed-m`, `RAG_TABLE_NAME=kb_chunks_v2`, `RAG_FILTER_SCORE=0.24` — and `kb_chunks_v2` must exist there (run `scripts/kb_reembed.py` from the deployed tree).

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py` | T7: ack-under-`rag_keep_markers` head-parity pin | Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (NEW) | T8: replay table + smoke 7/7 + async timing + T4b/T7 pins + the 5 bugs + FIND-5 port mechanics + dummy-vs-real-tools ASK + deferred live gates + DEPLOY NOTE | New (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` | T8: insert 5 FIND rows (BUG-1..5 → FIND-7..11) | Edit (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-49 status (line ~123) → implemented offline, live battery pending | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/AGENTS.md` | §Eval SOP: BOTH ledgers + `call_ledger.py` provenance + refresh ritual + pip trap | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` | recovered via `git show` (staging only; commit = owner ASK) | New (staging) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` | REFRESHED registry (backup first) | Edit (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/tree.md` (NEW) | iter47 T2 owner visual | New (gitignored) |

## Tasks (copied VERBATIM from iter49g — T7/T8/T9)

### T7 — residual pins (tiny)
Goal: finish the plan-T7 residue; most of it already landed in `ffe30d`.
- ALREADY DONE (do NOT redo): warm == heavy pre-history byte pin (`test_warm_prefills_rag_free_prefix_equal_heavy_prehistory`); ack/head/tail byte-parity pins (turn-2 test, transition test, chain same-state parity); fresh-delta prefix invariance (`test_live_delta_replaces_each_turn_prefix_bytes_stable`, T4).
- Files: `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py`.
- Commands: from the worktree, `.venv/bin/python -m pytest tests/test_iter49_rag_parity.py -q`.
- Verification: new pin — with `rag_keep_markers=True` + a store, the ACK head keeps `##slug-kb##` markers (mirrors the heavy round's strip decision, bytes equal to the heavy head); with the default False both strip (already pinned for heavy — extend to the ack). Then FULL suite `.venv/bin/python -m pytest tests -q` (expect ≥304 passed). Commit on the work branch.
- **BUG LOG rule applies (see the BUG LOG section above): note any bug found, do NOT fix (owner decides); stop-and-report only if T7 is blocked.**

### T8 — Report + ledger sync + ASK
Files: the report + PENDING_TASKS.md + the iter48 ledger findings table (paths above).
- Report content (all sections mandatory): (1) T2 replay table (82/82, aggregates vs pre-flight C) + smoke 7/7; (2) async timing pins from the T3 timing smoke (cold ~418–429ms once per process; warm no-window = bounded 61ms → degraded; warm +300ms speech window = 0.0ms fresh; cap 0 → previous set; dedupe cancels; broken store never raises); (3) T4b/T7 pins summary; (4) the 5 bugs (each: root cause, line refs, fix commit, residual); (5) FIND-5 port mechanics + the dummy-vs-real-tools open ASK (iter49f vs `ffe30d`, one paragraph, no advocacy); (6) DEFERRED LIVE GATES list: ack TTFT ≤800ms, first heavy ≤1300ms, awaited hot path ≤ +60ms, cache_read floors 2688/3712 (heavy turn-2+) AND the NEW ack expectation — ack rounds share the heavy prefix, so an ack after a landed transition warm must show cache_read ≈ the heavy floor (a cache-0 ack = the warm didn't land — investigate, don't shrug); (7) DEPLOY NOTE (.env triple + `kb_reembed.py` on the live host); (8) honest notes: mean chars/turn 1196 vs C's 693 (merged chunk bytes vs rendered excerpts), gold Intake r1 runs dv-bare (Retell V6.8 never extracted `pain_frame` before r1), the 1/47 zero-chunk turn = E1 anchor-unavailable (deferral pricing-vocab tweak deferred, lane B carries deferral).
- Ledger: insert 5 findings rows into `research/surgeon/iter48-rag-truth/ledger.db` — first query `SELECT max(id) FROM findings;` (currently FIND-6 is max), insert FIND-7..FIND-11 with severity/found_at/status (`FIXED @ <sha>`)/bug/evidence/branch_commit/fix_commit/fix_note from the iter49g Compaction bug list (BUG-1→94d0082, ONNX→c8dd05a, consume-replace→c8dd05a, keep_markers→c8dd05a, BUG-5→ffe30d). Use `.venv/bin/python -c "import sqlite3; …"` from the worktree (no sqlite3 CLI). Verify: `SELECT count(*) FROM findings;` increased by 5.
- PENDING_TASKS.md PT-49: status → implemented offline on `engine/iter49c-engine-finish` @ `ffe30d` (T1–T6), suite 304, gates PASS; live battery + merge = pending owner.
- Verification: report renders (read it top-to-bottom); findings +5; PT-49 updated. THEN ASK owner: (a) live battery go? (b) merge consents (`engine/iter49c-engine-finish`, `engine/iter47-call-ledger`)? (c) dummy-tool vs real-tools on the ack? (d) commit `scripts/call_ledger.py` to main?

### T9 — Registry repair (iter49b T7 verbatim — the branch/iteration SQLite control)
Goal: one queryable registry of ALL iterations/branches/commits, current as of today; owner visual.
Steps:
1. Recover the generator WITHOUT merging: `git -C /tmp/opencode/wt-iter49 show engine/iter47-call-ledger:scripts/call_ledger.py > /home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` (staging area only; committing it to main is the owner ASK at T8).
2. BACKUP first: `cp /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db.pre-iter49h.bak`.
3. Re-run from the worktree (so `git branch -a` sees all engine/* branches): `.venv/bin/python /home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py build --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db`. If the generator errors on main-repo-only paths (ITERATIONS.md / json_logs), that is a BLOCKED item — record the exact error and ask the owner; do NOT guess a fix.
4. Verify (SQL, not vibes — no `sqlite3` CLI):
   `.venv/bin/python -c "import sqlite3; c=sqlite3.connect('/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db'); print(c.execute('SELECT count(*) FROM branches').fetchone())"` → ≥ 92 (90 + iter48-rag-truth + iter49-rag-parity + iter49c-engine-finish).
   Same for `SELECT name, head_commit FROM branches WHERE name LIKE '%iter49%'` (expect the iter49 rows, `iter49c-engine-finish` head = `ffe30d` or later if T7 committed) and `SELECT count(*) FROM commits` (> 944).
5. Produce `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/tree.md` (iter47 T2): chronology snap-era → iter25 → iter49, one verdict line per branch, head commit + evidence paths.
6. Note honestly in the report: the registry DB is gitignored evidence (untracked) — git history itself is never lost; the DB is a derived view and this task is its refresh ritual. Recommend (ASK): run the refresh at the END of every battery session (candidate for the AGENTS.md Eval-SOP bullet).
Verification: the iter49 rows exist; tree.md renders; AGENTS.md §Eval SOP documents both ledgers + refresh ritual + the pip trap. Docs commit to main; DB/tree are evidence (gitignored).

## Validation Plan (end-to-end)
1. Every code step is its own commit on `engine/iter49c-engine-finish`; suite green (≥304) after each.
2. T7 proven by the keep_markers ack pin; no suite regression.
3. T8 proven by: report file exists + complete (7 sections), findings +5 verified by SQL, PT-49 updated, ASK delivered with all 4 questions.
4. T9 proven by SQL row counts (iter49 branches present, `iter49c-engine-finish` head = the T7 commit or `ffe30d`) + tree.md.
5. Offline gates re-run after ANY code change: `.venv/bin/python scripts/iter49_offline_replay.py --smoke` (7/7) and `--replay` (GATE PASS, right-vertical 0.788, zero-chunk 1/47, chunks/turn 2.17).
6. LIVE gates (next-next session, owner-gated): ack TTFT ≤800ms, first heavy ≤1300ms, cache_read floors 2688/3712 + the ack floor expectation, +60ms awaited-hot-path guard, happy-4 + battery-13 + price-push persona, `lf_quick.py bugs` ALL COVERED, `live_sql.py gates` no new failure.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Live battery + marker A/B live + cache_read floor measurement | owner directive 2026-09-15: separate live session |
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` (after iter49 proves, owner-gated) |
| Deferral lane-A pricing-vocab refinement (`"deferral escalation: what does this cost"` = 0.289) | lane B carries deferral today; revisit after battery |
| In-turn echo duplication (PT-48/FIND-8), name-loop (PT-43), time-extraction 1/500 (PT-44) | separate plans per owner |
| Merging `engine/iter47-call-ledger` into main | owner ASK at T8; generator recovered via `git show` meanwhile |
| Ack state-head slimming (2.0–3.0k tok heads) | the cache floor makes the head cheap to READ; revisit only if live ack TTFT misses 800ms |
| The 6-lane retrieval ceiling (3+3) | no defined query construction for lanes 3-6; only the measured shape (2-3 lanes) is implemented |
| Cold-start ONNX `warm_rag` GIL block (~350+490ms once per process) | absorbed during the greeting; revisit only if the live battery shows a first-call stall |
| The `iter49f` dummy-tool + `entry:<state>` warm implementation | superseded by `ffe30d` unless the owner picks it at the T8 ASK |
| Any bug found during T7 execution | owner rule: NOTE ONLY in the BUG LOG section, no fixes without owner say-so |
