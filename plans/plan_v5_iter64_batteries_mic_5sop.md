# PLAN — iter64: mic gate on :8022 + happy×4 + gatekeepers×5 batteries + full 5-SOP audit

## Meta
- Date: 2026-09-22
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — expose the iter64 mic on a NEW port :8022 (Caddy path-route, token-gated, Telegram link to owner), run the remaining 4 happy-path chat smokes + the 5 gatekeeper ("GK") chat personas, import everything to the ledger, then run ALL FIVE analysis SOPs (RAG, LATENCY, CALL, SALES, HUMANIZED) with ONE TABLE PER SOP as the deliverable.
- Status: **PLAN ONLY (not started — awaits approval)**

## Compaction Context (session 2026-09-22 — take-down of everything already run; pin, do not re-derive)

**Where we are:** iter64 `industry-gate` is EXECUTED on branch `engine/iter64-industry-gate` (worktree `/tmp/opencode/wt-iter64`, commit **`7145370`**, stacked on `engine/iter63-rag-fire-sim@2cb810f`). The fix: pre-pin `industry` scope gate in `engine/diallux/graph/builder.py` (`build_lanes` + `_retrieve_raw` laneB) + replay mirror in `engine/scripts/rag_replay.py` + 5 test-assertion updates (`tests/test_iter49_rag_parity.py` ×4, `tests/test_iter59_dedupe_semantic.py` ×1) + 2 new pins (`tests/test_iter64_industry_gate.py`). Suite: **427 passed, 0 failed**. Baseline was 425 on `2cb810f` (verified twice). NO merges — merge = owner (LAW 0). `:8021` UNTOUCHED (still wt-iter62, pid 3834955 — iter62 mic gate surface).

**What was already run (chat plane):**
1. **Maria smoke — PASS.** Run name `smoke-iter64-maria`, harness log `/tmp/opencode/wt-iter64/engine/tests/llm2llm/json_logs/BOOKMaria_l2l-bookmaria-60663a57.json`, trace `08a8ebb2…` (Langfuse), imported to ledger `research/surgeon/iter48-rag-truth/ledger.db` with `--commit 7145370` AND backfilled (22/22 rag rows now carry kbs/pinned/lanes/zero_hit). Gates: served_rate 100% · land_rate 100% · degraded 0% · q_empty 0% · await_p50 0ms · **pin_coverage 91%** (20/22, `Dental Practices`) · zero_hit 0%.
2. **Chunk-text replay verdict — PASS.** `/tmp/opencode/iter64_smoke.jsonl` (22 rounds via `engine/scripts/rag_replay.py --run smoke-iter64-maria`): **zero wrong-vertical industry chunks in pools/served on every round**; dental pin block served from t5 onward; pre-pin rounds (R00 Intake, R01 Discovery) industry-free.
3. **Chunk-USE judgment (analyst half, done in chat, must ride the report):** t3/t4/t5 RIGHT+USED (adapted, no verbatim leakage — R4 clean) · t6–t21 NO-AMMO-NEEDED (mechanical) · t21 Closing RIGHT+USED. Better-choice flag: R04 (Offer, "book the live call" turn) — the "Default path: book the live call" chunk (0.33) crowded out by owned laneA quota; harmless, record as quota-design note. Lane A/B shapes verified per state (Intake/Discovery tags+laneB, Closer/Offer 1 tag+laneB, contact_details/ConfirmSlots laneB-only, Closing booked-anchor+laneB); laneB utterance verbatim; industry anchor only when dv known; `query[:200]` truncation artifact explains R01's phantom 4th lane (documented trap, not a defect); doubled rows = eager-fire+consume pairs.
4. **SDK/ops — committed to MAIN as `a4802fa`:** PT-59 DONE — `scripts/live_sql.py` rag import now stores `kbs`/`pinned`/`lanes`/`zero_hit` natively (idempotent `_ensure_rag_cols` migration); `scripts/rag_pull.py` reads ledger columns first (sidecar = legacy fallback, globbed across `research/surgeon/*/`); `zero_hit` prefers the honest span flag over `chunks==0` inference. Docs updated: `docs/Testing_guidelines/RAG-ANALYSIS-SOP.md` + `docs/Testing_guidelines/full_call_analysys.md` (sidecar marked LEGACY; mandatory-fix note marked DONE). The smoke run was backfilled from its sidecar `research/surgeon/iter64-industry-gate/rag_span_enrichment_smoke-iter64-maria.json`. KNOWN BUG (documented, NOT fixed — lives in engine tree): `engine/scripts/lf.py` `_traces()` sends `limit=` → HTTP 400 on Langfuse 3.172.1; workaround = call `lf._get(f"/api/public/traces?fromTimestamp={lf._iso(hours)}")` directly and slice client-side.
5. **Aborted run:** `--personas happy3` battery was started 06:37 and user-aborted mid-flight — NO results, must be re-run (T4).

**Mic transport facts (verified):** the mic layer `diallux/media/session.py` NEVER builds scopes — it only fires `runtime.spawn_live_retrieve(state, dvs, transcript, lane)`; scope construction lives exclusively in `builder.py` → the iter64 gate is transport-agnostic. The mic page `diallux/static/mic/index.html` + the VOICE_TEST_TOKEN fail-closed gate (`diallux/app.py:188-193`, close code 4401) are already in the iter64 branch (iter58 ancestor). `:8022` is FREE. Live mic calls still run pre-iter64 code on `:8021` until the owner says restart; this plan adds `:8022` serving the iter64 branch so the owner can mic-test the NEW gate without touching `:8021`.

**The five SOPs to run at the end (one table each, no text walls):**
| # | SOP | Tool | Output plane |
|---|---|---|---|
| 1 | RAG-ANALYSIS | `scripts/rag_pull.py --gates` (+ replay for GK calls if flagged) | gates table |
| 2 | LATENCY-PERCENTILE | `scripts/latency_pull.py` | rounds/percentile table |
| 3 | CALL-ANALYSIS | `scripts/sop_mechanicals.py` + `scripts/live_sql.py sop-import --sop CALL` | sops table |
| 4 | SALES-ANALYSIS | `scripts/sop_mechanicals.py` digest + `sop-import --sop SALES` | sops table |
| 5 | HUMANIZED-ANALYSIS | `sop_mechanicals.py --rows-out` + `sop-import --sop HUMANIZED` | sops table |

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| Mic on a NEW port **:8022** from `/tmp/opencode/wt-iter64`, NOT repoint `:8021` | owner directive; `:8021` stays wt-iter62 (iter62 mic-gate surface, pid 3834955) — no restart law holds |
| Caddy path-route `/voice64/` → `127.0.0.1:8022` on `flores.diallux-ai.site` via the `caddy-apply` candidate flow | no DNS change; handle_path strips `/voice64` so the engine serves unchanged paths; /etc/caddy is root-owned git-tracked |
| Token: `openssl rand -hex 24` → `VOICE_TEST_TOKEN=` in `/tmp/opencode/wt-iter64/engine/.env` (gitignored, mode 660); gate is ALREADY in the app (fail-closed 4401) | public-endpoint-token-gate pattern; never print the token in chat/logs |
| Batteries: `happy3` + `Rourke` (= the 4 non-Maria happy) and `gatekeepers` (exactly 5: Sam, Priya, Boris, Bianca, Dave — all `expect: book`) on the CHAT harness, `RAG_FIRE_MODE=hybrid` exported per shell | owner directive "run the other four… then the five GK personas"; hybrid = iter63-proven mode |
| Runs named `chat-iter64-happy` (4 calls) and `chat-iter64-gk` (5 calls), both imported `--branch engine/iter64-industry-gate --commit 7145370` | ledger session convention `<run>@<commit>` |
| Five-SOP audit AFTER batteries; deliverable = ONE TABLE PER SOP + a ≤10-line summary | owner: "I don't want a full lot of text, I just want a table" |
| Mock slots (harness default) — no live Cal.com; cancel any real booking if one ever appears (event 3801235 is REAL) | standing law |
| Engine code: ZERO new changes this session | iter64 branch is complete; this session = ops (endpoint) + batteries + analysis only |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Current `/etc/caddy/Caddyfile` content (voice route block for flores.diallux-ai.site) | agent is rule-blocked from `sudo cat` — at execution: `sudo /usr/local/bin/caddy-apply` candidate flow reads it, or ask owner to paste the flores block; candidate must preserve the existing `/voice60/` and default routes EXACTLY |
| Owner mic test (the Telegram link) | T3 pings; owner calls whenever ready |
| Merge of `engine/iter64-industry-gate` | owner STOP POINT (LAW 0) — not this plan |

## Environment & Dependencies
- Worktree (all engine commands run here): `/tmp/opencode/wt-iter64/engine` — branch `engine/iter64-industry-gate` @ `7145370`, venv symlinked to `/home/julio/projects/clean_diallux_SDR/engine/.venv`, `.env` present (copy of wt-iter63's).
- Battery cmd (from `/tmp/opencode/wt-iter64/engine`): `set -a && . ./.env && set +a && export RAG_FIRE_MODE=hybrid && date +%H:%M && .venv/bin/python tests/llm2llm/harness.py --personas <MODE> --rag --rag-fire-sim --langfuse --max-turns 48; date +%H:%M`
  - `<MODE>` ∈ `happy3` (Danny, Susan, Marcus) · `Rourke` (Mike) · `gatekeepers` (Sam, Priya, Boris, Bianca, Dave)
- Mic server cmd (from `/tmp/opencode/wt-iter64/engine`, port **:8022**, flags mirroring :8021's health output): `set -a && . ./.env && set +a && export RAG_FIRE_MODE=hybrid CALL_PREWARM=true && setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8022 >> /tmp/opencode/voice_server_8022.log 2>&1 &` then `sleep 6; curl -sf http://127.0.0.1:8022/health`
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` — import from the worktree with `--db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (worktree ROOT trap: the default db path resolves inside the worktree, which has no research/).
- Import cmd: `set -a && . ./.env && set +a && .venv/bin/python scripts/live_sql.py import --window "HH:MM-HH:MM" --run <RUN> --branch engine/iter64-industry-gate --commit 7145370 --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`
- Read-side SDKs (main, commit `a4802fa`): `cd /home/julio/projects/clean_diallux_SDR && python3 scripts/rag_pull.py --run <RUN> --gates` · `python3 scripts/latency_pull.py --run <RUN>` · `python3 scripts/sop_mechanicals.py <json_logs...> --rows-out`
- SOP persistence: `scripts/live_sql.py sop-import --sop CALL|SALES|HUMANIZED --file <rows.json> --run <RUN> --db …` (split files per SOP — mixed file = one `sop` label, blood-paid gotcha). NO `sqlite3` CLI — venv python + sqlite3 module.
- Telegram HITL: `cd /tmp/opencode/wt-iter64/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<message>"`
- Caddy apply: `sudo /usr/local/bin/caddy-apply <candidate>` (allowed pattern; candidate flow = validate → backup → atomic replace → reload).
- Tokens/keys: never print; `VOICE_TEST_TOKEN` read from the worktree `.env` when building the owner link (`grep -c VOICE_TEST_TOKEN` to assert presence, `sed 's/=.*/=<redacted>/'` to display).
- Langfuse: `engine/scripts/lf.py` health OK at `http://localhost:3001` (v3.172.1); remember the `limit`-param 400 bug (workaround documented in `docs/Testing_guidelines/RAG-ANALYSIS-SOP.md`).

## Architecture (one block diagram)
```
iter64 session (branch engine/iter64-industry-gate@7145370 — NO new engine changes)
  T1 mic :8022 up (wt-iter64, token in .env, hybrid+prewarm)      → /health ok
  T2 Caddy candidate: /voice64/* → 127.0.0.1:8022 (caddy-apply)   → external 4401/ok probe
  T3 Telegram link https://flores.diallux-ai.site/voice64/mic?k=…  → owner mic test (async)
  T4 battery happy: --personas happy3  (Danny/Susan/Marcus)        → 3 PASS
     battery happy: --personas Rourke (Mike)                       → 1 PASS
  T5 battery GK:   --personas gatekeepers (Sam/Priya/Boris/Bianca/Dave) → per-expect book
  T6 ledger imports: chat-iter64-happy, chat-iter64-gk (+ windows)
  T7 five SOPs: RAG gates · LATENCY percentiles · CALL · SALES · HUMANIZED (one table each)
  T8 report research/surgeon/iter64-industry-gate/02_5sop_report.md + branch commit(s) + Telegram ASK
  STOP — merge = owner (LAW 0)
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter64/engine/.env` | append `VOICE_TEST_TOKEN=<hex>` | E (gitignored) |
| `/etc/caddy/candidates/<ts>_voice64.caddy` (or per caddy-apply's candidate convention) | add `handle_path /voice64/*` block inside the existing `flores.diallux-ai.site` site block; touch NOTHING else | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter64-industry-gate/02_5sop_report.md` | T8 deliverable: five tables + ≤10-line summary + chunk-USE verdicts from the smoke (compaction context) | N |
| `/tmp/opencode/wt-iter64/engine/eval/llm2llm_report.json` + `tests/llm2llm/json_logs/*.json` | harness artifacts (auto) | N (evidence) |
| UNTOUCHED: `:8021` (pid 3834955), `:8020`, `:8000-8003`, all `engine/diallux/*` code, prompts, `tests/llm2llm/harness.py`, main's `engine/` tree | — | — |

## Deploy Rules
- The ONLY new public surface is `/voice64/` → `127.0.0.1:8022`, token-gated, fail-closed (env unset = 4401 for everyone). Apply Caddy changes ONLY via `caddy-apply` candidates; never hand-edit `/etc/caddy/Caddyfile`.
- `:8021` keeps serving wt-iter62 — NO restart, NO repoint. `:8020` and 8000–8003 untouched.
- `.env` never committed; no token in chat/logs/git; rotate via sed + server restart if ever echoed.
- Batteries run with mock slots; if a real booking appears, cancel immediately (event 3801235 is REAL).
- Commits this session: docs/report/evidence only; any engine-file change = STOP and re-plan (there should be none).

## Tasks (in order)

### T1 — mic :8022 up from wt-iter64
Goal: iter64 branch serving mic on a free port with the token gate armed.
Files: `/tmp/opencode/wt-iter64/engine/.env` (append token line).
Commands:
```bash
TOKEN=$(openssl rand -hex 24) && echo "VOICE_TEST_TOKEN=$TOKEN" >> /tmp/opencode/wt-iter64/engine/.env
grep -c VOICE_TEST_TOKEN /tmp/opencode/wt-iter64/engine/.env   # must print 1
cd /tmp/opencode/wt-iter64/engine && set -a && . ./.env && set +a && export RAG_FIRE_MODE=hybrid CALL_PREWARM=true && setsid nohup .venv/bin/python -m uvicorn diallux.app:app --host 127.0.0.1 --port 8022 >> /tmp/opencode/voice_server_8022.log 2>&1 &
sleep 6; curl -sf http://127.0.0.1:8022/health
ss -ltnp | grep 8022 | grep -oP 'pid=\K[0-9]+' | head -1 > /tmp/opencode/voice_8022.pid
```
Dependencies: plan approval.
Verification: `/health` JSON shows `"python_venv":"/tmp/opencode/wt-iter64/engine/.venv"`, `rag_fire_mode: hybrid`, prewarm ready; `ss` shows 127.0.0.1:8022 LISTEN.
Prove the gate (do NOT print the token): with NO/wrong token the WS must close 4401; `curl -sf "http://127.0.0.1:8022/mic"` serves the page (page itself is not the gate — the WS is).

### T2 — Caddy route /voice64/ → :8022
Goal: public tokenized URL resolves.
Files: candidate file per caddy-apply convention.
Commands: read the current flores block (caddy-apply candidate flow or owner paste), write a candidate that adds ONLY:
```
handle_path /voice64/* {
    reverse_proxy 127.0.0.1:8022 {
        flush_interval -1
    }
}
```
inside the existing `flores.diallux-ai.site` site block, preserving `/voice60/`, `/voice/`, and default routes byte-for-byte. Then `sudo /usr/local/bin/caddy-apply <candidate>`.
Dependencies: T1.
Verification: `curl -sf https://flores.diallux-ai.site/voice64/mic?k=<token-from-.env>` returns the mic page HTML; `curl -s -o /dev/null -w '%{http_code}' https://flores.diallux-ai.site/voice64/mic` (no token) still 200 for the PAGE but the WS handshake without `?k=` closes 4401 (fail-closed lives in the app).
BLOCKED note: if the current Caddyfile cannot be read at execution time, ask the owner to paste the flores block BEFORE writing the candidate.

### T3 — Telegram the link
Goal: owner gets the clickable mic URL.
Commands: build the URL by reading the token into a shell var (never echoed), then `hitl_ping.py` with the message: "iter64 mic gate live on :8022 — <url>. Same flow as voice60; raise a pricing objection somewhere and name your trade late — testing the pre-pin industry gate. :8021 untouched."
Dependencies: T2.
Verification: hitl_ping returns sent; the message contains the full URL with `?k=`.

### T4 — happy battery: the other four
Goal: Danny, Susan, Marcus (happy3) + Mike Rourke.
Files: none (harness artifacts auto).
Commands: the battery cmd above, run twice: `--personas happy3` then `--personas Rourke`.
Dependencies: plan approval (chat plane needs no mic).
Verification: 4/4 PASS, `expect: book` → `booked=True ended=True`, mock slots; capture `date +%H:%M` before/after each run as the import windows.

### T5 — gatekeepers battery (the 5 GK)
Goal: Sam, Priya, Boris, Bianca, Dave — persuasion-heavy, all `expect: book`.
Commands: battery cmd with `--personas gatekeepers`.
Dependencies: T4 (happy gate first per SOP run-order).
Verification: per-persona PASS = booked+ended as expected (5/5 target; any no-book = per-call autopsy line in the report, not a silent pass).

### T6 — ledger imports
Goal: both runs queryable with the PT-59 columns natively.
Commands: two imports (windows from T4/T5): `--run chat-iter64-happy` and `--run chat-iter64-gk`, both `--branch engine/iter64-industry-gate --commit 7145370 --db /home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`.
Dependencies: T4, T5.
Verification: `python3 scripts/rag_pull.py --run chat-iter64-happy --gates` and `… --run chat-iter64-gk --gates` print tables (rounds>0); spot-check `kbs`/`pinned` non-null on post-pin rounds via `--rounds` (NO sidecar needed — PT-59 columns).

### T7 — five-SOP audit (one table each)
Goal: RAG + LATENCY + CALL + SALES + HUMANIZED over chat-iter64-happy, chat-iter64-gk (and smoke-iter64-maria where the SOP wants history).
Commands:
1. RAG: `python3 scripts/rag_pull.py --run chat-iter64-happy --gates` (+ `chat-iter64-gk`, + `--rounds --zero` drill-down only if a gate fails). Gate: served_rate ≥95% · land_rate ≥90% · q_empty 0% · await_p50 ≤80ms · pin_coverage >0 once dv known · zero wrong-vertical industry chunks pre-pin (replay `engine/scripts/rag_replay.py --run <RUN>` if any doubt).
2. LATENCY: `python3 scripts/latency_pull.py --run <RUN>` (both) — ttft p50/p95 vs prior-iteration baseline; one table.
3. CALL+SALES+HUMANIZED: generate rows per `docs/Testing_guidelines/` SOPs with `python3 scripts/sop_mechanicals.py tests/llm2llm/json_logs/<run-logs> --rows-out /tmp/opencode/<sop>_rows.json` (split per SOP), then `python3 scripts/live_sql.py sop-import --sop CALL --file /tmp/opencode/CALL_rows.json --run chat-iter64-gk --db <ledger>` (and SALES, HUMANIZED — separate files/invocations, per-run).
Dependencies: T6.
Verification: five tables exist; every `sops` import prints row counts; NO prose walls.

### T8 — report + ASK
Goal: the whole audit in one page.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter64-industry-gate/02_5sop_report.md`.
Commands: write the report = five tables + ≤10-line summary + the smoke chunk-USE verdicts + better-choice flag + mic-test status placeholder; `hitl_ping.py` the ASK: five gates pass/fail, GK book rate, mic link status — merge decision = owner (STOP POINT).
Dependencies: T7.
Verification: report on disk; Telegram sent; `git -C /tmp/opencode/wt-iter64 status` shows only evidence artifacts; NO engine diffs.

## Validation Plan (end-to-end)
1. `:8022` health OK + Caddy route live + owner mic test link delivered (T1-T3).
2. 9/9 chat batteries PASS with expected book outcomes (4 happy + 5 GK) — any miss gets an autopsy line, not silence.
3. Ledger: both runs imported @ `7145370`; gates readable ledger-only (no sidecar).
4. Five SOP tables produced and persisted (`rag`/`rounds` via SDKs, `sops` via sop-import).
5. Report + Telegram ASK; merge remains owner's call.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| Restarting/repointing `:8021` | iter62 mic-gate surface — owner's call, standing law |
| Merging `engine/iter64-industry-gate` or iter63 | LAW 0 — owner STOP POINT |
| `lf.py` limit-param fix | lives in `engine/` tree — next engine branch, not ops-on-main |
| Curve/breaker/assassin groups | separate owner decision; not ordered |
| Mic-plane automated batteries | owner mic test first; mic SOP verification rides the same SDK flow once a mic run exists |
| FIND-8 concat-echo, PT-59 follow-ups, RAG settings tuning | parked (prior plans) |
