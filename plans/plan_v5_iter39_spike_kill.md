# PLAN — v5 iter39: full OTEL + conversation analysis → spike-kill (flat ≤1.2s e2e)

> **STATUS 2026-09-09: T0–T2 DONE** (evidence frozen + analysis report `01_analysis_call_1480fbd1f29d.md` + owner verdict presented).
> **T3–T5 SUPERSEDED by `plans/plan_v5_iter40_spike_readback.md`** (branch `engine/iter40-spike-readback`; adds the 9/10 endpoint + noon/2pm-loop fixes; L1 dropped per evidence).

## Meta
- Date: 2026-09-09
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Branch: `engine/iter39-spike-kill` ← `engine/iter38b-gpt54` (=`engine/iter38-memory-latency-fix`, head `491a7a3`)
- Scope: FIRST a full OTEL/Langfuse + conversation analysis of the live 2026-09-09 gpt-5.4 call; THEN owner-presented verdict; THEN latency fixes (design adapts to the analysis).
- Status: PLAN ONLY (not started — awaits approval; owner wants the analysis done IN this session, not before)

## Compaction Context
- Project: Dialux SDR voice engine ("Linda"), LangGraph 9-state pipeline (Intake → Discovery → Closer → Offer → contact_details → ConfirmSlots → VerifyLead → Booking → Closing), Deepgram Flux STT → graph → gates → Cartesia TTS (sonic-3.6, Linda voice `829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30`).
- Doctrine: `/home/julio/projects/clean_diallux_SDR/AGENTS.md` (LAW 0: code = plan → branch `engine/iterNN-<slug>` → suite green → report → ASK Julio; docs straight to main; never touch :8001/:8002/:8003/:8000; live services read-only; Cal.com event 3801235 REAL — cancel test bookings).
- Plan SOP: `/home/julio/projects/new_plan_sop.md` (this plan follows it; plans live in `/home/julio/projects/clean_diallux_SDR/plans/`).
- **iter38 is DONE and verified LIVE** (branch `engine/iter38-memory-latency-fix`, head `491a7a3`; fork `engine/iter38b-gpt54` = same commits, only `.env` `OPENAI_MODEL` differs):
  - F1 eager-adopt on EOT (PT-33) · F2 `_late_turn_report` NameError fix · F3 cap = **64 turns / 600s** (Julio-tuned after a 24-cap killed a healthy 5-min call; `_cap_hit()` + `_graceful_cap_close()` in session.py) · F4 idempotent user-append in `ingest` (builder.py) · F5 barge_in carry across clock swap · F6 `t_audio_out` stamped in ws writer. Tests: `tests/test_iter38_turn_lifecycle.py` (8). Suite: **162 passed**.
  - Surgeon docs: `research/surgeon/iter38-memory-latency-fix/01–04*.md`.
- **Model A/B verdict (2026-09-09, owner-approved):** gpt-5.2 TTFT 2.7–8.4s (reasoning-serving floor + OpenAI variance, PT-40) vs **gpt-5.4 thinking-off (`reasoning_effort=none`, config default) ≈ 0.9–1.1s flat**. gpt-5.4 stays. `verbosity=low` on both (config defaults; no env overrides).
- **The assessed call (iter38b, gpt-5.4):** call `1480fbd1f29d`, Langfuse trace `ecbc42943d42`, :8007, 11:14:45→11:24:45 (600.2s). 47 real turns / 58 indexes; 10-min cap fired with graceful close (`session:turn_cap_close` span in trace). Julio verdict: "much better, still a disaster" → e2e p50 **1413ms** but ~6 spike turns **3.5–6.9s**.
- Latency anatomy so far (evidence, not yet fully analyzed): prompt cache **58% hit** (159.9k/274.6k tokens, 53/63 gens) — spikes are NOT cache misses; each LLM trip pays ~1.0s TTFT; spike turns ran **2–3 LLM trips** (tool round + speech round); state-entry turns pay a ~0.9s **RAG embedding before the LLM** (`chat/completions → embeddings → chat/completions` pattern); `query_livecall_slots` webhook **1.7–2.5s synchronous** inside the turn (×4 in the call, one returned `no_start_time` error when the model omitted `slot_target_date`).
- Conversation facts already visible in the trace tools (for the analysis to weigh): `transition_to_ConfirmSlots` gate_failed once (`missing: callback_number`), `set_callback_number` returned `wrong_number` ("the one i'm calling from" not 10-digit) then ok on retry; contact_details consumed ~12 turns; ConfirmSlots consumed ~12 turns / 4 slot queries; phaseb booking chain did NOT run in this call (no booking — cap closed the call first at 10 min).
- **EVIDENCE FROZEN** (this session, before the new one starts):
  - `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter39-spike-kill/otel_observations_ecbc42943d42.json` (223 observations: 128 spans, 63 GENERATION, 32 TOOL)
  - `.../uvicorn_8007_iter38b_call_1480fbd1f29d.log` (full server log, 45KB — SOURCE OF TRUTH on conflict; Langfuse ingest ~25% loss)
  - `.../uvicorn_8006_iter38_call_66bd7b0c7726.log` — **LOST (316 bytes; restart clobbered it). gpt-5.2 A/B turn reports survive only in session notes: turns 7–13 e2e = 3017/5409/3190/3309/4152/8856ms — treat as reconstructed-from-chat, flag it in the report.**
- Servers live RIGHT NOW: :8006 = wt-iter38 (gpt-5.2) pid 2583249; :8007 = wt-iter38b (gpt-5.4) pid 2583320; :8005 = OLD iter37 build pid 2099198 (leave); :8000 pid 2659243 (leave). Server launch pattern (plain nohup dies with the shell): `cd <worktree> && set -a && . ./.env && set +a && setsid nohup /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 80NN > /tmp/opencode/uvicorn_80NN.log 2>&1 < /dev/null & disown`.
- Tooling: `engine/scripts/lf.py` (health/traces/show/gens/tools/usage), `scripts/lf_eval.py ladder`, opencode skills `langfuse-call-analysis` (MUST load) and `sop_call_analysis`. Langfuse `http://localhost:3001`; tracer reads `os.environ` — export env before launching servers (iter38 lesson: untraced otherwise).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Model = gpt-5.4, thinking off | Live A/B 2026-09-09: 0.9–1.1s flat vs gpt-5.2 2.7–8.4s |
| Turn cap = 64 turns AND 600s (whichever first) | Julio order after the 24-cap killed a healthy call |
| Analysis FIRST, fix design SECOND | Julio: "full OTEL analysis and conv on a new plan" — fixes must cite the analysis |
| No prompt text / KB / RAG-scoring changes | One variable: latency structure |
| Prefetches must be stale-safe (webhook re-fetch fallback) | Correctness > latency |
| Evidence lives in `research/` (gitignored); reports go to `research/surgeon/iter39-spike-kill/` | AGENTS.md zone rules |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Julio's approval of the analysis verdict BEFORE fixes are coded | Owner gate (LAW 0) |
| Julio's ear-witness account of the 10-min call (what felt "disaster" besides spikes) | Ask Julio in-session |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12; langgraph 1.2.11, langfuse 4.15.1, httpx, fastapi)
- Worktree to create: `/tmp/opencode/wt-iter39` of branch `engine/iter39-spike-kill`; then `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter39/.venv`; `cp /tmp/opencode/wt-iter38b/.env /tmp/opencode/wt-iter39/.env`
- Suite: `cd /tmp/opencode/wt-iter39 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests` (baseline 162 passed)
- Battery: `cd /tmp/opencode/wt-iter39 && set -a && . ./.env && set +a && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf_eval.py ladder` (requires the `ROOT/.venv` symlink, as in iter38)
- pgvector KB store: docker `diallux-db` :5434 (`DATABASE_URL` in `.env`)
- Langfuse: `http://localhost:3001` (docker: langfuse-web/worker/clickhouse up; verified 2026-09-09)

## Architecture (one block diagram)
```
Mac Chrome /mic ──ssh tunnel──▶ :8007 (wt-iter39, gpt-5.4)
   16k PCM ─▶ Deepgram Flux ─▶ adopt-EOT ─▶ graph.astream ─▶ trips×LLM(gpt-5.4, cache 58%) ─▶ Cartesia TTS ─▶ ws
                                   │              │
                                   │  RAG tail (~0.9s embed on state entry)  ◀── suspect #1
                                   │  query_livecall_slots (~1.7–2.5s sync)  ◀── suspect #2
                                   │  multi-trip turns (tool round + speech) ◀── suspect #3
                                   └── Langfuse :3001 trace micbridge-<sid>  + uvicorn_8007.log
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter39-spike-kill/01_analysis_call_1480fbd1f29d.md` | FULL OTEL + conversation analysis verdict (turn table, per-stage p50/p90/max, per-turn trip counts, RAG/embed timeline, tool latency table, transcript with user-experience annotations, ranked spike causes with evidence) | NEW |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter39_spike_kill.md` | §Tasks re-locked after the analysis verdict (fix list may shrink/grow; one variable preserved) | EDIT |
| `/tmp/opencode/wt-iter39/diallux/graph/builder.py` | fixes per verdict (candidates: L1 RAG prefetch on transition; L3 one-trip routing for successful transitions) | EDIT |
| `/tmp/opencode/wt-iter39/diallux/graph/tools.py` | L2 slots prefetch candidate (background warm + stale-safe fallback) | EDIT |
| `/tmp/opencode/wt-iter39/diallux/config.py` | kill-switch flags (`rag_prefetch`, `slots_prefetch`) | EDIT |
| `/tmp/opencode/wt-iter39/tests/test_iter39_spike_kill.py` | regression tests per fix | NEW |
| `/tmp/opencode/wt-iter39/notes.md` | verdict lines per task | EDIT |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | iter39 ledger line | EDIT |

## Deploy Rules
- Branch/worktree per Environment; suite green after EVERY task; commit per task on `engine/iter39-spike-kill`.
- Live test ONLY on :8007 with the launch pattern in Compaction Context (env exported → otherwise untraced). Julio tunnels from his Mac: `ssh -N -L 8007:127.0.0.1:8007 julio@46.62.233.228`.
- Copy any live log BEFORE restarting a server (iter38 lesson: restart clobbers the log).
- NEVER touch :8001/:8002/:8003, :8005 (pid 2099198), :8000 (pid 2659243), production agents (`agent_f305…`, `agent_1698…`, `agent_87e4…`); cancel every test booking (event 3801235 REAL).
- No merges without Julio's explicit say-so.

## Tasks (in order)

### T0 — Evidence freeze (DONE in the planning session — verify, don't redo)
Goal: confirm the frozen evidence is intact.
Files: the three files under `research/surgeon/iter39-spike-kill/` (paths in Compaction Context).
Commands (full):
```bash
cd /home/julio/projects/clean_diallux_SDR/research/surgeon/iter39-spike-kill && wc -c otel_observations_ecbc42943d42.json uvicorn_8007_iter38b_call_1480fbd1f29d.log uvicorn_8006_iter38_call_66bd7b0c7726.log
set -a && . /tmp/opencode/wt-iter38b/.env && set +a && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py health
```
Verification: JSON >500KB, 8007 log >40KB with 47 "final report" lines, Langfuse server OK. (8006 log = 316 bytes, expected — LOST, flag in report.)
Dependencies: none.

### T1 — Full OTEL + conversation analysis of call `1480fbd1f29d`
Goal: one verdict report that explains EVERY second of the 10 minutes and names the ranked spike causes with line-level evidence.
Files: `research/surgeon/iter39-spike-kill/01_analysis_call_1480fbd1f29d.md`.
Commands: load skill `langfuse-call-analysis`; parse the frozen JSON + 8007 log with python (same scripts as iter38 autopsy). MUST produce:
1. Turn table (47 rows): index, timestamps, user text (from gen inputs), agent text, state, trip count, tools fired with ms, e2e/stage metrics.
2. Per-stage p50/p90/max (`stt_eot_to_llm_first_ms`, `llm_first_to_tts_first_ms`, `tts_first_to_audio_out_ms`, `e2e_response_ms`) vs the iter38b baseline (p50 1413ms).
3. Spike-turn dissection (6 turns, 3.5–6.9s): exact trip-by-trip timeline (TTFT × trips + embed + webhook).
4. RAG timeline: every embed call's position relative to the LLM (hot path?) + cached-vs-fresh per turn.
5. Tool latency table incl. `query_livecall_slots` 2534/1773/37/1764ms and the `no_start_time` failure.
6. Conversation-quality section: gate_failed `transition_to_ConfirmSlots` (missing callback_number), `set_callback_number` wrong_number round, contact_details ~12 turns, ConfirmSlots ~12 turns / 4 slot queries — user-perceived friction (Julio's ear-witness asked in BLOCKED).
7. Ranked root causes for spikes, each with evidence lines, and a recommended fix list (maps to T2 candidates).
Verification: every spike turn fully accounted for (sum of parts ≈ e2e); verdict names ≥3 quantified causes; report saved.
Dependencies: T0 + Julio's ear-witness answers.

### T2 — Present verdict to Julio → lock the fix list
Goal: owner approval on WHAT to fix (the one variable is latency structure; candidate fixes L1 RAG-prefetch, L2 slots-prefetch, L3 one-trip-transitions — the analysis may reorder/add/drop).
Files: plan §Tasks re-locked in this file; notes.md.
Commands: present `01_analysis_…md` to Julio; record his decisions in the plan's Resolved Decisions.
Verification: plan updated; explicit owner list of approved fixes.
Dependencies: T1.

### T3 — Execute approved fixes (one commit per fix)
Goal: implement the locked list. Candidate designs (ADAPT to T1/T2):
- L1 RAG prefetch: `CallRuntime` background prefetcher — on `outcome.new_state`, `asyncio.create_task` computing the next state's refer-query retrieval into the EXISTING `self._rag_cache[(state, query)]`; state_node falls back to the synchronous path on miss (stale-safe, zero behavior change).
- L2 slots prefetch: background warm of `query_livecall_slots` when date+timezone exist pre-ConfirmSlots; `_deterministic_node` answers the model's slots call from the warm result (<120s old, `"source":"prefetch"`), webhook fallback on miss/stale; `no_start_time` case must always fall back to the live webhook.
- L3 one-trip transitions: `route_after_deterministic` finalizes when `round_spoke` and every executed tool is fire-and-forget OR a `transition_to_*` with `ok=True`; gate-failed transitions keep looping back (repair round preserved).
Files: builder.py, tools.py, config.py (flags `rag_prefetch=True`, `slots_prefetch=True`), tests.
Verification: suite ≥162+new green; each fix has ≥1 regression test (transition-prefetch-populates-cache; slots-prefetch-no-sync-webhook + stale-fallback; one-trip-ok-transition + gate-failed-still-loops).
Dependencies: T2.

### T4 — Suite + battery + bookings cleanup
Commands (full):
```bash
cd /tmp/opencode/wt-iter39 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests
cd /tmp/opencode/wt-iter39 && set -a && . ./.env && set +a && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf_eval.py ladder
```
Verification: all PASS in `lf_eval.py status`; **cancel all test bookings** (event 3801235).
Dependencies: T3.

### T5 — Live A/B on :8007 + verdict + ASK JULIO
Goal: owner re-test proves flat latency.
Commands: kill old 8007 pid; relaunch per Deploy Rules (copy the OLD log to research/ first).
Verification: log analysis (T1 script rerun) shows: no synchronous embed before first token, no synchronous slots webhook in-turn, spike turns ≤~1.8s, p50 ≤1.2s, cache hit ≥58%; then verdict line in notes.md + ITERATIONS.md ledger + **ASK JULIO** (merge gate; also his call on keeping/killing :8006 gpt-5.2 A/B server).
Dependencies: T4.

## Validation Plan (end-to-end)
1. T1 report fully accounts for all 47 turns + 6 spikes.
2. T2 owner-approved fix list recorded in the plan.
3. T3–T4: suite ≥168 green, battery PASS, bookings cancelled.
4. T5: live p50 ≤1.2s / no structural spikes; Langfuse trace shows 0 hot-path embeds and 0 sync slots calls; cap armed (64/600s).

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Prompt/KB/RAG-scoring changes | out of the one variable |
| Deepgram EOT tuning | STT not a measured bottleneck yet |
| Streaming TTS (llm→tts 70–350ms) | already inside budget |
| PhaseB booking semantics | verified live 2026-09-09 (`e24H7HdM6URJiFwxBx81eh`) |
| gpt-5.2 A/B server disposal | Julio's call at T5 |
