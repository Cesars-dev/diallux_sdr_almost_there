# 02 — Decisions ledger (what was agreed and why)

All measured on 2026-09-13 in the isolated lab repo `/home/julio/projects/diallux_kb_lab`
(git: one commit per experiment; full evidence in its `results.db`). Judge for iteration
= gpt-4o-mini (0–2 relevance); headline configs re-judged with gpt-4o.

| # | decision | evidence | status |
|---|---|---|---|
| 1 | Local embedder = `snowflake-arctic-embed-m` (768-d) | gpt-4o judge: 0.788 vs OpenAI 0.760 on same config; 35ms/query; $0; -s too weak, -l too slow (99ms) | owner-approved direction; swap pending cutover session |
| 2 | Keep OpenAI embedder AS-IS today | owner directive ("leave the RAG embedder as it is") | LIVE (unchanged) |
| 3 | Threshold (arctic) = **0.24** | proper-10: 10/10 relevant; real-50: junk-served 15→1, mean@served 0.922; NOT 0.138 (15/50 junk) or 0.26 (refuses good answer at cos 0.257) | locked; apply at cutover |
| 4 | 0.40 (live) is harmful | refuses 20% of real answers (openai), 88% under arctic; sweep 0.30–0.45 strictly monotonic decline | replace at cutover |
| 5 | Retell's 0.6 was never portable | Retell internal scorer ≠ raw cosine (config.py:50 comment) | historical note only |
| 6 | OpenAI cosine unusable as quality gate on this corpus | anti-correlated: junk 0.48–0.61 vs answers 0.19–0.43; 9/10 refusals at 0.60 | evidence; informs embedder choice |
| 7 | Reranker (LLM, top-20→top-3) = WIN | arctic 0.832→0.896 (+0.064); biggest single lever | include at cutover (decision: rerank on/off per latency budget) |
| 8 | doc2query (it2) = REJECTED | 0.788/0.716 vs ref 0.844 | do not use |
| 9 | hybrid BM25+RRF (it4) = REJECTED | 0.748/0.840 | do not use |
| 10 | it6 topic-restructuring = REJECTED | boilerplate clustering diluted precision (0.812/0.752) | do not use |
| 11 | it5 v1-frontload prose (deterministic) = mild win | 0.972/0.908; order matters near headings | optional, free |
| 12 | NEW `faq-kb.md` (17 sections, facts from owner + existing KBs) | real-50 at 0.24: mean 0.479→1.031, refusals 24→9, 15 questions recovered | **file created in engine/agent/knowledge_bases/ — NOT yet ingested** |
| 13 | Remaining refusals = missing KB content | 9 refusals map to owner-fact topics (setup days etc.) — now answered | 7 owner answers received 2026-09-13, baked into faq-kb.md |
| 14 | Corpus = v2 chunking | 233→181, kills 46 header-only chunks | apply at ingest (chunker swap is part of cutover plan, NOT this session) |
| 15 | Vector DB stays `diallux-db` pgvector | 1 physical DB; staging tables `kb_chunks_emb_staging{,_m}` hold v2 corpora read-only | unchanged |
| 16 | No engine code edits in this project | owner directive; all work isolated in lab repo | enforced |
| 17 | KB policy: faq-kb is genuinely NEW (one create via kb_registry.json at deploy; never duplicates) | the ~$250 duplicate-KB lesson | applies at cutover |

## Owner answers received 2026-09-13 (verbatim intent, phrased into faq-kb.md)

1. Setup: **72 hours for the receptionist; 1–3 weeks for full system depending on complexity.**
2. Contract: **no contract, month-to-month, cancel anytime.**
3. SMS: **yes — booking confirmations + reminders via SMS.**
4. Phone system: **keep your number, forward to the agent, any carrier.**
5. Proof: **full dashboard + every call recording weekly/monthly; CRM integration = real-time data.**
6. Voice: **not a recording — top-of-the-line Voice AI acting as a true receptionist.**
7. Guarantee: **if you don't get results, we keep working for free until you make your money back.**

## Gold-label ground truth (queries_gold.json in lab)

- 28/50 queries ANSWERABLE from expected KB · 15 answers live in a different KB (loose tags) · 7 GAP (no answer exists) — all 7 confirmed by gpt-4o recheck, and all 7 now covered by faq-kb or owner answers.

## Pre-flight verdicts (iter49 preflight replay, 2026-09-15 — research/surgeon/iter49p-sharp-rag/02_replay_report.md)

| # | decision | evidence | status |
|---|---|---|---|
| 18 | Parameter pack validated by gold-chat replay (82 turns, 5 chats, A/B/C) | Offer re-anchor 5/5 (Retell 3/5, engine 1/5); Closing 4/4 (Retell 1/4); right-vertical C 0.788 vs Retell 0.637 vs engine 0.376; gate PASS | ready for iter49 execution |
| 19 | Lane B industry-dv anchor `(their industry: X)` added to the pack | right-vertical 0.589→0.788 measured on same turns | locked (pre-flight amendment) |
| 20 | Leak dv values $-formatted in lane-A queries ("$60000 a week") | raw numerals scored <0.24 → Closer Loss-Playback refusal; fix = refusal gone (2→1 zero-chunk) | locked (pre-flight amendment) |
| 21 | "35ms/query" arctic claim: SINGLE-query calls only | 6-lane batch p50 126ms (threads 4) / 192ms (threads 2); batch ≈ sequential | corrected; embedder = async off hot path (owner), threads ≥ 4 |
| 22 | Awaited hot-path = pgvector only | scoped SELECT p50 1.7–2.9ms p95 ≤6.4ms on staging_m | +60ms guard PASS (≈3.4ms) |
| 23 | Engine-today (openai/0.40/233/frozen) confirmed dumb on Retell's own gold turns | Indeed-job-post junk on Intake mirror; 0.376 right-vertical; 74% frozen-identical turns; 2/4 blind closes | replaced at iter49 cutover |
| 24 | Retell's real bugs measured | 9.7 chunks/turn burned on mechanical states (339 chunks/35 turns); 36% wrong-vertical industry; call-closing only 1/4 | all killed by construction in iter49 |
