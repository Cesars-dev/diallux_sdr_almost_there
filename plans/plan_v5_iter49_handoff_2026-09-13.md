# HANDOFF — iter49 execution session (2026-09-13)

> Purpose: context for the FRESH session that executes `plans/plan_v5_iter49_rag_retrieval_parity.md`.
> The plan is copied VERBATIM below from `plans/plan_v5_iter49_rag_retrieval_parity.md`
> @ main commit `c56a4c1`. THE PLAN FILE IS THE SOURCE OF TRUTH — this copy exists only
> so the executing session has plan + context in one place. Do NOT edit the plan via this file.

## Session context (what happened in the 2026-09-13 audit session)

1. **Plan audited against engine code @ `033f742` (worktree `/tmp/opencode/wt-iter44`) — every code claim verified:**
   - `kb_slugs_for` union semantics (builder.py:694-710) — per-state attachment is effectively fake (general_prompt references 7 KBs → all sales states get ~9-10 KB scope).
   - `_RETRIEVAL_OFF = {Booking, VerifyLead, ConfirmSlots, contact_details}`, `_RETRIEVAL_ALLOW = {Closing: [call-closing]}` (builder.py:691-692).
   - `refer_query` (builder.py:712-744) = ONE multi-intent embedding (tag whats + dv values + caller text concatenated).
   - Freeze at state entry (builder.py:973-976) + async drift lane whose deltas get deduped away (builder.py:662-668, 1042-1053) → tail never changes, ~180ms/round burned for nothing.
   - `rag_filter_score=0.40` (config.py:190), `rag_top_k=3` (config.py:186), `tail_before_history=True` (config.py:141 — the RAG tail sits INSIDE the cached prefix today), lite is `turn_index == 1` ONLY (builder.py:861-862 — no per-state lite entry exists today).
   - Transition prewarm EXISTS: `warm_prompt_cache` fires at transition tool-name detection (builder.py:1242) + post-execute force=True (builder.py:1357); `_await_warm` bounded 500ms EOT / 100ms mid-turn (builder.py:885-897); `_warm` builds the tail WITH staged RAG chunks when `prewarm_byte_exact=True` (builder.py:318-331) — this is the collision T4b fixes.
   - Suite confirmed **270/270 green** at `033f742` (run during the audit).
2. **Owner decisions baked into the plan** (docs commits on main: `84a23f7` + `c56a4c1` — see the Resolved Decisions table in the plan):
   - Fresh chunks render **POST-HISTORY in the delta slot, REPLACED each turn**; the pre-history prefix `[tools][head][state-block][history]` is NEVER rewritten. Prompt cache = prefix PLACEMENT, not byte-compare.
   - **Dedupe by chunk id (DB PK) against the CURRENT window** (history trims 16/8 hysteretic, so old chunks may legitimately return); never content bytes (sliding chunk windows break byte dedupe).
   - **Closing gets a hand-written anchor query** ("warm goodbye wrap-up next steps", scoped [call-closing, sales-language]) — Closing.md has ZERO refer tags, so lane A is empty there and raw caller text at 0.60 would still pull 0 chunks.
   - **≤3 engine lanes + ≤3 caller lanes; ONE batched embed call + parallel pgvector** — N sequential embeds cannot meet the ≤+60ms hot-path guard.
   - **Filter threshold re-calibrated for the chosen embedder** — Retell's 0.60 is a reference, not auto-copied (cosine distributions differ per model).
   - **Turn-1 lite UNCHANGED with `LITE_NOOP_TOOL`** — FIND-5: gpt-5.4 only prompt-caches tool-bearing requests; dropping tools kills turn-1 cache.
   - **T4b — per-state LITE ENTRY (owner MUST-HAVE <1000ms):** ack round in a new state = `[state head (kb=False)][state-block dvs][history]` ~1200 tok, NO tools, NO RAG, NO await → ~800ms TTFT; ALL states incl. Booking + contact_details (they stay `_RETRIEVAL_OFF` for RAG but get the lite entry); `_warm` realigned to the RAG-free prefix; `_await_warm` guards HEAVY rounds only; per-state opt-out `state_entry_lite_off`; gates: ack p50 ≤800ms, first heavy round p50 ≤1300ms, cache_read at first heavy round ≥ tools+head+state-block floor.
3. **Key mental model for the executing agent (owner-approved):**
   - The agent's MEMORY = conversation history + dvs. RAG = reference material only. Fresh retrieval per turn does NOT make the agent forget or re-ask.
   - OpenAI prompt cache is automatic and prefix-based; you control it ONLY by message ORDER (stable first, changing last). There is no client-side "compare against cache" API.
   - RAG dedupe (chunk id) and prompt cache (prefix placement) are INDEPENDENT mechanisms.
4. **Open items = the plan's BLOCKED table:** owner's local-embedder research answers (T1 gate — the ONLY blocker), `kb_chunks` other-consumer check at T0, pgvector index params at T0, marker A/B in T5.
5. **Execution mechanics:** fresh worktree `/tmp/opencode/wt-iter49`, branch `engine/iter49-rag-parity` cut from `engine/iter48-rag-truth` @ `033f742`. Follow plan tasks **T0 → T1 → T2 → T3 → T4 → T4b → T5 → T6 → T7 in order**. Every code step = its own commit on the branch. LAW 0: no merge without owner.

---

# PLAN (VERBATIM COPY — source: plans/plan_v5_iter49_rag_retrieval_parity.md @ c56a4c1)

# PLAN — v5 iter49: Knowledge-base retrieval parity + live fresh RAG (own the RAG)

## Meta
- Date: 2026-09-12
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Engine worktree: `/tmp/opencode/wt-iter44` (branch `engine/iter48-rag-truth`, HEAD `033f742`, suite **270 green**)
- Scope: rebuild the KB retrieval lane so every turn gets the RIGHT chunks on THAT response — mimic Retell's `kb_config` semantics, then beat them (per-tag multi-query + local embedder + fresh-per-turn, no freeze).
- Status: PLAN ONLY (not started — awaits owner approval + T1 research answers; execute in a NEW session)
- BASE worktree (read/verify only): `/tmp/opencode/wt-iter44` @ `033f742`
- CODE worktree (created in T0): `/tmp/opencode/wt-iter49`, branch `engine/iter49-rag-parity`
  (cut from `engine/iter48-rag-truth` @ `033f742`); ALL code/test edits happen there.
- Companion plan (infra, runs SECOND, separate session): `plans/plan_v5_iter50_us_region_migration.md` (US-East migration). iter49 (this plan) executes FIRST and can land BEFORE/without the region move — the local embedder works on the current Helsinki box too.

## ▶ NEXT AFTER THIS PLAN (do not start until iter49 passes)
`plans/plan_v5_iter50_us_region_migration.md` — US-East region migration
(Helsinki → Ashburn) + the same local embedder on the new host. Execute ONLY once
this plan's battery + live proof are green (owner-gated). This is the latency plan;
iter49 is the correctness plan. Order: **iter49 (RAG) → prove → iter50 (region).**

## Compaction Context

**Project:** Dialux SDR v5 — a LangGraph re-implementation of the deployed Retell
chat agent (Linda). Engine code on `engine/*` branches, checked out at
`/tmp/opencode/wt-iter44`. Evidence lives in `research/` (gitignored) + a SQLite
ledger (source of truth, see §Source of truth).

**State at end of the 2026-09-12 session (iter48b):**
- Branch `engine/iter48-rag-truth` @ `033f742`: `32d6ea9` Commit B (await split
  500/100 `prewarm_entry_wait_eot_ms`, lite-warm await `lite:<state>`, warm
  WARNING + one lite retry), `d1dd5a9` harness `--warm-greeting-ms` (session-parity
  greeting warms), `7188db7` live_sql G3 threshold fix (was `n+1`, impossible),
  `033f742` THE FIX (`LITE_NOOP_TOOL` `memory_note` on lite turn-1 +
  `prewarm_max_completion_tokens` 16→64).
- Why: raw cURL + OTEL proved **gpt-5.4 only prompt-caches requests carrying
  `tools`** (9/9 no-tools attempts cached=0; 3/3 with-tools cached>0) → FIND-5.
- battery-iter48 (13 personas @ `033f742`): **13/13 PASS**, turn-1 cache 12/13
  (1664-tok lite prefix), turn-1 TTFT 716-1562ms, LLM TTFT p50 821-1023ms.
- Latency forensics (`10_latency_findings.md`): VPS is **Helsinki** (not UK);
  OpenAI origin SF (~150-180ms RTT); **Deepgram worst: connect 120-214ms, TTFB
  457-586ms**; Cartesia 90-114ms; Cal.com US VPS ~75-90ms. Region move planned
  in iter50 (owner decision; all callers US-only).
- Owner confirmed: US-region move + local embedder + **fresh RAG per response**
  are the next structural changes; echo-duplication (PT-48) is separate.

**THE RAG DIAGNOSIS (this plan's subject) — evidence in `research/surgeon/iter48-rag-truth/`:**
- KB inventory (pgvector `kb_chunks`, DSN = settings `database_url`): **233 chunks
  / 10 KBs** — industry 77, pain-points 42, discovery-bridge 37, sales-psychology 30,
  voice-ai-capabilities 16, sales-language 11, hipaa 9, call-context 6, call-closing 3,
  are-you-ai 2.
- `kb_slugs_for(state)` = general_prompt KBs ∪ state KBs → Intake/Discovery/Closer/
  Offer all get the SAME 9-10 KB scope (per-state attachment is effectively fake).
  `_RETRIEVAL_OFF = {Booking, VerifyLead, ConfirmSlots, contact_details}`,
  `_RETRIEVAL_ALLOW = {Closing: [call-closing]}` (builder.py:691-710).
- Query = `refer_query` (iter48 R1): refer-tag `what`s + non-empty dv values + raw
  caller text, ONE embedding. Multi-tag states concatenate DIFFERENT intents
  (e.g. Discovery: "mirroring each problem; deferral escalation").
- Live replay (4 booker calls, Langfuse rag spans, 2026-09-12 14:04-14:06):
  - Intake mirror tag ("refer pain-points-kb") → retrieved **industry** in 4/4 calls;
    **pain-points never surfaced**.
  - Discovery "how does it work" → 3× industry; Discovery "what does this cost" →
    3× industry (sales-language deferral did NOT surface).
  - Offer re-anchoring tag ("refer sales-psychology-kb") → sales-psychology prefetch
    hit only **1/4** calls.
  - Closer "loss playback" → the ONE tag that works (sales-psychology, 1 chunk).
  - **Closing `call-closing` allow-list → 0 chunks in 4/4 calls** (filter_score 0.40
    rejects "ok thanks bye" against the goodbye KB) → agent closes blind.
  - Mid-visit: chunks FREEZE at state entry; the async drift lane re-embeds every
    round (~170-205ms, 137/173 lanes re-retrieved, cos avg 0.761, 98/173 below 0.85)
    but the dedupe discards all deltas → **tail never changes, ~180ms/round burned
    for zero freshness**. Transition prefetch queries carry STALE caller text.
- Recorded: ledger `findings` FIND-1..FIND-9 (FIND-9 = this retrieval diagnosis);
  `plans/PENDING_TASKS.md` PT-43..PT-49 (PT-49 = this plan's tracker).

**Retell parity target (extracted from the deployed snapshot, 2026-09-12):**
`retell/sdr/current/retell/versions/04_slot_lock_CURRENT_cd0464dd/DEPLOYED_llm_snapshot.json`
→ `knowledge_base_ids`: 9 (all KBs attached at the **LLM level, one global scope**);
`kb_config = {"filter_score": 0.6, "top_k": 3}`; model `gpt-5.2`. The `##slug-kb##`
markers in the prompt are **knowledge-base references the platform resolves server-side
(fresh EVERY turn)** — NOT tools. Retell docs: "the agent automatically searches
relevant KBs when it needs information." Our engine re-implements this but with
filter 0.40, a union scope, a hand-built multi-intent query, and a freeze+async-drift
layer Retell does not have. **We are below parity because of our own optimizations.**

**Source of truth (pin both — the owner's explicit requirement):**
- **Git branches/commits:** `engine/iter48-rag-truth` @ `033f742` (worktree
  `/tmp/opencode/wt-iter44`). Every code claim in the evidence is line-pinned to this sha.
  Retell config sha/date: snapshot file above (`last_modification_timestamp` in file).
- **Tests + call evidence DB (SQLite):**
  `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`
  — tables `runs(commit_sha,…)` / `calls` / `rounds` / `rag` / `findings`. Runs:
  smoke-a, happy-a..g, battery-iter48 (each tagged with its commit sha). A copy is
  also at the worktree `research/surgeon/iter48-rag-truth/ledger.db`.
- **Langfuse** (self-hosted `:3001`): the rag spans (`name=rag`/`rag:drift`, output =
  state/ms/chunks/kbs/query/prefetched/frozen_reuse/cosine) are the per-turn ground
  truth for retrieval; `scripts/lf_quick.py` + the REST pattern used in this session.

## Resolved Decisions (DO NOT revisit)
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
| **Closing gets a hand-written anchor query** (e.g. "warm goodbye wrap-up next steps"), scoped [call-closing, sales-language] | Closing.md has ZERO refer tags → lane A empty; raw "ok thanks bye" at 0.60 likely still retrieves 0 chunks (diagnosis was at 0.40) |
| **filter threshold re-calibrated for the chosen embedder** (Retell's 0.60 recorded as reference, NOT auto-copied) | cosine score distributions differ per model (MiniLM runs lower/tighter); per-tag scoping also reduces threshold dependence |
| **`rag_prefetch_on_transition` + drift lane INERT under `rag_live_retrieve=True`** (single flag owns the mode; False = iter48 behavior exactly) | stale-text prefetch is part of the diagnosis; dead work under live-retrieve |
| Turn-1 lite: **keep `LITE_NOOP_TOOL`**; optional ≤2 lane-B retrieves rendered post-history ONLY if turn-1 p50 TTFT budget holds | FIND-5: gpt-5.4 only prompt-caches tool-bearing requests — "lite async without tools" would KILL turn-1 cache |
| **Per-state LITE ENTRY (ALL states incl. Booking + contact_details): first round in a new state = [state head][state-block dvs][history] (~1200 tok) — NO tools, NO RAG, NO await** | owner 2026-09-13 MUST-HAVE: state changes invisible to the user; ack TTFT ~800ms; the 2-3s cold heavy payload NEVER sits on the ack path. Booking/contact_details stay `_RETRIEVAL_OFF` for RAG but GET the lite entry (context = history + state prompt) |
| **Lite entry carries ZERO RAG (owner-picked: context over chunks)** | frozen chunks on entry recreate the two-surface freeze/dedup complexity this plan deletes; KB facts ride the heavy round where fresh retrieval costs ~30-60ms |
| **Heavy warm KEEPS its role, REALIGNED: fires at transition detection + post-execute (unchanged triggers); warms the RAG-FREE prefix [tools][head][state-block][history]; `_await_warm` (500ms EOT / 100ms mid-turn) guards HEAVY rounds ONLY — lite rounds never await** | `_warm`'s staged-RAG tail (builder.py:318-331) must be dropped or `prewarm_byte_exact` breaks at EVERY transition (warm bytes ≠ entry bytes → cold re-prefill); awaiting 500ms before a light call is pure loss |
| **Worst-case budget: ack round ~800ms TTFT; first heavy round ≤1300ms TTFT** (warm landed + small suffix + ≤500ms await insurance) | owner: <1000ms is a must-have, not nice-to-have; battery gates enforce per-round TTFT at transitions |
| **Lite entry has NO tools → the ack round can only SPEAK** (extraction/slots fire round 2+); per-state opt-out list (`state_entry_lite_off`) for any state that must tool-call on entry | acks are speech by design; if a state's entry requires an immediate tool call, it opts out rather than silently losing the tool |
| Echo-dup (PT-48) and name-loop (PT-43) NOT in this plan | separate plans |
| Code lands on `engine/iter49-rag-parity`; LAW 0, no merge without owner | git crystal ball v2 |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner's local-embedder research answers (ms/embed, MB disk/RAM, quality vs text-embedding-3-small, pgvector re-embed difficulty, batch of 3-6 queries) | prompt saved at `research/surgeon/iter48-rag-truth/11_local_embedder_research_prompt.md`; owner runs it and delivers answers at session start |
| Local embedder choice + vector dim (assume `all-MiniLM-L6-v2` 384-dim until told otherwise) | T1 decision from the research answers |
| pgvector index type/params (`kb_chunks_emb_idx` HNSW, `vector_cosine_ops`) + exact row count at go-time | `select count(*) from kb_chunks;` + `\di` vs the live DB at T0 |
| Whether ANY other consumer reads `kb_chunks.embedding` (original workspace / live services) before the T3 column cutover | verify at T0 (`\conninfo`, DSN consumers), NOT at cutover time — dual-column keeps the old column one release as mitigation |
| Does the model actually USE the injected chunks better if the `##slug-kb##` marker is KEPT (not stripped)? | A/B in T5 (flag `rag_keep_markers`) |

## Environment & Dependencies
- Python: `/tmp/opencode/wt-iter49/.venv/bin/python` (3.12) after T0 creates the worktree (base check runs in `/tmp/opencode/wt-iter44`). Baseline suite: `270 passed`.
- pgvector store: Postgres on `localhost:5434/diallux` (DSN = Settings `database_url`,
  from `.env` — never hardcode). Table `kb_chunks(kb, content, embedding vector(1536))`,
  index `kb_chunks_emb_idx USING hnsw (embedding vector_cosine_ops)`.
- Embeddings today: OpenAI `text-embedding-3-small` (1536-dim) via `rag.py openai_embed_fn`.
- Config knobs (diallux/config.py): `rag_top_k=3`, `rag_filter_score=0.40`,
  `rag_drift_async=True`, `rag_append_delta=True`, `rag_prefetch_on_transition=True`,
  `rag_drift_threshold=0.85`, `rag_min_query_chars=12`, `rag_char_budget=1600`,
  `rag_mode='rag'`, `rag_embedding_model='text-embedding-3-small'`.
- Prompt KB references: `diallux/prompts/*.md` + `diallux/prompts/general_prompt.md`
  (`##slug-kb##` markers; `#[refer slug-kb for … — {{dv}}]` tags).
- Retell reference config: `/home/julio/projects/clean_diallux_SDR/retell/sdr/current/retell/versions/04_slot_lock_CURRENT_cd0464dd/DEPLOYED_llm_snapshot.json`
  + `.../knowledge_bases.json` (9 slugs).
- Harness: `/tmp/opencode/wt-iter44/tests/llm2llm/harness.py` (`--personas --rag --langfuse --max-turns 28 --warm-greeting-ms 2000`).
- Ledger tooling: `/tmp/opencode/wt-iter44/scripts/live_sql.py` (import/gates), `scripts/lf_quick.py` (bugs/rounds).
- Ports: :8007 OWNER live-test — never start/stop. :8000-:8006 live services — never touch.

## Architecture (one block)
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

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter49/diallux/config.py` | `rag_filter_score` 0.40→0.60 start (re-calibrated in T4); + `rag_live_retrieve: bool = True`, `rag_multiquery: bool = True`, `rag_keep_markers: bool = False`, `state_entry_lite: bool = True`, `state_entry_lite_off: str = ""` (per-state opt-out), `local_embed_url`/`local_embed_model` | Edit |
| `/tmp/opencode/wt-iter49/diallux/rag.py` | `openai_embed_fn` → add local-embedder path (HTTP `POST {local_embed_url}/embed` or in-process sentence-transformers); `retrieve()` returns chunk id + batched multi-query embed; `render_knowledge_section` provenance kept | Edit |
| `/tmp/opencode/wt-iter49/diallux/graph/builder.py` | `kb_slugs_for` per-state attachment; `refer_query` split into per-tag queries; entry path multi-retrieve + merge with quota; fresh working set REPLACES the post-history delta each turn (`rag_live_retrieve`); pre-history prefix never rewritten; drift+prefetch inert under `rag_live_retrieve`; **T4b: per-state LITE ENTRY path (state head + state-block + history, no tools/RAG/await) + `_warm` realigned to the RAG-free prefix + `_await_warm` gated to heavy rounds only** | Edit |
| `/home/julio/projects/clean_diallux_SDR/scripts/kb_reembed.py` (NEW, repo-level ops script) | one-time KB re-embed to the local model's dim (dual-column cutover + HNSW reindex) | New |
| `/tmp/opencode/wt-iter49/tests/test_iter49_rag_parity.py` | pins: per-tag retrieval hits its KB; Closing call-closing >0 chunks via hand-written anchor; chunk-id dedupe (sliding-window case); pre-history prefix bytes UNCHANGED when live-retrieve toggles fresh sets; filter threshold honored; revert flags restore iter48 behavior; **T4b: lite-entry shape (no tools/no RAG/no await, ~1200-tok budget), `_warm` bytes == heavy-round pre-history bytes (byte-exact re-pin), `_await_warm` skipped on lite rounds, per-state opt-out honored** | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` | post-battery evidence + Retell parity table | New |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` | new runs `happy-h`, `battery-iter49` tagged with commit sha (and `battery-iter49` after the region plan) | Edit (evidence) |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-49 status → IN PLAN; add PT-50 if new findings | Edit |

## Deploy Rules
- Commits ONLY on `engine/iter49-rag-parity` (worktree under `/tmp/opencode/wt-iter49`).
  NO merge/push without owner (LAW 0). Docs (plans/PENDING_TASKS/ITERATIONS) straight to main.
- NEVER start/stop :8007 (owner), live services :8000-:8006, or the original workspace.
- Never modify an existing Retell LLM — read the snapshot only.
- Before any push: `scripts/keyhound`.
- After any owner live/battery session: cancel ALL test bookings (Cal.com event 3801235 REAL).
- The local embedder service (if HTTP) binds `127.0.0.1` on a free port (8004), never public.

## Tasks (in order)

### T0 — Fresh-session context check
Goal: confirm tree/DB/suite before touching anything.
Commands:
```
cd /tmp/opencode/wt-iter44 && git log --oneline -1 && git status --porcelain
.venv/bin/python -m pytest tests -q --tb=no -p no:warnings    # expect 270 passed
.venv/bin/python - <<'EOF'
import sqlite3; db=sqlite3.connect("research/surgeon/iter48-rag-truth/ledger.db")
print([r for r in db.execute("select run_id,commit_sha from runs")])
print(db.execute("select id,status from findings order by id").fetchall())
EOF
```
Verification: HEAD `033f742` (or later iter49 commit), suite 270, ledger shows battery-iter48 + FIND-1..9.

### T1 — Local embedder decision (BLOCKED on owner research)
Goal: pick model + hosting.
Inputs: owner's web-research answers (ms/embed, MB disk, MB RAM, quality vs OpenAI, re-embed difficulty).
Decision to record in the plan + commit message: model name, dim, hosting (in-process vs HTTP :8004).
Verification: a written decision block appended to this plan before any code (or in the commit body).

### T2 — Local embedder wired (query path)
Goal: query embeddings via local model; keep OpenAI as fallback flag.
Files: `diallux/rag.py`, `diallux/config.py`.
Commands:
```
cd /tmp/opencode/wt-iter44
.venv/bin/python - <<'EOF'   # 100-sample latency + sanity
import asyncio,time,sys; sys.path.insert(0,'.')
from diallux.config import Settings
from diallux import rag
async def m():
    s=Settings(langfuse_enabled=False); fn=await rag.openai_embed_fn(s.rag_embedding_model, s.openai_api_key)
    t=time.perf_counter(); vs=await fn(["missed calls pricing objection"])
    print("embed ms", round((time.perf_counter()-t)*1000), "dim", len(vs[0]))
asyncio.run(m())
EOF
```
Verification: p50 embed ≤ 30ms; dim matches the KB column (or the T3 re-embed target).

### T3 — KB re-embed migration (only if dim changes)
Goal: migrate `kb_chunks.embedding` to the local model's space.
Files: `/home/julio/projects/clean_diallux_SDR/scripts/kb_reembed.py` (new).
Procedure (dual-column, zero-downtime):
1. `ALTER TABLE kb_chunks ADD COLUMN embedding_new vector(<dim>);`
2. Batch-embed all 233 chunks (local fn) → UPDATE `embedding_new` (batch ≤ 256).
3. `CREATE INDEX ... USING hnsw (embedding_new vector_cosine_ops)`.
4. Sanity: for the 7 replay queries in `10_latency_findings.md`, print top-3 KBs; assert the tag KB surfaces (pain-points for the mirror, sales-language for deferral).
5. Cutover: rename columns (or set `rag_embedding_col`); keep the old column one release.
Verification: replay table shows the designed KB in top-3 for ≥ the mirror + deferral queries; row count unchanged (233).

### T4 — Retrieval redesign in the engine (mimic Retell, then improve)
Goal: per-turn fresh multi-lane retrieval with a KB quota.
Files: `diallux/graph/builder.py`, `diallux/config.py`, `tests/test_iter49_rag_parity.py`.
- `kb_slugs_for`: real per-state attachment (`_STATE_KBS` map: Intake=[pain-points, call-context, sales-language, voice-ai-capabilities, are-you-ai, sales-psychology, industry, hipaa, call-closing]…; Discovery += discovery-bridge; Closer=[sales-psychology, industry, sales-language, call-context, pain-points]; Offer=[sales-psychology, sales-language, industry, voice-ai-capabilities]; Closing=[call-closing, sales-language]; OFF unchanged). Pin the exact map in the commit.
- `rag_multiquery`: for each refer-tag → `retrieve(tag.what + dv values, scope=tag.kb)`, plus lane B `retrieve(caller_text, scope=state scope)`; ≤3 lanes per side; merge by score, cap 1 chunk per KB unless it's the tag's own KB, top_k=3 total.
- Batch + parallelize: ONE embed call carrying ALL lane query texts; pgvector queries issued concurrently (asyncpg pool); no sequential per-lane embeds.
- Chunk identity: `retrieve()` SELECT adds the chunk PK; returned dicts carry `id`; dedupe keys on `id` against the CURRENT window (frozen tail + untrimmed history + last delta) — never content bytes (sliding-window chunk overlap breaks byte dedupe; history trims 16/8 so an old chunk may legitimately return).
- `rag_live_retrieve=True`: retrieval runs fresh every NON-lite round; the fresh working set REPLACES the post-history delta block each turn (`_build_messages` delta arg, builder.py:529-530); the pre-history prefix ([tools][head][state-block][history]) is NEVER rewritten. Drift lane + `rag_prefetch_on_transition` inert under this flag (revert = False restores iter48 exactly) — SAFE only because T4b realigns `_warm` to the RAG-free prefix (no staged chunks needed anymore).
- Closing anchor: Closing.md has ZERO refer tags (lane A empty there) → hand-written anchor query "warm goodbye wrap-up next steps" scoped [call-closing, sales-language]; parity test asserts >0 call-closing chunks.
- `filter_score`: measured on the 7 replay queries with the chosen embedder; Retell's 0.60 is the REFERENCE, re-calibrate to the model's score distribution; keep `rag_min_query_chars`.
- Lite turn-1 UNCHANGED: lite head + `LITE_NOOP_TOOL` stay (FIND-5: gpt-5.4 caches only tool-bearing requests — dropping tools kills turn-1 cache). Optional ≤2 lane-B retrieves, rendered post-history, only if turn-1 p50 TTFT budget holds.
Commands: suite + a live replay script mirroring the 4-call audit (assert tag-KB present).
Verification: `tests/test_iter49_rag_parity.py` green; the live replay output pasted into `11_rag_redesign_report.md` shows pain-points on Intake mirror, sales-language on Discovery deferral, sales-psychology on Offer re-anchor, call-closing >0 on Closing.

### T4b — State-transition LITE ENTRY + heavy-warm realignment (owner MUST-HAVE: <1000ms through state changes)
Goal: the user never feels a state change. Ack round is light and instant; the heavy payload warms in the background and is cached by the first heavy round.
Files: `diallux/graph/builder.py`, `diallux/config.py`, `tests/test_iter49_rag_parity.py`.
- **Lite entry path** (flag `state_entry_lite=True`): trigger = first round in a state whose name ≠ the previous round's state (covers post-`transition_to_X` ack rounds AND turn-2 entry into the initial state; turn-1 keeps the EXISTING first_turn_lite path untouched). Shape: `[state head (kb=False)][state-block dvs][history window]` — ~1200-tok budget. NO tools (ack speaks; extraction/slots fire round 2+), NO RAG lanes, NO `_await_warm`. Per-state opt-out via `state_entry_lite_off` (comma list) for any state that must tool-call on entry.
- **ALL states get it**, including Booking + contact_details (they stay `_RETRIEVAL_OFF` for RAG; their lite entry = history + state prompt + dvs — e.g. VerifyLead "one moment please", Booking "you're all verified, let me know if that's not for you").
- **`_warm` realignment (the collision fix):** drop the staged-RAG tail from `_warm` (builder.py:318-331); the warm now prefills EXACTLY `[tools][head][state-block][history]` — byte-equal to the heavy round's pre-history prefix. `prewarm_byte_exact` stays True but now pins the RAG-free prefix. Warm triggers UNCHANGED (transition tool-name detection builder.py:1242 + post-execute force=True builder.py:1357). The lite ack neither helps nor hurts the warm (independent shapes, diverge at byte 0 — tools render first).
- **`_await_warm` gating:** lite rounds NEVER await; heavy rounds keep the EOT split (500ms EOT / 100ms mid-turn, builder.py:885-897). Worst case first heavy round ≈ warm-landed cache hit + small suffix + ≤500ms insurance → ≤1300ms TTFT.
- **Timeline note (why this works):** warm fires at transition DETECTED → head start = tool exec + ack gen + TTS + user speech (~3-6s) → by the first heavy round the 2-3s cold warm is done. Mid-turn heavy rounds shortly after the ack (e.g. extract right after transition) are the risk zone — the 100ms await + the ack's ~1.5-2s of elapsed warm time usually cover it; the battery measures it (gate below), autopsy if not.
- Commands: suite + a transition-focused replay (force transitions Intake→Discovery→Offer→Closer→contact_details→VerifyLead→Booking; log per-round TTFT + cache_read at each landing).
Verification: lite-entry shape pins green (no tools/no RAG/no await/byte budget); `_warm` bytes == heavy-round pre-history bytes; ack-round p50 TTFT ≤800ms; first heavy round p50 ≤1300ms; cache_read at first heavy round ≥ tools+head+state-block floor; no state regresses vs battery-iter48.

### T5 — Marker A/B + tail-freshness vs cache check
Goal: decide whether keeping `##slug-kb##` in the prompt helps grounding; prove the fresh post-history delta does NOT bust the pre-history prefix cache (fresh chunks live AFTER history — the [tools][head][state-block][history] prefix bytes must be identical with live-retrieve on/off).
Commands: run happy-4 async with `rag_keep_markers=true|false`; `lf_quick.py bugs --run happy-h-markers`; ledger cache_read on turn-2+ unchanged.
Verification: cache_read floor still 2688/3712 on steady-state rounds AND the T4b transition floors hold (first heavy round after each landing ≥ tools+head+state-block) — if either floor drops, the delta or the warm is rendering in the wrong position — STOP and fix placement before any battery; a judgement on markers recorded.

### T6 — Suite + happy-4 + battery + gates (the proof)
Commands:
```
cd /tmp/opencode/wt-iter49 && .venv/bin/python -m pytest tests -q --tb=no -p no:warnings
# 4 happy personas, async, staggered 15s:
i=0; for P in Maria Danny Susan Marcus; do nohup bash -c "sleep $((i*15)) && set -a && . ./.env && set +a && .venv/bin/python tests/llm2llm/harness.py --personas $P --rag --langfuse --max-turns 28 --warm-greeting-ms 2000" > /tmp/opencode/iter49-$P.log 2>&1 & i=$((i+1)); done
.venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run happy-h --commit <sha>
.venv/bin/python scripts/lf_quick.py bugs --run happy-h
.venv/bin/python scripts/live_sql.py gates --a happy-a --b happy-h
# then battery-13 async staggered (13 personas, same flags) → import battery-iter49
```
Verification: suite green; bugs ALL COVERED; gates no new failure; per-call retrieval (Langfuse rag spans) shows the tag KB on the tag turn for ≥3/4 happy calls; Closing call-closing chunks >0 in all 4.

### T7 — Report + ASK
Files: `research/surgeon/iter48-rag-truth/11_rag_redesign_report.md` (parity table + replay + battery).
Verification: report written, ledger synced to main repo, PENDING_TASKS updated, then ASK owner (merge? live reference?).

## Validation Plan (end-to-end)
1. T0 pins tree/DB/suite; every code step is its own commit on `engine/iter49-rag-parity`.
2. Retrieval correctness is proven by the LIVE REPLAY (not vibes): the tag KB must appear in its state's top-3, Closing must have >0 chunks.
3. Cache regression guard: turn-2+ cache_read floor (2688/3712) unchanged when live-retrieve is on — fresh chunks must render POST-HISTORY (placement is the guard, not byte dedupe).
4. **State-transition latency gate (MUST-HAVE): ack round p50 TTFT ≤800ms; first heavy round p50 ≤1300ms; cache_read at first heavy round ≥ tools+head+state-block floor — measured per state in the battery via ledger rounds; any miss → autopsy + STOP.**
5. Latency guard: local embed p50 ≤30ms; per-round added hot-path time ≤ +60ms vs battery-iter48.
6. Battery + gates + bugs re-verified; any failure → autopsy (ledger findings + PENDING_TASKS) + STOP.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` (infra session, runs after iter49) |
| In-turn echo duplication (PT-48/FIND-8) | separate quality plan |
| First-name company-answer loop (PT-43/FIND-1) | owner: fix later |
| Time-extraction 1/500 (PT-44) | owner: fix later |
| Closing cache-0 round coverage (PT-46/FIND-4) | likely moot once fresh-per-turn RAG lands |
| Sofia slot-loop | iter47 SPEC |
| Heating-uk region | stays UK/EU |
