# plan_v5_iter70_speech_fixes_merged — merged plan: T2 pause re-prompt + T3 transition beat + T4' same-turn jaccard dedupe + T5 observability (verbatim instructions from the iter68 surgeon plans, re-scoped small on clean main)

## Meta
- Date: 2026-09-23
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: execute the 4 approved SMALL speech fixes on clean main, merging the VERBATIM task instructions from the iter68 surgeon plans (v1/v2/v3 + PT-68..73) with this session's owner decisions (jaccard same-turn dedupe, no embedder, HITL stop at EVERY task).
- Status: IN PROGRESS (T0 owner GO received in-session "yes that one, lets fix this sht"; T1 preflight DONE — branch + worktree live). **HITL LAW: every T = STOP, report, owner decide-act before the next T.**
- Branch: `engine/iter70-speech-fixes` (cut from main tip `2d9385d`; code base = `8e06fe9` state + .env knobs). Worktree: `/tmp/opencode/wt-iter70` (venv symlinked, `.env` copied, verified 2026-09-23).

## Compaction Context
Dialux SDR v5 engine (LangGraph voice pipeline). 2026-09-23 owner ear-tested iter68 ("speech flow") + iter68-lite on lane :8024 → verdict **total failure, both branches PARKED** (overengineering: semantic cos dedupe, scripted-pass registries, 2-strike ladders, chain-link buffering — muted/truncated REAL speech). Lane rolled back and LIVE on clean main @ `8e06fe9` + env knobs (verified 11:43): `TTS_PROVIDER=cartesia`, `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27` (THE pin, never remove), `TTS_GATE_FAST_FIRST_FLUSH=false`, `TTS_DEDUPE_SEMANTIC=false`. Same-turn dup-sentence guard (`tts_dedupe_sentences=True`) + sanitizer (`tts_sanitize_tokens=True`) STAY ON.

**Dedupe forensics (this session, verified from git):**
- `ca3112b` iter41 T1 (2026-09-09): exact-sentence dedupe born — byte-identical (case-insensitive, whitespace-collapsed) sentence never spoken twice in one turn's token stream (`tts_dedupe_sentences=True`).
- `65d7f3b` iter41 T1b: **extended to ROUNDS** — dedupe seed carried across rounds of the SAME turn (Danny-t10 shape: gpt-5.x repeated its closing sentence in round 2).
- `f5c0912` iter42 (2026-09-10): widened to 6-sentence sliding window (`tts_dedupe_window=6`), still exact-match, resets per turn at ingest (builder.py:2732), carries cross-round. **= the ACTIVE deduper today.**
- `6d13803` iter59 T4 (2026-09-20): the EMBEDDER — semantic cos≥0.90 question-stem window (`tts_dedupe_cos_threshold=0.90`) surviving the whole CALL (cross-turn). This muted scripted re-asks live (cos 0.99-1.0 CUT, micbridge-cbdcf4e1ab2f t11-13) → owner env-killed it (`TTS_DEDUPE_SEMANTIC=false`). NO fuzzy matcher is active.
- NO regex "similar phrasing" dedupe ever shipped on main. The owner-remembered "similar phrasing fix" = the PROMPT directives ("vary it, never verbatim twice in one call" — `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/Booking.md:22`, `Discovery.md:61`, `Closing.md:17`, `contact_details.md:18,59`).

**Owner decisions this session (2026-09-23, LAW):**
1. ONE thing at a time — every T is a HITL stop (report → owner decide-act).
2. T4 (merged-turn trim, "keep first + last, trim middle") DROPPED — replaced by **option 2: jaccard-style same-turn similar-sentence dedupe, NO embedder** (owner: "lets pick option 2").
3. Cross-turn repetition is handled PROMPT-side, but the exact prompt wording needs owner approval before it ships.
4. NO removals (worktrees/dirs) without owner say-so — rename/park instead.
5. NO cherry-picks/merges from parked branches `engine/iter68-speech-flow` @ `cc34343` / `engine/iter68-speech-lite` @ `95f7ace` — read-only reference (PT-73 law).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| iter42 exact window STAYS as-is | The only active dedupe; 0 false drops; owner law |
| iter59 semantic dedupe stays env-OFF (`TTS_DEDUPE_SEMANTIC=false`) | Muted scripted re-asks at cos 0.99-1.0; owner "audible redundancy > silencing" |
| New T4' fuzzy dedupe = same-TURN scope ONLY, no embedder | Same-turn reset at ingest (builder.py:2732) makes cross-turn scripted re-asks structurally untouchable — the exact failure mode of iter59 cannot recur |
| T4' mechanism = normalized token-overlap (jaccard), pure python, deterministic | Owner: "not via the embeder, just an engine rule"; hot-path safe (no embed call per sentence) |
| T4' gated by its own knob, default ON, owner A/B by ear | Voice LAW style: env-knob-first, owner ear verdict is the gate |
| T2 pause timer = one-shot ~10s, knob `pause_reask`/`pause_reask_ms=10000` | Owner: "~10s"; renamed from lite's `silence_reask` to avoid parked-branch semantics |
| T3 transition beat re-implemented small (prompt directives + one-trip + `turn_asked`) | PT-70: "the ONE piece of iter68 worth keeping… re-fix, don't grab" |
| T5 observability rides every drop (`speech_filter` INFO lines) | Owner must SEE every cut in the journal (iter68 T1 forensics worked; owner liked it) |
| Prompt-side repetition rules = owner-approved wording BEFORE commit | Owner session instruction 3 |
| HITL stop at every T; ≤60-line diffs; >50 lines needs owner sign-off | PT-73 law + session instruction 2 |
| Battery happy3 3/3 BOOK; merge = owner only (LAW 0) | AGENTS.md iteration loop |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner approval of T4' exact thresholds (min words=4, overlap=0.80, filler list) | HITL stop after T3 |
| Owner approval of the prompt-side repetition wording (T4p) | HITL stop — paste exact directive lines in chat before editing any .md |
| Ear-test verdicts | `https://flores.diallux-ai.site/voice24/mic?k=$VOICE_TEST_TOKEN` (token in `/home/julio/projects/clean_diallux_SDR/engine/.env`) |
| Merge say-so | Telegram ASK at closeout |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv` (3.12.3; pytest 9.1.1; openai 3.8.0; langchain_openai 1.6.0; fastembed local arctic-embed-m at `/home/julio/fastembed/models`)
- Worktree: `/tmp/opencode/wt-iter70` on branch `engine/iter70-speech-fixes` @ `2d9385d` (DONE in session)
- Suite subset verified green except pre-existing flake: `tests/test_iter46_latency_floor.py::test_fast_first_flush_before_stream_end` (perf-timer 1µs monotonicity assertion, flakes on main, unrelated)
- Suite expectation on clean main: 476 passed + 1 known env failure `tests/test_tts_providers.py::test_factory_switches_provider` (owner-confirmed intended)
- Mic lane: systemd `diallux-8024.service` (`WorkingDirectory=/home/julio/projects/clean_diallux_SDR/engine`), logs `journalctl --user -u diallux-8024.service`
- Langfuse: self-hosted `http://localhost:3001`; traces `chat-iter70-*` (harness) + `micbridge-<sid>` (mic lane)
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` — import ONLY via the MAIN-repo SDK `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` (worktree copy is STALE for micbridge-*)
- Report folder: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter70-speech-fixes/01_report.md` (gitignored)

## Architecture (one block)
```
main @ 2d9385d (code state 8e06fe9 + .env knobs) ── branch engine/iter70-speech-fixes (wt /tmp/opencode/wt-iter70)
   ├─ T2: pause re-prompt (one-shot 10s timer in media/session.py + config knobs + post-history directive)
   ├─ T3: transition beat (builder.py one-trip on turn_asked + state.py flag + prompt directives + llm.json mirror)
   ├─ T4': same-turn jaccard dedupe (builder.py iter42 flush site; token-overlap; own knobs; same-turn scope only)
   ├─ T5: speech_filter observability (~10 log.info lines + mic_events regex + speech_replay parity)
   └─ T4p: prompt-side repetition wording (owner-approved lines only)
   → battery happy3 → lane :8024 → owner ear test → ledger gates → ASK → (owner) merge
```

## File Map
| File (absolute path) | What changes | New/Edit |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter70_speech_fixes_merged.md` | THIS plan (docs → main) | New |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-68/69/70 status updates as they land (docs → main) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py` | T2: one-shot pause re-prompt timer | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py` | T2 knobs `pause_reask=True`/`pause_reask_ms=10000`; T4' knobs `tts_dedupe_similar=True`/`tts_dedupe_similar_overlap=0.80`/`tts_dedupe_similar_min_words=4` | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` | T3 one-trip transition beat; T4' jaccard hook at the iter42 flush site; T5 `_log_filter()` INFO lines | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/state.py` | T3: `turn_asked` flag (post-filter "? heard" truth) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/Intake.md` + `Discovery.md` + `Closer.md` + `Offer.md` | T3 transition-ack directives; T4p repetition wording (ONLY owner-approved lines) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json` | T3/T4p prompt mirror, byte-parity lockstep, refer-count 36 preserved | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter70_*.py` | Pins per task (small NEW files) | New |
| `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py` | T5: speech_filter regex (CUT tag) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/scripts/speech_replay.py` | T4'/T5: mirror the jaccard rule + filter lines so replay stays truthful | Edit |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter70-speech-fixes/01_report.md` | battery + ear-test report (gitignored) | New |

## Deploy Rules
- Lane deploy (copy + restart + verify) — per iter70 small plan (verbatim carry):
  ```
  cd /tmp/opencode/wt-iter70 && git checkout-index --prefix=/tmp/opencode/iter70_stage/ -af && \
  cp /tmp/opencode/iter70_stage/engine/diallux/graph/builder.py /home/julio/projects/clean_diallux_SDR/engine/diallux/graph/ && \
  cp /tmp/opencode/iter70_stage/engine/diallux/config.py /tmp/opencode/iter70_stage/engine/diallux/state.py /home/julio/projects/clean_diallux_SDR/engine/diallux/ && \
  cp /tmp/opencode/iter70_stage/engine/diallux/media/session.py /home/julio/projects/clean_diallux_SDR/engine/diallux/media/ && \
  cp /tmp/opencode/iter70_stage/engine/agent/llm.json /home/julio/projects/clean_diallux_SDR/engine/agent/ && \
  cp /tmp/opencode/iter70_stage/engine/diallux/prompts/*.md /home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/ && \
  cp /tmp/opencode/iter70_stage/engine/scripts/mic_events.py /tmp/opencode/iter70_stage/engine/scripts/speech_replay.py /home/julio/projects/clean_diallux_SDR/engine/scripts/ && \
  systemctl --user restart diallux-8024.service && sleep 5 && \
  journalctl --user -u diallux-8024.service -n 10 --no-pager | grep "cartesia connected"
  ```
- Lane RESTORE after every ear test: `git -C /home/julio/projects/clean_diallux_SDR checkout -- engine/diallux engine/agent/llm.json engine/scripts && systemctl --user restart diallux-8024.service`
- Battery (background-safe — `setsid nohup`, NOT bare nohup):
  ```
  cd /tmp/opencode/wt-iter70/engine && set -a && . ./.env && set +a && date +%H:%M && \
  setsid nohup .venv/bin/python tests/llm2llm/harness.py --personas happy3 --rag --langfuse --max-turns 48 > /tmp/opencode/iter70_battery.log 2>&1 < /dev/null &
  ```
- NEVER touch: `:8021`/`:8022` (pids 3834955/884638), `:8000-8003`, `engine/diallux/media/prewarm.py`, `elevenlabs_tts.py`, `tts_factory.py`, live agent IDs, Cal.com event 3801235 bookings (cancel test ones), `CARTESIA_MODEL_ID` in any .env, `TTS_DEDUPE_SENTENCES` (stays default-on), `TTS_DEDUPE_SEMANTIC` (stays env-false)
- Push = owner terminal (agent shell has no creds)

## VERBATIM SOURCE SECTIONS (extracted from the surgeon plans — quoted, not paraphrased)

### SOURCE A — `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter68_speech_flow_v2.md` (committed main `dd557a9`) — points at branch `engine/iter68-speech-flow` (PARKED @ `cc34343`) — T1 observability, VERBATIM:
> ### T1 — Speech-filter observability (SEE every cut live) + evidence SDK commit
> Goal: every sanitizer drop / exact-window drop / semantic drop / fast-flush cut logs `speech_filter stage=<…> sent="<sentence>" state=<s> turn=<n>` at INFO; commit `scripts/speech_replay.py` on the branch; fix the round-4 Langfuse gen gap (every round logs a generation, including suppressed/transition rounds).
> Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py`, `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py`, `/home/julio/projects/clean_diallux_SDR/engine/scripts/speech_replay.py`
> Verification: pins green; scripted FakeLLM round with an artifact + a dup logs both drop lines in caplog; `speech_replay.py` committed and runs.

### SOURCE B — same v2 plan — T2(b)(c) deterministic transition beat, VERBATIM:
> (b) DETERMINISTIC transition guarantee: the round that fires `transition_to_X` and ends without a spoken `?` is followed by exactly ONE continuation round in the destination state — engine-enforced, no prompt hoping;
> (c) continuation directive in destination prompts: "ask the destination script's first scripted question IF it fits the live conversation; otherwise compose ONE contextual question that keeps the flow" (owner rule — no blind splicing);

### SOURCE C — `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter68_speech_flow.md` (v1, committed main `99061cb` era) — T2b flat transition beat, VERBATIM:
> ### T2b — Flat transition beat (REPRODUCED 2026-09-23)
> Goal: kill the dead-air transition beat — on transition_to_X ack rounds the agent speaks ONLY the ack and waits for caller speech (call cc750d181c6f: "Makes sense — you need a change because your current service isn't delivering." [flat end, transition fired, 11s dead air]; "Got it — plumbing." [same]). Fix: the ack round renders the destination state's NEXT question in the same turn (prompt rule: transition ack = ack + first question of the new state, one sentence each), backed by the T4 silence re-ask as the safety net.
> Files: prompts (Intake.md + Discovery.md transition wording), llm.json state_prompts, pin.
> Verification: live mic — after each state transition the next question arrives in the SAME spoken turn (no caller prompt needed).

### SOURCE D — v2 plan T3(d) silence re-ask, VERBATIM (this is the ancestor of T2 pause re-prompt):
> (d) silence re-ask: EOT-timeout ~2s with no caller speech → graph speaks a REPHRASED re-ask of its last question (gated `silence_reask`, `silence_reask_ms=2000`, tracer span `silence_reask`).

### SOURCE E — `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` PT-68 row (`d74b63f`), VERBATIM:
> | PT-68 | **OPEN — re-fix SMALL on main (next tasks)** | 2026-09-23 | **~10s pause → agent speaks on its own** (owner flow rule). STT sometimes never fires EOT on a caller answer (live proof: micbridge-adaa30aeb282 t13: 26s dead air, STT dropped the utterance entirely; faeef9769187: adopted Deepgram socket zombie — 39s audio sent, zero messages). | Small fix on main: a silence/pause timer that re-prompts the agent (rephrased re-ask, one-shot). If re-doing the timer: T3-style session timer is the model — but port it CLEAN onto main, never from the polluted branches (lite @ 651e567 has the reference implementation if needed for reference ONLY). Also candidate: adoption health-check for prewarmed STT sockets. |

### SOURCE F — PENDING_TASKS PT-70 row, VERBATIM:
> | PT-70 | **WIN — keep (huge owner win), re-iterate carefully** | 2026-09-23 | **Silent acks FIXED (huge win)** — transition acks now carry the next question in the same turn (iter68 T2 `22e6f88` deterministic transition beat + `turn_asked` flag). This is the ONE piece of iter68 worth keeping. | Re-implement SMALL on main (the transition-beat prompt directives + one-trip logic) as its own tiny commit — reference `engine/iter68-speech-flow` @ `22e6f88` for the diff, but re-fix, don't grab. |

### SOURCE G — parked-commit implementation facts (for reference ONLY, verified this session):
- `c6159ce` iter68 T1 (observability): 5 files, +346/-128. speech_filter logging at BOTH flush sites + mic_events CUT/REASK tags + speech_replay knobs passthrough; 5 pins.
- `22e6f88` iter68 T2 (transition beat): 13 files, +228/-17 — one-trip ack + `turn_asked` flag + prompt directives + llm.json mirror (refer=36).
- `c3022c3` iter68 T3: silence re-ask = session timer + ingest no-empty-user guard + re-ask-round-always-heavy + post-history directive (the cos machinery AROUND it is parked — take ONLY the timer mechanics shape).
- `651e567` iter68-lite T3: the CLEAN silence re-ask port (3 files, +75/-3, "NO cos machinery") — the reference diff for T2.
- Read them: `git -C /home/julio/projects/clean_diallux_SDR show 651e567 -- engine/diallux/media/session.py engine/diallux/config.py` and `git -C /home/julio/projects/clean_diallux_SDR show 22e6f88 -- engine/diallux/graph/builder.py engine/diallux/state.py`

## Tasks (in order) — HITL STOP AT EVERY T
### T2 — Pause re-prompt (PT-68) — ONE commit — NEXT, awaiting owner GO
Goal (merged SOURCE D + E): caller silent ~10s after an agent question → agent speaks a REPHRASED re-ask ONCE; never loops; cancelled instantly on caller speech; one-shot per turn; knob-first.
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py`, 1 pin file.
Mechanics: one-shot asyncio timer armed after each agent turn drains (NOT on start); fires into `_run_turn("", extra_payload={"pause_reask": True})` (no empty user message in history — ingest no-empty-user guard shape from `651e567`); directive rides the post-history delta: "the caller has gone quiet — re-ask ONCE, shorter, differently worded, then stop"; disarmed by first speech (`_on_start_of_turn`); never re-arms on its own turn. Knobs: `pause_reask=True`, `pause_reask_ms=10000` (owner "~10s" — NOT the lite 2000ms).
Size law: ≤60 lines total or STOP and ASK.
Verification: pins; live mic — answer a question, go silent ~11s, agent re-asks once rephrased; journal `pause re-ask firing (armed at turn N)`; NO loop after the single re-ask.
### T3 — Transition beat / silent acks (PT-70) — ONE commit
Goal (merged SOURCE B + C + F): every `transition_to_X` ack round ends with the destination's next question in the SAME spoken turn (no flat ack → dead air). Engine one-trip: the transition ack round one-trips ONLY when `turn_asked`; a flat ack routes to the destination's ONE continuation round. Prompt directive per SOURCE B(c) — ask the destination's first scripted question IF it fits the live conversation; otherwise compose ONE contextual question (no blind splicing).
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/diallux/state.py` (`turn_asked` post-filter flag), prompts Intake/Discovery/Closer/Offer `.md` + `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json` (byte-parity mirror, refer=36).
Reference ONLY: `git -C /home/julio/projects/clean_diallux_SDR show 22e6f88 -- engine/diallux/graph/builder.py engine/diallux/state.py`
Verification: pins; live mic — after each state transition the next question arrives in the SAME spoken turn.
### T4' — Same-turn jaccard dedupe (owner option 2) — ONE commit — NEEDS owner threshold sign-off first
Goal: a sentence on the SAME TURN that is near-duplicate (not byte-identical) of an already-spoken sentence of that turn is dropped from SPEECH only. Same-turn scope ONLY (the window already resets at ingest, builder.py:2732 — cross-turn scripted re-asks are never touched). NO embedder.
Mechanics (exact spec, owner-approved this session): at the iter42 flush site (mid-stream + stream-end), after the exact-window check: normalize (casefold, whitespace-collapse, strip filler words `well|so|ok|okay|um|uh|hey|sorry|alright` + punctuation), tokenize to words; if both sentences have ≥ `tts_dedupe_similar_min_words` (4) tokens and jaccard overlap ≥ `tts_dedupe_similar_overlap` (0.80) → drop the SECOND from speech (never joins the window; log via T5 line). Knobs: `tts_dedupe_similar=True`, `tts_dedupe_similar_overlap=0.80`, `tts_dedupe_similar_min_words=4`.
Size law: ≤15 lines at each flush site (one shared helper), own knob, one commit + pin.
Verification: pins (near-dupe dropped, distinct question kept, cross-turn near-dupe KEPT); owner A/B by ear via knob.
### T4p — Prompt-side repetition wording — BLOCKED on owner approval of exact lines
Goal: cross-turn redundancy handled by prompts (PT-69 second row: "if the agent is redundant we can just prompt it"). DRAFT directives (owner must approve verbatim before any .md/llm.json edit): each state prompt gains "never say the same or near-same sentence twice this call; when re-asking, change the wording AND shorten" in the VOICE OUTPUT rules block.
Files: prompts `Intake/Discovery/Closer/Offer/contact_details` `.md` + llm.json mirror.
Verification: owner says the exact lines OK → edit → suite pins → battery transcripts show ≤2 asks per missing field.
### T5 — Observability lines (SOURCE A, re-scoped tiny) — ONE commit
Goal: every filter drop logs `speech_filter stage=<sanitize|exact|similar|fast_flush> sent="<sentence>" state=<s> turn=<n>` at INFO (forensics only — zero behavior change); `mic_events.py` gains the CUT tag; `speech_replay.py` mirrors the jaccard rule so replay stays truthful automatically.
Files: `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py`, `/home/julio/projects/clean_diallux_SDR/engine/scripts/mic_events.py`, `/home/julio/projects/clean_diallux_SDR/engine/scripts/speech_replay.py`, 1 pin.
Verification: scripted FakeLLM round with an artifact + a near-dupe logs both lines in caplog; `speech_replay.py` output matches journal lines on a replay.
### T6 — Battery + lane deploy + ear test
Commands: the battery block in Deploy Rules (`--personas happy3`), then the lane-deploy block, then owner ear test. Ear checklist: (1) pause re-prompt at ~10s ONCE; (2) transition acks carry the next question; (3) near-dupe same-turn second sentence NOT spoken; (4) scripted re-asks ACROSS turns still audible (the iter59 disaster must NOT return); voice UNCHANGED (cartesia pin verified in journal).
Verification: 3/3 BOOK; `python3 /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db gates --a chat-iter65-happy --b chat-iter70-happy` green on G1/G2/G4; report written; bookings cancelled/verified.
### T7 — Closeout: lane restore + HITL merge ASK
Commands: the lane-RESTORE block; `hitl_ping.py` the merge ASK (LAW 0 — merge = owner only). Verification: main checkout clean; ASK sent.

## Validation Plan (end-to-end)
1. HITL at every T — owner GO before each task starts; ≤60-line diffs (PT-73).
2. Each task = one small commit + pin; suite subset green after every commit.
3. Battery happy3 3/3 BOOK on branch code; ledger via MAIN SDK; gates by SQL.
4. Lane :8024 serves the branch for the ear test; cartesia pin verified; restored after.
5. Owner ear verdict = the ONLY merge gate; merge = owner only.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merged-turn "keep first + last, trim middle" hook | Owner verdict 2026-09-23: unnecessary — replaced by T4' jaccard same-turn dedupe + T4p prompts |
| STT zombie-socket watchdog / adoption health-check (PT-72, lite `95f7ace`) | Infra bug — separate small ride after this one proves out |
| Mic WS 11-12s open on page load (PT-72) | Browser-bridge audit, separate |
| Twilio merge (iter67 `0394a3b`) | Parked merge-ready; owner-gated separately |
| Industry-vertical KB pin | Owner-gated separate decision |
| Cherry-picking anything from `engine/iter68-*` | PT-73 law — reference-only |
