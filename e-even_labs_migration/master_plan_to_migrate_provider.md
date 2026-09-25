# Plan v5 iter64 — ElevenLabs TTS cutover (Cartesia → ElevenLabs, multi-stream-input)

## Meta
- Date: 2026-09-22
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: Switch the voice agent's TTS provider from Cartesia to ElevenLabs by rewriting the EL adapter onto the multi-stream-input WebSocket with native contexts, provider-gating prewarm, and hermetic pin tests — no graph/prompt/RAG changes.
- Status: PLAN ONLY (not started — awaits approval). TOP-PRIORITY MIGRATION — kept OUT of the surgeon report folders at owner request. Full surgeon dossier (audit + action plan + cross-reference + master plan): `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/eleven_labs_migration/`.

## Compaction Context

- Repo `/home/julio/projects/clean_diallux_SDR` (fork of Retell_AI_MCP_connection, the MAIN workspace; original still serves :8000-8003 — never run services from the fork on those ports). Engine = LangGraph 9-state voice agent "Linda" at `/home/julio/projects/clean_diallux_SDR/engine/` (Deepgram flux STT → gpt-5.4 → gates → TTS → ws; transports: `AUDIO_TRANSPORT=browser` pcm_s16le@16k test lane (current `.env`) or twilio ulaw@8000).
- Branch state: `main` (docs + production code, diverged from origin 12/5 — do NOT merge/push without owner); `engine/iter63-rag-fire-sim` @ 2cb810f (RAG fixes only; media layer byte-identical to main; "probably our last iter" per owner). Suite 422 green on iter63. NEW branch `engine/iter64-elevenlabs-cutover` created from iter63 via worktree `/tmp/opencode/wt-iter64-ela` (2026-09-22, this session).
- Owner request (verbatim intent): iter63 is likely the last iter; use the Surgeon Framework to plan switching TTS from Cartesia to ElevenLabs — "it's not just a basic env swap, we are changing providers so a couple things might not work" — on a new branch, docs in `tasks/surgeon/eleven_labs_migration/`, execution in a later session after approval.
- Audit verdict (already written, `01_audit.md`): the EL adapter EXISTS (`engine/diallux/media/elevenlabs_tts.py`) and is wired via `tts_factory.py` (`TTS_PROVIDER=elevenlabs`), delivery profiles (`delivery.py` EL columns), config env surface (`config.py:378-386`) — but was written against an OLDER EL docs generation. Four protocol drifts: `{"text":""}` now CLOSES the WebSocket (adapter uses it as flush AND in cancel → turn 2+ mute, barge-in kills audio); no server-side cancel on stream-input; `output_format=ulaw_8000` hardcoded (browser test lane needs `pcm_16000`); `optimize_streaming_latency` deprecated. Plus: prewarm.py is Cartesia-hardcoded (protocol-mismatch adoption = mute call 1), EL idle-kills sockets at 20s vs Cartesia ~20min, `tts_phone_style=spell` is Cartesia-only (default `digits` is EL-correct — verify-only).
- This session (2026-09-22) completed the Surgeon procedure: worktree + branch created; preflight verified every audit claim against the branch (all confirmed; 5 refinements R1-R5, notably session.py needs NO code change because T1's `ws=` adoption support absorbs audit C2, and `tts_factory.py:19` drops `transport` for EL — factory one-liner folded into T5); multi-stream-input message schema re-pinned live from official docs (SEND snake_case `context_id`/`flush`/`close_context`/`close_socket`; RECV `contextId`+`is_final`; keepalive `{"text":" "}`; ws-level `inactivity_timeout` ≤180s; 5 concurrent contexts; flush-on-sentence = documented best practice). 02_action_plan.md, 03_cross_reference.md, 04_master_plan.md written — zero open issues.
- What remains: owner approval → execute T4→T1→T5→T2 on the branch → suite green → commit → T6 owner-driven live browser-mic verification (BLOCKED on owner's `ELEVENLABS_API_KEY` + Chloe `ELEVENLABS_VOICE_ID` — absent from every `.env` on the box, verified) → report + ledger import → ASK before merge (LAW 0).
- Working doctrine: `engine/AGENTS.md` LAW 0 — code = branch + test + report, owner-gated merge; docs = straight to main. Evidence to `research/` (gitignored). websockets 16.1.1: concurrent recv() raises ConcurrencyError — companion drain tasks MUST be cancelled before socket adoption (prewarm.get already does).

## Resolved Decisions (DO NOT revisit)

| Decision | Rationale |
|---|---|
| Plan via Surgeon Framework in `tasks/surgeon/eleven_labs_migration/` | Owner instruction |
| Branch `engine/iter64-elevenlabs-cutover` forked from `engine/iter63-rag-fire-sim`, worktree `/tmp/opencode/wt-iter64-ela` | Owner: new branch; iter63 RAG fixes must ride along; engine/iterNN convention |
| Migrate adapter to `multi-stream-input` WS | Native contexts = exact Cartesia semantics (real barge-in cancel, per-context audio routing); docs-current |
| Output format transport-aware: `ulaw_8000` twilio / `pcm_16000` browser | Matches CartesiaTTS; browser lane is the owner's test lane |
| Flush strategy: `flush:true` on EVERY text message (sentence boundary) | Official best practice; SentenceGate already emits complete sentences; optimal TTFB |
| `("", False)` gate closing marker → `close_context` only | Empty context-less text is the socket-killer shape |
| Prewarm provider-gated; EL keepalive `{"text":" "}` every 15s; `inactivity_timeout=180` | EL 20s idle close documented; keepalive+timeout are the documented levers |
| Phrase cache Cartesia-only (gate off for EL) | Lowest-risk first cut; EL greeting via normal flush path |
| Model default `eleven_flash_v2_5`; `optimize_streaming_latency` removed | Deprecated param; Flash = lowest latency ($0.05/1k chars) |
| session.py / delivery.py / sentence_gate.py / cartesia_tts.py byte-identical | Preflight: C2 absorbed by T1 `ws=`; profiles already EL-tuned; gate is provider-agnostic |
| Docs committed to main; CODE waits for owner-approved plan | LAW 0 |

## BLOCKED / NEEDS INPUT

| Item | Where to get it |
|---|---|
| `ELEVENLABS_API_KEY` | Owner (verified absent from `/home/julio/projects/clean_diallux_SDR/engine/.env` and `/home/julio/projects/.env`) |
| `ELEVENLABS_VOICE_ID` (Chloe clone) | Owner (ElevenLabs dashboard) |
| Execution go (T1-T5) | Owner approval of this plan |
| T6 live lane go | Owner, after suite green |
| T7 production-grade verdict on the Cartesia lane | Owner (llm2llm ladder + SQL gates + owner ears) — the cutover gate: no EL switch before it |

## Environment & Dependencies

- Python `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12); websockets **16.1.1** (concurrent-recv ConcurrencyError lesson, iter60 AUD-1); pytest **9.1.1**; pydantic-settings 2.x (unknown env keys ignored → removing `elevenlabs_latency_opt` is `.env`-safe).
- Worktree: `/tmp/opencode/wt-iter64-ela` (branch `engine/iter64-elevenlabs-cutover` @ fork of 2cb810f). BEFORE first test run: `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter64-ela/engine/.venv` and `cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter64-ela/engine/.env` (iter44 pattern, `/home/julio/projects/clean_diallux_SDR/plans/plan_iter44_cache_floor.md`).
- EL endpoints: `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/multi-stream-input?model_id={model}&output_format={fmt}&inactivity_timeout={s}`; auth header `xi-api-key` (query-param fallback). SEND: `{"text","context_id"[,"voice_settings"[,"flush"]]}`, `{"context_id","close_context":true}`, `{"close_socket":true}`, keepalive `{"text":" "}`. RECV: `{"audio","contextId","is_final"}`. 5 concurrent contexts; context inactivity 20s default (param ≤180s).
- Cartesia reference (unchanged default until owner flips `TTS_PROVIDER`): voice Linda `829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30`, sonic-3.6, `wss://api.cartesia.ai/tts/websocket?cartesia_version=2026-08-14`.
- `.env` today: `TTS_PROVIDER=cartesia`, `AUDIO_TRANSPORT=browser`, no `ELEVENLABS_*` keys.
- Engine test server pattern: foreground uvicorn on a FREE 127.0.0.1 port (historic :8007/:8021); live infra :8001-8003 is READ-ONLY (original workspace).
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (import via `scripts/live_sql.py`); reports to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter64-elevenlabs-cutover/`.

## Architecture (one block diagram)

```
mic(/mic ws, browser pcm16@16k) ──┐
                                  ├─> CallSession (session.py, provider-agnostic, UNCHANGED)
twilio media ws (ulaw@8k) ────────┘        │
        DeepgramSTT (flux) ──> graph (gpt-5.4, RAG iter63) ──> SentenceGate ──> tts.speak(ctx, text, continue_, overrides)
                                                                                        │
                          tts_factory (TTS_PROVIDER) ────────────────────────────────────┤
                        ┌─────────────────────────┴────────────────────────┐
                  CartesiaTTS (UNCHANGED)                      ElevenLabsTTS (T1 REWRITE)
                  contexts native                              multi-stream-input: context_id/flush/close_context
                  pcm_mulaw | pcm_s16le                        ulaw_8000 | pcm_16000 (transport-aware)
                        └─────────────────────────┬────────────────────────┘
                             prewarm pool (T2: provider-gated spawn, EL keepalive 15s, phrase cache cartesia-only)
                                                  └──> on_audio(b64, ctx) ──> twilio media frames | /mic raw PCM
```

## File Map

| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter64-ela/engine/diallux/config.py` | `elevenlabs_latency_opt: int = 2` → `elevenlabs_inactivity_timeout: int = 180` (line 382 region) | Edit |
| `/tmp/opencode/wt-iter64-ela/engine/diallux/media/elevenlabs_tts.py` | Full rewrite onto multi-stream-input: `connect_url()` helper + `EL_KEEPALIVE_S=15`; `__init__(settings, on_audio, transport=None)` with `output_format` pcm_16000/ulaw_8000; `connect(ws=None)` adoption; `speak()` text+flush+close_context; `cancel()` close_context; `keepalive()`; `close()` sends close_socket; `_handle_message` routes by `contextId`/`is_final` | Edit (rewrite) |
| `/tmp/opencode/wt-iter64-ela/engine/diallux/media/tts_factory.py` | Line 19: pass `transport=transport` to ElevenLabsTTS | Edit (1 line) |
| `/tmp/opencode/wt-iter64-ela/engine/diallux/media/prewarm.py` | `_spawn_idle_tts` provider branch + new `_spawn_idle_tts_elevenlabs` (shared `connect_url`, keepalive+drain companion in `_companion_tasks["tts"]`); `_warm_phrase_cache` cartesia-only gate | Edit |
| `/tmp/opencode/wt-iter64-ela/engine/tests/test_tts_providers.py` | Rewrite EL block (lines 101-180) to new protocol; Cartesia block untouched | Edit |
| `/tmp/opencode/wt-iter64-ela/engine/tests/test_iter64_elevenlabs_cutover.py` | Pin file: URL/format/latency-param-absent, message sequence, socket-killer guard, cancel+contextId routing, is_final casing, ws= adoption + factory transport, prewarm gate + companion cancel, keepalive shape | New |
| `/tmp/opencode/wt-iter64-ela/engine/.env` | (T6 only, owner) `TTS_PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | Edit (owner) |
| NOT touched | `session.py`, `cartesia_tts.py`, `delivery.py`, `sentence_gate.py`, graph/prompts/RAG, mic bridge, tracer, token gate | — |

## Deploy Rules

- All code on branch `engine/iter64-elevenlabs-cutover` (worktree `/tmp/opencode/wt-iter64-ela`); commits `iter64: <task> — <one line>`; NO merge to main without owner say-so (LAW 0).
- NEVER bind :8000-8003 or start services from the fork; T6 = foreground uvicorn on a free 127.0.0.1 port only.
- Secrets only in `.env` (gitignored); run `scripts/keyhound` before any push; no push of `main` (diverged 12/5).
| Cartesia stays the default provider (`TTS_PROVIDER=cartesia`) until owner flips it after T6 passes.
- **Cutover gate (T7): the EL switch happens ONLY after the Cartesia lane hits production grade** — llm2llm ladder + SQL ledger gates + owner verdict (owner directive 2026-09-22).
- No production agent IDs, no live validator, no Cal.com real bookings (event 3801235 is REAL — mock fixtures only).

## Tasks (in order)

### T1 — config surface
- Goal: replace deprecated latency param with inactivity timeout.
- Files: `/tmp/opencode/wt-iter64-ela/engine/diallux/config.py`
- Commands: edit line ~382: `elevenlabs_latency_opt: int = 2` → `elevenlabs_inactivity_timeout: int = 180`
- Dependencies: none (first — T1 adapter imports it)
- Verification: `cd /tmp/opencode/wt-iter64-ela/engine && .venv/bin/python -c "from diallux.config import Settings; s=Settings(); assert s.elevenlabs_inactivity_timeout == 180"`

### T2 — adapter rewrite (multi-stream-input)
- Goal: fix B1-B5, E1-E5; Cartesia-equivalent semantics.
- Files: `/tmp/opencode/wt-iter64-ela/engine/diallux/media/elevenlabs_tts.py` (exact code patterns in `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/eleven_labs_migration/02_action_plan.md` §1)
- Commands: rewrite per action plan; module docstring updated to multi-stream protocol
- Dependencies: T1
- Verification: import check + pin-tests 1-6,8 pass (T4)

### T3 — factory one-liner
- Goal: stop dropping `transport` for EL (preflight R4).
- Files: `/tmp/opencode/wt-iter64-ela/engine/diallux/media/tts_factory.py` line 19 → `return ElevenLabsTTS(settings, on_audio, transport=transport)`
- Dependencies: T2
- Verification: pin-test 6 (factory builds EL with correct output_format per transport)

### T4 — tests (rewrite + pin file)
- Goal: hermetic protocol pins; suite green.
- Files: `/tmp/opencode/wt-iter64-ela/engine/tests/test_tts_providers.py` (EL block 101-180 rewritten), `/tmp/opencode/wt-iter64-ela/engine/tests/test_iter64_elevenlabs_cutover.py` (new, FakeWS seam from test_tts_providers.py:28-48; 8 pins listed in action plan §5)
- Commands: `cd /tmp/opencode/wt-iter64-ela/engine && .venv/bin/python -m pytest tests -q`
- Dependencies: T2, T3; worktree setup first (`.venv` symlink + `.env` copy, see Environment)
- Verification: 0 failed; count = 422 + new pins − 0 (4 EL tests rewritten in place)

### T5 — prewarm provider gate
- Goal: fix C1/C5 — no Cartesia sockets when EL selected; EL pool survives 20s idle close.
- Files: `/tmp/opencode/wt-iter64-ela/engine/diallux/media/prewarm.py` (branch in `_spawn_idle_tts` + `_spawn_idle_tts_elevenlabs` + `_warm_phrase_cache` gate; exact code in action plan §2)
- Dependencies: T2 (imports `connect_url`, `EL_KEEPALIVE_S`)
- Verification: pin-test 7 + full suite green

### T6 — live verification lane (OWNER-DRIVEN)
- Goal: prove the cutover on the real wire.
- Files: `/tmp/opencode/wt-iter64-ela/engine/.env` (owner adds `TTS_PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`; optionally `CALL_PREWARM=true`)
- Commands: foreground engine on free 127.0.0.1 port; browser mic call ≥3 turns + mid-sentence barge-in
- Dependencies: T4 suite green + BLOCKED items supplied
- Verification: LV-1 turn-2+ audio & no end-of-turn truncation (fallback: defer close_context); LV-2 barge-in instant stop + clean next turn; LV-3 recv casing `contextId`/`is_final` in logs; LV-4 browser audio intelligible + digit readback; LV-5 idle >20s socket adoptable. Ledger: `cd /tmp/opencode/wt-iter64-ela/engine && .venv/bin/python scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run iter64-ela-smoke --commit <sha>`; report to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter64-elevenlabs-cutover/`; ASK JULIO before merge.

### T7 — Cartesia production-grade battery (the cutover gate)
- Goal: prove the CURRENT (Cartesia) lane is production-grade — owner precondition for the provider flip.
- Files: none changed (measurement only); evidence to `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter64-elevenlabs-cutover/`
- Commands: `cd /tmp/opencode/wt-iter64-ela/engine && set -a; . ./.env; set +a; .venv/bin/python scripts/lf_eval.py ladder` (happy → stress → curve → gatekeepers → breakers; assassin only gated); then ledger import + gates: `.venv/bin/python scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run iter64-cartesia-prod --commit <sha>` and `.venv/bin/python scripts/live_sql.py gates --a <a> --b <b>`
- Dependencies: T4 suite green (the branch is safe to run regardless of provider; Cartesia lane byte-identical to iter63)
- Verification: happy-path gate first (never stress a broken flow), SQL gates green (named queries, never "feels okay"), 3-SOP call-quality audit (`sop_call_analysis` skill), owner verdict "production grade" recorded. Battery ritual: cancel ALL test bookings after (Cal.com event 3801235 is REAL).

### T8 — Provider flip (the actual cutover)
- Goal: switch the live lane to ElevenLabs once T7 verdicts production grade.
- Files: `/home/julio/projects/clean_diallux_SDR/engine/.env` (owner): `TTS_PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`
- Commands: owner edits `.env`; one T6-style live browser-mic lane check on EL; ITERATIONS.md verdict line
- Dependencies: T7 production-grade verdict + owner say-so (LAW 0) + EL keys supplied
- Verification: live call LV-1..LV-5 checklist on EL; rollback = flip `TTS_PROVIDER` back to `cartesia` (CartesiaTTS untouched throughout)

## Validation Plan (end-to-end)

1. Hermetic suite green (T4 gate) — 0 failures.
2. Extinction greps: no `'"text": ""'` in `/tmp/opencode/wt-iter64-ela/engine/diallux/media/elevenlabs_tts.py`; `stream-input` only in comments; `optimize_streaming_latency` absent from URL builder.
3. Untouched-lane proof: `git -C /home/julio/projects/clean_diallux_SDR diff engine/iter63-rag-fire-sim engine/iter64-elevenlabs-cutover -- engine/diallux/media/session.py engine/diallux/media/cartesia_tts.py engine/diallux/media/delivery.py engine/diallux/media/sentence_gate.py` → empty.
4. T6 live checklist LV-1..LV-5 (owner ears) + Langfuse `micbridge-*` trace TTFB + ledger import verified by SQL.
5. T7 gate: Cartesia battery — ladder + ledger import + `scripts/live_sql.py gates` named queries green + 3-SOP audit; production-grade verdict recorded BEFORE any flip.
6. Post-battery ritual: refresh branch registry from the MAIN checkout (`scripts/call_ledger.py` per repo AGENTS.md), keyhound before any push, ITERATIONS.md verdict line if abandoned.

## Deferred / Not In This Plan

| Item | Why |
|---|---|
| EL phrase cache (greeting pre-record) | Cartesia-only first cut (resolved decision); revisit if LV-4 TTFB unacceptable |
| Mid-call auto-reconnect | inactivity_timeout=180 covers call-lifetime gaps; parity with CartesiaTTS |
| `eleven_multilingual_v2` quality A/B | Owner tuning, env-only, post-cutover |
| SSML / pronunciation dictionaries | Unused by current prompts; separate scope |
| Twilio lane live phone test | ulaw_8000 pinned hermetically; live check at owner discretion |
| Merge to main / tag `engine/iter64` | LAW 0 — owner-gated |
