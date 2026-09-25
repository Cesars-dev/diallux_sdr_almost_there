# MIGRATION_MAP.md — old path → new path (machine-checkable)

> This fork's tree was restructured from `Retell_AI_MCP_connection/` per STRUCTURE.md.
> Every legacy path an agent might reference resolves here. If a path isn't listed,
> it's in `_cold_archive/` (tarball) or `research/salvage/` (recovered uniques).

| Legacy path (inside Retell_AI_MCP_connection) | Now at (clean_diallux_SDR/…) | Notes |
|---|---|---|
| `Dialux_SDR/dialux-…-v5` **(typo = LIVE repo)** | `engine/` + refs `engine/*` (23 branches) | renamed; nested .git stripped; history in root refs |
| `Dialux_SDR/diallux-…-v5` **(correct = STALE twin)** | `_cold_archive/diallux-twin-stale-correct-spelling.tar` | 32 unique files salvaged → `research/salvage/stale-twin-iter21-divergence/`; 227 transcripts → `research/transcripts/engine-stale-twin-logs/` |
| `Dialux_SDR/state_machine/` | `_cold_archive/state-machine-copy.tar` | 2 unique docs → `research/salvage/state-machine-copy/` |
| `Dialux_SDR/v5-snapshots/v1.3-iter7 … v1.8-iter20` (9 folders) | `_cold_archive/v5-snapshots-all-9.tar` + branches `engine/snap-v1.3-iter7 … snap-v1.8-iter20` (chained) | source-only imports (venv/secrets/transcripts excluded) |
| `Dialux_SDR/_archive/v5-iter22-aborted-20260906/` | branch `engine/snap-iter22-aborted` (3 docs) + `_cold_archive/dialux-6.1-iterations-era.tar` | |
| `Dialux_SDR/V7.9_slot_lock/` | `retell/sdr/current/` | nested .git stripped; refs `history/v79-simulator/*` (⚠️ remote URL contains exposed PAT — rotate; see §security) |
| `Dialux_SDR/V7.5_lean … V7.8_reach_details` (5 folders) | `retell/sdr/versions/…` | read-only lineage |
| `Dialux_SDR/_archive/versions/` (22 folders V6.6→V7.4) | `retell/sdr/_archive_versions/` | kept in tree, MANIFEST pending |
| `Dialux_SDR/_archive/6.1 iterations/` + `_archive` rest | `_cold_archive/dialux-6.1-iterations-era.tar` | |
| `Dialux_SDR/testing/` (chat harness + 293 transcripts) | `retell/sdr/testing/` (harness+runners) · `research/transcripts/` (logs) | |
| `Dialux_SDR/tasks/surgeon/` (12 folders, 156 files) | `research/surgeon/` | |
| `Dialux_SDR/tasks/v7.8_appt_confirmed/` | `research/salvage/tasks-v78-appt/` | |
| `Dialux_SDR/config/` · `SKILL.md` · `STATE.md` · `README.md` · `SOURCES.md` | `retell/sdr/…` | |
| `Dialux_SDR/Knowledge bases/` (authoring docs) | `retell/sdr/kb_authoring/` | |
| `Dialux_SDR/compaction/` | `research/salvage/compaction/` | |
| `agents/heating_uk/` | `retell/heating-uk/` | |
| `time_endpoint/` · `cal_slots_endpoint/` · `validator_endpoint/` · `proxy_guard/` | `services/…` | **live units still point at ORIGINAL paths — cutover = explicit plan** |
| `docs/` | `docs/` (+ `docs/legacy/dialux-groq-era/` from `_archive/legacy-dialux/`) | |
| `plans/` + root `NEXT_STEPS.md` `PENDING_TASKS.md` `new_plan_sop.md` | `plans/` (live) · `plans/archive/` (28 items) · `plans/SOP_NEW_PLAN.md` | |
| `data/` (exports, kb_dump_2026-08-21) | `research/data/` | |
| `PROJECT_STRUCTURE.txt` | `docs/legacy/PROJECT_STRUCTURE_old.txt` | superseded by GIT_TREE.md |
| `_archive/retellai-mcp-server/` (nested repo) | `_cold_archive/retellai-mcp-server-nested.tar` + refs `history/retellai-mcp-server/*` | |
| `_archive/old-webhooks-runtime/` | `_cold_archive/dialux-6.1-iterations-era.tar` | |
| `_archive/knowledge_bases_root_authoring_snapshots/` | `research/salvage/kb-authoring-snapshots/` (23 files) + tarball in 6.1-era | |
| Root `.env` | kept (gitignored) | same as original |

## Security ledger (open items)

1. **Exposed PAT** in old V7.9 remote URL (`ghp_5Q…` at `github.com/Cesars-dev/dialux-sdr-simulator`) — present in the ORIGINAL workspace git config; refs imported here are clean (no remotes carried). **Owner action: rotate on GitHub.** Tracked in plans/PENDING_TASKS.md.
2. Stray GitHub repo `Cesars-dev/scope-test-nonexistent` (empty, from token scope-test) — delete via UI (token lacks delete).
3. Known plaintext creds in some legacy docs (see original AGENTS.md notes) — keyhound before any push of docs/legacy.

## Cutover checklist (do NOT do until explicitly planned)

- [ ] Repoint `cal-slots.service`, `time-service.service`, `validator-service.service` WorkingDirectory/ExecStart → `services/*` here
- [ ] Pin `User=`/`Group=` in all 3 units (kills the chown race — the slots.db incident root cause)
- [ ] Restart + `python3 scripts/bridge.py` chain test green
- [ ] Freeze original (rename to `Retell_AI_MCP_connection_FROZEN_2026-09-08` or similar)
- [ ] Update opencode skills referencing `Retell_AI_MCP_connection/` paths (langfuse-call-analysis, sop_call_analysis, new-plan, cartesia-iterations)
