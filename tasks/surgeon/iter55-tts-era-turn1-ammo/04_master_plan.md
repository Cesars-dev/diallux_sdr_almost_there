# 04 — MASTER PLAN — iter55: production-era truth + turn-1 "ammo locked"

**STATUS: AIRTIGHT — AWAITING OWNER APPROVAL (HITL STOP). NO CODE TOUCHED YET.**
Branch: `engine/iter55-tts-era-turn1-ammo` (worktree `/tmp/opencode/wt-iter55`, cut from `engine/iter52-industry-pin` @ `054af7b`, verified zero-diff). Suite at branch point: 332/333 (F-01, fixed in Commit 0).

Provenance: source plan `plans/plan_v5_iter55_tts_era_turn1_ammo.md` · surgeon audit `01_audit.md` · action plan `02_action_plan.md` · cross-reference `03_cross_reference.md` (all contradictions resolved: CR-1…CR-6, findings F-01…F-09 covered or deferred-with-visibility).

---

## EXECUTION SEQUENCE (post-approval)

| Step | Commit | What | Gate | Rollback |
|---|---|---|---|---|
| 0 | C0 | Rourke → happy block (fixtures) + surgeon docs on branch | 333 green | revert (no engine code) |
| 0.5 | — | **Wire Telegram HITL ping** (`engine/scripts/hitl_ping.py`, creds on file at `/home/julio/projects/video_strategy/.env` → copy to engine/.env, never commit; fail-safe log-and-continue) | test ping lands | delete script |
| 1 | C1 | **T0 observability**: warm spans (`warm:lite:<state>`/`warm:<state>`: fired_at/ms/outcome/degraded/error), `await_warm` outcomes (landed/timeout/already_done/no_task + waited_ms), voice greeting spans (`greeting:first_audio`, `greeting` drain). Files: config.py (+`warm_observability=True`), llm.py (un-swallow warm failures), builder.py (diag + done-callback + await outcomes), session.py (`_greet` anchors), new `test_iter55_observability.py`. tracer.py UNCHANGED | suite 333+new green; `git diff 054af7b -- diallux/` observability-only | `warm_observability=False` (env) or revert C1 |
| 2 | — | T0 live verify (chat: 1 harness run; voice: 1 mic-bridge session) → Langfuse shows the new spans | spans present both channels | — |
| 3 | C2 | T3 prerequisite: `prewarm_lite_max_completion_tokens=64` + `_warm_llm_lite` twin (F-07 — the shared-cap trap) | pins green; default = byte-exact today | revert |
| 4 | — | **T1** (LIVE, pinged): warm-span harvest + `cold-probe-b` (≥3.5 h idle) + ledger import (MAIN checkout!) → `01_era_and_warm_p90.md` table: warm-completion p50/p90 × lite/full × cold/warm; ack p50/p90 | ≥10 lite + ≥10 full completion samples | — |
| 5 | — | **T2** (HITL): era table — Option A existing micbridge traces (re-resolve `43d83d0815c9`) and/or Option B fresh mic sessions ×2 personas ×3 calls (owner at browser; engine foreground 127.0.0.1 free port) | era-0 vs era-52 same-path delta decomposed | — |
| 6 | — | **T3** (LIVE, autonomous, pinged): `PREWARM_LITE_MAX_COMPLETION_TOKENS=32` → `=16` sweeps (AFTER C2) | zero warm failures ×20 lite; registration ms delta reported | unset env |
| 7 | — | **T4** (LIVE, true-cold ×4): sanity — T0 spans show greeting FULL warm completes BEFORE turn-1 fires; then `FIRST_TURN_LITE=false` ×4 (`ammo-a..d`) | turn-1 cache ≥2,688 ×4/4 AND TTFT ≤900 ms ×4/4 | unset env |
| 8 | — | **T5** (LIVE): `cold-probe-b` + `warm-battery-iter55` (Maria/Danny/Susan/Marcus, 15 s stagger; cancel ALL test bookings after) | cache-0 ≤3/call; p50 ≤950; first-3 ≤900; hear ≤1,400 | — |
| 9 | C3 | **T6** (CONDITIONAL on T4 miss): owner-approved filler copy + `prefill_fallback=False` default + pins | fires only warm-pending; ≤700 ms cold; no chaining; next-round cache>0 | flag stays OFF |
| 10 | — | **T7**: report + ITERATIONS.md line + PT-51/PT-52 flips + ASK pings | owner answers ASKs | — |

## OWNER GATES (hard, from the source plan)
First 3-4 interactions TTFT ≤900 ms · worst-case TTFT ≤1,100 ms · user-hears ≤1,400 ms · steady p50 ≤950 ms.
Never touched: live :8000-:8006 (read-only /metrics only), production agents, kb_chunks (SELECT-count only), no merges/pushes without say-so, `scripts/keyhound` before any push.

## HITL / TELEGRAM PING POINTS (bot on file — wired at step 0.5)
T1 start + table → **T2-B scheduling** (mic sessions) → T4 failure-mode verdict + wait-ceiling ask (only on miss) → **T6 copy approval** (only if needed) → T5 results → **T7 ASKs** (merge iter52? merge iter55? `FIRST_TURN_LITE=false` default? **cutover authorization**).

## OPEN DECISIONS FED BY THIS WORK (not blocking T0–T3)
1. warm_rag / KB-resolve keep-drop-reorder — after T1 greeting-span numbers (physics: dropping warm_rag degrades turn-2 first heavy round's lane-B embed to zero fresh chunks).
2. Real-Twilio test level GO (browser mic only vs + real call).
3. EOT wait ceiling (raise above 500 ms) — only if T4 misses.

## BANKED EVIDENCE (read-only, already harvested)
- :8000 live (47 turns): e2e 2,201 ms · stt→llm 1,914 · llm→tts 288 (**LLM dominates; TTS clean**).
- :8005 iter52 (38 turns, population unverified): e2e 2,749 ms — NOT comparable to :8000 raw (F-04); T2 decides.
- Ledger (19 traces): turn-1 p50 866/p90 975 (warm provider); heavy p50 888/p90 1,079; cache floors {1664, 2688, 3712, 4736}.
- Telegram creds on file; `send_telegram()` reference pattern verified.

## DEFERRED (out of scope, unchanged from source plan)
iter52 merge decision · iter53 hygiene · real-Twilio cutover execution · time-to-first-audio gate redefinition · provider cache internals · lite-head trim · O3/O4 (dead under the gates).
