# iter80 session report — EL flip + mic phone fix + fake-caller smoke

**Date:** 2026-09-26 · **Box:** OREGON `5.78.83.174` (root, key `id_ed25519_hetznor`)
**Plan worked:** `plans/plan_v5_iter80_el_flip_mic_phone_fix.md` (big repo `clean-dialux-sdr`)
**Branch:** `engine/iter80-el-flip-mic-phone-fix` — base `031bb73` (iter65 model-defaults), tip `88381a2`
**This repo:** `diallux_sdr_almost_there` — iter66-era engine snapshot (`0ce798f`) that produced the
Sep 24 BOOKED mic-bridge call. This session's artifacts are added on top in ONE commit: the fake
caller (`engine/scripts/llm_mic_caller.py`), this report, and the two voice-SDR turn-taking MD
research docs.

## Commits on the branch (big repo)

| commit | what |
|---|---|
| `471e50c` | T2: shared LLM pool `keepalive_expiry=600` (port of iter75 `858543c`; kills turn-1 fresh-TLS cost) |
| `3829d16` | T4: browser `?rate=` knob (verbatim 2-line port of iter73 `8c5f72f`) + mic page sends optional `callback_number` customParameter on WS start (browser lane has no caller-ID; chat-parity seed) |
| `420e8a6` | fake caller `engine/scripts/llm_mic_caller.py` ported verbatim from iter79 ref (`bf21983`+`d8260c2`) — Cartesia caller voice, Deepgram flux ear, scenarios happy/barge-in/dump/watchdog, zero diallux imports |
| `5815a81` | T3-fix: fork the LIVE-PROVEN iter66 multi-stream-input EL adapter (lineage of the booked :8024 call, `1a8e04a`) over the stale pre-iter66 stream-input adapter present at base |
| `88381a2` | T3-fix2: sync EL plumbing from prod-proven tree `df23d37` (prewarm provider-gated EL branch + keepalive drain, tts_factory transport passthrough, config knobs incl. `elevenlabs_inactivity_timeout=180`) — byte-verified |

## Key audit findings

- Base `031bb73` is NOT in main's lineage (pre-rebase iter65): it predates the iter66 EL cutover.
  Its EL adapter was the OLD `stream-input` one — its `{"text": ""}` "flush" is end-of-stream and
  makes EL close the socket (smoke #1 proved the 1000 (OK) close + 1008 voice_settings policy
  violation). The live-proven code is the iter66 `multi-stream-input` rewrite (native contexts,
  `close_context`, space-keepalive, deprecated `optimize_streaming_latency` removed).
- Engine brain files (builder/session/gates/delivery) are byte-identical base ↔ prod: the Intake
  lite-ack round shape observed in smokes (~1.8k tok turn-1, ~3k after) EXACTLY matches the
  original BOOKED call's ledger signature (`mic-iter64-live`, trace `39eca78d…`) — the lite rounds
  are original behavior, not a regression.
- T5 (mic phone capture) needed ZERO code: the iter62 `need_digits` instruction +
  `record_reach_details`/`set_callback_number` path is fully present at base. Chat's advantage was
  only the seeded `callback_number`; for browser calls the page now supplies it (or the spoken
  number is captured via the existing ask→confirm→`set_callback_number` flow).

## Fake-caller smoke campaign (7 runs, ports :8026→:8029 on the worktree lane)

| run | agent model | outcome |
|---|---|---|
| #1 | luna | EL stale adapter died at first speak (stale `stream-input` flush) → agent silent |
| #2 | luna | after adapter fork: EL voiced every turn (TTFB 172–363 ms); Intake lite-ack loop — luna never fires extract tools |
| #3 | luna | fixed driver pacing: 0 barge-ins, 13/13 turns heard both ways, still stuck in Intake (luna = talker, not tool-driver) |
| #4–#6 | gpt-5.4 | driver-pacing pathologies (rambling/stall) + infra retries — discarded |
| #7 | gpt-5.4 | clean run: turn 1–3 voiced EL; ONE barge-in at turn 2 (2.5–4 s caller gaps) → Deepgram flux never EOT'd turn 3 → engine silent 65 s; driver 13 turns → cap goodbye |

**Conclusions:**
- EL voice works end-to-end on the browser lane (pcm_16000, Sarah pin `uG1JFy6xppqckhHCs2KG`).
- `gpt-5.6-luna` cannot drive this engine's tool loop: at `reasoning_effort=none` (the only mode
  OpenAI allows for function tools on chat/completions for luna) it answers speech-only and never
  fires extract tools → funnel never leaves Intake. Do not use luna for engine smokes.
- Barge-in is the killer for the fake caller: caller speech starting while Linda is still speaking
  wedges Deepgram flux (back-to-back `StartOfTurn`, no `EOT`). Patient pacing (≥8 s gaps,
  `--agent-idle-s 4`) produced 0 barge-ins; fast pacing (2.5–4 s) reliably triggers it.
  Recommended driver settings for future runs: gaps 4–6 s, caller reply cap ~60 chars.
- No bookings were created in any run; Cal.com untouched.

## Evidence (OREGON)

- `/tmp/opencode/iter80_smoke_*.json` — full per-run transcripts (agent + caller turns)
- `/tmp/opencode/voice_server_*.log` — lane journals (round usage, turn reports, barge-ins)
- big repo tree: `research/surgeon/iter80-el-flip-mic-phone-fix-src/` — the two voice-SDR MDs

## Status / next

- Branch unmerged; push/merge = owner only (LAW 0). Prod `:8026` restored to main checkout
  (`diallux.service`, gpt-5.4) and verified after the smoke lane moved to test ports.
- The EL adapter fork (`5815a81`) is the load-bearing fix for any future EL testing.
- For end-to-end fake-call testing of the funnel: gpt-5.4 (full) + patient pacing; luna is
  unsuitable as the engine model; driver barge-in avoidance is the open driver-side item.
