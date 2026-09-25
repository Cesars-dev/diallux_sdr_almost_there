# PLAN — iter62: lane restore (fix the retrieval "nonsense", keep mic behavior byte-stable)

## Meta
- Date: 2026-09-21
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — repair the two-lane retrieval (Lane A pinned at first-Update + Lane B utterance at EagerEOT) by deleting the coordination machinery that breaks it (msg-mismatch respawn, history re-extraction, stale fallback, dishonest degraded flag), add solar alias, fix the `is_calling_best_number` dead-end (empty `callback_number` has NO recovery — engine must never leave the model without a scripted next step). **NO code changes to `tests/llm2llm/harness.py`** — the chat surface stays exactly as-is; lane logic is checked on chat via a no-LLM pin that drives spawn/consume directly, and the fire-sim flag is DEFERRED (owner decision 2026-09-21: "lets not mess the py… no code changes to make this both ways — just fix what we set out to do"). NO regressions on mic: when retrieval lands in time, behavior is byte-identical; suite green; owner mic re-test gates the merge. NO merges, NO :8020 changes, NO prompt edits (one contact_details string flagged owner-HITL).
- Status: **PLAN ONLY (not started — awaits approval)**

## Compaction Context (session 2026-09-21 — pin, do not re-derive)

- **Project state:** iter61 (`engine/iter61-prewarm-staleness` @ `6c986e8`, suite **413 passed** = 407 + 6 pins) fixed AUD-11/12/13 (prewarm socket staleness) and is LIVE-VERIFIED on the mic: call `cc22e0a0185e` (2026-09-21 05:48-06:04 UTC, 54 turns) ran with ZERO UNPARSABLE frames, ZERO idle-timeout deaths, TTL respawns rotated the pool mid-call untouched. Test server `127.0.0.1:8021` runs from worktree `/tmp/opencode/wt-iter61` (pid file `/tmp/opencode/voice_8021.pid` — REAL pid 1983323, verify with `ss -ltnp | grep 8021` + `readlink /proc/<pid>/cwd`), env-injected `RAG_FIRE_MODE=hybrid CALL_PREWARM=true`. Production `:8020` = wt-iter58, UNTOUCHED.
- **The mic call was "80% there" (owner):** agent quality excellent on a "lobotomized DB"; failures = calendar gate (FIND-29, parked) + retrieval blindness (FIND-30 — THIS iter fixes). Full SOP analysis: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter61-prewarm-staleness/02_mic_call_sop_report.md`. Deep dive: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter61-prewarm-staleness/03_kb_retrieval_deep_dive.md`.
- **The four proven retrieval failure classes (67 rag spans, trace `775a7aa8510c`):**
  1. **Lane B ran EMPTY on 25/67 rounds** — rag span `query=''` while the SAME round's generation input contained the full utterance (proof: 06:02:40 span `query=''` vs input *"how how much do you guys charge…"*). Mechanism: `_consume_hybrid` (`/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py:1508`) compares the fire-side msg against a consume-side re-extraction from graph history (`builder.py:1867-1869`); under eager/barge-in they diverge → the **msg-mismatch RESPAWN** (`builder.py:1548-1556`, iter60 AUD-4) re-fires lane B with `''` → `rag_min_query_chars=12` gate (`config.py:232`) builds no lane → instant empty result reported `degraded=False`.
  2. Lane A = recipe-NAME embedding queries ("re-anchoring", "the empathic mirror") that match nothing — 0 chunks 0/8 Offer, 0/7 Intake. (Owner decision: keep iter49 Lane A shape — refer-tag lanes; the KB content itself is fine.)
  3. `rag_live_await_ms=60` covers only pgvector+merge when the fire→consume hand-off is intact (embed ~90 ms runs during speech, by design). It loses only when the respawn bug restarts the embed from zero inside the await. Owner calibrated `rag_filter_score=0.24` (`config.py:225`) — **NOT the problem, do not touch**.
  4. `degraded` only means "machinery crashed" — 25 blind rounds hid behind `degraded=False` with chunks=0.
- **Design archaeology (git-proven):** iter49 T4 (`fc42a3e`) = ONE batched task (`build_lanes` → single embed → one merge), fired at EagerEOT, 60 ms await, landed-late fed the next round. iter52 (`054af7b`) = industry PIN: `_ensure_pinned_industry` → `pinned_by_tag()` = METADATA fetch (no embed, no filter), dv-gated, cached per dv, rendered first. iter59 (`6d13803`, plan `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter59_assess_rag_rebalance.md`) split into two keyed tasks + ~375 lines of seq/respawn/supersede coordination (the plan's own contradiction: "fire the final utterance at StartOfTurn" is physically impossible) — the coordination machine is the bug source. iter60 AUD-3/AUD-4 patches added more reconciliation.
- **KB data facts (verified against `DATABASE_URL` in `/home/julio/projects/clean_diallux_SDR/engine/.env` → `postgresql://…@localhost:5434/diallux`, table `kb_chunks_v2` via `RAG_TABLE_NAME`):** `kb_chunks_v2` HAS the `vertical` column (plain `kb_chunks` does NOT — irrelevant, engine reads v2); industry = 60 chunks, 20 verticals × 3; solar exists as vertical **"Residential Roofing & Solar Installers"** (3 chunks). `_PIN_ALIASES` (`builder.py:119`) has NO "solar" alias → resolver fell to embed fallback with `"solar company"` → < 0.24 → miss **cached per dv for the whole call** → `pinned=""` in all 67 spans.
- **Owner Resolved Decisions (verbatim intent):** "absolutely no regressions — this iter is working excellent on mic"; "we don't need to go back — fix the nonsense, make the two-lane design work"; "lane A = 3 pinned KB retrieves (check what iter49 was doing)"; **fix 2 REJECTED** — "landed-late feeding the next round" is exactly what we avoid: a late chunk that makes no sense must NOT be injected; if the await fails, the turn fails clean (no fresh chunks); "the missed pin should not be a problem unless it really blocks a state change" (pin untouched, alias one-liner ok); "no prompt edits — prompting is owner HITL"; calendar bug (FIND-29) parked for later.
- **Ledger:** `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` — run `mic-20260921-0548@6c986e8` (12 sops rows), FIND-26/27/28 = `fixed-in-iter61 verified-live`, FIND-29 (calendar, parked), FIND-30 (retrieval blindness — THIS iter's target), FIND-31 (duplicate log lines, parked), FIND-32 (mid-sentence cuts, parked).
- **Chat-surface testing gap (owner):** the llm2llm harness has no EOT/Update events, so the lane fire/consume paths never run on chat. Owner direction: "we can just add awaits that mimic a call — good for testing the logic." → harness fires laneA+laneB per turn with a configurable simulated speech window before consuming.
- **Verified-safe facts (do not re-check):** mic latency profile to PRESERVE — e2e_response p50 1188/p90 2435 ms, llm_first_to_tts_first p50 238 ms, eager_final_match 54/54, barge-in working (38/54 — owner-confirmed natural); prewarm loads: STT 531 ms / TTS 463 ms / RAG embedder 1338 ms / phrase cache 2160 ms; turn 1 = lite (cache_read=0), turn 2 = first full-cached (cache_read=2688); websockets 16.1.1, fastembed arctic-m 768-d, `RAG_TABLE_NAME=kb_chunks_v2`; NO sqlite3 CLI (use `<venv>/bin/python -c "import sqlite3…"`); pip trap: always `<venv>/bin/python -m pip`.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Fix 1: single source of truth for the turn utterance — `ingest` keeps `user_text` for the whole turn (stops wiping it mid-turn), `state_node` consumes `state["user_text"]`; DELETE the history re-extraction (`builder.py:1867-1869`) and the msg-mismatch respawn (`builder.py:1548-1556`) | fire and consume then agree by construction (both use the session-provided transcript) — kills the 25/67 empty-query rounds at the root |
| Fix 3: Lane A keeps the iter49 shape — spawn at first Update, `build_lanes(state, dvs, "")` = ≤3 refer-tag lanes (`tag.what` + dv values, scope `[tag.kb]`, quota-exempt); states without refer-tags get no Lane A (Lane B covers them, KB-everywhere stands) | owner: "lane A 3 pinned KB retrieves (check what iter49 was doing)"; no recipe-name invention; zero behavior change when tags exist |
| Fix 4: `degraded=True` when the merged set is EMPTY (not only when machinery crashes) + add `zero_hit: bool` to the rag span output | owner: "just a boolean so we understand nothing was retrieved"; observability only |
| Fail clean: DELETE the `_live_consumed_res`/`_live_prev` stale fallback in `_consume_hybrid` — await miss ⇒ empty delta + `degraded=True`; a late-landing task is simply superseded by the next turn's fire (spawn already cancels pending) | owner REJECTED landed-late injection: "the model can be fed a chunk that makes no sense whatsoever" |
| `rag_filter_score=0.24` and `rag_min_query_chars=12` UNTOUCHED | owner calibrated 0.24 over many measured conversations; 12-char gate is correct once the utterance reaches retrieval |
| Solar alias one-liner: `("solar", "Residential Roofing & Solar Installers")` in `_PIN_ALIASES` | vertical exists in `kb_chunks_v2` (3 chunks); pin missed only for lack of the alias; dv-gated pin gating unchanged (iter52) |
| Best-calling recovery (FIND-29 family, IN scope now): `record_reach_details(is_calling_best_number=true)` with EMPTY `{{callback_number}}` must return a scripted recovery (`{"status": "need_digits", "instruction": "ask <What's the best number to reach you?> then call set_callback_number with the digits"}`) instead of `ok` — today the YES branch is a guaranteed dead end on mic (no caller-ID to seed from), the ConfirmSlots gate then blocks with no recovery and the model drifted 4 min | live proof: call `cc22e0a0185e` 05:58:51 `gate_failed missing callback_number` → "I don't see the calendar on my side here" → no booking. The matching contact_details.md string edit (YES branch) = OWNER-HITL, agent proposes, owner applies |
| Harness UNTOUCHED: zero code changes to `tests/llm2llm/harness.py` in this iteration; lane logic is proven on chat by the no-LLM pins (direct `spawn_live_retrieve` → `_consume_live_retrieve` drive in the new pin file, no harness edits) | owner: "lets not mess the py… no code changes to make this both ways — leave as is, just fix what we set out to do" |
| Chat-surface consequence (known, accepted): with the respawn deleted, a chat harness `--rag` run fires NO lane tasks (fires live in the session layer, chat has no EOT) → rag spans on chat show `degraded=true, zero_hit=true` — that IS the fail-clean semantics working; the chat fire decision is DEFERRED | follows from fail-clean (fix 2 rejected); documented so the chat check is not mistaken for a regression |
| Mic regression gate: when retrieval lands in time the round is byte-identical; suite 413+N green; owner mic re-test on :8021 with the SAME URL/token before any merge talk | owner: "absolutely no regressions — mic was perfect" |
| Chat parity: harness `--rag-fire-sim <ms>` fires laneA (`msg=""`) + laneB (`msg=<turn text>`) then sleeps `<ms>` before the turn — mimics Update→EagerEOT→consume; `0` ms tests the await-miss path | owner: "add awaits that mimic a call — good for testing the logic" (chat has no EOT events) |
| Laws: no merges, no :8020/deploy, `.env` never committed, prompts owner-HITL, Cal event 3801235 REAL (cancel test bookings) | LAW 0 + AGENTS.md |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None | — |

## Environment & Dependencies
- Main venv: `/home/julio/projects/clean_diallux_SDR/engine/.venv` (symlinked into worktrees). websockets 16.1.1, fastembed 0.8.0 (arctic-m 768-d ONNX), pytest present. NO new dependencies.
- Base branch: `engine/iter61-prewarm-staleness` @ `6c986e8` (suite 413). New branch `engine/iter62-lane-restore` cut from `6c986e8`; worktree `/tmp/opencode/wt-iter62`.
- Suite: `cd /tmp/opencode/wt-iter62/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → baseline **413 passed** before edits.
- `.env`: `cp -p /tmp/opencode/wt-iter61/engine/.env /tmp/opencode/wt-iter62/engine/.env` (has `VOICE_TEST_TOKEN`, `LANGFUSE_*`, `DATABASE_URL` → localhost:5434/diallux, `RAG_TABLE_NAME=kb_chunks_v2`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.7`). If wt-iter61 is gone: `cp -p /home/julio/projects/clean_diallux_SDR/engine/.env …` and append `RAG_TABLE_NAME=kb_chunks_v2` if absent.
- Test server :8021 (ONLY restart surface): pid file `/tmp/opencode/voice_8021.pid` — VERIFY reality first: `ss -ltnp | grep 8021` → `readlink /proc/<pid>/cwd` must be the worktree you restarted (stale-pid trap burned iter61: setsid forks so `$!` is a wrapper — after launch, re-resolve the real pid by cwd and write THAT into the pid file). Caddy route `/voice60/* → 127.0.0.1:8021` live. Mic URL: `https://flores.diallux-ai.site/voice60/mic?k=$VOICE_TEST_TOKEN`.
- `:8020` = wt-iter58 production test surface — NEVER touch. Ports 8000-8003 NEVER bound.
- Harness: `/home/julio/projects/clean_diallux_SDR/engine/tests/llm2llm/harness.py` (personas in `tests/llm2llm/personas.py` — 13 REAL names only).
- Langfuse `http://localhost:3001` (keys in `.env`); puller `scripts/lf.py`; mic timeline `scripts/mic_events.py` (`--sid`, `--window`, `--langfuse`).
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (NO sqlite3 CLI).
- Telegram ASK: `cd /tmp/opencode/wt-iter62/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<message>"`.

## Architecture (one block diagram)
```
iter62 LANE RESTORE (branch engine/iter62-lane-restore @ base 6c986e8)
  T1 worktree + baseline 413
  T2 utterance single-source: ingest keeps user_text; state_node consumes it; DELETE history re-extract + msg-respawn
  T3 Lane A = iter49 shape at first Update (≤3 refer-tag lanes, tag-owned) — unchanged shape, guaranteed non-stale
  T4 honest degraded: merged==0 ⇒ degraded=True + span field zero_hit
  T5 fail clean: delete stale fallback (await miss ⇒ no chunks, degraded=True)
  T6 solar alias one-liner in _PIN_ALIASES
  T7 best-calling recovery: record_reach_details need_digits (no more empty-callback dead end)
  T8 pins file (incl. no-LLM lane drive) + suite 413+N — harness.py UNTOUCHED
  T9 restart :8021 from wt-iter62 + mic regression gate (owner re-test, same URL)
  T10 ledger flips (FIND-30, FIND-29 note) + 01_fix_report.md + commit + ASK
  STOP — merge/deploy = owner decision
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter62/engine/diallux/graph/builder.py` | T2: in `ingest` (~line 2650) do NOT wipe `user_text` mid-turn (set `patch["user_text"] = text` instead of `""`; next turn's payload overwrites it anyway); in `state_node` (~line 1867) replace the history re-extraction with `user_msg = (state.get("user_text") or "").strip()`; in `_consume_hybrid` (~line 1548) DELETE the msg-mismatch respawn block (AUD-4) — lane B tasks are keyed+cancelled by the next fire, nothing to reconcile; (~line 1583) DELETE the `_live_consumed_res`/`_live_prev` stale fallback — on no-land return `("", [], ms, [], [], True, await_ms)`; T4: after `merge_lane_chunks`, `if not merged: degraded=True` + span output gains `"zero_hit": len(merged)==0` (both span emitters at ~1882 and ~2062 paths); T6: add `("solar", "Residential Roofing & Solar Installers")` to `_PIN_ALIASES` (~line 119) | E |
| `/tmp/opencode/wt-iter62/engine/diallux/media/session.py` | T3: NO functional change — `_fire_live_retrieve(transcript)` already carries the transcript; verify only. UNTOUCHED unless T2 verification shows a divergence | E (verify-only) |
| `/tmp/opencode/wt-iter62/engine/diallux/graph/tools.py` | T7: in `record_reach_details` — when `is_calling_best_number` is true AND the dvs' `callback_number` is empty, return `{"status": "need_digits", "instruction": "Ask: What's the best number to reach you? Then call set_callback_number with the exact digits they spoke."}` instead of `{"status": "ok", …}` (still writes `phone_confirmed`); when callback_number is non-empty the response is byte-identical to today | E |
| `/tmp/opencode/wt-iter62/engine/tests/test_iter62_lane_restore.py` | 9 pins (exact list in T9) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter62-lane-restore/01_fix_report.md` | THE deliverable: per fix — change + file:line + pin + before/after (cite 03_kb_retrieval_deep_dive.md) + mic re-test + harness-sim results | N |
| everything else (prewarm.py, deepgram_stt.py, prompts, `.env`, iter61 worktree) | UNTOUCHED | — |

## Deploy Rules
- NOTHING deploys to production. `:8020` (wt-iter58) untouched forever. The ONLY restart surface is `:8021` (exact commands in T9). NEVER bind :8000-:8003. No git merges. `.env` never committed. `scripts/keyhound` before any push. Commits only on `engine/iter62-lane-restore` after suite green. Merge = owner decision at the STOP POINT.
- Kill/restart of :8021 ONLY via the verified pid (see Environment) — never `systemctl`, never `pkill uvicorn`.

## Tasks (in order)

### T1 — Worktree + baseline
Goal: exact tree to fix; suite green before touching anything.
Files: none.
Commands (full):
```
cd /home/julio/projects/clean_diallux_SDR && git worktree add -b engine/iter62-lane-restore /tmp/opencode/wt-iter62 6c986e8
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter62/engine/.venv
cp -p /tmp/opencode/wt-iter61/engine/.env /tmp/opencode/wt-iter62/engine/.env
cd /tmp/opencode/wt-iter62/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
Dependencies: none.
Verification: `git -C /tmp/opencode/wt-iter62 log --oneline -1` = `6c986e8`; suite = **413 passed**.

### T2 — Utterance single source of truth (kills the empty-query rounds)
Goal: the consume-side utterance IS the session transcript — fire and consume agree by construction.
Files: `/tmp/opencode/wt-iter62/engine/diallux/graph/builder.py`.
Changes (exact):
1. `ingest` (~line 2650): replace `"user_text": ""` in the patch with `"user_text": state.get("user_text", "")` (keep the transcript for all rounds of the turn; next turn's payload overwrites it; the existing idempotent-append guard below is unchanged).
2. `state_node` (~line 1867): replace
   `user_msg = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")`
   with
   `user_msg = (state.get("user_text") or "").strip()` (comment: iter62 — the session-provided transcript is the single source of truth; history re-extraction diverged under eager/barge-in and triggered empty respawns — 25/67 blind rounds on call cc22e0a0185e).
3. `_consume_hybrid` (~line 1548): DELETE the `if task_b is None or task_b.cancelled() or self._live_msgs.get(key_b) != msg:` respawn block; replace with: if `task_b` is missing/cancelled → `res_b = None` (no respawn — the next fire supersedes; fail clean per T5).
Dependencies: T1.
Verification: T9 pins 1-2 pass; suite green.

### T3 — Lane A confirmed iter49-shape (no code change expected)
Goal: Lane A = ≤3 refer-tag lanes at first Update, tag-owned; no recipe-name invention.
Files: `/tmp/opencode/wt-iter62/engine/diallux/media/session.py` (verify-only).
Steps: read `_on_stt_update` (session.py ~433) and `_retrieve_raw` laneA branch (builder.py ~1186-1199): confirm laneA = `build_lanes(state, dvs, "")` (refer-tags + dv values, scope `[tag.kb]`, `owned` quota-exempt). If any deviation found, fix to this shape; otherwise no edit.
Dependencies: T1.
Verification: T9 pin 3 (laneA build shape) passes; a grep proof goes into the fix report.

### T4 — Honest degraded flag + zero_hit
Goal: `chunks=0` can never report healthy again.
Files: `/tmp/opencode/wt-iter62/engine/diallux/graph/builder.py`.
Changes (exact): in `_consume_hybrid` after `merged = ragmod.merge_lane_chunks(...)`: `degraded = degraded or (not merged)`; in the rag span output dicts (live emitter ~1882 and, for parity, the freeze emitter ~2062) add `"zero_hit": (len(merged) == 0)` next to `"degraded"`. Apply the same empty-set rule in the eot/speech-window consume path (~1478-1505).
Dependencies: T1.
Verification: T9 pins 4-5 pass.

### T5 — Fail clean (delete stale fallback)
Goal: await miss ⇒ the turn goes with NO fresh chunks; nothing stale is ever injected.
Files: `/tmp/opencode/wt-iter62/engine/diallux/graph/builder.py`.
Changes (exact): in `_consume_hybrid`, replace the `if not landed:` fallback block (~line 1583) with:
```python
        if not landed:
            return ("", [], 0.0, [], [], True, await_ms)
```
(comment: iter62 — owner decision: a late/failed retrieval is a CLEAN FAIL; stale-prev injection feeds the model chunks that make no sense at the wrong moment.)
Dependencies: T2.
Verification: T9 pin 6 passes.

### T6 — Solar alias one-liner
Goal: the dv "solar company" resolves the existing vertical instead of caching a miss.
Files: `/tmp/opencode/wt-iter62/engine/diallux/graph/builder.py`.
Changes (exact): in `_PIN_ALIASES` (~line 119) add one tuple: `("solar", "Residential Roofing & Solar Installers"),` (sorted position per the existing `sorted(...)` wrapper).
Dependencies: T1.
Verification: T9 pin 7 passes (fake store: `_resolve_industry_tag("solar company")` returns the vertical tag; `pinned_by_tag` fetches 3 chunks).

### T7 — Best-calling recovery (`record_reach_details` empty-callback dead end)
Goal: the YES branch ("is the number you're calling from the best number?") can never dead-end again — the tool hands the model a scripted next step when `callback_number` is empty.
Files: `/tmp/opencode/wt-iter62/engine/diallux/graph/tools.py`.
Changes (exact): in the `record_reach_details` tool handler: when `is_calling_best_number` is true AND the session dvs' `callback_number` is empty/absent, return
```python
{"status": "need_digits",
 "instruction": "Ask: What's the best number to reach you? Then call set_callback_number with the exact digits they spoke."}
```
(still record `phone_confirmed` as today). When `callback_number` is non-empty the response is byte-identical to today. Rationale: mic transport has no caller-ID to seed from — the iter61 call proved the YES→"seeded number stands" path is an unrecoverable dead end (gate_failed → 4-min drift → no booking).
Owner-HITL rider (NOT this agent): the matching one-string edit in `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/contact_details.md` step 4 (YES branch: "if `{{callback_number}}` is empty, ask for the digits first") — propose it in the fix report, owner applies.
Dependencies: T1.
Verification: T9 pin 8 passes.

### T8 — Pins (9, one file) + suite
Goal: prove every fix hermetically; zero edits to existing test files.
Files: `/tmp/opencode/wt-iter62/engine/tests/test_iter62_lane_restore.py` (N). Crib the fake-runtime/`object.__new__` patterns from `/tmp/opencode/wt-iter62/engine/tests/test_iter59_rag_freshness.py` and settings from `_t4_settings` in `/tmp/opencode/wt-iter62/engine/tests/test_iter49_rag_parity.py`.
The 9 pins:
1. `test_ingest_keeps_user_text_across_rounds` — run `ingest` twice on the same graph state: `user_text` survives round 2 (not wiped to `""`).
2. `test_consume_uses_session_transcript_not_history` — build a bare CallRuntime (`object.__new__`), stash a laneB task FIRED with transcript "how much do you guys charge"; call the consume with `state["user_text"]` = same string → consumed `lane_qs` contains the transcript (no respawn, no history lookup).
3. `test_lane_a_shape_refer_tags_owned` — `build_lanes("Offer", dvs_with_monthly_leak, "")` returns exactly the refer-tag lanes (query = tag.what + dv values, scope `[tag.kb]`, owned == {tag.kb}); no lanes for a state without tags.
4. `test_zero_chunks_is_degraded` — hybrid consume where both lanes land but merge returns [] → returns `degraded=True`.
5. `test_span_zero_hit_field` — the rag span output dict includes `zero_hit` equal to `len(merged)==0`.
6. `test_await_miss_fails_clean` — laneB task pending with a slow fake (never done within cap) → consume returns empty delta, `degraded=True`, and the PREVIOUS set is NOT returned (no `_live_prev` read).
7. `test_solar_alias_resolves_vertical` — `_resolve_industry_tag("solar company", fake_store)` returns `"Residential Roofing & Solar Installers"` via the alias (no embed call); with a fake `pinned_by_tag` returning 3 chunks, `_ensure_pinned_industry` caches `chunks` len 3.
8. `test_lane_drive_no_llm` — directly drive `spawn_live_retrieve(laneA, "")` + `spawn_live_retrieve(laneB, "how much do you guys charge")` then `_consume_live_retrieve` with `state["user_text"]` set: merged chunks render, `zero_hit=false` — the chat-surface logic check WITHOUT touching the harness (owner: chat has no EOT; this pin is the both-surfaces proof).
9. `test_record_reach_details_need_digits_recovery` — call the `record_reach_details` handler with `is_calling_best_number=true` and empty `callback_number` dvs → response `status == "need_digits"` with an instruction mentioning `set_callback_number`; with a non-empty `callback_number` → response byte-identical to today (`status == "ok"`).
Commands (full):
```
cd /tmp/opencode/wt-iter62/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
Dependencies: T2-T7.
Verification: all 9 pins pass; suite = **413 + 9 = 422 passed** (print the actual count); ZERO existing test files edited.

### T9 — Restart :8021 from the fixed tree + mic regression gate
Goal: the test surface runs the fixed code; mic behavior proven unchanged; retrieval visibly un-blinded.
Files: none (ops).
Commands (full):
```
kill $(cat /tmp/opencode/voice_8021.pid) 2>/dev/null; sleep 2
ss -ltn | grep 8021 && kill -9 $(ss -ltnp | grep 8021 | grep -oP 'pid=\K[0-9]+' | head -1) 2>/dev/null; sleep 1
cd /tmp/opencode/wt-iter62/engine && git log --oneline -1
set -a && . ./.env && set +a
RAG_FIRE_MODE=hybrid CALL_PREWARM=true setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8021 >> /tmp/opencode/voice_server_8021.log 2>&1 &
sleep 6
# re-resolve the REAL pid (setsid fork trap) and pin it:
ss -ltnp | grep 8021 | grep -oP 'pid=\K[0-9]+' | head -1 > /tmp/opencode/voice_8021.pid
curl -sf http://127.0.0.1:8021/health && .venv/bin/python scripts/voice_preflight.py --url http://127.0.0.1:8021 2>&1 | tail -2
```
Then Telegram the owner the SAME mic URL (`https://flores.diallux-ai.site/voice60/mic?k=$VOICE_TEST_TOKEN`): "iter62 mic regression test ready — same URL, speak a pricing objection somewhere in the call". Owner calls; agent pulls:
```
.venv/bin/python scripts/mic_events.py --sid <new-sid> --langfuse
```
MIC REGRESSION GATE (all must hold, from the call's turn reports + rag spans):
- e2e_response_ms p50 within noise of 1188 ms (±25%); eager_final_match 100%; ZERO STT/TTS errors/drops; greeting plays in full; TTL respawns normal.
- Retrieval improvement: `zero_hit=true` span count on rag-eligible turns STRICTLY LOWER than the iter61 call's 38/67; the pricing-objection turn's span `query` is NON-EMPTY and contains the utterance; `pinned` non-empty once industry is known (solar alias).
Dependencies: T9.
Verification: health 200 + preflight GREEN + gate table filled in the fix report.

### T10 — Ledger flips + report + commit + ASK
Goal: close the loop; evidence survives the session.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter62-lane-restore/01_fix_report.md` (N).
Steps:
1. Ledger (venv python, NO sqlite3 CLI): import the re-test window (`scripts/live_sql.py import --window "HH:MM-HH:MM" --run mic-iter62 --branch engine/iter62-lane-restore --commit <sha>` from the worktree with `.env`); flip **FIND-30** → `fixed-in-iter62 verified-live` with the span evidence (before: 38/67 zero-hit, empty queries on objection turns; after: counts from the re-test); append a **FIND-29 fix-note** (`record_reach_details need_digits recovery` + `fix_commit` the iter62 sha — the gate/prompt half stays parked for the owner's string edit).
2. Write `01_fix_report.md`: per fix (T2/T4/T5/T6/T7) — before (cite `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter61-prewarm-staleness/03_kb_retrieval_deep_dive.md` §7) / after (file:line + pin) / mic gate table / harness-sim outputs.
3. Commit on the branch:
```
cd /tmp/opencode/wt-iter62 && git add engine/diallux engine/tests && git commit -m "iter62: lane restore — session-transcript single source (kill empty respawn), fail-clean await, honest zero_hit, solar pin alias, harness --rag-fire-sim"
```
4. ASK owner (hitl_ping): "iter62 done: suite <N> passed, mic gate GREEN (no regressions), retrieval un-blinded (zero_hit <N> vs 38), FIND-30 flipped — report at research/surgeon/iter62-lane-restore/01_fix_report.md — merge decision yours".
Dependencies: T9.
Verification: suite green; `git status` clean after commit; report on disk; FIND-30 flipped; ping sent.

## Validation Plan (end-to-end)
1. `tests/test_iter62_lane_restore.py` exists with the 9 named pins; suite = **422 passed, 0 failed**; zero existing test files edited.
2. Chat logic check (no code changes): pin `test_lane_drive_no_llm` proves the fire→consume path; a plain existing `Maria --rag` harness run is EXPECTED to show `degraded=true/zero_hit=true` rag spans on chat (no lane fires there — fail-clean working as decided), documented in the fix report so it is not mistaken for a regression.
3. Mic regression gate (T9) fully GREEN — latency profile and socket behavior byte-stable vs the iter61 call.
4. Retrieval delta: objection-turn spans carry the real utterance; `zero_hit` count drops vs 38/67; `pinned` resolves post-industry.
5. Ledger: FIND-30 flipped with SQL/span evidence; report on disk; owner pinged (STOP POINT).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| FIND-29 calendar seed fix (callback_number on mic transport + gate ordering) | owner parked it ("very simple fix, later") — separate small iteration |
| FIND-31 duplicate log handler, FIND-32 mid-sentence cuts/barge-in opener variance | parked; independent surfaces |
| Pain-amplification KB (owner-drafted content + `kb_registry.json` + cost sign-off) | owner HITL — content does not exist yet |
| `rag_filter_score` / `rag_min_query_chars` tuning | owner calibrated 0.24; no evidence to change |
| Chat-surface lane firing (e.g. a `--rag-fire-sim` harness flag or session-free fire) | owner deferred 2026-09-21 ("no code changes to make this both ways"); chat `--rag` fail-clean behavior documented in the fix report |
| Merge of iter61/iter62, tag, `scripts/git-tree.sh` | owner decision at the STOP POINT (LAW 0) |
| `/voice60` Caddy route commit to `/etc/caddy` git | owner sudo one-liner, harmless, still pending |
