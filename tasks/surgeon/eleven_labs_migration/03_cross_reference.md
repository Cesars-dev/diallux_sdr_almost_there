# 03 CROSS-REFERENCE — ElevenLabs TTS cutover (iter64)

> Surgeon Framework step 3. Compares `01_audit.md` (what's wrong) against
> `02_action_plan.md` (what we'll do). Every cell cites the plan section that
> addresses the audit item (or flags a gap). Result: **no gaps, 2 refinements**
> (see §C).

## A. Audit §B (protocol drifts) → plan coverage

| Audit | Severity | Plan fix | Covered |
|---|---|---|---|
| B1 `{"text":""}` flush closes socket → turn 2+ mute | HIGH | T1: text messages carry `flush:true`; `("",False)` marker → `close_context` only; T5 pin-test 3 (socket-killer guard: no context-less empty text EVER) | YES |
| B2 cancel sends `{"text":""}` → barge-in kills socket | HIGH | T1: `cancel()` = `close_context` (real server-side cancel); T5 pin-tests 4 | YES |
| B3 `ulaw_8000` hardcoded → browser lane static | HIGH | T1: `transport` param + `output_format = pcm_16000 / ulaw_8000`; factory passes transport (T5); pin-test 1 | YES |
| B4 `optimize_streaming_latency` deprecated | MEDIUM | T1 URL omits it; T4 removes `elevenlabs_latency_opt` (replaced by `elevenlabs_inactivity_timeout`); pin-test 1 asserts ABSENT | YES |
| B5 single-generation + `_live_context` guesswork | MEDIUM | T1: full multi-stream-input rewrite — native `context_id` contexts, recv routing by `contextId`, 5-context budget (we use 1/turn) | YES |
| B6 20s idle close | LOW | T1 `inactivity_timeout=180` (ws-level, T4 config) + `keepalive()` (`{"text":" "}`); T2 prewarm keepalive companion every 15s; LV-5 | YES |
| B7 `eleven_v3` unsupported on WS | LOW | No change: default stays `eleven_flash_v2_5` (config.py:381 verified); T4 touches only the timeout field | YES (no-op) |

## B. Audit §C (naive-swap breakage) + §E (adapter bugs) → plan coverage

| Audit | Plan fix | Covered |
|---|---|---|
| C1 prewarm Cartesia-hardcoded (paid idle sockets, protocol-mismatch adoption, dead phrase cache) | T2: `_spawn_idle_tts` branches on provider; EL URL via shared `connect_url()` (single source of truth); phrase cache gated to cartesia; pin-test 7 | YES |
| C2 session adoption `connect(ws=)` TypeError on EL | T1 adds `ws=` to `ElevenLabsTTS.connect()` → session.py:205-217 works for both providers UNCHANGED (preflight refinement R1 — see §C); pin-test 6 | YES |
| C3 browser lane garbage | = B3 | YES |
| C4 turn 2+ / barge-in mute | = B1/B2 | YES |
| C5 prewarm idle model inverted (EL 20s vs Cartesia ~20min) | T2 keepalive companion (15s `{"text":" "}` + drain) + `inactivity_timeout=180`; TTL 240 kept as hygiene bound; LV-5 | YES |
| C6 `tts_phone_style=spell` Cartesia-only | Preflight: default is `digits` (config.py:348) and `.env` sets nothing → NO change needed; LV-4 sanity-listens digit readback | YES (verify-only) |
| E1 empty-final-chunk convention vs flush redesign | T1 speak() maps `("",False)` → `close_context` (sentence_gate.py:71-73 contract preserved); pin-test 2 | YES |
| E2 `_dropped_contexts.clear()` on ANY isFinal | T1 `_handle_message`: `is_final` discards ONLY that `contextId`; pin-test 5 | YES |
| E3 `isFinal` vs `is_final` casing | Pinned from official multi-stream example: RECV = `contextId` + `is_final`; pin-test 5 + LV-3 live re-verify | YES |
| E4 no inactivity handling (>20s tool pause) | `inactivity_timeout=180` (T4/T1) + keepalive (T1/T2); LV-5 | YES |
| E5 `first_byte_ts` semantics | Kept verbatim in T1 rewrite (iter55 greeting anchors) | YES |

## C. Preflight refinements (plan BETTER than audit assumed — no contradictions)

| # | Refinement | Why safe |
|---|---|---|
| R1 | session.py needs NO code change (audit C2 proposed a gate; T1's `ws=` param makes the existing try/except-fresh-connect fallback sufficient for both providers) | Pool only contains provider-correct sockets after T2; adoption failure path already never fails a call |
| R2 | Flush strategy: `flush:true` on EVERY text message (docs best practice: flush at end of complete sentences) instead of end-of-turn-only flush | SentenceGate already emits complete sentences; maximizes TTFB; makes `chunk_length_schedule` moot; still pinned by tests |
| R3 | Keepalive on multi-stream: socket-level `{"text":" "}` (stream-input-documented shape) + ws-level `inactivity_timeout=180`; per-context `{"context_id","text":""}` keepalive NOT used (we close contexts at end of turn) | Documented levers only; the resolved decision "keepalive `{"text":" "}` every ~15s" is honored |
| R4 | `tts_factory.py` EL branch currently DROPS `transport` (tts_factory.py:19) — factory fix folded into T5 scope (one line) | Preflight-found; without it T1's transport-aware format never receives the lane |
| R5 | `test_tts_providers.py:101-180` pins the OLD protocol (incl. `texts.count("") == 1` at line 143) — rewrite is mandatory T5 scope, not optional | Suite cannot go green otherwise |

## D. Reverse check — does every plan change trace to an audit item?

| Plan | Traces to |
|---|---|
| T1 adapter rewrite | B1,B2,B3,B4,B5,B6,E1,E2,E3,E4,E5,C2,C3,C4 |
| T2 prewarm gating | C1,C5,B6 |
| T3 session.py no-change | C2 (resolution), audit §A1 "provider-agnostic session" claim verified |
| T4 config | B4 (remove latency_opt), B6/E4 (inactivity_timeout) |
| T5 tests | All of the above (pins) + R4/R5 |
| T6 live lane | E3 (LV-3), B3 (LV-4), B1 (LV-1), B2/B5 (LV-2), E4 (LV-5), C6 (LV-4) |

No unaddressed audit items. No plan changes without an audit driver. No contradictions found.
