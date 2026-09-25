# 02 — ACTION PLAN — iter55: T0 implementation + T1–T7 protocols

Answers 01_audit.md §B (MISSING) and resolves F-01…F-09. Sequenced commits; every step has a rollback; NO behavior change ships in T0 (observability only). T1–T7 are written protocols — live runs happen ONLY after owner GO per phase.

---

## Commit 0 — Preflight: Rourke reposition + surgeon docs (test-fixture only)

**File:** `engine/tests/llm2llm/personas.py`
- Move the Rourke dict (currently lines 444-477, END of `PERSONAS`) to INSIDE the happy-path block, immediately after Marcus. Zero text changes to the dict itself.
- Restores `test_happy_path_present_and_first` (SOP order: happy first) → suite 333 green.
- Also commits the four surgeon docs (`tasks/surgeon/iter55-tts-era-turn1-ammo/`) to the branch (LAW 0 v3: docs ride the branch).
- Rollback: `git revert` — no engine code involved.

## Commit 1 — T0: warm + greeting + await observability (no behavior change)

### 1a. `engine/diallux/config.py`
```python
# ---- iter55 T0: warm/greeting observability ------------------------------
# Emits Langfuse spans + info logs for prompt-cache warms (fire/complete/
# fail per shape), _await_warm outcomes, and the voice greeting runway.
# Pure observability — False restores the exact pre-T0 span surface.
warm_observability: bool = True
```
(Placed in the iter52/iter55 knob section. NOTE: F-02 duplicate block left untouched.)

### 1b. `engine/diallux/graph/llm.py` — un-swallow warm failures (F-08)
`warm()` (llm.py:234-244): REMOVE the internal try/except; keep a docstring note that callers (`_warm`) own failure handling. All 3 callers verified inside their own try/except (builder.py:421, 454, 467) — zero unhandled-exception risk; failures now reach `_warm`'s except → warning + lite retry (existing behavior) AND the diag record (new).

### 1c. `engine/diallux/graph/builder.py` — warm spans + await outcomes
1. `__init__`: add `self._warm_diag: dict[str, dict] = {}` (per-call degrade/error record).
2. `initial_state` (builder.py:2198): add `self._warm_diag.clear()`.
3. `warm_prompt_cache` (365-397): stamp `fired = time.time()` before `create_task`; after registering: `task.add_done_callback(self._make_warm_done_cb(key, state_name, lite, fired))`.
4. New method `_make_warm_done_cb(...)` — returns a callback that (fail-safe, own try/except):
   - computes `ms = round((time.time() - fired) * 1000)`, `outcome = ok` | `failed` (task.exception()) | `cancelled` (task.cancelled());
   - reads `diag = self._warm_diag.get(key)` → `degraded = diag.get("retried_lite", False)`, `error = diag.get("error")`;
   - emits `tracer.span(f"warm:{key}", metadata={"shape": "lite"|"full", "state": ..., "fired_at": fired, "ms": ms, "outcome": ..., "degraded": ..., "error": ...})` (only when `settings.warm_observability`) and ALWAYS `log.info("warm done key=%s shape=%s outcome=%s degraded=%s ms=%s", ...)`.
5. `_warm` except path (455-469): BEFORE the retry, record `self._warm_diag[key] = {"error": str(exc), "retried_lite": True}` (callback reads it at completion).
6. `_await_warm` (471-489): record outcome —
```python
task = self._latest_warm.get(state_name)
if task is None:            outcome, waited = "no_task", 0        # F-09
elif task.done():           outcome, waited = "already_done", 0
else:
    t0 = time.perf_counter()
    try: await asyncio.wait_for(asyncio.shield(task), wait_ms/1000); outcome, waited = "landed", ...
    except asyncio.TimeoutError: outcome, waited = "timeout", ...
    except Exception:       outcome, waited = "task_error", ...    # shield keeps warm alive
log.info("await_warm key=%s outcome=%s waited_ms=%s cap_ms=%s", ...)
if warm_observability: tracer.span("await_warm", metadata={key, outcome, waited_ms, cap_ms})
```

### 1d. `engine/diallux/media/session.py` — greeting spans (voice only, F-06 design)
1. `__init__`: `self._greet: dict | None = None`.
2. `start()` before `tts.speak(ctx, begin, ...)` (session.py:216): `self._greet = {"ctx": ctx, "t_stream": time.perf_counter(), "first_audio": None, "last_audio": None}`.
3. `_on_tts_audio` (654-662): if `self._greet and context_id == self._greet["ctx"]`: stamp `first_audio` (once) / `last_audio`; on FIRST stamp emit `tracer.span("greeting:first_audio", metadata={"stream_to_first_ms": ...})` (gated by `warm_observability`).
4. Follow-up task (mirrors `_late_turn_report` pattern, session.py:543): `asyncio.create_task(self._greeting_drain())` — sleeps ~7 s, then if `_greet["first_audio"]`: `tracer.span("greeting", metadata={"stream_to_first_ms", "audio_drain_ms": last_audio - first_audio, "total_ms": last_audio - stream_start})`. Dedicated anchors only — never touches the turn-0 clock.

### 1e. `engine/tests/test_iter55_observability.py` (new pins, ~10)
1. Warm span emitted with all fields (fake Tracer capture; stub `llm.warm`); key `lite:Intake` vs `Intake` shapes.
2. Failure path: stub `llm.warm` raising → span `outcome=failed`, `degraded=True` (lite retry fired), `_warm_diag` recorded.
3. `await_warm` outcomes: `no_task` / `already_done` / `landed` / `timeout` + waited_ms ≤ cap.
4. Greeting spans: stubbed TTS + `_on_tts_audio` with the begin ctx → `greeting:first_audio` + `greeting` drain fields.
5. `warm_observability=False` → ZERO new spans (exact pre-T0 Langfuse surface); logs still fire.
6. Zero behavior delta: latch semantics, `force=True` supersede, `aclose()` cancellation, entry-ack `pass` (builder.py:1382) all unchanged.
Suite gate: 333 + new pins, all green.

### 1f. T0 live verification protocol (AFTER owner GO — written, not run)
- CHAT: 1 harness run (`--personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini`) → Langfuse trace shows `warm:Intake`, `warm:lite:Intake`, `await_warm` spans.
- VOICE: 1 mic-bridge session (engine foreground, 127.0.0.1, free port; owner at browser per SOP exception) → `greeting:first_audio`, `greeting`, warm spans present.
- `git diff 054af7b -- diallux/` reviewed: observability-only.

## Commit 2 — T3 prerequisite: split lite warm cap (F-07)
- `config.py`: `prewarm_lite_max_completion_tokens: int = 64` (default = current behavior, byte-exact).
- `llm.py`: `_warm_llm_lite` twin (same kwargs, the lite cap); `warm(messages, tools, lite=False)` routes to it.
- Pins: lite warm uses the lite twin; full warm untouched by `PREWARM_LITE_MAX_COMPLETION_TOKENS`.
- Rollback: flag defaults reproduce today exactly.

## Commit 3 — T6 prerequisite (conditional authoring, default OFF)
`agent/prompts/prefill_fallback_head.md` (owner-approved copy ONLY) + `prefill_fallback: bool = False` + wiring in builder.py at the entry/warm-pending point + `tests/test_iter55_fallback.py` pins (fires only on warm-pending; no-tools shape; never chains; next-round cache>0). NOT executed unless T4 shows residual misses.

---

## T1 — Measured truth protocol (LIVE — owner ping at phase start + at table delivery)
1. **Ping** (Telegram): "T1 live phase starting: harness runs + cold probe."
2. Harness warm-span runs (chat): `cd /tmp/opencode/wt-iter55/engine && set -a && . ./.env && set +a` then `.venv/bin/python tests/llm2llm/harness.py --personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini` → warm spans ≥10 lite + ≥10 full completions.
3. True-cold rerun (`cold-probe-b`) ≥3.5 h provider idle — same command, letter-suffixed run id. NO back-to-back cold probes.
4. Ledger import from MAIN checkout (`live_sql.py import --run warm-span-a --commit <sha>` — the ROOT trap, hit twice in iter52).
5. Deliverable table (research/surgeon/iter55-era-truth/01_era_and_warm_p90.md): warm-completion p50/p90 × {lite, full} × {cold, warm}; ack p50/p90 (lite-class SQL, D1 method); greeting distribution (voice runs); :8000 snapshot already banked (D2).
6. **Ping**: table + the warm_rag/KB-resolve HITL decision inputs.

## T2 — Era A/B protocol (HITL)
- **Option A (autonomous):** pull existing micbridge traces (Sep 6/11/12) via `lf.py` — `e2aacc99471a` verified; re-resolve `43d83d0815c9` (F-03) — era-52 sample, n noted.
- **Option B (HITL, owner GO needed):** fresh mic sessions ×2 personas ×3 calls on the iter55 engine (foreground uvicorn, 127.0.0.1, free port). **Ping to schedule**: "T2-B needs you at a browser with a mic — 6 short calls."
- Era table: :8000 deployed-iter40 (banked D2) vs era-52 same-path; delta decomposed LLM-cache vs TTS/STT/carrier.

## T3 — O5 sweep protocol (LIVE — autonomous harness runs, ping at start)
- AFTER Commit 2: `PREWARM_LITE_MAX_COMPLETION_TOKENS=32` then `=16` (env prefix; unset = rollback). Full warm stays 64.
- Gate: zero `prewarm failed`/`warm done ... outcome=failed` ×20 lite warms; registration ms delta from T0 spans across the three settings.

## T4 — Turn-1 "ammo locked" probe (LIVE — true cold ×4)
- Sanity FIRST: T0 spans must show the greeting FULL warm completing BEFORE the turn-1 round fires (the mechanism under test).
- `FIRST_TURN_LITE=false` env prefix; ≥3.5 h idle; 4 calls lettered `ammo-a..d` (staggered per cold-probe discipline).
- Gate: turn-1 cache ≥2,688 ×4/4 AND TTFT ≤900 ms ×4/4; first-3-turns ≤900 steady.
- On miss: T0 data names the failure (silent fail / cold queue / registration lag) → **Ping** with the failure-mode verdict + decision ask (T6 fallback vs EOT wait-ceiling raise vs accept).

## T5 — Cold probe + warm battery (LIVE)
- `cold-probe-b` + `warm-battery-iter55` (Maria/Danny/Susan/Marcus, 15 s stagger). Cancel ALL test bookings after (Cal.com 3801235 is REAL; `--slots mock`).
- Gates: turn-1 cache ≥2,688 ×4/4 cold; battery cache-0 ≤3/call; steady TTFT p50 ≤950; first-3 ≤900; hear-band p50 ≤1,400. **Ping** results table.

## T6 — Fallback filler (CONDITIONAL on T4 miss — HITL copy approval)
- **Ping** owner with draft copy ("one moment, taking notes" ~700-900 tok, no tools). Wire ONLY after approval. Gates: fallback TTFT ≤700 ms cold; fires only warm-pending; no chaining; next round cache>0.

## T7 — Verdict + closeout (HITL)
- Report to `research/surgeon/iter55-era-truth/01_era_and_warm_p90.md`; ITERATIONS.md line; PT-51/PT-52 flips.
- **Ping ASK list**: merge iter52? merge iter55? keep `FIRST_TURN_LITE=false` default? **cutover authorization** (:8000 has never run the cache machine).

---

## Telegram HITL wiring (owner directive — NOTED, not wired)
- T0 execution step 1 = `engine/scripts/hitl_ping.py`: reads `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` (on file at `/home/julio/projects/video_strategy/.env`; copy values into `engine/.env` — gitignored — at execution time; NEVER commit). Pattern: `send_telegram()` in `video_strategy/execution/clients.py`.
- Ping points: T1 start + table; T2-B scheduling; T4 failure verdict; T6 copy approval; T5 results; T7 ASKs.
- Fail-safe: ping failure NEVER blocks engine work (log-and-continue), same contract as the tracer.
