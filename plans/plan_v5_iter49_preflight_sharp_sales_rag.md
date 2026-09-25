# PLAN — v5 iter49 PRE-FLIGHT: dry-run evaluation of the measured RAG parameters (feeds iter49 execution)

## Meta
- Date: 2026-09-13
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Design source (DO NOT duplicate): `plans/plan_v5_iter49_rag_retrieval_parity.md` — iter49's plan already contains the full implementation design (T2 embedder wiring, T3 re-embed, T4 retrieval redesign, T4b lite entry, T5 marker A/B, T6 battery). The dumb-agent DIAGNOSIS is already done there (FIND-9, `research/surgeon/iter48-rag-truth/10_latency_findings.md`). This pre-flight does NOT re-diagnose and does NOT implement.
- Scope: DRY evaluation only — measure that the iter51 lab parameters (arctic-m ~35ms, threshold 0.24, v2 corpus + faq-kb, per-tag lanes, fresh-per-turn) blend with the engine's design, simulate agent behavior on Retell-era gold calls, and prove it beats Retell's design (which was smart but slow and buggy). Output = the measured parameter pack + replay evidence that iter49's execution session consumes.
- Status: EXECUTED 2026-09-15 (all tasks T0–T5 done; gate PASS) — outputs: `research/surgeon/iter49p-sharp-rag/02_replay_report.md` (measured parameter pack) + `02_better_than_retell.md` (matrix); lab evidence: `diallux_kb_lab/results.db` run `replay` + `logs/replay_gold.md` + `logs/sim_latency.md`. Awaiting owner: parameter-pack approval + iter49-plan pinning + docs commit.
- HARD BUDGET: no engine code edits, no live calls, no service starts. OpenAI calls: ZERO. Embeddings = local arctic (free). Relevance arbiter = THE SESSION AGENT ITSELF (in-session LLM analysis, documented per-sample in the report) — owner directive: gpt-4o-mini is too stupid for this job (kept as quoted rationale in Decisions table).
- Worktree: NONE (no branch). All work in `/home/julio/projects/diallux_kb_lab` + this repo's `research/`.
- Companion: `plans/plan_v5_iter49_rag_retrieval_parity.md` (the implementation plan this feeds), `Vector_DBs/` pack (already on main).

## Compaction Context

**What the engine is:** Dialux SDR v5 (9-state chat machine Intake→Discovery→Closer→Offer→contact_details→ConfirmSlots→VerifyLead→Booking→Closing). KB attachment = `##slug-kb##` prompt markers → `kb_slugs_for(state)` → `retrieve()` scoped by `kb = ANY(slugs)` + cosine `>= rag_filter_score` (0.40 today), top-3, 1600-char budget, chunks frozen per state-visit. Ingest = `scripts/rag_ingest.py` from `agent/knowledge_bases/*.md` → `public.kb_chunks` (233 chunks, OpenAI 1536-d, docker `diallux-db` port 5434). Engine proven working: iter48 battery 13/13 @ `033f742`, suite 270.

**The dumb diagnosis (ALREADY DONE — do not repeat):** iter48 FIND-9 (`research/surgeon/iter48-rag-truth/10_latency_findings.md`): Intake pain-mirror → industry 4/4 (pain-points never); Discovery deferral → industry (sales-language never); Offer re-anchor → sales-psychology 1/4; Closing → 0 chunks 4/4; freeze lane ~180ms/round lands zero deltas; scope general∪state = fake per-state attachment.

**Why Retell was SMART (proven from logs 2026-09-13, `research/surgeon/iter49p-sharp-rag/01_retell_era_retrieval.md`):** 91 chats in `Dialux_SDR/testing/json_logs/BOOK_chat_*.json`; `knowledge_base_retrieved_contents_url` = pre-signed, fetchable WITHOUT auth, returns per-`response_id` KB ids + chunk contexts. Gold calls: 47 + 43 fresh retrieval rounds/call; KB mix rotates (industry ~2×/turn but discovery-bridge 18–25 and sales-psychology 6–21 surface as conversation demands). Sharp pattern in transcripts: mirror caller's words → live loss math from THEIR numbers ("$6,500/week — $28,000/month walking out") → vertical by name → book + SMS detail. Retell was smart BECAUSE every turn had fresh, relevant chunks in context. It was also slow (server-side search every turn) and buggy (duplicate KB era). Engine = fast but dumb. The missing piece is smart; we almost cracked it.

**What iter51 measured (lab repo `/home/julio/projects/diallux_kb_lab`, 12+ commits, full ledger `results.db`, handoff pack `Vector_DBs/`):**
- OpenAI cosine anti-correlated with quality on this corpus (junk 0.48–0.61 > answers 0.19–0.43); no threshold fixes OpenAI. 0.60 (Retell's internal-scorer value, never portable) = 9/10 refusals.
- arctic-m (local, 768-d): cosine tracks quality; 34.5ms/query p95; 0.43GB at `/home/julio/fastembed/models`; venv `/home/julio/fastembed/bin/python`.
- Threshold arctic = **0.24**: proper-10 10/10 relevant (mean 1.233); real-50 junk-served 15→1, mean@served 0.922; cliff at 0.14 (loses gold), 0.26 refuses a good answer at cos 0.257.
- v2 chunker corpus (181 clean chunks; kills 46 header-only shells) = winning base; it6 topic-restructure/doc2query/hybrid all REJECTED.
- faq-kb (17 sections, facts sourced from existing KBs + 7 owner answers: 72h receptionist/1–3wk full; month-to-month; SMS confirmations; keep-your-number; dashboard+recordings+CRM; top-tier Voice AI not a recording; keep-working-free-until-money-back): real-50 at 0.24 mean 0.479→**1.031**, refusals 24→9, 15 questions recovered (10 at judge 2.00).
- Reranker (LLM top-20→top-3) = biggest single quality lever (+0.064) — engine port = owner latency decision, NOT this pre-flight.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| This is a PRE-FLIGHT to `plan_v5_iter49_rag_retrieval_parity.md`, not a new iteration | owner: "part of iter49"; avoid redundancy; keep iter49's flow (mimic → improve) |
| Dry only: no engine branch/worktree/commits, no live calls | owner: "dry tests only, analysis, simulations… don't burn thousands of tokens" |
| Measure the agent's CONTEXT, not full conversations | we evaluate KB-retrieval blending, not chat quality — that's iter49's battery (T6) |
| Arbiter = THE SESSION AGENT ITSELF (in-session analysis, zero API); embeddings = local arctic (free) | owner: gpt-4o-mini too stupid for this; zero OpenAI calls |
| iter49's flow is preserved: mimic Retell first (acceptance = parity vs Retell's actual retrievals), then beat it (0.24 + faq-kb + arctic + quota + fresh-per-turn) | owner framing: "retell was smart, poorly, slow, buggy — we keep smart, kill slow and buggy" |
| faq-kb.md already written in `engine/agent/knowledge_bases/`, NOT ingested; no `##faq-kb##` markers added yet | integration is iter49 execution's job (its T3/T4), simulation here uses the lab corpus copy (`corpi/it7_faq.json`) |
| Pinned gold chats (5): `BOOK_chat_6ac2470351eff798042fcf7a792` (real estate, booked, full dv trail), `BOOK_chat_e85884c023ec3f2f817a534b5cf` (real estate, loss-math "$60,000 a week / $259,800 a month", no-book but sharpest sales talk), `BOOK_chat_b17a5dcec28ef8f87a253d7241e` (dental/medical, booked+verified), `BOOK_chat_1bcf735edff68c925e8a441cc15` (dental/medical, booked incl. avg_job_value dv), `BOOK_chat_823327e42b6114a34666c790706` (dental, closer_completed, no-book stress variant) | ranked by $-density + loss-math + vertical naming + booking outcome across all 91 retell-era chats (scan 2026-09-13); mix of booked/no-book and verticals so parity isn't tuned to one industry |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner approval to START pre-flight | Julio (this plan) |
| More gold chats (optional, up to 3 more) | owner names them from `Dialux_SDR/testing/json_logs/` |

## Environment & Dependencies
- Lab venv: `/home/julio/fastembed/bin/python` (fastembed 0.8.0, numpy 2.5.3, httpx 0.28.1, psycopg 3.3.5, sqlite3 stdlib)
- Lab repo: `/home/julio/projects/diallux_kb_lab` (scripts/, corpi/, results.db, queries_real.json, queries_gold.json)
- fastembed cache: `/home/julio/fastembed/models` (arctic-m downloaded)
- Retell-era logs: `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/testing/json_logs/BOOK_chat_*.json` (read-only)
- Engine (READ-ONLY reference): `engine/diallux/{rag.py,graph/builder.py,config.py}`, `engine/agent/knowledge_bases/`
- pgvector (read-only SELECT): docker `diallux-db` port 5434 db `diallux`; staging tables `kb_chunks_emb_staging_m` (768-d v2 corpus)
- OpenAI key: via `diallux_kb_lab/scripts/openai_util.py:get_key()` (never printed)
- Retell KB-retrieval URLs: pre-signed, fetch each ONCE, cache to `diallux_kb_lab/cache/retell_retrievals/` (json)

## Architecture (what the pre-flight measures)
```
retell gold chats (transcript + actual per-turn retrievals)
        │
        ▼ replay rig (lab script, dry)
caller turn → candidate configs:
  A = engine today:    openai, 0.40, 233 corpus, state scope, frozen
  B = retell actual:   per-turn chunks from the fetched URLs (gold)
  C = iter49 preflight: arctic 0.24, v2+faq corpus (193), per-tag lanes, fresh-per-turn, quota
        │
        ├─ per-turn chunk-set diff A vs B vs C (right-vertical, intended-KB, junk, freshness)
        ├─ context-budget fit: does C's top-3 fit 1600-char budget per turn
        ├─ latency sim: batched arctic embed 1/2/3 lanes on this box + staging_m SQL timing
        └─ output: measured parameter pack + "better-than-retell" matrix → iter49 execution
```

## File Map
| File (absolute) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/diallux_kb_lab/scripts/replay_retell.py` | NEW — replays gold-chat caller turns through configs A/B/C, writes per-turn diffs to `logs/replay_gold.md` + `results.db` (iteration `replay`) | NEW (lab repo, allowed) |
| `/home/julio/projects/diallux_kb_lab/cache/retell_retrievals/` | fetched gold-chat retrieval JSONs (fetched once) | NEW data |
| `/home/julio/projects/diallux_kb_lab/scripts/sim_latency.py` | NEW — lane-embed + SQL timing bench (no API) | NEW (lab repo) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter49p-sharp-rag/02_replay_report.md` | the main deliverable | NEW |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter49p-sharp-rag/02_better_than_retell.md` | the matrix | NEW |
| `/home/julio/projects/clean_diallux_SDR/Vector_DBs/02_DECISIONS.md` + `05_CUTOVER_STEPS.md` | append pre-flight verdicts (docs = main) | EDIT |
| `plans/plan_v5_iter49_rag_retrieval_parity.md` | ONE edit max: pin the measured params into its Environment section (owner-gated) | Edit |
| engine/ code | NOTHING | — |

## Deploy Rules
- No engine worktree, no branch, no commits outside docs; engine tree untouched (verify with `git status` in `engine/` clean at end).
- No live calls, no uvicorn, no Retell agent touches, no bookings (nothing to cancel — no bookings).
- OpenAI: ZERO calls. Relevance judgment = the session agent, each sample documented in the report with its reasoning (auditable).
- pgvector: SELECT only (staging_m reads for C-config latency sim).

## Tasks (in order)
### T0 — Asset freeze (15 min)
Goal: confirm inputs unchanged since this session.
Commands: `ls /home/julio/projects/diallux_kb_lab/corpi/it7_faq.json`; verify the 5 gold chat files + their retrieval URLs still fetch (from cache if present); `git -C /home/julio/projects/clean_diallux_SDR status` (clean).
Verification: cache/retell_retrievals/ has all 5 gold chats. JSON cached; research file 01 updated with the 5.
Dependencies: none.
### T1 — Replay rig: same caller turns, three configs
Goal: for EVERY agent-response turn in the **5 pinned gold chats** (retrieval rounds 40–47 each ≈ ~215 replay turns): build the query the engine would build (iter49 `refer_query` semantics: tag-whats + dv values + caller text), then retrieve under A (openai/0.40/233/state-scope), B (=Retell's actual chunks from URL), C (arctic/0.24/v2+faq/per-tag lanes per iter49 `_STATE_KBS` draft, quota). All lab-side; no engine code.
Files: `replay_retell.py` (spec: reads gold chat + its retrieval URL JSON; emits per-turn chunk sets + overlap stats vs B).
Verification: `logs/replay_report.md` table: per-turn KB match-rate C vs B (target ≥ Retell mix: discovery-bridge and sales-psychology surface in the turns where the sharp transcripts used them, i.e., ≥ parity on the 4 FIND-9 failure patterns), A vs B as the "dumb" baseline.
Dependencies: T0.
### T2 — Context-quality simulation (smart vs dumb, cheap)
Goal: quantify what Linda would SEE per turn under A vs C on the same turns: right-vertical rate, junk-chunk rate (session agent reads and grades ≤30 sampled turns directly, reasoning per sample recorded in the report), 1600-char budget fit, freshness (identical-context turn count A vs C).
Files: extension of replay_retell.py output.
Verification: numbers table in `02_replay_report.md`; if C ≥ B on intended-KB match and C ≥ 2× A on right-vertical → pre-flight PASSES its gate.
Dependencies: T1.
### T3 — Latency simulation (no live calls)
Goal: prove the 35ms + lane-budget claim on THIS box.
Commands: time arctic embed of 1/2/3 queries batched (50 reps, p50/p95); time `SELECT ... WHERE kb = ANY(...) AND embedding <=> q <= 0.76 LIMIT 3` on `kb_chunks_emb_staging_m` via docker exec (allowlisted read).
Verification: table in `02_better_than_retell.md`: projected hot-path delta ≤+60ms guard holds; fresh-per-turn cost vs Retell server-side search (they paid it per turn too — we're strictly faster: local embed vs their remote scorer + RTT).
Dependencies: T0.
### T4 — Better-than-Retell matrix (the "flow" deliverable)
Goal: their design (global 9-KB, fresh-per-turn, their 0.6 scorer, top_k 3) vs ours (per-tag lanes + quota + faq-kb + arctic 0.24 + v2 corpus): for each design point, the measured advantage. Include the bugs Retell had that we kill by construction (freeze staleness, 0-chunk Closing, wrong-vertical junk, unanswerable logistics).
Files: `02_better_than_retell.md`.
Verification: every row has a number attached (T1–T3 outputs or lab results.db).
Dependencies: T1–T3.
### T5 — Report + handoff + ASK
Goal: write `02_replay_report.md` summary + update `Vector_DBs/` decision tables (docs to main) + ASK JULIO: approve parameter pack → iter49 execution session runs its own T2–T6 with these numbers.
Verification: ledger import per SQL SOP; `git status` in repo shows ONLY docs changed; plan-file edit limited to Environment/params pinning.
Dependencies: T2, T4.

## Validation Plan (end-to-end)
1. Zero engine diffs: `git -C clean_diallux_SDR status` shows only `research/` (gitignored) + `Vector_DBs/` docs + plan edits.
2. ZERO OpenAI calls; analyst-judged samples (≤30) itemized WITH reasoning in the report.
3. Replay rig output stored in lab `results.db` (new iteration `replay`), queryable.
4. The "better-than-Retell" matrix: every improvement row quantified; every mimic-row shows parity (KB visibility, freshness, top_k).
5. Exit criterion: owner approves the parameter pack → iter49 execution session starts at its own T2 with zero re-litigation.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Engine implementation (iter49 T2–T4b), battery, live calls | iter49's own plan; engine already proven (13/13 @033f742) — this session only loads the measured ammo |
| Reranker in engine | latency decision = owner; lab code exists |
| US region migration | iter50, after iter49 passes |
| More gold-chat pinning | optional; owner names them |
