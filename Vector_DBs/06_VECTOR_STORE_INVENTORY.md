# 06 — Vector store & data inventory (everything that exists, 2026-09-13)

## Physical

| store | where | dims | embedder | chunks | status |
|---|---|---|---|---|---|
| `public.kb_chunks` | docker `diallux-db`, pgvector/pg16, port 127.0.0.1:5434, db `diallux`, user `diallux` | vector(1536) | OpenAI text-embedding-3-small | 233 (10 KBs) | 🔴 LIVE — read-only in this project |
| `public.kb_chunks_emb_staging` | same container | 1536 | OpenAI | 181 (v2 corpus) | staging (BATCH C), read-only |
| `public.kb_chunks_emb_staging_m` | same container | 768 | arctic-m | 181 (v2 corpus) | staging (BATCH C), read-only |
| `faiss/none` | — | — | — | — | does not exist (pgvector only) |

Read pattern (allowlisted): `sudo /usr/bin/docker exec diallux-db psql -U diallux -d diallux ...` (SELECT only).

## Data files (lab repo `/home/julio/projects/diallux_kb_lab`)

| file | what |
|---|---|
| `results.db` (SQLite, 1.5MB) | FULL experiment ledger: 30 evals, 1500 qresults (raw cosine scores per chunk!), 2006 chunk texts |
| `results.db` tables | `evals`, `qresults` (per-query: judge mean, top-k chunk ids, cosines, config JSON), `chunks_iter` |
| `queries.json` / `queries_real.json` / `queries_proper10.json` | 50 golden / 50 messy real-caller / 10 proper test sets |
| `queries_gold.json` | gold-truth labels (28 ANSWERABLE / 15 AMBIGUOUS / 7 GAP) |
| `corpi/it0_baseline.json` | exact prod 233-chunk export |
| `corpi/it1_chunker_v2.json` | v2 corpus, 181 clean chunks (the WINNER corpus) |
| `corpi/it2_d2q.json`, `it5_*.json`, `it6_*.json`, `it7_faq.json` | rejected-experiment corpora + the v2+FAQ corpus (193 chunks) |
| `corpi/it6_skeletons.json` | 7 GAP skeletons (superseded by faq-kb.md owner answers) |
| `kb_baseline/` | read-only copies of the 10 live KB md files |
| `cache/` | openai embed caches, gold-label caches (gitignored) |
| `logs/` | filter sweeps, retrieval dumps, topic analysis, it6 structure map |

## Model caches & paths

| thing | path |
|---|---|
| fastembed arctic-embed-m model (0.43GB) | `/home/julio/fastembed/models` |
| lab python venv (fastembed 0.8.0, numpy, httpx, psycopg) | `/home/julio/fastembed/bin/python` |
| lab repo (git, 12+ commits) | `/home/julio/projects/diallux_kb_lab` |
| KB md sources (live) | `engine/agent/knowledge_bases/*.md` (10 KBs + **faq-kb.md, new**) |
| this pack | `/home/julio/projects/clean_diallux_SDR/Vector_DBs/` |

## `vector_dbs.sqlite` (this folder)

Lite queryable mirror for any agent: tables `vector_stores`, `kb_inventory`,
`config_keys`, `thresholds`, `evals_summary`, `decisions`, `faq_status`.
The FULL raw evidence stays in the lab `results.db` (this is the summary).
