# Turn-Taking Fixes — Implementation-Grade Patches for the Dialux SDR Engine

**Companion to:** `voice-sdr-turn-taking-research.md` (the research) · **This file:** the fixes themselves.
**Target repo:** `Cesars-dev/diallux_sdr_almost_there` @ `0ce798f` (engine = iter66-era + iter73 playback-rate fix; iter70 speech-fix branch is plan-only in this snapshot).
**Date:** 2026-09-26 · **Answer to "did the report include fixes?":** the research report diagnosed the six failure modes, verified how Vapi/Retell/LiveKit/Deepgram/ElevenLabs/Pipecat solve them, and ranked 8 ports — but it stopped at port *sketches*. **This document is the missing half: diff-level, code-first fixes for every port, written against the actual engine source.**

---

## 0. How to Use This Document

### 0.1 What each fix contains

Every fix (FIX 1–8, in one-to-one correspondence with the research PORT 1–8) is a self-contained work order:

1. **Failure modes fixed** — which of F1–F6 it kills, and by which edge of the failure graph.
2. **Mechanism copied** — the platform whose design it ports, with the primary-source justification already verified in the research doc (§2 dossiers D1–D11).
3. **Design** — what changes, in which file, at which seam.
4. **Code** — the actual hunks. Written to match repo house style (dense `# iterNN:`-style comments, here tagged `FIX N (PORT N)`).
5. **DELETES** — what becomes dead code. Per the research contract, every port that can delete machinery does.
6. **Tests** — pytest cases in the `tests/test_iterNN_*.py` culture.
7. **Rollout & rollback** — the env knob, the lane procedure, the metrics to watch.

### 0.2 Working laws (unchanged, restated)

These come from the repo's own doctrine and the owner's session laws; every fix below obeys them:

- **Env-knob-first, default-off.** Every fix ships behind a knob whose default value reproduces **byte-exact today behavior**. `False`/`0`/`off` = the current engine, always.
- **One variable per fix.** Each knob flips exactly one mechanism. No fix depends on another being enabled (FIX 4 *reuses* FIX 1's gate-hold primitive, but degrades gracefully if FIX 1 is off).
- **HITL stop at every task.** Each fix lands as its own branch + battery + owner ear-verdict before merge. Merge is owner-only (LAW 0).
- **≤60-line diffs per commit.** The hunks below are grouped so each committed task stays under the PT-73 line budget; where a fix needs more, it is split into T1/T2/T3 tasks.
- **No cherry-picks from parked branches.** Everything here is written fresh against `0ce798f` main. The parked iter68/iter70 branches are read-only reference (PT-73 law).
- **The owner's ear is the gate.** A fix is "done" when the A/B ear verdict says so, not when tests pass.

### 0.3 F1–F6 recap — the failure graph we are cutting

| # | Failure mode | What the caller hears | The seam that produces it (verified @ `0ce798f`) |
|---|---|---|---|
| **F1** | Re-ask loop | Agent asks → caller answers → agent *re-asks the same question* over the answer → both talk over each other → agent asks again | `pause_reask`-class timer re-prompt (plan-only; live lane) + barge-in re-anchoring (`_on_start_of_turn`, `session.py:583` resets `_update_fired`/`_t_speech_growth`/`_last_update_len` mid-speech, `session.py:599–604`) + fragment `user_text` reaching the LLM |
| **F2** | Going mute | Silence — agent "completes" a turn but nothing comes out of the speaker | Prewarmed STT socket adopted without any liveness check (`session.py:197–223`, `prewarm.py:83–94`; the 39s zombie, PT-68) or long tool-chain dead air with no filler |
| **F3** | Double/triple turns | Agent answers the same utterance 2–3 times; stacked "Okay, so you said…" recounts | Round stacking + said-truth drift: history stores the LLM's **full** text even when TTS was cut (`builder.py:2469–2481`) |
| **F4** | Transition silence | Caller says "yeah" mid-question → agent's question dies → awkward beat instead of ack + next question | Flat ack spawns a turn: `_on_start_of_turn` yields the floor to any speech, including backchannels |
| **F5** | Speculation mismatch | Agent starts answering before the caller finished, then stumbles/collides when speech continues | Eager path releases **audio** at `EagerEndOfTurn` (`session.py:466–515`) instead of holding it for confirmed `EndOfTurn` (Deepgram's own two-moment contract releases audio only at EOT) |
| **F6** | Mid-sentence TTS cuts | Question chopped mid-audio; "sorry, what?" | TTS-side content surgery (question clamp, yield-on-"?", dedupe family) — a layer **no shipping platform has**; the correct fix is upstream (F4/F6-aftermath via FIX 6) |

**F1 loop mechanics (from the research, confirmed against code):** (i) a re-prompt speaks while the caller answers → (ii) `_on_start_of_turn` cancels it and re-anchors the cumulative-Update bookkeeping mid-speech → (iii) the caller's in-flight words fragment across the re-anchored accumulation → (iv) the next EOT carries a fragment/empty `user_text` → (v) the model, seeing no answer, re-asks. FIX 2 (no scripted re-ask), FIX 3 (fragments never reach the LLM), FIX 4 (an "answer" that was really an ack doesn't yield), FIX 5 (no collide-re-speak) and FIX 1 (no early audio to collide with) each cut a different edge. That redundancy is deliberate — every edge has independently reproduced in the logs.

---

## 1. New Knob Registry — one `config.py` patch for all eight fixes

All fixes are env-first. Land this single patch once (its own commit, `T0`); every fix then only *reads* knobs.

```python
    # ---- FIX 1–8 (PORT 1–8): turn-taking fixes, 2026-09-26 ---------------- #
    # ALL defaults below = exact pre-fix engine behavior. Every knob flips
    # exactly one mechanism (owner law); see voice-sdr-turn-taking-fixes.md.
    #
    # FIX 1 (PORT 1): eager-think, confirmed-speak. Hold the eager turn's
    # TTS audio at the SentenceGate until the confirmed EndOfTurn adopts it;
    # TurnResumed discards silently. Deepgram two-moment contract; LiveKit
    # ships the same default (preemptive_tts=false).
    eager_hold_audio_until_confirm: bool = False
    #
    # FIX 2 (PORT 2): pause ladder — Vapi customer.speech.timeout shape.
    # "off" = no timer at all (snapshot behavior). "reminder" = deterministic
    # say.exact nudges, never an LLM round, never a state round.
    pause_ladder_mode: str = "off"               # off | reminder
    pause_reask_ms: int = 10000                  # rung 1 (Vapi default 10s)
    pause_ladder_max: int = 2                    # nudges before the close rung
    pause_close_ms: int = 30000                  # close rung (Vapi 30s endCall)
    pause_reminder_text: str = "Hey, you still there?"
    pause_reminder_text_2: str = ("No rush at all - take your time. "
                                  "Just say whenever you're ready.")
    pause_close_text: str = ("Seems like you stepped away - no worries at "
                             "all. We'll try again another time. "
                             "Have a great day!")
    #
    # FIX 3 (PORT 3): confidence-band ingest firewall (Vapi
    # endpointedSpeechLowConfidence). Inert until the provider actually
    # sends a confidence on EndOfTurn (verify with stt_log_raw_eot=true).
    # Band [floor, ceil] -> canned repeat request, no LLM round.
    # < floor -> silent drop, ladder re-armed. ceil=0 disables banding.
    stt_confidence_floor: float = 0.2            # Vapi floor = max - 0.2
    stt_confidence_reask_ceil: float = 0.4       # Vapi ceiling ~= 0.4
    stt_confidence_reask_text: str = ("Sorry, you cut out for a second - "
                                      "could you say that again?")
    stt_log_raw_eot: bool = False                # one JSON dump per EOT (verify field)
    #
    # FIX 4 (PORT 4): ack/backchannel filter + false-interruption resume.
    # Barge-in audio stops immediately (always), but the TURN-cancel decision
    # waits barge_false_interrupt_timeout_ms for the interrupting speech to
    # declare itself: ack-list or no transcript -> resume the held speech
    # (LiveKit false_interruption_timeout / resume_false_interruption).
    barge_ack_filter: bool = False
    barge_false_interrupt_timeout_ms: int = 2000  # LiveKit default 2.0s
    barge_ack_phrases: str = ("yeah,yep,yup,okay,ok,right,uh-huh,mm-hmm,"
                              "mhm,sure,alright,got it")
    # NOTE: bare "yes" is deliberately NOT in the default list - in a sales
    # call "yes" is often a real ANSWER to the question the agent just asked,
    # not a backchannel. Owner may add it after ear-testing.
    #
    # FIX 5 (PORT 5): post-interrupt backoff (Vapi backoffSeconds, default
    # 1.0s). After a REAL barge-in, the next turn's first TTS chunk waits
    # out the window so the caller's answer lands first.
    post_interrupt_backoff_ms: int = 1000        # 0 = off
    #
    # FIX 6 (PORT 6): said-truth history commit (Pipecat). On a true
    # barge-in, the conversation view the LLM sees is rewritten to the
    # spoken-so-far text (belief == audio).
    history_said_truth_only: bool = False
    #
    # FIX 7 (PORT 7): STT liveness. Adoption age gate + recv-heartbeat
    # zombie watchdog (fires the EXISTING transparent reconnect path).
    stt_adopt_max_age_s: float = 120.0           # refuse older pooled sockets
    stt_rx_zombie_ms: int = 15000                # 0 = off; > eot_timeout(2500)
    #
    # FIX 8 (PORT 8): general one-shot soft filler on tool/LLM latency
    # (ElevenLabs soft_timeout semantics: once per turn, deterministic text,
    # never model-generated). 0 = off; iter40 L3 slots filler stays as-is.
    soft_filler_ms: int = 0                      # recommended first live value: 3000
    soft_filler_text: str = "One moment while I check that for you."
```

**Verification key for the rest of this document:** every mechanism claim (Vapi/Retell/LiveKit/Deepgram/ElevenLabs/Pipecat) was verified against primary sources in the research doc; where a default value is quoted (2.0s, 1.0s, 10s/20s/30s, 0.2/0.4, 3.0s) the citation lives in the research doc §7 source index. This document only re-states what the code should do.

---

## 2. FIX 1 — Eager-Think, Confirmed-Speak

**Ports:** Deepgram D1 (two-moment turn contract) + LiveKit D2 (`preemptive_tts: false` default).
**Fixes:** F5 (speculation/adoption mismatch), the talk-over half of F1, mid-speech audio collisions.
**Knob:** `EAGER_HOLD_AUDIO_UNTIL_CONFIRM=true`.

### 2.1 Design

Today, `EagerEndOfTurn` starts a full turn **including TTS audio** (`session.py:466–515`); `TurnResumed` then has to cancel speech that is already in flight — the grace-window machinery (`_grace_then_cancel`, `eager_resume_grace_ms`) exists solely to manage that waste. Every shipping platform does the opposite split: **think early, speak only on confirmation**. Deepgram's managed agent starts the LLM at `EagerEndOfTurn` but gates audio release on `EndOfTurn`; LiveKit ships `preemptive_generation.enabled=true` with `preemptive_tts=false`.

The change is surgical and reuses the existing pipeline: the `SentenceGate` gains a **hold** state. An eager turn's tokens still stream from the LLM (all the latency banking — prompt prewarm, RAG fire, first-token head start — still happens), but the gate stops flushing sentences to TTS. When the confirmed `EndOfTurn` adopts the running turn (the existing adopt branch at `session.py:361–382`), the gate **releases** and the audio flows. When `TurnResumed` fires instead, the turn is **discarded silently** — no TTS cancel, no Twilio `clear`, because nothing was ever spoken.

```
EagerEndOfTurn ──> LLM round starts, gate.hold()          [think early]
EndOfTurn (adopt)──> gate.release() ──> TTS audio flows    [speak confirmed]
TurnResumed ──────> gate.discard(), task.cancel()          [silent teardown]
```

### 2.2 Code — `media/sentence_gate.py`

```python
class SentenceGate:
    def __init__(self, on_sentence: OnSentence, managed: bool = False):
        self.on_sentence = on_sentence
        self.managed = managed
        self._buffer = ""
        self._timer_task: asyncio.Task | None = None
        self._closed = False
        self._last_continue_sent = False
        self._queue: asyncio.Queue[tuple[str, bool] | None] = asyncio.Queue()
        self._sender_task: asyncio.Task | None = None
        # FIX 1 (PORT 1): hold state — buffer tokens without flushing.
        # Used by the eager path (audio held until confirmed EndOfTurn) and
        # by the FIX 4 barge-in hold window.
        self._held = False
        self._held_final = False
```

`add()` grows an early-out so a held gate only accumulates:

```python
    def add(self, token: str) -> None:
        """Called for every LLM content delta (sync — cheap, no awaits)."""
        if self._closed or not token:
            return
        self._ensure_sender()
        self._buffer += token
        if self._held:                    # FIX 1: buffering only, no flush
            return
        if not self._managed:
            if len(self._buffer) >= _MIN_LEN:
                m = _SENTENCE_END.search(self._buffer)
                if m:
                    self._flush_upto(m.end())
            if len(self._buffer) >= _FLUSH_LEN:
                self._flush_upto(len(self._buffer))
        self._schedule_idle_flush()
```

`end_of_turn()` parks its final marker if still held (the LLM stream can legitimately finish before the confirmed EOT arrives — a short answer):

```python
    async def end_of_turn(self) -> None:
        """Turn finished: mark the context done; drains all queued chunks."""
        self._cancel_timer()
        if self._closed:
            return
        if self._held:
            # FIX 1: stream ended while audio is held — park the final
            # flush; release() performs it when confirmation arrives.
            self._held_final = True
            return
        text = self._buffer.strip()
        self._buffer = ""
        ... (unchanged) ...
```

The three new primitives:

```python
    def hold(self) -> None:
        """FIX 1 (PORT 1): stop flushing — buffer tokens until release()/
        discard(). Queued chunks are untouched (while held, none are made).
        Idempotent: holding a held gate is a no-op."""
        self._held = True
        self._cancel_timer()

    async def release(self) -> None:
        """FIX 1 (PORT 1): confirmation arrived — flush everything buffered
        while held, at normal sentence boundaries. If the LLM stream already
        parked its final marker, the closing flush (continue=false) runs
        exactly as the normal end_of_turn path would have."""
        if not self._held:
            return
        self._held = False
        if self._closed:
            self._held_final = False
            return
        if not self._managed:
            if len(self._buffer) >= _MIN_LEN:
                m = _SENTENCE_END.search(self._buffer)
                if m:
                    self._flush_upto(m.end())
            if len(self._buffer) >= _FLUSH_LEN:
                self._flush_upto(len(self._buffer))
        final = self._held_final
        self._held_final = False
        if final:
            await self.end_of_turn()          # normal final flush + drain
        elif self._buffer.strip():
            self._schedule_idle_flush()

    async def discard(self) -> None:
        """FIX 1 (PORT 1): speculation was wrong (TurnResumed) — drop the
        held buffer. Like reset() minus the queue surgery: while held,
        nothing was ever queued, so the queue is already empty."""
        self._held = False
        self._held_final = False
        self._cancel_timer()
        self._buffer = ""
        self._last_continue_sent = False
```

And `reset()` must clear the hold too — this makes **every** cancel path safe by construction (a stale hold could otherwise buffer a whole rerun turn forever):

```python
    async def reset(self) -> None:
        """Barge-in: drop buffered text and any queued-but-unsent chunks."""
        self._cancel_timer()
        self._held = False                   # FIX 1: never leak a hold
        self._held_final = False
        self._buffer = ""
        self._last_continue_sent = False
        self._drop_queue()
```

### 2.3 Code — `media/session.py`

Class-level default (the no-`__init__` test convention):

```python
class CallSession:
    _eager_transcript: str | None = None
    _resumed_count = 0
    _greet: dict | None = None
    _t_speech_growth: float | None = None
    _last_update_len = 0
    _eager_held: bool = False                # FIX 1 (PORT 1)
```

In `_run_turn`, after the TTS context is minted:

```python
        self._tts_context = self.tts.new_context_id() if self.tts else None
        # FIX 1 (PORT 1): a turn that started at EagerEndOfTurn runs the
        # LLM now, but its AUDIO is held at the gate; the confirmed EOT
        # (adopt branch in _on_eot) releases, TurnResumed discards.
        self._eager_held = bool(clock.extra.get("eager")) and \
            bool(getattr(self.settings, "eager_hold_audio_until_confirm",
                         False))
        if self._eager_held and self.gate:
            self.gate.hold()
```

In `_on_eot`, inside the existing adopt branch (after `self._update_fired = False`, before the `log.info("eot adopted running eager turn (no rerun)")`):

```python
                    self._eager_transcript = None
                    self._clock.extra["resume_pending"] = False
                    self._update_fired = False
                    if getattr(self, "_eager_held", False) and self.gate:
                        self._eager_held = False
                        await self.gate.release()   # FIX 1: audio flows NOW
                        log.info("eager turn audio released at confirmed EOT")
                    log.info("eot adopted running eager turn (no rerun)")
                    return
```

In `_on_turn_resumed`, a new first branch **before** the grace-window logic:

```python
    async def _on_turn_resumed(self):
        """User kept talking: the speculative turn is cancelled."""
        self._resumed_count += 1
        if self._turn_task and not self._turn_task.done() and self._clock.extra.get("eager"):
            if getattr(self, "_eager_held", False):
                # FIX 1 (PORT 1): nothing was ever spoken — discard
                # silently. No TTS cancel (no context was ever sent), no
                # Twilio clear (none of our audio is playing). The task
                # cancel's own gate.reset() is a harmless no-op on the
                # already-discarded gate.
                self._eager_held = False
                self._clock.extra["eager"] = False
                self._clock.extra["resume_pending"] = False
                self._turn_task.cancel()
                if self.gate:
                    await self.gate.discard()
                log.info("eager turn discarded silently "
                         "(user resumed, audio was held)")
                return
            # ... existing grace-window / cancel path unchanged ...
```

### 2.4 Telemetry and latency math

- `head_start_ms` (already stamped, iter43 T1) measures `EndOfTurn − EagerEndOfTurn` — that is exactly the **extra TTFT** this fix pays, and it is bounded by `eot_timeout_ms` (2500) minus the eager threshold's earlier fire. In practice the Sep-24 mic call measured `eot_silence_wait` p50 ≈ 700–1,550ms; expect the confirmed-speak TTFT to land 300–900ms after the old eager TTFT, in exchange for zero mid-speech collisions.
- `tts_first_byte` now anchors at the release flush (the `t_tts_req` stamp in `_speak_chunk` fires on the first post-release chunk). No code change needed — the stamp is lazy.
- `eager_final_match` continues to be logged; with the hold on, a mismatch (the guarded branch at `session.py:356–360`) now costs nothing audible — the rerun happens on a turn that never spoke.

### 2.5 DELETES (after the battery passes)

- `_grace_then_cancel()` (session.py:548–567) — the entire method.
- The `eager_resume_grace_ms` knob + its branch in `_on_eot` (session.py:356–360) and `_on_turn_resumed` — the grace window exists to avoid wasting *spoken* partial turns; with audio held there is nothing to grace.
- The iter38 F1 race-guard ordering dance around `extra["eager"]` (session.py:536–541) — the discard path clears the marker itself; keep the clearing lines only.
- Keep the deletes in a **separate T3 commit** so the A/B is fix-vs-main, not fix-vs-deleted.

### 2.6 Tests (`tests/test_iter74_eager_hold.py`)

1. `test_held_gate_buffers_until_release` — `gate.hold()`; `add("Hello there. ")`; assert `on_sentence` not called; `await gate.release()`; assert the sentence flushed with `continue=True`.
2. `test_end_of_turn_parks_while_held` — hold; add; `await gate.end_of_turn()`; assert nothing sent; `await gate.release()`; assert final chunk carried `continue=False` and the queue drained.
3. `test_resume_discards_silently` — fake TTS + fake ws; run an eager turn held; fire `_on_turn_resumed`; assert **no** `tts.cancel`, **no** `clear` event, gate buffer empty.
4. `test_adopt_releases_audio` — `_on_eager_eot("Friday works")` then `_on_eot("Friday works")`; assert adopt log + at least one `_speak_chunk` call after release.
5. `test_mismatch_rerun_not_stuck` — held eager turn; `_on_eot` with a *different* transcript (grace=0 → cancel+rerun); assert the rerun turn's tokens reach `on_sentence` (gate not stuck held — the `reset()` hold-clear proving itself).
6. `test_knob_off_is_byte_exact` — with `eager_hold_audio_until_confirm=False`, an eager turn flushes during the stream exactly as today (golden-log comparison).

### 2.7 Rollout

Lane procedure: branch `engine/iter74-eager-hold` → `T0` knob patch → `T1` gate primitives + tests → `T2` session wiring + tests → battery (`happy3` 3/3 BOOK + fake-caller barge script) → ear A/B on `:8024` (`EAGER_HOLD_AUDIO_UNTIL_CONFIRM=true`, everything else stock) → owner verdict → `T3` deletes → merge ask. Rollback at any point: env off, zero code path changes.

---

## 3. FIX 2 — Reminder Ladder: Tagged, Deterministic, Never a State Round

**Ports:** Vapi D4 (`customer.speech.timeout` hooks + `say.exact`, ladder 10s/20s/30s, `triggerMaxCount`, reset-on-user-speech) + Retell D3 (`reminder_required` tagging — the future LLM variant).
**Fixes:** F1's core loop amplifier — the re-prompt that asks the *same scripted question*.
**Knob:** `PAUSE_LADDER_MODE=reminder` (+ `PAUSE_REASK_MS`, `PAUSE_LADDER_MAX`, `PAUSE_CLOSE_MS`).

### 3.1 Design

`pause_reask` does not exist in this snapshot (iter70 T2 is plan-only; the live lane's timer is the one producing the F1 re-ask loops). The research verdict is unambiguous: **no shipping platform re-runs the state machine to nudge a silent caller.** Vapi fires a hook that speaks either a verbatim `say.exact` line or a small `say.prompt` — outside the LLM round, capped per call. Retell tags the round `reminder_required` so the LLM knows it is checking in, not answering.

This fix ships the whole mechanism fresh, in Vapi's shape, at the session layer:

```
agent audio finishes (twilio mark echo / browser drain)
   └─ arm: silence clock starts
        ├─ 10s  → rung 1: "Hey, you still there?"        (say.exact, no LLM)
        ├─ 20s  → rung 2: "No rush - take your time..."   (say.exact, no LLM)
        └─ 30s  → close rung: goodbye + hangup             (deterministic)
any caller speech (StartOfTurn or transcript growth) → disarm instantly
```

Laws baked into the design:

1. **The nudge is deterministic text spoken straight to TTS** — same pattern as the begin-message greeting (`session.start()` already does `await self.tts.speak(ctx, begin, ...)`). Zero LLM rounds, zero graph invocations, zero `rounds_left` consumption, zero state mutation, nothing written to history. The model never even knows a nudge happened — exactly Vapi `say.exact` semantics.
2. **Timers measure from one arm point** (end of agent speech), matching Vapi's `timeoutSeconds` per hook. The nudges do **not** re-arm the close clock; only *user* speech resets the ladder (`triggerResetMode: onUserSpeech`).
3. **Capped structurally**: `pause_ladder_max` rungs per call, then the close rung.
4. **Fix 2 ships after FIX 8** so the ladder never polices tool-wait dead air — the soft filler owns that; the ladder only handles true caller absence.

### 3.2 Code — `media/session.py`

Shared deterministic speaker (also used by FIX 3's re-ask band):

```python
    async def _speak_exact(self, text: str) -> None:
        """FIX 2/3 (PORT 2/3): Vapi say.exact — deterministic text spoken
        straight to TTS on a fresh context. Zero LLM rounds, zero graph
        state, zero history writes. Same pattern as the begin-message."""
        if self._stopped or self._ended or not self.tts:
            return
        try:
            ctx = self.tts.new_context_id()
            await self.tts.speak(ctx, text, False,
                                 overrides=resolve_delivery(
                                     self.settings, self._turn_state))
        except Exception:
            log.exception("say.exact failed on call %s", self.call_sid)
```

Ladder state + arm/disarm/run:

```python
    # FIX 2 (PORT 2): pause-ladder state (Vapi customer.speech.timeout)
    _ladder_task: asyncio.Task | None = None
    _ladder_step = 0

    def _ladder_disarm(self) -> None:
        if self._ladder_task is not None:
            self._ladder_task.cancel()
            self._ladder_task = None

    def _ladder_arm(self) -> None:
        """FIX 2: agent finished speaking — the silence clock starts now.
        Armed at the Twilio mark echo (playback-confirmed) or the browser
        late-report drain. Any caller speech disarms (Vapi reset-on-speech)."""
        if getattr(self.settings, "pause_ladder_mode", "off") != "reminder":
            return
        if self._stopped or self._ended:
            return
        self._ladder_disarm()
        self._ladder_step = 0
        self._ladder_task = asyncio.get_event_loop().create_task(
            self._ladder_run())

    async def _ladder_run(self) -> None:
        nudge_ms = float(getattr(self.settings, "pause_reask_ms", 10000))
        max_n = int(getattr(self.settings, "pause_ladder_max", 2))
        close_ms = float(getattr(self.settings, "pause_close_ms", 30000))
        t0 = time.perf_counter()
        try:
            step = 0
            while step < max_n:
                await self._sleep_until(t0 + nudge_ms * (step + 1) / 1000.0)
                if self._stopped or self._ended:
                    return
                text = (self.settings.pause_reminder_text if step == 0
                        else self.settings.pause_reminder_text_2)
                await self._speak_exact(text)
                step += 1
                self._ladder_step = step
                if self.tracer:
                    self.tracer.span("pause_ladder:nudge",
                                     metadata={"step": step})
                log.info("pause ladder rung %d spoken (reminder)", step)
            await self._sleep_until(t0 + close_ms / 1000.0)
            if self._stopped or self._ended:
                return
            await self._ladder_close()
        except asyncio.CancelledError:
            return

    async def _sleep_until(self, due: float) -> None:
        remaining = due - time.perf_counter()
        if remaining > 0:
            await asyncio.sleep(remaining)

    async def _ladder_close(self) -> None:
        """Close rung: honest goodbye + hangup (Vapi 30s endCall rung).
        Deterministic — the graceful-cap-close pattern, pause-ladder flavor."""
        if self._stopped or self._ended:
            return
        log.warning("pause ladder close on call %s (caller absent, "
                    "nudges=%d)", self.call_sid, self._ladder_step)
        if self.tracer:
            self.tracer.span("pause_ladder:close",
                             metadata={"nudges": self._ladder_step})
        await self._speak_exact(self.settings.pause_close_text)
        await asyncio.sleep(HANGUP_GRACE_S)
        try:
            await self.ws.close(code=1000)
        except Exception:
            pass
        await self.stop(reason="pause_ladder_close")
```

Wiring — four one-liners:

```python
    # on_twilio_mark: playback-confirmed turn end = the arm point (twilio)
    async def on_twilio_mark(self, msg: dict):
        name = ((msg.get("mark") or {}).get("name") or "")
        if self._pending_end_mark and name == self._pending_end_mark:
            ... (unchanged) ...
        elif name.startswith("turn-") and name.endswith("-done"):
            self._ladder_arm()               # FIX 2: audio finished playing

    # _late_turn_report: browser transport has no mark echo — arm at drain
        self._send({"event": "mark", "streamSid": self.stream_sid,
                    "mark": {"name": f"turn-{clock.turn_index}-done"}})
        if self.transport == "browser":
            self._ladder_arm()               # FIX 2 (browser fallback arm)

    # _on_start_of_turn: caller spoke — disarm BEFORE anything else
    async def _on_start_of_turn(self):
        if self._stopped:
            return
        self._ladder_disarm()                # FIX 2: user speech resets ladder

    # _on_stt_update: transcript growth also disarms (mid-speech)
        if len(transcript) > self._last_update_len:
            self._ladder_disarm()            # FIX 2
            self._t_speech_growth = time.perf_counter()
            self._last_update_len = len(transcript)
```

And in `stop()`: `self._ladder_disarm()` next to the `_turn_task` cancel.

### 3.3 The tagged LLM-round variant (spec only — for iter70 T2 to adopt)

When a smarter nudge is wanted, `PAUSE_LADDER_MODE=reminder_llm` (not implemented in this fix) must follow the Retell contract, not the state machine:

- The round's payload carries `interaction_type: "reminder"` and an **empty** `user_text`.
- The state node sees the tag and appends **one post-history directive line** instead of the state head's question machinery:
  `"[reminder] The caller has gone quiet for a while. Check in briefly and warmly - do NOT re-ask your last question, do NOT advance the conversation."`
- The round does not decrement `rounds_left`, cannot fire tools, cannot transition state.
- Cap stays `pause_ladder_max` per call, reset on user speech.
- This deletes the iter68-lite port design (c3022c3 / 651e567: re-ask round = heavy state round + post-history directive) — the reminder is a **tagged interaction**, never a state round.

### 3.4 Tests (`tests/test_iter75_pause_ladder.py`)

1. `test_no_nudge_when_talking` — arm; simulate `_on_stt_update` growth at +2s; advance clock past `pause_reask_ms`; assert zero `_speak_exact` calls.
2. `test_rung1_at_10s_rung2_at_20s_close_at_30s` — arm with a fake clock; assert the two nudge texts and the close text at the right deadlines, in order.
3. `test_max_rungs_respected` — `pause_ladder_max=1`; assert rung 2 never speaks; close still fires.
4. `test_nudge_writes_no_history_no_state` — run a nudge; `aget_state`; assert history/dvs/rounds_left unchanged.
5. `test_knob_off_is_byte_exact` — `pause_ladder_mode=off`; assert no ladder task is ever created (also on long silences).
6. `test_disarm_on_start_of_turn` — arm; fire `_on_start_of_turn`; advance clock; assert silence.

### 3.5 Rollout

Ship **after FIX 8** (soft filler owns tool-wait dead air; the ladder owns true caller absence). Branch `engine/iter75-pause-ladder`. Ear test protocol: 3 silent-caller calls (answer nothing after greeting) — expect nudge at ~10s, second at ~20s, close at ~30s; 3 normal calls — expect zero audible difference. Watch `pause_ladder:*` spans. Rollback: `PAUSE_LADDER_MODE=off`.

---

## 4. FIX 3 — Confidence-Band Ingest Firewall

**Ports:** Vapi D6 (`endpointedSpeechLowConfidence[confidence=min:max]` hook; defaults ceiling ≈ transcriber threshold 0.4, floor = ceiling − 0.2).
**Fixes:** the fragment half of F1 (fragment `user_text` → model re-asks), F5's fragment finals.
**Knobs:** `STT_CONFIDENCE_FLOOR=0.2`, `STT_CONFIDENCE_REASK_CEIL=0.4`, `STT_CONFIDENCE_REASK_TEXT`, `STT_LOG_RAW_EOT`.

### 4.1 Design

Vapi discards low-confidence endpointed transcripts **before they reach the LLM**, and speaks a canned "please repeat" for the borderline band. This is the structural kill for "fragment `user_text` → model re-asks": the model never sees the fragment. Our bands, verbatim Vapi semantics:

```
confidence >= 0.4          → run the round (today's path, unchanged)
0.2 <= confidence < 0.4    → speak ONE canned line via TTS, NO LLM round,
                             ladder re-arms (the repeat answer is awaited)
confidence < 0.2           → drop silently, ladder re-arms
confidence is None         → today's behavior (feature inert)
```

**Precondition — verify the field first.** The Deepgram Flux `TurnInfo.EndOfTurn` payload is not documented as carrying a `confidence` field in our harvested docs. The nova3 `Results` alternatives do (`alt.get("confidence")`). So this fix lands in two steps:

- **T0 (observation):** set `STT_LOG_RAW_EOT=true` on the lane for a handful of calls; `deepgram_stt._handle` dumps the raw EndOfTurn JSON once per turn. If no confidence field exists on flux, the band logic stays permanently inert (None passthrough) and the fallback is the documented length-heuristic in §4.4 — decided by the owner with the payload in hand, not guessed.
- **T1 (the firewall):** the code below.

### 4.2 Code — `media/deepgram_stt.py`

Pass confidence through (signature widens; `None` default keeps every existing caller/test valid):

```python
OnEOT = Callable[[str, "float | None"], Awaitable[None]]
```

```python
    async def _handle(self, msg: dict):
        mtype = msg.get("type")
        if mtype == "TurnInfo":                      # Flux v2
            event = msg.get("event")
            transcript = (msg.get("transcript") or "").strip()
            if event == "EndOfTurn" and transcript:
                if getattr(self.settings, "stt_log_raw_eot", False):
                    log.info("raw EndOfTurn payload: %s",
                             json.dumps(msg)[:600])   # FIX 3 T0: field check
                await self.on_eot(transcript,
                                  msg.get("confidence"))   # FIX 3
            ... (rest unchanged) ...
        elif mtype == "Results":                     # nova3 v1
            if not msg.get("is_final"):
                return
            alt = ((msg.get("channel") or {}).get("alternatives") or [{}])[0]
            text = (alt.get("transcript") or "").strip()
            if text:
                self._final_buffer.append(text)
            if msg.get("speech_final"):
                full = " ".join(self._final_buffer).strip()
                self._final_buffer = []
                if full:
                    await self.on_eot(full, alt.get("confidence"))  # FIX 3
```

### 4.3 Code — `media/session.py`

```python
    async def _on_eot(self, transcript: str,
                      confidence: float | None = None):
        if self._stopped or self._ended:
            return
        # FIX 3 (PORT 3): confidence-band ingest firewall (Vapi
        # endpointedSpeechLowConfidence). None (no provider confidence or
        # banding disabled) = today's behavior, byte-exact.
        ceil = getattr(self.settings, "stt_confidence_reask_ceil", 0.0)
        if confidence is not None and ceil > 0:
            floor = getattr(self.settings, "stt_confidence_floor", 0.0)
            if confidence < floor:
                log.info("speech_filter: EOT below confidence floor "
                         "(%.2f < %.2f) - dropped, ladder re-armed",
                         confidence, floor)
                if self.tracer:
                    self.tracer.span("stt_conf:drop",
                                     metadata={"confidence": confidence})
                self._ladder_arm()               # FIX 2: silence clock restarts
                return
            if confidence <= ceil:
                log.info("speech_filter: EOT in re-ask band "
                         "(%.2f in [%.2f, %.2f]) - canned repeat request",
                         confidence, floor, ceil)
                if self.tracer:
                    self.tracer.span("stt_conf:reask",
                                     metadata={"confidence": confidence})
                await self._speak_exact(                 # FIX 2 helper
                    self.settings.stt_confidence_reask_text)
                self._ladder_arm()
                return
        ... (existing _on_eot body unchanged) ...
```

Note the synergy: the re-ask band **re-arms the FIX 2 ladder** instead of running an LLM round — the caller's repeat is awaited by the same silence clock that would have fired a scripted re-prompt in the old design. The band, the ladder, and FIX 5's backoff are one coherent "the caller owns the floor" doctrine.

### 4.4 Fallback if Flux carries no confidence (decide after T0)

If the payload dump shows no field, the documented fallback is a **transcript-shape band** (weaker, opt-in, off by default): `STT_FRAGMENT_MIN_WORDS=2` — an EOT transcript with fewer than 2 word tokens AND no digits is treated as the re-ask band (canned line, no LLM round). It is weaker because it cannot see audio confidence, only text shape; it is still strictly better than feeding "the" to GPT-5.x and getting a re-ask. Owner decides with the payload in hand.

### 4.5 DELETES

Every LLM round that would have run on a fragment — structurally, the model never sees sub-floor or banded transcripts. No existing code is deleted (the guard is additive); the DELETES here are **rounds, not lines**.

### 4.6 Tests (`tests/test_iter76_conf_band.py`)

1. `test_none_confidence_passthrough` — EOT with `confidence=None` runs the turn exactly as today.
2. `test_below_floor_dropped` — EOT conf 0.1; assert no `_run_turn`, no `_speak_exact`, ladder re-armed.
3. `test_band_reasks_without_llm` — EOT conf 0.3; assert `_speak_exact(reask_text)` fired once, zero graph invocations.
4. `test_above_ceil_runs` — EOT conf 0.8; assert the turn ran.
5. `test_ceil_zero_disables` — `stt_confidence_reask_ceil=0`, conf 0.1; assert the turn ran (feature off).
6. `test_nova3_confidence_threaded` — nova3 `Results` path passes `alt["confidence"]` through.

### 4.7 Rollout

Only after the T0 payload check confirms the field (or the owner picks the fallback). Branch `engine/iter76-conf-band`. Ear test: the fake-caller barge script that used to produce fragment re-asks; expect the canned "you cut out" line instead of a model re-ask. Watch `stt_conf:*` spans + `speech_filter` INFO lines. Rollback: `STT_CONFIDENCE_REASK_CEIL=0`.

---

## 5. FIX 4 — Ack/Backchannel Filter + False-Interruption Resume

**Ports:** Vapi D7 (`acknowledgementPhrases` — backchannels never yield the floor) + LiveKit D7 (`interruption.false_interruption_timeout` 2.0s, `resume_false_interruption` true).
**Fixes:** F4 (transition silence after "yeah"), the false-barge-in share of F1/F3 (the "?"-glue turn and stacked recounts).
**Knobs:** `BARGE_ACK_FILTER=true`, `BARGE_FALSE_INTERRUPT_TIMEOUT_MS=2000`, `BARGE_ACK_PHRASES`.

### 5.1 Design

Today `_on_start_of_turn` (session.py:583) treats **any** caller speech as a real barge-in: cancel the turn, reset the gate, cancel TTS, clear Twilio, and — the F1 wound — re-anchor the cumulative-Update bookkeeping mid-speech. A flat "yeah" mid-question kills the agent's question and spawns a turn that asks "sorry, what?".

The platform split is: **audio stops immediately (barge is always respected), but the turn-cancel decision waits.** LiveKit holds the interruption decision for `false_interruption_timeout` (2.0s default); if no real speech materialized, the agent **resumes** its interrupted utterance. Vapi simply never yields the floor to phrases on the ack list.

The design, in event order:

```
StartOfTurn while a turn is speaking
   ├─ audio stops NOW:        gate.hold() + tts.cancel + twilio clear
   ├─ LLM task KEEPS RUNNING (tokens buffer in the held gate)
   └─ hold window opens (2.0s deadline)
        ├─ Update text arrives:
        │    ├─ >= 3 words  → REAL: resolve(true)  — today's full cancel path
        │    └─ otherwise   → keep accumulating
        ├─ EndOfTurn inside window:
        │    ├─ ack-only text → resolve(false); the ack is CONSUMED
        │    │                  (never committed to history, never a turn)
        │    └─ real text     → resolve(true); normal EOT path runs the turn
        └─ 2.0s deadline, no/ack text → resolve(false)

resolve(false) = false interruption:
   new TTS context, gate.release() → speech RESUMES from where it was cut
   (the held buffer is the unspoken remainder; bookkeeping was never
   re-anchored, so the F1 fragment source is untouched)

resolve(true) = real barge-in:
   today's exact path (task.cancel, gate.reset, re-anchor) + FIX 5 backoff
   stamp + FIX 6 said-truth capture
```

The critical property: on a **false** interruption, `_update_fired` / `_t_speech_growth` / `_last_update_len` are **never reset** — the caller's continued speech accumulates across the window exactly as if nothing happened. That is the Retell D5 doctrine (never touch the input stream) applied to our seams.

### 5.2 Code — `media/session.py`

Ack matcher (module level):

```python
import re

_ACK_CACHE: tuple[str, re.Pattern | None] = ("", None)

def _ack_pattern(phrases_csv: str) -> re.Pattern | None:
    """FIX 4 (PORT 4): Vapi acknowledgementPhrases — compiled ack list.
    A match means the WHOLE utterance so far is a backchannel ("yeah.",
    "okay okay", "mm-hmm?"). Multi-word real speech never matches."""
    global _ACK_CACHE
    if _ACK_CACHE[0] != phrases_csv:
        phrases = [p.strip().lower() for p in phrases_csv.split(",")
                   if p.strip()]
        pat = re.compile(r"^(?:" + "|".join(re.escape(p) for p in phrases)
                         + r")(?:\s+(?:" + "|".join(re.escape(p) for p in phrases)
                         + r"))*[.,!?\s]*$") if phrases else None
        _ACK_CACHE = (phrases_csv, pat)
    return _ACK_CACHE[1]

def _is_ack(text: str, settings) -> bool:
    pat = _ack_pattern(getattr(settings, "barge_ack_phrases", ""))
    return bool(pat and pat.match((text or "").strip().lower()))
```

Session state (class-level defaults for the no-`__init__` tests):

```python
    _barge_hold: dict | None = None          # FIX 4 (PORT 4)
```

`_on_start_of_turn` rewritten as a dispatcher:

```python
    async def _on_start_of_turn(self):
        if self._stopped:
            return
        self._ladder_disarm()                # FIX 2: user speech resets ladder
        interrupted = bool(self._turn_task and not self._turn_task.done())
        if interrupted and getattr(self.settings, "barge_ack_filter",
                                    False):
            # FIX 4 (PORT 4): defer the cancel decision. Audio stops NOW
            # (barge respected); the turn's fate waits for the hold window.
            self._clock.barge_in = True
            self._clock.t_barge_in = time.perf_counter()
            self._barge_hold = {"t0": time.perf_counter(), "text": ""}
            if self.gate:
                await self.gate.hold()        # FIX 1 primitive, shared
            if self.tts and self._tts_context:
                await self.tts.cancel(self._tts_context)
            self._send({"event": "clear", "streamSid": self.stream_sid})
            asyncio.get_event_loop().create_task(self._barge_decide())
            log.info("barge-in hold window open (ack filter)")
            return
        await self._barge_cancel_path(interrupted)
```

Today's body, extracted verbatim (its behavior is the `resolve(true)` path):

```python
    async def _barge_cancel_path(self, interrupted: bool):
        """The pre-FIX 4 cancel path — unchanged semantics, now also the
        'real barge-in' resolution."""
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
        self._update_fired = False       # iter59 C8 re-arm
        self._t_speech_growth = None     # iter65 T4 re-anchor
        self._last_update_len = 0
        if interrupted:
            log.info("barge-in on call %s", self.call_sid)
```

The decider and the resolver:

```python
    async def _barge_decide(self):
        """FIX 4: hold-window deadline (LiveKit false_interruption_timeout).
        No transcript or ack-only text at the deadline -> false interruption
        (resume). Real text resolved earlier via _on_stt_update/_on_eot."""
        timeout = getattr(self.settings,
                          "barge_false_interrupt_timeout_ms", 2000) / 1000.0
        await asyncio.sleep(timeout)
        if self._barge_hold is None or self._stopped:
            return
        text = self._barge_hold["text"]
        false_interrupt = (not text.strip()) or _is_ack(text, self.settings)
        await self._barge_resolve(not false_interrupt)

    async def _barge_resolve(self, real: bool):
        hold, self._barge_hold = self._barge_hold, None
        if hold is None:
            return
        if real:
            log.info("barge-in confirmed real (text=%.60r)", hold["text"])
            await self._barge_cancel_path(True)
            # FIX 5 (PORT 5): the caller's answer owns the floor — stamp
            # the post-interrupt backoff window.
            backoff = getattr(self.settings, "post_interrupt_backoff_ms", 0)
            if backoff > 0:
                self._backoff_until = time.perf_counter() + backoff / 1000.0
            # FIX 6 (PORT 6): snapshot said-truth while the accumulator is
            # intact (gate resets below do not touch it).
            if getattr(self.settings, "history_said_truth_only", False) \
                    and self.runtime is not None:
                await self._capture_said_truth()
            return
        # false interruption: resume the agent's speech from the held
        # remainder. Bookkeeping (_update_fired / _t_speech_growth /
        # _last_update_len) was never re-anchored — the input stream was
        # never touched (Retell D5 doctrine).
        log.info("false interruption (ack/none) - resuming held speech")
        if self.tracer:
            self.tracer.span("barge:false_interrupt",
                             metadata={"text": (hold["text"] or "")[:80]})
        if self.tts:
            self._tts_context = self.tts.new_context_id()
        if self.gate and not getattr(self, "_eager_held", False):
            # FIX 1 interplay: an EAGER-held turn stays held — its audio
            # may only release at a confirmed EndOfTurn, not here.
            await self.gate.release()
```

Feeding the window — in `_on_stt_update` (before the mode dispatch) and at the top of `_on_eot`:

```python
    async def _on_stt_update(self, transcript: str):
        # FIX 4: hold window accumulates the interrupting speech; >= 3
        # words is real speech, resolved immediately (latency matters).
        if self._barge_hold is not None and transcript:
            self._barge_hold["text"] = transcript
            if len(transcript.split()) >= 3:
                await self._barge_resolve(True)
                return
        if len(transcript) > self._last_update_len:
            self._ladder_disarm()            # FIX 2
            self._t_speech_growth = time.perf_counter()
            self._last_update_len = len(transcript)
        ... (existing body unchanged) ...
```

```python
    async def _on_eot(self, transcript: str,
                      confidence: float | None = None):
        if self._stopped or self._ended:
            return
        # FIX 4: an EOT inside the hold window decides it. An ack-only
        # utterance is CONSUMED here — never committed to history, never
        # run as a turn (Vapi acknowledgementPhrases semantics).
        if self._barge_hold is not None:
            text = self._barge_hold["text"] or transcript
            if _is_ack(text, self.settings):
                await self._barge_resolve(False)
                return                      # ack consumed; agent resumes
            await self._barge_resolve(True)  # real: falls through, the
                                             # normal path runs this turn
        ... (FIX 3 band, then the existing body) ...
```

### 5.3 Interaction with FIX 1 (must-read)

Both mechanisms use `gate.hold()`. If a barge-in arrives while an **eager** turn is held (FIX 1 on), the hold window opens on an already-held gate (harmless — `hold()` is idempotent). On `resolve(false)`, the eager hold **persists** (the guard `not self._eager_held` in the release path) — speculative audio may only ever release at a confirmed EndOfTurn. On `resolve(true)`, `_barge_cancel_path` → `gate.reset()` clears every hold. The combination is safe by construction and covered by test 7 below.

### 5.4 DELETES (deferred)

The transition-beat problem's **cause** dies here — the iter68/PT-70 `turn_asked` one-trip patch becomes belt-and-suspenders rather than the load-bearing fix (do not delete it in this iteration; revisit after the battery). The cross-turn `question_stem_window` machinery (builder.py:2264–2266, iter59 T4 — already env-killed) loses its reason to exist: the "?"-glue re-ask stops being generated. Candidate for deletion together with the FIX 6 cleanup pass.

### 5.5 Tests (`tests/test_iter77_ack_filter.py`)

1. `test_ack_midquestion_resumes` — speaking turn; `_on_start_of_turn`; Update "Yeah"; EOT "Yeah"; assert: no new turn ran, gate released, `barge:false_interrupt` span, **no** history append for "Yeah".
2. `test_real_barge_runs_turn` — Update "actually Friday doesn't work"; assert cancel path ran (BARGEINS +1), new turn ran with the full text.
3. `test_three_words_resolve_early` — Update reaching 3 words resolves true before the deadline (no 2s stall).
4. `test_silence_timeout_resumes` — StartOfTurn, no Updates, deadline passes; assert resume (release called, no cancel).
5. `test_bookkeeping_never_reanchored_on_false` — arm anchors; false path; assert `_last_update_len` retains its value and `_update_fired` untouched.
6. `test_ack_list_env_override` — `BARGE_ACK_PHRASES=si,claro` matches "Sí." and not "yeah".
7. `test_eager_hold_survives_false_barge` — eager held turn + ack barge; assert the gate is STILL held after resolve(false).
8. `test_knob_off_is_byte_exact` — `barge_ack_filter=false`; assert the exact pre-fix `_on_start_of_turn` behavior (immediate cancel).

### 5.6 Rollout

Ship **after FIX 1** (shares the gate-hold primitive; degrades gracefully without it, but the battery should test the real configuration). Branch `engine/iter77-ack-filter`. Ear test: the "yeah-mid-question" script ×10 — expect the agent to keep talking through the ack (audio dips ~200–500ms then resumes the same sentence); the fake-caller real-barge script — expect today's behavior for real interruptions. Watch `barge:false_interrupt` vs `BARGEINS` ratio. Rollback: `BARGE_ACK_FILTER=false`.

---

## 6. FIX 5 — Post-Interrupt Backoff (the caller's answer gets the floor)

**Ports:** Vapi D8 (`stopSpeakingPlan.backoffSeconds`, 0–10s, default 1.0s).
**Fixes:** the collide-re-speak component of F1 — the agent re-prompting while the caller is still answering the re-prompt.
**Knob:** `POST_INTERRUPT_BACKOFF_MS=1000` (0 = off).

### 6.1 Design

After any **real** barge-in (FIX 4 decided it was real), Vapi blocks all new agent audio for `backoffSeconds` so the caller's answer lands before the agent can speak again. It is a pure guardrail: no structure deleted, nothing added to the hot path except one timestamp comparison on the first chunk of the next turn. Its real job is making FIX 2 and FIX 3 safe by construction — even if a reminder or a re-ask line races a caller starting to answer, the backoff keeps the agent from talking over the answer that would otherwise fragment.

### 6.2 Code — `media/session.py`

Class-level default:

```python
    _backoff_until: float | None = None      # FIX 5 (PORT 5)
```

The stamp lives in `_barge_resolve`'s real branch (already shown in §5.2). The wait lives in `_speak_chunk`, before the first TTS request of a turn is stamped:

```python
    async def _speak_chunk(self, text: str, continue_: bool):
        clock = getattr(self, "_speak_clock", None) or getattr(self, "_clock", None)
        if clock is not None and clock.extra.get("t_tts_req") is None:
            # FIX 5 (PORT 5): post-interrupt backoff (Vapi backoffSeconds,
            # default 1.0s). The FIRST chunk of the next turn waits out the
            # window so the caller's answer lands before we speak again.
            until = getattr(self, "_backoff_until", None)
            if until is not None:
                self._backoff_until = None          # one-shot
                wait = until - time.perf_counter()
                if wait > 0:
                    await asyncio.sleep(wait)
            clock.extra["t_tts_req"] = time.perf_counter()
        ... (existing body unchanged) ...
```

Notes: the wait applies exactly once per interruption (the stamp guard makes it first-chunk-only); deterministic `_speak_exact` lines (FIX 2 rungs, FIX 3 re-ask) bypass `_speak_chunk` deliberately — they are already owned by their own silence logic and the ladder disarms on user speech anyway.

### 6.3 Tests (`tests/test_iter78_backoff.py`)

1. `test_first_chunk_waits_out_backoff` — real barge; assert the next turn's first `_speak_chunk` slept ≥ the remaining window (mock `asyncio.sleep`).
2. `test_backoff_is_oneshot` — second chunk of the same turn does not wait.
3. `test_no_barge_no_wait` — a normal turn's first chunk sleeps zero.
4. `test_knob_zero_off` — `post_interrupt_backoff_ms=0`; no sleep ever.

### 6.4 Rollout

Independent — can ship in the same first wave as FIX 7/8. Branch `engine/iter78-backoff`. Ear test: fake-caller real-barge script; expect the agent's reply to start ~1s after the caller finishes instead of colliding. Rollback: `POST_INTERRUPT_BACKOFF_MS=0`.

---

## 7. FIX 6 — Said-Truth History Commit (belief == audio)

**Ports:** Pipecat D10 (`on_assistant_turn_stopped` commits spoken-so-far text only; `message.interrupted`).
**Fixes:** the said-truth drift behind F3's stacked recounts ("Okay, so… you said 10-15, that's weekly?" — the model believes it said things that were cut) and F6's aftermath.
**Knob:** `HISTORY_SAID_TRUTH_ONLY=true`.

### 7.1 Design

Today the history write is `assistant_text = content` — the LLM's **full** output — even when a barge-in killed the audio mid-sentence (`builder.py:2469–2481`). The model's belief and the caller's ears diverge; the model then "finishes" unspoken thoughts, re-asks, and recounts. No platform post-filters TTS text to fix this — Pipecat instead commits **the spoken-so-far text** to context at interruption time, making belief == audio by construction.

Two implementation truths shape the design:

1. **`history` is an append-only reducer** (`state.py:29`: `Annotated[list[dict], operator.add]`). An in-place rewrite via `graph.aupdate_state` would *append*, not replace — fighting the checkpointer is the wrong seam. The correct seam is the **prompt build**: the conversation *view* the LLM sees is corrected, while the checkpointer stays append-only. That is exactly Pipecat's design (context commit, not transcript rewrite).
2. **Two interruption shapes exist.** (a) The round *completed* and its audio was cut during playback — a full-text assistant message sits at the tail; the view rewrite *replaces* its content with the spoken-so-far text. (b) The round died *mid-stream* (task cancelled) — no assistant message exists; the view rewrite *inserts* one carrying the partial speech, so the model knows what the caller actually heard.

### 7.2 Code — `media/session.py`

The accumulator (class-level default; cleared at turn start; **survives** gate resets — `gate.reset()` never touches it):

```python
    _spoken_this_turn: list[str] = []        # FIX 6 (PORT 6)
```

In `_run_turn`, first line after `clock = self._clock`:

```python
        self._spoken_this_turn = []          # FIX 6: per-turn accumulator
```

In `_speak_chunk`, top (before normalization — the accumulator keeps the raw sentence text, matching what the model "said" in its own words):

```python
        if text:
            # FIX 6 (PORT 6): said-truth accumulator — the text actually
            # handed toward TTS this turn, pre-normalization.
            self._spoken_this_turn.append(text)
```

The capture (called from `_barge_resolve`'s real branch, §5.2):

```python
    async def _capture_said_truth(self):
        """FIX 6 (PORT 6): on a REAL barge-in, snapshot what was actually
        spoken and where it lives in the conversation, for the prompt-view
        rewrite on the next round (Pipecat spoken-so-far commit)."""
        spoken = "".join(getattr(self, "_spoken_this_turn", []) or []).strip()
        try:
            snap = await self.runtime.graph.aget_state(self._thread_config)
            hist = (snap.values or {}).get("history") or []
            idx = len(hist)
            orig = None
            for i in range(len(hist) - 1, -1, -1):
                if hist[i].get("role") == "assistant":
                    idx = i
                    orig = hist[i].get("content")
                    break
            self.runtime.said_truth = {"idx": idx, "orig": orig,
                                       "spoken": spoken}
            if self.tracer:
                self.tracer.span("said_truth:capture", metadata={
                    "orig_chars": len(orig or ""),
                    "spoken_chars": len(spoken)})
        except Exception:
            log.exception("said-truth capture failed on call %s",
                          self.call_sid)
```

### 7.3 Code — `graph/builder.py`

On `CallRuntime.__init__`: `self.said_truth: dict | None = None`.

Module-level view rewriter:

```python
def _apply_said_truth(history: list[dict], said: dict) -> list[dict]:
    """FIX 6 (PORT 6): rewrite the conversation VIEW so the model's belief
    == the audio the caller heard (Pipecat on_assistant_turn_stopped).

    (a) completed round, audio cut:   tail assistant message content is
        replaced with the spoken-so-far text (dropped when nothing was
        spoken — the caller heard nothing from this turn).
    (b) round died mid-stream:        an assistant message carrying the
        partial speech is INSERTED at the capture index, so it precedes
        the user's barge utterance in the view.
    The checkpointer's append-only history is never touched."""
    idx = said.get("idx", -1)
    if idx < 0 or idx > len(history):
        return history
    spoken = (said.get("spoken") or "").strip()
    orig = said.get("orig")
    out = list(history)
    if orig is None:                              # shape (b): insert
        if spoken:
            out.insert(idx, {"role": "assistant", "content": spoken})
        return out
    cur = out[idx]                                # shape (a): replace
    if cur.get("role") == "assistant" and cur.get("content") == orig:
        if spoken:
            out[idx] = {**cur, "content": spoken}
        else:
            out.pop(idx)
    return out
```

In `_make_state_node`, immediately before `messages = self._build_messages(...)`:

```python
            # FIX 6 (PORT 6): said-truth commit — the conversation view the
            # model sees is rewritten to the spoken-so-far text.
            said = getattr(runtime, "said_truth", None)
            if said is not None and history:
                history = _apply_said_truth(history, said)
                if runtime.tracer:
                    runtime.tracer.span("said_truth:commit", metadata={
                        "turn_idx": state.get("turn_index"),
                        "spoken_chars": len(said.get("spoken") or "")})
                # NOTE: not cleared — the append-only state history keeps
                # the full-text message forever, so the view rewrite must
                # keep applying to every subsequent round of this call.
```

The override is deliberately **not** one-shot: because the checkpointer's history is append-only, the full-text message persists at its index for the whole call, and every subsequent prompt build must keep seeing the corrected view. The rewrite self-invalidates only if the target message's content no longer matches (state moved on in a way that rewrote it — it cannot, by construction).

Edge case, documented: if the interrupted assistant message carries `tool_calls`, the replace keeps the `tool_calls` intact (`{**cur, "content": spoken}` preserves every other key) — required for OpenAI message-list validity, and correct: the tool exchange happened even when the speech was cut.

### 7.4 DELETES (deferred — the big one)

With belief == audio by construction, the **dedupe family** loses its reason to exist: `tts_dedupe_sentences`, `tts_dedupe_window`, the planned `tts_dedupe_similar` (jaccard), and the parked `tts_dedupe_semantic` lineage (already env-killed) become dead-code candidates — the model no longer sees unspoken text it wants to "finish," which is what generated the repetition in the first place. **Do not delete in this fix.** Delete only after a battery with FIX 4 + FIX 6 on proves repetition stays dead with every dedupe knob off (`TTS_DEDUPE_SENTENCES=false`) — that battery is the acceptance test for the deletion, in a separate owner-gated commit.

### 7.5 Tests (`tests/test_iter79_said_truth.py`)

1. `test_completed_round_replaced` — history tail = full text; interrupt after 1 of 3 sentences; assert the next round's `messages` show the tail assistant content == sentence 1 only.
2. `test_midstream_insert` — no assistant message this turn; spoken "So the way i"; assert the view inserts `assistant("So the way i")` before the new user message.
3. `test_nothing_spoken_drops_message` — interrupt before any audio; assert the completed round's assistant message is removed from the view.
4. `test_rewrite_persists_across_rounds` — two subsequent rounds; both see the corrected view.
5. `test_toolcall_message_keeps_calls` — replace on a message with `tool_calls`; assert the calls survive, content swapped.
6. `test_knob_off_is_byte_exact` — `history_said_truth_only=false`; no capture, no rewrite.

### 7.6 Rollout

Ship **after FIX 4** (the capture hook lives in the true-barge resolution; without FIX 4 it can hang off the raw interrupt flag, but the paired battery is the meaningful one). Branch `engine/iter79-said-truth`. Ear test: the barge-heavy fake-caller script — expect stacked "Okay, so you said…" recounts to disappear. Then the deletion battery: dedupe off + FIX 4 + FIX 6 on, ×10 calls, zero repeated sentences. Rollback: `HISTORY_SAID_TRUTH_ONLY=false`.

---

## 8. FIX 7 — STT Liveness Watchdog (kills the adopted-zombie mute)

**Ports:** D11 discipline (Retell 3×7s reconnect + `ping_pong`; Vapi per-stage `reconnecting` hooks; Deepgram `KeepAlive` where the protocol allows it).
**Fixes:** F2's adopted-zombie — 39s of audio piped into a socket that delivered zero messages.
**Knobs:** `STT_ADOPT_MAX_AGE_S=120`, `STT_RX_ZOMBIE_MS=15000` (0 = off).

### 8.1 Design

Two layers, both cheap:

1. **Adoption age gate.** The pool already stamps spawn time (`prewarm.py:_spawn_ts`) and TTL-evicts at 240s (iter61 AUD-12). The gate refuses adoption of any socket older than `stt_adopt_max_age_s` (default 120) — a *probable corpse* by the Cartesia-observed idle-death curve — and lets the session fall back to the existing fresh-connect path (a call never fails on the pool; that law is already in the code).
2. **Recv-heartbeat zombie watchdog.** `DeepgramSTT` stamps `_last_rx` on **every** inbound frame. A session-level watchdog fires the **existing** `_on_stt_disconnect` transparent-reconnect path when caller audio is flowing (`_mic_chunks > 0`) but no STT frame has arrived within `stt_rx_zombie_ms`.

**Honest constraint, stated plainly:** Deepgram Flux sends nothing on silence — a genuinely silent caller and a zombie socket are indistinguishable at the message level, and flux v2 rejects client KeepAlive frames (prewarm.py:91–94, iter61 AUD-11). The watchdog's default is therefore deliberately long (15s ≫ `eot_timeout_ms` 2500 + generous margin) and its false-positive cost is **a transparent reconnect** — the call continues on a fresh socket, at the price of ~1–2s of STT blindness on a caller who has already been silent for 15 seconds. That trade is strictly better than the status quo (a 39s+ mute with no recovery ever). The 39s zombie is caught at 15s worst-case; tune down if the lane shows faster zombie onset.

### 8.2 Code — `media/prewarm.py`

```python
def get(kind: str, max_age_s: float | None = None):
    """Pop one prewarmed socket for adoption (None when empty).
    iter60 AUD-1: cancel the idle companion task FIRST (live recv on an
    adopted TTS socket races the session's recv loop = mute call).
    FIX 7 (PORT 7): max_age_s — refuse probable corpses. An idle socket
    older than the gate is closed + respawned by the maintainer; the
    caller falls back to a fresh connect (never fails on the pool)."""
    t = _companion_tasks.pop(kind, None)
    if t is not None:
        t.cancel()
    ts = _spawn_ts.get(kind)
    if max_age_s is not None and ts is not None \
            and (time.monotonic() - ts) > max_age_s:
        old = pool.pop(kind, None)
        _spawn_ts.pop(kind, None)
        if old is not None:
            try:
                asyncio.get_event_loop().create_task(_close_quiet(old))
            except Exception:
                pass
        log.info("prewarm: refused stale %s (age > %.0fs)", kind, max_age_s)
        return None
    _spawn_ts.pop(kind, None)   # iter61 AUD-12: adopted socket leaves TTL
    return pool.pop(kind, None)
```

### 8.3 Code — `media/deepgram_stt.py`

```python
        self._last_rx: float = 0.0             # FIX 7 (PORT 7): heartbeat

    @property
    def last_rx(self) -> float:
        """FIX 7: monotonic time of the last inbound frame (0 = never)."""
        return self._last_rx
```

In `connect()` (both the adopt and fresh paths), after the socket is bound: `self._last_rx = time.monotonic()`. In `_recv_loop`, immediately after `raw = await self._ws.recv()` succeeds: `self._last_rx = time.monotonic()`.

### 8.4 Code — `media/session.py`

Adoption call site (inside the existing `call_prewarm` block):

```python
                pw = pool_get("stt",
                              max_age_s=getattr(self.settings,
                                                "stt_adopt_max_age_s",
                                                120.0))   # FIX 7 age gate
```

The watchdog (started in `start()` next to the writer task; cancelled in `stop()`):

```python
    async def _stt_liveness_watchdog(self):
        """FIX 7 (PORT 7): audio is flowing but the STT socket is silent —
        the adopted-zombie class (39s piped, zero messages). Fires the
        EXISTING transparent reconnect (_on_stt_disconnect); the call
        continues. Deliberately long horizon: flux emits nothing on
        silence, so a quiet caller is indistinguishable at the message
        level — the false-positive cost is one transparent reconnect."""
        while not self._stopped:
            await asyncio.sleep(1.0)
            try:
                if self.stt is None or self._mic_chunks == 0:
                    continue
                zombie_ms = getattr(self.settings, "stt_rx_zombie_ms", 0)
                if zombie_ms <= 0:
                    return
                last = self.stt.last_rx or 0.0
                silent_for = time.monotonic() - last
                if silent_for > zombie_ms / 1000.0:
                    log.warning("stt zombie suspected: no frames for %.1fs "
                                "(mic chunks=%d) - forcing reconnect",
                                silent_for, self._mic_chunks)
                    if self.tracer:
                        self.tracer.span("stt:zombie_reconnect", metadata={
                            "silent_s": round(silent_for, 1),
                            "mic_chunks": self._mic_chunks})
                    await self._on_stt_disconnect()
                    return                     # the reconnect path rebuilds
            except Exception:
                log.exception("stt liveness watchdog tick failed")
```

One subtlety: `_on_stt_disconnect` rebuilds `self.stt`, whose fresh `connect()` re-stamps `_last_rx` — but the watchdog holds a reference-free loop reading `self.stt` each tick, so after the reconnect the (returned) watchdog is gone anyway; a fresh one is not needed (the new socket is fresh-connect young). If the owner wants continuous coverage, start the watchdog per-socket instead — noted as a tuning option.

### 8.5 Tests (`tests/test_iter80_stt_liveness.py`)

1. `test_stale_socket_refused` — pool a socket, backdate `_spawn_ts` past the gate; `get("stt", max_age_s=120)` returns None and the session fell back to fresh connect.
2. `test_fresh_socket_adopted` — young socket adopts as today.
3. `test_zombie_fires_reconnect` — fake STT with `last_rx` 20s ago and `_mic_chunks=100`; tick the watchdog; assert `_on_stt_disconnect` ran (stt rebuilt).
4. `test_silent_caller_no_premature_fire` — `last_rx` 3s ago; no reconnect within the horizon.
5. `test_knob_zero_off` — `stt_rx_zombie_ms=0`; watchdog exits immediately.

### 8.6 Rollout

Independent — first wave. Branch `engine/iter80-stt-liveness`. Verification: kill the pooled socket server-side (restart the pool maintainer or drop the TTL to force a corpse), run a call, expect the `stt:zombie_reconnect` span and an audible continuation instead of mute. Rollback: `STT_RX_ZOMBIE_MS=0` + `STT_ADOPT_MAX_AGE_S=0` (age gate off when 0 — add `if max_age_s` guard, shown above).

---

## 9. FIX 8 — General One-Shot Soft Filler on Tool/LLM Latency

**Ports:** ElevenLabs D9 (`turn.soft_timeout_config`: static filler, 0.5–8.0s, recommended 3.0s, **fires once per turn**) + Vapi request-start messages ("Hold on a sec" class).
**Fixes:** the dead-air behind F1 — the 5–15s tool-chain silences the pause timer currently polices (and would fire scripted re-asks into).
**Knobs:** `SOFT_FILLER_MS=3000` (0 = off — the recommended first live value), `SOFT_FILLER_TEXT`.

### 9.1 Design

The iter40 L3 filler ("One moment while I check availability.") is a slots-path special case: it fires the moment a slots-query round with empty text starts. Every other slow tool chain (validate_lead, create_livecall_booking, the Phase B chain's `_PHASEB_SLOW` steps have their own partial treatment) leaves dead air. The general rule, in ElevenLabs' shape: **any round whose tools are still in flight after `soft_filler_ms` speaks one canned line, once per turn, never model-generated** (deterministic — no extra LLM call, no latency added to the hot path).

The existing iter40 L3 immediate slots filler **stays** — for the known-slow webhook, speaking at 0ms is strictly better than waiting 3s. FIX 8 is the general net under everything else.

### 9.2 Code — `graph/builder.py` (inside the tool_calls branch, after the L3 `emit_filler` block, around builder.py:2517)

```python
                # FIX 8 (PORT 8): general one-shot soft filler (ElevenLabs
                # soft_timeout semantics: once per TURN, deterministic text,
                # never LLM-generated). Fires only when nothing was spoken
                # this round AND this turn — speech playing = no filler.
                soft_filler_fired = False

                async def _soft_filler_watch():
                    nonlocal soft_filler_fired
                    await asyncio.sleep(
                        runtime.settings.soft_filler_ms / 1000.0)
                    if soft_filler_fired or state.get("turn_spoke") \
                            or content.strip():
                        return
                    soft_filler_fired = True
                    try:
                        writer({"tts_token":
                                runtime.settings.soft_filler_text + " "})
                        log.info("speech_filter: soft filler spoken "
                                 "(tools in flight %dms+)",
                                 runtime.settings.soft_filler_ms)
                    except Exception:
                        pass

                soft_watch = None
                if getattr(runtime.settings, "soft_filler_ms", 0) > 0 \
                        and writer is not None \
                        and not emit_filler:          # L3 already spoke
                    soft_watch = asyncio.get_event_loop().create_task(
                        _soft_filler_watch())
                try:
                    for tc in tool_calls:
                        ... (existing execute loop unchanged) ...
                finally:
                    if soft_watch is not None:
                        soft_watch.cancel()
                if soft_filler_fired:
                    fillers = list(state.get("fillers_said") or []) + \
                        [runtime.settings.soft_filler_text]
                    updates["fillers_said"] = fillers
                    updates["turn_spoke"] = True    # round 2 separator logic
```

Once-per-turn semantics come from the `turn_spoke` guard: round 1's filler sets it (via `updates`), so a second slow round of the same turn stays silent — matching ElevenLabs' "fires once per turn" exactly. The `fillers_said` append additionally caps repeats across the call for the same text, reusing the existing anti-repeat state key.

### 9.3 Tests (`tests/test_iter81_soft_filler.py`)

1. `test_filler_after_threshold` — tool sleeping 5s, `soft_filler_ms=1000` (test-scaled); assert the filler token was written once.
2. `test_no_filler_when_speech_playing` — round with `content="Let me check"`; assert no filler.
3. `test_once_per_turn` — two consecutive slow rounds; assert exactly one filler.
4. `test_l3_takes_precedence` — slots round; assert the L3 line, not the general one.
5. `test_knob_zero_off` — `soft_filler_ms=0`; no watchdog task ever created.
6. `test_watchdog_cancelled_on_fast_tools` — tools returning in 100ms; assert the task was cancelled (no late filler).

### 9.4 Rollout

Independent — first wave. Branch `engine/iter81-soft-filler`. Ear test: a call that triggers the booking chain (the slowest path); expect "One moment while I check that for you." once, ~3s into the wait, then the real answer. Rollback: `SOFT_FILLER_MS=0`.

---

## 10. Sequencing, Batteries and Rollout (HITL order)

### 10.1 Ship order and why

Three waves. Within a wave, order is free; across waves it is not.

| Wave | Fix | Branch | Knob to flip | Why this position |
|---|---|---|---|---|
| 1 | **FIX 7** STT liveness | `engine/iter80-stt-liveness` | `STT_RX_ZOMBIE_MS=15000` | Independent guardrail; kills the mute class while everything else is still being built. No interactions with any other fix. |
| 1 | **FIX 5** post-interrupt backoff | `engine/iter78-backoff` | `POST_INTERRUPT_BACKOFF_MS=1000` | Independent guardrail; one timestamp. Makes every later fix safer to A/B (no collide-re-speak noise in the batteries). |
| 1 | **FIX 8** soft filler | `engine/iter81-soft-filler` | `SOFT_FILLER_MS=3000` | Independent; must precede FIX 2 so the ladder never polices tool-wait dead air. |
| 2 | **FIX 1** eager hold | `engine/iter74-eager-hold` | `EAGER_HOLD_AUDIO_UNTIL_CONFIRM=true` | The architectural core. Ships the gate `hold/release/discard` primitive that FIX 4 reuses. Biggest single kill: F5 + talk-over F1. |
| 2 | **FIX 4** ack filter + false-interrupt resume | `engine/iter77-ack-filter` | `BARGE_ACK_FILTER=true` | Reuses FIX 1's primitive; its `resolve(true)` path is the trigger point for FIX 5's stamp and FIX 6's capture. |
| 3 | **FIX 6** said-truth commit | `engine/iter79-said-truth` | `HISTORY_SAID_TRUTH_ONLY=true` | Wants FIX 4's true-barge decision (capture fires exactly once per real interruption). Then the deferred dedupe-deletion battery. |
| 3 | **FIX 3** confidence band | `engine/iter76-conf-band` | `STT_LOG_RAW_EOT=true` → then bands | Gated on the T0 payload observation (does Flux send confidence?). The observation can run any time from wave 1 — it is read-only. |
| 3 | **FIX 2** reminder ladder | `engine/iter75-pause-ladder` | `PAUSE_LADDER_MODE=reminder` | Last: it is the only fix that adds a new speaker behavior on silent calls, and it must sit on top of FIX 8 (tool-wait air) + FIX 3 (fragment air) to inherit a clean jurisdiction: **true caller absence only**. |

### 10.2 Lane procedure (per fix, the repo's proven loop)

1. Branch from clean main tip; worktree; `pytest tests/ -k <fix>` green; full suite expectation unchanged (476 passed + 1 known env failure, per iter70 plan baseline).
2. Deploy to the `:8024` lane (`systemctl --user restart diallux-8024.service`); logs via `journalctl --user -u diallux-8024.service`.
3. **Battery first, ears second**: `happy3` (3/3 BOOK required), the fake-caller barge script, and the fix's own scripted scenario from its test section.
4. Langfuse verification: traces `micbridge-<sid>`; the fix's spans (`eager turn audio released`, `barge:false_interrupt`, `stt_conf:*`, `pause_ladder:*`, `stt:zombie_reconnect`, `said_truth:*`, `speech_filter: soft filler`) present with sane values.
5. Owner ear A/B: knob on vs knob off, same script, same time of day. **The ear is the gate.**
6. HITL stop: report in chat, owner decides merge (Telegram ASK at closeout; LAW 0).

### 10.3 Red flags that abort a step (roll back to knob-off, investigate before re-testing)

- Any battery call that fails to BOOK where `happy3` passed on main.
- `resumed_count` climbing without corresponding caller speech (FIX 1 hold leaking audio early).
- Agent audio overlapping caller speech in the ear test (FIX 5 backoff not stamping — check the `resolve(true)` path).
- Nudges firing during tool waits (FIX 2 armed while FIX 8 off/disabled — wrong order; re-sequence).
- Latency regression: `tts_first_byte` p90 growing by more than the FIX 1 math predicts (> ~1.2s over the pre-fix eager p90).

---

## 11. Acceptance Criteria + What We Deliberately Did NOT Port

### 11.1 Per-fix pass signals (against existing observability)

| Fix | Passes when | Existing metric/span that proves it |
|---|---|---|
| FIX 1 | 10-call battery: zero mid-speech audio collisions; `resumed_count` unchanged; TTFT p50 regression ≤ 600ms | turn reports (`head_start_ms`, `eager_final_match`), `tts_first_byte`, `eot_silence_wait` |
| FIX 2 | Silent-caller calls: nudge @ ~10s, ~20s, close @ ~30s; normal calls: zero audible difference; no history/state writes from nudges | `pause_ladder:nudge/close` spans; `aget_state` diff in test 4 |
| FIX 3 | Fragment-class EOTs produce the canned line, never a model re-ask; clean EOTs unchanged | `stt_conf:drop/reask` spans; `speech_filter` INFO lines |
| FIX 4 | "Yeah" mid-question: agent resumes its sentence (audio dip ≤ ~500ms), no new turn, no history entry; real barge: today's behavior | `barge:false_interrupt` span vs `BARGEINS` counter; turn reports |
| FIX 5 | Post-barge replies start after the caller finishes (≥ 1s gap), never overlapping | `barge-in` + next-turn `tts_first_byte` delta in turn reports |
| FIX 6 | Barge-heavy script: stacked "okay, so you said…" recounts gone; deletion battery (all dedupe off) shows zero repeated sentences across 10 calls | `said_truth:capture/commit` spans; `speech_filter` window-drop lines going to zero |
| FIX 7 | Killed pooled socket: reconnect fires ≤ 15s, call continues audibly; normal calls: zero spurious reconnects | `stt:zombie_reconnect` span; `prewarm: refused stale` log line |
| FIX 8 | Booking-chain call: one filler ~3s into the wait, once per turn, then the real answer | `speech_filter: soft filler` INFO line; `fillers_said` in state |

### 11.2 What we deliberately did NOT port (from the research §4 — so nobody re-litigates)

1. **Semantic/audio turn-detection models** — Retell's proprietary turn-taking model, LiveKit's TurnDetector, OpenAI's `semantic_vad`. We already run Deepgram Flux EOT, the same class of signal, and it is already the input to the eager path. FIX 1 fixes the *release rule*, not the detector.
2. **Vapi's `waitFunction` sigmoid** — a latency-shaping knob for a problem we do not have (we are not over-eager on EOT; we were over-eager on *audio release*).
3. **Any TTS-side text filtering** — no platform ships it. The entire dedupe/sanitizer family is *our* invention; FIX 6 replaces its job at the correct layer (belief == audio), and the family becomes a deletion candidate after the battery. `tts_sanitize_tokens` (code-artifact suppression) is the one piece with no platform counterpart but real observed value — keep it; it is content hygiene, not turn-taking.

### 11.3 The one-sentence summary

Every fix above moves the engine toward the same doctrine the shipping platforms converged on: **the microphone stream is sacred (never re-anchored, never filtered mid-speech), the caller owns the floor (acks never yield it, answers are never spoken over), speech is released only on confirmation, and the model believes exactly what the caller heard.**

---

## 12. Companion Deliverable — the Plain-English README

This document is the engineering artifact. A second, non-technical companion — `README-whats-going-on.md` (plus PDF render) — explains the same material in layman terms: what the six problems sound like on a phone call, what the big platforms do about them, what these eight fixes change, and how the safety switches work. It is generated alongside this document and intended for anyone who needs to understand the situation without reading code.
