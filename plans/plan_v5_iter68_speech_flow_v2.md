# plan_v5_iter68_speech_flow_v2 — speech-filter observability + dedupe calibration + deterministic transition/round flow

## Meta
- Date: 2026-09-23
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: SEE every speech-stream cut live (observability), then fix the four reproduced defects — scripted re-asks muted by the iter59 semantic dedupe, multi-round turn leaks, flat transition acks, fast-flush mid-sentence cuts — plus re-ask escalation per the owner flow rule.
- Status: PLAN ONLY (v2, rewritten per plan SOP with 2026-09-23 forensics; awaits owner GO)
- Branch: `engine/iter68-speech-flow`, cut from main tip `99061cb` (see Deploy Rules)
- Evidence SDK: `/home/julio/projects/clean_diallux_SDR/engine/scripts/speech_replay.py` (written 2026-09-23, UNCOMMITTED — commit on the branch in T1)

## Compaction Context
Dialux SDR v5 engine (LangGraph voice pipeline) in `/home/julio/projects/clean_diallux_SDR` (single git repo; engine worktrees under `/tmp/opencode/wt-iterNN`). Main tip `99061cb` contains iter66 EL cutover (`84fd1ce`, EL merged dormant), iter65 (`fc45536`, sanitizer + boot prewarm + gpt-5.4), iter67 Twilio pins. Production lanes `:8021` (pid 3834955, OLD pre-merge process) and `:8022` (pid 884638) are NEVER touched; the fresh test lane is systemd `diallux-8024.service` (mic via `flores.diallux-ai.site/voice24/mic`), log = `journalctl --user -u diallux-8024.service`.

VOICE LAW (root `AGENTS.md`, commit `6724be3`, owner ear-confirmed twice): `TTS_PROVIDER=cartesia`, `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` (the dated pin — owner: "pin = the good voice, rolling alias = garbage"), voice Linda `829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30`, `CARTESIA_SPEED=1.12`. The iter66 env rebuild had dropped `CARTESIA_MODEL_ID`; restored today in `/home/julio/projects/clean_diallux_SDR/engine/.env`, `:8024` restarted and confirmed (`cartesia connected (model=sonic-3.6-2026-08-27)` in the journal). Env today: `TTS_PROVIDER=cartesia`, `TTS_GATE_FAST_FIRST_FLUSH=false`, `OPENAI_MODEL=gpt-5.4`.

Forensics session 2026-09-23 (the basis of this plan):
- Root cause of "dumb agent": iter59 cross-turn semantic question dedupe (`tts_dedupe_cos_threshold=0.90`) MUTES re-asks the prompts deliberately script. Proven by `/home/julio/projects/clean_diallux_SDR/engine/scripts/speech_replay.py` over 4 calls: call `ccacb090cc54` (00:32, 40 gens) — 8 cuts, ALL scripted lines: `<And your last name?>` ×2 (cos 0.9138), "What's your last name?" (0.9576), `<What's the best number to reach you?>` ×4 (0.9055), scripted number-ask variant (cos 1.0000 — the prompt's own fallback). Call `14d42eafa601` (04:53, post-pin) — 2 cuts (cos 0.9903, improvised Intake question, not scripted). Call `cc750d181c6f` — 1 cut (cos 0.9705) + the fast-flush fragment "I'm doing well,". Call `9b79911c8e46` (EL) — 0 cuts. Sanitizer = 0 drops everywhere; exact window = 0 drops everywhere.
- Multi-round leak (call `ccacb090cc54`, turn 32): ONE caller turn → FOUR spoken LLM rounds back-to-back (round usage `turn=32` ×4 @ 00:39:27/29/30/33; outputs 90/66/66/292 tokens; e2e 5.9s; `resumed_count: 7`). Cause: the extract→calculate→transition tool chain — every round SPOKE text (each ended with a question) and the loop re-fired after each tool result. Round 4 (292 tok) has NO Langfuse generation = observability gap.
- Scripted spans live in `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/*.md` as `<...>` spans (mirrored into `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json` `state_prompt` fields minus `#[refer …]` spans).
- Fast-flush (`tts_gate_fast_first_flush`) already flipped OFF via env on :8024; this plan makes the CODE default False (single-knob revert proof is in the plan history).
- Owner confirmed: `sonic-3.6-2026-08-27` pin is NOT deprecated and IS the good voice; no A/B needed. Latency of the scripted flex-pass ≈ 0 (reuses the `_embed_stem` query embed the hot path already pays per question at builder.py:2343; boot-time batch pre-embed of ~10-20 spans/state is ~50-150ms one-off, off the call path; exact tier is a dict lookup).
- Suite count baseline: 463 passed (iter65 merge), tests via `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q`.
- Langfuse: self-hosted `http://localhost:3001`, traces `micbridge-<sid>`; ledger `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; import via `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (accepts `micbridge-*` since `537e53c`).
- Push from the agent shell FAILS (no GitHub creds) — commits land locally on main; owner pushes from their terminal.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| TTS = Cartesia, `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` pinned in env | Owner ear ×2: pin = good voice, rolling alias = garbage. VOICE LAW in root AGENTS.md |
| `tts_gate_fast_first_flush` code default → False | Mid-sentence cut reproduced ("I'm doing well," ‖ " thanks for asking."); env already off on :8024 |
| Scripted-question full pass = 2-tier: (1) exact normalized match, (2) cos ≥ 0.85 vs pre-embedded scripted spans of the CURRENT state | Owner: allowlist needs "room to breathe" — LLM varies phrasing; no NEW embedding infra (reuses iter59 embedder); ~0 hot-path latency |
| Cross-turn semantic dedupe is per-state gated; OFF in Intake | Owner: Intake has per-turn exact dedupe + filters; cross-turn muting there destroys flow |
| One spoken reply per turn: all-mechanical tool rounds are SILENT; speech lands once at chain end; `?`-yield backstop for text-only stacks | Turn-32 leak: 4 spoken rounds in one breath; owner approved ("ok perfect lets add that") |
| Transition beat = deterministic ENGINE guarantee + LLM content: if the transition round ends without a spoken `?`, the graph fires exactly ONE continuation round in the destination state (scripted-first-question-if-fits, else one contextual question) | Owner rejected blind "ack + first scripted question" splicing (off-logic risk); continuation round reads full history so it keeps flow |
| Flow rule: 2-strike re-ask escalation (strike-1 rephrase, strike-2 skip/alternative), never verbatim re-ask ×N | Owner 2026-09-23; contact_details re-asked ×6 in `ccacb090cc54` |
| One variable per iteration; branch per LAW 0; merge = owner only | AGENTS.md law |
| Sanitizer stays ON (0 drops measured — not the problem) | Evidence: 0 sanitizer drops across all 4 replayed calls |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner GO on this plan (v2) | Telegram ASK at session start |
| Live mic calls for calibration (owner speaks) | lane :8024 `flores.diallux-ai.site/voice24/mic` |
| Git push of main commits `6724be3` + `99061cb` + this plan | Owner terminal (agent shell has no creds) |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12.3; pytest 9.1.1; langchain_openai 1.6.0; openai 3.8.0; fastembed local arctic-embed-m at `/home/julio/fastembed/models`)
- LLM: `gpt-5.4` via `OPENAI_MODEL` in `/home/julio/projects/clean_diallux_SDR/engine/.env` (MODEL LAW — env wins over code defaults)
- RAG: pgvector `postgresql://…@localhost:5434/diallux` (DATABASE_URL in engine `.env`), `rag_fire_mode=hybrid`, embedder ok (health `http://127.0.0.1:8024/health`)
- Mic lane: systemd `diallux-8024.service` — restart `systemctl --user restart diallux-8024.service`; logs `journalctl --user -u diallux-8024.service`
- Langfuse: self-hosted `http://localhost:3001`; keys in engine `.env` (`LANGFUSE_*`); SDK `/home/julio/projects/clean_diallux_SDR/engine/scripts/lf.py`
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (NO sqlite3 CLI — use `.venv/bin/python -c "import sqlite3; …"`)
- Suite baseline: 463 passed
- NEVER touch: `:8021` (pid 3834955), `:8022` (pid 884638), `:8000-8003` services, `engine/diallux/media/prewarm.py`, `engine/diallux/media/elevenlabs_tts.py`, `engine/diallux/media/tts_factory.py`, branches `engine/iter66-*`/`iter64-ela`, live agent IDs, Cal.com event 3801235 (REAL — cancel test bookings)

## Architecture (one block)
```
LLM token stream ──► builder flush sites ──> [T2 sanitizer] ──> [exact window dedupe] ──> [semantic stem dedupe (0.90)]
        (mid-stream ~:2320 + stream-end ~:2400)        (drop { } [ ] => ": function_calls)
──> [sentence gate + fast-first-flush] ──> writer tts_token ──> CallSession._speak_chunk ──> CartesiaTTS (sonic-3.6-2026-08-27)
                                     ▲
iter68 changes:  T1 logs EVERY drop stage (speech_filter event)
                 T3 scripted full-pass BEFORE the semantic drop (exact dict + flex cos≥0.85 vs current state's spans); per-state gate (OFF in Intake)
                 T4 round loop: all-mechanical rounds silent; one spoken reply per turn; '?'-yield backstop
                 T2 transition ack without '?' → exactly ONE continuation round in the destination state
```

## File Map
| File (absolute path) | What changes | New/Edit |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` | T1: log every sanitizer/exact/semantic/fast-flush drop at INFO with sentence + stage + state+turn (`speech_filter` event); T3: scripted-span extraction (`<...>` per state) + pre-embed at graph init + full-pass check BEFORE the semantic drop + per-state semantic gate (OFF in Intake); T4: all-mechanical round speech suppression + `?`-yield backstop in the round loop; T2: continuation-round rule on transition acks | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py` | Knobs: `speech_filter_observability: bool = True`; `tts_gate_fast_first_flush: bool = False` (was True); `tts_gate_fast_first_flush_min_chars: int = 12` (was hardcoded); `scripted_pass_cos_threshold: float = 0.85`; `tts_dedupe_semantic_exempt_states: tuple = ("Intake",)`; `silence_reask: bool = True`; `silence_reask_ms: int = 2000` | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py` | Filter regex += `speech_filter` so pulls show drops | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/scripts/speech_replay.py` | Commit on branch (evidence SDK, already written); add `--knobs` passthrough for calibration A/B | Edit + commit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py` | T3: on EOT-timeout silence (~2s no caller speech → `deepgram_eot_timeout_ms` path) speak a REPHRASED re-ask of the last question, gated `silence_reask`, tracer span `silence_reask` | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/contact_details.md` | 2-strike rule: strike-1 rephrase + offer alternative ("or I can call you at the number on file"); strike-2 skip to next required field; never verbatim ×3 | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/Intake.md`, `Discovery.md`, `Closer.md` | Turn-end question rule + transition directive: ack then EITHER destination's first scripted question (if it fits) OR one contextual question; spell company names letter-by-letter on first capture | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json` | state_prompts regenerated from the edited .md files (minus `#[refer …]` spans, byte-parity convention) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter68_speech_filters.py` | NEW pins: observability log fired per drop class; fast-flush default False; min_chars knob; scripted full-pass (exact + flex) beats the semantic cut; Intake exempt; sanitizer byte-identical when observability off | New |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter68_reask_escalation.py` | NEW pin: FakeLLM round replay — last-name/number 2-strike wording, no verbatim third ask; silence re-ask fires once at ~2s | New |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter68_round_yield.py` | NEW pin: 4-round tool chain (extract→calculate→transition) speaks ONCE; text-only `?`-stack yields; transition ack without `?` fires exactly one continuation round | New |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-65 (speech filter observability) + PT-66 (re-ask escalation + 2s silence rule) + PT-67 (one-reply-per-turn + scripted full-pass) rows | Edit (docs, main) |

## Deploy Rules
- Branch + worktree (exact):
  ```
  git -C /home/julio/projects/clean_diallux_SDR branch engine/iter68-speech-flow main
  git -C /home/julio/projects/clean_diallux_SDR worktree add /tmp/opencode/wt-iter68 engine/iter68-speech-flow
  ```
- Compile-check after every file touched: `cd /tmp/opencode/wt-iter68/engine && .venv/bin/python -m py_compile diallux/graph/builder.py diallux/config.py diallux/media/session.py scripts/speech_replay.py`
- Suite: `cd /tmp/opencode/wt-iter68/engine && .venv/bin/python -m pytest tests -q` → expect 463 + new pins, 0 failed
- Lane deploy for live ear tests: copy edited files into `/home/julio/projects/clean_diallux_SDR/engine/` (the main checkout runs the service) + `systemctl --user restart diallux-8024.service`; NEVER touch `:8021`/`:8022`
- Post-change re-verify: `/tmp/opencode/wt-iter68/engine/.venv/bin/python /tmp/opencode/wt-iter68/engine/scripts/speech_replay.py micbridge-ccacb090cc54 --fast-flush` must show the 8 previously-muted scripted cuts now PASS (with flex tier on) — offline proof before any live call
- NEVER touch: `engine/diallux/media/prewarm.py`, `elevenlabs_tts.py`, `tts_factory.py`; `:8021`/`:8022`; Cal.com event 3801235

## Tasks (in order)
### T1 — Speech-filter observability (SEE every cut live) + evidence SDK commit
Goal: every sanitizer drop / exact-window drop / semantic drop / fast-flush cut logs `speech_filter stage=<…> sent="<sentence>" state=<s> turn=<n>` at INFO; commit `scripts/speech_replay.py` on the branch; fix the round-4 Langfuse gen gap (every round logs a generation, including suppressed/transition rounds).
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py`, `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py`, `/home/julio/projects/clean_diallux_SDR/engine/scripts/speech_replay.py`
Commands: compile-check (see Deploy Rules); suite.
Verification: pins green; scripted FakeLLM round with an artifact + a dup logs both drop lines in caplog; `speech_replay.py` committed and runs (see replay commands below).

### T2 — Deterministic transition beat + flow rule + fast-flush OFF in code
Goal: (a) `tts_gate_fast_first_flush` code default → False + `…_min_chars` knob (12); (b) DETERMINISTIC transition guarantee: the round that fires `transition_to_X` and ends without a spoken `?` is followed by exactly ONE continuation round in the destination state — engine-enforced, no prompt hoping; (c) continuation directive in destination prompts: "ask the destination script's first scripted question IF it fits the live conversation; otherwise compose ONE contextual question that keeps the flow" (owner rule — no blind splicing); (d) every turn ends with a question; (e) company NAME captured spelled-out with letter confirmation on first capture (Everlast/Everest flip seen in `ccacb090cc54` fragments "Got it — Everlast," → "Got it — Everest,").
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/Intake.md`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/Discovery.md`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/Closer.md`, `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json`
Commands: compile-check; suite; llm.json regeneration parity check (`grep -c 'refer' agent/llm.json` before/after).
Verification: pins; replay of `ccacb090cc54` turn-32 shape in a FakeLLM test shows ack + one question, never flat.

### T3 — Dedupe calibration + re-ask escalation (owner flow rule)
Goal: (a) scripted-question full pass — exact tier: `_norm_sentence(spoken)` in the state's normalized `<...>` question keys → pass, no dedupe check; flex tier: the spoken question's EXISTING `_embed_stem` vec (builder.py:2343 already computes it) cos ≥ `scripted_pass_cos_threshold` (0.85) against any pre-embedded scripted span of the CURRENT state → pass; pre-embed happens once at graph init (~10-20 spans/state, boot-time, off hot path); (b) cross-turn semantic dedupe per-state gate — OFF for Intake (exact window + sanitizer still active everywhere); (c) contact_details 2-strike escalation (strike-1 rephrase + alternative; strike-2 skip; never verbatim ×N); (d) silence re-ask: EOT-timeout ~2s with no caller speech → graph speaks a REPHRASED re-ask of its last question (gated `silence_reask`, `silence_reask_ms=2000`, tracer span `silence_reask`).
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/contact_details.md`, `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py`
Commands: compile-check; suite; calibration: `cd /tmp/opencode/wt-iter68/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/speech_replay.py micbridge-ccacb090cc54 --fast-flush` → the 8 previously-muted scripted re-asks must now show SPOKEN (flex tier), while true loops (cos ≥ 0.95 non-scripted) still cut.
Verification: pins; offline replay proof; live mic call shows ≤2 asks per missing field.

### T4 — One spoken reply per turn (turn-32 fix)
Goal: a round whose tool_calls are ALL mechanical (`_MECHANICAL_RE` set already in builder.py — extract_*/calculate_*/record_*/flag setters) gets its spoken text SUPPRESSED (history keeps the round; TTS gets nothing); the speech lands once at the chain end (transition ack rounds still speak, per T2); backstop: in a text-only stack, the first round that spoke a sentence ending in `?` ends the turn (no further rounds without new caller input). Deterministic, no prompt dependence.
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py` (knob `mechanical_round_silent: bool = True`)
Commands: compile-check; suite.
Verification: FakeLLM pin replays the exact turn-32 sequence (extract_leak_inputs → calculate_monthly_leak → extract_closer_details+transition_to_Offer) and asserts ONE spoken reply; `?`-yield pin for text-only stacks.

### T5 — Mic turn-1 TTFT autopsy + KB-coverage gate (read-only first)
Goal: (a) decompose the 1,558 ms turn-1 TTFT on `cc750d181c6f` — suspect `stt_eot_to_llm_first 1,259 ms` (Deepgram flux handshake on the adopted socket / eager adoption path / first-round prefill without greeting warms); read-only via `journalctl --user -u diallux-8024.service` + Langfuse spans `turn:1`/`warm:*` + `scripts/mic_events.py`; fix only after diagnosis. (b) KB-coverage gate on the live lane: from ledger/Langfuse rag spans — chunks-per-turn, degraded%, KBs hit per call; if starving (iter22 lesson: 79/102 queries → 0 chunks), recommend pinning the industry vertical (iter52 metadata lane, no embed) — separate decision, owner-gated.
Files: read-only (journalctl, Langfuse, ledger); any fix = NEW branch after owner sees the diagnosis.
Verification: next mic call logs per-hop turn-1 spans; KB-coverage numbers in the report.

### T6 — Battery + report + ASK (HITL stop)
Commands (full):
```
cd /tmp/opencode/wt-iter68/engine && set -a && . ./.env && set +a && date +%H:%M && \
.venv/bin/python tests/llm2llm/harness.py --personas happy3 --rag --rag-fire-sim --langfuse --max-turns 48; date +%H:%M
```
Import: `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py import --window "<HH:MM-HH:MM>" --run chat-iter68-happy --branch engine/iter68-speech-flow --commit <sha> --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`
Verification: happy3 3/3 + Rourke booked; transcript scan shows no muted-scripted-question pattern (replay the battery traces too); no 4-round leaks; report → `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter68-speech-flow/01_report.md`; `scripts/hitl_ping.py` the ASK — **STOP at HITL; merge = owner only.**

## Validation Plan (end-to-end)
1. Suite 463 + new pins, 0 failed.
2. Offline: `speech_replay.py` on `micbridge-ccacb090cc54` + `micbridge-14d42eafa601` shows scripted re-asks SPOKEN under the new logic (flex tier) and true loops still cut.
3. Live mic call on :8024: `speech_filter` journal lines match what the owner heard; ≤2 asks per missing field; transition acks never flat; one spoken reply per turn.
4. Battery gates green; report + ASK; merge = owner.
5. Cancel ALL test bookings after the battery (Cal.com event 3801235 is REAL).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| EL delivery tuning (speed/style per state, jitter) | Owner prefers Cartesia pin; EL stays merged but dormant |
| :8021/:8022 restart on new main | Owner-gated, separate call |
| iter67 Twilio lane | Blocked on owner Twilio creds (separate session) |
| Retell repo validator | Done (c790bdf); no further work |
| Real-time prompt-side "don't repeat" tuning beyond 2-strike | T3's deterministic pass/gate covers it; revisit only if battery shows loops |
