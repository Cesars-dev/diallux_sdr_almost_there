# 01 — AUDIT — iter59: KB-everywhere · RAG freshness · semantic dedupe 0.90 · prewarm

- Date: 2026-09-20
- Audited plan: `plans/plan_v5_iter59_assess_rag_rebalance.md` (main @ `38e8a56`)
- Code base audited: `engine/iter58-eot08-public-mic` @ `db8e56f` (read from worktree `/tmp/opencode/wt-iter58` — verified `git rev-parse` == branch head; `:8020` serves from this worktree, pid 3824992)
- Method: every line-number claim in the plan traced to source; every pinned metric re-derived from the SQLite ledger + Langfuse API (read-only); every environment asset checked on disk.

---

## A. Plan claims vs reality (verified one by one)

| # | Plan claim | Verified reality | Verdict |
|---|---|---|---|
| A1 | `_RETRIEVAL_OFF = {"Booking","VerifyLead","ConfirmSlots","contact_details"}` at builder.py:945 | Exact, builder.py:945 | ✅ |
| A2 | `_STATE_KBS` at builder.py:955-963 | Dict spans 953-965 (minor offset) | ✅ (offset noted) |
| A3 | `are-you-ai` + `voice-ai-capabilities` attached only to Intake/Discovery | `are-you-ai`: Intake+Discovery only. **`voice-ai-capabilities` is ALSO on Offer** (builder.py:963) | ⚠️ PARTIALLY WRONG |
| A4 | `_fire_live_retrieve` at session.py:355-370 fires at EagerEOT/final EOT — same instant the round consumes → no speech window | Def at session.py:358; called at `_on_eot`:355 and `_on_eager_eot`:399; `_run_turn` task created at 356/400 — same tick. **THE bug confirmed in code** | ✅ |
| A5 | 23/24 rounds `degraded=True`, await≈60-61 ms, 1/24 landed fresh (await_ms=0) | Langfuse trace `daee4b00…`: 24 rag spans, **23 degraded, 1 await==0**, await p50 60.8 ms | ✅ EXACT |
| A6 | retrieval bg cost p50 131 ms | Ledger rag rows (24): ms p50 **123.2** (min 92.2, max 203.7) — same ballpark, plan's number from spans median | ✅ (~8 ms off, immaterial) |
| A7 | contact_details 10-turn stretch had ZERO retrievals; rag rows stop 06:57:20 | Ledger rag states: Intake 6, Discovery 7, Closer 7, Offer 4 — **no contact_details**; last row ts 06:57:20.308Z | ✅ |
| A8 | iter42 dedupe = exact normalized sentence match, window resets every turn ingest | builder.py:1872-1987 (exact-match `_norm_sentence` + `tts_dedupe_window`); reset at ingest builder.py:2257 (`"tts_sentence_window": []`); write-back builder.py:2003; state.py:43 | ✅ |
| A9 | `openai_verbosity: "medium"` config.py:42; `openai_reasoning_effort: "none"` config.py:41 | Exact | ✅ |
| A10 | temperature 0.30 ignored for gpt-5.4 | Guard in llm.py:176-181 (log line verified in code) | ✅ |
| A11 | Suite = 368 | `pytest --collect-only`: **368 collected, 0 errors** | ✅ |
| A12 | Flags `tts_dedupe_semantic`, `tts_dedupe_cos_threshold`, `rag_fire_mode`, `call_prewarm` do not exist yet | Absent from config.py (verified full read) | ✅ (N-status confirmed) |
| A13 | fastembed arctic-m, 768-d, threads 4, query prefix baked | rag.py:69 `LOCAL_EMBED_MODELS`, query-prefix comment rag.py:71, config.py:222-226 | ✅ |
| A14 | Deepgram eager_eot_threshold hard cap 0.70 (0.8 → HTTP 400) | .env `DEEPGRAM_EAGER_EOT_THRESHOLD` present (value not read); iter58 report bisection documented; config default None | ✅ |
| A15 | Caps live via .env: MAX_CALL_TURNS=64, MAX_CALL_SECONDS=900 | Both keys present in wt-iter58 `.env` | ✅ |
| A16 | Retell reference s07_t1.json "are you a real person…" | File exists (929 B); exchange confirmed; **structure = one file per TURN** (scenario 7 spans s07_t1…t8) | ✅ (structure note) |
| A17 | "chat-tested payloads already downloaded somewhere in the repo — likely ignored" | **12 V7.8/V7.9-era dialogues on disk** (3 pulled 2026-09-18 + 9 inherited, all `message_with_tool_calls` get-chat shape). BUT: the plan's cited `GK_chat_*.json` (65 files) are **V7.0-V7.7-era, NOT 7.8/7.9**; and **zero V7.9 chats from the production agent `agent_87e4…` exist on disk** (its 46 chats are V7.7) | ⚠️ PARTIALLY WRONG (see H2) |
| A18 | TTFT p50 845 ms / e2e p50 1143 ms; mic p50 ~46/p90 ~63 | iter58 report table (source doc), ledger consistent | ✅ |
| A19 | Call had 39 turns | Ledger `calls` row: `n_turns=38` (off-by-one vs report's "turns=39" — turn_index vs count, cosmetic) | ⚠️ cosmetic |
| A20 | iter58 leftovers: CALL_FACTS row, PT rows, docs commit, merge ASK | **CALL_FACTS.md is UNTRACKED and has NO iter58 row** (3 rows, last = iter56 redo); PENDING_TASKS highest = **PT-56** (PT-52 skipped, PT-57/58/59 unused); **ITERATIONS.md has NO iter56/57/58 ledger lines anywhere** (stale since MVP-Finally merge 2026-09-16); `plans/plan_v5_iter58_eot08_public_mic.md` itself untracked on main | ✅ (with detail, see H7) |

## B. What EXISTS (machinery inventory — all verified in code)

### B1. Live retrieval pipeline (iter49/iter52)
- `spawn_live_retrieve(state_name, dvs, user_msg)` builder.py:1199 — fire-and-forget, supersede-by-cancel per state, stashes into `_live_prev`.
- `_live_task` builder.py:1222 → `_live_retrieve` builder.py:1091 — `build_lanes` (1024) → ONE batched embed → parallel pgvector (`retrieve_lanes` rag.py:376-417) → `merge_lane_chunks` (rag.py:622) → `render_knowledge_section` (rag.py:669) + `render_pinned_section` (rag.py:680).
- `_consume_live_retrieve` builder.py:1245-1294 — priority: landed → bounded-await (`rag_live_await_ms`, config.py:254 = **60**) → degrade to `_live_prev[state]`. **Task match keyed by message TEXT** (`_live_msgs`, builder.py:1266), not turn.
- Round-path consumption: builder.py:1545-1565, gated by `do_retrieve = bool(scope) and (bool(refer_tags) or state_name in _RETRIEVAL_ALLOW)` (builder.py:1535-1536). **This gate is a second blocker the plan does not mention** (see F1).
- Industry pin (iter52): `_ensure_pinned_industry` builder.py:1159, resolver ladder 1131, `pinned_by_tag` rag.py:432 (metadata-only). dv-gated — resolves when `industry` dv first non-empty. Unchanged per owner decision.
- Rag span carries `degraded` + `await_ms` (builder.py:1556-1565) — the T6 gate metrics exist.

### B2. STT event surface (Deepgram flux)
- `DeepgramSTT._handle` deepgram_stt.py:176-189: handles EndOfTurn / StartOfTurn / EagerEndOfTurn / TurnResumed. **`Update` events are IGNORED** (comment line 189) — no per-final-transcript callback exists in flux mode today.
- `connect()` deepgram_stt.py:101-118: 3-attempt `websockets.connect`, recv task starts here. **KeepAlive loop only runs for nova3** (line 116-117) — flux idle connections have no keepalive.
- Callbacks are bound at `__init__` (session-specific closures).
- Session wiring: session.py:166-175; `_turn_state`/`_turn_dvs` maintained post-turn at session.py:588-591 (`_late_turn_report`) — the data a mid-speech fire needs already exists on the session.

### B3. TTS (Cartesia)
- `CartesiaTTS.connect()` cartesia_tts.py:82-92 — per-call connect, recv loop, no keepalive, no pool. `speak(context_id, text, continue_, overrides)` per chunk; contexts per turn.

### B4. App / server
- app.py (217 lines): NO startup/lifespan hook of any kind. `/mic/ws` token gate (fail-closed, 4401) — iter58. CallSession constructed per WS connection.
- `serve_voice.sh`: the only legal launcher; **REFUSES a busy :8020** (must kill the iter58 server before iter59 deploy; pid file `/tmp/opencode/voice_8020.pid`); runs `voice_preflight.py` RAG gate post-boot.
- Greeting warm machinery (session.py:187-215): KB-store resolve (2 s bounded) + `warm_rag` + full-Intake `warm_prompt_cache` + lite warm — all fire-and-forget during greeting. (Plan's "Lite-warm machinery EXISTS and worked" ✅.)

### B5. Dedupe (iter41/iter42)
- Sentence buffer + flush on `_SENTENCE_SPLIT_RE` (builder.py:86); exact window key `_norm_sentence` (builder.py:211); window = last `tts_dedupe_window=6` spoken sentences, carried across rounds of the SAME turn via `state["tts_sentence_window"]` (write-back 2003, load 1885), **reset at ingest** (2257).
- Fast-first-flush (iter46) integrates with the window (fragment joins window, builder.py:1904-1914).
- Silence guard: all-dup round still speaks if nothing spoken yet this turn (1887, 1932).

### B6. Verbosity plumbing
- `_verbosity_for(state_name)` builder.py:1396-1402 → `"medium"` for states in `verbosity_states_medium` (config.py:48 = **"Closer,Offer,contact_details,ConfirmSlots"**), else `""`.
- llm.py:253-256: `verbosity != settings.openai_verbosity` → routes to per-level twin (`llm_for_verbosity`, llm.py:213). Under today's default (`openai_verbosity="medium"`) the per-state override is a **no-op** (medium == medium). Under `OPENAI_VERBOSITY=high` the 4 listed states would STAY medium → **A/B confound** (see F3).
- `OPENAI_VERBOSITY` env override works (pydantic-settings; `.env` does NOT define it — env var survives `set -a; . ./.env`).

### B7. State / config surface for new work
- GraphState (state.py:22-50): adding a per-CALL key (e.g. question-stem window) is a 1-line TypedDict addition; `initial_state` (state.py:58) seeds defaults; ingest (builder.py:2247-2258) resets per-TURN keys — a per-call key must NOT be listed there.
- Config: pydantic BaseSettings, env-file backed; duplicate field definitions exist (database_url at 217+360, prompts_dir etc. at 358+374 — same values, harmless, pre-existing slop).
- KB store is a module-level singleton (`_SINGLETON`, rag.py ~560) — server-start RAG staging is feasible without per-call work.

## C. What's MISSING (gaps the plan must create)

| # | Missing thing | Evidence |
|---|---|---|
| C1 | Any mid-speech fire point: no `Update` handling in flux STT; no callback channel for partial transcripts | deepgram_stt.py:189 |
| C2 | Turn-keyed task identity: `_live_msgs` text-match is the only task-round association | builder.py:1264-1268 |
| C3 | Semantic dedupe: no embedder access on the TTS token path; no question-stem window; no cross-turn memory | builder.py:1896-1941 |
| C4 | `rag_fire_mode`, `call_prewarm`, `tts_dedupe_semantic`, `tts_dedupe_cos_threshold` flags | config.py (absent) |
| C5 | App startup hook / connection pool / idle-WS maintainer | app.py (absent) |
| C6 | `connect(adopt_ws=…)` adoption signatures on DeepgramSTT/CartesiaTTS | deepgram_stt.py:101, cartesia_tts.py:82 |
| C7 | Round-gate path for tag-less states under live mode | builder.py:1535-1536 |
| C8 | iter59 test files (3 planned) — confirmed absent; precedents exist (`test_iter49_rag_parity.py`, `test_dedupe_window.py`, `test_iter43_prewarm.py`) | tests/ inventory |

## D. Environment & assets (verified)

- Worktrees/branches: `wt-iter58` @ `db8e56f` = `engine/iter58-eot08-public-mic` head; **no `engine/iter59*` branch, no `wt-iter59`** — clean slate for the plan's worktree recipe. `wt-iter58/engine/.venv` is itself a symlink to the main engine venv → the plan's symlink recipe matches existing practice (pip trap: always `<venv>/bin/python -m pip`).
- `.env` (wt-iter58, key NAMES only): RETELL_API_KEY ✅, VOICE_TEST_TOKEN ✅, DEEPGRAM_EAGER_EOT_THRESHOLD ✅, MAX_CALL_TURNS/MAX_CALL_SECONDS ✅, LANGFUSE_HOST ✅ (Langfuse serving on :3001, health `{"status":"OK","version":"3.172.1"}`), OPENAI/CARTESIA/DEEPGRAM keys ✅.
- Ports: :8020 (iter58 voice, from wt-iter58) · :3001 Langfuse · :8000/:8001-:8003/:8005/:8007/:8008 live/stale — untouchable per deploy rules.
- Scripts all present: `engine/scripts/{serve_voice.sh, hitl_ping.py, lf.py, lf_quick.py, live_sql.py, voice_preflight.py}` · root `scripts/{live_sql.py, latency_pull.py, keyhound, git-tree.sh}`.
- Scrapling: `/home/julio/projects/scrapling-mcp/.venv/bin/python` exists.
- Dedupe sweep corpus: `/tmp/opencode/iter58_gens_raw.txt` exists (21,199 B, 304 lines, mtime Sep 20 07:03) — harness generations, question sentences extractable.
- Ledger: `research/surgeon/iter48-rag-truth/ledger.db` — run `live-iter58-070@db8e56f` present; tables runs/calls/rounds/rag/findings/sops/sessions; rag schema has NO degraded/await_ms columns (those live in Langfuse span outputs — verified via API pull).
- Langfuse pull (read-only, trace `daee4b00…`): **24 rag spans · 23 degraded=True · await p50 60.8 ms · exactly 1 span await_ms==0** — the plan's freshness-bug numbers are exact.

## E. Retell 7.8/7.9 dialogue corpus (asset reality)

On disk (`research/transcripts/`, 793 files):
- **Usable V7.8/V7.9 multi-turn dialogues: 12** — `V7.9_slot_lock_chat_86abc43fff5eb74a44faf5ecd9c.json` (133 msgs, agent_f305…), `V7.8_reach_details_chat_797488f65d5db70a2d5f2529f97.json` (133 msgs, agent_e996…), `V7.8_reach_details_chat_0f9a36cd89fc1e4df2a437078f0.json` (14, short), + 9 inherited test-battery files (8× BOOK_chat_* V7.8-era + **NO-BOOK_chat_0f5f1c08496e163200d21d561d9.json — the 10-round objection gauntlet: "Is this a scam?" → "fishy" → "what's the catch?" → goodbye; V7.8, tracks `objection_type` dv**).
- All share the full get-chat shape: `message_with_tool_calls` turn array, roles user/agent/tool_call_invocation/tool_call_result/state_transition, `knowledge_base_retrieved_contents_url` present → KB-trigger extraction feasible.
- **GK_chat_*.json (65) are V7.0-V7.7-era** — objection-rich but NOT 7.8/7.9 (plan's T1 grep command points at the wrong family).
- **No V7.9 production-agent (`agent_87e4…`) chats on disk** (its 46 = V7.7). If production-objection behavior is required, a fresh read-only Retell pull is needed (`GET /v2/list-calls?agent_id=agent_f305…` — the V7.9 slot_lock TEST agent also has more history available via list-calls).
- heating-uk s07_t1.json: confirmed, per-turn file structure, the "AI things" exchange present verbatim.

## F. Bugs / risks / conflicts found (NEW, beyond the plan's text)

| # | Finding | Impact |
|---|---|---|
| F1 | **Round gate blocks tag-less states even with scope**: `do_retrieve = bool(scope) and (bool(refer_tags) or state in _RETRIEVAL_ALLOW)` (builder.py:1535-6). contact_details/Booking/VerifyLead/ConfirmSlots prompts have ZERO refer tags (verified: only `##call-closing-kb##` markers in Booking/ConfirmSlots, nothing in contact_details/VerifyLead). Killing `_RETRIEVAL_OFF` alone changes NOTHING for those states. | KB-everywhere MUST also change this gate (live mode: `do_retrieve = bool(scope)`). |
| F2 | **Scope for freed states = the iter48 general-union fallback**: `kb_slugs_for` unmapped path (builder.py:975-986) = general_prompt's 9 KB markers ∪ state markers = the 9-KB general set for all 4 freed states. | Matches owner intent (global KB à la Retell); must be PINNED in tests, not assumed. |
| F3 | **Verbosity A/B confound**: with `OPENAI_VERBOSITY=high`, `verbosity_states_medium` keeps Closer/Offer/contact_details/ConfirmSlots at medium (llm.py:253 routes "medium" ≠ "high" → medium twin). The plan's A/B command as written tests a HYBRID, not high. | High arm must run `VERBOSITY_STATES_MEDIUM=""`. |
| F4 | **Flux STT drops `Update` events** (deepgram_stt.py:189): the plan's "fire at first-final-transcript" has no existing hook — needs a new `_handle` branch + `on_update` callback + session wiring. | Freshness variant A is a 3-file change (stt, session, builder), not a 1-line move. |
| F5 | **Flux idle WS has no keepalive** (keepalive is nova3-only, deepgram_stt.py:116): a prewarmed idle Deepgram flux WS may be reaped by the server. | Prewarm pool needs a keepalive/maintainer + respawn-on-close. |
| F6 | **Prewarm adoption is callback-bound**: DeepgramSTT/CartesiaTTS bind session closures at `__init__`; a pooled connection must be adopted at the WS level (`connect(adopt_ws=…)`) so the recv loop starts with the ADOPTING session's callbacks. | Prewarm design constraint, resolved in action plan. |
| F7 | **Semantic dedupe cost on the TTS hot path**: arctic single-query embed ≈ 30-60 ms; embedding EVERY sentence before speaking would tax TTFT. | Gate to interrogative sentences (contain "?") + only when the stem window is non-empty; stems embedded ONCE and cached as vectors in the window. |
| F8 | **`_live_prev` degrade semantics vs the plan's "`_frozen_chunks` fallback"**: under live mode `_frozen_chunks` is never maintained (inert iter48 machinery); "never stale-prev" as written is unimplementable without new state. | Master plan defines `_live_consumed[state]` (last CONSUMED fresh set) as the timeout fallback — strictly better than `_live_prev` (which can hold a never-consumed set). |
| F9 | **serve_voice.sh refuses busy :8020**: deploy step needs an explicit stop of the iter58 server (`kill $(cat /tmp/opencode/voice_8020.pid)`) — the plan says "iter59 restarts it" without the kill. | Deploy-recipe gap. |
| F10 | **Same-text rerun edge**: `_live_msgs` text-match (builder.py:1266) treats a landed task from a PREVIOUS turn with identical text as this round's (dvs may have changed). Turn-keyed supersede (plan already wants this) fixes it. | Confirmed real; fix spec'd. |
| F11 | **Docs/ledger drift for T7**: CALL_FACTS.md untracked (first commit = iter58 row commit); ITERATIONS.md missing iter56/57/58 lines entirely; PENDING_TASKS header stale (2026-09-12); NEXT_STEPS top item stale (iter55). PT numbering: plan's PT-58/59 + PT-60/61/62 leaves PT-57 unused (precedent: PT-52 skipped — acceptable, but must be stated). | Closeout scope must be explicit. |
| F12 | **round-sync variant breaks the e2e gate by construction**: inline retrieval ≈ +123-131 ms TTFT → e2e p50 ≈ 1270 ms > the plan's ≤1100 gate. The T5 evaluation must score variants against PER-VARIANT gates (sync: TTFT budget explicit; speech-window: await p50 ≤15 ms + degraded <10%). | Gate definition depends on chosen variant — decision must be recorded BEFORE coding (per owner). |

## G. Test-suite conventions (for the new pins)

- 368 tests, no conftest, no pytest-asyncio — all sync; async driven by `asyncio.run`/local `_run(coro)`. Every file self-bootstraps `sys.path`; deferred imports inside test bodies; module-level `SETTINGS = Settings(openai_api_key="test", …)` inline.
- Fakes are per-file inline (no shared store/embedder fake): copy `_FakeConn/_FakePool` + `embed_fn=` pattern from `test_iter49_rag_parity.py:48-83`; `FakeLLM` from `tests/fake_llm.py` IS shared/importable.
- Precedents: RAG freshness pins → `test_iter48_rag_truth.py`/`test_iter49_rag_parity.py`; dedupe pins → `test_dedupe_window.py`; prewarm pins → `test_iter43_prewarm.py`/`test_iter44_prewarm_bytes.py` (FastAPI TestClient + FakeWS patterns).

## H. Verdicts feeding the action plan

1. The plan's core diagnosis is **fully verified** (A4/A5: fire-at-consume + 23/24 degraded). The freshness fix direction is sound.
2. The plan's KB-everywhere scope is **under-specified** (F1/F2): two code sites, not one.
3. The plan's A/B command is **confounded** (F3) and its Retell-corpus pointer is **wrong-family** (A17/E): T1 needs corrected commands.
4. The prewarm concept is feasible but is **new machinery** (C5/C6, F5/F6), not a flag flip.
5. All infrastructure prerequisites (env keys, scripts, ledger, Langfuse, scrapling, worktree recipe) are **in place**.
