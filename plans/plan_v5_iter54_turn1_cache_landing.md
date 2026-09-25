# PLAN — v5 iter54: turn-1 cache landing — solve the cold-start latency riddle (owner picks ONE option)

## Meta
- Date: 2026-09-17 (authored from the iter52 session forensics; owner-ordered: "solve the riddle with options")
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: make the prompt-cache prefill LAND EVERY SINGLE TIME (owner: "I don't need a redesign, I need it to land every single time") — turn-1 and transition entries must stop reading cold. NO redesign: the architecture (warm → register → ride) stays; the options below only change the clock or add the fallback round.
- Status: **PLAN ONLY (not started — awaits owner option pick from the OPTIONS table)**
- Branch discipline: work happens on a NEW branch `engine/iter54-turn1-cache-landing` cut from `engine/iter52-industry-pin` @ `a36bdd7` (NOT from main — see Resolved Decisions). ZERO changes to main. Zero merges without owner say-so (LAW 0 v3).

## Compaction Context (everything learned — pin, do not re-derive)

### The riddle, in one paragraph
The engine's cache architecture (prefill the payload → provider registers it → rounds ride the prefix) works when the provider still holds recently-registered prefixes and fails at every COLD start: turn-1 lite rounds read `cache_read=0` and pay ~1,000 ms TTFT (vs 679–840 cached), and 3–5 transition entries per call race their prefill and lose (~10–20% cache-0 rounds in every run, warm or cold provider). The user-facing symptom: first turn of a call and some topic switches answer ~300–400 ms slower than the 600–800 ms design band.

### The measured evidence table (ledger `research/surgeon/iter48-rag-truth/ledger.db`, runs imported per SQL SOP)
| Run | Commit | Config | turn-1 (ttft/cache) | cache-0 | Note |
|---|---|---|---|---|---|
| happy-mvp-a | `1f15e8b` | lite ON, warm-greeting 0 (off) | 2,258 / 0 | 6/36 | coldest start of 09-16 — slowest TTFT on record |
| happy-chat-a | `fc2fa2f` | lite ON, harness `--warm-greeting-ms 3000` | 807 / 1,664 | 5/32 | session 03:41, 43 min after mvp-a |
| happy-chat-b | `fc2fa2f` | same | 809 / 1,664 | 3/25 | 03:45 (+4 min) |
| happy-chat-c ×4 | `fc2fa2f` | same | 711/691/722/608 all /1,664 | 2–4 each | 03:50–54 (+1 min apart) |
| battery-iter52 call 1 (Maria) | `0f2128d` | lite ON, warm 3000, cold | 790 / **0** | **5**/31 | first call after 3.5 h gap |
| battery-iter52 calls 2–4 | `0f2128d` | same, 68 s apart | 695–840 / 1,664 | 2,2,4 | rode lite-head cross-call residue |
| **happy-f** (09_sql_report_iter48b.md) | `d1dd5a9` | **FIRST_TURN_LITE=false** (turn-1 = FULL round) | **792–810 / 2,688 ×4/4** | 7/144 | the "nailed it" run — no lite round existed |
| happy-g | `033f742` | lite ON + LITE_NOOP_TOOL + M12 | 782/809/679 = 1,664 ×3; 1,187/0 ×1 | — | 4 back-to-back |
| happy-plumber-a (Mike Rourke persona) | `a36bdd7` | lite ON, warm 3000, COLD | **1,047 / 0** | 5/25 | single call, 14 h idle |
| happy-plumber-b (same, rerun) | `a36bdd7` | same | **998 / 0** | 5/31 | ~10 h later, cold again |

### The five root causes (all verified in code, file:line from `/tmp/opencode/wt-iter52/engine/diallux/`)
1. **Provider registers cache on request COMPLETION, not TTFT.** Warm = TTFT (~1.3–2.2 s) + up to 64 discarded output tokens → ~2.5–4 s total to serving. All engine windows were budgeted at TTFT scale. (`llm.py:234` `warm()`; `builder.py:399-454` `_warm`)
2. **The windows lose by an order of magnitude:** greeting window 3.0 s (marginal — lost both cold probes), transition entry EOT wait 0.5 s (`config.py:188 prewarm_entry_wait_eot_ms`), mid-turn 0.1 s (`config.py:183`), RAG await 0.06 s (`config.py:234`). Transition trace: entry rounds fired 3–18 ms after the post-execute warm — that warm structurally CANNOT serve its own entry; the entry's only real prefill is the detection warm, which had 0.1–2.2 s lead and needs ~1.2–1.5 s (cutoff measured: Discovery ~1.1 s miss, Closer ~2.1 s hit, Offer ~0.3 s miss, contact_details ~1.9 s hit, ConfirmSlots ~1.4 s hit, Closing ~0.5 s miss).
3. **No lock between warm and round.** `_await_warm` (`builder.py:471-489`) uses `asyncio.shield` + `wait_for`; on timeout the warm keeps running and the round fires anyway (`builder.py:1364-1392`) → two concurrent same-prefix provider requests → the round can never hit the uncommitted prefix. Deliberate ("never a stall"), but it converts the miss into a guaranteed cold read.
4. **Two independent cache trees.** Lite prefix ([lite head]) and full prefix ([tools][head][state-block]) share no bytes (`builder.py:412-421` lite warm vs `:423-454` full warm). Turn-1's traffic never helps transitions register and vice versa. Also: gpt-5.4 caches ONLY tool-bearing requests (FIND-5) — lite carries `LITE_NOOP_TOOL` so warm==hot shape.
5. **Transition prefixes are call-unique** (history inside the payload differs call to call) → provider residue can NEVER cover a transition entry. Only the turn-1 lite head is byte-identical across calls → residue covers it when calls run minutes apart. This is why batteries look perfect (calls 2+) and every cold start (mvp-a, battery call 1, plumber A/B) misses turn-1 + 2–5 transitions.

### Riddle solved — the one-sentence verdict
*"Working as designed, failing as intended"*: the design assumed prefill registration happens at TTFT-scale and that residue covers the gap; registration actually costs ~2.5–4 s and residue only exists back-to-back — so every cold turn-1 and ~10–20% of transition entries structurally miss, and the numbers are the sum of measured parts, not anomalies.

### Where the evidence lives (all read-only paths)
- Ledger: `research/surgeon/iter48-rag-truth/ledger.db` (rounds/rag tables; runs `happy-plumber-a`/`b` imported @ `a36bdd7`)
- Traces: Langfuse `8e9acde9b4ee9b21d05d1a727a7e87a3` (plumber A), `82d1b826691df3f8b2fda519ec0de313` (plumber B)
- Reports: `research/surgeon/iter48-rag-truth/09_sql_report_iter48b.md` (happy-f recipe + FIND-5), `.../05_battery_report.md`, `research/surgeon/iter52-industry-pin/01_industry_pin.md` (battery-iter52, warm 3000)
- Session findings recorded in this plan only (no surgeon report yet — T5 writes it)

### Git state at plan time
- main @ `4559a33` (ONE commit — the MVP merge; docs collapsed). Branch `engine/iter52-industry-pin` @ `a36bdd7` (ONE commit: iter52 feature + docs + LAW 0 v3 + Mike Rourke persona). LAW 0 v3 in force (docs ride the branch, amend don't stack). 5 `engine/docs-archive/*` labels pin all old doc states. GitHub `origin` stale (shows pre-rewrite history — force-push pending, owner-gated). Untracked `scripts/call_ledger.py` (PT-50, owner-gated). iter53 hygiene plan (`plans/plan_v5_iter53_git_hygiene_rag_next.md`) exists, T1–T7 unexecuted, INDEPENDENT of this plan.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| **Branch cut from `engine/iter52-industry-pin` @ `a36bdd7`, NOT from main** | apples-to-apples with the plumber runs (ledger runs pinned `a36bdd7`); the warm/await code under test lives in that builder.py; main has no iter52 code |
| **NO redesign of the warm→register→ride architecture** | owner directive: "I don't need a redesign, I need it to land every single time" |
| **Options are mutually exclusive in spirit — owner picks ONE for iter54** | house law: one variable per iteration |
| **Nothing is trimmed from `agent/llm.json` prompts** | verified: no "play along/small talk" rule exists to trim; acknowledgment rules are load-bearing for all rounds; the fallback hint is AUTHORED fresh (~120 tok); trimming would not help anyway (1,700→1,580 tok head, same ~1 s cold cost) |
| **The fallback (if picked) never chains** — round after a fallback goes full-cold if it also misses | fallback must never be worse than today; no fallback loops |
| **Prefill observability lands BEFORE any option execution** | no fix can be sized without the measured warm-completion distribution; everything else is guessing (how the 500 ms got picked) |
| Turn-1 TTFT gate stays ≤1,000 ms; steady p50 ≤950; RAG await ≤+60 ms | existing SOP gates unchanged |
| `scripts/keyhound` before any push; **no push in normal flow** (GitHub sync is a separate owner ASK) | LAW 0 v3 + standing session rule |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| **Owner picks ONE option from the OPTIONS table** | owner, after reading this plan |
| Turn-1 wait ceiling if O3 chosen (1 s? 2 s? never?) | owner |
| Fallback content if O2: mini-head scope (identity+voice ~450 tok vs +2 hard constraints ~600 tok); generic vs +pin block; DB-chunk variant in/out | owner |
| `engine/iter52-industry-pin` merge ASK (standing, separate) | owner |

## Environment & Dependencies
- Engine worktree: `/tmp/opencode/wt-iter52` (branch `engine/iter52-industry-pin` @ `a36bdd7`); venv = symlink to `/home/julio/projects/clean_diallux_SDR/engine/.venv` (3.12.3). pip trap: always `<venv>/bin/python -m pip`.
- New branch: `git -C /tmp/opencode worktree add /tmp/opencode/wt-iter54 -b engine/iter54-turn1-landing engine/iter52-industry-pin` + symlink venv + copy `.env` (same as iter52 setup).
- Ledger: `research/surgeon/iter48-rag-truth/ledger.db` — import via `scripts/live_sql.py import --window "HH:MM-HH:MM" --run <name> --commit <sha> --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (RUN FROM THE MAIN CHECKOUT's engine dir; the script's ROOT resolves wrong from worktrees — TRAP, hit twice this session).
- Langfuse SDK: `scripts/lf.py` (`_traces/_obs`), keys in `engine/.env`. Percentiles: `scripts/latency_pull.py --run <run>`.
- Harness: `engine/tests/llm2llm/harness.py` — flags: `--personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini`. Personas: 26 (Mike Rourke added @ `a36bdd7`).
- Provider: gpt-5.4 agent (env `engine/.env`), prompt-cache behavior: tool-bearing requests only, registers on completion. NO sqlite3 CLI — use `.venv/bin/python -c "import sqlite3…"`.
- NEVER touch: live services :8000–:8006, owner port :8007, production agent IDs, `kb_chunks` (SELECT-count only), Cal.com event `3801235` (REAL — the harness runs `--slots mock` by default: bookings are the mock's hardcoded `BOOKING_UID`, verified, no real booking created — still cancel any real booking if a live-slots run is ever executed).

## Architecture (the race, and what each option changes)
```
CURRENT (the riddle):
  warm fires (T+0) ──provider── TTFT 1.3-2.2s ── +64 dead tokens ──► REGISTERED (~2.5-4s)
  entry round fires (T+0.1-2.2s), waits 0.5s/0.1s ──► warm still pending ──► round goes out
  → CONCURRENT same-prefix requests → round reads COLD (cache 0) → TTFT ~1,000ms+
  → warm registers a beat later → serves the NEXT round (the alternation)

O1 FIRST_TURN_LITE=false : turn-1 becomes a FULL round riding the greeting full-warm
                           (happy-f recipe: 2,688×4/4 @792-810ms — already proven 4/4)
O2 fallback mini-load    : on warm-pending at entry → speak a ~700-900 tok mini-round
                           (own MINI HEAD + hint, NO tools, NO state head) instead of
                           the cold full round; warm lands; next round rides cache
O3 honest waits          : entry waits sized to measured completion p99 (costs 0 when
                           warm already done; turn-1 ceiling = owner decision)
O4 serialize             : round waits for warm completion, bounded cap, then goes —
                           deterministic slower-but-cached; lottery removed
O5 shrink warm tail      : lite warm completion tokens 64→ smaller (fewer dead ms on
                           the registration path); gate: zero rejections (16-tok history)
```

## OPTIONS TABLE (owner picks exactly ONE — O1 is also the cheapest proof)
| ID | Option | Evidence it works | Cost/risk | First step | Gate |
|---|---|---|---|---|---|
| O1 | `FIRST_TURN_LITE=false` (one config flag, `config.py:76`) | happy-f @`d1dd5a9`: turn-1 2,688×4/4 @792–810 ms, cold-ish start | loses the lite turn-1 shape (turn-2 shape work from iter49 T6/M12 rides lite); turn-1 heavier payload (~2.7k vs 1.8k) | 1-command A/B: env `FIRST_TURN_LITE=false`, rerun plumber persona cold | turn-1 = 2,688 floor + ≤900 ms TTFT cold; suite green |
| O2 | **Fallback mini-head "2nd lite load"** (owner's design): on warm-pending at entry, speak a ~700–900 tok small-talk round instead of the cold full round | structure mirrors existing lite path (no tools ⇒ speech-only by construction); cold prefill scales with size (~0.4–0.6 s at 800 tok vs ~1 s at 1.8k) | +1 round per genuine miss (~5/call worst cold, 0 warm); fallback is cold too — MUST be structurally faster or the cure is worse; state-machine round-budget tolerance must be pinned | author MINI_HEAD + HINT (new md, ~450–600 tok), wire trigger behind flag `prefill_fallback=True` (default OFF), zero behavior change until probe | fallback TTFT ≤700 ms cold; fires ONLY on misses (rate ≈ cache-0 rate); next round cache>0; transcripts clean; turn caps respected |
| O3 | Honest waits — entry waits = measured warm-completion p99 (`config.py:183/188` values) | ledger: every entry with ≥1.2–1.5 s warm lead HIT; the wait returns INSTANTLY when the warm is done (steady-state cost ~0) | turn-1 may wait 1–2 s on the unluckiest cold starts (owner ceiling UNSET — blocked); transitions wait up to ~3 s before speaking (owner must accept the pause) | log warm fired/completed + wait outcome per entry (T0), measure distribution, set `prewarm_entry_wait_*` to p99 | cold probe: turn-1 cache ≥1,664, transitions ≥2,688, zero cache-0 on first-of-kind rounds; steady TTFT p50 ≤950 (no warm-provider regression) |
| O4 | Serialize warm→round (round sends only after warm completes, bounded cap) | deterministic; removes the concurrent-request physics entirely | converts lottery into a capped wait — same pause as O3 but mandatory-shaped; biggest behavior change | same observability as O3, then gate the round send on warm-done | same as O3 + no round ever sends while its warm is in flight (assert in trace) |
| O5 | Shrink the lite warm's completion tail (64 → smallest clean value) | 64-token bump (`prewarm_max_completion_tokens`) was for REJECTION safety on the FULL warm (16-tok 400s in happy-e); the LITE warm has ONE noop tool | registration gain ~0.5–1.5 s; must prove zero `prewarm failed` warnings | sweep warm tokens 64→32→16 on lite-only, probe registration delta | zero prewarm failures ×20 rounds; registration inside O3's budget |
| — | **Recommended combo (if owner wants fastest landing with least risk): O5+O2** — shrink the dead tail, and where it still misses, speak small talk instead of silence | — | — | — | — |

## File Map
| File (absolute) | What changes | N/E/D |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py` (on new branch) | O-dependent: flag `prefill_fallback` (O2) / wait values (O3) / warm tokens (O5) — default OFF/unchanged until probe | Edit (branch) |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` (on new branch) | O-dependent: fallback round path (O2) — trigger at `_make_state_node` entry + `_await_warm` outcome; warm observability log (all options need it: fired/completed/wait-outcome per entry) | Edit (branch) |
| `/home/julio/projects/clean_diallux_SDR/engine/agent/prompts/prefill_fallback_head.md` (O2) | NEW mini-head (~400–600 tok: identity + voice rules [+2 hard constraints per owner answer]) + the hint text (~120 tok) — authored fresh, main `llm.json` untouched | New (branch) |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter54_prefill_landing.py` | pins: trigger only on warm-pending; no-tools fallback shape; no-chaining; next-round-cache assertion (integration via offline replay) | New (branch) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter54-turn1-landing/01_cold_start_probe.md` | the measured truth (T1) + option execution results | New (gitignored) |

## Deploy Rules
- NO code changes to main. Branch `engine/iter54-turn1-landing` cut from `a36bdd7`; one variable (the owner-picked option); suite green (`cd /tmp/opencode/wt-iter54/engine && .venv/bin/python -m pytest tests -o addopts="" -q`, expect 333+); cold-start probe; battery rerun; ledger import; report; ASK.
- Docs (this plan, PT rows) already committed per LAW 0 v3 — further plan versions amend, never stack.
- Kill switches: every option lands behind a config flag defaulting to CURRENT behavior; `RAG_PIN_INDUSTRY`/`STATE_ENTRY_LITE`/`FIRST_TURN_LITE` kill switches untouched.
- Battery after any change: cancel ALL test bookings (Cal.com `3801235` REAL); harness runs use `--slots mock` (no real booking).
- Before any push: `scripts/keyhound`. No push without owner say-so.

## Tasks (in order)
### T0 — Branch + prefill observability (no behavior change)
Goal: make warm fired/completed + wait outcome VISIBLE per entry (today: invisible — the blind spot that hid the riddle).
Files: `diallux/graph/builder.py` (`warm_prompt_cache`/`_warm` completion log; `_await_warm` outcome log), `diallux/observability/tracer.py` (span `warm` with fired/completed/ms), `diallux/config.py` (log flag).
Commands: cut worktree+branch (see Environment), suite green.
Verification: one plumber-persona run; Langfuse shows warm spans with completed-at; `git diff a36bdd7` shows only the logging.
### T1 — Cold-start baseline probe (flag OFF, current behavior)
Commands (full):
```bash
cd /tmp/opencode/wt-iter54/engine && set -a && . ./.env && set +a
.venv/bin/python tests/llm2llm/harness.py --personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini
cd /home/julio/projects/clean_diallux_SDR/engine && set -a && . ./.env && set +a
.venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run cold-probe-a --commit <sha> --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db
.venv/bin/python scripts/latency_pull.py --run cold-probe-a
```
Verification: turn-1 ttft/cache + per-entry warm-completed-vs-entry table from the new warm spans; numbers match the plumber band (turn-1 ~1,000/0). This is the plan's measured baseline.
### T2 — Execute the owner-picked option (BLOCKED until pick)
Per the OPTIONS row: exact first step + gate listed there. Suite green + the row's gate.
### T3 — Cold-start probe, option ON + battery
Same commands as T1 (run `cold-probe-b`), plus a warm-provider 4-call battery (staggered 15 s, Maria/Danny/Susan/Marcus) for the no-regression gate. Report to `research/surgeon/iter54-turn1-landing/01_cold_start_probe.md`.
### T4 — Verdict + closeout
Gates from the OPTIONS row all green → ITERATIONS.md ledger line + PENDING_TASKS PT-51 status flip + report to owner with the ASK list (merge iter52? merge iter54? keep flag default?).

## Validation Plan (end-to-end)
1. T0: warm spans visible in Langfuse; no behavior delta (cache-0 pattern identical to plumber baseline).
2. T1: baseline pinned with numbers in the report.
3. T2: option's own gate (from the table) met.
4. T3: cold probe — turn-1 cache ≥1,664 (O1: 2,688) + every transition entry ≥2,688 (or fallback TTFT ≤700 for O2 misses with next-round cache >0); warm battery: steady p50 ≤950, cache-0 ≤ the battery band (≤3/call).
5. T4: ledger lines + report + ASK list.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merging `engine/iter52-industry-pin` → main | standing owner ASK, separate decision |
| The iter53 hygiene plan (T1–T7) | independent; can run before or after this plan |
| Time-to-first-AUDIO gate re-definition (TTFT + sentence tail + TTS gate) | surfaced this session; needs its own owner decision + harness change; NOT the riddle |
| The fallback DB-chunk variant (fallback + one relevant chunk) | owner said defer unless O2 picks it (question 3 open) |
| Trimming the 1.7k lite head below 1k tokens | content-design decision (identity vs constraints trade), separate from the landing problem |
| Provider-side cache mechanics research (TTL, registration latency guarantees) | black box; we measure empirically via T0 spans instead |
| Removing `FIRST_TURN_LITE`/`STATE_ENTRY_LITE` kill switches | untouched; O1 uses the existing flag as designed |
