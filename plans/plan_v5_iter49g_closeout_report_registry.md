# PLAN — v5 iter49g: iter49 close-out (T7 residual pin, report+ASK, registry repair)

## Meta
- Date: 2026-09-16
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Predecessor plans (READ FIRST): `plans/plan_v5_iter49e_t4b_report_registry.md` (T4b/report/registry work queue — its Compaction Context is the iter49c session history) and `plans/plan_v5_iter49f_lite_dummy_tool_fix.md` (the T6 cache-fix plan, superseded — see Compaction).
- Scope: finish iter49's remaining OFFLINE work — (a) T7 residual pin, (b) the T8 report + ledger findings + owner ASK, (c) the iter47 registry repair. NO live battery (owner-gated, separate session).
- Status: PLAN ONLY (not started — awaits approval).
- **Work branch: `engine/iter49c-engine-finish` @ `ffe30d`** (lineage `fc42a3e` → `94d0082` T1 → `c8dd05a` T4-final → `a4b53b3` T6-lite-entry → `ffe30d` T6-rev FIND-5 port + BUG-5). Worktree: `/tmp/opencode/wt-iter49`. ALL code edits happen there. NO merge without owner (LAW 0).
- **49-b checkpoint: `engine/iter49-rag-parity` @ `fc42a3e`** — frozen. Do NOT advance.

## Compaction Context (the 2026-09-16 T6-revision session — pin, do not re-derive)

**Starting state.** T1–T5 of iter49 DONE at `c8dd05a` (BUG-1 fix, async live retrieval, offline replay in-repo, 15 T4 pins, suite 298). A prior session then landed **T6 base `a4b53b3`** (state-entry lite: first round in a new state = `[state head kb=False][state-block][history]`, NO tools/lanes/await, 6 pins, suite 304) — but shipped the ack with `tools=[]`.

**Owner problem statement (2026-09-16):** "~1200 toks is proly overstated, dont take it as a hard rule... only problem is we are not calling tools on lite state load so we cant cache those tokens... we have an iter — look on the SQL DB where we added that, find it so we can port that."

**The ported logic (FIND-5):** `research/surgeon/iter48-rag-truth/ledger.db` → `findings` row **FIND-5**, status `FIXED @ 033f742` — gpt-5.4 prompt-caches ONLY tool-bearing requests (cURL+OTEL-proven: 9/9 no-tools = cache_read 0; 3/3 with-tools = cached). iter48b's fix = lite turn-1 binds `LITE_NOOP_TOOL` (`memory_note`, "NEVER call", executor no-ops it, FIRE_AND_FORGET) + the lite warm binds the SAME tool (warm shape == hot shape). Docs: `research/surgeon/iter48-rag-truth/09_sql_report_iter48b.md` (FIND-5 + fix table), `05_battery_report.md` @ `033f742` ("THE FIX"; turn-1 rode the warm-seeded lite prefix 1,664 tok at 679–809ms).

**What landed this session — `ffe30d` "iter49 T6 rev":**
- The ack carries the **FULL tool array**, byte-identical to the heavy round's (same `(state, expand_kb=False)` `_tools_cache` key; with a store present heavy/warm/ack all expand False — `builder.py:553-557`). So the ack's `[tools][head][state-block]` prefix **IS** the heavy/warm prefix → the ack rides the already-landed transition/greeting heavy warm at the **2688/3712 cache floor** and EXTENDS the cache for the following heavy round. DEVIATION from both the noop-tool proposal and the iter49f dummy-tool plan: a dummy tool would create a THIRD shape (neither heavy nor turn-1-lite) that nothing seeds — turn-2 and mid-call acks would still read cache 0 unless a NEW `entry:<state>` warm is fired per transition. Real tools read the warms that ALREADY fire. Owner approved the deviation in-session (HITL report delivered; "so whats next" = no objection). **The dummy-tool + entry-warm variant stays an open owner ASK (T8).**
- Speech-only moved to a **post-history directive** in the delta slot — same proven `force_speech` text ("THIS ROUND: SPEECH ONLY — do not call any tool. Reply to the caller in one or two short sentences, then stop."). Fresh bytes every round, ZERO cached-prefix cost (the iter43 tail placement would bust the state-block out of the prefix). Executor still runs anything the model calls (no worse than pre-iter32); `state_entry_lite_off` = per-state escape hatch.
- Ack still runs NO retrieval lanes and NEVER awaits (`_await_warm` heavy-only, 500ms EOT / 100ms mid-turn untouched). The transition/greeting heavy warm fires the PREVIOUS turn and lands during the caller's speech; in-flight = cold prefill, never a stall.
- The plan's ~1200-tok ack budget DEMOTED to a shape note (measured ack head-bound ~2.6–3.2k tok incl. history; the speed answer is the cache floor, not the byte diet). tiktoken facts (iter49f plan, still true): general_prompt ≈ 1,648 tok; ack heads Intake 2,373 / Discovery 2,824 / Closer 2,963 / Closing 2,053 tok; Intake tools ≈ 688 tok.
- **BUG-5 (found + fixed, pre-existing in T3):** `_consume_live_retrieve` re-raised `CancelledError` when the matched live task was CANCELLED (orphaned by the PREVIOUS closed event loop — the identical-text rerun path, `tests/test_iter38_turn_lifecycle.py::test_ingest_dedupe_consecutive_user`, `NodeCancelledError: Node 'Intake' raised asyncio.CancelledError`, deterministic 5/5 at `a4b53b3`). Fixed: cancelled task counts as nothing (respawn for this round + degrade to `_live_prev`); the bounded await discriminates inner-task-cancel (degrade) from node-cancel (propagate via `task.cancelled()`). This violated the T3 never-raises contract — the prior session's "304 green" claim was racy-green (warm embedder in full-suite ordering; solo runs fail).
- Re-pins: turn-2 initial-state shape (full tools == heavy's; directive as the ONLY trailing system block; head+state-block byte-parity with the heavy round = the cache-floor pin), transition-ack-then-heavy (ack tools+head == next same-state heavy's), transition-chain test's ack discriminator is now the post-history SPEECH-ONLY directive (tools can no longer discriminate) + same-state tools parity + no-knowledge-section, `test_first_turn_lite.py` turn-2 pin. Total pins in `tests/test_iter49_rag_parity.py` file unchanged in count (6 T6 pins re-written, not added).

**Gates at `ffe30d` (all green, verified this session):**
- Suite: **304 passed** (`pytest tests`, hermetic, ~49s).
- Smoke: **7/7 PASS** (`.venv/bin/python scripts/iter49_offline_replay.py --smoke`).
- Gold replay: **GATE PASS** — right-vertical 0.788 pooled AND mean (pre-flight C: 0.788), zero-chunk 1/47 (C: 1/47), chunks/turn 2.17 (C: 2.4), mechanical 0, 0 over the 1600 budget. Retrieval untouched by the port (acks never fired lanes before or after).

**Bug ledger for the T8 report (5 total — iter49c Compaction listed 4, this session added the 5th):**
1. BUG-1 `live`/`live_delta` UnboundLocalError (`fc42a3e`) — fixed T1 `94d0082`.
2. `TextEmbedding()` ONNX-session constructor blocked the EVENT LOOP ~350ms — fixed T3 `c8dd05a` (`_load` parked on a worker thread). Residual: cold build GIL-blocks ~350+490ms once per process (first round of first call may await ~420–500ms once; `warm_rag` absorbs it during the greeting).
3. First `_consume_live_retrieve` REPLACED a landed task instead of consuming it — fixed T3 (`_live_msgs` round-keying + `task.result()`).
4. `_head_for`'s strip made `rag_keep_markers` INERT whenever a store is present — fixed T3 (caught by a T4 pin).
5. BUG-5 `_consume_live_retrieve` CancelledError on stale/orphaned cancelled task — fixed T6-rev `ffe30d`.

**TRAPS (paid for; violating these = repeat mistakes):**
1. `engine/.venv` is a COPY-mirror venv: `bin/pip` shebang points at the ORIGINAL live workspace venv. **ALWAYS `<venv>/bin/python -m pip …`, never the pip script** (contamination incident 2026-09-15, reverted).
2. Worktrees share the venv via symlink: `wt-iter49/.venv → /home/julio/projects/clean_diallux_SDR/engine/.venv`. fastembed 0.8.0 + onnxruntime live THERE.
3. NEVER run python with cwd=`/home/julio`: `/home/julio/fastembed/` shadows the `fastembed` package. Run from the worktree. (`Settings` also loads `.env` from cwd.)
4. Model id has the org slash: `snowflake/snowflake-arctic-embed-m` (bare id raises ValueError in fastembed 0.8.0).
5. arctic scores around 0.40 are a borderline cluster (±0.005 flips ranks): replay scripts must use the EXACT `caller` text from the lab DB, never paraphrases.
6. The 7 smoke scenarios live in-repo (`scripts/iter49_offline_replay.py --smoke`). `/tmp/opencode/iter49c_t3_timing.py` is EPHEMERAL (its asserts are hermetic pins — nothing lost).
7. NO `sqlite3` CLI on this box — read `research/surgeon/iter47-call-ledger/ledger.db` and `research/surgeon/iter48-rag-truth/ledger.db` via python: `.venv/bin/python -c "import sqlite3; …"` (from the worktree).
8. **NEW:** a suite green-count can be RACY-green (BUG-5 passed in the prior session's ordering, failed solo). Always re-run the FULL suite from the worktree after any change; treat a green claim without a re-run as unverified.

## Resolved Decisions (DO NOT revisit — carry-overs marked; NEW = this session)
| Decision | Rationale |
|---|---|
| Lite entry: first round in a new state = `[state head (kb=False)][state-block dvs][history]`, NO RAG lanes, NO `_await_warm`; ALL states incl. Booking + contact_details; per-state opt-out `state_entry_lite_off`; turn-1 `first_turn_lite` + `LITE_NOOP_TOOL` untouched | owner 2026-09-13 MUST-HAVE <1000ms |
| **NEW: the ack carries the FULL tool array (byte-identical heavy prefix) — reads the existing transition/greeting heavy warm at the 2688/3712 floor; NO third warm shape** | owner in-session 2026-09-16 ("cached tokens are the speed", "port the FIND-5 logic"); a dummy tool needs a NEW `entry:<state>` warm per transition — real tools need none |
| **OPEN ASK (T8): dummy-tool + `entry:<state>` warm (iter49f recipe, owner verbatim "Lite turns must have a dummy tool") vs the landed real-tools port (`ffe30d`)** | iter49f plan records an earlier owner directive; ffe30d supersedes it mechanically but the ASK is unresolved — owner decides at T8 |
| Speech-only on the ack = post-history directive (delta slot), NOT a tail append | tail placement busts the state-block out of the cached prefix (iter43 lesson) |
| The ~1200-tok ack estimate is NOT a hard rule — shape pins only (head+state-block+history+directive); head slimming deferred | owner 2026-09-16; measured ~2.6–3.2k tok; speed = cache floor |
| Fresh retrieval every turn as the default; `rag_live_retrieve=False` = iter48 exactly (revert switch) | owner 2026-09-12; single flag owns the mode |
| Cutover triple flipped TOGETHER (arctic-m / kb_chunks_v2 / 0.24) | one vector space; revert = set all three back |
| filter 0.24 (arctic), top_k 3, 1600-char budget, quota ≤1 chunk/KB unless lane-owned | pinned pack `research/surgeon/iter49p-sharp-rag/02_replay_report.md` |
| Live battery excluded (owner directive 2026-09-15) — separate session | separate session |
| Registry repair (iter47 generator) = final task, ops-level | owner 2026-09-15 |
| Code lands on `engine/iter49c-engine-finish`; LAW 0, no merge without owner; docs straight to main | git crystal ball v2; 49-b checkpoint frozen |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner go for the LIVE battery session | ASK at the report step (T8) |
| Merge consents: `engine/iter49c-engine-finish`, `engine/iter47-call-ledger` | ASK at T8 |
| Dummy-tool vs real-tools on the ack | ASK at T8 (owner verbatim in iter49f plan vs approved deviation this session) |
| Live gate baselines (TTFT 800/1300ms, cache_read floors 2688/3712, ack floor) | measured in the LIVE session, not here |
| Commit consent for `scripts/call_ledger.py` to main | ASK at T8 (T9 stages it via `git show` meanwhile) |

## Environment & Dependencies
- Working dir for ALL commands: `/tmp/opencode/wt-iter49` (the worktree). Branch `engine/iter49c-engine-finish` @ `ffe30d`.
- Python: `/tmp/opencode/wt-iter49/.venv/bin/python` (3.12.3; symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`). fastembed 0.8.0 + onnxruntime in the shared venv; model cache `/home/julio/fastembed/models`.
- **Pip rule: `<venv>/bin/python -m pip …` ONLY** (TRAP 1). Run everything from the worktree (TRAP 3).
- Postgres `localhost:5434/diallux` (DSN from worktree `.env`). Tables: `kb_chunks` 233/1536-d (NEVER touched), `kb_chunks_v2` 193/768-d.
- Lab DB: `/home/julio/projects/diallux_kb_lab/results.db` (table `replay_turns`, `run_id='replay'`, 82 turns; read via python sqlite3 — TRAP 7).
- iter48 ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (tables runs/calls/rounds/rag/findings/sops/sessions; findings columns: id, severity, found_at, status, bug, evidence, branch_commit, fix_commit, fix_note).
- Registry: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` (tables branches/commits/runs/calls) + generator ref `engine/iter47-call-ledger:scripts/call_ledger.py`.
- Pre-flight pack: `research/surgeon/iter49p-sharp-rag/02_replay_report.md`. Latency facts: `research/surgeon/iter48-rag-truth/10_latency_findings.md`.
- Ports: :8007 owner live-test — never start/stop. :8000–:8006 live services — never touch. ORIGINAL workspace — never modify.

## Architecture (current shape, post-`ffe30d`)
```
LITE ENTRY (state_entry_lite=True, all states):
  first round in a NEW state (round state != previous round state):
    [state head (kb=False)] [state-block dvs] [history window]  ~2.6-3.2k tok
    FULL tool array (byte-identical heavy prefix — rides the landed
      transition/greeting heavy warm at the 2688/3712 cache floor)
    + post-history SPEECH-ONLY directive (delta slot, fresh bytes)
    NO RAG lanes · NO _await_warm
  per-state opt-out: state_entry_lite_off (comma list)
  turn-1 first_turn_lite + LITE_NOOP_TOOL: UNTOUCHED

HEAVY ROUNDS (unchanged):
  [tools][head][state-block][history]  pre-history prefix (warm prefills EXACTLY this)
  + fresh post-history RAG delta (async, replaced each turn)
  _await_warm: 500ms EOT / 100ms mid-turn (HEAVY only)
```

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py` | T7: ack-under-`rag_keep_markers` head-parity pin | Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (NEW) | T8: replay table + smoke 7/7 + async timing + T4b/T7 pins + the 5 bugs + FIND-5 port mechanics + dummy-vs-real-tools ASK + deferred live gates + DEPLOY NOTE | New (evidence, gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` | T8: insert 5 FIND rows (BUG-1..5 → FIND-7..11 continuing from max(id)) | Edit (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-49 status (line ~123) → implemented offline, live battery pending | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/AGENTS.md` | §Eval SOP: BOTH ledgers + `call_ledger.py` provenance + refresh ritual + pip trap | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter49e_t4b_report_registry.md` + `plans/plan_v5_iter49f_lite_dummy_tool_fix.md` | BOTH currently UNTRACKED — commit to main (docs rule), mark iter49f superseded-in-part (T6 fixed by `ffe30d`; its ASK survives) | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` | recovered via `git show` (staging only; commit = owner ASK) | New (staging) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` | REFRESHED registry (backup first) | Edit (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/tree.md` (NEW) | iter47 T2 owner visual | New (gitignored) |

## Deploy Rules (predecessor verbatim)
- Commits ONLY on `engine/iter49c-engine-finish` (worktree `/tmp/opencode/wt-iter49`). NO merge/push without owner (LAW 0). Docs (plans/AGENTS.md/PENDING_TASKS) straight to main.
- NEVER start/stop :8007 (owner), live services :8000–:8006, or the original workspace.
- **Pip: `<venv>/bin/python -m pip` only** — `bin/pip` shebangs point at the ORIGINAL live venv (contamination incident 2026-09-15, reverted).
- Never modify an existing Retell LLM — read the snapshot only. Before any push: `scripts/keyhound`. After any owner live/battery session: cancel ALL test bookings (Cal.com event 3801235 REAL).
- The embedder is in-process (no service, no port). Nothing writes to `kb_chunks`; `kb_chunks_v2` is owned by `scripts/kb_reembed.py` only.
- DEPLOY NOTE (goes in the T8 report): the live host `.env` must gain the cutover triple at deploy — `RAG_EMBEDDING_MODEL=snowflake/snowflake-arctic-embed-m`, `RAG_TABLE_NAME=kb_chunks_v2`, `RAG_FILTER_SCORE=0.24` — and `kb_chunks_v2` must exist there (run `scripts/kb_reembed.py` from the deployed tree).

## Tasks (in order — T1–T6 are DONE, do not redo)

### T7 — residual pins (tiny)
Goal: finish the plan-T7 residue; most of it already landed in `ffe30d`.
- ALREADY DONE (do NOT redo): warm == heavy pre-history byte pin (`test_warm_prefills_rag_free_prefix_equal_heavy_prehistory`); ack/head/tail byte-parity pins (turn-2 test, transition test, chain same-state parity); fresh-delta prefix invariance (`test_live_delta_replaces_each_turn_prefix_bytes_stable`, T4).
- Files: `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py`.
- Commands: from the worktree, `.venv/bin/python -m pytest tests/test_iter49_rag_parity.py -q`.
- Verification: new pin — with `rag_keep_markers=True` + a store, the ACK head keeps `##slug-kb##` markers (mirrors the heavy round's strip decision, bytes equal to the heavy head); with the default False both strip (already pinned for heavy — extend to the ack). Then FULL suite `.venv/bin/python -m pytest tests -q` (expect ≥304 passed). Commit on the work branch.

### T8 — Report + ledger sync + ASK
Files: the report + PENDING_TASKS.md + the iter48 ledger findings table (paths above).
- Report content (all sections mandatory): (1) T2 replay table (82/82, aggregates vs pre-flight C) + smoke 7/7; (2) async timing pins from the T3 timing smoke (cold ~418–429ms once per process; warm no-window = bounded 61ms → degraded; warm +300ms speech window = 0.0ms fresh; cap 0 → previous set; dedupe cancels; broken store never raises); (3) T4b/T7 pins summary; (4) the 5 bugs (each: root cause, line refs, fix commit, residual); (5) FIND-5 port mechanics + the dummy-vs-real-tools open ASK (iter49f vs `ffe30d`, one paragraph, no advocacy); (6) DEFERRED LIVE GATES list: ack TTFT ≤800ms, first heavy ≤1300ms, awaited hot path ≤ +60ms, cache_read floors 2688/3712 (heavy turn-2+) AND the NEW ack expectation — ack rounds share the heavy prefix, so an ack after a landed transition warm must show cache_read ≈ the heavy floor (a cache-0 ack = the warm didn't land — investigate, don't shrug); (7) DEPLOY NOTE (.env triple + `kb_reembed.py` on the live host); (8) honest notes: mean chars/turn 1196 vs C's 693 (merged chunk bytes vs rendered excerpts), gold Intake r1 runs dv-bare (Retell V6.8 never extracted `pain_frame` before r1), the 1/47 zero-chunk turn = E1 anchor-unavailable (deferral pricing-vocab tweak deferred, lane B carries deferral).
- Ledger: insert 5 findings rows into `research/surgeon/iter48-rag-truth/ledger.db` — first query `SELECT max(id) FROM findings;` (currently FIND-6 is max), insert FIND-7..FIND-11 with severity/found_at/status (`FIXED @ <sha>`)/bug/evidence/branch_commit/fix_commit/fix_note from the Compaction bug list (BUG-1→94d0082, ONNX→c8dd05a, consume-replace→c8dd05a, keep_markers→c8dd05a, BUG-5→ffe30d). Use `.venv/bin/python -c "import sqlite3; …"` from the worktree (TRAP 7). Verify: `SELECT count(*) FROM findings;` increased by 5.
- PENDING_TASKS.md PT-49: status → implemented offline on `engine/iter49c-engine-finish` @ `ffe30d` (T1–T6), suite 304, gates PASS; live battery + merge = pending owner.
- Verification: report renders (read it top-to-bottom); findings +5; PT-49 updated. THEN ASK owner: (a) live battery go? (b) merge consents (`engine/iter49c-engine-finish`, `engine/iter47-call-ledger`)? (c) dummy-tool vs real-tools on the ack? (d) commit `scripts/call_ledger.py` to main?

### T9 — Registry repair (iter49b T7 verbatim — the branch/iteration SQLite control)
Goal: one queryable registry of ALL iterations/branches/commits, current as of today; owner visual.
Steps:
1. Recover the generator WITHOUT merging: `git -C /tmp/opencode/wt-iter49 show engine/iter47-call-ledger:scripts/call_ledger.py > /home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` (staging area only; committing it to main is the owner ASK at T8).
2. BACKUP first: `cp /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db.pre-iter49g.bak`.
3. Re-run from the worktree (so `git branch -a` sees all engine/* branches): `.venv/bin/python /home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py build --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db`. If the generator errors on main-repo-only paths (ITERATIONS.md / json_logs), that is a BLOCKED item — record the exact error and ask the owner; do NOT guess a fix.
4. Verify (SQL, not vibes — no `sqlite3` CLI, TRAP 7):
   `.venv/bin/python -c "import sqlite3; c=sqlite3.connect('/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db'); print(c.execute('SELECT count(*) FROM branches').fetchone())"` → ≥ 92 (90 + iter48-rag-truth + iter49-rag-parity + iter49c-engine-finish).
   Same for `SELECT name, head_commit FROM branches WHERE name LIKE '%iter49%'` (expect the iter49 rows, `iter49c-engine-finish` head = `ffe30d`) and `SELECT count(*) FROM commits` (> 944).
5. Produce `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/tree.md` (iter47 T2): chronology snap-era → iter25 → iter49, one verdict line per branch, head commit + evidence paths.
6. Note honestly in the report: the registry DB is gitignored evidence (untracked) — git history itself is never lost; the DB is a derived view and this task is its refresh ritual. Recommend (ASK): run the refresh at the END of every battery session (candidate for the AGENTS.md Eval-SOP bullet).
Verification: the iter49 rows exist; tree.md renders; AGENTS.md §Eval SOP documents both ledgers + refresh ritual + the pip trap. Docs commit to main; DB/tree are evidence (gitignored).

## Validation Plan (end-to-end)
1. Every code step is its own commit on `engine/iter49c-engine-finish`; suite green (≥304) after each.
2. T7 proven by the keep_markers ack pin; no suite regression.
3. T8 proven by: report file exists + complete (7 sections), findings +5 verified by SQL, PT-49 updated, ASK delivered with all 4 questions.
4. T9 proven by SQL row counts (iter49 branches present, head `ffe30d`) + tree.md.
5. Offline gates re-run after ANY code change: `.venv/bin/python scripts/iter49_offline_replay.py --smoke` (7/7) and `--replay` (GATE PASS, right-vertical 0.788, zero-chunk 1/47, chunks/turn 2.17).
6. LIVE gates (next-next session, owner-gated): ack TTFT ≤800ms, first heavy ≤1300ms, cache_read floors 2688/3712 + the ack floor expectation, +60ms awaited-hot-path guard, happy-4 + battery-13 + price-push persona, `lf_quick.py bugs` ALL COVERED, `live_sql.py gates` no new failure.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Live battery + marker A/B live + cache_read floor measurement | owner directive 2026-09-15: separate live session |
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` (after iter49 proves, owner-gated) |
| Deferral lane-A pricing-vocab refinement (`"deferral escalation: what does this cost"` = 0.289) | lane B carries deferral today (pre-flight E4 option (a)); revisit after battery |
| In-turn echo duplication (PT-48/FIND-8), name-loop (PT-43), time-extraction 1/500 (PT-44) | separate plans per owner |
| Merging `engine/iter47-call-ledger` into main | owner ASK at T8; generator recovered via `git show` meanwhile |
| Ack state-head slimming (2.0–3.0k tok heads) | the cache floor makes the head cheap to READ; revisit only if live ack TTFT misses 800ms |
| The 6-lane retrieval ceiling (3+3) | no defined query construction for lanes 3-6; only the measured shape (2-3 lanes) is implemented |
| Cold-start ONNX `warm_rag` GIL block (~350+490ms once per process) | absorbed during the greeting; revisit only if the live battery shows a first-call stall |
| The `iter49f` dummy-tool + `entry:<state>` warm implementation | superseded by `ffe30d` unless the owner picks it at the T8 ASK |
