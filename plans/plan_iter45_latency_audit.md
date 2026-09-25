# PLAN — iter45: latency audit iter42→44 — find the sub-1s recipe, repeat it on every state change

## Meta
- Date: 2026-09-11
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Worktree under audit: `/tmp/opencode/wt-iter44` (branch `engine/iter44-cache-floor`, HEAD `68541f7` + uncommitted iter44 work + this session's telemetry/appends)
- Scope: one session — AUDIT ONLY. Inventory every live call since iter40, find the ~700 ms
  first-response record and exactly which build/config produced it, diff the hot path
  iter42→43→44, quantify the cache/tool-state-block re-bill, and deliver proposals (NO code
  changes in this session) to reach: **first response < 1,000 ms and p90 e2e < 1,000 ms**.
- Status: PLAN ONLY (awaits approval)

## Compaction Context (session state as of 2026-09-11 ~08:00 UTC)

### The owner's goal (verbatim intent)
- First response (and every turn) must feel sub-1-second: **< 1,000 ms on ~90% of turns,
  especially the FIRST response**. iter42's low end was "phenomenal" (best turns ~1,076-1,270 ms
  e2e, STT-EOT→first-token 823-1,005 ms; owner remembers "700 ms"). iter42's p50 (1,304) was
  "conflated" by terrible p90s (2,935; max 3,758) — the tail, not the floor, made it look bad.
- iter44 is a BETTER AGENT (RAG correctness, industry chunks, append-only cache fix) but WORSE
  on felt latency ("way worse" per owner) — must audit why between iter42→43→44 latency regressed.
- The intended iter43 fix (silent async OpenAI call at greeting + every state transition that
  pre-populates the destination state's cache so the next reply rides it) is the design whose
  full promise is still unmet.
- Also audit the "tool cache burn/flush": per-state tool arrays bust the prefix at every state
  transition (tools render FIRST in the OpenAI request). Owner wants smart handling — more
  cached tokens (they're cheap) if it kills the re-bill.
- Deliverable: an audit report + proposals. Owner decides; fixes land in a LATER session.

### Current live infrastructure (as left by the previous session)
- `:8007` = iter44 build, PID **3152652**, worktree `/tmp/opencode/wt-iter44`, launched with
  `.env` sourced (Langfuse ON), log APPENDS to `/tmp/opencode/uvicorn_8007_iter44.log`.
  Config state: `first_turn_lite=True` (code default, owner-approved),
  `rag_append_delta=True`, `openai_verbosity="medium"` (owner changed TODAY from low —
  suspected +150-250 ms/turn), `openai_reasoning_effort="none"`, model gpt-5.4,
  cartesia_speed 1.12, deepgram flux eager EOT (threshold 0.6).
- `:8008` = iter42 build, PID **3166619**, worktree `/tmp/opencode/wt-iter42` @ `f5c0912`
  (the "almost working" branch), verbosity=low (its config default), no lite, no append-only,
  no TTFT telemetry, mic bridge without heartbeat.
- Julio tunnels: `ssh -N -L 8007:127.0.0.1:8007 julio@46.62.233.228` (and an old `8006` tunnel
  PID 2536589 exists — do not kill).
- Mic-bridge path: browser AudioWorklet sends 1,600-sample (100 ms) PCM chunks over
  `/mic/ws` → `session.on_media` → Deepgram flux. `on_media` now logs a heartbeat
  ("mic audio FIRST chunk received" / "flowing: N chunks" every 100 chunks) — added this
  session to diagnose two "stuck" calls.
- Two "stuck" live calls (84a3c67127ae on :8007 old PID, and one later) were NOT latency:
  **zero mic audio reached the server** (trace had only the root span; zero STT events;
  greeting played fine = downstream OK). Mac/browser/tunnel upstream — not engine.

### Live-call evidence inventory (the raw material for T1/T2)
| Call | Trace | When | Build | Turn reports | Key numbers |
|---|---|---|---|---|---|
| iter42 live | `44866edbea1d` (Langfuse) + `research/surgeon/iter42-dedupe-window/03_live_call_assessment.md` | 2026-09-10 ~07:45 | wt-iter42 `f5c0912`, verbosity=low | 45 | e2e p50 **1,304** / p90 2,935 / max 3,758; STT→first p50 1,202; best turns 1,076-1,270 e2e; 13 turns >2s; 2 >3s |
| iter43 live | `de9d47732ad2` (call `532d92727e0f`) | 2026-09-10 23:30 | wt-iter43 pre-`374318b` (16.5k lite bug) | report: `research/surgeon/iter43-eot-firstturn/01_telemetry_and_live_calls.md` | e2e p50 **1,939** / p90 3,269; STT→first p50 1,870; turn2 cold 1,870; transition 3,052 |
| iter44 live #1 | micbridge trace `micbridge-e175b32d80cc` MISSING (tracer was disabled — launch error), but server log survived pre-overwrite only partially | 2026-09-11 07:31 | wt-iter44 WITHOUT `.env` sourced | 8 turns (captured in session chat) | TTFT 727-1,150 (verbosity=LOW); e2e 1,041-1,830; turn 8 outlier 3,699 |
| iter44 live #2 | `micbridge-84a3c67127ae` | 07:36 | wt-iter44 WITH `.env` sourced | 1 (root only) | STUCK — zero mic audio (Mac-side), no LLM rounds |
| iter44 live #3 | `micbridge-cce5691cb6ef` | 07:42-07:45 | wt-iter44, verbosity=**medium** | 13 gens / 9 eff. turns | TTFT p50 **1,019** (854-1,389); e2e response 1,327-2,025; cache_read 2,688 constant; 2 barge-ins; transcript: owner testing latency, wants 1,000 ms |
- Langfuse: self-hosted `:3001` v3.172.1; keys in `/tmp/opencode/wt-iter44/.env`
  (`LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`). Traces listable via the langfuse 4.15.1 SDK
  (`lf.api.trace.list(limit=N)`); micbridge traces named `micbridge-<callid>`;
  battery traces named `llm2llm-graph-<slug>`.
- TTFT telemetry (added this session): every Langfuse GENERATION carries
  `usage_details.ttft_ms` = time to FIRST SPOKEN token (tool-only rounds have none).
  Server log per-round line: `round usage: turn=N state=S input=I cache_read=C output=O ttft=Tms`.
- Per-turn media budget (session reports): `stt_eot_to_llm_first_ms`, `llm_first_to_tts_first_ms`,
  `tts_first_to_audio_out_ms`, `e2e_response_ms`, `e2e_turn_ms`, `eager`, `head_start_ms`,
  `barge_in`, `resumed_count` — in `/tmp/opencode/uvicorn_8007_iter44.log` (APPEND-mode since
  07:42; earlier content was LOST by a truncating relaunch — do not relaunch with `>` again).

### What the hot path looks like today (iter44 + this session)
- Layout `[tools][static head][frozen STATE-BLOCK tail][history][delta?]`
  (`_build_messages`, builder.py ~418). Tools render FIRST → cache keys on tools first.
- Knowledge (RAG) tail frozen per state-visit (`_frozen_rag_tail`); drift re-retrievals append
  a DELTA system block AFTER history (`rag_append_delta=True`) — prefix stable, delta re-bills.
- `frozen_state_block` freezes the dvs STATE-BLOCK **per TURN** (iter40 C3). Every turn's
  `extract_*` dvs writes change the block → next turn busts the prefix right after the head
  → this is why cache_read is pinned at 2,688 (tools+head) today. THE known remaining buster;
  fix (freeze per STATE VISIT, dvs reach model via history) needs owner OK — behavioral change.
- Silent prewarm: `warm_prompt_cache(state)` + `warm_rag_async(state)` fire on every ok
  transition (builder.py ~1042-1047) and at greeting (session.start). `prompt_prewarm=True`,
  warm = byte-exact full payload, `max_completion_tokens=16`, output discarded, bg task.
  Evidence it works when it wins the race: today's entries rode 3,712 cached on
  Closer/contact_details/ConfirmSlots entries (battery lite run 06:43).
- Lite turn 1: `first_turn_lite=True` (owner flipped default ON today); turn 1 = general prompt
  + VOICE_OUTPUT_RULES only (~1,650 tok), tools channel opens turn 2.
- iter42 (the "phenomenal" low end) had NONE of: lite (default OFF then), append-only delta,
  TTFT telemetry, transition prewarm consumption, verbosity medium. It ran verbosity=low.
- Verbosity today = medium (owner call): turn-1 TTFT went 727→1,248 ms between the two live
  calls of today (only env-level change) — ~+150-250 ms/turn suspected.

### iter42→43→44 timeline (the audit skeleton)
1. **iter42** (`engine/iter42-dedupe-window` @ `f5c0912`): best low-end latency on record;
   bugs: empty-speech transition rounds, in-turn double-speak (fixed by dedupe window),
   cache stuck at 2,688 (tail-after-history — SAME as today), 13/45 turns >2s.
2. **iter43** (`engine/iter43-eot-cache-askgate`): the INTENDED latency fixes — hysteretic
   history window, forced-speech keeps tools, silent prewarm (greeting + transitions),
   first-turn-lite, EOT telemetry, Cartesia speed +0.07. Live call proved WORSE (1,939 p50)
   because of 3 bugs: lite head 16.5k tok (kb=True bug), prewarm shape mismatch, tail-after-
   history cache bust. Fix `374318b` (lite kb=False → 1,648 tok) ADOPTED into iter44.
   iter43 tagged `iter43-failed`.
3. **iter44** (`engine/iter44-cache-floor`): T1 byte-exact prewarm, T2 session-start store
   resolve, T3 tail-before-history, T6a embed-once, T6b transition RAG prefetch,
   T6c drift re-retrieval (industry chunks FIXED — 11/13 battery calls), T4 inline guard.
   Battery 12/13. Latency: in-process p50 1,332-2,265; live today 1,327-2,025.
4. **This session (still uncommitted on iter44 branch)**: TTFT telemetry, append-only delta,
   prefetch latch removal (re-stage every transition), lite default ON, verbosity medium
   (owner), mic heartbeat. Suite 242/242, eval 6/6.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| AUDIT ONLY — no code changes in iter45 session; fixes are proposals for owner | Owner: "Don't code, just analyze… new session, new plan, then proposals" |
| The latency target is p90 < 1,000 ms (not p50) — "below 1,000 on 90% of conversations, especially the first" | Owner words; p50 averages hide the tail (his iter42 complaint) |
| iter42 is the latency REFERENCE build, not the code base | Owner: iter42 "had a lot of bugs"; we take its latency recipe, not its code |
| iter44's correctness gains stay (industry chunks, append-only, lite) | Owner: "iter44 is better as a sales agent" — we do NOT roll back to iter42 |
| The verbosity=medium change is SUSPECT #1 for the felt regression; the audit must verify the per-round distribution (iter42: MOST rounds sub-1,000 incl. cache=0 rounds at 887-1,010; only its ceiling was bad) before proposing revert | Owner changed it today; iter42 ran low; measured turn-1 delta 727→1,248 ms |
| All live-call evidence pulled from Langfuse + append-mode uvicorn logs; never relaunch a server with `>` (truncates history) | Lost the 07:31 call log + transcript this way already |
| Never touch `:8000-:8005`, live Retell agent IDs, `slots.db`, Cal.com event 3801235 | AGENTS.md LAW 6 / deploy rules |
| Mic "stuck" calls are OUT of scope (upstream audio, Mac/browser) unless the audit shows engine involvement | Trace `84a3c67127ae` = zero audio arrived; heartbeat now proves flow |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| The exact call that produced a ~700 ms first response (owner memory) — candidates: iter42 call `a76f7d57bbc6` best turns, iter21-era gpt-5.2 cached rounds (843-952 ms), or an un-inventoried micbridge call | T1/T2 inventory of ALL Langfuse traces (limit=200, from 2026-09-09) + all `/tmp/opencode/uvicorn_*8007*.log` files + `research/surgeon/iter4*/` reports |
| Whether "under 1,000" in owner's memory meant e2e_response or LLM-only | Audit tables compute BOTH from turn reports + gens |
| Whether tool-schema unification (shared tool prefix across states) is acceptable to the prompt architecture | Owner decision after T5 quantifies the per-transition re-bill |
| Whether to accept state-block freeze per state VISIT (dvs via history only) | Owner decision after T5/T6; changes model read-back behavior |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter44/.venv/bin/python` (3.12); langfuse SDK 4.15.1;
  langchain-openai 1.6.0; model gpt-5.4 (reasoning_effort="none", verbosity low↔medium).
- Langfuse `http://localhost:3001` — env: `set -a; . /tmp/opencode/wt-iter44/.env; set +a`.
- Extraction scripts (reuse): `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter44-cache-floor/extract_summary.py`,
  `extract_langfuse.py` (battery traces). NEW per-call script for this audit goes in
  `research/surgeon/iter45-latency-audit/` (gitignored — never commit).
- Servers: `:8007` iter44 (PID 3152652, append log `/tmp/opencode/uvicorn_8007_iter44.log`),
  `:8008` iter42 (PID 3166619, log `/tmp/opencode/uvicorn_8008_iter42.log`).
  Restart pattern (NEVER `>`): `setsid nohup .venv/bin/python -m uvicorn diallux.app:app
  --host 127.0.0.1 --port <PORT> >> <LOG> 2>&1 < /dev/null & disown` with `.env` sourced.
- OpenAI TTFT/probe: the audit reads usage_details + trace timestamps; NO new OpenAI spend
  beyond optional 1-2 verification live calls by owner.
- Postgres 5434 (RAG pgvector) read-only; Langfuse :3001 read via SDK only.

## Architecture (one block)
```
EVIDENCE SOURCES                                AUDIT                    OUTPUT
Langfuse :3001 ──micbridge-* traces (4 calls)──┐
uvicorn_8007_*.log (append, per-turn reports)  ├→ T1 inventory: per-call per-turn table
uvicorn_8008_iter42.log (iter42 live build)    │   (STT-EOT→first / TTFT / LLM→TTS / e2e)
research/surgeon/iter42…/03_live_call…md       │
research/surgeon/iter43…/01_telemetry…md       ▼
ITERATIONS.md ledger                      T2 fastest-first-response census
                                          (find the ~700ms record + its build/config)
                                          ▼
                                          T3 hot-path diff iter42→43→44 (git + code read)
                                          — every hot-path change, latency-tagged
                                          ▼
                                          T4 first-round anatomy (what fires, what races)
                                          + T5 cache/tool re-bill quantification
                                          ▼
                                          T6 REPORT + proposals (P1..Pn) → ASK owner
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter45-latency-audit/01_report.md` | the audit report: inventory, fastest-first-response recipe, hot-path diff, cache/tool re-bill, proposals | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter45-latency-audit/extract_live_calls.py` | per-call turn-report extractor (Langfuse + uvicorn logs → one latency table) | NEW |
| `/tmp/opencode/uvicorn_8007_iter44.log` | READ ONLY evidence (append-mode; do NOT relaunch with `>`) | read |
| `/tmp/opencode/uvicorn_8008_iter42.log` | READ ONLY evidence | read |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter42-dedupe-window/03_live_call_assessment.md` | READ ONLY (iter42 baseline table) | read |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter43-eot-firstturn/01_telemetry_and_live_calls.md` | READ ONLY (iter43 audit) | read |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter45_latency_audit.md` | this plan | NEW |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | NO change this session (analysis only) | read |

## Deploy Rules
- ANALYSIS ONLY. No engine code changes, no branch ops, no merges, no commits.
- Servers stay AS-IS: `:8007` (iter44) and `:8008` (iter42) both running; do NOT kill/relaunch
  either unless a task requires it, and then ONLY with `>>` (append) logs and `.env` sourced.
- Re-pull evidence command pattern:
  ```bash
  cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && \
    .venv/bin/python /home/julio/projects/clean_diallux_SDR/research/surgeon/iter45-latency-audit/extract_live_calls.py
  ```
- NEVER touch: `:8000/:8001/:8002/:8003/:8005/:8006` (julio's tunnel), live Retell agent IDs
  (`agent_f305…` sdr, `agent_1698…` heating, `agent_87e4…` chat), `slots.db`, Cal.com event
  3801235, Langfuse server itself.

## Tasks (in order)

### T1 — Live-call inventory (every call, every turn)
Goal: one table per live call: turn, STT-EOT→LLM-first, TTFT (spoken), LLM→TTS, TTS→audio,
e2e_response, e2e_turn, cache_read, state, eager/barge/resume flags.
Sources: Langfuse traces (`micbridge-*`, the 2026-09-10 untitled traces `44866edbea1d`,
`de9d47732ad2`, any others — `limit=200` from 2026-09-09), the two append logs, and the two
surgeon reports (iter42/iter43 baselines already tabulated).
Commands:
```bash
cd /tmp/opencode/wt-iter44 && set -a && . ./.env && set +a && \
  .venv/bin/python /home/julio/projects/clean_diallux_SDR/research/surgeon/iter45-latency-audit/extract_live_calls.py
grep -E "turn .* report|round usage" /tmp/opencode/uvicorn_8007_iter44.log | head -100
```
Dependencies: Langfuse up (`scripts/lf.py health`), `.env` sourced.
Verification: every live call has a table; zero trace-fetch errors; iter42's 45 turns and
iter44's 13 turns reproduced to match the surgeon reports.

### T2 — Find the fastest first response + the ~700 ms record
Goal: identify the fastest FIRST-response turn and the fastest steady-state turns across ALL
calls; pin the exact build/config that produced each (worktree, verbosity, lite, prewarm state,
provider cache warmth). Owner remembers ~700 ms — find it or prove the floor was ~800-850.
Commands: from T1 tables, rank all turns by e2e_response and by TTFT; for each top-5 fastest,
pull the generation's input tokens + cache_read + the server log line for that timestamp.
Verification: one "recipe" row: build/config → measured first-response; min TTFT and min e2e
named per call with trace IDs.

### T3 — Hot-path diff audit iter42→43→44
Goal: every change touching the per-turn hot path, tagged with measured/suspected latency
impact and its evidence.
Commands:
```bash
cd /home/julio/projects/clean_diallux_SDR && \
  git diff engine/iter42-dedupe-window engine/iter44-cache-floor -- diallux/graph/ diallux/media/session.py diallux/config.py > /tmp/opencode/iter45_hotpath.diff
```
Then read the diff against: (a) verbosity low→medium (config.py:42), (b) lite default flip,
(c) append-only delta block (extra system message per drift round), (d) prefetch latch removal
(more bg embeds during conversation), (e) drift re-query embeds on the hot path
(~100-300 ms when drift fires), (f) TTS handoff (llm_first_to_tts_first 80-250 ms — check
sentence-gate flush threshold at medium verbosity), (g) the state-block per-turn re-freeze.
Dependencies: T1 (numbers), both worktrees checked out at known commits.
Verification: a table in the report — change → file:line → latency direction → evidence.

### T4 — First-round anatomy (the "two requests at once" complaint)
Goal: reconstruct, second by second, what fires between call start and first spoken reply:
greeting prewarm `warm()` (NOT traced in Langfuse — visible only in server log httpx lines),
RAG staging embed, lite round, and whether any of it blocks the first caller round.
Commands: server logs around call starts (`84a3c67127ae`, `cce5691cb6ef`, `e175b32d80cc`) +
Langfuse gen start times + trace root span.
Verification: a timeline for each call showing request start → embeddings → chat → first
token → TTS → audio, naming each gap; verdict on whether the first reply ran ONE round or TWO
in parallel (owner observed "running two at a time").

### T5 — Cache/tool re-bill quantification
Goal: for one battery call and one live call: per state transition, how many tokens re-bill
(tools array change + head change + state-block change), and what the TTFT cost of a full
uncached prefill is vs cached (use today's matched-output data: cache≈0 latency benefit
measured 856 vs 942 ms — restate with the new TTFT telemetry).
Commands: reuse `extract_summary.py` pattern against `langfuse_summary.json` + the new
extractor; grep `tools` block sizes from `agent/llm.json` per state.
Verification: a table: transition → tokens re-billed → measured TTFT delta.

### T6 — Report + proposals + ASK
Goal: `research/surgeon/iter45-latency-audit/01_report.md` with (a) the full inventory tables,
(b) the ~700 ms recipe (or its floor), (c) hot-path diff verdicts, (d) first-round anatomy,
(e) cache re-bill table, and (f) PROPOSALS with expected ms impact each:
  P1 verbosity low (revert today's change; recover ~150-250 ms/turn)
  P2 state-block freeze per STATE VISIT (dvs via history; the monotonic cache climb)
  P3 prewarm hardening (greeting-prewarm AFTER store resolve + shape-match asserted;
     transition prewarm awaited with a bounded wait ~50-100 ms at entry when not ready)
  P4 tool-prefix strategy (canonical/shared tool ordering across states so transitions keep
     the tools prefix — needs prompt/tool schema layout decision)
  P5 eager-EOT threshold tuning (0.6 → earlier speculative start, at false-EOT risk)
  P6 mic-bridge 100 ms chunk → 40-60 ms (upstream felt-latency trim, browser file only)
Then ASK JULIO which proposals become iter46.
Dependencies: T1-T5.
Verification: report exists with all sections; each proposal has an expected-impact estimate
and a revert switch; explicit ASK at the end.

## Validation Plan (end-to-end)
1. T1: every live call inventoried; tables match the two surgeon reports.
2. T2: the fastest first-response record named with its exact build/config.
3. T3: every hot-path diff item tagged with evidence; no speculation without numbers.
4. T4: first-round timeline reconstructed for ≥2 calls; the "two requests" question answered.
5. T5: cache re-bill quantified with token counts.
6. T6: report + proposals delivered; NO code touched; servers untouched (or restarted ONLY
   with append-mode logs).
7. NO merges, NO commits, NO live agent changes.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Implementing any latency fix (P1-P6) | Needs owner decision after the audit; separate session/branch `engine/iter45-*` or `iter46-*` |
| The two "stuck" mic calls (zero audio) | Mac/browser-side input; the heartbeat now detects it; fix the browser page only if the audit's T4 shows server-side contribution |
| dvs state-block freeze implementation | Owner decision inside the audit proposals (P2) |
| iter44 branch commit/cleanup | Stacked telemetry work remains uncommitted by design until owner reviews |
