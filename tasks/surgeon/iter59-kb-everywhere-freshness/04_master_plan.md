# 04 — MASTER PLAN — iter59: KB-everywhere · RAG freshness · semantic dedupe 0.90 · prewarm

- Status: **AIRTIGHT — ready for execution. STOPPED HERE per owner instruction (no execution yet).**
- Supersedes: `plans/plan_v5_iter59_assess_rag_rebalance.md` (source archived at `tasks/surgeon/iter59-kb-everywhere-freshness/archive/`).
- Built via: 01_audit (all claims traced to code @ `db8e56f`) → 02_action_plan → 03_cross_reference → preflight (4 open items verified against code/venv; 1 new subtlety found and resolved, see C8).
- Execution gate: **owner GO after T2** (the plan's own HITL structure: Phase A read-only → owner review → Phase B code).

---

## 0. CORRECTIONS APPLIED vs the original plan (audit-verified; do not re-litigate)

| # | Original plan said | Corrected to (verified) |
|---|---|---|
| C1 | T1 grep for `GK_chat_*` as 7.8/7.9 payloads | GK files are V7.0-V7.7. Use the **12 on-disk V7.8/V7.9 dialogues** (§T1.1). No production-agent V7.9 exists on disk — fresh pull optional, read-only. |
| C2 | "kill `_RETRIEVAL_OFF`" (one site) | **Two sites**: `_RETRIEVAL_OFF` (builder.py:945) AND the round gate `do_retrieve` (builder.py:1535-6, requires refer_tags or allow-list — tag-less states stay blind without this). |
| C3 | A/B: `OPENAI_VERBOSITY=high` only | High arm must ALSO set `VERBOSITY_STATES_MEDIUM=""` (else Closer/Offer/contact_details/ConfirmSlots stay medium — confounded A/B). |
| C4 | Timeout fallback = `_frozen_chunks` | `_frozen_chunks` is never maintained under live mode. Fallback = **`_live_consumed[state]`** (last CONSUMED fresh set — the intent "never stale-prev", implementable). |
| C5 | "moved to first-final-transcript" | Flux STT **drops `Update` events today** (deepgram_stt.py:189). Requires a new handler + `on_update` callback + session wiring (3 files). |
| C6 | `voice-ai-capabilities` only Intake/Discovery | Also on **Offer** (builder.py:963). Documentation-only fix (evidence pack). |
| C7 | e2e ≤1100 gate for both variants | round-sync pays ~123-131 ms inline → **per-variant gates** (speech-window: await p50 ≤15 ms; round-sync: TTFT p50 ≤980 ms). Variant decision recorded in the T1/T5 report BEFORE the winning default commits. |
| C8 | (implicit) Update-fire keyed per turn | Clocks swap at EOT/EagerEOT, NOT StartOfTurn (session.py:349-356/390-400) — keying on `clock.turn_index` is WRONG mid-speech. Use a **boolean `self._update_fired`**, cleared at EOT/EagerEOT. |
| C9 | Deploy: "iter59 restarts :8020" | `serve_voice.sh` REFUSES a busy port — explicit `kill $(cat /tmp/opencode/voice_8020.pid)` first. |
| C10 | PT-58/59 + PT-60/61/62 | Kept; PT-57 left unused deliberately (precedent PT-52) — stated in PENDING_TASKS. |

Pinned numbers (verified this session — cite as-is): 23/24 degraded · await p50 60.8 ms · 1 fresh (await 0) · bg ms p50 123.2 (ledger) · TTFT p50 845 / e2e p50 1143 · rag rows stop 06:57:20, zero contact_details · suite 368 · turns 38 (ledger; report says 39 — turn_index vs count).

## 1. Fixed context (fresh-agent readable)

- **The bug**: `_fire_live_retrieve` (session.py:358) fires at `_on_eot`:355 / `_on_eager_eot`:399 — the same tick `_run_turn` is spawned (356/400). The retrieval task starts at consume time; the 60 ms bounded await (config.py:254) can never cover a ~123 ms task → 23/24 rounds degraded to the previous turn's chunks.
- **KB-blind states**: `_RETRIEVAL_OFF = {"Booking","VerifyLead","ConfirmSlots","contact_details"}` (builder.py:945); their prompts have no refer tags → the round gate (1535-6) also blocks them. Freed states will retrieve via **lane B** (caller utterance) over the **9-KB general-union scope** (`kb_slugs_for` fallback, builder.py:975-986; general_prompt.md markers: are-you-ai, call-closing, call-context, hipaa, industry, pain-points, sales-language, sales-psychology, voice-ai-capabilities). 9 states total: Booking, Closer, Closing, ConfirmSlots, Discovery, Intake, Offer, VerifyLead, contact_details.
- **Dedupe today**: exact normalized match, window = last 6 spoken sentences, per-TURN (reset at ingest, builder.py:2257; write-back 2003; load 1885). Target bug: near-verbatim question re-asked across turns ("What's the name of your company?" ×3 + 2 variants, t30-t34).
- **Prewarm gap**: app.py has NO startup hook; Deepgram/Cartesia connect per call (~1.4 s + ~0.5 s on the greeting hot path). Greeting-time RAG/LLM warm machinery exists and works (session.py:187-215).
- **Owner decisions (DO NOT revisit)**: KB in all states all times · dv-gated industry pin unchanged · semantic dedupe cosine **0.90** cross-turn · evaluate fire modes before choosing — now THREE: speech-window / round-sync / **hybrid (owner-preferred 2026-09-20)** · prewarm transport at server start · A/B medium-vs-high offline only · prompts are OWNER-only · math humanization is prompt-side · migration parked · lane-B/EOT latency compression (below ~90 ms) DEFERRED ("let's address that later") · ONE embed model only (arctic-m; no dual-model).
- **House rules**: LAW 0 (code→branch→ASK; docs→main) · evidence→`research/` (gitignored) · `.env` never in git · `scripts/keyhound` before push · Cal event 3801235 REAL (cancel test bookings) · production agents READ-ONLY · KB policy: `kb_registry.json`, never hand-create (~$250 lesson) · Retell API GET-only.

## 2. Environment (verified in place)

- Worktree recipe (T0): branch `engine/iter59-kb-everywhere-freshness` from `db8e56f` (== iter58 branch head); `git worktree add /tmp/opencode/wt-iter59 …`; `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter59/engine/.venv` (wt-iter58 does the same); `cp -p /tmp/opencode/wt-iter58/engine/.env /tmp/opencode/wt-iter59/engine/.env` (has RETELL_API_KEY, VOICE_TEST_TOKEN, DEEPGRAM_EAGER_EOT_THRESHOLD=0.7, MAX_CALL_TURNS=64, MAX_CALL_SECONDS=900, LANGFUSE_HOST→:3001).
- Suite: `cd /tmp/opencode/wt-iter59/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → 368 (baseline) + new pins. Conventions: no conftest, sync tests, `asyncio.run`, inline `_FakeConn/_FakePool`+`embed_fn=` fakes (copy `test_iter49_rag_parity.py:48-83`), shared `tests/fake_llm.py`.
- fastapi 0.141.1 / starlette 1.6.0 — `FastAPI(lifespan=…)` verified working in this venv.
- Server :8020 ONLY via `bash scripts/serve_voice.sh` (from the engine dir; it loads .env, refuses prod ports AND a busy :8020, runs the RAG preflight gate). Langfuse `http://localhost:3001` (health OK). Ledger `research/surgeon/iter48-rag-truth/ledger.db` (no sqlite3 CLI — use venv python). Scrapling `/home/julio/projects/scrapling-mcp/.venv/bin/python`. Telegram: `scripts/hitl_ping.py` with the both-env export chain.

## 3. Tasks (execute in order; STOP POINTS marked)

### T0 — Worktree (mechanical; §2 recipe). Verify: 368 passed.

### T1 — ASSESSMENT PACK (READ-ONLY — no code) → `research/surgeon/iter59-kb-everywhere/01_assessment.md`
1. **Retell objection-engine extraction** — corpus = the 12 on-disk V7.8/V7.9 dialogues; primary: `NO-BOOK_chat_0f5f1c08496e163200d21d561d9.json` (10-round objection gauntlet), `V7.9_slot_lock_chat_86abc43fff5eb74a44faf5ecd9c.json`, `V7.8_reach_details_chat_797488f65d5db70a2d5f2529f97.json` + 3-5 BOOK files for contrast (all under `research/transcripts/`; full get-chat shape with `message_with_tool_calls`). Per call: objection turns, agent answers, which KB content answered (`knowledge_base_retrieved_contents_url`), rebuttal pattern (acknowledge→reframe→advance). Optional (only if owner wants production data): read-only Retell pulls → `research/transcripts/retell_78_79/`. GK_chat_* may be cited as V7.0-7.7 background only.
2. **Retell stack research (Scrapling, $0)** — docs.retellai.com / retellai.com: their answer→speech claims, voice-engine architecture, any pre-connect behavior. ALSO pull the **Deepgram flux `TurnInfo.Update` payload spec** (feeds T3 — see OPEN ITEM below).
3. **Dedupe sweep** — corpus: question sentences from `/tmp/opencode/iter58_gens_raw.txt` + synthesized 1-2-word variant pairs + the 0.54-0.57 rephrase controls; arctic-m embed (query prefix); sweep 0.80-0.97; prove 0.90 separates (near-verbatim ≥0.95 vs legit ≤0.6).
4. **Verbosity A/B** (corrected): arm 1 = defaults; arm 2 = `OPENAI_VERBOSITY=high VERBOSITY_STATES_MEDIUM=""`. Both: `cd /tmp/opencode/wt-iter58/engine && set -a && . ./.env && set +a && .venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 28`. Import both runs to the ledger (`ab-verb-medium`, `ab-verb-high`); report TTFT + objection-turn quality per SOP.
5. **Vertical prompt before/after** — pinned-industry block + knowledge delta at turns 9→11 from trace `daee4b00…` + `render_pinned_section` (rag.py:680) output.

**OPEN ITEM (resolve inside T1/T3):** the exact flux `Update` message shape is NOT documented in the repo. Before finalizing the T3 handler, either confirm from Deepgram docs (T1.2) or run one logged synthetic call with a raw-Update dump hook. Do not assume `is_final` semantics.

**STOP POINT — T2 (HITL):** Telegram ping → owner reviews `01_assessment.md`, decides prompts, painification KB go/no-go, Phase B scope. Record GO per fix. NO Phase B code before this.

### T3 — RAG FRESHNESS (builder.py, session.py, deepgram_stt.py, config.py)
- Config: `rag_fire_mode: str = "eot"` — `"eot"` (iter58 exact, revert) | `"speech-window"` | `"round-sync"` | `"hybrid"`.
- **speech-window**: (a) `deepgram_stt.py _handle`: `elif event == "Update" and transcript and self.on_update: await self.on_update(transcript)` (+ `on_update=None` ctor param, fire-safe). (b) `session.py`: `_on_stt_update(transcript)` — on FIRST Update of the turn (`if self._update_fired: return; self._update_fired = True`) call `_fire_live_retrieve(transcript)`; clear `_update_fired` in `_on_eot`/`_on_eager_eot` AFTER the fire decision, and in `_on_start_of_turn`. **When an Update fired this turn, SKIP the EOT/EagerEOT fire** (it would cancel/replace the landed task → degrade). (c) **Turn-keyed supersede**: `spawn_live_retrieve` gains `seq`; runtime `self._live_seq[state]`; `_consume_live_retrieve` matches `seq` (not msg text — fixes the same-text-rerun edge). (d) **`_live_consumed[state]`**: set on every consumed fresh result; timeout fallback degrades to it (never `_live_prev`'s unconsumed overwrite). (e) bounded await stays as safety net.
- **round-sync**: `_consume_live_retrieve` short-circuit → inline `await self._live_retrieve(...)` (span `mode="live-sync"`). Gate: TTFT p50 ≤980 ms, degraded 0%.
- Pins `tests/test_iter59_rag_freshness.py`: first-Update fire (once/turn) · Update-fired ⇒ EOT fire skipped · turn-keyed supersede (same text, changed dvs) · landed-fresh preferred · timeout → `_live_consumed` · `"eot"` = iter58 surface (regression) · round-sync inline · hybrid lane split.
- **HYBRID mode (owner-preferred 2026-09-20 — "best of both")**: lane A (refer-tag queries + dv values — utterance-INDEPENDENT) fires at FIRST Update, full multi-lane embed; lane B (caller utterance — only exists at EOT) fires at EOT as a **single-query embed** (~30-60 ms) + pgvector + merge, consumed inline within the await cap. Implementation: two `spawn_live_retrieve`-shaped tasks per state (`laneA` keyed by turn-seq, `laneB` keyed at EOT with supersede); `_consume_live_retrieve` merges lane A's landed chunks + lane B's awaited set through the SAME `merge_lane_chunks` (top_k=3, 1600 chars, per-KB quota — lane A candidates keep their owned-KB exemption). Gate (per-variant table): await p50 ≤80 ms, lane-A landed ≥90%, degraded <5%, TTFT p50 ≤900 ms.
- **Variant decision recorded in the report BEFORE the winning default is committed** (owner rule). Live gate (speech-window): ≥90% `degraded=False`, await p50 ≤15 ms. **Lane-B-at-EOT latency compression below ~90 ms (single-query lane B everywhere / multiquery=False tradeoffs / smaller embed model) is DEFERRED per owner — not in this iteration.**

### T4 — KB EVERYWHERE + DEDUPE 0.90 (builder.py, state.py, config.py)
- KB: `_RETRIEVAL_OFF: set[str] = set()` (keep the attribute — referenced at 971/1536/tests) + live-branch gate `do_retrieve = bool(scope)` (non-live path unchanged). Freed states: lane B over the 9-KB union (C2). `rag_char_budget=1600` still caps rendered chars; token-cost delta noted in the report. Lite rounds (turn-1/state-entry) still skip retrieval by design.
- Dedupe v2: config `tts_dedupe_semantic: bool = True`, `tts_dedupe_cos_threshold: float = 0.90`, `tts_dedupe_stem_window: int = 12`. state.py: `question_stem_window: list` — **plain key, NO reducer, NOT in the ingest reset list** (per-call persistence; seeded empty in `initial_state`). Token path (after exact-match check): `is_question = "?" in sentence`; if question AND semantic flag AND window non-empty → ONE `embed_query(stem)` (store's reused client, rag.py:424; **store None or embed failure → exact-only fallback, never block speech**) → cosine vs window vecs → `≥0.90` drop-from-spoken (same path as exact dup); else speak + append `{"text","vec"}` capped at 12 (FIFO). Statements and fast-flush fragments NEVER embed (G5: fragments exempt, join the exact window as today).
- Pins `tests/test_iter59_dedupe_semantic.py`: 1-2-word variant dropped @0.90 (fake embedder) · rephrase control (0.54-0.57) survives · cross-turn survival (ingest does not reset) · statements never embed (spy count) · flag off = iter58 surface. KB pins: `kb_slugs_for` non-empty for all 9 states == the 9 general slugs · a contact_details round with utterance ≥ `rag_min_query_chars` retrieves (lane B) and renders KNOWLEDGE.
- Re-run bug-coverage queries after the change (`lf_quick.py bugs --run <run>`).

### T5 — PREWARM (app.py + NEW diallux/media/prewarm.py + config.py)
- Config: `call_prewarm: bool = False` (OFF by default; flag-off = iter58 surface).
- `prewarm.py`: `prewarm_startup(settings)` — (1) idle Deepgram flux WS (same URL/headers as `DeepgramSTT._url()`, **effective eager threshold computed with the same None→0.6 default session.start applies** — settings are lru_cached/shared, G3) + KeepAlive every 5 s + maintainer respawn-on-close; (2) idle Cartesia WS (same URL/headers as `CartesiaTTS.connect`); (3) RAG stage: resolve the KB store singleton + one warm embed batch (loads the ONNX session). `adopt_stt_ws()/adopt_tts_ws()` pop-and-refill.
- `DeepgramSTT.connect(ws=None)` / `CartesiaTTS.connect(ws=None)`: adopted ws skips `websockets.connect`; recv loop binds the OWNING session's callbacks (F6).
- `session.start()`: `if settings.call_prewarm:` adopt from pool (fallback: fresh connect — a call never fails on the pool).
- `app.py`: lifespan hook → `prewarm_startup` when flag on; startup logs `prewarm: stt/tts/rag` + timings.
- Pins `tests/test_iter59_prewarm.py`: flag off = iter58 surface · flag on (fakes) = conns created + adopted + refilled.
- Deploy: `kill "$(cat /tmp/opencode/voice_8020.pid)"; sleep 2` THEN `cd /tmp/opencode/wt-iter59/engine && bash scripts/serve_voice.sh`. Verify: prewarm log lines; synthetic-call Deepgram connect ≤300 ms (baseline 1.4 s); suite green.

### T6 — OWNER LIVE CALL (STOP POINT — HITL)
Telegram ping → owner calls `https://flores.diallux-ai.site/voice/mic?k=<VOICE_TEST_TOKEN>`. Extract: degraded histogram, contact_details rag rows, dedupe drops, greeting first-audio, prewarm timings; ledger import (`live_sql.py import --window … --run live-iter59-<tag> --commit <sha>`).
Gates: fresh ≥90% · await p50 ≤15 ms (speech-window) OR TTFT p50 ≤980 ms (round-sync) · 0 cross-turn near-verbatim re-asks · server answer→speech ≤1.5 s · e2e p50 ≤1100 ms · bookings cancelled.

### T7 — CLOSEOUT + ASK (STOP POINT — HITL)
1. `docs/CALL_FACTS.md`: iter58 row (sid `49fdd9a4cf43`, db8e56f numbers from §0) + iter59 row; `git add docs/CALL_FACTS.md` (first-ever commit of this untracked file).
2. `plans/PENDING_TASKS.md`: PT-58 (contact_details prompt loop — OWNER) · PT-59 (unit-mislabel/leak-phrasing prompt pattern — OWNER) · PT-60 (freshness follow-ups) · PT-61 (dedupe v2 follow-ups) · PT-62 (KB-everywhere/prewarm follow-ups); note "PT-57 intentionally unused (like PT-52)".
3. `engine/ITERATIONS.md`: iter56/57/58 have NO ledger lines anywhere — add them + iter59's ON THE BRANCH closeout (never hand-edit on main).
4. Docs commit to main (LAW 0): CALL_FACTS.md + untracked `plans/plan_v5_iter58_eot08_public_mic.md` + surgeon outcome note. Code stays on the branch.
5. `scripts/keyhound` → Telegram ping → **ASK JULIO**: (a) merge branch, (b) keep flores/voice endpoint, (c) painification KB go/no-go, (d) US-East migration as separate session.

## 4. Validation plan (end-to-end)
1. T1 pack on disk with SQL/API citations; T2 GO recorded.
2. T3-T5: 368 + ~12-16 new pins green on the branch; bug-coverage re-run clean.
3. T6 live call: per-variant gates green; trace + ledger imported; bookings cancelled.
4. T7: docs committed, PT rows + ITERATIONS lines added, keyhound clean, ASK sent.

## 5. Out of scope (unchanged)
US-East migration · painification KB ingest (owner content + cost sign-off; agent never hand-creates) · engine-side math humanization (owner chose prompt-side) · min-trailing-silence EOT guard (only if sub-800 ms fires persist) · iter58 access-log token redaction · default-vertical industry assumption (dv-gating stays).
