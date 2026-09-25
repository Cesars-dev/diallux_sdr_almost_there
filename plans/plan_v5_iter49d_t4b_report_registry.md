# PLAN — v5 iter49d: iter49 close-out (T4b lite entry, T5-offline pins, report+ASK, registry)

## Meta
- Date: 2026-09-16
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Predecessor plan (READ FIRST — the T6/T7/T8/T9 bodies below are copied from it VERBATIM): `plans/plan_v5_iter49c_finish_iter49_engine.md`
- Scope: finish iter49's remaining offline work — (a) T4b lite entry + heavy-warm verification, (b) T5-offline cache-floor pins, (c) the report + owner ASK, (d) the iter47 registry repair. No live battery (owner-gated, separate session).
- Status: PLAN ONLY (handoff for the next session — T1–T5 of the predecessor are DONE; see Compaction Context).
- **Work branch: `engine/iter49c-engine-finish` @ `c8dd05a`** (lineage `fc42a3e` → `94d0082` T1 → `c8dd05a` T4-final). Worktree: `/tmp/opencode/wt-iter49`. ALL code edits happen there. NO merge without owner (LAW 0).
- **49-b checkpoint: `engine/iter49-rag-parity` @ `fc42a3e`** — deliberately frozen so the pre-iter49c state is one checkout away. Do NOT advance it.

## Compaction Context (the 2026-09-15/16 iter49c session — pin, do not re-derive)

**Where it started.** `fc42a3e` ("iter49 T4: live multi-lane fresh retrieval (WORK-IN-PROGRESS save)") was an UNTESTED WIP commit on `engine/iter49-rag-parity`: the cutover triple had been flipped TOGETHER (`rag_embedding_model="snowflake/snowflake-arctic-embed-m"`, `rag_table_name="kb_chunks_v2"`, `rag_filter_score=0.24`) plus `rag_live_retrieve=True`, `rag_multiquery=True`, `rag_keep_markers=False`, and the suite had NEVER been run ("suite NOT yet run (owner deferred tests)").

**Owner directive (2026-09-16):** audit/pinpoint the failures FIRST, then toss that branch state and land the fix CLEAN on a new branch from the 49-b checkpoint. Done: scratch branch deleted and recreated as **`engine/iter49c-engine-finish`** from `fc42a3e`.

**The audit found (78 failures at `fc42a3e`):**
- **BUG-1 (the only genuine engine bug, 59 of 78 failures):** `builder.py` state_node bound `live`/`live_delta` ONLY inside `if kb_store is not None:` but referenced them unconditionally at the `rag_delta` branch → `UnboundLocalError` on EVERY round without a KB store (all hermetic tests, KB-disabled production).
- **DEBT (18 tests, test-side):** 17 fakes (`DriftStore`, `SpyKB`, `VecStore`, `FakeKBStore`, `CountingStore`, `BlockingStore`, `TwoChunkStore`, `StagingStore`) lack `retrieve_lanes` and pin the iter48 freeze/drift/prefetch paths; 1 pinned the pre-cutover table default; 1 pinned the old Closing allow-list.

**What was landed (all committed on `engine/iter49c-engine-finish`):**
- **T1 `94d0082`** — hoisted `live`/`live_delta` above the `kb_store` gate (BUG-1 fix); re-pinned the 18 tests (the 16 iter48-path pins now run with explicit `rag_live_retrieve=False` = the revert switch; table default → `kb_chunks_v2`; Closing scope → `["call-closing", "sales-language"]`). Suite 283 green.
- **T2** — `scripts/iter49_offline_replay.py` (NEW, repo-relative): `--smoke` = the 7 T4 scenarios VERBATIM from the ephemeral `/tmp/opencode/iter49_t4_smoke.py`; `--replay` = the 82-turn gold-chat drive from the lab DB (dv trail rebuilt from the Retell gold logs, EXACT lab-DB caller text, pre-flight `VERT_PAT` judge). VERIFIED: `--smoke` 7/7 PASS; `--replay` 82/82, GATE PASS — right-vertical **0.788 pooled AND mean (pre-flight C: 0.788, exact)**, zero-chunk 1/47 (C: 1/47), mechanical 0 lanes, 0 over the 1600 budget, chunks/turn 2.17 (C: 2.4 — leaner under the same quota). Honest notes: mean chars/turn 1196 vs C's 693 (pre-flight measured rendered excerpts, this measures merged chunk bytes); gold Intake r1 runs dv-bare (Retell V6.8 never extracted `pain_frame` before r1) so mirror→pain-points is smoke-pinned only.
- **T3 (the owner-flagged async gap, closed):** `config.rag_live_await_ms=60`; `CallRuntime._live_tasks`/`_live_prev`/`_live_msgs` (cancelled in `aclose`); `spawn_live_retrieve` (fire-and-forget at eager EOT, superseding dedupe, NEVER raises); `_live_task` (resolves the store, stashes + returns the landed set); `_consume_live_retrieve` (landed-for-this-round → use now 0ms / in-flight → `wait_for(shield(task), cap)` / else spawn + degrade to `_live_prev` — previous turn's fresh set, first turn empty; never a stall; the shielded task lands for next round). Tracer span gains `mode=live-async`, `degraded`, `await_ms`. `media/session.py` fires `_fire_live_retrieve` at `_on_eager_eot` AND `_on_eot` (eager-off fallback), tracks `_turn_dvs` alongside `_turn_state`, fully `getattr`-defensive. `rag.py`: the `TextEmbedding()` ONNX load now parks on a worker thread too.
- **T4** — 15 hermetic pins appended to `tests/test_iter49_rag_parity.py` (map/lanes/leak-fmt/anchors/caps/multiquery, merge id-dedupe/quota/owned/top_k/budget/None-id, retrieve_lanes one-batched-embed/per-lane-scopes/empty/failure, placement replace+prefix-stable, keep_markers A/B, revert, async bounded-await/landed/degrade/dedupe/never-raise/broken-store).
- **T5 `c8dd05a`** — T2+T3+T4 committed together. **Suite 298 passed (283 + 15 pins).**

**Bugs found this session (4 — all fixed; the T8 report must record them):**
1. BUG-1 `live`/`live_delta` UnboundLocalError (`fc42a3e`) — fixed in T1.
2. `TextEmbedding()`'s ONNX-session constructor blocked the EVENT LOOP ~350ms (GIL) — `asyncio.to_thread` only wrapped inference; the bounded-await timer + TTS/STT stalled. Fixed in T3 (`_load` parked). Documented residual: the cold build still GIL-blocks ~350+490ms → the FIRST round of the FIRST call after a process start may await ~420-500ms once; `warm_rag` normally absorbs the build during the greeting.
3. My first `_consume_live_retrieve` REPLACED a landed task instead of consuming it (round-2-with-speech-window degraded forever) — fixed by `_live_msgs` round-keying + `task.result()`.
4. `_head_for`'s `strip = (... and not rag_keep_markers) or not expand_kb` made **`rag_keep_markers` INERT whenever a store is present** (store ⇒ expand=False ⇒ always strip; the A/B could never keep markers). CAUGHT BY A T4 PIN. Fixed: strip = store-and-not-flag OR (no-store-and-no-expand).

**Timing smoke numbers (real arctic embedder + pgvector, `/tmp/opencode/iter49c_t3_timing.py` — EPHEMERAL, its asserts are now hermetic pins):** cold round ~418-429ms awaited (once per process); warm round with NO speech window = bounded 61ms → degraded (task landed 149ms); warm round after a 300ms speech window = **0.0ms awaited, FRESH**; `rag_live_await_ms=0` → 0.0ms, previous set; dedupe cancels; broken store never raises.

**Latency contract (do not overstate):** the awaited hot path is capped at **60ms** (`rag_live_await_ms`), NOT <50ms. Warm single-lane rounds finish ~36-40ms (fresh); multi-lane rounds can exceed the cap and then DEGRADE to the previous turn's set. The awaited portion when the embed already ran = pgvector + merge only (~4-15ms; pgvector ~3.4ms pre-flight).

**Retrieval shape (do not overstate):** up to **4** lanes implemented = ≤3 lane-A refer-tag lanes + **ONE** lane-B caller lane (`_MAX_LANES_A=3`, `_MAX_LANES_B=3` is the owner budget envelope but only one caller lane is emitted). Real usage is 2-3 lanes (no prompt has 3 refer tags: Intake 1, Discovery 2, Closer 1, Offer 1, Closing 1 anchor). ONE batched `embed_fn` call over all lane texts + `asyncio.gather` concurrent pgvector fetches → quota/id-dedupe merge → top_k 3 → 1600 budget. No reranker, no hybrid BM25, no LLM query rewrite (confirmed in the pre-flight winner rig too). The 0.788 comes from query construction + the 0.24 floor + lane scoping + the quota merge — not from the matcher.

**Known residual gap (DEFERRED, not a lane-count problem):** the 1/47 zero-chunk turn = E1 anchor-unavailable; fix candidate is the lane-A pricing-vocab tweak (`"deferral escalation: what does this cost"` = 0.289), deferred per pre-flight E4 option (a).

**TRAPS (paid for; violating these = repeat mistakes):**
1. `engine/.venv` is a COPY-mirror venv: `bin/pip` shebang points at the ORIGINAL live workspace venv. **ALWAYS `<venv>/bin/python -m pip …`, never the pip script** (contamination incident 2026-09-15, reverted).
2. Worktrees share the venv via symlink: `wt-iter49/.venv → /home/julio/projects/clean_diallux_SDR/engine/.venv`. fastembed 0.8.0 + onnxruntime live THERE.
3. NEVER run python with cwd=`/home/julio`: `/home/julio/fastembed/` shadows the `fastembed` package. Run from the worktree. (`Settings` also loads `.env` from cwd.)
4. Model id has the org slash: `snowflake/snowflake-arctic-embed-m` (bare id raises ValueError in fastembed 0.8.0).
5. arctic scores around 0.40 are a borderline cluster (±0.005 flips ranks): replay scripts must use the EXACT `caller` text from the lab DB, never paraphrases.
6. ~~`/tmp/opencode/iter49_t4_smoke.py` is EPHEMERAL~~ — RESOLVED: the 7 scenarios now live in-repo at `scripts/iter49_offline_replay.py --smoke`. Still true for `/tmp/opencode/iter49c_t3_timing.py` (its asserts are hermetic pins, so nothing is lost).
7. The lab DB has NO `sqlite3` CLI on this box — read `/home/julio/projects/diallux_kb_lab/results.db` and `research/surgeon/iter47-call-ledger/ledger.db` via python `sqlite3` (`.venv/bin/python -c "import sqlite3; …"`).

**Vector store facts (measured):** `kb_chunks` 233 rows/1536-d (UNTOUCHED, iter48 live) · `kb_chunks_v2` 193 rows/768-d arctic (T3-built; idempotent rebuild `scripts/kb_reembed.py`, sanity `--replay-only`) · `kb_chunks_emb_staging_m` 233/768 (lab-built). pgvector DSN = Settings `database_url` (worktree `.env` → `localhost:5434/diallux`).

## Resolved Decisions (DO NOT revisit — verbatim from the predecessor unless marked NEW)
| Decision | Rationale |
|---|---|
| Fresh retrieval every turn as the default; `rag_live_retrieve=False` = iter48 exactly (revert switch) | owner 2026-09-12; single flag owns the mode |
| Lane budget: ≤3 engine lanes + ≤3 caller lanes, ONE batched embed + parallel pgvector | owner 2026-09-13 (envelope; implementation emits ≤3 tag lanes + ONE caller lane — see Compaction) |
| Fresh chunks render in the POST-HISTORY delta slot, REPLACED each turn; pre-history prefix `[tools][head][state-block][history]` NEVER rewritten | owner 2026-09-13 audit |
| Dedupe by chunk id (DB PK) against the CURRENT window, never content bytes | sliding windows break byte dedupe |
| Closing hand anchor "warm goodbye wrap-up next steps" [call-closing, sales-language]; E3 swap to "recap booking SMS confirmation next steps" after booking | Closing.md has zero refer tags |
| filter 0.24 (arctic), top_k 3, 1600-char budget, quota ≤1 chunk/KB unless lane-owned | pinned pack `research/surgeon/iter49p-sharp-rag/02_replay_report.md` |
| Lane-B industry anchor `(their industry: {industry dv})`; leak dvs $-formatted with units | pack #5/#6 (right-vertical 0.589→0.788; raw numerals refuse) |
| Cutover triple flipped TOGETHER (arctic-m / kb_chunks_v2 / 0.24) | one vector space; revert = set all three back |
| `kb_chunks` stays one release; additive table; `KBStore.ingest` owns `kb_chunks` only | zero-downtime, revertible |
| The arctic embed runs ASYNC off the hot path — bg task fired as early as the queries exist, round bounded-awaits (~60ms cap), degrade = previous turn's fresh set (first turn of a call may run empty/prev), never a stall; awaited portion = pgvector + merge only | pinned pack + validation §5; owner flagged the awaited embed 2026-09-15; DONE in `c8dd05a` |
| The 7-scenario smoke becomes a repo script (`scripts/iter49_offline_replay.py`) | /tmp is ephemeral; the plan's T4 verification requires a gold-chat replay; DONE in `c8dd05a` |
| Lite entry: first round in a new state = `[state head][state-block dvs][history]` ~1200 tok, NO tools/RAG/await; ALL states incl. Booking + contact_details; per-state opt-out `state_entry_lite_off`; turn-1 `first_turn_lite` + `LITE_NOOP_TOOL` UNTOUCHED | owner 2026-09-13 MUST-HAVE <1000ms |
| Heavy warm realigned to the RAG-free prefix; `_await_warm` (500ms EOT / 100ms mid-turn) guards HEAVY rounds only | staged tail would break `prewarm_byte_exact` |
| Worst-case: ack ~800ms TTFT; first heavy ≤1300ms; awaited hot path ≤ +60ms vs battery-iter48 | owner must-haves; LIVE gates, next session |
| Deferral lane-A pricing-vocab refinement (`"deferral escalation: what does this cost"` = 0.289) is DEFERRED — lane B carries deferral today | pre-flight E4 accepted (a); measure in battery |
| Code lands on `engine/iter49c-engine-finish`; LAW 0, no merge without owner; docs straight to main | git crystal ball v2; 49-b checkpoint = `engine/iter49-rag-parity` @ `fc42a3e` |
| Live battery excluded from THIS plan (owner directive 2026-09-15) | separate session |
| Registry repair (iter47 generator) = final task, ops-level | owner 2026-09-15 |
| **NEW (this plan): the 4 bugs found in `fc42a3e` are recorded in the T8 report** | AGENTS.md autopsy rule |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None blocking T6–T9. | — |
| Owner go for the LIVE battery session | ASK at the report step (T8) |
| Merge consents: `engine/iter49c-engine-finish` (the work branch), `engine/iter47-call-ledger` | ASK at T8 |
| Live gate baselines (TTFT 800/1300ms, cache_read floors 2688/3712) | measured in the LIVE session, not here |

## Environment & Dependencies
- Working dir for ALL commands: `/tmp/opencode/wt-iter49` (the worktree). Branch `engine/iter49c-engine-finish` @ `c8dd05a`.
- Python: `/tmp/opencode/wt-iter49/.venv/bin/python` (3.12.3; symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`). fastembed 0.8.0 + onnxruntime in the shared venv; model cache `/home/julio/fastembed/models`.
- **Pip rule: `<venv>/bin/python -m pip …` ONLY** (TRAP #1). Run everything from the worktree (TRAP #3).
- Postgres `localhost:5434/diallux` (DSN from worktree `.env`). Tables: `kb_chunks` 233/1536-d (never touched), `kb_chunks_v2` 193/768-d.
- Lab DB: `/home/julio/projects/diallux_kb_lab/results.db` (table `replay_turns`, `run_id='replay'`, 82 turns; read via python sqlite3 — TRAP #7).
- Gold-chat logs (dv trail): `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/testing/json_logs/BOOK_chat_<chat>.json`.
- Pre-flight pack: `research/surgeon/iter49p-sharp-rag/02_replay_report.md` (E1–E5, the §T1 C column). Latency facts: `research/surgeon/iter48-rag-truth/10_latency_findings.md`.
- Registry source: generator at `engine/iter47-call-ledger:scripts/call_ledger.py` (recover via `git show`; never merge that branch without owner).
- Ports: :8007 owner live-test — never start/stop. :8000–:8006 live services — never touch. ORIGINAL workspace — never modify.

## Architecture (the T4b shape this plan must land)
```
LITE ENTRY (state_entry_lite=True, all states):
  first round in a NEW state (round state != previous round state):
    [state head (kb=False)] [state-block dvs] [history window]   ~1200 tok
    NO tools · NO RAG lanes · NO _await_warm
  per-state opt-out: state_entry_lite_off (comma list)
  turn-1 first_turn_lite + LITE_NOOP_TOOL: UNTOUCHED

HEAVY ROUNDS (unchanged from c8dd05a):
  [tools][head][state-block][history]  pre-history prefix (warm prefills EXACTLY this)
  + fresh post-history RAG delta (async, replaced each turn)
  _await_warm: 500ms EOT / 100ms mid-turn (HEAVY only)
```

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter49/diallux/graph/builder.py` | T6: lite-entry path (`state_entry_lite` + `state_entry_lite_off`), `_await_warm` gating | Edit |
| `/tmp/opencode/wt-iter49/diallux/config.py` | T6: `state_entry_lite: bool = False`, `state_entry_lite_off: str = ""` | Edit |
| `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py` | T6 lite-entry pins + T7 cache-floor pins | Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (NEW) | replay table + smoke 7/7 + async timing + T4b/T7 pins + the 4 bugs + deferred live gates + DEPLOY NOTE | New |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-49 status | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/AGENTS.md` | §Eval SOP: BOTH ledgers + `call_ledger.py` provenance + pip trap (T9 step 6) | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` | recovered via `git show` (staging only) | New (staging) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` | REFRESHED registry | Edit (evidence, gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/tree.md` (NEW) | iter47 T2 owner visual | New (evidence) |

## Deploy Rules (predecessor verbatim)
- Commits ONLY on `engine/iter49c-engine-finish` (worktree `/tmp/opencode/wt-iter49`). NO merge/push without owner (LAW 0). Docs (plans/AGENTS.md/PENDING_TASKS/ITERATIONS) straight to main.
- NEVER start/stop :8007 (owner), live services :8000–:8006, or the original workspace.
- **Pip: `<venv>/bin/python -m pip` only** — `bin/pip` shebangs point at the ORIGINAL live venv (contamination incident 2026-09-15, reverted).
- Never modify an existing Retell LLM — read the snapshot only. Before any push: `scripts/keyhound`. After any owner live/battery session: cancel ALL test bookings (Cal.com event 3801235 REAL).
- The embedder is in-process (no service, no port). Nothing writes to `kb_chunks`; `kb_chunks_v2` is owned by `scripts/kb_reembed.py` only.
- DEPLOY NOTE (goes in the T8 report): the live host `.env` must gain the cutover triple at deploy — `RAG_EMBEDDING_MODEL=snowflake/snowflake-arctic-embed-m`, `RAG_TABLE_NAME=kb_chunks_v2`, `RAG_FILTER_SCORE=0.24` — and `kb_chunks_v2` must exist there (run `scripts/kb_reembed.py` from the deployed tree).

## Tasks (in order — T1–T5 of the predecessor are DONE, do not redo)

### T6 — T4b verbatim (from iter49b — lite entry + heavy-warm realignment)
Goal: the user never feels a state change. Ack round is light and instant; the heavy payload warms in the background.
Files: `/tmp/opencode/wt-iter49/diallux/graph/builder.py`, `/tmp/opencode/wt-iter49/diallux/config.py`, `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py`.
- **Lite entry path** (flag `state_entry_lite=True`): trigger = first round in a state whose name ≠ the previous round's state (covers post-`transition_to_X` ack rounds AND turn-2 entry into the initial state; turn-1 keeps the EXISTING first_turn_lite path untouched). Shape: `[state head (kb=False)][state-block dvs][history window]` — ~1200-tok budget. NO tools, NO RAG lanes, NO `_await_warm`. Per-state opt-out via `state_entry_lite_off` (comma list).
- **ALL states get it**, including Booking + contact_details (they stay `_RETRIEVAL_OFF` for RAG).
- **`_warm` realignment: ALREADY DONE in `fc42a3e`** — the staged-RAG tail is gated behind `not rag_live_retrieve` (warm prefills exactly `[tools][head][state-block][history]`). Remaining: confirm `prewarm_byte_exact` pins the RAG-free prefix; warm triggers UNCHANGED (transition tool-name detection + post-execute force=True).
- **`_await_warm` gating:** lite rounds NEVER await; heavy rounds keep the EOT split (500ms EOT / 100ms mid-turn).
- Commands: suite + a transition-focused OFFLINE replay (force transitions Intake→Discovery→Offer→Closer→contact_details→VerifyLead→Booking via the test fake; log per-round shapes + byte budgets).
Verification: lite-entry shape pins green (no tools/no RAG/no await/byte budget); `_warm` bytes == heavy-round pre-history bytes; per-state opt-out honored; no suite regression. (TTFT gates 800/1300ms are LIVE measurements — next session's gates, not this one's.) Commit.

### T7 — T5-offline verbatim (cache-floor pins)
Goal: prove placement correctness without live calls.
- Suite pin: with `rag_live_retrieve=True`, the `[tools][head][state-block][history]` prefix bytes are byte-IDENTICAL across turns with DIFFERENT fresh chunk sets (the delta renders post-history), and with `rag_keep_markers=true|false` the prefix is unchanged except the marker text itself.
- Ledger cache_read floors (2688/3712 turn-2+; T4b transition floors) are LIVE checks — listed in `11_rag_redesign_report.md` as next-session gates.
Verification: new pins green. Commit.
- NOTE (already done in T4, do not duplicate): `test_live_delta_replaces_each_turn_prefix_bytes_stable` and `test_rag_keep_markers_strips_by_default_keeps_on_flag` already exist. T7's residual work = the T4b transition-shape prefix pin (lite entry vs heavy pre-history bytes) + the LIVE floor list in the report.

### T8 — Report + ledger sync (parent T7, offline scope) + ASK
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (T2 replay table + smoke 7/7 + async timing pins from T3 + T4b/T7 pins + the 4 bugs from the Compaction Context + the deferred live-gate list + the DEPLOY NOTE (.env triple + `kb_reembed.py` on the live host)), `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` PT-49 status, ledger sync to the main repo copy.
Verification: report written; ledger synced; then ASK owner: (a) live battery session go? (b) merge consents (`engine/iter49c-engine-finish`, `engine/iter47-call-ledger`)?

### T9 — Registry repair (iter49b T7 verbatim — the branch/iteration SQLite control)
Goal: one queryable registry of ALL iterations/branches/commits, current as of today; owner visual.
Steps:
1. Recover the generator WITHOUT merging: `git -C /tmp/opencode/wt-iter49 show engine/iter47-call-ledger:scripts/call_ledger.py > /home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` (staging area only; committing it to main is an owner ASK at T8).
2. BACKUP first: `cp research/surgeon/iter47-call-ledger/ledger.db research/surgeon/iter47-call-ledger/ledger.db.pre-iter49d.bak`.
3. Re-run: `.venv/bin/python scripts/call_ledger.py build --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` (from the worktree, so `git branch -a` sees all branches; generator reads ITERATIONS.md + surgeon folders + json_logs + Langfuse REST).
4. Verify (SQL, not vibes — no `sqlite3` CLI on this box, TRAP #7: use `.venv/bin/python -c "import sqlite3…"`):
   ```bash
   sqlite3 …/iter47-call-ledger/ledger.db "SELECT count(*) FROM branches;"   # >= 92 (90 + iter48-rag-truth + iter49-rag-parity [+ iter49c-engine-finish])
   sqlite3 … "SELECT name, head_commit FROM branches WHERE name LIKE '%iter49%';"  # the iter49 rows
   sqlite3 … "SELECT count(*) FROM commits;"   # > 944
   ```
5. Produce `research/surgeon/iter47-call-ledger/tree.md` (iter47 T2): chronology snap-era → iter25 → iter49, one verdict line per branch, head commit + evidence paths.
6. Note honestly in the report: the registry DB is gitignored evidence (untracked) — git history itself is never lost; the DB is a derived view and this task is its refresh ritual. Recommend (ASK): run the refresh at the END of every battery session (candidate for AGENTS.md Eval-SOP bullet).
Verification: the iter49 rows exist; tree.md renders; AGENTS.md §Eval SOP documents both ledgers + refresh ritual + the pip trap. Docs commit to main; DB/tree are evidence (gitignored).

## Validation Plan (end-to-end, next session)
1. Every code step is its own commit on `engine/iter49c-engine-finish`; suite green (≥298 + new pins) after each.
2. T6 proven by lite-entry shape pins + a transition-focused offline replay (per-round shapes + byte budgets); `_warm` bytes == heavy pre-history bytes.
3. T7 proven by byte-level suite pins (prefix invariance under fresh deltas + marker A/B) and the LIVE floor list recorded in the report.
4. T9 registry verified by SQL row counts (iter49 branches present).
5. Re-run the two offline gates after every code change: `.venv/bin/python scripts/iter49_offline_replay.py --smoke` (7/7) and `--replay` (GATE PASS).
6. LIVE gates (next-next session, owner-gated): ack TTFT ≤800ms, first heavy ≤1300ms, cache_read floors 2688/3712, +60ms awaited-hot-path guard, happy-4 + battery-13 + price-push persona, `lf_quick.py bugs` ALL COVERED, `live_sql.py gates` no new failure.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Live battery + marker A/B live + cache_read floor measurement | owner directive 2026-09-15: separate live session |
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` (after iter49 proves, owner-gated) |
| Deferral lane-A pricing-vocab refinement (`"deferral escalation: what does this cost"` = 0.289) | lane B carries deferral today (pre-flight E4 option (a)); revisit after battery |
| In-turn echo duplication (PT-48/FIND-8), name-loop (PT-43), time-extraction 1/500 (PT-44) | separate plans per owner |
| Merging `engine/iter47-call-ledger` into main | owner ASK at T8; generator recovered via `git show` meanwhile |
| The 6-lane retrieval ceiling (3+3) | no defined query construction for lanes 3-6; only the measured shape (2-3 lanes) is implemented |
| Cold-start ONNX `warm_rag` GIL block (~350+490ms once per process) | absorbed during the greeting; revisit only if the live battery shows a first-call stall |
