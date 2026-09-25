# 05 — Cutover steps (for the NEXT session; owner say-so per LAW 0 at every gate)

> This session changed NOTHING in main code. Everything below is the queue for the
> cutover session. Owner upserts paths himself ("I will upsert the paths on another
> session") — this doc is the map for that session.

## Current live state (do not disturb until cutover)

- Embedder: OpenAI `text-embedding-3-small` · threshold 0.40 · top-3 · 233 chunks
- `public.kb_chunks` in docker `diallux-db` (port 5434, db `diallux`)
- faq-kb.md written but NOT ingested

## Phase A — FAQ KB only (no embedder change; lowest risk)

1. `cd engine && python scripts/rag_ingest.py --dry-run` → check chunk counts.
2. Owner "go" → `python scripts/rag_ingest.py` (re-embeds all KBs, OpenAI, ~$0.02).
3. Add `##faq-kb##` to `general_prompt.md` (+ any state prompts wanted; NOT Booking/VerifyLead/ConfirmSlots/contact_details — they pull nothing by design).
4. Threshold: decide separately (Phase B). Note: under OpenAI the threshold is broken anyway (anti-correlated) — leaving 0.40 = today's status quo.
5. Validate: `pytest tests/ -q` (expect suite green) + one harness persona with --rag.

## Phase B — threshold change (one line)

1. Set `rag_filter_score=0.24` ONLY IF the embedder is arctic (see Phase C). Under
   OpenAI, 0.24 was never validated — the measured-safe OpenAI change is LOWER
   (≤0.25) not higher. Do not mix: threshold value is embedder-specific.
2. Restart app per RUNBOOK (never edit running service mid-call).

## Phase C — embedder swap to arctic-m (the full re-engineering)

1. Staging tables already exist in `diallux-db`:
   - `kb_chunks_emb_staging` (v2 corpus, 1536-d OpenAI)
   - `kb_chunks_emb_staging_m` (v2 corpus, 768-d arctic) — read-only, reuse or re-build.
2. Embed corpus: lab embedder code = `/home/julio/projects/diallux_kb_lab/scripts/`
   (`openai_util.py`, `corpus.py` for chunker-v2, `build_corpus.py`, `evaluate.py`).
   fastembed model cache: `/home/julio/fastembed/models`.
3. Swap config: `rag_embedding_model=snowflake/snowflake-arctic-embed-m` (or a local
   fastembed path — owner upserts exact wiring), `rag_filter_score=0.24`, add rerank
   step after top-20 (LLM gpt-4o-mini scoring; code exists in lab
   `scripts/rerank_util.py` — port decision is owner's; NOT edited into engine here).
4. DB: 768-d vectors need the staging table promoted (column swap or new table +
   view). NO writes to `public.kb_chunks` outside the ingest script.
5. Validate: full harness ladder per repo SOP + one real-device test call; cancel test bookings.
6. KB policy: create faq-kb ONCE via kb_registry.json flow at deploy.

## Latency note for the swap

- arctic-m embed: ~35ms/query local (0.43GB model, threads=2).
- Rerank adds 2 LLM calls/query (~+2s). If hot-path budget can't absorb it, ship
  Phase A + B without rerank first (arctic alone = parity with OpenAI), add rerank
  when the latency budget allows.

## Explicitly OUT of scope of this pack

- Editing any engine/*.py (none was touched; none needed for FAQ).
- Starting/stopping services, touching Retell agent IDs, live `.env`.
- Deciding cutover day — owner does that.

## Pre-flight amendments (2026-09-15, measured — research/surgeon/iter49p-sharp-rag/02_replay_report.md)

- Embedder wiring: ASYNC off the hot path (owner directive); threads ≥ 4;
  lane queries (per-tag + caller lane) in ONE batched embed call; query prefix
  "Represent this sentence for searching relevant passages: ".
- Lane-B query: caller text + ` (their industry: {industry dv})` when the dv
  exists (right-vertical 0.589→0.788).
- Lane-A leak values: $-formatted with units ("$60000 a week / $259800 a month").
- Quota: ≤1 chunk/KB unless lane-owned; top_k 3; 1600-char budget (0/47 over).
- Closing anchor "warm goodbye wrap-up next steps" [call-closing, sales-language];
  after a successful booking swap to "recap booking SMS confirmation next steps"
  (pre-flight edge E3: wrap-up section served on booked closes).
- Known edges E1/E2/E4/E5 in 02_replay_report.md — iter49 battery needs a
  price-push persona (Discovery deferral is UNTESTED on the gold chats; Retell
  never surfaced sales-language there either).
- Latency note correction: the "~35ms/query" figure is single-query only;
  a 6-lane batch costs 126–192ms — fine as async background (5–10s speech
  window), never awaited on the hot path.
