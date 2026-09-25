# PLAN — v5 iter59: Assess everything, then fix the live-call verdicts (RAG freshness · KB everywhere · semantic dedupe 0.90 · prewarm · Retell-parity research)

## Meta
- Date: 2026-09-20
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: owner-ordered plan after the 2026-09-20 live public-path call audit. Phase A (assessment, read-only) first: Retell dialogue pulls (iterations 7.8/7.9), Retell production-stack research via Scrapling/websearch, offline dedupe sweep, verbosity A/B, before/after vertical-prompt dump. Phase B (code, on branch, owner-approved): RAG fresh-every-round, RAG in ALL states ALL times, semantic dedupe at 0.90, Deepgram/Cartesia/RAG prewarm. Prompts and prompt-file edits belong to the OWNER (HITL) — agent proposes patterns, never edits prompts.
- Status: **PLAN ONLY (not started — awaits approval)**
- Branch (Phase B): NEW `engine/iter59-kb-everywhere-freshness` cut from `engine/iter58-eot08-public-mic` @ `db8e56f`.
- Prior plan `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter59_rag-freshness-dedupe-prewarm.md` was DISCARDED by owner 2026-09-20 (revert commit `4e316b6`) — this file supersedes it and absorbs the owner's Q&A decisions verbatim.

## Compaction Context (session 2026-09-20 — pin, do not re-derive)

- **Live call audited:** sid `49fdd9a4cf43`, trace `daee4b0059ac42c5d52826aa2f56eff9`, 2026-09-20 06:49-06:59 UTC, 39 turns, capped at 600 s, NO booking (died in contact_details). Audit run `live-iter58-070@db8e56f` in `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (20 SOP rows). Report: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter58-eot08-public-mic/01_report.md`. Verdicts: CALL PARTIAL · SALES 9/14 solid · HUMANIZED FAIL (verbatim "What's the name of your company?" ×3 across turns + math re-explained ×4) · LATENCY TTFT p50 845 ms / e2e p50 1143 ms · mic inter-arrival p50 ~46/p90 ~63 ms (SSH bridge was the culprit; network path clean).
- **RAG freshness bug (THE bug):** retrieval bg cost p50 131 ms (fastembed arctic ~30-60 + pgvector ~15-40 + merge/pin ~10) vs `rag_live_await_ms` cap 60 → **23/24 rounds `degraded=True`, await_ms≈60-61, LLM consumed the PREVIOUS turn's chunks**. Root cause verified in code: `_fire_live_retrieve` (`diallux/media/session.py:355-370`) fires at EagerEOT/final EOT — the same instant the round consumes — so there is NO speech window despite the design comment. The await never helps because the task starts at consume time. 1/24 landed fresh (await_ms=0).
- **KB-blind spot:** `_RETRIEVAL_OFF = {"Booking", "VerifyLead", "ConfirmSlots", "contact_details"}` at `diallux/graph/builder.py:945` → 10-turn contact_details stretch had ZERO retrievals (rag rows stop 06:57:20). `are-you-ai` + `voice-ai-capabilities` KBs attached only to Intake/Discovery (`_STATE_KBS` builder.py:955-963). Owner DECISION: retrieval in ALL states at ALL times ("that's what Retell does").
- **Industry pin (iter52):** dv-gated (resolves when `industry` dv first non-empty — turn 10, 12.4 ms). Owner DECISION: do NOT resolve at init — "fill that value where we understand the industry, not before". No change to the gating.
- **Dedupe:** iter42 = exact normalized sentence match, window resets every turn ingest (builder.py ~1872-1940). Owner's target bug = the LLM injecting the SAME question twice in a row with 1-2 words different (OpenAI repetition bug, seen repeatedly across iterations). Measured: verbatim 1.00 string-ratio; 1-2-word variants expected cosine ~0.95+ (verified offline in T1 sweep); whole-response rephrasings 0.54-0.57 are a DIFFERENT issue (behavioral, prompt/KB — owner's rebuttal-SOP approach). Owner DECISION: semantic cosine threshold **0.90**, window spans turns.
- **Retell reference (owner-designated quality bar):** `research/transcripts/heating-uk/s07_t1.json` — "are you a real person or one of those AI things?" → "I'm Tom, the AI virtual receptionist. You're after a plumber — how can I help?" — identity owned in one sentence, call advanced. Owner wants 3-5 MORE dialogue calls from Retell iterations 7.8/7.9 (chat-tested payloads already downloaded somewhere in the repo — likely ignored; else download via Retell API) to extract the objection-engine design and KB-trigger pattern.
- **Retell stack question (Q7):** 3.4 s answer→first-speech (server-side slice of the measured 6.4 s) is "brutal". Owner wants Scrapling used to research what Retell does for instant speech (they claim sub-800 ms, in-house voice engine). This is an ASSESSMENT task feeding the prewarm design.
- **Call-start split (measured):** 6.4 s total = 2.9 s Mac/browser (mic permission + AudioWorklet + WSS — Twilio never sees it) + 3.4 s engine (Deepgram connect 1.4 s + Cartesia 0.5 s + greeting 0.5 s + wiring). Lite-warm/preload machinery EXISTS and worked (warm:Intake landed during greeting, turn-1 cache 1664) — what is NOT prewarmed is the transport layer. Prewarm = idle Deepgram flux WS + Cartesia WS + RAG staged at server start, adopted by call 1.
- **Math/unit bug:** agent said "$8,400 a month" (t20) for a WEEKLY leak (tool: `weekly_leak: 8,400`, `monthly_leak: 36,300`). Owner DECISION: platform-side prompt pattern — the model receives the values and an instruction like "[read the math to the user in a non-robotic humanized way]" ("from 20 calls, 70% = 14 jobs × $600 = $8,400 a week — $36,000 a month — how would it feel to get that back?"); model composes, no verbatim script; tool stays the calculator.
- **Painification KB:** owner-approved concept — dedicated KB + refer-tag (`#kb:painification` style, like today's refer system) so the engine queries it where the prompt tags it; model combines numbers + painification technique + industry into ITS OWN question (logic, not verbatim). KB CONTENT owner-drafted; creation needs `kb_registry.json` entry + owner cost sign-off ($250 lesson). Agent may ingest only after approval.
- **Verbosity:** already medium everywhere (no .env override; `openai_verbosity: "medium"` config.py:42). Medium-state TTFT p50 (Offer 813, contact 841) ≤ others. Owner DECISION: A/B test medium vs high offline ("but first pick the bot" — the A/B runs on the ENGINE persona harness, not a live call). Temperature: we send 0.30 but gpt-5.4 IGNORES temperature (log line "temperature=0.30 ignored for reasoning model gpt-5.4 (API-fixed)"); `openai_reasoning_effort: "none"` (config.py:41). The A/B is verbosity-only.
- **Geo (measured):** VPS = Hetzner Helsinki, FI. Deepgram TLS 303 ms / Cartesia 160-267 ms / OpenAI edge 30-50 ms. Migration parked (owner Q8: "later, until we have production").
- **Deepgram eager_eot_threshold hard cap 0.70** (0.8 → HTTP 400, bisected live). `.env` = 0.7 now.
- **Caps live via `.env`:** `MAX_CALL_TURNS=64`, `MAX_CALL_SECONDS=900`.
- **Live endpoint:** `https://flores.diallux-ai.site/voice/mic?k=<VOICE_TEST_TOKEN>` → Caddy `handle_path /voice/*` → 127.0.0.1:8020 (fail-closed token gate, skill `public-endpoint-token-gate`). :8020 currently runs the iter58 worktree; iter59 restarts it from the NEW worktree at the deploy step.
- **iter58 open items:** `docs/CALL_FACTS.md` row, `plans/PENDING_TASKS.md` PT rows, docs commit, merge ASK (folded into T7 closeout).
- **House rules:** LAW 0 (code → branch → ASK; docs → main), evidence → `research/` (gitignored), `.env` never committed, `scripts/keyhound` before push, Cal event 3801235 REAL (cancel test bookings), never modify production agents (`agent_16985b…` voice, `agent_f305…` sdr, `agent_87e4…` chat) — READ-ONLY API pulls of their transcripts are allowed; KB policy: reuse/upsert via `kb_registry.json`, never hand-create (~$250 lesson).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| RAG retrieval in ALL states, ALL times (kill `_RETRIEVAL_OFF` entirely; local arctic embedder makes cost a non-issue) | owner: "let's just add all knowledge base at all states at all times because that's what Retell does" |
| Keep the dv-gated industry pin AS-IS (no init resolution) | owner: "don't reinvent the wheel… fill that value where we understand the industry, not before" |
| Dedupe v2 = semantic cosine **0.90**, cross-turn window; targets the LLM twice-injected near-verbatim question bug | owner: "give it 90%, that should do it"; 1-2-word variants score ~0.95 cosine |
| Freshness fix evaluated BOTH ways in the plan: (A) fire at StartOfTurn + keep bounded await as safety net, (B) pure sync merge at round time (no await) — decision recorded in T1 report before code lands | owner: "the plan shall evaluate if we should keep the 60 ms wait or just do the sync, merge, and launch" |
| Prewarm transport (Deepgram + Cartesia + RAG stage) at server start | owner confirmed prewarm intent; 1.9 s of the 3.4 s is connect cost |
| Verbosity A/B medium vs high = OFFLINE harness test only | owner: "run an A-B test on the velocity medium and the velocity high" |
| Retell research = (a) find/re-pull 3-5 dialogue calls from iterations 7.8/7.9, (b) Scrapling/websearch their production stack | owner ordered both (Q5/Q7) |
| All prompts + prompt-file edits = OWNER only; agent proposes patterns/structure | owner: "leave the prompting to me" |
| Humanized math = prompt-side pattern; engine never reformats math | owner: "maybe doing it engine-side creates more problems than it solves" |
| Server migration deferred | owner Q8: "leave that for later" |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Painification KB source content | owner drafts; ingest + `kb_registry.json` entry AFTER owner cost approval |
| Prompt rewrites (humanized math pattern, side-question rule, "never re-ask" rebuttal SOP) | owner writes (HITL) — agent supplies the evidence pack + proposal shapes |
| Location of already-downloaded Retell-era dialogue JSONs (if not found in repo) | owner points to path, or T0 pulls fresh via Retell API (read-only) |
| `RETELL_API_KEY` for dialogue pulls | already in engine `.env` (`RETELL_API_KEY`) — used READ-ONLY (list-calls / get-chat) |

## Environment & Dependencies
- Worktree: `/tmp/opencode/wt-iter59` — `cd /home/julio/projects/clean_diallux_SDR && git worktree add /tmp/opencode/wt-iter59 engine/iter59-kb-everywhere-freshness` after `git branch engine/iter59-kb-everywhere-freshness db8e56f`. Venv symlink: `ln -s /home/julio/projects/clean_diallux_SDR/engine/.venv /tmp/opencode/wt-iter59/engine/.venv`.
- Env: `cp -p /tmp/opencode/wt-iter58/engine/.env /tmp/opencode/wt-iter59/engine/.env` (mode 660, gitignored; carries keys, `DEEPGRAM_EAGER_EOT_THRESHOLD=0.7`, `MAX_CALL_TURNS=64`, `MAX_CALL_SECONDS=900`, `VOICE_TEST_TOKEN`).
- Suite: `cd /tmp/opencode/wt-iter59/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → 368 + new pins.
- Server :8020 ONLY via `bash scripts/serve_voice.sh` from the engine dir. NEVER `.venv/bin/uvicorn`.
- Langfuse: `http://localhost:3001`; SDK `scripts/lf.py`. Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db`; SDKs `python3 /home/julio/projects/clean_diallux_SDR/scripts/live_sql.py` + `latency_pull.py`. NO sqlite3 CLI.
- Local embedder: fastembed 0.8.0, `snowflake/snowflake-arctic-embed-m` (768-d), ONNX threads 4, query prefix baked in `diallux/rag.py`.
- Scrapling: `/home/julio/projects/scrapling-mcp/.venv/bin/python` + `from scrapling import Fetcher` (see `/home/julio/projects/scrapling-mcp/AGENTS.md`); no key, $0. Websearch tool available as fallback.
- Retell API (READ-ONLY): base `https://api.retellai.com`, auth `Bearer $RETELL_API_KEY` (engine `.env`); endpoints used: `GET /v2/list-calls?agent_id=<id>&limit=…`, `GET /v2/get-call/:call_id` (voice), `GET /get-chat/:chat_id` (chat V7.9 `agent_87e4d5f08475e5bc558b2f390f`). NEVER PATCH/POST agent configs.
- Telegram ping (both-env export form): `cd /tmp/opencode/wt-iter59/engine && set -a && . /home/julio/projects/video_strategy/.env 2>/dev/null; set +a; set -a && . ./.env && set +a && .venv/bin/python scripts/hitl_ping.py "<text>"`.

## Architecture (one block)
```
Assessment Phase A (read-only, this plan's T1-T4):
  Retell 7.8/7.9 dialogue pulls ─┐
  Retell stack research          ├─► evidence pack ─► owner reviews ─► GO per fix
  dedupe sweep 0.90              │
  verbosity A/B med vs high      ┘
Fix Phase B (branch, owner-approved):
  Mac/Twilio ─► Caddy /voice/* ─► :8020 (iter59)
    ws open ─► token gate ─► PREWARM POOL (Deepgram flux WS + Cartesia WS idle, adopted by call 1)
    session ─► RAG already staged (embedder session, pgvector pool)
    StartOfTurn ─► spawn_live_retrieve ONCE (final utterance) ─► task LANDS during speech
    EOT ─► round consumes: fresh landed (pgvector ~15-30 ms, zero await) | frozen-reuse fallback — never stale-prev
    ALL states retrieve (no _RETRIEVAL_OFF) ─► refer-tag lanes + lane-B utterance + industry pin (dv-gated, unchanged)
    dedupe v2: sentence stream → exact window + semantic cosine 0.90 vs per-CALL question-stem window (cross-turn)
    ─► gpt-5.4 verbosity medium|high (A/B decided) ─► Cartesia sonic-3.6 ─► PCM out
```

## File Map
| File (absolute) | What changes | N/E/D |
|---|---|---|
| `/tmp/opencode/wt-iter59/engine/diallux/graph/builder.py` | (a) `_RETRIEVAL_OFF` → empty (all states retrieve); (b) freshness: fire `spawn_live_retrieve` at StartOfTurn via `session._fire_live_retrieve` moved to first-final-transcript; supersede keyed by TURN not msg-text; on timeout → `_frozen_chunks` fallback (never stale-prev); await-vs-sync decision implemented per T5 evaluation; (c) dedupe v2: per-CALL question-stem window + `_semantic_dup` cosine gate 0.90 (flag `tts_dedupe_semantic`) | E |
| `/tmp/opencode/wt-iter59/engine/diallux/config.py` | `rag_live_await_ms` (150 if keep-await path), `tts_dedupe_semantic: bool = True`, `tts_dedupe_cos_threshold: float = 0.90` | E |
| `/tmp/opencode/wt-iter59/engine/diallux/app.py` | startup prewarm: idle Deepgram flux WS (KeepAlive, adopt at call 1, re-spawn on close) + idle Cartesia WS + RAG stage (embedder session, pool, Intake staging) — flag `call_prewarm` | E |
| `/tmp/opencode/wt-iter59/engine/tests/test_iter59_rag_freshness.py` | pins: all states retrieve (incl. contact_details/Booking/VerifyLead/ConfirmSlots); landed-fresh preferred over stale-prev; frozen fallback; StartOfTurn fire | N |
| `/tmp/opencode/wt-iter59/engine/tests/test_iter59_dedupe_semantic.py` | pins: 1-2-word variant dup dropped at 0.90; legit rephrase survives; cross-turn window | N |
| `/tmp/opencode/wt-iter59/engine/tests/test_iter59_prewarm.py` | pins: flag off = iter58 surface; on = conns created + adopted (fakes) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/01_assessment.md` | Phase A evidence pack: Retell dialogues, stack research, sweep table, A/B table, prompt before/after | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/01_report.md` | post-fix measurement report | N |
| `/home/julio/projects/clean_diallux_SDR/docs/CALL_FACTS.md` | iter58 + iter59 call rows (T7) | E |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT-58/59 (iter58 closeout) + PT-60/61/62 (freshness, dedupe, KB-everywhere, prewarm) | E |

## Deploy Rules
- Engine :8020 ONLY via `cd /tmp/opencode/wt-iter59/engine && bash scripts/serve_voice.sh`. NEVER bind :8000-:8003; never kill :8005/:8007/:8008/:8000 stale pids; never touch production agents or live :8001-:8003.
- Retell API: READ-ONLY GETs only. NEVER patch/post agent configs. Production agent IDs untouched.
- No Caddy/DNS changes. No prompt-file edits by the agent.
- `scripts/keyhound` before any push. `.env`/tokens never in git or chat. Public endpoint can book REAL — cancel every test booking (event 3801235 REAL).

## Tasks (in order)
### T1 — ASSESSMENT PACK (read-only; the plan's first point)
Goal: the evidence Julio asked for, before any code.
Files: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter59-kb-everywhere/01_assessment.md`.
Commands (full):
1. **Retell dialogues:** search the repo first: `grep -rl "message_with_tool_calls\|get-chat\|dialogue" /home/julio/projects/clean_diallux_SDR/research /home/julio/projects/Retell_AI_MCP_connection --include="*.json" --include="*.md" | head -40` and inspect candidates; pick 3-5 calls from iterations 7.8/7.9 (chat-tested) showing objection handling. If absent/insufficient: pull via Retell API read-only — `cd /tmp/opencode/wt-iter58/engine && set -a && . ./.env && set +a && .venv/bin/python` with `GET https://api.retellai.com/get-chat/<chat_id>` for 3-5 historical chat_ids (listed via the Langfuse-era saved chat ids in `research/transcripts/GK_chat_*.json` etc. or `list-calls`), save to `/home/julio/projects/clean_diallux_SDR/research/transcripts/retell_78_79/`.
2. Extract per call: objection turns, what the agent answered, when KB content appears (Retell agent has global KB → identify which chunk/knowledge answered).
3. **Retell stack research (Scrapling):** `/home/julio/projects/scrapling-mcp/.venv/bin/python` script (or websearch fallback) against `https://docs.retellai.com` / `https://www.retellai.com` public pages: what their production voice engine does for instant answer→speech (pre-connect/prewarm model, in-house vs provider stack). Save findings to the assessment md.
4. **Dedupe sweep (0.90 proof):** corpus = `/tmp/opencode/iter58_gens_raw.txt` question sentences + the 1-2-word variant pairs; embed with the local embedder; sweep 0.80-0.97; confirm 0.90 catches the near-verbatim injections with margin over legit rephrasings.
5. **Verbosity A/B (medium vs high):** `cd /tmp/opencode/wt-iter58/engine && set -a && . ./.env && set +a && .venv/bin/python tests/llm2llm/harness.py --personas Maria --rag --langfuse --max-turns 28` twice — once `OPENAI_VERBOSITY=medium`, once `OPENAI_VERBOSITY=high` (env override) — same persona, grade TTFT + objection-turn quality per SOP; report numbers.
6. **Vertical prompt before/after:** dump the rendered pinned-industry block + knowledge delta the model saw at turns 9→11 (from the trace rag spans + `render_pinned_section` output) into the assessment md.
Verification: `01_assessment.md` on disk with SQL/API citations; sweep table; A/B table; 3-5 Retell dialogues archived.
Dependencies: none. NO CODE CHANGES in T1.
### T2 — Owner review of the assessment (HITL gate)
Owner reads `01_assessment.md`, rewrites prompts if moved, approves/denies painification KB creation, approves Phase B scope. Telegram ping BEFORE the ask.
### T3 — RAG freshness fix
Goal: fresh chunks ≥ every round; await ≈0 when landed; never stale-prev.
Files: `builder.py`, `config.py`, pins.
Commands: implement BOTH variants behind a flag (`rag_fire_mode: speech-window | round-sync`); the T5 evaluation picks the winner; suite `cd /tmp/opencode/wt-iter59/engine && .venv/bin/python -m pytest tests -o addopts="" -q` → 368 + pins.
Verification: pins (landed-fresh preferred, frozen fallback, StartOfTurn fire); live gate ≥90% `degraded=False`, `await_ms` p50 ≤15 ms.
Dependencies: T2 GO.
### T4 — KB everywhere + dedupe v2 0.90
Files: `builder.py`, `config.py`, pins.
Commands: remove `_RETRIEVAL_OFF` (all states retrieve); dedupe semantic 0.90 cross-turn; suite green; re-run the bug-coverage queries after the change (fixes break other things).
Verification: `kb_slugs_for(state)` non-empty for ALL sales states; 0.70-string pair caught at cosine; 0.65 legit survives.
Dependencies: T2 GO.
### T5 — Prewarm
Files: `app.py`, pins.
Commands: implement flag `call_prewarm`; restart :8020 `bash scripts/serve_voice.sh`; measure Deepgram connect delta (baseline 1.4 s).
Verification: startup log shows prewarm lines; synthetic call connect ≤300 ms; suite green.
Dependencies: T2 GO (independent of T3/T4 files).
### T6 — Owner live call + gates
Commands: Telegram ping; owner calls the SAME tokenized URL; extraction: degraded histogram, contact_details rag rows, dedupe drops, greeting first-audio, prewarm timings; import via the micbridge-filter workaround pattern (documented in iter58 report).
Gates: fresh ≥90% · await p50 ≤15 ms · 0 cross-turn near-verbatim re-asks · server answer→speech ≤1.5 s · e2e p50 ≤1100 ms · bookings cancelled.
Dependencies: T3-T5 on :8020 + Julio's prompts deployed.
### T7 — Closeout + ASK
Commands: iter58 leftovers (CALL_FACTS rows, PENDING_TASKS PT-58/59) + iter59 report + docs to main + code commits on branch + Telegram ping; ASK JULIO: (a) merge, (b) keep flores/voice endpoint, (c) painification KB go/no-go, (d) US-East migration ops plan as separate session.
Verification: ledger rows queryable; bookings cancelled; ping sent.

## Validation Plan (end-to-end)
1. T1 assessment pack on disk (owner-approved).
2. T3-T5 suite 368+ green with new pins.
3. T6 live call gates all green; trace + ledger import.
4. T7 docs/commits done; ASK asked.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| US-East server migration | owner: later, after production testing |
| `pain-amplification` KB ingest | owner content + cost sign-off (T2); agent never hand-creates KBs |
| Engine-side math humanization | owner chose platform-side prompt pattern |
| `min-trailing-silence` EOT guard | only if the live call still shows sub-800 ms EOT fires |
| iter58 access-log token redaction | cutover-era ops plan |
| Default-vertical industry assumption | owner rejected pin-at-init; dv-gating stays |
