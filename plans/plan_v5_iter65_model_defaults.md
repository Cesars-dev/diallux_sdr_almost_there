# PLAN — iter65: model defaults + speech sanitizer + OpenAI boot-prewarm + mic spans + ops rides

## Meta
- Date: 2026-09-22
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: one session — on branch `engine/iter65-model-defaults` (worktree `/tmp/opencode/wt-iter65`, cut from main @ `09bf87b`): (T1) OpenAI connection boot-prewarm, (T2) TTS speech sanitizer gate (verbatim `function_calls` strip + JSON/bracket drop + round-boundary flush — NO tail detector, owner 2026-09-22), (T3) dv carryover — script asks DAILY missed calls, weekly=×5 computed in the code tool, (T4) mic-bridge Langfuse spans (eot_silence_wait + tts_first_byte), (T5) ops rides: SDK rows-out fix + RAG_FIRE_MODE code-default flip (config.py) + FIND-29 row closeout + PT-57 offline smoke re-script + PENDING_TASKS status flips. Suite must stay green (427 baseline), battery, report, ASK.
- Status: **PLAN ONLY (not started — awaits approval)**

## Compaction Context (session 2026-09-22 — pin, do not re-derive)

**Git state:** the ENTIRE iter52→64c ladder (21 commits) was MERGED to main @ `40b3b40` (owner say-so), tag `engine/iter64` @ `801fcdf`, pushed (`f5850e5..09bf87b` on main, branch pushed as backup). LAW 0 v2.1 committed (`09bf87b`): "branch" = owner trigger word → NEW branch per owner order, never stack onto an existing iteration branch, never code/config on main, never on a merge-pending branch. Current worktree: `/tmp/opencode/wt-iter65` on branch `engine/iter65-model-defaults` @ `09bf87b`, suite **427 passed** verified on it, `.env` copied (contains `OPENAI_MODEL=gpt-5.4` — the RUNTIME model pin; `agent/llm.json` model field is display-only dead metadata), venv symlinked to `/home/julio/projects/clean_diallux_SDR/engine/.venv`. MODEL LAW (AGENTS.md): agent LLM = gpt-5.4 everywhere; Langfuse `observations[].model` is ground truth (batteries verified gpt-5.4).

**Batteries + audit (today):** 9/9 BOOK — `chat-iter64-gk` (Sam/Priya/Boris/Bianca/Dave, 06:46-06:55) + `chat-iter64-happy` (Danny/Susan/Marcus/Mike Rourke, 06:55-07:01), ledger `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` @ `7145370` with PT-59 native columns (imported from MAIN SDK `a4802fa`; the WORKTREE's pre-PT-59 `live_sql.py` strips kbs/pinned/lanes/zero_hit — trap documented, engine copy update rides this plan). Five-SOP audit persisted (102 rows in `sops`); reports: `research/surgeon/iter64-industry-gate/02_5sop_report.md` + `03_exec_dashboard.md`. Owner mic test on :8022 (10:34, 53 rounds) imported analyst-side as `mic-iter64-live`.

**The 4 approved fixes + their evidence:**
1. **OpenAI boot-prewarm (owner's #1):** turn-1 TTFT 1,026-2,956ms on 4/9 battery calls + mic turn-1 1,026ms. Root cause: OpenAI TCP/TLS connection cold-start + model spin-up — `llm_ms` 3,249 on the worst (Sam), prompt cache already warm (cache_read 1,664 on ALL 9 turn-1s), RAG 0-51ms. `CALL_PREWARM` (config `diallux/config.py:307`, app startup `diallux/app.py:37-41`) warms ONLY Deepgram flux WS + Cartesia WS + ONNX embed + greeting phrase cache — NO OpenAI connection warm. Fix = one throwaway gpt-5.4 completion at server boot (tiny request, output discarded), so the httpx keep-alive pool is hot when call 1 arrives. `StreamingLLM` (diallux/graph/llm.py:154+) already holds persistent ChatOpenAI twins (`_llm` hot + `_warm_llm` iter43 prewarm twin, `max_completion_tokens=prewarm_max_completion_tokens`); the warm mechanism exists for prompt-cache but is fired per-transition, never at boot.
2. **TTS speech sanitizer:** Susan t3 agent speech ended "…would've booked. **function_calls**" (raw protocol token spoken — model-emitted, exists NOWHERE in prompts/KBs/engine; gpt-5.4 artifact); Sam t35 turn-glue "…lock the walkthrough in? **Absolutely, Sam. Would you prefer la**" (two agent rounds concatenated + mid-word truncation "la"). Both reached speech. Fix territory = the TTS token pipeline: iter41/42 sentence-dedupe buffer at `diallux/graph/builder.py:2224-2442` (sentence flushing + dedupe) — sanitizer belongs there (strip/gate non-natural tokens per sentence before flush; hard sentence-boundary flush BETWEEN rounds; tail-cut detection). CAREFUL: do not break the dedupe machinery (tts_dedupe_sentences, tts_dedupe_semantic 0.90, stem window 12) — sanitizer runs BEFORE the dedupe window on raw flushed sentences.
3. **dv carryover (leak inputs) — DAILY script (owner 2026-09-22, APPROVED):** Susan said avg job $2,500 at t4; Closer re-asked at t10. Owner: script asks DAILY ("how many calls a day go to voicemail?"), code multiplies ×5; outputs ("alpha") stay weekly_leak + monthly_leak. Fix = (a) `Discovery.md` §3 asks daily + capture-if-volunteered rule; (b) `extract_discovery_details` gains 3 variables `missed_calls_daily`/`close_rate_pct`/`avg_job_value` (schema currently LACKS them — plan-correction); (c) `extract_leak_inputs` gains optional `missed_calls_daily`; (d) `calculate_monthly_leak` (llm.json JS code tool) converts weekly = daily × 5 and RETURNS `missed_calls_weekly` so dv stays filled; (e) **the FastAPI validator** `Retell_AI_MCP_connection/validator_endpoint/validate.py:249-260` (LIVE :8003 — owner granted sudo for this): accept `missed_calls_daily` → weekly = daily × 5 (weekly input still accepted), outputs unchanged; `test_validate.py` daily cases; (f) `validate_lead` tool schema gains `missed_calls_daily` param; (g) `Closer.md`: ask daily + never-re-ask-stored + **plain-English reveal** (owner: no robot algebra — "you miss X a day, that's Y a week, so about $Z extra a week"), tool outputs still spoken verbatim; (h) reveal flow UNCHANGED (weekly → monthly from tool outputs). Prompts dir = source of truth; `agent/llm.json` state_prompt updated to byte-match.
4. **Mic-bridge Langfuse spans:** owner mic call E2E is only estimable (~1.2-1.5s) — TTS first-byte and EOT-silence-wait are unspanned. Fix = `diallux/media/session.py`: span `eot_silence_wait` (last speech packet → EagerEOT fire, session.py:454 `_on_eager_eot` — `self._clock.extra["t_eager"]` anchor already exists at iter43 T1, add the span around the detect window) + span `tts_first_byte` (TTS speak request → first WS audio frame; Cartesia/TTS layer `diallux/tts.py` + prewarm pool adoption in `diallux/media/session.py`). Spans land in the `micbridge-*` Langfuse trace → latency_pull + a new ledger column or sidecar read.

**Ops rides approved (T5):**
- `scripts/sop_mechanicals.py` (MAIN SDK) `--rows-out` bug: `rows` list is REASSIGNED per call inside the loop (line ~124 `rows = []` inside `for p in paths:`) → only the LAST call's rows survive (proven today: happy_rows.json = 4 rows = Mike only; gk_rows.json = 5 rows = Dave only). Fix: accumulate `out_rows` (the declared-but-unused list at line ~58). docs rule: scripts/ SDK = straight to main.
- PT-59 engine copy — DROPPED from this plan (owner 2026-09-22: all ledger imports go through the MAIN SDK, which is fixed @ `a4802fa`). The engine worktree copy of `live_sql.py` stays pre-PT-59; known trap documented (importing FROM the engine tree strips kbs/pinned/lanes/zero_hit — always import via main SDK). Rides Deferred for a future ops ride.
- FIND-29 ledger row closeout: `research/surgeon/iter48-rag-truth/ledger.db` table `findings` row FIND-29 (mic best-number wall) — fix landed iter62 (`diallux/graph/tools.py:158-177` need_digits handoff) + proved live today (Danny t11 + Susan t19 rejected the boolean, number captured). UPDATE the row: `fix_commit` = the iter62 commit sha `6d651ea`, `status` = FIXED/VERIFIED, `fix_note` appended. Ops-only (ledger row update via sqlite3 module — NO sqlite3 CLI on this box).
- PT-57 — DROPPED from this plan (owner 2026-09-22: "I don't wanna mess with the engine" — the offline harness lives in `engine/tests/llm2llm/harness.py`, so fixing it = engine edits; it is NOT an SDK bug). Rides Deferred for a separate engine-only ride.
- PT-58 resolution (owner 2026-09-22): flip the CODE default — `rag_fire_mode: "eot"` → `"hybrid"` in `diallux/config.py` — NOT .env (owner: ".env gets lost on worktree copies — carry it in code"). Settings env override remains available if ever needed.
- PT-48/43/45/46 status flips in `plans/PENDING_TASKS.md`: PT-43 → verified fixed by owner prompt (today's Susan t15 company answer PASSED); PT-48 → verified fixed (R5.5 verbatim = 0 across 9/9 calls today, iter59 dedupe v2; Sam t35 glue tracked under the new sanitizer PT); PT-45 → DONE (turn-1 cache_read 1,664 in all 9 battery calls = greeting warms fire in harness); PT-46 → re-scoped per today's data (cache-0 = Closing booked-anchor busts, ≤3/call band holds: 7 happy / 12 gk over 4-5 calls).

**Standing context:** `:8021` STILL serves wt-iter62 (pid 3834955) — untouched (owner law). `:8022` serves wt-iter64 tip (mic test lane, Caddy `/voice64/`, token-gated 4401 fail-closed) — this plan does NOT restart it; the mic server keeps running iter64 code until owner orders the repoint. No merges without owner say-so. `research/` is gitignored. NO `sqlite3` CLI — use venv python + sqlite3 module. pip trap: always `<venv>/bin/python -m pip`, never the pip script.

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| All work on branch `engine/iter65-model-defaults`, worktree `/tmp/opencode/wt-iter65` | LAW 0 v2.1: owner said "branch" → new branch cut from main @ `09bf87b`; suite 427 already verified on it |
| RAG_FIRE_MODE=hybrid goes INTO `.env` (T5) | owner approved ("why do I need to decide" — recommended default); batteries + mic both proven on hybrid today |
| Sanitizer = engine-side TTS-buffer gate: (1) verbatim `function_calls` stripped; (2) JSON/bracket-ish fragments dropped ("never have a code or JSON" — any flushed sentence containing `{ } [ ] => ":` → drop + log); (3) hard flush at round boundaries. Tail-cut detector DROPPED (owner 2026-09-22: "I don't want to trim unnecessarily — it's just gonna cause more problems") | artifacts are model-emitted (gpt-5.4); minimal-touch sanitizer per owner |
| dv carryover = prompt capture-at-Discovery, NOT a new tool | Closer.md already skips when inputs exist; only the capture side is missing |
| Spans named `eot_silence_wait` + `tts_first_byte` on the micbridge trace | matches Langfuse naming family (`await_warm`, `warm:{key}`, `greeting:first_audio` precedents) |
| llm.json + prompts/ edited TOGETHER (byte-parity) | prompts dir = source of truth, llm.json = deployed payload; iter58-era convention both copies updated |
| Suite gate: 427 passed (current count), zero new failures | baseline verified on wt-iter65 today |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| ElevenLabs keys (PT-60) — SEPARATE plan, blocked | owner supplies `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` |
| None for this plan | — |

## Environment & Dependencies
- Worktree: `/tmp/opencode/wt-iter65/engine` — branch `engine/iter65-model-defaults` @ `3ac4ac6` (REBASED from `09bf87b` onto main tip `3ac4ac6` per owner 2026-09-22 — docs-only delta, two-branch discipline; never rebase again unless owner says so), venv symlink `→ /home/julio/projects/clean_diallux_SDR/engine/.venv`, `.env` present (OPENAI_MODEL=gpt-5.4, DEEPGRAM_EAGER_EOT=true, DEEPGRAM_EAGER_EOT_THRESHOLD=0.7 — RAG_FIRE_MODE is NOT in .env; it becomes a config.py code default `hybrid`, PT-58).
- Suite: `cd /tmp/opencode/wt-iter65/engine && .venv/bin/python -m pytest tests -p no:warnings -q` → expect **427 passed** (baseline verified).
- Battery cmd (from `/tmp/opencode/wt-iter65/engine`): `set -a && . ./.env && set +a && date +%H:%M && .venv/bin/python tests/llm2llm/harness.py --personas happy3 --rag --rag-fire-sim --langfuse --max-turns 48; date +%H:%M` (T4 battery: happy3 + Rourke; no RAG_FIRE_MODE export needed — code default `hybrid` rides config.py now).
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; import via MAIN SDK (`cd /home/julio/projects/clean_diallux_SDR && set -a && . /tmp/opencode/wt-iter65/engine/.env && set +a && python3 scripts/live_sql.py import --window "HH:MM-HH:MM" --run <RUN> --branch engine/iter65-model-defaults --commit <sha> --db research/surgeon/iter48-rag-truth/ledger.db`) — main SDK has PT-59 columns; the engine copy does NOT and stays that way (PT-59 engine port dropped from this plan — ALWAYS import via main SDK).
- Read SDKs (main): `python3 scripts/latency_pull.py --run <RUN>` · `python3 scripts/rag_pull.py --run <RUN> --gates`.
- Langfuse: `engine/scripts/lf.py`, host `http://localhost:3001` v3.172.1; `limit=` 400 bug known (workaround documented).
- HITL: `cd /tmp/opencode/wt-iter65/engine && set -a && . /home/julio/projects/video_strategy/.env && set +a && set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<msg>"`.
- Mic server (UNCHANGED, still iter64): `:8022` pid in `/tmp/opencode/voice_8022.pid`, log `/tmp/opencode/voice_server_8022.log`, Caddy route `/voice64/` live. :8021 = wt-iter62 pid 3834955 — NEVER touch.
- Git: push via token from `/home/julio/projects/.env` `GITHUB_TOKEN` (never print; sed-redact URLs). keyhound `./scripts/keyhound` from repo root before push (286 false-positive hits = current clean baseline; no real secrets).

## Architecture (one block diagram)
```
iter65 (branch engine/iter65-model-defaults, worktree wt-iter65)
  T1 boot prewarm: app.py startup → 1 throwaway gpt-5.4 call  → /health warm flag
  T2 sanitizer: builder TTS buffer → token blocklist + round boundary flush → speech
  T3 dv carryover: Discovery asks DAILY → capture volunteered numbers → ×5 in code tool → Closer silent
  T4 mic spans: session.py eot_silence_wait + tts.py tts_first_byte → micbridge trace
  T5 ops: sop_mechanicals rows-out fix (main) · config rag_fire_mode=hybrid code default ·
          FIND-29 row closeout · PT-57 offline re-script ·
          PENDING_TASKS flips (43/48/45/46 verified)
  → suite 427 → battery happy3+Rourke (turn-1 gate) → mic verify → report → ASK
```

## File Map
| File (absolute path) | What changes | New/Edit/Delete |
|---|---|---|
| `/tmp/opencode/wt-iter65/engine/diallux/app.py` | T1: boot-prewarm — after CALL_PREWARM block, one throwaway ChatOpenAI completion (reuse `StreamingLLM._warm_llm` shape; max_completion_tokens=16; content "HI") when `call_prewarm` on; log `llm_prewarm_ms`; expose `"llm_prewarm": true` in `/health` | E |
| `/tmp/opencode/wt-iter65/engine/diallux/config.py` | T1: add `llm_boot_prewarm: bool = True` (gated by call_prewarm) + T5: `openai_model` default `"gpt-5.2"` → `"gpt-5.4"` + comment MODEL LAW + T5 (PT-58): `rag_fire_mode` default `"eot"` → `"hybrid"` | E |
| `/tmp/opencode/wt-iter65/engine/diallux/graph/builder.py` | T2: sanitizer pass on the TTS sentence buffer (before dedupe window): (1) strip verbatim `function_calls` token; (2) drop any flushed sentence still containing JSON/bracket-ish content (`{ } [ ] => ":`) + log; (3) hard flush sentence buffer at round end (glue root cause). NO tail detector (owner: no unnecessary trimming). New config knob `tts_sanitize_tokens: bool = True` | E |
| `/tmp/opencode/wt-iter65/engine/tests/test_iter65_speech_sanitizer.py` | T2 pins: `function_calls` token stripped; JSON/bracket sentence dropped; glued turns flush clean; natural sentences pass byte-identical | N |
| `/tmp/opencode/wt-iter65/engine/diallux/prompts/Discovery.md` + `agent/llm.json` Discovery `state_prompt` (byte-parity) | T3: §3 asks DAILY ("<Roughly how many calls a day do you miss — no one picks up?>") + capture-if-volunteered rule for the leak numbers | E |
| `/tmp/opencode/wt-iter65/engine/diallux/prompts/Closer.md` | T3: ask DAILY; skip-if-stored rule (never re-ask a stored number); manual-math fallback line shows daily×5 | E |
| `/tmp/opencode/wt-iter65/engine/agent/llm.json` (tool schemas + code tools) | T3: `extract_discovery_details` + `missed_calls_daily`/`close_rate_pct`/`avg_job_value`; `extract_leak_inputs` + optional `missed_calls_daily`; `calculate_monthly_leak` weekly = daily×5, returns `missed_calls_weekly` (dv fill); `validate_lead` schema + `missed_calls_daily` param | E |
| `/home/julio/projects/Retell_AI_MCP_connection/validator_endpoint/validate.py` | T3 (FASTAPI, LIVE :8003, owner granted sudo): leak math accepts `missed_calls_daily` → weekly = daily×5 (weekly still accepted); outputs `weekly_leak`/`monthly_leak` unchanged | E |
| `/home/julio/projects/Retell_AI_MCP_connection/validator_endpoint/test_validate.py` | T3: daily→weekly cases (e.g. daily 4 · 50% · $650 → weekly $6,500) | E |
| `systemctl restart validator-service` | T3 deploy step AFTER test_validate green — sudo restart of the LIVE gate (owner-granted), then health-check the endpoint | CMD |
| `/tmp/opencode/wt-iter65/engine/tests/test_iter65_dv_carryover.py` | T3 pin: daily→weekly ×5 conversion; volunteered numbers captured at Discovery; Closer skips the re-ask | N |
| `/tmp/opencode/wt-iter65/engine/diallux/media/session.py` | T4: `eot_silence_wait` span (tracer.span around the EagerEOT detect window; anchor `t_eager` exists iter43 T1) | E |
| `/tmp/opencode/wt-iter65/engine/diallux/tts.py` (or the WS speak path used by mic) | T4: `tts_first_byte` span (request → first WS byte) | E |
| `/home/julio/projects/clean_diallux_SDR/scripts/sop_mechanicals.py` | T5 (MAIN, docs-rule SDK): rows-out accumulates across calls (`out_rows.extend(rows)`) | E |
| DROPPED: engine `live_sql.py` PT-59 rag-columns port | owner 2026-09-22: imports go through MAIN SDK (fixed @ `a4802fa`); engine copy = documented trap, port rides Deferred | — |
| DROPPED: engine `.env` RAG_FIRE_MODE append | moved to config.py code default (owner 2026-09-22: ".env gets lost on worktree copies") | — |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` | T5: UPDATE findings row FIND-29 (fix_commit=`6d651ea`, status=FIXED-VERIFIED) via venv sqlite3 | E (evidence DB) |
| DROPPED: engine `tests/llm2llm/harness.py` PT-57 re-script | owner 2026-09-22: "don't wanna mess with the engine" — offline smoke rides Deferred (separate engine-only ride) | — |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | T5: PT-43 → VERIFIED (owner prompt); PT-48 → VERIFIED (R5.5=0 today); PT-45 → DONE (greeting warms fire in harness, turn-1 cache 1664 9/9); PT-46 → re-scoped done (≤3/call band); PT-57/58/59 status updates; new PT-61..64 rows | E (docs → main) |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter65-model-defaults/01_report.md` | T6 deliverable | N |
| UNTOUCHED: `:8021` (pid 3834955), `:8022` (iter64, live), `:8000-8003`, `engine/iter64*` branches | — | — |

## Deploy Rules
- Suite must be green BEFORE battery: 427 passed + new T2/T3 pins green.
- **BRANCH DISCIPLINE (owner 2026-09-22):** iter65 runs ONLY on its own branch `engine/iter65-model-defaults` (worktree `/tmp/opencode/wt-iter65`, cut from main @ `09bf87b`, clean). NEVER stack on `engine/iter64-elevenlabs-cutover` / `engine/iter66-elevenlabs-cutover` (owner's live ElevenLabs migration) or any merge-pending branch (LAW 0 v2.1). Merge sequencing: owner merges AFTER the ElevenLabs + Twilio work lands — iter65 waits, no cross-branch merges.
- ONE battery minimum after T2/T3 (chat happy3 + Rourke — battery cmd above); mic plane verification = reuse the live :8022 owner test (do NOT restart :8022 for this plan; the mic spans T4 verify on the NEXT owner mic call, or foreground a local uvicorn on a free port :8023 for a self-check).
- Mock slots; cancel any real booking (event 3801235 REAL).
- `.env` never committed; no token in chat/logs/git; keyhound before push.
- Commits: branch commits for engine code; docs/plans/PENDING_TASKS straight to main; SDK fix (sop_mechanicals) straight to main (docs-rule SDK); validator_endpoint edit = Retell repo convention (work on main, test, commit); `systemctl restart validator-service` ONLY after test_validate green (sudo granted by owner for this plan).
- Merge = owner (LAW 0). NEW branches only (LAW 0 v2.1).

## Tasks (in order)

### T1 — OpenAI boot-prewarm
Goal: first call after server boot rides a warm OpenAI connection (turn-1 ≤900ms).
Files: `/tmp/opencode/wt-iter65/engine/diallux/app.py`, `/tmp/opencode/wt-iter65/engine/diallux/config.py`.
Commands: none to run manually (code); verify via suite + battery.
Dependencies: plan approval.
Verification: (a) suite green incl. new pin `test_llm_boot_prewarm_fires` (fake client asserting the warm request shape: max_completion_tokens=16, model from settings); (b) live check: start a foreground uvicorn on `127.0.0.1:8023` from wt-iter65 with `CALL_PREWARM=true`, `/health` shows `"llm_prewarm": true`, log line `llm boot prewarm ok Nms`; (c) battery turn-1 TTFT ≤900ms on 3/3.

### T2 — TTS speech sanitizer gate
Goal: the verbatim `function_calls` token and any JSON/bracket fragment never reach speech; glued rounds flush clean. Natural text is never trimmed.
Files: `/tmp/opencode/wt-iter64/…` NOT — `/tmp/opencode/wt-iter65/engine/diallux/graph/builder.py` (sentence-buffer zone ~2224-2442), new test file above, knob in `config.py`.
Commands: suite; battery.
Verification: new pins green; battery json logs regex-scan `function_calls` + `{`/`[` = 0 hits in agent speech; Sam-class glue gone (round boundary = sentence flush, verbatim-restart absent).

### T3 — dv carryover (DAILY script: capture at Discovery, ×5 in the code tool)
Goal: Closer never re-asks a number the caller already volunteered; script asks DAILY calls (the natural unit), code computes weekly = daily × 5.
Files: `/tmp/opencode/wt-iter65/engine/diallux/prompts/Discovery.md`, `/tmp/opencode/wt-iter65/engine/diallux/prompts/Closer.md`, `/tmp/opencode/wt-iter65/engine/agent/llm.json` (Discovery state_prompt byte-parity + tool schemas `extract_discovery_details`/`extract_leak_inputs`/`validate_lead` + `calculate_monthly_leak` code), `/home/julio/projects/Retell_AI_MCP_connection/validator_endpoint/validate.py` + `test_validate.py` (sudo restart after green), new test above.
Commands: suite; `test_validate.py` daily cases; battery (Susan persona covers it — she volunteers $2,500 at t4).
Verification: new pin green (daily→weekly ×5 conversion, volunteered capture, Closer skip); validator daily math green + service restarted + endpoint health-check; battery Susan call shows missed_calls_daily captured pre-Closer, NO re-ask of any stored number, weekly/monthly leak reveal unchanged (regex scan of transcript).

### T4 — mic spans (eot_silence_wait + tts_first_byte)
Goal: E2E turn latency becomes SQL/Langfuse-measurable.
Files: `/tmp/opencode/wt-iter65/engine/diallux/media/session.py`, `/tmp/opencode/wt-iter65/engine/diallux/tts.py`.
Commands: suite; live check via :8022 owner call OR foreground local test on `:8023` (self-check only, 127.0.0.1, no Caddy).
Verification: a mic session trace contains `eot_silence_wait` + `tts_first_byte` spans; analyst-side ledger import shows the fields; E2E = computed from spans (no more estimates).

### T5 — ops rides (main-side + bookkeeping)
Goal: SDK bug fixed, RAG mode carried in code, ledger truth, status flips.
Files: `/home/julio/projects/clean_diallux_SDR/scripts/sop_mechanicals.py`, `/tmp/opencode/wt-iter65/engine/diallux/config.py` (rag_fire_mode default), ledger findings row, `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md`.
Commands: as in File Map; FIND-29 update cmd (from worktree): `.venv/bin/python -c "import sqlite3; con=sqlite3.connect('/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db'); con.execute(\"UPDATE findings SET fix_commit='6d651ea', fix_note='FIXED iter62 tools.py need_digits handoff; VERIFIED live 2026-09-22 (Danny t11 + Susan t19 NO-boolean → number captured)', status='FIXED-VERIFIED' WHERE id='FIND-29'\"); con.commit()"`.
Verification: rows-out emits rows for ALL calls (spot-check count = calls × categories); `/health` shows `rag_fire_mode: "hybrid"` from the code default; PENDING_TASKS shows flips.

### T6 — battery + report + ASK
Goal: prove it all on the branch, one-page report, owner merge ASK.
Commands: battery happy3 + Rourke (windows captured with `date +%H:%M`), import from main SDK with branch `engine/iter65-model-defaults`, latency_pull turn-1 table, suite re-run, report `research/surgeon/iter65-model-defaults/01_report.md`, `hitl_ping.py` the ASK (turn-1 numbers, sanitizer scan, dv carryover, mic spans seen).
Dependencies: T1-T5.
Verification: report on disk; ledger rows for the new run; NO real bookings (cancel if any appear).

## Validation Plan (end-to-end)
1. Suite 427+new pins green on `engine/iter65-model-defaults`.
2. Battery: happy3 3/3 + Rourke 1/4 booked, turn-1 TTFT ≤900ms on 3/3 (boot-prewarm proof), zero sanitizer violations in transcripts, zero leak-input re-asks; validator `test_validate.py` green incl. daily→weekly cases + `validator-service` restarted + endpoint health-checked.
3. Mic spans appear on a live/foreground mic session trace.
4. SDK rows-out returns all calls' rows; imports store native columns via MAIN `live_sql.py` only (spot-check one run, NO sidecar).
5. Report + Telegram ASK; merge = owner.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| PT-60 ElevenLabs cutover | BLOCKED on owner keys + its own master plan (T1-T8) + T7 production-grade gate |
| Eager threshold sweep (0.5/0.6/0.7) | separate mic experiment; today's 0.7 baseline is recorded |
| PT-43/48/45/46 code work | verified fixed/re-scoped this session — status flips ride T5, no code |
| PT-50 call_ledger fix + main-commit ASK | 6-line spec'd fix; separate owner ASK |
| Restart/repoint :8021, mic-server restart for T4 live verify | owner's call; T4 verifies via foreground self-check first |
| Retell-side PTs (PT-01..08, 31, heating-uk line) | separate project line, not engine |
| PT-59 engine-copy port (`live_sql.py` rag cols) | owner 2026-09-22: all imports via MAIN SDK (fixed @ `a4802fa`); engine copy = documented trap — port on a future ops ride |
| PT-57 offline harness re-script | owner 2026-09-22: "don't wanna mess with the engine" — engine-tests-only edit, deferred to a separate engine ride |
| JSON leak parser beyond the bracket/JSON sentence-drop | the bracket/JSON drop in T2 covers it; deeper parser only if a leak escapes (new PT) |
| Tail-cut detector | owner 2026-09-22: dropped — "I don't want to trim unnecessarily, it's just gonna cause more problems"; if cut tails recur in batteries, revisit as its own PT |
