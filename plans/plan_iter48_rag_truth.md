# PLAN — iter48: RAG truth + payload coverage (two commits, SQL-gated)

## Meta
- Date: 2026-09-12
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Worktree: `/tmp/opencode/wt-iter44` (inherited folder name; new branch `engine/iter48-rag-truth` from `515f81f` = iter46 shipped)
- Scope: restore caller-anchored KB retrieval + close the warm/cache coverage holes that made the live agent "stupid" — two commits, each gated by smoke → happy-paths → SQL-ledger comparison; battery of 13 only after both.
- Status: PLAN ONLY (not started — awaits approval + T1 surgeon audit)

## Compaction Context

**Where things stand (post-iter47 session):** iter46 (`engine/iter46-latency-floor` @ `515f81f`) shipped the latency floor (turn-1 TTFT p50 848 battery / 823 live, cache 2,688 floor, 93% hit rate). Quality at baseline: battery B 12/13, D 11/13 (Pedro = known persona variance, byte-identical since iter42; Sofia-D 48t = the slot-loop engine bug, fix SPEC'd separately in the iter47 plan). The T1 verbosity revert restored `medium` default.

**The live-call forensics (Sep 12, owner's call, trace `e2aacc99471aee15e9ac07fa2163094c`):** the agent answered "what do you guys do" with the **are-you-ai script** instead of the pitch. Root-cause chain, all code-pinned:

1. **Entry retrieval is content-free by construction**: every prefetch (greeting `warm_rag`, T6b transition `warm_rag_async`) calls `_stage_rag` with `user_msg=""` → `refer_query` early-returns (builder.py:688-689) at `"[state: Intake] "` → embeds a placeholder → chunks=[] → **frozen for the whole state visit** (iter40 C3). Offer entered 0-chunk-frozen in 10/15 battery calls; Sofia-B/D + Carlos-D Intake entered 0-frozen.
2. **Drift query is scaffold-polluted**: `[state: Intake] the empathic mirror: <user msg>` (~60-70% scaffolding from refer-tag labels; "the empathic mirror" is Intake.md:35's directive label). Wrong chunks win top-3 (are-you-ai beat voice-ai-capabilities for "what do you do"); cosine ≥0.85 on short messages (scaffold dominates both vectors → drift never fires); cosine <0.85 against junk baselines (drift fires every round, retrieving with the polluted vector).
3. **Empty-freeze is permanent**: filler-turn (<12 char) or junk-staging freeze leaves the base vector unset → `_drift_check` early-returns (builder.py:612-617) → that state stays knowledge-blind forever.
4. **Turn-1 lite** (`first_turn_lite=True` default, config.py:76): [general prompt + voice rules] only — no state prompt, no tools, no RAG, no dvs block. Turn 1 improvised "Hi there. What made you call in today?" The lite warm (T3, session.py:198-205) exists but live turn-1 cache_read=0 — fire-and-forget, no entry-await on the lite path, failures swallowed at info level (`prewarm skipped`, llm.py:223), 16-token completion cap possibly rejected by gpt-5.x.
5. **Warm coverage holes**: entry await 100 ms < prefill time → 1-6 cache-0 rounds per battery call; T4a detection-warm (pre-patch dvs) + T4b post-execute warm (post-patch dvs) double-bill near-duplicate prefixes; mid-turn loop rounds miss warms entirely.
6. **Cross-turn repeats** (the live double-speak): dedupe window resets per TURN at ingest (builder.py:1463, iter41's own design); eager-cancel rerun = new turn = structurally invisible to dedupe. **Working as designed** — deferred by owner decision. The iter42 dedupe still works within-turn (tests pin it; battery transcripts clean).
7. dvs: global graph state, all 41 fields, every state reads them via the state-block tail; tail freezes per turn at ingest; dv changes re-bill only the small tail. Sound — no change needed.
8. Tracer logs only `history[-6:]` as gen input (builder.py:1085) — Langfuse never sees the payload; SQL ledger must pull rag spans + usage details instead.

**iter47 artifacts already on disk:** `research/surgeon/iter47-call-ledger/ledger.db` (branches/commits/runs/calls, 90 branches, 142 commits, 89 calls, TTFT/cache enriched) + `live_calls_pinned.json` + `06_live_baseline_compare.md`. Branch `engine/iter47-call-ledger` @ `fd997e5` (call_ledger.py + tests only, no engine changes).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Commit A = fixes 1+2+3 (RAG query truth) | owner confirmed; #2 lives in the same function and without it the cosine stays scaffold-locked |
| Commit B = fixes 4+5 (payload coverage) | owner confirmed ("four, five, six" = 4+5+verify) |
| NO second light LLM call | doubles latency; two responses per turn = the splice/merge bug family; entry rounds already fall back to the cached floor (2,688) — slower, not dumber |
| Entry await split: 500 ms cap on EOT-boundary entries, 100 ms mid-turn | owner confirmed; EOT-boundary rounds have the user's reply window as warm head start; mid-turn loops must not eat 500 ms each |
| Turn-1 lite keeps general-prompt-only head; improvisation rule added to general_prompt.md (2-3 lines) instead of restructuring `_lite_head` | owner design: "if it lands lobotomized, at least it can improvise" — mirror the caller's words, never fabricate |
| Cross-turn dedupe: DEFERRED | owner: main prompt's never-repeat + a fed model covers it; eager-cancel grace A/B is the partial mitigation |
| Sofia slot-loop fix: SEPARATE plan (already SPEC'd in iter47 plan) | not a retrieval bug; VerifyLead is RETRIEVAL_OFF by design |
| Verification ladder: smoke → happy paths (per-turn analysis) → SQL gate → battery(13) — battery ONLY after commit B passes its gate | owner-mandated staging |
| SQL ledger ("live SQL") built in this plan, imported from Langfuse, compared at every gate | owner: "clear roadmap of what we're trying against, see if it was successful or not" |
| T1 = Surgeon Framework audit of this plan (next session, fresh cache) | owner-mandated; execute only when 04_master_plan.md is airtight |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Final wording of the general-prompt improvisation rule | draft in T4 below; owner approves before Commit B |
| gpt-5.x rejection behavior on `max_completion_tokens=16` warm calls | verify empirically in T4 (warm retry logging); if rejected, raise cap to 64 |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter44/.venv/bin/python` (3.12). sqlite3, urllib stdlib. NO new deps.
- Langfuse: self-hosted `:3001`, REST `?limit=100&page=N` (fromTimestamp ignored on this build — paginate + client-side filter). Keys via `.env` (`LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`) — reuse `scripts/call_ledger.py` `lf_env()/lf_get()`.
- `.env` sourcing: `cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a` (OPENAI_MODEL=gpt-5.4, NO FIRST_TURN_LITE line — code default True applies).
- Ports: test server :8007 ONLY (append-log `/tmp/opencode/uvicorn_8007_iter44.log`, NEVER `>`). NEVER :8000-:8006, live agent IDs, slots.db, Cal.com event 3801235.
- Harness: `.venv/bin/python tests/llm2llm/harness.py --personas <Name> --rag --langfuse --max-turns 28`
- Surgeon folder: `research/surgeon/iter48-rag-truth/` (01_audit → 04_master_plan per framework).

## Architecture (one block)
```
f5c0912 (iter42: entry retrieval = real user msg)
   └─ iter44/46 "optimization" replaced it: prefetch("[state: X] ") → frozen-empty visits
        └─ engine/iter48-rag-truth (from 515f81f)
             ├─ COMMIT A (RAG truth): refer_query anchor branch + drift vectors cleaned
             │                        + empty-freeze guard removed
             ├─ [smoke → happy(4) → SQL gate G1-G2]
             ├─ COMMIT B (payload): general-prompt improvisation rule + await split 500/100
             │                    + warm WARNING/retry + cap verify
             ├─ [smoke → happy(4) → SQL gate G3-G4 → compare vs A snapshot]
             ├─ battery first-13 → SQL gate G5 → report → ASK
             └─ live :8007 (owner drives) → gate G6 → final report
Langfuse :3001 ──REST──► scripts/live_sql.py ──► research/surgeon/iter48-rag-truth/ledger.db
```

## File Map
| File | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter44/diallux/graph/builder.py` | `refer_query` empty-user branch (state anchor, ~688-702); drift query recipe (~625); `_drift_check` guard removal (612-617); entry await split (~838) | Edit |
| `/tmp/opencode/wt-iter44/diallux/prompts/general_prompt.md` | +2-3 line improvisation rule (T4 draft) | Edit |
| `/tmp/opencode/wt-iter44/agent/llm.json` | sync general_prompt copy (byte-parity with .md) | Edit |
| `/tmp/opencode/wt-iter44/diallux/graph/llm.py` | warm failure → WARNING + lite warm retry (~223) | Edit |
| `/tmp/opencode/wt-iter44/diallux/config.py` | `prewarm_entry_wait_ms` → split into `prewarm_entry_wait_ms` (mid-turn, 100) + `prewarm_entry_wait_eot_ms` (500) | Edit |
| `/tmp/opencode/wt-iter44/tests/test_iter48_rag_truth.py` | NEW: anchor query, drift vectors, empty-freeze rescue, await split, prompt rule presence | New |
| `/tmp/opencode/wt-iter44/scripts/live_sql.py` | NEW: Langfuse → SQLite import (runs/calls/rounds/rag tables) + gate queries | New |
| `/tmp/opencode/wt-iter44/tests/test_live_sql.py` | NEW: hermetic import/gate tests | New |
| `research/surgeon/iter48-rag-truth/*` | 01_audit.md … 04_master_plan.md, ledger.db, 05_battery_report.md, 06_live_report.md | New (evidence, gitignored) |

## Deploy Rules
- Commits on `engine/iter48-rag-truth` only. NO merge/push without owner (LAW 0).
- :8007 relaunch (append-only):
  ```bash
  cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && \
    setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8007 \
    >> /tmp/opencode/uvicorn_8007_iter44.log 2>&1 < /dev/null & disown
  ```
- After any live session: cancel ALL test bookings (Cal.com 3801235 is REAL). Langfuse server: never restart.

## Tasks (in order)

### T1 — Surgeon Framework audit of THIS plan (next session, fresh cache) — ✅ DONE 2026-09-12
Goal: airtightness before any code. Produce, in `research/surgeon/iter48-rag-truth/`:
`01_audit.md` (re-read every touched function against real line numbers — `refer_query`,
`_stage_rag`, `_drift_check`, `_warm`/`_await_warm`, `warm_rag`/`warm_rag_async`, session.py
greeting block, `_lite_head`; document EXISTS vs MISSING), `02_action_plan.md` (this plan's
fixes as step-by-step code patterns), `03_cross_reference.md` (does the plan address every
audit finding? does the audit support every change?), `04_master_plan.md` (all flaws
resolved; archive sources). **Execute only when 04 has zero open issues + owner approval.**
Verification: 4 files exist; every claim traced to a line number; contradictions resolved.

**MASTER PLAN REFERENCE (follow to the letter):** T1 is complete — all four surgeon files
exist in `research/surgeon/iter48-rag-truth/` (plus `PREFLIGHT_notes.md` + `archive/`),
zero open issues. **For ALL code changes (Commits A + B), follow
`research/surgeon/iter48-rag-truth/04_master_plan.md` TO THE LETTER** — its R1-R8
resolutions and M1-M15 steps supersede this plan's code wording where they differ
(the audit found 4 new flaws + 2 ambiguities; all resolved there; every forensics claim
here was verified code-TRUE). Non-code tasks (T3/T5/T6 gates, battery, live, deploy rules)
remain governed by THIS plan as written. Execution gates unchanged: owner approval of the
improvisation-rule wording (before Commit B) + owner go-ahead (before M1).

### T2 — Branch + Commit A (fixes 1+2+3)
Goal: RAG query truth. (1) `refer_query`: empty `user_msg` → build from refer tags + dv
values (state's own anchor), never the bare `"[state: X] "`. (2) Drift vectors: round query
+ base query = caller text + refer whats ONLY (no state tag, no labels, no empty-dv join).
(3) Remove `_drift_check` base-vec-None early return → empty freezes rescuable on first
real message. Unit tests in `tests/test_iter48_rag_truth.py` pin all three.
Commands: `cd /tmp/opencode/wt-iter44 && git checkout -b engine/iter48-rag-truth 515f81f` →
edits → `.venv/bin/python -m pytest tests -q --tb=no -p no:warnings` (expect 282+new green)
→ commit.
Verification: suite green; new tests pin: prefetch query contains refer whats; empty freeze
rescued in one round; drift cosine moves on intent change.

### T3 — Smoke + happy paths + SQL gate (Commit A)
Goal: prove A on real runs before B.
- Smoke: one Maria harness run, then
  `.venv/bin/python scripts/live_sql.py import --window <HH:MM-HH:MM> --run smoke-a --commit <sha>`.
- Happy: 4 happy personas (Maria, Danny, Susan, Marcus), one run each; import each as
  `happy-a-<persona>`.
- Per-turn analysis: `scripts/live_sql.py` prints per-call round table (state/ttft/cache/chunks).
**Gate G1-G2 (SQL, pinned):** G1: zero 0-chunk state-entries across Intake/Discovery/Closer/
Offer in the 5 runs; G2: no are-you-ai chunk in any round whose caller text matches
`%do you guys do%/%what do you do%`; happy 4/4 pass.
Verification: gate queries (embedded in `live_sql.py gates` subcommand) return expected values.

### T4 — Commit B (fixes 4+5) + smoke + happy + SQL compare
Goal: payload coverage. (4) Improvisation rule into `general_prompt.md` + `agent/llm.json`
parity (draft below, owner approves wording first). (5) Await split:
`prewarm_entry_wait_eot_ms=500` on turn-boundary entries / 100 mid-turn; warm failures →
WARNING + lite warm retry once; verify/raise the 16-token cap (T6 logging shows it).
Draft (wording for approval):
```
# Improvising before you have context
If you don't yet have the context your flow needs for its next scripted question, never
fabricate one. Mirror the caller's own words and ask ONE natural follow-up about exactly
what they said — what did they say about us, what caught your attention, what made today
the day you called. Their words, one question, then listen.
```
- Smoke + happy 4/4 again (runs `happy-b-*`), import, **compare vs `happy-a-*` snapshot**
  (same queries, side-by-side).
**Gate G3-G4:** G3: turn-1 `cache_read > 0` in ≥3/4 happy calls (lite warm lands); cache-0
rounds ≤1 per call. G4: steady TTFT p50 ≤950 ms per call, turn-1 ≤1,000 ms; A's G1-G2 still
hold (no regression).
Verification: `live_sql.py gates --compare happy-a happy-b` prints PASS/FAIL per gate.

### T5 — Battery first-13 + SQL gate + report + ASK
Goal: full battery on the two-commit branch. Run first-13 per SOP (happy first, stress
after), import as `battery-iter48`.
**Gate G5:** ≥11/13 (Pedro expected fail; Sofia expected to still loop — her fix is a
separate plan); **no NEW failure vs iter44/46 baseline**; Offer 0-chunk freeze = 0 across
all calls; per-call TTFT/cache table vs battery-B/D rows from iter47's ledger.db
(reference join on persona). Cancel all mock bookings. Report
`research/surgeon/iter48-rag-truth/05_battery_report.md` + ASK (merge? live reference?).

### T6 — Live reference on :8007 (owner drives)
Relaunch :8007 on the branch HEAD. Owner asks "what do you guys do" early in Intake.
**Gate G6:** the answer is the pitch (head), not the are-you-ai script; turn-1
cache_read > 0; turn-1 TTFT ≤1,000 ms; rag span shows state-anchored Intake chunks.
Final report `06_live_report.md` + ASK (merge decision).

## Validation Plan (end-to-end)
1. T1 surgeon docs airtight (zero open issues) before any code.
2. Every commit: full suite green.
3. Every stage gated by SQL ledger queries (G1-G6) — no "feels okay" judgments; every gate
   query is a pinned `live_sql.py gates` invocation.
4. Battery only after B passes its gate; live only after battery.
5. NO merge/push without owner say-so (LAW 0).

## The SQL/Langfuse logic (import → why → referenced against)

| We import from Langfuse | Into table | Why | Referenced against |
|---|---|---|---|
| GENERATION observations (per LLM round): `ttft_ms`, `cache_read`, input/output tokens, state | `rounds` | latency + cache proof per round | G3 (turn-1 cache>0), G4 (TTFT p50s) |
| `rag` + `rag:drift` spans: chunks, kbs, query, prefetched, frozen_reuse, cosine, delta_chunks | `rag` | KB-retrieval truth per state visit | G1 (entry chunks>0), G2 (no wrong-KB redirect), G5 (Offer freeze=0) |
| harness json_logs (pass/turns/outcome) + trace scores | `calls`, `runs` | quality rows | G5 (≥11/13, no new failures vs iter44/46 ledger rows) |
| Reference baseline | iter47's `ledger.db` battery-B/D rows (already enriched) | apples-to-apples per-persona TTFT/cache/chunks before-vs-after | every gate |

Nothing is judged by feel: each gate is a named SQL query in `scripts/live_sql.py`, run at
a named stage, printing PASS/FAIL.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Sofia slot-loop fix (engine slots injection) | separate plan, SPEC'd in iter47 |
| Cross-turn dedupe / eager-cancel double-speak | owner deferred; grace A/B partial mitigation |
| Cache growth 2,688 → ~5k (D1/D2: shared-prefix reorder, state-block per-visit) | separate iteration; compatible with this plan |
| Marker-splice fix (filler `<...>` joins) | separate analysis (iter47 plan T5) |
