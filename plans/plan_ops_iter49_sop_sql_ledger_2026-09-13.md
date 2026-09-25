# PLAN — OPS: seed SALES + HUMANIZED SOP results into the SQLite ledger (same DB as latency)

## Meta
- Date: 2026-09-13
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: finish the 3-SOP → SQLite mechanic: seed the SALES and HUMANIZED past-audit rows into the `sops` table (CALL is already seeded), add the persist section to the two individual SOP md files, and commit the already-built+dry-tested `live_sql.py` extension on the engine branch.
- Status: PLAN ONLY (not started — awaits owner approval; execute in a NEW session)

## Compaction Context

**Project:** Dialux SDR v5 — LangGraph re-implementation of the deployed Retell chat agent
(Linda). Engine worktrees under `/tmp/opencode/wt-iterNN`, branches `engine/iterNN-*`.
Evidence lives in `research/` (gitignored) + SQLite ledgers.

**What already exists (built + dry-tested 2026-09-13, this session — DO NOT rebuild):**
1. **`sops` table** added to `SCHEMA` in `/tmp/opencode/wt-iter44/scripts/live_sql.py`
   (branch `engine/iter48-rag-truth`, **UNCOMMITTED** — the only code change pending commit):
   ```sql
   CREATE TABLE IF NOT EXISTS sops (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     run_id TEXT, trace_id TEXT, ts TEXT,
     sop TEXT, category TEXT, scope TEXT,
     verdict TEXT, rule TEXT,
     failure_reason TEXT, failure_assessment TEXT,
     evidence TEXT, source TEXT
   );
   ```
2. **SDK subcommands** in the same file: `sop-import --run <run_id> --sop CALL|SALES|HUMANIZED
   --file <rows.json> [--trace <id>]` (idempotent — re-import skips identical rows;
   verdicts validated to PASS/PARTIAL/FAIL/OBSERVATION) and `sops [--run] [--sop]
   [--verdict] [--json]` (grouped human output or machine JSON).
3. **Dry tests passed** against a COPY (`/tmp/opencode/sop_dry/ledger_dry.db`): 29-row
   CALL seed imports clean, second import skips all 29, `--verdict FAIL` query works,
   bad verdict rejected, REAL ledger untouched (verified same mtime + no sops table).
4. **CALL SOP seeded:** `/tmp/opencode/sop_dry/seed_call_happy_b.json` (29 rows —
   4 happy-b calls × 7-8 CALL categories, trace_ids joined to the ledger:
   Maria `d054fe09…`, Danny `40d420db…`, Susan `59a4c5d4…`, Marcus `9d992a98…`).
   NOT YET imported into the REAL ledger (dry test only).
5. **Docs already updated:** `Retell_AI_MCP_connection/docs/Testing_guidelines/CALL-ANALYSIS-SOP.md`
   §9 + `Retell_AI_MCP_connection/docs/Testing_guidelines/full_call_analysys.md` Step 4
   (mandatory persist step covering all 3 SOPs with per-SOP category enums).

**The two ledgers (complementary, not conflicting):**
- `research/surgeon/iter48-rag-truth/ledger.db` — forensics layer: `runs/calls/rounds/rag/findings`
  + now `sops`. Round-level latency/RAG. THIS is "the same DB that holds latency".
- `research/surgeon/iter47-call-ledger/ledger.db` — verdict layer: `runs/calls` with
  precomputed e2e/ttft p50s + `branches/commits` git history tables. Read-only here.

**Source of truth for the mechanism:** the `live_sql.py` edit lives in the engine worktree
`/tmp/opencode/wt-iter44` (branch `engine/iter48-rag-truth` @ `033f742`, suite 270 green).
The ledger itself is in the main repo `research/` (gitignored — survives branch switches).
If wt-iter44 is gone, recover the script from branch `engine/iter48-rag-truth`.

**Latency SDK (already built this session, in main repo):**
`clean_diallux_SDR/scripts/latency_pull.py` + SOP `Retell_AI_MCP_connection/docs/Testing_guidelines/LATENCY-PERCENTILE-SOP.md`.
Unrelated to this plan except: same ledger, same discipline.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| ONE ledger, ONE `sops` table for all 3 SOPs | user 2026-09-13: "extend the one we have"; tables join by trace_id |
| `sop` enum: `CALL` / `SALES` / `HUMANIZED`; `verdict` enum: `PASS / PARTIAL / FAIL / OBSERVATION` uniform across SOPs | one query grammar for everything; SALES D-scores ride the `rule` field (e.g. `rule: "D3 1/2"`) |
| SALES `category` = `D1…D7`; HUMANIZED `category` = `R1…R5` (rule ids like `R5.5` in `rule`) | mirrors each SOP's own rule set; matches full_call_analysys.md Step 4 mapping (already written) |
| Seeds are curated JSON files stored NEXT TO their source report in `research/surgeon/…/` | evidence home (gitignored); re-importable; keeps provenance (`source` column points at the md) |
| Idempotent import stays (skip-on-identical) | past audits get bundled once; re-runs never duplicate |
| `live_sql.py` extension commits on the engine branch (one commit) | LAW 0: code = branch discipline; it is engine-tree tooling |
| SOP md updates go straight to the md files in `Retell_AI_MCP_connection/docs/Testing_guidelines/` | DOCS = straight to main (no ceremony) |
| One SOP at a time (SALES first, then HUMANIZED) | user instruction; each gets seed + md section + query sanity before moving on |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Which past reports contain per-call SALES D1–D7 scores (0–2 each) | read `research/surgeon/iter46-latency-floor/02_callsop_audit.md` + `research/surgeon/v5-pgvector-gpt52-argfix/` + iter48 battery report; if per-call D-scores were never written down (only band totals), seed `OBSERVATION` rows per call with the band in `evidence` — never invent numbers |
| Which past reports carry HUMANIZED R1–R5 verdicts (R5.5 echo hard flags) | `research/surgeon/iter48-rag-truth/05_battery_report.md` (FIND-8/PT-48 echo evidence, ~8/13 calls ≥1 echo turn) + iter47/48 call SOP audits; echo evidence per call: Maria t2, Marcus t4, Susan t10, Gene t4 (+Daniel/Jorge/Pedro/Brenda) |
| Trace_ids for persona calls in older runs (iter47-era calls have no ledger trace ids) | join by `run_id` only and leave `trace_id` NULL for rows whose source predates the iter48 ledger — acceptable; do NOT fabricate trace ids |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter44/.venv/bin/python` (3.12) — stdlib only for the sops path.
- Ledger: `clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (SQLite; tables
  `runs/calls/rounds/rag/findings/sops`). Iter47-era ledger: `research/surgeon/iter47-call-ledger/ledger.db`.
- SDK: `/tmp/opencode/wt-iter44/scripts/live_sql.py` (`sop-import`, `sops`, plus existing
  `import/runs/rounds/gates`).
- SOP docs: `Retell_AI_MCP_connection/docs/Testing_guidelines/{CALL,SALES,HUMANIZED}-ANALYSIS-SOP.md`,
  `full_call_analysys.md` (Step 4 already written).
- Seed sources (read-only): `research/surgeon/iter48-rag-truth/07_call_analysis_sop_happy_b.md`
  (done), `02_callsop_audit.md` (iter46), `05_battery_report.md` (iter48), `v5-pgvector-gpt52-argfix/` reports.
- Keyhound: `scripts/keyhound` before any push (engine branch).

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` — NO: the edit lives at `/tmp/opencode/wt-iter44/scripts/live_sql.py` | already edited (sops table + 2 subcommands); task = COMMIT it on the engine branch | Edit (commit only) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/sop_seed_call_happy_b.json` | CALL seed moved from /tmp staging into evidence folder (29 rows, already curated) | New (move) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/sop_seed_sales.json` | SALES rows from past audits (curated, trace_id joined where possible) | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/sop_seed_humanized.json` | HUMANIZED rows from past audits (R1–R5, echo flags) | New |
| `/home/julio/projects/Retell_AI_MCP_connection/docs/Testing_guidelines/SALES-ANALYSIS-SOP.md` | add "PERSIST TO THE LEDGER" section (same shape as CALL §9, SALES categories) | Edit |
| `/home/julio/projects/Retell_AI_MCP_connection/docs/Testing_guidelines/HUMANIZED-ANALYSIS-SOP.md` | same, HUMANIZED categories | Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` | gains SALES + HUMANIZED + CALL rows in `sops` (real import) | Edit (evidence) |

## Deploy Rules
- The ONLY code commit = `live_sql.py` sops extension, committed on the CURRENT engine
  branch in wt-iter44 (`engine/iter48-rag-truth`) OR carried to `engine/iter49-rag-parity`
  if iter49 already started in a fresh worktree — pick ONE, never both. NO merge/push
  without owner (LAW 0). Docs straight to main (Testing_guidelines).
- NEVER start/stop :8007 or live services :8000-:8006; never touch Retell agents/LLMs.
- Never modify the iter47 ledger (verdict layer is frozen history).
- Real imports go ONLY into `research/surgeon/iter48-rag-truth/ledger.db`.
- Keyhound before push; after any battery/live session cancel ALL test bookings (Cal.com event 3801235 REAL).

## Tasks (in order)

### T0 — Fresh-session context check
Goal: confirm the built mechanism is present and the ledger is intact.
Commands:
```
cd /tmp/opencode/wt-iter44 && git log --oneline -1 && git status --porcelain scripts/live_sql.py
grep -n "sop-import\|CREATE TABLE IF NOT EXISTS sops" scripts/live_sql.py | head -5
cd /home/julio/projects/clean_diallux_SDR
/tmp/opencode/wt-iter44/.venv/bin/python /tmp/opencode/wt-iter44/scripts/live_sql.py sops --run happy-b
```
Verification: HEAD `033f742` (+ only expected dirty files), sops schema + subcommands
present, `sops` query on the REAL ledger returns "no sop rows" (empty — imports happen later)
or already-seeded CALL rows if the CALL seed was imported.

### T1 — SALES seed + md section
Goal: SALES-SOP results queryable, SOP doc wired.
Steps: read the past SALES audits (BLOCKED table row 1) → curate
`research/surgeon/iter48-rag-truth/sop_seed_sales.json` (one row per call × D1–D7;
`rule` carries the score "x/2" where recorded; missing scores = OBSERVATION rows with
the band in `evidence`) → import to the REAL ledger → add the persist section to
`SALES-ANALYSIS-SOP.md` (copy CALL §9, swap categories to D1–D7 + score rule).
Commands:
```
cd /home/julio/projects/clean_diallux_SDR
/tmp/opencode/wt-iter44/.venv/bin/python /tmp/opencode/wt-iter44/scripts/live_sql.py sop-import \
    --run happy-b --sop SALES --file research/surgeon/iter48-rag-truth/sop_seed_sales.json
/tmp/opencode/wt-iter44/.venv/bin/python /tmp/opencode/wt-iter44/scripts/live_sql.py sops --sop SALES
```
Verification: import reports N rows (no duplicates on re-run); `sops --sop SALES` shows
grouped rows with reasons/assessments; every row's `source` points at the report it came from.

### T2 — HUMANIZED seed + md section
Goal: R-verdicts + echo hard flags queryable; SOP doc updated.
Steps: same formula — read past HUMANIZED evidence (05_battery_report.md FIND-8/PT-48:
Maria t2, Marcus t4, Susan t10, Gene t4 + Daniel/Jorge/Pedro/Brenda echo turns) → curate
`sop_seed_humanized.json` → import → md section (categories R1–R5, `rule` = R-id, e.g.
`R5.5` with "verbatim repeat = hard flag" in the assessment).
Commands: same as T1 with `--sop HUMANIZED` + `sop_seed_humanized.json`.
Verification: `sops --run happy-b --sop HUMANIZED --verdict FAIL` lists the R5.x hard flags
with quotes; battery-iter48 echo rows present (Maria t2, Marcus t4, Susan t10 at minimum).

### T3 — CALL seed lands in the REAL ledger
Goal: finish what the dry test proved (real DB gets the 29 CALL rows).
Commands:
```
cd /home/julio/projects/clean_diallux_SDR
/tmp/opencode/wt-iter44/.venv/bin/python /tmp/opencode/wt-iter44/scripts/live_sql.py sop-import \
    --run happy-b --sop CALL --file research/surgeon/iter48-rag-truth/sop_seed_call_happy_b.json
```
Verification: 29 rows (or fewer if already imported — idempotent); `sops --run happy-b`
shows all 3 SOPs grouped per call.

### T4 — Bundle sanity + commit
Goal: one-command cross-SOP view; mechanism committed.
Commands:
```
cd /home/julio/projects/clean_diallux_SDR
/tmp/opencode/wt-iter44/.venv/bin/python /tmp/opencode/wt-iter44/scripts/live_sql.py sops --run happy-b --json | head -40
cd /tmp/opencode/wt-iter44 && git add scripts/live_sql.py && git commit -m "iter49-ops: sops table + sop-import/sops subcommands — 3-SOP audit results in the call ledger (dry-tested; CALL/SALES/HUMANIZED seeds)"
```
Verification: json bundle contains CALL+SALES+HUMANIZED rows joined by trace_id;
commit lands clean on the engine branch (no push without owner).

## Validation Plan (end-to-end)
1. T0 pins the mechanism + intact ledger before touching anything.
2. Every seed row carries `source` = its md report; trace_id NULL only for pre-iter48 calls.
3. Idempotency proven per seed (import twice, second run skips).
4. Real ledger untouched EXCEPT the intended `sops` inserts; runs/calls/rounds/rag/findings byte-untouched.
5. Cross-SOP query (`sops --run <run>`) returns all 3 SOPs grouped — the "instant analysis" bar.
6. Docs: both individual SOP mds + full_call_analysys.md tell the same story (Step 4 already written).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| `latency_pull.py` + `LATENCY-PERCENTILE-SOP.md` commit (main repo scripts/docs) | separate owner call; already built + verified |
| Committing the SOP md edits in the ORIGINAL repo (Retell_AI_MCP_connection docs → main) | user asked to "fix the SOPs" — files are edited; committing is owner-gated |
| sop_call_analysis opencode-skill update (persist step) | optional follow-up once the mechanic is proven on a live audit |
| iter49 engine work (RAG parity) | `plans/plan_v5_iter49_rag_retrieval_parity.md` — separate plan, executes FIRST per its own order; the live_sql.py commit may ride its branch if that session runs first |
