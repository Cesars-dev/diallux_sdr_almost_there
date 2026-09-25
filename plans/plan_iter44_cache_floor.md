# PLAN — iter44: cache floor lift + conversation-driven RAG (kill the 2,688 cache cap, the 400 ms embed waste, and the frozen-retrieval miss)

## Meta
- Date: 2026-09-11
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — branch `engine/iter44-cache-floor` off `f5c0912`: byte-exact prewarm, session-start store resolve, tail-before-history reorder, embed-client reuse, transition RAG prefetch, drift-triggered re-retrieval, inline-fallback guard; suite + eval green; battery; owner live calls as pass/fail. iter43 gets the abandoned-iteration verdict.
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context (verbatim carry — session 2026-09-10/11, iter43 audit + latency forensics + iter44 design)

- **Project:** Dialux SDR voice engine "Linda" — LangGraph 9-state pipeline (Intake → Discovery → Closer → Offer → contact_details → ConfirmSlots → VerifyLead → Booking → Closing), Deepgram Flux STT → gpt-5.4 (`reasoning_effort=none`, `verbosity=low`) → gates → Cartesia sonic-3.6. Repo FORK = `clean_diallux_SDR` (MAIN workspace). Base branch `engine/iter42-dedupe-window` @ **`f5c0912`**, suite **206 passed** at base.
- **iter43 verdict (evidence-verified this session):** live call `532d92727e0f` (2026-09-10 23:30, trace `de9d47732ad2c0b5d210931772410db5`) was slow for three REAL reasons; DeepSeek's 16.5k-token root cause was NOT one of them (the blob never fired — first gen in=3,163; turn 1 barge-in'd before any LLM round). All its reported numbers REPRODUCED from Langfuse turn spans after the raw uvicorn log was destroyed by its own relaunch:
  - Per-turn e2e/TTFT (ms): t2 1,939/1,870 (cache_read 0) · t3 1,041/824 (2,688) · t4 1,841/1,654 (2,688) · t5 3,269/3,052 (cache 0 = Intake→Discovery transition) · t6 2,363/2,289 (3,712) · t7 1,463/1,244 (3,712).
  - **Cache floor:** cache_read stuck at 2,688 (tools ~700 + head ~2,096) while input grew 3,203→3,298 — history NEVER caches because the STATE-BLOCK tail sits AFTER history (builder.py:621-625); next turn's history lands where the tail was → prefix busts every round. tail is frozen per state visit (`frozen_state_block: bool = True`, config.py:103) but POSITION makes it cache-hostile.
  - **Retrieval cost:** state-entry rag spans measured 675.6 ms (Intake) / 422.3 ms (Discovery) on the critical path — designed 60-120 ms; cause: production rebuilds the OpenAI HTTPS client (fresh TLS handshake) per retrieve (rag.py:240 `embed = self.embed_fn or await openai_embed_fn(...)`; bug self-documented at rag.py:118 "code built a fresh AsyncOpenAI (new TCP+TLS handshake) on EVERY embed").
  - **Frozen-retrieval miss (sharpness gap vs Retell):** pgvector holds **77 industry chunks** (largest KB: are-you-ai 2, call-closing 3, call-context 6, discovery-bridge 37, hipaa 9, **industry 77**, pain-points 42, sales-language 11, sales-psychology 30, voice-ai-capabilities 16) but the call retrieved ZERO industry chunks — scope/query anchored on `{{pain_points}}` at Discovery entry, frozen 7 rounds; caller said "trucking" at turn 3 (Intake — no industry-kb in scope), `{{industry}}` captured at turn 6, no re-retrieval fired. Retell retrieved per turn server-side (kb_config `{filter_score: 0.6, top_k: 3}` verified in deployed snapshot `retell/sdr/current/retell/versions/04_slot_lock_CURRENT_cd0464dd/DEPLOYED_llm_snapshot.json`, 9 KBs attached).
  - **Turn-1 lite bug (real, never fired live):** `_lite_head()` kb=True inlined 16,299 tokens (measured; fix kb=False → 1,648; normal Intake head 2,322; normal Intake head, committed `374318b` UNPUSHED on iter43; correct, ADOPTED into iter44 via cherry-pick). Lite path hardcodes `kb_store=None` (builder.py:499) and `expand_kb = kb_store is None` (builder.py:500) routes no-store → inline fallback (the 16k blob path).
  - **Latch bug:** `_resolve_kb_store` (builder.py:338-344) sets `_kb_store_resolved=True` BEFORE awaiting → one transient RAG failure latches `None` for the whole session → inline-KB heavy mode permanently.
  - **Prewarm shape mismatch:** `_warm` (builder.py:230) sends `[head][history]` without tail; hot path sends `[head][history][tail]` → turn-2 cache_read=0.
  - **TTS exonerated:** llm→tts 69-218 ms, tts→audio 0.7 ms every turn. **LLM exonerated:** gen durations p50 1,354 ms (iter43, 8 gens) vs ~1,280 (iter42, 41 gens, trace `44866edbea1d`), max 1,811 vs 2,634.
  - **Evidence-recovery method (reusable):** Langfuse trace GET needs the FULL 32-char id (short id 404s; resolve via `lf.py traces --hours 168` list, then `/api/public/traces/{full_id}` with Basic auth from `LANGFUSE_HOST/LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY` in `engine/.env`); turn spans (`turn:N` / `turn:N:final`) carry the full per-turn reports as span OUTPUT (e2e_response_ms, stt_eot_to_llm_first_ms, head_start_ms...); generations carry `usageDetails.cache_read` as a custom key.
- **Live infra:** `:8007` PID 2324149 (since 2026-09-10 23:58:06, cwd `/tmp/opencode/wt-iter43`, env `FIRST_TURN_LITE=true CARTESIA_SPEED=1.12 OPENAI_MODEL=gpt-5.4`) serves the iter43-fixed build; ZERO live calls have hit it. `:8000` = original (PID 2659243, scanner noise only). NEVER touch `:8000/:8001/:8002/:8003/:8005`, live agent IDs, `slots.db`, Cal.com event **3801235** (REAL — cancel any test booking).
- **Unapproved-then-adopted:** `374318b` (kb=False + test_iter32_gate hermetic `first_turn_lite=False`) is the ONLY iter43 commit carried forward. iter43's OTHER unapproved changes (.env FIRST_TURN_LITE removal, server relaunch) are replicated deliberately in iter44's env rules (flag stays launch-env, never in `.env`).
- **Evidence protocol (learned the hard way):** copy any uvicorn log to a timestamped safety copy BEFORE any kill/relaunch; never overwrite a live log filename. Aggregates for call 532d survive ONLY in Langfuse.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| New branch `engine/iter44-cache-floor` off **`17b5c21`** (iter43's last owner-APPROVED commit, T0-T5) + cherry-pick `374318b` → HEAD `68541f7`; iter43 branch left unpushed, tagged `iter43-failed`, verdict line in ITERATIONS.md | CORRECTED during T0 execution: cherry-pick `374318b` CONFLICTS off `f5c0912` (`_lite_head` was born in iter43 T3 — the function doesn't exist at base). All plan code anchors (hysteretic window, prewarm, lite head) live in the approved iter43 commits, so `17b5c21` is the base that matches this plan's anchors. `17b5c21` = approved work exactly, zero unapproved carries |
| All six fixes in ONE iteration (T1,T2,T3,T4,T6a,T6b,T6c), each behind a kill-switch config flag, defaults ON for the iteration (T4's `fallback_inline_kb` default False by design) | Owner approved the full package; flags allow instant per-behavior rollback without code edits |
| Retrieval stays ENGINE-driven (state scope + drift re-retrieval); NO `search_kb` model tool | Model-driven retrieval = +1 LLM round-trip (2-3 s) — owner rejected ("That's gonna be a 2,000, 3,000 milliseconds turn latency") |
| Drift check pays ~100 ms embed on rounds with a NEW caller message; dedupe by cosine vs stashed query vector | Owner: "we can afford ourselves to do that on every call because we're not wasting time" — explicit cost approval |
| Local (non-OpenAI) embedding model = iter45 candidate, NOT this iteration | Needs full corpus re-embed + quality check; with T6b the embed comes off the critical path anyway |
| Turn 1 stays lite (main prompt only, 1,648 tokens); `FIRST_TURN_LITE` stays launch-env, NEVER in `.env` (leaks into tests via pydantic `env_file=".env"`, config.py:31-33) | Verified test-breakage mechanism; `374318b` carries the hermetic SETTINGS guard |
| Battery: standard first-13 low tier before live calls | Doctrine: happy-path gate first; bookings cancelled after |
| 2 owner live calls AFTER suite+eval+battery green, served from the NEW worktree `/tmp/opencode/wt-iter44`; pass criteria = cache curve + rag timing + industry chunks in Langfuse | Turns "felt slow" into measurable pass/fail; same-source method proven on 532d |
| iter43's T4 prompt changes (Offer ask), T1 EOT telemetry, T2 hysteretic window, T3 prewarm infra, T5 speeds are APPROVED work — they live on iter43's branch but iter44 rebuilds from base; the telemetry/window/prewarm capabilities ARE re-shipped by iter44's own tasks (T1/T6b) plus T1's telemetry is NOT cherry-picked (out of scope) — measured success uses the Langfuse same-source method instead | Avoids carrying an entire unapproved-fix branch; iter44 is a clean line of work with every change owner-blessed |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner availability for the 2 live calls (T9) | Julio, after T8 green |
| Ruling if pass criteria partially fail | Review session with the Langfuse pull in hand |
| Exact `scripts/eval_accuracy.py` invocation name (verify at T7) | `ls /tmp/opencode/wt-iter44/scripts/ | grep -i eval` — if the entry differs, use the one iter42's report used (`scripts/eval_accuracy.py` offline 5/5) |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12). Pinned: langchain-openai **1.6.0**, langgraph **1.2.11**, langfuse **4.15.1**, pytest **9.1.1**, pydantic **2.13.5**, pydantic-settings **2.15.0**, httpx **0.28.1**, fastapi **0.141.1**, tiktoken (encoding `gpt-5.4`), asyncpg (pgvector pool), openai (AsyncOpenAI embeddings, model `text-embedding-3-small`, 1536 dims).
- Base: **`17b5c21`** (see Resolved Decisions correction); branch HEAD `68541f7` (cherry-pick of `374318b`); worktree `/tmp/opencode/wt-iter44`; `.venv` symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`; `.env` copied from `/tmp/opencode/wt-iter43/.env` (has `CARTESIA_SPEED=1.12`; T5's test expectations need it — the wt-iter42 copy fails `test_cartesia_generation_config_sent_every_request`; `FIRST_TURN_LITE` verified absent).
- Services/ports: engine test server `:8007` (127.0.0.1), Langfuse `:3001` v3.172.1, PG `:5434` (DATABASE_URL in `.env`), Cal.com slots `:8001`, egress proxy for julio's outbound (TLS handshake overhead is the measured 300-500 ms — T6a target).
- Key code anchors (paths relative to `/tmp/opencode/wt-iter44`):
  - `diallux/graph/builder.py` — 197-209 `warm_prompt_cache` (latched `_prewarmed`), 210-235 `_warm` (no tail), 324-334 `warm_rag`, 336-344 `_resolve_kb_store` (latch-before-await bug), 349-375 `kb_slugs_for` + `_RETRIEVAL_OFF` (Booking/VerifyLead/ConfirmSlots/contact_details) + `_RETRIEVAL_ALLOW` (Closing: call-closing), 407+ `static_head`, 426+ `_lite_head`, 460-475 `_history_window` (hysteretic n=16 step=8), 486-625 state_node compose (497-506 lite/store/head, 513-518 frozen tail, 519-574 rag freeze/`_rag_cache` keyed `(state, query)`/filler guard `rag_min_query_chars`, 584-617 tools cache `_tools_cache[(state, expand_kb)]`, 621-625 messages layout), 890-930 engine tool plan, 1015-1030 one-trip finalize (T6b hook region; grep anchor `t["name"].startswith("transition_to_")`).
  - `diallux/media/session.py` — 170-195 `start()` order: `warm_rag()` task, `warm_prompt_cache(...)`, greeting `speak()`.
  - `diallux/rag.py` — 114-126 `openai_embed_fn`, 140-175 `KBStore.__init__` (embed_fn injectable, filter_score 0.40, char_budget 1600, top_k 4), 228-260 `retrieve` (embeds at 240-241; docstring 232 "caller falls back to inline KBs"), 314-330 `get_kb_store` (RAG_MODE auto/rag/inline), 393-401 `render_knowledge_section`.
  - `diallux/config.py` — 31-33 env_file, 54-59 `history_window: int = 16` / `history_trim_step: int = 8`, 103 `frozen_state_block: bool = True`, ~54-76 knob region for new flags.
- Test blast radius: `tests/fake_llm.py:27-45` (C3b layout comment; `seen_systems` JOINS all system msgs → substring checks survive T3; `systems[0]` + `match_system` asserts target the head — head stays messages[0]), `tests/test_iter31_c3_prefix.py` (head/tail split asserts, lines ~65-128 — MUST update for new layout), `tests/test_iter43_prewarm.py` (WarmSpyLLM pattern — extend for byte-identity), `tests/test_iter32_gate.py:31` (hermetic SETTINGS via cherry-pick), `tests/test_iter43_history_hysteresis.py` + `tests/test_iter30_fast.py:178` (window-only, unaffected by reorder).
- Unknowns pinned by audit: none blocking. `RAG_MODE` in live `.env` = `rag` (per :8007 /health `"rag_mode":"rag"`).

## Architecture (one block)
```
CALL START (session.py start())
  │ await _resolve_kb_store (≤2.0s wait_for, latch AFTER await)   ← T2  [kills race + 16k session latch]
  │ greeting speaks (canned, no LLM)
  ├─ fire-and-forget: warm_prompt_cache("Intake", hist)            ← T1  [BYTE-IDENTICAL via shared _build_messages]
  ▼
TURN N (state_node)
  messages = [tools][static head][FROZEN TAIL: state block + KB chunks][history]  ← T3 (tail BEFORE history)
  │                                                                └→ prefix cache GROWS each round (2,688 → climbs, bounded ~5k by window 16/step 8)
  ├─ rag lane: NEW user msg? → drift check = embed round query (~100ms) vs stashed vector
  │    ├─ cosine ≥ rag_drift_threshold (0.85) → SKIP retrieve (dedupe, 0ms extra)   ← T6c
  │    └─ drifted → retrieve(vec reuse, ~15ms pgvector) → tail rebuilt → one-time rebill
  ├─ TRANSITION fires (transition_to_X ok)
  │    └─ bg: RAG prefetch for X's scope + byte-exact prewarm for X (existing latch)  ← T6b (worst case = today's sync fetch)
  └─ embed client: created ONCE at store init, reused forever                        ← T6a (425-675ms → 60-120ms)
GUARD: fallback_inline_kb=False (default) — pgvector down ⇒ no-KB head + loud log + health flag, NEVER the 16k blob   ← T4
PASS CRITERIA (2 live calls, Langfuse same-source): cache_read climbs past 2,688 · state-entry rag ≈ 0ms critical-path · industry chunks appear when caller names industry · e2e p50 ≤ 1,304 (iter42 baseline)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter44_cache_floor.md` | this plan | NEW (commit main, docs path) |
| `/home/julio/projects/clean_diallux_SDR/ITERATIONS.md` | iter43 abandoned-iteration verdict line | EDIT (docs, commit main) |
| `/tmp/opencode/wt-iter44/diallux/config.py` | new knobs beside line 76: `prewarm_byte_exact: bool = True`, `tail_before_history: bool = True`, `rag_prefetch_on_transition: bool = True`, `rag_drift_requery: bool = True`, `rag_drift_threshold: float = 0.85`, `fallback_inline_kb: bool = False` | EDIT |
| `/tmp/opencode/wt-iter44/diallux/graph/builder.py` | T1 `_build_messages()` shared composer used by `_warm` + state_node; T2 latch order fix (336-344); T3 layout (621-625); T6b transition hook + `_rag_prewarmed` latch + staged chunks; T6c drift check + `_frozen_query_vec` stash + `rag:drift` span; T4 guard (line 500) | EDIT |
| `/tmp/opencode/wt-iter44/diallux/media/session.py` | T2: `await asyncio.wait_for(runtime._resolve_kb_store(), 2.0)` before `warm_prompt_cache` in `start()` (176-183) | EDIT |
| `/tmp/opencode/wt-iter44/diallux/rag.py` | T6a: embed_fn built/cached ONCE at store init/first connect; `retrieve(query, kb_slugs, vec=None)` optional precomputed vector (240-241 uses it, skips re-embed) | EDIT |
| `/tmp/opencode/wt-iter44/tests/test_iter44_prewarm_bytes.py` | warm bytes == hot bytes (WarmSpyLLM) | NEW |
| `/tmp/opencode/wt-iter44/tests/test_iter44_cache_floor.py` | tail layout order, drift re-retrieval, fallback guard, prefetch latch, resolve-latch fix | NEW |
| `/tmp/opencode/wt-iter44/tests/test_iter31_c3_prefix.py` | update tail-position asserts to new layout | EDIT |
| `/tmp/opencode/wt-iter44/tests/fake_llm.py` | update C3b layout comment (behavior unchanged) | EDIT |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/01_report.md` | findings + before/after report (gitignored evidence) | NEW |

## Deploy Rules
- Branch ops (execution session, exact commands — EXECUTED 2026-09-11, verified):
```bash
cd /tmp/opencode/wt-iter42 && git worktree add -b engine/iter44-cache-floor /tmp/opencode/wt-iter44 17b5c21
ln -sfn /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter44/.venv
cp /tmp/opencode/wt-iter43/.env /tmp/opencode/wt-iter44/.env        # CARTESIA_SPEED present, FIRST_TURN_LITE absent
grep -q FIRST_TURN_LITE /tmp/opencode/wt-iter44/.env && sed -i '/FIRST_TURN_LITE/d' /tmp/opencode/wt-iter44/.env || true
cd /tmp/opencode/wt-iter44 && git cherry-pick 374318b               # applies CLEAN off 17b5c21 (its parent)
git -C /tmp/opencode/wt-iter43 tag -a iter43-failed -m "iter43: abandoned — cache floor + embed-TLS + frozen-retrieval miss; evidence in research/surgeon/iter43-eot-firstturn/"
```
(DO NOT base off `f5c0912`: cherry-pick conflicts — `_lite_head` born in iter43 T3.)
- Test/eval/battery:
```bash
cd /tmp/opencode/wt-iter44 && .venv/bin/python -m pytest tests -q                      # T0 DONE: 224/224, exit 0 (dot-count metric; no summary line in this repo's pytest)
cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && .venv/bin/python -m pytest tests -q   # later gates: expect ≥232
cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && .venv/bin/python scripts/eval_accuracy.py --mode offline   # verify exact CLI at T7; expect 6/6 (s1-s6)
```
- Battery (T8): first-13 personas low tier, harness pattern from AGENTS.md (`tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 48`), logs to `/tmp/opencode/iter44_low_<Persona>.log`, staging dir `/tmp/opencode/sop_batch_w44_low/`, digest out `/tmp/opencode/iter44_low_sop_digest.txt`; **cancel ALL test bookings (Cal.com event 3801235 is REAL)**.
- Live relaunch (ONLY after owner gate at T9):
```bash
cp /tmp/opencode/uvicorn_8007_iter43.log /tmp/opencode/uvicorn_8007_iter43_CLOSED_2026-09-11.log   # SAFETY FIRST
lsof -tiTCP:8007 -sTCP:LISTEN   # confirm PID (expect 2324149) → kill <pid>
cd /tmp/opencode/wt-iter44 && export FIRST_TURN_LITE=true CARTESIA_SPEED=1.12 && \
  nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8007 > /tmp/opencode/uvicorn_8007_iter44.log 2>&1 &
curl -s http://127.0.0.1:8007/health   # expect {"ok":true,...,"llm":"gpt-5.4","rag_mode":"rag"}
```
- NEVER touch: `:8000/:8001/:8002/:8003/:8005`, live Retell agent IDs, `slots.db`, Cal.com event 3801235 (no test bookings left), Langfuse :3001, PG clusters 5432-5434 (5434 = RAG, read-only SELECTs only).
- LAW 0: no merge/push without Julio's explicit say-so; the ONLY carry from iter43 is cherry-picked `374318b`; `research/` stays gitignored.

## Tasks (in order)

### T0 — Branch + worktree + baseline ✅ DONE (2026-09-11)
Goal: clean branch off the approved iter43 work + the adopted one-line fix; iter43 marked abandoned.
Files: worktree `/tmp/opencode/wt-iter44`; `engine/ITERATIONS.md` verdict line; plan file (committed main).
Commands: Deploy Rules branch-ops block (EXECUTED — see correction note there).
Dependencies: none.
Verification: DONE — `git -C /tmp/opencode/wt-iter44 log --oneline -2` = `68541f7` (fix) on `17b5c21`; tag `iter43-failed` exists on the iter43 branch; suite **224/224, exit 0** (log `/tmp/opencode/iter44_t0_suite.log`; dot-count 224 = recorded iter43 baseline). Plan file + verdict committed to main (`local only — push pending owner say-so`).

### T1 — Shared message builder (byte-exact prewarm)
Goal: prewarm request == hot-path request (exact bytes + tools), so the greeting prewarm's cache carries into turn 2.
Files: `builder.py` — factor `_build_messages(state_name, history, tail, system)` from the state_node composer (621-625); `_warm` (210-235) calls it with the frozen tail (rendered via `_state_block(dvs)` on the warm path — the same code the hot path uses at 513-518, with `frozen_state_block` honored); config knob `prewarm_byte_exact` gates the new path (False → legacy behavior).
Commands: edit builder.py; add `tests/test_iter44_prewarm_bytes.py` using the WarmSpyLLM pattern from `tests/test_iter43_prewarm.py`: drive one FakeLLM hot round, capture warm() messages, assert `warm_messages == hot_messages` and `warm_tools == hot_tools` (exact equality).
Dependencies: T0.
Verification: new test passes; full suite green (no regressions in test_iter43_prewarm.py — its WarmSpyLLM head assertions survive because the head is unchanged, only the tail is added).

### T2 — Store resolve at session start + latch fix
Goal: prewarm and hot path always see the SAME store decision; a transient failure never latches inline mode for a session.
Files: `builder.py:336-344` — move `_kb_store_resolved = True` to AFTER the await succeeds (on exception: leave unresolved so the next call retries, but set `_failed_at`-style backoff if rag.py provides one); `session.py:176-183` — `await asyncio.wait_for(self.runtime._resolve_kb_store(), 2.0)` before `warm_prompt_cache` (wrapped in try/except so a store outage never blocks call start).
Commands: edit both files; add tests in `tests/test_iter44_cache_floor.py`: (a) store raising once → first resolve returns None, second resolve retries and succeeds (no permanent latch); (b) session start with dead store still proceeds (start doesn't raise).
Dependencies: T0.
Verification: new tests pass; full suite green.

### T3 — Tail before history
Goal: `[tools][head][tail][history]` so the prefix grows round-to-round; bounded by the existing window cap (16/8) → ceiling ≈ 5k tokens.
Files: `builder.py:621-625` — when `tail_before_history`: `messages = [head] + [tail] + history` else legacy order; update `tests/test_iter31_c3_prefix.py` asserts (head=messages[0], tail=messages[1], "values only ever in the tail" check now targets messages[1]); update `fake_llm.py:27` comment.
Commands: edit; add tests in `tests/test_iter44_cache_floor.py`: two same-state rounds → messages[0]+messages[1]+first history entries byte-identical; kill-switch `tail_before_history=False` → legacy layout (old iter31 tests pass unmodified).
Dependencies: T1.
Verification: new tests pass; `test_iter31_c3_prefix.py` green in BOTH modes; full suite green; offline eval 6/6 (behavior check — the model now reads history last).

### T6a — Embed client built once
Goal: kill the per-retrieve TLS handshake (425-675 ms → designed 60-120 ms).
Files: `rag.py` — in `KBStore`, lazily build `self.embed_fn` once (first `retrieve` or `connect()`): `if self.embed_fn is None: self.embed_fn = await openai_embed_fn(self.embedding_model, self.api_key)`; `retrieve` (240-241) uses `self.embed_fn` directly (no per-call `openai_embed_fn`). Injected embed_fn (tests/hermetic) still wins.
Commands: edit rag.py; add test in `tests/test_iter44_cache_floor.py`: monkeypatch `openai_embed_fn` with a spy counting constructions; 2 retrieves → exactly 1 construction.
Dependencies: T0.
Verification: new test passes; `test_rag.py` green; full suite green. (Live timing proof deferred to T9.)

### T6b — Transition prefetch (RAG + prewarm)
Goal: state entries pay ~0 ms retrieval; next state's full payload prewarmed at the moment the transition executes.
Files: `builder.py` — hook where a `transition_to_X` tool executes with `status=="ok"` (grep anchors: `t["name"].startswith("transition_to_")` region 1015-1030 one-trip finalize + engine plan 890-930; hook at the point the executor records the ok transition, before the next state_node runs): fire (a) `warm_prompt_cache("X", history)` — existing `_prewarmed` latch, now byte-exact via T1; (b) NEW `_rag_prewarmed: set[str]` latch + bg task: `retrieve(query, kb_slugs_for("X"))` staging into `self._rag_staging["X"]`; state_node rag lane (519-574) consumes staged chunks if present (pops them), else sync fetch (today's behavior, never worse). Config knob `rag_prefetch_on_transition`.
Commands: edit; add tests in `tests/test_iter44_cache_floor.py`: FakeKBStore records retrieves; ok transition → staged chunks present; next state_entry uses them with NO second retrieve; prefetch failure → state entry falls back to sync fetch (never raises).
Dependencies: T1, T2, T6a.
Verification: new tests pass; full suite green; offline eval 6/6.

### T6c — Drift-triggered per-need re-retrieval
Goal: "query when needed, for what we need" — fixes the industry-kb miss; dedupe by cosine (no redundant retrieves), zero extra LLM turns.
Files: `builder.py` rag lane (519-574): stash `self._frozen_query_vec` (vector of the query that produced `_frozen_chunks`) + `self._frozen_query_text`; on each round with a NEW user message (skip filler turns via existing `rag_min_query_chars` guard at 536) and `rag_drift_requery` ON: build round query via `refer_query(state_name, dvs, user_msg)`; embed it (~100 ms, T6a-stable client); cosine vs `_frozen_query_vec`; `≥ rag_drift_threshold` (0.85) → SKIP retrieve (chunks still valid); `< threshold` → `retrieve(query, scope, vec=just_computed)` (rag.py optional `vec` param — no double embed), rebuild tail, reset `_frozen_state`, stash new vec, emit `rag:drift` span `{state, cosine, ms, chunks}` for tuning telemetry. First state entry sets the vec baseline (no check). Cache note: tail change re-bills once — accepted (existing "Correctness > cache" precedent, builder.py:510-512).
Commands: edit builder.py + rag.py `retrieve` signature; add tests in `tests/test_iter44_cache_floor.py`: (a) same-topic repeat round → retrieve NOT called again; (b) topic-shift round ("trucking" after after-hours talk) → retrieve called with the NEW query, tail rebuilt with new chunks, span logged.
Dependencies: T6a.
Verification: new tests pass; full suite green; offline eval 6/6.

### T4 — Inline fallback guard
Goal: the 16k whole-KB blob becomes unreachable; Postgres outage degrades gracefully.
Files: `config.py` — `fallback_inline_kb: bool = False`; `builder.py:500` — `expand_kb = (kb_store is None and settings.fallback_inline_kb)`; `rag.py get_kb_store` auto-mode path — when store unavailable and flag False, log `RAG fallback inline DISABLED (fallback_inline_kb=False) — running without KB excerpts` once per session.
Commands: edit; add tests in `tests/test_iter44_cache_floor.py`: (a) store=None + flag False → head has markers stripped, NO inline KB text, loud log recorded; (b) flag True → legacy inline expansion (existing behavior tests keep passing); (c) explicit `RAG_MODE=inline` UNTOUCHED (legit V1 mode).
Dependencies: T0.
Verification: new tests pass; full suite green.

### T7 — Full gates (suite + offline eval)
Goal: everything green before battery.
Commands:
```bash
cd /tmp/opencode/wt-iter44 && .venv/bin/python -m pytest tests -q
cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && .venv/bin/python scripts/eval_accuracy.py --mode offline
```
Dependencies: T1-T4, T6a-T6c.
Verification: suite ≥ **232 passed** (224 + ~8 new), exit 0; eval **6/6 PASS** (s1-s6). If the eval CLI differs from `--mode offline`, use the iter42-report invocation (verify with `ls scripts/ | grep -i eval`).

### T8 — Battery (first-13 low)
Goal: quality guard before live calls.
Commands: run the standard first-13 battery per AGENTS.md run-and-test (harness `--personas` loop, low tier, `--rag --langfuse --max-turns 48`), logs `/tmp/opencode/iter44_low_<Persona>.log`, staging `/tmp/opencode/sop_batch_w44_low/`, digest `/tmp/opencode/iter44_low_sop_digest.txt`.
Dependencies: T7.
Verification: 13/13 `ALL PASS`; digest saved; **cancel ALL test bookings on Cal.com event 3801235**; any FAIL → stop, diagnose, report before T9.

### T9 — Relaunch :8007 + owner live calls + pass criteria
Goal: measurable pass/fail on the real wire.
Commands: Deploy Rules relaunch block (log-safety copy FIRST → kill → launch from wt-iter44 → health check). Julio drives **2 live calls** from the Mac.
Dependencies: T8 green + owner go.
Verification (Langfuse same-source method — resolve full trace id via `lf.py traces --hours 2`, pull turn spans + gens `usageDetails.cache_read` + rag span `ms` fields):
1. cache_read on turns 3+ **climbs past 2,688** (grows with history)
2. state-entry turns: rag `ms` ≈ 0 critical-path (prefetched) — entry e2e ≤ ~1,400 ms
3. caller names an industry → industry-kb chunks appear in a `rag`/`rag:drift` span mid-state
4. e2e p50 ≤ **1,304 ms** (iter42 baseline); stretch ≤ 1,100
5. NO generation with input >4,500 tokens (blob guard working)

### T10 — Report + commits + LAW 0 ask
Goal: evidence on record; nothing merged without owner.
Files: `research/surgeon/iter44-cache-floor/01_report.md` — before/after table (per-turn e2e/TTFT/cache/rag-ms, both live calls), pass-criteria checklist, any deviations.
Commands: commits on branch grouped per task (T1, T2, T3, T6a, T6b, T6c, T4, tests included per group); plan file + ITERATIONS.md verdict committed to main (docs path, no ceremony).
Dependencies: T9.
Verification: `git -C /tmp/opencode/wt-iter44 log --oneline origin/main..HEAD` lists the task commits; report exists; explicit ASK to Julio: merge/keep verdict.

## Validation Plan (end-to-end)
1. T0: branch + cherry-pick + 206 baseline green + iter43 tag/verdict done.
2. T1-T4, T6a-T6c: each lands with its NEW test passing + full suite green (no skips, no xfails).
3. T7: suite ≥232 + offline eval 6/6.
4. T8: battery first-13 low 13/13 PASS; bookings cancelled.
5. T9: 2 live calls meet ALL 5 pass criteria (Langfuse same-source, raw pulls saved to `research/surgeon/iter44-cache-floor/`).
6. T10: report + commits on branch + LAW 0 ask; nothing merged/pushed without Julio.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Local embedding model on the VPS (drop OpenAI embed entirely) | iter45 candidate — needs full corpus re-embed + quality check; with T6b the embed is off the critical path |
| `search_kb` model tool (LLM-driven retrieval) | Rejected: +1 LLM round-trip (2-3 s); revisit only with missed-chunk evidence post-iter44 |
| EOT params A/B/C/D decision (old iter43 T7) | Data-gated on live calls; the 2 iter44 calls provide the data |
| iter43's T1 EOT telemetry cherry-pick | Out of scope — success is measured via Langfuse same-source method; telemetry rework can join iter45 if owner wants in-engine turn reports again |
| `transition_to_*` in `_MECHANICAL_RE`, battery root-causes (Gene LOW stall, name-refusal loops), Postgres memory, model swap | Pre-existing deferred list, unchanged |
| Any merge of `engine/iter43-*` or `engine/iter44-*` into `engine/main` | LAW 0 — owner say-so only |
