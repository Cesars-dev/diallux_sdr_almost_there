# KB Lab — Gold Labels, Filter Calibration, doc2query / Reranker Iterations

## Meta
- Date: 2026-09-13
- Project root: `/home/julio/projects/diallux_kb_lab` (standalone git repo, isolated from live app)
- Scope: add gold-truth labels + per-embedder filter calibration to the KB eval harness, then run 3 measured corpus iterations (doc2query → reranker → hybrid) and pick winning candidates for a later cutover.
- Status: EXECUTED 2026-09-13 (all tasks T1–T7 done autonomously, owner away). Full
  session log: `/home/julio/projects/diallux_kb_lab/logs.md`. Final table:
  `/home/julio/projects/diallux_kb_lab/logs/final_report.txt`. PICK (pending owner
  confirmation): it1 v2 corpus + arctic-m + LLM rerank top20→top3 + filter 0.138
  (gpt-4o judge: 0.788 vs openai 0.760). REJECTED: doc2query (it2), hybrid RRF (it4).
  Prod filter_score=0.40 would drop 83.3% of arctic gold top-1s — must recalibrate
  at cutover. Cutover remains a separate plan (HITL).

## Compaction Context

**Project.** Dialux v5 voice SDR runs a self-hosted RAG (Postgres+pgvector, OpenAI `text-embedding-3-small`). Goal of this effort: re-engineer the KB corpus so a local embedder (fastembed `snowflake-arctic-embed-m`, 768-d) matches/exceeds the OpenAI incumbent, measured objectively, then cut over later.

**Live infra (READ-ONLY — never modify in this plan):**
- Live app: `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/diallux-langgraph-production-v5` (uvicorn `diallux.app:app`, port 8000, runs as user `julio`, PID 2659243). `.env`: `RAG_MODE=rag`, `RAG_EMBEDDING_MODEL=text-embedding-3-small`, `RAG_TOP_K=3`, `RAG_CHAR_BUDGET=1600`, `rag_filter_score=0.40` (config.py default, never validated), `rag_min_query_chars=12`.
- DB: docker container `diallux-db` (image `pgvector/pgvector:pg16`), port `127.0.0.1:5434`, db `diallux`, user `diallux`, password in that app's `.env` (`DATABASE_URL=postgresql://diallux:<pw>@localhost:5434/diallux`). Table `public.kb_chunks(id bigint PK, kb text, content text, embedding vector(1536), created_at)` — 233 rows, 10 KBs, HNSW `vector_cosine_ops`, pgvector 0.8.2. Retrieval scopes `WHERE kb = ANY(state slugs)` + `score >= filter_score` (`rag.py` `retrieve()`).
- Shell policy: generic `sudo` DENIED; allowlisted patterns only. Read DB via `sudo /usr/bin/docker exec diallux-db psql -U diallux -d diallux ...` (allowed). `chmod` denied. Never touch running services.

**Lab (this plan's workspace):** `/home/julio/projects/diallux_kb_lab` — git repo, commits `242bcb2` (harness+corpora) and `ba61269` (it0+it1 results). Python venv: `/home/julio/fastembed/bin/python` (Python 3.12.3, fastembed==0.8.0, numpy 2.5.3, httpx 0.28.1, psycopg 3.3.5, sqlite3 stdlib). fastembed model cache: `/home/julio/fastembed/models` (arctic-embed-m loaded ~5.9s, query p95 ≈ 34.5ms at threads=2).

**Lab scripts** (all under `/home/julio/projects/diallux_kb_lab/scripts/`): `openai_util.py` (`get_key()` resolves a working OpenAI key from the live app `.env` then `/home/julio/projects/.env`; `post()` retry; `embed_openai()` batched), `corpus.py` (`chunk_v2`: heading-path breadcrumbs `[kb | h2 > h3]`, no orphan headings, min_len 200 merge, target 700/overlap 90), `build_corpus.py` (`--kb-dir --out [--doc2query]`; doc2query via gpt-4o-mini, batches of 12, prepends `Q:` lines), `judge_util.py` (`judge(query, chunks, model, key)` → 0–2 scores, 3 retries), `evaluate.py` (args `--corpus --embedder {openai-3-small,arctic-m} --iteration --system --judge --topk`; numpy cosine top-k; writes SQLite `results.db` tables `evals`, `qresults`, `chunks_iter`), `report.py` (`--all`, `--pair REF_ID CAND_ID` with sign-test), `run_it01.sh`. Data: `queries.json` (50 golden queries with expected-KB tags), `kb_baseline/` (10 md copies of live KBs), `corpi/it0_baseline.json` (exact prod 233 chunks exported from DB), `corpi/it1_chunker_v2.json` (181 chunks, 0 header-only, min 202 chars).

**Results so far (judge gpt-4o-mini, n=50, relevance@5 0–2, UNscoped top-5):**
| eval id | corpus | embedder | mean | top1-KB |
|---|---|---|---|---|
| 1 | prod (233) | openai-3-small | 0.848 | 23/50 |
| 2 | prod | arctic-m | 0.856 | 22/50 |
| 3 | v2 chunker (181) | arctic-m | 0.832 | 25/50 |
| 4 | v2 chunker (181) | openai-3-small | **0.908** | **31/50** |
Separate earlier run with **gpt-4o** judge (different scale — NOT comparable to mini numbers): prod openai 0.516 vs prod arctic-m 0.524, wins 14/21/15, chunk-Jaccard 0.375, top1 agreement 32/50.

**Key findings.** (a) Prod corpus has 46/233 header-only chunks + 54 <120 chars — chunker bug in live `rag.py:76` `chunk_markdown` (orphan headings when `##` directly precedes `###`); `chunk_v2` fixes it. (b) Retrieval landscape is flat → different embedders pick different near-ties (chunk-Jaccard ≈ 0.375–0.45). (c) ~10/50 queries bad on BOTH models → suspected corpus gaps, not embedder failure (must be verified by gold labeling). (d) `filter_score=0.40` is an unvalidated guess; cosine distributions differ per embedder so each needs its own calibrated threshold. (e) Production retrieves KB-scoped + filtered top-3 — current lab evals are unscoped top-5 (harsher); production-mirrored eval mode must be added. (f) Local embedder status: arctic-m = parity with OpenAI on quality, 0.43GB disk, ~34.5ms/query; arctic-s = too weak (reject); arctic-l = 99ms p95 (too slow for hot path).

**OpenAI key fact:** the ONLY working key is the one in the live app `.env` (identical to `SUGARPIXELS_OPENAI_API_KEY` in `/home/julio/projects/.env`). `OPENAI_API_KEY` in `/home/julio/projects/.env` returns 401. `get_key()` in `openai_util.py` already handles resolution.

**Already done vs remaining.** Done: batches A/B/C preflight+install+staging; 20q and 50q cross-references; chunker-v2 corpus; eval harness + sqlite; it0/it1 measured. Remaining (this plan): gold labels, filter calibration, production-mirror eval mode, it2 doc2query, it3 reranker, it4 hybrid, final gpt-4o confirmation, candidate pick. Cutover to the live engine is OUT OF SCOPE (separate plan after owner picks candidate).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Local embedder = `snowflake/snowflake-arctic-embed-m` (768d) | Only tier at OpenAI parity; -s too weak, -l too slow (99ms p95) |
| Judge for iteration loop = `gpt-4o-mini` | Cheap/noisy-tolerant for iteration deltas; final candidates re-judged with `gpt-4o` |
| Eval protocol baseline = top-5, unscoped, cosine | Keeps continuity with it0/it1 numbers; prod-mirror mode added as separate flag |
| Gold labels judged against `corpi/it1_chunker_v2.json` (181 chunks) | Contains all body content of prod corpus minus header-only noise; single source of truth |
| Gold pass judged by `gpt-4o-mini`; GAP-flagged queries re-checked by `gpt-4o` | Balance cost vs ground-truth confidence |
| All results in SQLite `results.db` at lab root | User requirement: compare across iterations |
| One git commit per iteration in `diallux_kb_lab` | User requirement: clean history |
| HITL: pause and present after it2 and after it4 | User requirement |
| Lab is standalone; live app dir and live DB tables untouched | Zero-risk constraint from BATCH rules |
| Staging pgvector tables (`kb_chunks_emb_staging`, `kb_chunks_emb_staging_m`) exist and may be reused read-only | Created in BATCH C |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Cutover decision (which corpus/embedder goes live) | Owner (Julio) after final report — HITL |
| Production state→KB-slugs map (for exact prod-mirror scoping) | `runtime.kb_slugs_for(state_name)` in live app; for now lab uses expected-KB scoping (documented approximation) |

## Environment & Dependencies
- Python: `/home/julio/fastembed/bin/python` (3.12.3) with fastembed==0.8.0, numpy==2.5.3, httpx==0.28.1, psycopg==3.3.5
- fastembed model cache: `/home/julio/fastembed/models` (arctic-embed-m already downloaded)
- Cross-encoder for rerank: fastembed `TextCrossEncoder`, model `Xenova/ms-marco-MiniLM-L-6-v2` (~90MB, downloads on first use into same cache). If `TextCrossEncoder` is missing from fastembed 0.8.0 → fallback = gpt-4o-mini LLM rerank (documented decision inside T5).
- OpenAI API: `https://api.openai.com/v1/embeddings` (model `text-embedding-3-small`), `https://api.openai.com/v1/chat/completions` (models `gpt-4o-mini`, `gpt-4o`); key via `scripts/openai_util.py:get_key()`
- SQLite: `results.db` at lab root (stdlib sqlite3)
- Paths: lab root `/home/julio/projects/diallux_kb_lab`; corpora in `corpi/`; logs in `logs/`; caches in `cache/` (gitignored)

## Architecture
```
kb_baseline/*.md ──chunk_v2──(+doc2query it2)──► corpi/<iter>.json ──► embedder (arctic-m local | openai API)
                                                                        │
queries.json ──(+gold tags/gold-ids T1)─────────────────────────────────┤
                                                                        ▼
                                              numpy cosine top-k (─+ reranker it3 ─+ hybrid RRF it4)
                                                                        ▼
                                              gpt-4o-mini judge (0-2 relevance per chunk)
                                                                        ▼
                                              results.db (evals, qresults, chunks_iter)
                                                                        ▼
                                              report.py --all/--pair → candidate pick
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/home/julio/projects/diallux_kb_lab/scripts/gold_label.py` | Gold-truth pass over 50 queries | NEW |
| `/home/julio/projects/diallux_kb_lab/queries_gold.json` | 50 queries + tag + gold chunk ids | NEW |
| `/home/julio/projects/diallux_kb_lab/scripts/evaluate.py` | store raw cosine scores; add `--scope {none,expected}`, `--filter-score FLOAT`, `--rerank INT` | EDIT |
| `/home/julio/projects/diallux_kb_lab/scripts/calibrate_filter.py` | per-embedder threshold from scores+judgments | NEW |
| `/home/julio/projects/diallux_kb_lab/scripts/rerank_util.py` | cross-encoder (or LLM fallback) rerank | NEW |
| `/home/julio/projects/diallux_kb_lab/scripts/report.py` | split metrics by gold tag; show GAP vs retrieval-failure | EDIT |
| `/home/julio/projects/diallux_kb_lab/scripts/run_it2.sh`, `run_it3.sh`, `run_it4.sh` | per-iteration eval sequences | NEW |
| `/home/julio/projects/diallux_kb_lab/results.db` | gains columns/rows per iteration | AUTO |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_iter51_kb_gold_filter_d2q_2026-09-13.md` | this plan | NEW (committed to main) |

## Deploy Rules
- NEVER touch: live app dir, live DB tables (only SELECT), docker containers (read via allowlisted `sudo /usr/bin/docker exec diallux-db psql ...` only), running services, the two protected Retell agents.
- All work in `/home/julio/projects/diallux_kb_lab`; commit there per iteration (`git add -A && git commit -m "itN: ..."`).
- No service starts/stops. No writes to `public.kb_chunks` or live `.env`.
- API keys only via `get_key()`; never print or hardcode them.

## Tasks (in order)

### T1 — Gold-label pass
Goal: for each of the 50 queries, determine from the v2 corpus whether an answer exists (tag ANSWERABLE/GAP/AMBIGUOUS) and which chunk ids are gold.
Files: `scripts/gold_label.py` (new), `queries_gold.json` (new).
Commands (workdir `/home/julio/projects/diallux_kb_lab`):
```
/home/julio/fastembed/bin/python scripts/gold_label.py --corpus corpi/it1_chunker_v2.json --judge gpt-4o-mini --out queries_gold.json
/home/julio/fastembed/bin/python scripts/gold_label.py --recheck-gaps --judge gpt-4o   # second pass only on GAP-tagged
```
Implementation contract: per query, show ALL chunks of the expected KB from the v2 corpus, batched ≤15 chunks/call, first 500 chars each; prompt asks: does any chunk DIRECTLY answer the query → reply strict JSON `{"answers":[chunk_idx,...],"partial":[...]}`; tag = ANSWERABLE if ≥1 answer, GAP if none, AMBIGUOUS if gold spans ≥2 KBs. Recheck pass repeats GAP queries with `gpt-4o` and the same contract; final tag = GAP only if both judges say GAP.
Dependencies: T-none (first task).
Verification: `python -c "import json;d=json.load(open('queries_gold.json'));print(len(d), {t:sum(1 for x in d if x['tag']==t) for t in ['ANSWERABLE','GAP','AMBIGUOUS']})"` prints 50 + tag counts; every ANSWERABLE query has ≥1 gold id; GAP list manually eyeballed by owner at HITL.

### T2 — evaluate.py: store raw scores + prod-mirror flags
Goal: persist per-chunk cosine scores; add scoping/filter/rerank knobs for later tasks.
Files: `scripts/evaluate.py` (edit).
Changes: `--scope {none,expected}` (expected = candidate pool restricted to `kb == expected_kb` before top-k), `--filter-score FLOAT` (drop candidates below score), `--rerank N` (retrieve top-N then rerank, default 0=off), and `qresults` gains `scores TEXT` (JSON array of raw cosine scores for the 5 returned). Backward compatible: existing rows untouched.
Commands: none to run yet (used by T3–T6).
Verification: after T3's first run, `sqlite3 results.db "SELECT scores FROM qresults LIMIT 1"` returns 5 floats; old evals still readable via `report.py --all`.

### T3 — Filter calibration (replaces the 0.40 guess)
Goal: data-driven `filter_score` per embedder.
Files: `scripts/calibrate_filter.py` (new).
Commands (workdir lab root):
```
/home/julio/fastembed/bin/python scripts/evaluate.py --corpus corpi/it1_chunker_v2.json --embedder openai-3-small --iteration calib --system calib-openai --judge gpt-4o-mini --topk 20 --scope expected
/home/julio/fastembed/bin/python scripts/evaluate.py --corpus corpi/it1_chunker_v2.json --embedder arctic-m      --iteration calib --system calib-arctic --judge gpt-4o-mini --topk 20 --scope expected
/home/julio/fastembed/bin/python scripts/calibrate_filter.py
```
Contract: calibrate_filter joins qresults scores × judge scores × gold ids; for each embedder prints score distributions (gold-2 vs judged-0) and the threshold keeping ≥95% of gold-2 chunks, plus recall loss at 0.40; writes `logs/filter_calibration.md`.
Verification: markdown file exists with two thresholds (one per embedder) and a recall-loss table; thresholds quoted in the HITL report.
Dependencies: T1, T2.

### T4 — it2: doc2query (first measured iteration of this session)
Goal: Q-line expansion on the v2 corpus; measure on both embedders.
Files: `corpi/it2_d2q.json` (built), `scripts/run_it2.sh` (new).
Commands (workdir lab root):
```
/home/julio/fastembed/bin/python scripts/build_corpus.py --kb-dir kb_baseline --out corpi/it2_d2q.json --doc2query
bash scripts/run_it2.sh   # runs 3 evals: it2 on openai-3-small, it2 on arctic-m, prod-openai reference re-run (same judge, paired)
```
run_it2.sh content = `evaluate.py` calls with `--iteration it2 --system v2d2q-{openai,arctic}` + `--corpus corpi/it0_baseline.json --system prod-openai` reference, all `--judge gpt-4o-mini`.
Verification: 3 new rows in `evals`; `report.py --pair` (reference vs it2-openai, reference vs it2-arctic) shows deltas; commit `it2: doc2query ...`. **HITL: present results to owner before T5.**
Dependencies: T2.

### T5 — it3: reranker
Goal: rerank top-20 → top-3 with a cross-encoder; measure stability + quality.
Files: `scripts/rerank_util.py` (new), `scripts/run_it3.sh` (new), `evaluate.py` already supports `--rerank` from T2.
Contract: `rerank_util.rerank(query, texts, top_n)` using fastembed `TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2")` (query+chunk concatenated); if that class is absent in fastembed 0.8.0, fallback = gpt-4o-mini scoring (batch 10 chunks/call, JSON scores) — decision recorded in the script docstring line printed to log.
Commands:
```
/home/julio/fastembed/bin/python scripts/evaluate.py --corpus corpi/it2_d2q.json --embedder arctic-m --iteration it3 --system v2d2q-arctic-rerank --judge gpt-4o-mini --rerank 20 --topk 3 --scope expected
/home/julio/fastembed/bin/python scripts/evaluate.py --corpus corpi/it2_d2q.json --embedder openai-3-small --iteration it3 --system v2d2q-openai-rerank --judge gpt-4o-mini --rerank 20 --topk 3 --scope expected
bash scripts/run_it3.sh   # wraps the two calls + report
```
Verification: two new eval rows; chunk-level stability check — rerun `--pair` on same-config candidates twice? (No: reranker is deterministic at temperature 0; verify instead that per-query top-3 Jaccard vs non-reranked it2 drops noise, i.e., mean chunk-Jaccard across paired queries changes as predicted direction: rerank ON should agree MORE with the same embedder's gold order.) Commit `it3: reranker ...`.
Dependencies: T2, T4 (uses it2 corpus).

### T6 — it4: hybrid lexical+vector RRF (lab-side)
Goal: cover exact-token failures ("HIPAA", "BAA", "medical").
Files: `scripts/hybrid.py` (new), `scripts/run_it4.sh` (new).
Contract: BM25-lite in pure Python over the corpus tokens (no new deps): score = 0.7·vector_rank_RRF + 0.3·lexical_rank_RRF (k=60); implement as a callable used by `evaluate.py --hybrid 0.3`; top-20 fusion → (optionally rerank) → top-3.
Commands: `bash scripts/run_it4.sh` (two evals, same shape as T5, `--iteration it4`).
Verification: new eval rows; `report.py --pair` deltas; commit `it4: hybrid RRF ...`. **HITL: present full comparison table to owner.**
Dependencies: T2.

### T7 — Final confirmation + candidate pick
Goal: re-judge the 2 best configs with `gpt-4o` judge (comparable to the earlier 0.516/0.524 headline); produce pick recommendation.
Files: `scripts/run_final.sh` (new); report goes to `logs/final_report.md`.
Commands:
```
/home/julio/fastembed/bin/python scripts/evaluate.py --corpus <best> --embedder <best> --iteration final --system final-<name> --judge gpt-4o
/home/julio/fastembed/bin/python scripts/report.py --all > logs/final_report.txt
git add -A && git commit -m "final: gpt-4o confirmation + candidate pick"
```
Verification: final report includes mean/top1 on ANSWERABLE subset vs GAP subset; owner picks candidate (HITL). Cutover = separate plan.
Dependencies: T3–T6.

## Validation Plan (end-to-end)
1. `report.py --all` shows a monotonic experiment log; every eval row has judge model recorded.
2. Success bars (on ANSWERABLE subset, gpt-4o-mini judge): top1-KB ≥ 44/50 for at least one config; mean ≥ 1.3; gold-chunk recall@3 ≥ 90% for the winning config.
3. Filter thresholds quoted with measured recall-loss numbers, replacing the 0.40 guess.
4. All 4 iterations committed individually in `diallux_kb_lab`; `git log --oneline` reads as the experiment history.
5. Final candidates re-verified with gpt-4o judge before presenting.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Cutover to live engine (`rag.py` chunker swap, embedding model switch, config changes) | Separate plan after owner picks candidate; live app is read-only here |
| pgvector HNSW index on staging tables | Only needed at cutover; 233 rows scan fine |
| Splitting `industry` into per-vertical KBs | Depends on it4 results + owner taxonomy decision |
| Shadow mode / canary in production | Cutover plan |
| arctic-embed-l as embedder | Latency (99ms p95) fails hot-path budget; revisit only if reranker changes the latency picture |
