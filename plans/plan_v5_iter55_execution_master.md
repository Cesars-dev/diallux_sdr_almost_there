# PLAN — v5 iter55 EXECUTION: surgeon master plan (TTS-era truth + turn-1 ammo)

## Meta
- Date: 2026-09-18
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: execute the ALREADY-APPROVED surgeon master plan — Commit 0 → C0.5 (Telegram) → C1 (T0 observability) → live-verify → C2 (lite-cap split) → T1–T7. Code analysis is DONE; the four surgeon documents are the implementation spec. This plan = session context + execution protocol (shorter per owner directive).
- Status: **APPROVED BY OWNER 2026-09-18 ("let's do the master plan") — fresh execution session starts here.**
- Branch: `engine/iter55-tts-era-turn1-ammo` — worktree `/tmp/opencode/wt-iter55`, cut from `engine/iter52-industry-pin` @ `054af7b`. **Code diff is ZERO at plan time** (only untracked `tasks/` surgeon docs). Commit 0 commits them.
- Source plans: `plans/plan_v5_iter55_tts_era_turn1_ammo.md` (the iter55 plan, unchanged) + surgeon package (below). This plan does NOT supersede the iter55 plan — it operationalizes it.

## REQUIRED READING (in order, before ANY edit)
1. `/tmp/opencode/wt-iter55/tasks/surgeon/iter55-tts-era-turn1-ammo/04_master_plan.md` — THE execution sequence (approved)
2. `…/01_audit.md` — code truth with line numbers (findings F-01…F-09)
3. `…/02_action_plan.md` — exact code patterns per file (§1a–1e are the C1 implementation spec)
4. `…/03_cross_reference.md` — why the plan differs from the source plan (CR-1…CR-6)
5. Repo law: `/home/julio/projects/clean_diallux_SDR/AGENTS.md`

## SESSION START PROTOCOL (fresh agent — execute in order)
1. Read the 5 items above.
2. Verify worktree intact: `git -C /tmp/opencode/wt-iter55 log --oneline -1` → `ec650fa` (owner-approved surgeon-package commit; parent `054af7b`) (if the worktree is missing: recreate per the iter55 source plan's Session Start Protocol — `git -C /tmp/opencode worktree add /tmp/opencode/wt-iter55 -b engine/iter55-tts-era-turn1-ammo engine/iter52-industry-pin`; then `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter55/engine/.venv` and `cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter55/engine/.env`; NOTE: surgeon docs then live ONLY here in this plan — copy them back from the paths above if missing from the worktree).
3. Suite baseline: `cd /tmp/opencode/wt-iter55/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → expect **332 passed, 1 failed** (`test_happy_path_present_and_first` — F-01, Rourke ordering). After Commit 0: **333 green**.
4. Langfuse: `cd /tmp/opencode/wt-iter55/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/lf.py health` → server OK expected.

## Compaction Context (session summary 2026-09-18 — pin, do not re-derive)

- **Owner instruction chain:** "execute T0 to T2 on both chat and voice, branch as iter55" → surgeon-framework planning → MASTER PLAN READY → STOP → **approved**: "let's do the master plan but on another session … new plan is basically context + master plan". Each HITL step = **Telegram ping** via the bot ON FILE (do not create a new bot).
- **Branch state:** `engine/iter55-tts-era-turn1-ammo` @ `054af7b`, zero code touched. Surgeon docs written but UNCOMMITTED at `/tmp/opencode/wt-iter55/tasks/surgeon/iter55-tts-era-turn1-ammo/` (Commit 0 commits them).
- **Suite:** 332/333 — F-01: the iter52 amend `054af7b` appended Rourke (happy-path persona) at the END of `PERSONAS` (`tests/llm2llm/personas.py:444-477`), breaking `test_happy_path_present_and_first` (SOP order pin). Fix = reposition the dict into the happy block after Marcus; zero text changes.
- **Code truth (audit-verified):** warm machine = `warm_prompt_cache` (builder.py:365-397) → `_warm` (399-469) → `StreamingLLM.warm` (llm.py:234-244); `warm()` SWALLOWS exceptions (F-08 — done-callbacks would be blind; fix = un-swallow, all 3 callers verified inside try/except); `prewarm_max_completion_tokens` is baked into the ONE shared `_warm_llm` twin (llm.py:205-211 — F-07: T3 sweep-as-written would cap BOTH shapes; fix = split knob + lite twin); entry-ack awaits NOTHING (`pass`, builder.py:1382); `_await_warm` outcomes = landed/timeout/already_done/**no_task**; greeting has NO span; `Tracer.span` (tracer.py:143-153) already exists — **tracer.py needs ZERO changes** (CR-3).
- **Banked evidence (read-only, saved):** `research/surgeon/iter55-era-truth/live_8000_snapshot_0918.prom` (:8000 deployed-iter40 era, 47 turns: e2e 2,201 ms, stt→llm 1,914, llm→tts 288 — LLM dominates, TTS clean) · `iter52_8005_snapshot_0918.prom` (:8005, 38 turns, e2e 2,749 — population UNVERIFIED, not comparable raw; F-04) · ledger ack analysis: turn-1 p50 866/p90 975 (n=14, warm provider), lite-class p50 862/p90 1,221, heavy p50 888/p90 1,079, cache floors {1664, 2688, 3712, 4736}.
- **Telegram bot ON FILE** (do NOT create): `/home/julio/projects/video_strategy/.env` → `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`; reference pattern `send_telegram()` in `/home/julio/projects/video_strategy/execution/clients.py`.
- **Langfuse:** server OK 3.172.1; micbridge trace `e2aacc99471a` verified queryable; `43d83d0815c9` NOT resolvable (F-03 — re-resolve before T2 use).
- **Done vs remains:** audit+plan+cross-ref+master plan = DONE. NOTHING executed. Remains = Commit 0 → T7 per `04_master_plan.md` execution table.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Master plan APPROVED 2026-09-18; execute its sequence C0→T7 verbatim | Owner say-so; surgeon method followed to the letter |
| T0 = observability ONLY, no behavior change; `warm_observability: bool = True` flag gates spans | Framework rule: airtight plan first; one-flag rollback |
| llm.py edit in C1 = un-swallow warm exceptions (NOT timestamps) | F-08; timestamps live in builder's done-callback (CR-3) |
| tracer.py UNCHANGED in T0 | `Tracer.span` already suffices (audit A6) |
| T3 sweep REQUIRES C2 first (split `prewarm_lite_max_completion_tokens`) | F-07: shared twin would cap full warm → 400-rejection history re-exposed |
| Telegram pings at HITL gates: T1 start+table, T2-B scheduling, T4-miss verdict, T6 copy, T5 results, T7 ASKs | Owner directive 2026-09-18; bot on file; ping failure NEVER blocks work (tracer contract) |
| NO KB loads at/before call start = owner directive | iter55 source plan Resolved Decisions (physics: warm_rag drop degrades turn-2 lane-B embed — keep/drop = owner HITL after T1 numbers) |
| O3/O4 multi-second waits DEAD | Gates: TTFT ≤1,100 / hear ≤1,400; ack path has no wait knob by design |
| Live :8000–:8006 NEVER restarted; production agents never touched | LAW 0 + repo law |
| No merges/pushes without owner say-so; `scripts/keyhound` before any push | LAW 0 |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| T2-B fresh mic sessions (owner at browser, 6 short calls) | Telegram ping when T2 option B is chosen |
| warm_rag / KB-resolve keep-drop-reorder | Owner, after T1 greeting-span numbers |
| Filler copy approval ("one moment, taking notes") | Owner ping, ONLY if T4 misses |
| Re-resolve Langfuse trace `43d83d0815c9` (full ID) | `lf.py traces --name micbridge --hours 340` listing |
| Merge iter52 / merge iter55 / `FIRST_TURN_LITE=false` default / cutover authorization | Owner, T7 ASK pings |

## Environment & Dependencies
- Worktree: `/tmp/opencode/wt-iter55` (branch `engine/iter55-tts-era-turn1-ammo`); venv symlink `/tmp/opencode/wt-iter55/engine/.venv` → main checkout's `.venv` (python 3.12.3; ALWAYS `<venv>/bin/python -m pip`).
- Suite: `cd /tmp/opencode/wt-iter55/engine && .venv/bin/python -m pytest tests -o addopts="" -q` (333 baseline after C0; +~10 pins after C1; +~4 after C2).
- Harness: `cd /tmp/opencode/wt-iter55/engine && set -a && . ./.env && set +a && .venv/bin/python tests/llm2llm/harness.py --personas Rourke --rag --langfuse --warm-greeting-ms 3000 --max-turns 48 --caller-model gpt-4o-mini`.
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; import TRAP: run `scripts/live_sql.py` from the MAIN checkout's `engine/` dir, NEVER the worktree. NO sqlite3 CLI — `.venv/bin/python -c "import sqlite3…"`.
- Cold discipline: true-cold probes need ≥3.5 h provider idle (residue TTL proven ≥43 min, dead by 3.5 h); letters a/b; NO back-to-back cold probes.
- Metrics: `curl http://localhost:8000/metrics` (live deployed era — NEVER restart) · `http://localhost:8005/metrics` (iter52 instance; population unverified).
- Telegram: creds in `/home/julio/projects/video_strategy/.env`; at execution copy values into `/tmp/opencode/wt-iter55/engine/.env` (gitignored — NEVER commit). New helper `engine/scripts/hitl_ping.py` (C0.5), fail-safe.
- Cal.com event `3801235` is REAL — cancel ALL test bookings after every battery.

## Architecture
See surgeon `01_audit.md` §A (call-start sequence, warm machine, await sites, greeting path — all line-pinned) and the source iter55 plan's Architecture block. One line: `call start → KB-resolve (≤2s) → warm_rag (async) → FULL+LITE warm (fire-and-forget) → greeting TTS (~4.5-5 s) → turn-1 (lite, awaits lite-warm ≤500 ms) → …`; T0 adds spans (`warm:{key}`, `await_warm`, `greeting:first_audio`, `greeting`) with ZERO behavior change.

## File Map
| File (absolute) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter55/tests/surgeon/…/0*.md` → committed as `tasks/surgeon/iter55-tts-era-turn1-ammo/` | the 4 surgeon docs | Commit in C0 |
| `/tmp/opencode/wt-iter55/engine/tests/llm2llm/personas.py` | Rourke dict → happy block (after Marcus) | E (C0) |
| `/tmp/opencode/wt-iter55/engine/scripts/hitl_ping.py` | Telegram ping helper (env TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID; fail-safe) | N (C0.5) |
| `/tmp/opencode/wt-iter55/engine/diallux/config.py` | +`warm_observability: bool = True` (C1); +`prewarm_lite_max_completion_tokens: int = 64` (C2) | E |
| `/tmp/opencode/wt-iter55/engine/diallux/graph/llm.py` | warm(): remove internal try/except (C1); +`_warm_llm_lite` twin + `lite` param (C2) | E |
| `/tmp/opencode/wt-iter55/engine/diallux/graph/builder.py` | `_warm_diag` + done-callback warm spans + `_await_warm` outcomes (C1) | E |
| `/tmp/opencode/wt-iter55/engine/diallux/media/session.py` | `_greet` anchors + `greeting:first_audio` + `greeting` drain span (C1) | E |
| `/tmp/opencode/wt-iter55/engine/tests/test_iter55_observability.py` | ~10 pins (C1) | N |
| `/tmp/opencode/wt-iter55/engine/tests/test_iter55_splitcap.py` (or pins inside test_iter55_observability.py) | lite-twin routing pins (C2) | N |
| `/tmp/opencode/wt-iter55/engine/agent/prompts/prefill_fallback_head.md` + `engine/tests/test_iter55_fallback.py` | filler (ONLY if T4 misses; owner-approved copy first) | N (C3) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter55-era-truth/01_era_and_warm_p90.md` | T1/T2/T7 measured-truth report (gitignored evidence dir — snapshots already banked there) | N (gitignored) |

## Deploy Rules
- ALL engine work on `engine/iter55-tts-era-turn1-ammo` in `/tmp/opencode/wt-iter55`; suite green before any probe; ONE variable per probe.
- Never touch: live :8000–:8006 (read-only `/metrics`), production agents, `kb_chunks` (SELECT-count only), no merges/pushes without owner say-so (LAW 0), keyhound before any push.
- Owner-ordered exception for voice tests: foreground uvicorn, `127.0.0.1`, free port — never background, never the live ports.
- Cancel ALL test bookings after batteries (Cal.com `3801235` REAL).
- Surgeon docs + this plan ride the branch (LAW 0 v3); iter55 source plan in `plans/` stays on main, unamended.

## Tasks (in order) — execute per `04_master_plan.md` §EXECUTION SEQUENCE (steps 0→10); the surgeon `02_action_plan.md` §1a–1e is the C1 implementation spec. Essentials:
### T0a — C0: fixtures + docs
Move Rourke into happy block; commit surgeon docs + personas fix on the branch. Verification: suite **333 green**; `git diff 054af7b -- engine/diallux/` still empty.
### T0b — C0.5: Telegram ping
`engine/scripts/hitl_ping.py` per 02 §"Telegram HITL wiring". Verification: test ping lands in Julio's chat; ping failure = log-and-continue.
### T0c — C1: T0 observability
Implement EXACTLY 02 §1a–1e (config flag; llm un-swallow; builder diag/done-callback/await outcomes; session `_greet` spans; new pin file). Verification: suite 333+new green; every new span fail-safe.
### T0d — C1 live verify (ping at start)
CHAT: 1 harness run → `warm:Intake`, `warm:lite:Intake`, `await_warm` spans in Langfuse. VOICE: 1 mic-bridge session (owner-assisted) → `greeting:first_audio`, `greeting`. Verification: spans present both channels; `git diff 054af7b -- engine/diallux/` = observability-only.
### T0e — C2: split lite cap
`prewarm_lite_max_completion_tokens=64` + `_warm_llm_lite`. Verification: pins green; default = byte-exact current behavior.
### T1 — measured truth (LIVE — ping at start + at table delivery)
Harness warm-span runs + true-cold `cold-probe-b` (≥3.5 h idle) + ledger import (MAIN checkout). Deliverable: `01_era_and_warm_p90.md` — warm-completion p50/p90 × {lite, full} × {cold, warm}; ack p50/p90; ≥10 lite + ≥10 full samples.
### T2 — era A/B (HITL)
Option A: existing micbridge traces (re-resolve `43d83d0815c9`). Option B (owner GO): mic sessions ×2 personas ×3 calls. Deliverable: era-0 vs era-52 same-path table.
### T3 — O5 sweep (LIVE, autonomous, pinged) — AFTER C2
`PREWARM_LITE_MAX_COMPLETION_TOKENS=32` then `=16` (env prefix, unset = rollback). Gate: zero warm failures ×20 lite; registration ms delta from T0 spans.
### T4 — turn-1 ammo (LIVE, true-cold ×4, pinged)
Sanity: T0 spans show greeting FULL warm completes BEFORE turn-1 fires. `FIRST_TURN_LITE=false`, calls `ammo-a…d`, ≥3.5 h idle. Gate: turn-1 cache ≥2,688 ×4/4 AND TTFT ≤900 ×4/4. On miss: ping failure-mode verdict + decision ask.
### T5 — cold probe + battery (LIVE)
`cold-probe-b` + `warm-battery-iter55` (Maria/Danny/Susan/Marcus, 15 s stagger; cancel ALL test bookings). Gates: cache-0 ≤3/call; p50 ≤950; first-3 ≤900; hear ≤1,400. Ping results.
### T6 — fallback filler (CONDITIONAL, owner copy approval first)
Per 02 Commit 3. Gate: fires only warm-pending; ≤700 ms cold; no chaining; next-round cache>0; default OFF.
### T7 — verdict + closeout (pinged ASKs)
Report `01_era_and_warm_p90.md` + ITERATIONS.md line + PT-51/PT-52 flips. ASKs: merge iter52? merge iter55? `FIRST_TURN_LITE=false` default? **cutover authorization**.

## Validation Plan (end-to-end)
1. C0: 333 green, zero engine-code diff.
2. C1: suite green + pins; spans in Langfuse on BOTH channels; `warm_observability=False` → zero new spans.
3. C2: default byte-exact; sweep only lite.
4. T1: warm-completion table exists (the never-measured number).
5. T2: era table, same-path delta decomposed.
6. T3: zero-rejection ×20 + measured registration delta.
7. T4: turn-1 ≤900 ms cold ×4/4, cache ≥2,688.
8. T5: battery no-regression.
9. T7: report + ASK list answered by owner.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Merging iter52/iter55, cutover execution | Owner ASKs (T7) — never agent-side |
| iter53 hygiene | docs-only, independent |
| warm_rag keep/drop | owner HITL after T1 numbers |
| EOT wait ceiling raise | only if T4 misses (data-fed ask) |
| O3/O4 | dead under the 1,100/1,400 gates |
| F-02 config.py duplicate block | hygiene only, logged in audit — not touched |
