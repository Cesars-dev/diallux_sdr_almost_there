# Plan v5 iter66 — ElevenLabs TTS cutover (Cartesia → ElevenLabs, multi-stream-input) — FRESH BRANCH

## Meta
- Date: 2026-09-22
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: Switch the voice agent's TTS provider from Cartesia to ElevenLabs by rewriting the EL adapter onto the multi-stream-input WebSocket with native contexts, provider-gating prewarm, and hermetic pin tests — no graph/prompt/RAG changes.
- Status: IN PROGRESS (owner-approved execution 2026-09-22: "start the plan, branch from main, a clear new branch, iter66; key comes later; local only — no push").
- This plan supersedes `e-even_labs_migration/master_plan_to_migrate_provider.md` (its branch `engine/iter64-elevenlabs-cutover` is STALE — cut from iter63 before the ladder merged, zero commits; reusing it violates LAW 0 v2.1).

## Compaction Context

- Repo `/home/julio/projects/clean_diallux_SDR` (fork of Retell_AI_MCP_connection, the MAIN workspace; original still serves :8000-8003 — never run services from the fork on those ports). Engine = LangGraph 9-state voice agent "Linda" at `/home/julio/projects/clean_diallux_SDR/engine/` (Deepgram flux STT → gpt-5.4 → gates → TTS → ws; transports: `AUDIO_TRANSPORT=browser` pcm_s16le@16k test lane (current `.env`) or twilio ulaw@8000).
- Branch state 2026-09-22: main tip = `09bf87b` (docs LAW 0 v2.1); ladder merge `40b3b40` merged iter52..64c into main (suite **427** green, batteries 9/9, mic live, tag engine/iter64). main is 46 commits ahead of origin — **OWNER: NO PUSH, local only this session**. Owner's current work branch `engine/iter65-model-defaults` (worktree `/tmp/opencode/wt-iter65`) is OFF-LIMITS — do not touch it.
- Owner directives this session (2026-09-22, verbatim intent): a NEW clear branch from main (not stacked on an existing one) — `engine/iter66-elevenlabs-cutover`; write the plan first; owner supplies `ELEVENLABS_API_KEY` (+ Chloe `ELEVENLABS_VOICE_ID`) after the plan; same WebSocket approach (multi-stream-input); branch stands on its own, merge later by owner say-so; no push right now.
- Migration background (all previously audited and CONFIRMED against main tip this session): the EL adapter EXISTS (`/home/julio/projects/clean_diallux_SDR/engine/diallux/media/elevenlabs_tts.py`, 214 lines) but was written against an OLDER EL docs generation (stream-input). Four protocol drifts: `{"text":""}` now CLOSES the WebSocket (adapter uses it as flush AND in cancel → turn 2+ mute, barge-in kills audio); no server-side cancel on stream-input; `output_format=ulaw_8000` hardcoded (browser test lane needs `pcm_16000`); `optimize_streaming_latency` deprecated. Plus: prewarm.py is Cartesia-hardcoded (protocol-mismatch adoption = mute call 1), EL idle-kills sockets at 20s vs Cartesia ~20min.
- Full surgeon dossier with EXACT code patterns: `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/eleven_labs_migration/02_action_plan.md` (§0 pinned protocol facts, §1 full adapter rewrite code, §2 prewarm gate code, §5 pins). Audit: `01_audit.md`; cross-reference: `03_cross_reference.md`; old master plan: `04_master_plan.md`.
- Multi-stream-input message schema re-pinned live from official docs (2026-09-22 session): SEND snake_case `context_id`/`flush`/`close_context`/`close_socket`; RECV `contextId`+`is_final`; keepalive `{"text":" "}`; ws-level `inactivity_timeout` ≤180s; 5 concurrent contexts; flush-on-sentence = documented best practice.
- Preflight refinements R1-R5 (still valid): session.py needs NO code change (T2's `ws=` adoption support absorbs audit C2); `tts_factory.py:19` drops `transport` for EL (one-liner fix); `tts_phone_style=spell` is Cartesia-only (default `digits` is EL-correct — verify-only).

## Resolved Decisions (DO NOT revisit)

| Decision | Rationale |
|---|---|
| Fresh branch `engine/iter66-elevenlabs-cutover` forked from main tip `09bf87b`, worktree `/tmp/opencode/wt-iter66` | LAW 0 v2.1: never stack onto an existing iteration branch; owner ordered a clear new branch from main |
| Migrate adapter to `multi-stream-input` WS | Native contexts = exact Cartesia semantics (real barge-in cancel, per-context audio routing); docs-current |
| Output format transport-aware: `ulaw_8000` twilio / `pcm_16000` browser | Matches CartesiaTTS; browser lane is the owner's test lane |
| Flush strategy: `flush:true` on EVERY text message (sentence boundary) | Official best practice; SentenceGate already emits complete sentences; optimal TTFB |
| `("", False)` gate closing marker → `close_context` only | Empty context-less text is the socket-killer shape |
| Prewarm provider-gated; EL keepalive `{"text":" "}` every 15s; `inactivity_timeout=180` | EL 20s idle close documented; keepalive+timeout are the documented levers |
| Phrase cache Cartesia-only (gate off for EL) | Lowest-risk first cut; EL greeting via normal flush path |
| Model default `eleven_flash_v2_5`; `optimize_streaming_latency` removed | Deprecated param; Flash = lowest latency ($0.05/1k chars) |
| session.py / delivery.py / sentence_gate.py / cartesia_tts.py byte-identical | Preflight: C2 absorbed by T2 `ws=`; profiles already EL-tuned; gate is provider-agnostic |
| `.env` provider stays `cartesia` until owner flips after live pass | Rollback = one env var |
| Local only — NO push, NO merge to main | Owner directive 2026-09-22 |

## BLOCKED / NEEDS INPUT

| Item | Where to get it |
|---|---|
| `ELEVENLABS_API_KEY` | Owner (will supply after this plan; verified absent from `/home/julio/projects/clean_diallux_SDR/engine/.env` and `/home/julio/projects/.env`) |
| `ELEVENLABS_VOICE_ID` (Chloe clone) | Owner (ElevenLabs dashboard) |
| T7 live lane go | Owner, after suite green |
| Merge consent | Owner (LAW 0), after live pass |

## Environment & Dependencies

- Python `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12); websockets **16.1.1** (concurrent-recv ConcurrencyError lesson, iter60 AUD-1 — companion drain tasks MUST be cancelled before socket adoption); pytest **9.1.1**; pydantic-settings 2.x (unknown env keys ignored → removing `elevenlabs_latency_opt` is `.env`-safe).
- Worktree: `/tmp/opencode/wt-iter66` (branch `engine/iter66-elevenlabs-cutover` @ `09bf87b`). BEFORE first test run: `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter66/engine/.venv` and `cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter66/engine/.env` (iter44 pattern).
- EL endpoint: `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/multi-stream-input?model_id={model}&output_format={fmt}&inactivity_timeout={s}`; auth header `xi-api-key` (query-param fallback). SEND: `{"text","context_id"[,"voice_settings"[,"flush"]]}`, `{"context_id","close_context":true}`, `{"close_socket":true}`, keepalive `{"text":" "}`. RECV: `{"audio","contextId","is_final"}`. 5 concurrent contexts; context inactivity 20s default (param ≤180s).
- Cartesia reference (unchanged default until owner flips `TTS_PROVIDER`): voice Linda `829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30`, sonic-3.6, `wss://api.cartesia.ai/tts/websocket?cartesia_version=2026-08-14`.
- `.env` today: `TTS_PROVIDER=cartesia`, `AUDIO_TRANSPORT=browser`, no `ELEVENLABS_*` keys.
- Engine test server pattern: foreground uvicorn on a FREE 127.0.0.1 port (historic :8007/:8021/:8022); live infra :8001-8003 is READ-ONLY (original workspace).
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (import via `scripts/live_sql.py`); reports to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter66-elevenlabs-cutover/`.

## Architecture (one block diagram)

```
mic(/mic ws, browser pcm16@16k) ──┐
                                   ├─> CallSession (session.py, provider-agnostic, UNCHANGED)
twilio media ws (ulaw@8k) ────────┘        │
         DeepgramSTT (flux) ──> graph (gpt-5.4, RAG iter63) ──> SentenceGate ──> tts.speak(ctx, text, continue_, overrides)
                                                                                          │
                           tts_factory (TTS_PROVIDER) ────────────────────────────────────┤
                         ┌─────────────────────────┴────────────────────────┐
                   CartesiaTTS (UNCHANGED)                      ElevenLabsTTS (T2 REWRITE)
                   contexts native                              multi-stream-input: context_id/flush/close_context
                   pcm_mulaw | pcm_s16le                        ulaw_8000 | pcm_16000 (transport-aware)
                         └─────────────────────────┬────────────────────────┘
                              prewarm pool (T5: provider-gated spawn, EL keepalive 15s, phrase cache cartesia-only)
                                                   └──> on_audio(b64, ctx) ──> twilio media frames | /mic raw PCM
```

## File Map

| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter66/engine/diallux/config.py` | `elevenlabs_latency_opt: int = 2` → `elevenlabs_inactivity_timeout: int = 180` (line 381 region) | Edit |
| `/tmp/opencode/wt-iter66/engine/diallux/media/elevenlabs_tts.py` | Full rewrite onto multi-stream-input: `connect_url()` helper + `EL_KEEPALIVE_S=15`; `__init__(settings, on_audio, transport=None)` with `output_format` pcm_16000/ulaw_8000; `connect(ws=None)` adoption; `speak()` text+flush+close_context; `cancel()` close_context; `keepalive()`; `close()` sends close_socket; `_handle_message` routes by `contextId`/`is_final` | Edit (rewrite) |
| `/tmp/opencode/wt-iter66/engine/diallux/media/tts_factory.py` | Line 19: pass `transport=transport` to ElevenLabsTTS | Edit (1 line) |
| `/tmp/opencode/wt-iter66/engine/diallux/media/prewarm.py` | `_spawn_idle_tts` (line 97) provider branch + new `_spawn_idle_tts_elevenlabs` (shared `connect_url`, keepalive+drain companion in `_companion_tasks`, line 34); `_warm_phrase_cache` (line 143) cartesia-only gate; maintainer re-spawn path (~line 276) inherits the branch automatically | Edit |
| `/tmp/opencode/wt-iter66/engine/tests/test_tts_providers.py` | Rewrite EL block (starts line 104) to new protocol; Cartesia block untouched | Edit |
| `/tmp/opencode/wt-iter66/engine/tests/test_iter66_elevenlabs_cutover.py` | Pin file: URL/format/latency-param-absent, message sequence, socket-killer guard, cancel+contextId routing, is_final casing, ws= adoption + factory transport, prewarm gate + companion cancel, keepalive shape | New |
| `/tmp/opencode/wt-iter66/engine/.env` | (T7 only, owner) `TTS_PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | Edit (owner) |
| NOT touched | `session.py`, `cartesia_tts.py`, `delivery.py`, `sentence_gate.py`, graph/prompts/RAG, mic bridge, tracer, token gate, owner's `engine/iter65-model-defaults` worktree | — |

## Deploy Rules

- All code on branch `engine/iter66-elevenlabs-cutover` (worktree `/tmp/opencode/wt-iter66`); commits `iter66: <task> — <one line>`; NO merge to main without owner say-so (LAW 0).
- NEVER bind :8000-8003 or start services from the fork; T7 = foreground uvicorn on a free 127.0.0.1 port only.
- Secrets only in `.env` (gitignored); **NO push this session** (owner directive); keyhound before any future push.
- Cartesia stays the default provider (`TTS_PROVIDER=cartesia`) until owner flips it after the live pass.
- No production agent IDs, no live validator, no Cal.com real bookings (event 3801235 is REAL — mock fixtures only; cancel ALL test bookings after any battery).

## Tasks (in order)

### T1 — config surface
- Goal: replace deprecated latency param with inactivity timeout.
- Files: `/tmp/opencode/wt-iter66/engine/diallux/config.py`
- Commands: edit line ~381: `elevenlabs_latency_opt: int = 2` → `elevenlabs_inactivity_timeout: int = 180`
- Dependencies: none (first — T2 adapter imports it)
- Verification: `cd /tmp/opencode/wt-iter66/engine && .venv/bin/python -c "from diallux.config import Settings; s=Settings(); assert s.elevenlabs_inactivity_timeout == 180"`

### T2 — adapter rewrite (multi-stream-input)
- Goal: fix all four protocol drifts; Cartesia-equivalent semantics.
- Files: `/tmp/opencode/wt-iter66/engine/diallux/media/elevenlabs_tts.py` (exact code patterns in `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/eleven_labs_migration/02_action_plan.md` §1)
- Commands: rewrite per action plan; module docstring updated to multi-stream protocol
- Dependencies: T1
- Verification: import check + pin-tests 1-6,8 pass (T4)

### T3 — factory one-liner
- Goal: stop dropping `transport` for EL (preflight R4).
- Files: `/tmp/opencode/wt-iter66/engine/diallux/media/tts_factory.py` line 19 → `return ElevenLabsTTS(settings, on_audio, transport=transport)`
- Dependencies: T2
- Verification: pin-test 6 (factory builds EL with correct output_format per transport)

### T4 — tests (rewrite + pin file)
- Goal: hermetic protocol pins; suite green.
- Files: `/tmp/opencode/wt-iter66/engine/tests/test_tts_providers.py` (EL block from line 104 rewritten), `/tmp/opencode/wt-iter66/engine/tests/test_iter66_elevenlabs_cutover.py` (new, FakeWS seam from test_tts_providers.py:28-48; 8 pins listed in action plan §5)
- Commands: `cd /tmp/opencode/wt-iter66/engine && .venv/bin/python -m pytest tests -q`
- Dependencies: T2, T3; worktree setup first (`.venv` symlink + `.env` copy, see Environment)
- Verification: 0 failed; count = 427 + new pins − 0 (4 EL tests rewritten in place)

### T5 — prewarm provider gate
- Goal: fix C1/C5 — no Cartesia sockets when EL selected; EL pool survives 20s idle close.
- Files: `/tmp/opencode/wt-iter66/engine/diallux/media/prewarm.py` (branch in `_spawn_idle_tts` line 97 + new `_spawn_idle_tts_elevenlabs` + `_warm_phrase_cache` line 143 gate; exact code in action plan §2)
- Dependencies: T2 (imports `connect_url`, `EL_KEEPALIVE_S`)
- Verification: pin-test 7 + full suite green

### T6 — commit + report
- Goal: snapshot the working branch; write the iteration report.
- Files: report to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter66-elevenlabs-cutover/`
- Commands: `git -C /tmp/opencode/wt-iter66 add -A engine && git -C /tmp/opencode/wt-iter66 commit -m "iter66: ElevenLabs multi-stream-input cutover — adapter rewrite, factory transport, prewarm gate, pins"`
- Dependencies: T4, T5 green
- Verification: `git -C /tmp/opencode/wt-iter66 log --oneline -1` = iter66 commit; untouched-lane proof: `git -C /home/julio/projects/clean_diallux_SDR diff engine/iter66-elevenlabs-cutover -- engine/diallux/media/session.py engine/diallux/media/cartesia_tts.py engine/diallux/media/delivery.py engine/diallux/media/sentence_gate.py` → empty

### T7 — live verification lane (OWNER-DRIVEN)
- Goal: prove the cutover on the real wire with the owner's keys.
- Files: `/tmp/opencode/wt-iter66/engine/.env` (owner adds `TTS_PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`; optionally `CALL_PREWARM=true`)
- Commands: foreground engine on free 127.0.0.1 port; browser mic call ≥3 turns + mid-sentence barge-in
- Dependencies: T6 + BLOCKED items supplied
- Verification: LV-1 turn-2+ audio & no end-of-turn truncation; LV-2 barge-in instant stop + clean next turn; LV-3 recv casing `contextId`/`is_final` in logs; LV-4 browser audio intelligible + digit readback; LV-5 idle >20s socket adoptable. Ledger: `cd /tmp/opencode/wt-iter66/engine && .venv/bin/python scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run iter66-ela-smoke --commit <sha>`; report to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter66-elevenlabs-cutover/`; ASK JULIO before merge.

## Validation Plan (end-to-end)

1. Hermetic suite green (T4 gate) — 0 failures, baseline 427.
2. Extinction greps: no `'"text": ""'` in `/tmp/opencode/wt-iter66/engine/diallux/media/elevenlabs_tts.py`; `stream-input` only in comments; `optimize_streaming_latency` absent from URL builder.
3. Untouched-lane proof (T6): diff vs main on session.py / cartesia_tts.py / delivery.py / sentence_gate.py → empty.
4. T7 live checklist LV-1..LV-5 (owner ears) + Langfuse `micbridge-*` trace TTFB + ledger import verified by SQL.
5. Post-battery ritual: refresh branch registry from the MAIN checkout (`scripts/call_ledger.py`), keyhound before any future push, ITERATIONS.md verdict line if abandoned.

## Deferred / Not In This Plan

| Item | Why |
|---|---|
| EL phrase cache (greeting pre-record) | Cartesia-only first cut (resolved decision); revisit if LV-4 TTFB unacceptable |
| Mid-call auto-reconnect | inactivity_timeout=180 covers call-lifetime gaps; parity with CartesiaTTS |
| `eleven_multilingual_v2` quality A/B | Owner tuning, env-only, post-cutover |
| SSML / pronunciation dictionaries | Unused by current prompts; separate scope |
| Twilio number live phone test | ulaw_8000 pinned hermetically; separate iteration (`iter67` candidate) — owner scoped it out of this branch |
| Push / merge to main / tag `engine/iter66` | LAW 0 — owner-gated; local only this session |
