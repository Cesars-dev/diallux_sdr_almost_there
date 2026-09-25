# STRUCTURE.md — The Reorganization Blueprint (read before touching anything)

> **What this is:** the approved architecture for `clean_diallux_SDR/`. This file is the contract:
> diagram → why per zone → migration map → execution order. If the tree and this file disagree,
> **the tree is wrong** — fix the tree or fix this file, never let them drift.
> Written 2026-09-08, by the systems-architect pass. Original workspace untouched & still serving :8000–8003.

---

## 1. THE TARGET — one repo, one tree, zero nesting

```
                            clean_diallux_SDR/            ← ONE git repo. PERIOD.
                            ┌─────────────────────────────┐
   live Retell agents  ────►│  retell/                    │ config-as-code. Deployed from
   (they never change)      │  agents/                    │ here via build+deploy scripts.
   engine :8000 hot-path ──►│  engine/                    │ The LangGraph voice pipeline.
   booking gate :8003 ─────►│  services/                 │ The 3 live systemd endpoints.
                            │  docs/                      │ SOPs, APIs, doctrine.
                            │  plans/  research/  history/│ process & evidence, gitignored.
                            └─────────────────────────────┘
     cold storage (NOT git, outside repo): _cold_archive/   ← tarballs of everything dead
```

**The four principles:**

1. **ONE .git at the root. No repo inside a repo. Ever.** Nested histories are preserved as
   root-repo refs (`engine/*`, `history/*`) so nothing is lost — but there is exactly one
   place `git status` means something.
2. **Zones by rate-of-change, not by history.** `retell/` (deployed artifacts, tagged,
   immutable), `engine/` (changes daily), `services/` (independent deployables), process
   zones (`plans/`, `research/`) gitignored where they're outputs.
3. **Iteration = branch + tag + report.** Not folder-photocopies. Git already solves
   versioning; we were running three redundant mechanisms (folders, snapshots, twins) for
   what tags do natively.
4. **Evidence lives outside repos.** Transcripts (400+), surgeon reports (156), battery
   artifacts — write-once outputs. They bloat clones and poison AI-agent context.

---

## 2. THE FULL ASCII TREE — what/where/why

```
clean_diallux_SDR/
│
├─ AGENTS.md                 ★ operating manual — the ONE file agents read first
├─ README.md                 ★ orientation: what this is, where everything is
├─ DOCTRINE.md               ★ the law: git-branch-iter-test-report-commit, branch/merge rules
├─ STRUCTURE.md              (this file) the architecture contract
├─ GIT_TREE.md               auto-refreshed git map — REGENERATED EVERY ITERATION (make git-tree)
├─ MIGRATION_MAP.md          old path → new path, machine-checkable (onegrep = one answer)
├─ .gitignore                hardened: evidence & runtime & secrets never enter
├─ .mcp.json                 Retell MCP config (unchanged)
│
├─ engine/ ────────────────── THE PRODUCT (was the typo dir; its .git becomes root refs)
│   ├── diallux/             the LangGraph pipeline package
│   │   ├── graph/           builder, llm, tools, subst — the 9-state brain
│   │   ├── prompts/         ★ live source-of-truth state prompts (*.md)
│   │   ├── media/           TTS/STT adapters, delivery profiles, normalization
│   │   ├── observability/   tracer, Langfuse SDK, latency/metrics
│   │   └── static/mic/      browser-mic bridge page
│   ├── agent/llm.json       state machine config (9 states, edges, gates, tools)
│   │   └── knowledge_bases/ 9 markdown KBs — sales craft corpus
│   ├── tests/               pytest suite (129) + llm2llm harness + personas (25)
│   │   └── llm2llm/json_logs/   ← gitIGNORED: transcripts are evidence, not source
│   ├── scripts/             lf.py, lfpull, rag_ingest, eval runners, deploy
│   ├── eval/                scenario definitions + report.json (gitignored output)
│   ├── ITERATIONS.md        ★ the engine's changelog — every iteration, rationale, verdicts
│   ├── notes.md             running session notes
│   ├── ARCHITECTURE.md / DECISIONS.md / DEPLOYMENT.md / RUNBOOK.md / TELEPHONY.md
│   ├── Dockerfile, docker-compose.yml, requirements.txt, pytest.ini
│   └── .env.example        (real .env stays gitignored at engine root)
│
├─ retell/ ────────────────── THE DEPLOYED AGENT LINES (config-as-code)
│   ├── sdr/                 Dialux SDR "Linda" — the V6.6→V7.9 ladder
│   │   ├── current/         ★ = V7.9_slot_lock content (deployed agent_f305…)
│   │   │   ├── retell/      llm.json, prompts/, tools/, edges/, KBs, deploy_v68.py
│   │   │   └── lab/         engine.py, run_ladder.py, langfuse_bridge.py, demo
│   │   ├── versions/        V7.5_lean → V7.8_reach_details (5 folders, read-only lineage)
│   │   │   └── MANIFEST.md  every version: agent_id, llm_id, why, verdict, dates
│   │   ├── testing/         ★ chat-line harness + runners (reg_one/adv_one)
│   │   │   └── json_logs/   ← gitignored 293 transcripts
│   │   ├── SKILL.md         build blueprint: how to build an SDR agent from scratch
│   │   ├── STATE.md         sdr-line lineage verdict + accepted trade-offs
│   │   └── config/          kb_registry.json + llm.json/agent.json
│   └── heating-uk/          "Tom" — UK HVAC voice line (was agents/heating_uk)
│       ├── multiprompt/V3.1 current build + V3 (prior) + WEBHOOK_TEST
│       ├── performance_tests/  runners + personas (json_logs gitignored)
│       ├── STATE.md
│       └── edits/ original_design/ single_prompt_test/
│
├─ services/ ──────────────── THE LIVE INFRASTRUCTURE (independent deployables)
│   ├── time_endpoint/       :8002 /time-function/* (systemd time-service)
│   ├── cal_slots_endpoint/  :8001 /check_availability (cal-slots) ← slots.db gitignored
│   ├── validator_endpoint/  :8003 /validator-function/* (validator-service)
│   └── proxy_guard/         iptables Retell masking + DNS watcher + RUNBOOK
│
├─ agents/ ───────────────── NO LONGER EXISTS. (was heating_uk — moved into retell/heating-uk/)
│
├─ docs/ ──────────────────── REFERENCE (from parent docs/ + Dialux_SDR root docs)
│   ├── BUILD-SOP.md         how to build a Retell agent end-to-end
│   ├── DEPLOYMENT-SOP.md    deploy chain incl. KB-registry upsert
│   ├── SERVICES_OVERVIEW.md the 3 endpoints at a glance
│   ├── KNOWLEDGE_BASE_STRUCTURE.md
│   ├── custom_endpoints.md  how to wire custom function tools + HMAC
│   ├── Testing_guidelines/  CALL / SALES / HUMANIZED SOPs + llm2llm testing
│   ├── api/                 Retell + Cal.com + MCP notes
│   ├── platform/            platform research
│   ├── deprecations/        what died and why
│   └── legacy/              dialux MEMORY.md, legacy maps (from _archive/legacy-dialux)
│
├─ plans/ ─────────────────── PROCESS (tracked) — was scattered root files + plans/
│   ├── NEXT_STEPS.md        ★ the single live queue (one item at a time)
│   ├── PENDING_TASKS.md     running backlog
│   ├── SOP_NEW_PLAN.md      plan-writing SOP (was new_plan_sop.md)
│   ├── archive/             all completed plan files (iter9…iter31), read-only
│   └── DEPLOY_V6.4_2026-08-22, V6.6_ITERATIONS_2026-08-22  (process snapshots)
│
├─ research/ ──────────────── EVIDENCE, NOT SOURCE (entirely gitignored from the repo)
│   ├── transcripts/         engine json_logs (135) + chat-line json_logs (293)
│   │                        + heating_uk logs — organized by line
│   ├── surgeon/             12 iteration folders: reports + battery artifacts
│   │                        (v5-pgvector-gpt52-argfix, iter28, iter31-c3, v76, v68…)
│   ├── reports/             engine reports/ (iter23/iter24 analysis artifacts)
│   ├── analysis/            per-build SOP analyses (was per-version analysis/ dirs)
│   ├── data/                exports & dumps (leads CSVs, scenario results, KB dump 2026-08-21)
│   └── salvage/             unique files rescued from stale twin + state_machine +
│   │                        anything unique in removed trees (MANIFEST.md lists each)
│
├─ history/ ──────────────── GIT ARCHAEOLOGY (gitignored working dir, refs in repo)
│   ├── nested-repos.md     ★ which nested repo was preserved under which root ref
│   │                        (engine/* = 13 iter branches; history/v79-simulator,
│   │                        history/state-machine-voice, history/retellai-mcp-server)
│   ├── V7.9_slot_lock/      the V7.9 nested .git, preserved as tarball+refs (PAT stripped)
│   └── (ref namespaces live in .git, working trees stripped to plain files)
│
└─ _cold_archive/ ─────────── OUTSIDE the repo. NOT in git. tarballs only.
    ├── diallux-twin-stale-correct-spelling.tar   (367 MB incl .venv — dead copy)
    ├── state_machine-copy.tar                     (980 KB — third copy)
    ├── v5-snapshots-all-9.tar                    (740 MB — folder-photocopy era)
    ├── dialux-6.1-iterations-era.tar             (V6.x legacy tree)
    └── old-parent-worktree.tar                   (untracked-by-old-git leftovers)
```

**Legend:** ★ = the few files a fresh agent must read first. `gitignored` = present on disk,
deliberately outside version control (evidence/runtime/secrets).

---

## 3. GIT MODEL — one root, no nesting, history preserved

```
   ROOT REPO (clean_diallux_SDR)  — created from the OLD parent's .git (heating_uk,
   docs, endpoints, plans lineage preserved), then:
     main ── c0 (dirty state captured) ── c1 RESTRUCTURE ── c2 docs+doctrine ──► you
     engine/* namespace: 13 refs imported from the typo-twin's .git
     (main, iter25-a…iter31-c3d, phaseB-wip-stash, tag iter29-winner)
     history/* namespace: refs from V7.9-simulator, state_machine_voice, retellai-mcp-server

   WHY import refs into the root?  You never lose a nested repo's history when you
   delete its .git — `git fetch <nested> refs/heads/*:refs/heads/engine/*` copies
   EVERYTHING (12 branches, stash, tags) into the root repo as plain refs.
   One `git log engine/iter31-c3d-wrap-dampener -- engine/diallux` answers any
   "what did the engine look like at iter31" question. Zero nesting, zero loss.
```

## 4. DOCTRINE (the law — full text lives in DOCTRINE.md)

- **⚖️ LAW 0 (v2) — THE GIT CRYSTAL BALL: CODE = branch + test + report + owner-gated
  merge (NO code merges without Julio's say-so, ever). DOCS/md/notes = straight to main,
  no ceremony. History surgery (rebase/force/delete) = always say-so.**
- **`git-branch-iter-test-report-commit`**: every experiment = plan file → branch
  `iterNN-<slug>` → work → battery → surgeon report → merge to `main` (or abandon with a
  one-line verdict). **No folder copies. No snapshots. Ever.**
- **Branch rules:** work directly on `main` only for docs/small fixes; **any code/prompt
  iteration diverges** on an `iterNN-*` branch; **merge** only with green suite + battery
  receipts. One variable per iteration.
- **Evidence writes into `research/`** (gitignored), never into `engine/` or `retell/`.
- **`make git-tree`** (helper script) regenerates GIT_TREE.md — **mandatory at every merge
  and every new-iteration commit**.
- **Secrets:** `.env` files gitignored; keyhound before any push; no tokens in URLs — ever.
- **Systemd units still point at the OLD paths** until cutover (MIGRATION_MAP.md §cutover).

---

## 5. MIGRATION MAP (old → new — machine-checkable, do not lose)

| Old path (inside Retell_AI_MCP_connection) | New path (inside clean_diallux_SDR) |
|---|---|
| `Dialux_SDR/dialux-langgraph-production-v5/` (typo, LIVE) | `engine/` (+ refs `engine/*`) |
| `Dialux_SDR/diallux-langgraph-production-v5/` (correct, STALE) | `_cold_archive/…twin-stale.tar` (+ `research/salvage/` uniques) |
| `Dialux_SDR/state_machine/` | `_cold_archive/…state-machine-copy.tar` (+ salvage) |
| `Dialux_SD/R v5-snapshots/*` (9 folders) | `_cold_archive/…snapshots.tar` + tags (existing branch tips document the era) |
| `Dialux_SDR/V7.9_slot_lock/` | `retell/sdr/current/` (+ refs `history/v79-simulator/*`) |
| `Dialux_SDR/V7.5_lean…V7.8_reach_details` (5 folders) | `retell/sdr/versions/` |
| `Dialux_SDR/_archive/versions/` (V6.6→V7.4, 22 folders) | `retell/sdr/_archive_versions/` → gitignored cold (kept in tree, read-only) |
| `Dialux_SDR/_archive/6.1 iterations/` | `_cold_archive/…6.1-era.tar` (dead weight) |
| `Dialux_S STRUCTURE.txt/` (their old maps) | `docs/legacy/` |
| `Dialux_SDR/testing/` (chat harness + 293 logs) | `retell/sdr/testing/` (logs → `research/transcripts/chat-line/`) |
| `Dialux_SDR/tasks/surgeon/` (156 files) | `research/salvage/surgeon/` (uniques) → `research/surgeon/` |
| `Dialux_SDR/plans/` (was in parent `plans/`) | `plans/archive/` |
| `Dialux_SDR/config/`, `STATE.md`, `SKILL.md` | `retell/sdr/` |
| `Dialux_SDR/Knowledge bases/` (5 authoring MDs) | `retell/sdr/kb_authoring/` |
| `Dialux_SDR/compaction/` | `research/salvage/compaction/` |
| `agents/heating_uk/` | `retell/heating-uk/` |
| `time_endpoint/` `cal_slots_endpoint/` `validator_endpoint/` | `services/` |
| `proxy_guard/` | `services/proxy_guard/` |
| `docs/` | `docs/` |
| `plans/` (parent, tracked) | `plans/` (live files) + `plans/archive/` |
| root loose files (`NEXT_STEPS.md`, `new_plan_sop.md`, …) | `plans/` |
| `data/` (exports, kb_dump) | `research/data/` |
| `_archive/legacy-dialux/` (groq era) | `docs/legacy/` |
| `_archive/retellai-mcp-server/` | `_cold_archive/…retellai-mcp.tar` (+ refs `history/retellai-mcp-server/*`) |
| `_archive/old-webhooks-runtime/` | `_cold_archive/…old-webhooks.tar` |
| `_archive/knowledge_bases_root_authoring_snapshots/` | `research/salvage/kb-authoring-snapshots/` |
| `.kilo/` `.vscode/` `__pycache__/` `.DS_Store` … | deleted (runtime noise) |

---

## 5.1 WHAT GETS DELETED vs SALVAGED vs KEPT (dead-weight rules)

**Deleted outright (runtime noise, zero informational value):**
- All `.venv/` trees (recreatable from requirements.txt; the fork's engine may keep ONE
  working venv at engine root, gitignored)
- All `__pycache__/`, `.pytest_cache/` (bytecode caches)
- `.DS_Store`, `.kilo/` (IDE/agent runtime), `.vscode/` (recreate settings if wanted)
- Empty dirs; `carpeta sin título` (was never in this tree; noted for workspace hygiene)

**Tarballed to `_cold_archive/` (dead weight, but history — never `rm`):**
- Stale twin (`diallux-langgraph-production-v5`, 367 MB) — after unique-file salvage
- `state_machine/` copy — after unique-file salvage
- All 9 `v5-snapshots/` folders (740 MB) — their content = git tags + existing branches
- `6.1 iterations/` legacy V6-era tree
- `_archive/retellai-mcp-server/` (nested repo → refs preserved first)
- `_archive/old-webhooks-runtime/`

**Kept in tree, read-only lineage:**
- `retell/sdr/versions/` — V7.5→V7.8 folders (small, referenced by MANIFEST.md)
- `retell/sdr/_archive_versions/` — the 22 V6.6→V7.4 folders (kept in place, gitignored
  to avoid bloating the repo, MANIFEST describes each)
- `plans/archive/` — all iter9→iter31 plan files

**Moved to `research/` (evidence):** all json_logs, surgeon folders, reports/, analysis/,
data/, compaction/, battery artifacts, kb-authoring snapshots.

## 6. EXECUTION ORDER (why this order — each step gates the next)

```
 0. STRUCTURE.md saved (this file) ──► you approve/execute against it
 1. c0 commit: capture the fork's dirty tracked state (parent .git has 50 dirty files)
    → the old repo's truth is frozen in history BEFORE the tree changes shape
 2. Ref-import: engine .git + V7.9 .git + state_machine_voice .git + retellai-mcp-server
    .git → root refs (engine/*, history/*) — HISTORY IS NOW SAFE INSIDE THE ROOT
 3. Salvage pass: stale twin + state_machine + snapshots → uniques to research/salvage/
    (MANIFEST.md per file: what/why rescued) — NOTHING UNIQUE IS LOST BEFORE TARBALL
 4. Tarball dead weight → _cold_archive/ + delete originals (mv first, verified tarballs)
 5. The big mv: engine/ retell/ services/ docs/ plans/ research/ per the tree above
 6. Purge venvs/pycache/IDE noise; harden .gitignore
 7. Write root docs: AGENTS.md, README.md, DOCTRINE.md, GIT_TREE.md, MIGRATION_MAP.md
 8. c1/c2 commits; verify: git status clean, ONE .git, all engine/* refs alive
 9. Push root → private GitHub backup repo (token via header, never in URL)
10. Cutover day (LATER, only on your order): repoint systemd units to this tree
```

**Worst case at every step:** we're on the fork; original still live; GitHub already
holds all 13 engine branches. Nothing in this plan can touch production.
