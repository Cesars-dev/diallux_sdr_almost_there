# PLAN — v5 iter40: spike-kill (L2/L3/C3) + slot-readback speech fixes (9/10 endpoint, noon/2pm loop)

## Meta
- Date: 2026-09-09
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Branch: `engine/iter40-spike-readback` ← `engine/iter38b-gpt54` (head `491a7a3`)
- Scope: one session, four workstreams in owner-fixed order: (1) archaeology — find/verify the humanized slot-readback branch lineage; (2) latency spike-kill fixes L2/L3/C3 on a NEW engine branch; (3) fix the "9/10" date speech + noon/"12 pm" rendering at the LIVE cal_slots endpoint (`:8001` / slots.diallux-ai.site); (4) kill the 2pm loop (engine auto-fill + JULIO-SUPERVISED prompt lines). Ends with battery + live A/B on `:8007` + ASK JULIO.
- Status: SHIPPED — commits 8600e00..91aa4ac (7 engine commits + 2 owner-gated endpoint deploys 2a64523/7094bd8, both verified; suite 187; first-13 battery 11/13; 2 REAL live happy paths — Susan booked+cancelled, Maria t9 Closer flake → fixed by commit7). OPEN: T8 live A/B on :8007 + ASK JULIO merge gates — carried into iter41 plan (plan_v5_iter41_quality_debt.md T5).

## Compaction Context
- **Project:** Dialux SDR voice engine ("Linda"), LangGraph 9-state pipeline (Intake → Discovery → Closer → Offer → contact_details → ConfirmSlots → VerifyLead → Booking → Closing), Deepgram Flux STT → graph → gates → Cartesia TTS (sonic-3.6, voice `829ccd10-f8b3-43cd-b8a0-4aeaa81f3b30`). Repo fork of `Retell_AI_MCP_connection` (fork = MAIN workspace since 2026-09-08; ORIGINAL still serves live infra).
- **Doctrine:** `/home/julio/projects/clean_diallux_SDR/AGENTS.md` — LAW 0: CODE = plan → branch `engine/iterNN-<slug>` → suite green → report → ASK Julio; docs straight to main; never touch `:8001/:8002/:8003/:8000`; live services read-only EXCEPT owner-gated deploys from this plan; Cal.com event 3801235 REAL — cancel test bookings (cancel = `POST /v2/bookings/{uid}/cancel`, NOT DELETE).
- **Plan SOP:** `/home/julio/projects/new_plan_sop.md` (this file follows it). Old plan `plans/plan_v5_iter39_spike_kill.md`: T0–T2 DONE (evidence frozen + full analysis + verdict presented); its T3–T5 SUPERSEDED by THIS plan (branch renumbered iter40).
- **iter38 DONE+LIVE-VERIFIED** (`engine/iter38-memory-latency-fix` head `491a7a3`; fork `engine/iter38b-gpt54` = same commits, only `.env` `OPENAI_MODEL` differs): eager-EOT adopt, `_late_turn_report` fix, cap 64 turns/600s, idempotent ingest, barge-in carry, `t_audio_out`. Suite **162 passed**.
- **Model verdict (owner-approved 2026-09-09):** gpt-5.4 thinking-off (`reasoning_effort=none`) ≈ 0.9–1.1s flat vs gpt-5.2 2.7–8.4s. gpt-5.4 stays. `verbosity=low`.
- **Assessed call:** `1480fbd1f29d`, trace `ecbc42943d42`, `:8007`, 2026-09-09 11:14:45→11:24:45 (600.2s). 47 real turns/58 indexes, 63 GENERATION, 32 TOOL. Cap fired (`session:turn_cap_close`, real_turns=58) mid-ConfirmSlots. **NO booking.** Julio verdict: "much better, still a disaster".
- **Analysis verdict** (full report: `research/surgeon/iter39-spike-kill/01_analysis_call_1480fbd1f29d.md`): e2e p50 1413 / p90 3571 / max 6867ms; LLM p50 1261ms (single-trip floor); TTS p50 0.6ms, STT clean — **path to ≤1.2s = single-trip + cache-hit every turn**. 9 spikes (t22 24 28 34 39 40 48 55 58), all accounted:
  - **C1 sync slots webhook in-turn**: 2534/1773/1764ms (t40/48/58) + t55 `no_start_time` arg error.
  - **C2 multi-trip turns**: 16 of 47 turns pay 2–3 LLM trips (tool round + speech round) — also caused t9 double-speak (user: "You just repeated yourself").
  - **C3 cache-miss variance**: t28 2nd gen 5698ms, cache_read=0 on 3.3k tokens (state-block re-render between rounds mutates the prefix).
  - **RAG CLEARED**: all 31 rag spans ≤1ms, embeds overlap the eager window, 0 hot-path embeds after t27 → **L1 prefetch dropped**.
- **Conversation bugs (evidence in 01_analysis):**
  - **9/10 speech**: endpoint `_slots_human()` same-day branch emits `"tomorrow, 9/10 at 6 pm or 6:30 pm"` (per-slot `human` fields are clean; the JOIN is not). ConfirmSlots.md orders verbatim readback → model says "nine ten" → caller confusion t41–t43, repeat at t58.
  - **noon→"12 pm"**: `_time_alt()` maps noon→"12 pm"; phone-ear collision with "two pm" → t48–t57 five-turn loop, agent re-asks the day caller already gave ("I already told you Friday"), t57 self-contradiction ("Yes — Friday I have 12 pm. I don't have 1 pm open"), `no_start_time` at t55 (model omitted `slot_target_date` after the error round).
  - SALES 9/14, HUMANIZED PASS/POLISH (R1 ×2, no hard flags) — speech quality is fine; the pain is slots UX + latency.
- **Branch archaeology facts (gathered 2026-09-09, verify in T1 — do not redo the search):**
  - Humanized slot readback = **`engine/iter27-human-slots` @ `e69f512`** (human-slot contract: `agent/llm.json` + `ConfirmSlots.md` re-point, mock mirror, webhook signing) → **`engine/iter28-server-time-payload` @ `62c9a81`** (v1 humanizer + containment gate + `booked_human`, battery 13/13, HUMANIZED 10 PASS/3 POLISH) → merged into **`engine/main`** ("Merge iter28-server-time-payload").
  - Live endpoint code = ORIGINAL repo commit **`93a744c`** "iter28: v1 humanizer + booked_human (cal_slots_endpoint)…" (2026-09-07) at `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/main.py`.
  - Fork mirror `/home/julio/projects/clean_diallux_SDR/services/cal_slots_endpoint/main.py` **byte-identical** (both md5 `0232c06813dafef063b52c551d8d296b`; fork restructure commit `b94dad4`).
  - "3 combos of humanized time" = `_humanize_slot()` 3 templates (at/`,`/around variants), random pick.
  - Current head iter38b CARRIES the contract (live call t40 tool payload has `day_human/time_human/human/slots_human`; worktree `/tmp/opencode/wt-iter38b` has the verbatim clause in `diallux/prompts/ConfirmSlots.md` + mock mirror in `tests/mock_webhooks.py`).
- **Evidence frozen (research/, gitignored):** `research/surgeon/iter39-spike-kill/otel_observations_ecbc42943d42.json` (223 obs), `uvicorn_8007_iter38b_call_1480fbd1f29d.log` (45KB, SOURCE OF TRUTH; Langfuse ingest ~25% loss), `uvicorn_8006_iter38_call_66bd7b0c7726.log` (316B — LOST, gpt-5.2 A/B turn reports only in session notes: turns 7–13 e2e 3017/5409/3190/3309/4152/8856ms — reconstructed, flag if quoted).
- **Servers live right now:** `:8006` wt-iter38 gpt-5.2 pid 2583249 · `:8007` wt-iter38b gpt-5.4 pid 2583320 · `:8005` OLD iter37 pid 2099198 (leave) · `:8000` pid 2659243 (leave) · Langfuse `:3001` (health OK 2026-09-09) · pgvector KB docker `diallux-db` :5434 · **LIVE endpoint `:8001`** = `slots.diallux-ai.site` (systemd USER service `cal-slots.service` as user `2nd_workspace`, ORIGINAL workspace; validator `:8003`).
- **Launch pattern** (plain nohup dies with shell): `cd <worktree> && set -a && . ./.env && set +a && setsid nohup /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 80NN > /tmp/opencode/uvicorn_80NN.log 2>&1 < /dev/null & disown`. Tracer reads `os.environ` — export env BEFORE launching (iter38 lesson: untraced otherwise).
- **Tooling:** `engine/scripts/lf.py` (health/traces/show/gens/tools/usage), `scripts/lf_eval.py ladder|status`, skills `langfuse-call-analysis` + `sop_call_analysis` (LOAD BOTH at session start), protocol `docs/Testing_guidelines/full_call_analysys.md` (table → summary → relevant info).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| L1 RAG prefetch DROPPED | Evidence: 0 hot-path embeds after t27; embeds overlap eager window |
| L2 slots prefetch: bg-warm ASAP payload on ConfirmSlots entry, <120s staleness, live-webhook fallback; `no_start_time` always falls back live | Kills t40-class spikes (2.5s webhook); correctness > latency |
| L3 one-trip: finalize when `round_spoke` AND all executed tools fire-and-forget OR `transition_to_*` ok=True; gate_failed keeps repair loop; slots-round empty-text → deterministic speak of the prompt's own prescribed line ("One moment while I check availability.") | Kills 16 multi-trip turns + t9 double-speak class + gives first-audio ~1.2s on slots turns |
| C3: freeze per-turn state-block bytes (render once at turn start, reuse across all rounds of the turn) | Tool-round gen shares the cached prefix → t28-class 5.7s cache-miss spikes die; miss rate 16%→~5% |
| 9/10 fixed AT THE ENDPOINT (`_slots_human` same-day join drops `m/dd`), not engine-side | Owner direction 2026-09-09; source-of-truth fix, engine keeps verbatim clause |
| noon rendered "noon" (kill `_time_alt` noon→"12 pm" + midnight→"12 am" mappings) | 2pm-loop root cause #1 (phone-ear twelve/two collision); canonicalizer already maps noon↔12:00 pm both sides |
| Engine auto-fills `slot_target_date` from the last successfully used date when the model omits it | Kills `no_start_time` round trip (t55) and the "which day?" re-ask |
| Prompt lines (ConfirmSlots.md) = DRAFTS below — commit ONLY after Julio approves verbatim in-session | Owner: "the prompt related needs my supervision" |
| Branch `engine/iter40-spike-readback` forked from `engine/iter38b-gpt54` (`491a7a3`); iter39 plan T3–T5 superseded | Fresh branch per owner; iter39 numbers reserved by its plan, remaining work renumbered |
| gpt-5.4 thinking-off + cap 64/600s unchanged; gates: p50 ≤1.2s, spike turns ≤~1.8s, cache ≥58%, 0 spoken M/D dates, 0 `no_start_time` | iter38/A/B verdicts stand |
| Endpoint deploy = edit ORIGINAL `main.py` (commit only that file there) + restart `cal-slots.service` (user unit `2nd_workspace`) + signed probe; then sync byte-identical fork `services/` mirror + commit fork main | Service runs from ORIGINAL workspace; fork mirror must not drift |
| One variable rule bent by owner decree: latency + speech workstreams in one iteration, separate commits per fix | Owner consolidated the three workstreams 2026-09-09 |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Julio verbatim approval of the ConfirmSlots.md DRAFT lines (T6) before commit | Owner gate (in-session) |
| Julio OK to restart `cal-slots.service` (LIVE production endpoint) before T5 deploy | Owner gate (in-session ASK) |
| Keep or kill `:8006` gpt-5.2 A/B server (pid 2583249) | Julio's call at T8 |
| Merge of `engine/iter40-spike-readback` | ASK JULIO (LAW 0) after T8 |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12; langgraph 1.2.11, langfuse 4.15.1, httpx, fastapi). Worktree venv = symlink to this.
- Worktree (T2): `/tmp/opencode/wt-iter40` of branch `engine/iter40-spike-readback`; `.env` copied from `/tmp/opencode/wt-iter38b/.env` (contains `OPENAI_MODEL=gpt-5.4`, `DATABASE_URL` for docker `diallux-db` :5434, `LANGFUSE_*`, Cal keys — never print).
- Suite: `cd /tmp/opencode/wt-iter40 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q` (baseline **162 passed**).
- Battery: `cd /tmp/opencode/wt-iter40 && set -a && . ./.env && set +a && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf_eval.py ladder` (needs worktree-root `.venv` symlink). Battery books REAL Cal.com slots on event 3801235 → cancel after (`POST /v2/bookings/{uid}/cancel` with Cal key from `.env`; NEVER DELETE).
- Langfuse: `http://localhost:3001` (docker langfuse-web/worker/clickhouse; `lf.py health` first).
- Endpoint paths: LIVE `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/main.py` (git repo; commit only this file — the repo has OTHER uncommitted changes (AGENTS.md, CLAUDE.md, NEXT_STEPS.md deleted, PROJECT_STRUCTURE.txt, README.md) — DO NOT touch them). Fork mirror: `/home/julio/projects/clean_diallux_SDR/services/cal_slots_endpoint/main.py`. Both md5 today `0232c06813dafef063b52c551d8d296b`.
- Endpoint bug locations in `main.py`: `_slots_human()` lines 261–273 (same-day branch line 270 `f"{slots[0]['day_human']}, {m}/{dd} at {times}"`); `_time_alt()` lines 220–228 (noon→"12 pm", midnight→"12 am"); canonicalizer `_CANON_*` lines 276–280 already handles noon↔12:00 pm (`_CANON_SYNONYMS`), strips "around", maps M/D dates.
- Service control (agent-permitted): `sudo systemctl --user -M 2nd_workspace@.host status cal-slots.service --no-pager` / `sudo systemctl --user -M 2nd_workspace@.host restart cal-slots.service`. Health: `curl -s https://slots.diallux-ai.site/health` → `{"ok":true,"service":"cal_slots"}`.
- Signed probe: reuse the HMAC signed-caller pattern in `services/cal_slots_endpoint/TEST_VERIFY.md` (signature `v=<ms>,d=HMAC-SHA256(raw_body+ts)`, header `X-Retell-Signature`, key = `RETELL_API_KEY` from the endpoint `.env` — never print). URL `https://slots.diallux-ai.site/check_availability`; body `{"account_id":"diallux_live","timezone":"America/New_York"}` (+ `slot_target_date` for per-date).
- PT-38 RULE: NEVER open/touch `slots.db` as julio (julio-owned WAL sidecars break the `2nd_workspace` service). Edit only `main.py`.
- Engine mock lockstep: `tests/mock_webhooks.py` mirrors the endpoint contract ("keep in lockstep" header) — its `slots_human` fixture still asserts the OLD `"today, 9/4 at 1 pm or 2:30 pm"` format → must update with the endpoint fix.
- Git remotes: fork origin `https://github.com/Cesars-dev/clean-diallux-sdr.git` (docs → commit+push main; run `scripts/keyhound` before push). ORIGINAL repo has its own history (3 commits on cal_slots path: `523dd51`→`1515333`→`93a744c`).

## Architecture (one block diagram)
```
Mac Chrome /mic ──ssh──▶ :8007 (wt-iter40, gpt-5.4)
  16k PCM → Deepgram Flux → adopt-EOT → graph.astream
      ├─ LLM trips (gpt-5.4, cache 58%)  [C3: frozen state block → prefix shared]
      ├─ tool rounds                     [L3: one-trip finalize / deterministic filler]
      ├─ query_livecall_slots            [L2: bg-warm ASAP cache <120s + auto-fill date]
      │        └─▶ LIVE :8001 slots.diallux-ai.site (cal-slots.service @ ORIGINAL)
      │                    [T5: _slots_human drops m/dd · _time_alt keeps "noon"]
      ├─ RAG (pgvector diallux-db :5434) — NOT touched (cleared)
      └─ Cartesia TTS → ws
  Langfuse :3001 trace micbridge-<sid> + uvicorn log (SOURCE OF TRUTH)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter40_spike_readback.md` | this plan | NEW (committed with iter39 status edit) |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter39_spike_kill.md` | Meta status → "T0–T2 DONE; T3–T5 superseded by iter40" | EDIT |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter40-spike-readback/01_branch_archaeology.md` | T1 lineage verification report | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter40-spike-readback/02_latency_fixes.md` | T2–T4 verdicts (per-fix evidence) | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter40-spike-readback/03_endpoint_910_noon.md` | T5 endpoint fix + probe + deploy receipt | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter40-spike-readback/04_battery_live_ab.md` | T7–T8 battery + live A/B verdict | NEW |
| `/tmp/opencode/wt-iter40/diallux/graph/tools.py` | L2 slots prefetch warm-cache + `slot_target_date` auto-fill | EDIT |
| `/tmp/opencode/wt-iter40/diallux/graph/builder.py` | L3 one-trip routing + deterministic filler line + C3 frozen state block per turn | EDIT |
| `/tmp/opencode/wt-iter40/diallux/config.py` | kill-switch flags `slots_prefetch=True`, `one_trip=True`, `frozen_state_block=True` | EDIT |
| `/tmp/opencode/wt-iter40/tests/test_iter40_spike_readback.py` | regression tests per fix | NEW |
| `/tmp/opencode/wt-iter40/tests/mock_webhooks.py` | mirror endpoint change (slots_human format + noon) | EDIT |
| `/tmp/opencode/wt-iter40/diallux/prompts/ConfirmSlots.md` | DRAFT recovery lines — JULIO-GATED (T6) | EDIT |
| `/tmp/opencode/wt-iter40/notes.md` | per-task verdict lines | EDIT |
| `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/main.py` | T5: `_slots_human` same-day join drops `m/dd`; `_time_alt` keeps noon/midnight | EDIT (LIVE) |
| `/home/julio/projects/clean_diallux_SDR/services/cal_slots_endpoint/main.py` | byte-identical mirror sync after T5 | EDIT |
| `/home/julio/projects/clean_dialux_SDR/engine/ITERATIONS.md` | iter40 ledger line | EDIT |

## Deploy Rules
- Suite green after EVERY task; one commit per fix on `engine/iter40-spike-readback`; report per task in `research/surgeon/iter40-spike-readback/`.
- Engine live test ONLY on `:8007`: BEFORE killing pid 2583320, copy its current log out (`cp /tmp/opencode/uvicorn_8007.log research/surgeon/iter40-spike-readback/pre_restart_uvicorn_8007.log` — restart clobbers, iter38 lesson). Launch per Compaction Context pattern with log `/tmp/opencode/uvicorn_8007_iter40.log`.
- Endpoint deploy (T5) ONLY after in-session ASK JULIO: edit ORIGINAL `main.py` → `git -C /home/julio/projects/Retell_AI_MCP_connection add cal_slots_endpoint/main.py && git -C ... commit -m "iter40: slots_human same-day join drops m/dd; _time_alt keeps noon (phone 12/2 collision) — mirrors fork services/"` → `sudo systemctl --user -M 2nd_workspace@.host restart cal-slots.service` → signed probe.
- NEVER touch `:8000/:8002/:8003`, `:8005` (pid 2099198), production agents (`agent_f305…`, `agent_1698…`, `agent_87e4…`), `slots.db`, ORIGINAL repo's other dirty files.
- No merges without Julio's explicit say-so. Cancel ALL test bookings after every battery/live run (event 3801235 REAL).

## Tasks (in order)

### T0 — Session bootstrap
Goal: skills loaded, evidence + servers verified, iter39 plan marked superseded (status edit already committed with this plan — verify only).
Files: none new.
Commands (full):
```bash
# skills: load langfuse-call-analysis AND sop_call_analysis (opencode skill tool)
cd /home/julio/projects/clean_diallux_SDR/research/surgeon/iter39-spike-kill && wc -c otel_observations_ecbc42943d42.json uvicorn_8007_iter38b_call_1480fbd1f29d.log
cd /home/julio/projects/clean_diallux_SDR/engine && set -a && . /tmp/opencode/wt-iter38b/.env && set +a && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf.py health
ss -ltnp | grep -E ':800[05-7]'   # expect 8000/8005/8006/8007 listeners as pinned above
grep -n "Status" /home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter39_spike_kill.md | head -2
```
Verification: JSON 501,947B; log 45,323B; Langfuse server+ingest OK; iter39 plan shows the superseded status line.
Dependencies: none.

### T1 — Branch archaeology: the humanized slot-readback lineage (VERIFY, don't re-search)
Goal: prove which branches carry the humanized slot readback, that the live endpoint = that code, and that iter40's parent (iter38b) still carries the engine side. Write `01_branch_archaeology.md`.
Files: `research/surgeon/iter40-spike-readback/01_branch_archaeology.md` (NEW).
Commands (full):
```bash
cd /home/julio/projects/clean_diallux_SDR
git log --oneline engine/iter27-human-slots -3          # expect e69f512 human-slot contract
git log --oneline engine/iter28-server-time-payload -3  # expect 62c9a81 v1 humanizer + containment gate
git log --oneline engine/main -5                        # expect "Merge iter28-server-time-payload (62c9a81 ...)"
git merge-base --is-ancestor 62c9a81 engine/iter38b-gpt54 && echo "iter28 IS ancestor of iter38b" || echo "BROKEN LINEAGE — investigate before T2"
git show engine/iter28-server-time-payload:diallux/prompts/ConfirmSlots.md | grep -n "slots_human\|verbatim"
git -C /home/julio/projects/Retell_AI_MCP_connection log --oneline -3 -- cal_slots_endpoint/main.py   # expect 93a744c on top
md5sum /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/main.py /home/julio/projects/clean_diallux_SDR/services/cal_slots_endpoint/main.py   # BOTH must equal 0232c06813dafef063b52c551d8d296b
grep -n "slots_human" /tmp/opencode/wt-iter38b/diallux/prompts/ConfirmSlots.md /tmp/opencode/wt-iter38b/tests/mock_webhooks.py | head
grep -n "def _humanize_slot" -A 12 /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/main.py   # the 3 templates
```
Verification: lineage chain intact (e69f512 → 8c0a0bb → 62c9a81 → engine/main → … → iter38b), both md5 identical, engine side present in iter38b worktree, live-call payload (frozen OTEL t40) shows `day_human/time_human/human/slots_human`. Report saved with the lineage graph + md5 receipts.
Dependencies: T0.

### T2 — Worktree + L2 slots prefetch (commit 1)
Goal: bg-warm the ASAP slots payload so `query_livecall_slots` (no date) answers from a <120s warm cache; stale/miss → live webhook; `no_start_time` ALWAYS live.
Files: `/tmp/opencode/wt-iter40/diallux/graph/tools.py`, `/tmp/opencode/wt-iter40/diallux/config.py`, `/tmp/opencode/wt-iter40/tests/test_iter40_spike_readback.py`.
Commands (full):
```bash
cd /home/julio/projects/clean_diallux_SDR && git branch engine/iter40-spike-readback engine/iter38b-gpt54 && git worktree add /tmp/opencode/wt-iter40 engine/iter40-spike-readback
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter40/.venv
cp /tmp/opencode/wt-iter38b/.env /tmp/opencode/wt-iter40/.env
cd /tmp/opencode/wt-iter40 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q   # baseline 162
# ... implement L2 ... then:
cd /tmp/opencode/wt-iter40 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q
cd /tmp/opencode/wt-iter40 && git add -A && git commit -m "iter40 L2: slots prefetch — bg-warm ASAP payload on ConfirmSlots entry, <120s cache, live fallback, no_start_time always live"
```
Design (pin): `CallRuntime` gets `_slots_warm: dict` (payload + timestamp). On `transition_to_ConfirmSlots` ok=True (and on ConfirmSlots state entry), `asyncio.create_task` fires the webhook with `{"account_id":"diallux_live","timezone":<prospect_timezone>}` (no date) into the warm store. `_deterministic_node` answers the model's no-date slots call from warm if age <120_000ms (response gains `"source":"prefetch"`); any other case → live webhook (existing path). Flag `slots_prefetch=True` in config.py (kill switch → falls back to today's behavior).
Tests (≥2): warm-hit answers without HTTP (mock clock); stale (>120s) + miss + `no_start_time` → live webhook called.
Verification: suite ≥162+new green; commit on branch.
Dependencies: T1.

### T3 — L3 one-trip transitions + deterministic filler (commit 2)
Goal: end the tool-round+speech-round double trip; fix the t9 double-speak class; first-audio ~1.2s on slots turns.
Files: `/tmp/opencode/wt-iter40/diallux/graph/builder.py`, config flag `one_trip=True`, tests.
Design (pin): `route_after_deterministic` finalizes the turn when `round_spoke` AND every executed tool is fire-and-forget OR a `transition_to_*` with `ok=True`. `gate_failed` transitions keep looping back (repair round preserved — t34 behavior). NEW: when a round emits tool calls with `query_livecall_slots` pending and EMPTY text, the engine speaks the ConfirmSlots.md prescribed Start line "One moment while I check availability." deterministically (the sentence already exists in the prompt — no new prompt content) instead of a second silent round.
Tests (≥3): one-trip finalize on ok-transition (trip count == 1); gate_failed still loops (repair round); empty-text slots round speaks the filler (assert TTS token + no second LLM trip).
Verification: suite green; commit 2.
Dependencies: T2.

### T4 — C3 frozen state block per turn (commit 3)
Goal: tool-round and speech-round gens share byte-identical prefixes → OpenAI prompt cache hits on round 2 (t28-class 5.7s dies).
Files: `/tmp/opencode/wt-iter40/diallux/graph/builder.py`, config flag `frozen_state_block=True`, tests.
Design (pin): render the trailing CURRENT CALL STATE system block ONCE per turn (at turn start, before round 1) and reuse the frozen bytes for every round of that turn — today the block re-renders dvs between rounds (tool writes mutate dvs → prefix bytes differ → full re-prefill). Block refresh moves to next turn start. This is structure-only: same information, one render later.
Tests (≥2): FakeLLM captures round-1 and round-2 system blocks in a tool round → byte-equal with flag on; dvs updates still visible to the NEXT turn.
Verification: suite green; commit 3. Record in `02_latency_fixes.md` per-fix evidence.
Dependencies: T3.

### T5 — 9/10 + noon fix at the LIVE endpoint (+ engine mock lockstep, commits 4a/4b)
Goal: `slots_human` never contains M/D; noon never renders "12 pm". Deploy + signed-probe the LIVE service.
Files: ORIGINAL `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/main.py`; fork mirror `/home/julio/projects/clean_diallux_SDR/services/cal_slots_endpoint/main.py`; engine `/tmp/opencode/wt-iter40/tests/mock_webhooks.py`.
Steps (full):
1. READ FIRST: `grep -n "book-livecall\|def _resolve\|canonical" /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/main.py | head -20` — confirm the booking resolver matches echoed human strings against the returned slot set (canonicalized), i.e. that dropping `m/dd` from the offered join keeps echoes resolvable. If (unexpected) the resolver needs the date, keep `m/dd` in a MACHINE field only (slot dicts already carry `day`) and still drop it from the spoken join.
2. Edit BOTH `main.py` copies identically:
   - `_slots_human` same-day branch: `f"{slots[0]['day_human']}, {m}/{dd} at {times}"` → `f"{slots[0]['day_human']} at {times}"` (e.g. "tomorrow at 6 pm or 6:30 pm").
   - `_time_alt`: `noon → "noon"` and `midnight → "midnight"` (delete the 12 pm/12 am remap) so template 2 renders "friday, noon".
   - No other lines. Machine fields untouched (iter28 contract).
3. Unit check (no server needed): `cd /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint && python3 -c "import main; slots=[{'day':'2026-09-10','time':'2026-09-10T18:00:00','day_human':'tomorrow','time_human':'6','human':'tomorrow, 6 pm'},{'day':'2026-09-10','time':'2026-09-10T18:30:00','day_human':'tomorrow','time_human':'6:30 pm','human':'tomorrow, 6:30 pm'}]; print(main._slots_human(slots))"` → must print `tomorrow at 6 or 6:30 pm`-family with NO `9/10` and NO `12 pm` when a noon slot is used.
4. Engine mock lockstep (commit 4a on the engine branch): update `tests/mock_webhooks.py` fixtures — `slots_human` `"today, 9/4 at 1 pm or 2:30 pm"` → new format; `_human_pick`/`_time_alt` mirror noon change; suite green.
5. **ASK JULIO** (owner gate — live production): approval to deploy. Then:
```bash
cd /home/julio/projects/Retell_AI_MCP_connection && git add cal_slots_endpoint/main.py && git commit -m "iter40: slots_human same-day join drops m/dd; _time_alt keeps noon (12/2pm phone collision) — mirrors fork services/"
sudo systemctl --user -M 2nd_workspace@.host restart cal-slots.service
sudo systemctl --user -M 2nd_workspace@.host status cal-slots.service --no-pager
curl -s https://slots.diallux-ai.site/health    # {"ok":true,"service":"cal_slots"}
# signed probe per services/cal_slots_endpoint/TEST_VERIFY.md pattern (RETELL_API_KEY from endpoint .env — never print):
#   POST /check_availability {"account_id":"diallux_live","timezone":"America/New_York"} → slots_human has NO m/dd, noon slots show "noon"
```
6. Mirror sync (commit on fork main — byte-identical mirror, owner-approved live fix): `cp /home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/main.py /home/julio/projects/clean_diallux_SDR/services/cal_slots_endpoint/main.py` → md5 both == new md5 → `cd /home/julio/projects/clean_diallux_SDR && git add services/cal_slots_endpoint/main.py && git commit -m "services mirror: cal_slots iter40 9/10+noon fix (byte-identical to ORIGINAL deploy)"`.
Verification: probe shows no `m/dd` in `slots_human`, noon rendered "noon"; resolver read-back confirms echo resolution (or machine-field fallback applied); md5 receipts in `03_endpoint_910_noon.md`; ORIGINAL commit touches ONLY main.py.
Dependencies: T4 (mock lockstep needs the branch), owner gate.

### T6 — 2pm-loop recovery: engine auto-fill + JULIO-GATED prompt lines (commits 5, 6)
Goal: never re-ask the day; never die in the no-time-available loop.
Files: `/tmp/opencode/wt-iter40/diallux/graph/tools.py`, `/tmp/opencode/wt-iter40/diallux/prompts/ConfirmSlots.md`, tests.
Steps:
1. Commit 5 — `slot_target_date` auto-fill in `tools.py`: when the model omits `slot_target_date` (the t55 `no_start_time` case) AND this call has a previously used date (last successful slots call) or `{{requested_slot}}` implies one, fill it and tag the response `"source":"prefill"`; if none known → existing live `no_start_time` message (unchanged). Test: omitted-date call with prior date → prefilled, no error round.
2. Commit 6 — **ASK JULIO FIRST (verbatim approval)** — DRAFT lines for `ConfirmSlots.md`:
   - Availability section: "If the caller asks for a specific time you don't have: say once that time isn't open, offer the closest open time on the SAME day, and stop. Never re-ask which day they want — you already have it."
   - Critical Rules: "Never open a reply with 'Yes' when the answer is no." (t57)
   - Critical Rules: "If a tool returns an error, keep the thread: use what the caller already told you; never re-ask facts already given this call." (t51–t55)
   Julio may edit/reword — commit ONLY his approved text.
Verification: suite green; both commits on branch; prompt diff shows ONLY the approved lines.
Dependencies: T5.

### T7 — Suite + battery + bookings cleanup
Commands (full):
```bash
cd /tmp/opencode/wt-iter40 && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q
cd /tmp/opencode/wt-iter40 && set -a && . ./.env && set +a && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf_eval.py ladder
cd /tmp/opencode/wt-iter40 && set -a && . ./.env && set +a && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python scripts/lf_eval.py status
# then cancel EVERY test booking created (event 3801235 REAL): POST /v2/bookings/{uid}/cancel per booking_uid from the run
```
Verification: suite ≥162+~10 new green; ladder all PASS in status; **`unfixable_format` count == 0** (iter27's failure mode — proves the new slots_human echoes still resolve through the validator); bookings cancelled (calendar clean).
Dependencies: T6.

### T8 — Live A/B on :8007 + verdict + ASK JULIO
Goal: owner re-test proves flat latency AND clean slot speech.
Commands (full):
```bash
cp /tmp/opencode/uvicorn_8007.log /home/julio/projects/clean_diallux_SDR/research/surgeon/iter40-spike-readback/pre_restart_uvicorn_8007.log   # BEFORE killing (iter38 lesson)
kill 2583320   # old :8007 (verify pid first: ss -ltnp | grep 8007)
cd /tmp/opencode/wt-iter40 && set -a && . ./.env && set +a && setsid nohup /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8007 > /tmp/opencode/uvicorn_8007_iter40.log 2>&1 < /dev/null & disown
# Julio tunnels from Mac: ssh -N -L 8007:127.0.0.1:8007 julio@46.62.233.228 → mic bridge test call
```
Post-call verification (from the NEW log + Langfuse trace — log is source of truth):
- `grep "final report" /tmp/opencode/uvicorn_8007_iter40.log` → parse e2e p50/p90/max per turn: **p50 ≤1.2s, spike turns ≤~1.8s**;
- 0 synchronous slots webhooks INSIDE slots-offering turns (httpx POST lines vs turn windows; prefetch warm calls appear background);
- 0 `no_start_time` errors; 0 `"source":"prefetch"` misses (stale falls back are OK but logged);
- Agent speech contains **zero M/D dates** (grep gen outputs for `\d{1,2}/\d{1,2}` in spoken text = 0) and no "twelve pm" (noon slots say "noon");
- cache hit ≥58% (Langfuse usageDetails cache_read);
- conversation-quality rerun per `docs/Testing_guidelines/full_call_analysys.md` (load skill `sop_call_analysis`; table → summary → relevant info) into `04_battery_live_ab.md`;
- verdict line in notes.md + iter40 ledger line in `engine/ITERATIONS.md`;
- **ASK JULIO**: merge gate; his call on `:8006` gpt-5.2 A/B server (pid 2583249); cancel any booking from the live test.
Dependencies: T7.

## Validation Plan (end-to-end)
1. T1: lineage verified + receipts (md5, merge-base) — the "lost" humanized-readback branch is identified and pinned in the report.
2. T2–T4: each fix has ≥1 regression test; suite ≥172 green; commits 1–3 on `engine/iter40-spike-readback`.
3. T5: signed probe shows no `m/dd` in `slots_human` + "noon" rendering; ORIGINAL commit touches only `main.py`; fork mirror md5-identical; service healthy.
4. T6: prompt lines committed ONLY after Julio's verbatim approval (diff proves it).
5. T7: ladder PASS, `unfixable_format` 0, bookings cancelled.
6. T8: live p50 ≤1.2s / spikes ≤~1.8s / cache ≥58% / 0 spoken M/D / 0 no_start_time; verdict + ledger + ASK JULIO.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| `time_of_day` search param on the endpoint (model could search "2 pm Friday" directly) | Endpoint contract change — needs its own owner-gated design; current fixes (noon rendering + auto-fill + prompt) remove the observed loop |
| L1 RAG prefetch | Dropped — evidence cleared RAG (0 hot-path embeds after t27) |
| Prompt/KB/RAG-scoring changes beyond the 3 approved lines | One-variable discipline + owner supervision |
| gpt-5.2 `:8006` server disposal | Julio's call at T8 |
| Services cutover (repoint systemd units to fork `services/`) | Existing NEXT_STEPS owner-gated item, unchanged |
| Deepgram EOT tuning, streaming TTS | Not bottlenecks (analysis: STT clean, TTS 0.6ms) |
