# 02 ACTION PLAN — ElevenLabs TTS cutover (iter64)

> Surgeon Framework step 2. Written 2026-09-22 against branch
> `engine/iter64-elevenlabs-cutover` (worktree `/tmp/opencode/wt-iter64-ela`,
> forked from `engine/iter63-rag-fire-sim` @ 2cb810f). Every line number below
> was re-verified in the worktree (preflight done — see 04_master_plan.md §P).
> Target protocol: ElevenLabs **multi-stream-input** WebSocket (docs scraped
> 2026-09-22, schema re-pinned live in preflight — see §0).

## 0. Pinned protocol facts (multi-stream-input, from official example + guides)

Endpoint:
`wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/multi-stream-input?model_id={model}&output_format={fmt}&inactivity_timeout={s}`
Auth: `xi-api-key` header (fallback `xi-api-key=` query param — pattern already used by both adapters).

SEND (all keys snake_case):
| Purpose | Message |
|---|---|
| text into a context (first msg may carry `voice_settings`) | `{"text": <s>, "context_id": <id>[, "voice_settings": {...}]}` |
| force generation of buffered text | `{"context_id": <id>, "flush": true}` (or ride `"flush": true` on a text message) |
| barge-in / done with a context | `{"context_id": <id>, "close_context": true}` |
| keep a context alive (resets its 20s clock) | `{"context_id": <id>, "text": ""}` |
| end everything | `{"close_socket": true}` |

RECV: `{"audio": <b64>, "contextId": <id>, "is_final": <bool>}` — **`contextId` camelCase,
`is_final` snake_case** (differs from stream-input's `isFinal`; pinned from the official
Python/JS examples; LV-3 re-verifies live).

Limits: 5 concurrent contexts per socket (we use 1 per turn, closed at end of turn → max 1 open).
`inactivity_timeout` is a **websocket-level** query param, default 20s, max 180s.
Socket keepalive (stream-input guide, same message shape works here): `{"text": " "}` — a bare
`""` text closes the socket on stream-input; NEVER send a context-less `{"text": ""}`.
Models: `eleven_flash_v2_5` (default, ≈75ms) | `eleven_multilingual_v2`. `eleven_v3` NOT supported.
`optimize_streaming_latency` is DEPRECATED (removed from URL).
Docs best practice (quoted): "stream text in smaller chunks and use the `flush: true` flag at the
end of complete sentences" → our SentenceGate already emits complete sentences → **every text
message carries `flush: true`** (max responsiveness; makes `chunk_length_schedule` moot).

## 1. T1 — Rewrite `/tmp/opencode/wt-iter64-ela/engine/diallux/media/elevenlabs_tts.py` onto multi-stream-input

**Goal:** real server-side contexts = Cartesia semantics; fix B1–B5; transport-aware output;
`ws=` adoption.

New module surface (exact):

```python
EL_KEEPALIVE_S = 15          # prewarm keepalive cadence (see T2)

def connect_url(settings, output_format: str) -> str:
    """Single source of truth for the connect URL (adapter + prewarm share it —
    kills the duplication that caused audit C1)."""
    return (f"wss://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
            f"/multi-stream-input?model_id={settings.elevenlabs_model_id}"
            f"&output_format={output_format}"
            f"&inactivity_timeout={settings.elevenlabs_inactivity_timeout}")

class ElevenLabsTTS:
    def __init__(self, settings, on_audio: OnAudio, transport: str | None = None):
        # transport-aware output format (B3): browser lane plays raw PCM
        self.transport = transport or settings.audio_transport
        self.output_format = "pcm_16000" if self.transport == "browser" else "ulaw_8000"
        self._ws = None; self._recv_task = None; self._closed = False
        self.first_byte_ts = None                       # kept (E5, iter55 anchors)
        self._send_lock = asyncio.Lock()
        self._open_contexts: set[str] = set()           # contexts with text sent, not closed
        self._settings_ctx: set[str] = set()            # contexts that already carried voice_settings
        self._cancelled: set[str] = set()               # barge-in race guard (in-flight frames)

    async def connect(self, ws=None):
        """Fresh connect, or ADOPT a prewarmed socket (ws= skips websockets.connect).
        No connect-time init message on multi-stream-input — voice_settings ride
        the first message of each context."""
        if ws is not None:
            self._ws = ws
            self._recv_task = asyncio.create_task(self._recv_loop())
            return
        url = connect_url(self.settings, self.output_format)
        headers = {"xi-api-key": self.settings.elevenlabs_api_key}
        try:
            self._ws = await websockets.connect(url, additional_headers=headers,
                                                max_size=None, open_timeout=10)
        except Exception:
            self._ws = await websockets.connect(
                url + f"&xi-api-key={self.settings.elevenlabs_api_key}",
                max_size=None, open_timeout=10)
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def speak(self, context_id: str, text: str, continue_: bool,
                    overrides: dict | None = None):
        """One SentenceGate chunk. Text messages ALWAYS carry flush:true (docs
        best practice: flush at end of complete sentences). continue_=False
        additionally closes the context (frees the 5-context slot; session
        opens a fresh context per turn — session.py:621). ("", False) is the
        gate's closing marker (sentence_gate.py:71-73) → close_context only."""
        if self._ws is None or self._closed:
            return
        if not text and continue_:
            return
        if text:
            msg: dict = {"text": text, "context_id": context_id, "flush": True}
            if overrides and context_id not in self._settings_ctx:
                msg["voice_settings"] = self._merged_voice_settings(overrides)
                self._settings_ctx.add(context_id)
            self._open_contexts.add(context_id)
            await self._send_json(msg)
        if not continue_ and (text or context_id in self._open_contexts):
            await self._send_json({"context_id": context_id, "close_context": True})
            self._open_contexts.discard(context_id)
            self._settings_ctx.discard(context_id)

    async def cancel(self, context_id: str):
        """Barge-in: REAL server-side cancel (close_context) — replaces the
        drop-flag + empty-flush hack (B2/B5)."""
        if self._ws is None or self._closed:
            return
        self._cancelled.add(context_id)
        await self._send_json({"context_id": context_id, "close_context": True})
        self._open_contexts.discard(context_id)
        self._settings_ctx.discard(context_id)

    async def keepalive(self):
        """Socket keepalive — documented shape `{"text": " "}` (a SPACE)."""
        await self._send_json({"text": " "})

    async def close(self):
        self._closed = True
        if self._recv_task:
            self._recv_task.cancel()
        if self._ws:
            try:
                await self._send_json({"close_socket": True})   # documented graceful end
            except Exception:
                pass
            try:
                await self._ws.close()
            except Exception:
                pass

    @staticmethod
    def new_context_id() -> str: ...        # unchanged (uuid4)

    def _merged_voice_settings(self, overrides): ...   # unchanged (clamps verified vs API ranges)

    async def _recv_loop(self): ...          # unchanged shape

    async def _handle_message(self, msg: dict):
        """RECV frame: {"audio": b64, "contextId": id, "is_final": bool}.
        Routing by contextId (kills _live_context guesswork); is_final clears
        ONLY that context's cancel-guard (fixes E2)."""
        audio = msg.get("audio")
        ctx = msg.get("contextId", "")
        final = bool(msg.get("is_final"))
        if audio:
            if ctx and ctx in self._cancelled:
                return                      # in-flight frames of a cancelled turn: swallow
            if self.first_byte_ts is None:
                self.first_byte_ts = time.perf_counter()
            await self.on_audio(audio, ctx)
        if final:
            self._cancelled.discard(ctx)
            self._open_contexts.discard(ctx)
```

Deleted: `_live_context`, `_dropped_contexts`, `_generation_open`, `optimize_streaming_latency`
URL param, connect-time `{"text": " ", "voice_settings": ...}` init message, `{"text": ""}` flush
anywhere. Module docstring rewritten to the multi-stream protocol.

## 2. T2 — Provider-gate `/tmp/opencode/wt-iter64-ela/engine/diallux/media/prewarm.py`

**Goal:** fix C1/C5 — no Cartesia sockets/credits when EL selected; EL pooled sockets stay
alive past the 20s idle close.

- `_spawn_idle_tts(settings)` (prewarm.py:97): first line branches —
  `if getattr(settings, "tts_provider", "cartesia") == "elevenlabs": await _spawn_idle_tts_elevenlabs(settings); return`
  Existing Cartesia body unchanged below the branch.
- New `_spawn_idle_tts_elevenlabs(settings)`:
  - URL = `connect_url(settings, fmt)` imported from `elevenlabs_tts` (shared, byte-identical —
    the C1 root cause was duplicated URL strings). `fmt = "pcm_16000" if settings.audio_transport == "browser" else "ulaw_8000"`.
  - Headers `{"xi-api-key": settings.elevenlabs_api_key}`, query-param fallback like Cartesia.
  - Same pool bookkeeping: `pool["tts"] = ws`, `_spawn_ts["tts"] = monotonic()`.
  - ONE companion task `_keepalive_drain`: every `EL_KEEPALIVE_S` (15s) send
    `{"text": " "}` (socket keepalive) and opportunistically `recv()` with 0.5s timeout (drain).
    Registered in `_companion_tasks["tts"]` — `prewarm.get()` (prewarm.py:298-307) already cancels
    it on adoption (iter60 AUD-1 ConcurrencyError lesson honored: companion cancelled BEFORE the
    session's recv loop starts).
- `_warm_phrase_cache(settings)` (prewarm.py:143): add first-line gate
  `if getattr(settings, "tts_provider", "cartesia") != "cartesia": return 0.0`
  (phrase cache stays Cartesia-only per resolved decision; EL greeting = normal flush path).
- `_maintain_once` / TTL: NO change — it calls `_spawn_idle_tts` (provider-branched) and TTL 240s
  stays a hygiene bound (keepalive makes EL sockets live indefinitely; TTL caps adoption age).

## 3. T3 — session.py adoption: NO CODE CHANGE (preflight resolution of audit C2)

`/tmp/opencode/wt-iter64-ela/engine/diallux/media/session.py:205-217` calls
`await self.tts.connect(ws=tws)`. After T1, `ElevenLabsTTS.connect(ws=...)` EXISTS, so:
- TTS adoption works for BOTH providers with the existing try/except-fresh-connect fallback.
- The pool only ever contains provider-correct sockets (T2 branches the spawner).
- Preflight note: SSML jitter gate (session.py:775-777) already cartesia-only; browser raw-PCM
  decode (session.py:802-803) is format-agnostic (EL pcm_16000 frames decode identically);
  barge-in paths (session.py:523-525, 544-546, 576-578) call `tts.cancel(ctx)` — maps 1:1 to
  close_context. **The audit's C2 fix is absorbed by T1; session.py stays byte-identical.**

## 4. T4 — `/tmp/opencode/wt-iter64-ela/engine/diallux/config.py` env surface (lines 378-386)

- REPLACE `elevenlabs_latency_opt: int = 2` (config.py:382) with
  `elevenlabs_inactivity_timeout: int = 180  # ws-level, max 180 (docs); was latency_opt (deprecated param, removed)`.
- Nothing else: `elevenlabs_api_key/voice_id/model_id/stability/similarity_boost/style/speed`
  stay (values verified vs current docs ranges in audit §B).
- `.env` compatibility: `ELEVENLABS_LATENCY_OPT` is set NOWHERE (engine `.env` has zero
  `ELEVENLABS_*` entries — verified), and pydantic-settings ignores unknown env keys → removal safe.

## 5. T5 — Factory + tests

**`/tmp/opencode/wt-iter64-ela/engine/diallux/media/tts_factory.py`** (line 19): pass transport
through — `return ElevenLabsTTS(settings, on_audio, transport=transport)` (Cartesia branch
already does; EL branch currently drops it — preflight finding).

**NEW pin file `/tmp/opencode/wt-iter64-ela/engine/tests/test_iter64_elevenlabs_cutover.py`**
(FakeWS seam copied from `/tmp/opencode/wt-iter64-ela/engine/tests/test_tts_providers.py:28-48`;
hermetic, no network):
1. URL: `multi-stream-input` endpoint, `model_id`, `output_format=pcm_16000` (transport=browser)
   / `ulaw_8000` (twilio), `inactivity_timeout=180` present, `optimize_streaming_latency` ABSENT.
2. Message sequence: sentence chunks = `{"text","context_id","flush":true}`; voice_settings on
   FIRST message of a context only (with overrides); end-of-turn (text, False) → text+flush then
   `close_context`; closing marker ("", False) → `close_context` only.
3. **Socket-killer guard:** NO sent message ever has `text == ""` without a `context_id`
   (the B1 shape `{"text": ""}` must never appear).
4. cancel → exactly `{"context_id": ctx, "close_context": true}`; in-flight frames for the
   cancelled contextId swallowed; audio for a NEW context routes by `contextId`.
5. Recv casing: `{"audio", "contextId", "is_final"}` frames route + clear the cancel-guard per
   context (E2 pin).
6. Adoption: `connect(ws=FakeWS())` starts the recv loop without `websockets.connect`; factory
   passes `transport` (instance output_format correct via `create_tts`).
7. Prewarm provider gate: with `tts_provider="elevenlabs"`, `_spawn_idle_tts` builds an
   elevenlabs.io URL (no cartesia.io anywhere), registers a cancellable companion
   (`prewarm.get("tts")` cancels it — AUD-1 pin); `_warm_phrase_cache` returns 0.0 for EL.
8. Keepalive: `tts.keepalive()` sends `{"text": " "}` (never `{"text": ""}`).

**REWRITE the ElevenLabs block of `/tmp/opencode/wt-iter64-ela/engine/tests/test_tts_providers.py`
(lines 101-180)** — those 4 tests pin the OLD protocol (`stream-input` URL,
`texts.count("") == 1` empty-flush assertion at line 143, `isFinal` casing) and WILL fail after
T1. Replace with thin equivalents of pin-tests 1-5 above (Cartesia block lines 55-98 untouched).

**Suite gate:** `422` tests green at iter63 baseline; after T5 the count grows by the pin file
(≈8) with the 4 rewritten EL tests replaced 1:1 — net new = pin count. Zero failures allowed:
`cd /tmp/opencode/wt-iter64-ela/engine && .venv/bin/python -m pytest tests -q` (after worktree
setup: `.venv` symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv` + `.env` copy —
iter44 pattern, `plans/plan_iter44_cache_floor.md`).

## 6. T6 — Live verification lane (OWNER-DRIVEN, after approval — LAW 0)

BLOCKED until owner supplies `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` (Chloe) — verified
absent from `/home/julio/projects/clean_diallux_SDR/engine/.env` AND `/home/julio/projects/.env`.

1. Owner appends to `/tmp/opencode/wt-iter64-ela/engine/.env`:
   `TTS_PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY=<owner>`, `ELEVENLABS_VOICE_ID=<owner>`.
   (`AUDIO_TRANSPORT=browser` already the lane; `CALL_PREWARM=true` to exercise T2.)
2. Foreground engine on a free 127.0.0.1 port (pattern `:8021`; NEVER the live :8000-8003).
3. Mic-page call, ≥3 turns + one mid-sentence barge-in. Checkpoints:
   - LV-1 turn 2+ audio present (B1) and no truncation at end-of-turn flush→close (official
     example pattern; fallback if truncation observed: defer close_context to next speak/cancel).
   - LV-2 barge-in stops audio instantly; next turn clean (B2/B5).
   - LV-3 recv casing `contextId`/`is_final` confirmed in logs (E3).
   - LV-4 browser lane audio intelligible (B3, pcm_16000); greeting speaks via normal flush path.
   - LV-5 idle socket >20s (prewarm keepalive) still adoptable; >20s mid-call pause survives (E4).
4. Twilio lane format: covered hermetically by pin-test 1 (ulaw_8000); live phone check optional
   at owner's discretion.
5. Evidence per repo SOP: ledger import (`scripts/live_sql.py import --run iter64-ela-smoke
   --commit <sha>`), Langfuse trace check, autopsy report on any failure
   (`research/surgeon/iter64-elevenlabs-cutover/`).

## 7. Execution order & compile gates

T4 (config) → T1 (adapter) → T5-factory line + tests rewrite + pin file → T2 (prewarm) →
suite green → commit on branch → T6 owner lane. Compile-check after each step
(`python -c "import diallux.media.elevenlabs_tts"` etc. from the worktree engine dir).
Branch commits: `engine/iter64-elevenlabs-cutover`, messages `iter64: <task> — <one line>`.
NO merge to main without owner say-so (LAW 0).
