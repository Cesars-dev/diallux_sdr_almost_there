# plan_v5_iter68_speech_flow_calibration — sanitizer/dedupe/gate observability + owner-flow re-ask ladder

## Meta
- Date: 2026-09-23
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: instrument + calibrate the three speech-stream filters (T2 sanitizer, iter59 semantic dedupe, iter46 fast-flush gate) on the live mic lane, then implement the owner's flow rule (always answer, re-ask after ~2s silence, 2-strike escalation instead of verbatim re-ask loops).
- Status: PLAN ONLY (not started — awaits owner GO)
- Branch: `engine/iter68-speech-flow` cut from main tip (see T0)
- REPRODUCED ROOT CAUSE 2026-09-23 (owner ear + replay): `tts_gate_fast_first_flush` cuts the FIRST utterance of every turn at the first "," past 12 chars (or a hard 28-char fallback) — mid-sentence, e.g. call `cc750d181c6f` gen3: spoken "I'm doing well," || " thanks for asking." (one sentence, two TTS segments, prosody reset). Owner verdict: does more harm than help with the iter65 warm pool. RECOMMENDATION: `TTS_GATE_FAST_FIRST_FLUSH=false` (single-knob revert); env already set on :8024 for ear test.
- Evidence base: mic calls `ccacb090cc54` (00:32–00:42), `9b79911c8e46` (01:01), `cc750d181c6f` (01:07) on lane :8024; report `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter65-model-defaults/05_mic_call_report.md`

## Compaction Context
Dialux SDR v5 engine (LangGraph voice pipeline, repo `/home/julio/projects/clean_diallux_SDR`, single git repo; engine worktrees under `/tmp/opencode/wt-iterNN`). Current main tip: `537e53c` (contains iter66 EL cutover `84fd1ce`, iter65 model-defaults `fc45536` merged `50a453f`, T7 provider flip `f236697`, live_sql micbridge import fix `537e53c`). Owner ear verdict 2026-09-23: **Cartesia preferred over ElevenLabs Sarah on live mic** — `.env` `TTS_PROVIDER=cartesia` on lane :8024 (systemd unit `diallux-8024.service`, EnvironmentFile loads `/home/julio/projects/clean_diallux_SDR/engine/.env`); EL stays merged but dormant behind the knob.
Session shipped: iter65 (T1 boot prewarm, T2 speech sanitizer `_sanitize_spoken()` in `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` gated by `tts_sanitize_tokens: bool = True`, T3 dv carryover DAILY daily×5, T4 mic spans `eot_silence_wait`/`tts_first_byte`, model default gpt-5.4, `rag_fire_mode` default hybrid, wall cap now 900s @ commit "iter66-T7: call wall-clock cap 600s -> 900s"), full SOP audits (harness + mic) persisted to ledger `research/surgeon/iter48-rag-truth/ledger.db`.
Key live facts: lane `:8024` = systemd `diallux-8024.service` (fresh test lane, Caddy route `flores.diallux-ai.site/voice24/*`); production lanes `:8021` (pid 3834955) and `:8022` (pid 884638) still on OLD processes, untouched; validator `:8003` on Retell main `c790bdf` with daily-carryover math. iter65 knobs on main: `llm_boot_prewarm=True` (shared httpx pool), `tts_sanitize_tokens=True`, `rag_fire_mode="hybrid"`, `openai_model="gpt-5.4"`. Mic-call data plane: uvicorn log via `journalctl --user -u diallux-8024.service` (NOT `/tmp/opencode/voice_server_8021.log`), per-turn `turn N final report` json, Langfuse traces `micbridge-<sid>` (now importable — `scripts/live_sql.py` accepts `micbridge-*` as of `537e53c`).
Evidence from the owner complaint: sanitizer scan of the last mic call's 12 gens = **0 drops, 0 strips** (ran `_sanitize_spoken` over every sentence). Suspects for the perceived trimming: (a) `tts_gate_fast_first_flush` (first "," ≥12 chars → clause-level flush, choppy), (b) iter59 semantic question dedupe (`tts_dedupe_cos_threshold=0.90`) eating rephrased questions, (c) sanitizer `.strip()` + `head_tokens=[sent]` rewrite. Owner flow complaint from call `ccacb090cc54`: contact_details re-asked "what's the best number to reach you?" verbatim ×6 and last-name ×3 — needs 2-strike escalation + ~2s silence re-ask per owner rule.

## Session closeout — commits carried into this plan (owner: log them into SQL next session)
Owner directive 2026-09-23: merges to main happen ONLY on an explicit owner "merge now" — never adjacent to another instruction; noted as LAW 0 addendum (v2.2). Commits to inventory in T0 (all on main, pushed):
- `84fd1ce` merge iter66 (EL adapter rewrite, factory, prewarm gate, 12 pins; tag engine/iter66)
- `50a453f` merge: iter65 @ `fc45536` (T1 boot prewarm, T2 sanitizer, T3 dv DAILY, T4 mic spans, gpt-5.4, hybrid; rebased over iter66; suite 463; tag engine/iter65)
- `f236697` iter66-T7: tts_provider default → elevenlabs + EL env block (owner directive)
- `87e173f` iter66-T7: wall cap 600s → 900s (owner directive)
- `537e53c` ops: live_sql import accepts micbridge-* (SOP write path was dead)
- `bfea1fd`/`d83a187`/`9078884` plan: iter68 (PLAN ONLY, no code)
- env ops (gitignored): TTS_PROVIDER=cartesia (owner ear A/B reversal), TTS_GATE_FAST_FIRST_FLUSH=false (mid-sentence cut, reproduced), VOICE_TEST_TOKEN copied to main .env
Owner ear verdicts (facts, do not revisit): Cartesia > EL Sarah on live mic; EL "much better" than the accidental Cartesia default call; fast-flush mid-sentence cuts confirmed ("I'm doing well,‖ thanks for asking…").
Open owner questions carried: mic turn-1 TTFT 1,558 ms root cause (T4 — "not the browser; something else"); which service drives the mic turn-1 chain (Deepgram flux handshake / graph warm adopt / first-round prefill).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| TTS provider = cartesia on all lanes (env knob) | Owner ear A/B on :8024: Cartesia > EL Sarah (EL lacks the iter21-59 delivery-tuning stack) |
| EL stays merged, dormant | Reversible one-line; voice config pinned (Sarah `uG1JFy6xppqckhHCs2KG`, turbo_v2_5, speed 1.06, style 1.0, stability 0.5) |
| max_call_seconds = 900 | Owner directive (was 600), commit on main |
| Sanitizer stays ON but gets drop-telemetry first, loosening decided on evidence | Owner wants "D-Dop" drops kept but trimming gone — need to SEE what's gated before loosening |
| Flow rule (owner): always answer the question asked; if caller silence ~2s → ask again (rephrase, never verbatim); never re-ask a stored value | Owner 2026-09-23 |
| One variable per iteration; branch per LAW 0 | AGENTS.md law |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner GO on this plan | Telegram ASK |
| Live mic calls for calibration (owner speaks) | lane :8024 `flores.diallux-ai.site/voice24/mic` |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12.3; pytest 9.1.1; langchain_openai 1.6.0; openai 3.8.0)
- Branch base: main tip at cut time (`git -C /home/julio/projects/clean_diallux_SDR rev-parse main`)
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (import/sops via `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py`)
- Mic lane: systemd `diallux-8024.service` (restart: `systemctl --user restart diallux-8024.service`), env file `/home/julio/projects/clean_diallux_SDR/engine/.env` (has `VOICE_TEST_TOKEN`, `CALL_PREWARM=true`, `TTS_PROVIDER=cartesia`)
- Langfuse: self-hosted, keys in engine `.env` (`LANGFUSE_*`), traces `micbridge-<sid>`
- NEVER touch: `:8021` (pid 3834955), `:8022` (pid 884638), `:8000-8003` services, branches `engine/iter66-*`/`iter64-ela`

## Architecture (one block)
```
LLM token stream ──► builder flush sites ──> [T2 sanitizer] ──> [exact window dedupe] ──> [semantic stem dedupe (0.90)]
        (mid-stream ~:2320 + stream-end ~:2400)        (drop { } [ ] => ": function_calls)
──> [sentence gate + fast-first-flush (first "," ≥12 chars)] ──> writer tts_token ──> CallSession._speak_chunk ──> CartesiaTTS
Owner gap: NOTHING logs what was dropped/trimmed at any stage. Plan adds the observability layer + calibration knobs, then owner-ear A/B.
```

## File Map
| File (absolute path) | What changes | New/Edit |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` | T1: log every sanitizer drop + dedupe drop + fast-flush cut at INFO with the sentence text + state+turn (`speech_filter` log event); NO behavior change | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py` | T2 knobs: `speech_filter_observability: bool = True`; `tts_gate_fast_first_flush_min_chars: int = 12` (was hardcoded); `tts_dedupe_cos_threshold` stays 0.90 (evidence first) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py` | T1: filter regex += `speech_filter` so pulls show drops | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter68_speech_filters.py` | NEW pins: observability logs fired on each drop class; min_chars knob honored; sanitizer behavior byte-identical when observability off | New |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/contact_details.md` | T3: 2-strike re-ask rule (strike 1 rephrase + offer alternative "or I can call you at the number on file"; strike 2 skip to next required field, never verbatim re-ask) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json` | T3: contact_details state_prompt = edited .md minus `#[refer …]` spans (regenerate, byte-parity convention) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter68_reask_escalation.py` | NEW pin: FakeLLM round replay — last-name/number 2-strike wording, no verbatim third ask | New |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py` | T4 (owner silence rule): on EOT-timeout silence (~2s with no caller speech → `deepgram_eot_timeout_ms` path), the graph speaks a re-ask of its own last question (rephrased) — gated `silence_reask: bool = True`, `silence_reask_ms: int = 2000`; tracer span `silence_reask` | Edit |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-65 (speech filter observability) + PT-66 (re-ask escalation + 2s silence rule) rows | Edit (main, docs) |

## Deploy Rules
- Worktree: `git -C /home/julio/projects/clean_diallux_SDR worktree add /tmp/opencode/wt-iter68 engine/iter68-speech-flow` (branch cut from main tip first: `git branch engine/iter68-speech-flow main`)
- Compile-check after every task: `cd /tmp/opencode/wt-iter65 2>/dev/null || cd /tmp/opencode/wt-iter68; cd engine && .venv/bin/python -m py_compile <files>`
- Suite: `cd /tmp/opencode/wt-iter68/engine && .venv/bin/python -m pytest tests -p no:warnings` → expect 463 + new pins, 0 fail
- Lane deploy for live ear tests: copy edited files into `/home/julio/projects/clean_diallux_SDR/engine/` (main checkout runs the service) + `systemctl --user restart diallux-8024.service`; NEVER touch `:8021`/`:8022`
- NEVER touch: `engine/diallux/media/prewarm.py`, `elevenlabs_tts.py`, `tts_factory.py` (iter66's files); `:8021`/`:8022`; Cal.com event 3801235 (REAL — cancel test bookings)

## REPRODUCED 2026-09-23 (post-plan forensics, speech_replay.py SDK)
- **SDK:** `engine/scripts/speech_replay.py` (uncommitted; commit = owner say-so) — replays a call's Langfuse gens through the REAL filter chain (sanitizer → exact window → iter59 semantic dedupe, live arctic-embed-m) and prints SPOKEN vs CUT per sentence. `--all` verbose, `--fast-flush` simulates the flush era.
- **MUTED = SCRIPTED (call ccacb090cc54, 8 cuts):** every semantic-dedupe cut was a SCRIPTED re-ask: `<And your last name?>` ×2 (cos 0.9138), "What's your last name?" (0.9576), `<What's the best number to reach you?>` ×4 (0.9055), scripted variant number-ask (cos 1.0000). The prompt orders the re-ask; the engine mutes it → caller hears ack + dead air → model history thinks it asked. Intake cuts are improvised questions (not scripted): "What had you calling in today?" muted ×2 on 14d42eafa601 (cos 0.9903).
- **MULTI-ROUND LEAK (call ccacb090cc54, turn 32):** ONE caller turn → **FOUR LLM rounds spoken back-to-back** (round usage turn=32 ×4 @ 00:39:27/29/30/33, output 90/66/66/292 tokens, e2e_turn 5.9s, resumed_count 7). Each round ends in a question; the graph never yields to the caller between rounds — owner heard 4 phrases mashed in one breath ("agent speaking 2 turns in one turn"). Root suspects: state_in_delta + rag_fire_mode=hybrid re-firing rounds (delta_tokens 4360 on the re-fired rounds).
- **Owner directives (add to T2/T3):** (a) scripted-QUESTION full pass — extract every `<...>` question span per state, pre-embed at graph init, spoken question matching a scripted span (exact or cos≥thr) is EXEMPT from the semantic window; (b) cross-turn semantic dedupe OFF in Intake (per-state gate; per-turn exact dedupe + sanitizer stay everywhere); (c) ONE question per turn — the round loop must yield to the caller after any round that spoke a question (no back-to-back rounds in one turn).

## Tasks (in order)
### T1 — Speech-filter observability (SEE before loosening)
Goal: every sanitizer drop / dedupe drop / fast-flush cut logs the exact sentence + reason.
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py`
Commands: compile-check both files; suite.
Verification: pins green; a scripted FakeLLM round with an artifact sentence logs `speech_filter drop …` line.
### T2 — Speech-flow rule (owner instruction #1) + fast-flush OFF pin + spelling capture
Goal: (a) `tts_gate_fast_first_flush` code default → False (mid-sentence cut reproduced — "I'm doing well,‖ thanks…"); (b) EVERY turn ends with a question — contextual from the last agent/caller sentence first, state's first scripted question as fallback (prompt rule in each state prompt + llm.json state_prompts regenerated); (c) transition acks carry ack + next question in one breath (T2b evidence: "…isn't delivering." → dead air); (d) company NAME captured spelled-out with letter confirmation on first capture (Everlast/Everest flip fix).
Files: builder/config knobs, prompts/{Intake,Discovery,Closer}.md, agent/llm.json, test pin.
Verification: pins; live mic — no verbatim re-ask, no dead-air ack, no mid-word cuts.
Goal: `tts_gate_fast_first_flush_min_chars` knob (12 default) + observability flag; owner does 2 mic calls (A: defaults, B: `tts_gate_fast_first_flush=False`) and picks.
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py`
Verification: knobs effective on :8024 (grep journal for `speech_filter` lines during owner call).
### T2b — Flat transition beat (REPRODUCED 2026-09-23)
Goal: kill the dead-air transition beat — on transition_to_X ack rounds the agent speaks ONLY the ack and waits for caller speech (call cc750d181c6f: "Makes sense — you need a change because your current service isn't delivering." [flat end, transition fired, 11s dead air]; "Got it — plumbing." [same]). Fix: the ack round renders the destination state's NEXT question in the same turn (prompt rule: transition ack = ack + first question of the new state, one sentence each), backed by the T4 silence re-ask as the safety net.
Files: prompts (Intake.md + Discovery.md transition wording), llm.json state_prompts, pin.
Verification: live mic — after each state transition the next question arrives in the SAME spoken turn (no caller prompt needed).

### T3 — Re-ask escalation (owner flow rule)
Goal: contact_details never verbatim-re-asks; 2-strike wording; silence >2s on EOT-timeout → rephrased re-ask of the pending question.
Files: prompts + llm.json + session.py + test pin.
Verification: pins; live mic call shows ≤2 asks per missing field.
### T4 — Mic turn-1 TTFT autopsy (owner Q: "why is our first turn so long — not the browser")
Goal: decompose the 1,558 ms turn-1 on mic call cc750d181c6f — stt_eot_to_llm_first 1,259 ms is the suspect (Deepgram flux handshake/EOT on the adopted socket? eager adoption path? first-round prefill without greeting warm — mic sessions never fire the harness's greeting warms).
Files: read-only analysis first (`journalctl --user -u diallux-8024.service`, Langfuse trace spans `turn:1`, `warm:*`, mic_events). Fix only after diagnosis (candidates: fire lite+full Intake greeting warm in CallSession.start like GraphAgent does).
Verification: next mic call turn-1 TTFT logged with per-hop spans; owner decides the fix target.

### T5 — Battery + report + ASK
Commands (full):
```
cd /tmp/opencode/wt-iter68/engine && set -a && . ./.env && set +a && date +%H:%M && \
.venv/bin/python tests/llm2llm/harness.py --personas happy3 --rag --rag-fire-sim --langfuse --max-turns 48; date +%H:%M
```
Import: `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run chat-iter68-happy --branch engine/iter68-speech-flow --commit <sha> --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`
Verification: happy3 3/3 + Rourke booked; sanitizer scan 0 artifacts; no verbatim re-ask loops in transcripts; report → `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter68-speech-flow/01_report.md`; `hitl_ping.py` the ASK.

## Validation Plan (end-to-end)
1. Suite 463 + new pins, 0 failed.
2. Owner mic call on :8024 shows `speech_filter` log lines exactly matching what the owner heard as drops (quantified, not guessed).
3. Owner picks A/B (fast-flush on/off) by ear.
4. Live call: missing number → strike-1 rephrase → strike-2 skip — NEVER 6 verbatim re-asks.
5. Battery gates green; report + ASK; merge = owner.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| EL delivery tuning (speed/style per state, jitter) | Owner prefers Cartesia; EL stays dormant — separate ride only if owner re-opens |
| :8021/:8022 restart on new main | Owner-gated, separate call |
| iter67 Twilio lane | Blocked on owner Twilio creds (separate session) |
| Retell repo validator | Done (c790bdf); no further work |
