# PLAN — v5 iter49b: RAG cutover + lanes (finish iter49) + ledger registry repair

## Meta
- Date: 2026-09-15
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Parent plan (read it first — Resolved Decisions / Architecture / T4 / T4b below are copied from it verbatim): `plans/plan_v5_iter49_rag_retrieval_parity.md`
- Scope: finish iter49's ENGINE work on the SAME branch — T3 (KB re-embed cutover), T4 (lanes), T4b (lite entry + warm realign), offline cache pins, report — then repair the branch/iteration SQLite registry (iter47 generator, stale since Sep 12). Live battery (marker A/B live, happy-4, battery-13) is EXCLUDED (owner directive 2026-09-15) — separate session.
- Status: READY TO EXECUTE by a fresh session. Code work is mid-flight: T0+T2 already done and committed.
- Branch: `engine/iter49-rag-parity` @ **`266237b`** (base `c40f06b` = iter48 pinned `033f742` + 2 docs/ops commits). Worktree: `/tmp/opencode/wt-iter49`. ALL code edits happen there. NO merge without owner (LAW 0).
- Companion plans: `plans/plan_v5_iter50_us_region_migration.md` (runs AFTER iter49 proves, owner-gated).

## Compaction Context (what the 2026-09-15 wiring session did — pin, do not re-derive)

**Done and committed (`266237b`, suite 277 green = 270 baseline + 7 new):**
- Worktree `/tmp/opencode/wt-iter49` created; branch cut from `c40f06b` (branch tip = `033f742` + ledger-ops commits `06656e7`, `c40f06b` — plan-acceptable "or later iter49 commit").
- **T2 wired** (`diallux/rag.py`, `diallux/config.py`, `tests/test_iter49_local_embed.py`):
  - `EMBEDDING_DIMS["snowflake/snowflake-arctic-embed-m"] = 768`; `LOCAL_EMBED_MODELS = {"snowflake/snowflake-arctic-embed-m"}`; `ARCTIC_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "`.
  - `local_embed_fn(model, cache_dir, threads=4, prefix)` — in-process fastembed, every call parked via `asyncio.to_thread` (async-off-hot-path directive), session warmed once at build.
  - `KBStore._ensure_embed_fn()` routes by `rag_embedding_model`: arctic → local, anything else → `openai_embed_fn` (iter48 exact). Used by `retrieve()`, `embed_query()`, `ingest()`.
  - `KBStore.ingest()` REFUSES local models (doc re-embed = T3's `kb_reembed.py`; documents take no prefix).
  - Config knobs: `local_embed_cache_dir="/home/julio/fastembed/models"`, `local_embed_threads=4`. Default `rag_embedding_model` STILL `text-embedding-3-small` → current live behavior unchanged.
- **Measured (smoke, offline):** model load ~833ms; single query ~20ms; 2-query batch ~33ms (threads=4); pgvector scoped SELECT p50 1.6–1.7ms warm (17ms first call) — the +60ms hot-path guard holds.

**TRAPS paid for this session (violating these = repeat mistakes):**
1. `engine/.venv` is a COPY-mirror venv: its `bin/pip` shebang points at the ORIGINAL live workspace venv (`Retell_AI_MCP_connection/Dialux_SDR/dialux-langgraph-production-v5/.venv`). A naive `pip install` CONTAMINATED the original live venv (13 packages — since fully uninstalled, `pip check` clean). **ALWAYS install with `<venv>/bin/python -m pip …`, never the pip script.**
2. Worktrees share the venv via symlink: `wt-iter49/.venv → /home/julio/projects/clean_diallux_SDR/engine/.venv`. fastembed 0.8.0 + deps (onnxruntime etc.) are installed THERE — visible to every worktree.
3. NEVER run python with cwd=/home/julio: the lab venv dir `/home/julio/fastembed/` shadows the `fastembed` package as a namespace dir. Run from the worktree.
4. Model id has the org slash: `snowflake/snowflake-arctic-embed-m` (bare `snowflake-arctic-embed-m` raises ValueError in fastembed 0.8.0).

**Vector store facts (measured):**
- `kb_chunks`: 233 rows, `embedding vector(1536)` (OpenAI prod space) — UNTOUCHED.
- `kb_chunks_emb_staging_m`: 233 rows, 768-d arctic — **columns are (id, embedding) ONLY** → any KB/content lookup must `JOIN kb_chunks c ON c.id = s.id`. Built by the lab from the PROD corpus (has the 46 header-only shells).
- Target corpus for T3: `/home/julio/projects/diallux_kb_lab/corpi/it7_faq.json` — a LIST of 193 dicts `{"kb": slug, "content": …}` (v2 chunker + faq). **Content differs from kb_chunks' 233 rows → T3 is a re-INGEST (new rows), not a per-row vector update.**
- pgvector DSN = Settings `database_url` (`localhost:5434/diallux`); asyncpg is in the venv.
- Smoke vs staging_m @0.24: Closing anchor "warm goodbye wrap-up next steps" → call-closing 0.362/0.288 (engine today: 0 chunks); "how does it work" → REFUSED 0.24 on prod corpus (edge E1/E2 family, expected); mirror query → industry pain chunks. Full config-C parity was proven by the pre-flight (`research/surgeon/iter49p-sharp-rag/02_replay_report.md`) on the 193 corpus — the smoke proves the WIRING only.

**The registry debt (final task of this plan):**
- `plans/plan_iter47_call_ledger.md` is the SPEC; generator `scripts/call_ledger.py` (567 lines) lives ONLY on branch `engine/iter47-call-ledger` (commits `5e7cd1f`, `fd997e5`) — NOT merged, NOT in main's scripts/.
- Registry DB `research/surgeon/iter47-call-ledger/ledger.db`: branches(90)/commits(944)/runs/calls, built 2026-09-12 — **stale: zero rows for `engine/iter48-rag-truth` or `engine/iter49-rag-parity`**. It is ALSO a separate DB from the active call ledger (`research/surgeon/iter48-rag-truth/ledger.db` = runs/calls/rounds/rag/findings/sessions/sops).
- iter47 T2 `tree.md` (owner visual) was never produced. `AGENTS.md` §Eval SOP (line 84) documents only the iter48 ledger — no mention of the registry or the generator. Ledger DBs are gitignored evidence (untracked) — the git history itself is safe; the DB view of it is what rots.

## Resolved Decisions (DO NOT revisit — verbatim from the parent plan)
| Decision | Rationale |
|---|---|
| iter49 = RAG retrieval redesign (executes FIRST); iter50 = region migration (after iter49 proves) | one variable per iteration; local embedder works on either host |
| **Mimic Retell first, then improve** | parity acceptance test = same KBs visible, filter 0.6, top_k 3, fresh per turn |
| **Fresh retrieval every turn** as the default (drop freeze as default) | owner 2026-09-12: reply must carry the right KB THAT turn; freeze caused stale tails |
| **Local embedder** replaces OpenAI embeddings for the query path | ~15-25ms vs 184ms → several queries/turn affordable |
| Explore **2-lane query**: engine intent (refer-tag what) + user intent (caller text) as SEPARATE retrievals merged | owner: "we can do both… query six knowledge bases" at negligible latency |
| Keep `first_turn_lite` + `LITE_NOOP_TOOL` (as landed) | proven by battery-iter48; do NOT regress turn-1 cache |
| `filter_score` 0.40 → **0.60** (Retell's value) at minimum | stop noise chunks (industry) crowding top-3 |
| Keep `top_k = 3` per KB, but allow per-tag/per-KB slots (quota) | owner: "three is enough" per query, but no big KB may monopolize |
| **Lane budget: ≤3 engine lanes + ≤3 caller lanes per turn, ONE batched embed call + parallel pgvector** | owner 2026-09-13; N sequential embeds cannot meet the ≤+60ms hot-path guard |
| **Fresh chunks render in the POST-HISTORY delta slot, REPLACED each turn; the pre-history prefix ([tools][head][state-block][history]) is NEVER rewritten** | owner 2026-09-13 audit: prompt cache = prefix PLACEMENT, not byte-compare; reuse iter44's delta lane (`_build_messages` delta arg, builder.py:529-530) |
| **Dedupe by chunk id (DB PK), against the CURRENT window** (tail + untrimmed history + delta), not a lifetime set and not content bytes | sliding chunk windows (…101,102,103… → …102,103,104…) break byte dedupe; history trims 16/8 so old chunks may legitimately return |
| **Closing gets a hand-written anchor query** (e.g. "warm goodbye wrap-up next steps"), scoped [call-closing, sales-language] | Closing.md has ZERO refer tags → lane A empty; raw "ok thanks bye" at 0.60 likely still retrieves 0 chunks |
| **filter threshold re-calibrated for the chosen embedder** (Retell's 0.60 recorded as reference, NOT auto-copied) | arctic-m measured **0.24** (proper-10 10/10, real-50 junk 15→1); OpenAI cosine is anti-correlated on this corpus (MiniLM rejected) |
| **`rag_prefetch_on_transition` + drift lane INERT under `rag_live_retrieve=True`** (single flag owns the mode; False = iter48 behavior exactly) | stale-text prefetch is part of the diagnosis; dead work under live-retrieve |
| Turn-1 lite: **keep `LITE_NOOP_TOOL`**; optional ≤2 lane-B retrieves rendered post-history ONLY if turn-1 p50 TTFT budget holds | FIND-5: gpt-5.4 only prompt-caches tool-bearing requests |
| **Per-state LITE ENTRY (ALL states incl. Booking + contact_details): first round in a new state = [state head][state-block dvs][history] (~1200 tok) — NO tools, NO RAG, NO await** | owner 2026-09-13 MUST-HAVE: state changes invisible to the user; ack TTFT ~800ms |
| **Lite entry carries ZERO RAG (owner-picked: context over chunks)** | frozen chunks on entry recreate the freeze/dedup complexity this plan deletes |
| **Heavy warm KEEPS its role, REALIGNED: fires at transition detection + post-execute (unchanged triggers); warms the RAG-FREE prefix [tools][head][state-block][history]; `_await_warm` (500ms EOT / 100ms mid-turn) guards HEAVY rounds ONLY — lite rounds never await** | staged-RAG tail would break `prewarm_byte_exact` at every transition; awaiting 500ms before a light call is pure loss |
| **Worst-case budget: ack round ~800ms TTFT; first heavy round ≤1300ms TTFT** | owner: <1000ms is a must-have; battery gates enforce at transitions |
| **Lite entry has NO tools → the ack round can only SPEAK**; per-state opt-out list (`state_entry_lite_off`) | acks are speech by design; states needing immediate tool calls opt out |
| Echo-dup (PT-48) and name-loop (PT-43) NOT in this plan | separate plans |
| Code lands on `engine/iter49-rag-parity`; LAW 0, no merge without owner | git crystal ball v2 |
| **T3 = new-corpus re-ingest, additive table** (`kb_chunks_v2` with its own content+768-d embedding), `kb_chunks` stays one release | iter49b session: the 193 v2+faq corpus has DIFFERENT content than kb_chunks' 233 rows — a per-row `embedding_new` UPDATE cannot work; additive table is zero-downtime and revertible |
| **Live battery excluded from THIS session** (marker A/B live, happy-4, battery-13) | owner directive 2026-09-15: wire + prove offline now; live proof is the next session |
| Registry repair (iter47 generator) = final task, ops-level | owner 2026-09-15: "we have so much mess we need that control" |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| None blocking T3/T4/T4b. | — |
| Owner go for the LIVE battery session (T5/T6 of the parent plan) | ASK at T7 (report + ASK step) |
| Merge consent for `engine/iter47-call-ledger` (to get `scripts/call_ledger.py` into main) | ASK at T8 — until then the generator is recovered from the branch via `git show` |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter49/.venv/bin/python` (3.12.3; symlink → `engine/.venv`). Suite at `266237b`: **277 passed** (270 + 7 in `tests/test_iter49_local_embed.py`).
- **Pip rule: `<venv>/bin/python -m pip …` ONLY** (shebang trap — see Compaction Context #1).
- fastembed 0.8.0 + onnxruntime installed in the shared engine venv; model cache `/home/julio/fastembed/models` (`models--Snowflake--snowflake-arctic-embed-m` present; no download needed).
- Embedder pack (pinned, from `research/surgeon/iter49p-sharp-rag/02_replay_report.md`): arctic-m 768-d, threads ≥4, query prefix "Represent this sentence for searching relevant passages: ", threshold **0.24**, ASYNC off hot path; corpus = `diallux_kb_lab/corpi/it7_faq.json` (193, list of `{"kb","content"}`); lanes per refer-tag + caller-text lane B (industry-dv anchor, $-formatted leak values), ≤3/side, ONE batched embed, parallel pgvector; quota ≤1 chunk/KB unless lane-owned, top_k 3, 1600-char budget; fresh-per-turn post-history delta; Closing anchor "warm goodbye wrap-up next steps" [call-closing, sales-language] (swap to "recap booking SMS confirmation next steps" after a successful booking — edge E3).
- Postgres: `localhost:5434/diallux` (DSN from `.env`). Tables: `kb_chunks` (233, 1536-d), `kb_chunks_emb_staging_m` (233, 768-d, id+embedding only).
- Key files (line pins against `033f742`): `diallux/graph/builder.py` (`kb_slugs_for` ~691-710; `_warm` staged tail ~318-331; `_build_messages` delta arg ~529-530; await split ~885-897; transition detection ~1242; post-execute force ~1357), `diallux/rag.py` (post-T2: `_ensure_embed_fn`, `local_embed_fn`), `diallux/config.py` (rag knobs ~183-200).
- Registry artifacts: `plans/plan_iter47_call_ledger.md` (spec), `git show engine/iter47-call-ledger:scripts/call_ledger.py` (generator), `research/surgeon/iter47-call-ledger/ledger.db` (stale registry), `engine/ITERATIONS.md` (narratives), `research/surgeon/iter48-rag-truth/ledger.db` (active call ledger).
- Ports: :8007 owner live-test — never start/stop. :8000-:8006 live services — never touch. ORIGINAL workspace — never modify (pip trap above is how).

## Architecture (verbatim from the parent plan)
```
TODAY (iter48 engine, per round):
  state entry → retrieve ONCE (refer-whats + dv + caller text, filter .40, top3 over 9-10 KBs)
              → FREEZE chunks for the state visit
              → every later round: frozen tail + bg drift re-embed (~180ms) → deltas DEDUPED AWAY
  ⇒ tag-KB missing, Closing 0 chunks, stale tail, latency burned for nothing

ITER49 TARGET (Retell parity, then better):
  every turn, BEFORE the LLM call:
    lane A (engine intent):  one retrieve PER refer-tag  → its OWN kb scope + top_k
    lane B (user intent):    one retrieve on the caller utterance (≤3 lanes a side)
    ONE batched embed (all lane query texts in ONE call) + parallel pgvector
    merge + dedupe BY CHUNK ID against the CURRENT window + per-KB quota
    → fresh working set rendered in the POST-HISTORY delta slot (REPLACED each
      turn; pre-history prefix [tools][head][state-block][history] NEVER
      rewritten — cache = placement, not byte-compare)
    local embedder (~15-25ms/query) · filter re-calibrated · no freeze (flag revert available)
  ⇒ every response carries exactly the KB the prompt asked for + what the caller asked

  STATE-ENTRY (transition landing) — TWO-SHAPE design (owner 2026-09-13, MUST-HAVE <1000ms):
    warm bg (fires at transition_to_X DETECTED in stream + post-execute):
        HEAVY prefill of [tools][head][state-block][history] — 2-3s cold,
        runs during tool exec + ack speech + user speech (real call, may be silent)
    round 1 in new state (the ACK):  [state head][state-block dvs][history]
        ← LITE ~1200 tok · NO tools · NO RAG · NO await → ~800ms TTFT
    round 2+ (HEAVY): [tools][head][state-block][history][fresh RAG delta]
        ← warm-cached prefix · ≤500ms EOT await insurance → ≤1300ms TTFT worst case
    lite shape and heavy shape are INDEPENDENT requests (diverge at byte 0,
    tools render first) — the lite ack neither helps nor hurts the heavy warm
  ⇒ the user never feels the state change; KB facts arrive on the heavy round
```
T2 delta already landed: the embedder behind "ONE batched embed" is `local_embed_fn` (arctic-m, to_thread-parked) selected by `KBStore._ensure_embed_fn`.

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/scripts/kb_reembed.py` (NEW) | one-time re-ingest: read `corpi/it7_faq.json` (193) → embed content with arctic-m (NO query prefix, batch ≤256) → build `kb_chunks_v2(kb, content, embedding vector(768))` + HNSW + replay sanity vs the 7 pre-flight queries | New |
| `/tmp/opencode/wt-iter49/diallux/config.py` | + `rag_table_name: str = "kb_chunks"` (T3 cutover switch); + `rag_filter_score` flip to 0.24 ONLY at cutover (arctic); + `rag_live_retrieve: bool = True`, `rag_multiquery: bool = True`, `rag_keep_markers: bool = False`, `state_entry_lite: bool = True`, `state_entry_lite_off: str = ""` | Edit |
| `/tmp/opencode/wt-iter49/diallux/rag.py` | KBStore honors `rag_table_name` in SELECT/ingest-guard; `retrieve()` returns chunk id (PK) for dedupe; batched multi-query embed helper | Edit |
| `/tmp/opencode/wt-iter49/diallux/graph/builder.py` | T4 lanes + T4b lite entry + warm realignment (spec verbatim in Tasks below) | Edit |
| `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py` (NEW) | pins for lanes/quota/dedupe/fresh-delta/Closing-anchor/lite-entry/warm-bytes/await-gating/revert-flags | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (NEW) | offline evidence: replay sanity table, suite, cache-floor pins, what remains (live battery) | New |
| `/home/julio/projects/clean_diallux_SDR/AGENTS.md` | §Eval SOP: document BOTH ledgers (iter48 call ledger AND iter47 branch/commit registry) + `call_ledger.py` provenance + the pip trap | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` | REFRESHED registry (re-run generator; iter48/iter49 rows present) | Edit (evidence, gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/tree.md` (NEW) | iter47 T2 owner visual — ALL iterations → branches → commits → runs | New (evidence) |

## Deploy Rules (parent plan verbatim + iter49b additions)
- Commits ONLY on `engine/iter49-rag-parity` (worktree `/tmp/opencode/wt-iter49`). NO merge/push without owner (LAW 0). Docs (plans/AGENTS.md/PENDING_TASKS/ITERATIONS) straight to main.
- NEVER start/stop :8007 (owner), live services :8000-:8006, or the original workspace.
- **Pip: `<venv>/bin/python -m pip` only** — `bin/pip` shebangs point at the ORIGINAL live venv (contamination incident 2026-09-15, reverted).
- Never modify an existing Retell LLM — read the snapshot only. Before any push: `scripts/keyhound`. After any owner live/battery session: cancel ALL test bookings (Cal.com event 3801235 REAL).
- The embedder is in-process (no service, no port). The 193-corpus ingest writes ONLY `kb_chunks_v2` — `kb_chunks` is never truncated/altered in this plan.

## Tasks (in order)

### T3 — KB re-embed migration (new-corpus re-ingest, additive)
Goal: a 768-d arctic KB store with the 193 v2+faq corpus, selectable by flag; `kb_chunks` untouched.
Files: `/home/julio/projects/clean_diallux_SDR/scripts/kb_reembed.py` (new), `diallux/rag.py` (table-name plumbing), `diallux/config.py` (`rag_table_name`).
Procedure:
1. Read `/home/julio/projects/diallux_kb_lab/corpi/it7_faq.json` (list of 193 `{"kb","content"}`).
2. `CREATE TABLE IF NOT EXISTS kb_chunks_v2 (id BIGSERIAL PRIMARY KEY, kb TEXT NOT NULL, content TEXT NOT NULL, embedding vector(768) NOT NULL, created_at TIMESTAMPTZ DEFAULT now());` + `kb` btree index.
3. Embed content with `local_embed_fn`-equivalent **without the query prefix** (documents!): batch ≤256 via fastembed directly in the script (`TextEmbedding("snowflake/snowflake-arctic-embed-m", cache_dir="/home/julio/fastembed/models", threads=4)`), idempotent: skip rows already present (match on kb + sha256(content)).
4. `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` on `kb_chunks_v2`.
5. Sanity (write into the script or a companion replay): run the 7 replay queries from `research/surgeon/iter48-rag-truth/10_latency_findings.md` + the parent plan's asserts — mirror query surfaces pain-points/vertical pain in top-3; Discovery deferral surfaces sales-language; Closing anchor surfaces call-closing. Print a table (this becomes part of `11_rag_redesign_report.md`).
6. Plumbing: `KBStore` reads `rag_table_name` (default `kb_chunks`) for SELECT + count/indexed checks; do NOT flip any flag yet.
Verification: `select count(*) from kb_chunks_v2` = 193; `kb_chunks` still 233/1536-d; sanity table shows the designed KB in top-3 for mirror + deferral + closing; suite still 277 green. Commit.

### T4 — Retrieval redesign in the engine (verbatim from the parent plan)
Goal: per-turn fresh multi-lane retrieval with a KB quota.
Files: `diallux/graph/builder.py`, `diallux/config.py`, `tests/test_iter49_rag_parity.py`.
- `kb_slugs_for`: real per-state attachment (`_STATE_KBS` map: Intake=[pain-points, call-context, sales-language, voice-ai-capabilities, are-you-ai, sales-psychology, industry, hipaa, call-closing]…; Discovery += discovery-bridge; Closer=[sales-psychology, industry, sales-language, call-context, pain-points]; Offer=[sales-psychology, sales-language, industry, voice-ai-capabilities]; Closing=[call-closing, sales-language]; OFF unchanged). Pin the exact map in the commit.
- `rag_multiquery`: for each refer-tag → `retrieve(tag.what + dv values, scope=tag.kb)`, plus lane B `retrieve(caller_text, scope=state scope)`; ≤3 lanes per side; merge by score, cap 1 chunk per KB unless it's the tag's own KB, top_k=3 total. Lane B appends `(their industry: {industry dv})` when extracted; leak dv values $-formatted with units.
- Batch + parallelize: ONE embed call carrying ALL lane query texts (via `local_embed_fn` — already batched); pgvector queries issued concurrently (asyncpg pool); no sequential per-lane embeds.
- Chunk identity: `retrieve()` SELECT adds the chunk PK; returned dicts carry `id`; dedupe keys on `id` against the CURRENT window (frozen tail + untrimmed history + last delta) — never content bytes.
- `rag_live_retrieve=True`: retrieval runs fresh every NON-lite round; the fresh working set REPLACES the post-history delta block each turn (`_build_messages` delta arg, builder.py:529-530); the pre-history prefix is NEVER rewritten. Drift lane + `rag_prefetch_on_transition` inert under this flag (revert = False restores iter48 exactly) — SAFE only because T4b realigns `_warm` to the RAG-free prefix.
- Closing anchor: hand-written "warm goodbye wrap-up next steps" scoped [call-closing, sales-language]; parity test asserts >0 call-closing chunks. (E3: after `create_livecall_booking` success, swap anchor to "recap booking SMS confirmation next steps".)
- `filter_score`: use 0.24 (arctic) — active only at the T3 cutover flip; `rag_min_query_chars` stays.
- Lite turn-1 UNCHANGED: lite head + `LITE_NOOP_TOOL` stay.
Verification: `tests/test_iter49_rag_parity.py` green; an OFFLINE replay script (no live calls — reuse the pre-flight's gold-chat turn texts from `diallux_kb_lab` results.db, run_id `replay`) asserting per-turn tag-KB presence; output pasted into `11_rag_redesign_report.md`. Commit.

### T4b — State-transition LITE ENTRY + heavy-warm realignment (verbatim from the parent plan)
Goal: the user never feels a state change. Ack round is light and instant; the heavy payload warms in the background.
Files: `diallux/graph/builder.py`, `diallux/config.py`, `tests/test_iter49_rag_parity.py`.
- **Lite entry path** (flag `state_entry_lite=True`): trigger = first round in a state whose name ≠ the previous round's state (covers post-`transition_to_X` ack rounds AND turn-2 entry into the initial state; turn-1 keeps the EXISTING first_turn_lite path untouched). Shape: `[state head (kb=False)][state-block dvs][history window]` — ~1200-tok budget. NO tools, NO RAG lanes, NO `_await_warm`. Per-state opt-out via `state_entry_lite_off` (comma list).
- **ALL states get it**, including Booking + contact_details (they stay `_RETRIEVAL_OFF` for RAG).
- **`_warm` realignment:** drop the staged-RAG tail from `_warm` (builder.py:318-331); the warm now prefills EXACTLY `[tools][head][state-block][history]` — byte-equal to the heavy round's pre-history prefix. `prewarm_byte_exact` stays True but now pins the RAG-free prefix. Warm triggers UNCHANGED (builder.py:1242 + builder.py:1357).
- **`_await_warm` gating:** lite rounds NEVER await; heavy rounds keep the EOT split (500ms EOT / 100ms mid-turn, builder.py:885-897).
- Commands: suite + a transition-focused OFFLINE replay (force transitions Intake→Discovery→Offer→Closer→contact_details→VerifyLead→Booking via the test fake; log per-round shapes + byte budgets).
Verification: lite-entry shape pins green (no tools/no RAG/no await/byte budget); `_warm` bytes == heavy-round pre-history bytes; per-state opt-out honored; no suite regression. (TTFT gates 800/1300ms are LIVE measurements — recorded as the next session's gates, not this one's.) Commit.

### T5-offline — cache-floor pins (offline part of parent T5)
Goal: prove placement correctness without live calls.
- Suite pin: with `rag_live_retrieve=True`, the `[tools][head][state-block][history]` prefix bytes are byte-IDENTICAL across turns with DIFFERENT fresh chunk sets (the delta renders post-history), and with `rag_keep_markers=true|false` the prefix is unchanged except the marker text itself.
- Ledger cache_read floors (2688/3712 turn-2+; T4b transition floors) are LIVE checks — listed in `11_rag_redesign_report.md` as next-session gates.
Verification: new pins green in `test_iter49_rag_parity.py`. Commit.

### T6 — Report + ledger sync (parent T7, offline scope)
Files: `research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (replay-sanity table from T3, offline replay from T4, pins from T4b/T5-offline, the deferred live-gate list), PENDING_TASKS PT-49 status, ledger sync to main repo copy.
Verification: report written; ledger synced; then ASK owner: (a) live battery session go? (b) merge consents (`engine/iter49-rag-parity`, `engine/iter47-call-ledger`)?

### T7 — Registry repair (the branch/iteration SQLite control)
Goal: one queryable registry of ALL iterations/branches/commits, current as of today; owner visual.
Steps:
1. Recover the generator WITHOUT merging: `git -C /tmp/opencode/wt-iter49 show engine/iter47-call-ledger:scripts/call_ledger.py > /home/julio/projects/clean_diallux_SDR/scripts/call_ledger.py` (staging area only; committing it to main is an owner ASK at T6).
2. BACKUP first: `cp research/surgeon/iter47-call-ledger/ledger.db research/surgeon/iter47-call-ledger/ledger.db.pre-iter49b.bak`.
3. Re-run: `.venv/bin/python scripts/call_ledger.py build --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter47-call-ledger/ledger.db` (from the worktree, so `git branch -a` sees all branches; generator reads ITERATIONS.md + surgeon folders + json_logs + Langfuse REST).
4. Verify (SQL, not vibes):
   ```bash
   sqlite3 …/iter47-call-ledger/ledger.db "SELECT count(*) FROM branches;"   # ≥ 92 (90 + iter48-rag-truth + iter49-rag-parity)
   sqlite3 … "SELECT name, head_commit FROM branches WHERE name LIKE '%iter4[89]%';"  # 2 rows
   sqlite3 … "SELECT count(*) FROM commits;"   # > 944
   ```
5. Produce `research/surgeon/iter47-call-ledger/tree.md` (iter47 T2): chronology snap-era → iter25 → iter49, one verdict line per branch, head commit + evidence paths.
6. Note honestly in the report: the registry DB is gitignored evidence (untracked) — git history itself is never lost; the DB is a derived view and this task is its refresh ritual. Recommend (ASK): run the refresh at the END of every battery session (candidate for AGENTS.md Eval-SOP bullet).
Verification: the two iter4[89] rows exist; tree.md renders; AGENTS.md §Eval SOP documents both ledgers + refresh ritual + the pip trap. Docs commit to main; DB/tree are evidence (gitignored).

## Validation Plan (end-to-end, THIS session)
1. Every code step is its own commit on `engine/iter49-rag-parity`; suite green (≥277 + new pins) after each.
2. T3 proven by the replay-sanity table against `kb_chunks_v2` (mirror/deferral/closing KBs surface) — NOT vibes; `kb_chunks` byte-count unchanged (233).
3. T4 proven by the OFFLINE gold-chat replay (per-turn tag-KB presence, Closing >0).
4. T4b/T5 proven by byte-level suite pins (`_warm` == heavy pre-history; prefix invariance under fresh deltas; lite shape budget).
5. T7 registry verified by SQL row counts (iter48 + iter49 branches present).
6. LIVE gates (next session, owner-gated): ack TTFT ≤800ms, first heavy ≤1300ms, cache_read floors 2688/3712, +60ms hot-path guard, happy-4 + battery-13 + price-push persona, `lf_quick.py bugs` ALL COVERED, `live_sql.py gates` no new failure.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Live battery + marker A/B live + cache_read floor measurement (parent T5/T6) | owner directive 2026-09-15: separate live session |
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` (after iter49 proves, owner-gated) |
| In-turn echo duplication (PT-48/FIND-8), name-loop (PT-43), time-extraction 1/500 (PT-44) | separate plans per owner |
| Merging `engine/iter47-call-ledger` into main | owner ASK at T6; generator recovered via `git show` meanwhile |
