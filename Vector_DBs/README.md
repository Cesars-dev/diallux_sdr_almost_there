# Vector_DBs — KB retrieval re-engineering pack (iter51)

> **READ THIS FIRST.** This folder is the complete, self-contained handoff for the
> KB retrieval re-engineering done on 2026-09-13 (plan:
> `plans/plan_iter51_kb_gold_filter_d2q_2026-09-13.md`).
> It is written for an agent with NO prior conversation context. Everything needed
> to understand, verify, and (in a later session, with owner say-so) wire up is here.

## ⚠️ What was changed vs NOT changed (owner directive)

| thing | status |
|---|---|
| Main engine code (`engine/diallux/**`) | **NOT touched. Not one line.** |
| Live RAG embedder | **LEFT AS-IS** (OpenAI `text-embedding-3-small`, threshold 0.40) — owner will upsert paths in a separate session |
| `agent/knowledge_bases/faq-kb.md` | **NEW file created** (owner-approved content, 17 sections) — NOT yet ingested into pgvector (waiting on owner "go") |
| Lab repo `/home/julio/projects/diallux_kb_lab` | all experiment code + results live THERE (standalone git repo, 12 commits) |
| This folder | docs + lite SQLite only — no code, no data spills, nothing to run |

## The one-paragraph version

We measured the KB retrieval stack scientifically: 28 evals, 3 query sets (50 golden,
50 messy real-caller, 10 proper), gold-truth labels, cosine sweeps. Findings: the prod
`rag_filter_score=0.40` was never validated and is actively harmful (refuses 20% of
real answers under OpenAI; would refuse 88% under arctic); OpenAI's cosine ranking is
**anti-correlated with answer quality** on this corpus (no threshold can fix it); the
local model `snowflake-arctic-embed-m` matches/exceeds OpenAI (gpt-4o judge: 0.788 vs
0.760), is free, ~35ms/query, and its cosine DOES separate value from garbage. A new
FAQ KB (facts sourced from the existing KBs, owner-supplied facts included) recovered
15 previously-refused real-caller questions (mean 0.479 → 1.031 at threshold 0.24).

## THE DECISION (owner-approved direction, cutover pending)

| parameter | value | why |
|---|---|---|
| Embedding model (target) | `snowflake/snowflake-arctic-embed-m` (local, 768-d) | free, 35ms, quality ≥ OpenAI; cosine still carries signal |
| `rag_filter_score` (target) | **0.24** | keeps good answers (10/10 proper, 75% messy), junk-served 15→1; NOT 0.138 (loose) and NOT 0.40/0.60 |
| Reranker | LLM rerank top-20 → top-3 (gpt-4o-mini) | the actual relevance gate; cosine alone can't do it (it3: +0.064 arctic) |
| Corpus | v2-quality chunks + **new faq-kb** (17 sections) | FAQ recovered 15 refused real questions |
| Current live state | OpenAI 3-small + 0.40 + top-3, NO rerank, no FAQ | unchanged until owner wires cutover |

## How the pieces connect (READ BEFORE TOUCHING ANYTHING)

1. KB markdown files: `engine/agent/knowledge_bases/*.md` (10 KBs) + `faq-kb.md` (new).
2. `scripts/rag_ingest.py` (engine) rebuilds pgvector table from those md files —
   this is the ONLY ingest path. It re-embeds with `settings.rag_embedding_model`.
3. The state machine pulls KBs via `##slug-kb##` markers inside prompts
   (`diallux/rag.py::kb_slugs_in`, `diallux/graph/builder.py::kb_slugs_for`).
   **Connecting faq-kb later = add `##faq-kb##` to `general_prompt.md` / state prompts.
   No code change.**
4. Retrieval scoping is per-state (see `01_SYSTEM_ANALYSIS.md`): Booking/VerifyLead/
   ConfirmSlots/contact_details pull NOTHING; Closing pulls only call-closing;
   everything else pulls general+state slugs.

## Folder map

| file | contents |
|---|---|
| `01_SYSTEM_ANALYSIS.md` | how the 9-state SDR + RAG wiring works (with file:line refs) |
| `02_DECISIONS.md` | every decision + evidence + owner approvals |
| `03_EXPERIMENTS.md` | all 28 evals + real-caller + threshold sweeps (full table) |
| `04_FAQ_KB.md` | the new FAQ KB (full text) + the 7 owner answers baked in |
| `05_CUTOVER_STEPS.md` | exact step-by-step for the next session (upsert/ingest/threshold/embedder) |
| `06_VECTOR_STORE_INVENTORY.md` | every vector store & data file that exists |
| `vector_dbs.sqlite` | lite queryable database of all of the above |
| `faq-kb.md` | copy of the new KB (live copy sits in engine/agent/knowledge_bases/) |

## For a fresh agent starting cold

1. Read `01_SYSTEM_ANALYSIS.md` → understand the machine.
2. Read `02_DECISIONS.md` → understand what's agreed.
3. Read `05_CUTOVER_STEPS.md` → that's your job queue for the cutover session.
4. Anything numeric → `vector_dbs.sqlite` or `03_EXPERIMENTS.md`.
5. **Do NOT start services, do NOT edit engine code, do NOT re-ingest without owner OK.**
