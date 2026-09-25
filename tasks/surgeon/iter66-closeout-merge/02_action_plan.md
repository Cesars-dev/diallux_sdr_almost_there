# 02 ACTION PLAN — iter66 closeout: T7 live lane → ledger → merge/tag → docs → push (all owner-gated after Phase 0)

Built on `01_audit.md` (every command below is preflighted against the live box). Governing plan: `plans/plan_v5_iter66_elevenlabs_cutover.md` (T7 definition). Nothing in Phases A–E executes before the owner approves `04_master_plan.md` (HITL stop).

## Phase 0 — docs to main (LAW 0: docs go straight to main; executes with this dossier)

```bash
cd /home/julio/projects/clean_diallux_SDR
# commits: this dossier (01-04) + the pending GIT_TREE.md refresh (accurate 21:23 snapshot, unblocks a clean merge)
git add tasks/surgeon/iter66-closeout-merge GIT_TREE.md
git commit -m "docs: surgeon iter66-closeout-merge dossier (T7+merge closeout plan, pre-HITL) + GIT_TREE refresh"
```
- NO push (standing owner directive "local only"; push is Phase D, owner-gated).
- Verification: `git status` → clean except the pre-existing untracked docs (left alone, F5).

## Phase A — T7 live verification lane (OWNER: keys + ears; agent: launch + watch)

**A0. Owner supplies (into `/tmp/opencode/wt-iter66/engine/.env` ONLY — main `.env` stays `cartesia`, F10):**
```
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=<owner>
ELEVENLABS_VOICE_ID=<owner, Chloe>
CALL_PREWARM=true
```
Owner passes values via HITL/DM — never into chat logs or git.

**A1. Launch (foreground, free port, never 8000-8003 / 8020 / 8021 / 8022):**
```bash
cd /tmp/opencode/wt-iter66/engine
ss -tln | grep '127.0.0.1:8023 ' && echo "BUSY - pick another free port"   # must be empty; 8023 verified free at audit time (F8)
set -a; . ./.env; set +a
.venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8023
```
- Access from the Mac: ssh tunnel `ssh -L 8023:127.0.0.1:8023 julio@46.62.233.228` → `http://127.0.0.1:8023/mic`. If a public Caddy route is preferred instead, the VOICE_TEST_TOKEN fail-closed gate is MANDATORY before exposure (public-endpoint-token-gate skill; 4401 pattern). Never naked.
- Watch the startup log line: with `CALL_PREWARM=true` expect the EL prewarm branch (`diallux.prewarm` — provider-gated, no Cartesia sockets).

**A2. Owner call (browser mic, ≥3 turns + one mid-sentence barge-in + one >20s idle pause). Pass gates:**
- LV-1 turn-2+ audio & no end-of-turn truncation
- LV-2 barge-in instant stop + clean next turn
- LV-3 recv casing `contextId`/`is_final` present in server logs (NOT `isFinal`)
- LV-4 browser audio intelligible + digit readback correct
- LV-5 after >20s idle, next turn still has audio (keepalive adopted socket)

**A3. On ANY failure:** stop, kill server (Ctrl-C), write autopsy `research/surgeon/iter66-elevenlabs-cutover/67_t7_autopsy_<symptom>.md` (transcript turns, root cause w/ line numbers, NEW vs known `findings` row), record finding in ledger `findings` + `plans/PENDING_TASKS.md` (PT-NN). Fix rides the SAME branch as a new commit (`iter66: T7 fix — …`), suite re-green (439), T7 re-run. No merge until LV-1..LV-5 all PASS.

## Phase B — ledger import (ROOT SDK — fixes F1) + T7 report

```bash
cd /home/julio/projects/clean_diallux_SDR
set -a && . /tmp/opencode/wt-iter66/engine/.env && set +a
date +%H:%M   # note the window
python3 scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run iter66-ela-smoke --commit 6dc1ed8 --db research/surgeon/iter48-rag-truth/ledger.db
python3 scripts/latency_pull.py --run iter66-ela-smoke
```
- MUST be the ROOT SDK (`/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py`, PT-59 `a4802fa`) — the engine-worktree copy is pre-PT-59 and strips `kbs/pinned/lanes/zero_hit` (audit §D).
- Verify by SQL (no sqlite3 CLI on this box):
  `.venv`-python one-liner → `SELECT run_id, COUNT(*) FROM calls WHERE run_id='iter66-ela-smoke'` ≥1 row; `rag` rows carry `kbs`/`pinned`/`lanes`/`zero_hit` populated.
- Write `research/surgeon/iter66-elevenlabs-cutover/67_t7_live_report.md`: LV-1..5 verdicts, port, window, micbridge-* Langfuse trace id, TTFB observations, ledger row counts.
- Report is evidence (research/ is gitignored) — no commit needed.

## Phase C — merge to main + tag (OWNER SAY-SO = the approval of this master plan + explicit "merge" word)

**C1. Pre-merge proof pack (re-run, must all hold):**
```bash
cd /home/julio/projects/clean_diallux_SDR
git rev-parse main engine/iter66-elevenlabs-cutover         # main == 3ac4ac6 lineage, branch head == 6dc1ed8 (+ any T7-fix commits)
git merge-base main engine/iter66-elevenlabs-cutover        # == main tip (FF-only, zero conflict — audit F3)
git -C /tmp/opencode/wt-iter66 status --short               # clean (or only .env, gitignored)
git status --short                                          # main clean (Phase 0 absorbed GIT_TREE.md)
```
If T7 produced fix commits (A3), branch head > `6dc1ed8` — tag C3 tags the FINAL head; all shas in the report update accordingly.

**C2. Merge (--no-ff, ladder-commit style):**
```bash
git merge --no-ff engine/iter66-elevenlabs-cutover -m "Merge engine/iter66-elevenlabs-cutover (ElevenLabs multi-stream-input TTS cutover: adapter rewrite, factory transport fix, provider-gated prewarm, 12 protocol pins; suite 439 green; T7 live LV-1..LV-5 PASS) — owner say-so <date>"
```

**C3. Tag + post-merge suite on the MAIN checkout (the real gate):**
```bash
git tag engine/iter66 engine/iter66-elevenlabs-cutover      # tag at branch head
cd engine && .venv/bin/python -m pytest tests -q             # expect 439 passed, 0 failed
```

**C4. Rituals (docs commit on main):**
```bash
cd /home/julio/projects/clean_diallux_SDR
scripts/git-tree.sh
# append iter66 line to engine/ITERATIONS.md (draft in 04_master_plan §ITERATIONS)
git add GIT_TREE.md engine/ITERATIONS.md
git commit -m "docs: ITERATIONS — iter66 merged to main (<merge-sha>, tag engine/iter66) + GIT_TREE refreshed"
```

## Phase D — push (OPTIONAL, OWNER DECISION ONLY — out of closeout scope; the closeout completes LOCALLY at Phase C)

Facts (audit §B4): LIVE remote main = `dfc0926` = strict ancestor of local main (208 behind, linear) → any push is a clean fast-forward, zero divergence. Pushing publishes the full local-only history since 2026-09-08 (208+ commits incl. `40b3b40` — all owner-approved content).

```bash
cd /home/julio/projects/clean_diallux_SDR
./scripts/keyhound                 # expect the 286-FP clean baseline, zero real secrets
# token URL pattern (never print the token; sed-redact any URL echoed to logs):
git push https://x-access-token:${GITHUB_TOKEN}@github.com/Cesars-dev/clean-dialux-sdr.git main
git push https://x-access-token:${GITHUB_TOKEN}@github.com/Cesars-dev/clean-dialux-sdr.git engine/iter66-elevenlabs-cutover   # branch backup
git push https://x-access-token:${GITHUB_TOKEN}@github.com/Cesars-dev/clean-dialux-sdr.git refs/tags/engine/iter66
```
- URL-pushes do NOT update `origin/*` tracking refs — verify with a redacted `ls-remote` (`refs/heads/main` sha == local `git rev-parse main`), never by `git status`.

## Phase E — post-merge hygiene menu (each item needs its own owner say-so; NOTHING is auto-done)

| # | Item | Command / action |
|---|---|---|
| E1 | Flip MAIN `engine/.env` to EL (`TTS_PROVIDER=elevenlabs` + keys) — production-ish lane follows owner verdict; rollback = one env var | owner edits `/home/julio/projects/clean_diallux_SDR/engine/.env` |
| E2 | iter65 re-preflight: re-baseline suite 427→439 in `plans/plan_v5_iter65_model_defaults.md`; re-walk prewarm/session/ws= structure (audit F4) | at iter65 kickoff |
| E3 | Delete stale branch pointers (`engine/iter64-elevenlabs-cutover`, `engine/chat-tests`, `engine/mvp-finally` — all 0-ahead, no-op deletes) | `git branch -d <name>` each (safe: fully merged) |
| E4 | Worktree prune: `git worktree prune` (wt-iter33/34/35 prunable); remove `wt-iter66` AFTER tag+push (`git worktree remove /tmp/opencode/wt-iter66` then `git branch -d engine/iter66-elevenlabs-cutover`) | owner say-so |
| E5 | Commit-or-leave the ~17 untracked docs on main (10 plan files, 5 surgeon dossiers, `docs/CALL_FACTS.md`, `scripts/call_ledger.py` — the ledger script's home branch is `engine/iter47-call-ledger`, commit-to-main = owner call per AGENTS) | owner say-so |

## Rollback points

- Anywhere before C2: nothing happened; branch and main untouched.
- After C2, before D: `git reset --hard 3ac4ac6` on main (pre-push local only; legal, no history rewrite published). Tag delete: `git tag -d engine/iter66`.
- After D (pushed): NO reset/force — a revert commit would be required, owner decision only (LAW 0 "always say-so" list).
- T7 failures: A3 loop (fix on branch, never merge red).

## Verification matrix (gate per step)

| Step | Gate |
|---|---|
| A2 | LV-1..LV-5 all PASS (owner ears) |
| B | ledger row count ≥1 for `iter66-ela-smoke`, rag columns populated (root SDK) |
| C1 | proof pack: merge-base == main tip, both trees clean |
| C3 | main-checkout suite 439 passed / 0 failed |
| C4 | GIT_TREE.md regenerated + ITERATIONS line committed |
| D | keyhound clean → push OK → redacted `ls-remote` main sha == local `git rev-parse main` (tracking refs don't move on URL pushes) |
