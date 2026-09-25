# PLAN — iter47: call ledger (SQLite) + branch/test tree + live TTFT reference + Sofia/marker forensics

## Meta
- Date: 2026-09-11
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Worktree: `/tmp/opencode/wt-iter44` (folder name inherited from iter44 — the branch is
  `engine/iter46-latency-floor`, HEAD `515f81f`; verify with
  `git -C /tmp/opencode/wt-iter44 branch --show-current`)
- New branch: `engine/iter47-call-ledger` (created from `engine/iter46-latency-floor` HEAD)
- Owner goal: (1) a SQLite ledger of EVERY iteration/branch/commit/test-run/battery with
  latency + verdict + "why we moved on", queryable; (2) an ASCII tree of the same; (3) a
  HUMAN-IN-THE-LOOP live-call session on :8007 of the shipped commit to establish the live
  TTFT reference; (4) deep forensics on the Sofia slot-loop bug and the filler-marker splice
  bug, ending in a written fix spec (implementation is a SEPARATE later plan).
- Every step is HUMAN-IN-THE-LOOP: nothing merges, nothing deploys, live calls only happen
  when Julio is driving the browser.
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context (session state as of 2026-09-11, post-iter46)

### Where things stand
- iter46 (`engine/iter46-latency-floor`, 6 commits, NOT merged) implemented the latency-floor
  plan `plans/plan_iter46_latency_floor.md`: T2 async RAG drift lane, T3 lite warm for turn 1,
  T4 transition prewarm (fire-at-detection + post-patch dvs + bounded entry await), T5
  fast-first-flush, T6 mic 50 ms chunks, T7 grace window (DEFAULT OFF), D5 per-state verbosity.
- T1 (verbosity=low) was REVERTED (commit `7141a2a`): the eval ladder stalls the
  contact_details ask at low (H1 fix-2, pre-agreed). Default = `medium` (iter44 behavior).
  D5 (`verbosity_states_medium`) shipped and is a no-op at the medium default.
- Quality: pytest suite 256/256 · hermetic eval 6/6 · battery first-13 12/13 (baseline level;
  Pedro = the known marginal, fails at turns=23 in BOTH verbosity configs — byte-identical to
  the iter44 baseline). Sofia's one 48-turn variance miss (Battery D only).
- Latency (shipped config, Battery D + ladder): **turn-1 TTFT p50 848 ms (min 601)** — the
  ≤1,000 ms mark HIT · steady TTFT p50 892 (5% over the ≤850 target — the medium-revert tax;
  D1/D2 in iter48 recover it) · cache hit 93% of rounds (p50 2,688 tok = the audit's floor) ·
  e2e (brain turn) p50 2,177 (Battery D) / 1,498 (ladder).
- NOT yet done: the 2 live mic calls on :8007 (owner drives), merge decision, grace A/B
  (`EAGER_RESUME_GRACE_MS=200`), D1/D2/D3 decisions. The ASK is open.

### The two quality criticals (analyzed to root cause, fixes SPEC'd but NOT implemented)
1. **Sofia-D slot loop (THE bug)** — 48 turns, ended=False, `phaseb:chain_abort` ×26 on
   `verify_lead_data` with `{"problems":[{"field":"selected_time","issue":"unfixable_format"}],
   "actions":["Say: 'Sorry, I lost track - which slot did you pick?'"]}`. Chain:
   model extracted `selected_time="tomorrow at 3 PM Central"` WITHOUT ever calling
   `query_livecall_slots` (0 slots queries; `requested_slot=None`) → `validate_lead` asserted
   `slot_verified=True` vacuously (its containment check is `if slot_options and not
   contained(...)` — EMPTY menu SKIPS the check) → `verify_lead_data` correctly returned
   `unfixable_format` 26× but its prescribed Say-line asks the caller a question the caller
   had just answered ("3 PM"), and the model had no menu to re-offer → dead-end loop until
   the 48-turn cap. Engine already held the menu: `slots_prefetch` fired 4× into
   `self._slots_warm` (iter40 L2, payload = the exact `query_livecall_slots` response, TTL
   120 s). PRE-AGREED FIX (owner approved direction): on chain abort with empty
   `requested_slot`, the ENGINE injects `requested_slot = slots["slots_human"]` +
   `slot_reservation_uids` from the warm store (0 ms, no webhook) or a bounded live re-query,
   so the model re-offers HUMANLY ("3 PM's taken — I have tomorrow at 1 pm or 2:30 pm, which
   works?"). ~30-40 lines in the Phase B abort path + regression test. NOT yet implemented.
2. **Filler-marker splice bug** — prompts render fillers inside `<angle-bracket>` markers and
   command "Write it as ONE complete sentence. NEVER splice sentences together without a
   space". Violations observed: Sofia-D t25 "let me lock that in real quick.Great — booking
   that for you as we speak." (two `<...>` fillers spliced); Marcus-D t30 "Perfect, thanks.
   Thanks. One sec while I lock...One sec — finishing that up."; the dedupe layer cannot
   catch these (different bytes). Root problem to analyze: marker-adjacent filler generation
   + engine filler insertion interleaving with model fillers.

### Batteries and runs (the ledger's primary rows — mtime windows pinned)
All call logs: `/tmp/opencode/wt-iter44/tests/llm2llm/json_logs/*.json` (one json per call,
mtime = run end time, local = UTC on this box). Langfuse: self-hosted `:3001`, SDK 4.15.1,
REST via `scripts/lf.py` `_env()/_get()` (trace names `llm2llm-graph-<slug>@<HH:MM:SS>`,
UTC timestamps). Pre-session baseline traces: bookmaria@05:56/06:43/06:56/07:19 (iter44 era).

| Run | Window (mtime) | Config | Result | Latency (per-turn e2e p50 / TTFT p50 / turn-1 / cache) |
|---|---|---|---|---|
| Battery A | ~13:47 | — | CLI persona-flag failure (harness takes ONE group/substring, not comma list) | none |
| Battery B | 13:57-14:10 | iter46 flags + verbosity LOW | 12/13 (Pedro only) | e2e 2,121 · 375 rounds · TTFT 849 · turn-1 799 · cache 86% |
| Ladder A (happy stage) | 14:12-14:16 | LOW | happy 3/4 → SOP STOP | Maria 15t 1,438 ✓; Danny/Susan/Marcus 28t stalls |
| Bisect 1 | 14:22-14:27 | flush OFF | happy 2/4 → T5 NOT the cause | Maria spike 54,941 |
| Bisect 2 | 14:30-14:34 | MEDIUM | happy 4/4 → T1 verbosity=low WAS the cause | e2e 2,4-2,6 |
| D5 ladder (happy stage) | 14:45-14:49 | medium on late states | happy 3/4 → SOP STOP | stalls persist in Intake/Discovery at low |
| Ladder post-revert (ALL stages) | 15:01-15:25 | shipped (medium) | 20/25, first-13 12/13 | e2e 1,498 · TTFT 892 · turn-1 848 · cache 93% |
| Battery C (CORRUPT) | 15:36-15:42 | — | concurrent-write junk, EXCLUDED | 4 happy rows only |
| Battery D | 15:51-16:07 | shipped | 11/13 (Pedro + Sofia 48t) | e2e 2,177 · 421 rounds · TTFT 934 · turn-1 981 · cache 91% |

Per-persona latency (Battery B | Battery D, e2e p50 ms / TTFT p50 / cache%):
Maria 2,688/837/62% | 3,324/937/93% · Danny 2,212/854/80% | 2,336/992/86% ·
Susan 2,578/835/86% | 2,616/946/88% · Marcus 2,267/813/88% | 1,779/900/96% ·
Carlos 1,522/845/93% | 1,454/965/94% · Pedro 2,002/865/90% | 2,132/908/86% ·
Sofia 2,458/835/90% | 2,607/970/98% · Jorge 1,532/910/89% | 1,570/937/94% ·
Daniel 1,574/851/91% | 1,467/1,030/71% · Brenda 2,311/859/92% | 1,608/909/92% ·
Gene 2,252/881/86% | 1,583/865/87% · Frank 1,267/833/89% | 1,523/935/90% ·
Ray 1,374/820/83% | 1,336/881/83%.

### Commit ledger (branch `engine/iter46-latency-floor`, parent `engine/iter44-cache-floor`)
| Commit | Content | Files |
|---|---|---|
| `4e412c8` iter46 baseline | carries iter44's uncommitted telemetry work (TTFT usage_details, append-only delta, lite default ON, mic heartbeat) | 20 files |
| `8ee8d59` T1-T7 | ALL flag code: async drift lane, lite warm, transition warm (T4a/b/c), fast-first-flush, mic 800, grace window | config.py, graph/llm.py, graph/builder.py, media/session.py, static/mic/index.html, fake_llm.py, + tests/test_iter46_latency_floor.py (14 tests) |
| `d98d978` | iter44 drift tests re-pinned to async contract | tests/test_iter44_cache_floor.py |
| `1d6958b` D5 | per-state verbosity twins (H1 fix-1 — did NOT fix ladder) | graph/llm.py, graph/builder.py, 4 test fakes |
| `7141a2a` T1 REVERTED | verbosity back to medium (H1 fix-2) | config.py + 2 test lines |
| `515f81f` evidence | battery report | eval/llm2llm_report.json |
Reports: `research/surgeon/iter46-latency-floor/01_report.md` (latency/flags/revert table),
`02_callsop_audit.md` (26-call CALL-ANALYSIS-SOP audit). Digest: `/tmp/opencode/sop_digest_iter46.txt`.

### Key mechanics pinned (for the Sofia forensics)
- `query_livecall_slots` → `https://slots.diallux-ai.site/check_availability` returns
  `slots_human` ("tomorrow at 1 pm or 2:30 pm") + `slot_reservation_uids`; tool
  `response_variables` maps `slots_human`→`requested_slot` (the menu in the state block).
- Mock (`tests/mock_webhooks.py`): validate_lead's containment gate is conditional
  (`if slot_options and not _contained(...)` → empty menu = SKIP = vacuous pass);
  verify_lead_data: pick not contained (or empty menu) → `unfixable_format` +
  `Say: 'Sorry, I lost track - which slot did you pick?'` — the loop's literal text.
- Phase B chain (`diallux/graph/builder.py` `_deterministic_node`): abort pops `chain_done`
  and re-arms every pass (hence ×26); `_PHASEB_ABORT` includes `unfixable_format`.
- Engine fillers: `builder.py` `_ENGINE_FILLERS` + slots filler
  "One moment while I check availability."; prompt fillers render as `<...>` markers in
  VerifyLead.md/ConfirmSlots.md — the splice bug's surface.
- Engine warm store: `builder.py` `self._slots_warm[date] = {"payload", "ts", "tz"}` —
  iter40 L2, `slots_prefetch` flag, TTL `slots_prefetch_ttl_s=120`.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Ledger = SQLite at `research/surgeon/iter47-call-ledger/ledger.db`, generated by a script, NOT hand-maintained | evidence zone (gitignored); reproducible from json_logs + pinned mtime windows + Langfuse REST |
| Ledger generator script = code on branch `engine/iter47-call-ledger` | LAW 0: code → branch → suite → report → ASK |
| Every DB row for a RUN carries: run id, window, branch, commit, config (flags), score, latency trio (e2e/TTFT/turn-1/cache), verdict line | the owner's ask: "which branch and which commit did they belong to" |
| Live reference calls on :8007 run the SHIPPED commit `515f81f` (medium verbosity) | "the last iter that proved to work on the p50 < 1,000" = turn-1 848 / 981 |
| Sofia fix = ENGINE-SIDE slots injection on abort (owner's design), NOT a prompt re-ask | owner: re-asking feels less human; the warm store already holds `slots_human` |
| Fix implementation is a SEPARATE plan (iter48); this plan only delivers the forensics + spec | owner wants to analyze code in depth first; human-in-the-loop at each step |
| The filler-marker splice analysis is in-scope for this plan (analysis only) | the `<...>` splice ("real quick.Great —") appeared 3× in Battery D |
| :8000-:8006, live agent IDs, slots.db, Cal.com event 3801235 NEVER touched | AGENTS.md law |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Julio present to drive the browser mic for the live calls (T3) | owner says "go" |
| Whether `EAGER_RESUME_GRACE_MS=200` A/B runs during T3 or later | owner decides at T3 |
| Larry the assassin run? | owner only, `--assassin`, once, never batched |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter44/.venv/bin/python` (3.12). sqlite3 = stdlib. NO new deps.
- Langfuse: self-hosted `:3001` (docker). Keys via `scripts/lf.py _env()` (reads `.env`:
  `LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`). NOTE: the REST list endpoint ignores
  `fromTimestamp` params on this build — paginate `?limit=100&page=N` and filter client-side.
- `.env` sourcing: `cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a`
  (contains OPENAI_MODEL=gpt-5.4, CARTESIA_SPEED=1.12, DEEPGRAM_EAGER_EOT=true;
  NO OPENAI_VERBOSITY line — code default medium applies).
- Ports: test server :8007 (append-log pattern below). NEVER :8000-:8006.
- Ports of evidence: `/tmp/opencode/uvicorn_8007_iter44.log` (iter44/45 era, append).
- json_logs: `/tmp/opencode/wt-iter44/tests/llm2llm/json_logs/*.json`.
- Surgeon: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter46-latency-floor/`
  (01_report.md, 02_callsop_audit.md) — read-only inputs.

## Architecture (one block)
```
git (89 branches: snap era → engine/iter25 … engine/iter46) ─┐
ITERATIONS.md (iteration ledger) ────────────────────────────┤
research/surgeon/* (per-iter reports) ───────────────────────┼─► scripts/call_ledger.py build
json_logs/*.json (mtime windows) ────────────────────────────┤        │
Langfuse REST (:3001, paginated) ────────────────────────────┘        ▼
                                              research/surgeon/iter47-call-ledger/
                                              ├─ ledger.db (branches, commits, runs, calls)
                                              └─ tree.md (E3 ASCII, full chronology)
uvicorn :8007 (515f81f) ── browser mic (Julio) ── turn reports ──► ledger.db (kind=live rows)
Sofia forensics: trace llm2llm-graph-booksofia@15:58:02.769Z + mock_webhooks.py + VerifyLead.md
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter44/scripts/call_ledger.py` | ledger generator: scans json_logs (mtime windows pinned in the script as data), queries Langfuse per-trace TTFT/cache, emits SQLite + tree.md | NEW |
| `/tmp/opencode/wt-iter44/tests/test_call_ledger.py` | unit tests: schema, window bucketing, run attribution, tree rendering | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` | the database (artifact, regenerated) | NEW (generated) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/tree.md` | E3 ASCII tree: branches → commits → runs → calls, with verdict lines | NEW (generated) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/03_sofia_forensics.md` | Sofia deep-dive: trace evidence, 26 aborts, the 3 holes, fix spec (engine-side injection), Marcus-D dance | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/04_marker_splice.md` | filler-marker splice analysis: the 3 observed splices, why dedupe can't catch them, fix options | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/05_live_reference.md` | live-call TTFT results (T3), the reference table | NEW |
| `/tmp/opencode/uvicorn_8007_iter44.log` | live-call log (APPEND ONLY — never `>`) | edit (append) |

## Deploy Rules
- Test server relaunch (NEVER `>`, always `>>`; always with `.env` sourced):
  ```bash
  cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && \
    setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8007 \
    >> /tmp/opencode/uvicorn_8007_iter44.log 2>&1 < /dev/null & disown
  ```
- Grace A/B relaunch (owner-approved only): prefix `EAGER_RESUME_GRACE_MS=200` on the uvicorn line.
- Commits on `engine/iter47-call-ledger` only. NO merge, NO push, NO git-tree.sh without owner.
- After any live session: cancel ALL test bookings (Cal.com event 3801235 is REAL) — battery
  runs used mock slots, live calls may book REAL.
- Langfuse server itself: never restart/touch; read via REST only.

## Tasks (in order)

### T1 — Ledger DB + generator (`scripts/call_ledger.py`) — FULL HISTORY, ALL ITERS
Goal: one SQLite DB answering "which branch/commit produced which run/call and why we moved
on" — for EVERY iteration, not just iter46. The repo carries 89 branches:
`engine/iter25-a` → `engine/iter46-latency-floor` (25 engine/iter* branches), the
`engine/snap-*` photocopy era, `history/*` refs — all in scope as branch rows; commits from
`git log`; iteration narratives from `ITERATIONS.md`; run evidence from json_logs mtime
windows + Langfuse + the surgeon report folders.
Schema (minimum):
- `branches(name, kind[engine-iter|snap|history|main], parent, head_commit, first_iter,
  last_iter, status, summary_line)` — ALL 89 from `git branch -a`; summary_line from
  `ITERATIONS.md` where present (e.g. "engine/iter44-cache-floor: cache floor + drift",
  "engine/snap-*: photocopy era, read-only archaeology").
- `commits(sha, branch, date, subject, files_touched, summary_line)` — every commit on
  every engine/iter* branch via `git log <branch>` (first-parent), ~150+ rows expected.
  The per-commit summary = the commit subject (they are already one-line narratives).
- `runs(run_id, window_start, window_end, kind[full-battery|ladder|bisect|corrupt|live],
  branch, head_commit, config_flags, score, e2e_p50, ttft_p50, turn1_ttft_p50, cache_pct,
  verdict_line, evidence_paths)` — iter46's 9 runs pinned verbatim from this plan;
  older iterations get rows ONLY where evidence exists (surgeon report + ITERATIONS.md
  line + json_logs surviving); missing metrics = NULL + verdict from the report text.
- `calls(run_id, json_path, persona, slug, outcome, expect, pass, turns, ended,
  gate_rejections, tools, transitions, e2e_p50, ttft_p50, cache_pct, langfuse_trace_id,
  notes)` — iter46 runs fully populated (26+25+8+4 calls); older runs as far as json_logs
  and reports allow (many were overwritten — note that honestly).
Sources to scan (in order):
1. `git -C /tmp/opencode/wt-iter44 branch -a` + `git log` per branch.
2. `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` — the iteration ledger
   (one line per merged iteration).
3. `/home/julio/projects/clean_diallux_SDR/research/surgeon/` — folder inventory; one
   row per report folder (iteration, report path, dates).
4. `/tmp/opencode/wt-iter44/tests/llm2llm/json_logs/*.json` — mtime windows (pinned
   windows for iter46 in-script; older files bucketed by mtime day and flagged
   attribution-confidence=low).
5. Langfuse REST (paginate `?limit=100&page=N`, client-side filter) — per-trace
   TTFT/cache where traces survive (iter46 era guaranteed; earlier eras opportunistically).
Commands:
```bash
cd /tmp/opencode/wt-iter44 && git checkout -b engine/iter47-call-ledger && \
  .venv/bin/python scripts/call_ledger.py build \
    --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db
```
Dependencies: T0 (branch). Verification:
```bash
sqlite3 <db> "SELECT count(*) FROM branches;"     # expect 89
sqlite3 <db> "SELECT count(*) FROM commits;"      # expect 150+ (every engine/iter* commit)
sqlite3 <db> "SELECT count(*) FROM runs;"         # expect ≥ 9 (iter46) + older rows where evidenced
sqlite3 <db> "SELECT count(*) FROM calls;"        # expect ≥ 84 attributed (iter46 era) + older where surviving
sqlite3 <db> "SELECT run_id, verdict_line FROM runs;"
sqlite3 <db> "SELECT name, summary_line FROM branches WHERE kind='engine-iter';"
```

### T2 — E3 ASCII tree (`tree.md`)
Goal: the owner's visual — ALL iterations → branches → commits → runs → calls, one
verdict line per branch and per run. Structure: chronology first (snap era → iter25 →
iter46), each engine/iter* branch shows its head commit + ITERATIONS.md summary + the
runs that evidence it; the iter46 sub-tree expands to all 6 commits + 9 runs + per-call
rows. Include the "why we moved" lines: T1 reverted because…, D5 no-op because…, Battery C
excluded because… — and the evolution story the owner wants to read (iter25 → iter46).
Dependencies: T1. Verification: `cat tree.md` shows every engine/iter* branch with its
head commit + verdict; the iter46 sub-tree shows all 6 commits + 9 runs.

### T3 — LIVE TTFT reference on :8007 (HUMAN-IN-THE-LOOP)
Goal: Julio drives 2-3 live browser-mic calls on the SHIPPED commit; measure turn-1 TTFT
live (the reference for all future work).
Steps:
1. Confirm HEAD is `515f81f` on `engine/iter46-latency-floor` (`git log --oneline -1`).
2. Relaunch :8007 per Deploy Rules (append log). Verify: `curl -s localhost:8007/health`
   and `tail -1 /tmp/opencode/uvicorn_8007_iter44.log`.
3. JULIO opens the mic page (:8007/mic) and makes the calls; agent watches the log live.
4. After EACH call: extract `round usage` + `turn N report` + `turn N final report` lines
   for that call from the log; insert a `runs` row (kind=live) + `calls` rows into the DB.
Gate: turn-1 TTFT ≤ 1,000 ms and cache_read > 0 on turn 1; steady p50 ≤ 850 desirable
(medium config — honest expectation ~850-950). Grace A/B (EAGER_RESUME_GRACE_MS=200) only
if Julio says so at relaunch 2.
Dependencies: T1 (DB ready), Julio present. Verification: `03 rows in ledger with kind=live`;
`03_live_reference.md` table written.

### T4 — Sofia forensics doc (`03_sofia_forensics.md`)
Goal: the complete machine autopsy, evidence-pinned, so iter48's fix plan can be written
without re-deriving. Contents: the 26-abort trace dump (from
`llm2llm-graph-booksofia@2026-09-11T15:58:02.769Z`), the three holes (0 slots queries /
validate_lead vacuous pass / dead-end Say-line), the warm-store injection fix spec with
exact code locations (`builder.py` abort path, `_slots_warm` read, `dvs_patch` injection),
the Marcus-D dance (9-turn hand negotiation, slots query only at t28), and the regression
scenario spec for the suite.
Dependencies: T1 (trace IDs in DB). Verification: doc contains the verbatim abort JSON ×1
sample + the fix spec + "expected behavior after fix" walk-through.

### T5 — Marker-splice analysis (`04_marker_splice.md`)
Goal: understand the `<...>` filler splice bug. Observed: Sofia-D t25
"real quick.Great — booking", Marcus-D t30 "thanks. Thanks. One sec...One sec — finishing",
Frank-B t7 verbatim repeat. Analyze: prompt marker format (VerifyLead.md/ConfirmSlots.md),
engine filler insertion (`_ENGINE_FILLERS` interleave), why the iter42 dedupe window cannot
catch different-byte splices, and 2-3 fix options (join-space guard in `sentence_gate`/
`speak_chunk`; prompt marker removal; engine filler suppression when a model filler
preceded). NO implementation.
Dependencies: T4. Verification: doc lists every observed splice with turn numbers + the
mechanical reason dedupe missed it.

### T6 — Report + ASK
Goal: `05_report.md` in the surgeon folder + the ASK: (1) approve iter46 merge NOW or after
the fix branch? (2) live-reference numbers accepted? (3) green-light the iter48 Sofia-fix
plan (engine-side injection)? (4) D1/D2/D3 sequencing.
Dependencies: T1-T5. Verification: ASK answered in chat by Julio.

## Validation Plan (end-to-end)
1. T1: DB exists, **89 branches, 150+ commits, ≥9 runs, ≥84 attributed calls**, every row has branch+commit+verdict (older-era rows honestly marked NULL/attribution-confidence).
2. T2: tree renders; `pytest tests/test_call_ledger.py` green.
3. T3: live rows recorded; turn-1 TTFT ≤ 1,000 ms live or the miss documented honestly.
4. T4/T5: forensic docs complete; NO code changes to the engine in this plan.
5. NO merge/push/live-agent changes without Julio's say-so.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| iter48 Sofia fix (engine slots injection + validate gate + Say-line re-offer) | owner analyzes T4 first; separate plan + branch |
| iter48 marker-splice fix | owner analyzes T5 first |
| D1/D2 (shared-prefix reorder + state-block per-visit) — steady p50 892→765 + p90 goal | iter48+ |
| D3 local embedder (fastembed bge-small) | owner un-holds it |
| Grace default 200 | after live A/B |
| Larry assassin run | owner-only, once |
