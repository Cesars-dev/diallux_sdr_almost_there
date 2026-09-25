# iter33 — OTEL tail-loss fix + Maria re-run + first-13 battery

## Meta
- Date: 2026-09-08
- Project root (fork): `/home/julio/projects/clean_diallux_SDR`
- Engine worktree (branch): `/tmp/opencode/wt-iter33` on ref `engine/iter33-phaseb-engine-chain`
- Scope: fix the Langfuse tail-observation loss so every battery turn is measurable, re-run the Maria smoke to prove it, then run the Phase B first-13 battery (gpt-5.2) with full 3-SOP audit; if green, repeat the SAME assessment on a model-only gpt-4.1 branch; final compare table + verdict.
- Status: PLAN ONLY (not started — awaits Julio approval).
- HARD CAP: exactly 2 iterations — iter33 (gpt-5.2) + iter34 (gpt-4.1, model-only change). No further branches, no scope creep. Any fix + re-run happens ON the same branch, committed, and documented in the report (what broke, what changed, re-run numbers).

## Compaction Context
Project: LangGraph port of the Dialux SDR chat agent ("Linda"), 9-state machine
(Intake→Discovery→Closer→Offer→contact_details→ConfirmSlots→VerifyLead→Booking→Closing),
worked in the fork `/home/julio/projects/clean_diallux_SDR` on branch ref
`engine/iter33-phaseb-engine-chain` (worktree `/tmp/opencode/wt-iter33`), off `596f1bb`
(= `engine/iter32-silent-round-gate` tip). Model gpt-5.2, mock slots, venv
`/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12).

What is DONE (committed on the branch, suite 141/141 green):
- c74b072: plan port (plans/plan_v5_iter33_phaseb_engine_chain.md +
  reports/phaseb-engine-chain/04_master_plan.md + archive/01-03).
- d2fc37f (U1-U3): `phaseb_chain` Settings flag, `chain_done/chain_aborted_step/chain_aborted_msg`
  typed dvs, `_ENGINE_FILLERS` pool + `_PHASEB_ABORT/_PHASEB_SLOW` + `_chain_args`.
- 2c29199 (U4-U5 + fix): engine-owned booking chain in `_deterministic_node` (resumable 8-step
  plan, fillers via tts_token, abort→model repair), abort clears in state_node.
- 683978d (U6-U7): test_v2 happy path trimmed (F12), 8 new tests/test_phaseb_chain.py.
- Maria smoke (live gpt-5.2, mock slots): PASS book, ended=True, 20 turns. Engine booked it:
  fillers audible in transcript, 0 VerifyLead/Booking LLM gens, chain_done=True, single booking
  attempt, gate_rejections=0, booking_uid=qeTqHuZ1EDzH8bxEdhPQ6H.

Two plan gaps fixed during implementation (documented in commits, both would have crashed the graph):
- `fillers_said: list[str]` added to GraphState (plan referenced the channel, never created it).
- Plan's `"chain_aborted"` return key dropped (not a GraphState channel; abort surface lives in dvs only).

The problem this plan solves (measured 2026-09-08): the Maria smoke's Langfuse trace
`ea562555fe8d55bea84b26d8e64769a6` ends at turn 18 — the booking turns' ~2 gens, ~9 chain TOOL
spans and the `phaseb:chain_ok` span never arrived, although `tracer.finish()` calls `flush()`.
Proven NOT engine behavior: (a) hermetic probe with real tracer delivers the full trace incl.
`phaseb:chain_ok` + all 9 tool spans + post-chain gen; (b) pre-chain iter32 battery traces
(10:19–10:27 window, 13 traces) all have complete Booking/Closing tails. Working theory:
OTEL batch-exporter race — process exits before the in-flight tail export lands. Battery meters
(state_latency.py/silent_rounds.py/latency.py) would undercount tails ~6% without the fix.

Resolved facts for the fix: Tracer.finish() ends root + flushes (diallux/observability/tracer.py:143).
Harness creates one Tracer per persona, scores, finishes (tests/llm2llm/harness.py:595-611).
Trace REST names are EMPTY (SDK sees them; REST `name` filter fails) — meters must pull by window
and filter client-side. scripts/state_latency.py is UNTRACKED in the original worktree only
(`/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5/scripts/state_latency.py`)
— copy for read-only use, NEVER commit. Fork engine/.env holds OPENAI_API_KEY, LANGFUSE_*,
DATABASE_URL (copy to worktree root, gitignored, NEVER commit). Mock slots default (no real
calendar). df -i / must show free > 50000 before harness runs.

IDs/paths pinned: fork `/home/julio/projects/clean_diallux_SDR`; worktree `/tmp/opencode/wt-iter33`;
venv `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python`; Langfuse
`http://localhost:3001` (LANGFUSE_HOST in .env); smoke trace id above; probe trace
`52444b49ec2bbe40040e3e30e407ef3b`; first-13 SOP order: Maria Danny Susan Marcus Carlos Pedro
Sofia Jorge Daniel Brenda Gene Frank Ray; agent-model gpt-5.2; caller gpt-4o; max-turns 48.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Work stays on `engine/iter33-phaseb-engine-chain` (worktree `/tmp/opencode/wt-iter33`); NO merge/push/main commits without Julio | LAW 0; phaseb plan §4 binding |
| Tracer (`diallux/observability/tracer.py`) + harness (`tests/llm2llm/harness.py`) MAY be edited for the OTEL fix | The phaseb NEVER list predates the tail-loss finding; observability-only, zero call-behavior change; Julio ordered "fix OTEL, I want all data" |
| `diallux/graph/*.py` engine behavior, `agent/llm.json`, `diallux/prompts/**`, `tests/mock_webhooks.py` stay FROZEN | Phase B scope lock; only suite + tracer/harness change |
| Battery = mock slots, sequential, one process per persona via shell loop; ONE battery only | Cost control; no parallel load on Langfuse/self-hosted PG |
| 3-SOP audit per `/home/julio/projects/clean_diallux_SDR/docs/Testing_guidelines/full_call_analysys.md` (digest SDK + OTEL latency, table→summary→relevant info) | Julio-ordered; same structure for both models |
| iter34 = model-only change (Settings default → gpt-4.1), assessed with the IDENTICAL structure | Apples-to-apples model compare; nothing else moves |
| Every modification committed on the branch (explicit paths) so any state is recoverable | Julio: "if you modify anything make sure you add to git so we can go back" |
| Meters read Langfuse by time window, client-side filter (trace REST names are empty) | Proven by the smoke investigation |
| `scripts/state_latency.py` copied from original path for read-only metering, never committed; worktree `.env` never committed | Untracked helpers/secrets stay out of the branch |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None — all keys/paths verified present | — |

## Environment & Dependencies
- Python 3.12 via `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python`; pytest 9.1.1; langfuse SDK 4.15.1 (OTEL-based v4); httpx MockTransport (hermetic); openai (live runs).
- Langfuse self-hosted `http://localhost:3001` (docker); keys LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY in fork `engine/.env`.
- Postgres pgvector `postgresql://diallux:diallux@localhost:5432/diallux` (RAG, `--rag` flag).
- Worktree `/tmp/opencode/wt-iter33` (branch `engine/iter33-phaseb-engine-chain`); `.env` copied from `/home/julio/projects/clean_diallux_SDR/engine/.env`.
- Suite gate: `.venv/bin/python -m pytest tests` → 141 before and after every task.

## Architecture (OTEL tail-loss)
```
harness turn 19-20 (booking gens, 9 chain TOOL obs, phaseb:chain_ok SPAN)
  └─ OTEL BatchSpanProcessor queue → HTTP export → localhost:3001
       └─ tracer.finish() → root.end() + lf.flush() → main() returns → PROCESS EXITS
            └─ in-flight tail export ABORTED (theory) → Langfuse trace ends at turn 18
FIX SHAPE: finish() + blocking server-side confirm (poll trace observations count
until ≥ expected or 60s timeout), harness waits for confirm before exit.
Probe (hermetic, 1 turn, sleep+flush): tail ARRIVED → exporter path works when given time.
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter33/diallux/observability/tracer.py` | blocking confirm in finish() (poll REST observations count; bounded 60s) | Edit |
| `/tmp/opencode/wt-iter33/tests/llm2llm/harness.py` | wait for confirm before per-persona exit (only if tracer exposes it; else sleep 10s fallback) | Edit |
| `/tmp/opencode/wt-iter33/tests/test_otel_tail.py` | hermetic regression test: 3-turn chain run with end_call, assert finish()+confirm path invoked and tail complete (mocked REST) — style: no live keys, FakeLLM + mock_client | New |
| `/tmp/opencode/phaseb_battery.sh` | sequential first-13 loop (SOP order), one harness process per persona, battery window echo | New (in /tmp, never committed) |
| `/tmp/opencode/wt-iter33/reports/phaseb-engine-chain/05_battery.md` + `06_sops_full_call.md` + `07_verdict.md` | battery numbers + 3-SOP audit + verdict (T3–T5) | New |
| `/tmp/opencode/wt-iter33/ITERATIONS.md` + `git_tree.md` | §23 + row (own commit, post-battery) | Edit |
| NEVER touched | `diallux/graph/*.py`, `agent/llm.json`, `diallux/prompts/**`, `tests/mock_webhooks.py`, `eval/llm2llm_report.json` (restore with `git checkout --` if harness ran), prod agent IDs, services/ ports | — |

## Deploy Rules
- No service deploys/restarts. No commits to main. Commit per task on the branch ONLY. Julio reviews before any merge.
- `.env` and `scripts/state_latency.py` in the worktree are UNTRACKED helpers — verify with `git status --short` before every commit; never `git add -A` blindly (use explicit paths).
- One Maria re-run + ONE first-13 battery. No Pedro changes, no prompt changes, no extra harness runs.
- Langfuse pulls read-only. Never print/commit secrets. `bash scripts/keyhound` before any push (push itself needs Julio say-so).

## Tasks (in order)

### T1 — OTEL tail-loss repro + fix
Goal: root-cause the missing tail and land a fix that guarantees complete traces.
Files: `diallux/observability/tracer.py`, `tests/llm2llm/harness.py`, `tests/test_otel_tail.py` (new).
Commands (full, workdir `/tmp/opencode/wt-iter33`):
1. `git status --short` (expect only `?? .env`, `?? scripts/state_latency.py` — else STOP).
2. Repro probe (hermetic, real tracer, ends with end_call + immediate exit, no sleep):
   `set -a; . ./.env; set +a; /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -c "<3-turn FakeLLM chain script ending end_call, Tracer(session_name='llm2llm-probe-tail'), tr.finish()>"` then REST-query the returned trace id for the tail gen + `phaseb:chain_ok` (same query pattern as the smoke investigation).
3. Fix per finding: blocking confirm in `Tracer.finish()` — after `self.flush()`, poll `GET /api/public/observations?traceId=<id>` until count stops growing (2 consecutive equal polls 5s apart) or 60s cap; harness calls it and only then exits. If repro shows tails arrive without any fix (timing flake), land the confirm anyway as the guarantee + regression test.
4. `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m py_compile diallux/observability/tracer.py tests/llm2llm/harness.py`
5. `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests` → 141 + new test count green.
6. Commit (explicit paths only): `git add diallux/observability/tracer.py tests/llm2llm/harness.py tests/test_otel_tail.py && git commit -m "iter33 OTEL: blocking tail confirm in finish() + harness wait + regression test; suite <N>"`.
Dependencies: langfuse SDK 4.15.1; REST creds from worktree `.env` (LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST).
Verification: repro probe's tail (final gen + `phaseb:chain_ok`) present in Langfuse WITHOUT any manual sleep; suite green.

### T2 — Maria re-run (live smoke)
Goal: prove the fix on a live call + re-confirm Phase B behavior.
Files: none (run only).
Commands (full, workdir `/tmp/opencode/wt-iter33`):
1. `df -i /` (free > 50000, else STOP) + `git status --short` (clean except the two `??` helpers).
2. `set -a; . ./.env; set +a; /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 48 --agent-model gpt-5.2`
3. `git checkout -- eval/llm2llm_report.json` (harness overwrites it; never committed).
4. Pull the fresh trace (window query, client-side name match): assert Booking/Closing gens present, `phaseb:chain_ok` span present, chain TOOL spans present, booking-turn wall ≤6s (last-turn gen start → end).
Dependencies: OPENAI_API_KEY (gpt-5.2 agent + gpt-4o caller), mock slots (default; no real calendar).
Verification: PASS book + tail complete + chain_ok + booking turn ≤6s; on chain abort → STOP and report the span payload (no band-aids).

### T3 — first-13 battery + meters (gpt-5.2)
Goal: the measured Phase B gates.
Files: `/tmp/opencode/phaseb_battery.sh` (new, /tmp only).
Commands (full, workdir `/tmp/opencode/wt-iter33`):
1. Write `/tmp/opencode/phaseb_battery.sh`: sequential loop over `Maria Danny Susan Marcus Carlos Pedro Sofia Jorge Daniel Brenda Gene Frank Ray`, each: `set -a; . ./.env; set +a; /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python tests/llm2llm/harness.py --personas <Name> --rag --langfuse --max-turns 48 --agent-model gpt-5.2`; echo battery window start/end UTC.
2. `df -i /` then run it (expect ~2h).
3. `git checkout -- eval/llm2llm_report.json` after.
4. Meters (window = echoed start/end):
   `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/state_latency.py --from <start> --to <end>`
   `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/silent_rounds.py --from <start> --to <end>`
   `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/latency.py --hours 2`
5. Write `reports/phaseb-engine-chain/05_battery.md` (table per persona + gate reconciliation; disclose any tail undercount vs harness json_logs).
Dependencies: same keys as T2.
Verification: 12/13+ PASS · ended 13/13 · gens ≤300 · silent% ≤30 · booking turns ≤6s · turn p50 ≤2.0s · suite still 141.
Gate to T3b: battery 12/13+ AND tail complete on every trace — else STOP, fix + re-run ON the branch (commit + document in 05_battery.md), no new branch.

### T3b — full 3-SOP audit, gpt-5.2 (ONLY if T3 green)
Goal: the CALL / SALES / HUMANIZED quality verdict on the Phase B battery, exactly per
`/home/julio/projects/clean_diallux_SDR/docs/Testing_guidelines/full_call_analysys.md`.
Files: `reports/phaseb-engine-chain/06_sops_full_call.md` (new).
Commands (full, workdir `/tmp/opencode/wt-iter33`):
1. `set -a; . ./.env; set +a; /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py health` (ingest up before trusting trace data).
2. Digest: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/call.py digest --hours <battery-span-hours> --out /tmp/opencode/iter33_sop_digest.txt` (fresh digest, never grade from memory).
3. Latency profile: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py lat --hours <span> --limit 100 --window <HH:MM-HH:MM> > /tmp/opencode/iter33_lat.txt` (aggregate ALL line + per-call table; window widened — trace timestamp is LAST event time).
4. Grade per the 3 SOPs (`CALL-ANALYSIS-SOP.md`, `SALES-ANALYSIS-SOP.md` D1–D7 bands, `HUMANIZED-ANALYSIS-SOP.md` R1–R5) by READING the digest; mechanicals from json_logs.
5. Write `reports/phaseb-engine-chain/06_sops_full_call.md`: TABLE first (one row per SOP × persona with verdicts + p50/p90 columns), then summary, then relevant info (quotes, worst offenders, OTEL aggregate line). Commit it: `git add reports/phaseb-engine-chain/06_sops_full_call.md && git commit -m "iter33: 3-SOP audit gpt-5.2 battery"`.
Dependencies: json_logs from T3 (`tests/llm2llm/json_logs/*.json`); Langfuse traces; the 3 SOP docs.
Verification: report carries per-call verdicts + latency per-call table + aggregate line; committed on the branch.
Gate to T4: no call-quality FAIL requiring engine changes. If a fix is needed → fix + re-run ON the branch, commit, document (what/why/numbers) in the report. Still no new branch (2-iter cap).

### T4 — iter34: model-only gpt-4.1 branch + IDENTICAL assessment (ONLY if T3b green)
Goal: apples-to-apples model compare — the ONLY delta is the model.
Files: `diallux/config.py` (one-line default), `ITERATIONS.md` (edit, §24), `reports/phaseb-engine-chain/` (iter34 battery + SOP files, new).
Commands (full):
1. In `/home/julio/projects/clean_diallux_SDR`: `git branch engine/iter34-gpt41-model-only engine/iter33-phaseb-engine-chain && git worktree add /tmp/opencode/wt-iter34 engine/iter34-gpt41-model-only` (workdir for all below: `/tmp/opencode/wt-iter34`).
2. One-line edit: `Settings.openai_model` default → `gpt-4.1` in `diallux/config.py`; copy `.env` + `scripts/state_latency.py` helpers in (untracked, never commit). Commit: `git add diallux/config.py && git commit -m "iter34: model-only change gpt-5.2 -> gpt-4.1 (all Phase B code unchanged)"`.
3. Suite: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests` → 141 green (model default does not affect hermetic suite).
4. Maria smoke: `set -a; . ./.env; set +a; /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 48 --agent-model gpt-4.1`; `git checkout -- eval/llm2llm_report.json`. Gate: PASS + complete tail + chain_ok + booking turn ≤6s.
5. First-13 battery: same loop as T3 with `--agent-model gpt-4.1` (window echoed); same 3 meters; write `reports/phaseb-engine-chain/08_battery_gpt41.md`.
6. 3-SOP audit with the IDENTICAL structure (digest + `lf.py lat` + grading + table→summary→relevant info): `reports/phaseb-engine-chain/09_sops_gpt41.md`. Commit both reports.
Dependencies: same keys as T2 (gpt-4.1 agent spend + gpt-4o caller).
Verification: same gates as T3/T3b, same tables; any divergence vs gpt-5.2 is model behavior, not engine (code identical — `git diff engine/iter33-phaseb-engine-chain engine/iter34-gpt41-model-only -- diallux/ tests/` shows ONLY config.py).

### T5 — final compare + verdict + ledgers
Goal: one clear table for both models, then close through reporting (no merge).
Files: `reports/phaseb-engine-chain/07_verdict.md` (new; covers BOTH models), `ITERATIONS.md` §23–24 + `git_tree.md` row(s) (edit, on iter33 branch; iter34 ledgers committed on iter34).
Commands (full):
1. Write `07_verdict.md`: compare table (gpt-5.2 vs gpt-4.1 — PASS rate, gens, silent%, booking-turn, p50/p90, SALES bands, HUMANIZED fails, cost from `scripts/lf.py costs`), summary, relevant info, merge recommendation. Commit on the branch.
2. Ledgers commit (explicit paths): `git add reports/phaseb-engine-chain/05_battery.md reports/phaseb-engine-chain/06_sops_full_call.md reports/phaseb-engine-chain/07_verdict.md ITERATIONS.md git_tree.md && git commit -m "iter33 ledgers: battery <X/13> + 3-SOP + verdict + ITERATIONS §23"`.
3. Table + summary + relevant info to Julio in chat; merge decision his.
Dependencies: T3–T4 numbers (cite measured pulls, not memory).
Verification: commits on branches only; `git status --short` clean (except the two `??` helpers); NOTHING pushed/merged.

## Validation Plan (end-to-end)
1. T1: tail present without manual sleep; suite green; commit on branch.
2. T2: Maria PASS + complete tail + chain_ok + booking turn ≤6s.
3. T3: battery gates from measured meters (state_latency TOTAL reconciles with json_logs gens within the disclosed tail margin); T3b: 3-SOP report committed (table→summary→relevant info + latency tables).
4. T4: iter34 differs from iter33 by config.py ONLY; same battery + same SOP structure; same gates.
5. T5: compare table (both models) + verdict cites T3–T4 numbers; branches hold all commits past 596f1bb; no merge without Julio.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merge of iter32/iter33 to main | Julio's call, after verdict |
| Pedro over-book retrain | Craft, orthogonal |
| Cache-hit re-tune | Decide post-Phase-B numbers |
| Prompts cleanup of dead chain text | Phase B v2, only after battery proof |
| History window re-tune | After Phase B numbers |
| state_latency.py upstreaming into the tree | Untracked helper; commit decision is Julio's |
