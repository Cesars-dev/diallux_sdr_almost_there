# iter36 — SOP autopilot: model pulls data + analyses on its own

## Meta
- Date: 2026-09-08
- Project root (fork): `/home/julio/projects/clean_diallux_SDR`
- Scope: run a fully self-serve 3-SOP audit loop — a fresh agent with zero prior context,
  working READ-ONLY from the iter35 worktree (SDKs already there, nothing merged anywhere),
  pulls the digest, OTEL latency, and dossiers via SDKs and writes the
  table→summary→relevant-info report on its own.
- Status: PLAN ONLY (not started — awaits Julio approval).

## Compaction Context
Project: LangGraph port of the Dialux SDR chat agent ("Linda"), 9-state machine
(Intake→Discovery→Closer→Offer→contact_details→ConfirmSlots→VerifyLead→Booking→Closing),
worked in the fork `/home/julio/projects/clean_diallux_SDR` (fork of
`Retell_AI_MCP_connection` 2026-09-08; original still serves :8000–8003, never run
services from the fork until cutover).

What is DONE:
- iter33 (`engine/iter33-phaseb-engine-chain`, worktree `/tmp/opencode/wt-iter33`):
  engine-owned Phase B booking chain + OTEL census fix (`tail_complete` in every json_log,
  LOUD SHORTFALL, 6 regression tests); suite 147. gpt-5.2 first-13 battery 12/13 PASS
  (Pedro over-book = known deferred craft item), ended 13/13. 3-SOP audit committed
  (`reports/phaseb-engine-chain/05_battery.md`, `06_sops_full_call.md`).
- iter34 (`engine/iter34-gpt41-model-only`, worktree `/tmp/opencode/wt-iter34`):
  config.py one-liner ONLY (gpt-5.2 → gpt-4.1; verified `git diff` shows nothing else).
  gpt-4.1 battery 12/13 (Brenda model-gap FAIL), identical SOP structure
  (`08_battery_gpt41.md`, `09_sops_gpt41.md`). Verdict `07_verdict.md` (on iter33):
  merge ENGINE, keep 5.2 default.
- iter35 (`engine/iter35-sdk-sync`, worktree `/tmp/opencode/wt-iter35`, commit `7d90045`):
  ported `scripts/call.py digest` + `scripts/lf.py lat` from the original repo. PROVEN:
  fork's call.py/lf.py were strict subsets (diff showed 196 added lines on original side,
  1 dispatch line fork-side, 0 fork-only lines in lf.py). Both verified against fork logs;
  suite 147; worktree clean. NOT merged anywhere, by explicit owner order ("do nothing...
  agent can pull the branch and check the calls right?") — the autopilot runs READ-ONLY
  from this worktree and never merges.
- Live grading precedent (what the autopilot must reproduce): T3b/T4 audits graded by
  READING freshly built condensed digests + `call.py sop` dossiers ×26 + meter outputs;
  mechanical R-stats computed from json_logs (not eyeballed); SALES D1–D7/14 with bands
  12–14 hire / 8–11 solid / 4–7 retrain / <4 don't ship; HUMANIZED R1–R5 PASS/POLISH/FAIL.
- Known environment facts: venv `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python`
  (3.12, pytest 9.1.1, langfuse SDK 4.15.1); Langfuse self-hosted `http://localhost:3001`
  (keys in worktree `.env`, gitignored, NEVER commit); trace REST names are sometimes EMPTY
  (meters pull by window, client-side filter); `lf.py costs` 400s on this server AND
  json_log `cost` is empty → costs unavailable for both models (note, don't chase);
  `scripts/state_latency.py` is an UNTRACKED helper (copied into worktrees, NEVER commit);
  mock slots default; `df -i /` free > 50000 before harness runs; docker socket NOT
  accessible (cannot read Langfuse server logs); `chmod`/`sudo`/`rm -rf` are DENIED by
  tool policy (run scripts via `bash script.sh`, never `chmod +x`).

Resolved facts for this plan: SDKs live ONLY on `engine/iter35-sdk-sync`
(worktree `/tmp/opencode/wt-iter35`, `.env` present) and STAY there — no merges, ever,
per owner order. Battery json_logs live in the branch worktrees
(`/tmp/opencode/wt-iter33/tests/llm2llm/json_logs/`,
`/tmp/opencode/wt-iter34/tests/llm2llm/json_logs/`, gitignored, accumulate across runs).
`digest` batch mode reads `<its-own-worktree>/tests/llm2llm/json_logs/` and takes the
FRESHEST log per persona — so the agent first copies EXACTLY the 13 battery basenames
(Appendix A — never re-run files, never smoke files) into
`/tmp/opencode/wt-iter35/tests/llm2llm/json_logs/` (untracked, created for the run,
never committed; `git status --short` must show it as the only `??` before/after).
Grading rules below are settled from T3b/T4 — DO NOT re-derive, apply as written.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| No merges anywhere, ever (T1 deleted per owner order) | Owner: "do nothing... agent can pull the branch" — analysis reads across worktrees, writes nothing outside its own report commit |
| Autopilot runs READ-ONLY from `/tmp/opencode/wt-iter35`; report commits land on the branch under audit (report file only) | SDKs + `.env` already in wt-iter35; wt-iter33/wt-iter34 are touched ONLY by the final report-file commit; main never touched |
| Grading input = freshly pulled digest + lat + dossiers, never memory | SOP law; the two reference digests below show the exact shape |
| R1 flag iff ≥2 hits/call; phone-digit recycling, R1 singletons, and the designed booking filler triple are DISCOUNTED (stated, not counted) | Settled T3b/T4: single idioms and required readbacks are not patterns; the filler triple is designed engine behavior |
| Report order is ALWAYS table → summary → relevant info, committed on the branch | Owner-required format (`full_call_analysys.md`) |
| Costs section = "unavailable" (one line, no investigation) | Both sources broken; chasing it is out of scope |
| No new harness runs in this plan (analysis only) | Batteries already done; re-runs only if Julio orders fresh data |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Julio approval of THIS plan (analysis + report-file commits only, zero merges) | Julio in chat |

## Environment & Dependencies
- Python 3.12 via `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python`
  (any worktree may use this venv — same interpreter).
- Langfuse `http://localhost:3001`; creds `LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST` from
  worktree `.env` (`set -a; . ./.env; set +a` first for any Langfuse command).
- Worktrees: `/tmp/opencode/wt-iter35` (SDK home + autopilot workdir — READ-ONLY except
  the untracked json_logs staging dir) · `/tmp/opencode/wt-iter33` (iter33 battery logs
  source) · `/tmp/opencode/wt-iter34` (iter34 battery logs source).
- Key files (absolute):
  - SOPs: `/home/julio/projects/clean_diallux_SDR/docs/Testing_guidelines/CALL-ANALYSIS-SOP.md` (122 lines) · `SALES-ANALYSIS-SOP.md` (43) · `HUMANIZED-ANALYSIS-SOP.md` (68) · `full_call_analysys.md` (148, the protocol).
  - SDKs (ONLY on iter35 — never merged, never copied into other branches): `/tmp/opencode/wt-iter35/scripts/call.py` {list,show,sop,dvs,turns,lat,digest} · `/tmp/opencode/wt-iter35/scripts/lf.py` {health,traces,show,gens,tools,usage,costs,lat} · `/tmp/opencode/wt-iter35/scripts/silent_rounds.py` · `latency.py` · `scripts/state_latency.py` (untracked helper — copy from `/tmp/opencode/wt-iter33/scripts/state_latency.py` if absent, NEVER commit).
  - Logs: `<worktree>/tests/llm2llm/json_logs/*.json` (mtime = run time; filename embeds persona + call_id).
  - Format examples (5.2 audit): `/tmp/opencode/iter33_sop_digest.txt` (608 lines, condensed) · `/tmp/opencode/iter33_lat.txt` (state_latency full output) · worktree `reports/phaseb-engine-chain/05_battery.md` + `06_sops_full_call.md`.
  - Format examples (4.1 audit): `/tmp/opencode/iter34_sop_digest.txt` (541 lines) · worktree `reports/phaseb-engine-chain/08_battery_gpt41.md` + `09_sops_gpt41.md`.
  - Personas registry: `<worktree>/tests/llm2llm/personas.py` (13 names: Maria Danny Susan Marcus Carlos Pedro Sofia Jorge Daniel Brenda Gene Frank Ray).

## Architecture (autopilot dataflow)
```
workdir for ALL reads/pulls: /tmp/opencode/wt-iter35 (READ-ONLY; SDKs + .env here)
  ├─ 0. stage: copy the 13 EXACT battery basenames (Appendix A) from the source
  │     worktree's tests/llm2llm/json_logs/ into wt-iter35/tests/llm2llm/json_logs/
  │     (mkdir if absent; untracked staging dir, nothing else in it, never committed)
  ├─ scripts/call.py digest --hours 8760 --out /tmp/opencode/<tag>_digest.txt   # dir holds ONLY the 13 → N=13 guaranteed
  ├─ scripts/call.py sop <basename> × 13                                        # dossiers (outcome/turns/p50/gates/dvs)
  ├─ scripts/lf.py health                                                       # ingest up before trusting traces
  ├─ scripts/lf.py lat --hours 8760 --limit 100 --window <HH:MM-HH:MM> > /tmp/opencode/<tag>_lat.txt
  ├─ scripts/state_latency.py --from <start> --to <end>  (exact UTC windows, Appendix A)
  ├─ scripts/silent_rounds.py --from <start> --to <end>
  └─ Appendix B python (json_log stats + R-mechanicals, exact commands)
        └─ agent READS digest + dossiers + meter outputs
              └─ grades CALL (8 cats) / SALES (D1–D7) / HUMANIZED (R1–R5, rubric below)
                    └─ writes report to the branch-under-audit worktree's
                        reports/phaseb-engine-chain/<NN>_<name>.md, commits THAT FILE ONLY on that branch
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter35/tests/llm2llm/json_logs/` (13 staged battery files) | read-only input staging (T2 step 0) | New (untracked dir, never committed, deleted or left untracked after) |
| `/tmp/opencode/<tag>_digest.txt`, `<tag>_lat.txt` | fresh pulls (never committed) | New (/tmp only) |
| `<branch-worktree>/reports/phaseb-engine-chain/<NN>_<name>.md` | audit report (T3) — the ONLY file ever written outside wt-iter35 | New |
| `<worktree>/ITERATIONS.md`, `<worktree>/git_tree.md` | ledger line(s) (T4) | Edit |
| NEVER touched | `diallux/**`, `agent/llm.json`, `tests/**`, `eval/llm2llm_report.json` (restore with `git checkout --` if touched), `.env`, `scripts/state_latency.py` (untracked helper), main branch, live agent IDs, services/ports | — |

## Deploy Rules
- No service deploys/restarts. No commits to main. No pushes. NO MERGES of any kind.
  Julio reviews the report before anything else happens.
- wt-iter35 is READ-ONLY except: the untracked `tests/llm2llm/json_logs/` staging dir
  (13 files, T2 step 0) and /tmp outputs. Verify with `git -C /tmp/opencode/wt-iter35 status --short`
  before and after: the staging dir is the only `??` allowed; never `git add` it.
- wt-iter33 / wt-iter34 are touched ONLY by the single report-file commit (T3). Nothing
  else is written there — no checkouts, no restores, no edits.
- `git add` explicit file paths only, never `git add -A`. `.env` + `scripts/state_latency.py` stay untracked.
- Analysis only: no harness runs, no prompt/model/config edits, no engine changes. Any `tail_complete=False` found → DISCLOSE in the report (re-run decisions are Julio's, not the autopilot's).

## Tasks (in order)

### T1 — Verify read-only setup (no merges, no writes)
Goal: prove the autopilot can run without touching any branch.
Files: none (checks only).
Commands (full):
1. `git -C /tmp/opencode/wt-iter35 log --oneline -1` (expect `7d90045 iter35 SDK sync…`).
2. `git -C /tmp/opencode/wt-iter35 status --short` (expect EMPTY — no output at all).
3. Workdir `/tmp/opencode/wt-iter35`: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/call.py digest --help` (shows `--substr/--hours/--frm/--to/--out/--full`) and `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py lat --help` (shows `--hours/--name/--limit/--window`).
4. `ls /tmp/opencode/wt-iter35/.env` (exists) and `ls /tmp/opencode/wt-iter33/scripts/state_latency.py` (helper source for T2 step 5 if absent in wt-iter35).
Dependencies: none.
Verification: iter35 tip is `7d90045`; wt-iter35 status empty; both help outputs show the new flags. If ANY check fails → STOP and report (do not improvise).

### T2 — Pull all data (the autopilot input set)
Goal: every number the grades cite, pulled fresh, saved to /tmp.
Files: none in repo (staging dir untracked; outputs to `/tmp/opencode/<tag>_digest.txt`, `<tag>_lat.txt`).
Commands (full, workdir `/tmp/opencode/wt-iter35` for ALL steps):
0. Stage EXACTLY the 13 basenames from Appendix A (source dir per audit target):
   `mkdir -p tests/llm2llm/json_logs && cp <src>/tests/llm2llm/json_logs/<f1>.json … tests/llm2llm/json_logs/` (13 files, nothing else — NOT smoke files, NOT re-run files; Appendix A lists which is which).
1. Windows/tags from Appendix A — no guessing: iter33 window `2026-09-08T16:00:10Z → 2026-09-08T16:19:50Z`, tag `iter33`, lat-window `16:00-16:35`; iter34 window `2026-09-08T22:47:54Z → 2026-09-08T22:59:31Z`, tag `iter34`, lat-window `22:47-23:15`.
2. `set -a; . ./.env; set +a; /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py health` (expect `server: OK`; else STOP — do not trust trace data, grade json_logs only and say so).
3. `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/call.py digest --hours 8760 --out /tmp/opencode/<tag>_digest.txt` (expect `digest written: … 13 call(s)` — the staging dir holds ONLY the 13, so batch mode cannot grab re-runs; if N≠13 → STOP, the staging dir is wrong).
4. `set -a; . ./.env; set +a; /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py lat --hours 8760 --limit 100 --window <lat-window> > /tmp/opencode/<tag>_lat.txt` (trace timestamp is LAST event time — windows above are pre-widened).
5. `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/call.py sop <basename-without-.json>` × 13 (basenames = Appendix A list); record outcome/pass/turns/p50/gate_rej/blocked/uid per call.
6. `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/state_latency.py --from <start> --to <end>` + `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/silent_rounds.py --from <start> --to <end>` (exact UTC windows from step 1; record TOTAL gens/silent% + per-state p50s; note EMPTY-named traces excluded — count them by direct trace-ID pull only if the report needs them).
7. Appendix B python (json_log stats + R-mechanicals) run against `tests/llm2llm/json_logs/` in THIS workdir (the 13 staged files).
Dependencies: T1 verified; `.env` present; Langfuse up.
Verification: digest file has 13 calls with R-mechanicals + condensed transcripts; lat file has per-call rows + (self-computed) `ALL:` aggregate; dossier table has 13 rows; meter TOTALs recorded; `git -C /tmp/opencode/wt-iter35 status --short` shows ONLY the `?? tests/llm2llm/json_logs/` staging dir.

### T3 — Grade + write the report (the autonomous analysis)
Goal: table→summary→relevant-info report, committed on the branch under audit (report file ONLY).
Files: `<branch-worktree>/reports/phaseb-engine-chain/<NN>_<name>.md` (new; NN = next number
in that folder — check with `ls <branch-worktree>/reports/phaseb-engine-chain/`).
Grading rubric (apply EXACTLY — settled T3b/T4, do not re-derive):
- CALL (per call): 8 cats (prompt-following per state ✅/⚠️/❌ · nonsense/hallucination · redundancy · repetition · bugs · tools · flow · metrics). Verdict PASS/POLISH/FAIL. Auto-FAIL: wrong outcome (book vs expect) or `ended=false` at max-turns. Note duplicates (`end_call,end_call`), misreadbacks, identity contradictions with turn quotes.
- SALES (per call): D1 discovery · D2 pain quantification (numbers from PROSPECT + played back) · D3 objection (acknowledge→reframe→re-ask; steamroll = 0) · D4 value framing (their business, not generic) · D5 close confidence (assumed/binary = 2; folded = 0) · D6 momentum · D7 recovery — 0–2 each, /14. Bands: 12–14 hire · 8–11 solid · 4–7 retrain · <4 don't ship. Every dimension gets a one-line evidence quote/paraphrase.
- HUMANIZED (per call): count R1 (flag iff ≥2 hits) · R2 opener variance (note top repeated opener) · R3/R4 (any hit = flag) · R5 (bloat/rule as documented; recycling ≥3× = flag per kind BUT discount phone-digit sequences; filler stacking ≥2 acks in a turn = flag; verbatim cross-turn repeats = hard flag; cross-call fingerprint = note, discounted as designed filler unless newly introduced; mirroring via caller/agent medians). Verdict: 0 flags PASS · 1–2 POLISH · 3+ FAIL.
- Mechanicals MUST be computed from json_logs with regexes (R1 `I completely understand|I hear you|Certainly|I'd be happy to`; tool-talk names; brackets; >40w agent vs ≤5w caller + no caller question; 4-gram recycling; ack stacking), never eyeballed.
- Latency section: per-call table (trace name, llm_calls, p50, p90, max) + `ALL:` aggregate + slow-state note + harness turn p50/p90. Costs: single line "unavailable (lf.py costs 400s, json_log cost empty)".
- Gate statement at end: which gates met/failed with measured numbers; whether any FAIL requires engine changes (then STOP — no new branch, report it); else declare the onward gate OPEN/CLOSED explicitly.
Commands (full — the ONLY writes outside wt-iter35; `<branch-worktree>` is
`/tmp/opencode/wt-iter33` for a gpt-5.2 audit, `/tmp/opencode/wt-iter34` for gpt-4.1):
`git -C <branch-worktree> add reports/phaseb-engine-chain/<NN>_<name>.md && git -C <branch-worktree> commit -m "<iter>: 3-SOP audit <model> battery"`.
Dependencies: T2 outputs (cite pulled files, not memory).
Verification: report has TABLE first (one row per SOP × persona + p50/p90 columns), then summary, then relevant info (quotes, worst offenders, OTEL aggregate line); committed on the branch; `git -C <branch-worktree> status --short` shows ONLY the pre-existing `?? scripts/state_latency.py` (the report file is now committed, nothing else changed).

### T4 — Ledgers
Goal: ITERATIONS + git_tree rows so any state is recoverable.
Files: `<branch-worktree>/ITERATIONS.md`, `<branch-worktree>/git_tree.md` (edit, next § number / next table row — same worktree as T3).
Commands (full): `git -C <branch-worktree> add ITERATIONS.md git_tree.md && git -C <branch-worktree> commit -m "<iter> ledgers: <what> + ITERATIONS §<N>"`.
Dependencies: T3 committed.
Verification: `git -C <branch-worktree> log --oneline -3` shows report commit then ledger commit; `git status --short` shows ONLY `?? scripts/state_latency.py`; NOTHING pushed, NOTHING merged, no main commits.

## Validation Plan (end-to-end)
1. T1: iter35 tip is `7d90045`; wt-iter35 status EMPTY; both help outputs show the new flags. Zero writes anywhere.
2. T2: staging dir holds EXACTLY the 13 Appendix A files; 13-call digest + lat file with per-call rows + 13 dossiers + meter TOTALs — all cited by path in the report; wt-iter35 status shows ONLY the staging `??`.
3. T3: report carries per-call CALL/SALES/HUMANIZED verdicts + latency per-call table + aggregate line + gate statement; the branch worktree status shows ONLY `?? scripts/state_latency.py` after commit.
4. T4: ledger commits on the branch only; nothing pushed, nothing merged, no main commits.
5. Lobotomized-agent check: a fresh agent with ONLY this plan + the three worktrees can execute T1–T4 without asking a single question (every path absolute, every command full, every rule stated, every battery file pinned in Appendix A).

## Appendix A — all calls to analyse (model × persona × file × known result)

Source dirs: iter33 → `/tmp/opencode/wt-iter33/tests/llm2llm/json_logs/`
· iter34 → `/tmp/opencode/wt-iter34/tests/llm2llm/json_logs/`.
Destination (both audits): `/tmp/opencode/wt-iter35/tests/llm2llm/json_logs/`
(clear it first if a previous audit staged files there: `rm` the 13 staged `.json`
files ONLY — never `rm -rf`, never anything else).
Cross-check rule: after staging + digest, every row below must match
(outcome/pass/turns) — a mismatch means the WRONG file was staged. STOP and restage.

### A1 — iter33 battery: gpt-5.2, branch `engine/iter33-phaseb-engine-chain`
Window `2026-09-08T16:00:10Z → 2026-09-08T16:19:50Z`, lat-window `16:00-16:35`.
12/13 PASS (Pedro over-book), ended 13/13.

| Persona | Expect | Model did | Pass | Turns | Stage this basename (ONLY these 13) |
|---|---|---|---|---|---|
| Maria | book | book | True | 15 | `BOOKMaria_l2l-bookmaria-133cc99b.json` |
| Danny | book | book | True | 16 | `BOOKDanny_l2l-bookdanny-69512140.json` |
| Susan | book | book | True | 16 | `BOOKSusan_l2l-booksusan-c6e57fc7.json` |
| Marcus | book | book | True | 15 | `BOOKMarcus_l2l-bookmarcus-44acde62.json` |
| Carlos | no-book | no-book | True | 16 | `NOBOOKCarlos_l2l-nobookcarlos-4be0ff77.json` |
| Pedro | no-book | **book** | **False** | 27 | `NOBOOKPedro_l2l-nobookpedro-abac084f.json` |
| Sofia | book | book | True | 15 | `BOOKSofia_l2l-booksofia-e2ca101e.json` |
| Jorge | no-book | no-book | True | 11 | `NOBOOKJorge_l2l-nobookjorge-b84bc3c6.json` |
| Daniel | no-book | no-book | True | 15 | `NOBOOKDaniel_l2l-nobookdaniel-28eb6538.json` |
| Brenda | book | book | True | 36 | `CURVEBrenda_l2l-curvebrenda-84fa1867.json` |
| Gene | book | book | True | 19 | `CURVEGene_l2l-curvegene-e91424b2.json` |
| Frank | no-book | no-book | True | 5 | `CURVEFrank_l2l-curvefrank-d0cc3d34.json` |
| Ray | no-book | no-book | True | 6 | `CURVERay_l2l-curveray-cdf5d955.json` |
TRAPS (same source dir, DO NOT stage): `BOOKMaria_l2l-bookmaria-b215c8ca.json` (T2 Maria
smoke, 16 turns) and any Susan/Gene/Frank/Maria re-run files — battery record = first
runs ONLY (turns column above disambiguates).

### A2 — iter34 battery: gpt-4.1, branch `engine/iter34-gpt41-model-only`
Window `2026-09-08T22:47:54Z → 2026-09-08T22:59:31Z`, lat-window `22:47-23:15`.
12/13 PASS (Brenda model-gap FAIL), ended 12/13 (Pedro no-end_call).

| Persona | Expect | Model did | Pass | Turns | Stage this basename (ONLY these 13) |
|---|---|---|---|---|---|
| Maria | book | book | True | 15 | `BOOKMaria_l2l-bookmaria-c40f7dc9.json` |
| Danny | book | book | True | 19 | `BOOKDanny_l2l-bookdanny-828415a1.json` |
| Susan | book | book | True | 19 | `BOOKSusan_l2l-booksusan-0f557f16.json` |
| Marcus | book | book | True | 19 | `BOOKMarcus_l2l-bookmarcus-ef6fcce5.json` |
| Carlos | no-book | no-book | True | 11 | `NOBOOKCarlos_l2l-nobookcarlos-024b57c1.json` |
| Pedro | no-book | no-book | True | 28 | `NOBOOKPedro_l2l-nobookpedro-69ea8ec8.json` |
| Sofia | book | book | True | 16 | `BOOKSofia_l2l-booksofia-b4b69114.json` |
| Jorge | no-book | no-book | True | 12 | `NOBOOKJorge_l2l-nobookjorge-0ed1fffd.json` |
| Daniel | no-book | no-book | True | 9 | `NOBOOKDaniel_l2l-nobookdaniel-8ff2523d.json` |
| Brenda | book | **no-book** | **False** | 20 | `CURVEBrenda_l2l-curvebrenda-a41ea5d0.json` |
| Gene | book | book | True | 21 | `CURVEGene_l2l-curvegene-f959618e.json` |
| Frank | no-book | no-book | True | 4 | `CURVEFrank_l2l-curvefrank-bc2f6a20.json` |
| Ray | no-book | no-book | True | 10 | `CURVERay_l2l-curveray-ee696d69.json` |
TRAPS: `BOOKMaria_l2l-bookmaria-804bce0e.json` is the SMOKE (16 turns), NOT the battery
(15 turns, `c40f7dc9`) — mtimes mislead, trust basenames + turns column. Post-battery
re-run files (Susan/Marcus/Carlos/Pedro/Sofia/Daniel) stay out.

## Appendix B — exact stats commands (workdir `/tmp/opencode/wt-iter35`)

B1 — battery table (turns/ended/chain/tail/turn-ms), run with the venv python.
`<FILES>` = the 13 basenames from Appendix A for the audit target, space-separated,
no `.json` suffix:
`/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -c "
import json,statistics
files='<FILES>'.split()
allms=[]; tot=0; sil=0
for fn in files:
    d=json.load(open('tests/llm2llm/json_logs/'+fn+'.json')); f=d.get('final_dvs',{})
    allms+=d.get('turn_ms') or []
    tr=d.get('transcript') or []; tot+=len(tr)
    sil+=sum(1 for t in tr if not (t.get('agent') or '').strip())
    print(fn[:22], d.get('outcome'), 'pass='+str(d.get('pass')), 'turns='+str(d.get('turns')), 'ended='+str(d.get('ended')), 'chain='+str(f.get('chain_done')), 'tail='+str(d.get('tail_complete')))
print('TOTAL turns=',tot,'speaker-silent=',sil,'p50=',round(statistics.median(allms)/1000,2),'p90=',round(sorted(allms)[int(0.9*len(allms))]/1000,2))
"`
B2 — HUMANIZED mechanicals (same `<FILES>` placeholder):
`/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -c "
import json,re,collections,statistics
R1=re.compile(r'I completely understand|I hear you|Certainly|I.d be happy to',re.I)
for fn in '<FILES>'.split():
    d=json.load(open('tests/llm2llm/json_logs/'+fn+'.json'))
    tr=d.get('transcript',[])
    agents=[(t.get('agent') or '') for t in tr]; callers=[(t.get('caller') or '') for t in tr]
    r1=sum(1 for a in agents if R1.search(a))
    r3=sum(1 for a in agents if re.search(r'validate_lead|slot_verified|dynamic var|extract_|transition_to|dvs|callback_number',a,re.I))
    r4=sum(1 for a in agents if '[' in a and ']' in a)
    bloat=sum(1 for i,a in enumerate(agents) if len(a.split())>40 and len(callers[i].split())<=5 and '?' not in callers[i])
    grams=collections.Counter()
    for a in agents:
        w=a.split()
        for j in range(len(w)-3): grams[' '.join(w[j:j+4]).lower()]+=1
    rec=[(g,c) for g,c in grams.most_common(8) if c>=3]
    stack=sum(1 for a in agents if len(re.findall(r'got it|i hear you|that makes sense|totally|makes sense|fair enough|love that',a,re.I))>=2)
    print(fn[:22],'R1='+str(r1),'R3='+str(r3),'R4='+str(r4),'bloat='+str(bloat),'stack='+str(stack),'recyc='+str(rec[:3]),'agm=%.0f'%statistics.median([len(a.split()) for a in agents]),'clm=%.0f'%statistics.median([len(c.split()) for c in callers]))
"`
Apply the T3 rubric discount rules to B2 output (digits/singletons/designed-filler);
B2 does not decide — the agent does, reading the digest.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Fresh harness batteries (new runs) | Analysis-only plan; new data needs its own battery plan + Julio cost approval |
| Re-runs for `tail_complete=False` traces | Julio's call after reading the report, not the autopilot's |
| Engine/prompt/model changes for any FAIL found | Reported with evidence; fixes are separate iterations (max 3 iters per plan) |
| Costs investigation (`lf.py costs` 400) | Broken server-side; one-line note, revisit when server fixed |
| Porting further SDK pieces (ladder, eval, costs) | Only digest+lat are proven needed; port on demand |
