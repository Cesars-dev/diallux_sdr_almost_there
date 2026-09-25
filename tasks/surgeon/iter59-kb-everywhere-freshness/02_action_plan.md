# 02 — ACTION PLAN — iter59 (fix design, based on 01_audit.md)

Design owner note: prompts and prompt files are OWNER-only (HITL). Every fix below is engine-side; where the plan referenced prompt patterns, this action plan only PRODUCES EVIDENCE PACKS for the owner.

---

## T0 — Worktree + branch (mechanical)

```bash
cd /home/julio/projects/clean_diallux_SDR
git branch engine/iter59-kb-everywhere-freshness db8e56f
git worktree add /tmp/opencode/wt-iter59 engine/iter59-kb-everywhere-freshness
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter59/engine/.venv
cp -p /tmp/opencode/wt-iter58/engine/.env /tmp/opencode/wt-iter59/engine/.env   # mode 660, gitignored
```
Baseline: `cd /tmp/opencode/wt-iter59/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → 368 passed.

## T1 — Assessment pack (READ-ONLY; no code changes)

Output: `research/surgeon/iter59-kb-everywhere/01_assessment.md`.

### T1.1 Retell 7.8/7.9 objection-engine extraction (CORRECTED corpus — audit A17/E)
- Use the 12 on-disk V7.8/V7.9 dialogues (list in audit §E). Primary: `NO-BOOK_chat_0f5f1c08496e163200d21d561d9.json` (objection gauntlet), `V7.9_slot_lock_chat_86abc43fff5eb74a44faf5ecd9c.json`, `V7.8_reach_details_chat_797488f65d5db70a2d5f2529f97.json`, plus 3-5 of the BOOK set for contrast.
- Extract per call: every objection turn (user msg + agent answer), whether a KB chunk answered it (`knowledge_base_retrieved_contents_url` + `message_with_tool_calls`), and the rebuttal pattern (acknowledge → reframe → advance).
- OPTIONAL fresh pulls (only if owner wants production-agent data): read-only `GET https://api.retellai.com/v2/list-calls?agent_id=<id>&limit=…` + `GET /v2/get-call/:call_id`; save to `research/transcripts/retell_78_79/`. NEVER PATCH/POST.
- Do NOT use GK_chat_* as "7.8/7.9" (they are V7.0-V7.7); they may be cited separately as objection-corpus background.

### T1.2 Retell production-stack research (Scrapling)
- `/home/julio/projects/scrapling-mcp/.venv/bin/python` + `from scrapling import Fetcher` against docs.retellai.com / retellai.com public pages: their answer→speech latency claims, voice-engine architecture (in-house vs provider), any pre-connect/prewarm behavior documented. Websearch fallback. Findings → assessment md. $0, no key.

### T1.3 Dedupe sweep 0.90 (offline proof)
- Corpus: question sentences extracted from `/tmp/opencode/iter58_gens_raw.txt` + synthesized 1-2-word variant pairs + the legit-rephrase pairs (difflib 0.54-0.57 from the iter58 report) as controls.
- Embed with the local embedder (arctic-m, query prefix — import path via engine `diallux/rag.py` helpers or direct fastembed in the wt-iter58 venv); sweep thresholds 0.80-0.97; produce the table showing 0.90 separates near-verbatim (≥0.95) from legit rephrasings (≤0.6).

### T1.4 Verbosity A/B (CORRECTED — audit F3)
```bash
cd /tmp/opencode/wt-iter58/engine
# ARM 1 (medium — today's default):
set -a && . ./.env && set +a && .venv/bin/python tests/llm2llm/harness.py \
  --personas Maria --rag --langfuse --max-turns 28
# ARM 2 (high — CLEAN high, per-state override cleared):
set -a && . ./.env && set +a && OPENAI_VERBOSITY=high VERBOSITY_STATES_MEDIUM="" \
  .venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 28
```
- Import each run into the ledger (`scripts/live_sql.py import …` with run names `ab-verb-medium` / `ab-verb-high`); grade TTFT + objection-turn quality per SOP; report numbers. Same persona, same seed conditions.

### T1.5 Vertical prompt before/after dump
- From trace `daee4b00…` rag spans + `render_pinned_section` (rag.py:680): dump the rendered pinned-industry block + knowledge delta the model saw at turns 9→11 (the industry-pin resolution moment, turn 10, 12.4 ms) into the assessment md.

**T1 verification:** `01_assessment.md` on disk with SQL/API citations, sweep table, A/B table, 12 dialogues referenced (paths), stack-research findings. **T1 does not touch code.**

## T2 — Owner review (HITL gate — unchanged from plan)

Telegram ping (`scripts/hitl_ping.py`) BEFORE the ask. Owner reads the assessment; approves/denies painification KB; approves Phase B scope; may rewrite prompts. Record GO/NO-GO per fix.

## T3 — RAG freshness (builder.py, session.py, deepgram_stt.py, config.py)

### T3.1 Config
```python
# config.py (new flags; defaults preserve iter58 exactly)
rag_fire_mode: str = "eot"        # "eot" (iter58) | "speech-window" | "round-sync"
rag_live_await_ms: int = 60      # unchanged default; speech-window eval may raise to 150
```

### T3.2 Variant A — `speech-window` (fire at FIRST Update of the turn)
1. `deepgram_stt.py _handle`: add branch `elif event == "Update" and transcript: await self.on_update(transcript)` (new optional callback `on_update=None` in `__init__`; fire-safe try/except like the others). Updates arrive repeatedly during speech — the SESSION decides when to actually fire.
2. `session.py`: new `_on_stt_update(transcript)` — fires `self._fire_live_retrieve(transcript)` ONCE per turn (guard: `self._update_fired_turn is not clock.turn_index`; reset in `_on_eot`/`_on_eager_eot` after the EOT fire). Keep the existing EOT/EagerEOT fires as the fallback when no Update preceded (eager-off, missed updates).
3. Turn-keyed supersede (fixes audit F10 + plan's "keyed by TURN not msg-text"): `spawn_live_retrieve` gains a `seq` param; runtime keeps `self._live_seq: dict[str, int]`; `_consume_live_retrieve` matches on `seq == self._live_seq[state]` (a stale landed task from an earlier turn is ignored → respawn+degrade).
4. Timeout fallback (audit F8): maintain `self._live_consumed[state]` = the last set actually CONSUMED by a round; on await-timeout degrade to `_live_consumed` (never an unconsumed `_live_prev` overwrite). `_live_prev` remains as task-landing stash only.
5. Bounded await stays as safety net (`rag_live_await_ms`); the landed path is zero-await.

### T3.3 Variant B — `round-sync`
`_consume_live_retrieve` short-circuit: `if mode == "round-sync": delta,… = await self._live_retrieve(state, dvs, user_msg, kb_store)` — inline, no await cap; span `mode="live-sync"`. TTFT pays ~123-131 ms (audit A6); per-variant gate (audit F12): sync gate = "TTFT p50 ≤ 980 ms, degraded=0%".

### T3.4 Pins — `tests/test_iter59_rag_freshency.py` (name: `test_iter59_rag_freshness.py`)
- fire-at-first-Update (FakeSTT seq of events: Update → EndOfTurn; assert `spawn_live_retrieve` called at Update, once per turn);
- turn-keyed supersede (same text two turns, dvs changed → round 2 does NOT consume turn-1's landed task);
- landed-fresh preferred over stale-prev; await-timeout → `_live_consumed` fallback;
- `rag_fire_mode="eot"` = byte-iter58 behavior (regression pin);
- `round-sync` path consumes inline.
Conventions: per audit §G (inline `_FakeConn/_FakePool` + `embed_fn=`, `asyncio.run`, no conftest).

**T3 verification:** suite 368 + new pins green; live gate (speech-window): ≥90% `degraded=False`, `await_ms` p50 ≤15 ms. The variant choice is RECORDED IN THE T1/T5 REPORT BEFORE the winning default is committed (owner's decision rule).

## T4 — KB everywhere + dedupe v2 (builder.py, state.py, config.py)

### T4.1 KB everywhere (audit F1/F2 — TWO sites)
1. builder.py:945: `_RETRIEVAL_OFF: set[str] = set()` (keep the attribute — `kb_slugs_for` and tests reference it; empty = kill).
2. builder.py:1535-1536 round gate, live branch only:
   `do_retrieve = bool(scope) if live else (bool(scope) and (bool(refer_tags) or state_name in runtime._RETRIEVAL_ALLOW))`
   → freed states retrieve via lane B (caller utterance over the 9-KB general-union scope; lane A empty — no refer tags; `build_lanes` already handles tag-less states: only Closing has the anchor).
3. Scope pin: freed states resolve to the general-union fallback (`kb_slugs_for` 975-986) = the 9 general_prompt KBs (audit F2). No prompt edits (OWNER territory).
4. Note: `first_turn_lite`/`state_entry_lite` rounds still skip retrieval by design (unchanged).

### T4.2 Dedupe v2 — semantic 0.90, cross-turn question stems
1. Config: `tts_dedupe_semantic: bool = True`, `tts_dedupe_cos_threshold: float = 0.90`, `tts_dedupe_stem_window: int = 12`.
2. state.py: new per-CALL key `question_stem_window: list` (entries `{"text": str, "vec": list}`); seeded empty in `initial_state` (state.py:58 area); **NOT reset at ingest** (builder.py:2247-2258 must not list it — contrast `tts_sentence_window`).
3. builder.py token path (1896-1941), after the existing exact-match check, add:
   - candidate = flushed sentence; `is_question = "?" in sentence` (cheap gate — audit F7);
   - if `is_question and runtime.settings.tts_dedupe_semantic and stem_window_nonempty`: embed the stem ONCE via the runtime's KB store `embed_query` (reused client, rag.py:420; the runtime already holds `_kb_store`), cosine vs every window vec; `cos >= 0.90` → drop from SPOKEN stream (same as exact-dup path); else speak.
   - on speak: append `{"text": stem, "vec": vec}` to `question_stem_window`, cap at 12 (FIFO).
   - non-question sentences NEVER embed (zero added latency for statements); first clause fast-flush path unaffected (fragments without "?" skip the gate).
   - embed failure → fall back to exact-match only (never block speech).
4. Hot-path budget: one arctic embed ≈ 30-60 ms, only on question sentences with a non-empty window; acceptable mid-utterance (post-first-clause). Recorded in the report.
5. Write-back: `updates["question_stem_window"] = window` alongside `tts_sentence_window` (builder.py:2003 area).

### T4.3 Pins — `tests/test_iter59_dedupe_semantic.py`
- 1-2-word variant of an asked question → dropped at 0.90 (fake embedder returning controlled vectors);
- legit rephrase (cos 0.54-0.57 control) → survives;
- cross-turn: window survives ingest (asked turn N, variant dropped turn N+2);
- statements never embed (embed spy count == number of question sentences);
- `tts_dedupe_semantic=False` = iter58 exact surface.
Plus KB-everywhere pins (may live in the same file or the freshness file):
- `kb_slugs_for` non-empty for ALL 9 states incl. contact_details/Booking/VerifyLead/ConfirmSlots (== the 9 general slugs);
- a contact_details round with a caller utterance ≥ `rag_min_query_chars` produces a live retrieval (lane B) and renders a KNOWLEDGE delta.

**T4 verification:** suite green; bug-coverage queries re-run (`lf_quick.py bugs --run <name>`); the 0.70-string pair caught at cosine; 0.65 legit survives (plan's targets, via the sweep controls).

## T5 — Prewarm (app.py + new diallux/media/prewarm.py + config.py)

1. Config: `call_prewarm: bool = False` (default OFF until the live gate passes — flag-off = iter58 surface).
2. New `diallux/media/prewarm.py` — module-level pool:
   - `await prewarm_startup(settings)`: (a) open ONE idle Deepgram flux WS (`websockets.connect(DeepgramSTT._url()-equivalent URL, same headers)`) + start a KeepAlive/maintainer loop (audit F5: flux has none today; send `{"type":"KeepAlive"}` every 5 s — same shape as nova3's; on close → respawn after backoff); (b) open ONE idle Cartesia WS (same URL/headers as `CartesiaTTS.connect`); (c) RAG stage: `await resolve` the KB store singleton + ONE warm embed batch (pre-loads the ONNX session — the ~1.7 s cold-embed cost, session.py:187-189 comment).
   - `async def adopt_stt_ws() -> ws | None` / `adopt_tts_ws() -> ws | None`: pop-and-refill (spawn replacement immediately).
3. `DeepgramSTT.connect(ws=None)` / `CartesiaTTS.connect(ws=None)`: if `ws` given, skip `websockets.connect`, start recv loop with THE OWNING SESSION's callbacks (audit F6 — adoption at WS level).
4. `session.py start()`: `if settings.call_prewarm: stt_ws = await prewarm.adopt_stt_ws(); tts_ws = await prewarm.adopt_tts_ws()` then `DeepgramSTT(...)`/`create_tts(...)` with `connect(ws=…)`. Fallback: pool empty → today's fresh connect (never fail a call on the pool).
5. `app.py`: FastAPI lifespan hook → `prewarm_startup` when `settings.call_prewarm` (audit C5 — app has NO startup hook today). Startup logs: `prewarm: stt connected`, `prewarm: tts connected`, `prewarm: rag staged` (+ timings).
6. Pins — `tests/test_iter59_prewarm.py`: flag off = iter58 surface (no pool calls); flag on with fakes = conns created + adopted + refilled (FakeWS patterns from `test_iter43_prewarm.py`).

**T5 verification:** startup log shows the 3 prewarm lines; suite green; after deploy, a synthetic call's Deepgram connect ≤300 ms (baseline 1.4 s).

## T6 — Owner live call + gates (HITL — unchanged from plan, plus deploy recipe)

Deploy (audit F9 — explicit stop first):
```bash
kill "$(cat /tmp/opencode/voice_8020.pid)" && sleep 2   # iter58 server down
cd /tmp/opencode/wt-iter59/engine && bash scripts/serve_voice.sh
```
Extraction: degraded histogram, contact_details rag rows, dedupe drops, greeting first-audio, prewarm timings; ledger import (`live_sql.py import --window … --run live-iter59-<tag> --commit <sha>`).
Gates (per chosen fire-mode variant — audit F12): fresh ≥90% · await p50 ≤15 ms (speech-window) OR TTFT p50 ≤980 ms (round-sync) · 0 cross-turn near-verbatim re-asks · server answer→speech ≤1.5 s · e2e p50 ≤1100 ms · bookings cancelled (Cal event 3801235 is REAL).

## T7 — Closeout + ASK (audit F11 corrections)

1. `docs/CALL_FACTS.md`: add iter58 row (sid `49fdd9a4cf43`) AND iter59 row; `git add docs/CALL_FACTS.md` (file is currently UNTRACKED — this is its first commit).
2. `plans/PENDING_TASKS.md`: PT-58/PT-59 (iter58 leftovers: contact_details prompt loop → owner; unit-mislabel prompt pattern → owner) + PT-60 (freshness), PT-61 (dedupe v2), PT-62 (KB-everywhere + prewarm follow-ups). Note in the file: PT-57 intentionally unused (like PT-52).
3. `engine/ITERATIONS.md`: iter56/57/58 have NO ledger lines anywhere — add them on the BRANCH closeout per SOP (do not hand-edit on main), together with iter59's line.
4. Docs commit to main (LAW 0): CALL_FACTS.md + untracked `plans/plan_v5_iter58_eot08_public_mic.md` + this surgeon folder's outcome note. Code commits stay on the branch.
5. `scripts/keyhound` before any push. Telegram ping. ASK JULIO: (a) merge `engine/iter59-kb-everywhere-freshness`, (b) keep flores/voice endpoint, (c) painification KB go/no-go, (d) US-East migration as separate session.

## Validation plan (end-to-end)

1. T1 pack on disk, owner-reviewed (T2 GO).
2. T3-T5: suite 368 + ~10-14 new pins green on the branch.
3. T6 live call: all per-variant gates green; trace + ledger imported; bookings cancelled.
4. T7: docs committed, PT rows added, ITERATIONS lines on branch, ASK sent.
