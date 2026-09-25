# PLAN — iter46: latency floor — sub-1s first response by removing the 4 measured taxes

## Meta
- Date: 2026-09-11
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Worktree: `/tmp/opencode/wt-iter44` (branch `engine/iter44-cache-floor`, HEAD `68541f7` +
  uncommitted session telemetry work — suite 242/242, eval 6/6 as left by the iter45 audit session)
- New branch: `engine/iter46-latency-floor` (created from the iter44 worktree's current state,
  uncommitted files carried onto it and committed first as the telemetry baseline)
- Scope: implement P1-P6 + eager-resume grace from the iter45 audit
  (`research/surgeon/iter45-latency-audit/01_report.md`), each behind an independent revertible
  flag, validate suite + eval + battery + 2 live calls, report, ASK JULIO before any merge.
- Target (owner): first response < 1,000 ms; p90 e2e < 1,000 ms. Realistic after this plan:
  turn-1 TTFT ~950-1,000, steady TTFT p50 ~765-800, e2e p50 ~1,050-1,200 — the p90<1,000
  goal additionally needs Deferred D1/D2 (structural cache work) and is NOT promised here.
  NOTE: "first response < 1,000" is verified on TTFT in T8 (owner's ~700 ms memory was TTFT);
  turn-1 e2e realistically lands ~1,100-1,300 (TTFT + gate ~80-100 + STT gap ~150-300) until
  D1/D2 + grace stack on top.
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context (session state as of 2026-09-11, post-audit)

### The owner's goal (verbatim intent)
- Latency is the moat's felt layer: agent must be 1. natural, 2. smart. First response < 1 s,
  p90 < 1 s. iter42's FLOOR (best turns 966-1,127 e2e) was the reference; iter42's p90 (2,935)
  was its defect. iter44 fixed the tail (max 2,025 live) but raised the floor via 4 stacked taxes.
- Owner approved the audit's P1-P6 direction and the grace-window EOT policy ("I like having
  options"). Owner explicitly HELD the local embedder ("until I really understand what we are
  doing") — it is Deferred D3, not a task.

### The audit's four measured taxes (root causes this plan removes)
1. **Verbosity medium** (`config.py:42`, uncommitted owner change): turn-1 lite TTFT 727 (low,
   07:31 live) vs 1,248 (medium, 07:42 live); battery 06:56 low: turn-1 976 / dur p50 1,105 vs
   07:19 medium: 2,115 / 1,528. Steady TTFT p50: 765-766 (low battery) vs 1,019 (medium live).
2. **Drift embed on hot path** (`builder.py:756-830`, iter44 T6c, `rag_drift_requery=True`):
   every same-state round with user_msg ≥ 12 chars (`rag_min_query_chars`) awaits `embed_q(query)`
   — measured 234-272 ms round-trip (07:42 log, eager-start→embed-200); 105 drift spans / 13
   battery calls. First drift check of a visit can pay TWO serial embeds (base is lazy,
   `builder.py:777-779`). NOTE: vector SEARCH itself is p50 6.4 ms local pgvector — the cost
   is the embeddings API round-trip, not retrieval.
3. **Turn-1 prewarm shape mismatch**: greeting warm (`session.py:194-197`) sends FULL Intake
   (tools first, correct initial dvs, staged RAG) — turn-1 lite sends
   `[general_prompt + VOICE_OUTPUT_RULES]`, no tools → diverges at byte 0 → `cache_read=0` every
   first turn (proven live 07:31 + 07:42, battery 06:56/07:19 in=1,711/1,692 cache=0).
   CAUSE (owner asked "why was this off"): prewarm (iter43 T3) was written for the full Intake
   shape; lite became turn-1 default (iter44) without re-auditing the warm path; tests run
   hermetically at `first_turn_lite=False` so the interaction was invisible to suite/battery.
4. **Transition prewarm loses the human race + tail mismatch**: transition warm fires after
   `executor.execute()` returns (`builder.py:~1089`) with `dvs=None` → tail bytes (`_state_block({})`)
   can never match the entry round's frozen state-block (post-transition dvs) — caps transition
   cache at tools+head even when the warm completes in time. Full prefill ~1-2 s; fast callers
   arrive first → entry rounds cache=0 (TTFT 855-1,138, outliers 1,900-2,115) vs cache=3,712 when
   warm wins (695-853, n=6). Closing entries cache=0 in 3/3 telemetry runs. RAG staging is a
   SEPARATE bg task (embed+retrieve at transition) — the entry embed only bites when BOTH miss.
   (The GREETING warm already passes initial dvs correctly — `session.py:194-197`; the `dvs=None`
   bug is the TRANSITION warm site only.)

### Cache semantics (pinned so no re-litigating)
- Request layout: `[tools ~688 tok][state head ~2,000][frozen state-block + RAG tail][history][delta?]`.
  OpenAI cache is a strict byte-prefix KV cache — reuse requires byte-identity from token 0.
- Floors measured: iter42 live 2,688 pinned (tail-after-history); iter44 live 2,688 pinned
  (state-block re-frozen per TURN, dvs churn); iter44 battery climbs 2,688→3,712→4,736 within
  state (tail-before-history + append-only working).
- Cache ≈ 100-250 ms TTFT benefit at 3-5k payloads (Closing cache=0 rounds still ran 696-765 ms)
  — SAME-STATE delta only; transitions stack 3 costs (cold 4.5-5.2k prefill + entry embed +
  queue) → ~500 ms typical, see T4's measured basis. Cache's real value: killing the
  976-2,115 ms cold tail + 10x cheaper billing. Cache NEVER adds latency; re-billed tokens do.
- TTFT floor at verbosity=low: 666-766 ms (n=40+, battery_gens.json) — the "700 ms" recipe.

### EOT / eager mechanics (pinned)
- Deepgram flux: `EagerEndOfTurn` (threshold 0.6, .env `DEEPGRAM_EAGER_EOT_THRESHOLD`) → engine
  starts the LLM speculatively; `EndOfTurn` (threshold 0.7) adopts it. `TurnResumed` → instant
  cancel + rerun today (no grace) — resumed turns cost a full TTFT restart (live turns
  8/10/11: e2e 1,460-2,025; resumed_count up to 3). head_start_ms measured 0-1,040 ms (free
  when it hits). `eager_final_match` telemetry already logs transcript equality at adoption.
- Owner rejected "ONE blob" (drop eager, wait for final EOT): that adds the full EOT-detection
  wait to EVERY turn to avoid a false start that costs only affected turns.
- Owner accepted the grace-window policy: hold the cancel, re-evaluate, measure on real calls.
  Speaker pace differs per human — the grace window IS the pace adaptation v1; learned
  per-caller thresholds are iter47+.

### Metric semantics (comparable across iter42/43/44 — do not "fix" the anchor)
- `stt_eot_to_llm_first_ms` is EagerEOT-anchored (`mark_user_end()` in `_on_eager_eot` both
  builds: iter42 `session.py:292`, iter44 `session.py:335`) and includes the sentence-gate's
  first-sentence completion; `ttft_ms` (Langfuse usage_details + `round usage` log line) is
  `t0`(pre-astream)→first token, excludes RAG. `head_start_ms` = EagerEOT→EndOfTurn.
- felt latency ≈ `e2e_response_ms − head_start_ms`.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Implement P1-P6 + grace as independently flag-gated changes on ONE branch `engine/iter46-latency-floor` | Each has its own config flag + revert; battery validates the stack; one plan = one session per SOP |
| `openai_verbosity` default → `"low"` (revert the uncommitted owner change) | Three matched pairs measured; battery quality gates (12/13, eval 6/6) all ran at low |
| Drift check goes ASYNC (bg embed, apply-next-round via `rag_append_delta`), base vec materialized at state entry when available | Removes 234-272 ms/turn hot-path embed; correctness lag ≤ 1 round, strictly better than pre-T6c (never re-anchored); append-only plumbing already exists |
| Greeting fires TWO byte-exact warms: lite shape (for turn 1) + full Intake (for turn 2+) | Turn 1 is the metric that matters most; each warm is a 16-token-capped POST; cheap |
| `_warm()` gains a dvs parameter; transition warm passes post-patch dvs | Kills the tail-byte mismatch that caps transition cache at tools+head |
| State entry bounded-awaits an in-flight warm: `asyncio.wait_for(asyncio.shield(task), timeout=prewarm_entry_wait_ms=100 ms)`; fire-at-detection (T4a) is the PRIMARY transition fix, the await is the safety net | Warm entry 695-853 (n=6) vs cold 855-1,138 (n=4) + entry embed 234-272 → transition tax ~500 ms typical when everything misses; cap bounds only the ADDED wait; full await REJECTED (would serialize the turn) |
| Sentence gate fast-first-flush: when nothing spoken this turn, flush on first `,` or ≥28 chars | iter42's gate p50 was 113 ms (low verbosity); medium pushed it to 160-250; flag `tts_gate_fast_first_flush` |
| Mic chunk 1,600 → 800 samples (100→50 ms) at `diallux/static/mic/index.html:71` | Upstream trim 40-60 ms; engine untouched |
| Eager resume grace `eager_resume_grace_ms` DEFAULT 0 (off), live A/B at 200 | New behavior (adopt-after-resume) must be measured before defaulting; `eager_final_match` is the adoption guard |
| Local embedder HELD (owner) | Deferred D3 with full spec; no `pip install fastembed` in this iteration |
| Shared-prefix reorder + state-block per-visit freeze NOT in this iteration | Prompt-architecture changes need owner sign-off (plan BLOCKED items from iter45); spec'd in Deferred D1/D2 |
| Suite + eval + battery gates BEFORE any live call; live calls ONLY on :8007/:8008 pattern with append-mode logs | AGENTS.md LAW 0 + iter45 lesson (never `>` truncating logs) |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner OK to commit the iter44 uncommitted telemetry work as the iter46 baseline commit | ASK at plan approval (T0) |
| Whether `eager_resume_grace_ms=200` becomes default after A/B | Owner decision after T8 live calls |
| D1 shared-prefix reorder / D2 state-block per-visit freeze — go/no-go for iter47 | Owner decision at end of iter46 |
| D3 local embedder model choice + calibration set | Owner un-holds it; calibration data = 105 drift spans + battery transcripts (paths in D3) |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter44/.venv/bin/python` (3.12). No NEW dependencies in this plan.
- Langfuse: self-hosted `:3001` (docker), SDK 4.15.1; env via `set -a; . /tmp/opencode/wt-iter44/.env; set +a`
  (contains `LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`, `OPENAI_MODEL=gpt-5.4`, `CARTESIA_SPEED=1.12`,
  `DEEPGRAM_EAGER_EOT=true`, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.6`; NO `OPENAI_VERBOSITY` line —
  verbosity comes from the code default being reverted in T1).
- Model: gpt-5.4, `openai_reasoning_effort="none"`, `openai_verbosity` low (T1).
- Postgres 5434 (RAG pgvector) read-only for tests.
- Ports: engine test servers :8007 (iter44, PID 3152652, append log
  `/tmp/opencode/uvicorn_8007_iter44.log`) and :8008 (iter42, PID 3166619). NEVER touch
  :8000-:8006 (live infra + julio's tunnel), live Retell agent IDs (`agent_f305…`,
  `agent_1698…`, `agent_87e4…`), `slots.db`, Cal.com event 3801235.
- Evidence inputs (read-only): `research/surgeon/iter45-latency-audit/01_report.md`,
  `iter45_live_calls.json`, `turn_tables.json`, `battery_gens.json`;
  `/tmp/opencode/uvicorn_8007_iter44.log`; `/tmp/opencode/uvicorn_8007_iter42.log`.

## Architecture (one block)
```
browser mic (800-sample chunks, T6) ─► Deepgram flux ──EagerEOT──► grace window (T7)
                                        │                            ├─ EndOfTurn in grace → verify eager_final_match → adopt (FREE)
                                        │                            └─ grace expires → cancel+rerun (today)
                                        └─ EndOfTurn ─► state_node:
                                            [lite? turn1] ─ greeting warms (T3): lite-shape + full-Intake (bg, byte-exact)
                                            [RAG lane]  ─ frozen chunks; drift embed ASYNC (T2), base vec at entry,
                                                          delta appends next round (rag_append_delta)
                                            [entry]     ─ bounded-await in-flight warm ≤100 ms (T4c) → cache 3,712
                                            [LLM]       ─ verbosity=low (T1) → TTFT ~700
                                            [gate]      ─ fast first flush on "," / ≥28 chars (T5)
                                            [TTS]       ─ Cartesia (unchanged, TTFB ~80 ms)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter44/diallux/config.py` | `openai_verbosity: str = "low"` (revert line 42); NEW flags: `tts_gate_fast_first_flush: bool = True`, `tts_gate_fast_first_flush_chars: int = 28`, `rag_drift_async: bool = True`, `prewarm_entry_wait_ms: int = 100` (MILLISECONDS — divide by 1000 for `asyncio.wait_for`, which takes seconds), `eager_resume_grace_ms: int = 0` (off until A/B) | edit |
| `/tmp/opencode/wt-iter44/diallux/graph/llm.py` | `astream` already accumulates `tool_call_chunks` (`llm.py:227-236`) but only yields the names in the `final` event — add an early `LLMEvent({"type":"tool_call_start", "name": ...})` the FIRST time a given index's name completes, so T4a can fire the warm at name detection (verify: names arrive in chunks BEFORE arguments finish streaming; `tc.get("name")` accumulates in name-fragments — emit when the next chunk has a new id/args or at first non-empty join) | edit |
| `/tmp/opencode/wt-iter44/diallux/graph/builder.py` | (a) `_warm(..., dvs=None, lite=False)` — lite renders `_lite_head()` messages with NO tools; (b) transition warm call passes post-patch dvs; (c) drift branch: base vec at entry when available (`_frozen_query_vec` from staged vec or set at sync entry), round drift embed+cosine+retrieve moved into a bg task, round uses frozen chunks, `rag:drift` span emitted from the bg task, delta lands via existing `rag_append_delta` path next round; (d) state entry: if a warm task exists for this state, `asyncio.wait_for` bounded await before consuming staging (timeout in SECONDS: `prewarm_entry_wait_ms/1000`); (e) fast-first-flush in the sentence loop (flush on first `,` or `tts_gate_fast_first_flush_chars` when `not spoken_any` this turn); (f) T4a hook: on `tool_call_delta` event whose name matches `transition_to_*`, fire `warm_prompt_cache(dest_state, history_snapshot, dvs_snapshot)` immediately (latch de-dupes vs the post-execute fallback) | edit |
| `/tmp/opencode/wt-iter44/diallux/media/session.py` | (a) `_on_turn_resumed`: when `eager_resume_grace_ms > 0`, delay the cancel by the grace; if `EndOfTurn` arrives within the grace → ADOPT ONLY IF `eager_transcript == final transcript` (NEW GUARD — see T7 session.py audit note: today's adopt path at `session.py:280-305` logs `eager_final_match` but adopts UNCONDITIONALLY, safe today only because resume always cancels first; with a grace window an unconditional adopt would answer a stale transcript); transcript mismatch or grace expiry → cancel+rerun as today; a second `TurnResumed` inside the grace cancels immediately; (b) `start()`: fire the lite-shape warm IN ADDITION to the full-Intake warm | edit |
| `/tmp/opencode/wt-iter44/diallux/static/mic/index.html` | line 71 `new Int16Array(1600)` → `new Int16Array(800)` (100→50 ms chunks @16 kHz) | edit |
| `/tmp/opencode/wt-iter44/tests/test_iter46_latency_floor.py` | flag-gated unit tests (see T7 verification) | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter46-latency-floor/01_report.md` | iteration report (suite/eval/battery/live numbers vs audit baseline) | NEW |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | ledger line appended after owner-approved merge only | edit (post-ASK) |

## Deploy Rules
- All work on branch `engine/iter46-latency-floor` in `/tmp/opencode/wt-iter44`. Commits on the
  branch only. NO merge to main, NO tag, NO `scripts/git-tree.sh` without Julio's explicit say-so.
- Test server relaunch (NEVER `>`, always `>>`; always with `.env` sourced):
  ```bash
  cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && \
    setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8007 \
    >> /tmp/opencode/uvicorn_8007_iter44.log 2>&1 < /dev/null & disown
  ```
- After every battery: cancel ALL test bookings (Cal.com event 3801235 is REAL).
- NEVER: touch :8000-:8006, live agent IDs, `slots.db`, Langfuse server itself, `git push` without keyhound.

## Tasks (in order)

### T0 — Branch + baseline commit
Goal: carry the iter44 uncommitted telemetry work onto the new branch as commit 1.
Files: none new (git ops only).
Commands:
```bash
cd /tmp/opencode/wt-iter44 && git status --short && \
  git checkout -b engine/iter46-latency-floor && \
  git add diallux/config.py diallux/graph/builder.py diallux/media/session.py \
          diallux/observability/tracer.py diallux/rag.py tests/fake_llm.py \
          tests/test_first_turn_lite.py scripts/eval_accuracy.py eval/report.json eval/llm2llm_report.json && \
  git commit -m "iter46 baseline: carry iter44 telemetry work (TTFT usage_details, append-only delta, lite default ON, mic heartbeat)" && \
  git log --oneline -3
```
Dependencies: Julio's OK (BLOCKED table row 1).
Verification: `git log --oneline -2` shows the baseline commit on `engine/iter46-latency-floor`; `git status` clean except intended files.

### T1 — Verbosity low (P1)
Goal: revert `openai_verbosity` default to `"low"` in `config.py:42` (comment: "gpt-5.2 output length control (audit P1: 727→1,248 ms turn-1 measured)").
Files: `diallux/config.py`.
Commands: edit + suite.
Dependencies: T0.
Verification: `grep -n 'openai_verbosity' diallux/config.py` shows `"low"`; suite green (T7).

### T2 — Drift lane async + base-at-entry (P2)
Goal: no sync `await embed_q(...)` inside `state_node` on the round path.
Implementation spec (builder.py:756-830):
- At state entry (both staged and sync-fetch paths), when chunks freeze: keep
  `_frozen_query_vec = staged.get("vec")` when available; else leave None (lazy fallback kept,
  but now computed inside the BG task, never on the round path).
- Drift branch becomes: spawn `asyncio.create_task(self._drift_check(state_name, query, user_msg))`
  which embeds base (if None) + round query, computes cosine, on drift runs `kb_store.retrieve`
  and appends NEW chunks to `_rag_delta_chunks` (existing `rag_append_delta` semantics); emits
  the `rag:drift` span from inside the task. The round itself uses `runtime._frozen_chunks`
  unconditionally (zero awaits). Serialize drift tasks per state (a simple `self._drift_task`
  handle; cancel-supersede on a newer query).
- Add `_drift_inflight` guard so two bg tasks never append the same delta twice.
Files: `diallux/graph/builder.py`, `diallux/config.py` (flag `rag_drift_async=True`).
Commands: edit; `grep -n "await embed_q" diallux/graph/builder.py` must return ZERO hits on the
round path after the change (embeds only inside `_drift_check`).
Dependencies: T0. Flag OFF → exact today behavior.
Verification: unit test (T7); battery shows `rag:drift` spans still present; drift deltas still
land (grep `delta_chunks>0` in spans).

### T3 — Greeting warm covers the lite shape (P3)
Goal: turn 1 rides a cached prefix.
Implementation spec:
- `warm_prompt_cache(state_name, history=None, dvs=None, lite=False)`; `_warm` renders the lite
  payload when `lite=True`: `messages=[{"role":"system","content": self._lite_head()}] +
  history` where history = the INITIAL history (the greeting assistant message from
  `initial_state`, `state.py:58` — history[0]) — the turn-1 hot payload is
  `[lite system][greeting assistant msg]` via `_build_messages`, and the warm must byte-match
  INCLUDING that history message. `tools=[]`, NO tail.
- Full warm call (greeting, `session.py:194-197`) already passes initial dvs — unchanged.
- `session.start()`: after the existing full-Intake warm call, add
  `self.runtime.warm_prompt_cache(self._turn_state, self._initial_payload.get("history") or [],
  None, lite=True)`.
- Transition warm call site passes the post-patch dvs: `runtime.warm_prompt_cache(new_state,
  list(history) + list(new_history), {**dvs, **dvs_patch})` (dvs_patch is in scope where the
  warm currently fires — builder.py:~1089).
Files: `diallux/graph/builder.py`, `diallux/media/session.py`.
Dependencies: T0.
Verification: unit test (T7) asserts lite warm payload == turn-1 hot payload bytes (compose both
through the same `_build_messages` and compare `messages` INCLUDING the greeting history
message); live: turn-1 `cache_read > 0` in `round usage`.

### T4 — Transition prewarm: fire at tool detection + bounded await at entry (P4)
Goal: entry rounds stop paying cold prefill + entry embed on fast replies.
Implementation spec:
- (a) FIRE EARLIER: warm the destination state the moment a `transition_to_*` tool call is
  detected in the streaming tool-call deltas (tool name encodes the destination) — NOT after
  `executor.execute()` returns. This banks the remaining speaking round + TTS drain (~0.5-1.5 s)
  as warm-prefill head start. The existing post-execute warm call stays as fallback (latch makes
  the second call a no-op).
- (b) DVS FIX: the warm passes the post-patch dvs (`{**dvs, **dvs_patch}`) so `_state_block`
  bytes match the entry round's frozen tail — removes the mismatch that capped transition cache
  at tools+head.
- (c) BOUNDED AWAIT: in `state_node`, right before consuming `_rag_staging` / building messages:
  if a warm task exists for this state, `await asyncio.wait_for(asyncio.shield(task),
  timeout=self.settings.prewarm_entry_wait_ms)` in try/except TimeoutError (shield keeps the
  warm running for the NEXT round even on timeout).
- MEASURED BASIS (corrected 2026-09-11 after owner push-back on the ~250 ms claim): warm entry
  TTFT 695-853 (n=6) vs cold entry 855-1,138 (n=4, outliers 1,900-2,115) + entry embed
  234-272 ms when staging missed → the transition tax is ~500 ms typical when everything
  misses (cold 4.5-5.2k prefill + embed + queue variance), NOT the ~100-250 ms same-state
  cache delta. The cap only bounds the ADDED wait; the real transition fix is (a)+(b).
Files: `diallux/graph/builder.py`, `diallux/config.py`.
Dependencies: T3 (shares the warm plumbing).
Verification: unit test (T7); live: entry rounds show `cache_read ≥ 2,688` even on fast replies.

### T5 — Sentence-gate fast first flush (P5)
Goal: first audio earlier at any verbosity.
Implementation spec (builder.py sentence loop, ~947-976): when `not spoken_any` (nothing spoken
this turn yet) and `settings.tts_gate_fast_first_flush`: flush `pending_tokens` when
`_SENTENCE_SPLIT_RE` matches OR `len(pending_text) >= settings.tts_gate_fast_first_flush_chars`
OR the text contains `,` after ≥12 chars. The flushed fragment is added to the dedupe window
exactly like a sentence (dedupe integrity preserved).
Files: `diallux/graph/builder.py`, `diallux/config.py`.
Dependencies: T0. Flag OFF → exact today behavior.
Verification: unit test (T7): first tts_token write happens at the comma/char threshold with the
flag on; at flag off, unchanged.

### T6 — Mic chunk 100→50 ms (P6)
Goal: upstream trim.
Files: `diallux/static/mic/index.html` line 71.
Commands: edit `new Int16Array(${1600})` → `new Int16Array(${800})`.
Dependencies: T0.
Verification: grep shows 800; browser page reloads and `mic audio flowing` heartbeat still logs
(100 chunks now every ~5 s instead of ~10 s).

### T7 — Tests (unit) — `tests/test_iter46_latency_floor.py`
Goal: hermetic proof for every flag, in the existing test style (FakeLLM, settings overrides).
Cases:
1. verbosity default is `"low"`.
2. lite warm payload byte-equals the turn-1 hot payload (compose via `_build_messages` on both
   paths, compare `messages`).
3. transition warm tail contains the post-patch dvs line (e.g. a dvs key written by the
   transitioning tool appears in the warm's tail message).
4. `rag_drift_async=True`: a same-state round with a fresh user message performs ZERO awaited
   embeds on the round path (FakeKBStore counts embed calls and the round completes without
   calling it); with flag OFF the old sync behavior runs.
5. fast-first-flush: first `tts_token` emitted at the `,`/char threshold with flag on; sentence
   boundary only with flag off.
6. grace window: FakeSTT fires TurnResumed then EndOfTurn 120 ms later with EQUAL transcript →
   round adopted, no rerun, `eager_final_match: true`; same sequence with a LONGER final
   transcript → cancel+rerun (the stale-transcript guard); grace=0 → cancel+rerun (today).
7. adopt guard (standalone): with grace enabled, `_on_eot` adopting a running eager round whose
   `eager_transcript != transcript` MUST cancel+rerun — proves the new guard covers the
   previously-unconditional adopt path (`session.py:280-305`).
Commands:
```bash
cd /tmp/opencode/wt-iter44 && .venv/bin/python -m pytest tests -q
```
Dependencies: T1-T6.
Verification: suite green, expected count = 242 + new tests (report the number).

### T8 — Battery + eval + live validation
Goal: prove the stack on the quality gates and on real mic calls.
Commands:
```bash
cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && \
  .venv/bin/python tests/llm2llm/harness.py --personas Maria,Danny,Susan,Marcus,Carlos,Pedro,Sofia,Jorge,Daniel,Brenda,Gene,Frank,Ray --rag --langfuse --max-turns 48 && \
  .venv/bin/python scripts/lf_eval.py ladder && \
  .venv/bin/python -m pytest tests -q
```
Then: restart :8007 (Deploy Rules pattern), run 2 live mic-bridge calls (owner drives the
browser; agent measures from `/tmp/opencode/uvicorn_8007_iter44.log` `round usage` + `turn N
report` lines + Langfuse `micbridge-*` traces).
Second live call: owner sets `EAGER_RESUME_GRACE_MS=200` at relaunch for the grace A/B.
Dependencies: T1-T7 all green.
Verification:
- eval ladder 6/6 PASS; battery first-13 extraction success ≥ 12/13 (today's level).
- Battery TTFT telemetry: steady cached TTFT p50 ≤ 850 ms; turn-1 lite cache_read > 0 in ≥ 2 runs.
- Live turn-1: TTFT ≤ 1,000 ms and `cache_read > 0` (lite warm landed).
- Live steady: TTFT p50 ≤ 850; `stt_eot_to_llm_first − ttft` gap ≤ 200 ms (basis: the gap is
  graph hop + RAG lane + sentence-gate first-sentence completion; iter42's live floor had
  823-1,005 stt→first with ~650-700 TTFT ⇒ gap floor ~150-300 ms; iter44 live gaps ran
  93-921 ms; T2 removes the embed (234-272), so ≤ 200 ms is the honest target, 120 was
  over-tight).
- Grace A/B call: `resumed_count` turns show adopt-without-rerun when EndOfTurn lands in grace
  (`eager_final_match: true`, no duplicate `round usage` for the same turn index).
- Report actuals honestly; if any target misses, the report states which flag underdelivered.

### T9 — Report + ASK
Goal: `research/surgeon/iter46-latency-floor/01_report.md` — per-task diffs, before/after tables
(audit baseline vs iter46 measured), flag states, revert instructions per flag, and the ASK:
(1) merge? (2) grace default 200? (3) D1/D2 into iter47? (4) un-hold D3?
Dependencies: T8.

## Validation Plan (end-to-end)
1. T0: branch exists, baseline commit clean.
2. T7: suite green with the new flag tests; every flag independently revertible (documented in
   the report's revert table).
3. T8: eval 6/6; battery ≥ 12/13; TTFT telemetry present on all battery runs.
4. T8 live: turn-1 cache_read > 0 AND TTFT ≤ 1,000 ms; steady gap ≤ 200 ms; no quality
   regression in the two live transcripts (read them per the 3-SOP checklist before ASK).
5. NO merge, NO push, NO live-agent changes without Julio's explicit say-so.

## Deferred / Not In This Plan
| Item | Why | Spec (ready to lift into iter47) |
|---|---|---|
| D1 — Shared-prefix prompt reorder | Prompt-architecture change, owner sign-off required (iter45 BLOCKED item) | Make `[general_prompt + VOICE_OUTPUT_RULES]` messages[0] for EVERY shape (lite AND full states; tools second, state head third, tail fourth). Turn 1 keeps full tools + SPEECH-ONLY directive (reuse the iter43 forced-speech mechanism). Then ONE warm covers turn 1 + turn 2 + transitions; lite flag can retire. Owner's Q2b instinct ("round 1 + round 2 = one cache") — this is its implementation. |
| D2 — State-block freeze per state VISIT | Behavioral change (model reads dvs via history tool messages instead of the tail), owner sign-off | Freeze `_state_block` bytes at state entry (like `_frozen_rag_tail`); dvs updates reach the model through history tool messages (they already do). Kills the per-turn divergence that pins cache at 2,688 in live. |
| D3 — Local embedder for the drift lane | Owner HELD it | **Effort: ~4-8 h, one session** (integration 1-2 h: `pip install fastembed`, ONNX bge-small-en-v1.5 ~90 MB, ~10-20 ms/query CPU, lazy-load, no API call; calibration 2-3 h: replay the 105 drift spans + battery transcripts, label each (old,new) query pair with the API model's drift outcome as ground truth, fit the threshold — target ≥ 95% agreement; tests 1 h; battery spot-check 30 min). Scope: drift-check ONLY — embed base + round query with the SAME local model so the cosine is internally consistent; pgvector chunk vectors stay on text-embedding-3-small (no KB migration). NO training involved. |
| D4 — Per-caller learned EOT pacing | Needs call data volume | Track per-call inter-phrase pause distribution from STT events; adapt grace window within a call; revisit after ≥ 20 live calls with grace telemetry. |
| D5 — Per-state verbosity (medium on Closer/Offer) | Only if owner finds low too terse after T8 live calls | `verbosity` is a per-request `model_kwargs` entry; map state → verbosity in `CallRuntime`. |
| D6 — Cold-entry fail-soft (owner proposal, 2026-09-11): when the transition warm misses, send a PREFIX-TRUNCATED payload instead of the full one | GATED on D1 (needs prefix-compatible ordering — with today's layout a light payload is a third cache shape and busts the prefix at byte 0; tools must also stay for the state machine) | Layout under D1: `[general+VOICE][tools][state head][dvs tail][RAG tail][history]`. Fail-soft = drop the RAG TAIL ONLY: `[general+VOICE][tools][state head][dvs tail][history]`. Properties: byte-prefix of the full layout → still seeds ~3.7k cached tokens for the next full round; tools/history/dvs intact (flow + smartness preserved); saves the RAG-tail prefill (~100-200 ms). Guard: skip fail-soft when RAG staging already landed (staged chunks cost 0 ms embed anyway) — staging and prompt-warm are independent bg tasks. |

## Appendix — HYPOTHESES: what can go wrong, how we'll know, and the pre-agreed fix
*(Written 2026-09-11 from audit data only — every fallback is a flag flip or a pre-spec'd
variant, decided NOW so a failing task never triggers improvisation mid-session.)*

| # | Hypothesis (what we're betting) | Failure signature (how we detect it) | Pre-agreed fix (in priority order) |
|---|---|---|---|
| H1 | verbosity=low keeps sales quality | Battery extraction success < 12/13, or owner listen-test on the 2 live calls says "too terse" | (1) D5 per-state verbosity (medium on Closer/Offer only); (2) revert `openai_verbosity` flag — one line, iter44-medium behavior restored exactly |
| H2 | Async drift (next-round delta) never leaves the model answering on stale knowledge in a way that hurts | Battery: curvebrenda/curvegene/gkboris (industry-chunk personas) drop vs the 11/13 baseline; live: a product question right after a topic switch gets a generic answer once | (1) Hybrid gate: sync embed ONLY when `user_msg` is ≥ 40 chars (substantive) — filler/short answers keep async; (2) move the drift embed into the EagerEOT window (transcript already in hand ~300-1,000 ms before EOT — free AND same-round); (3) revert `rag_drift_async=False` (exact today) |
| H2b | Drift bg task races the next round (delta appended after it was consumed) | `rag:drift` span timestamped AFTER the next round's `round usage` line with `delta_chunks>0` that never rendered | Serialize per state: one `_drift_task` handle per state, cancel-supersede (already in T2 spec); worst case the delta lands one round later — acceptable by design |
| H3 | Lite warm payload ≠ turn-1 hot payload (ordering/separator drift) → turn-1 `cache_read` stays 0 | Live turn-1 `cache_read == 0` after T3 | (1) T7's byte-compare test already composes both paths — diff the two payloads with a debug dump flag and fix the ordering; (2) ultimate fallback: retire lite, send turn 1 as full shape + SPEECH-ONLY directive (iter43 mechanism) — costs ~300-500 ms on turn 1 but the warm is then guaranteed to cover it |
| H4 | Bounded await adds 100 ms without buying a cache hit (warm hung/slow) | Entry `cache_read == 0` AND `stt_eot→llm_first − ttft` gap grows by ~the cap | Set `prewarm_entry_wait_ms=0` (flag off) — exact today behavior; investigate the hung warm separately (it would also show as a stuck `_warm_tasks` entry) || H5 | Grace window adopts a round whose transcript is stale (caller appended words after EagerEOT) | `eager_final_match: false` on an adopted turn; live transcript shows the agent answering an incomplete utterance | (1) Grace stays DEFAULT 0 until T8 proves it; (2) adoption guard is already `eager_final_match` — mismatch → cancel+rerun (existing path); (3) D4 learned pacing later |
| H6 | Fast-first-flush hurts prosody or collides with dedupe | Live transcript: clipped first clause, or a later sentence audibly missing | Dedupe is exact-match on normalized fragments, so a later FULL sentence can never be dropped by an earlier fragment flush (different bytes) — prosody risk only; fallback `tts_gate_fast_first_flush=False` |
| H7 | 800-sample mic chunks overload the bridge | Heartbeat stutters, audio gaps in live call | Revert to 1600 (one number); bandwidth delta is 32→64 KB/s — negligible in practice |
| H8 | Whole stack still misses p90 < 1,000 ms | T8 live p90 > 1,000 with all flags on | Expected per plan: the residual tail is the structural cache floor → D1 (shared-prefix reorder) + D2 (state-block per-visit) are the pre-spec'd iter47 fix; iter46's honest claim is floor/median, not p90 |
| H9 | Battery quality drops from the STACK (not one flag) | Battery < 12/13 with all flags on | Bisect by flag: run battery with each flag individually OFF (5 quick runs, ~10 min each) — the audit baseline run (all flags off) already exists as the control |

**Escalation rule:** any H detected at T8 → apply its fix-1; if fix-1 also fails at re-run,
apply fix-2; if fix-2 fails, flag OFF and the report documents it. No new mechanisms invented
during the session.
