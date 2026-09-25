# PLAN — v5 iter52: Pinned Industry Chunk (tag-matched, fetch-once)

## Meta
- Date: 2026-09-16 (v3; supersedes the v1 text committed at `eccb6b0` and the v2 text. **v3 change — owner directive: two-layer Plumbing is IN SCOPE**: the condensed `Plumbing` vertical is authored + ingested this iteration (20th vertical, what the pin grabs), the deep-dive `plumbing` KB is ingested + vectorized and scoped to the engine on the `plumb` trigger, and the `plumbing`/`plumber` alias ships in T3. Also fixes two v2 doc errors: plumbing is the 4th-most-common dv (not 2nd), and the delta-vs-history share is ~18% (not ~9%).)
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: tag every `industry` KB chunk with its vertical at ingest; at runtime resolve `{{industry}}` → tag **once**, fetch that vertical's chunks by **metadata lookup** (no embed, no pgvector), pin them in per-call state, and re-inject from the pin into the post-history RAG delta every round — killing the biggest re-fetcher and freeing all 3 `top_k` slots for the dynamic KBs (`pain-points`, `sales-language`, …). Two-layer Plumbing rides the same iteration: condensed `Plumbing` vertical inside `industry` (pinned) + separate `plumbing` deep-dive KB (scoped, retrieved, never pinned).
- Status: **APPROVED by owner 2026-09-16** (v3 scope) — executing T1→T8. Surgeon procedure backing this plan: `research/surgeon/iter52-industry-pin/` (01_audit → 02_action_plan → 03_cross_reference → 04_master_plan; all flaws closed).

## Compaction Context (session state at plan time — pin, do not re-derive)

- **MVP-Finally is MERGED to main.** Merge `4559a33`, tag `mvp-finally`, suite **305** re-verified on the main checkout. main HEAD at v2 time = `21fe6b0` (docs) → `eccb6b0` (this plan v1) → `fc2fa2f` (mvp-finally docs). Post-merge layout: engine tree lives under `engine/` in the outer repo; NEW iteration branches cut from `main` and merge back normally.
- **Motivating RAG analysis (run `happy-chat-c`, 4 happy paths, 37 real retrievals):** retrieval p50 98ms; KB hit frequency `industry` 23 / `sales-psychology` 15 / `sales-language` 12 / `call-closing` 9 / **`pain-points` 1**. `industry` is the single biggest re-fetcher — the same 1-of-3 vertical chunks re-embedded + re-vector-searched every heavy round.
- **Corpus reality (queried live 2026-09-16, v2 session):** `kb_chunks_v2` = 193 rows, 768-d arctic-m, columns `id, kb, content, embedding, created_at` — **NO vertical column today**. `kb='industry'` = 57 rows = **19 verticals** (18×3 + Home Remodeling ×2: it has Voice AI Solutions + ROI Metrics, no Pain Points chunk) **+ 1 KB-header row** (id 46). Content heading format (verified on ALL 56 content rows): `[industry | Industry-Specific Sales Knowledge Base > <Vertical> > <Section>]`, Section ∈ {Business Owner Pain Points, Voice AI Solutions, ROI Metrics}. Parser regex validated live: **56/56 parsed, 0 unparsed, 1 header** — deterministic, NO LLM/classifier needed. Chunk lengths 428–673 (avg 529); **per-vertical totals 984–1709 chars** (max = Residential Roofing & Solar Installers).
- **Runtime facts (main @ 21fe6b0):** `build_lanes` at builder.py:869 (lane B scopes `_STATE_KBS`; industry ∈ Intake/Discovery/Closer/Offer scopes, NOT Closing; **no `#[refer industry…]` tag exists in any prompt** — industry is reachable ONLY via lane B scope). `_live_retrieve` at builder.py:918 is the ONLY compose point (bg task `_live_task` :971 → `_consume_live_retrieve` :994 bounded-awaits 60ms → post-history delta :1529–1553). `initial_state` at :2028 resets per-call state. Cache layout: `tail_before_history=True` → prefix [tools][head][state-block][history] byte-frozen; the post-history delta is ALREADY replaced every turn — pin bytes there are cache-free. Entry-lite acks override the delta with a speech directive (no pin on acks, by design). Parity tests pin `_STATE_KBS` exact, `build_lanes` shapes (called positionally!), `merge_lane_chunks` quota/dedupe, and live-delta prefix stability (tests/test_iter49_rag_parity.py).
- **Real `{{industry}}` dv variants (428 json_logs, extracted v2 session — 60 distinct values):** dental practice (71), personal injury law firm (33), auto repair shop (26), hardware store (21), landscaping (19), real estate office (16), auto repair (15), Plumbing/plumbing (28), home remodeling and contractor* (~35), roofing (6), restaurant (6), med spa, law firm, dentist, medical clinic, healthcare, unknown (6), plus noisy forms ("personal injury law firm in New York, NY, Bell & Associates Legal", "dental practice in Phoenix, Arizona, offering…"). **Gap: hardware store, real estate, restaurant, tour operator, tech consultancy have NO vertical among the canonical set** — today they ride lane-B similarity; the resolver must be no-worse (embed fallback → miss → today's vector lane). Plumbing WAS in this gap (3rd/4th-most-common dv family, 28 hits; currently retrieves ZERO industry chunks — best 0.20 < 0.24) and is CLOSED by this plan: **Plumbing becomes its OWN condensed vertical** in `industry` (NEVER nested under "HVAC & Home Services"), with a separate `plumbing` KB as the deep-dive manual (owner directive 2026-09-16; drafts at `vps-inbox/plumbing-kb.md` and `plumbing-niche.md`). iter52 ships the vertical + the resolver alias `plumbing`/`plumber` → **Plumbing** (this is what iter52 pins).
- **Traps found by the v2 audit (all closed in this plan):** (1) `kb_reembed.py` is idempotent by `(kb, sha256(content))` — a plain re-run tags NOTHING; a backfill UPDATE is required. (2) 3 chunks ≈ 1600 chars = the entire `rag_char_budget` — the pin must sit OUTSIDE the merge with its own cap. (3) `merge_lane_chunks` is parity-pinned — leave it untouched; remove industry at the `build_lanes` scope level instead. (4) the v1 T3 extraction command crashes (`turns[0]` is an int) — fixed below. (5) worktree json_logs is EMPTY — variant extraction runs from the MAIN checkout.
- **Owner directive (2026-09-16):** "match `{{industry}}` to tag the chunk embedder, then we always use that, we leave it as a pinned chunk." Plan on another session, another branch. v2 directive: no code in the planning session; another model executes.

## Resolved Decisions (DO NOT revisit)

| Decision | Rationale |
|---|---|
| Iteration = **iter52**; branch `engine/iter52-industry-pin`; base **`main` @ `eccb6b0`** (docs-only commits above it — `21fe6b0`…`5b4432c` — are harmless) | next free engine number; post-merge layout branches from main and merges back normally |
| Vertical tag = **new nullable column `vertical TEXT` on `kb_chunks_v2`**, set by `kb_reembed.py` (the table's sole owner), parsed from the content heading; **NO new index**; `kb_chunks` NEVER touched | heading parse is deterministic (56/56 validated); 57 industry rows sit behind the existing `kb_chunks_v2_kb_idx` — an extra index is DDL for zero gain |
| **diallux-db schema rule reconciliation:** the "NEVER touch docker diallux-db schema" rule = no UNPLANNED mutations; `kb_chunks_v2` is engine-owned by `scripts/kb_reembed.py` (AGENTS KB policy: one owner per table) and was CREATED on this container by owner-approved iter49; this owner-directed additive migration (`ADD COLUMN IF NOT EXISTS vertical TEXT`, nullable) is the sanctioned path. Rollback = `rag_pin_industry=False` (zero schema dependency) or `ALTER TABLE kb_chunks_v2 DROP COLUMN vertical` | removes the apparent v1 self-contradiction (plan forbade what it prescribed) |
| Tagging convention: **57/57 existing industry rows tagged** — 56 with their vertical, 1 header row tagged literal `header`; header is never pinned, never resolved-to (stoplisted, and the embed fallback skips a header top-1). The NEW `Plumbing` vertical (3 chunks) is written WITH vertical at INSERT (no backfill needed) | defense in depth ×3 against pinning instruction noise |
| Pin fetch = **metadata lookup** `WHERE kb='industry' AND vertical=$tag ORDER BY id` — NO embed, NO `<=>`; try/except → `[]` on ANY failure (missing column, DB down) → caller degrades to today's vector lane | the vertical is a per-call constant once known; a vector search re-computes a constant; fresh/hermetic tables lack the column (KBStore._ensure_schema doesn't create it) |
| **Pin lives OUTSIDE the merge**: when pinned, `build_lanes` drops `industry` from lane scopes (query text unchanged); `merge_lane_chunks` is UNTOUCHED; the pin renders as its own block prepended to the per-turn KNOWLEDGE in the post-history delta | v1's "quota-exempt owned chunks in merge_lane_chunks" is REVISED (superseded): merge is parity-pinned AND 3 chunks ≈ the whole 1600 budget — scope-removal achieves the same freed slots with a smaller blast radius |
| Pin char cap = **`rag_pin_char_budget: int = 1800`**, whole-chunk drops only (never mid-chunk truncation); pinned chunks are exempt from `rag_char_budget` | measured max vertical total = 1709 + margin; T2 asserts every vertical ≤ 1800 so no vertical is ever truncated |
| Pin placement = **post-history delta ONLY, live mode ONLY** (`rag_live_retrieve=True`); prefix/tools/head untouched; `rag_live_retrieve=False` → iter48 exact, no pin | the delta slot is already replaced every turn (cache-free); the industry dv can change mid-state so the pin must never enter the byte-frozen pre-history tail; the two revert flags compose |
| **Delta composition invariant — the pin can NEVER be evicted by a threshold.** (a) no delta/section trimming exists today: the "~5k ceiling" is the HISTORY window (`_history_window`, builder.py:1110 trims only history entries); `_build_messages` (builder.py:607) appends the delta whenever non-empty (:622), unbudgeted and unsliced; (b) the only budgets are `merge_lane_chunks`/`retrieve` (dynamic chunks only) — pin and dynamic are composed as separate blocks, pin FIRST; (c) the delta is REPLACED each round (:1532), never appended, so it cannot grow over the call; (d) **reserve order if a global delta cap is ever introduced: pin first (reserved), dynamic fills the remainder — trimming, if any, applies to dynamic whole-chunks only, NEVER the pin.** | measured max delta = 1800 + 1600 chars + headers ≈ 880 tk vs the ~5k history ceiling (~18%); the pin is a per-call constant and the industry context MUST survive any future budget pressure |
| Pin fetch happens **once per call**, lazily, inside the bg `_live_retrieve` task (off the hot path); **invalidate + re-resolve if the dv value changes**; pin state resets in `initial_state` with the other per-call state | industry dv is set during Discovery and stable afterward; fetch = one asyncpg SELECT (~ms) |
| Resolver = 5-step ladder: normalize → stoplist → **alias map** (word-boundary substring, every alias → exactly ONE tag, sorted longest-first; **≥2 distinct tag hits = ambiguous → embed fallback, never guess**) → **embed fallback** (ONE `store.retrieve(dv, ["industry"])`, top-1 score ≥ `rag_filter_score`, skip header, `vertical_of(id)`) → None → today's vector lane | free text vs canonical tags; never block, never regress; "roofing contractor" must not lose to a generic "contractor" (which is why "contractor" alone is NOT an alias) |
| `build_lanes` gains `pinned_tag: str | None = None` (optional, default None = byte-exact today) | parity tests call it positionally; default-off keeps the 305 green |
| Tracer contract: every live rag span gains `"pinned": tag or ""`; each pin resolve logs ONE `rag:pin` span; reported `kbs` gains `"industry"` when pinned | makes T8's fetch-once gate a named SQL query |
| Kill switch `rag_pin_industry: bool = True` (env `RAG_PIN_INDUSTRY`); `False` = byte-exact today | rollback safety, mirrors `rag_live_retrieve` precedent |
| `lf_quick.py` gains `--db` (default unchanged), mirroring `live_sql.py` | v1 left it "decide in-session"; decided |
| Embedder model, `rag_filter_score` (0.24), prompt-cache mechanism, prompts: **unchanged** | this iteration only changes WHICH industry chunks are selected and HOW they are fetched |

## BLOCKED / NEEDS INPUT

| Item | Where to get it |
|---|---|
| ~~Owner approval to start~~ **GRANTED 2026-09-16** (v3 scope: two-layer Plumbing IN, deep-dive KB vectorized) | owner |
| Confirm the 20 canonical tags post-T2 (do NOT hardcode — the alias-integrity test reads `SELECT DISTINCT vertical` live) | T2 verification SQL |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv` (3.12.3). Worktree venv = symlink to it.
- Postgres/pgvector: DSN = `DATABASE_URL` in `/home/julio/projects/clean_diallux_SDR/engine/.env` (do NOT assume a port; read the var). Table `kb_chunks_v2`, 193 rows, 768-d. Docker container `diallux-db`.
- Embedder: `snowflake/snowflake-arctic-embed-m` (local in-process fastembed; queries get the arctic prefix, documents do not).
- Corpus source (read-only): `/home/julio/projects/diallux_kb_lab/corpi/it7_faq.json` — **extended in T2 to `it8_plumbing.json`** (193 existing rows verbatim + the condensed `## Plumbing` vertical chunks + the `plumbing` deep-dive KB chunks; built with the KB-Lab v2 chunker `chunk_v2`, same heading format). The plumbing CONTENT sources (`vps-inbox/plumbing-niche.md`, `vps-inbox/plumbing-kb.md`) are read-only inputs; new corpus file lives in `diallux_kb_lab/corpi/`.
- Langfuse: `http://localhost:3001` (keys in `engine/.env`).
- Worktree: `/tmp/opencode/wt-iter52`.
- Call/findings ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (schema + gates: `research/surgeon/iter48-rag-truth/SQL_ANALYSIS_SOP.md`).
- NEVER touch: live services `:8000`–`:8006`, owner port `:8007`, production agent IDs, deployed Retell LLMs, `kb_chunks` table (SELECT-count only), Cal.com event `3801235` (REAL — cancel every test booking), the ORIGINAL workspace.

## Architecture (one block diagram)
```
INGEST (once, T2):
  kb_reembed.py  (owns kb_chunks_v2)
    ALTER TABLE kb_chunks_v2 ADD COLUMN IF NOT EXISTS vertical TEXT
    parse heading "> <Vertical> >" -> tag (regex, 56/56 validated; header row -> 'header')
    INSERT new rows WITH vertical + BACKFILL UPDATE every existing industry row (idempotent)
    corpus it8_plumbing.json: + condensed '## Plumbing' industry vertical (20th, pinned layer)
                              + 'plumbing' deep-dive KB (scoped layer, vectorized, never pinned)

RUNTIME (per call, T3–T6):
  {{industry}} dv (free text; set in Discovery)
    └─ _ensure_pinned_industry (bg _live_retrieve task; ONCE per call; re-resolve on dv change)
        1 normalize -> 2 stoplist -> 3 alias map (plumbing/plumber->Plumbing; single-tag; ambiguous -> 4)
                     -> 4 embed fallback (top-1 >= 0.24, skip header) -> tag
        5 miss -> None -> today's vector lane (industry stays in scopes)
            └─ KBStore.pinned_by_tag(tag): SELECT id,kb,content
               WHERE kb='industry' AND vertical=$tag ORDER BY id   (NO embed, NO <=>)
               -> CallRuntime._pinned_industry = {tag, dv_value, chunks}   [per-call state]
                    └─ build_lanes(..., pinned_tag): scope -= 'industry'  (query text unchanged)
                         └─ merge_lane_chunks UNTOUCHED (3 dynamic slots, 1600 budget)
                              └─ delta = render_pinned_section(pin, cap 1800)
                                        + render_knowledge_section(merged)   [post-history]
  deep-dive scope trigger (independent of the pin): normalized dv contains 'plumb'
    -> lane-B scope += 'plumbing' KB (deep dive rides normal similarity, never pinned)
   kill switch / miss / missing column / DB down  -> byte-exact today
```

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/engine/agent/knowledge_bases/industry-kb.md` | + `## Plumbing` condensed vertical (3 sections, zero $ digits, from the niche draft) — the pinned layer's source | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/agent/knowledge_bases/plumbing-kb.md` | deep-dive manual (from `vps-inbox/plumbing-kb.md`, zero $ digits) — the scoped layer's source | New |
| `/home/julio/projects/clean_diallux_SDR/engine/scripts/kb_reembed.py` | corpus → `it8_plumbing.json`; `vertical` column DDL + heading parser + INSERT-with-vertical + **backfill UPDATE** (all existing industry rows, by id, idempotent) | Edit |
| `/home/julio/projects/diallux_kb_lab/corpi/it8_plumbing.json` | 193 existing rows verbatim + Plumbing vertical chunks + plumbing KB chunks (built with `chunk_v2`) | New |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/rag.py` | `KBStore.pinned_by_tag(tag)` + `KBStore.vertical_of(chunk_id)` + `render_pinned_section(chunks, tag)`; `retrieve`/`retrieve_lanes`/`merge_lane_chunks`/`render_knowledge_section` UNTOUCHED | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/graph/builder.py` | `CallRuntime._pinned_industry` (~:258, beside `_live_prev`) + reset in `initial_state` (:2028 block); `_ensure_pinned_industry` + `_resolve_industry_tag` helpers; `build_lanes` optional `pinned_tag` param (:869) + `plumb`→`plumbing` scope trigger; `_live_retrieve` compose + `rag:pin`/`pinned` tracer fields (:918) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/diallux/config.py` | `rag_pin_industry: bool = True`, `rag_pin_char_budget: int = 1800` (iter49 live block, ~:221) | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/scripts/lf_quick.py` | add `--db` (default = current DB constant), mirroring `live_sql.py` | Edit |
| `/home/julio/projects/clean_diallux_SDR/engine/tests/test_iter52_industry_pin.py` | new pins (list in T7) | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter52-industry-pin/` | surgeon docs (written) + live evidence + report `01_industry_pin.md` | exists (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter52_industry_pin.md` | this plan (v3) | docs → main |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | ledger line for iter52 (at close) | Edit (docs → main) |

## Deploy Rules
- Branch (base pinned `eccb6b0`; `21fe6b0` above it is docs-only — harmless):
  `git -C /home/julio/projects/clean_diallux_SDR worktree add /tmp/opencode/wt-iter52 -b engine/iter52-industry-pin eccb6b0`
- Env: `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter52/engine/.venv` ·
  `cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter52/engine/.env` ·
  `mkdir -p /tmp/opencode/wt-iter52/engine/tests/llm2llm/json_logs`
- Suite must run from the worktree's `engine/` dir (dry-run trap: `~/fastembed` shadows the package if cwd=`/home/julio`).
- **json_logs live ONLY in the MAIN checkout** — any dv-variant extraction runs from `/home/julio/projects/clean_diallux_SDR/engine`, never the worktree (the T1 mkdir creates an EMPTY dir there).
- NO merges of code branches without Julio's explicit say-so (LAW 0). Docs (md) go straight to main.
- `scripts/keyhound` before ANY push. NO push in normal flow.
- After ANY live/battery session: cancel ALL test bookings (Cal.com event `3801235` is REAL).
- NEVER touch live services `:8000`–`:8006`, owner port `:8007`, production agent IDs, deployed Retell LLMs, `kb_chunks` table, the ORIGINAL workspace. The `diallux_kb_lab` corpus is read-only; if it changes, re-run T2.

## Tasks (in order)

### T1 — Branch + worktree + green baseline
Goal: `engine/iter52-industry-pin` exists at base; suite green in the worktree.
Commands (full):
```bash
git -C /home/julio/projects/clean_diallux_SDR worktree add /tmp/opencode/wt-iter52 -b engine/iter52-industry-pin eccb6b0
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter52/engine/.venv
cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter52/engine/.env
mkdir -p /tmp/opencode/wt-iter52/engine/tests/llm2llm/json_logs
cd /tmp/opencode/wt-iter52/engine && .venv/bin/python -m pytest tests -o addopts="" -q
```
Verification: `git -C /tmp/opencode/wt-iter52 branch --show-current` = `engine/iter52-industry-pin`; suite = **305 passed**.

### T2 — Tag the corpus at ingest (corpus it8 + DDL + backfill)
Goal: 20/20 verticals tagged; 57/57 existing industry rows tagged (56 vertical + 1 `header`); Plumbing vertical + plumbing deep-dive KB ingested + vectorized; replay stays green.
Files: `engine/agent/knowledge_bases/industry-kb.md` (+`## Plumbing`), `engine/agent/knowledge_bases/plumbing-kb.md` (new), KB-Lab corpus `it8_plumbing.json` (new), `engine/scripts/kb_reembed.py` (worktree copy).
Behavior:
1. **Author the condensed `## Plumbing` vertical** into `industry-kb.md` (after `## HVAC & Home Services`-adjacent block order is irrelevant; standalone `##` section, NEVER nested): 3 subsections `### Business Owner Pain Points` / `### Voice AI Solutions` / `### ROI Metrics`, whole-vertical total ≤ 1800 chars, zero $ digits (sanctioned pricing pending — quantities only: 15–25 missed calls/week, 35–40% after-hours, ~40% spouse-as-office-manager, 60% office-manager bottleneck). Source: `vps-inbox/plumbing-niche.md` (merge notes at its bottom). Language rules from the draft apply: plain English, "catch calls / book jobs", no "optimize/leverage/scale".
2. **Author the deep-dive `plumbing-kb.md`** into `engine/agent/knowledge_bases/` from `vps-inbox/plumbing-kb.md` (already zero digits/$, Keep/usable/partial only, 1,283 tk): same header convention as the other KB files (`> Retrieved when: …` / `> KB name: plumbing-kb`).
3. **Build corpus `it8_plumbing.json`** with the KB-Lab v2 chunker (`diallux_kb_lab/scripts/corpus.py::chunk_v2`) over the two changed/new KB files + the 193 existing rows verbatim → expected ≈ 193 + 3 (Plumbing vertical) + ~14 (plumbing KB) rows. Industry content rows carry the standard heading `[industry | Industry-Specific Sales Knowledge Base > Plumbing > <Section>]` (parser tags them automatically).
4. **kb_reembed.py changes**: point CORPUS at `it8_plumbing.json`; after `CREATE TABLE IF NOT EXISTS`, run `ALTER TABLE kb_chunks_v2 ADD COLUMN IF NOT EXISTS vertical TEXT`; add the pure parser function (header regex + content regex from the Compaction Context); INSERT path writes vertical for industry rows; **after the pending-insert block, backfill: `SELECT id, content FROM kb_chunks_v2 WHERE kb='industry'`, parse each, `UPDATE kb_chunks_v2 SET vertical=$tag WHERE id=$rid` (unconditional — same-value re-runs are no-ops)**. Non-industry rows (incl. the plumbing KB) keep `vertical = NULL`. No new index.
Commands (full, from the worktree):
```bash
cd /tmp/opencode/wt-iter52/engine && set -a && . ./.env && set +a
.venv/bin/python scripts/kb_reembed.py              # ingest(it8 delta) + backfill + replay sanity
.venv/bin/python scripts/kb_reembed.py --replay-only  # idempotence proof: second run, same result
```
Verification (SQL via asyncpg — no psql CLI assumptions):
```bash
cd /tmp/opencode/wt-iter52/engine && set -a && . ./.env && set +a && .venv/bin/python -c "
import asyncio,os,asyncpg
async def m():
    c=await asyncpg.connect(os.environ['DATABASE_URL'])
    print('industry rows', await c.fetchval(\"select count(*) from kb_chunks_v2 where kb='industry'\"))
    print('tagged', await c.fetchval(\"select count(*) from kb_chunks_v2 where kb='industry' and vertical is not null\"))
    print('header', await c.fetchval(\"select count(*) from kb_chunks_v2 where vertical='header'\"))
    rows = await c.fetch(\"select vertical, count(*) n, sum(length(content)) chars from kb_chunks_v2 where kb='industry' and vertical<>'header' group by vertical order by 1\")
    assert len(rows)==20 and all(r['chars']<=1800 for r in rows), rows
    for r in rows: print('  ',r['vertical'], r['n'], r['chars'])
    print('plumbing kb rows', await c.fetchval(\"select count(*) from kb_chunks_v2 where kb='plumbing'\"))
    await c.close()
asyncio.run(m())"
```
Expected: industry 60 (57 existing + 3 Plumbing); tagged 60; header 1; 20 verticals; every vertical total ≤ 1800 chars (measured max 1709; the authored Plumbing vertical is authored to fit); plumbing KB rows ≈ 14 (whole deep-dive, vectorized, `vertical = NULL`). Replay sanity: hard asserts PASS (unchanged).

### T3 — Resolver (alias map + embed fallback)
Goal: `{{industry}}` free text → canonical tag, never guessing, never blocking.
Files: `engine/diallux/graph/builder.py` (helpers; called from T5's `_ensure_pinned_industry`).
Design: the 5-step ladder in Resolved Decisions. Alias draft (seeded from the 60 real variants; each alias → exactly ONE tag; word-boundary substring, longest-first; NO bare "contractor"):
dental/dentist→Dental Practices · law firm/personal injury/attorney→Law Firms (Personal Injury, Family, Immigration) · auto repair/auto body/mechanic→Auto Repair & Body Shops · landscap/lawn/tree service→Landscaping, Maintenance & Tree Services · remodel/renovation/general contractor→Home Remodeling & Small General Contractors · roofing→Residential Roofing & Solar Installers · hvac/heating/air conditioning→HVAC & Home Services · med spa/medical spa/aesthetic→Medical Spas & Aesthetic Clinics · vet/veterinary→Veterinary Clinics (General Practice, Small Animal) · moving→Local & Regional Moving Companies · maid/house cleaning/cleaning service→Residential Home Cleaning & Maid Services · property management→Residential Property Management · pest→Pest Control (Residential & Commercial) · garage door/locksmith→Garage Door & Locksmith Services · appliance repair/handyman→Appliance Repair & Handyman Services · security system/smart home/alarm→Residential/Commercial Security & Smart Home · msp/it services/it support/managed service→IT Managed Service Providers (MSPs) · urgent care/physical therapy/chiropract→Private Clinics (Urgent Care, Physical Therapy, Chiropractic) · dermatology/ophthalmology→Specialty Clinics (Dermatology & Ophthalmology) · **plumbing/plumber→Plumbing**.
Stoplist: "", unknown, n/a, none, not sure, unsure, tbd, various, multiple, header. Values with NO vertical (hardware store, real estate, restaurant, tour operator, tech consultancy, …) take the embed fallback (nearest vertical, top-1 ≥ 0.24) or miss → vector lane — never worse than today.
Re-extract variants (fixed command — recursive walk; run from the MAIN checkout, NOT the worktree):
```bash
cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python -c "
import json,glob,collections
def walk(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='industry' and isinstance(v,str) and v.strip(): yield v.strip()
            else: yield from walk(v)
    elif isinstance(o,list):
        for x in o: yield from walk(x)
vals=collections.Counter()
for p in glob.glob('tests/llm2llm/json_logs/*.json'): vals.update(walk(json.loads(open(p).read())))
print(vals.most_common(60))"
```
Verification: T7 tests 4–5 (alias hits incl. noisy forms; ambiguity → fallback; stoplist → None; embed top-1 < filter → None; header top-1 → None; every alias target ∈ live `SELECT DISTINCT vertical`).

### T4 — `KBStore.pinned_by_tag` + `vertical_of` + `render_pinned_section`
Goal: metadata fetch with ZERO embed calls; render helper.
Files: `engine/diallux/rag.py`.
Design: exact SQL in Resolved Decisions; chunk dicts `{id, kb, content, score: None, vertical: tag}`; try/except → `[]` on ANY failure (missing column included); `render_pinned_section` emits `\n\n## INDUSTRY CONTEXT ({tag} — pinned for this call)` + `### from industry-kb` blocks, whole-chunk cap `rag_pin_char_budget`. **`retrieve`, `retrieve_lanes`, `merge_lane_chunks`, `render_knowledge_section` byte-unchanged.**
Verification: T7 tests 2–3 (SQL shape has `vertical = $` and no `<=>`; `embed_fn` never invoked; failure → `[]`).

### T5 — Pin state + lane integration + delta injection + deep-dive scope trigger
Goal: fetch ONCE per call; industry never re-embedded; 3 dynamic slots freed; prefix untouched.
Files: `engine/diallux/graph/builder.py`.
Behavior: `_pinned_industry` state + `initial_state` reset; `_ensure_pinned_industry(dvs, store)` (kill-switch gate, dv-value cache, invalidate on change, called ONLY from `_live_retrieve`); `build_lanes(..., pinned_tag=None)` scope filter; `_live_retrieve` composes `render_pinned_section(pin) + "\n\n" + render_knowledge_section(merged)` (pin first), adds `industry` to reported `kbs`, logs `rag:pin` span per resolve + `pinned` field on live rag spans; **`plumb`→`plumbing` deep-dive scope trigger** (normalized dv contains `plumb` → lane-B scope += `plumbing`, independent of the pin, never a per-call state, gated by the same `rag_pin_industry` kill switch so False = byte-exact today).
Verification: T7 tests 6–9 (scope minus industry + query text unchanged; pin-once; dv-change re-resolve; initial_state reset; delta composition; kill switch = today; prefix bytes stable pin on/off).

### T6 — Config knobs
Goal: `rag_pin_industry=True`, `rag_pin_char_budget=1800` in `config.py` (iter49 live block); env-able `RAG_PIN_INDUSTRY` / `RAG_PIN_CHAR_BUDGET`.
Verification: T7 test 8 kill-switch path; suite green in both modes.

### T7 — Tests, tooling, offline gates, full suite
Files: `engine/tests/test_iter52_industry_pin.py` (new; hermetic fake-pool pattern from test_iter49 `_FakeConn`/`_FakePool`), `engine/scripts/lf_quick.py` (`--db`).
Test list (one pin per line): (1) parser 3-sections+header+non-industry (incl. a Plumbing row); (2) pinned_by_tag SQL shape + zero embeds + ORDER BY id; (3) pinned_by_tag failure → `[]`; (4) resolver ladder incl. noisy/ambiguous/stoplist/header cases; (5) alias integrity vs live DB (skipif no DB); (6) build_lanes pinned scope + None-parity + plumb→plumbing scope trigger; (7) pin-once / dv-change / per-call reset; (8) delta composition (pin FIRST) + kill switch + whole-chunk budget + **eviction-resistance: the pin block is present when `merged == []` AND when the dynamic budget is fully consumed — and `_build_messages` still appends the delta with a 40-entry history (well past the 16/8 window)**; (9) prefix byte-stability with pin on/off (iter49 L424 pattern).
Commands (full):
```bash
cd /tmp/opencode/wt-iter52/engine && .venv/bin/python -m pytest tests -o addopts="" -q
.venv/bin/python tests/llm2llm/harness.py --offline
.venv/bin/python -m pytest tests/test_iter49_rag_parity.py -o addopts="" -q
RAG_PIN_INDUSTRY=false .venv/bin/python -m pytest tests -o addopts="" -q   # kill-switch mode green too
```
Verification: full suite green (305 + new; record the exact new count); smoke 7/7 PASS; iter49 parity file green in BOTH modes.

### T8 — Live verification + report + ASK
Goal: prove on live calls: industry fetched once, recall improves, cache floors intact.
Commands (full):
```bash
cd /tmp/opencode/wt-iter52/engine && set -a && . ./.env && set +a
.venv/bin/python tests/llm2llm/harness.py --personas happy --rag --langfuse --max-turns 48 --warm-greeting-ms 3000
.venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run battery-iter52 \
  --commit <branch-head-sha> --branch engine/iter52-industry-pin \
  --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db
.venv/bin/python scripts/lf_quick.py bugs --run battery-iter52 \
  --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db
```
Verification (named SQL/Langfuse, not vibes): for `battery-iter52` — exactly ONE `rag:pin` span per call (re-resolves only on dv change); zero industry-lane embeds after the pin round (no industry in lane spans' kbs except via `pinned`); `pain-points` hit-count increases vs `happy-chat-c` (baseline 1/37); transition-entry TTFT <1000ms (warm 3000); cache floors 2688/3712 intact; `lf_quick.py bugs` #1/#3 covered. Then: cancel ALL Cal.com test bookings; write `research/surgeon/iter52-industry-pin/01_industry_pin.md`; ASK Julio (merge? plus carried ASKs: dummy-tool/real-tools, root `scripts/call_ledger.py`). On say-so: `git merge --no-ff` → tag → `scripts/git-tree.sh` → ITERATIONS.md line.

## Validation Plan (end-to-end)
1. T1: branch at `eccb6b0`; suite 305 in the worktree.
2. T2: 57/57 existing industry rows tagged (56 vertical + 1 header); 20 verticals (incl. the authored Plumbing vertical ≤ 1800 chars); plumbing deep-dive KB ingested + vectorized (~14 rows); replay hard asserts PASS; second run idempotent.
3. T3: aliases resolve to live-read tags (incl. plumbing/plumber→Plumbing); ambiguous → fallback; stoplist/miss → None → vector lane.
4. T4: pinned lookup = all of a vertical's chunks, zero embeds, failure → `[]`.
5. T5/T6: second heavy round does no industry embed; industry out of scopes; pin block in post-history delta only; prefix bytes stable; dv change re-resolves; initial_state resets; kill switch = today; `plumb` dv adds the plumbing deep-dive KB to lane-B scope.
6. T7: full suite green in BOTH modes; smoke 7/7; iter49 parity green.
7. T8: one `rag:pin` per call; pain-points recall up; TTFT <1000ms; floors intact; report written; ASK made; bookings cancelled.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Sanctioned $ figures for the Plumbing ROI Metrics (owner pricing pending) | the vertical ships with quantity-only ROI (missed-call counts, after-hours %); re-author with $ when the numbers land |
| Pinning other per-call-constant KBs (`call-closing`, `call-context`) | same pattern; evaluate after industry proves |
| Changing `rag_filter_score` (KB-Lab suggests ~0.138 for arctic gold) | separate calibration iteration; the pin bypasses the filter for pinned chunks only |
| Other gap industries (hardware store, real estate, restaurant, tour operator, tech consultancy) | no defensible vertical yet; the embed fallback bridges; corpus work in `diallux_kb_lab` |
| `discovery-bridge` / price-push lane recall; the 2 zero-chunk Discovery retrievals | not exercised by happy personas; stress/curve battery or KB-Lab lane work |
| Reranker (top20→top3) from KB-Lab iter51 | separate cutover plan |
| dummy-tool vs real-tools ack; root `scripts/call_ledger.py` | owner ASKs; unrelated to the pin |
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` |
