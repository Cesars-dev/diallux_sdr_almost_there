# 01 AUDIT — ElevenLabs TTS cutover (iter63 codebase)

> Surgeon Framework step 1. Written 2026-09-22 against branch `engine/iter63-rag-fire-sim`
> (HEAD 2cb810f). Media layer is byte-identical between `engine/iter63-rag-fire-sim`
> and `main` (verified: `git diff --stat main...engine/iter63-rag-fire-sim` touches only
> RAG/tests/plans). All line numbers below must be re-verified in Surgeon step 4
> (preflight) against the NEW branch `engine/iter64-elevenlabs-cutover`.

## A. What EXISTS (trace summary)

### A1. Provider abstraction (working)
- `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/tts_factory.py` — `create_tts(settings, on_audio, transport)` returns `ElevenLabsTTS` when `settings.tts_provider == "elevenlabs"`, else `CartesiaTTS`. `tts_label()` handles both.
- `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/elevenlabs_tts.py` — full adapter, same 4-method contract as CartesiaTTS: `connect()` / `speak(context_id, text, continue_, overrides)` / `cancel(context_id)` / `close()` + `new_context_id()` + `first_byte_ts`.
- `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/cartesia_tts.py` — default provider; native contexts; `_PHRASE_CACHE` module dict (iter59 T5); `connect(ws=)` adoption support (iter59 T5).
- `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py` — provider-agnostic CallSession. SSML jitter already gated: `if text and self.settings.tts_provider == "cartesia"` (line ~776). TTS adoption path lines ~205-216.
- `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/delivery.py` — per-state profiles with SEPARATE `elevenlabs` columns (stability/style/speed) + clamps (0-1 / 0-1 / 0.7-1.2). No change needed.
- `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py:378-386` — EL env surface already defined: `elevenlabs_api_key`, `elevenlabs_voice_id` (empty default), `elevenlabs_model_id="eleven_flash_v2_5"`, `elevenlabs_latency_opt=2`, `elevenlabs_stability=0.55`, `elevenlabs_similarity_boost=0.8`, `elevenlabs_style=0.15`, `elevenlabs_speed=1.0`.
- `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/prewarm.py` — iter59 T5 pool + iter60 AUD-1 companion-cancel + iter61 AUD-11/12 (no keepalive on flux; TTL 240s respawn).

### A2. Existing EL adapter protocol (as written)
- Connect: `wss://api.elevenlabs.io/v1/text-to-speech/{voice}/stream-input?model_id={model}&output_format=ulaw_8000&optimize_streaming_latency={N}`; header `xi-api-key`; fallback `xi-api-key=` query param.
- Connect-time first message: `{"text": " ", "voice_settings": {...}}` (documented init slot).
- speak(): `{"text": chunk}`; per-context voice_settings on first message of context (`_settings_ctx` tracking); flush = `{"text": ""}` when `continue_=False`.
- cancel(): drop-flag `_dropped_contexts` + `{"text": ""}` to "reset socket".
- Recv loop: `{"audio": b64, "isFinal": bool}`; routes audio by `_live_context` (single generation at a time); swallowed audio for dropped contexts.

## B. What's WRONG vs current ElevenLabs docs (scraped 2026-09-22)

Sources: elevenlabs.io/docs llms.txt → realtime-tts guide, multi-context-web-socket guide, models overview, REST convert reference (append `.md` for clean markdown).

| # | Severity | Adapter behavior | Current docs truth | Consequence |
|---|---|---|---|---|
| B1 | HIGH | Turn-final flush = `{"text": ""}` | Empty text message **closes the WebSocket** (documented: "Send an empty string to close the WebSocket"). Correct end-of-turn flush = `{"text": <text>, "flush": true}` per-message. | After turn 1's flush, socket dies → turn 2+ mute (fresh connect per call would mask it, but breaks the one-socket-per-session design + prewarm). |
| B2 | HIGH | cancel() sends `{"text": ""}` | Same socket-close semantics; and stream-input has NO server-side cancel. | Barge-in during a generation kills the socket → mid-call mute. Drop-flag swallow alone is correct. |
| B3 | HIGH (browser lane) | `output_format=ulaw_8000` hardcoded in connect URL | `pcm_16000` (S16LE) is a valid EL output format | Owner's test lane `AUDIO_TRANSPORT=browser` plays raw PCM → ulaw bytes sound like static. Must mirror CartesiaTTS transport-aware format (`ulaw_8000` twilio / `pcm_16000` browser). |
| B4 | MEDIUM | `optimize_streaming_latency=N` query param | **Deprecated** per REST convert reference (2026) | Dead param; remove. Latency control now = model choice + `flush` + `chunk_length_schedule`. |
| B5 | MEDIUM (recommended fix) | Single-generation stream-input; `_live_context` guesswork; fake contexts | NEW endpoint `multi-stream-input` has native contexts: `context_id` per message, `{"context_id","close_context":true}` = real server-side cancel, `{"context_id","flush":true}` per-context flush, recv frames carry `contextId`, 5 concurrent contexts, 20s context inactivity timeout (raisable via `inactivity_timeout` query param up to 180s), `{"close_socket":true}` ends all. | Migrating gives the EXACT Cartesia context semantics the pipeline was designed around: real barge-in cancel, per-context audio routing (kills `_live_context`), no drop-flag hack. |
| B6 | LOW | — | 20s socket idle close; documented keepalive = send `{"text": " "}` (must contain a space). | Keepalive needed for prewarm + long tool-pauses mid-call. |
| B7 | LOW | — | `eleven_v3` NOT supported on stream-input/multi-stream-input WS. | Model must stay `eleven_flash_v2_5` (≈75ms, $0.05/1k chars) or `eleven_multilingual_v2` (best quality, higher TTFB). |

EL voice_settings schema (per REST reference): `stability` (default 0.5), `similarity_boost` (default 0.75), `style` (default 0), `speed` (default 1.0), `use_speaker_boost` (default true). Settable at init AND overridden per-message. Adapter's clamps (stability/style 0-1, speed 0.7-1.2) are within API ranges — keep.

## C. What breaks on a NAIVE env swap (`TTS_PROVIDER=elevenlabs` + keys)

- C1. **prewarm.py Cartesia-hardcoded** — `_spawn_idle_tts()` builds the Cartesia wss URL + `X-API-Key` header; `_warm_phrase_cache()` imports `CartesiaTTS` + `resolve_delivery("begin")` and writes `CartesiaTTS._PHRASE_CACHE`. With EL selected: idle Cartesia sockets still spawned (paid), session adopts a Cartesia WS into ElevenLabsTTS → protocol mismatch → **mute call 1** (worst class of bug; iter60 AUD-1 family). Phrase cache silently never used.
- C2. **session.py adoption calls `self.tts.connect(ws=tws)`** (lines ~205-216) — `ElevenLabsTTS.connect()` signature has NO `ws` param → TypeError → caught by the `except` → fallback fresh connect. Safe-ish, but prewarm gain lost + repeated exception logs.
- C3. **Browser lane audio garbage** (B3).
- C4. **Turn 2+ mute / barge-in mute** (B1/B2).
- C5. **Prewarm idle model inverted for EL** — Cartesia idles ~20min (iter61 AUD-12, TTL 240s); EL closes idle sockets at 20s. The pool needs an EL-specific keepalive (`{"text":" "}` ~every 15s) or TTS prewarm must be provider-gated.
- C6. `tts_phone_style="spell"` is Cartesia-only (`<spell>` tags); digits style is EL-correct (repo KB docs retell/heating-uk/.../uk_address_kb.md document EL hyphenation rules). Verify .env doesn't set spell when switching.

## D. What does NOT change (verified)

- Deepgram flux STT (unchanged), LangGraph graph/prompts/RAG (iter63 work orthogonal — media identical across branches), SentenceGate (flush contract maps to `flush:true`), barge-in session logic, `normalize_for_tts` (digits), token gate, mic bridge, Langfuse tracer, Twilio b64-ulaw passthrough, delivery profile tables (EL columns already tuned), `tts_factory` signature, CartesiaTTS itself (stays default until owner flips env).

## E. Bugs/risks found in existing EL code (beyond protocol drift)

- E1. `speak()` returns early `if not text and continue_` — fine; but with `flush:true` redesign the empty-final-chunk convention changes shape (gate always sends text with continue_=False except end-marker; see sentence_gate.py flush contract).
- E2. `_handle_message` clears `_dropped_contexts` on ANY `isFinal` — with multi-stream-input, per-context `is_final` must clear only that context.
- E3. Recv `isFinal` vs `is_final` casing differs between stream-input (camelCase, per official guide) and multi-stream-input examples (`is_final`) — must pin per endpoint, verify live.
- E4. No `inactivity_timeout` handling: a long tool-call pause (>20s) mid-context would silently drop the context. Map to `inactivity_timeout=180` query param + keepalive.
- E5. `first_byte_ts` semantics preserved (needed by iter55 greeting anchors + telemetry) — keep in rewrite.

## F. Environment / versions

- websockets 16.1.1 (engine venv /home/julio/projects/clean_diallux_SDR/engine/.venv) — concurrent recv() raises ConcurrencyError (iter60 AUD-1): any adopted-socket design must cancel companion drain FIRST (prewarm.get already does).
- EL auth: `xi-api-key` header (stream-input supports `xi_api_key` JSON field fallback — shown in official init example).
- EL regional hosts exist (api.us.elevenlabs.io etc.) — default global host fine; note for latency work.
- UNKNOWN (BLOCKED for live tests): owner's `ELEVENLABS_API_KEY` + Chloe `ELEVENLABS_VOICE_ID` — read from /home/julio/projects/clean_diallux_SDR/engine/.env (may already exist there) or owner supplies.

## G. Audit conclusion

The provider swap is REAL and plannable: adapter exists, factory exists, profiles exist, env surface exists. The work is: (1) rewrite the adapter onto `multi-stream-input` with transport-aware output + flush/close_context semantics + ws= adoption, (2) provider-gate prewarm + EL keepalive, (3) gate session TTS adoption, (4) pin-file tests, (5) owner-driven live verify. Estimated surface: 4 engine files + 1 test file + .env. No graph/prompt/RAG changes.
