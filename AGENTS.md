# AGENTS.md — Operating manual for AI agents working in this repo

> **Read this before touching anything.** One repo, one tree, zero nested repos.
> The law: DOCTRINE.md · the map: GIT_TREE.md · the why: STRUCTURE.md · the queue: plans/NEXT_STEPS.md.
> Fork of Retell_AI_MCP_connection (2026-09-08). The ORIGINAL still serves :8000–8003;
> **never run services from this repo until cutover** (DOCTRINE §6).

## ⏭️ NEXT UP (pinned by owner, 2026-09-23 11:50 UTC)

**NEXT SESSION = `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter70_speech_fixes_small.md`** (committed `e26fa40`).
Start at **T0 = HITL ASK** (owner GO before any code). Three SMALL fixes on clean main @ `8e06fe9` — nothing else:

1. **~10s pause → agent re-prompts itself once** (one-shot timer, rephrased, PT-68)
2. **Transition acks carry the next question** — the silent-ack win from iter68 T2, re-implemented small (PT-70)
3. **Merged-turn trim** — "?" yields; >2 questions/turn → trim (PT-69)
4. **speech_filter observability lines** (~10 lines, forensics only)

**Context (owner post-mortem 2026-09-23):** iter68/68-lite = PARKED, total failure ("our solutions caused more problems than they solved"). The overengineering — semantic cos dedupe, scripted-pass registries, 2-strike ladders, chain-link buffering — muted/truncated REAL speech. We fix small, on main, prompt-first, env-knob-first. **Do NOT cherry-pick or merge from `engine/iter68-speech-flow` / `engine/iter68-speech-lite`.** Reference plans (all on main): `plans/plan_v5_iter68_speech_flow.md` (v1, the good one) + v2 + v3; post-mortem rows PT-68..PT-73 in `plans/PENDING_TASKS.md`.
**Parked merge-ready:** `engine/iter67-twilio-live-lane` @ `0394a3b` (collision-free verified; merge = owner only).
**Voice LAW current:** `.env` `TTS_PROVIDER=cartesia` + `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` + `TTS_GATE_FAST_FIRST_FLUSH=false` + `TTS_DEDUPE_SEMANTIC=false`; same-turn dup guard + sanitizer stay ON (main defaults). Lane :8024 serves this state live.

## Zones and what they mean

| Zone | What it is | You may | You may NOT |
|---|---|---|---|
| `engine/` | The LangGraph voice pipeline (diallux brain, prompts, tests, harness) | iterate on `engine/iterNN-*` branches | commit evidence into it; create folder copies |
| `retell/sdr/` | Deployed Retell chat agent, config-as-code (`current/` = V7.9 slot-lock) + versions ladder | read; new version = new folder + MANIFEST + tag | patch a version in place; deploy without plan |
| `retell/heating-uk/` | UK HVAC voice agent line (V3.1 near-prod) | same discipline as sdr | same |
| `services/` | time :8002 / cal_slots :8001 / validator :8003 + proxy_guard — LIVE infra (original still serving) | read code, write docs | **start/stop/bind ports**; run uvicorn here |
| `docs/` | SOPs (BUILD, DEPLOYMENT, Testing_guidelines 3-SOP audit, api, legacy) | read first; update on drift | — |
| `plans/` | NEXT_STEPS.md (live queue) + SOP_NEW_PLAN.md + archive/ of every past plan | write plans per SOP | park active work anywhere else |
| `research/` | EVIDENCE: surgeon reports, transcripts (engine+chat+heating), batteries, dumps, salvage manifests | append; read for forensics | track in git (gitignored); put source there |
| `_cold_archive/` | tarballs of every dead folder (snapshots, stale twin, state_machine, 6.1 era, mcp server) | nothing | resurrect without explicit plan + owner OK |

## The iteration loop (DOCTRINE §1 — mandatory)

```
plan (plans/plan_*_iterNN_*.md) → branch engine/iterNN-<slug> → ONE variable
→ suite green (pytest engine/tests) → battery (first-13 + stress per SOPs)
→ report (research/surgeon/iterNN-slug/NN_*.md) → commits on the branch
→ ASK JULIO (LAW 0) → [on owner say-so: merge --no-ff → tag engine/iterNN
→ scripts/git-tree.sh → ITERATIONS.md ledger line]
```

- Happy-path gate first: never stress a broken flow (`--no-happy-gate` only on purpose).
- After every battery: cancel ALL test bookings (Cal.com event 3801235 is REAL).
- Abandoning an iteration? Leave the branch + one-line verdict in ITERATIONS.md.

## Hard rules (violations = revert on sight)

0. **⚖️ LAW 0 — THE GIT CRYSTAL BALL (v2):** **CODE = full discipline:** any code,
   prompt, agent-config, KB or services change → branch `engine/iterNN-<slug>` per
   approved plan → commit on branch → test → report → ASK. **NO merges of code branches
   without Julio's explicit say-so. Ever.** **DOCS = straight to main:** md files
   (README/AGENTS/DOCTRINE/GIT_TREE/STRUCTURE/MIGRATION_MAP/plans/notes/ITERATIONS)
   commit + push directly to main, no ceremony — nothing harmful in them (no secrets,
   no evidence bulk). **Always say-so:** rebase, force, branch delete/rename, history
   rewrite; tags only with owner-approved merges.
   **"Branch" is an owner trigger word (v2.1, 2026-09-22):** when Julio says
   "branch (it)", a NEW branch `engine/iterNN-<slug>` is cut from the current
   tip for that work — NEVER stack onto an existing iteration branch (lesson
   2026-09-22: the iter64c llm.json MODEL LAW bump rode the already-complete
   iter64 branch and merged with it), NEVER commit code/agent-config changes
   to main, and never do the new work on a branch that is awaiting merge.
1. **No repo inside a repo.** Nested histories live as refs (`engine/*`, `history/*`) — that's where they stay.
2. **No folder snapshots.** iter state = branches. Snap-era (`engine/snap-*`) is read-only archaeology.
3. **No tokens in URLs, no .env in git.** Run `scripts/keyhound` before any push. Rotate the exposed V7.9 PAT (known contamination — see MIGRATION_MAP).
4. **Evidence goes to `research/`** — transcripts, reports, dumps. Never inside engine/ or retell/.
5. **`scripts/git-tree.sh` after every merge** — GIT_TREE.md must never be >1 iteration stale.
6. **Never touch live agent IDs** (`agent_f305…` sdr, `agent_1698…` heating voice, `agent_87e4…` chat) without an explicit plan + owner instruction.
7. **KB policy stands**: reuse/upsert via `kb_registry.json` — never hand-create KBs (~$250 lesson).

## Where the history is (the thing agents always ask)

- Engine iterations iter21→iter31: branches `engine/iter*` (+`engine/main` = iter28 merge)
- Photocopy era iter7→iter20 + iter22-abort: branches `engine/snap-*` (chained chronologically; `git diff engine/snap-v1.3-iter7 engine/snap-v1.3-iter8` shows what iter8 changed)
- Stash: `refs/stashes/engine-phaseB` (phaseB WIP) + `engine/phaseB-wip-stash`
- Nested repos of the past: `history/v79-simulator/*`, `history/state-machine-voice/*`, `history/retellai-mcp-server/*`
- Folder-era archives: `_cold_archive/*.tar` (stale twin, 9 snapshots, state_machine, 6.1 era, mcp server, old webhooks)
- Old-path → new-path: MIGRATION_MAP.md

## Run & test (engine only; services are read-only here until cutover)

```bash
cd engine
.venv/bin/python -m pytest tests -q                    # suite (expect current count from ITERATIONS.md)
set -a; . ./.env; set +a                                 # secrets (gitignored)
.venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 48   # single persona
.venv/bin/python scripts/lf_eval.py ladder               # full SOP ladder (skips Larry the assassin)
```

Langfuse SDK: `scripts/lf.py` (health/traces/costs), `scripts/lf_eval.py status`.
Personas: 25 in `tests/llm2llm/personas.py` — 13 original + 12 adversarial; Larry is gated.
Reports of past batteries: `research/surgeon/v5-pgvector-gpt52-argfix/` and siblings.

## Eval SOP — SQLite call ledger (iter48+, MANDATORY for every engine iteration)

Every engine iteration MUST leave its call evidence in the SQLite ledger —
Langfuse is the source, SQLite is the workspace. **No run is "done" until it is
imported and verified by SQL.** Read
`research/surgeon/iter48-rag-truth/SQL_ANALYSIS_SOP.md` FIRST (exact design:
tables, import, bug-coverage queries, Langfuse cross-check, percentile fields).

- Ledger: `research/surgeon/iter48-rag-truth/ledger.db` (runs/calls/rounds/rag/findings).
- Import: `scripts/live_sql.py import --window "HH:MM-HH:MM" --run <name> --commit <sha>`.
- Quick pulls: `scripts/lf_quick.py runs|bugs|table|rounds|scaffold`.
- Gates are named SQL queries (`live_sql.py gates --a <a> --b <b>`), never "feels okay".

**TWO ledgers (different jobs):**
1. **Call/findings ledger** — `research/surgeon/iter48-rag-truth/ledger.db` (runs/calls/rounds/rag/findings): per-call evidence + the `findings` bug log. Schema + gates: `SQL_ANALYSIS_SOP.md` in the same folder.
2. **Branch/iteration registry** — `research/surgeon/iter47-call-ledger/ledger.db` (branches/commits/runs/calls): one queryable view of ALL `engine/*` branches + head commits. Generator: `scripts/call_ledger.py` — lives on branch `engine/iter47-call-ledger` (NOT on main; extract via `git show engine/iter47-call-ledger:scripts/call_ledger.py` — no merge needed to RUN it, commit to main = owner call). **Refresh ritual: re-run the build from the MAIN checkout's `engine/` dir at the END of every battery session** (the registry is a derived view of git; it goes stale otherwise) — backup `ledger.db` to `ledger.db.<tag>.bak` first. TRAP: run it from the MAIN `engine/` checkout — `json_logs` live there (a fresh worktree has none and the glob silently returns nothing = empty calls table), and the script reads `json_logs`/`.env` from `__file__`-derived ROOT, not cwd.
3. Reading either DB: NO `sqlite3` CLI on this box — `.venv/bin/python -c "import sqlite3; …"` from the engine worktree.
4. **pip trap:** `engine/.venv` is a copy-mirror venv — `bin/pip`'s shebang points at the ORIGINAL live venv. Always `<venv>/bin/python -m pip …`, never the pip script.

**REVISION LOGGING (mandatory):** every harness/battery/live run gets its own
imported `run_id` tagged with the commit sha it ran on (naming: `smoke-a`,
`happy-a`, `happy-b`, `battery-iter48` — letter = commit snapshot). Re-run the
bug-coverage check (`lf_quick.py bugs --run <name>`) after EVERY change: fixes
break other things, so the SAME queries must be re-verified after each revision.

**AUTOPSY REPORT (mandatory on any failure):** when a call/persona crashes,
loops, regresses vs the previous run, or fails a gate — write an autopsy to
`research/surgeon/iterNN-slug/` (per-call: transcript turns, rag/round rows from
the ledger, root cause with line numbers, whether it is NEW vs a known `findings`
row). Record the finding in the ledger `findings` table + `plans/PENDING_TASKS.md`
(as PT-NN) so branch/commit evidence survives the session.

## MODEL LAW (owner, 2026-09-22)

- **Agent LLM = `gpt-5.4` EVERYWHERE** — chat harness, voice/mic, every deploy, every test. No exceptions without an explicit plan + owner say-so.
- Runtime switch = `OPENAI_MODEL` in the engine `.env` (this OVERRIDES code defaults — pydantic Settings env wins). `agent/llm.json`'s `"model"` field is DISPLAY-ONLY dead metadata the engine never reads — do not trust it, do not "fix" the model by editing llm.json alone.
- `config.py:openai_model` default flip to `gpt-5.4` = next engine branch (LAW 0).
- Retell-HOSTED agents (live V7.9 etc.) are separate surfaces — model changes there need explicit owner instruction (LAW 6).
- Paid lesson (2026-09-22): `agent/llm.json` said `gpt-5.2` while the .env ran `gpt-5.4` — an agent misreported the test model from the dead field. Langfuse trace `observations[].model` is the ground truth for "what model ran".

## VOICE LAW — CARTESIA TTS (owner, 2026-09-23)

**THE proven voice config (owner ear verdict: "out of this world", better than ElevenLabs Sarah). Do not lose it again:**

```
TTS_PROVIDER=cartesia
CARTESIA_MODEL_ID=sonic-3.6-2026-08-27     # ← THE pin. Dated snapshot, NOT the rolling alias
CARTESIA_VOICE_ID=829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30   # Linda (public stock, "Conversational Guide", en-US feminine)
CARTESIA_SPEED=1.12
```

- **Paid lesson (2026-09-23):** the iter66 EL cutover env rebuild DROPPED `CARTESIA_MODEL_ID` from `engine/.env` → code default fell back to the rolling `sonic-3.6` alias → different model build, phenomenally different delivery on every :8024 call (journal: `model=sonic-3.6`). The dated pin `sonic-3.6-2026-08-27` was only still alive in the old :8021 process env (`/proc/3834955/environ`). ANY env-file edit that touches TTS keys MUST preserve `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27`.
- Per-state delivery profiles (`engine/diallux/media/delivery.py`: speed/emotion per state) are part of the sound — unchanged, do not "simplify" them.
- Verify what a lane actually runs: `journalctl --user -u diallux-<port>.service | grep "cartesia connected"` — must print `model=sonic-3.6-2026-08-27`.
- EL stays merged but dormant (`ELEVENLABS_*` env block kept for rollback; Sarah `uG1JFy6xppqckhHCs2KG`, turbo_v2_5).

## Naming traps (paid for in blood)

- `engine/` IS the old typo dir `dialux-langgraph-production-v5` (the live one). The
  correctly-spelled dir was the STALE twin — now `_cold_archive/diallux-twin-stale-correct-spelling.tar`.
- `retell/` here = Retell config lines, NOT the Retell company. `retell/sdr/current/` = V7.9.
- Old `Dialux_SDR/` path no longer exists — MIGRATION_MAP.md translates every legacy path.
