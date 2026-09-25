# PLAN — v5 iter53: git-hygiene closeout + RAG retrieval next variable

## Meta
- Date: 2026-09-16 (author: session after iter52 execution; owner-requested)
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: **(A)** close out the git-hygiene mess left by iter52's docs-commit sprawl + the phantom `engine/chat-tests` branch — label/worktree moves only, **ZERO code changes to main**; **(B)** assemble the RAG-retrieval evidence dossier from the existing reports/ledger and pick + execute the next **ONE** retrieval variable (owner-gated).
- Status: **PLAN ONLY (not started — awaits owner approval)**
- This plan is a continuation/recovery plan, not a feature iteration. Read `## Compaction Context` first — it is the whole prior conversation condensed.

## Compaction Context (session state at plan time — pin, do not re-derive)

### Repo, branches, and what happened
- Repo: `/home/julio/projects/clean_diallux_SDR` (outer repo; engine tree lives under `engine/`; engine work happens on `engine/iterNN-*` branches checked out via worktrees under `/tmp/opencode/wt-iterNN`).
- **main trunk (actual, verified 2026-09-16):**
  `4559a33` (merge engine/mvp-finally into main, tag `mvp-finally`) → `fc2fa2f` (mvp docs: ledger + GIT_TREE) → `eccb6b0` (plan iter52 v1) → `ebd3c43` (plan iter52 v2+v3, ONE squashed docs commit — **main HEAD**).
  - 8 docs commits (`eccb6b0`, `21fe6b0`, `a3fac36`, `e069e68`, `37f471a`, `775f985`, `5b4432c`, `f6582dc`) were **squashed today**: `git reset --soft eccb6b0` + one commit (`ebd3c43`, message "docs iter52: plan v2+v3 …"; verified byte-identical to the pre-squash v3 file). The 7 superseded commits are reflog fossils (~90d).
  - `eccb6b0` was **kept** because the iter52 code stub is based on it (avoids a rebase).
- **`engine/iter52-industry-pin`** (worktree `/tmp/opencode/wt-iter52`, HEAD `87612dd`): 2 commits off `eccb6b0` — `0f2128d` (the feature) + `87612dd` (lf_quick fix **+ an accidental sweep of `engine/eval/llm2llm_report.json`** because `git add -A`). Verified diff between the two: only `scripts/lf_quick.py` (1 line) + that eval artifact. **UNMERGED — merge is an owner ASK, NOT part of this plan.**
- **`engine/chat-tests`** (worktree `/tmp/opencode/wt-chat`, parked at `fc2fa2f`): **a phantom branch** — `git log main..engine/chat-tests` = **0 commits**. It never diverged; it is a label on a commit main already contains. Its worktree has ONE uncommitted change: `engine/eval/llm2llm_report.json` (modified). The intended purpose (from `engine/ITERATIONS.md`, mvp-finally entry) was: *"next = `engine/chat-tests` branch: `--warm-greeting-ms 3000` across all states, gate = every transition TTFT <1000ms"* — that work was never committed as branch code.
- **The 3000 ms question (resolved this session):** `warm_greeting_ms` is **test-harness-only** — `engine/tests/llm2llm/harness.py:141,151,157,178` (+ CLI `--warm-greeting-ms`), added by commit `d1dd5a9` ("iter48b exp … engine untouched"). It simulates the production greeting-playback window (`diallux/media/session.py:179-205` fires the same warms during real TTS playback). Production `diallux/` code contains **zero** 3000 ms awaits (grep verified). It IS on main (rode in with the mvp merge) — there was never a divergent chat copy.
- Worktrees: 18 total; `wt-iter33/34/35` are flagged **prunable** (dead dirs). All branch labels are treated by AGENTS.md as the iteration archive — **do not delete labels**.
- Branch counts: 28 branches reachable from main; many older `engine/iterNN-*` / `engine/snap-*` labels are NOT ancestors (their history is the pre-subtree engine tree) — normal, leave alone.

### iter52 execution status (done, unmerged)
- **Shipped on the branch:** pinned industry vertical (metadata fetch-once, `WHERE kb='industry' AND vertical=$tag ORDER BY id`, own block `## INDUSTRY CONTEXT (<tag> — pinned for this call)` prepended to the post-history delta, cap `rag_pin_char_budget=1800`); 5-step resolver (normalize → stoplist → alias map → embed fallback ≥ `rag_filter_score` 0.24 → None); two-layer Plumbing (condensed `## Plumbing` vertical = **20th vertical**, 3 chunks/1759 chars; separate `plumbing` deep-dive KB, 14 chunks, vectorized, scoped on the `plumb` trigger, NEVER pinned); config `rag_pin_industry=True`; `lf_quick.py --db`.
- **DB (shared docker `diallux-db`, already migrated):** `kb_chunks_v2` now **210 rows** (was 193): +3 Plumbing vertical +14 plumbing deep-dive; `vertical TEXT` column added; 60/60 industry rows tagged; 20 verticals; idempotent re-run verified (`pending=0`); `kb_chunks` untouched (233→233).
- **Corpus:** `/home/julio/projects/diallux_kb_lab/corpi/it8_plumbing.json` (210 rows = it7's 193 byte-identical + 17 new); committed in `diallux_kb_lab` at `bc7cee2`. KB sources: `engine/agent/knowledge_bases/industry-kb.md` (+`## Plumbing`, appended AFTER the "End of…" marker to keep existing chunk bytes identical) and NEW `engine/agent/knowledge_bases/plumbing-kb.md`.
- **Tests:** **333 passed** (305 baseline + 28 new) in BOTH modes (`RAG_PIN_INDUSTRY` true/false); iter49 parity file green both modes.
- **Live battery `battery-iter52`** (4 happy personas, ledger commit `0f2128d`): 4/4 PASS booked; **4 × `rag:pin` spans = exactly one per call**, ~2–4 ms each, all resolved via the ALIAS ladder (Marcus→Law Firms, Susan→Home Remodeling, Danny→Auto Repair, Maria→Dental Practices); `pinned` field present on 33 live rag spans; `industry` in reported `kbs` only via the pin; **zero industry lane embeds after the pin round** (baseline happy-chat-c had 23 industry lane hits).
- **Honest misses from the battery:** `pain-points` recall did NOT improve (1 hit / 49 rag spans vs baseline 1/37 — freed slots went to `sales-psychology` 14 / `call-closing` 6); transition-entry TTFT p50 875 ms but **4/28 entries ≥1000 ms** (1002–1113 ms, ConfirmSlots/Closer) vs baseline 1/28 (max 1332 — so max improved, distribution shifted); cache floors intact (118/121 ≥2688; distinct set {1664, 2688, 3712, 4736}).
- **Pre-existing (NOT iter52):** `engine/tests/llm2llm/harness.py --offline` smoke FAILS on the pristine base too — `tests/fake_llm.py:41` asserts `"Discovery" in system`; the offline smoke is stale vs current prompt assembly. Fails identically on the main checkout with zero iter52 code.
- Report: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter52-industry-pin/01_industry_pin.md` (plus the pre-existing `01_audit.md`, `02_action_plan.md`, `03_cross_reference.md`, `04_master_plan.md`).

### RAG-retrieval thread (what the work has been about)
- **Where it came from:** iter48 FIND-9 (`research/surgeon/iter48-rag-truth/10_latency_findings.md`) — the prompt's tag-KB was systematically missing (Intake mirror → industry/pain-points never; Closing `call-closing` 0/4); mid-visit freeze + drift burned ~180 ms/round landing zero deltas. iter49 built the live multi-lane retrieval (`rag_live_retrieve=True`): lane A = one lane per refer-tag scoped `[tag.kb]`; lane B = caller utterance + industry anchor, scoped `_STATE_KBS`; ONE batched arctic embed + concurrent pgvector; quota merge by chunk id (`merge_lane_chunks`, top_k 3, `rag_char_budget` 1600). iter52 added the pin.
- **Retrieval economics today:** the pin removes the biggest re-fetcher (industry) from every round's embed+pgvector; the 3 dynamic `top_k` slots now go to `pain-points` / `sales-language` / `sales-psychology` / `call-closing` / `voice-ai-capabilities` per similarity + quota.
- **KB-Lab (separate repo `/home/julio/projects/diallux_kb_lab`, plan `plans/plan_iter51_kb_gold_filter_d2q_2026-09-13.md`, results `RESULTS.md`)**: headline = **reranker (gpt-4o-mini reads top-20 → returns true top-3) scores 0.896 vs 0.788 arctic baseline**; arctic+rerank **0.788** beats openai+rerank 0.760 under the stronger gpt-4o judge; filter calibration suggests **~0.138** for arctic (0.40 causes 20–88 % silent refusals); scoped prod-mirror at filter 0.138 = 0 refusals. Cutover to the engine is NOT done.
- **Ledger (call evidence):** `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (runs/calls/rounds/rag/findings; schema + gates in `SQL_ANALYSIS_SOP.md` in the same folder). Recent runs: `battery-iter48` (13 calls), `happy-mvp-a`, `happy-chat-a/b/c`, `battery-iter52` (4 calls). Import: `engine/scripts/live_sql.py import --window "HH:MM-HH:MM" --run <name> --commit <sha>`; quick pulls `engine/scripts/lf_quick.py runs|bugs|table|rounds`.

### Open ASKs carried out of the prior session
1. **Merge `engine/iter52-industry-pin` → main?** (owner say-so; the code is tested + battery-verified, branch head `87612dd`).
2. **Two-layer Plumbing is IN and shipped** — its ROI section ships quantity-only; **sanctioned $ figures** are pending (Deferred row in the iter52 plan).
3. `dummy-tool vs real-tools` ack decision; commit root `scripts/call_ledger.py` to main (PT-50 note-only fix parked).
4. **The rule gap that caused the docs-commit sprawl:** AGENTS.md LAW 0 says "DOCS = straight to main" but never says *how many* commits → every edit-pass became a commit. Fix = add the "one docs commit per session/version; amend, don't stack" clause.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| **main = the TTS/voice line. Chat work must live on a real diverging branch (`engine/chat-tests`) with its own commits.** | owner directive 2026-09-16; the chat tests need different logic/harness conventions (e.g. `--warm-greeting-ms 3000` across states) and must not ride main's commits |
| **Hygiene is label/worktree-only — ZERO code changes, ZERO merges of code branches in this plan** | owner directive ("NO messing with code, we are just fixing git mess"); the iter52 code merge is a separate owner ASK |
| `eccb6b0` + `ebd3c43` stay as-is; the full v1→v3 collapse (rebase of the iter52 stub) is **DEFERRED** | owner: "whatever I will clean later"; collapsing would rewrite the stub's base and the ledger references `0f2128d` |
| The 7 squashed docs commits are left as reflog fossils (auto-expire ~90d) | no reachable refs point into them; zero risk |
| `engine/chat-tests` label gets **fast-forwarded to main's tip** (not deleted) | makes it a real, current base for future chat code; deleting labels destroys the archive per AGENTS |
| **Docs rule to add:** one docs commit per session/version — amend the session's docs commit instead of stacking; never one commit per edit-pass | root cause of the 8-commit sprawl; md edits are a single logical unit per session |
| `engine/eval/llm2llm_report.json` on the iter52 branch is **reverted to base** (artifact, not feature) | it rode in via `git add -A`; harness output is evidence → belongs under `research/` (LAW 4), not in the merge diff |
| The RAG next variable = **ONE** owner-picked item from the dossier (T5); no bundling | house law: one variable per iteration |
| `--warm-greeting-ms 3000` stays harness-only; production greeting warms are `media/session.py`'s job | verified `d1dd5a9` + grep; no production change needed |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Approve this plan (hygiene moves + dossier) | owner |
| **Pick the RAG next variable** from the T5 candidate table (C1–C7) | owner (after T5 dossier) |
| Merge `engine/iter52-industry-pin` → main? (separate ASK, not this plan's tasks) | owner |
| Confirm `engine/chat-tests` purpose = the chat harness (`--warm-greeting-ms 3000` across states, gate every transition TTFT <1000 ms) | owner |
| Sanctioned $ figures for the Plumbing ROI Metrics vertical | owner (pricing) |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv` (3.12.3). Worktree venv = symlink.
- Postgres/pgvector: DSN = `DATABASE_URL` in `/home/julio/projects/clean_diallux_SDR/engine/.env` (read the var; do not assume a port). Table `kb_chunks_v2` = **210 rows**, 768-d, has `vertical`. Docker container `diallux-db`.
- Embedder: `snowflake/snowflake-arctic-embed-m` (local fastembed, 768-d; query prefix for queries only; documents none).
- Corpus: `/home/julio/projects/diallux_kb_lab/corpi/it8_plumbing.json` (210 rows). KB-Lab chunker: `/home/julio/projects/diallux_kb_lab/scripts/corpus.py::chunk_v2`.
- KB-Lab results: `/home/julio/projects/diallux_kb_lab/RESULTS.md`, `results.db`, `logs.md`.
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; SOP: `.../iter48-rag-truth/SQL_ANALYSIS_SOP.md`. NO `sqlite3` CLI — use `.venv/bin/python -c "import sqlite3; …"`.
- Langfuse: `http://localhost:3001` (keys in `engine/.env`); SDK helpers `engine/scripts/lf.py` (`_traces(hours=..., name=..., limit=...)`, `_obs(trace_id)`).
- Git: main checkout `/home/julio/projects/clean_diallux_SDR`; iter52 worktree `/tmp/opencode/wt-iter52`; chat worktree `/tmp/opencode/wt-chat`; tree script `scripts/git-tree.sh`; `scripts/keyhound` before ANY push (**no push in normal flow**).
- NEVER touch: live services `:8000`–`:8006`, owner port `:8007`, production agent IDs, deployed Retell LLMs, `kb_chunks` table (SELECT-count only), Cal.com event `3801235` (REAL — cancel every test booking after any battery), the ORIGINAL workspace.

## Architecture (current git topology → target)
```
CURRENT (verified 2026-09-16)
  trunk:  4559a33 ── fc2fa2f ── eccb6b0 ── ebd3c43            [main]
          mvp merge  mvp docs   plan v1    plan v2+v3 (approved v3)
                                  │
                                  └── 0f2128d ── 87612dd      [engine/iter52-industry-pin]
                                                 (feature)  (lf_quick fix + stray eval json)
  label:  engine/chat-tests @ fc2fa2f  ← phantom (0 own commits)
  worktrees: wt-iter33/34/35 prunable; 15 live

TARGET (after this plan's T2)
  trunk:  4559a33 ── fc2fa2f ── eccb6b0 ── ebd3c43            [main]
                                  │
                                  ├── 0f2128d ── 87612dd′     [engine/iter52-industry-pin]
                                  │                (stray eval json reverted)
                                  └── ebd3c43                 [engine/chat-tests]  ← ff'd to main tip
  worktrees: only live ones; prunable metadata gone
```
RAG runtime (iter52, in branch code — for the T5 dossier):
```
{{industry}} dv ─► _ensure_pinned_industry (bg _live_retrieve, ONCE per dv value)
                    ladder: normalize→stoplist→alias→embed(≥0.24, skip header)→None
    tag ─► pinned_by_tag (metadata SELECT, no embed) ─► pin block (cap 1800)
                                                          prepended to the delta
    miss ─► industry stays in lane-B scope (today's vector lane)
  dv contains 'plumb' ─► lane-B scope += 'plumbing' (deep-dive KB, never pinned)
  dynamic lanes: lane A (refer-tags) + lane B (caller+industry) ─► ONE embed ─►
                 pgvector ─► merge_lane_chunks (top_k 3, 1600 chars, ≤1/KB quota)
                 ─► render_knowledge_section (post-history delta)
```

## File Map
| File (absolute path) | What changes | N/E/D |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/AGENTS.md` | LAW 0 gets the docs-commit clause ("one docs commit per session/version; amend, don't stack") | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/DOCTRINE.md` | mirror the clause under the DOCS rule (§2) | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | add a PT row for the git-hygiene closeout + the iter52 merge ASK | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter53-git-hygiene/01_forensics.md` | the forensics report (T1) | New (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter53-git-hygiene/02_rag_dossier.md` | the RAG next-variable dossier (T5) | New (gitignored) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter53-git-hygiene/llm2llm_report_battery-iter52.json` | copy of the battery artifact before reverting it on the branch (T4) | New (gitignored) |
| `/tmp/opencode/wt-iter52` (branch `engine/iter52-industry-pin`) | revert `engine/eval/llm2llm_report.json` to base + commit (T4) | Edit (branch) |
| `/home/julio/projects/clean_diallux_SDR/engine/ITERATIONS.md` | ledger line for the hygiene closeout + iter52 status (T7) | Edit (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/GIT_TREE.md` | regenerated by `scripts/git-tree.sh` (T7) | Edit (docs → main) |

## Deploy Rules
- **NO code merges without Julio's explicit say-so (LAW 0).** This plan performs NO code merge.
- Docs (md) go straight to main; one docs commit for all md changes in this session (the new rule, practiced).
- Branch/label commands are label-only; NEVER `git branch -D`, NEVER `git push`, NEVER force/rebase (the deferred collapse is out of scope).
- Any live/battery session: cancel ALL test bookings after (Cal.com event `3801235` is REAL).
- Before ANY commit that could later be pushed: `scripts/keyhound`.

## Tasks (in order)

### T1 — Forensics report (read-only, no git mutations)
Goal: a fresh agent (or the owner) can read one md and know exactly how the repo got into this state.
Files: `research/surgeon/iter53-git-hygiene/01_forensics.md` (new).
Commands (full, read-only):
```bash
cd /home/julio/projects/clean_diallux_SDR
git log --oneline --graph -12 main
git log --oneline eccb6b0..ebd3c43
git diff --stat main engine/iter52-industry-pin
git log --oneline main..engine/chat-tests | wc -l
git reflog --date=iso | head -30
git worktree list
```
Behavior: record (a) the 8→1 squash + the kept `eccb6b0`; (b) the iter52 branch's 2 commits and the stray eval-json sweep in `87612dd`; (c) the chat-tests phantom proof (`main..chat-tests` = 0); (d) the 3000 ms finding (`d1dd5a9`, harness-only, on main, no production equivalent); (e) the docs-commit rule gap; (f) worktree inventory with prunable flags.
Verification: file exists; every claim carries a sha/command output; no git state changed (`git status` clean except the pre-existing untracked `scripts/call_ledger.py`).

### T2 — Worktree + label hygiene (label-only, ZERO code)
Goal: no dead worktrees, no phantom label; iter52 branch untouched except T4.
Files: none (git metadata only).
Commands (full):
```bash
cd /home/julio/projects/clean_diallux_SDR
# 1. drop dead worktree metadata (dirs already gone; -v prints what it does)
git worktree list                     # confirm which paths are flagged "prunable" FIRST
git worktree prune -v
# 2. move the chat-tests label to main's tip (ff inside its worktree)
git -C /tmp/opencode/wt-chat checkout -- engine/eval/llm2llm_report.json   # discard the stale artifact edit
git -C /tmp/opencode/wt-chat merge main                                    # fast-forward fc2fa2f -> ebd3c43
git -C /tmp/opencode/wt-chat log --oneline -1                              # must equal main's tip
```
Verification: `git worktree list` shows no `prunable`; `git -C /tmp/opencode/wt-chat log --oneline -1` == `git log --oneline -1 main`; `git status --short` in wt-chat clean. **`git worktree prune` only removes records whose DIRECTORY is already gone — it never deletes live files. If any worktree directory holds untracked files you care about, STOP and copy them to `research/` before any removal.**
Dependencies: T1 (inventory).
NOTE: do NOT remove live worktrees (wt-iter37…wt-iter49, wt-mvp, wt-iter52) — owner-gated, list them in the report.

### T3 — Add the docs-commit rule (docs → main)
Goal: the root-cause rule exists so the sprawl cannot repeat by accident.
Files: `AGENTS.md` (LAW 0 area, ~line 40), `DOCTRINE.md` (§2 "DOCS = straight to main", ~line 17).
Exact sentence to add (both files, same wording):
> **One docs commit per session (or plan version) — `--amend` the session's docs commit instead of stacking; never one commit per edit-pass. Plan versions may stack (v1/v2/v3 = max 3 per plan). Code never rides docs commits.**
Verification: `grep -n "One docs commit per session" AGENTS.md DOCTRINE.md` returns both.
Commit (docs lane, ONE commit):
```bash
cd /home/julio/projects/clean_diallux_SDR
git add AGENTS.md DOCTRINE.md
git commit -m "docs: LAW 0 clause — one docs commit per session/version (amend, don't stack)"
```

### T4 — Revert the stray battery artifact on the iter52 branch
Goal: the iter52 merge diff contains code+tests+content only — no eval output.
Files: `/tmp/opencode/wt-iter52/engine/eval/llm2llm_report.json` (branch), plus a copy into research.
Commands (full):
```bash
# 1. preserve the evidence outside engine/ (LAW 4)
mkdir -p /home/julio/projects/clean_diallux_SDR/research/surgeon/iter53-git-hygiene
cp /tmp/opencode/wt-iter52/engine/eval/llm2llm_report.json \
   /home/julio/projects/clean_diallux_SDR/research/surgeon/iter53-git-hygiene/llm2llm_report_battery-iter52.json
# 2. restore the tracked file to the branch base state (removes it from the diff)
cd /tmp/opencode/wt-iter52/engine
git checkout eccb6b0 -- engine/eval/llm2llm_report.json
git add engine/eval/llm2llm_report.json
git commit -m "iter52: revert stray llm2llm_report.json artifact (evidence moved to research/, LAW 4)"
```
Verification: `git -C /tmp/opencode/wt-iter52 diff --stat main | grep llm2llm_report` prints nothing; the copy exists in research; `git -C /tmp/opencode/wt-iter52 status --short` clean.
Dependencies: T1. **Branch-only commit; no merge.**

### T5 — RAG next-variable dossier
Goal: one md table that lets the owner pick the next variable with evidence, no re-derivation.
Files: `research/surgeon/iter53-git-hygiene/02_rag_dossier.md` (new).
Commands (full):
```bash
# a) ledger state for the retrieval runs (SQL, no sqlite3 CLI)
cd /tmp/opencode/wt-iter52/engine
.venv/bin/python -c "
import sqlite3
c=sqlite3.connect('/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db'); c.row_factory=sqlite3.Row
print([dict(r) for r in c.execute(\"SELECT run_id,commit_sha,window,n_calls FROM runs ORDER BY imported_at\")])
print('rag rows battery-iter52:', c.execute(\"SELECT count(*) n FROM rag WHERE run_id='battery-iter52'\").fetchone()['n'])
"
# b) Langfuse pin/span evidence for battery-iter52 (pinned + kbs)
cd /tmp/opencode/wt-iter52/engine && set -a && . ./.env && set +a && .venv/bin/python -c "
import sys; sys.path.insert(0,'scripts'); import lf, json
from collections import Counter
kc=Counter(); pin=Counter()
for t in lf._traces(hours=48, name=None, limit=50):
    for o in lf._obs(t['id']):
        out=o.get('output') or {}
        if isinstance(out,str):
            try: out=json.loads(out)
            except Exception: continue
        if o.get('name')=='rag' and out.get('kbs'):
            for kb in out['kbs']: kc[kb]+=1
            if out.get('pinned'): pin[out['pinned']]+=1
print('kbs:',dict(kc)); print('pinned:',dict(pin))
"
# c) read the referenced reports (no commands — paths):
#    research/surgeon/iter52-industry-pin/01_industry_pin.md
#    research/surgeon/iter48-rag-truth/10_latency_findings.md
#    /home/julio/projects/diallux_kb_lab/RESULTS.md
#    /home/julio/projects/diallux_kb_lab/logs.md
#    plans/plan_iter51_kb_gold_filter_d2q_2026-09-13.md
```
Behavior — the dossier MUST contain this candidate table (each row: evidence, expected gain, cost/risk, exact first step, gate):

| ID | Variable | Evidence | Expected gain | Cost/risk | First step | Gate |
|---|---|---|---|---|---|---|
| C1 | Reranker cutover (top-20 → gpt-4o-mini → top-3) | KB-Lab RESULTS.md rows 10/11/18: 0.896 vs 0.788 baseline; arctic+rerank 0.788 > openai+rerank 0.760 (gpt-4o judge) | biggest relevance win available | one extra LLM call per retrieve (~200–400 ms; must fit `rag_live_await_ms`/speech window) + $ per call | KB-Lab replay of the 4 battery-iter52 queries with rerank over `kb_chunks_v2` | offline replay ≥ baseline relevance; latency delta measured |
| C2 | `rag_filter_score` 0.24 → 0.138 | KB-Lab calibration: 0.40 → 20–88 % silent refusals; scoped 0.138 = 0 refusals | recall up on weak matches (plumbing best 0.20 class) | junk risk; the pin bypasses the filter only for pinned chunks | sweep on live replay (`research/surgeon/iter48-rag-truth` replay script) | hit-rate up, junk chunk rate flat, no regression on iter49 parity |
| C3 | pain-points recall (1/49) | iter52 battery vs happy-chat-c baseline 1/37; slots went to sales-psychology/call-closing | core sales KB surfacing more | none structural; needs diagnosis (query text vs KB content vs quota) | per-span diff of the queried text vs the pain-points KB content for the 4 calls | pain-points ≥ 4/49 retained across 2 batteries |
| C4 | Gap industries (hardware store, real estate, restaurant, tour operator, tech consultancy) | iter52 dv variants (21/16/6 hits); no vertical today → embed fallback | closes the remaining empty-vertical dvs | content authoring (KB-Lab) + T2-style ingest | author 1 vertical (highest hit = hardware store 21) + ingest | vertical resolves + pin fetches; owner picks which |
| C5 | Pin other per-call-constant KBs (call-closing, call-context) | iter48 FIND-9: Closing `call-closing` 0/4 chunks; iter52 call-closing now 6 hits via the anchor | removes the next re-fetcher | second pin mechanism; AGENTS one-owner discipline | measure call-closing/call-context re-fetch counts in battery-iter52 spans | ≥1 fetch removed, no recall loss |
| C6 | Offline smoke fix (`harness.py --offline` stale assert) | fails identically on the pristine base; `tests/fake_llm.py:41` | restores a gate the plans keep citing ("smoke 7/7") | none (test-only) | reproduce at `ebd3c43`, fix the match_system fixture | smoke 7/7 on base + iter branch |
| C7 | chat-tests harness (`--warm-greeting-ms 3000` across states, gate every transition TTFT <1000 ms) | ITERATIONS.md mvp-finally entry; iter52 battery 4/28 entries ≥1000 ms | makes the chat/voice test lanes real + TTFT gate measurable | lives on `engine/chat-tests` (NOT main) | cut real chat commits on the ff'd branch | transitions <1000 ms across the chat run |

Verification: dossier exists; every number traceable to a path/command above; the table is the exact set the owner picks from.

### T6 — Execute the picked RAG variable (BLOCKED until owner picks from T5)
Goal: ONE variable, one iteration, the standard loop.
Files: per the picked candidate (T5 table).
Commands (template — substitute the branch slug and the candidate's steps):
```bash
cd /home/julio/projects/clean_diallux_SDR
git worktree add /tmp/opencode/wt-iter53 -b engine/iter53-<slug> main
ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter53/engine/.venv
cp /home/julio/projects/clean_diallux_SDR/engine/.env /tmp/opencode/wt-iter53/engine/.env
cd /tmp/opencode/wt-iter53/engine && .venv/bin/python -m pytest tests -o addopts="" -q   # baseline (333 on main after iter52 merge — 305 if not merged)
```
Verification: suite green in the worktree; then the candidate's own gate from T5; then battery + `live_sql.py import` + `lf_quick.py bugs`; report under `research/surgeon/iter53-<slug>/`.
Dependencies: owner pick (BLOCKED table).

### T7 — Validation + closeout
Goal: state consistent, ledgered, one-line verdict.
Commands (full):
```bash
cd /home/julio/projects/clean_diallux_SDR
git worktree list                       # no prunable
git -C /tmp/opencode/wt-chat log --oneline -1    # == main tip
git log --oneline --graph -6 main
bash scripts/git-tree.sh
```
Behavior: append the iteration line(s) to `engine/ITERATIONS.md` (hygiene closeout done; iter52 status = unmerged + ASK; the picked RAG variable + verdict), refresh `GIT_TREE.md` via the script, then report to the owner with the ASK list.
Verification: `GIT_TREE.md` regenerated; `ITERATIONS.md` has the new lines; final summary lists exactly the open ASKs.

## Validation Plan (end-to-end)
1. T1: forensics md exists; every claim has a sha/command; git state unchanged.
2. T2: no prunable worktrees; chat-tests == main tip; no label deleted; no code file modified on main.
3. T3: the rule sentence present in BOTH AGENTS.md and DOCTRINE.md; one docs commit.
4. T4: iter52 diff has no `llm2llm_report.json`; artifact copy safe in research; branch commit made.
5. T5: dossier exists with the C1–C7 table; every number traceable.
6. T6 (gated): ONE variable, suite green, candidate gate + battery + ledger import + `lf_quick bugs`.
7. T7: tree refreshed, ledger line written, ASK list reported.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Full collapse of `eccb6b0`+`ebd3c43` into one plan commit (would rebase the iter52 stub) | owner said "I will clean later"; rewrites the stub base + ledger-referenced sha `0f2128d` |
| **Merge `engine/iter52-industry-pin` → main** | owner ASK; separate decision (tested + battery-verified, `87612dd`) |
| Implementing the chat-tests harness code (`--warm-greeting-ms 3000` across states) | belongs ON the chat-tests branch after T2 ff's it; C7 owns it |
| Removing/fixing the pre-existing untracked `scripts/call_ledger.py` / PT-50 registry double-count | owner ASK (d); note-only fix parked |
| Reranker, filter calibration, gap-industry authoring — as a SET | T5 picks exactly ONE (C1–C7); the rest stay queued |
| US-East region migration | `plans/plan_v5_iter50_us_region_migration.md` |
| Sanctioned $ figures for the Plumbing ROI vertical | owner pricing pending |
