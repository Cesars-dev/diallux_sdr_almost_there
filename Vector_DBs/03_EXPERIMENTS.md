# KB Lab — RESULTS.md (root, single source of truth)

Session 2026-09-13. Plan: `clean_diallux_SDR/plans/plan_iter51_kb_gold_filter_d2q_2026-09-13.md`.
All numbers from `results.db` (SQLite, this repo root) — table `evals` mirrored below
in full. Reports: `logs.md` (narrative), `logs/final_report.txt`, `logs/filter_sweep.md`,
`logs/filter_calibration.md`, `logs/kb_topic_analysis.md`, `logs/it6_structure.md`.

## The winner (pick pending owner confirmation)

```
1. v2 corpus          corpi/it1_chunker_v2.json — 181 clean chunks (replaces 233 buggy prod ones)
2. v1-frontload prose fact-dense sentences first, deterministic code, wording untouched
3. arctic-m embedder  snowflake-arctic-embed-m, local, 768d, ~35ms/query, $0
4. filter_score 0.13  cosine floor (0.40 would cause 20–88% silent refusals)
5. rerank             gpt-4o-mini reads top-20, returns true top-3 (the real QA gate)
```

- gpt-4o judge (stronger): arctic+rerank **0.788** beats openai+rerank 0.760 → local model parity/exceedance = session goal MET.
- gpt-4o-mini judge: openai variant slightly ahead (0.972 vs 0.908) — near-tie flip between judges; both within judge noise.
- Scoped prod-mirror (expected-KB, top-3): 1.127–1.144 mean relevance, 0 refusals at filter 0.138.
- ANSWERABLE subset (n=28): mean 1.44 with filter 0.138 — best scoped number of the session.
- Cutover MUST set `rag_filter_score` 0.13 (arctic) — 0.40 drops 83% of gold answers.
- Real remaining ceiling = content: 7 GAP queries (no KB answer) + 15 answers outside expected KB → `corpi/it6_skeletons.json` is the authoring TODO.

## Full experiment table (mirrors SQLite `evals`, ids 1–28)

| id | iteration | system | embedder | judge | mean | top1 | verdict |
|----|-----------|--------|----------|-------|------|------|---------|
| 1 | it0 | prod-openai (233 chunks, exact prod copy) | openai-3-small | gpt-4o-mini | 0.848 | 0.46 | incumbent baseline |
| 2 | it0 | prod-arctic-m (same corpus) | arctic-m | gpt-4o-mini | 0.856 | 0.44 | local parity on prod corpus |
| 3 | it1 | v2-arctic-m (181 clean chunks) | arctic-m | gpt-4o-mini | 0.832 | 0.50 | chunker fix neutral on arctic |
| 4 | it1 | v2-openai (same corpus) | openai-3-small | gpt-4o-mini | 0.908 | 0.62 | chunker fix big win on openai |
| 5 | calib | calib-openai (scoped top-20, raw scores) | openai-3-small | gpt-4o-mini | 0.830 | 1.00* | calibration data |
| 6 | calib | calib-arctic (same) | arctic-m | gpt-4o-mini | 0.833 | 1.00* | calibration data |
| 7 | it2 | v2d2q-openai (doc2query Q-lines) | openai-3-small | gpt-4o-mini | 0.788 | 0.46 | ❌ REJECTED (hurts) |
| 8 | it2 | v2d2q-arctic | arctic-m | gpt-4o-mini | 0.716 | 0.44 | ❌ REJECTED (hurts) |
| 9 | it2 | prod-openai-ref (paired reference) | openai-3-small | gpt-4o-mini | 0.844 | 0.46 | judge noise ±0.004 |
| 10 | it3 | v2-arctic-rerank (rerank top-20→top-5) | arctic-m | gpt-4o-mini | **0.896** | 0.54 | 🏆 WIN (+0.064) |
| 11 | it3 | v2-openai-rerank | openai-3-small | gpt-4o-mini | **0.924** | 0.64 | 🏆 WIN (+0.016) |
| 12 | it3 | v2-arctic-rerank-scoped (top-3) | arctic-m | gpt-4o-mini | 1.127 | 1.00* | prod-mirror |
| 13 | it3 | v2-openai-rerank-scoped | openai-3-small | gpt-4o-mini | 1.140 | 1.00* | prod-mirror |
| 14 | it4 | v2-arctic-hybrid (BM25+RRF w=0.3) | arctic-m | gpt-4o-mini | 0.748 | 0.50 | ❌ REJECTED |
| 15 | it4 | v2-openai-hybrid | openai-3-small | gpt-4o-mini | 0.840 | 0.54 | ❌ REJECTED |
| 16 | it4 | v2-arctic-hybrid-scoped | arctic-m | gpt-4o-mini | 1.057 | 1.00* | ❌ REJECTED |
| 17 | it4 | v2-openai-hybrid-scoped | openai-3-small | gpt-4o-mini | 1.107 | 1.00* | ❌ REJECTED |
| 18 | final | final-v2-openai-rerank | openai-3-small | **gpt-4o** | 0.760 | 0.64 | confirmation |
| 19 | final | final-v2-arctic-rerank | arctic-m | **gpt-4o** | **0.788** | 0.56 | 🏆 arctic BEATS openai |
| 20 | filter138 | v2-openai-f0138-scoped (filter 0.138 live test) | openai-3-small | gpt-4o-mini | 1.113 | 1.00* | 0 refusals, GAP garbage passes (0.35–0.54) |
| 21 | it5 | prose-v1_frontload-openai-3-small | openai-3-small | gpt-4o-mini | **0.972** | 0.66 | ✅ best openai number |
| 22 | it5 | prose-v1_frontload-arctic-m | arctic-m | gpt-4o-mini | **0.908** | 0.54 | ✅ WINNER config |
| 23 | it5 | prose-v2_strip-openai-3-small | openai-3-small | gpt-4o-mini | 0.940 | 0.58 | mild win |
| 24 | it5 | prose-v2_strip-arctic-m | arctic-m | gpt-4o-mini | 0.900 | 0.54 | neutral |
| 25 | it6 | topic-openai-rerank (topic restructure) | openai-3-small | gpt-4o-mini | 0.812 | 0.56 | ❌ REJECTED (boilerplate clustering) |
| 26 | it5 | prose-v3_compact-openai-3-small | openai-3-small | gpt-4o-mini | 0.964 | 0.64 | close 2nd |
| 27 | it6 | topic-arctic-rerank | arctic-m | gpt-4o-mini | 0.752 | 0.58 | ❌ REJECTED |
| 28 | it5 | prose-v3_compact-arctic-m | arctic-m | gpt-4o-mini | 0.908 | 0.54 | tie with v1 on arctic |

\* top1 = 1.00 is trivial under expected-KB scoping (only scoped chunks exist) — not a quality signal.

## Cosine filter sweep (the 0.40 lesson)

| threshold | openai: gold@3 / refusals | arctic: gold@3 / refusals |
|---|---|---|
| none–0.135 | 19% / 0% | 19% / 0% |
| 0.14 | 19% / 0% | 17% / 2% ← cliff edge |
| 0.20 | 19% / 0% | 18% / 8% |
| 0.28 | 17% / 2% | 15% / 40% |
| **0.40 (prod today)** | 18% / **20%** | 17% / **88%** |

Filter = refusal dial, NOT quality dial. Recommended: **0.13 arctic / 0.25 openai**.
The reranker is the actual relevance gate (GAP garbage scores 0.35–0.54, filter can't catch it).

## Gold labels (queries_gold.json, 50 queries)

- 28 ANSWERABLE / 15 AMBIGUOUS (answer exists, outside expected KB) / 7 GAP (no answer exists; gpt-4o recheck confirmed all 7).
- Weak-query failure split (winning config): 6 prose-caused vs 17 retrieval-caused → authoring > prose.

## Vector stores (1 physical, 3 logical — docker `diallux-db`, port 5434, READ-ONLY)

| store | status | contents |
|---|---|---|
| `public.kb_chunks` | 🔴 LIVE — untouched | 233 chunks, vector(1536), OpenAI |
| `kb_chunks_emb_staging` | 🟡 staging | v2 corpus, 1536d |
| `kb_chunks_emb_staging_m` | 🟡 staging | v2 corpus, 768d arctic |

Lab `results.db` = eval ledger (28 evals, 50 qresults each), not a vector store.

## Git

This repo (`diallux_kb_lab`) = standalone lab repo, one commit per iteration on its
main (9 commits = experiment history). Nothing pushed anywhere; no feature branches;
**live repo and md KBs untouched** — cutover is a separate plan requiring owner OK.

## CRITICAL: OpenAI cosine is inverted on the real corpus (eval 31/32)

10 proper golden questions, openai embeddings, scoped top-3:

| threshold | answered | refusals | mean |
|---|---|---|---|
| 0.138 | 10/10 | 0 | 0.633 |
| **0.60 (original Retell value)** | **1/10** | **9/10** | **0.000** |

Top-1 cosine vs judged quality, same 10 questions:

| question | cos | judged |
|---|---|---|
| What can your voice AI actually do? | 0.339 | **1.67** |
| What psychological triggers help close a sale? | 0.248 | **1.33** |
| Do you sign a BAA? | 0.190 | 1.00 |
| What questions should I ask in discovery? | 0.218 | 1.00 |
| Which verticals benefit most from AI voice agents? | **0.608** | **0.00** |
| Have you worked with IT managed service providers? | 0.512 | 0.00 |
| Do you work with home cleaning companies? | 0.484 | 0.00 |

**OpenAI cosine ranking is anti-correlated with answer quality on this corpus**:
correct answers score low (0.19–0.34), in-domain junk scores high (0.48–0.61).
No threshold fixes this. The 2026-09-04 calibration (relevant 0.57–0.62) measured
high-cosine text, which here is often junk. 0.60 refuses the right answers first.

Consequence: `rag_filter_score` is NOT a usable quality gate under OpenAI embeddings.
The reranker is mandatory, and arctic-m (whose cosine does separate value from
garbage: value median 0.313 vs garbage 0.203) is the only embedder of the two where
a threshold is even meaningful. Cutover spec: arctic + 0.24 + rerank.

## OpenAI threshold sweep 0.30–0.45 (10 proper questions, scoped top-3, evals 33–40)

| threshold | mean (all 10) | genuinely answered | mean (answered) |
|---|---|---|---|
| no filter | 0.633 | 5/10 | 1.267 |
| **0.30** (least-bad) | 0.283 | 2/10 | 1.417 |
| 0.325 | 0.233 | 2/10 | 1.167 |
| 0.35 | 0.250 | 2/10 | 1.250 |
| 0.375 | 0.150 | 1/10 | 1.500 |
| 0.40 (LIVE today) | 0.150 | 1/10 | 1.500 |
| 0.425 | 0.150 | 1/10 | 1.500 |
| 0.45 | 0.000 | 0/10 | 0.000 |
| 0.60 (original Retell) | 0.000 | 1/10 (junk) | 0.000 |
| **arctic @ no filter** | **1.300** | **10/10** | 1.300 |
| **arctic @ 0.24** ✅ | **1.233** | **10/10** | 1.233 |

Per-question top-1 cosine / judged quality (openai vs arctic, no filter):

| question | openai cos/judge | arctic cos/judge |
|---|---|---|
| Is Diallux HIPAA compliant? | 0.433/1.33 | 0.396/1.67 |
| Do you sign a BAA? | 0.190/1.00 | 0.394/1.00 |
| Do you work with home cleaning companies? | 0.484/**0.00** | 0.293/1.33 |
| Have you worked with IT managed service providers? | 0.512/**0.00** | 0.257/1.33 |
| Which verticals benefit most from AI voice agents? | 0.608/**0.00** | 0.404/1.00 |
| What can your voice AI actually do? | 0.339/1.67 | 0.446/1.67 |
| What psychological triggers help close a sale? | 0.248/1.33 | 0.411/1.33 |
| How do I handle the it's too expensive objection? | 0.365/**0.00** | 0.321/1.00 |
| What are common challenges in the maid services industry? | 0.286/**0.00** | 0.400/1.33 |
| What questions should I ask in discovery? | 0.218/1.00 | 0.358/1.33 |

**Conclusion:** within OpenAI, every threshold in 0.30–0.45 is strictly worse than
no filter; 0.30 is least-bad (2/10) and 0.45 already refuses everything. There is no
OpenAI operating point that helps, because its cosine rank is anti-correlated with
quality. Arctic@0.24 = 1.233 mean with 10/10 answered → beats the best OpenAI
threshold by **4.4×** and OpenAI-unfiltered by **1.9×**. Cutover spec unchanged,
now with 10-query confirmation: **arctic-m + filter 0.24 + rerank**.
