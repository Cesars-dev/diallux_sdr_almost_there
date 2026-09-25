# PLAN — iter41b: gpt-5.4 full 13-persona battery at verbosity LOW then MEDIUM + 3-SOP audit with latency

## Meta
- Date: 2026-09-10
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session: run the 13 original personas on **gpt-5.4** (the proper iter `engine/iter41-quality-debt` @ `65d7f3b` — all 4 quality fixes live: T1, T1b, T2, T3), **all async**, once at verbosity LOW then once at verbosity MEDIUM; then audit BOTH batches identically with the SDK digests + OTEL latency + the full 3-SOP protocol, and deliver a LOW-vs-MEDIUM comparison (latency tracked as a first-class metric per the updated `full_call_analysys.md`). Ends with the full path of this plan.
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context (verbatim carry — session 2026-09-09→10, iter41)

- **Project:** Dialux SDR voice engine "Linda" — LangGraph 9-state pipeline (Intake→Discovery→Closer→Offer→contact_details→ConfirmSlots→VerifyLead→Booking→Closing), Deepgram Flux STT → gpt-5.4 (thinking-off, verbosity configurable) → gates → Cartesia sonic-3.6 TTS. Repo FORK = `clean_diallux_SDR` (MAIN workspace); ORIGINAL `Retell_AI_MCP_connection` serves LIVE infra `:8001/:8002/:8003`.
- **iter41 branch state:** `engine/iter41-quality-debt` @ **`65d7f3b`** (worktree `/tmp/opencode/wt-iter41`, `.venv` symlink → `engine/.venv`, `.env` present, `OPENAI_MODEL=gpt-5.4`). 4 commits: `ca3112b` T1 in-turn sentence dedupe · `0bc61ab` T2 filler cap · `5810620` T3 date-aware mock · `65d7f3b` T1b cross-round dedupe. Suite **199 green**. Docs committed to main (`00dd386`, `7e04072`). `:8007` server (pid 3213896) runs wt-iter41 @ `65d7f3b`, health `llm gpt-5.4 / flux / sonic-3.6 / eager EOT`.
- **Luna A/B (owner-directed) verdict: DROP gpt-5.6-luna, keep gpt-5.4.** (9/13 best vs 5.4's 12/13; luna narrates-instead-of-acts under objection pressure; capability-gate hallucinations; self-bail; Sofia fails at every verbosity. Report `research/surgeon/iter41-quality-debt/05_luna_ab.md`.)
- **Known gap this plan fixes:** the gpt-5.4 fixes were only ever exercised on a 5-call batch (T3 re-runs + T4 live) that ran WITHOUT T1b, and never as a full 13. This plan runs the FULL 13 on gpt-5.4 at the CURRENT head with all fixes, at two verbosities.
- **SOP just updated (`full_call_analysys.md`, commit `7e04072`):** latency is a REQUIRED tracked metric — per-call **round** p50/p90 (from json `turn_ms`) AND **LLM** p50/p90 (OTEL `lf.py lat`) as two columns per table row, a latency-comparison table for multi-batch audits, and the delivery must END with the full path of the plan file.
- **Model settings:** config default `openai_reasoning_effort="none"`, `openai_verbosity="low"`. Overridable via env vars `OPENAI_VERBOSITY`, `OPENAI_REASONING_EFFORT` (pydantic-settings, no env prefix). gpt-5.* + function tools on chat-completions REQUIRES reasoning_effort='none' (luna 400 proof). For MEDIUM batch: `OPENAI_VERBOSITY=medium OPENAI_REASONING_EFFORT=none`.
- **Harness:** `tests/llm2llm/harness.py --personas <Name> --rag --langfuse --max-turns 28` (mock slots default; `--agent-model` override). Runs 13 original personas: Maria, Susan, Danny, Marcus, Carlos, Pedro, Sofia, Jorge, Daniel, Brenda, Gene, Frank, Ray. Larry (assassin) NEVER in routine batches. Parallel-safe as separate processes.
- **SDK digest:** fork's `scripts/call.py` LACKS `digest`/`lat` — temp-copy ORIGINAL's `call.py`+`lf.py` into `/tmp/opencode/sop_batch_<tag>/scripts/`, run, then `rm` (proven). ORIGINAL root: `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5`. OTEL via ORIGINAL's `lf.py lat --hours 16 --window HH:MM-HH:MM` (UTC = VPS local). Langfuse `:3001` healthy.
- **Batch json disambiguation:** all harness json_logs land in `/tmp/opencode/wt-iter41/tests/llm2llm/json_logs/` (same dir for LOW+MEDIUM). Stage per batch by persona-scoped glob `*<Persona>*.json` matched to each stdout log's mtime (min |Δ|; logs written seconds after the json). Proven matcher.
- **Tooling/evidence:** digests → `/tmp/opencode/iter41b_low_*_digest.txt` / `iter41b_med_*_digest.txt`; OTEL → `lat_iter41b_{low,med}.txt`; report → `research/surgeon/iter41-quality-debt/07_gpt54_low_vs_med.md`.
- **Latency reference (same metric, OTEL per-LLM-call):** iter40 13-parallel battery LLM p50 **1.58s**; iter41 audited 5-call batch LLM p50 **1.52s**; iter39 single cache-hot live call 1.26s (outlier). T1 dedupe adds **~0.1ms** measured first-token (benchmarked) — not a latency concern.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Proper test iter = `engine/iter41-quality-debt` @ `65d7f3b` on gpt-5.4 | All 4 fixes live; :8007 already serves it |
| Two verbosities tested separately: LOW (config default) then MEDIUM (env override) | Owner directive; medium is the new preferred recipe being validated |
| reasoning_effort='none' always (env set explicitly both batches) | gpt-5.x + tools rejects anything else |
| Mock slots for the battery | Hermetic, no calendar touches; no real bookings to cancel |
| 13 original personas, Larry excluded | Standard first-13; Larry gated |
| Latency tracked BOTH planes (round + LLM) per updated SOP | Owner: "get latency as well tracked" |
| Luna dropped — NOT part of this plan | Owner verdict |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None — all inputs pinned above | — |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12; langgraph 1.2.11, langfuse 4.15.1, httpx, fastapi).
- Worktree: `/tmp/opencode/wt-iter41` @ `65d7f3b` (`.venv` symlink, `.env` with `OPENAI_MODEL=gpt-5.4`).
- Suite: `cd /tmp/opencode/wt-iter41 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q` → **199 passed** (unchanged by this plan; run once to confirm head).
- Langfuse `http://localhost:3001`; SDK scripts via temp-copy of ORIGINAL `call.py`/`lf.py` (fork lacks digest/lat).
- Personas: `tests/llm2llm/personas.py` (13 original; Larry assassin excluded).
- Never touch: `:8000/:8002/:8003`, live agent IDs, `slots.db`, ORIGINAL dirty files.

## Architecture (one block)
```
13 personas (parallel processes, mock slots, gpt-5.4)
  ├─ BATCH A  OPENAI_VERBOSITY=low   OPENAI_REASONING_EFFORT=none  (iter41-quality-debt @ 65d7f3b)
  ├─ BATCH B  OPENAI_VERBOSITY=medium OPENAI_REASONING_EFFORT=none  (same code)
  │        json_logs → tests/llm2llm/json_logs/  (disambiguate by stdout-log mtime)
  ▼
audit each batch identically:
  - SDK digest  (temp-copy ORIGINAL call.py → per-batch dir, `call.py digest`)
  - OTEL LLM latency  (temp-copy ORIGINAL lf.py → `lf.py lat --window <batch-window>`)
  - grade per full_call_analysys.md (CALL / SALES / HUMANIZED) + round p50/p90 + LLM p50/p90
  ▼
07_gpt54_low_vs_med.md  +  chat: table → summary → relevant-info → latency-comparison → FULL PLAN PATH
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter41b_gpt54_low_med.md` | this plan | NEW (commit main) |
| `/home/julio/projects/clean_diallux_SDR/docs/Testing_guidelines/full_call_analysys.md` | latency tracked + plan-path at end | EDIT (already done, `7e04072`) |
| `/tmp/opencode/sop_batch_low/` and `/tmp/opencode/sop_batch_med/` | staged json + temp-copied call.py/lf.py | NEW (temp; rm scripts after) |
| `/tmp/opencode/iter41b_{low,med}_*_digest.txt` | SDK digests | NEW (evidence) |
| `/tmp/opencode/lat_iter41b_{low,med}.txt` | OTEL latency | NEW (evidence) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter41-quality-debt/07_gpt54_low_vs_med.md` | full audit report | NEW (gitignored evidence) |

## Deploy Rules
- Suite green before launch (confirm 199).
- Launch both batteries as separate `setsid nohup` background processes; `.env` sourced with `set -a; . ./.env; set +a` in the launch shell; env overrides exported BEFORE the python invocation.
- mock slots only → NO real bookings, nothing to cancel.
- Temp-copied ORIGINAL scripts are `rm`-ed after each digest/lat run.
- NEVER touch `:8000/:8002/:8003`, `:8005`, live agent IDs, `slots.db`.

## Tasks (in order)

### T0 — Confirm head + suite
Goal: verify the worktree is on the proper iter and the suite is green.
Commands:
```bash
cd /tmp/opencode/wt-iter41 && git rev-parse --short HEAD   # expect 65d7f3b
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q   # expect 199 passed
```
Verification: HEAD `65d7f3b`; suite 199 passed.
Dependencies: none.

### T1 — Battery A: 13 personas, gpt-5.4, verbosity LOW (async)
Goal: full first-13 on gpt-5.4 with all fixes, verbosity low.
Commands (13 parallel background processes):
```bash
cd /tmp/opencode/wt-iter41 && set -a && . ./.env && set +a && \
export OPENAI_REASONING_EFFORT=none OPENAI_VERBOSITY=low && \
for p in Maria Susan Danny Marcus Carlos Pedro Sofia Jorge Daniel Brenda Gene Frank Ray; do \
  setsid nohup /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python \
    tests/llm2llm/harness.py --personas $p --rag --langfuse --max-turns 28 \
    > /tmp/opencode/iter41b_low_$p.log 2>&1 < /dev/null & done; disown -a
```
Verification: 13 stdout logs; each contains `[PASS]`/`[FAIL]` and an `ALL PASS`/`FAILURES PRESENT` tail; 13 json files in `tests/llm2llm/json_logs/`.
Dependencies: T0.

### T2 — Battery B: 13 personas, gpt-5.4, verbosity MEDIUM (async)
Goal: same, verbosity medium. Run after T1 (or concurrent — the two batches MUST NOT interleave json matching; prefer sequential completion of T1's json writes before T2 launches; allow overlap of T1-finishing/T2-running is acceptable since matching is per stdout-log mtime).
Commands: identical to T1 with `OPENAI_VERBOSITY=medium` and log tag `iter41b_med_$p.log`.
Verification: 13 stdout logs + 13 json files (newest set per persona).
Dependencies: T1 (json log written).

### T3 — SDK digests + OTEL latency for BOTH batches
Goal: build compliant digests + OTEL LLM latency per batch.
Commands:
```bash
# stage (proven matcher): for each batch, copy *<Persona>*.json matched to each stdout log's mtime
#   into /tmp/opencode/sop_batch_low/tests/llm2llm/json_logs and .../sop_batch_med/...
#   and cp ORIGINAL scripts/call.py + lf.py into each sop_batch_<tag>/scripts/
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python /tmp/opencode/sop_batch_low/scripts/call.py digest --hours 48 --out /tmp/opencode/iter41b_low_sop_digest.txt
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python /tmp/opencode/sop_batch_med/scripts/call.py digest --hours 48 --out /tmp/opencode/iter41b_med_sop_digest.txt
# OTEL (from ORIGINAL root, its .env):
cd /home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5 && set -a && . ./.env && set +a
python3 scripts/lf.py lat --hours 16 --limit 80 --window <LOW_WINDOW> > /tmp/opencode/lat_iter41b_low.txt
python3 scripts/lf.py lat --hours 16 --limit 80 --window <MED_WINDOW> > /tmp/opencode/lat_iter41b_med.txt
rm /tmp/opencode/sop_batch_{low,med}/scripts/call.py /tmp/opencode/sop_batch_{low,med}/scripts/lf.py
```
(`<LOW_WINDOW>`/`<MED_WINDOW>` = UTC trace-timestamp windows from `lf.py traces`, derived at run time from the battery stdout mtimes.)
Verification: digests report 13 call(s) each; lat files have per-trace + `ALL:` lines.
Dependencies: T1, T2.

### T4 — Grade + write report + deliver
Goal: grade every call per the 3 SOPs (read the three SOP files first), build the tables with round+LLM latency columns, a latency-comparison table, summary, relevant info, and end with the FULL PATH of this plan file.
Files: `research/surgeon/iter41-quality-debt/07_gpt54_low_vs_med.md`.
Verification: report + chat delivery include all 5 SOP deliverables (table→summary→relevant-info→latency-comparison→full plan path).
Dependencies: T3.

## Validation Plan (end-to-end)
1. T0: suite 199, HEAD 65d7f3b.
2. T1: 13/13 logs+json (low).
3. T2: 13/13 logs+json (med).
4. T3: digests 13 calls each; OTEL `ALL:` lines both batches.
5. T4: two per-batch tables + comparison + low-vs-med latency + full plan path delivered.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Live (real-calendar) happy-path test | Separate owner-gated step; T8 A/B on :8007 |
| Pedro over-book retrain | Pre-existing; iter42 candidate |
| Luna | Dropped (owner verdict) |
| gen p50 ≤1.2s gate | iter31 carry-forward; T8 live decides |