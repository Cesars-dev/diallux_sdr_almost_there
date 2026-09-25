"""CallSession — V3 production orchestration.

V1 flow (Twilio -> Deepgram -> LangGraph -> gate -> Cartesia -> Twilio) plus:

  - mark-based hangup: after end_call audio, a `mark` frame confirms Twilio
    finished PLAYING the goodbye before we close the stream (timer fallback)
  - STT auto-reconnect: Deepgram socket death mid-call transparently reconnects
  - buffer-overflow watchdog: Twilio warning 31931 (media discarded) is logged
    + counted, not silently ignored
  - eager end-of-turn (optional): EagerEndOfTurn starts the LLM speculatively;
    TurnResumed cancels it (Deepgram guarantees the eager transcript equals
    the final EndOfTurn transcript when no resume happens)
  - Prometheus metrics per turn + per call (observability/metrics.py)
  - V3: provider-agnostic TTS (media/tts_factory.py — Cartesia OR ElevenLabs,
    both native ulaw/mulaw @ 8000) and deterministic speech normalization on
    every spoken sentence (media/normalize.py — the Retell-native layer).
  - V5: per-state delivery profiles (media/delivery.py — the state machine
    controls emotion/speed; the profile follows the state whose prompt
    generated the speech: snapshotted at turn END, applied from the next
    turn, exactly like Retell's per-state prompt semantics).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from ..config import Settings
from ..graph.builder import CallRuntime
from ..observability.latency import TurnClock
from ..observability.tracer import Tracer
from .deepgram_stt import DeepgramSTT
from .delivery import resolve_delivery
from .normalize import normalize_for_tts
from .sentence_gate import SentenceGate
from .tts_factory import create_tts, tts_label

log = logging.getLogger("diallux.session")

HANGUP_GRACE_S = 1.2   # fallback when hangup_mode=timer or no mark arrives


def _ssml_jitter(settings) -> str:
    """Per-sentence inline Cartesia SSML: volume/speed ratios with natural
    jitter (t11 voicemail recipe finding: mechanical + reliable; kills the
    robotic flatness). Occasionally a sentence dips slightly more — real
    speech isn't uniform. Tags are forward-applying and open at the request
    boundary, so streaming never reads them aloud."""
    import random
    j_s = getattr(settings, "tts_jitter_speed", 0.06)
    j_v = getattr(settings, "tts_jitter_volume", 0.10)
    s = random.uniform(1.0 - j_s, 1.0 + j_s)
    v = random.uniform(1.0 - j_v, 1.0 + j_v)
    if random.random() < 0.10:                   # occasional natural dip
        s *= 0.97
        v *= 0.94
    s = max(0.6, min(1.5, s))
    v = max(0.5, min(2.0, v))
    return f'<volume ratio="{v:.2f}"/><speed ratio="{s:.2f}"/> '


class CallSession:
    # iter43 T1: EOT telemetry defaults (class-level: some tests build
    # CallSession objects without __init__)
    _eager_transcript: str | None = None
    _resumed_count = 0
    # iter55 T0 (F-06): class-level default — some tests build CallSession
    # objects without __init__; the greeting anchors must never AttributeError.
    _greet: dict | None = None
    # iter65 T4: mic-span anchors (class-level for the same no-__init__ tests)
    _t_speech_growth: float | None = None
    _last_update_len: int = 0

    def __init__(
        self,
        settings: Settings,
        ws,
        stream_sid: str,
        call_sid: str,
        custom_parameters: dict | None = None,
        llm_json: dict | None = None,
        tracer: Tracer | None = None,
        transport: str | None = None,
    ):
        self.settings = settings
        self.ws = ws
        self.stream_sid = stream_sid
        self.call_sid = call_sid
        self.llm_json = llm_json or json.loads(open(settings.agent_llm_json).read())
        self.custom_parameters = custom_parameters or {}
        # iter21: codec layer only. twilio = 8k mulaw Media Streams frames;
        # browser = 16-bit PCM @ browser_sample_rate (/mic ws). Everything
        # after the STT ingest / TTS output format is identical.
        self.transport = transport or settings.audio_transport

        self.tracer = tracer
        self.stt: DeepgramSTT | None = None
        self.tts: CartesiaTTS | None = None
        self.gate: SentenceGate | None = None
        self.runtime: CallRuntime | None = None

        self._turn_task: asyncio.Task | None = None
        self._writer_task: asyncio.Task | None = None
        self._outbox: asyncio.Queue[dict | None] = asyncio.Queue()
        self._clock = TurnClock()
        self._speak_clock: TurnClock | None = None   # turn whose TTS is speaking
        self._tts_context: str | None = None
        self._turn_state: str | None = None   # V5: state whose profile voices the current turn
        self._first_turn = True
        self._initial_payload: dict | None = None
        self._stopped = False
        self._ended = False
        self._pending_end_mark: str | None = None
        self._turn_mark_seq = 0
        self.turn_reports: list[dict] = []
        # iter38 F2: the graph thread config, shared by _run_turn /
        # _late_turn_report / stop (the 2026-09-09 disaster call died on a
        # NameError here: `config` was a local of _run_turn, so the late
        # report's aget_state raised and the post-goodbye hangup never fired).
        self._thread_config = {"configurable": {"thread_id": self.call_sid}}
        self._real_turns = 0                       # iter38 F3: hard cap counter
        self._cap_closed = False                   # iter38 F3: graceful close fires once
        self._call_start = 0.0                     # iter38 F3: wall-clock guard (set in start())
        # iter43 T1: EOT telemetry — eager transcript + false-start counter
        self._eager_transcript: str | None = None  # transcript seen at EagerEndOfTurn
        self._resumed_count = 0                    # TurnResumed (false-start) counter
        # iter55 T0 (F-06): dedicated greeting-runway anchors — independent
        # of the turn-0 clock, so turn 1's clock swap never contaminates them.
        self._greet: dict | None = None
        # iter59 T3: flux-Update speech-window fire guard. BOOLEAN — clocks
        # swap at EOT/EagerEOT, NOT StartOfTurn, so turn-index keying is wrong
        # mid-speech (C8). Cleared in _on_eot/_on_eager_eot AFTER the fire
        # decision, and in _on_start_of_turn.
        self._update_fired = False
        # iter65 T4: mic-span anchors — last transcript-growth instant +
        # its length (eot_silence_wait + tts_first_byte spans).
        self._t_speech_growth: float | None = None
        self._last_update_len = 0

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    async def start(self):
        known = set(self.llm_json.get("default_dynamic_variables", {}))
        persona = {k: v for k, v in self.custom_parameters.items() if k in known}

        # iter21: browser bridge calls trace as micbridge-<session> with the
        # SAME span/score schema — only the trace name differs.
        session_name = (f"micbridge-{self.call_sid}" if self.transport == "browser"
                        else "diallux-call")
        self.tracer = self.tracer or Tracer(
            session_name=session_name,
            metadata={
                "agent": "diallux-langgraph-production",
                "llm_model": self.settings.openai_model,
                "call_sid": self.call_sid,
                "stream_sid": self.stream_sid,
                "transport": self.transport,
                "stt_mode": self.settings.deepgram_mode,
                "eager_eot": self.settings.deepgram_eager_eot,
                "tts": tts_label(self.settings),
                "rag_mode": self.settings.rag_mode,
            },
            enabled=self.settings.langfuse_enabled,
        )
        self.runtime = CallRuntime(self.settings, self.llm_json, tracer=self.tracer)
        self._initial_payload = dict(self.runtime.initial_state(self.call_sid, persona))
        self._turn_state = self._initial_payload.get("state_name") or self.llm_json.get("starting_state", "Intake")
        # iter49 T3: last-known dvs (updated post-turn) — the eager-EOT
        # live-retrieve fire uses these; dvs refinement lands next round
        # (pack degrade semantics).
        self._turn_dvs: dict = dict(self._initial_payload.get("dvs") or {})

        # eager end-of-turn wiring
        eager = self.settings.deepgram_eager_eot or self.settings.deepgram_eager_eot_threshold is not None
        self.stt = DeepgramSTT(
            self.settings,
            on_eot=self._on_eot,
            on_start_of_turn=self._on_start_of_turn,
            on_disconnect=self._on_stt_disconnect,
            on_state=self._on_stt_state,          # iter43 T1: STT state telemetry
            on_eager=self._on_eager_eot if (eager and self.settings.deepgram_eager) else None,
            on_turn_resumed=self._on_turn_resumed if (eager and self.settings.deepgram_eager) else None,
            on_update=self._on_stt_update,        # iter59 T3: speech-window/hybrid fire
            transport=self.transport,
        )
        if eager and self.settings.deepgram_eager:
            self.settings.deepgram_eager_eot_threshold = self.settings.deepgram_eager_eot_threshold or 0.6

        self.tts = create_tts(self.settings, on_audio=self._on_tts_audio,
                              transport=self.transport)
        self.gate = SentenceGate(self._speak_chunk, managed=self.settings.cartesia_buffering == "managed")

        self._writer_task = asyncio.create_task(self._writer())
        # iter59 T5: adopt a prewarmed STT socket when the pool has one
        # (get() POPS the slot so the maintainer respawns a fresh idle);
        # adoption failure NEVER fails the call — fall back to fresh connect.
        adopted = False
        if self.settings.call_prewarm:
            try:
                from .prewarm import get as pool_get
                pw = pool_get("stt")
                if pw is not None:
                    await self.stt.connect(ws=pw)
                    adopted = True
            except Exception:
                adopted = False
        if not adopted:
            await self.stt.connect()
        # iter59 T5: same adoption for TTS (fallback: fresh connect).
        adopted_tts = False
        if self.settings.call_prewarm:
            try:
                from .prewarm import get as pool_get
                tws = pool_get("tts")
                if tws is not None:
                    await self.tts.connect(ws=tws)
                    adopted_tts = True
            except Exception:
                adopted_tts = False
        if not adopted_tts:
            await self.tts.connect()
        self._call_start = time.perf_counter()     # iter38 F3: 10-min guard origin
        # iter21: warm the RAG path during the greeting — the ~1.7s cold
        # embed never lands on the caller's first turn.
        if self.runtime is not None:
            # iter44 T2: resolve the KB store BEFORE the prewarm fires so the
            # warm path and the hot path always see the SAME store decision.
            # Bounded (2.0 s) + best-effort: a store outage never blocks the
            # call start (the resolve latch retries on the first turn).
            try:
                await asyncio.wait_for(self.runtime._resolve_kb_store(), 2.0)
            except Exception:
                pass
            asyncio.get_event_loop().create_task(self.runtime.warm_rag(
                self._turn_state,
                dict(self._initial_payload.get("dvs") or {})))
            # iter43 T3: prewarm the FULL Intake payload (tools + head + history)
            # during the greeting playback — turn 2+ runs on a warm prefix.
            # warm_prompt_cache is fire-and-forget and spawns its own task.
            self.runtime.warm_prompt_cache(
                self._turn_state,
                self._initial_payload.get("history") or [],
                dvs=dict(self._initial_payload.get("dvs") or {}))
            # iter46 T3: ALSO warm the first_turn_lite shape (general_prompt +
            # VOICE_OUTPUT_RULES only, no tools) — the turn-1 hot payload
            # byte-diverges from the full-Intake shape at byte 0, so without
            # the lite warm turn 1 paid cache_read=0 every call (audit tax #3).
            self.runtime.warm_prompt_cache(
                self._turn_state,
                self._initial_payload.get("history") or [],
                None, lite=True)

        # begin_message (start_speaker: agent) — spoken immediately, no LLM.
        # V5: the greeting gets the "begin" delivery profile (warm, energetic).
        begin = (self._initial_payload.get("history") or [{}])[0].get("content", "")
        ctx = self.tts.new_context_id()
        self._tts_context = ctx
        # iter55 T0: greeting runway anchors — stream start → first audio out
        # → drain, measured on dedicated state (never the turn-0 clock).
        self._greet = {"ctx": ctx, "t_stream": time.perf_counter(),
                       "first_audio": None, "last_audio": None}
        await self.tts.speak(ctx, begin, continue_=False,
                              overrides=resolve_delivery(self.settings, "begin"))
        asyncio.get_event_loop().create_task(self._greeting_drain())
        if self.settings.metrics_enabled:
            from ..observability import metrics
            metrics.CALLS.inc()
        log.info("call %s started (sid=%s)", self.call_sid, self.stream_sid)

    async def stop(self, reason: str = "stopped"):
        if self._stopped:
            return
        self._stopped = True
        if self._turn_task:
            self._turn_task.cancel()
        if self.gate:
            await self.gate.close()
        if self.stt:
            await self.stt.close()
        if self.tts:
            await self.tts.close()
        await self._outbox.put(None)
        if self.runtime:
            try:
                state = await self.runtime.graph.aget_state(self._thread_config)
                values = state.values or {}
                convo = [
                    {"role": m.get("role"), "content": m.get("content", "")}
                    for m in values.get("history", []) if m.get("role") in ("user", "assistant")
                ]
                booked = bool((values.get("dvs") or {}).get("booking_verified"))
                if booked and self.settings.metrics_enabled:
                    from ..observability import metrics
                    metrics.BOOKINGS.inc()
                self.tracer.finish(output={
                    "conversation": convo,
                    "tool_trace": self.runtime.executor.trace,
                    "final_state": values.get("state_name"),
                    "ended": values.get("ended", self._ended),
                    "dynamic_variables": values.get("dvs", {}),
                    "gate_rejections": self.runtime.executor.gate_rejections,
                    "turn_reports": self.turn_reports,
                    "stop_reason": reason,
                })
            except Exception:
                self.tracer.finish(output={"stop_reason": reason, "turn_reports": self.turn_reports})
            await self.runtime.aclose()
        log.info("call %s stopped (%s)", self.call_sid, reason)

    # ------------------------------------------------------------------ #
    # Twilio events
    # ------------------------------------------------------------------ #
    async def on_media(self, payload_b64: str):
        if self.stt:
            self._mic_chunks = getattr(self, "_mic_chunks", 0) + 1
            if self._mic_chunks == 1:
                log.info("mic audio FIRST chunk received (sid=%s)", self.call_sid)
            elif self._mic_chunks % 100 == 0:
                log.info("mic audio flowing: %d chunks (sid=%s)",
                         self._mic_chunks, self.call_sid)
            await self.stt.send_audio(_b64decode(payload_b64))

    async def on_twilio_mark(self, msg: dict):
        """Playback-confirmed hangup: end_call audio has finished PLAYING."""
        name = ((msg.get("mark") or {}).get("name") or "")
        if self._pending_end_mark and name == self._pending_end_mark:
            self._pending_end_mark = None
            await self.ws.close(code=1000)
            await self.stop(reason="end_call_played")

    async def on_twilio_warning(self, msg: dict):
        """Twilio 31931 etc. — media discarded downstream (buffer overflow)."""
        log.warning("twilio stream warning: %s", json.dumps(msg)[:300])
        self.tracer.span("twilio:warning", output=msg)

    # ------------------------------------------------------------------ #
    # STT callbacks
    # ------------------------------------------------------------------ #
    async def _on_eot(self, transcript: str):
        if self._stopped or self._ended:
            return
        if self._cap_hit():
            await self._graceful_cap_close()    # iter38 F3 (PT-34)
            return
        if self._turn_task and not self._turn_task.done():
            if self._clock.extra.get("eager"):
                # iter46 T7: with a grace window enabled, adoption is
                # GUARDED — a stale eager transcript (caller appended words
                # after EagerEOT, TurnResumed held inside the grace) must
                # cancel+rerun, never answer the incomplete utterance.
                # Grace=0 (default): the old unconditional adopt — today's
                # behavior exactly (resume always cancelled first).
                if getattr(self.settings, "eager_resume_grace_ms", 0) > 0 \
                        and self._eager_transcript != transcript:
                    self._clock.extra["eager"] = False
                    self._clock.extra["resume_pending"] = False
                    self._turn_task.cancel()
                else:
                    # iter38 F1 (PT-33): the eager transcript IS the final
                    # transcript (Deepgram contract when no TurnResumed happened).
                    # The turn is already running — ADOPT it. Cancel+rerun here
                    # double-appended the user utterance to history (~40 dupes in
                    # the 2026-09-09 disaster call) and ran the graph twice per
                    # utterance (even-only turn indexes).
                    # iter43 T1: head-start telemetry — t_eager was stamped in
                    # _on_eager_eot (mark_user_end fired there, so the live metric
                    # stt_eot_to_llm_first_ms is actually EagerEOT-anchored).
                    t_eager = self._clock.extra.get("t_eager")
                    if t_eager is not None:
                        self._clock.extra["t_final"] = time.perf_counter()
                        self._clock.extra["head_start_ms"] = round(
                            (self._clock.extra["t_final"] - t_eager) * 1000, 1)
                        self._clock.extra["eager_final_match"] = (
                            self._eager_transcript == transcript)
                    self._eager_transcript = None
                    self._clock.extra["resume_pending"] = False   # grace window: adopted
                    self._update_fired = False   # iter59: adopted — fires already dispatched at EagerEOT
                    log.info("eot adopted running eager turn (no rerun)")
                    return
            else:
                self._turn_task.cancel()
        # iter38 F5: carry the barge-in flag across the clock swap —
        # _on_start_of_turn marked it on the OLD clock; a fresh TurnClock here
        # silently dropped it (all 6 real barge-ins reported barge_in:false in
        # the 2026-09-09 disaster call).
        prev = self._clock
        self._clock = TurnClock(turn_index=prev.turn_index + 1)
        if prev.barge_in:
            self._clock.barge_in = True
            self._clock.t_barge_in = prev.t_barge_in
        self._clock.mark_user_end()
        # iter59 T3: fire mode dispatch at final EOT.
        #   hybrid      — lane B fires here (single-query utterance embed,
        #                 consumed inline by the running/starting round).
        #   speech-window — when an Update already fired this turn, SKIP the
        #                 fire: spawning again would CANCEL the landed
        #                 task and re-degrade (the exact iter58 bug).
        #   round-sync  — consume retrieves INLINE; firing a "full" task
        #                 here was a wasted embed+pgvector per turn (iter60
        #                 AUD-5).
        #   eot         — iter58 surface (fire at EOT).
        mode = getattr(self.settings, "rag_fire_mode", "eot")
        if mode == "hybrid":
            self._fire_live_retrieve(transcript, lane="laneB")
        elif mode == "speech-window" and self._update_fired:
            pass
        elif mode == "round-sync":
            pass    # iter60 AUD-5: consume retrieves INLINE — firing a
                    # "full" task here was a wasted embed+pgvector per turn
        else:
            self._fire_live_retrieve(transcript)
        self._update_fired = False
        self._turn_task = asyncio.create_task(self._run_turn(transcript))

    def _fire_live_retrieve(self, transcript: str, lane: str = "full") -> None:
        """iter49 T3: fire the batched lane retrieval at the EARLIEST moment
        the queries exist (EagerEOT / final EOT before the graph invoke) —
        the arctic embed (~90-190ms multi-lane) runs inside the caller's
        remaining speech + the speculative LLM start, so the round's bounded
        await only pays pgvector + merge. Best-effort, NEVER raises: the
        state_node consumer spawns a fallback when nothing is in flight."""
        try:
            runtime = getattr(self, "runtime", None)
            if runtime is None:
                return
            runtime.spawn_live_retrieve(
                getattr(self, "_turn_state", None) or "Intake",
                dict(getattr(self, "_turn_dvs", None) or {}),
                transcript or "", lane=lane)
        except Exception as exc:
            try:
                log.warning("live-retrieve fire failed on call %s: %s",
                            getattr(self, "call_sid", "?"), exc)
            except Exception:
                pass

    async def _on_stt_update(self, transcript: str):
        """iter59 T3: flux TurnInfo.Update handler (~every 0.25 s of audio,
        cumulative turn transcript). Fires ONCE per turn (boolean guard):
          speech-window — the FULL multi-lane retrieval (partial transcript
                          is lane B's input; scopes/queries already exist).
          hybrid        — lane A ONLY (refer-tag queries + dv values:
                          utterance-INDEPENDENT, lands during speech).
        On a TurnResumed the same turn keeps its fire (lane A is
        utterance-independent; the EagerEOT/EOT path re-fires lane B with
        the final transcript)."""
        # iter65 T4: speech-growth anchor — the last instant the turn
        # transcript grew (EOT silence span = EagerEOT − this).
        if len(transcript) > self._last_update_len:
            self._t_speech_growth = time.perf_counter()
            self._last_update_len = len(transcript)
        mode = getattr(self.settings, "rag_fire_mode", "eot")
        if mode not in ("speech-window", "hybrid"):
            return
        if self._stopped or self._ended or self._update_fired:
            return
        self._update_fired = True
        if mode == "speech-window":
            self._fire_live_retrieve(transcript)          # full lanes, partial utterance
        else:
            self._fire_live_retrieve("", lane="laneA")    # hybrid lane A: engine intent only

    async def _on_eager_eot(self, transcript: str):
        """Speculative LLM start (optional): runs the turn early; EndOfTurn keeps it."""
        if self._stopped or self._ended:
            return
        if self._cap_hit():
            await self._graceful_cap_close()    # iter38 F3 (PT-34)
            return
        if self._turn_task and not self._turn_task.done():
            return                      # a turn is already running
        log.info("eager turn started (speculative)")
        prev = self._clock
        self._clock = TurnClock(turn_index=prev.turn_index + 1, extra={"eager": True})
        if prev.barge_in:                        # iter38 F5: carry barge-in across swap
            self._clock.barge_in = True
            self._clock.t_barge_in = prev.t_barge_in
        self._clock.mark_user_end()
        # iter43 T1: stamp the eager anchor — head_start_ms = EagerEOT → EndOfTurn
        self._clock.extra["t_eager"] = time.perf_counter()
        # iter65 T4: eot_silence_wait span — EagerEOT minus the last instant
        # the transcript GREW (the caller's trailing silence the EOT waited
        # through). Observability-only.
        if self._t_speech_growth is not None and self.tracer:
            self.tracer.span("eot_silence_wait", metadata={
                "ms": round((time.perf_counter() - self._t_speech_growth) * 1000, 1),
                "turn": self._clock.turn_index})
        self._eager_transcript = transcript
        # iter59 T3: EagerEOT fire dispatch (the round STARTS here — the
        # consumer is about to run):
        #   hybrid      — lane B fires NOW (the eager transcript IS the final
        #                 transcript per Deepgram contract when no resume);
        #                 an EOT adopt reuses it (the adopt return below must
        #                 not double-fire).
        #   speech-window — skip when an Update landed (landed task beats a
        #                 superseding spawn).
        #   round-sync  — consume retrieves INLINE; firing a "full" task
        #                 here was a wasted embed+pgvector per turn (iter60
        #                 AUD-5).
        #   eot         — iter58 surface.
        mode = getattr(self.settings, "rag_fire_mode", "eot")
        if mode == "hybrid":
            self._fire_live_retrieve(transcript, lane="laneB")
        elif mode == "speech-window" and self._update_fired:
            pass
        elif mode == "round-sync":
            pass    # iter60 AUD-5: consume retrieves INLINE — firing a
                    # "full" task here was a wasted embed+pgvector per turn
        else:
            self._fire_live_retrieve(transcript)
        self._update_fired = False
        self._turn_task = asyncio.create_task(self._run_turn(transcript))

    async def _on_turn_resumed(self):
        """User kept talking: the speculative turn is cancelled."""
        # iter43 T1: false-start counter (pre-registered EOT winner criterion)
        self._resumed_count += 1
        if self._turn_task and not self._turn_task.done() and self._clock.extra.get("eager"):
            # iter46 T7: eager-resume GRACE — hold the cancel for
            # eager_resume_grace_ms; if EndOfTurn lands within the grace with
            # an EQUAL transcript the running round is adopted (no TTFT
            # restart, the measured 1,460-2,025 ms resumed-turn tail dies).
            # The adoption guard (eager_final_match) lives in _on_eot. A
            # second TurnResumed inside the grace cancels immediately.
            # Default 0 (off) — exact today behavior until the live A/B.
            grace = getattr(self.settings, "eager_resume_grace_ms", 0)
            if grace > 0 and not self._clock.extra.get("resume_pending"):
                self._clock.extra["resume_pending"] = True
                asyncio.get_event_loop().create_task(
                    self._grace_then_cancel(grace))
                log.info("eager resume held for %.0f ms grace", grace)
                return
            # iter38 F1 race guard: clear the eager marker BEFORE cancelling —
            # otherwise the imminent EndOfTurn would ADOPT this dying task and
            # the utterance would never run.
            self._clock.extra["eager"] = False
            self._clock.extra["resume_pending"] = False
            self._turn_task.cancel()
            await self.gate.reset()
            if self.tts and self._tts_context:
                await self.tts.cancel(self._tts_context)
            self._send({"event": "clear", "streamSid": self.stream_sid})
            log.info("eager turn cancelled (user resumed)")

    async def _grace_then_cancel(self, grace_ms: float):
        """iter46 T7: grace-window expiry — the caller is STILL talking after
        eager_resume_grace_ms, so the speculative round was a false start:
        cancel+rerun as today. Adoption inside the grace clears
        `resume_pending` first, which no-ops this."""
        await asyncio.sleep(grace_ms / 1000.0)
        if self._stopped or self._ended:
            return
        if not self._clock.extra.get("resume_pending"):
            return                      # adopted inside the grace window
        self._clock.extra["resume_pending"] = False
        if self._turn_task and not self._turn_task.done() \
                and self._clock.extra.get("eager"):
            self._clock.extra["eager"] = False
            self._turn_task.cancel()
            await self.gate.reset()
            if self.tts and self._tts_context:
                await self.tts.cancel(self._tts_context)
            self._send({"event": "clear", "streamSid": self.stream_sid})
            log.info("eager turn cancelled (grace expired, user still talking)")

    async def _on_stt_state(self, msg: dict):
        """iter43 T1: raw STT state telemetry (Flux TurnInfo events etc.).
        Telemetry-only — never mutates turn flow."""
        try:
            mtype = msg.get("type")
            if mtype == "TurnInfo":
                event = msg.get("event")
                if event in ("StartOfTurn", "TurnResumed"):
                    log.info("stt state: %s (turn %s)", event, msg.get("turn_index"))
                # Update/EagerEndOfTurn/EndOfTurn are already handled elsewhere —
                # keep this quiet to avoid double-logging every transcript.
        except Exception:
            pass

    async def _on_start_of_turn(self):
        if self._stopped:
            return
        interrupted = bool(self._turn_task and not self._turn_task.done())
        if interrupted:
            self._clock.barge_in = True
            self._clock.t_barge_in = time.perf_counter()
            self._turn_task.cancel()
            if self.settings.metrics_enabled:
                from ..observability import metrics
                metrics.BARGEINS.inc()
        if self.gate:
            await self.gate.reset()
        if self.tts and self._tts_context:
            await self.tts.cancel(self._tts_context)
        self._send({"event": "clear", "streamSid": self.stream_sid})
        # iter59 T3: a new speech turn begins — re-arm the Update fire guard.
        # (C8: boolean, cleared here AND at EOT/EagerEOT; never turn-index keyed.)
        self._update_fired = False
        # iter65 T4: reset the mic-span anchors for the new turn.
        self._t_speech_growth = None
        self._last_update_len = 0
        if interrupted:
            log.info("barge-in on call %s", self.call_sid)

    async def _on_stt_disconnect(self):
        """V2: transparent STT reconnect (audio gap, call continues)."""
        if self._stopped or not self.settings.deepgram_reconnect:
            return
        log.warning("deepgram dropped mid-call; reconnecting")
        self.tracer.span("stt:reconnect", output={"call_sid": self.call_sid})
        try:
            await self.stt.close()
        except Exception:
            pass
        eager = self.settings.deepgram_eager
        self.stt = DeepgramSTT(
            self.settings,
            on_eot=self._on_eot,
            on_start_of_turn=self._on_start_of_turn,
            on_disconnect=self._on_stt_disconnect,
            on_state=self._on_stt_state,          # iter43 T1: STT state telemetry
            on_eager=self._on_eager_eot if eager else None,
            on_turn_resumed=self._on_turn_resumed if eager else None,
            on_update=self._on_stt_update,        # iter59 T3: survive reconnect
            transport=self.transport,
        )
        try:
            await self.stt.connect()
        except Exception as exc:
            log.error("stt reconnect failed: %s", exc)

    # ------------------------------------------------------------------ #
    # The brain
    # ------------------------------------------------------------------ #
    async def _run_turn(self, transcript: str):
        clock = self._clock
        self._speak_clock = clock                   # TTS marks route to THIS turn
        self._real_turns += 1                       # iter38 F3: real graph executions
        config = self._thread_config
        self._tts_context = self.tts.new_context_id() if self.tts else None
        try:
            payload: dict[str, Any] = {"user_text": transcript}
            if self._first_turn:
                payload.update(self._initial_payload or {})
                self._first_turn = False
            async for mode, data in self.runtime.graph.astream(
                payload, config=config, stream_mode=["custom", "updates"]
            ):
                if mode == "custom" and isinstance(data, dict) and "tts_token" in data:
                    if clock.t_llm_first is None:
                        clock.mark_llm_first()
                    self.gate.add(data["tts_token"])
        except asyncio.CancelledError:
            await self.gate.reset()
            return
        except Exception as exc:
            log.exception("turn failed on call %s: %s", self.call_sid, exc)
            return

        await self.gate.end_of_turn()
        clock.mark_turn_done()
        report = clock.report()
        self.turn_reports.append(report)
        self.tracer.span(f"turn:{clock.turn_index}", output=report)
        log.info("turn %d report: %s", clock.turn_index, json.dumps(report))
        # iter21: TTS audio often arrives AFTER the graph turn completes
        # (sentence gate flush -> Cartesia TTFB) — the early report above
        # structurally misses tts_first/audio_out. A late follow-up span
        # captures the COMPLETE budget once audio has flowed (or timed out);
        # metrics are emitted once, on the complete report.
        asyncio.get_event_loop().create_task(self._late_turn_report(clock))

    async def _late_turn_report(self, clock: TurnClock):
        for _ in range(20):                          # up to ~3s of drain wait
            await asyncio.sleep(0.15)
            if clock.t_audio_out is not None:
                break
        final = clock.report()
        # iter43 T1: false-start counter rides on the final report (clock.extra
        # would drop it across the resume swap — it is call-scoped, not turn-scoped)
        final["resumed_count"] = self._resumed_count
        self.tracer.span(f"turn:{clock.turn_index}:final", output=final)
        if self.settings.metrics_enabled:
            from ..observability import metrics
            metrics.observe_turn_report(final)
        log.info("turn %d final report: %s", clock.turn_index, json.dumps(final))

        # mark frame: Twilio echoes it back once the audio finished PLAYING
        self._turn_mark_seq += 1
        self._send({"event": "mark", "streamSid": self.stream_sid,
                    "mark": {"name": f"turn-{clock.turn_index}-done"}})

        try:
            snap = await self.runtime.graph.aget_state(self._thread_config)
            vals = snap.values or {}
            if vals.get("ended"):
                self._ended = True
                # mark-based hangup needs Twilio's mark echo; the browser ws
                # has no echo, so the timer drain applies there.
                if self.settings.hangup_mode == "mark" and self.transport == "twilio":
                    self._pending_end_mark = f"turn-{clock.turn_index}-done"
                else:
                    asyncio.get_event_loop().create_task(self._hangup_after_drain())
            # V5: the post-transition state becomes the delivery profile for
            # the NEXT turn — turn N's speech was generated by turn N's
            # starting state's prompt, so that is whose profile voiced it.
            if vals.get("state_name"):
                self._turn_state = vals["state_name"]
            # iter49 T3: keep the last-known dvs for the eager-EOT fire.
            self._turn_dvs = dict(vals.get("dvs") or {})
        except Exception:
            # iter38 F2: NEVER silent — the 2026-09-09 disaster call lost the
            # post-goodbye hangup to a swallowed NameError here.
            log.exception("post-turn state check failed on call %s", self.call_sid)

    async def _greeting_drain(self):
        """iter55 T0 (F-06): one greeting summary span after the drain window
        (mirrors the `_late_turn_report` follow-up-task pattern). Dedicated
        anchors only — never touches the turn-0 clock."""
        try:
            await asyncio.sleep(7.0)
            greet = self._greet
            if greet is None or greet.get("first_audio") is None:
                return
            self.tracer.span("greeting", metadata={
                "stream_to_first_ms":
                    round((greet["first_audio"] - greet["t_stream"]) * 1000),
                "audio_drain_ms":
                    round((greet["last_audio"] - greet["first_audio"]) * 1000),
                "total_ms":
                    round((greet["last_audio"] - greet["t_stream"]) * 1000),
            })
        except Exception:
            pass

    async def _hangup_after_drain(self):
        await asyncio.sleep(HANGUP_GRACE_S)
        try:
            await self.ws.close(code=1000)
        except Exception:
            pass
        await self.stop(reason="end_call")

    def _cap_hit(self) -> bool:
        """iter38 F3: turn cap (64) OR wall-clock cap (600s) — Julio-tuned
        2026-09-09 after the 24-cap murdered a healthy 5-minute call."""
        if self._real_turns >= self.settings.max_call_turns:
            return True
        limit = getattr(self.settings, "max_call_seconds", 0)
        if limit and self._call_start and \
                (time.perf_counter() - self._call_start) >= limit:
            return True
        return False

    async def _graceful_cap_close(self):
        """iter38 F3 (PT-34): the call blew past the turn/time cap — say so
        honestly and hang up. Deterministic (no LLM): the same failure mode as
        the 2026-09-09 disaster call (97 turns, 11 minutes, no closure) can
        never repeat. Fires BETWEEN turns only — a mid-flight booking chain
        always finishes first."""
        if self._cap_closed:
            return
        self._cap_closed = True
        elapsed = round(time.perf_counter() - self._call_start, 1) if self._call_start else None
        log.warning("call cap reached on call %s (turns=%d, elapsed_s=%s) — graceful close",
                    self.call_sid, self._real_turns, elapsed)
        self.tracer.span("session:turn_cap_close", output={"real_turns": self._real_turns})
        line = ("We're having some temporary technical issues on my end — I'll register "
                "everything we discussed and Jay will call you back. Have a great day!")
        self._tts_context = self.tts.new_context_id() if self.tts else None
        if self.gate:
            self.gate.add(line)
            await self.gate.end_of_turn()
        await asyncio.sleep(HANGUP_GRACE_S)
        try:
            await self.ws.close(code=1000)
        except Exception:
            pass
        await self.stop(reason="turn_cap")

    # ------------------------------------------------------------------ #
    # TTS plumbing
    # ------------------------------------------------------------------ #
    async def _speak_chunk(self, text: str, continue_: bool):
        # iter65 T4: first TTS request of the turn — stamp the request anchor
        # (tts_first_byte span = first audio byte minus this). getattr guards:
        # some tests build CallSession objects without __init__.
        clock = getattr(self, "_speak_clock", None) or getattr(self, "_clock", None)
        if clock is not None and clock.extra.get("t_tts_req") is None:
            clock.extra["t_tts_req"] = time.perf_counter()
        if self.tts and self._tts_context:
            # V3 speech normalization: what Retell did in its platform layer,
            # now deterministic and self-hosted. Runs per flushed sentence —
            # µs of regex, never touches history/dvs/prompts.
            if self.settings.tts_normalize and text:
                text = normalize_for_tts(text, phone_style=self.settings.tts_phone_style)
            # iter21 naturalness: per-sentence inline SSML variance (Cartesia).
            # Tags sit at the START of the request (never mid-tag), so the
            # streaming path never speaks them — verified by A/B duration.
            if text and self.settings.tts_provider == "cartesia" \
                    and getattr(self.settings, "tts_delivery_jitter", False):
                text = _ssml_jitter(self.settings) + text
            # V5 delivery profile: dict lookup on the turn's state — the
            # state machine, not the LLM, decides how it sounds.
            await self.tts.speak(
                self._tts_context, text, continue_,
                overrides=resolve_delivery(self.settings, self._turn_state),
            )

    async def _on_tts_audio(self, b64_payload: str, context_id: str):
        # iter55 T0 (F-06): dedicated greeting anchors — stamped BEFORE the
        # turn-0 clock logic; the greeting span uses these, never the clock.
        greet = self._greet
        if greet is not None and context_id == greet.get("ctx"):
            now = time.perf_counter()
            if greet.get("first_audio") is None:
                greet["first_audio"] = now
                if getattr(self.settings, "warm_observability", True) \
                        and self.tracer:
                    self.tracer.span("greeting:first_audio", metadata={
                        "stream_to_first_ms":
                            round((now - greet["t_stream"]) * 1000)})
            greet["last_audio"] = now
        clock = self._speak_clock or self._clock    # iter21: the TURN being spoken, not the newest
        if clock.t_tts_first is None:
            clock.mark_tts_first()
            # iter65 T4: tts_first_byte span — first audio byte minus the
            # turn's first TTS request (tracer None-guard; once per turn).
            t_req = clock.extra.get("t_tts_req")
            if t_req is not None and self.tracer:
                self.tracer.span("tts_first_byte", metadata={
                    "ms": round((clock.t_tts_first - t_req) * 1000, 1),
                    "turn": clock.turn_index})
        if self.transport == "browser":
            self._send_raw(_b64decode(b64_payload))    # raw PCM s16le -> /mic ws
        else:
            self._send({"event": "media", "streamSid": self.stream_sid,
                        "media": {"payload": b64_payload}})
        # iter38 F6: t_audio_out is stamped by the WRITER after the bytes are
        # actually written to the socket (was stamped here — same instant as
        # tts_first — which made tts_first_to_audio_out_ms a structural ~0.0).

    # ------------------------------------------------------------------ #
    # outbound writer (single sender for the Twilio/browser WS)
    # ------------------------------------------------------------------ #
    def _send(self, msg: dict):
        try:
            self._outbox.put_nowait(msg)
        except Exception:
            pass

    def _send_raw(self, audio: bytes):
        try:
            self._outbox.put_nowait(audio)
        except Exception:
            pass

    async def _writer(self):
        try:
            while True:
                msg = await self._outbox.get()
                if msg is None:
                    break
                try:
                    if isinstance(msg, (bytes, bytearray)):
                        await self.ws.send_bytes(bytes(msg))
                        # iter38 F6: first real socket write of this speak clock =
                        # audio OUT (caller-audible boundary).
                        clock = self._speak_clock or self._clock
                        if clock.t_audio_out is None:
                            clock.mark_audio_out()
                    else:
                        await self.ws.send_text(json.dumps(msg))
                except RuntimeError:
                    # iter38: ws already closed (e.g. the cap-close path) — the
                    # 2026-09-09 :8007 test died on a send-after-close warning.
                    break
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.warning("session writer stopped: %s", exc)


def _b64decode(s: str) -> bytes:
    import base64
    return base64.b64decode(s)
