# 01 AUDIT — iter66 closeout (T7 live lane → ledger → merge/tag/push) + branch-collision proof

- Procedure: `tasks/surgeon/iter66-closeout-merge/`
- Date: 2026-09-22 (evening UTC)
- Trigger: owner — "execute this plan per the surgeon framework… make sure branches won't collide (main worry)… stop at master_plan creation HITL step", referring to the remaining work in `research/surgeon/iter66-elevenlabs-cutover/66_execution_report.md` (§BLOCKED/next + §Parallel-lane state).
- Sources read: `66_execution_report.md` · `plans/plan_v5_iter66_elevenlabs_cutover.md` (committed @ `3ac4ac6`, the governing plan) · `tasks/surgeon/eleven_labs_migration/{00_SESSION_HANDOFF,04_master_plan}.md` (superseded iter64-era dossier) · `plans/plan_v5_iter65_model_defaults.md` (untracked, PLAN ONLY) · `engine/AGENTS.md` + root `AGENTS.md` (LAW 0, MODEL LAW) · live git state (every claim below re-verified on the box today).

## A. Git landscape (verified live 2026-09-22 ~21:40 UTC)

| Ref | Commit | State |
|---|---|---|
| `main` (main checkout `/home/julio/projects/clean_diallux_SDR`) | `4658305` | Tip = Phase-0 docs commit (this dossier + the pending GIT_TREE.md refresh absorbed; tree clean except pre-existing untracked docs, §C1). **Local-only history: 48 ahead of the stale origin/main tracking ref, 208 ahead of the LIVE remote (next row) — linear ancestor chain, 0 behind either way.** |
| `origin/main` tracking ref (github.com/Cesars-dev/clean-diallux-sdr.git) | `7049dea` (STALE) | **LIVE remote verified 2026-09-22 via token `ls-remote` (token redacted): GitHub `refs/heads/main` = `dfc0926`** — a 2026-09-08-era commit ("NEXT_STEPS: c3e + iter32 imported from ORIGINAL…"), i.e. **208 commits behind local main and a strict ancestor (linear)**. The tracking ref (`7049dea`, 09-16 sync) does NOT match the live remote (remote main was reset/recreated after 09-16); the remote also currently LACKS `engine/iter52-industry-pin` and tag `engine/iter64` that stale tracking refs still show. URL-pattern pushes never update tracking refs; anonymous fetch fails (no cached creds). **Per owner 2026-09-22: this closeout is LOCAL-COMMIT work — remote state is context, not a gate (F6).** |
| `engine/iter66-elevenlabs-cutover` | `6dc1ed8` | **Exactly 1 commit** (`+554/−134`, 7 files) whose parent is `3ac4ac6` = main tip. `git merge-base main engine/iter66-elevenlabs-cutover` = `3ac4ac6` = main tip. |
| `engine/iter65-model-defaults` (owner lane, OFF-LIMITS) | `3ac4ac6` | **ZERO commits of its own** — pointer == main tip. Worktree `/tmp/opencode/wt-iter65` CLEAN (no uncommitted changes). Plan (`plans/plan_v5_iter65_model_defaults.md`, untracked) says "PLAN ONLY (not started — awaits approval)"; branch was re-pointed from `09bf87b` to main tip `3ac4ac6` (docs-only delta) per owner 2026-09-22. |
| `engine/chat-tests` | `fc2fa2f` | **0 ahead / 51 behind main** = fully merged stale pointer (archived as `engine/docs-archive/fc2fa2f-mvp-bookkeeping`). |
| `engine/mvp-finally` | `1f15e8b` | **0 ahead** = merged (merge `4559a33`, tag `mvp-finally`). |
| `engine/iter64-elevenlabs-cutover` | `2cb810f` | **0 ahead** = EMPTY stale pointer at iter63's head; superseded by iter66 per the `3ac4ac6` plan-doc commit. |
| Tags | — | `engine/iter64` @ `801fcdf` (ladder tag). `engine/iter66` does NOT exist yet. Convention: tag `engine/iterNN` at branch HEAD. |
| Worktrees | — | 30 registered; 3 prunable (`wt-iter33/34/35`). `wt-iter66` holds the iter66 branch (merging it INTO main is legal while checked out elsewhere; branch DELETION later requires worktree removal first). `wt-iter62` (:8021) and `wt-iter64` (:8022) serve live owner lanes — untouched. |

**Conclusion of §A: `engine/iter66-elevenlabs-cutover` is the ONLY branch in the repo with unmerged commits, and it is a direct descendant of main tip — the merge cannot textually collide with anything, by construction.**

## B. Collision analysis (the owner's main worry) — file-overlap matrix

### B1. iter66 → main (the actual merge): conflict IMPOSSIBLE

- Proof: merge-base(main, iter66) = main tip `3ac4ac6` → `git merge` is a pure fast-forward; `--no-ff` (doctrine) only adds a merge commit. No three-way content merge ever happens.
- Dirty-tree check: iter66's 7 files (`engine/diallux/config.py`, `engine/diallux/media/{elevenlabs_tts,prewarm,tts_factory}.py`, `engine/tests/{test_delivery,test_tts_providers,test_iter66_elevenlabs_cutover}.py`) — none is modified or untracked in the main checkout (main's only modification is `GIT_TREE.md`; untracked files are docs/plans/tasks, no `engine/` paths). Merge will NOT be blocked.
- Post-merge suite re-verify on the MAIN checkout is the real gate (expect **439 passed**, see §D1).

### B2. iter66 vs iter65 (the owner's NEXT lane): no textual conflict, semantic re-preflight required

iter65 has zero commits today (§A), so nothing can collide **now**. Forward analysis against iter65's approved-scope plan:

| iter66 touches (merged) | iter65 plans to touch | Overlap? |
|---|---|---|
| `engine/diallux/config.py` line **382** (`elevenlabs_latency_opt` → `elevenlabs_inactivity_timeout=180`) | `engine/diallux/config.py` line **272** + validator 274–282 (`rag_fire_mode: "eot"` → `"hybrid"`, PT-58) | **Same file, hunks ≥100 lines apart → git auto-merges cleanly.** |
| `media/elevenlabs_tts.py`, `media/tts_factory.py`, `media/prewarm.py`, 3 test files | `diallux/app.py` (boot-prewarm), `diallux/graph/builder.py` (sanitizer), prompts + `agent/llm.json`, `graph/tools.py`, `validator_endpoint/validate.py` (LIVE :8003), `media/session.py` + TTS layer (mic spans), root `scripts/` SDK | **No file overlap.** |

Semantic dependencies iter65 MUST re-preflight against post-merge main (goes in the hygiene menu, §F):
1. iter65 T4 (mic spans: `tts_first_byte`, prewarm-pool adoption in `session.py`) — iter66 restructured `prewarm.py` (provider-gated `_spawn_idle_tts`, EL keepalive companion, cartesia-only phrase cache) and added EL `ws=` adoption. iter65's instrumentation must be written against the NEW structure.
2. iter65 suite baseline: plan doc says **427**; post-iter66-merge it is **439** (427 + 12 net-new pins). Plan doc must be re-baselined at iter65 kickoff.
3. iter65 T1 boot-prewarm interacts with `CALL_PREWARM=true` + provider-gated prewarm (works for either provider post-iter66; verify at kickoff).

### B3. Merge ORDER (corrects the 66_execution_report §Parallel-lane proposal)

The report proposed "merge iter65 and iter66 with `--no-ff`". That was written when iter65 was believed to carry work (`@ 09bf87b`). TODAY iter65 is an empty pointer at main tip → there is **nothing to merge from iter65**; merging its pointer would be a no-op. Correct order:

1. **iter66 alone, first** (done work, suite green, live lane pending owner keys).
2. **iter65 later**, after its work is committed — re-preflighted per §B2.
3. `chat-tests`, `mvp-finally`, `iter64-elevenlabs-cutover`: already-in-main stale pointers — never merge (no-op), deletion is owner-say-so hygiene (§F).

### B4. Remote state — OUT OF SCOPE for this closeout (owner 2026-09-22: "we are talking about local commits"); context recorded for completeness

Live remote main = `dfc0926` = strict ancestor of local main (208 behind, linear, verified via token `ls-remote`) → **if** a push is ever ordered, it is a clean fast-forward — zero divergence risk. Pushing would publish the entire local-only history since 2026-09-08 (208+ commits incl. the `40b3b40` ladder merge — all already owner-approved content). Creds are not cached (anonymous fetch fails); push mechanics = `GITHUB_TOKEN` URL pattern + keyhound first. The iter65 plan doc's "pushed (`f5850e5..09bf87b`)" wording does not match the live remote — informational only; not this procedure's concern.

## C. T7 live-lane readiness (what EXISTS vs MISSING)

### C1. EXISTS (hermetic side complete)
- T1–T6 done @ `6dc1ed8`: suite **439 passed / 0 failed** (baseline 427 + 12 net-new pins; 6 old-protocol EL tests rewritten in place), extinction greps clean, untouched-lane proof empty (`session.py`, `cartesia_tts.py`, `delivery.py`, `sentence_gate.py` byte-identical to main).
- Worktree `/tmp/opencode/wt-iter66/engine` run-ready: `.venv` symlink → main venv, `.env` copy present (`TTS_PROVIDER=cartesia`).
- Main checkout untracked files (10 plan files, 5 old surgeon dossiers, `docs/CALL_FACTS.md`, `scripts/call_ledger.py`) do NOT intersect iter66's files — left alone (owner hygiene, §F).

### C2. MISSING (all owner-gated)
- `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` (Chloe) — verified ABSENT from `wt-iter66/engine/.env`, main `engine/.env`, and root `/home/julio/projects/.env`.
- `.env` flip in the WORKTREE only: `TTS_PROVIDER=elevenlabs`, keys, `CALL_PREWARM=true` (CALL_PREWARM currently absent from both .envs). Main `engine/.env` stays `cartesia` until owner flips post-merge (rollback = one env var).
- T7 go-ahead (owner ears on the live call).

### C3. Port + launch pattern (live scan this session)
- BUSY (never use): `8000-8003` (live infra, LAW), `8005, 8007, 8008, 8010, 8020, 8021` (wt-iter62 lane, owner law), `8022` (wt-iter64 mic lane, pid 884638, owner law), `8082, 8123, 8191, 8501, 8888, 8899`, plus system ports.
- **`8023` is free NOW** — re-verify with `ss -tln` immediately before bind (the plan's rule: free 127.0.0.1 port, never 8000–8003, never the live lanes 8020/8021/8022).
- Launch: **foreground** uvicorn per the governing plan — `set -a; . ./.env; set +a; .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8023`. (`engine/scripts/serve_voice.sh` is the detached launcher but is hardwired to `:8020`, which is BUSY — do not reuse it for T7; foreground lets the owner watch logs and Ctrl-C.)
- Routes (verified in `diallux/app.py`): `/health`, `/metrics`, `/mic` (browser mic page), `/mic/ws` (browser lane), `/media` (twilio).
- Access from the owner's Mac: **ssh tunnel** (preferred, zero public exposure) OR a Caddy route — if publicly exposed, the VOICE_TEST_TOKEN fail-closed gate is MANDATORY (public-endpoint-token-gate skill; 4401 pattern). Never expose naked.

### C4. T7 pass gates (from the governing plan, unchanged)
LV-1 turn-2+ audio, no end-of-turn truncation · LV-2 barge-in instant stop + clean next turn · LV-3 recv casing `contextId`/`is_final` in logs · LV-4 browser audio intelligible + digit readback · LV-5 idle >20s socket adoptable (keepalive wins over EL idle-kill).

## D. Ledger import path — TRAP FOUND (F1, the one real flaw)

| Copy | PT-59? | Evidence |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (root SDK) | **YES** | commit `a4802fa` 2026-09-22 06:36 "PT-59 DONE — ledger rag import stores kbs/pinned/lanes/zero_hit natively"; 4 `zero_hit` refs in file |
| `engine/scripts/live_sql.py` (main checkout AND `wt-iter66` copy — byte-identical) | **NO (pre-PT-59)** | last touched by `0d21763` (iter60); ZERO `zero_hit` refs; strips kbs/pinned/lanes/zero_hit on import |

- **The governing iter66 plan (T7 line) and `66_execution_report.md` line 37 BOTH prescribe `cd /tmp/opencode/wt-iter66/engine && .venv/bin/python scripts/live_sql.py import …` — that is the ENGINE copy = the TRAP.** Both texts predate the owner's PT-59 decision (recorded in the iter65 plan: "all ledger imports go through the MAIN SDK"; the engine-worktree port was deliberately dropped).
- Correct import (owner decision, adopt in master plan): run from the MAIN checkout with the root SDK:
  `cd /home/julio/projects/clean_diallux_SDR && set -a && . /tmp/opencode/wt-iter66/engine/.env && set +a && python3 scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run iter66-ela-smoke --commit 6dc1ed8 --db research/surgeon/iter48-rag-truth/ledger.db`
- Ledger: `research/surgeon/iter48-rag-truth/ledger.db` (call/findings ledger; gitignored). T7 report goes to `research/surgeon/iter66-elevenlabs-cutover/` (gitignored evidence). NO `sqlite3` CLI on this box — venv/python + sqlite3 module only.

## E. Post-merge ritual requirements (from AGENTS/DOCTRINE, all verified present)

- `scripts/git-tree.sh` exists (repo root); must run after the merge; GIT_TREE.md committed (docs, main).
- `engine/ITERATIONS.md` exists on main — append the iter66 ledger line (docs commit on main; format: the iter52→64c ladder line).
- Tag `engine/iter66` at `6dc1ed8` — tags only with owner-approved merges (this HITL approval).
- `scripts/keyhound` from repo root before ANY push — baseline: **286 false-positive hits = current clean baseline, no real secrets** (per iter65 plan compaction; `keyhound_clean.txt` in /tmp/opencode).
- Push mechanics (owner-gated, OUT of closeout scope): token URL from `/home/julio/projects/.env` `GITHUB_TOKEN`; never print; sed-redact; verify via `ls-remote` sha == local `git rev-parse main` (tracking refs don't move on URL pushes). Live remote facts in §B4.

## F. Findings register

| # | Finding | Severity | Disposition |
|---|---|---|---|
| F1 | T7 ledger-import command in plan + report uses the pre-PT-59 ENGINE `live_sql.py` (strips kbs/pinned/lanes/zero_hit) | **HIGH** | Master plan corrects to root SDK import (§D) |
| F2 | Report's merge proposal ("merge iter65 and iter66") rests on a stale premise — iter65 has ZERO commits; only iter66 is mergeable | HIGH | Master plan: iter66 alone, iter65 later (§B3) |
| F3 | Merge conflict risk main←iter66 = ZERO (descendant, FF-only) | INFO | Proof recorded (§B1) |
| F4 | iter65 future lane: config.py hunk regions ≥100 lines apart → auto-merge clean; semantic re-preflight required (prewarm structure, ws= adoption, suite 427→439) | MEDIUM | Hygiene menu item (§B2) |
| F5 | Main checkout has uncommitted GIT_TREE.md refresh (accurate) + ~17 untracked docs | LOW | GIT_TREE.md absorbed into the Phase-0 docs commit; untracked docs left for owner |
| F6 | Remote/tracking-ref mismatch: tracking `origin/main` @ `7049dea` vs LIVE remote main @ `dfc0926` (2026-09-08 era, 208 behind local, strict ancestor — verified via token ls-remote); anonymous fetch fails; iter65 plan's "pushed" wording doesn't match the live remote | **INFO (reframed per owner 2026-09-22: local-commit closeout — push topic out of scope)** | Phase-D context only; no blocker; push solely on explicit owner order, keyhound first |
| F7 | EL keys absent everywhere; TTS_PROVIDER=cartesia in both .envs; CALL_PREWARM unset | INFO (expected) | Owner supplies per T7 (§C2) |
| F8 | :8020 (serve_voice.sh's port) is BUSY; T7 must use a verified-free port (8023 free now) | LOW | Launch command pinned (§C3) |
| F9 | Stale branch pointers (chat-tests, mvp-finally, iter64-ela) + 3 prunable worktrees | LOW | Owner-say-so hygiene menu |
| F10 | Main `engine/.env` provider flip (post-merge) is owner-gated; rollback = one env var | INFO | Hygiene menu |

Zero open questions remain that an agent can resolve; everything else is owner-gated by design.
