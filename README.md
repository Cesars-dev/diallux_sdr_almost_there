# clean_diallux_SDR — Dialux SDR workspace (clean fork)

> **FORK of `/home/julio/projects/Retell_AI_MCP_connection/` (2026-09-08), restructured
> per STRUCTURE.md. The ORIGINAL still serves live traffic :8000–8003 — this repo does
> not touch it (cutover only by explicit plan; DOCTRINE §6).**

## What lives here (one repo, one tree, zero nesting)

```
                    ┌────────────────────────────────────────────────┐
   voice pipeline   │ engine/     the LangGraph 9-state agent        │
   (iter7→iter31,   │             23 branches: engine/*             │
   one branch per   │ retell/     deployed agent lines (config-as-   │
   iteration)       │             code): sdr/ V7.x + heating-uk/    │
                    │ services/   the 3 live endpoints + proxy_guard │
                    │ docs/       SOPs, APIs, doctrine              │
                    │ plans/      NEXT_STEPS + archive of all plans  │
                    │ research/   EVIDENCE (gitignored): surgeon     │
                    │             reports, transcripts, dumps        │
                    │ _cold_archive/ tarballs of every dead folder   │
                    └────────────────────────────────────────────────┘
```

## Status (2026-09-08)

- **Engine:** `engine/iter31-c3d-wrap-dampener` = latest iteration (prompt-cache C3:
  69.9% cache-hit, −52% tokens; end-call dampener; suite 129). `engine/main` = iter28
  merge (13/13 battery). iter29–31 not yet merged — per DOCTRINE they merge with receipts.
- **Retell SDR:** production artifact `retell/sdr/current/` (V7.9 slot-lock,
  agent `agent_f305981ef7b5ce312c1c899bbf`); version ladder in `retell/sdr/versions/`.
- **Heating UK:** `retell/heating-uk/` (V3.1 near-prod).
- **Services:** code only — DO NOT RUN here; live units still point at the original.
- **2026-09-08 session wrap:** hermetic suite verified **129 green** at this repo's path
  (receipt: `research/surgeon/suite-verification-fork/`); **LAW 0 v2** in force (code =
  owner-gated merges, docs = straight to main); next = iteration import from the original
  → validate. Live queue: `plans/NEXT_STEPS.md`.

## Read first (60-second contract, DOCTRINE §7)

1. **AGENTS.md** — operating manual (what/how/where)
2. **DOCTRINE.md** — the law: `plan→branch→iterate→test→report→commit→merge`
3. **GIT_TREE.md** — the living map (auto: `scripts/git-tree.sh` after every merge)
4. **STRUCTURE.md** — why the tree is shaped this way + old→new MIGRATION_MAP
5. **plans/NEXT_STEPS.md** — the live queue

## The iteration model (short version)

**⚖️ LAW 0 — THE GIT CRYSTAL BALL (v2):** **CODE = full discipline** — branch per plan,
test, report, and **NO merges without Julio's explicit say-so, ever**. **DOCS = free** —
md files (these root docs, plans/, notes) commit straight to main, no ceremony. History
surgery (rebase/force/delete/rename) always needs say-so; tags only ride approved merges.

Every change = **branch** (`engine/iterNN-<slug>`) + **surgeon report**
(`research/surgeon/…`) + **battery receipts** → **ASK JULIO** → merge to `engine/main`
+ tag only on his word. Folder-photocopies are banned; the 9 snapshot folders + iter22
abort exist now as `engine/snap-*` branches (chained, diffable). Git is the memory.
Docs are the map. Evidence never lives inside source.

## Safety net

- All engine branches pushed to private `Cesars-dev/dialux-sdr-langgraph-v5-backup`
- Cold archive tarballs in `_cold_archive/` (gitignored): stale twin, state_machine
  copy, 9 snapshots, 6.1-era, retellai-mcp-server, old webhooks runtime
- Salvage manifests: `research/salvage/` (stale-twin iter21 divergence: 32 files;
  state_machine uniques; 227+135+293 transcripts preserved under research/transcripts/)
