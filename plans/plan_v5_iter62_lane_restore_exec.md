# PLAN — iter62-exec: execute the surgeon master plan (lane restore) in a fresh session

## Meta
- Date: 2026-09-21
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — execute, in order, the airtight surgeon master plan at `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/04_master_plan.md` (11 code edits, 2 existing-test rewrites, 9 new pins, suite 422, restart test server :8021, owner mic gate, ledger flips, fix report, branch commit, owner ASK). THIS plan carries zero code content — every code change, exact diff, and test body lives in the master plan, which is the sole engineering source of truth. This plan provides the session context, references, environment facts, and gates a fresh agent needs to carry the work without prior conversation.
- Status: **PLAN ONLY (not started — awaits approval)**

## Compaction Context (session 2026-09-21 — pin, do not re-derive)

- **What happened this session:** the owner asked to run `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter62_lane_restore.md` through the Surgeon Framework (`/home/julio/projects/SURGEON_FRAMEWORK.md`: audit → action plan → cross-reference → preflight → execute-only-when-airtight+approved). The full procedure was completed and is on disk at `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/` — active file `04_master_plan.md`; sources `01_audit.md`, `02_action_plan.md`, `03_cross_reference.md` archived under `archive/` in the same folder.
- **Preflight verdict:** the master plan is AIRTIGHT (zero open issues). It corrected three real flaws found in the original plan: (1) the `record_reach_details` fix is a LOCAL interception in the tool executor — the tool is a REMOTE webhook (`type: "custom"` in `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json`), there is no local handler to edit, and the live validator endpoint is another repo's read-only infra; (2) deleting the hybrid lane-B respawn must KEEP the msg-mismatch rejection (else a stale done-task gets consumed as fresh — worse than the bug being fixed); (3) the original plan's "zero existing test files edited" claim was false — exactly TWO existing pins assert the respawn behavior being deleted and must be rewritten to the new fail-clean semantics (count-neutral; suite math 413 + 9 = 422 still holds). Full reasoning in `archive/01_audit.md` (findings AUD-01..AUD-12) and `archive/03_cross_reference.md` (resolutions NEW-1..NEW-6).
- **Owner decision state:** the owner was offered the execution gate and chose **"Hold — review the master plan"**. NOTHING has been executed: no worktree, no edits, no pins, no restart, no commit. GATE 0 of this plan = the owner's explicit approval of `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/04_master_plan.md` (owner may also request changes first — then update the master plan and re-gate before any code).
- **Audit source-of-truth discipline (mandatory):** all code facts were verified against worktree `/tmp/opencode/wt-iter61` @ `6c986e8` = tip of `engine/iter61-prewarm-staleness` (worktree verified CLEAN; the `:8021` test server, pid 1983323, runs from it). The main checkout `/home/julio/projects/clean_diallux_SDR` sits on `main` @ `069feed` which has DIVERGED from the iter61 branch (merge-base `4559a33`; engine tree differs by 13 files / ~1.7k lines) — a fresh agent MUST NOT read engine code from the main checkout for this work and MUST NOT audit from anything but the base commit `6c986e8` (or the new wt-iter62 once cut).
- **Project state:** iter61 is LIVE-VERIFIED on the mic (call `cc22e0a0185e`, 2026-09-21 05:48-06:04 UTC, 54 turns: zero UNPARSABLE frames, zero idle-timeout deaths) — owner called it "80% there"; the remaining gap was retrieval blindness (ledger FIND-30), which iter62 fixes. `:8020` = wt-iter58 production test surface — NEVER touched. Ports 8000-8003 NEVER bound. No merges without owner say-so (LAW 0).
- **The four proven retrieval failure classes (67 rag spans, deep dive `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter61-prewarm-staleness/03_kb_retrieval_deep_dive.md` §7):** (1) lane B ran EMPTY on 25/67 rounds — the consume-side utterance was re-extracted from graph history and diverged from the fired transcript under eager/barge-in, triggering an empty respawn that passed the 12-char gate as a "healthy" zero-hit round; (2) lane A = recipe-NAME embedding queries matching nothing; (3) the 60 ms await cap vs 30-190 ms retrieval (owner: do NOT touch the cap or the 0.24 filter); (4) `degraded=False` hid 38/67 zero-chunk rounds. iter62 kills class 1 at the root (session transcript = single source of truth), makes zero-chunk honest (degraded + zero_hit), fails clean on await miss (no stale injection — owner explicitly rejected landed-late injection), keeps lane A's iter49 shape (verify-only, confirmed correct), adds the solar pin alias, and scripts the empty-callback recovery.
- **Test-impact certainty (from the audit, do not re-derive):** exactly TWO existing tests break by design and get rewritten in place (names kept, count-neutral): the iter60 AUD-4 respawn pin in `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter60_audit_fixes.py` and the laneB-only respawn pin in `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter59_rag_freshness.py`. All existing `record_reach_details(true)` call sites seed a non-empty callback number, so the need_digits interception breaks nothing. The solar alias creates no ambiguity (the resolver's hit-set is keyed by TAG, and both roofing and solar aliases map to the same vertical). Every other existing pin was traced and passes unchanged.
- **Chat-surface expectation (owner-accepted, do not mistake for a regression):** on chat (`--rag` harness runs) NO lane tasks fire (fires live in the session layer; chat has no EOT events) → rag spans show `degraded=true, zero_hit=true` — that IS the fail-clean semantics working. The chat firing decision is DEFERRED by the owner ("no code changes to make this both ways"). `tests/llm2llm/harness.py` is UNTOUCHED in this iteration.
- **Mic regression gate (owner must re-test before any merge talk):** same URL/token as iter61 (`https://flores.diallux-ai.site/voice60/mic?k=$VOICE_TEST_TOKEN`); owner raises a pricing objection somewhere in the call. Gate: e2e p50 within ±25% of 1188 ms, eager_final_match 100%, zero STT/TTS errors, greeting full, TTL respawns normal, zero-hit span count STRICTLY below the iter61 call's 38/67, objection-turn span query non-empty, pinned non-empty once industry is known.
- **Ops traps (paid for in blood, from the iter61 session):** the setsid launch forks — after starting uvicorn on :8021, re-resolve the REAL pid via `ss -ltnp` + cwd and write THAT into `/tmp/opencode/voice_8021.pid` (a stale `$!` wrapper pid burned iter61). NO sqlite3 CLI on this box — use `<venv>/bin/python -c "import sqlite3…"`. pip trap: always `<venv>/bin/python -m pip`. The kill/restart of :8021 goes ONLY through the verified pid — never `systemctl`, never `pkill uvicorn`.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| The surgeon master plan `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/04_master_plan.md` is the SOLE engineering source of truth; this exec plan adds context/references only, no code | owner instruction: "do not add ANY code references, that's already planned on the master plan" |
| GATE 0: no code until the owner approves the master plan (owner currently HOLDING to review it) | surgeon framework step 5 + owner's explicit "Hold — review the master plan" answer |
| Utterance single source of truth: ingest keeps the turn transcript; state_node consumes it; history re-extraction AND the hybrid msg-mismatch respawn are deleted — but the mismatch REJECTION stays (missing/cancelled/mismatched laneB = clean fail, no respawn) | kills the 25/67 empty-query rounds at the root; owner: "fix the nonsense, make the two-lane design work"; stale-task rejection prevents a worse AUD-4 regression |
| Fail clean: await miss ⇒ empty delta + degraded=True; NO stale fallback in the hybrid path | owner REJECTED landed-late injection: "the model can be fed a chunk that makes no sense whatsoever" |
| Honest degraded: merged==0 ⇒ degraded=True everywhere (hybrid landed path, same-turn stash reuse, eot/speech-window task path) + `zero_hit` in both rag span emitters | owner: "just a boolean so we understand nothing was retrieved"; 38/67 blind rounds hid behind False |
| Lane A unchanged (iter49 shape, session verifies nothing to edit); `rag_filter_score=0.24`, `rag_min_query_chars=12`, `rag_live_await_ms=60` UNTOUCHED | owner calibrated; audit confirmed lane A shape is already correct |
| Solar alias one-liner into the pin-alias table | vertical exists (3 chunks in `kb_chunks_v2`); pin missed only for lack of the alias; resolver hit-set keyed by tag → no ambiguity |
| `record_reach_details` need_digits LOCAL interception (YES ∧ empty callback_number), webhook still called, phone_confirmed patch preserved; non-empty number or NO answer = byte-identical | owner: the YES branch is a guaranteed dead end on mic; the matching prompt string edit is OWNER-HITL (agent proposes in fix report, owner applies) |
| Exactly 2 existing tests rewritten in place (names kept); suite = 413 + 9 = 422 passed | the deleted respawn machinery is what those pins assert; documented deviation, count-neutral |
| Harness UNTOUCHED; lane logic proven on chat via a no-LLM pin driving spawn/consume directly | owner: "lets not mess the py… just fix what we set out to do"; chat `--rag` expected fail-clean spans documented, not a regression |
| Ops: only :8021 restarts (from the new worktree, env `RAG_FIRE_MODE=hybrid CALL_PREWARM=true`); :8020/8000-8003 never; commit only on `engine/iter62-lane-restore`; merge = owner STOP POINT | LAW 0 + AGENTS.md + plan Deploy Rules |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| GATE 0 — owner approval of the master plan (owner is reviewing; chose Hold) | ask the owner; on approval proceed T1; on change requests, update the master plan first and re-gate |
| Mic re-test call (owner speaks on the mic page) | Telegram the owner the SAME URL after the :8021 restart (T8); the session id comes from the call |
| New call's re-test window `HH:MM-HH:MM` for the ledger import | read off the mic call timestamps after T8 |

## Environment & Dependencies
- Project root: `/home/julio/projects/clean_diallux_SDR` (docs/plans/research live here on `main`; engine code lives on `engine/iterNN-*` branches via worktrees).
- Base commit: `6c986e8` (tip of `engine/iter61-prewarm-staleness`; clean worktree `/tmp/opencode/wt-iter61`). New worktree: `/tmp/opencode/wt-iter62`, branch `engine/iter62-lane-restore` cut from `6c986e8`.
- Venv: symlink `/home/julio/projects/clean_diallux_SDR/engine/.venv` into the new worktree (copy-mirror venv — pip via `<venv>/bin/python -m pip` only). websockets 16.1.1, fastembed 0.8.0 (arctic-m 768-d), pytest present. NO new dependencies.
- Suite command: `cd /tmp/opencode/wt-iter62/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → baseline gate **413 passed** BEFORE any edit; final gate **422 passed, 0 failed** AFTER edits+pins.
- `.env`: copy from `/tmp/opencode/wt-iter61/engine/.env` (has `VOICE_TEST_TOKEN`, `LANGFUSE_*`, `DATABASE_URL` → localhost:5434/diallux, `RAG_TABLE_NAME=kb_chunks_v2`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.7`). If that worktree is gone: copy from `/home/julio/projects/clean_diallux_SDR/engine/.env` and append `RAG_TABLE_NAME=kb_chunks_v2` if absent.
- Test server :8021: pid file `/tmp/opencode/voice_8021.pid` (currently REAL pid 1983323 from wt-iter61 — verify with `ss -ltnp | grep 8021` before killing). Log: `/tmp/opencode/voice_server_8021.log`. Caddy route `/voice60/* → 127.0.0.1:8021` live. Health: `curl -sf http://127.0.0.1:8021/health`; preflight script: `scripts/voice_preflight.py --url http://127.0.0.1:8021`.
- Mic page (owner): `https://flores.diallux-ai.site/voice60/mic?k=$VOICE_TEST_TOKEN`.
- Evidence pullers: `scripts/mic_events.py --sid <sid> --langfuse`; Langfuse UI `http://localhost:3001`; `scripts/lf.py`.
- Call ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (import via `scripts/live_sql.py import --window "HH:MM-HH:MM" --run mic-iter62 --branch engine/iter62-lane-restore --commit <sha>` from the worktree with `.env` sourced).
- Telegram HITL: `cd /tmp/opencode/wt-iter62/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<message>"`.
- Surgeon procedure folder: `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/` (master plan + archive). Fix report target: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter62-lane-restore/01_fix_report.md`.
- Prior-iteration references (read-only): iter61 SOP report `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter61-prewarm-staleness/02_mic_call_sop_report.md`; deep dive `…/03_kb_retrieval_deep_dive.md` (§7 = the failure evidence the fix report must cite).

## Architecture (one block diagram)
```
iter62 EXEC (branch engine/iter62-lane-restore @ base 6c986e8)
  GATE 0 owner approves 04_master_plan.md   ← CURRENT BLOCKER
  T1 worktree wt-iter62 + .env + baseline suite 413
  T2 apply master-plan edits E1-E11 (builder.py x10, tools.py x1) — code lives ONLY in the master plan
  T3 rewrite 2 existing pins (master plan §2 R1/R2) + write 9-pin file (master plan §3)
  T4 suite 422 passed, 0 failed (gate; fix forward on surprises, never weaken a pin)
  T5 restart :8021 from wt-iter62 (verified-pid discipline) + health/preflight
  T6 owner mic re-test (same URL) → MIC GATE (latency byte-stable + retrieval un-blinded)
  T7 ledger: import run, FIND-30 flip, FIND-29 fix-note
  T8 fix report + branch commit + Telegram ASK
  STOP — merge/deploy = owner decision (LAW 0)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/04_master_plan.md` | THE engineering spec: 11 exact edits (§1 E1-E11), 2 test rewrites (§2), 9 pin specs (§3), task order + full commands + gates (§4), accepted consequences (§5) | read-only reference |
| `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/archive/01_audit.md` | audit evidence + findings AUD-01..12 (why each fix exists) | read-only reference |
| `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/archive/03_cross_reference.md` | flaw resolutions NEW-1..6 (why the master plan deviates from the original plan) | read-only reference |
| `/tmp/opencode/wt-iter62/engine/diallux/graph/builder.py` | E1-E10 (utterance single-source, honest degraded + zero_hit, fail-clean, solar alias) | E |
| `/tmp/opencode/wt-iter62/engine/diallux/graph/tools.py` | E11 (record_reach_details need_digits interception) | E |
| `/tmp/opencode/wt-iter62/engine/tests/test_iter60_audit_fixes.py` | R1: stale-laneB pin rewritten to fail-clean semantics | E |
| `/tmp/opencode/wt-iter62/engine/tests/test_iter59_rag_freshness.py` | R2: laneB-only pin rewritten to fail-clean semantics | E |
| `/tmp/opencode/wt-iter62/engine/tests/test_iter62_lane_restore.py` | the 9 new pins | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter62-lane-restore/01_fix_report.md` | THE deliverable: per-fix before/after + mic gate table + chat fail-clean note + the owner-HITL prompt-string proposal | N |
| UNTOUCHED forever: `tests/llm2llm/harness.py`, `diallux/media/session.py`, prompts (incl. `contact_details.md`), `.env` (never committed), prewarm.py, deepgram_stt.py, wt-iter61, `:8020` | — | — |

## Deploy Rules
- NOTHING deploys to production. `:8020` (wt-iter58) untouched forever. The ONLY restart surface is `:8021`, from `/tmp/opencode/wt-iter62`, exact commands in master plan §4 T8 (kill via verified pid only — re-resolve the REAL pid after setsid and pin it into `/tmp/opencode/voice_8021.pid`). NEVER bind :8000-:8003. No git merges, no tags. `.env` never committed; run `scripts/keyhound` before any push. Commits only on `engine/iter62-lane-restore` after the suite gate is green. Merge = owner decision at the STOP POINT.
- Cancel any Cal.com test bookings (event 3801235 is REAL) if a booking gets created during testing.

## Tasks (in order)

### T0 — GATE 0: owner approval of the master plan
Goal: explicit owner go-ahead before any code (owner chose "Hold — review the master plan" on 2026-09-21).
Files: none.
Commands: present `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter62-lane-restore/04_master_plan.md` summary + the one flagged deviation (2 test rewrites); wait for owner.
Dependencies: none.
Verification: owner says approve (or returns change requests → update master plan first, re-present).

### T1 — Worktree + baseline (master plan §4 T1)
Goal: exact tree to fix; suite green before touching anything.
Files: none.
Commands: full command block in master plan §4 T1 (worktree add from `6c986e8`, venv symlink, `.env` copy, pytest baseline).
Dependencies: T0.
Verification: `git -C /tmp/opencode/wt-iter62 log --oneline -1` = `6c986e8`; suite = **413 passed** (any other count → STOP and reconcile).

### T2 — Apply the 11 edits E1-E11 (master plan §1)
Goal: the code fixes, byte-exact as specified.
Files: `/tmp/opencode/wt-iter62/engine/diallux/graph/builder.py` (E1-E10), `/tmp/opencode/wt-iter62/engine/diallux/graph/tools.py` (E11).
Commands: apply each before/after block from master plan §1; `py_compile` both files after.
Dependencies: T1.
Verification: compile clean; grep-spot each edit landed (e.g. no respawn call left in the hybrid consume; `zero_hit` present in both span emitters; solar tuple present).

### T3 — Rewrites R1/R2 + 9-pin file (master plan §2-§3)
Goal: pins prove every fix hermetically; the 2 respawn-asserting pins move to the new fail-clean semantics (names kept).
Files: `/tmp/opencode/wt-iter62/engine/tests/test_iter60_audit_fixes.py`, `/tmp/opencode/wt-iter62/engine/tests/test_iter59_rag_freshness.py`, `/tmp/opencode/wt-iter62/engine/tests/test_iter62_lane_restore.py` (new).
Commands: bodies from master plan §2 (R1, R2) and §3 (pin specs 1-9; crib helpers from the iter49 parity test file as the master plan specifies).
Dependencies: T2.
Verification: new file has exactly the 9 named test functions; zero other existing test files touched.

### T4 — Suite gate (master plan §4 T7)
Goal: 422 passed, 0 failed.
Files: none.
Commands: `cd /tmp/opencode/wt-iter62/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3`.
Dependencies: T3.
Verification: **422 passed, 0 failed**. If an UNEXPECTED existing test fails: fix forward per the empty⇒degraded semantics, record it in the fix report — never weaken a pin to pass.

### T5 — Restart :8021 from wt-iter62 + health/preflight (master plan §4 T8 commands)
Goal: the test surface runs the fixed code.
Files: none (ops).
Commands: exact block in master plan §4 T8 (kill via verified pid; `RAG_FIRE_MODE=hybrid CALL_PREWARM=true` setsid uvicorn; re-resolve REAL pid into `/tmp/opencode/voice_8021.pid`; health + preflight).
Dependencies: T4.
Verification: `:8021` healthy, preflight GREEN, pid file holds the REAL pid, `git log --oneline -1` in the serving worktree = the iter62 commit-to-be (branch head).

### T6 — Owner mic re-test → MIC GATE (master plan §4 T8 gate)
Goal: byte-stable mic behavior + visibly un-blinded retrieval.
Files: none.
Commands: Telegram the owner the SAME mic URL (hitl command in Environment); pull `.venv/bin/python scripts/mic_events.py --sid <new-sid> --langfuse`.
Dependencies: T5 + owner availability.
Verification: full gate table in master plan §4 T8 (p50 ±25% of 1188 ms, eager_final_match 100%, zero STT/TTS errors, zero_hit count < 38/67, objection query non-empty, pinned non-empty post-industry). Fill the table into the fix report.

### T7 — Ledger flips (master plan §4 T9 step 1)
Goal: evidence survives the session.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`.
Commands: `scripts/live_sql.py import --window "HH:MM-HH:MM" --run mic-iter62 --branch engine/iter62-lane-restore --commit <sha>` (from the worktree, `.env` sourced); flip FIND-30 → `fixed-in-iter62 verified-live` with span evidence; append FIND-29 fix-note (need_digits recovery + sha; prompt half stays parked).
Dependencies: T6.
Verification: SQL reads back the new run + flipped finding (venv python, NO sqlite3 CLI).

### T8 — Fix report + commit + ASK (master plan §4 T9 steps 2-4)
Goal: close the loop; owner decision point.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter62-lane-restore/01_fix_report.md` (new).
Commands: exact commit block + hitl_ping ASK text in master plan §4 T9 (include the owner-HITL proposal for the contact_details YES-branch string — owner applies, agent never edits prompts).
Dependencies: T7.
Verification: suite green; `git -C /tmp/opencode/wt-iter62 status` clean after commit; report on disk; FIND-30 flipped; ping sent. **STOP — merge = owner.**

## Validation Plan (end-to-end)
1. Master plan approved (GATE 0) before any code; all work on `/tmp/opencode/wt-iter62` @ branch `engine/iter62-lane-restore`.
2. `tests/test_iter62_lane_restore.py` exists with the 9 named pins; suite = **422 passed, 0 failed**; zero edits to `harness.py`/`session.py`/prompts; exactly 2 existing test files amended (R1/R2) as approved.
3. `:8021` serving wt-iter62 (verified pid), health + preflight GREEN.
4. MIC GATE fully GREEN (owner call): latency byte-stable vs iter61; zero-hit spans strictly < 38/67; objection-turn query carries the utterance; pin resolves post-industry.
5. Ledger FIND-30 flipped with evidence; fix report on disk; owner pinged. Chat `--rag` fail-clean spans documented as expected behavior, not a regression.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merge of iter62 (and iter61), tags, `scripts/git-tree.sh` | owner decision at the STOP POINT (LAW 0) |
| contact_details.md YES-branch string edit | owner HITL — agent proposes in the fix report, owner applies |
| FIND-29 calendar seed + gate ordering | owner parked ("very simple fix, later") — separate small iteration |
| FIND-31 duplicate log handler, FIND-32 mid-sentence cuts/barge-in opener variance | parked; independent surfaces |
| Pain-amplification KB | owner HITL — content does not exist yet |
| `rag_filter_score` / `rag_min_query_chars` / `rag_live_await_ms` tuning | owner-calibrated; no evidence to change |
| Chat-surface lane firing (`--rag-fire-sim` or session-free fire) | owner deferred 2026-09-21 ("no code changes to make this both ways") |
| `/voice60` Caddy route commit to `/etc/caddy` git | owner sudo one-liner, harmless, still pending |
