#!/usr/bin/env python3
"""Maria-v2 conversational LLM caller over the REAL mic WS path.

Standalone driver: stdlib + websockets + openai + requests only, zero
engine imports (runs against ANY engine branch/box). Streams Cartesia
synthesized caller speech into ws://<engine>/mic/ws in 20ms linear16 16k
frames, HEARS the agent through a second Deepgram flux WS fed the agent
PCM the engine sends back, and PACES like a human: waits for the agent
to finish every turn, waits 5-15s between turns (sends NO frames during
the wait).

Scenarios: happy (full arc incl. forced-repeat + question-dump),
barge-in-only, dump-only, watchdog (zero-energy frames 12s).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import time
import urllib.parse

import requests
import websockets
from openai import AsyncOpenAI

FRAME_BYTES = 640
FRAME_SECS = 0.02
SAMPLE_RATE = 16000
DEFAULT_LOG = "/tmp/opencode/voice_server_8020.log"

PERSONA_PROMPT = (
    "You are Maria, the office manager at Bright Smile Dental, calling an AI "
    "voice agent that handles calls for a lighting/electrical business. "
    "You want a walkthrough of their service and to get a demo call booked. "
    "You are a real human caller on a phone call.\n"
    "PACING RULES (hard): you speak in SHORT bursts of one or two sentences "
    "maximum, like a person on a phone. You WAIT for the other side to finish "
    "speaking before you reply, and you take a natural pause (5-15 seconds) "
    "before speaking again. You never say more than two sentences in one turn "
    "unless told otherwise. You never invent outcomes: only react to what the "
    "agent actually said. You never mention being an AI or a test."
)

DUMP_QUESTIONS = (
    "Okay so I have a few questions real quick: how fast can someone come out? "
    "Do you handle the permits? What does it usually cost? And do you work "
    "weekends?"
)
REPEAT_PHRASE = "Sorry, I didn't catch that - could you say that part again?"
GOODBYE_PHRASE = "Perfect, that's everything I needed. Thanks so much, have a good one!"

PRICING_HINTS = ("$", "price", "cost", "per month", "quote", "pricing")
QUESTION_HINTS = ("question", "ask", "anything else")
BOOKED_HINTS = ("booked", "confirmed", "scheduled", "put you down", "see you on")


PACING_PROMPT = (
    "PACING RULES (hard): you speak in SHORT bursts of one or two sentences "
    "maximum, like a person on a phone. You WAIT for the other side to finish "
    "speaking before you reply, and you take a natural pause (2-4 seconds) "
    "before speaking again. HARD LIMIT: every reply is AT MOST 30 CHARACTERS "
    "— count them; if longer, cut it down. You never invent outcomes: only "
    "react to what the agent actually said. You never mention being an AI."
)
PERSONA_DIRECTIVE = (
    "Reply in one short burst (1-2 short sentences), pursuing the goal stated "
    "in your persona. Never invent outcomes. Never mention being an AI or a test."
)
PERSONA_GOODBYE_DIRECTIVE = (
    "Wrap up and end the call naturally, one short sentence."
)


def load_persona(name: str) -> str:
    """iter78b: load a caller persona system prompt from tests/llm2llm/personas.py."""
    import importlib.util
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    spec = importlib.util.spec_from_file_location(
        "mic_personas", os.path.join(root, "tests", "llm2llm", "personas.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    matches = [p for p in mod.PERSONAS if name.lower() in p["name"].lower()]
    if not matches:
        gks = ", ".join(p["name"].split(")")[0][1:] for p in mod.PERSONAS
                        if p["name"].startswith("(GK)"))
        raise SystemExit(f"no persona matches {name!r}; available GKs: {gks}")
    return matches[0]["system"] + "\n\n" + PACING_PROMPT


def load_env(path: str):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def chunk_frames(pcm: bytes, size: int = FRAME_BYTES) -> list[bytes]:
    return [pcm[i:i + size] for i in range(0, len(pcm), size)]


def zero_pcm(seconds: float) -> bytes:
    return b"\x00" * (int(seconds * SAMPLE_RATE) * 2)


def agent_idle(last_audio_ts: float | None, now: float, idle_s: float) -> bool:
    return last_audio_ts is not None and (now - last_audio_ts) >= idle_s


class CartesiaCallerTTS:
    URL = "https://api.cartesia.ai/tts/bytes"

    def __init__(self, api_key: str, model_id: str, voice_id: str):
        self.api_key = api_key
        self.model_id = model_id
        self.voice_id = voice_id
        self.output_format = {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": SAMPLE_RATE,
        }

    def synth(self, text: str) -> bytes:
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                r = requests.post(
                    self.URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Cartesia-Version": "2025-04-16",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model_id": self.model_id,
                        "transcript": text,
                        "voice": self.voice_id,
                        "language": "en",
                        "output_format": self.output_format,
                    },
                    timeout=30,
                )
                if r.status_code == 200:
                    return r.content
                last_exc = RuntimeError(f"cartesia {r.status_code}: {r.text[:200]}")
            except Exception as exc:
                last_exc = exc
            time.sleep(0.5)
        raise RuntimeError(f"cartesia synth failed after retries: {last_exc}")


class AgentEar:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws = None
        self.turns: list[str] = []
        self.updates: list[str] = []
        self.speaking = False
        self.last_feed_ts: float | None = None

    def _flush_turn(self):
        """iter78b: flux EndOfTurn is too slow for TTS streaming - finalize the
        open turn driver-side on an audio-idle gap (same threshold as turn-end
        wait). Duplicates the flux EndOfTurn append."""
        if self.updates and (not self.turns or self.updates[-1] != self.turns[-1]):
            self.turns.append(self.updates[-1])

    def _url(self) -> str:
        params = urllib.parse.urlencode({
            "model": "flux-general-en",
            "encoding": "linear16",
            "sample_rate": str(SAMPLE_RATE),
        })
        return "wss://api.deepgram.com/v2/listen?" + params

    async def start(self):
        headers = {"Authorization": f"Token {self.api_key}"}
        self.ws = await websockets.connect(
            self._url(), additional_headers=headers, max_size=None, open_timeout=10
        )
        asyncio.create_task(self._recv_loop())
        asyncio.create_task(self._keepalive())

    async def _keepalive(self):
        """iter78b: the caller's 5-15s human gaps starve the flux WS (idle
        timeout = silent death mid-call) - drip 100ms of silence every 3s."""
        silence = zero_pcm(0.1)
        while self.ws is not None:
            try:
                await self.ws.send(silence)
            except Exception:
                self.ws = None
                return
            await asyncio.sleep(3)

    async def _recv_loop(self):
        try:
            async for raw in self.ws:
                if isinstance(raw, bytes):
                    continue
                msg = json.loads(raw)
                if msg.get("type") != "TurnInfo":
                    continue
                event = msg.get("event")
                transcript = (msg.get("transcript") or "").strip()
                if event == "StartOfTurn":
                    self.speaking = True
                elif event == "EndOfTurn" and transcript:
                    self.speaking = False
                    self.turns.append(transcript)
                elif event == "Update" and transcript:
                    self.updates.append(transcript)
        except Exception as exc:
            print(f"[ear] deepgram stream error: {exc}", flush=True)
        finally:
            self.ws = None

    async def feed(self, pcm: bytes):
        if self.ws is None:
            try:
                await self.start()
                print("[ear] deepgram reconnected", flush=True)
            except Exception:
                return
        now = time.monotonic()
        if self.last_feed_ts is not None and now - self.last_feed_ts > 1.2:
            self._flush_turn()
        self.last_feed_ts = now
        if self.ws is not None:
            try:
                await self.ws.send(pcm)
            except Exception:
                self.ws = None


class MicDriver:
    def __init__(self, ws_url: str, ear: AgentEar):
        self.ws_url = ws_url
        self.ear = ear
        self.ws = None
        self.agent_audio_bytes = 0
        self.agent_first_audio_ts: float | None = None
        self.last_agent_audio_ts: float | None = None
        self.events: list[dict] = []
        self.open = False

    def _stamp(self, kind: str, **detail):
        self.events.append({"t": time.time(), "mono": time.monotonic(), "kind": kind, **detail})

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=None, open_timeout=10)
        self.open = True
        await self.ws.send(json.dumps({"event": "start", "customParameters": {}}))
        self._stamp("start_sent")
        asyncio.create_task(self._recv_loop())

    async def _recv_loop(self):
        try:
            async for raw in self.ws:
                if isinstance(raw, (bytes, bytearray)):
                    now = time.monotonic()
                    b = bytes(raw)
                    self.agent_audio_bytes += len(b)
                    if self.agent_first_audio_ts is None:
                        self.agent_first_audio_ts = now
                        self._stamp("agent_first_audio")
                    self.last_agent_audio_ts = now
                    await self.ear.feed(b)
                else:
                    self._stamp("server_text", text=str(raw)[:200])
        except websockets.ConnectionClosed:
            pass
        except Exception as exc:
            self._stamp("recv_error", error=str(exc))
        finally:
            self.open = False
            self._stamp("ws_closed")

    async def stream_pcm(self, pcm: bytes):
        self._stamp("caller_stream_start", bytes=len(pcm))
        for frame in chunk_frames(pcm):
            await self.ws.send(frame)
            await asyncio.sleep(FRAME_SECS)
        self._stamp("caller_stream_end")

    async def close(self):
        if self.ws is None:
            return
        try:
            await self.ws.send(json.dumps({"event": "stop"}))
        except Exception:
            pass
        try:
            await self.ws.close()
        except Exception:
            pass


class CallerBrain:
    def __init__(self, api_key: str, model: str, prompt: str | None = None,
                 base_url: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.prompt = prompt or PERSONA_PROMPT

    async def reply(self, conversation: list[dict], directive: str) -> str:
        user = json.dumps({"conversation": conversation, "directive": directive})
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": user},
            ],
            max_completion_tokens=40,
        )
        return (resp.choices[0].message.content or "").strip()


class RunState:
    def __init__(self, args):
        self.args = args
        self.t0 = time.monotonic()
        self.caller_turns: list[dict] = []
        self.repeat_used = False
        self.dump_used = False
        self.goodbye_done = False
        self.stop_reason = "max_turns"

    def elapsed(self) -> float:
        return time.monotonic() - self.t0


def conversation_pairs(agent_turns: list[str], caller_turns: list[dict]) -> list[dict]:
    out = []
    for t in agent_turns:
        out.append({"role": "agent", "text": t})
    for c in caller_turns:
        out.append({"role": "caller", "text": c["text"]})
    return out


async def wait_agent_turn_end(driver: MicDriver, state: RunState):
    idle = state.args.agent_idle_s
    while driver.open:
        now = time.monotonic()
        if state.elapsed() > state.args.max_run_s:
            state.stop_reason = "max_run_s"
            return False
        last = driver.last_agent_audio_ts
        if agent_idle(last, now, idle) and driver.agent_first_audio_ts is not None:
            return True
        if last is None and (now - state.t0) > state.args.max_turn_wait:
            state.stop_reason = "agent_never_spoke"
            return False
        await asyncio.sleep(0.1)
    return False


async def human_gap(state: RunState, min_gap: float, max_gap: float) -> float:
    gap = random.uniform(min_gap, max_gap)
    await asyncio.sleep(gap)
    return gap


async def speak(driver: MicDriver, tts: CartesiaCallerTTS, state: RunState,
                ear: AgentEar, text: str, gap: float | None):
    entry = {"text": text, "gap_before_s": gap, "agent_turns_heard": len(ear.turns)}
    t_gen = time.monotonic()
    pcm = await asyncio.to_thread(tts.synth, text)
    entry["tts_ms"] = int((time.monotonic() - t_gen) * 1000)
    entry["audio_bytes"] = len(pcm)
    entry["dur_s"] = round(len(pcm) / (SAMPLE_RATE * 2), 2)
    await driver.stream_pcm(pcm)
    state.caller_turns.append(entry)


async def run_happy(driver, tts, brain, state, ear):
    args = state.args
    await asyncio.sleep(2.0)
    ok = await wait_agent_turn_end(driver, state)
    if not ok:
        return
    agent_turns = []
    persona_mode = bool(getattr(args, "persona", ""))
    while driver.open and state.stop_reason == "max_turns":
        if state.elapsed() > args.max_run_s:
            state.stop_reason = "max_run_s"
            break
        last_agent = ear.turns[-1] if ear.turns else ""
        agent_turns = list(ear.turns)
        text = None
        directive = PERSONA_DIRECTIVE if persona_mode \
            else "reply naturally as Maria in one short burst"
        if not persona_mode:
            text = REPEAT_PHRASE if (state.repeat_used is False and any(
                h in last_agent for h in PRICING_HINTS) and len(ear.turns) >= 2
            ) else None
            if text:
                state.repeat_used = True
                directive = "say exactly the given line"
            elif state.dump_used is False and any(h in last_agent for h in QUESTION_HINTS):
                text = DUMP_QUESTIONS
                state.dump_used = True
                directive = "ask exactly these 4 questions in one breath"
        elif any(h in " ".join(agent_turns).lower() for h in BOOKED_HINTS) \
                and not state.goodbye_done and len(state.caller_turns) >= 2:
            state.goodbye_done = True
            state.stop_reason = "booked_goodbye"
            text = None
            directive = PERSONA_GOODBYE_DIRECTIVE
        if text is None and not persona_mode:
            if any(h in " ".join(agent_turns).lower() for h in BOOKED_HINTS) \
                    and not state.goodbye_done and len(state.caller_turns) >= 2:
                text = GOODBYE_PHRASE
                state.goodbye_done = True
                state.stop_reason = "booked_goodbye"
                directive = "say goodbye exactly like this"
            elif len(state.caller_turns) >= args.max_caller_turns:
                text = GOODBYE_PHRASE
                state.goodbye_done = True
                state.stop_reason = "turn_cap_goodbye"
                directive = "say goodbye exactly like this"
        if persona_mode and len(state.caller_turns) >= args.max_caller_turns \
                and not state.goodbye_done:
            state.goodbye_done = True
            state.stop_reason = "turn_cap_goodbye"
            text = None
            directive = PERSONA_GOODBYE_DIRECTIVE
        gap = await human_gap(state, args.min_gap, args.max_gap)
        if text is None:
            try:
                text = await asyncio.wait_for(
                    brain.reply(conversation_pairs(agent_turns, state.caller_turns),
                                directive), timeout=30)
            except Exception as exc:
                state.stop_reason = f"brain_error: {exc}"
                break
        await speak(driver, tts, state, ear, text, gap)
        if state.goodbye_done:
            await wait_agent_turn_end(driver, state)
            break
        ok = await wait_agent_turn_end(driver, state)
        if not ok:
            break


async def run_barge_in_only(driver, tts, state, ear):
    while driver.open:
        now = time.monotonic()
        if driver.last_agent_audio_ts and not agent_idle(
                driver.last_agent_audio_ts, now, 0.3) and driver.agent_audio_bytes > 0:
            break
        if state.elapsed() > state.args.max_turn_wait:
            state.stop_reason = "no_agent_speech"
            return
        await asyncio.sleep(0.05)
    await asyncio.sleep(0.5)
    if driver.open:
        await speak(driver, tts, state, ear, "Oh hold on, one second- sorry go ahead.", None)
        state.stop_reason = "barged_in"


async def run_dump_only(driver, tts, brain, state, ear):
    ok = await wait_agent_turn_end(driver, state)
    if not ok:
        return
    gap = await human_gap(state, state.args.min_gap, state.args.max_gap)
    await speak(driver, tts, state, ear, DUMP_QUESTIONS, gap)
    state.dump_used = True
    state.stop_reason = "dumped"
    await wait_agent_turn_end(driver, state)


async def run_watchdog(driver, tts, state, ear):
    ok = await wait_agent_turn_end(driver, state)
    if not ok:
        return
    await asyncio.sleep(2.0)
    await driver.stream_pcm(zero_pcm(12.0))
    state.stop_reason = "watchdog_silence_sent"
    await wait_agent_turn_end(driver, state)


async def main_async(args):
    load_env(args.env)
    api_key = os.environ["CARTESIA_API_KEY"]
    model_id = os.environ["CARTESIA_MODEL_ID"]
    voice_id = args.voice_id or os.environ["CARTESIA_VOICE_ID"]
    dg_key = os.environ["DEEPGRAM_API_KEY"]
    oa_key = os.environ["OPENAI_API_KEY"]
    model = args.caller_model or os.environ.get("OPENAI_MODEL", "gpt-5.4")
    args.persona_prompt = load_persona(args.persona) if args.persona else None

    journal_start = 0
    if os.path.exists(args.journal_log):
        journal_start = os.path.getsize(args.journal_log)

    tts = CartesiaCallerTTS(api_key, model_id, voice_id)
    ear = AgentEar(dg_key)
    brain = CallerBrain(oa_key, model, prompt=args.persona_prompt)
    driver = MicDriver(args.ws_url, ear)
    state = RunState(args)

    await ear.start()
    await driver.connect()
    try:
        if args.scenario == "happy":
            await run_happy(driver, tts, brain, state, ear)
        elif args.scenario == "barge-in-only":
            await run_barge_in_only(driver, tts, state, ear)
        elif args.scenario == "dump-only":
            await run_dump_only(driver, tts, brain, state, ear)
        elif args.scenario == "watchdog":
            await run_watchdog(driver, tts, state, ear)
    finally:
        await asyncio.sleep(1.0)
        await driver.close()
        try:
            if ear.ws is not None:
                await ear.ws.close()
        except Exception:
            pass

    journal = []
    if os.path.exists(args.journal_log):
        with open(args.journal_log, "rb") as f:
            f.seek(journal_start)
            journal = f.read().decode(errors="replace").splitlines()[-400:]

    evidence = {
        "scenario": args.scenario,
        "persona": args.persona or None,
        "ws_url": args.ws_url.split("k=")[0] + "k=<redacted>",
        "caller_model": model,
        "started_wall": time.time(),
        "events": driver.events,
        "agent_turns": ear.turns,
        "agent_updates_tail": ear.updates[-5:],
        "caller_turns": state.caller_turns,
        "agent_audio_bytes": driver.agent_audio_bytes,
        "stop_reason": state.stop_reason,
        "journal_lines": journal,
        "elapsed_s": round(state.elapsed(), 2),
    }
    with open(args.out, "w") as f:
        json.dump(evidence, f, indent=2, default=str)
    print(json.dumps({
        "out": args.out, "scenario": args.scenario,
        "agent_turns": len(ear.turns), "caller_turns": len(state.caller_turns),
        "stop_reason": state.stop_reason,
    }))
    return evidence


def build_parser():
    p = argparse.ArgumentParser(description="iter76 LLM mic caller")
    p.add_argument("--ws-url", required=True)
    p.add_argument("--scenario", choices=["happy", "barge-in-only", "dump-only", "watchdog"],
                   default="happy")
    p.add_argument("--min-gap", type=float, default=5.0)
    p.add_argument("--max-gap", type=float, default=15.0)
    p.add_argument("--agent-idle-s", type=float, default=1.5)
    p.add_argument("--max-turn-wait", type=float, default=30.0)
    p.add_argument("--caller-model", default=None)
    p.add_argument("--persona", default="",
                   help="registry persona name (e.g. Sam, Priya) - persona mode")
    p.add_argument("--voice-id", default="",
                   help="override CARTESIA_VOICE_ID for the CALLER voice only"),
    p.add_argument("--max-run-s", type=float, default=600.0)
    p.add_argument("--max-caller-turns", type=int, default=12)
    p.add_argument("--journal-log", default=DEFAULT_LOG)
    p.add_argument("--env", default=os.path.join(os.path.dirname(__file__), "..", ".env"))
    p.add_argument("--out", required=True)
    return p


def main():
    args = build_parser().parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
