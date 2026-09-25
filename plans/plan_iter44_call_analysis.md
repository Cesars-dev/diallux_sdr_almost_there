# PLAN — iter44: battery call analysis vs plan criteria (post-mortem matching)

## Meta
- Date: 2026-09-11
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Worktree under test: `/tmp/opencode/wt-iter44` (branch `engine/iter44-cache-floor`, HEAD `68541f7` + uncommitted iter44 work)
- Scope: one session — pull all 13 battery mock calls from Langfuse + json_logs, match each to the
  iter44 pass criteria (cache_read climb, state-entry RAG ms, industry chunks, e2e p50, token cap),
  and produce a results table + a decision on the cache-floor-vs-drift conflict.
- Status: PLAN ONLY (awaits approval)

## Compaction Context (hand-built; no /compact available in this environment)

### Project + current state
- Dialux SDR voice engine "Linda", LangGraph 9-state pipeline, Deepgram Flux STT → gpt-5.4 →
  gates → Cartesia. Repo = `clean_diallux_SDR` (MAIN). Live engine test server on `:8007`.
- `engine/iter44-cache-floor` branches off `17b5c21` (iter43's last owner-approved commit) +
  cherry-picked `374318b` (iter43 lite-head kb=False fix) → HEAD `68541f7`. iter43 branch is
  tagged `iter43-failed` (abandoned — cache floor + embed-TLS + frozen-retrieval miss).
- iter44 implements SIX fixes (the plan `plans/plan_iter44_cache_floor.md`), all behind config
  kill-switches (defaults ON), in `/tmp/opencode/wt-iter44/diallux/`:
  - **T1** `prewarm_byte_exact=True` — warm == hot bytes via shared `_build_messages` (builder.py `_build_messages`, `_warm`)
  - **T2** store resolve at session start `wait_for(_, 2.0)` + `_resolve_kb_store` latch AFTER success (session.py + builder.py)
  - **T3** `tail_before_history=True` — layout `[head][tail][history]`
  - **T6a** embed client built ONCE per store (rag.py `embed_fn` lazy-once + `embed_query`)
  - **T6b** `rag_prefetch_on_transition=True` — ok transition → bg RAG prefetch staged, consumed at entry (builder.py `warm_rag_async`/`_stage_rag`/`_rag_staging`)
  - **T6c** `rag_drift_requery=True`, `rag_drift_threshold=0.85` — cosine(new round query, frozen vec) < 0.85 → re-retrieve (vec reuse) + `rag:drift` span
  - **T4** `fallback_inline_kb=False` — pg down ⇒ lean head (markers stripped) + loud log; blob reachable ONLY via flag True or explicit `rag_mode="inline"` (builder.py `_expand_kb`)
- SUITE 240/240 (≥232 required), offline eval 6/6 PASS, battery first-13 = **12/13 PASS** (Pedro fail is PRE-EXISTING: same fail at iter42 baseline — "dumb customer" persona cooperates, agent books; harness expects no-book; NOT an iter44 regression).

### What was ALREADY verified on the battery calls (this session) — DO NOT re-derive blindly, but CONFIRM
From `research/surgeon/iter44-cache-floor/langfuse_summary.json` (13 calls) + `extract_langfuse.py`:
- **WORKS (confirmed firing):** T6a embed-once (first embed ~1008 ms → 139-167 ms); T6b prefetch
  (`rag {"prefetched": true, ms: 0}` on some entries); T6c drift re-retrieval (drift_spans 4-17 per
  call, cosine 0.44-0.77, pgvector retrieve 4-7 ms); **industry chunks now appear** on
  Discovery/Closer (the iter43 miss IS fixed).
- **FAILS (the conflict):** the cache-floor lift (T1+T3 headline goal). Across every call,
  `cache_read` oscillates 2,688/3,712/4,736 and is **0 on every state transition** — it NEVER
  climbs with history. Root cause: T6c drift fires on ~every same-state round (cosine always
  < 0.85), and each drift re-renders the KNOWLEDGE tail → the tail is never byte-stable →
  prefix diverges after tools+head → history never enters the cached prefix. The plan's
  "correctness > cache, one-time re-bill" assumption is wrong in practice (it's every-round).
- **T2 is NOT exercised by the battery:** the harness (`tests/llm2llm/harness.py` → `GraphAgent`)
  drives the graph in-process and BYPASSES `CallSession.start()` (session.py). So the
  session-start resolve/prewarm path is unverified in the battery; only live T9 calls can test it.
  (That's why the FIRST Intake retrieval pays ~2.8 s cold in battery.)
- **max_input** across calls: 3,707-5,355 tokens — never the 16k blob (T4 blob guard works), but
  some gens exceed the plan's literal "<4,500" criterion (that's legit RAG tail + history, not blob).

### Artifacts (all exist — paths are absolute)
- Per-call harness JSON logs: `/tmp/opencode/wt-iter44/tests/llm2llm/json_logs/*.json` (15 files;
  13 are the first-13 battery, 2 are stale first-run Sofia/Pedro — ignore the stale ones, keep the
  newest per slug). Primary run artifacts: `transcript`, `final_dvs`, `turn_ms`, `p50_ms`, `cost`,
  `rag_stats`, `call_id`, `tools`.
- Battery console logs: `/tmp/opencode/iter44_low_<Persona>.log` (13).
- 3-SOP digest: `/tmp/opencode/iter44_low_sop_digest.txt` (13 calls, built via
  `/tmp/opencode/sop_batch_w44_low/scripts/call.py digest --hours 2`).
- Langfuse consolidated summary: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/langfuse_summary.json`
- Langfuse extraction scripts (saved, runnable):
  - `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/extract_langfuse.py` (per-call gens cache_read + rag/rag:drift spans)
  - `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/extract_summary.py` (consolidates all 13)
- Prior report (partially written): `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/01_report.md`
- Langfuse: self-hosted `:3001` v3.172.1, keys in `.env` (`LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`).
  Trace ids (short, from `lf.py traces`): bookmaria `fe94a5092fcc`, bookdanny `9b03a6fe4f0d`,
  booksusan `b62914b5b797`, bookmarcus `df43b15a86de`, nobookcarlos `6444cc674e71`,
  nobookjorge `d415cc0968f5`, nobookdaniel `167117220406`, booksofia `9e37fb62a5ac` (latest run),
  nobookpedro `1eab515f481a` (latest), curvebrenda `6593dabe6537`, curvegene `3dfffb231f6d`,
  curvefrank `94e325149c34`, curveray `6ec8442e9fe8`.

### iter44 pass criteria (the thing we match results against — from plan_iter44_cache_floor.md T9)
1. cache_read on turns 3+ CLIMBS past 2,688 (grows with history) — **KNOWN FAIL in battery**
2. state-entry turns: rag ms ≈ 0 critical-path (prefetched); entry e2e ≤ ~1,400 ms — **partial**
3. caller names an industry → industry-kb chunks appear in a `rag`/`rag:drift` span mid-state — **CONFIRMED WORKING**
4. e2e p50 ≤ 1,304 ms (iter42 baseline) — battery p50s were 1,332-2,265 ms (in-process metric; NOT the live metric)
5. NO generation with input > 4,500 tokens (blob guard) — literal: fails at 5,355; blob guard itself: works

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Run the analysis against the battery (13 mock) calls, NOT live — T9 live calls are gated on owner + this analysis | Owner asked to verify the logic fired on mock calls before live |
| Keep both extraction scripts + langfuse_summary.json as the single evidence source for this analysis | Fresh session must not re-derive Langfuse pulls by hand; scripts are saved and reproducible |
| The cache-floor-vs-drift conflict is REAL and must be reported, not papered over | Langfuse cache_read across all 13 calls is pinned at the floor; drift is always-on |
| Battery cannot validate T2 (session-start prewarm) | The harness bypasses CallSession.start(); only live calls exercise it — must be stated in the report |
| Do NOT change production code in THIS analysis session | This plan is analysis-only; the fix (chunk-set-equal tail dedupe) is a separate decision for the owner |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner decision: accept correctness-over-cache (redefine criterion #1) OR implement the chunk-set-equal tail-dedupe fix so cache AND correctness both hold | Julio, after this analysis report |
| Whether to still proceed to T9 (2 live calls) after this analysis, and with which stance on the conflict | Julio |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter44/.venv/bin/python` (3.12). langfuse 4.15.1 SDK. `.env` in
  `/tmp/opencode/wt-iter44/.env` (LANGFUSE_*, OPENAI keys). Env must be sourced before scripts:
  `set -a; . ./.env; set +a` run from `/tmp/opencode/wt-iter44`.
- Langfuse server: `http://localhost:3001` (v3.172.1). lf.py wrapper: `/tmp/opencode/wt-iter44/scripts/lf.py`.
- The two saved extract scripts live under `research/surgeon/iter44-cache-floor/` (gitignored —
  never commit).
- NEVER touch: `:8000/:8001/:8002/:8003/:8005`, live Retell agent IDs, `slots.db`, Cal.com event
  3801235, Langfuse server itself.

## Architecture (one block)
```
13 battery mock calls (first-13, --rag --langfuse, gpt-5.4 agent / gpt-4o caller)
   │
   ├─ json_logs/*.json  (transcript, p50, rag_stats, call_id)     ← primary
   ├─ iter44_low_<P>.log (console PASS/FAIL)
   └─ Langfuse traces :3001  (per-generation cache_read + rag/rag:drift spans)  ← the "why"
        │  pulled by extract_langfuse.py / extract_summary.py → langfuse_summary.json
        ▼
   MATCH each call against the 5 iter44 pass criteria
        ▼
   results table + conflict verdict (cache-floor FAILS, industry-chunks WORKS, T2 untested)
        ▼
   report: research/surgeon/iter44-cache-floor/01_report.md (append the matching section)
        ▼
   ASK Julio: accept correctness-over-cache, or implement tail-dedupe fix + proceed to T9
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter44/tests/llm2llm/json_logs/*.json` | READ ONLY evidence (13 battery runs; newest per slug wins) | read |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/langfuse_summary.json` | exists (13-call consolidated data) — READ, extend if needed | read/edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/extract_langfuse.py` | exists, runnable | read |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/extract_summary.py` | exists, runnable | read |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/01_report.md` | APPEND an "Analysis: results vs criteria" section | edit |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter44_call_analysis.md` | this plan | new |

## Deploy Rules
- ANALYSIS ONLY. NO code changes. NO branch ops. NO server/port changes. NO merges.
- Evidence under `research/` is gitignored — do not commit it.
- To re-pull Langfuse evidence from `/tmp/opencode/wt-iter44`:
  ```bash
  cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a \
    && .venv/bin/python research/surgeon/iter44-cache-floor/extract_summary.py   # all 13
  # or per call:
  cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a \
    && .venv/bin/python research/surgeon/iter44-cache-floor/extract_langfuse.py bookmaria bookcurvebrenda ...
  ```
- To read a per-call digest:
  ```bash
  cd /tmp/opencode/sop_batch_w44_low && python3 scripts/call.py digest --substr Maria
  ```

## Tasks (in order)

### T1 — Re-pull + sanity the 13-call Langfuse summary
Goal: confirm `langfuse_summary.json` matches the current Langfuse (fresh pull), 13 calls present.
Commands:
```bash
cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && .venv/bin/python research/surgeon/iter44-cache-floor/extract_summary.py
```
Dependencies: Langfuse up (`scripts/lf.py health`), `.env` sourced.
Verification: output lists 13 slugs, gens>0 each, matches langfuse_summary.json; zero trace-fetch errors.

### T2 — Build the results-vs-criteria table
Goal: one row per call, five columns (one per criterion), value = PASS/FAIL + evidence.
Commands: read `langfuse_summary.json` (cache_reads, max_input, rag spans per state) +
  json_logs (p50_ms) + digest (`iter44_low_sop_digest.txt`).
Verification: table produced for all 13 calls. For each criterion, the column is the computed value.

### T3 — Quantify the cache-floor conflict
Goal: show cache_read does NOT climb with history anywhere; isolate which state/history tail mutates.
Commands: from `langfuse_summary.json`, for each call list the cache_read sequence and the
  rag-span sequence in order; confirm the KNOWLEDGE tail re-renders on each drift.
Verification: a written explanation (report) of why drift re-render pins cache at the floor,
  with 2-3 concrete (call, state, round) examples.

### T4 — Confirm the WINS (industry chunks, fast retrieve, embed-once, prefetch)
Goal: evidence the iter43 miss is fixed and T6a/T6b fired.
Commands: grep `kbs:["industry"` and `ms` / `prefetched` / `embed_ms` across the rag spans.
Verification: at least 3 calls show industry chunks on Discovery/Closer; a prefetch span and
  the 1008→139ms embed story documented.

### T5 — Report + ASK
Goal: append the analysis section to the surgeon report and present the verdict + decision to Julio.
Files: append to `research/surgeon/iter44-cache-floor/01_report.md`.
Commands: write the results table + conflict verdict + the "T2 untested by battery" caveat.
Dependencies: T2-T4.
Verification: report has the full matched table; explicit ASK to Julio (accept correctness-over-cache
  OR implement tail-dedupe fix; then proceed to T9 live calls).

## Validation Plan (end-to-end)
1. T1: 13-call summary reproduced from Langfuse.
2. T2-T4: results table + both the FAIL (cache floor) and WINS (industry chunks, fast RAG, prefetch)
   are evidenced with concrete spans, not assertion.
3. T5: report appended; verdict + decision ask delivered to Julio.
4. NO code touched. NO branch/commit. NO live server changes.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| The tail-dedupe FIX (re-render KNOWLEDGE only when chunk set changes, so cache AND correctness hold) | Needs owner decision; it is a CODE change → separate iteration/session, not this analysis |
| T9 live calls (:8007 relaunch + 2 owner calls) | Gated on owner after this analysis + decision on the conflict |
| iter43 T1 EOT telemetry, local embed model, model swap | Pre-existing deferred list, unchanged |