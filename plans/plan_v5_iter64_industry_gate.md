# PLAN — iter64: `industry-gate` — drop the `industry` KB from PRE-pin retrieval scopes (2-line engine fix)

## Meta
- Date: 2026-09-22
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — gate the shared `industry` KB OUT of retrieval scopes until the industry dv exists / the pin resolves, eliminating the wrong-vertical chunks served on early rounds (Marcus t5 dental→lawyer, Maria t4 derm→dental); + 2 pins + one battery. ONE variable: the pre-pin scope.
- Status: **PLAN ONLY (not started — awaits approval)**

## ⛔ ABSOLUTE NO-TOUCH — MIC/VOICE (read this twice)

| NEVER touch in iter64 | Why |
|---|---|
| `/tmp/opencode/wt-iter62/engine/diallux/media/session.py`, `deepgram_stt.py`, `prewarm.py` | mic/voice owner-calibrated; iter62 MIC GATE still pending the owner's mic re-test call |
| `/tmp/opencode/wt-iter63/engine/diallux/media/*` (same files, iter63 branch) | same |
| `diallux/graph/builder.py` EXCEPT the two scope lines named in the File Map | the rest of the brain is owner-calibrated |
| prompts, `.env`, RAG settings (`rag_filter_score=0.24`, `rag_min_query_chars=12`, `rag_live_await_ms=60`, `rag_top_k=3`, `rag_char_budget=1600`, `rag_pin_industry=True`) | owner-calibrated; the fix is SCOPE-only |
| `:8021` server (pid 3834955, wt-iter62) — NO restart for iter64 | iter62 MIC GATE surface; the server never imports tests/ or the new branch code |
| `:8020`, ports 8000–8003, live agent IDs | live infra |

The ONLY files iter64 may create/modify are listed in the File Map.

## Compaction Context (session 2026-09-22 — pin, do not re-derive)

- **Where we are:** iter63 (`--rag-fire-sim`, harness-only) is COMPLETE on branch `engine/iter63-rag-fire-sim` (head `2cb810f`; commits `5441046` code + `90e71e0`/`1a43a9d` eval artifacts + `2cb810f` replay SDK), suite **425 passed**, hybrid battery 6/6 PASS, full 4-SOP audit persisted (session `chat-iter63-sim-b@1a43a9d`), SDKs live: `/home/julio/projects/clean_diallux_SDR/scripts/rag_pull.py` (read-side, main) + `engine/scripts/rag_replay.py` @ `engine/iter63-rag-fire-sim` (chunk replay) + `/home/julio/projects/clean_diallux_SDR/scripts/sop_mechanicals.py`. iter62 remains UNMERGED (owner mic re-test call pending). iter63 NOT merged (owner STOP POINT). Docs committed to main (`c740b58`, `2a444e4`).
- **The problem iter64 fixes (critical, owner-flagged):** the general retrieval scope (`_STATE_KBS`, Intake/Discovery/Closer/Offer = 9 KBs) **includes the shared `industry` KB before the industry dv is extracted**. The industry KB's pain/ROI chunks are near-identical prose across verticals, so generic caller turns ("50% would book", "15 calls to voicemail") cross-match EVERY vertical at 0.33–0.37 → wrong-vertical chunks in pools and SERVED: Susan t3–t4 (plumbing chunks to a remodeler), Marcus t5 (dental chunk served to a law firm), Maria t4 (derm/cleaning/security to a dentist), Danny t6 (plumbing+MSP). Never wielded harmfully in the battery (6/6 benign), but it is a live risk and quota-crowding + token waste.
- **The pin itself is CORRECT**: `_ensure_pinned_industry` resolved the right vertical in every call (Dental ×2, Auto Repair, Remodeling, Law, Plumbing — 122/146 rounds) and `industry` leaves the vector lanes when pinned (re-enters via the pin block). The defect is ONLY the pre-pin window (~4–6 rounds/call while the caller hasn't named their trade).
- **The key insight:** the wrong-vertical sweep comes from ONE line — `scope = [s for s in kb_slugs_for(state_name) if not (pinned_tag and s == "industry")]` keeps `industry` in scope whenever `pinned_tag` is empty. Gating `industry` out until pinned (or the industry dv exists) removes the entire window with zero information loss: pre-pin rounds are probing rounds served by generic sales KBs; the vertical re-enters via the pin block the moment it resolves (measured: 1 turn after extraction, `await_ms=0` every land).
- **Battery evidence for the fix gate:** replay SDK shows wrong-vertical pool hits on Susan t3/t4, Marcus t3(MSP)/t5(dental), Maria t4(derm/cleaning), Danny t6(plumbing/MSP) — after the fix these pools must contain zero non-caller-vertical industry chunks. The pin-served rounds must be UNCHANGED (kbs=['industry'] pin rounds still serve).
- **SOPs to reuse (SDK-first, do NOT rebuild):** `scripts/rag_pull.py`, `scripts/sop_mechanicals.py`, `scripts/latency_pull.py`, `scripts/live_sql.py sop-import`, engine `scripts/rag_replay.py`. One table per SOP. See `/home/julio/projects/clean_diallux_SDR/docs/Testing_guidelines/RAG-ANALYSIS-SOP.md` + `full_call_analysys.md`.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Gate `industry` out of laneB/lane scope ONLY when `pinned_tag` is empty AND the industry dv is empty | the pin re-introduces the vertical via the pin block; the deep-dive trigger (`_INDUSTRY_KB_TRIGGERS`, e.g. plumb→plumbing) still works because it requires the industry dv |
| Fix lives in `diallux/graph/builder.py` ONLY — the two scope lines (`build_lanes` + `_retrieve_raw` laneB) | single source of the scope; `_STATE_KBS` untouched (frozen/map exactness preserved) |
| Branch `engine/iter64-industry-gate` cut from the head of `engine/iter63-rag-fire-sim` (`2cb810f`) | stacked; the pins need the iter63 replay SDK + fire-sim harness |
| Suite gate: baseline **425** (iter63 head) + 2 new pins = **427 passed, 0 failed** | per-iteration pin convention |
| Battery scope: happy group + Maria solo with `--rag --rag-fire-sim --langfuse` and `RAG_FIRE_MODE=hybrid` exported in the SHELL (never in .env) | same as iter63's proven run `chat-iter63-sim-b`; owner token go required before running |
| Wrong-vertical verdicts computed via `scripts/rag_replay.py` (chunk texts) + Langfuse pin truth — NOT ledger `chunks=0` labels (PT-59 accounting artifact) | ledger drops kbs/pinned |
| No merges, no tags, commits only on `engine/iter64-industry-gate` after suite green; ASK owner at the end (LAW 0) | standing law |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Owner approval of THIS plan | owner says "go" |
| Owner go for the battery (spends OPENAI_API_KEY tokens) | the ASK after T4 |
| iter62 merge decision | pending the owner's mic re-test call (out of scope here) |

## Environment & Dependencies
- Project root: `/home/julio/projects/clean_diallux_SDR` (docs/plans on main; engine on `engine/iterNN-*` worktrees).
- Stacked base: head of `engine/iter63-rag-fire-sim` = **`2cb810f`**. Worktree: `/tmp/opencode/wt-iter64`, branch `engine/iter64-industry-gate`.
- Venv: symlink `/home/julio/projects/clean_diallux_SDR/engine/.venv` → `/tmp/opencode/wt-iter64/engine/.venv` (copy-mirror; pip ONLY via `<venv>/bin/python -m pip`).
- `.env`: copy from `/tmp/opencode/wt-iter63/engine/.env` (contains `OPENAI_API_KEY`, `DATABASE_URL`, `RAG_TABLE_NAME=kb_chunks_v2`, `RAG_FILTER_SCORE=0.24`; note `RAG_FIRE_MODE` is NOT in .env — hybrid must be EXPORTED per shell, see T5). Never committed.
- Suite: `cd /tmp/opencode/wt-iter64/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3` → baseline **425 passed** before edits; final **427 passed, 0 failed**.
- Battery (from `/tmp/opencode/wt-iter64/engine`, `.env` sourced): `set -a && . ./.env && set +a && export RAG_FIRE_MODE=hybrid && .venv/bin/python tests/llm2llm/harness.py --personas happy --rag --rag-fire-sim --langfuse --max-turns 48` then `--personas Maria`.
- Test server `:8021` (pid 3834955, wt-iter62): read-only, health `curl -sf http://127.0.0.1:8021/health`.
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; import `scripts/live_sql.py import --window "HH:MM-HH:MM" --run chat-iter64-sim --branch engine/iter64-industry-gate --commit <sha>` from the wt-iter64 worktree (engine copy) with `.env` sourced. NO sqlite3 CLI — venv python + sqlite3 module.
- Langfuse enrichment sidecar collector: the pattern in `research/surgeon/iter63-rag-fire-sim/rag_span_enrichment_chat-iter63-sim-b.json` (lf.py `_obs` over the 6 traces → JSON). New sidecar: `rag_span_enrichment_chat-iter64-sim.json` in `research/surgeon/iter64-industry-gate/`.
- Telegram HITL: `cd /tmp/opencode/wt-iter64/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<message>"`.
- Prior-iteration refs (read-only): `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter63-rag-fire-sim/06_others_rag_per_turn.md` (the evidence for this fix), `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter63_rag_fire_sim.md`.

## Architecture (one block diagram)
```
iter64 EXEC (branch engine/iter64-industry-gate, stacked on engine/iter63-rag-fire-sim@2cb810f)
  GATE 0 owner approves THIS plan          ← CURRENT
  T1 worktree wt-iter64 + baseline suite 425 (iter63 head)
  T2 THE FIX: pre-pin `industry` scope gate (2 one-line edits in builder.py)
  T3 2 pins (tests/test_iter64_industry_gate.py) — wrong-vertical absent pre-pin; pin path unchanged
  T4 suite gate 427 passed, 0 failed
  T5 battery: happy group + Maria solo (RAG_FIRE_MODE=hybrid exported; owner token go)
  T6 rag_pull + rag_replay verdict: wrong-vertical pool/served = 0 pre-pin; pin rounds unchanged
  T7 ledger import chat-iter64-sim + 4-SOP one-table pass + report + branch commit + Telegram ASK
  STOP — merge = owner decision (LAW 0)
  (NO :8021 restart anywhere — mic/voice untouched)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter64/engine/diallux/graph/builder.py` | T2: in `build_lanes` scope construction (~line 1112–1132) and `_retrieve_raw` laneB scope (~line 1200–1203): when `pinned_tag` is empty AND `str((dvs or {}).get("industry") or "").strip()` is empty → remove `"industry"` from `scope`. TWO one-line conditions; NOTHING else in the file | E |
| `/tmp/opencode/wt-iter64/engine/tests/test_iter64_industry_gate.py` | T3: 2 hermetic pins (spec in §Tasks T3) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter64-industry-gate/01_iteration_report.md` | T7 deliverable: gates table + wrong-vertical verdict + per-SOP one-table pass | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter64-industry-gate/rag_span_enrichment_chat-iter64-sim.json` | T6 sidecar (kbs/pinned per rag span, Langfuse) | N |
| UNTOUCHED FOREVER: `diallux/media/*`, all prompts, `.env`, `:8021`, `:8020`, `:8000-8003`, live agent IDs | — | — |

## Deploy Rules
- NOTHING deploys. `:8021` keeps serving wt-iter62 (pid 3834955) — NO restart (harness/test-only iteration; the server never imports the new branch).
- `.env` never committed; `scripts/keyhound` before any push. Commits only on `engine/iter64-industry-gate` after the suite gate is green. Merge = owner decision (STOP POINT).
- Cancel any Cal.com test bookings (event 3801235 is REAL) if the battery creates one (mock slots default — it should not).

## Tasks (in order)

### T1 — Worktree + baseline
Goal: exact stacked tree; suite green before touching anything.
Files: none.
Commands:
```bash
cd /home/julio/projects/clean_diallux_SDR && git worktree add -b engine/iter64-industry-gate /tmp/opencode/wt-iter64 2cb810f
ln -sfn /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter64/engine/.venv
cp -p /tmp/opencode/wt-iter63/engine/.env /tmp/opencode/wt-iter64/engine/.env
cd /tmp/opencode/wt-iter64/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3
```
Dependencies: owner approval (GATE 0).
Verification: `git -C /tmp/opencode/wt-iter64 log --oneline -1` = `2cb810f`; suite = **422+3 = 425 passed** (any other count → STOP and reconcile).

### T2 — The fix (THE engine change)
Goal: `industry` KB leaves all scopes until pinned or the industry dv exists.
Files: `/tmp/opencode/wt-iter64/engine/diallux/graph/builder.py`.
Commands: in `build_lanes` (after `scope = self.kb_slugs_for(state_name)`, before lane construction) and in `_retrieve_raw` laneB branch, apply:
```python
if not pinned_tag and not str((dvs or {}).get("industry") or "").strip():
    scope = [s for s in scope if s != "industry"]
```
The existing `if pinned_tag:` drop-line stays (covers the pinned case). Note `build_lanes`'s `dvs` param already exists; `_retrieve_raw` has `dvs` in hand. Byte-identical when pinned OR when industry dv known (pin/trigger paths unchanged).
Dependencies: T1.
Verification: `py_compile` clean; `git diff --stat` shows ONLY the two lines (+comment) in `builder.py`; the existing 425 suite still passes BEFORE adding new pins.

### T3 — 2 hermetic pins
Goal: prove the gate closes the window and the pin path is untouched.
Files: `/tmp/opencode/wt-iter64/engine/tests/test_iter64_industry_gate.py` (crib `_t4_settings`/`LanesStore`/`_chunk`/`_run` from `tests/test_iter49_rag_parity.py`; FakeLLM speech round pattern from `tests/test_iter62_lane_restore.py`).
Pins:
1. **`test_industry_absent_pre_pin`** — `rt.build_lanes("Discovery", {}, "<utterance>≥12 chars")` and `rt._retrieve_raw(..., lane="laneB")` produce lanes whose scope EXCLUDES `"industry"` when no industry dv and no pin (pre-fix: included). Also assert the SERVED set from a replayed round contains no `industry`-KB chunk for a generic utterance.
2. **`test_industry_returns_on_pin`** — with industry dv set (`rag_pin_industry=True`, store with `pinned_by_tag` like `test_iter62` solar pin): `_retrieve_raw` laneB scope excludes `industry` (pin path) AND `store.pinned_by_tag` is fetched — the pin block re-introduces the vertical (pin chunks present in `_pinned_industry`), byte-identical to iter63 behavior.
Dependencies: T2.
Verification: `pytest tests/test_iter64_industry_gate.py -q` → 2 passed; zero other test files touched.

### T4 — Suite gate
Files: none.
Commands: `cd /tmp/opencode/wt-iter64/engine && .venv/bin/python -m pytest tests -o addopts="" -q 2>&1 | tail -3`.
Dependencies: T3.
Verification: **427 passed, 0 failed**. If an existing test fails: STOP, diagnose, fix forward or amend THIS plan — never weaken a pin.

### T5 — Chat battery (owner go required — spends tokens)
Commands (from `/tmp/opencode/wt-iter64/engine`, `.env` sourced; `RAG_FIRE_MODE=hybrid` exported in the SHELL — .env untouched):
```bash
set -a && . ./.env && set +a && export RAG_FIRE_MODE=hybrid && date +%H:%M
.venv/bin/python tests/llm2llm/harness.py --personas happy --rag --rag-fire-sim --langfuse --max-turns 48
.venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --rag-fire-sim --langfuse --max-turns 48
date +%H:%M
```
Dependencies: T4 + owner token go.
Verification: 6/6 PASS, all booked/ended, mock slots (no real bookings); window captured for the import.

### T6 — Ledger + replay verdict
Commands: import as above (run `chat-iter64-sim`); collect the Langfuse enrichment sidecar (6 traces → `rag_span_enrichment_chat-iter64-sim.json`, pattern in the iter63 sidecar); then:
```bash
cd /home/julio/projects/clean_diallux_SDR && python3 scripts/rag_pull.py --run chat-iter64-sim --gates
cd /tmp/opencode/wt-iter64/engine && set -a && . ./.env && set +a && .venv/bin/python scripts/rag_replay.py --run chat-iter64-sim --out /tmp/opencode/iter64_rag_truth.jsonl
```
Dependencies: T5.
Verification: (a) gates PASS on served_rate ≥ 95% / await p50 ≤ 80; (b) replay shows **zero wrong-vertical industry chunks in pools/served on pre-pin rounds** (the iter63 defect list: Susan t3/t4, Marcus t3/t5, Maria t4, Danny t6 — those pools now carry no cross-vertical industry chunks); (c) pin rounds byte-unchanged (pin coverage ≈84%, pin-only rounds still serve the vertical block).

### T7 — Report + commit + ASK
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter64-industry-gate/01_iteration_report.md`.
Commands:
```bash
cd /tmp/opencode/wt-iter64 && git add engine/diallux/graph/builder.py engine/tests/test_iter64_industry_gate.py && git commit -m "iter64: pre-pin industry scope gate — wrong-vertical sweep eliminated (2-line fix + 2 pins)"
```
Then Telegram ASK: suite count, gates table, before/after wrong-vertical table, ledger run, report path — merge decision = owner (STOP POINT).
Dependencies: T6.
Verification: suite green; `git -C /tmp/opencode/wt-iter64 status` clean; report on disk; ping sent. **STOP — merge = owner.**

## Validation Plan (end-to-end)
1. Plan approved; all work on `/tmp/opencode/wt-iter64` @ `engine/iter64-industry-gate` stacked on `2cb810f`.
2. Zero diff outside `diallux/graph/builder.py` + the new test file (`git -C /tmp/opencode/wt-iter64 diff 2cb810f --stat`).
3. Suite 427/0; the two pins prove absence pre-pin and unchanged pin behavior.
4. Battery 6/6 PASS; `rag_pull.py --gates` PASS; replay shows zero wrong-vertical industry chunks pre-pin; pin coverage unchanged (~84%).
5. Report on disk; owner ASK sent.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| iter62 T7/T8 (ledger flips, fix report, commit, ASK) | pending the owner's MIC CALL — iter62 plan governs |
| Merging iter63 or iter64 | LAW 0 — owner STOP POINT |
| RAG settings tuning (0.24/12/60) | owner-calibrated |
| `rag` import kbs/pinned columns (PT-59) | separate ops task, engine-branch copy of live_sql.py |
| FIND-8 concat-echo fix | separate iteration (5 CALL PARTIAL verdicts ride on it) |
| Chat lane firing default-on | owner decision after iter63/64 evidence |
