# 04 MASTER PLAN — ElevenLabs TTS cutover (iter64) — AIRTIGHT, AWAITING OWNER GO

> Surgeon Framework step 4 output. Preflight completed 2026-09-22 against
> worktree `/tmp/opencode/wt-iter64-ela` (branch `engine/iter64-elevenlabs-cutover`,
> forked from `engine/iter63-rag-fire-sim` @ 2cb810f — media layer byte-identical
> to main, per handoff §0). **Status: PLAN ONLY. No engine code touched.**
> Companion SOP plan file (TOP-PRIORITY MIGRATION, repo root): `/home/julio/projects/clean_diallux_SDR/e-even_labs_migration/master_plan_to_migrate_provider.md`.
> Execution starts ONLY after owner approval (LAW 0).

## P. Preflight verification (every audit claim re-traced against the branch)

| Claim (from 01_audit.md / handoff) | Verified at | Verdict |
|---|---|---|
| EL adapter exists, 4-method contract | `/tmp/opencode/wt-iter64-ela/engine/diallux/media/elevenlabs_tts.py:65-214` | CONFIRMED |
| `{"text":""}` flush in speak | elevenlabs_tts.py:157 | CONFIRMED (the killer) |
| `{"text":""}` in cancel | elevenlabs_tts.py:181 | CONFIRMED |
| `ulaw_8000` hardcoded | elevenlabs_tts.py:86 | CONFIRMED |
| `optimize_streaming_latency` in URL | elevenlabs_tts.py:87 | CONFIRMED |
| EL connect() has no `ws=` param | elevenlabs_tts.py:82 | CONFIRMED |
| Factory drops transport for EL | `/tmp/opencode/wt-iter64-ela/engine/diallux/media/tts_factory.py:19` | CONFIRMED (new finding R4) |
| Session TTS adoption `connect(ws=tws)` | `/tmp/opencode/wt-iter64-ela/engine/diallux/media/session.py:205-217` | CONFIRMED |
| SSML jitter gated to cartesia | session.py:775-777 | CONFIRMED |
| Browser lane decodes b64 → raw PCM | session.py:802-803 | CONFIRMED (format-agnostic) |
| Barge-in: gate.reset + tts.cancel(ctx) | session.py:523-525, 544-546, 576-578; new ctx per turn at :621 | CONFIRMED (cancel maps 1:1 to close_context) |
| Gate closing marker `("", False)` | `/tmp/opencode/wt-iter64-ela/engine/diallux/media/sentence_gate.py:71-73` | CONFIRMED (exactly the message that kills the EL socket today) |
| Prewarm Cartesia-hardcoded | `/tmp/opencode/wt-iter64-ela/engine/diallux/media/prewarm.py:97-124` (spawner), `:143-200` (phrase cache imports CartesiaTTS at :149) | CONFIRMED |
| PREWARM_SOCKET_TTL=240 + companion cancel in get() | prewarm.py:38, 298-307 | CONFIRMED (T2 reuses both) |
| EL env surface at config.py:378-386 | `/tmp/opencode/wt-iter64-ela/engine/diallux/config.py:378-386` | CONFIRMED exact |
| `tts_phone_style` default digits, not spell | config.py:348 | CONFIRMED (C6 verify-only) |
| `.env`: `TTS_PROVIDER=cartesia`, `AUDIO_TRANSPORT=browser`, zero `ELEVENLABS_*` | `/home/julio/projects/clean_diallux_SDR/engine/.env` (+ root `/home/julio/projects/.env` also zero) | CONFIRMED → keys are BLOCKED (owner supplies) |
| test_tts_providers.py pins OLD EL protocol | `/tmp/opencode/wt-iter64-ela/engine/tests/test_tts_providers.py:101-180` (`texts.count("") == 1` at :143) | CONFIRMED (R5: rewrite mandatory) |
| Multi-stream-input message schema | Official example fetched live 2026-09-22 (preflight): SEND snake_case `context_id`/`flush`/`close_context`/`close_socket`; RECV `contextId`+`is_final`; keepalive `{"text":" "}`; `inactivity_timeout` ws-level ≤180 | PINNED (E3 resolved on paper; LV-3 re-verifies live) |
| Suite baseline 422 green (iter63) | Handoff pinned fact | CITED (worktree needs `.venv` symlink + `.env` copy before first run) |

All flaws found during preflight are resolved in 02_action_plan.md (refinements R1-R5,
cross-referenced in 03_cross_reference.md §C). Zero open issues in the plan itself.

## B. BLOCKED / NEEDS INPUT (owner)

| Item | Where to get it |
|---|---|
| `ELEVENLABS_API_KEY` | Owner (absent from every `.env` on the box — verified) |
| `ELEVENLABS_VOICE_ID` (Chloe clone) | Owner (ElevenLabs dashboard → voice) |
| Approval to execute T1-T5 on `engine/iter64-elevenlabs-cutover` | Owner (this document) |
| T6 live lane go-ahead (browser mic test call) | Owner (after suite green) |
| T7 production-grade verdict on the Cartesia lane | Owner (llm2llm ladder + SQL gates + owner ears) — **this is the cutover gate: no EL switch before it** |

## T. Task order (full detail in 02_action_plan.md)

| # | Task | Files (absolute) | Gate |
|---|---|---|---|
| T4 | config: `elevenlabs_latency_opt` → `elevenlabs_inactivity_timeout=180` | `/tmp/opencode/wt-iter64-ela/engine/diallux/config.py` | import OK |
| T1 | Adapter rewrite onto multi-stream-input (contexts, flush-on-sentence, close_context barge-in, transport-aware format, `ws=` adoption, `keepalive()`, shared `connect_url()`) | `/tmp/opencode/wt-iter64-ela/engine/diallux/media/elevenlabs_tts.py` | import OK + pin-tests 1-6,8 |
| T5a | Factory passes transport (1 line) | `/tmp/opencode/wt-iter64-ela/engine/diallux/media/tts_factory.py` | pin-test 6 |
| T5b | Rewrite EL block (4 old-protocol tests) + NEW pin file `test_iter64_elevenlabs_cutover.py` (≈8 hermetic FakeWS pins) | `/tmp/opencode/wt-iter64-ela/engine/tests/test_tts_providers.py`, `/tmp/opencode/wt-iter64-ela/engine/tests/test_iter64_elevenlabs_cutover.py` | full suite green (≥422+new, 0 fail) |
| T2 | Prewarm provider gate + EL keepalive companion + phrase-cache gate | `/tmp/opencode/wt-iter64-ela/engine/diallux/media/prewarm.py` | pin-test 7 + suite green |
| T6 | Live browser-mic lane: LV-1 turn-2 audio, LV-2 barge-in, LV-3 recv casing, LV-4 pcm_16000 listen + digits readback, LV-5 idle>20s | worktree engine, foreground 127.0.0.1 free port (never :8000-8003) | owner ears + ledger import |
| T7 | Cartesia production-grade battery (the cutover gate): llm2llm ladder on `TTS_PROVIDER=cartesia` (happy → stress → curve → gatekeepers → breakers; assassin only gated), SQL ledger import + `live_sql.py gates` green, 3-SOP call-quality audit — the EL switch happens ONLY once the owner verdicts the Cartesia lane production-grade | worktree or main-checkout engine per SOP | ledger gates + owner verdict "production grade" |
| T8 | Provider flip (the actual cutover): owner sets `TTS_PROVIDER=elevenlabs` + EL keys in the live `.env`, one more T6-style live lane check on EL, then commit the `.env` change decision + ITERATIONS.md verdict — rollback = flip back to `cartesia` (adapter stays byte-identical) | `/home/julio/projects/clean_diallux_SDR/engine/.env` (owner) | T7 verdict + owner say-so (LAW 0) |

Worktree setup (before first test run, iter44 pattern): `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter64-ela/engine/.venv` + `cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter64-ela/engine/.env` (then owner adds the two EL keys for T6 only).

## V. Validation plan (end-to-end)

1. Hermetic: `cd /tmp/opencode/wt-iter64-ela/engine && .venv/bin/python -m pytest tests -q` — 0 failures, count = 422 + pin tests (4 old EL tests rewritten in place).
2. Old-protocol extinction: `grep -n 'stream-input' /tmp/opencode/wt-iter64-ela/engine/diallux/media/elevenlabs_tts.py` → only in comments/docstrings; `grep -n '"text": ""' …elelabs_tts.py` → ZERO hits (socket-killer shape gone).
3. Cartesia lane untouched: `git diff engine/iter63-rag-fire-sim -- engine/diallux/media/cartesia_tts.py engine/diallux/media/session.py engine/diallux/media/delivery.py engine/diallux/media/sentence_gate.py` → EMPTY (session/delivery/gate byte-identical; cartesia_tts byte-identical).
4. Live (T6, owner): LV-1..LV-5 checklist; Langfuse trace `micbridge-*` TTFB sane; ledger import `--run iter64-ela-smoke --commit <sha>`; autopsy to `/home/julio/projects/clean_dialux_SDR/research/surgeon/iter64-elevenlabs-cutover/` on any failure.
5. T7 cutover gate: Cartesia production-grade battery per the iteration SOP (llm2llm ladder, ledger import, `scripts/live_sql.py gates --a <a> --b <b>` named queries green, 3-SOP call-quality audit) — owner records the production-grade verdict BEFORE the provider flip.
6. Report + commits on branch `engine/iter64-elevenlabs-cutover` → ASK JULIO before any merge (LAW 0). `scripts/keyhound` before any push. No Cal.com bookings involved (mock fixtures only, per SOP).

## D. Deferred / not in this plan

| Item | Why |
|---|---|
| EL phrase cache (greeting pre-record for EL) | Resolved decision: Cartesia-only first cut; EL greeting rides the normal flush path; revisit only if LV-4 TTFB is unacceptable |
| Auto-reconnect on mid-call socket death | inactivity_timeout=180 covers all call-lifetime gaps; parity with CartesiaTTS (no auto-reconnect there either) |
| `eleven_multilingual_v2` quality A/B | Owner tuning decision after cutover, env-only (`ELEVENLABS_MODEL_ID`) |
| SSML/pronunciation dictionaries (`enable_ssml_parsing`) | Not used by current prompts; new scope if wanted |
| Twilio lane LIVE phone test | ulaw_8000 covered hermetically; live phone check at owner's discretion |
| Merge to main / tag `engine/iter64` | Owner-gated (LAW 0) |
