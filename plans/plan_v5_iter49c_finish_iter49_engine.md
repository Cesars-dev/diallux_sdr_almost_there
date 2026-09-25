# PLAN — v5 iter49c: finish the engine (T4 async + pins + replay, T4b lite entry, T5-offline, report, registry)

## Meta
- Date: 2026-09-15
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Parent plans (READ BOTH FIRST — Resolved Decisions / Environment / T4b / T5-offline / T6 / T7 below are copied from them verbatim where marked):
  - `plans/plan_v5_iter49_rag_retrieval_parity.md` (parent)
  - `plans/plan_v5_iter49b_rag_cutover_lanes.md` (immediate predecessor — its T3 is DONE, its T4 is WIP)
- Scope: finish iter49's ENGINE work on the SAME branch — (a) close the T4 async gap (NEW fix, owner-flagged), (b) T4 pins + offline replay, (c) T4b lite entry, (d) T5-offline cache pins, (e) report + ASK, (f) registry repair. Live battery (marker A/B live, happy-4, battery-13) is EXCLUDED — separate owner-gated session.
- Status: PLAN ONLY (not started — awaits approval).
- Branch: `engine/iter49-rag-parity` @ **`fc42a3e`** (T4 WIP save; lineage `c40f06b` → `266237b` T2 → `4cca6b7` T3 → `fc42a3e` T4-WIP). Worktree: `/tmp/opencode/wt-iter49`. ALL code edits happen there. NO merge without owner (LAW 0).

## Compaction Context (what the 2026-09-15 T3+T4 session did — pin, do not re-derive)

**T3 — DONE, committed `4cca6b7` (suite 283 green = 277 + 6 pins):**
- `scripts/kb_reembed.py`: one-time re-INGEST of `/home/julio/projects/diallux_kb_lab/corpi/it7_faq.json` (193 `{"kb","content"}`, v2 chunker + faq) into **`kb_chunks_v2`** — arctic-m 768-d, **NO query prefix** (documents), batch ≤256, threads 4, idempotent on (kb, sha256(content)), HNSW + kb btree after inserts. `kb_chunks` UNTOUCHED (233 rows, 1536-d OpenAI — verified 233→233).
- Plumbing: config knob `rag_table_name` (identifier-validated); `KBStore` honors it for SELECT/schema-ensure/count; `KBStore.ingest` owns `kb_chunks` ONLY (refuses any other table); `get_kb_store` passes the knob.
- Replay sanity (8 rows, real refer-tag texts + gold-chat caller texts, 0.24/top-3 vs `kb_chunks_v2`): hard asserts PASS — mirror→pain-points 0.264, price-push deferral→sales-language 0.305, Closing anchor→call-closing 0.348. Honest misses recorded: lane-A deferral `"deferral escalation: {pain_frame}"` tops at **0.2117 < 0.24** (deferral rides lane B; `"deferral escalation: what does this cost"` = 0.289 passes — optional refinement, DEFERRED); how-it-works raw top-3 depends on the exact gold text (see TRAPS #5).

**T4 — WIP, committed `fc42a3e` (WORK-IN-PROGRESS save, suite NOT run):**
- `diallux/graph/builder.py`: `_STATE_KBS` real per-state map (Intake 9 KBs; Discovery +discovery-bridge; Closer/Offer/Closing per plan; `_RETRIEVAL_OFF` unchanged; unmapped states fall back to the iter48 union); `build_lanes()` = lane A per refer-tag (query = `tag.what` + non-empty dv values, **leak dvs $-formatted** via `_fmt_leak_value`: raw `"4,000"` → `"$4,000 a week"`, scope `[tag.kb]` ONLY, ≤3 tags) + lane B caller text + industry anchor `"(their industry: {industry})"` (scope `_STATE_KBS[state]`) + Closing hand anchor `"warm goodbye wrap-up next steps"` (E3: swaps to `"recap booking SMS confirmation next steps"` when `booking_verified`/`booking_confirmed`); `_live_retrieve()` = build_lanes → `KBStore.retrieve_lanes` → `rag.merge_lane_chunks`; state_node live branch renders the fresh set as the **post-history delta, REPLACED each turn** (pre-history prefix `[tools][head][state-block][history]` never rewritten); freeze/drift/transition-prefetch/staged-warm-tail all INERT under `rag_live_retrieve` (`False` = iter48 exactly); `rag_keep_markers` A/B in `_head_for`.
- `diallux/rag.py`: `retrieve()`/`retrieve_lanes()` SELECT the chunk PK; output dicts carry `id`; `retrieve_lanes(lanes)` = ONE batched embed for ALL lane texts + `asyncio.gather` of concurrent pgvector fetches; `merge_lane_chunks()` = score-desc merge, dedupe by chunk id (fallback `(kb, content[:80])` when id is None), quota ≤1 chunk/KB unless the lane owns that KB, top_k 3, 1600-char budget.
- `diallux/config.py`: **CUTOVER TRIPLE FLIPPED TOGETHER** — `rag_embedding_model="snowflake/snowflake-arctic-embed-m"`, `rag_table_name="kb_chunks_v2"`, `rag_filter_score=0.24` — plus `rag_live_retrieve=True`, `rag_multiquery=True`, `rag_keep_markers=False`. Worktree `.env` (gitignored) aligned with the same triple — NOT in the commit; the live host `.env` needs the same triple at deploy time.
- OFFLINE SMOKE 7/7 PASS (`/tmp/opencode/iter49_t4_smoke.py`, real prompts + dvs + embedder + pgvector): Intake mirror→pain-points+industry; Discovery how-it-works→discovery-bridge (faithful gold text incl. `"Hi — "` prefix, NO industry dv at r1 — matches pre-flight `c_kbs` exactly); Discovery price-push→**sales-language 0.358** (the FIND-9 catcher, via lane B); Closer loss playback→sales-psychology; Closing→call-closing; Closing booked→recap anchor swap; Booking OFF→zero lanes. Merged-lane latency warm: 39–181ms (first turn 1.46s = ONNX load; killed in-engine by `warm_rag`'s embedder warm).

**THE KNOWN GAP (owner-flagged 2026-09-15, THE reason this plan exists):**
- `_live_retrieve` **awaits** the batched arctic embed (~90–190ms multi-lane) on the round path. The pinned pack requires: *"ASYNC off hot path (awaited portion = pgvector ~3.4ms; 6-lane batch 126–192ms runs in the speech window)"* and validation §5: *"awaited hot path (pgvector + merge) ≤ +60ms vs battery-iter48 … degrade path = previous turn's fresh set for one turn, never a stall."* The fix (bg task + bounded await + previous-set degrade) is **T3 of this plan** — written from scratch, it does NOT exist in the parent plans.

**TRAPS (paid for; violating these = repeat mistakes):**
1. `engine/.venv` is a COPY-mirror venv: `bin/pip` shebang points at the ORIGINAL live workspace venv. **ALWAYS `<venv>/bin/python -m pip …`, never the pip script** (contamination incident 2026-09-15, reverted).
2. Worktrees share the venv via symlink: `wt-iter49/.venv → /home/julio/projects/clean_diallux_SDR/engine/.venv`. fastembed 0.8.0 + onnxruntime live THERE.
3. NEVER run python with cwd=`/home/julio`: `/home/julio/fastembed/` shadows the `fastembed` package. Run from the worktree. (`Settings` also loads `.env` from cwd — another reason.)
4. Model id has the org slash: `snowflake/snowflake-arctic-embed-m` (bare id raises ValueError in fastembed 0.8.0).
5. arctic scores around 0.40 are a borderline cluster (±0.005 flips ranks): the how-it-works turn ONLY surfaces discovery-bridge with the faithful gold caller text (incl. `"Hi — "`). Replay scripts must use the EXACT `caller` text from the lab DB, never paraphrases.
6. `/tmp/opencode/iter49_t4_smoke.py` is EPHEMERAL (active `systemd-tmpfiles-clean.timer`, ~10-day age). Copy its 7 scenarios into the repo (T2 of this plan) before relying on it.
7. The lab DB has NO `sqlite3` CLI on this box — read `/home/julio/projects/diallux_kb_lab/results.db` via python `sqlite3` module.

**Vector store facts (measured):** `kb_chunks` 233 rows/1536-d (UNTOUCHED, iter48 live) · `kb_chunks_v2` 193 rows/768-d arctic (T3-built, idempotent rebuild via `scripts/kb_reembed.py`, sanity via `--replay-only`) · `kb_chunks_emb_staging_m` 233/768 (id+embedding only, lab-built). pgvector DSN = Settings `database_url` (worktree `.env` → `localhost:5434/diallux`).

**Expected suite breakage at `fc42a3e` (why T1 exists):** the cutover triple changed `Settings` defaults, so T3-era pins pinned to the PRE-cutover defaults now fail — at minimum `tests/test_iter49_rag_parity.py::test_rag_table_name_default_is_kb_chunks` (default is now `kb_chunks_v2`); audit for any pin asserting `rag_filter_score==0.40` / `rag_embedding_model=="text-embedding-3-small"` defaults, and any test reaching `get_kb_store` WITHOUT an injected `embed_fn` (would now load the real ONNX model — slow, and hermetic-hostile; inject fakes).

## Resolved Decisions (DO NOT revisit — verbatim from the parent plans unless marked NEW)
| Decision | Rationale |
|---|---|
| Fresh retrieval every turn as the default; `rag_live_retrieve=False` = iter48 exactly (revert switch) | owner 2026-09-12; single flag owns the mode |
| Lane budget: ≤3 engine lanes + ≤3 caller lanes, ONE batched embed + parallel pgvector | owner 2026-09-13 |
| Fresh chunks render in the POST-HISTORY delta slot, REPLACED each turn; pre-history prefix `[tools][head][state-block][history]` NEVER rewritten | owner 2026-09-13 audit |
| Dedupe by chunk id (DB PK) against the CURRENT window, never content bytes | sliding windows break byte dedupe |
| Closing hand anchor "warm goodbye wrap-up next steps" [call-closing, sales-language]; E3 swap to "recap booking SMS confirmation next steps" after booking | Closing.md has zero refer tags |
| filter 0.24 (arctic), top_k 3, 1600-char budget, quota ≤1 chunk/KB unless lane-owned | pinned pack `research/surgeon/iter49p-sharp-rag/02_replay_report.md` |
| Lane-B industry anchor `(their industry: {industry dv})`; leak dvs $-formatted with units | pack #5/#6 (right-vertical 0.589→0.788; raw numerals refuse) |
| Cutover triple flipped TOGETHER (arctic-m / kb_chunks_v2 / 0.24) | one vector space; revert = set all three back |
| `kb_chunks` stays one release; additive table; `KBStore.ingest` owns `kb_chunks` only | zero-downtime, revertible |
| **NEW (this session): the arctic embed runs ASYNC off the hot path** — bg task fired as early as the queries exist, round bounded-awaits (~60ms cap), degrade = previous turn's fresh set (first turn of a call may run empty/prev), never a stall; awaited portion = pgvector + merge only | pinned pack + validation §5; owner flagged the awaited embed 2026-09-15 |
| **NEW: the 7-scenario smoke becomes a repo script** (`scripts/iter49_offline_replay.py`), merged with the plan's offline-replay verification | /tmp is ephemeral (TRAP #6); the plan's T4 verification requires a gold-chat replay anyway |
| Lite entry: first round in a new state = `[state head][state-block dvs][history]` ~1200 tok, NO tools/RAG/await; ALL states incl. Booking + contact_details; per-state opt-out `state_entry_lite_off`; turn-1 `first_turn_lite` + `LITE_NOOP_TOOL` UNTOUCHED | owner 2026-09-13 MUST-HAVE <1000ms |
| Heavy warm realigned to the RAG-free prefix; `_await_warm` (500ms EOT / 100ms mid-turn) guards HEAVY rounds only | staged tail would break `prewarm_byte_exact` |
| Worst-case: ack ~800ms TTFT; first heavy ≤1300ms; awaited hot path ≤ +60ms vs battery-iter48 | owner must-haves; LIVE gates, next session |
| Deferral lane-A pricing-vocab refinement (`"deferral escalation: what does this cost"` = 0.289) is DEFERRED — lane B carries deferral today | pre-flight E4 accepted (a); measure in battery |
| Code lands on `engine/iter49-rag-parity`; LAW 0, no merge without owner; docs straight to main | git crystal ball v2 |
| Live battery excluded from THIS plan (owner directive 2026-09-15) | separate session |
| Registry repair (iter47 generator) = final task, ops-level | owner 2026-09-15 |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None blocking T1–T5 of this plan. | — |
| Owner go for the LIVE battery session | ASK at the report step (T8) |
| Merge consents: `engine/iter49-rag-parity`, `engine/iter47-call-ledger` | ASK at T8 |
| Exact session-state/dvs accessor inside `media/session.py` for the eager-EOT fire | verify at T3 execution (`grep -n "self.runtime\|dvs\|state_name" diallux/media/session.py`); if dvs are NOT reachable there, spawn with `dvs={}` (lane A dv-bare + lane B text still retrieve; dvs refinement lands next round — pack degrade covers it) |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter49/.venv/bin/python` (3.12.3; symlink → `engine/.venv`). fastembed 0.8.0 + onnxruntime in the shared venv; model cache `/home/julio/fastembed/models` (`models--Snowflake--snowflake-arctic-embed-m` present).
- **Pip rule: `<venv>/bin/python -m pip …` ONLY** (TRAP #1). Run everything from the worktree (TRAP #3).
- Postgres `localhost:5434/diallux` (DSN from worktree `.env`). Tables: `kb_chunks` 233/1536-d (never touched), `kb_chunks_v2` 193/768-d.
- Branch/worktree: `engine/iter49-rag-parity` @ `fc42a3e`, worktree `/tmp/opencode/wt-iter49`. Suite at `4cca6b7` was 283 green; at `fc42a3e` NOT RUN (see expected breakage above).
- Gold-chat replay source: `/home/julio/projects/diallux_kb_lab/results.db`, table `replay_turns`, `run_id='replay'`, 82 turns. Columns: `chat, rid, state, vertical, caller, c_lanes, c_kbs, …` (read via python sqlite3 — TRAP #7). The `caller` column = the faithful per-turn caller text; `c_lanes` = the pre-flight's lane queries (JSON string).
- Pre-flight pack + edges: `research/surgeon/iter49p-sharp-rag/02_replay_report.md` (E1–E5); latency facts `research/surgeon/iter48-rag-truth/10_latency_findings.md`.
- Code anchors at `fc42a3e` (pin by SYMBOL, line numbers drift): `builder.py` — `_STATE_KBS`, `kb_slugs_for`, `build_lanes`, `_fmt_leak_value`, `_live_retrieve`, state_node live branch (grep `live = bool(getattr(runtime.settings, "rag_live_retrieve"`), delta wiring (grep `if live:` near `_build_messages`), `_warm` staged-tail gate (grep `not getattr(self.settings, "rag_live_retrieve", False)`), `warm_rag_async` gate, `warm_rag` embedder-warm, `_await_warm`, `_head_for`. `rag.py` — `_chunk_out`, `retrieve`, `retrieve_lanes`, `merge_lane_chunks`. `config.py` — cutover triple + `rag_live_retrieve`/`rag_multiquery`/`rag_keep_markers`. `media/session.py` — `_on_eager_eot`, `_on_eot`, eager wiring (grep `on_eager=`).
- Ports: :8007 owner live-test — never start/stop. :8000-:8006 live services — never touch. ORIGINAL workspace — never modify.

## Architecture (parent verbatim + the async timing shape)
```
ITER49 TARGET (landed at fc42a3e, minus the async piece):
  every turn, BEFORE the LLM call:
    lane A (engine intent):  one retrieve PER refer-tag → its OWN kb scope
    lane B (user intent):    one retrieve on the caller utterance (+ industry anchor)
    ONE batched embed + parallel pgvector → merge (quota, id-dedupe) → top_k 3
    → fresh working set in the POST-HISTORY delta slot (REPLACED each turn)
    local embedder · 0.24 · no freeze (flag revert available)

T4-ASYNC FIX (this plan — the timing shape):
  fire (earliest moment the lane queries exist):
    eager EOT (media/session.py _on_eager_eot, speculative transcript)
      → runtime.spawn_live_retrieve(state, dvs, transcript)   [bg task]
      → batched arctic embed (126-192ms) runs INSIDE the caller's
        remaining speech + speculative LLM start = the speech window
  consume (state_node live branch):
    bounded-await the in-flight task (rag_live_await_ms, default 60)
      → ready:    use THIS turn's fresh set (awaited = pgvector+merge only)
      → not ready: previous turn's fresh set (first turn of a call: empty)
                   — never a stall; the task lands for the next round
  revert: rag_live_retrieve=False → iter48 freeze/drift path byte-exact
```

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter49/diallux/graph/builder.py` | T4-async: `_live_tasks` registry + `_spawn_live_retrieve`/`_consume_live_retrieve` (bounded await + prev-set store keyed by state) | Edit |
| `/tmp/opencode/wt-iter49/diallux/media/session.py` | fire `spawn_live_retrieve` at `_on_eager_eot` (+ `_on_eot` fallback when eager off); best-effort, never raises | Edit |
| `/tmp/opencode/wt-iter49/diallux/config.py` | + `rag_live_await_ms: int = 60` | Edit |
| `/home/julio/projects/clean_diallux_SDR/scripts/iter49_offline_replay.py` (NEW) | the 7 smoke scenarios (ported from `/tmp/opencode/iter49_t4_smoke.py`) + the 82-turn gold-chat replay from `results.db` asserting per-turn tag-KB presence; prints the table for the report | New |
| `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py` | T4 pins (map/lanes/quota/anchors/delta-placement/revert/keep-markers/async-bounded-await+degrade) | Edit |
| `/tmp/opencode/wt-iter49/tests/test_iter49_local_embed.py` + any pin asserting pre-cutover `Settings` defaults | update to the cutover reality (explicit-arg revert pins stay) | Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (NEW) | replay table, suite, pins, deferred live gates, deploy note (.env triple) | New |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-49 status | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/AGENTS.md` | §Eval SOP: BOTH ledgers + `call_ledger.py` provenance + pip trap (T7 step 6) | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` | REFRESHED registry | Edit (evidence, gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/tree.md` (NEW) | iter47 T2 owner visual | New (evidence) |

## Deploy Rules (iter49b verbatim)
- Commits ONLY on `engine/iter49-rag-parity` (worktree `/tmp/opencode/wt-iter49`). NO merge/push without owner (LAW 0). Docs (plans/AGENTS.md/PENDING_TASKS/ITERATIONS) straight to main.
- NEVER start/stop :8007 (owner), live services :8000-:8006, or the original workspace.
- **Pip: `<venv>/bin/python -m pip` only** — `bin/pip` shebangs point at the ORIGINAL live venv (contamination incident 2026-09-15, reverted).
- Never modify an existing Retell LLM — read the snapshot only. Before any push: `scripts/keyhound`. After any owner live/battery session: cancel ALL test bookings (Cal.com event 3801235 REAL).
- The embedder is in-process (no service, no port). Nothing writes to `kb_chunks`; `kb_chunks_v2` is owned by `scripts/kb_reembed.py` only.
- DEPLOY NOTE (goes in the T8 report): the live host `.env` must gain the cutover triple at deploy — `RAG_EMBEDDING_MODEL=snowflake/snowflake-arctic-embed-m`, `RAG_TABLE_NAME=kb_chunks_v2`, `RAG_FILTER_SCORE=0.24` — and `kb_chunks_v2` must exist there (run `scripts/kb_reembed.py` from the deployed tree).

## Tasks (in order)

### T1 — Suite triage + pin repair (pre-cutover pins vs the flipped defaults)
Goal: know and fix the damage the cutover triple did to hermetic pins; restore a green baseline BEFORE building on it.
Files: `tests/test_iter49_rag_parity.py`, `tests/test_iter49_local_embed.py`, any file the failures name.
Commands:
```
cd /tmp/opencode/wt-iter49 && .venv/bin/python -m pytest tests -q --tb=short -p no:warnings
```
Procedure: fix ONLY pins that asserted the PRE-cutover `Settings` defaults (`rag_table_name=="kb_chunks"`, `rag_filter_score==0.40`, `rag_embedding_model=="text-embedding-3-small"`) — re-pin them to the cutover values, and keep the OLD behavior pinned via explicit constructor args (e.g. `KBStore(..., table_name="kb_chunks")` already does this). Any test hitting `get_kb_store` without an injected `embed_fn` gets a fake (never load ONNX in unit tests). NO engine-code changes in this task unless a genuine bug surfaces (then: smallest possible fix, noted in the commit).
Verification: suite green (≥283); `git diff --stat` shows test-file-only changes (or documented bug fixes). Commit: `iter49c T1: suite triage — pins re-pinned to the cutover defaults`.

### T2 — Offline replay script into the repo (smoke preservation + plan's T4 replay verification)
Goal: the 7 smoke scenarios live in the repo; the gold chats replay through the NEW engine with per-turn tag-KB asserts.
Files: `/home/julio/projects/clean_diallux_SDR/scripts/iter49_offline_replay.py` (NEW).
Procedure:
1. Port the 7 scenarios from `/tmp/opencode/iter49_t4_smoke.py` VERBATIM (they are pinned in this plan's Compaction Context) as `--smoke` mode.
2. `--replay` mode: read `/home/julio/projects/diallux_kb_lab/results.db` `replay_turns` (`run_id='replay'`), drive `CallRuntime.build_lanes` + `_live_retrieve` per turn with the EXACT `caller` text (TRAP #5) and the state from the row; sales states (Intake/Discovery/Closer/Offer/Closing) assert the pre-flight's intended tag-KB presence (mirror→pain-points, price-push→sales-language, loss playback→sales-psychology, re-anchor→sales-psychology, Closing→call-closing; mechanical states assert 0 lanes); print the per-turn table + aggregates (chunks/turn, right-vertical rate, zero-chunk turns) comparable to `02_replay_report.md` §T1.
3. Script conventions: `sys.path.insert(0, parents[1])`, `get_settings()`, run from the worktree, exit 1 on hard-assert failure, `--db` override, NEVER touches `kb_chunks`.
Verification: `.venv/bin/python scripts/iter49_offline_replay.py --smoke` → 7/7; `--replay` → table printed, aggregates ≥ pre-flight C numbers (chunks/turn ~2.4, right-vertical ≥0.75, zero-chunk ≤2/47). Paste both into the T8 report. (No commit yet — lands with T5.)

### T3 — THE ASYNC FIX (new, written from scratch — owner-flagged gap)
Goal: awaited hot path = pgvector + merge only (≤ +60ms); the arctic batch runs in the speech window; degrade = previous turn's fresh set, never a stall.
Files: `diallux/graph/builder.py`, `diallux/media/session.py`, `diallux/config.py`.
Procedure:
1. `config.py`: `rag_live_await_ms: int = 60` (bounded-await cap; 0 = never await → always prev-set/empty; `rag_live_retrieve=False` keeps the whole iter48 path untouched).
2. `builder.py` (CallRuntime):
   - `self._live_tasks: dict[str, asyncio.Task] = {}` and `self._live_prev: dict[str, dict] = {}` (key = state_name; value = `{"delta", "kbs", "chunks", "lane_qs", "ms"}`) in `__init__`; cancel/await in `aclose()` next to `_drift_tasks`.
   - `spawn_live_retrieve(self, state_name, dvs, user_msg) -> None`: fire-and-forget `create_task(self._live_retrieve(...))`; dedupe — an in-flight task for the same state supersedes (cancel older, like `_spawn_drift_check`); store the finished result into `self._live_prev[state_name]`; NEVER raises (wrap in try/except, log at warning).
   - In the state_node live branch, REPLACE the direct `await runtime._live_retrieve(...)` with: ensure a task is spawned for THIS (state, user_msg) if none in flight (so rounds still work when the eager hook never fired); then bounded-await via `asyncio.wait_for(asyncio.shield(task), rag_live_await_ms/1000)`; on result → use it (and update `_live_prev`); on timeout/exception → use `self._live_prev.get(state_name)` (delta/kbs/chunks), else empty delta; the shield keeps the task running for the next round. Tracer span gains `"mode": "live-async"`, `"degraded": bool`, `"await_ms"`.
3. `media/session.py`: in `_on_eager_eot` (and in `_on_eot` before the graph invoke as the fallback when eager is off) call, best-effort inside try/except: `self.runtime.spawn_live_retrieve(<current state>, <dvs or {}>, <transcript>)`. FIRST verify what the session object exposes (BLOCKED table row); if dvs are unreachable there, pass `{}` (lane A dv-bare + lane B text still retrieve — pack degrade semantics).
Verification: (a) suite green; (b) new pins (T4): bounded await honors `rag_live_await_ms`, timeout degrades to prev-set, task lands for next round, eager-off fallback fires; (c) timing smoke from the worktree: a scripted two-turn pair logs awaited ≤ `rag_live_await_ms` + ~10ms slack on round 1 (degraded or fresh) and fresh-with-prev-available on round 2. Commit with T5 (or standalone if large).

### T4 — T4 pins (plan iter49b T4 verification, adapted)
Goal: nobody can silently break lanes/quota/anchors/placement/revert/async.
Files: `tests/test_iter49_rag_parity.py`.
Pins (all hermetic — fake pool + fake `embed_fn` capturing calls, per the T3 pins' style):
1. `_STATE_KBS` map exact (the 5 states, OFF unchanged, unmapped → union fallback).
2. `build_lanes`: mirror lane query format `"<tag.what>: <dv values>"`; leak $-fmt (`"4,000"`→`"$4,000 a week"`, already-`$` passthrough, empty-dv skip); industry anchor appended only when the dv exists; Closing anchor + E3 booked swap; ≤3 tag lanes + 1 lane B; OFF states → no lanes; `rag_multiquery=False` → single combined query.
3. `merge_lane_chunks`: id-dedupe across lanes; quota ≤1/KB for non-owned; lane-owned exemption; top_k 3; char budget; None-id fallback key.
4. `retrieve_lanes`: ONE `embed_fn` call carrying N lane texts; per-lane scope honored; empty-lanes → empty result; failure → per-lane empties (never raises).
5. Live branch: fresh delta REPLACES each turn; pre-history prefix bytes IDENTICAL across turns with different chunk sets; `rag_keep_markers` strips/keeps.
6. Revert: `rag_live_retrieve=False` exercises the freeze/drift path (existing iter48-behavior pins still green).
7. Async (from T3): bounded await honored; degrade to prev-set on timeout; `spawn_live_retrieve` dedupes/cancels in-flight; never raises.
Verification: suite green. Commit with T5.

### T5 — Commit T4-final
Goal: one (or two, if T3 ran large) clean commits closing T4.
Procedure: stage `diallux/graph/builder.py`, `diallux/media/session.py`, `diallux/config.py`, `scripts/iter49_offline_replay.py` (repo-root scripts/ — note: this path is the MAIN checkout; commit it from the worktree's `scripts/` so it rides the branch), `tests/test_iter49_rag_parity.py` (+ touched pin files). Message style: `iter49 T4-final: …` with the async shape, replay aggregates, pin count, suite count.
Verification: `git log --oneline -3` shows the commit; `git status` clean; suite green.

### T6 — T4b verbatim (from iter49b — lite entry + heavy-warm realignment)
Goal: the user never feels a state change. Ack round is light and instant; the heavy payload warms in the background.
Files: `diallux/graph/builder.py`, `diallux/config.py`, `tests/test_iter49_rag_parity.py`.
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

### T8 — Report + ledger sync (parent T7, offline scope) + ASK
Files: `research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (T2 replay table + smoke 7/7 + async timing pins from T3 + T4b/T7 pins + the deferred live-gate list + the DEPLOY NOTE (.env triple + `kb_reembed.py` on the live host)), `plans/PENDING_TASKS.md` PT-49 status, ledger sync to the main repo copy.
Verification: report written; ledger synced; then ASK owner: (a) live battery session go? (b) merge consents (`engine/iter49-rag-parity`, `engine/iter47-call-ledger`)?

### T9 — Registry repair (iter49b T7 verbatim — the branch/iteration SQLite control)
Goal: one queryable registry of ALL iterations/branches/commits, current as of today; owner visual.
Steps:
1. Recover the generator WITHOUT merging: `git -C /tmp/opencode/wt-iter49 show engine/iter47-call-ledger:scripts/call_ledger.py > /home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` (staging area only; committing it to main is an owner ASK at T8).
2. BACKUP first: `cp research/surgeon/iter47-call-ledger/ledger.db research/surgeon/iter47-call-ledger/ledger.db.pre-iter49c.bak`.
3. Re-run: `.venv/bin/python scripts/call_ledger.py build --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` (from the worktree, so `git branch -a` sees all branches; generator reads ITERATIONS.md + surgeon folders + json_logs + Langfuse REST).
4. Verify (SQL, not vibes):
   ```bash
   sqlite3 …/iter47-call-ledger/ledger.db "SELECT count(*) FROM branches;"   # ≥ 92 (90 + iter48-rag-truth + iter49-rag-parity)
   sqlite3 … "SELECT name, head_commit FROM branches WHERE name LIKE '%iter4[89]%';"  # 2 rows
   sqlite3 … "SELECT count(*) FROM commits;"   # > 944
   ```
   (no `sqlite3` CLI on this box — TRAP #7: use `.venv/bin/python -c "import sqlite3…"`.)
5. Produce `research/surgeon/iter47-call-ledger/tree.md` (iter47 T2): chronology snap-era → iter25 → iter49, one verdict line per branch, head commit + evidence paths.
6. Note honestly in the report: the registry DB is gitignored evidence (untracked) — git history itself is never lost; the DB is a derived view and this task is its refresh ritual. Recommend (ASK): run the refresh at the END of every battery session (candidate for AGENTS.md Eval-SOP bullet).
Verification: the two iter4[89] rows exist; tree.md renders; AGENTS.md §Eval SOP documents both ledgers + refresh ritual + the pip trap. Docs commit to main; DB/tree are evidence (gitignored).

## Validation Plan (end-to-end, THIS session)
1. Every code step is its own commit on `engine/iter49-rag-parity`; suite green (≥283 + new pins) after each.
2. T4 proven by the OFFLINE gold-chat replay (per-turn tag-KB presence; aggregates ≥ pre-flight C) — NOT vibes; smoke 7/7 preserved in-repo.
3. T4-async proven by pins + a timing smoke: awaited ≤ `rag_live_await_ms` + slack; degrade never stalls.
4. T4b/T7 proven by byte-level suite pins (`_warm` == heavy pre-history; prefix invariance under fresh deltas; lite shape budget).
5. T9 registry verified by SQL row counts (iter48 + iter49 branches present).
6. LIVE gates (next session, owner-gated): ack TTFT ≤800ms, first heavy ≤1300ms, cache_read floors 2688/3712, +60ms awaited-hot-path guard, happy-4 + battery-13 + price-push persona, `lf_quick.py bugs` ALL COVERED, `live_sql.py gates` no new failure.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Live battery + marker A/B live + cache_read floor measurement | owner directive 2026-09-15: separate live session |
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` (after iter49 proves, owner-gated) |
| Deferral lane-A pricing-vocab refinement (`"deferral escalation: what does this cost"` = 0.289) | lane B carries deferral today (pre-flight E4 option (a)); revisit after battery |
| In-turn echo duplication (PT-48/FIND-8), name-loop (PT-43), time-extraction 1/500 (PT-44) | separate plans per owner |
| Merging `engine/iter47-call-ledger` into main | owner ASK at T8; generator recovered via `git show` meanwhile |
