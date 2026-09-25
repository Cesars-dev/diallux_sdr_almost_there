# 04 MASTER PLAN — iter66 closeout: T7 live lane → ledger → merge `engine/iter66` (HITL: AWAITING OWNER APPROVAL)

- Procedure: `tasks/surgeon/iter66-closeout-merge/` (audit 01 · action plan 02 · cross-reference 03 — all preflighted against the live box 2026-09-22)
- Governing plan: `plans/plan_v5_iter66_elevenlabs_cutover.md` (T1–T6 DONE @ `6dc1ed8`, suite 439 green)
- Status: **PLAN AIRTIGHT — EXECUTION STOPPED AT THE HITL GATE. Nothing below runs without Julio's explicit say-so (LAW 0).**

## 1. The collision verdict (owner's main worry) — SOLVED, zero conflict

| Question | Answer (proof) |
|---|---|
| Can merging iter66 conflict with main? | **No — impossible.** `merge-base(main, iter66)` = main tip `3ac4ac6`; the branch is ONE commit (`6dc1ed8`) on top of main tip → fast-forward-only. Re-proved at execution time in C1. |
| Can merging iter66 collide with iter65? | **No — iter65 has ZERO commits** (pointer == main tip `3ac4ac6`, worktree clean, plan-only). There is nothing to merge from iter65 today. |
| Will iter65 collide LATER? | Only shared file = `engine/diallux/config.py`: iter66 hunk @ line 382, iter65 planned hunks @ 272/274-282 → ≥100 lines apart, git auto-merges. Semantic re-preflight (prewarm structure, EL `ws=` adoption, suite baseline 427→439) = first task of iter65 kickoff (E2). |
| chat-tests / mvp-finally / iter64-ela? | All fully merged stale pointers (0 commits ahead) — never merge (no-op); deletion = owner menu E3. |
| Remote? | **Out of scope (owner: local commits).** LIVE remote main = `dfc0926` = strict ancestor of local main (208 behind, linear — verified via token ls-remote) → any future push is a clean fast-forward. Tracking refs are stale (don't match the live remote); URL pushes never update them. Push = optional Phase D, owner's word only. |

## 2. Owner gates (every one explicit)

| Gate | Owner action |
|---|---|
| G1 — T7 keys | Put `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` (Chloe) into `/tmp/opencode/wt-iter66/engine/.env` (worktree ONLY) + set `TTS_PROVIDER=elevenlabs`, `CALL_PREWARM=true` |
| G2 — T7 live run | Owner ears on the browser-mic call (LV-1..LV-5) |
| G3 — MERGE say-so | Approve this master plan + say "merge" (unlocks Phase C) |
| G4 — PUSH say-so (OPTIONAL — out of closeout scope) | Separate word "push" (unlocks Phase D; the closeout itself completes locally at Phase C) |
| G5 — hygiene menu | E1–E5 individually (provider flip on main, iter65 re-preflight, stale branch deletes, worktree prune, untracked docs) |

## 3. Execution sequence (condensed; full commands in 02)

**Phase 0 — docs (done with this dossier, LAW 0):** commit `tasks/surgeon/iter66-closeout-merge/` + pending `GIT_TREE.md` refresh to main. No push.

**Phase A — T7 live lane (after G1):**
```bash
cd /tmp/opencode/wt-iter66/engine
ss -tln | grep '127.0.0.1:8023 '   # must be EMPTY (8023 free at audit; never 8000-8003/8020/8021/8022)
set -a; . ./.env; set +a
.venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8023
```
Mac access: `ssh -L 8023:127.0.0.1:8023 julio@46.62.233.228` → `http://127.0.0.1:8023/mic` (or Caddy route — then VOICE_TEST_TOKEN fail-closed gate MANDATORY).
Owner call: ≥3 turns + mid-sentence barge-in + >20s idle pause. PASS = LV-1 turn-2+ audio/no truncation · LV-2 barge-in clean · LV-3 `contextId`/`is_final` in logs · LV-4 intelligible + digits · LV-5 post-idle audio.
FAIL → autopsy to `research/surgeon/iter66-elevenlabs-cutover/`, finding in ledger `findings` + PT-NN, fix commits on the SAME branch, suite re-green (439), re-run. No merge while red.

**Phase B — ledger import via ROOT SDK (fixes F1; the engine-copy command in the old plan/report is a known trap):**
```bash
cd /home/julio/projects/clean_dialux_SDR
set -a && . /tmp/opencode/wt-iter66/engine/.env && set +a
python3 scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run iter66-ela-smoke --commit 6dc1ed8 --db research/surgeon/iter48-rag-truth/ledger.db
python3 scripts/latency_pull.py --run iter66-ela-smoke
```
Verify: `calls` row(s) for `iter66-ela-smoke`; rag rows carry kbs/pinned/lanes/zero_hit (venv-python + sqlite3 module; NO sqlite3 CLI). Report → `research/surgeon/iter66-elevenlabs-cutover/67_t7_live_report.md`.

**Phase C — merge + tag (after G3):**
```bash
cd /home/julio/projects/clean_diallux_SDR
# C1 proof pack: merge-base(main, iter66) == main tip; both worktrees clean; branch head = 6dc1ed8 (or T7-fix head)
git merge --no-ff engine/iter66-elevenlabs-cutover -m "Merge engine/iter66-elevenlabs-cutover (ElevenLabs multi-stream-input TTS cutover: adapter rewrite, factory transport fix, provider-gated prewarm, 12 protocol pins; suite 439 green; T7 live LV-1..LV-5 PASS) — owner say-so <date>"
git tag engine/iter66 engine/iter66-elevenlabs-cutover
cd engine && .venv/bin/python -m pytest tests -q        # GATE: 439 passed, 0 failed on MAIN checkout
cd .. && scripts/git-tree.sh
# append ITERATIONS.md line (draft below) → git add GIT_TREE.md engine/ITERATIONS.md → docs commit
```

**Phase D — push (OPTIONAL, after G4 — out of closeout scope; the closeout completes at Phase C):** live remote main `dfc0926` is a strict ancestor (208 behind, linear) → clean fast-forward. `./scripts/keyhound` (expect 286-FP clean baseline) → push `main` + branch `engine/iter66-elevenlabs-cutover` + `refs/tags/engine/iter66` via the `GITHUB_TOKEN` URL pattern (never print). Verify via redacted `ls-remote` sha == `git rev-parse main` (URL pushes don't update tracking refs).

**Phase E — hygiene menu (after G5, each item individually):** E1 flip main `engine/.env` to EL (rollback = one var) · E2 iter65 re-preflight (suite 427→439 re-baseline, prewarm/session structure re-walk) · E3 `git branch -d engine/iter64-elevenlabs-cutover engine/chat-tests engine/mvp-finally` (all 0-ahead, safe) · E4 `git worktree prune` + remove `wt-iter66` after tag (+push if ordered) · E5 commit-or-leave the ~17 untracked docs.

## 4. ITERATIONS.md line draft (Phase C4)

```
- **iter66 (`engine/iter66-elevenlabs-cutover` @ `6dc1ed8`, MERGED to main `<merge-sha>` — owner say-so <date>, tag `engine/iter66`) — ElevenLabs multi-stream-input TTS cutover.** Adapter rewrite (native contexts, flush-on-sentence, close_context barge-in, transport-aware output_format pcm_16000/ulaw_8000, ws= adoption, keepalive `{"text":" "}`, close_socket), factory transport fix (browser lane format), provider-gated prewarm (EL keepalive companion, cartesia-only phrase cache), config `elevenlabs_latency_opt`→`elevenlabs_inactivity_timeout=180`, 12-pin hermetic file. Suite 427→439. T7 live lane LV-1..LV-5 PASS (`iter66-ela-smoke`, imported via root SDK). Provider flip on main .env = owner-gated (rollback = one env var). Cartesia lane byte-identical. Evidence: research/surgeon/iter66-elevenlabs-cutover/.**
```

## 5. Rollback

- Before C2: nothing happened.
- C2→D: `git reset --hard 3ac4ac6` (local only, legal) + `git tag -d engine/iter66`.
- After D: no reset/force — revert commit only, owner decision (LAW 0).
- T7 red: fix-on-branch loop, never merge red.

## 6. Flaws / open items

- All flaws found during audit + cross-reference are RESOLVED in this plan (F1 ledger-trap → Phase B; F2 merge-order → Phase C; C-1..C-8 source contradictions → resolved with newest owner decision winning; register in 01 §F / 03 §C).
- Open items: **only the owner gates G1–G5.** Zero agent-resolvable items remain.

---

## ⏸ HITL STOP — SURGEON FRAMEWORK STEP 5 NOT ENTERED

Per the framework and LAW 0: **user reviews and approves first.** Awaiting Julio:
1. Approve this master plan (or amend).
2. G1: drop the ElevenLabs keys + provider flip into `wt-iter66/engine/.env` → T7 runs.
3. G3 "merge", G4 "push", G5 hygiene — each in its own word, in that order, after the gates before them pass.
