# PLAN — MVP-Finally: branch baptism + registry naming + the battery (new session)

## Meta
- Date: 2026-09-16
- Project root: `/home/julio/projects/clean_diallux_SDR` (double-L — the REAL repo; see TRAPS)
- Scope: open ONE new branch `engine/mvp-finally` cut from the proven iter49c state, name it **MVP-Finally** in the md ledger (ITERATIONS.md) and in the SQL registry, then run the battery on it in a SEPARATE owner-gated session. Iterations on MVP-Finally = plain commits on the branch (no iterNN renumbering).
- Status: setup tasks T1–T3 execute THIS session on owner instruction; battery tasks T4–T6 are the NEXT session (owner present).

## Compaction Context (session state at plan time — pin, do not re-derive)
- iter49h T7/T8/T9 are DONE. Work branch `engine/iter49c-engine-finish` @ **`1f15e8b`** (lineage `fc42a3e` → `94d0082` → `c8dd05a` → `a4b53b3` → `ffee30d` → `0c8a743` T7 pin → `1f15e8b` T7 flaky fix) — UNMERGED (LAW 0).
- Gates at `1f15e8b` (verified this session): suite **305 passed**, smoke **7/7 PASS**, gold replay **GATE PASS** (right-vertical 0.788 pooled AND mean, zero-chunk 1/47, chunks/turn 2.17), offline gates re-run after every change.
- T8 delivered: `research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (8 sections), ledger findings **FIND-10..14** inserted (count 9→14 verified by SQL; actual max was FIND-9, not the plan's assumed FIND-6), PT-49 = implemented offline @ `1f15e8b`, AGENTS.md Eval SOP = both ledgers + ritual.
- T9 delivered: registry `research/surgeon/iter47-call-ledger/ledger.db` rebuilt with ZERO loss (93 branches / 1217 commits / 16 runs / 428 calls; pinned-window attribution 86/86 preserved; backup `ledger.db.pre-iter49h.bak`). `tree.md` written. `call_ledger.py` recovered byte-proven (blob `dadf9c2`) and staged UNTRACKED at BOTH `/home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` and `/home/julio/projects/clean_diallux_SDR/engine/scripts/call_ledger.py` — commit to main = owner ASK (d), still OPEN.
- json_logs CONSOLIDATED: all 428 call logs now in the canonical `/home/julio/projects/clean_diallux_SDR/engine/tests/llm2llm/json_logs/` (gitignored); registry coverage from that ONE dir = 428/428. Ritual corrected in AGENTS.md (`2acea96`): run the build from the MAIN `engine/` checkout, never a fresh worktree (0 jsons → silently empty calls table), and the script resolves JSON_LOGS/.env from `__file__`-derived ROOT, not cwd.
- FIND-5 mechanics (the ack speed answer): gpt-5.4 prompt-caches ONLY tool-bearing requests; the state-entry ack carries the FULL tool array (byte-identical heavy prefix) and rides the transition/greeting warm at the 2688/3712 cache floor. OPEN ASK carried: dummy-tool + `entry:<state>` warm (iter49f recipe) vs the landed real-tools port — owner decides, no advocacy.
- **The 4 standing owner ASKs from iter49h T8:** (1) live battery go? (2) merge consent `engine/iter49c-engine-finish` (+ `engine/iter47-call-ledger`), (3) dummy-tool vs real-tools, (4) commit `call_ledger.py` to main. The owner's answer to (1)+(2) is: new branch **MVP-Finally** first, battery on it in a new session, merge decided after.
- Owner directive 2026-09-16: name the branch **MVP-Finally** in md files AND SQL; open a new branch to test on; battery runs in a NEW session.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Branch name: git = `engine/mvp-finally`, display name = **MVP-Finally** (md + SQL narrative) | owner 2026-09-16; git lowercase keeps shell/ref hygiene, display name stays MVP-Finally everywhere humans read |
| Cut point: `engine/iter49c-engine-finish` @ `1f15e8b` — NOT from main | main is stale at the iter28 merge (5e9d088); iter49c carries the proven state (suite 305 + gates); the whole point of MVP-Finally is to stabilize THAT line |
| Iterations on MVP-Finally = commits on the branch; no iterNN renumbering | owner: "that will be the name on the branch we can iter by commits" |
| Battery = separate NEW session, owner present | owner directive 2026-09-15/16 (same gate as iter49h's deferred live session) |
| ITERATIONS.md line must contain the literal lowercase string `mvp-finally` | registry `summary_for_branch` matches `base in ln` case-sensitively (no iter-number fallback exists for this name) |
| The registry gains the branch via the REFRESH RITUAL (backup → build), not hand-INSERT | the registry is a derived view of git; hand rows = guessing (owner: "no guessing") |

## TRAPS (paid for — violating = repeat mistakes)
1. **Spell it `MVP-Finally` — double L** (M-V-P-F-i-n-a-l-l-y). Never `MVP-Finaly`. Same class as the diallux/dialux trap: this workspace has TWO look-alike dirs — `/home/julio/projects/clean_diallux_SDR` (double-L, REAL) vs `/home/julio/projects/clean_dialux_SDR` (single-L, stale gutted twin). ALL paths below are double-L. Verify with `ls -d` if in doubt.
2. Registry build: run from the MAIN checkout's `engine/` dir (`ROOT` = `__file__`-derived); `build()` UNLINKS its `--db` target — ALWAYS backup first and point `--db` at the real ledger only after a scratch-verified run (iter49h T9 proved the scratch-first method).
3. NO `sqlite3` CLI on this box — `.venv/bin/python -c "import sqlite3; …"`.
4. pip only as `<venv>/bin/python -m pip …` (bin/pip shebang points at the original live venv).
5. Never run python with cwd=`/home/julio` (`~/fastembed/` shadows the package).
6. Model id has the org slash: `snowflake/snowflake-arctic-embed-m`.
7. A suite green-count can be RACY-green — always re-run the FULL suite after any change.
8. Cal.com event 3801235 is REAL — cancel every test booking after any battery/live session.

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Live battery go (owner present) | T4–T6 are the next session; owner says when |
| Merge consents (iter49c + iter47-call-ledger branches) | owner, after the battery verdict |
| dummy-tool vs real-tools on the ack | owner ASK carried from iter49g/T8 — decide before or after battery; battery runs fine either way (the real-tools shape is what ships today) |
| commit `scripts/call_ledger.py` to main (which path: root `scripts/` vs `engine/scripts/` — the run-proven one is `engine/scripts/`) | owner ASK (d) |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-mvp/.venv/bin/python` (3.12.3; symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`).
- Worktree: `/tmp/opencode/wt-mvp` (branch `engine/mvp-finally`, cut from `engine/iter49c-engine-finish` @ `1f15e8b`).
- `.env`: copy from `/home/julio/projects/clean_diallux_SDR/engine/.env` (gitignored).
- Postgres `localhost:5434/diallux` (DSN in `.env`); `kb_chunks_v2` 193 chunks / 768-d (arctic-m) — owned by `scripts/kb_reembed.py` only.
- Langfuse `http://localhost:3001` (keys in `.env`).
- Ports: live services `:8000`–`:8006` NEVER touch; `:8007` owner live-test NEVER start/stop.
- Registry: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` (93 branches / 1217 commits / 16 runs / 428 calls as of the iter49h T9 rebuild).
- Generator: `/home/julio/projects/clean_diallux_SDR/engine/scripts/call_ledger.py` (staged, untracked — commit = owner ASK).

## Architecture (the MVP-Finally arc)
```
engine/iter49c-engine-finish @ 1f15e8b  (suite 305 · smoke 7/7 · replay GATE PASS)
        │  git worktree add -b engine/mvp-finally
        ▼
engine/mvp-finally  "MVP-Finally"  ── iterations = commits on this branch
        │
        ├── T4 happy gate (Maria) → live TTFT/cache gates → lf bugs → cancel bookings
        ├── T5 full battery (first-13 + price-push) → live_sql gates → report
        └── T6 verdict → owner ASK → [on say-so: merge --no-ff → tag → git-tree.sh]
```

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-mvp/` | NEW worktree, branch `engine/mvp-finally` @ cut = `1f15e8b` | New (git) |
| `/tmp/opencode/wt-mvp/.venv` | symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv` | New (symlink) |
| `/tmp/opencode/wt-mvp/.env` | copy of `/home/julio/projects/clean_diallux_SDR/engine/.env` | New (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | append the MVP-Finally ledger line (contains literal `mvp-finally`) | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` | refresh ritual → gains the `engine/mvp-finally` branch row | Edit (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db.pre-mvp-finally.bak` | pre-refresh backup | New (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/mvp-finally/01_battery.md` | T5 battery report (NEXT session) | New (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_mvp_finally_branch_2026-09-16.md` | this plan | New (docs → main) |

## Deploy Rules
- Branch creation: `git -C /home/julio/projects/clean_diallux_SDR worktree add /tmp/opencode/wt-mvp -b engine/mvp-finally engine/iter49c-engine-finish` — NO merge, NO push without owner; `scripts/keyhound` before any push.
- NEVER touch: live services `:8000`–`:8006`, owner port `:8007`, production agent IDs (`agent_f305…` sdr chat, `agent_1698…` heating voice, `agent_87e4…` chat), deployed Retell LLMs (read snapshots only), Cal.com event 3801235 (REAL — cancel every test booking), docker `diallux-db` schema, the ORIGINAL workspace.
- After ANY owner live/battery session: cancel ALL test bookings.
- No merges of code branches without Julio's explicit say-so (LAW 0). Docs (md) = straight to main.

## Tasks (in order)

### T1 — Cut the MVP-Finally branch (this session)
Goal: `engine/mvp-finally` exists @ `1f15e8b` with a green baseline.
Files: worktree `/tmp/opencode/wt-mvp` + `.venv` symlink + `.env`.
Commands (full):
```bash
git -C /home/julio/projects/clean_diallux_SDR worktree add /tmp/opencode/wt-mvp -b engine/mvp-finally engine/iter49c-engine-finish
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-mvp/.venv
cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-mvp/.env
cd /tmp/opencode/wt-mvp && .venv/bin/python -m pytest tests -q   # expect 305 passed
```
Verification: `git -C /tmp/opencode/wt-mvp branch --show-current` = `engine/mvp-finally`; `git log --oneline -1` = `1f15e8b`; suite 305 passed; `.env` present with `LANGFUSE_HOST=http://localhost:3001`.
Dependencies: none (owner instruction received).

### T2 — Name it in the md ledger (this session, docs → main)
Goal: MVP-Finally exists as a named ledger entry.
Files: `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` (append at the end).
Content (one bullet, must contain the literal lowercase `mvp-finally`):
`- **MVP-Finally (\`engine/mvp-finally\`, cut from \`engine/iter49c-engine-finish\` @ \`1f15e8b\`) — the stabilization/battery branch (NOT iterNN-numbered; iterations = commits). State at cut: suite 305, smoke 7/7, gold replay GATE PASS (0.788 / 1/47 / 2.17); registry rebuilt 93/1217; json_logs consolidated 428. Battery = NEXT session (owner-gated); report → research/surgeon/mvp-finally/.**`
Verification: `grep -c "mvp-finally" engine/ITERATIONS.md` ≥ 1; docs commit to main (`git add engine/ITERATIONS.md && git commit`).
Dependencies: T1 (so the line records a branch that actually exists).

### T3 — Name it in SQL (this session, refresh ritual)
Goal: the registry (SQL) carries the MVP-Finally branch — via the ritual, no hand-INSERTs.
Commands (full, from the MAIN checkout — TRAP: not a fresh worktree):
```bash
cp /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db \
   /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db.pre-mvp-finally.bak
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python \
  /home/julio/projects/clean_diallux_SDR/engine/scripts/call_ledger.py build \
  --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db
```
Verification (SQL, no vibes):
```bash
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -c "
import sqlite3; c=sqlite3.connect('/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db')
print(c.execute(\"SELECT name, head_commit, status FROM branches WHERE name='engine/mvp-finally'\").fetchone())
print(c.execute(\"SELECT summary_line FROM branches WHERE name='engine/mvp-finally'\").fetchone()[0][:120])
print('branches:', c.execute('SELECT count(*) FROM branches').fetchone()[0], 'commits:', c.execute('SELECT count(*) FROM commits').fetchone()[0])"
```
Expected: row `engine/mvp-finally` head `1f15e8b`, status open, summary = the T2 ITERATIONS.md line; branches 94 (93 + this one), commits still 1217 (no new commits yet); calls/runs UNCHANGED (428/16) — the ritual rebuilds from the consolidated json dir (428/428 proven).
Dependencies: T2 (ITERATIONS.md line must exist BEFORE the build so the summary matches).

### T4 — Happy-path gate (NEXT session, owner present)
Goal: prove the MVP on live calls before any stress — never stress a broken flow.
Files: none (runs only); evidence → `/home/julio/projects/clean_diallux_SDR/research/surgeon/mvp-finally/`.
Commands (full, from `/tmp/opencode/wt-mvp`):
```bash
cd /tmp/opencode/wt-mvp && set -a && . ./.env && set +a
.venv/bin/python -m pytest tests -q                       # 305 baseline re-confirm
.venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 48   # happy gate
.venv/bin/python scripts/lf_quick.py bugs --run happy-mvp-a
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py import --window "<HH:MM-HH:MM of the run>" --run happy-mvp-a --commit 1f15e8b
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py gates --a happy-mvp-a --b <baseline-run-id>
```
Live gates (from Langfuse/OTEL, named SQL not vibes): ack TTFT ≤ 800ms · first heavy ≤ 1300ms · awaited hot path ≤ +60ms · `cache_read` floors 2688/3712 (heavy turn-2+) AND the ack floor expectation (an ack after a landed transition warm shows `cache_read` ≈ the heavy floor — a cache-0 ack = the warm didn't land → investigate, don't shrug) · `lf_quick.py bugs` ALL COVERED · `live_sql.py gates` no new failure.
After: CANCEL ALL test bookings (Cal.com event 3801235 is REAL).
Dependencies: T1–T3 + owner present.

### T5 — Full battery + report (NEXT session)
Goal: first-13 + price-push on MVP-Finally; verdict with numbers.
Commands: same env as T4, then `.venv/bin/python scripts/lf_eval.py ladder` (skips Larry) + the battery run; import as `battery-mvp-a` per the Eval SOP naming; re-run `lf_quick.py bugs` after EVERY fix commit (revisions break other things).
Report: `/home/julio/projects/clean_diallux_SDR/research/surgeon/mvp-finally/01_battery.md` — score, latency trios (e2e/TTFT/turn-1), cache floors vs gates, bug-coverage table, autopsies for any failure (per AGENTS.md Eval SOP).
Dependencies: T4 green.

### T6 — Verdict + merge ASK (NEXT session)
Goal: owner decision with evidence.
Content: battery verdict → ASK: (a) merge `engine/mvp-finally` to main? (b) merge/close the standing consents (`engine/iter49c-engine-finish` consumed by the cut — its content IS MVP-Finally's base; (c) dummy-tool vs real-tools (carried); (d) commit `call_ledger.py` to main.
On owner say-so: `git merge --no-ff` per LAW 0 + tag + `scripts/git-tree.sh` + ITERATIONS.md line.
Dependencies: T5.

## Validation Plan (end-to-end)
1. T1: branch exists at `1f15e8b`, suite 305 green in `/tmp/opencode/wt-mvp`.
2. T2: ITERATIONS.md line with literal `mvp-finally`, docs commit on main.
3. T3: registry row `engine/mvp-finally` verified by SQL; calls/runs unchanged (428/16); backup exists.
4. T4 (next session): happy gate PASS + live gates measured; bookings cancelled.
5. T5 (next session): battery score + report; no regression vs iter48's 13/13 and iter49h offline gates.
6. T6 (next session): owner verdict recorded; merge only on say-so.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merging `engine/iter49c-engine-finish` and `engine/iter47-call-ledger` | owner ASK after the battery verdict (LAW 0) |
| dummy-tool + `entry:<state>` warm (iter49f recipe) vs landed real-tools ack | open owner ASK (carried from iter49g/T8) |
| Committing `call_ledger.py` to main (root `scripts/` vs `engine/scripts/`) | owner ASK (d); the run-proven location is `engine/scripts/` |
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` (after MVP-Finally proves) |
| Fork cutover to serving production | DOCTRINE §6 — owner-ordered cutover, separate plan |
| Deferral lane-A pricing-vocab tweak; PT-43/44/48 parked bugs | separate plans per owner |
