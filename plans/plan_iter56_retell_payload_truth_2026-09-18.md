# PLAN — iter56 RETELL PAYLOAD TRUTH (analysis-only session: decode deployed-agent logs, ground the architecture verdict)

## Meta
- Date: 2026-09-18
- Project root: `/home/julio/projects/clean_diallux_SDR`
- Scope: ANALYSIS ONLY (no code, no branches, no implementation). Decode the DEPLOYED Retell agent's actual per-turn log payloads (disk corpus + optional live API pull) to ground the fix architecture for the "stupid Intake" + cache-floor mess. Output = payload-anatomy + fidelity-comparison reports and an iter56 fix-spec draft for owner approval.
- Status: **PLAN ONLY (not started — awaits owner approval)** — fresh session starts here.
- This plan was written per `/home/julio/projects/new_plan_sop.md`. Prior session context is in `research/surgeon/retell-payload-truth/T0_session_verdict.md` (the two verdict responses, verbatim) — read it FIRST.

## Compaction Context (session 2026-09-18 — pin, do not re-derive)

- **What triggered this:** two live browser-mic voice calls on the iter55 engine (port 8020, isolated) were conversational disasters ("stupid Intake", verbatim question re-asking, 10-min cap cut call 2 at turn 61/603 s). Latency was GOOD both calls. Owner ordered a deep read-only comparison: engine vs deployed Retell agent ("retail logs", "pinned Jason chats").
- **Cache-token verdict (T0 Part 1):** engine cache_read only ever takes {0, 1664, 2688, 3712, 4736} — flat/oscillating floors per state, NEVER climbing with history (tonight's 86 `round usage` lines + ledger happy-d/happy-plumber-b + iter44 report). Causes: (1) the state-block re-renders every turn (ingest, builder.py:2189-2191) so everything after `[tools][main]` re-bills; (2) the 16-msg hysteretic window slides every ~3-4 turns (builder.py:1345-1359); warm only re-primes at transitions. Measured waste: ~300-2,900 uncached tokens/round, median ~1,000-1,500.
- **Retell design verdict (T0 Part 2):** deployed Linda (`retell/sdr/current/retell/llm.json`, V7.9_slot_lock, gpt-5.2, `agent_f305981ef7b5ce312c1c899bbf`, llm `llm_cd0464ddca4fa415cc7190cb7f7b`, deployed 2026-09-03 on the NEW Retell account) has ZERO cache/warm machinery. Per turn: `[system: general_prompt + CURRENT state prompt, {{dv}} SUBSTITUTED with live values] + [FULL transcript, no trimming]`. Provider auto-cache rides the stable system + append-only history. V7.9 LAB proof: full KB inline ~9K tokens, no retrieval, 0.84 s avg LLM latency.
- **THE ROOT-CAUSE FINDING (smoking gun):** engine `static_head` (builder.py:1292-1297) deliberately renders `{{var}}` tokens LITERAL (`subst.subst(text, {}, kb=...)` — dvs={} for byte-stability). The engine's model reads Intake.md's "# Context you have — `{{callback_number}}` may already hold the number…" with a DEAD PLACEHOLDER; the deployed model reads the same prompt text with the real value substituted every turn. Without value-anchored context, the model walks Intake.md's scripted Conversation Flow (7 verbatim question variants observed) until the extraction gate forces garbage extraction. This is "it's filling the {{extracted values}} and asking verbatim questions" — the owner's exact observation.
- **Owner architectural mandate (verbatim intent):** "the delta should always contain main plus state — this is mandatory — if not, what the fuck are we doing, why the hell do we have a state machine" + pinned RAG KBs ride the delta too; fresh retrieval also rides post-history. Verified mapping (T0 Part 2 table): prefix `[tools][main head, {{var}} stripped][FULL history append-only]` / delta (last message, ~200-400 tok/round) `[state: live dvs values][pinned-KB block][fresh retrieval]`. Matches iter32's recency finding (state must be the LAST message the model reads) and kills both cache mutators.
- **iter55 execution state:** branch `engine/iter55-tts-era-turn1-ammo` @ `7ac9879` (worktree `/tmp/opencode/wt-iter55`). DONE: C0 (Rourke fixture fix, suite 333), C0.5 (hitl_ping.py, test ping landed), C1/T0 observability (suite 346, chat spans verified in trace `d28d7d56b53a`, voice spans verified in `cc29eed37db9`: `greeting:first_audio`, `greeting`, warm spans, `await_warm`). NOT DONE: C2 (split lite cap), T1-T7. **iter55 is PAUSED** — owner redirected to this analysis session. The T0 observability spans are the instrument that will PROVE the iter56 fix later.
- **Voice-call evidence saved:** Langfuse traces `cc29eed37db9` (call 1, micbridge-57e8db2596ab, garbled STT "Sparkly") and `8d13f0b571e7` (call 2, micbridge-498d2df17fd7, good STT, full funnel run to ConfirmSlots then cap); full uvicorn log copied to `research/surgeon/retell-payload-truth/uvicorn8020_both_calls_0918.log`. Test server on :8020 KILLED. Chat harness run `d28d7d56b53a`/`483f49e45026` (Rourke, booked, PASS).
- **Cal.com anomaly (open):** the Rourke run's recorded booking uid `qeTqHuZ1EDzH8bxEdhPQ6H` resolves via Cal API v2 (Bearer auth, key `CAL_COM_API_KEY` in `/home/julio/projects/Retell_AI_MCP_connection/.env`) to an OLD Sep-4 CANCELLED booking — and a full upcoming-bookings scan returned 0. Either the booking never really created (slot/reservation echo from warm_slots) or it lives under a different credential scope. Must be verified + cancelled if real (event `3801235` is REAL).
- **Jason chats:** NOT on disk (exhaustive search — only UK-names dictionary hits). Likely pinned in the Retell dashboard; pull attempt = T3 below. Best on-disk fidelity evidence: 293-file `*_chat_*` corpus (real deployed agents V6.90→V7.8, GPT-4o persona callers) with 3 extracted verbatim intakes showing perfect fidelity (acknowledge → ONE question → reuse every fact).
- **Deployed-agent corpora locations (all verified):** `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/testing/json_logs/` (293 files, harness `test_llm_to_llm.py` → api.retellai.com create-chat/create-chat-completion, CHAT_AGENT_ID recorded per file); byte-identical fork copies at `retell/sdr/testing/json_logs/` and `research/transcripts/` (293 `*_chat_*` files: BOOK 91, GK 65, BRK 65, NO-BOOK 42, CURVE 30). Chat-file fields: `chat_id, chat_type:"api_chat", agent_id, agent_name, retell_llm_dynamic_variables, collected_dynamic_variables, transcript, message_with_tool_calls[], tool_call_invocation/tool_call_result/state_transition roles, start_timestamp/end_timestamp`.
- **iter23/iter24 banked comparisons:** `research/reports/iter23_toe_to_toe_verdict.md` (v5 38.25 vs Retell 38.39 — tie, Retell wins tie-breaks; v5 leaks price 5×, over-pulls KBs 2-9×, 68% of sales-psychology pulls wasted in Closing), `iter24_deviation_audit.md` (deployed prompts byte-stable V7.4→V7.9; v5 EXTENDED away: general_prompt.md 1052 words with no deployed equivalent, 28 refer lines vs 14).

## Resolved Decisions (DO NOT revisit)
| Decision | Rationale |
|---|---|
| This session = ANALYSIS ONLY: no engine code, no branches, no implementation | Owner: "we will work on this, not implement, keep analyzing"; "no touching anything" |
| iter55 execution PAUSED at C1 (`7ac9879`); C2/T1-T7 resume only after this analysis | Owner redirect 2026-09-18 |
| THE FIX ARCHITECTURE (iter56 candidate): prefix `[tools][main][full history append-only]`; delta (last message) = state (live dvs) + pinned-KB + fresh retrieval; drop/shrink the 16-msg window; strip literal `{{var}}` from the head | Owner mandate ("delta must always contain main plus state") + Retell-verified design + iter32 recency finding; still needs payload ground-truth before implementation (this plan) |
| Ground truth FIRST from actual deployed payloads (not platform docs) | Owner: "sneak in a couple of conversations and see the actual behavior… go check what I told you" |
| Jason/real chats pulled via Retell API (read-only GET) if the corpus lacks them | Owner ordered real-conversation evidence; best-effort |
| HITL Telegram pings fire BEFORE any question/ask, never after | Owner directive 2026-09-18 ("notifs should come before I answer") |
| Cal.com test bookings: none upcoming found today; the uid-echo anomaly must still be verified | Law: event 3801235 is REAL |

## BLOCKED / NEEDS INPUT
| Item | Where to get it |
|---|---|
| Exact `/v3/list-chats` request body schema (params: agent_id, filters, limit, sort) | Read `docs/api/RETELL_API_REFERENCE.md` §Chat Sessions in `/home/julio/projects/Retell_AI_MCP_connection/` (spec section exists; body shape to be read there) |
| Whether pinned Jason chats are retrievable via API | T3 `POST /v3/list-chats` on `agent_f305981ef7b5ce312c1c899bbf` (current account); older eras may need the account of `agent_87e4d5f08475e5bc558b2f390f` — the ACTIVE `RETELL_API_KEY` in the original `.env` is the new-Retro-workspace key (promoted from RETELL_CESAR_KEY) |
| Rourke-run real booking existence (start ~2026-09-19 18:00Z) | The `/book-livecall` webhook's own Cal credential scope (UNKNOWN which .env the booking service uses — original workspace `services/`) or the owner's Cal dashboard |
| KB retrieved-contents content | CloudFront URLs per conversation (see `research/reports/iter23_corpus_manifest.json` key `deployed`) — fetch a sample and cache the text into evidence |
| iter56 approval + scope split (fold into iter55 vs own branch) | Owner, at T5 gate |

## Environment & Dependencies
- Python: `/home/julio/projects/clean_diallux_SDR/engine/.venv/bin/python` (3.12.3; ALWAYS `<venv>/bin/python -m pip`, never the pip script). `requests` available.
- Secrets: `RETELL_API_KEY` (ACTIVE — new Retro workspace key) in `/home/julio/projects/Retell_AI_MCP_connection/.env` (also in `engine/.env`); `CAL_COM_API_KEY` (cal_live…) in `/home/julio/projects/Retell_AI_MCP_connection/.env`. NEVER print values; run `scripts/keyhound` before any push.
- Retell API: base `https://api.retellai.com`; `POST /v3/list-chats` (replaces deprecated `GET /list-chat`); `GET /get-chat/{chat_id}` returns full transcript + variables + cost; auth header `Authorization: Bearer <RETELL_API_KEY>`. READ-ONLY use only (list/get — never create/end/update).
- Corpus paths (read-only, NEVER modify): `/home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/testing/json_logs/` (293 files); fork copies `/home/julio/projects/clean_diallux_SDR/retell/sdr/testing/json_logs/` and `/home/julio/projects/clean_diallux_SDR/research/transcripts/`.
- Deployed config (read-only): `/home/julio/projects/clean_diallux_SDR/retell/sdr/current/retell/llm.json` (md5 `05258ab8f57b7527af0bc92169297641`); prompts `retell/sdr/current/retell/prompts/` (Intake.md verbatim in T0 verdict).
- Engine evidence (read-only): worktree `/tmp/opencode/wt-iter55` @ `7ac9879`; Langfuse `http://localhost:3001` with `engine/scripts/lf.py` (health/traces/show/gens); traces: `8d13f0b571e7` (voice call 2), `cc29eed37db9` (voice call 1), `d28d7d56b53a` (chat Rourke). Voice round-usage lines: `research/surgeon/retell-payload-truth/uvicorn8020_both_calls_0918.log` (grep `round usage`).
- Ledger: `/home/julio/projects/clean_diallux_SDR/research/surgeon/iter48-rag-truth/ledger.db` (tables runs/calls/rounds/rag/findings; NO sqlite3 CLI — `<venv>/bin/python -c "import sqlite3…"`; cache_read data verified tonight).
- iter44 report: `research/surgeon/iter44-cache-floor/01_report.md` (T3 section = the original floor phenomenon).
- Evidence output dir: `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/` (gitignored).
- Egress note: outbound HTTP from `julio` rides the egress proxy — the heating-uk scripts called api.retellai.com successfully from this box before.

## Architecture
```
DEPLOYED RETELL (ground truth to decode)        ENGINE (current, the problem)
┌─────────────────────────────────────┐   ┌──────────────────────────────────────────┐
│ per turn:                           │   │ per round:                               │
│  [system: general + state prompt    │   │  [tools][head general+state {{var}}      │
│   with {{dv}} values SUBSTITUTED]   │   │   LITERAL][state-block (mutates/turn)]   │
│  + [FULL transcript (no trim)]      │   │  + [16-msg hysteretic window (slides)]   │
│  + [KB retrieval: top_k=3 filter .6]│   │  + [delta: live RAG + pin]               │
│ no warm, no window, no state block  │   │  + warm machine compensating for busts   │
│ → provider auto-cache grows freely  │   │  → cache pinned at [tools][main] floors  │
└─────────────────────────────────────┘   └──────────────────────────────────────────┘
              ▲ decode from actual logs ▼                ▲ iter56 target shape ▼
┌─────────────────────────────────────┐   ┌──────────────────────────────────────────┐
│ T1-T4 of this plan: exact per-turn  │   │ prefix [tools][main][FULL history];      │
│ payload: system composition, dv     │   │ delta (last msg) = state values + pin +  │
│ substitution timing, KB injection   │   │ fresh retrieval; {{var}} never literal   │
│ point, tool-result placement,       │   │                                          │
│ memory/redundancy behavior          │   │                                          │
└─────────────────────────────────────┘   └──────────────────────────────────────────┘
```

## File Map
| File (absolute) | What changes | N/E/D |
|---|---|---|
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/01_corpus_and_payload.md` | corpus inventory (293 files classified by agent_id/date/class) + full JSON field schema + the 10 most-recent conversations listed | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/02_payload_anatomy.md` | EXACT per-turn message shape the deployed model receives: system composition, {{dv}} substitution ground truth, history shape (full/trimmed), KB-retrieval injection point, tool-result placement — reconstructed from 3 representative conversations | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/api_pull/` | 10 recent chats pulled via `POST /v3/list-chats` + `GET /get-chat/` (raw JSON, read-only) | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/03_fidelity_comparison.md` | deployed vs engine grid: question-redundancy counts, dv visibility, KB injection, memory reuse, first-question flow — engine side from Langfuse traces `8d13f0b571e7`/`cc29eed37db9` + the saved uvicorn log | N |
| `/home/julio/projects/clean_diallux_SDR/research/surgeon/retell-payload-truth/T0_session_verdict.md` | UPDATE at closeout: verdict confirmed/adjusted by payload evidence | E |
| `/home/julio/projects/clean_diallux_SDR/plans/plan_v5_iter56_<slug>.md` | iter56 fix-spec DRAFT (architecture + file map + gates) — owner approval gate, NOT executed | N |
| `/home/julio/projects/clean_diallux_SDR/plans/PENDING_TASKS.md` | PT rows: PT-53 (Intake verbatim loop + {{dv}} blindness), PT-54 (TTS-bleed echo), PT-55 (cache floors), PT-56 (booking uid echo anomaly) | E |
| NOTHING under `engine/` or `retell/` | read-only session | — |

## Deploy Rules
- READ-ONLY on: both repos' corpora, `retell/sdr/current/`, production agents (`agent_f305981ef7b5ce312c1c899bbf` current, `agent_87e4d5f08475e5bc558b2f390f` legacy, voice `agent_16985b5d087e56c35141983396`), live :8000-:8006, services. Retell API calls = GET/list only (never create-chat, never update/end anything).
- Engine worktree `/tmp/opencode/wt-iter55` stays at `7ac9879` — ZERO code changes this session (iter55 C2 resumes ONLY on owner say-so).
- Never restart/patch an existing Retell LLM; never bind ports; no merges/pushes; `scripts/keyhound` before any push (docs → main per LAW 0 only on owner say-so).
- No uvicorn services needed this session (no live voice tests planned).
- Every analysis artifact lands in `research/surgeon/retell-payload-truth/` (gitignored evidence zone).

## Tasks (in order)
### T1 — Corpus inventory + classification (disk, no API)
Goal: know exactly what we have locally, classify by deployed agent/version/date, pick the newest 10.
Files: writes `01_corpus_and_payload.md`.
Commands (full):
```
cd /home/julio/projects/clean_diallux_SDR/engine && .venv/bin/python - <<'EOF'
# 1) walk /home/julio/projects/Retell_AI_MCP_connection/Dialux_SDR/testing/json_logs/
#    load each json; collect: file, agent_id, agent_name, start_timestamp (ms→UTC), persona (transcript[0] user line), booked?
# 2) sort by start_timestamp desc; print top 20
# 3) for the newest file: print the COMPLETE key structure + one full message_with_tool_calls entry (verbatim JSON)
EOF
```
Verification: `01_corpus_and_payload.md` exists with ≥293 classified rows, the top-10 list, and one full verbatim message entry.
### T2 — Per-turn payload anatomy (the ground truth)
Goal: reconstruct EXACTLY what the deployed model received per turn — system composition (is the state prompt separate or merged? is {{dv}} substituted inline?), history shape (full transcript every turn? trimming?), where `knowledge_base_retrieved_contents` land, where tool results appear, where dvs appear.
Files: writes `02_payload_anatomy.md`.
Commands: python walk of 3 conversations (1 BOOK happy from the current era, 1 GK adversarial, 1 BRK breaker) from the disk corpus — print per-message: role, length, first 200 chars; note every `tool_call_invocation`/`tool_call_result`/`state_transition` entry and any KB-retrieval field; compare `retell_llm_dynamic_variables` vs `collected_dynamic_variables` timing. If KB content is behind CloudFront URLs: fetch ONE sample (GET, read-only) to see the payload shape.
Verification: the md contains a message-shape table that answers, with file+line citations: (a) is the system message stable within a state? (b) are dvs substituted into the prompt text and WHEN? (c) where do KB chunks inject (per turn? cached?)? (d) is history full-length? (e) how do tool results reach the model?
### T3 — Real-chat pull via API (option — owner-ordered if T2's corpus feels persona-stale)
Goal: 10 most recent REAL chats of the deployed agent (find Jason).
Files: writes `api_pull/*.json` + a pull script under `research/surgeon/retell-payload-truth/` (script lives in evidence, never in engine/).
Commands (full):
```
cd /home/julio/projects/clean_diallux_SDR/engine && set -a && . /home/julio/projects/Retell_AI_MCP_connection/.env && set +a && .venv/bin/python scripts/../../retell-payload-truth-pull.py   # script path: research/surgeon/retell-payload-truth/pull_chats.py
# pull_chats.py: POST https://api.retellai.com/v3/list-chats  body={"agent_id":"agent_f305981ef7b5ce312c1c899bbf","limit":10} (EXACT body shape: read docs/api/RETELL_API_REFERENCE.md §Chat Sessions FIRST — if UNKNOWN, mark BLOCKED and fall back to T1 corpus)
# then GET /get-chat/{chat_id} for each → save to research/surgeon/retell-payload-truth/api_pull/
```
Verification: ≥10 full transcripts on disk; grep them for "Jason"; note agent_id/llm version per chat.
### T4 — Fidelity grid + verdict consolidation
Goal: answer the owner's question with counts, not vibes: same-question-repeat density in deployed intakes (0 expected) vs engine voice call (7 variants) vs engine chat runs (iter23 corpus); dv-value visibility (deployed: substituted vs engine: literal `{{var}}`); KB injection timing.
Files: writes `03_fidelity_comparison.md`; updates `T0_session_verdict.md` if the payload evidence adjusts any verdict.
Verification: every row of the grid cites a file path + quote or trace ID.
### T5 — iter56 fix-spec draft + closeout (GATE: owner ping BEFORE the ask, per new ping protocol)
Goal: draft `plans/plan_v5_iter56_<slug>.md` (state→delta relocation, {{dv}} rendering fix, window removal/shrink, warm-machine repurpose for cross-call colds, T0-span verification of cache floors before/after) + PENDING_TASKS PT rows + Telegram ping "plan ready for review" THEN the approval ask.
Verification: plan file passes the SOP "lobotomized agent" test; PT rows reference evidence paths.

## Validation Plan (end-to-end)
1. T1: 01 file exists; ≥293 rows; one verbatim message dump.
2. T2: 02 exists; every question in "the payload anatomy" answered with a field citation (no UNKNOWN left except those in BLOCKED).
3. T3 (if run): 10 transcripts on disk; Jason searched.
4. T4: every claim cites corpus file / trace ID / ledger round row.
5. T5: iter56 draft plan exists; PT rows written; owner pinged BEFORE the approval ask.

## Deferred / Not In This Plan
| Item | Why |
|---|---|
| ANY engine code change ({{dv}} fix, delta relocation, window, C2 split cap) | iter56/iter55 scope — owner approval gate; this session is analysis-only |
| iter55 T1-T7 execution | paused; resumes after this analysis (owner decision) |
| Heating-UK agent payloads | different agent line; out of scope |
| Real-Twilio cutover work | separate owner decision |
| kb_chunks DB writes | NEVER (SELECT-count only, law) |
