# PLAN — iter59 code audit: master plan / build report vs the actual code (flaw hunt, top-tier model session)

## Meta
- Date: 2026-09-20
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: READ-ONLY audit — a fresh top-tier agent verifies the iter59 build (branch `engine/iter59-kb-everywhere-freshness` @ `6d13803`) against its two governing documents (`04_master_plan.md` + `02_build_report.md`), hunting for flaws, bugs, races, and spec violations. NO code changes in this session; findings go to an audit report for owner review.
- Status: **PLAN ONLY (not started — awaits approval)**
- Code under audit: commit `6d13803` on branch `engine/iter59-kb-everywhere-freshness` (one commit on top of base `db8e56f`), checked out at worktree `/tmp/opencode/wt-iter59`.

## Compaction Context (session 2026-09-20 — pin, do not re-derive)

- **What happened:** the owner's plan `plans/plan_v5_iter59_assess_rag_rebalance.md` was run through the Surgeon Framework → `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter59-kb-everywhere-freshness/04_master_plan.md` (10 corrections C1-C10 applied). Phase A (T1 assessment + T2 owner GO) completed; owner approved: greeting pre-record (stock-phrase cache), model snapshot pin `sonic-3.6-2026-08-27`, and T3/T4/T5 core. Phase B (T3-T5) was BUILT and COMMITTED this session as commit `6d13803` (13 files, +1931/−103): `rag_fire_mode` (eot|speech-window|round-sync|hybrid), KB-everywhere (`_RETRIEVAL_OFF=set()`), semantic dedupe 0.90, transport prewarm + greeting phrase cache. Suite: **398 passed** (368 baseline + 30 new pins; 7 old pins re-pinned to the new surface). NOT deployed; T6 (owner live call) and T7 (closeout) are open STOP POINTS.
- **The two documents the audit checks against:**
  - Master plan: `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter59-kb-everywhere-freshness/04_master_plan.md` (normative spec; corrections C1-C10 in its §0; tasks T3/T4/T5 in its §3).
  - Build report: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/02_build_report.md` (what was actually implemented, file:anchor per item, + 4 declared T3 deviations, + declared T4/T5 deviations, + the 7 updated old pins).
- **Assessment evidence pack:** `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/01_assessment.md` (flux Update payload spec, dedupe sweep 0.90, verbosity A/B, Retell/Cartesia provider research, greeting-cache decision §7).
- **Verified pinned facts (trust as-is):** flux `Update` = ~every 0.25 s, transcript CUMULATIVE within turn, NO `is_final` field; finality = EagerEOT/EndOfTurn (+TurnResumed cancel). Live trace `daee4b0059ac42c5d52826aa2f56eff9`: 24 rag spans, 23 degraded, await p50 60.8 ms, rag rows stop 06:57:20, zero in contact_details. Dedupe sweep: near-verbatim dups 0.939-1.000, legit controls max 0.748, cross-hit 0.851 — 0.90 separates. Verbosity high NOT slower (TTFT p50 794 vs 785 ms). Cartesia: WS+contexts is their lowest-latency endpoint; custom buffering (`max_buffer_delay_ms=0`) is our path; dated snapshot `sonic-3.6-2026-08-27` is their production recommendation.
- **Owner decisions (DO NOT revisit):** hybrid = preferred `rag_fire_mode` (owner: "our worse latency on RAG will be Lane B EOT 90ms which is acceptable"); greeting pre-record APPROVED ("thats what retell does"); prompts = OWNER only; one embed model only (arctic-m); KB in all states = Retell-parity intent; lane-B sub-90ms compression = Phase C later-tests only.
- **Key paths:** worktree `/tmp/opencode/wt-iter59` (engine at `engine/`); venv symlink `/tmp/opencode/wt-iter59/engine/.venv` → main venv; `.env` copied from wt-iter58 (has `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` appended; NO `RAG_FIRE_MODE` yet — deploy-time decision, default stays `eot`); ledger `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; Langfuse `http://localhost:3001`; report folder `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/`.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| This session is READ-ONLY: audit report only, zero code/config/test changes | owner: "main purpose is to check THAT plan against the code, specifically look for flaws or bugs" — fixes found = separate follow-up iteration plan, owner-gated |
| The audit target = commit `6d13803` diff vs `db8e56f`, reviewed against `04_master_plan.md` T3/T4/T5 + `02_build_report.md` claims | that commit is the entire Phase B surface |
| The audit report is the ONLY deliverable: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/04_code_audit.md` | evidence goes to research/ (LAW: evidence → research/, gitignored) |
| Every finding = severity (BLOCKER / HIGH / MED / LOW / INFO) + file:line + why + minimal-fix sketch (NOT applied) | owner decides what gets fixed |
| The 7 re-pinned old tests are IN SCOPE: verify each update reflects intended behavior, not a weakened assertion | re-pinning is where bugs hide (assertion weakened to pass) |
| Suite must be re-run by the auditor: `pytest tests -o addopts="" -q` expect **398 passed** | proves the audited tree is the committed tree |
| Laws: no merges, no deploy, no :8020 restart, no prompt edits, no KB creation | LAW 0 + master plan house rules |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None — everything the auditor needs is on disk (worktree, docs, suite, git history) | — |

## Environment & Dependencies
- Worktree (already exists): `/tmp/opencode/wt-iter59` — branch `engine/iter59-kb-everywhere-freshness` @ `6d13803`. If missing: `cd /home/julio/projects/clean_diallux_SDR && git worktree add /tmp/opencode/wt-iter59 engine/iter59-kb-everywhere-freshness && ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter59/engine/.venv && cp -p /tmp/opencode/wt-iter58/engine/.env /tmp/opencode/wt-iter59/engine/.env`
- Suite command: `cd /tmp/opencode/wt-iter59/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → expect `398 passed` (~71 s). NO sqlite3 CLI on this box — DB reads via `.venv/bin/python -c "import sqlite3; …"`.
- pip trap: `engine/.venv` is a copy-mirror — always `<venv>/bin/python -m pip …`, never the pip script.
- Reading SQLite: `cd /tmp/opencode/wt-iter59/engine && .venv/bin/python -c "import sqlite3; con=sqlite3.connect('/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db'); …"`.
- Git verification: `cd /tmp/opencode/wt-iter59 && git log --oneline -3` (expect `6d13803` on top, `db8e56f` below) && `git status --short` (expect clean) && `git diff db8e56f..6d13803 --stat`.
- Documents: master plan + build report + assessment (paths in Compaction Context). Code under audit: `/tmp/opencode/wt-iter59/engine/diallux/` (the 13 changed files listed in `02_build_report.md` §J).
- Relevant runtime facts: `.env` currently in wt-iter59 = wt-iter58 copy + `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27`; `DEEPGRAM_EAGER_EOT_THRESHOLD=0.7`; `MAX_CALL_TURNS=64`; `MAX_CALL_SECONDS=900`; `AUDIO_TRANSPORT=browser` (the :8020 mic bridge); Langfuse `:3001`.

## Architecture (one block diagram)
```
AUDIT SESSION (read-only, one report)
  1. Re-run suite (398 expected) + verify tree == commit 6d13803
  2. Read governing docs (master plan T3/T4/T5 §, build report)
  3. Diff review: git diff db8e56f..6d13803 (13 files)
  4. Deep-read the 6 runtime files against the spec:
     builder.py (consume/lanes/dedupe) · session.py (fire points)
     deepgram_stt.py · cartesia_tts.py · prewarm.py · app.py (+config/state)
  5. Adversarial checks (the hunt list in T3 of THIS plan)
  6. Write findings → research/surgeon/iter59-kb-everywhere/04_code_audit.md
  7. STOP — owner decides fixes (new plan, new session)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/04_code_audit.md` | THE deliverable: per-master-plan-item verdict + flaw list (severity, file:line, repro/trace, minimal-fix sketch, NOT applied) | N |
| everything else | UNTOUCHED | — |

## Deploy Rules
- Nothing deploys, nothing restarts. :8020 keeps serving `/tmp/opencode/wt-iter58` (untouched). NEVER bind :8000-:8003. No git merges, no branch changes, no .env edits, no prompt edits, no Retell API writes (GET-only), production agent IDs untouched (AGENTS.md hard rule 6).

## Tasks (in order)

### T1 — Re-verify the audited tree
Goal: prove the worktree is exactly commit `6d13803` and the suite is green BEFORE reading anything (audits a moving tree otherwise).
Files: none.
Commands (full): `cd /tmp/opencode/wt-iter59 && git log --oneline -3 && git status --short` then `cd /tmp/opencode/wt-iter59/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3`.
Dependencies: none.
Verification: `6d13803` on top of `db8e56f`; empty `git status`; `398 passed`.

### T2 — Rebuild the spec-vs-code map
Goal: for EACH master-plan T3/T4/T5 line item + each `02_build_report.md` claim, locate the code that implements it (or flag MISSING).
Files: read only — `/tmp/opencode/wt-iter59/engine/diallux/config.py`, `diallux/graph/builder.py`, `diallux/media/session.py`, `diallux/media/deepgram_stt.py`, `diallux/media/cartesia_tts.py`, `diallux/media/prewarm.py`, `diallux/app.py`, `diallux/state.py`; plus the 3 pin files `tests/test_iter59_rag_freshness.py`, `tests/test_iter59_dedupe_semantic.py`, `tests/test_iter59_prewarm.py` and the 2 updated files `tests/test_iter25_tags.py`, `tests/test_iter49_rag_parity.py`.
Commands (full): `cd /tmp/opencode/wt-iter59 && git diff db8e56f..6d13803 > /tmp/opencode/iter59_audit_diff.txt && wc -l /tmp/opencode/iter59_audit_diff.txt` (read the diff in slices; grep for each master-plan keyword: `rag_fire_mode`, `_update_fired`, `on_update`, `laneA`, `laneB`, `_live_seq`, `_live_consumed`, `round-sync`, `hybrid`, `_RETRIEVAL_OFF`, `question_stem_window`, `tts_dedupe_cos_threshold`, `call_prewarm`, `tts_phrase_cache`, `_phrase_key`, `_emit_cached`, `lifespan`).
Dependencies: T1.
Verification: every master-plan T3/T4/T5 bullet has a file:line citation or a MISSING entry in the working notes.

### T3 — Adversarial flaw hunt (the core of this session)
Goal: find real bugs. Check each of these PRE-DECLARED hunt vectors plus anything else observed (each vector ends with the failure it must disprove):
Files: the runtime files above.
Commands: reading only; targeted greps as needed from `/tmp/opencode/wt-iter59`.
Hunt vectors (each must be confirmed SAFE or become a finding):
1. **seq supersede races**: two spawns same state+lane in the same tick (EOT then EagerEOT) — does the older task's cancel propagate before consume? Does `spawn_live_retrieve` bump `_live_seq[state]` (state-level, shared across lanes) so a laneB fire invalidates a laneA fire's freshness comparison? (READ CAREFULLY: `_live_consumed` is state-level but `_live_task_seq` is key-level — a hybrid consume that consumes laneB's seq could wrongly un-fresh laneA, or vice versa.)
2. **hybrid degrade**: laneA landed but NOT yet consumed seq floor — `_consume_hybrid` uses `raw_a.get("seq", 0) > self._live_consumed.get(state, -1)`; verify a laneA task from a PREVIOUS turn (stale seq) can never pass, and that a cancelled laneB triggers respawn with the CURRENT msg (stale `_live_msgs[key]` from the fire at Update time could double-key).
3. **dedupe token path**: `_embed_stem` on the token streaming hot path — verify statements/fragments truly never embed; verify a `store=None` embed never blocks speech; verify the FIFO cap cannot drop below `tts_dedupe_stem_window` correctness; verify the round-scoped `stem_window` write-back can't lose questions when a round speaks no question (it rewrites the SAME list — confirm no duplicate-append across rounds via `_spoken_entry_has`).
4. **state plain-key race**: `question_stem_window` has NO reducer — two concurrent rounds of the same turn (tool loops) rewrite full lists; verify last-write-wins cannot erase a stem appended by a parallel round in the SAME turn (cross-round dedupe contract).
5. **session fire/skip matrix**: every combination of {eager ON/OFF, rag_fire_mode, Update fired/none, TurnResumed mid-turn, barge-in mid-turn, adopt path, cancel+rerun path, graceful cap close} — confirm lane B fires exactly once per turn, `_update_fired` clears in every path, and speech-window's skip never strands a turn with NO fire (e.g. eager OFF + Update fired at 0.3 s: EOT skips fire — is the landed partial-utterance task the ONLY source? its msg is the PARTIAL text — verify consume's seq path consumes it despite msg mismatch).
6. **speech-window partial-transcript lane B**: the fire at Update embeds a PARTIAL transcript as lane B's query; at consume the FINAL transcript differs — verify the consumed result is treated fresh (seq) but the KNOWLEDGE rendered used the partial query — is that acceptable per plan (Retell tier), and is it flagged in the report (the master plan speech-window gate says await p50 ≤15 ms — the partial-utterance tradeoff must be in the report).
7. **prewarm adoption races**: pool pop then session `connect(ws=...)` — if two calls start simultaneously, both pop → one gets None → fallback fresh connect (verify no crash); adopted STT socket keeps the PREWARM keepalive task (bounded? leaked after call end? does session.stop close it or does the maintainer leak one task per call?); adopted TTS socket's idle-drain task from prewarm is NOT cancelled on adoption — two recv loops on ONE socket? (READ `_spawn_idle_tts` drain task vs `CartesiaTTS.connect(ws=...)` recv task — potential double-consumer race on the adopted socket.)
8. **phrase cache**: byte-compat (cached bytes must match output_format+gen_cfg — key includes them, verify the PREWARM build uses `resolve_delivery(settings,"begin")` exactly as the session greeting does, incl. `tts_delivery_profiles=False` case where overrides=None); emit pacing (`_emit_cached` ~100 ms chunks — verify Twilio 20ms-frame expectation can't overflow; verify barge-in cancel cannot stop a cache splice mid-stream and whether that's acceptable); `first_byte_ts` stamping; the greeting `_greet` anchors still measure cache-hit audio correctly (stream_to_first_ms).
9. **config surface**: `rag_fire_mode` default "eot" everywhere respected (no silent hybrid); env override names (pydantic-settings: `RAG_FIRE_MODE`, `TTS_DEDUPE_SEMANTIC`, `CALL_PREWARM`, `TTS_PHRASE_CACHE`, `TTS_DEDUPE_COS_THRESHOLD`, `TTS_DEDUPE_STEM_WINDOW`); verify `.env` additions don't leak (gitignored).
10. **revert surfaces**: `rag_fire_mode="eot"` == iter58 byte-exact? (consume path keyed `|full` — confirm the msg-match + `_live_prev` degrade path is UNCHANGED logic, only re-keyed); `call_prewarm=False` == iter58 (no lifespan work, no adoption branch); `tts_phrase_cache=False` == always-API; `tts_dedupe_semantic=False` == iter42 exact.
11. **the 7 updated old pins**: confirm each update matches the new intended behavior and did not LOSE a property the old pin protected (list in `02_build_report.md` §E).
12. **KB-everywhere blast radius**: token-cost delta of 4 freed states retrieving every round (report must quantify: ~1600 chars delta per round × the freed states — verify the report's token-cost note exists, else flag); Closing allow-list interplay (`_RETRIEVAL_ALLOW` still referenced? dead code?).
13. **langfuse span schema**: node rag span `"mode"` now dynamic (`live-async`/`live-sync`/`hybrid`) — verify `scripts/live_sql.py` import + `lf_quick.py` consumers won't break on the new labels (read those scripts' span parsing).
Commands for 13: `cd /tmp/opencode/wt-iter59/engine && grep -n "live-async\|mode.*rag\|\"mode\"" scripts/live_sql.py scripts/lf_quick.py | head -20`.
Dependencies: T2.
Verification: every hunt vector has a verdict line in the working notes (SAFE + why / FINDING + severity).

### T4 — Write the audit report
Goal: the single deliverable.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/04_code_audit.md` (N).
Commands (full): none beyond editors.
Report structure (mandatory):
1. Header: audited commit `6d13803`, base `db8e56f`, suite result re-run.
2. Verdict table: master-plan item → verdict (MATCHES / DEVIATION-declared / MISSING / BUG) + file:line.
3. FINDINGS list: each = id (AUD-N), severity (BLOCKER/HIGH/MED/LOW/INFO), file:line, what, why it's wrong, minimal repro/trace, proposed minimal fix (described, NOT applied).
4. The 10 hunt vectors' explicit SAFE/FINDING dispositions.
5. Regression-risk list: what a top-tier reviewer believes could break the T6 live call, ranked.
Dependencies: T3.
Verification: report on disk; zero changes outside `research/` (verify `cd /tmp/opencode/wt-iter59 && git status --short` still empty).

### T5 — STOP POINT: owner review
Goal: owner reads `04_code_audit.md`, decides fixes (new iteration) vs proceed-to-T6-deploy.
Files: none.
Commands: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python /tmp/opencode/wt-iter59/engine/scripts/hitl_ping.py "<audit ready summary>"` (from the worktree engine dir with both-env export chain: `set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "..."`).
Dependencies: T4.
Verification: ping sent (or explicit skip logged); NO further action.

## Validation Plan (end-to-end)
1. `04_code_audit.md` exists with per-item verdicts + severity-ranked findings.
2. `git status --short` in the worktree is EMPTY (read-only session proven).
3. Suite re-run recorded in the report matches `398 passed`.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Applying fixes for any AUD-N finding | fixes = new iteration branch + plan (owner-gated); this session is read-only |
| T6 deploy + owner live call | still open from the master plan; runs only after the owner digests the audit |
| T7 closeout (CALL_FACTS, PENDING_TASKS, ITERATIONS, ASK) | blocked behind T6 |
| Phase C latency-compression exploration (`03_latency_compression.md`) | master plan Phase C — separate session after T7 |
