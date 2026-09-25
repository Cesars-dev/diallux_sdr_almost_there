# PLAN — iter43: EOT telemetry-first, cache-prefix fix + async state prewarm, Offer consent ask (prompt-first), contact-details softening, speed +0.07

## Meta
- Date: 2026-09-10
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — (1) wire EOT + token/cache telemetry into the live turn reports (no behavior change), (2) fix the prompt-cache prefix (hysteretic history trim + forced-speech keeps tools), (3) async prompt-cache prewarm of states (greeting + on-transition) with a light first exchange, (4) Offer consent ask (PROMPT-FIRST: the prompt carries the question, then the extract tool — same boolean pattern as every other state; the date binary is DELETED from Offer) and contact_details lead-in + attendee-name rule, (5) Cartesia speed +0.07 via delivery profiles, (6) owner-driven live calls on `:8007` then a data assessment that applies the EOT winner and the history-window verdict.
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context (verbatim carry — session 2026-09-10, iter42 audit + iter43 design)

- **Project:** Dialux SDR voice engine "Linda" — LangGraph 9-state pipeline (Intake → Discovery → Closer → Offer → contact_details → ConfirmSlots → VerifyLead → Booking → Closing), Deepgram Flux STT → gpt-5.4 (`reasoning_effort=none`, `verbosity=low`) → gates → Cartesia sonic-3.6. Repo FORK = `clean_diallux_SDR` (MAIN workspace). Base branch `engine/iter42-dedupe-window` @ **`f5c0912`**, suite **206 passed**. luna (gpt-5.6) DEAD. gpt-5.4 is the production candidate.
- **iter42 (shipped, unmerged):** TTS dedupe sliding window. 3-SOP audit + latency in `research/surgeon/iter42-dedupe-window/{01,02,03}_*.md`. Battery failures (Gene LOW 20-turn Intake stall, name-refusal loops) = owner-deferred, OUT of scope.
- **Live :8007 audit (the evidence this plan acts on):** call `a76f7d57bbc6`, trace `44866edbea1d`, 48 turns, 603.3s → 10-min cap. p50 e2e **1304 ms**, p90 **2935 ms**; bottleneck is entirely STT-EOT→first-LLM-token (p50 1202 / p90 2784). 13 turns >2s; t22=3498/t32=3291 ms align with eager-turn cancellations. TTS handoff ~113 ms — DO NOT TOUCH. Owner verdict: "900 ms felt great, just those awful pauses were terrible."
- **Root causes (code-verified this session):**
  1. **Eager head start ≈ 0** — `eager 0.6 / eot 0.7 / timeout 2500` (`config.py:111-115`, `.env` has only EAGER 0.6). EagerEndOfTurn and EndOfTurn land same-ms. NOTE the live metric `stt_eot_to_llm_first_ms` is actually **EagerEOT→first token** because `mark_user_end()` fires in `_on_eager_eot` (`session.py:292`) — mislabeled, keep the key, document it.
  2. **Cache pinned at 2688 read tokens** — `_history_window` (`builder.py:387-397`) returns exactly `history[-16:]` every round once len>16 → the front of history shifts every turn → OpenAI prefix cache invalidates at the first history element; only tools+static head (~2688 tok) ever hits. Second buster: `force_speech` sends `tools=[]` (`builder.py:495-499`) — tools render FIRST in the cached prefix, so any forced round = full miss (Langfuse cache_read=0 on gens 32/35/37/39, the iter32 force_speech rounds).
  3. **Offer consent is self-certified** — `extract_offer_details` writes `livecall_agreed` ("Call it the instant a commit signal lands"), `offer_completed` same shape; edge `Offer→contact_details` requires `[offer_completed, livecall_agreed]` (verified in `agent/llm.json`). In ONE empty-text round the model co-fires extract+completed+transition; same-round dvs visibility (`builder.py:660`) means the gate's own key was self-certified by the same actor. `Offer.md` step 1 is a date binary ("later today or tomorrow?") that never asks "do you want the walkthrough?" — unchanged since iter21 `2dc13ff`. Live failure: t18/t25/t29 empty-text transitions; t26 caller "What what true are you talking about?".
  4. **Speed knob no-op** — `.env CARTESIA_SPEED` is only the base; `media/delivery.py` `DELIVERY_PROFILES` sets an explicit Cartesia speed for EVERY state + `begin` (Intake 1.05, Discovery 1.0, VerifyLead 1.0, contact_details 0.92, ConfirmSlots 1.0, Booking 1.05, Offer 1.08, Closing 0.95, Closer 0.95, begin 1.05) and `cartesia_tts.py:118-121` merges overrides OVER the global. Changing `.env` alone does nothing.
  5. **Cold TTFT** — iter21 measured gpt-5.2 cold 1638 ms vs 843-952 ms cached (9.7k prefix era). Today's turn-1 payload is **~2956 tok** (tiktoken-verified: general_prompt 1494 + Intake state 674 + Intake tools 688 + VOICE_OUTPUT_RULES ≈100) — NOT 9k. Live turn-1 was 2930 ms.
- **Measured token facts (tiktoken, this session):** general_prompt.md 1494 tok · Intake.md 674 tok · Intake tool schemas (extract + intake_completed + transition_to_Discovery + end_call) 688 tok · Offer.md 748 tok.
- **Postgres verdict (owner question, resolved):** conversation memory via Postgres embedding+retrieval is **REJECTED** — (1) embedding is a 156-277 ms network round trip on the hot path vs effectively-free cached prefix tokens; (2) history must be verbatim (digits/read-backs), similarity top-k dilutes exact facts; (3) per-turn retrieved chunks bust the byte-stable prefix (iter31 C3 architecture); (4) full conv is only ~2-6k tok — the right lever is window size, decided by data. The LangGraph Postgres checkpointer is OFF (`LANGGRAPH_CHECKPOINT=memory` in `.env`, `builder.py:941-957`) and was never prompt context; pgvector RAG (`rag.py`) is KB-only, optimized (156 ms avg pull, keep-alive client, greeting warmup, `rag_min_query_chars=12`). **Keep `history_window=16`; T7 decides 16 vs 32 from the live cache curve.**
- **Cache mechanics (pinned):** LLM = `langchain_openai.ChatOpenAI` 1.6.0, Chat Completions + `bind_tools` (`graph/llm.py:170-184`). No Responses API / `previous_response_id`. OpenAI automatic prefix cache keys on tools FIRST, then messages. `static_head` cached per (state, expand_kb) (`builder.py:349-366`), tools cached per (state, expand_kb) (`builder.py:501-509`). Chat Completions accepts `max_completion_tokens` (constructor param; legacy `max_tokens` ABSENT in langchain-openai 1.6.0 — verified by signature inspection).
- **Prewarm architecture (owner-approved, "recover 800 ms"):** fire-and-forget `StreamingLLM.warm()` requests that replicate the EXACT next-round prefix (full tools + `strip_kb_markers(static_head(state, expand_kb))` + current history snapshot → messages), `max_completion_tokens=16`, output discarded, all exceptions swallowed, latched once per state per call, cancelled in `CallRuntime.aclose()`. Greeting-time prewarm of the FULL Intake shape (runs beside `warm_rag()` at `session.py:170-171` during begin-message playback); on-transition prewarm of the destination state (beside the existing `warm_slots_async` trigger at `builder.py:669-674`).
- **First-turn-lite (owner: "keep first exchange as light as possible"):** turn 1 = general_prompt + VOICE_OUTPUT_RULES only (no state prompt, no tools, no RAG, no state block); config default **False** (tests/eval unaffected), live `.env FIRST_TURN_LITE=true`. Lite does NOT warm turn 2 (tools=[] changes prefix) — the prewarm covers that. Guard `state.get("turn_index", 0) == 1` exactly (turn_index set 0 by `initial_state` (`state.py:73`), incremented at ingest (`builder.py:845`)).
- **Ask-gate (owner decision, final): PROMPT-FIRST — no regex, no engine gate.** The consent question lives in `Offer.md` and the model calls `extract_offer_details` AFTER the caller answers — the exact pattern every other state already uses (prompt ask → extract tool → boolean → edge gate). The date binary ("later today or tomorrow?") is DELETED from Offer entirely (it also contradicted the state's own Mission line "No dates or times here"); scheduling belongs to ConfirmSlots. FALLBACK NOTE (owner-approved): if T6 live calls still show the model capturing `livecall_agreed` without having asked, escalate to the deterministic py-side gate — server-owned dv `offer_asked` (`schema.py` field + `SERVER_OWNED_DVS` → `_exec_extract` hard-rejects model writes, `tools.py:401-403`), Offer state node scans assistant history with `_OFFER_ASK_RE`, executor rejects commit-flagged `extract_offer_details`/`offer_completed` while the flag is False (iter8 end_call-gate pattern, `tools.py:237-247`). Full fallback design is archived in the T4 note below.
- **EOT candidate space (owner: "all eot params we designed") — decided from LIVE telemetry at T7, synthetic probe dropped:** A `0.6/0.7/2500` (current) · B `0.4/0.7/2500` · C `0.4/0.8/4000` · D `0.3/0.8/5000` (eager/eot/timeout; eager must be ≤ eot). Pre-registered winner criteria: median live head_start ≥ 200 ms AND resumed (false-start) rate ≤ 10% AND zero eager-vs-final transcript mismatches AND cancellation count not worse than the ~3/45 baseline AND e2e p90 improves. No candidate qualifies → keep A and record why.
- **Speed (owner: +0.07 everywhere incl. contact_details):** `delivery.py` per-state +0.07: begin 1.12, Intake 1.12, Discovery 1.07, VerifyLead 1.07, contact_details 0.99, ConfirmSlots 1.07, Booking 1.12, Offer 1.15, Closing 1.02, Closer 1.02. `.env CARTESIA_SPEED=1.12` (unlisted-state fallback only). Jitter ±0.06 unchanged.
- **contact_details softening (owner):** lead-in with variations BEFORE step 1 ("Can I grab a few details to get you set up for the live demo?" style, `< >` convention); name-refusal fallback rule → ask "What should I use as the attendee name?" and capture the answer as `first_name`, never re-ask, never loop the read-back (kills the Marcus/Susan ping-pong class).
- **Key paths:** worktree `/tmp/opencode/wt-iter43` (branch `engine/iter43-eot-cache-askgate` off `f5c0912`), `.venv` symlink → `/home/julio/projects/clean_diallux_SDR/engine/.venv`, `.env` copied from `/tmp/opencode/wt-iter42/.env`. Live server `127.0.0.1:8007`. Langfuse `http://localhost:3001`. Postgres 5434 (RAG). Cal.com event `3801235` REAL — cancel every test booking.
- **What remains:** everything — this plan is the execution order T0→T7.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Telemetry BEFORE EOT param change; winner picked from owner's live calls at T7 | Owner: "add log data first, then decide — not guess with A/B/C"; synthetic TTS probe over-estimates confidence (clean audio bias) |
| Cache fix = hysteretic history trim + forced-speech keeps tools | Root cause verified: front-shifting `history[-16:]` busts the prefix every turn; `tools=[]` busts the whole prefix. Both flagged, revertible |
| Hysteresis formula: `start = 8 * ceil((len-n)/8)` (step 8, n 16) → window sawtooths 9..16 entries, start pinned for 8 turns | Stable prefix for ~8 turns per re-prefill; bounded by n; orphan-tool guard unchanged |
| Prewarm = async fire-and-forget `warm()` requests, latched per state, greeting + on-transition | Recovers the ~800 ms cold-vs-cached TTFT gap without touching the hot path; owner: "run async the pre-warms" |
| First-turn-lite default OFF, live via `.env FIRST_TURN_LITE=true`, guard `== 1` | Default-True breaks `test_graph.py:78` (`extract_intake_details in seen_tools[0]`) and eval s1 step-0; `<= 1` also catches default-0 states |
| Ask-gate = PROMPT-FIRST (consent ask in Offer.md → extract tool after the yes; date binary deleted). Regex engine gate = documented FALLBACK only, built only if T6 live calls still self-certify | Every other state already works as prompt-ask → extract-boolean → edge gate; Offer was the mess (its own Mission said "no dates" while step 1 asked "later today or tomorrow"). No new machinery to gamble on |
| `contact_details` speed 0.92→0.99 included | Owner: "+0.07 everywhere, test later" |
| Postgres conversation memory REJECTED; keep window 16; 16-vs-32 decided at T7 from cache curve | 4-axis assessment (latency/exactness/cache/need) in Compaction Context |
| Live testing is OWNER-DRIVEN (2-3 calls), then assess | Owner: "plan should test a few calls then assess from there" |
| Evidence → `research/surgeon/iter43-eot-firstturn/`; commits on branch; plan file on main; ASK JULIO before any merge | LAW 0 |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner's live test calls (T6) | Julio drives from the Mac via `http://127.0.0.1:8007/mic` (ssh tunnel) |
| Current `:8007` server pid at execution time | `lsof -tiTCP:8007 -sTCP:LISTEN` (the iter42 pid 583469 may be stale) |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12). Installed versions (verified): langchain-openai **1.6.0**, langgraph **1.2.11**, langfuse **4.15.1**, websockets **16.1.1**, pytest **9.1.1**, pydantic **2.13.5**, pydantic-settings **2.15.0**, httpx **0.28.1**, fastapi **0.141.1**.
- Base worktree: `/tmp/opencode/wt-iter42` @ `f5c0912` (`.env` present, suite 206).
- New worktree: `/tmp/opencode/wt-iter43`, branch `engine/iter43-eot-cache-askgate`, `.venv` symlink, `.env` copied from wt-iter42.
- Live test server: `127.0.0.1:8007` (uvicorn `diallux.app:app`, foreground via setsid/nohup, log `/tmp/opencode/uvicorn_8007_iter43.log`).
- Deepgram Flux: `wss://api.deepgram.com/v2/listen?model=flux-general-en&encoding=linear16&sample_rate=16000&eot_threshold=<f>&eot_timeout_ms=<ms>&eager_eot_threshold=<f>`, header `Authorization: Token $DEEPGRAM_API_KEY` (`deepgram_stt.py:72-99`). Current params: eager 0.6 (`.env`), eot 0.7 + timeout 2500 (`config.py:111-112` defaults).
- Cartesia: wss `api.cartesia.ai/tts/websocket?cartesia_version=2026-08-14`, key `$CARTESIA_API_KEY`, voice `$CARTESIA_VOICE_ID` (829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30), `generation_config.speed` 0.6-1.5 per request.
- Langfuse `http://localhost:3001`; json_logs + uvicorn log are source of truth when ingest drops.
- Services NEVER touched: `:8000/:8001/:8002/:8003/:8005` (ORIGINAL workspace), live agent IDs (`agent_f305…`, `agent_1698…`, `agent_87e4…`), `slots.db`, ORIGINAL dirty files.
- Cal.com event `3801235` REAL — cancel every booking created on `:8007`.
- Suite at base: 206 passed. `eval/report.json` is a GENERATED artifact — `git checkout -- eval/report.json` before any commit.

## Architecture (one block)
```
                     ┌─ telemetry (T1) ─────────────────────────────────┐
Flux EOT events ──▶ session on_state / clock.extra: t_eager, t_final,   │
                     head_start_ms, eager_final_match, resumed_count     │
                     + builder round-usage log line (input/cache_read/out)│
                     └──────────────────────────────────────────────────┘
caller speech ──▶ state_node ── messages = [strip(static_head)] + hyst_window(history) + [tail]
                       │                      start=8*ceil((len-16)/8)  ← T2 (cache-stable)
                       ├─ turn 1 & FIRST_TURN_LITE → general+VOR only, tools=[] (light)
                       ├─ force_speech → tools KEPT + tail "SPEECH ONLY" directive (T2)
                       ├─ Offer → PROMPT-FIRST consent ask in Offer.md (T4): ask → caller yes →
                       │          extract_offer_details(livecall_agreed) → edge gate (unchanged)
                       ├─ ok transition_to_X → async warm_prompt_cache(X) ┐ (T3)
                       └─ greeting (session.start) → async warm Intake  ──┴─ ChatOpenAI
                                                                       bind_tools(full tools)
                                                                       max_completion_tokens=16
                                                                       output discarded, latch/cancel
EOT decision (T7): live head_start/false-start/cancel data vs criteria → A/B/C/D → .env
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter43_eot_firstturn_ask.md` | this plan (replaces the mockup) | EDIT (this file) |
| `/tmp/opencode/wt-iter43/diallux/config.py` | knobs: `first_turn_lite=False`, `prompt_prewarm=True`, `prewarm_max_completion_tokens=16`, `history_trim_step=8`, `force_speech_keep_tools=True`; deepgram comments | EDIT |
| `/tmp/opencode/wt-iter43/diallux/graph/builder.py` | hysteretic `_history_window`; forced-speech keeps tools + tail directive; first-turn-lite branch; usage log line; `warm_prompt_cache()`/`_warm()`; transition prewarm trigger | EDIT |
| `/tmp/opencode/wt-iter43/diallux/graph/llm.py` | `StreamingLLM._warm_llm` (max_completion_tokens) + `async warm(messages, tools)` | EDIT |
| `/tmp/opencode/wt-iter43/diallux/graph/tools.py` | NO CHANGE (prompt-first consent ask; regex gate is fallback-only) | — |
| `/tmp/opencode/wt-iter43/diallux/schema.py` | NO CHANGE (no `offer_asked` dv unless the fallback is triggered later) | — |
| `/tmp/opencode/wt-iter43/diallux/media/session.py` | `_on_stt_state` wired (both STT constructions), eager/final transcript compare, `resumed_count`, t_eager/t_final/head_start into clock.extra | EDIT |
| `/tmp/opencode/wt-iter43/diallux/prompts/Offer.md` | consent ask + variations (step 0), day choice moves after yes, gate rules | EDIT |
| `/tmp/opencode/wt-iter43/diallux/prompts/contact_details.md` | demo lead-in + attendee-name fallback rule | EDIT |
| `/tmp/opencode/wt-iter43/agent/llm.json` | byte-lockstep `state_prompt` for Offer + contact_details | EDIT |
| `/tmp/opencode/wt-iter43/diallux/media/delivery.py` | +0.07 all cartesia speeds (begin 1.12, Intake 1.12, Discovery 1.07, VerifyLead 1.07, contact_details 0.99, ConfirmSlots 1.07, Booking 1.12, Offer 1.15, Closing 1.02, Closer 1.02) | EDIT |
| `/tmp/opencode/wt-iter43/tests/test_delivery.py` | speed expectations updated | EDIT |
| `/tmp/opencode/wt-iter43/tests/test_iter32_gate.py` | forced-speech tests: tools KEPT + directive; one kill-switch test (flag False → `[]`) | EDIT |
| `/tmp/opencode/wt-iter43/tests/test_iter30_fast.py` (+ grep `history` in `tests/test_iter31_c3_prefix.py`) | window-count expectations → hysteretic formula | EDIT |
| `/tmp/opencode/wt-iter43/tests/test_iter43_prompts.py` | 3 tests (Offer has consent ask + NO date binary; contact_details has lead-in + attendee-name rule; llm.json byte-lockstep) | NEW |
| `/tmp/opencode/wt-iter43/tests/test_iter43_prewarm.py` | 3 tests (warm sends full tools+head bytes; latch; exceptions swallowed) | NEW |
| `/tmp/opencode/wt-iter43/tests/test_iter43_history_hysteresis.py` | 3 tests (sawtooth pins start at len 17→8 and 25→16; orphan guard; growth appends) | NEW |
| `/tmp/opencode/wt-iter43/tests/test_first_turn_lite.py` | 3 tests (lite payload; turn 2 full; kill-switch) | NEW |
| `/tmp/opencode/wt-iter43/eval/scenarios/s6_offer_ask_gate.json` | ask-shape scenario (structure copied from `s1_*.json`) | NEW |
| `/tmp/opencode/wt-iter43/.env` | `FIRST_TURN_LITE=true`, `CARTESIA_SPEED=1.12`; T7 adds winner `DEEPGRAM_*` vars | EDIT |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter43-eot-firstturn/` | `01_telemetry_and_live_calls.md`, `02_iter43_report.md` | NEW (gitignored) |

## Deploy Rules
- Suite green before any live step; batteries/evals as separate processes; uvicorn log + json_logs are source of truth.
- `:8007` relaunch (old log preserved):
  ```bash
  lsof -tiTCP:8007 -sTCP:LISTEN | xargs -r kill; sleep 2
  cd /tmp/opencode/wt-iter43 && set -a && . ./.env && set +a && \
    setsid nohup /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python \
    -m uvicorn diallux.app:app --host 127.0.0.1 --port 8007 \
    > /tmp/opencode/uvicorn_8007_iter43.log 2>&1 < /dev/null & disown
  sleep 6 && curl -s -m 5 http://127.0.0.1:8007/health
  ```
- Mac tunnel (owner-side): `lsof -tiTCP:8007 -sTCP:LISTEN | xargs kill 2>/dev/null; ssh -N -L 8007:127.0.0.1:8007 julio@46.62.233.228` → `http://127.0.0.1:8007/mic`.
- `.env` sourced before any python needing keys: `set -a; . ./.env; set +a`.
- **Cancel EVERY live booking** created on `:8007` (Cal.com event 3801235 REAL) — booking UID from the call transcript/tool trace, cancel via Cal.com API with the ORIGINAL `.env` `CALCOM_API_KEY` or `booking_intent=cancel` semantics.
- NEVER touch `:8000/:8001/:8002/:8003/:8005`, live agent IDs, `slots.db`.
- **LAW 0:** commits on the branch; NO merge to `engine/main` without Julio's explicit say-so. Plan file commits straight to main. Run `scripts/keyhound` before any push. `git checkout -- eval/report.json` before commits.

## Tasks (in order)

### T0 — Branch + worktree + suite
Goal: iter43 branch exists at `f5c0912`, suite green.
Commands:
```bash
cd /tmp/opencode/wt-iter42 && git worktree add -b engine/iter43-eot-cache-askgate /tmp/opencode/wt-iter43 f5c0912
ln -sfn /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter43/.venv
cp /tmp/opencode/wt-iter42/.env /tmp/opencode/wt-iter43/.env
cd /tmp/opencode/wt-iter43 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q
```
Verification: HEAD = `f5c0912` on `engine/iter43-eot-cache-askgate`; suite exits 0 (206).
Dependencies: none.

### T1 — Telemetry (EOT + tokens; NO behavior change)
Goal: every live turn report carries the EOT timing block and the round's token/cache usage.
Files: `/tmp/opencode/wt-iter43/diallux/media/session.py`, `/tmp/opencode/wt-iter43/diallux/graph/builder.py`.
Edit spec:
1. `session.py` — add `async def _on_stt_state(self, msg)`; wire `on_state=self._on_stt_state` in BOTH `DeepgramSTT(...)` constructions (start ~line 148 and reconnect ~line 339). In `_on_eager_eot` (after `mark_user_end()`): store `self._clock.extra["t_eager"] = time.perf_counter()` and `self._eager_transcript = transcript`. In `_on_eot` adopt branch (the `clock.extra.get("eager")` block, ~line 255): `self._clock.extra["t_final"] = time.perf_counter()`; `self._clock.extra["head_start_ms"] = round((t_final - t_eager)*1000, 1)`; `self._clock.extra["eager_final_match"] = (self._eager_transcript == transcript)`; then clear `self._eager_transcript`. In `_on_turn_resumed`: `self._resumed_count += 1` (init `self._resumed_count = 0` in `__init__`); append `"resumed_count": self._resumed_count` into the final turn-report dict (read `session.py:380-430` first — the final report build — and add the key there). Fields flow into BOTH report lines automatically via `clock.report()`'s `**self.extra` (`observability/latency.py:50`).
2. `builder.py` — add `import logging` + `log = logging.getLogger("diallux.graph")`. After the `final` LLM event is consumed (after the `async for ev in runtime.llm.astream(...)` loop, where `usage` is bound):
   ```python
   if usage:
       itd = usage.get("input_token_details") or {}
       log.info("round usage: turn=%s state=%s input=%s cache_read=%s output=%s",
                state.get("turn_index"), state_name,
                usage.get("input_tokens"), itd.get("cache_read", 0) or 0,
                usage.get("output_tokens"))
   ```
3. No renames: `stt_eot_to_llm_first_ms` key stays (scripts parse it); document in the report that it is eager-anchored.
Verification: `grep -n "on_state" diallux/media/session.py` shows both wirings; `grep -n "round usage" diallux/graph/builder.py` shows the log line; suite still 206 green.
Dependencies: T0.

### T2 — Cache-prefix fix (hysteretic window + forced-speech keeps tools)
Goal: `cache_read` grows past 2688 across turns; forced rounds stop busting the prefix.
Files: `/tmp/opencode/wt-iter43/diallux/graph/builder.py`, `/tmp/opencode/wt-iter43/diallux/config.py`, `/tmp/opencode/wt-iter43/tests/test_iter43_history_hysteresis.py` (NEW), `/tmp/opencode/wt-iter43/tests/test_iter32_gate.py` (EDIT), `/tmp/opencode/wt-iter43/tests/test_iter30_fast.py` (EDIT).
Edit spec:
1. `config.py`: add `history_trim_step: int = 8` and `force_speech_keep_tools: bool = True` (comments: iter43 cache-prefix stability; flags revertible).
2. `builder.py` `_history_window` → hysteretic:
   ```python
   @staticmethod
   def _history_window(history: list[dict], n: int, step: int = 8) -> list[dict]:
       """iter43: hysteretic trim — the window START only advances every `step`
       entries past n, so the cached prefix stays byte-stable between jumps.
       len 17..24 (n=16,step=8): start pinned at 8 (window 9..16, append-only);
       len 25: start jumps to 16. One re-prefill per jump instead of per turn."""
       if n <= 0 or len(history) <= n:
           return list(history)
       start = step * ((len(history) - n + step - 1) // step)
       tail = history[start:] if start < len(history) else []
       while tail and tail[0].get("role") == "tool":
           tail = tail[1:]
       return tail
   ```
   Call site passes `step=self.settings.history_trim_step`.
3. Forced speech (`builder.py:495-499`): when `force_speech` and `settings.force_speech_keep_tools`, take the SAME tools from `runtime._tools_cache`/`build_tool_schemas` as the normal path, and append to the tail: `"\n\nTHIS ROUND: SPEECH ONLY — do not call any tool. Reply to the caller in one or two short sentences, then stop."` (tail may be empty — then this becomes the tail). Flag False → exact old behavior (`tools=[]`, no directive). Documented risk: the model may still call a tool on a forced round; the executor still runs it (no worse than pre-iter32) and `round_spoke` re-evaluates next round.
4. `tests/test_iter43_history_hysteresis.py` (FakeLLM-free, pure function tests): (a) len 17 and len 24 → start 8 (assert first element is `history[8]`); len 25 → start 16; (b) leading orphan `tool` message dropped; (c) len ≤ 16 → full list; window never exceeds n+step-1 entries.
5. `tests/test_iter32_gate.py`: update `test_silent_mechanical_round_closes_tool_channel` + `test_forced_speech_empty_finalizes` → forced round now asserts `fake.seen_tools[1]` equals the FULL set (not `[]`) and the messages tail contains "SPEECH ONLY"; add one test with `force_speech_keep_tools=False` asserting the old `== []` behavior. `tests/test_iter30_fast.py`: update window-count expectations to the hysteretic formula (grep `history` assertions in `tests/test_iter31_c3_prefix.py` too and update if they pin counts).
Verification: suite green (206 + 4ish new); unit tests pin the sawtooth; `grep -n "SPEECH ONLY" diallux/graph/builder.py`.
Dependencies: T1.

### T3 — Async prewarm + first-turn-lite
Goal: turn 1 light; turn 2+ and every state entry run on a warm prefix.
Files: `/tmp/opencode/wt-iter43/diallux/graph/llm.py`, `/tmp/opencode/wt-iter43/diallux/graph/builder.py`, `/tmp/opencode/wt-iter43/diallux/config.py`, `/tmp/opencode/wt-iter43/tests/test_iter43_prewarm.py` (NEW), `/tmp/opencode/wt-iter43/tests/test_first_turn_lite.py` (NEW).
Edit spec:
1. `config.py`: `first_turn_lite: bool = False`, `prompt_prewarm: bool = True`, `prewarm_max_completion_tokens: int = 16`.
2. `llm.py` `StreamingLLM.__init__`: also build `self._warm_llm = ChatOpenAI(model=..., api_key=..., max_completion_tokens=settings.prewarm_max_completion_tokens, **same kwargs incl. model_kwargs)`. Add:
   ```python
   async def warm(self, messages: list[dict], tools: list[dict]) -> None:
       """iter43: cache-warm request — identical prefix bytes, minimal output,
       discarded. Best-effort: never raises (caller wraps in create_task)."""
       try:
           await self._warm_llm.bind_tools(tools).ainvoke(messages)
       except Exception as exc:
           import logging; logging.getLogger("diallux.llm").info("prewarm skipped: %s", exc)
   ```
3. `builder.py` `CallRuntime`: `self._prewarmed: set[str] = set()`; `self._warm_tasks: set = set()`:
   ```python
   def warm_prompt_cache(self, state_name: str, history: list[dict] | None = None) -> None:
       """iter43: fire-and-forget prefix warm for `state_name`'s FULL payload shape."""
       if not self.settings.prompt_prewarm or state_name in self._prewarmed:
           return
       try:
           asyncio.get_running_loop()
       except RuntimeError:
           return
       self._prewarmed.add(state_name)
       self._warm_tasks.add(asyncio.get_running_loop().create_task(self._warm(state_name, history or [])))
   ```
   `async def _warm(self, state_name, history)`: resolve kb store; `expand_kb = store is None`; `system = ragmod.strip_kb_markers(self.static_head(state_name, expand_kb))` if store else `self.static_head(...)` — BYTE-IDENTICAL to the state_node path (`builder.py:417-421`); `tools` from the same `_tools_cache`/`build_tool_schemas` path; `messages = [{"role":"system","content":system}] + self._history_window(history, self.settings.history_window, self.settings.history_trim_step)`; `await self.llm.warm(messages, tools)`. In `aclose()`: cancel + await-suppress `self._warm_tasks`.
4. Triggers: (a) `session.py` `start()` — beside `warm_rag()` (~line 170): `asyncio.get_event_loop().create_task(self.runtime.warm_prompt_cache(self._turn_state, self._initial_payload.get("history") or []))` — this warms FULL Intake during the greeting; (b) `builder.py` tool-execution loop where `new_state` is set (~line 669-674, beside the ConfirmSlots `warm_slots_async` call): `runtime.warm_prompt_cache(new_state, <current history snapshot>)` — history snapshot = the history list in scope (only ever appends → snapshot is a prefix of next turn's history).
5. First-turn-lite in `state_node` (after `dvs = ...`, ~line 405): `lite = bool(self.settings.first_turn_lite) and state.get("turn_index", 0) == 1`. When lite: system = general_prompt text (read via the same path as `static_head`: `Path(self.settings.prompts_dir)/"general_prompt.md"`, fallback `self.llm_json["general_prompt"]`) + VOICE_OUTPUT_RULES (only if `tts_voice_rules`); skip the entire RAG block; `tail = ""`; `tools = []`; messages = `[{"role":"system","content":system}] + history_window`. Token streaming/dedupe path UNCHANGED. Guard is `== 1` (never `<= 1`).
6. `tests/test_first_turn_lite.py` (Settings with `first_turn_lite=True`): turn 1 → system contains "Identity" but NOT "Your Mission", `fake.seen_tools == [[]]`, no KNOWLEDGE section; turn 2 → full payload (state prompt + tools present); default Settings (`first_turn_lite=False`) → turn 1 full payload (kill switch). NOTE: default-off is what keeps `tests/test_graph.py` and eval s1 green — do not change those.
7. `tests/test_iter43_prewarm.py`: (a) `warm_prompt_cache("Intake", history)` → FakeLLM saw a request whose system == the full Intake head (with KB markers stripped when a store is injected) and tools == the full Intake tool array; (b) second call same state → NO new request (latch); (c) llm that raises → no exception propagates.
Verification: suite green; new tests pass; `grep -n "warm_prompt_cache" diallux/graph/builder.py diallux/media/session.py` shows both triggers.
Dependencies: T2 (needs the hysteretic window for byte-stable history in warm messages).

### T4 — Offer consent ask (PROMPT-FIRST) + contact_details softening
Goal: Offer ASKS the commitment question ("do you want the live walkthrough/demo?"), the caller's yes lands in history, THEN the model calls `extract_offer_details` — the same prompt-ask → extract-boolean → edge-gate pattern every other state already uses. The date binary is DELETED from Offer (it even contradicted Offer's own Mission line "No dates or times here — those come later"). contact_details never jumps straight into "what's your first name" and never ping-pongs on a declined name.
Files: `/tmp/opencode/wt-iter43/diallux/prompts/Offer.md`, `/tmp/opencode/wt-iter43/diallux/prompts/contact_details.md`, `/tmp/opencode/wt-iter43/agent/llm.json`, `/tmp/opencode/wt-iter43/eval/scenarios/s6_offer_ask_gate.json` (NEW), `/tmp/opencode/wt-iter43/tests/test_iter43_prompts.py` (NEW). NO engine changes (schema.py, tools.py, config knob: none — see the FALLBACK note).
Edit spec — PROMPT PLACEMENT (verified against the live `Offer.md`, unchanged since iter21 `2dc13ff`): the date binary IS current step 1 ("What's better for you — later today or tomorrow?") and the SAME date tail is also in the 2nd refusal (step 3). The consent ask REPLACES step 1 IN PLACE; the date binary is deleted everywhere in this state; scheduling stays with ConfirmSlots.
1. `Offer.md` — REPLACE current step 1 (### 1. The ask (soft, binary) + its date-binary line + the "Binary choice. NEVER <when works for you?>" line) with:
   ```markdown
   ### 1. The ask (commitment — a YES or NO, never a day or time)
   Offer the walkthrough and get an explicit YES or NO in their words. Vary the wording — never read one verbatim twice:
   <Would you like me to walk you through how this works on your numbers?>
   <Want to see it in action? I can show you on a quick live demo call.>
   <Can I show you how this would work for your business? It's a short walkthrough.>
   ONE question, then STOP and listen. NEVER ask for a day or time in this state — scheduling happens later, once their details are in.
   ```
2. `Offer.md` — REPLACE current step 2 ("### 2. If they agree … If they ask a question → answer it with the KBs, then re-ask.") with:
   ```markdown
   ### 2. When they say yes — capture and move
   An explicit yes in their own words (yes / sure / let's do it) → call `extract_offer_details` with {{livecall_agreed}} = true in the SAME response as your reply text, then:
   <Perfect. Let me grab a few details to get you booked.>
   A day answer ("today", "tomorrow") is NOT a yes — they are committing to the walkthrough, not picking a time. If they ask what the walkthrough is → answer briefly with the KBs, then re-ask.
   ```
3. `Offer.md` — in the 3-refusal ladder, REPLACE the 2nd refusal's line:
   `<What's the downside of a 20-minute walkthrough? You see the math on your numbers, you see how it works, and if it's not interesting, we part as friends. Later today or tomorrow?>`
   with:
   `<What's the downside of a 20-minute walkthrough? You see the math on your numbers, you see how it works, and if it's not interesting, we part as friends. Worth 20 minutes of your time?>`
   (3rd refusal already ends in a commitment ask — unchanged.)
4. `Offer.md` — `# Extraction reference` first bullet becomes: "Immediate: {{livecall_agreed}} — call `extract_offer_details` ONLY after the caller explicitly said yes to the walkthrough ask (never on the same response where you asked for the first time)." Keep `# Critical Rules` bullet "Secure commitment to 'this week' — never propose specific days or times" (now actually true), and ADD: "A caller question about WHAT the walkthrough is means they have not agreed — answer, re-ask, wait."
5. `contact_details.md` — above step 1 add:
   ```markdown
   ### 0. Lead-in (always open with this — never jump straight into a data question)
   <Perfect — can I grab a few details to get you set up for the live demo?>
   <Great, let me lock in your demo — just a few quick details.>
   <Awesome. Quick details so I can get the walkthrough on your calendar.>
   ```
   And in step 1 (first name) add the refusal rule:
   ```markdown
   If they decline or hesitate to give a name — ask ONCE: <No problem — what should I
   use as the attendee name for the demo?> Capture whatever they answer as
   {{first_name}} and move on. Never re-ask for a name, never loop the read-back.
   ```
6. `agent/llm.json`: set `states[Offer].state_prompt` and `states[contact_details].state_prompt` to the BYTE-IDENTICAL new file contents (iter40 no-drift lockstep).
7. `eval/scenarios/s6_offer_ask_gate.json` (copy `s1_*.json` structure): step (a) the scripted agent round SPEAKS the consent ask and fires NO tools → expect state stays `Offer`, `tools` does not include `extract_offer_details`; step (b) next scripted round (caller already said "yeah let's do it today") fires `extract_offer_details(livecall_agreed=true)` → expect accepted and dvs `livecall_agreed=True`. HONEST NOTE: with FakeLLM the rounds are scripted, so s6 pins the DESIRED round shape as a regression fixture — the REAL prompt-adherence gate is the T6 live transcript check (#6).
8. `tests/test_iter43_prompts.py`: (a) `Offer.md` contains "walk you through" and does NOT contain "later today or tomorrow" (date binary dead); (b) `contact_details.md` contains "attendee name" and the lead-in; (c) `states[Offer].state_prompt` and `states[contact_details].state_prompt` byte-equal their `.md` files.
FALLBACK NOTE (build ONLY if T6 live calls still capture `livecall_agreed` without an ask — otherwise do NOT build): deterministic py-side gate = server-owned dv `offer_asked` (`schema.py`: `offer_asked: bool = False` field + add `"offer_asked"` to the `SERVER_OWNED_DVS` frozenset at `schema.py:27` so `_exec_extract` hard-rejects model writes, `tools.py:401-403`); module-level `_OFFER_ASK_RE = re.compile(r"walk (you|us|it) through|show you how|see (it|this) (in action|works)|live demo|demo call|20[- ]minute|twenty[- ]minute", re.IGNORECASE)`; the Offer state node (before the LLM stream) sets `dvs["offer_asked"] = any(_OFFER_ASK_RE.search(m.get("content","")) for m in history if m.get("role")=="assistant")` and persists it in `updates["dvs"]`; `tools.py` `_execute_inner` (before the state-tool dispatch) rejects `extract_offer_details`/`offer_completed` with a truthy commit arg while `offer_asked` is False, returning `{"status": "ask_gate_failed", "message": "You have not asked the caller whether they want the live walkthrough/demo yet. First SPEAK the ask, wait for their answer, then capture the commitment."}` (same shape as the iter8 end_call booking-claim gate, `tools.py:237-247`). Gate it on a `offer_ask_gate: bool = True` config knob wired into `ToolExecutor`.
Verification:
```bash
cd /tmp/opencode/wt-iter43 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -c "
import json
a=json.load(open('agent/llm.json'))
for name in ('Offer','contact_details'):
    sp=[s for s in a['states'] if s['name']==name][0]['state_prompt']
    p=open(f'diallux/prompts/{name}.md').read()
    assert sp == p, f'{name} lockstep drift'
assert 'later today or tomorrow' not in open('diallux/prompts/Offer.md').read(), 'date binary still present'
print('lockstep OK')" && \
/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/eval_accuracy.py
```
offline eval = **5/5 original + s6 PASS (6 scenarios)**; suite green.
Dependencies: T3.

### T5 — Speed +0.07 (delivery profiles — the real knob)
Goal: every state speaks ~6.6% faster (1.12/1.05).
Files: `/tmp/opencode/wt-iter43/diallux/media/delivery.py`, `/tmp/opencode/wt-iter43/tests/test_delivery.py`, `/tmp/opencode/wt-iter43/.env`.
Edit spec:
1. `delivery.py` `DELIVERY_PROFILES` cartesia speed: begin 1.05→**1.12**, Intake 1.05→**1.12**, Discovery 1.0→**1.07**, VerifyLead 1.0→**1.07**, contact_details 0.92→**0.99**, ConfirmSlots 1.0→**1.07**, Booking 1.05→**1.12**, Offer 1.08→**1.15**, Closing 0.95→**1.02**, Closer 0.95→**1.02**. ElevenLabs fields UNCHANGED. Update the module docstring rationale line.
2. `tests/test_delivery.py`: update `test_resolve_delivery_cartesia_keys` (Intake `{"speed": 1.12, "emotion": "happy"}`, contact_details `{"speed": 0.99, "emotion": "calm"}`) and the speak-path test asserting `generation_config` (`speed 0.92` → `0.99`). The Offer ElevenLabs assertion (`stability 0.45, style 0.35, speed 1.05`) is EL — unchanged.
3. `.env`: `sed -i 's/^CARTESIA_SPEED=1.05$/CARTESIA_SPEED=1.12/' .env` (unlisted-state fallback only).
Verification: suite green; `grep -n '"speed"' diallux/media/delivery.py` shows the ten new values.
Dependencies: T0 (independent of T1-T4).

### T6 — Relaunch `:8007` + OWNER-DRIVEN live calls (2-3)
Goal: prove it live; capture the T1 telemetry; cancel all bookings.
Commands: the Deploy Rules relaunch block; then the OWNER runs 2-3 calls from the Mac via `http://127.0.0.1:8007/mic` (each ≥ 12 turns if possible, varied speaking styles: one fast/terse, one slow/hesitant with a mid-sentence pause).
Capture (after each call):
```bash
grep -E "turn .* final report|round usage|eager turn started|eager turn cancelled|eot adopted" /tmp/opencode/uvicorn_8007_iter43.log | tail -80
```
Check per call: (1) health ok; (2) `round usage` lines show `cache_read` GROWING past 2688 across turns (T2+T3 win); (3) turn 1 is light (no tools) and fast; (4) `head_start_ms` values present and nonzero; (5) `eager_final_match` true everywhere it appears; (6) consent ask (prompt-first): the agent SPEAKS a consent ask, the caller's yes precedes any `extract_offer_details`, NO empty-text transition before ask+yes; (7) contact_details opens with the lead-in, no name ping-pong; (8) speed audibly faster, read-backs still clear. **Cancel every Cal.com booking** (event 3801235) after each call. Paste the grep output into `research/surgeon/iter43-eot-firstturn/01_telemetry_and_live_calls.md`.
Verification: 2-3 call logs + 01 report on file; zero uncancelled bookings.
Dependencies: T1-T5. **PAUSED for owner testing.**

### T7 — Assess from data → apply EOT winner + window verdict → report + commits + ASK
Goal: every remaining decision made from the owner's call data.
Steps:
1. Aggregate the telemetry (python over the log lines): per-call median `head_start_ms`, resumed (false-start) rate, `eager_final_match` mismatches, `cache_read` curve, turn-1/turn-2 TTFT split, p50/p90 e2e vs the iter42 baseline (p50 1304 / p90 2935).
2. **EOT winner** among A `0.6/0.7/2500` / B `0.4/0.7/2500` / C `0.4/0.8/4000` / D `0.3/0.8/5000` (candidate sets are parameter space ONLY — the choice is from live data, no synthetic probe): apply to `.env` (`DEEPGRAM_EAGER_EOT_THRESHOLD`, `DEEPGRAM_EOT_THRESHOLD`, `DEEPGRAM_EOT_TIMEOUT_MS` — the latter two are `config.py:111-112` defaults today; adding them to `.env` overrides) + mirror in `config.py` defaults. Criteria (pre-registered): median head_start ≥ 200 ms AND false-start ≤ 10% AND zero transcript mismatches AND cancellations not worse than ~3/45 AND e2e p90 improves. None qualifies → keep A, record why (BLOCKED→owner).
   NOTE: if the live head_start under A already reads ≥ 200 ms with ≤10% false starts, no parameter change is needed at all — record that and stop.
3. **History window verdict**: if the `cache_read` curve is flat (hysteresis not holding) → investigate before any raise; if it grows cleanly → try `history_window=32` (`.env` `HISTORY_WINDOW=32`) on ONE follow-up owner call and compare the cache curve + battery-style quality; keep 16 if the gain is marginal.
4. Write `research/surgeon/iter43-eot-firstturn/02_iter43_report.md`: telemetry tables, EOT decision + rationale, cache before/after, TTFT split, consent-ask transcript quotes, speed verification (render one fixed sentence at old/new profile speeds through the TTS path — the 1.12 render must be ~4-8% shorter), suite/eval counts, full path of this plan file.
5. Commits:
```bash
cd /tmp/opencode/wt-iter43 && git checkout -- eval/report.json 2>/dev/null; \
git add -A && git commit -m "iter43: EOT telemetry + cache-prefix fix (hysteretic window, forced-speech keeps tools) + async state prewarm + first-turn-lite + Offer consent ask (prompt-first) + contact_details softening + speed +0.07" && \
/home/julio/projects/clean_diallux_SDR/scripts/keyhound || true
cd /home/julio/projects/clean_diallux_SDR && git add plans/plan_iter43_eot_firstturn_ask.md && \
git commit -m "plan: iter43 telemetry-first EOT + cache prewarm + consent ask (SOP rewrite)" && git push
```
Verification: branch commit exists; plan on main; **STOP and ASK JULIO (LAW 0)** — no merge to `engine/main`.
Dependencies: T6.

## Validation Plan (end-to-end)
1. T0: HEAD `f5c0912`, suite 206.
2. T1: no behavior change; suite 206; telemetry lines appear in the live log at T6.
3. T2: hysteresis unit tests pin start-jumps at len 17/25; suite green; iter32/iter30 test expectations updated coherently.
4. T3: prewarm tests (bytes, latch, swallow); lite tests (payload, turn-2 full, kill switch); suite green.
5. T4: lockstep check passes; "later today or tomorrow" absent from Offer.md; offline eval 6/6 (5 original + s6); prompt-shape tests 3/3; suite green.
6. T5: delivery tests updated; suite green.
7. T6: 2-3 owner calls logged; `cache_read` grows past 2688; consent ask visible in transcript; bookings cancelled.
8. T7: EOT winner applied (or A kept with recorded reason); window verdict recorded; report written; commits on branch + main; ASK JULIO.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Postgres conversation memory (embed conv + retrieve) | REJECTED on 4 axes (hot-path 156-277ms, verbatim-exactness loss, prefix-cache destruction, non-problem at 2-6k tok) — see Resolved Decisions |
| Cross-call prospect memory (Postgres) | Different feature (remembering a prior call's prospect); owner-gated separate iteration |
| `LANGGRAPH_CHECKPOINT=postgres` flip | Durability feature for multi-worker deploys; not latency; owner gate |
| Deterministic regex ask-gate (fallback) on the py side (`offer_asked` server-owned dv + `_OFFER_ASK_RE` + executor rejection) | FALLBACK ONLY — full design archived in the T4 note; build ONLY if T6 live calls still capture `livecall_agreed` without the ask having been spoken. Prompt-first ships instead: every state already runs prompt-ask → extract-boolean → edge gate |
| `transition_to_*` added to `_MECHANICAL_RE` (force-speech on empty-text transition rounds) | Empty-text transition suppression itself remains open — revisit if live calls still show empty-text transitions AFTER the consent ask + yes |
| Intake-extract timing (s1/s3/s4 live-eval 1/5; Gene/Brenda stalls) | Separate prompt-retraining variable — iter44 candidate; NOTE first-turn-lite (live-only, default-off) does not affect eval which runs with default Settings |
| `history_window` 16→32 beyond the T7 data check | Data-gated decision inside T7 only |
| Battery root-causes (mock number pollution, name-refusal loop beyond the new attendee-name rule) | Owner said "nah we are good" |
| gpt-5.4 raw TTFT floor (model swap) | Outside engine control; owner decision |
| iter42 merge to `engine/main` | Separate owner gate, unchanged |

Plan file: `/home/julio/projects/clean_diallux_SDR/plans/plan_iter43_eot_firstturn_ask.md`
