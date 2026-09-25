# 01 — AUDIT — iter55: TTS-era truth + turn-1 ammo (T0–T7)

Date: 2026-09-18 · Branch: `engine/iter55-tts-era-turn1-ammo` (worktree `/tmp/opencode/wt-iter55`, cut from `engine/iter52-industry-pin` @ `054af7b`, ZERO diff at audit time) · Method: full read of every T0-involved file + read-only evidence harvest. No code touched.

Source plan: `plans/plan_v5_iter55_tts_era_turn1_ammo.md` (supersedes iter54 plan). This audit verifies that plan's claims against the actual code on the branch point.

---

## A. What EXISTS today (verified, with line numbers)

### A1. Warm firing — ONE mechanism, BOTH channels (chat + voice)
`CallRuntime.warm_prompt_cache(state_name, history, dvs, lite=False, force=False)` — builder.py:365-397
- Key = `f"lite:{state}"` if lite else `state`; latch `self._prewarmed` (once per key per call, `force=True` re-fires).
- Creates the task, registers in `self._warm_tasks` (cancelled in `aclose()` builder.py:341-356) and `self._latest_warm[key]` (the await target).
- **Fire sites (all four verified):**
  1. session.py:198-209 (VOICE greeting): FULL Intake warm + LITE warm, fire-and-forget during greeting playback.
  2. harness.py:176-177 (CHAT parity, `_greeting_warms` mirror of session.py:179-205): same two warms, then `sleep(warm_greeting_ms)`.
  3. builder.py:1816 (tool-name detection): destination-state warm the moment `transition_to_<Dest>` name completes in the stream.
  4. builder.py:1930-1932 (post-execute): `force=True` re-warm with post-patch dvs — supersedes the detection warm as the `_latest_warm` await target.

### A2. Warm execution — `_warm(state_name, history, dvs, lite)` — builder.py:399-469
- Lite branch (412-422): `[lite head][history]` + `LITE_NOOP_TOOL` → `await self.llm.warm(messages, [LITE_NOOP_TOOL])`.
- Full branch (423-454): byte-exact via `_build_messages` (iter44 T1); under `rag_live_retrieve=True` (the default, config.py:221) the staged-RAG tail is SKIPPED — warm prefill = exactly `[tools][head][state-block][history]`.
- Except path (455-469): `log.warning("prewarm failed for %s: %s — one lite-shape retry")` + ONE lite-shape retry. **The retry's outcome is invisible.**

### A3. The warm LLM call — `StreamingLLM.warm()` — llm.py:234-244
- `_warm_llm` twin (llm.py:205-211): same model/kwargs as hot path + `max_completion_tokens=settings.prewarm_max_completion_tokens` (default 64).
- **`warm()` swallows ALL exceptions** (try/except → `log.warning("prewarm failed: %s")` at llm.py:240-244) → **the task ALWAYS completes "successfully" even when the request 400'd.** Callers: builder.py:421, 454 (inside `_warm`'s try), 467 (retry, inside its own try). No other callers (verified by grep).
- **ZERO tracing**: no span, no timestamps, no completion marker anywhere on this path (confirms plan finding #2).
- `StreamingLLM.__init__(self, settings)` (llm.py:169) — confirmed NO tracer access (plan's note holds).

### A4. Warm await — `_await_warm(state_name, wait_ms)` — builder.py:471-489
- `asyncio.wait_for(asyncio.shield(task), wait_ms/1000)`; silent catch of TimeoutError+Exception. NO outcome recorded.
- Call sites (builder.py:1373-1392): lite round → `lite:<state>` @ EOT cap (`prewarm_entry_wait_eot_ms`=500); **entry_lite ack → literal `pass` (builder.py:1382 — "the state-entry ack NEVER awaits")**; full EOT round → 500; mid-turn → `prewarm_entry_wait_ms`=100.

### A5. Greeting (VOICE only) — session.py:211-217
- `begin` message → `await self.tts.speak(ctx, begin, overrides=resolve_delivery(settings, "begin"))`. No LLM.
- First audio out: `_on_tts_audio` (session.py:654-662) — at greeting time `_speak_clock` is None → stamps the turn-0 `_clock` (harmless today; see F-06).
- `t_audio_out` stamped by `_writer` on first socket write (session.py:692-695).
- **NO greeting span exists** — stream-start → first-audio is unmeasured; greeting audio duration (the turn-1 runway) is unmeasured.

### A6. Tracer surface (reusable as-is)
- `Tracer.span(name, input, output, metadata)` — tracer.py:143-153 — fire-and-forget span, fail-safe. **This is the exact helper warm/greeting/await spans can reuse; NO tracer.py change strictly needed** (plan File Map lists tracer.py as Edit — see CR-3).
- `finish_llm` already writes `ttft_ms` + `cache_read` per generation row (tracer.py:85-114).
- Both channels route through `CallRuntime(tracer=...)` — builder-emitted spans appear in chat (harness `--langfuse` traces) AND voice (`micbridge-*` / `diallux-call-*`) traces automatically.

### A7. Chat vs voice divergence (verified)
| Concern | Chat (harness GraphAgent, harness.py:131-178) | Voice (CallSession) |
|---|---|---|
| Greeting warms | ✓ identical (mirror, `_greeting_warms`) | ✓ session.py:198-209 |
| Greeting audio | ✗ none — simulated by `sleep(warm_greeting_ms)` | ✓ TTS speak → audio |
| Warm/await spans after T0 | ✓ (builder-level) | ✓ (builder-level) |
| Greeting span after T0 | n/a (no audio; window length is known by construction) | ✓ new |

---

## B. What is MISSING (the T0 delta)
1. Warm fired/completed/failed timestamps + span per shape (lite/full/retry) — nowhere.
2. `_await_warm` outcome visibility: `landed | timeout | already_done | no_task` + waited_ms — nowhere.
3. Greeting span: stream-start → first-audio-out; greeting audio drain (runway) — nowhere.
4. Distinguish full-shape warm OK vs full-fail→lite-retry-degraded in evidence — impossible today (A2/A3).
5. Config flag gating the new observability (rollback = one env var).

---

## C. Findings (bugs / risks / corrections)

| # | Severity | Finding |
|---|---|---|
| **F-01** | BLOCKER (suite gate) | iter52 amend `054af7b` appended Rourke (happy-path) at the END of `PERSONAS` (personas.py:444-477) → `test_happy_path_present_and_first` FAILS (332/333 at branch point; plan expected 333 green). Pre-existing on the branch point, not environment. Fix = reposition the Rourke dict into the happy block (test fixture only, zero engine code). |
| **F-02** | Hygiene | config.py has a DUPLICATE "V2 production" block (lines 331-336 vs 347-351: prompts_dir/checkpoint_backend/database_url/metrics_enabled/hangup_mode). Identical defaults, second definition wins — harmless. NOT fixed in T0 (scope discipline); logged here. |
| **F-03** | T2 input risk | Langfuse short-ID `43d83d0815c9` NOT resolvable via `lf.py show` (lookup error); `e2aacc99471a` verified OK (micbridge-d928211cde17, turn spans + rag present). T2's agent-side era-52 sample must re-resolve the second trace ID (full ID or list-by-name). |
| **F-04** | Interpretation guard | Raw means: :8005 (iter52 lab, 38 turns) e2e 2,749 ms > :8000 (deployed iter40, 47 turns) 2,201 ms. Populations DIFFER (browser-mic bridge vs Twilio carrier; :8005 population unverified — plan's BLOCKED item). Do NOT read this as "iter52 slower" — that is precisely what T2's same-path A/B exists to answer. |
| **F-05** | Environment | Langfuse health: server OK (3.172.1), ingest "no recent traces" — expected (no runs since yesterday). Sep-era micbridge traces queryable. |
| **F-06** | Design note | At greeting, `_on_tts_audio`/`_writer` stamp the turn-0 `_clock` (`t_tts_first`, `t_audio_out`). No turn-0 report is emitted, but the T0 greeting span MUST use its own anchors (dedicated attributes), not the clock — avoids cross-contamination when turn 1 swaps clocks. |
| **F-07** | **BLOCKER for T3-as-written** | Plan T3 says "verify the sweep only touches the lite warm by reading `_warm`'s lite branch". **FALSE at code level:** `prewarm_max_completion_tokens` is baked into the SINGLE `_warm_llm` twin (llm.py:205-211) shared by BOTH warm shapes. Sweeping the env knob caps lite AND full warms — the full warm would re-expose the 400 "max_tokens reached mid-tool-call" rejection (observed in happy-e; the reason the cap was raised 16→64, config.py:97-101). T3 needs a prerequisite code change: split knob `prewarm_lite_max_completion_tokens` (default 64 = byte-exact current behavior) + a lite warm twin in `StreamingLLM`. |
| **F-08** | Failure-visibility blocker for T0 | `StreamingLLM.warm()` swallows all exceptions (A3) → a done-callback on the task CANNOT see failure; every warm would report ok. T0 must un-swallow: remove the internal try/except (safe — all three callers are inside their own try/except in `_warm`, verified) so `_warm`'s except + diag record can mark the span failed/degraded honestly. |
| **F-09** | Naming | `_await_warm` has a 4th outcome the plan didn't name: task never fired (`no_task` — e.g. `prompt_prewarm=False` or latched pre-call). Span taxonomy: `landed | timeout | already_done | no_task`. |

---

## D. Measured ground truth (read-only harvest, 2026-09-18 — saved evidence)

### D1. Ledger SQL (`research/surgeon/iter48-rag-truth/ledger.db`, runs: happy-d/e/f/g, happy-plumber-a/b, happy-mvp-a — 19 traces)
| Class | n | TTFT p50 | TTFT p90 |
|---|---|---|---|
| Turn-1 per call | 14 | 866 ms | 975 ms (max 1,088) |
| Lite-class (input < 2,000 tok, incl. acks) | 15 | 862 ms | 1,221 ms |
| Heavy-class (input ≥ 2,000 tok) | 345 | 888 ms | 1,079 ms |

Turn-1 cache_read observed: {0, 2688} (these runs probed turn-1 FULL; the 1,664 lite floor appears in the overall floor set {1664, 2688, 3712, 4736}). Warm-provider conditions — NOT true-cold (the cold-probe discipline ≥3.5 h idle is what T1/T4 enforce).

### D2. Prometheus snapshots (saved to `research/surgeon/iter55-era-truth/`)
| Engine | n turns | e2e mean | stt_eot→llm_first | llm_first→tts_first |
|---|---|---|---|---|
| :8000 LIVE (deployed iter40 era) | 47 | **2,201 ms** | 1,914 ms | 288 ms |
| :8005 (iter52 engine, browser-mic) | 38 | 2,749 ms | 2,380 ms | 369 ms |

→ LLM wait dominates (~87% of e2e) on BOTH engines; TTS is NOT the bottleneck (confirms plan finding). Files: `live_8000_snapshot_0918.prom`, `iter52_8005_snapshot_0918.prom`.

### D3. Telegram bot — ON FILE (owner directive: note only, do NOT wire now)
- Creds: `/home/julio/projects/video_strategy/.env` → `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (values on file, never committed).
- Reference pattern: `send_telegram(text)` — `/home/julio/projects/video_strategy/execution/clients.py` (requests POST to `api.telegram.org/bot<token>/sendMessage`).
- T0 execution step 1 (post-approval): `engine/scripts/hitl_ping.py` reading those env names; values copied into `engine/.env` (gitignored) at execution time.

### D4. Suite + branch state at audit time
- Suite: 332 passed, 1 failed (F-01). Langfuse server OK. Branch `engine/iter55-tts-era-turn1-ammo` @ `054af7b`, `git diff 054af7b` = empty.

---

## E. Files read (complete list)
`diallux/graph/llm.py` (312 ln, full) · `diallux/graph/builder.py` (2,234 ln — init/AC 270-357, warm machine 365-489, entry sites 1355-1429, detection/exec warms 1795-1934, reset 2195-2215) · `diallux/observability/tracer.py` (252 ln, full) · `diallux/config.py` (361 ln, full) · `diallux/media/session.py` (710 ln, full) · `tests/llm2llm/harness.py` (GraphAgent + greeting warms, 130-204) · `tests/llm2llm/personas.py` (Rourke diff vs `a36bdd7`) · ledger DB schema + runs/rounds · :8000/:8005 metrics endpoints · Langfuse (health, micbridge trace `e2aacc99471a`).
