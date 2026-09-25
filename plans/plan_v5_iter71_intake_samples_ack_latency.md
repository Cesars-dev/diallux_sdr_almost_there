# plan_v5_iter71_intake_samples_ack_latency — Intake samples → generation seeds + flat-ack continuation latency fix (carries iter70 battery evidence)

## Meta
- Date: 2026-09-23
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: three continuation items from the iter70 session — (1) latency forensics on the iter70 battery (cache-0 rounds / TTFT), (2) the flat-ack continuation latency gap (owner: "I think it's a minor gap"), (3) Intake.md (and siblings owner points at) samples rewritten from verbatim-followed scripts into generation seeds. HITL at every T.
- Status: PLAN ONLY (not started — awaits owner approval)
- Owner LAW recorded 2026-09-23: **NO batteries, no LLM-spending runs without owner say-so. No edits while any run is live.**

## Compaction Context
Dialux SDR v5 engine (LangGraph voice pipeline). Iter70 (`engine/iter70-speech-fixes`, 5 commits on the branch, worktree `/tmp/opencode/wt-iter70`) shipped 4 speech fixes re-implemented small from the parked iter68 branches (PT-73 law: reference diffs only, never cherry-pick):
- `65f3567` T2 pause re-prompt (PT-68): one-shot 10s session timer, `pause_reask`/`pause_reask_ms=10000` knobs, ingest no-empty-user guard, re-ask round always heavy, directive rides delta regardless of state-block emptiness (audit A1 fix)
- `94f5164` T3 transition beat (PT-70): ok `transition_to_*` one-trips ONLY when `turn_asked` (post-filter "caller heard '?'" truth, set at both flush sites); flat ack routes to the destination's ONE continuation round; prompt directives "Every turn ends with a question…" (Intake/Discovery/Closer/Offer) + "When a stage transition just moved you here, your ack ends with EITHER the next scripted question (if it fits the live conversation) OR one short contextual question that keeps the flow — never a flat ack." (Discovery/Closer/Offer); llm.json mirror (refer=36 preserved); 4 legacy tests updated
- `02b4bef` T4' same-turn jaccard dedupe (owner option 2, no embedder): token jaccard ≥0.80 (min 4 words, filler-stripped `well|so|ok|okay|um|uh|hey|sorry|alright`) after the exact-window check at both flush sites; knobs `tts_dedupe_similar=True`/`tts_dedupe_similar_overlap=0.80`/`tts_dedupe_similar_min_words=4`; speech_replay mirror
- `87a0ce5` T5 speech_filter observability: `speech_filter stage=<sanitize|exact|similar|fast_flush> sent=… state=… turn=…` INFO lines (7 sites) + mic_events CUT/REASK tags + replay parity
- `dc62fb9` T4p (owner-directed verbatim): bold hard rule `- **NEVER repeat yourself** — not the same sentence, not a near-same rewording. If it was covered, don't bring it up again; when re-asking, change the wording AND make it shorter.` in `general_prompt.md` CRITICAL CONSTRAINTS + 7 new ack filler samples `<Sure> <Ok so...> <Nice> <Gotcha> <Fair enough> <Absolutely> <Perfect>` appended to the acknowledge-before-moving-on line; llm.json `general_prompt` byte-parity mirror verified True

Evidence: first battery `chat-iter70-happy` (fired 15:07–15:29, commit `87a0ce5`, happy3 = Danny/Susan/Marcus) → **3/3 BOOK, ALL PASS**; ledger gates G1 PASS (iter70), G2 PASS (both runs). G3/G4 (cache/TTFT) FAILED with two causes: (a) T4p prompt commit landed MID-battery (~15:12) → Susan/Marcus loaded new general-prompt bytes → turn-1 cache cold → G3 turn-1 2/3 + G4 TTFT inflation; (b) T3 structural: same-turn continuation rounds cold-prefill the destination head (cache-0 rounds worst=5 ≈ one per flat transition) — the destination warm fired at `execute()` needs ~700-1200ms, the continuation only bounded-awaits 100ms (mid-turn, `rounds_left` already decremented) → timeout → cold round. Pre-T3, that same question rode the NEXT turn's entry_lite ack with the caller's 2-5s speech window for the warm to land. A second (clean) battery was fired at 15:30 WITHOUT owner say-so and killed ~2 min later (owner LAW above). Owner verdict on the cache-0 cause: "we are loading lite on a silent turn… we can load that turn with the filler question or the continuation script… its a minor gap" — the lite packing itself is CORRECT and untouched; the gap is WHEN the continuation arrives (same turn as the transition, no speech window for the warm).

Owner-directed next-session items (this plan): analyze the battery latency evidence; fix the Intake "weird state" — its `<sample>` lines are FULL scripted sentences the model follows verbatim, amplified by `Store it verbatim` / `never paraphrase {{interest_topic}}` rules (contrast: `general_prompt.md:15` "Any phrase between < > is an example to vary, not copy verbatim" and `Discovery.md:10` "Generate your question from their words + the angle — never read a question verbatim" — Intake has NO such line); and the ack-latency fix.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| iter70 branch stays UNMERGED | Merge = owner only (LAW 0); ear test is the merge gate |
| T4p = the bold rule + 7 filler samples, verbatim owner wording | Owner approved in-session 2026-09-23 (`dc62fb9`) |
| NO batteries / LLM-spending runs without owner say-so | Owner LAW this session (second battery fired 15:30 was killed) |
| NO edits while any run is live | Owner LAW this session (T4p mid-battery contaminated G3/G4) |
| Lite packing (entry_lite) is correct — do not re-engineer it | Owner: "they are all 'new' prompt (no cache) that's why we make them lite… whats going on" → the gap is timing, not packing |
| Intake fix direction = samples → generation seeds, NOT more dedupe code | Owner verdict: samples followed verbatim; `Discovery.md:10` already has the pattern |
| The cache-0/TTFT issue = "minor gap" | Owner words; fix small, prompt-first, env-knob-first (PT-73 law) |
| Suite baseline = 476 passed + 4 pre-existing env failures | Verified twice this session: `test_iter46_latency_floor.py::test_fast_first_flush_before_stream_end` (flake), `test_iter59_dedupe_semantic.py::test_semantic_threshold_config_defaults` + `test_iter60_audit_fixes.py::test_turn_opening_reask_dropped_when_window_nonempty` (worktree `.env` `TTS_DEDUPE_SEMANTIC=false` leak), `test_tts_providers.py::test_factory_switches_provider` (documented) |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner GO on this plan (T0) | HITL ASK |
| Exact Intake.md rewrite lines (T2) | Paste before/after in chat → owner approves before editing |
| Owner's list of OTHER states whose samples follow verbatim (Offer ask, contact_details lead-ins, …) | Owner points at them in-session |
| Ack-latency fix mechanism choice | T1 forensics → options table → owner picks |
| Any battery / lane-ear-test run | Owner say-so ONLY (LAW this session) |
| Merge say-so | Telegram ASK at closeout |

## Environment & Dependencies
- Branch `engine/iter70-speech-fixes` @ `dc62fb9` (5 commits, suite 476 passed + 4 pre-existing); worktree `/tmp/opencode/wt-iter70` (`.venv` symlinked to `/home/julio/projects/clean_diallux_SDR/engine/.venv`, `.env` has voice LAW: `TTS_PROVIDER=cartesia`, `CARTESIA_MODEL_ID=sonic-3.6-2026-08-27`, `TTS_GATE_FAST_FIRST_FLUSH=false`, `TTS_DEDUPE_SEMANTIC=false`)
- Python: `/tmp/opencode/wt-iter70/engine/.venv/bin/python` (3.12.3, pytest 9.1.1)
- Lane: systemd `diallux-8024.service` (`WorkingDirectory=/home/julio/projects/clean_diallux_SDR/engine`), logs `journalctl --user -u diallux-8024.service`; mic page `https://flores.diallux-ai.site/voice24/mic?k=$VOICE_TEST_TOKEN` (token in `/home/julio/projects/clean_diallux_SDR/engine/.env`)
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` — import/pulls ONLY via the MAIN-repo SDK `/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py`; reading DBs = NO `sqlite3` CLI, use `<worktree>/engine/.venv/bin/python -c "import sqlite3; …"`
- Langfuse: self-hosted `http://localhost:3001`; SDK `/home/julio/projects/clean_diallux_SDR/engine/scripts/lf.py` + `scripts/lf_quick.py`
- Battery artifacts (iter70 run): log `/tmp/opencode/iter70_battery.log`; per-call JSON logs `/tmp/opencode/wt-iter70/engine/tests/llm2llm/json_logs/BOOKDanny_l2l-bookdanny-84317da7.json`, `BOOKSusan_l2l-booksusan-a96874b7.json`, `BOOKMarcus_l2l-bookmarcus-6c9a0ae0.json`; ledger run `chat-iter70-happy` (imported, commit `87a0ce5`, window 15:07-15:29, 3 calls); Langfuse traces reachable via the ledger rows / `lf_quick.py runs`
- Dead artifact: `/tmp/opencode/iter70_battery_b.log` (530 bytes, killed 15:32, unusable)
- Suite baseline + known failures listed in Resolved Decisions

## Architecture (one block)
```
iter70 branch @ dc62fb9 (lane still serves clean main @ ced8538)
   ├─ T1: latency forensics on chat-iter70-happy (ledger rounds + Langfuse; zero spend)
   ├─ T2: ack-latency fix — owner picks mechanism from the T1 options table (≤60 lines)
   ├─ T3: Intake.md (+ owner-pointed states) samples → generation seeds (owner-approved lines only)
   ├─ T4: suite + pins
   ├─ T5: lane deploy → owner ear test → restore   (owner say-so: spend)
   └─ T6: closeout ASK (merge = owner only)
```

## File Map
| File (absolute path) | What changes | New/Edit |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter71_intake_samples_ack_latency.md` | THIS plan (docs → main) | New |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-68..71 status updates + new rows (docs → main) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/Intake.md` | T3: samples → generation seeds (owner-approved lines only) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/Offer.md` + `contact_details.md` | T3: same treatment ONLY where owner points | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/agent/llm.json` | T3: byte-parity mirror of every prompt edit | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` | T2: the owner-picked ack-latency fix (options below) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/media/session.py` | T2: only if the picked fix touches the timer | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter71_*.py` | T4: pins per task (small NEW files) | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter71-ack-latency/01_latency.md` | T1 forensics report (gitignored) | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter71-ack-latency/02_report.md` | battery/ear-test report (gitignored) | New |

## Deploy Rules
- Lane deploy (copy + restart + verify) — ONLY on owner say-so:
  ```
  cd /tmp/opencode/wt-iter70 && git checkout-index --prefix=/tmp/opencode/iter71_stage/ -af && \
  cp /tmp/opencode/iter71_stage/engine/diallux/graph/builder.py /home/julio/projects/clean_diallux_SDR/engine/diallux/graph/ && \
  cp /tmp/opencode/iter71_stage/engine/diallux/config.py /tmp/opencode/iter71_stage/engine/diallux/state.py /home/julio/projects/clean_diallux_SDR/engine/diallux/ && \
  cp /tmp/opencode/iter71_stage/engine/diallux/media/session.py /home/julio/projects/clean_diallux_SDR/engine/diallux/media/ && \
  cp /tmp/opencode/iter71_stage/engine/agent/llm.json /home/julio/projects/clean_diallux_SDR/engine/agent/ && \
  cp /tmp/opencode/iter71_stage/engine/diallux/prompts/*.md /home/julio/projects/clean_diallux_SDR/engine/diallux/prompts/ && \
  cp /tmp/opencode/iter71_stage/engine/scripts/mic_events.py /tmp/opencode/iter71_stage/engine/scripts/speech_replay.py /home/julio/projects/clean_diallux_SDR/engine/scripts/ && \
  systemctl --user restart diallux-8024.service && sleep 5 && \
  journalctl --user -u diallux-8024.service -n 10 --no-pager | grep "cartesia connected"
  ```
  MUST print `model=sonic-3.6-2026-08-27` (voice LAW).
- Lane RESTORE after the ear test: `git -C /home/julio/projects/clean_diallux_SDR checkout -- engine/diallux engine/agent/llm.json engine/scripts && systemctl --user restart diallux-8024.service`
- Battery (OWNER SAY-SO REQUIRED): `cd /tmp/opencode/wt-iter70/engine && set -a && . ./.env && set +a && setsid nohup .venv/bin/python tests/llm2llm/harness.py --personas happy3 --rag --langfuse --max-turns 48 > /tmp/opencode/iter71_battery.log 2>&1 < /dev/null &`
- NEVER touch: `:8021`/`:8022` (pids 3834955/884638), `:8000-8003`, `engine/diallux/media/prewarm.py`, `elevenlabs_tts.py`, `tts_factory.py`, live agent IDs, Cal.com event 3801235 real bookings (battery uses mock webhooks — nothing to cancel), `CARTESIA_MODEL_ID` in any .env, `TTS_DEDUPE_SENTENCES`, `TTS_DEDUPE_SEMANTIC` (stays env-false), `entry_lite` packing (owner-verified correct)
- Push = owner terminal (agent shell has no creds); main checkout has a pre-existing dirty `docs/Testing_guidelines/MIC-CALL-ANALYSIS-SOP.md` — never stage it

## Tasks (in order) — HITL STOP AT EVERY T
### T0 — HITL ASK
Present this plan → owner GO before anything.

### T1 — Latency forensics on `chat-iter70-happy` (READ-ONLY, zero spend)
Goal: attribute the G3/G4 failures to exact rounds. Pull per-round `cache_read`/`input_tokens`/`ttft` for the 3 calls from the ledger (`/home/julio/projects/clean_diallux_SDR/scripts/live_sql.py rounds --run chat-iter70-happy`) + Langfuse gens; identify which rounds were cache-0 (hypothesis: the 5 same-turn T3 continuation rounds — one per flat transition; verify whether the destination warm was in-flight at each). Cross-check with the per-call JSON logs above.
Commands: `python3 /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py rounds --run chat-iter70-happy`; `python3 /home/julio/projects/clean_diallux_SDR/engine/scripts/lf_quick.py rounds --run chat-iter70-happy` (adapt flags to the script's CLI — read `--help` first).
Output: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter71-ack-latency/01_latency.md` with a per-round table + the options table for T2.
Verification: the report names each cache-0 round (state, turn, round, ttft) and confirms/refutes the warm-in-flight hypothesis.

### T2 — Ack-latency fix — mechanism owner-picked from the T1 options table — ONE commit
Options (T1 refines the numbers):
- **(A) owner's filler-question shape:** a flat ack does NOT spawn a cold LLM continuation — the engine speaks a deterministic ack+question (destination prompt's first scripted question, pre-loaded, zero LLM round). Cache-0 gone; no LLM cost; risk: determinism vs flow fit.
- **(B) warm re-fire:** on `tool_call_start` of `transition_to_*`, ALSO prewarm the CONTINUATION shape (the exact next-round bytes incl. turn-1 history) so the same-turn continuation rides cache (the existing tool-detection warm fires too early with pre-patch dvs — `force=True` re-fires post-execute but lands too late for a same-turn continuation).
- **(C) prompt-only:** strengthen the transition-round directives so flat acks stop happening (the engine continuation becomes rare) — smallest change, no latency fix guarantee.
Files per option: (A) builder.py (+state prompts if the filler text needs a source) · (B) builder.py only · (C) prompts + llm.json.
Size law: ≤60 lines; >50 needs owner sign-off. Verification: pins + (owner say-so) ear test shows no dead air AND steady TTFT p50 back under the 950 gate on a fresh battery.

### T3 — Intake samples → generation seeds (owner-approved lines ONLY)
Goal: stop verbatim sample-following. Mirror `Discovery.md:10`'s pattern into Intake: add "Generate your question/ack from THEIR words — the samples below show the SHAPE only; never read one verbatim." + trim the full-sentence samples (`Intake.md:14-18`, `25-29`, `33`) to shape-only where owner approves; revisit the `:23` "Store it verbatim" and `:49` "never paraphrase {{interest_topic}}" rules so verbatim applies to CAPTURE (dvs), not to spoken output. Same treatment for any other state the owner points at (Offer ask `Offer.md:11-13`, contact_details lead-ins). llm.json byte-parity mirror (refer-count check: the word `refer` must stay 36 in llm.json unless the owner approves wording that contains it).
HITL: paste the exact before/after diff in chat → owner approves → edit .md → mirror llm.json (surgical raw-text insert, anchors at end-of-line) → `python3 -c "import json; json.load(open('/tmp/opencode/wt-iter70/engine/agent/llm.json'))"` + `pytest tests/test_iter43_prompts.py tests/test_iter31_c3_prefix.py -q` in `/tmp/opencode/wt-iter70/engine`.
Verification: lockstep tests green; owner reads the diff.

### T4 — Suite + pins
Commands: `cd /tmp/opencode/wt-iter70/engine && .venv/bin/python -m pytest tests --tb=no -p no:warnings` — expect 476 passed + the 4 documented failures (see Resolved Decisions). New pins in `test_iter71_*.py` for the T2 fix (flat ack → deterministic speech path when option A; warm-coverage pin when option B).
Verification: full suite matches baseline + new pins green.

### T5 — Lane deploy + owner ear test (OWNER SAY-SO: spend)
Deploy block above → ear checklist: (1) pause re-prompt ~10s ONCE; (2) transition acks carry the next question in the SAME turn; (3) near-dupe same-turn second sentence NOT spoken; (4) cross-turn scripted re-asks STILL audible; (5) voice UNCHANGED (`journalctl --user -u diallux-8024.service | grep "cartesia connected"` prints `model=sonic-3.6-2026-08-27`); (6) Intake acks now vary with the caller's words (no verbatim samples). Restore block after.

### T6 — Closeout
Report `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter71-ack-latency/02_report.md`; PENDING_TASKS updates (docs → main); Telegram merge ASK (LAW 0 — merge = owner only). Optionally the branch-registry refresh ritual from AGENTS.md §"TWO ledgers" (run from the MAIN `engine/` checkout).

## Validation Plan (end-to-end)
1. HITL at every T; ≤60-line diffs (PT-73).
2. T1 zero spend (ledger/Langfuse reads only).
3. Any battery/ear-test = owner say-so first (LAW 2026-09-23).
4. Owner ear verdict = the ONLY merge gate; merge = owner only.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merging `engine/iter70-speech-fixes` | Owner gate after the ear test |
| STT zombie-socket watchdog (PT-72) | Separate small ride |
| Mic WS 11-12s page-open audit (PT-72) | Browser-bridge audit, separate |
| Twilio merge (iter67 `0394a3b`) | Parked merge-ready; owner-gated |
| Industry-vertical KB pin | Owner-gated separate decision |
| Cherry-picking from `engine/iter68-*` | PT-73 law — reference-only |
