# ENGINE SUITE VERIFICATION — 129 hermetic units green at the fork's new path

## Meta
- Date: 2026-09-08
- Project root (absolute): `/home/julio/projects/clean_diallux_SDR` (NOTE: supersedes the SOP's legacy root `/home/julio/projects/Retell_AI_MCP_connection` — that path is now the frozen live reference; all work happens in the clean fork)
- Scope (one sentence): Prove the restructured fork's engine test suite (129 pytest units) passes at its new path, and file the receipt.
- Status: DONE — **129 passed in 9.71s, exit 0** (receipt: `research/surgeon/suite-verification-fork/MANIFEST.md`)

## Compaction Context
A byte-identical fork of `Retell_AI_MCP_connection` was created at `/home/julio/projects/clean_diallux_SDR` (rsync -aH, checksum-verified 0 diffs, 74,940 files) and restructured into one repo/one tree (commits c0→c5, HEAD `bfe172d` on `main`): `engine/` (ex typo dir `dialux-langgraph-production-v5`, the LIVE LangGraph agent repo, nested .git stripped; 13 iter branches preserved as root refs `engine/iter*` + 10 photocopy-era imports `engine/snap-*`), `retell/` (sdr V7.x ladder + heating-uk), `services/` (3 live endpoints + proxy_guard — dormant copies; live systemd units still point at the ORIGINAL workspace), `docs/`, `plans/`, `research/` (gitignored evidence), `_cold_archive/` (tarballs). Everything pushed to private GitHub `Cesars-dev/clean-diallux-sdr` (31 refs) + `Cesars-dev/dialux-sdr-langgraph-v5-backup`. Doctrine (`DOCTRINE.md`): plan→branch→iterate→test→report→commit→(owner GO)→merge; Tier 0 docs go straight to main. Engine working tree = iter31-c3d-wrap-dampener content (suite expected 129 per ITERATIONS.md §21). User aborted an earlier pytest attempt for clarification — **no test has executed yet**; only `--collect-only` inventory ran (executes zero test code) and confirmed exactly 129 collected. Engine `.venv` (Python 3.12.3, pytest 9.1.1) was copied byte-identical and is functional at the new path (proven by successful collection). Original workspace untouched and serving :8000–8003.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Plan lives in the clean fork's `plans/`, not the legacy root | work happens in the fork; legacy root is frozen reference |
| Suite is hermetic → no branch needed (verification, not code change) | DOCTRINE Tier 0/1: no source change; mock webhooks + FakeLLM only |
| Receipt goes to `research/surgeon/suite-verification-fork/` | doctrine §4: evidence in research/, gitignored |
| Expected result pinned at 129 passed | `pytest --collect-only` = 129; ITERATIONS.md §21 says suite 129 at iter31-c3d |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| (none) | — |

## Environment & Dependencies
- Python 3.12.3 via `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (venv copied from original; functional at new path — collection ran)
- pytest 9.1.1 (venv-resolved)
- Engine content = iter31-c3d-wrap-dampener (`engine/ITERATIONS.md` §21: suite 129)
- Local pgvector container `diallux-db` on `localhost:5432` (may be read by `test_rag.py`; `RAG_MODE=auto` falls back to inline if absent — same DB the original suite always used)
- No network services required: FakeLLM, in-process mock webhooks (`engine/tests/mock_webhooks.py`); llm2llm harness NOT part of pytest run
- Repo state: `/home/julio/projects/clean_diallux_SDR` on branch `main` @ `bfe172d`, clean status

## Architecture (one block diagram)
```
run: engine/.venv/bin/python -m pytest tests -q
        │
        ├─ tests/test_graph, test_v2, test_units ...   ← 129 units, FakeLLM + mock webhooks
        ├─ NO: real LLM calls · NO: Retell/Cal.com API · NO: bookings · NO: Twilio
        └─ writes: engine/.pytest_cache/ (gitignored)
evidence → research/surgeon/suite-verification-fork/  (gitignored)
plan + status → plans/ (tracked, Tier 0 commit to main)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_engine_suite-verification_2026-09-08.md` | the plan (this file); status → DONE + result | New, then Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/suite-verification-fork/01_suite_run_2026-09-08.log` | raw pytest output | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/suite-verification-fork/MANIFEST.md` | receipt: command, versions, counts, verdict | New |
| `/home/julio/projects/clean_diallux_SDR/engine/.pytest_cache/` | pytest cache (gitignored) | auto |

## Deploy Rules
- No deploy. Nothing restarts. Nothing binds ports.
- NEVER touched: `/home/julio/projects/Retell_AI_MCP_connection/**` (live), Retell agents (`agent_f305…`, `agent_1698…`, `agent_87e4…`), Cal.com event 3801235, any systemd unit, `tests/llm2llm/harness.py` (manual battery tool — NOT this plan).

## Tasks (in order)
### T1 — Run the 129-unit suite at the fork path
Goal: prove all hermetic units pass at the new path.
Files: none changed (cache only).
Commands (full):
```bash
cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python -m pytest tests -q > /home/julio/projects/clean_diallux_SDR/research/surgeon/suite-verification-fork/01_suite_run_2026-09-08.log 2>&1; echo "exit=$?"; tail -4 /home/julio/projects/clean_diallux_SDR/research/surgeon/suite-verification-fork/01_suite_run_2026-09-08.log
```
Dependencies: engine/.venv (pinned above); `mkdir -p` the receipt dir first.
Verification: `exit=0` AND last log line reads `129 passed` (no `failed`/`error`).

### T2 — File the receipt
Goal: durable evidence per doctrine §4.
Files: `…/research/surgeon/suite-verification-fork/MANIFEST.md` (New).
Commands (full): write MANIFEST.md (Write tool) with: command, Python/pytest pins, collected=129, passed/failed counts from T1 log, duration, engine HEAD = iter31-c3d content, repo HEAD.
Verification: MANIFEST exists and its numbers match the log.

### T3 — Update plan status + Tier-0 commit + push
Goal: plan ledger reflects reality (doctrine §7 freshness contract).
Files: this plan (status line → DONE, result appended under Validation Plan).
Commands (full):
```bash
cd /home/julio/projects/clean_diallux_SDR && git add plans/plan_engine_suite-verification_2026-09-08.md && git commit -m "plan: engine suite verification at fork path — <result>" && git push origin main
```
(push via header-auth pattern used all session; keyhound not run on this plan — contains no secrets, only paths/commands)
Verification: `git status --short` empty; remote `origin/main` advances.

## Validation Plan (end-to-end)
1. T1 log exists with `129 passed`, exit 0.
2. `git status --short` in repo root shows ONLY gitignored-untracked absence (clean).
3. Plan status = DONE with actual numbers; commit `+ pushed` on `origin/main`.
4. Negative check: original workspace untouched — `ls /home/julio/projects/Retell_AI_MCP_connection/.git` still exists; live ports still listening (ss -tlnp :8000-8003).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| llm2llm battery (real model, costs money) | separate deliberate run, needs owner instruction |
| Merging iter29→31 stack into engine/main | owner gate (DOCTRINE rule 0) — separate GO |
| Service cutover to `services/` | Tier 2, explicit plan later |
