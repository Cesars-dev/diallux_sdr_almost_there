# 01 — System analysis: clean_diallux_SDR state machine + RAG wiring

(Analysis done 2026-09-13, read-only. All paths relative to `clean_diallux_SDR/`.
`engine/` = the live LangGraph production v5 app, also serving :8000 from
`Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5`.)

## The state machine (9 states, chat SDR "Linda")

`Intake → Discovery → Closer → Offer → contact_details → ConfirmSlots → VerifyLead → Booking → Closing`
- Graph source: `engine/agent/llm.json` (loaded directly, `config.py`), prompts in `engine/diallux/prompts/*.md`.
- Typed dynamic variables + gates: `engine/diallux/schema.py`; executor: `engine/diallux/graph/{builder,llm,tools,subst}.py`.

## How RAG plugs in (the part this project re-engineered)

**KB attachment = text markers, not config.** Prompts contain `##slug-kb##` markers.
- `diallux/rag.py:375 kb_slugs_in()` — extracts slugs from marker syntax.
- `diallux/graph/builder.py:121 kb_slugs_for(state)` — per-state retrieval scope =
  slugs found in `general_prompt.md` + the state's prompt + `> refer:` tags.

**Retrieval gates (builder.py:116-125):**
- `_RETRIEVAL_OFF = {Booking, VerifyLead, ConfirmSlots, contact_details}` → NO retrieval (mechanical states; iter24 measured 431 wasted pulls).
- `_RETRIEVAL_ALLOW = {Closing: [call-closing]}` → only call-closing retrievable there.
- All other states: general + state scope.

**Retrieval itself (`diallux/rag.py:224 retrieve(query, kb_slugs)`):**
- SQL: chunks `WHERE kb = ANY(slugs)` AND cosine `>= filter_score`, HNSW index,
  top `rag_top_k=3`, trimmed to `rag_char_budget=1600` chars.
- Rendered into the system prompt as a `## KNOWLEDGE (retrieved for THIS turn)` block
  (`rag.py:390 render_knowledge_section`).
- iter31: chunks frozen per state-visit (one retrieval per state entry, reused while
  in the same state — no re-embed per turn).

**Ingest path (the only one):** `engine/scripts/rag_ingest.py` — reads
`agent/knowledge_bases/*.md`, chunks with `diallux/rag.py::chunk_markdown`
(legacy chunker: produces header-only chunks when `##` directly precedes `###` —
46/233 chunks in prod are empty shells), embeds with `settings.rag_embedding_model`,
`rebuild=True` wipes + refills `public.kb_chunks`.

## Config keys (all in `diallux/config.py:46-62`; env-overridable via .env)

| key | live value | meaning |
|---|---|---|
| `RAG_MODE` | auto (prod .env: rag) | auto / rag / inline fallback |
| `rag_embedding_model` | `text-embedding-3-small` | **the embedder swap target** |
| `rag_top_k` | 3 | chunks per retrieval |
| `rag_filter_score` | 0.40 | **the threshold — unvalidated; measured spec = 0.24 under arctic** |
| `rag_char_budget` | 1600 | chars of excerpts per turn |
| `rag_min_query_chars` | 12 | skip embedding on filler turns |

## Where the numbers came from (summary; full table in 03_EXPERIMENTS.md)

- Prod corpus (233 chunks, OpenAI-embedded, in `diallux-db` docker, port 5434, db `diallux`, table `public.kb_chunks` vector(1536)).
- Legacy: Retell's `kb_config.filter_score=0.6` used Retell's INTERNAL scorer — never portable as raw cosine (comment preserved at `config.py:50`).
- The v2 chunker fix (lab: `diallux_kb_lab/scripts/corpus.py`) removes header-only chunks; 233→181 chunks, same KBs.
- Real-caller A/B (50 messy spoken queries): arctic+rerank 0.552 vs OpenAI+rerank 0.336; with FAQ KB + 0.24: 1.031.
- OpenAI cosine vs quality is anti-correlated on this corpus (junk scores 0.48–0.61, good answers 0.19–0.43) — threshold sweeps 0.30–0.60 all strictly worse than no filter.

## What connects the FAQ KB to the machine (later, owner session)

1. faq-kb.md is already in `agent/knowledge_bases/` (17 sections, slug `faq`).
2. After (re)ingest, retrieval only surfaces it in states whose prompts carry
   `##faq-kb##`. Suggested attachment: general_prompt.md (all sales states) —
   it is caller-FAQ content, harmless in Discovery/Closer/Offer; do NOT attach to
   the mechanical states (they pull nothing anyway by design).
3. No code edits required anywhere — marker in prompt + ingest + threshold.
