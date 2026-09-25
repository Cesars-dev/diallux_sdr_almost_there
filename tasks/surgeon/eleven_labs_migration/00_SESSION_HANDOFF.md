# SESSION HANDOFF — ElevenLabs TTS Migration (iter64 candidate)

> This file is the FULL context of the 2026-09-22 session that produced the
> ElevenLabs cutover audit. A FRESH agent (no prior chat) must be able to pick
> up from this file alone, load /home/julio/projects/SURGEON_FRAMEWORK.md, and
> execute the Surgeon procedure in
> /home/julio/projects/clean_diallux_SDR/tasks/surgeon/eleven_labs_migration/
> (01_audit.md already EXISTS — pre-written by the session that produced this
> handoff; steps 02–04 + execution remain).

---

## 0. Project & state (facts, do not re-derive)

- Repo: /home/julio/projects/clean_diallux_SDR (git, the MAIN workspace; fork of Retell_AI_MCP_connection).
- Branches:
  - `main` — has all docs + production code merged. Diverged from origin/main (12 local / 5 remote commits). Do NOT merge without owner approval (LAW 0).
  - `engine/iter63-rag-fire-sim` — HEAD 2cb810f, iter63 = RAG retrieval fixes ONLY (scripts/rag_replay.py, RAG_FIRE_MODE=hybrid lane-fire sim, test_iter63_rag_fire_sim.py). **This is "probably our last iter" per owner.**
- The iter63 branch vs main diff touches RAG/tests/plans ONLY — the media layer (TTS/STT) is byte-identical between the two branches. Verified via `git ls-tree` + diff stat.
- Engine: LangGraph 9-state voice agent "Linda" at /home/julio/projects/clean_diallux_SDR/engine/
  - Pipeline: Deepgram flux STT → gpt-5.4 → gates → TTS → ws. Transport: `AUDIO_TRANSPORT=browser` (test lane, pcm_s16le@16k) or twilio (ulaw@8000).
  - Suite: 422 tests green on iter63 (iter62 line + 9-pin file).
- Working doctrine: engine/AGENTS.md LAW 0 — code = branch + test + report, owner-gated merge; docs = branch + amend.

## 1. The owner request (verbatim intent)

"we are on iter 63 which is going to be most probably our last iter... the iter 63 branch just fixing the RAG retrieval... use scrapling to check eleven labs docs... see how can we use that instead of cartesia and what we need to change the provider... audit iter63 main code for the voice agent and check what do we need to connect elevenlabs properly with the current behaviour (no mess... it's not just a basic env swap, we are changing providers so, a couple things might not work)"

=> Owner wants: a SURGEON procedure (audit → action plan → cross-reference → master plan) for switching TTS from Cartesia to ElevenLabs, planned as code edits on a NEW BRANCH, documented in a NEW subfolder `eleven_labs_migration`. Execution happens in a NEW SESSION using this handoff.

## 2. What this session already produced

### 2a. The surgeon folder (already created)

/home/julio/projects/clean_diallux_SDR/tasks/surgeon/eleven_labs_migration/
- `01_audit.md` — WRITTEN (the full audit, see §2b summary). Read it first.
- `00_SESSION_HANDOFF.md` — this file.
- 02_action_plan.md / 03_cross_reference.md / 04_master_plan.md — TO BE WRITTEN by the fresh agent per SURGEON_FRAMEWORK.md steps 2–4.

### 2b. Audit verdict (summary — full detail in 01_audit.md)

The ElevenLabs adapter ALREADY EXISTS and is wired:
- /home/julio/projects/clean_diallux_SDR/engine/diallux/media/elevenlabs_tts.py — ElevenLabsTTS, same 4-method contract as CartesiaTTS (connect/speak/cancel/close + new_context_id + first_byte_ts).
- /home/julio/projects/clean_diallux_SDR/engine/diallux/media/tts_factory.py — `TTS_PROVIDER=elevenlabs|cartesia` env switch.
- Delivery profiles (engine/diallux/media/delivery.py) already carry ElevenLabs columns (stability/style/speed per state).
- session.py is provider-agnostic; SSML jitter already gated to `tts_provider == "cartesia"` (session.py:776).
- .env keys already defined in engine/diallux/config.py:378-386 (elevenlabs_api_key, voice_id, model_id default `eleven_flash_v2_5`, latency_opt=2, stability 0.55, similarity_boost 0.8, style 0.15, speed 1.0).

BUT the adapter was written against an OLDER ElevenLabs docs generation. Fresh docs scraped 2026-09-22 (elevenlabs.io/docs — llms.txt + realtime-tts + multi-context-web-socket + models + REST convert reference) prove 4 protocol drifts:

1. **HIGH — `{"text": ""}` now CLOSES the whole WebSocket.** Adapter sends `{"text":""}` as the turn-final flush (speak, continue_=False) and inside cancel(). On stream-input WS the empty string terminates the socket → **turn 2+ is mute / barge-in kills the audio path**. The documented end-of-turn flush is `{"text": <text>, "flush": true}` per-message.
2. **HIGH — no server-side cancel** on stream-input is still true; adapter's drop-flag swallow is the right idea but must not send `""`.
3. **HIGH for browser lane — output format hardcoded to `ulaw_8000`** (connect URL). Browser mic transport (the owner's test lane) plays pcm_s16le@16k → needs `pcm_16000` when `AUDIO_TRANSPORT=browser`, mirroring CartesiaTTS transport-aware output_format.
4. **MEDIUM — `optimize_streaming_latency` query param is now DEPRECATED** per REST convert reference. Remove; rely on model choice + flush.
5. **Recommended (medium) — migrate adapter to `multi-stream-input` WS** (new endpoint): native per-context semantics nearly identical to Cartesia contexts — `context_id` per message, `close_context: true` = real barge-in cancel, `flush` per context, recv frames echo `contextId`, 5 concurrent contexts, context 20s inactivity timeout (up to 180s via `inactivity_timeout` query param), `close_socket: true` to end. This makes EL semantically equal to the Cartesia context model the whole pipeline was designed around (real server-side barge-in, per-context audio routing, no `_live_context` guesswork).
6. **20s socket idle close** — documented keepalive: send `{"text": " "}` (a SPACE; bare `""` closes). Adapter already does this in places — keep, and use it for prewarm keepalive.
7. `eleven_v3` is NOT supported on stream-input/multi-stream-input WS. Use `eleven_flash_v2_5` (≈75ms, $0.05/1k chars) or `eleven_multilingual_v2` (best quality, higher TTFB). Owner's "Chloe" voice = cloned voice; settings live in .env ELEVENLABS_*.

### 2c. What breaks on a naive env swap (the "no mess" list)

- **prewarm.py is Cartesia-hardcoded**: `_spawn_idle_tts()` builds the Cartesia URL/headers; `_warm_phrase_cache()` imports CartesiaTTS directly and stashes into `CartesiaTTS._PHRASE_CACHE`. With TTS_PROVIDER=elevenlabs: idle Cartesia sockets keep being paid for, and the session would adopt a Cartesia WS into an EL adapter → protocol mismatch → mute call 1. Also iter61 AUD-12: Cartesia idle-times-out silent sockets ~20min; EL kills idle sockets at 20s — the prewarm TTL model (PREWARM_SOCKET_TTL=240) must be re-derived for EL (likely: keepalive `{"text":" "}` every ~15s).
- **session.py:205-216 TTS adoption**: pops `pool["tts"]` and calls `self.tts.connect(ws=tws)` — ElevenLabsTTS.connect() does NOT accept `ws=` → exception → fallback fresh connect (safe but broken prewarm + error logs). Either add `ws=` to EL connect or gate adoption to cartesia.
- **Browser lane format** (item 3 above).
- **tts_phone_style "spell"** is Cartesia-only (`<spell>` tags) — digits style is EL-correct (EL v2 reads hyphenated chars; repo KB docs uk_address_kb.md document the EL hyphenation rules).
- Cartesia `emotion`/`volume` have no EL equivalent — already handled by separate profile columns; nothing to change.

### 2d. What does NOT change

Deepgram flux STT, LangGraph graph/prompts, RAG (iter63 work is orthogonal), sentence gate, barge-in session logic, normalize_for_tts (digits), token gate, mic bridge, Langfuse tracer, Twilio b64-ulaw passthrough (phone lane), delivery profile tables (EL columns already tuned), tts_factory signature.

## 3. Resolved decisions (owner + session, DO NOT revisit)

| Decision | Rationale |
|---|---|
| Plan via Surgeon Framework in tasks/surgeon/eleven_labs_migration/ | Owner instruction ("use the SURGEON_FRAMEWORK.md") |
| New branch for the code edits, named `engine/iter64-elevenlabs-cutover` (fork from `engine/iter63-rag-fire-sim`) | Owner: "on a new branch"; iter63 is the last iter and its RAG fixes must ride along; naming follows engine/iterNN-* convention |
| Migrate adapter to `multi-stream-input` WS | Native contexts = exact Cartesia semantics; fixes barge-in properly; docs-current |
| Output format transport-aware: `ulaw_8000` twilio / `pcm_16000` browser | Matches CartesiaTTS behavior; browser lane must keep working |
| Prewarm: gate TTS prewarm to provider; EL keepalive `{"text":" "}` every ~15s | EL 20s idle close is documented |
| Phrase cache: Cartesia-only initially (gate off for EL) | Lowest-risk first cut; EL greeting via normal flush path |
| Model default stays `eleven_flash_v2_5`; `optimize_streaming_latency` removed | Docs: deprecated param; Flash = lowest latency |
| Docs (this handoff + audit) can be committed to main per LAW 0 docs rule; CODE waits for owner-approved master plan | engine/AGENTS.md LAW 0 |

## 4. Key pinned facts (verified this session, trust as-is)

- websockets lib: 16.1.1 in engine venv (/home/julio/projects/clean_diallux_SDR/engine/.venv). Concurrent recv() raises ConcurrencyError (iter60 AUD-1 lesson) — any adopted-socket design must cancel companion drain tasks first.
- Cartesia voice Linda `829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30`, sonic-3.6, wss api.cartesia.ai/tts/websocket?cartesia_version=2026-08-14, X-API-Key header, api_key= query fallback.
- EL endpoints: `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=...` and `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/multi-stream-input?model_id=...`; auth header `xi-api-key` (fallback `xi_api_key` field in first JSON message). Recv: `{"audio": <b64>, "isFinal": true}` (stream-input) / `{"audio":..., "contextId":..., "is_final":...}` (multi-stream-input — note the casing difference between the two endpoints as shown in official examples).
- EL voice_settings: stability (default 0.5), similarity_boost (default 0.75), style (default 0), speed (default 1.0), use_speaker_boost (bool). Settable at init and overridden per-message.
- EL `generation_config.chunk_length_schedule` = chars-before-generate schedule (default e.g. [120,160,250,290]); `flush: true` forces generation of buffered text; pronunciation dictionaries need `enable_ssml_parsing=true` query param.
- EL docs index: https://elevenlabs.io/docs/llms.txt (append .md to any page URL for clean markdown). Full text: https://elevenlabs.io/docs/llms-full.txt.
- Session pin: mic lane = browser AudioWorklet 16k PCM; engine test server historically :8007/:8021; prewarm flag settings.call_prewarm; phrase cache flag settings.tts_phrase_cache (default True).
- UNKNOWN (goes in BLOCKED table of the plan): the owner's ELEVENLABS_API_KEY and Chloe ELEVENLABS_VOICE_ID — read from /home/julio/projects/clean_diallux_SDR/engine/.env or root /home/julio/projects/.env; if absent, BLOCKED — owner supplies.

## 5. Fresh-agent runbook (what to do in the new session)

1. Read, in order: /home/julio/projects/SURGEON_FRAMEWORK.md → /home/julio/projects/clean_diallux_SDR/engine/AGENTS.md → /home/julio/projects/clean_diallux_SDR/tasks/surgeon/eleven_labs_migration/01_audit.md → this file.
2. Load skill: new-plan (Plan SOP) — the final artifact combines Surgeon docs with a plans/ file per SOP (absolute paths everywhere; compaction context = this handoff).
3. Create branch: from /home/julio/projects/clean_diallux_SDR run
   `git worktree add /tmp/opencode/wt-iter64-ela -b engine/iter64-elevenlabs-cutover engine/iter63-rag-fire-sim`
   (worktree pattern used by iter43-iter63; .venv symlink + .env copy pattern from plan_iter44_cache_floor.md:48).
4. Write 02_action_plan.md (code edits, per-file, with exact function signatures), 03_cross_reference.md, 04_master_plan.md per the framework. Re-verify every line-number claim against the branch (preflight rule).
5. STOP for owner approval before touching engine code (framework step 5). Docs (surgeon folder + plan file) may be committed on the branch.
6. Suggested task breakdown for the action plan (from audit):
   - T1 elevenlabs_tts.py → multi-stream-input rewrite (contexts, close_context, flush, contextId routing, transport-aware output format, ws= adoption support)
   - T2 prewarm.py → provider-gated TTS prewarm + EL keepalive (~15s `{"text":" "}`) + phrase-cache gating
   - T3 session.py adoption gate (only adopt when adapter supports ws=; else fresh connect, no error spam)
   - T4 config.py / .env surface (drop latency_opt or repurpose; add elevenlabs_inactivity_timeout if needed)
   - T5 tests (pin file test_iter64_elevenlabs_cutover.py: hermetic fake-WS pins for contexts/flush/barge-in/adoption/browser-format; suite must stay green)
   - T6 live verification lane (browser mic on test port + twilio format check) — owner-driven per LAW 0
7. Deliverable at end of new session: airtight 04_master_plan.md + (after approval) executed branch with green suite.

## 6. Source docs scraped this session (for citation in the plan)

- https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts.md (stream-input guide: flush:true, "" closes socket, " " keepalive, voice_settings per-message, chunk_length_schedule)
- https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/multi-context-web-socket.md (multi-stream-input: contexts, close_context, contextId, 5 concurrent, 20s/180s timeouts, close_socket)
- https://elevenlabs.io/docs/overview/capabilities/text-to-speech.md (models: Flash v2.5 ≈75ms; ulaw/pcm output formats)
- https://elevenlabs.io/docs/api-reference/text-to-speech/convert.md (optimize_streaming_latency deprecated; voice_settings schema; output_format enum incl. ulaw_8000, pcm_16000)
