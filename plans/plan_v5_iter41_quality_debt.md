# PLAN — v5 iter41: quality debt kill (double-speak, filler stacks, Brenda mock date-awareness) + iter40 T8 live verdict

## Meta
- Date: 2026-09-09
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Branch: `engine/iter41-quality-debt` ← `engine/iter40-spike-readback` (head `91aa4ac`)
- Scope: one session: (1) close out iter40 — notes/ledger/iter40 plan status edit; (2) T8 live A/B on `:8007` (Julio mic-bridge) for the latency gates p50 ≤1.2s / spikes ≤~1.8s / cache ≥58%; (3) fix the three carry-forward quality defects: in-turn double-speak, Phase B filler stacking, mock date-awareness (Brenda conversion); (4) re-run first-13 + 2 live happy-path REAL bookings. Ends ASK JULIO (merge gate).
- Status: PLAN ONLY (not started — awaits approval)

## Compaction Context (session 2026-09-09 — iter40, verbatim carry)

- **Project:** Dialux SDR voice engine "Linda" — LangGraph 9-state pipeline (Intake→Discovery→Closer→Offer→contact_details→ConfirmSlots→VerifyLead→Booking→Closing), Deepgram Flux STT → gpt-5.4 (thinking-off, verbosity low) → gates → Cartesia sonic-3.6 TTS. Repo FORK = `clean_diallux_SDR` (MAIN workspace); ORIGINAL `Retell_AI_MCP_connection` still serves LIVE infra (`:8001` slots via systemd user unit `cal-slots.service` as user `2nd_workspace`).
- **Doctrine:** `AGENTS.md` LAW 0 — code = plan → branch `engine/iterNN-<slug>` → suite green → report → ASK JULIO; docs straight to main; never touch `:8000/:8002/:8003`; live services read-only EXCEPT owner-gated deploys; Cal.com event 3801235 REAL — cancel test bookings (`POST /v2/bookings/{uid}/cancel` body `{"cancellationReason": "..."}`, cal-api-version `2026-02-25`, key `${CAL_KEY_2}`; Cloudflare 403 on default urllib UA → send a browser User-Agent).
- **iter40 SHIPPED (branch `engine/iter40-spike-readback`, suite 187 green):**
  - `8600e00` L2 slots prefetch + `6bd7972` L2 CORRECTION (warm = freeze-mode parity: `{"args":{"account_id":"diallux_live","timezone":tz,"slot_target_date":<d>,"current_reservation_uids":""}}` for TODAY+TOMORROW keyed by date in `CallRuntime._slots_warm`; serve ONLY on exact arg-match — same date, empty uids, no preferred_time, <120s (`slots_prefetch_ttl_s`), ok+non-empty slots, same tz; flag `slots_prefetch`). Plan's no-date pin was impossible: LIVE endpoint REQUIRES `slot_target_date` (probe: no-date → `no_start_time`).
  - `5565ef2` L3 one-trip (spoken round + ok `transition_to_*` finalizes in 1 trip; `gate_failed` loops; empty-text slots round speaks "One moment while I check availability." via TTS; flag `one_trip`; iter31 RAG-freeze fixture updated to one-trip turn shape).
  - `188d3de` C3 frozen state block per turn (ingest renders `state.frozen_state_block` once; engine-fired rounds re-render — iter33 chain-abort surface + today-prefetch need live tail; flag `frozen_state_block`).
  - `ecd58ae` T6 commit5: `slot_target_date` auto-fill (omitted date → last SUCCESSFUL slots date, else requested_slot day word via today_date; response tagged `source: prefill`; nothing known → unchanged live no_start_time).
  - `c00a815` T6 commit6 (JULIO-APPROVED verbatim): ConfirmSlots.md — availability re-query logic line (preferred_time = caller's words; `preferred_unavailable` → nearest same-day options; empty slots → next day) + Critical Rules ("no 'Yes' on a no", "keep the thread on tool errors"); `agent/llm.json` state_prompt lockstepped (iter28 no-drift gate).
  - `91aa4ac` T6b commit7: **Closer-scoped end_call skip gate** — spoken end_call from Closer with `closer_completed` unset → refused ONCE with repair message, second attempt accepted (iter31 dampener escape). Scope: Closer ONLY; silent/goodbye/Intake/Closing paths untouched; iter8 absolute. (v1 attempt gated all states on livecall_agreed — broke iter16/30/31 contracts, 3 tests red, REVERTED before commit; lesson: scope gates to the state's OWN completion flag.)
  - Tests: `tests/test_iter40_spike_readback.py` (25 tests).
- **LIVE endpoint (ORIGINAL repo, port :8001) — 2 owner-gated deploys this session, both verified:**
  - `2a64523` (main ff): `_slots_human` same-day join drops `m/dd` ("tomorrow at 6 pm or 6:30 pm" — model read "9/10" as "nine ten"); `_time_alt` keeps noon/midnight. Snapshot: branch `snapshot/pre-iter40-deploy` @ `93a744c` + `stash@{0}` (`77c7340`) full dirty-tree. Rollback: `git checkout snapshot/pre-iter40-deploy -- cal_slots_endpoint/main.py` → restart.
  - `7094bd8` (main ff): humanized `preferred_time` resolver wired into `/check_availability` — `_resolve_booking_time(acct, [], out_tz, preferred_raw, anchor_day=slot_target_date)`; `anchor_day=None` default keeps booking path today-anchored (unchanged). Root audit: resolver existed ONLY on `/book-livecall`; availability ignored plain-English preferred_time silently (machine-only `_norm_local`) while the tool schema advertised it — root cause of the live 2pm loop t48. Smoke battery `test_preferred_resolver.py` 22/22; existing `test_slot_lock.py` 60/60. **LIVE probe:** `"2 pm"` + Friday → `slots_human: "friday at 2 pm or 2:30 pm"`, preferred FIRST, flag false.
  - Fork mirror syncs: `87fae0f`, `9acac66` (md5 `ac63faf91cd0268416b729bcca1b1efc` both sides).
- **Batteries run on iter40 code (all slots=mock unless noted):** 13-persona first-13 batch IN PARALLEL (13 separate harness processes — Julio: sequential is dumb, run async) → **11/13 PASS**; 2 live happy paths (`--slots live`, parallel): Susan booked REAL (`ecqbfZu5ntd8iDRB2Mthko`, then CANCELLED 200 — calendar clean), Maria FAILED turn 9 (model skipped ALL flow tools in Closer, role-played funnel as speech, hung up — root cause of the Closer gate; fixed by commit7). Full analysis: `research/surgeon/iter40-spike-readback/04_call_analysis_13.md`.
- **CONFIRMED quality defects (evidence in 04 report):**
  1. **In-turn double-speak (TOP):** exact duplicate sentences inside ONE turn's agent text on 5/13 calls (Marcus t1, Gene t7, Jorge t2, Maria t18, Sofia t19/t20). ROOT CAUSE PINNED via Langfuse: the GENERATION output text itself contains the double (`lf.py gens 2339f87545d4 --state Intake` → `text: 'Got it — after-hours…\nGot it — after-hours…'`, out=48 tok) — **model repetition artifact of gpt-5.4 reasoning-off, NOT a stream/layer bug** (astream accumulation is clean: `diallux/graph/llm.py:191-218`). Same class as live caller complaint "You just repeated yourself" (t9, iter39). Harness transcript = TTS token stream (`harness.py:178 speech="".join(tokens)`).
  2. **Phase B filler stacking:** 3 engine fillers spoken back-to-back at Closing on booked calls ("One sec — finishing that up. Alright, getting that locked in. Just confirming those details now.") — `_deterministic_node` PhaseB loop emits one filler per slow step in the SAME pass (builder.py `_ENGINE_FILLERS`). Robotic (R5.4), 5/5 booked calls.
  3. **Brenda FAIL ON BOOK (regression vs. her own history):** battery run = expect **book**, got **no-book**, 28-turn cap, ended=False — her FIRST-EVER fail (8/8 historical runs = PASS/book, 16–38 turns). Mechanism: mock `check_availability` ALWAYS returns "today" slots regardless of `slot_target_date`; persona insists "tomorrow 2:30"; agent CORRECTLY refuses unheld times (verbatim contract) + re-queries with preferred_time → loop → cap. Agent behavior correct; fixture wrong — but the OUTCOME is a lost conversion that must be fixed (T3 makes the mock date-aware so tomorrow-queries return tomorrow slots and she converts).
  4. **Pedro over-book:** pre-existing (fails 6/8 historical); caller says "2:30" with no day → agent confirms without day anchor. Day-anchor-before-confirm fix candidate.
- **Latency receipts (13-parallel harness load):** OTEL aggregate `ALL: calls=652 p50=1.58s p90=2.5s max=7.82s` (gen p50 gate ≤1.2s still open — iter31 carry-forward; load-inflated; live single-call decides). Harness p50 (includes caller gpt-4o) 1.4–3.0s. vs iter38b same-harness: p90 −30–50%, max −35–70% (Susan 15.0→6.1s, Marcus 13.5→4.9s).
- **Servers live right now:** `:8007` wt-iter38b gpt-5.4 pid 2583320 (TO BE REPLACED by T8 with wt-iter40 — BEFORE killing: `cp /tmp/opencode/uvicorn_8007.log /home/julio/projects/clean_diallux_SDR/research/surgeon/iter40-spike-readback/pre_restart_uvicorn_8007.log`) · `:8006` wt-iter38 gpt-5.2 pid 2583249 (Julio's call: keep/kill) · `:8005` OLD iter37 pid 2099198 (leave) · `:8000` pid 2659243 (leave) · `:8001/:8002/:8003` LIVE (leave) · Langfuse `:3001` OK.
- **Launch pattern (:8007):** `cd /tmp/opencode/wt-iter40 && set -a && . ./.env && set +a && setsid nohup /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8007 > /tmp/opencode/uvicorn_8007_iter40.log 2>&1 < /dev/null & disown`. Julio tunnels: `ssh -N -L 8007:127.0.0.1:8007 julio@46.62.233.228` → mic bridge call.
- **Worktree:** `/tmp/opencode/wt-iter40` (branch engine/iter40-spike-readback, `.venv` symlink → `engine/.venv`, `.env` present). Create wt-iter41 from the new branch the same way (`git worktree add /tmp/opencode/wt-iter41 ...`, `ln -s`, `cp /tmp/opencode/wt-iter40/.env`).
- **Tooling:** suite `cd <wt> && /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m pytest tests -q` (baseline **187**). Battery harness: `tests/llm2llm/harness.py --personas <Name> --rag --langfuse --max-turns 28` (`--slots live` = REAL bookings, parallel-safe as separate processes). Digest SDK: the FORK's `scripts/call.py` LACKS the `digest` subcommand — copy the ORIGINAL's `scripts/call.py` into the worktree scripts/ temporarily, run, then `rm` (proven this session; digest written 714 lines/13 calls). `scripts/lf.py lat` likewise only in ORIGINAL root (`/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5`). 3-SOP protocol: `docs/Testing_guidelines/full_call_analysys.md` (table → summary → relevant info).
- **Evidence frozen this session:** `research/surgeon/iter40-spike-readback/01_branch_archaeology.md`, `02_latency_fixes.md`, `03_endpoint_910_noon.md`, `04_call_analysis_13.md`; digests `/tmp/opencode/iter40_sop_digest.txt`, `/tmp/opencode/iter40_lat.txt`.
- **Owner directives learned this session (binding):** run batteries ASYNC (parallel processes); only run a couple of personas when verifying ("we shouldn't run tons"); "ask me again" before committing prompt lines; git discipline with snapshots before live deploys ("take a git snapshot, but work in main"); prefer fixing bugs with variables the STATE ALREADY HAS; don't stack gates that break old contracts (v1 gate lesson); use git revert/reset cleanly when wrong.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| iter40 shipped as-is (commits listed above); T8 + ledger are its only open items | All fixes battery-verified; 11/13 + goals clean |
| Double-speak root = MODEL repetition artifact (gpt-5.4 reasoning-off) — Langfuse generation text contains the double | Pinned this session; astream accumulation clean; history keeps model raw output |
| Double-speak fix = deterministic sentence-level dedup in the TTS stream (state_node), NOT prompt text, NOT more gates | Exact-duplicate consecutive sentences are never intended speech; suppress at audio layer regardless of root cause; history untouched |
| Filler fix = max ONE engine filler per deterministic pass | 3 fillers in one pass is the bug; anti-repeat per call already exists (`fillers_said`) |
| Mock fix = date-aware `check_availability` fixture (serve slots for the requested `slot_target_date`, mirroring the live endpoint) | Makes Brenda-class conversions possible in tests; endpoint lockstep header rule |
| Pedro day-anchor = retrain fix, NOT a new gate | Pre-existing; keep one-variable discipline |
| Closer gate stays scoped to Closer + `closer_completed` (commit 7 as shipped) | v1 all-states variant broke iter16/30/31; the scoped variant is suite-green 187 |
| gpt-5.4 thinking-off stays; cap 64/600s stays | Owner-approved verdicts stand |
| T8 gates: p50 ≤1.2s, spike turns ≤~1.8s, cache ≥58%, 0 spoken M/D, 0 no_start_time, 0 "12 pm" | Plan gates carried |
| REAL booking cancel = `POST /v2/bookings/{uid}/cancel` `{"cancellationReason": "..."}` + browser User-Agent (Cloudflare 403 default UA) | Proven this session |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Julio presence for T8 mic-bridge call | Owner (schedule in-session) |
| Keep/kill `:8006` gpt-5.2 A/B server (pid 2583249) | Julio's call at T8 |
| Merge `engine/iter40-spike-readback` + `engine/iter41-quality-debt` | ASK JULIO (LAW 0) after all gates |
| Double-speak fix acceptability trade-off (sentence buffering delays each subsequent sentence's first audio slightly) | Julio at T1 design lock |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12; langgraph 1.2.11, langfuse 4.15.1, httpx, fastapi, pydantic-settings). Worktree venv = symlink.
- Suite baseline: **187 passed** (`cd /tmp/opencode/wt-iter40 && .venv/bin/python -m pytest tests -q` equivalent).
- Langfuse `http://localhost:3001`; `scripts/lf.py health` first (fork copy lacks `lat`; use ORIGINAL root for `lat`/`digest` or temp-copy `scripts/call.py`+`scripts/lf.py` originals into the worktree and `rm` after — proven pattern).
- Endpoint repo: `/home/julio/projects/Retell_AI_MCP_connection` — working tree has UNRELATED dirty files (AGENTS.md, CLAUDE.md, README.md, PROJECT_STRUCTURE.txt, agents/heating_uk/*, NEXT_STEPS.md deleted) — **commit ONLY files you touch**; branch `iter28-server-time-payload` is the working branch there (main was ff'd twice this session; snapshot branch `snapshot/pre-iter40-deploy`).
- Service control (exact permitted forms): `sudo /usr/bin/systemctl --user -M 2nd_workspace@.host restart cal-slots.service` / `... status cal-slots.service --no-pager`. Health: `curl -s https://slots.diallux-ai.site/health` → `{"ok":true,"service":"cal_slots"}`.
- Signed probe: key `RETELL_API_KEY` from `/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/.env` (never print); sig `v=<ms>,d=HMAC-SHA256(raw_body+ts)` header `X-Retell-Signature`; URL `https://slots.diallux-ai.site/check_availability`; body `{"args":{"account_id":"diallux_live","timezone":"America/New_York","slot_target_date":"<YYYY-MM-DD>","current_reservation_uids":""}}` wrapped `{"args": ...}` at root (args_at_root=false). Humanized `preferred_time` now honored ("2 pm" → preferred-first or `preferred_unavailable:true` + nearest).
- Cal.com cancel: `POST https://api.cal.com/v2/bookings/{uid}/cancel` headers `Authorization: Bearer ${CAL_KEY_2}`, `cal-api-version: 2026-02-25`, browser User-Agent; body `{"cancellationReason": "test booking — iterNN cleanup"}`.
- PT-38: NEVER touch `slots.db`.

## Architecture (one block diagram)
```
Mac Chrome /mic ──ssh──▶ :8007 (wt-iter41, gpt-5.4)
  16k PCM → Deepgram Flux → adopt-EOT → graph.astream
      ├─ LLM trips (cache) [C3 frozen state block]
      ├─ TTS stream [NEW T1: sentence-dedup buffer kills in-turn doubles]
      ├─ tool rounds [L3 one-trip; NEW T2: max 1 filler per PhaseB pass]
      ├─ query_livecall_slots [L2 warm today+tomorrow; prefill date]
      │        └─▶ LIVE :8001 slots.diallux-ai.site
      │                    [9/10+noon ✅ · humanized preferred_time ✅ (7094bd8)]
      └─ Cartesia TTS → ws
   Langfuse :3001 + uvicorn log (SOURCE OF TRUTH)
   tests: mock date-aware fixture [NEW T3] → Brenda converts
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter41_quality_debt.md` | this plan | NEW (commit main) |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter40_spike_readback.md` | Meta status → shipped/pending-T8 | EDIT |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | iter40 ledger line | EDIT |
| `/tmp/opencode/wt-iter41/diallux/graph/builder.py` | T1 sentence-dedup in state_node TTS stream; T2 filler cap per PhaseB pass | EDIT |
| `/tmp/opencode/wt-iter41/diallux/config.py` | flag `tts_dedupe_sentences=True` (+ filler cap flag if wanted) | EDIT |
| `/tmp/opencode/wt-iter41/tests/test_iter41_quality_debt.py` | regression tests (dedup, filler cap, mock date-aware) | NEW |
| `/tmp/opencode/wt-iter41/tests/mock_webhooks.py` | T3 date-aware check_availability fixture (slots for requested `slot_target_date`, day_human/tomorrow rendering per date) | EDIT |
| `/tmp/opencode/wt-iter41/notes.md` | per-task verdict lines | EDIT |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter41-quality-debt/01_*.md` | per-fix evidence + T8 verdict | NEW |

## Deploy Rules
- Suite green after EVERY task; one commit per fix on `engine/iter41-quality-debt`.
- NO endpoint changes planned (both iter40 deploys verified; if T8 exposes endpoint needs → new owner-gated deploy with snapshot first).
- Live test ONLY on `:8007`; preserve old log BEFORE killing (iter38 lesson); env exported BEFORE launch (tracer reads os.environ).
- Cancel ALL REAL test bookings after every live run (event 3801235 REAL).
- NEVER touch `:8000/:8002/:8003`, `:8005`, live agent IDs, `slots.db`, ORIGINAL repo's other dirty files.

## Tasks (in order)

### T0 — Bootstrap
Goal: skills loaded (`langfuse-call-analysis`, `sop_call_analysis`), evidence + servers verified, iter40 plan status edited, iter40 ledger line in ITERATIONS.md.
Commands: verify `research/surgeon/iter40-spike-readback/` files exist; `ss -ltnp | grep -E ':800[0-7]'` pids match Compaction; `lf.py health`; edit iter40 plan Meta status ("SHIPPED — commits 8600e00..91aa4ac; T8 open"); add ITERATIONS.md §iter40 ledger line (summary: latency fixes + endpoint 9/10/noon + preferred resolver + Closer gate; suite 187; 11/13 battery; 2 REAL live happy paths 1 book 1 flake→fixed).
Verification: git log shows the two doc commits on fork main; ledger line present.
Dependencies: none.

### T1 — Double-speak kill: sentence-level TTS dedup (commit 1)
Goal: an exact-duplicate consecutive sentence inside ONE turn's token stream is never spoken twice.
Design (pin): in `_make_state_node`'s token loop (builder.py), buffer tokens per sentence (flush on `.`, `?`, `!` or stream end); before flushing, compare the pending sentence (stripped) against the last flushed sentence of THIS turn; exact match (case-insensitive, whitespace-collapsed) → drop (do NOT write to tts); else write. History/final content untouched (model output recorded as-is; only the SPOKEN stream dedupes). Flag `tts_dedupe_sentences=True` in config.py (kill switch). Do NOT buffer more than one sentence (first-audio of sentence 1 stays live; subsequent sentences flush on their boundary).
Tests (≥3): FakeLLM round whose content repeats a sentence → tts tokens contain it once; two DIFFERENT sentences unaffected (order preserved); kill switch off → doubles pass through; final content unchanged.
Files: `diallux/graph/builder.py`, `diallux/config.py`, `tests/test_iter41_quality_debt.py`.
Verification: suite ≥187+3 green; commit.
Dependencies: T0.

### T2 — Filler cap: max ONE engine filler per deterministic pass (commit 2)
Goal: Phase B never stacks 3 fillers in one turn ("One sec — finishing that up. Alright, getting that locked in. Just confirming those details now.").
Design (pin): in `_deterministic_node` PhaseB loop, track `emitted_this_pass` — the filler `break` in the `if writer and step in _PHASEB_SLOW` branch fires at most ONCE per pass (first slow step only). `fillers_said` anti-repeat unchanged.
Tests (≥2): multi-slow-step chain pass → exactly 1 tts filler emitted; abort pass → ≤1 filler.
Files: `diallux/graph/builder.py`, tests.
Verification: suite green; commit.
Dependencies: T1.

### T3 — Mock date-awareness: Brenda converts (commit 3)
Goal: mock `check_availability` serves slots for the REQUESTED `slot_target_date` (lockstep with live endpoint which anchors `_fetch_slots` to the requested day).
Design (pin): in `tests/mock_webhooks.py` handler, parse `slot_target_date` from request args (default "2026-09-04"); render `day_human` via the same day-word logic as the endpoint (today/tomorrow/weekday relative to mock-today 2026-09-04); `slots_human` = `{day_human} at 1 pm or 2:30 pm` (post-iter40 format, NO m/dd); times = DATE at 13:00/14:30 local. Keep per-slot human fields consistent. Tests: request for tomorrow → `slots_human` starts "tomorrow at"; no date → today (unchanged legacy); Brenda-replay: `validate_lead` with `selected_time` "tomorrow at 2:30 pm" + `slot_options` tomorrow-string → contained → PASS (no `unfixable_format`).
Then RE-RUN Brenda + Pedro + Sofia via 3 PARALLEL harness processes; expect Brenda PASS (book), record Pedro (over-book may persist — accepted, T5 candidate).
Files: `tests/mock_webhooks.py`, tests.
Verification: suite green; 3 re-runs logged; commit.
Dependencies: T2.

### T4 — 2 live happy paths REAL bookings (async) + cleanup
Goal: prove commerce + new fixes on the LIVE endpoint with real bookings (Julio directive: "2 happy paths and real bookings, async").
Commands: two parallel `harness.py --personas Maria --slots live --rag --langfuse --max-turns 32` + Susan same (worktree env). After: parse uids from json logs (`final_dvs.booking_uid`); cancel each via Cal.com cancel (Compaction recipe); verify 200.
Verification: ≥1 clean real book per run pair (the closer gate + preferred_time active); bookings cancelled (calendar clean).
Dependencies: T3.

### T5 — T8 live A/B on :8007 + verdict + ASK JULIO (iter40's open gate)
Commands:
```bash
cp /tmp/opencode/uvicorn_8007.log /home/julio/projects/clean_diallux_SDR/research/surgeon/iter40-spike-readback/pre_restart_uvicorn_8007.log
kill 2583320   # verify pid first: ss -ltnp | grep 8007
cd /tmp/opencode/wt-iter41 && set -a && . ./.env && set +a && setsid nohup /home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8007 > /tmp/opencode/uvicorn_8007_iter41.log 2>&1 < /dev/null & disown
```
Julio tunnels (`ssh -N -L 8007:127.0.0.1:8007 julio@46.62.233.228`) and makes ONE mic call.
Post-call (log = source of truth): `grep "final report" /tmp/opencode/uvicorn_8007_iter41.log` → per-turn e2e p50/p90/max; gates: **p50 ≤1.2s, spikes ≤~1.8s, cache ≥58% (Langfuse cache_read), 0 spoken M/D, 0 no_start_time, 0 "12 pm", 0 in-turn doubles audible**; SOP conversation rerun per `full_call_analysys.md` into `research/surgeon/iter41-quality-debt/02_live_t8.md`; verdict line in notes.md; ASK JULIO: merge gates for BOTH branches (`:8006` gpt-5.2 keep/kill too).
Dependencies: T4 (or Julio's availability — T5 can run before T4 if he's ready).

### T6 — Wrap
Goal: `ITERATIONS.md` iter41 ledger; `scripts/git-tree.sh` after merges (owner-approved only); keyhound before any push; docs commit+push main.
Dependencies: T5.

## Validation Plan (end-to-end)
1. T1: FakeLLM dedup tests green; suite green.
2. T2: filler-cap tests green; suite green.
3. T3: mock date-aware tests green; Brenda re-run converts (book); suite green.
4. T4: ≥1 real book per pair, both cancelled, calendar clean.
5. T5: live p50 ≤1.2s / spikes ≤1.8s / cache ≥58% / 0 M/D / 0 no_start_time / no audible doubles; SOP report; ASK JULIO.
6. Ledger + tree updated; no merges without Julio.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Pedro over-book retrain (day-anchor before confirm) | Separate prompt/flow change; candidate for iter42 with fresh evidence (6/8 historical) |
| Prompt changes beyond what's shipped | Owner gate: only verbatim-approved lines |
| Async harness infrastructure (built-in parallel batch mode) | Infra work; parallel separate processes proved sufficient this session |
| gen p50 ≤1.2s deep prefix work | iter31 carry-forward; T8 live decides if still open |
| `time_of_day` search param on endpoint | Superseded: humanized preferred_time resolver (7094bd8) already answers it |
| Services cutover (systemd → fork `services/`) | Existing NEXT_STEPS owner-gated item |
| History carrying model's raw doubled output (dedup only at TTS layer) | Chosen minimal scope; if caller-model conditioning shows echoes, revisit |
