# PLAN — v5 iter59 exec: Run the Surgeon Master Plan (hybrid RAG) + latency-compression exploration (LATER tests)

## Meta
- Date: 2026-09-20
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: EXECUTE the already-airtight surgeon master plan (context only here — all code analysis lives there); then, as a SEPARATE later-tests phase, explore the lane-B/EOT latency-compression idea ("can RAG retrieval at EOT go under ~90 ms without quality loss").
- Status: **PLAN ONLY (not started — awaits approval)**
- Branch (Phase B code): `engine/iter59-kb-everywhere-freshness` from `db8e56f` — cut per the master plan's T0, NOT in this plan's text.
- SOURCE OF TRUTH for all code work: `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter59-kb-everywhere-freshness/04_master_plan.md` — read it FIRST. This file deliberately contains NO code analysis.

## Compaction Context (session 2026-09-20 — pin, do not re-derive)

- **What happened:** the owner-supplied plan `plans/plan_v5_iter59_assess_rag_rebalance.md` was run through the Surgeon Framework (audit → action plan → cross-reference → preflight → master plan). Output: 4 files in `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter59-kb-everywhere-freshness/` (`01_audit.md`, `02_action_plan.md`, `03_cross_reference.md`, `04_master_plan.md`; original plan archived in `archive/`). Execution has NOT started (stopped at master plan per owner).
- **Verified facts (all re-measured this session, trust as-is):** the RAG freshness bug is real — retrieval task starts at the same tick the round consumes it; Langfuse trace `daee4b0059ac42c5d52826aa2f56eff9` (live call 2026-09-20): **24 rag spans, 23 degraded=True, await p50 60.8 ms, exactly 1 fresh (await 0)**; retrieval task cost p50 **123 ms** (min 92, max 204, ledger run `live-iter58-070@db8e56f`); TTFT p50 845 ms, e2e p50 1143 ms; rag rows stop 06:57:20, ZERO in contact_details; suite = 368 tests.
- **Cost anatomy (owner now knows):** one batched arctic ONNX embed for ALL lanes ≈ 90-190 ms (CPU-bound, 4 threads, no GPU — batching ≠ parallelizing) + pgvector 15-40 ms (already parallel via asyncio.gather) + merge/pin ~10 ms. The embedder IS async (`asyncio.to_thread`, never blocks the loop) — async ≠ parallel. "6 async calls" cannot compress the batch below ~90 ms; P90 spikes are shared-vCPU noise.
- **Retrieval budget today:** every lane fetches top 3 candidates; ONE merged working set of **3 chunks total / 1600 chars** (`rag_top_k=3`, `rag_char_budget=1600`), per-KB quota ≤1 (owned-KB lanes exempt), junk gate cosine 0.24, dedupe by chunk id. Industry pin renders OUTSIDE the 3-slot budget (own block, 1800 chars).
- **How prompts reference KBs (owner confusion resolved):** `##slug-kb##` markers = scope for the engine (parsed + stripped before the LLM sees them); `#[refer <kb>-kb for <what> — {{dvs}}]` tags = lane A — the tag ITSELF becomes the query (`"<what>: <dv values>"`, scoped to that one KB). LLM never sees markers; KNOWLEDGE arrives as post-history delta. Retell-parity = lane-B-only over the global KB; our tags/pin/quota = the "beat Retell" part.
- **Owner Q&A decisions made THIS session (absorb, do not revisit):**
  - Owner chose **HYBRID** fire mode as preferred: lane A (refer tags + dv values — utterance-independent) fires at FIRST Deepgram flux Update (~0.3 s into speech, lands during speech, 0 ms at answer time); lane B (caller utterance — only exists at EOT) fires at EOT as a SINGLE-query embed (~30-60 ms) consumed inline. Worst-case RAG answer-time latency ≈ 90 ms — **owner accepts this** ("our worse latency on RAG will be Lane B EOT 90ms which is acceptable").
  - **Latency compression of lane-B-at-EOT below ~90 ms = DEFERRED** — "let's address that later". It is a LATER-TESTS exploration (this plan's Phase C), NOT part of the fix build.
  - ONE embed model only (arctic-m 768-d). No dual-model. A smaller/faster model = full corpus re-embed migration = explicitly out of scope.
  - 9 KBs at every state mimics Retell's global KB (owner's explicit intent). Freed states (contact_details etc.) = lane-B-only = Retell tier — accepted; quality there is measured at the T6 live gate, and the fix if junk is OWNER prompt tags, not engine machinery.
  - Deepgram flux `Update` events are DROPPED by current code — the speech-window/hybrid fire point needs a new handler; the once-per-turn guard must be a BOOLEAN (clocks swap at EOT, not StartOfTurn — turn-index keying is wrong mid-speech).
- **Master plan corrections already applied (do not re-derive):** hybrid is a 4th `rag_fire_mode` in `04_master_plan.md` T3 (edit applied 2026-09-20); per-variant gates defined (hybrid: await p50 ≤80 ms, lane-A landed ≥90%, degraded <5%, TTFT p50 ≤980 ms... see master plan §T3 for the exact table); verbosity A/B high arm needs `VERBOSITY_STATES_MEDIUM=""`; GK_chat files are V7.0-7.7 (NOT 7.8/7.9 — use the 12 on-disk V7.8/V7.9 dialogues); `_frozen_chunks` fallback replaced by `_live_consumed` semantics; deploy needs explicit `kill $(cat /tmp/opencode/voice_8020.pid)` first.
- **What remains:** everything. Phase A (T1 assessment + T2 owner review), Phase B (T3-T6 code + live call), T7 closeout — all per the master plan. Then Phase C (below) as a separate later session.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Execute `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter59-kb-everywhere-freshness/04_master_plan.md` as written (T0→T7, its STOP POINTS included) | owner: "execute master plan" — the surgeon pass already resolved every flaw |
| Hybrid = preferred `rag_fire_mode` (lane A @ first Update, lane B single-query @ EOT) | owner: "I like hybrid... our worse latency on RAG will be Lane B EOT 90ms which is acceptable" |
| Lane-B/EOT latency compression below ~90 ms = Phase C, LATER TESTS ONLY | owner: "lets address that later" |
| One embed model (arctic-m); no dual-model; no smaller-model migration | owner confirmed single model; migration would need full corpus re-embed + filter re-tune |
| All prompts/prompt-files = OWNER only (agent proposes patterns, never edits) | standing HITL law |
| Hybrid exploration results NEVER block Phase B | Phase C is research; the fix build already has its gates |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Deepgram flux `TurnInfo.Update` payload shape (fields, is-final semantics) | T1.2 Scrapling/websearch pass, or one logged synthetic call with a raw-Update dump — REQUIRED before the T3 handler is finalized (master plan OPEN ITEM) |
| Owner GO per fix after T2 | owner reads `research/surgeon/iter59-kb-everywhere/01_assessment.md` |
| Painification KB content + cost sign-off | owner drafts; agent never hand-creates KBs |

## Environment & Dependencies
- Everything needed is listed in `04_master_plan.md` §2 (worktree recipe, venv symlink, .env copy, suite command, serve_voice.sh rules, ledger/Langfuse/Scrapling locations). That section is normative — do not duplicate it here.
- Key paths only: engine worktree `/tmp/opencode/wt-iter59` (created at T0); ledger `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; Langfuse `http://localhost:3001`; report folder `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/`; :8020 currently serves `/tmp/opencode/wt-iter58` (kill before deploy; pid file `/tmp/opencode/voice_8020.pid`).
- Retell corpus for T1.1: the 12 V7.8/V7.9 dialogues under `/home/julio/projects/clean_diallux_SDR/research/transcripts/` (primary: `NO-BOOK_chat_0f5f1c08496e163200d21d561d9.json`, `V7.9_slot_lock_chat_86abc43fff5eb74a44faf5ecd9c.json`, `V7.8_reach_details_chat_797488f65d5db70a2d5f2529f97.json`).

## Architecture (one block)
```
Phase A (assess, read-only)  = master plan T1 → T2 owner review (STOP POINT)
Phase B (code, on branch)    = master plan T3 (freshness: rag_fire_mode incl. HYBRID)
                               T4 (KB-everywhere + dedupe 0.90) · T5 (prewarm)
                               T6 owner live call (STOP POINT) · T7 closeout + ASK (STOP POINT)
Phase C (THIS plan's addition — LATER TESTS, separate session, after T7):
  "Can RAG at EOT go under 90 ms?" — offline sweep, no live risk:
  C1 baseline re-measure: single-query vs 6-lane embed on arctic-m (real corpus, real lengths)
  C2 multiquery=False quality A/B: combined query vs per-tag lanes — does FIND-9 reproduce?
     (merge slots won, tag-KB presence in top-3, junk rate @0.24)
  C3 candidate pruning: embed only lane B + OWNED tag lanes (skip un-owned lane-A queries
     whose tags' dvs are empty) — lane count reduction without dropping scope
  C4 thread scaling probe: ONNX threads 2/4/6 on this box (diminishing returns check)
  C5 verdict memo → research/surgeon/iter59-kb-everywhere/03_latency_compression.md
     (if any option holds quality AND <90 ms: propose as iter60 plan; NEVER code in Phase C)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter59-kb-everywhere-freshness/04_master_plan.md` | ALREADY EDITED this session: hybrid added as 4th rag_fire_mode (T3), owner-decisions line updated | E (done) |
| all Phase A/B files | per master plan §3 File Map — THIS plan adds none | (see master plan) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/03_latency_compression.md` | Phase C verdict memo (sweep tables C1-C4 + recommendation) | N |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter60_*.md` | only IF Phase C finds a winner — separate iter60 plan, owner-gated | N (conditional) |

## Deploy Rules
- Identical to master plan §5 + repo LAW 0. Highlights: engine :8020 ONLY via `bash scripts/serve_voice.sh` from the engine dir; kill the iter58 server first; NEVER :8000-:8003; Retell API GET-only; `scripts/keyhound` before push; docs→main, code→branch; Cal event 3801235 REAL — cancel test bookings.

## Tasks (in order)
### T-A — Execute master plan Phase A (T1 assessment + T2 HITL gate)
Goal: evidence pack on disk; owner GO per fix.
Files/commands/verification: EXACTLY as `/home/julio/projects/clean_diallux_SDR/tasks/surgeon/iter59-kb-everywhere-freshness/04_master_plan.md` §3 T1 and its T2 STOP POINT. Do not improvise; the master plan's commands are complete (Retell corpus paths, A/B env incl. `VERBOSITY_STATES_MEDIUM=""`, sweep thresholds 0.80-0.97, Scrapling targets).
Dependencies: none. NO CODE CHANGES in Phase A.
### T-B — Execute master plan Phase B (T0 worktree, T3 freshness incl. hybrid, T4 KB+dedupe, T5 prewarm, T6 live call, T7 closeout)
Goal: the three fixes live and gated; closeout + ASK.
Files/commands/verification: EXACTLY as master plan §3 T0-T7, including its STOP POINTS (T2 before any code; T6 owner call; T7 ASK JULIO). Every pin file, config flag, gate number, and deploy command is already spelled out there — the executing agent must NOT re-audit or re-design; load the master plan and run it.
Dependencies: T-A GO.
### T-C — Phase C latency-compression exploration (LATER TESTS — own session, after T7, no live risk)
Goal: answer "can RAG at EOT go under 90 ms without quality loss" with offline evidence; produce a verdict memo; propose iter60 ONLY if a winner exists.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/03_latency_compression.md`.
Commands (full):
1. C1 baseline: `cd /tmp/opencode/wt-iter59/engine && set -a && . ./.env && set +a && .venv/bin/python` — script embeds (a) 6 representative lane texts (from the live-call rag span queries in the ledger) and (b) their 1-query combined form, ×20 runs each; report p50/p90 both shapes.
2. C2 quality A/B: re-run the iter49 offline replay pattern (`scripts/iter49_offline_replay.py` if present in the worktree, else replicate with the same 10 proper + 15 junk query pack from `research/surgeon/iter49p-sharp-rag/02_replay_report.md`): combined-query lanes vs per-tag lanes; count tag-KB presence in the merged top-3 (FIND-9 metric) + junk rate at 0.24.
3. C3 pruning simulation: from the ledger's 24 live rag rows, count how many lane-A queries had EMPTY dv values (those embed a tag-`what` with no anchor) — quantify what skipping them would have saved.
4. C4 thread probe: re-run C1's single-query shape with ONNX threads 2/4/6 (env `ORT_*` or fastembed `threads` kwarg — use the `local_embed_fn(threads=...)` parameter, rag.py).
5. Write the memo: one table per C1-C4 + a verdict (winner / no winner) + if winner: one-paragraph iter60 proposal sketch. STOP — no code, no config change, no deploy.
Verification: memo on disk with p50/p90 tables; verdict stated; zero changes outside `research/`.
Dependencies: T-B merged or at least T7 asked (so measurements run against the final engine shape).

## Validation Plan (end-to-end)
1. T-A: `research/surgeon/iter59-kb-everywhere/01_assessment.md` exists with citations; T2 GO recorded.
2. T-B: master plan §4 validation list (suite 368+green with new pins; live gates per chosen variant — hybrid: await p50 ≤80 ms, lane-A landed ≥90%, degraded <5%; bookings cancelled; ASK sent).
3. T-C: `03_latency_compression.md` verdict memo; no code touched.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Lane-B/EOT compression CODE changes (multiquery=False default, pruning, thread bump, smaller model) | Phase C is offline tests only; any change = new iter60 plan + owner approval |
| Smaller/faster embed model (384-d class) | full corpus re-embed + rag_filter_score re-tune = migration, explicitly parked |
| US-East migration / GPU embedder | owner: later, after production |
| Painification KB ingest | owner content + cost sign-off (T2 gate) |
| Engine-side math humanization, prompt rewrites | OWNER-only (HITL) |
